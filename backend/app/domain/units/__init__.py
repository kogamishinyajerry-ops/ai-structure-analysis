"""Unit conversion — RFC-001 §4.6 trap #6 + ADR-003.

Pure-numeric, closed-set conversions between the three MVP unit systems
(SI / SI_mm / English). The closed-set discipline mirrors ADR-002:
adding a new unit requires an RFC; never expand the dictionary in a
feature branch. Open-vocabulary unit strings (``"m/s"``,
``"kg/m^3"``, composite units) are intentionally NOT supported in MVP
— design-institute static-strength reports rely on the four basic
scalars below.

Module surface:

  convert(value, from_unit, to_unit) -> value
      Convert a scalar or NDArray. ``from_unit`` and ``to_unit`` MUST
      share a dimension; otherwise ``UnitConversionError``.

  conversion_factor(from_unit, to_unit) -> float
      The multiplicative factor: ``value_to = value_from * factor``.

  is_compatible(unit_a, unit_b) -> bool
      Whether two units share a dimension.

  dimension_of(unit) -> str
      ``"length" | "stress" | "mass" | "force" | "time"``.

ADR-003: importing this module registers the converter on
``app.core.types.Quantity`` so ``q.to("mm")`` works. Without this
import, ``Quantity.to`` raises ``NotImplementedError``.
"""

from __future__ import annotations

from typing import Union

import numpy as np
import numpy.typing as npt

from app.core.types.quantity import Quantity, _register_converter

__all__ = [
    "UnitConversionError",
    "convert",
    "conversion_factor",
    "dimension_of",
    "is_compatible",
    "supported_units",
]


class UnitConversionError(ValueError):
    """Raised when a unit string is unknown or two units do not share a dimension."""


# --- closed-set conversion table -----------------------------------------
#
# Stored as factors to a per-dimension SI base unit. Conversion between
# any two units of the same dimension is then
#
#     factor(from -> to) = factor(from -> SI) / factor(to -> SI)
#
# Adding a new unit is one line in the relevant dimension's dict; new
# DIMENSIONS require an RFC.

_UNIT_TO_SI: dict[str, tuple[str, float]] = {
    # length — SI base = m
    "m": ("length", 1.0),
    "mm": ("length", 1e-3),
    "in": ("length", 0.0254),
    # stress — SI base = Pa
    "Pa": ("stress", 1.0),
    "kPa": ("stress", 1e3),
    "MPa": ("stress", 1e6),
    "GPa": ("stress", 1e9),
    "psi": ("stress", 6894.757293168361),
    # mass — SI base = kg
    "kg": ("mass", 1.0),
    "t": ("mass", 1e3),         # tonne (SI_mm convention)
    "slug": ("mass", 14.59390294),
    # force — SI base = N
    "N": ("force", 1.0),
    "kN": ("force", 1e3),
    "lbf": ("force", 4.4482216152605),
    # time — SI base = s
    "s": ("time", 1.0),
    "ms": ("time", 1e-3),
    "min": ("time", 60.0),
    "hr": ("time", 3600.0),
}


def supported_units() -> tuple[str, ...]:
    """Return the closed set of known unit strings (sorted)."""
    return tuple(sorted(_UNIT_TO_SI))


def dimension_of(unit: str) -> str:
    """Return the dimension name for ``unit`` or raise ``UnitConversionError``."""
    try:
        return _UNIT_TO_SI[unit][0]
    except KeyError as exc:
        raise UnitConversionError(
            f"unknown unit {unit!r}; supported: {supported_units()!r}"
        ) from exc


def is_compatible(unit_a: str, unit_b: str) -> bool:
    """``True`` when both units exist and share the same dimension."""
    try:
        return _UNIT_TO_SI[unit_a][0] == _UNIT_TO_SI[unit_b][0]
    except KeyError:
        return False


def conversion_factor(from_unit: str, to_unit: str) -> float:
    """Return the multiplier such that ``value_to = value_from * factor``.

    Raises ``UnitConversionError`` if either unit is unknown or the two
    units do not share a dimension.
    """
    try:
        from_dim, from_si = _UNIT_TO_SI[from_unit]
    except KeyError as exc:
        raise UnitConversionError(
            f"unknown source unit {from_unit!r}; supported: {supported_units()!r}"
        ) from exc
    try:
        to_dim, to_si = _UNIT_TO_SI[to_unit]
    except KeyError as exc:
        raise UnitConversionError(
            f"unknown target unit {to_unit!r}; supported: {supported_units()!r}"
        ) from exc
    if from_dim != to_dim:
        raise UnitConversionError(
            f"cannot convert {from_unit!r} ({from_dim}) to {to_unit!r} "
            f"({to_dim}) — incompatible dimensions"
        )
    return from_si / to_si


_NumericValue = Union[float, "npt.NDArray[np.float64]"]


def convert(
    value: _NumericValue, from_unit: str, to_unit: str
) -> _NumericValue:
    """Multiply ``value`` by the appropriate conversion factor.

    Inputs are NOT mutated. Float in → float out; NDArray in → NDArray
    out (a fresh array, never a view, so the caller cannot break the
    source).
    """
    factor = conversion_factor(from_unit, to_unit)
    if isinstance(value, np.ndarray):
        return value * factor  # broadcasts; result is a fresh array
    return float(value) * factor


def _convert_quantity(qty: Quantity, to_unit: str) -> Quantity:
    """Backing implementation registered onto :meth:`Quantity.to`."""
    new_value = convert(qty.value, qty.unit, to_unit)
    return Quantity(value=new_value, unit=to_unit)


# Register on import so ``Quantity(value=1.0, unit="m").to("mm")`` works
# from any caller that imports this package (or any package that depends
# on it).
_register_converter(_convert_quantity)
