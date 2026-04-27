"""Layer-3 stress-linearization tests — RFC-001 §6.4 / ASME VIII Div 2 §5.5.

The tests exercise:
  * Algebraic invariants (pure membrane, pure bending) where
    trapezoidal integration is exact
  * Combined membrane + bending recovery (still exact under trapz)
  * Quadratic input (where trapz has discretisation error) under a
    documented tolerance
  * Shape / monotonicity preconditions
"""

from __future__ import annotations

import numpy as np
import pytest

from app.domain.stress_linearization import (
    LinearizedStress,
    linearize_through_thickness,
)


# Component layout: [σ_xx, σ_yy, σ_zz, σ_xy, σ_yz, σ_xz]
ZERO_TENSOR = np.zeros(6, dtype=np.float64)


# --- algebraic invariants -------------------------------------------------


def test_pure_membrane_yields_zero_bending_and_peak() -> None:
    """A constant tensor along the SCL is pure membrane: bending and
    peak must be exactly zero, and membrane must equal the input."""
    sigma_const = np.array(
        [100.0, 50.0, 25.0, 10.0, 5.0, 2.5], dtype=np.float64
    )
    n = 7
    s = np.linspace(0.0, 1.0, n)
    tensors = np.tile(sigma_const, (n, 1))

    result = linearize_through_thickness(tensors, s)

    assert isinstance(result, LinearizedStress)
    assert np.allclose(result.membrane, sigma_const, atol=1e-12)
    assert np.allclose(result.bending_outer, ZERO_TENSOR, atol=1e-12)
    assert np.allclose(result.peak, 0.0, atol=1e-12)


def test_pure_bending_linear_field_has_zero_membrane_and_peak() -> None:
    """A linear-in-s tensor, antisymmetric about the midplane, is
    pure bending. Trapezoidal integration is exact for linear inputs,
    so membrane and peak must be zero to floating-point tolerance."""
    n = 11
    s = np.linspace(0.0, 2.0, n)  # t = 2, s_mid = 1
    s_mid = 1.0
    # σ_xx varies linearly through thickness, all other components zero.
    tensors = np.zeros((n, 6), dtype=np.float64)
    tensors[:, 0] = (s - s_mid)  # σ_xx = s - s_mid

    result = linearize_through_thickness(tensors, s)

    assert np.allclose(result.membrane, ZERO_TENSOR, atol=1e-12)
    # Bending at outer surface: σ_xx component = (s_outer - s_mid) = 1.0.
    expected_bending = np.array([1.0, 0, 0, 0, 0, 0], dtype=np.float64)
    assert np.allclose(result.bending_outer, expected_bending, atol=1e-12)
    assert np.allclose(result.peak, 0.0, atol=1e-12)


def test_pure_bending_recovers_at_inner_surface_with_negated_sign() -> None:
    """Bending at the inner surface is -bending_outer; reconstructing
    σ at the inner sample must match the original tensor exactly."""
    n = 5
    s = np.linspace(0.0, 1.0, n)
    s_mid = 0.5
    tensors = np.zeros((n, 6), dtype=np.float64)
    tensors[:, 1] = 3.0 * (s - s_mid)  # σ_yy = 3 * (s - s_mid)

    result = linearize_through_thickness(tensors, s)

    # At inner surface (s = 0): σ = membrane + bending * (2(0 - 0.5)/1)
    #                             = 0 + bending * (-1) = -bending
    sigma_inner_reconstructed = result.membrane - result.bending_outer
    assert np.allclose(sigma_inner_reconstructed, tensors[0], atol=1e-12)
    # At outer surface (s = 1): σ = membrane + bending
    sigma_outer_reconstructed = result.membrane + result.bending_outer
    assert np.allclose(sigma_outer_reconstructed, tensors[-1], atol=1e-12)


def test_combined_membrane_plus_bending_is_separable() -> None:
    """Any linear-in-s tensor decomposes exactly into a constant
    (membrane) part plus a midplane-antisymmetric (bending) part."""
    n = 9
    s = np.linspace(0.0, 4.0, n)  # t = 4
    s_mid = 2.0
    # σ_xx = 50 + 10*(s - s_mid) → membrane = 50, bending_outer = 20
    # σ_yy = 25 (pure membrane)
    # σ_xy = 5*(s - s_mid)  → membrane = 0, bending_outer = 10
    tensors = np.zeros((n, 6), dtype=np.float64)
    tensors[:, 0] = 50.0 + 10.0 * (s - s_mid)
    tensors[:, 1] = 25.0
    tensors[:, 3] = 5.0 * (s - s_mid)

    result = linearize_through_thickness(tensors, s)

    expected_membrane = np.array(
        [50.0, 25.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float64
    )
    expected_bending = np.array(
        [20.0, 0.0, 0.0, 10.0, 0.0, 0.0], dtype=np.float64
    )
    assert np.allclose(result.membrane, expected_membrane, atol=1e-12)
    assert np.allclose(result.bending_outer, expected_bending, atol=1e-12)
    assert np.allclose(result.peak, 0.0, atol=1e-12)


def test_distances_need_not_start_at_zero() -> None:
    """The SCL parametrisation is offset-invariant; only the spacing
    matters. Verify by shifting s by a constant."""
    n = 7
    s_a = np.linspace(0.0, 1.0, n)
    s_b = s_a + 100.0
    tensors = np.zeros((n, 6), dtype=np.float64)
    tensors[:, 0] = 7.0 + 3.0 * (s_a - 0.5)  # uses original midplane

    a = linearize_through_thickness(tensors, s_a)
    # For s_b the midplane is 100.5; rebuild tensors against that offset
    # so the *physical* field is the same:
    tensors_b = np.zeros((n, 6), dtype=np.float64)
    tensors_b[:, 0] = 7.0 + 3.0 * (s_b - 100.5)

    b = linearize_through_thickness(tensors_b, s_b)

    assert np.allclose(a.membrane, b.membrane, atol=1e-12)
    assert np.allclose(a.bending_outer, b.bending_outer, atol=1e-12)
    assert np.allclose(a.peak, b.peak, atol=1e-12)


# --- quadratic peak -------------------------------------------------------


def test_quadratic_peak_recovers_linear_residual() -> None:
    """A pure quadratic input σ(s) = (s - s_mid)² has membrane =
    t²/12 (the average of the parabola) and bending = 0 (the
    antisymmetric integrand averages to zero by parity). The peak
    is the parabola minus its mean — non-trivial residual at each
    point. Validate the algebraic identity rather than chase an
    arbitrary tolerance."""
    n = 9
    t = 2.0
    s = np.linspace(0.0, t, n)
    s_mid = t / 2.0
    tensors = np.zeros((n, 6), dtype=np.float64)
    tensors[:, 0] = (s - s_mid) ** 2  # σ_xx = (s - s_mid)²

    result = linearize_through_thickness(tensors, s)

    # Trapz of (s - s_mid)² over a uniformly-sampled interval has
    # an O(h²) error. Use a generous tolerance — the analytical
    # mean is t²/12 ≈ 0.333.
    assert result.membrane[0] == pytest.approx(t**2 / 12.0, rel=0.05)
    # Bending must be zero by parity (integrand is odd about midplane).
    assert np.allclose(result.bending_outer, ZERO_TENSOR, atol=1e-12)
    # Peak at midplane is -membrane (parabola is zero there); peak
    # at extremes is t²/4 - membrane.
    mid_idx = n // 2
    assert result.peak[mid_idx, 0] == pytest.approx(
        -result.membrane[0], abs=1e-12
    )
    expected_at_extremum = (t / 2.0) ** 2 - result.membrane[0]
    assert result.peak[0, 0] == pytest.approx(expected_at_extremum, abs=1e-12)
    assert result.peak[-1, 0] == pytest.approx(expected_at_extremum, abs=1e-12)


# --- shape / monotonicity preconditions ----------------------------------


def test_rejects_wrong_tensor_shape() -> None:
    s = np.array([0.0, 1.0])
    bad = np.zeros((2, 4))  # not 6 components
    with pytest.raises(ValueError, match="shape \\(N, 6\\)"):
        linearize_through_thickness(bad, s)


def test_rejects_distances_length_mismatch() -> None:
    s = np.array([0.0, 0.5, 1.0])
    tensors = np.zeros((4, 6))
    with pytest.raises(ValueError, match="match tensors along axis 0"):
        linearize_through_thickness(tensors, s)


def test_rejects_single_point() -> None:
    tensors = np.zeros((1, 6))
    s = np.array([0.0])
    with pytest.raises(ValueError, match="at least 2 SCL points"):
        linearize_through_thickness(tensors, s)


def test_rejects_non_monotonic_distances() -> None:
    s = np.array([0.0, 0.5, 0.5, 1.0])  # duplicate value
    tensors = np.zeros((4, 6))
    with pytest.raises(ValueError, match="strictly monotonically"):
        linearize_through_thickness(tensors, s)


def test_rejects_decreasing_distances() -> None:
    s = np.array([1.0, 0.5, 0.0])  # decreasing
    tensors = np.zeros((3, 6))
    with pytest.raises(ValueError, match="strictly monotonically"):
        linearize_through_thickness(tensors, s)


def test_rejects_non_uniform_spacing_codex_repro() -> None:
    """Codex R1 HIGH regression: non-uniform spacing biases the
    bending coefficient on even-symmetric fields. This is the exact
    grid Codex used to demonstrate the leak.
    """
    s = np.array([0.0, 0.1, 0.4, 1.0, 1.6, 2.0], dtype=np.float64)
    s_mid = (s[0] + s[-1]) / 2.0
    tensors = np.zeros((s.size, 6), dtype=np.float64)
    tensors[:, 0] = (s - s_mid) ** 2  # pure peak (symmetric about midplane)
    with pytest.raises(ValueError, match="uniformly-spaced"):
        linearize_through_thickness(tensors, s)


def test_rejects_subtle_non_uniform_spacing() -> None:
    """A grid where one interval is even slightly larger than the
    others must still trip the uniform-spacing guard."""
    s = np.array([0.0, 0.5, 1.0, 1.51, 2.0], dtype=np.float64)
    tensors = np.zeros((s.size, 6), dtype=np.float64)
    with pytest.raises(ValueError, match="uniformly-spaced"):
        linearize_through_thickness(tensors, s)


def test_accepts_uniform_spacing_with_floating_point_jitter() -> None:
    """Float-precision wobble from np.linspace round-trips must NOT
    trip the uniform check (rtol=1e-9)."""
    s = np.linspace(0.0, 1.0, 17)
    tensors = np.zeros((17, 6), dtype=np.float64)
    tensors[:, 0] = 5.0  # constant — easy positive case
    result = linearize_through_thickness(tensors, s)
    assert result.membrane[0] == pytest.approx(5.0)


def test_two_point_scl_is_always_uniform() -> None:
    """A 2-point SCL has only one Δs, so the uniform check is
    vacuous (n > 2 guard skipped). Make sure 2-point still works."""
    s = np.array([0.0, 1.0])
    tensors = np.array(
        [[10.0, 0, 0, 0, 0, 0], [30.0, 0, 0, 0, 0, 0]], dtype=np.float64
    )
    result = linearize_through_thickness(tensors, s)
    # Membrane = (10 + 30)/2 = 20, bending_outer = 10 (linear from 10 to 30).
    assert result.membrane[0] == pytest.approx(20.0)
    assert result.bending_outer[0] == pytest.approx(10.0)
    assert np.allclose(result.peak, 0.0, atol=1e-12)


# --- output type contracts ------------------------------------------------


def test_output_is_frozen_dataclass_with_float64_arrays() -> None:
    s = np.linspace(0.0, 1.0, 5, dtype=np.float64)
    tensors = np.zeros((5, 6), dtype=np.float64)
    tensors[:, 0] = 42.0
    result = linearize_through_thickness(tensors, s)
    assert result.membrane.dtype == np.float64
    assert result.bending_outer.dtype == np.float64
    assert result.peak.dtype == np.float64
    assert result.membrane.shape == (6,)
    assert result.bending_outer.shape == (6,)
    assert result.peak.shape == (5, 6)
    # Frozen — assignment should fail.
    with pytest.raises((AttributeError, TypeError)):
        result.membrane = np.zeros(6)  # type: ignore[misc]


def test_accepts_int_distances_and_promotes_to_float() -> None:
    """Convenience: integer distance arrays must work without the
    caller having to dtype-cast first."""
    s = np.array([0, 1, 2], dtype=np.int64)
    tensors = np.zeros((3, 6), dtype=np.float64)
    tensors[:, 0] = 10.0  # constant, pure membrane
    result = linearize_through_thickness(tensors, s)
    assert result.membrane[0] == pytest.approx(10.0)


# --- integration with stress_derivatives ---------------------------------


def test_membrane_and_bending_compose_with_von_mises() -> None:
    """The Layer-4 producer will call von_mises on (membrane) and
    (membrane + bending) to compute P_m and P_m+P_b. Verify that
    chain works end-to-end on a simple case where we know the
    expected scalar."""
    from app.domain.stress_derivatives import von_mises

    n = 5
    s = np.linspace(0.0, 1.0, n)
    s_mid = 0.5
    tensors = np.zeros((n, 6), dtype=np.float64)
    # σ_xx = 100 (membrane only) — uniaxial.
    tensors[:, 0] = 100.0

    result = linearize_through_thickness(tensors, s)

    p_m_vm = von_mises(result.membrane.reshape(1, 6))[0]
    # Uniaxial σ_xx = 100, all others 0 → von Mises = 100.
    assert p_m_vm == pytest.approx(100.0)
    # Bending is zero so P_m + P_b at outer = von_mises(membrane) too.
    sigma_outer = (result.membrane + result.bending_outer).reshape(1, 6)
    p_m_plus_p_b_vm = von_mises(sigma_outer)[0]
    assert p_m_plus_p_b_vm == pytest.approx(100.0)
