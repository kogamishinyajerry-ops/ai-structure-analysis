"""Layer-3 unit-conversion tests — RFC-001 §4.6 + ADR-003."""

from __future__ import annotations

import numpy as np
import pytest

from app.core.types.quantity import Quantity, _unregister_converter
from app.domain.units import (
    UnitConversionError,
    convert,
    conversion_factor,
    dimension_of,
    is_compatible,
    supported_units,
)


# --- closed-set surface ---------------------------------------------------


def test_supported_units_is_closed_and_sorted() -> None:
    units = supported_units()
    expected = {
        "m", "mm", "in",
        "Pa", "kPa", "MPa", "GPa", "psi",
        "kg", "t", "slug",
        "N", "kN", "lbf",
        "s", "ms", "min", "hr",
    }
    assert set(units) == expected
    assert list(units) == sorted(units)


def test_dimension_of_known_units() -> None:
    assert dimension_of("m") == "length"
    assert dimension_of("MPa") == "stress"
    assert dimension_of("kg") == "mass"
    assert dimension_of("N") == "force"
    assert dimension_of("s") == "time"


def test_dimension_of_unknown_raises() -> None:
    with pytest.raises(UnitConversionError, match="unknown unit"):
        dimension_of("furlong")


def test_is_compatible_same_dimension_true() -> None:
    assert is_compatible("m", "mm")
    assert is_compatible("Pa", "psi")
    assert is_compatible("kg", "slug")


def test_is_compatible_cross_dimension_false() -> None:
    assert not is_compatible("m", "Pa")
    assert not is_compatible("kg", "N")


def test_is_compatible_unknown_unit_false() -> None:
    assert not is_compatible("m", "furlong")
    assert not is_compatible("furlong", "m")


# --- conversion factor invariants -----------------------------------------


def test_factor_identity_is_one() -> None:
    for u in supported_units():
        assert conversion_factor(u, u) == pytest.approx(1.0, rel=1e-12)


def test_factor_round_trip_is_one() -> None:
    pairs = [("m", "mm"), ("Pa", "psi"), ("kg", "slug"), ("N", "lbf")]
    for a, b in pairs:
        f_ab = conversion_factor(a, b)
        f_ba = conversion_factor(b, a)
        assert f_ab * f_ba == pytest.approx(1.0, rel=1e-9)


def test_factor_known_lengths() -> None:
    assert conversion_factor("m", "mm") == pytest.approx(1000.0)
    assert conversion_factor("mm", "m") == pytest.approx(1e-3)
    assert conversion_factor("in", "mm") == pytest.approx(25.4)
    assert conversion_factor("mm", "in") == pytest.approx(1.0 / 25.4)


def test_factor_known_stress() -> None:
    assert conversion_factor("MPa", "Pa") == pytest.approx(1e6)
    assert conversion_factor("Pa", "MPa") == pytest.approx(1e-6)
    assert conversion_factor("psi", "Pa") == pytest.approx(6894.757293168361)


def test_factor_known_mass_and_force() -> None:
    assert conversion_factor("t", "kg") == pytest.approx(1000.0)
    assert conversion_factor("kN", "N") == pytest.approx(1000.0)
    assert conversion_factor("lbf", "N") == pytest.approx(4.4482216152605)


def test_factor_unknown_source_raises() -> None:
    with pytest.raises(UnitConversionError, match="unknown source unit"):
        conversion_factor("furlong", "m")


def test_factor_unknown_target_raises() -> None:
    with pytest.raises(UnitConversionError, match="unknown target unit"):
        conversion_factor("m", "furlong")


def test_factor_cross_dimension_raises() -> None:
    with pytest.raises(UnitConversionError, match="incompatible dimensions"):
        conversion_factor("m", "Pa")


# --- convert() scalar + array --------------------------------------------


def test_convert_scalar_length() -> None:
    assert convert(1.0, "m", "mm") == pytest.approx(1000.0)
    assert convert(2.54, "in", "mm") == pytest.approx(64.516)


def test_convert_scalar_stress() -> None:
    assert convert(7.5, "MPa", "Pa") == pytest.approx(7_500_000.0)
    assert convert(1.0, "psi", "kPa") == pytest.approx(6.894757293168361)


def test_convert_array_returns_fresh_array() -> None:
    src = np.array([1.0, 2.0, 3.0])
    dst = convert(src, "m", "mm")
    assert isinstance(dst, np.ndarray)
    assert np.allclose(dst, [1000.0, 2000.0, 3000.0])
    # Source must NOT be mutated by the conversion.
    assert np.array_equal(src, np.array([1.0, 2.0, 3.0]))
    # Result must be a fresh array (mutating it doesn't change src).
    dst[0] = -1.0
    assert src[0] == 1.0


def test_convert_propagates_unknown_unit() -> None:
    with pytest.raises(UnitConversionError):
        convert(1.0, "furlong", "m")


# --- Quantity.to integration ---------------------------------------------


def test_quantity_to_after_units_imported() -> None:
    # Importing this test module already imported app.domain.units, so
    # the converter should be wired up.
    q = Quantity(value=1.0, unit="m")
    q_mm = q.to("mm")
    assert isinstance(q_mm, Quantity)
    assert q_mm.unit == "mm"
    assert q_mm.value == pytest.approx(1000.0)
    # Original is immutable (frozen dataclass) and unchanged.
    assert q.unit == "m"
    assert q.value == 1.0


def test_quantity_to_array_value() -> None:
    arr = np.array([7.5, 15.0])
    q = Quantity(value=arr, unit="MPa")
    q_pa = q.to("Pa")
    assert q_pa.unit == "Pa"
    assert isinstance(q_pa.value, np.ndarray)
    assert np.allclose(q_pa.value, [7_500_000.0, 15_000_000.0])


def test_quantity_to_raises_when_no_converter_registered() -> None:
    """ADR-003 spirit: Quantity is pure Layer 2; if Layer 3 hasn't been
    imported, ``Quantity.to`` must fail loudly rather than silently
    returning the source value or guessing a conversion.
    """
    _unregister_converter()
    try:
        q = Quantity(value=1.0, unit="m")
        with pytest.raises(NotImplementedError, match="app.domain.units"):
            q.to("mm")
    finally:
        # Re-register for any subsequent tests that rely on the wiring.
        from app.domain.units import _convert_quantity
        from app.core.types.quantity import _register_converter

        _register_converter(_convert_quantity)
