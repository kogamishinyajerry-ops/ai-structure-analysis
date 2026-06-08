"""FM-04a Phase 33 D — Hertz line-contact analytical helper tests.

Phase 33 D delivers the analytical SSOT module for the
hertz-contact-candidate cross-check; full *CONTACT PAIR ccx
integration is deferred to Phase 34 (honest scope pivot per the
Phase 33 D NOTES.md). This test pins the analytical formulas
against Johnson "Contact Mechanics" §4.2 textbook values.

Anti-gaming guards:
* A:-1 — analytical numbers pinned at high precision (1e-6
  relative tolerance) from independent textbook calculation,
  NOT from a regression against the same module's output.
* D:-3 — formulas live in hertz_contact.py; tests import and
  reuse, no parallel implementation.
* E:-1 — non-physical inputs (negative load, ν≥0.5, R≤0)
  raise ValueError per the module contract.
"""

from __future__ import annotations

import math

import pytest

from app.services.cross_check.hertz_contact import (
    HertzLineContactInputs,
    HertzLineContactSolution,
    hertz_line_contact,
    residual_pct,
)


# ─── Canonical textbook problem (Johnson §4.2 worked example) ─────
#
# Steel-on-steel: E = 210 GPa, ν = 0.3
# Cylinder: R = 10 mm, L = 20 mm
# Load: F = 1000 N
#
# Hand-computed reference values (§4.2 eq. 4.42, 4.43, 5.78):
#   E* = 210e9 / (2 (1 - 0.09)) = 115.385 GPa
#   F' = F/L = 50000 N/m
#   b  = sqrt(4 × 50000 × 0.010 / (π × 1.154e11))
#      = sqrt(2000/3.625e11) = sqrt(5.517e-9) = 74.28 µm
#   p0 = 2 × 50000 / (π × 7.428e-5) = 4.285e8 Pa = 428.5 MPa
#   δ  = (50000/(π × 1.154e11)) × (1 + 2 ln(4 × 0.010 / 7.428e-5))
#      = 1.379e-7 × (1 + 2 ln(538.55))
#      = 1.379e-7 × (1 + 12.577) = 1.873 µm
#   τ_max ≈ 0.30 × 428.5 = 128.55 MPa


CANONICAL_INPUTS = HertzLineContactInputs(
    total_load_n=1000.0,
    cylinder_radius_m=0.010,
    cylinder_length_m=0.020,
    youngs_modulus_pa=210e9,
    poisson_ratio=0.30,
)

CANONICAL_EXPECTED = {
    "effective_modulus_pa": 1.15385e11,
    "contact_half_width_m": 7.4279e-05,
    "peak_contact_pressure_pa": 4.2853e08,
    "indentation_depth_m": 1.8728e-06,
    "maximum_subsurface_shear_pa": 1.2856e08,
}


@pytest.fixture
def canonical_solution() -> HertzLineContactSolution:
    """Compute Hertz solution once for the canonical inputs."""
    return hertz_line_contact(CANONICAL_INPUTS)


def test_effective_modulus(canonical_solution: HertzLineContactSolution) -> None:
    """E* = E / (2 (1 - ν²)) for like materials; eq. 4.11 Johnson."""
    assert canonical_solution.effective_modulus_pa == pytest.approx(
        CANONICAL_EXPECTED["effective_modulus_pa"], rel=1e-4
    )


def test_contact_half_width(canonical_solution: HertzLineContactSolution) -> None:
    """b = sqrt(4 F' R / (π E*)); eq. 4.42 Johnson."""
    assert canonical_solution.contact_half_width_m == pytest.approx(
        CANONICAL_EXPECTED["contact_half_width_m"], rel=1e-4
    )


def test_peak_contact_pressure(canonical_solution: HertzLineContactSolution) -> None:
    """p_0 = 2 F' / (π b); eq. 4.43 Johnson."""
    assert canonical_solution.peak_contact_pressure_pa == pytest.approx(
        CANONICAL_EXPECTED["peak_contact_pressure_pa"], rel=1e-4
    )


def test_indentation_depth(canonical_solution: HertzLineContactSolution) -> None:
    """δ = (F'/(π E*)) × (1 + 2 ln(4 R / b)); eq. 5.78 Johnson."""
    assert canonical_solution.indentation_depth_m == pytest.approx(
        CANONICAL_EXPECTED["indentation_depth_m"], rel=1e-3
    )


def test_maximum_subsurface_shear(canonical_solution: HertzLineContactSolution) -> None:
    """τ_max ≈ 0.30 × p_0; eq. 4.49 Johnson."""
    assert canonical_solution.maximum_subsurface_shear_pa == pytest.approx(
        CANONICAL_EXPECTED["maximum_subsurface_shear_pa"], rel=1e-3
    )


def test_load_scaling_b_proportional_sqrt_F() -> None:
    """For Hertz line contact, b ∝ sqrt(F). Pinning the scaling
    invariant guards against a hidden formula-rewrite that would
    change the validation-regime semantics."""
    inputs_2x = HertzLineContactInputs(
        total_load_n=2000.0,
        cylinder_radius_m=0.010,
        cylinder_length_m=0.020,
        youngs_modulus_pa=210e9,
        poisson_ratio=0.30,
    )
    sol_1x = hertz_line_contact(CANONICAL_INPUTS)
    sol_2x = hertz_line_contact(inputs_2x)
    ratio = sol_2x.contact_half_width_m / sol_1x.contact_half_width_m
    assert ratio == pytest.approx(math.sqrt(2.0), rel=1e-6)


def test_load_scaling_p0_proportional_sqrt_F() -> None:
    """p_0 = 2 F' / (π b). With b ∝ √F and F' ∝ F, p_0 ∝ √F."""
    inputs_4x = HertzLineContactInputs(
        total_load_n=4000.0,
        cylinder_radius_m=0.010,
        cylinder_length_m=0.020,
        youngs_modulus_pa=210e9,
        poisson_ratio=0.30,
    )
    sol_1x = hertz_line_contact(CANONICAL_INPUTS)
    sol_4x = hertz_line_contact(inputs_4x)
    ratio = sol_4x.peak_contact_pressure_pa / sol_1x.peak_contact_pressure_pa
    assert ratio == pytest.approx(2.0, rel=1e-6)


def test_radius_scaling_b_proportional_sqrt_R() -> None:
    """b ∝ √R from eq. 4.42."""
    inputs_2x_r = HertzLineContactInputs(
        total_load_n=1000.0,
        cylinder_radius_m=0.020,
        cylinder_length_m=0.020,
        youngs_modulus_pa=210e9,
        poisson_ratio=0.30,
    )
    sol_1x = hertz_line_contact(CANONICAL_INPUTS)
    sol_2x_r = hertz_line_contact(inputs_2x_r)
    ratio = sol_2x_r.contact_half_width_m / sol_1x.contact_half_width_m
    assert ratio == pytest.approx(math.sqrt(2.0), rel=1e-6)


# ─── Input-validation guards ──────────────────────────────────────


def test_rejects_negative_load() -> None:
    with pytest.raises(ValueError, match="total_load_n must be positive"):
        hertz_line_contact(
            HertzLineContactInputs(
                total_load_n=-100.0,
                cylinder_radius_m=0.010,
                cylinder_length_m=0.020,
                youngs_modulus_pa=210e9,
                poisson_ratio=0.30,
            )
        )


def test_rejects_zero_load() -> None:
    with pytest.raises(ValueError, match="total_load_n must be positive"):
        hertz_line_contact(
            HertzLineContactInputs(
                total_load_n=0.0,
                cylinder_radius_m=0.010,
                cylinder_length_m=0.020,
                youngs_modulus_pa=210e9,
                poisson_ratio=0.30,
            )
        )


def test_rejects_non_positive_radius() -> None:
    with pytest.raises(ValueError, match="cylinder_radius_m must be positive"):
        hertz_line_contact(
            HertzLineContactInputs(
                total_load_n=1000.0,
                cylinder_radius_m=0.0,
                cylinder_length_m=0.020,
                youngs_modulus_pa=210e9,
                poisson_ratio=0.30,
            )
        )


def test_rejects_poisson_ratio_at_05() -> None:
    """ν = 0.5 (incompressible limit) breaks E* = E/(2(1-ν²))."""
    with pytest.raises(ValueError, match="poisson_ratio must be in"):
        hertz_line_contact(
            HertzLineContactInputs(
                total_load_n=1000.0,
                cylinder_radius_m=0.010,
                cylinder_length_m=0.020,
                youngs_modulus_pa=210e9,
                poisson_ratio=0.5,
            )
        )


def test_rejects_negative_poisson_ratio() -> None:
    with pytest.raises(ValueError, match="poisson_ratio must be in"):
        hertz_line_contact(
            HertzLineContactInputs(
                total_load_n=1000.0,
                cylinder_radius_m=0.010,
                cylinder_length_m=0.020,
                youngs_modulus_pa=210e9,
                poisson_ratio=-0.1,
            )
        )


# ─── residual_pct helper ──────────────────────────────────────────


def test_residual_pct_signed_positive() -> None:
    """observed > analytical → positive residual."""
    assert residual_pct(observed=110.0, analytical=100.0) == pytest.approx(10.0)


def test_residual_pct_signed_negative() -> None:
    """observed < analytical → negative residual."""
    assert residual_pct(observed=90.0, analytical=100.0) == pytest.approx(-10.0)


def test_residual_pct_zero_when_match() -> None:
    """exact match → 0% residual."""
    assert residual_pct(observed=100.0, analytical=100.0) == pytest.approx(0.0)


def test_residual_pct_infinity_when_analytical_zero() -> None:
    """analytical=0 returns +inf (caller's bug to surface)."""
    assert residual_pct(observed=1.0, analytical=0.0) == float("inf")
