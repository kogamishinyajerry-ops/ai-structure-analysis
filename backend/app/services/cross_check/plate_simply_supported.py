"""Simply-supported rectangular plate, uniform pressure — Phase 25 A.

Closed-form analytical for the center deflection of a thin
rectangular plate, simply-supported on all four edges, loaded by a
uniform transverse pressure ``q``.

For a square plate (a = b) with Poisson's ratio ``nu = 0.3``, the
Timoshenko / Woinowsky-Krieger closed-form gives:

    w_center = α · q · a⁴ / D

with the dimensionless coefficient α = 0.00406 and the plate
flexural rigidity

    D = E · t³ / (12 · (1 - ν²))

References:
* Timoshenko, S., & Woinowsky-Krieger, S. (1959). "Theory of
  Plates and Shells", 2nd ed., McGraw-Hill. §30, "Bending of
  rectangular plates with simply supported edges", Table 8.
* Roark, R. J., & Young, W. C. (2012). "Formulas for Stress and
  Strain", 8th ed., McGraw-Hill. Table 11.4, case 1a
  (rectangular plate, simply supported, uniform load).

Both sources cite α = 0.00406 for a = b, ν = 0.3 — independent of
material (the ratio w·D / (q·a⁴) is a pure dimensionless function
of plate geometry + Poisson's ratio).

**Validity envelope (the runner enforces this):**

* a / t ≥ 20 — Kirchhoff thin-plate regime (transverse shear
  ignored). Below 20, Mindlin-Reissner correction starts mattering
  (~+5% on δ_center).
* w_center / t ≤ 0.2 — small-deflection (linear) regime. Beyond
  this, membrane stretching kicks in and the linear formula
  under-predicts.
* Square plates only at this phase. Rectangular plates require an
  α(a/b) lookup (Timoshenko Table 8) — deferred to a later phase.

Tier 1 / Tier 2 engineering candidate; not signed validation; not
benchmark agreement.
"""

from __future__ import annotations

from typing import Final

TIMOSHENKO_ALPHA_SQUARE_NU_0_3: Final[float] = 0.00406
"""Dimensionless center-deflection coefficient α for a SQUARE plate
(a = b), Poisson's ratio ν = 0.3, simply supported on all 4 edges,
uniform pressure load. From Timoshenko & Woinowsky-Krieger §30
Table 8 / Roark Table 11.4 case 1a."""

PLATE_SS_THIN_PLATE_RATIO_MIN: Final[float] = 20.0
"""Lower bound on a/t for the Kirchhoff thin-plate regime where the
α coefficient applies without Mindlin-Reissner correction."""

PLATE_SS_SMALL_DEFLECTION_RATIO_MAX: Final[float] = 0.2
"""Upper bound on w/t for the small-deflection regime where the
linear Kirchhoff formula applies (no membrane stretching)."""

PLATE_SS_CROSS_CHECK_TOLERANCE_PCT: Final[float] = 15.0
"""Phase 25 A verdict tolerance. The honest envelope decomposes as:
* Kirchhoff-vs-3D-solid (transverse shear ignored by analytical):
  ~3-5% on δ_center for a/t = 20-50.
* C3D10 mesh-discretization-of-thin-plate (gmsh coarseness on the
  through-thickness direction): ~5-8% with the default 2-3 elements
  through thickness.
* Numerical extrapolation gmsh → ccx → frd reader: ~1-2%.
Total honest envelope: ~10-15%. 15% gives a small margin without
verdict-padding."""


class PlateSimplySupportedValidityError(ValueError):
    """Raised when the input parameters fall outside the validated
    Kirchhoff thin-plate small-deflection envelope. Carries a citation
    hint to the relevant theory boundary."""


def compute_simply_supported_plate_center_deflection_m(
    *,
    side_length_m: float,
    thickness_m: float,
    youngs_modulus_pa: float,
    poisson_ratio: float,
    pressure_pa: float,
) -> float:
    """Return the analytical center deflection of a square simply-
    supported plate under uniform pressure.

    Args:
        side_length_m: a (= b) in meters (>0).
        thickness_m: t in meters (>0).
        youngs_modulus_pa: E in pascals (>0).
        poisson_ratio: ν (0 ≤ ν < 0.5).
        pressure_pa: q in pascals (any sign; magnitude used for
            deflection magnitude — sign is preserved in the returned
            value following the load convention).

    Returns:
        w_center in meters. Sign matches the load direction.

    Raises:
        ValueError: if any non-physical input (non-positive geometry,
            non-positive E, ν out of [0, 0.5)).
        PlateSimplySupportedValidityError: if a/t < 20 (outside
            Kirchhoff thin-plate envelope) — the small-deflection
            ratio (w/t) cannot be checked from inputs alone; the
            runner does that against the simulated deflection.
    """
    if side_length_m <= 0:
        raise ValueError(
            f"side_length_m must be positive; got {side_length_m}"
        )
    if thickness_m <= 0:
        raise ValueError(
            f"thickness_m must be positive; got {thickness_m}"
        )
    if youngs_modulus_pa <= 0:
        raise ValueError(
            f"youngs_modulus_pa must be positive; got {youngs_modulus_pa}"
        )
    if not (0.0 <= poisson_ratio < 0.5):
        raise ValueError(
            f"poisson_ratio must be in [0, 0.5); got {poisson_ratio}"
        )
    aspect_ratio = side_length_m / thickness_m
    if aspect_ratio < PLATE_SS_THIN_PLATE_RATIO_MIN:
        raise PlateSimplySupportedValidityError(
            f"a/t = {aspect_ratio:.2f} below the Kirchhoff thin-plate "
            f"lower bound {PLATE_SS_THIN_PLATE_RATIO_MIN}; "
            f"Mindlin-Reissner correction needed for thicker plates "
            f"(Timoshenko & Woinowsky-Krieger §61)"
        )

    flex_rigidity_d = (
        youngs_modulus_pa * thickness_m**3
        / (12.0 * (1.0 - poisson_ratio**2))
    )
    return (
        TIMOSHENKO_ALPHA_SQUARE_NU_0_3
        * pressure_pa
        * side_length_m**4
        / flex_rigidity_d
    )


def plate_flexural_rigidity_d_n_m(
    *,
    youngs_modulus_pa: float,
    thickness_m: float,
    poisson_ratio: float,
) -> float:
    """Plate flexural rigidity D = E·t³ / (12·(1-ν²)) in N·m."""
    if youngs_modulus_pa <= 0:
        raise ValueError(
            f"youngs_modulus_pa must be positive; got {youngs_modulus_pa}"
        )
    if thickness_m <= 0:
        raise ValueError(
            f"thickness_m must be positive; got {thickness_m}"
        )
    if not (0.0 <= poisson_ratio < 0.5):
        raise ValueError(
            f"poisson_ratio must be in [0, 0.5); got {poisson_ratio}"
        )
    return (
        youngs_modulus_pa * thickness_m**3
        / (12.0 * (1.0 - poisson_ratio**2))
    )


__all__ = [
    "PLATE_SS_CROSS_CHECK_TOLERANCE_PCT",
    "PLATE_SS_SMALL_DEFLECTION_RATIO_MAX",
    "PLATE_SS_THIN_PLATE_RATIO_MIN",
    "PlateSimplySupportedValidityError",
    "TIMOSHENKO_ALPHA_SQUARE_NU_0_3",
    "compute_simply_supported_plate_center_deflection_m",
    "plate_flexural_rigidity_d_n_m",
]
