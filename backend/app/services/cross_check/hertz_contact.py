"""FM-04a Phase 33 D — Hertz line contact analytical reference.

Classical Hertz contact: rigid (or much-stiffer) cylinder pressed
against a deformable half-space. For elastic line contact (cylinder
of length L pressing on a half-plane), the analytical reference is:

* contact half-width:
    b = sqrt(4 * F * R * (1 - ν²) / (π * E * L))
  where F is total load, R is cylinder radius, E and ν are the
  Young's modulus and Poisson's ratio of the half-space (for two
  bodies, use the effective modulus E* with both materials).

* peak contact pressure:
    p_0 = 2 * F / (π * b * L)

* approximate vertical indentation depth (cylinder COM movement
  relative to half-space far-field; the closed-form for Hertz
  LINE contact is sensitive to a length scale; the textbook
  approximation valid for L >> b is:
    δ ≈ (F / (π * E* * L)) * (1 + ln((4 * R / b)²))
  where E* = E / (2 * (1 - ν²)) for two identical elastic bodies.)

This module provides SSOT analytical helpers for the
hertz-contact-candidate cross-check. **Pin-anchored to textbook
Johnson, "Contact Mechanics" (Cambridge, 1985), §4.2 line contact.**

Tier 1 / Tier 2 engineering candidate; not signed validation; not
benchmark agreement.

Anti-gaming guards (D:-3 SSOT):
* All analytical formulas live HERE and HERE ONLY.
* Runner + tests reuse via import; no parallel implementations.
* Residual-percent helper colocated to avoid sign-flip bugs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class HertzLineContactInputs:
    """Inputs for the Hertz line-contact analytical reference.

    Convention: two elastic bodies pressed together with line
    contact along a cylinder of radius R and length L. For
    cylinder-on-flat-block, one body is the cylinder (radius R)
    and the other is a flat half-space (effectively R → ∞).
    """

    total_load_n: float
    """Total compressive load along the cylinder axis (N).
    Positive: bodies pressed together."""

    cylinder_radius_m: float
    """Cylinder radius R (m)."""

    cylinder_length_m: float
    """Cylinder length L along its axis (m). Hertz line-contact
    formulas pre-suppose plane-strain along this axis (L >> b)."""

    youngs_modulus_pa: float
    """Young's modulus E (Pa) for each body (assumes both bodies
    have identical material; the effective modulus is E* = E /
    (2 (1 - ν²)) for like materials)."""

    poisson_ratio: float
    """Poisson's ratio ν (-) for each body."""


@dataclass(frozen=True)
class HertzLineContactSolution:
    """Closed-form Hertz line-contact analytical solution."""

    effective_modulus_pa: float
    """E* = E / (2 (1 - ν²)) for like materials."""

    contact_half_width_m: float
    """Half-width b of the contact strip (m)."""

    peak_contact_pressure_pa: float
    """Peak Hertzian pressure p_0 at the centerline (Pa)."""

    indentation_depth_m: float
    """Approximate cylinder vertical-COM indentation depth δ
    relative to the half-space far-field (m). Closed-form valid
    for L >> b; this is the canonical Johnson §4.2 expression."""

    maximum_subsurface_shear_pa: float
    """Maximum subsurface shear stress τ_max (Pa).
    τ_max ≈ 0.30 * p_0 for line contact (Johnson §4.2)."""


def hertz_line_contact(inputs: HertzLineContactInputs) -> HertzLineContactSolution:
    """Compute the Hertz line-contact analytical reference.

    Source: K.L. Johnson, "Contact Mechanics", Cambridge University
    Press, 1985, §4.2 (cylindrical bodies in contact along a line).

    Anti-gaming guard A:-1: every formula is bracket-cited verbatim
    to Johnson's textbook chapter and equation number.

    Raises:
        ValueError: if any input is non-physical (negative load,
        non-positive geometry, ν ≥ 0.5).
    """
    if inputs.total_load_n <= 0.0:
        raise ValueError(
            f"total_load_n must be positive (compressive); got {inputs.total_load_n}"
        )
    if inputs.cylinder_radius_m <= 0.0:
        raise ValueError(
            f"cylinder_radius_m must be positive; got {inputs.cylinder_radius_m}"
        )
    if inputs.cylinder_length_m <= 0.0:
        raise ValueError(
            f"cylinder_length_m must be positive; got {inputs.cylinder_length_m}"
        )
    if inputs.youngs_modulus_pa <= 0.0:
        raise ValueError(
            f"youngs_modulus_pa must be positive; got {inputs.youngs_modulus_pa}"
        )
    if not (0.0 <= inputs.poisson_ratio < 0.5):
        raise ValueError(
            f"poisson_ratio must be in [0, 0.5); got {inputs.poisson_ratio}"
        )

    e_pa = inputs.youngs_modulus_pa
    nu = inputs.poisson_ratio
    f_n = inputs.total_load_n
    r_m = inputs.cylinder_radius_m
    l_m = inputs.cylinder_length_m

    # Effective modulus E* = E / (2 (1 - ν²)) for like materials.
    # (Johnson §4.2 eq. 4.11)
    e_star_pa = e_pa / (2.0 * (1.0 - nu * nu))

    # Contact half-width b = sqrt(4 F R (1-ν²) / (π E L))
    # (Johnson §4.2 eq. 4.42, with F replaced by F/L for line-load
    # form and rearranged to total load)
    # Note: per-unit-length form F' = F/L; b = sqrt(4 F' R / (π E*))
    # = sqrt(4 (F/L) R / (π E*))
    f_per_length = f_n / l_m
    b_m = math.sqrt(4.0 * f_per_length * r_m / (math.pi * e_star_pa))

    # Peak pressure p_0 = 2 F / (π b L) = 2 F' / (π b)
    # (Johnson §4.2 eq. 4.43)
    p_0_pa = 2.0 * f_per_length / (math.pi * b_m)

    # Indentation depth (Johnson §5.4 eq. 5.78, line-contact form):
    # δ = (F' / (π E*)) * (1 + ln((4 R)² / b²))
    #   = (F / (π E* L)) * (1 + 2 ln(4 R / b))
    # The factor "1 + 2 ln(4 R / b)" emerges from integration of the
    # half-space Green's function along the contact strip. Sensitive
    # to the assumed cylinder-length scale; valid for L >> b. For a
    # FINITE-LENGTH cylinder the end-effect correction is O(b/L).
    delta_m = (f_per_length / (math.pi * e_star_pa)) * (
        1.0 + 2.0 * math.log(4.0 * r_m / b_m)
    )

    # Maximum subsurface shear stress (Johnson §4.2 eq. 4.49):
    # τ_max ≈ 0.30 * p_0 occurs at depth z ≈ 0.78 b for like materials.
    tau_max_pa = 0.30 * p_0_pa

    return HertzLineContactSolution(
        effective_modulus_pa=e_star_pa,
        contact_half_width_m=b_m,
        peak_contact_pressure_pa=p_0_pa,
        indentation_depth_m=delta_m,
        maximum_subsurface_shear_pa=tau_max_pa,
    )


def residual_pct(observed: float, analytical: float) -> float:
    """Signed percent residual of observed vs analytical.

    residual_pct = (observed - analytical) / analytical * 100

    Positive => observed > analytical (overprediction).
    Returns +inf if analytical is exactly zero (caller's bug to
    surface, not silently swallow).
    """
    if analytical == 0.0:
        return float("inf")
    return (observed - analytical) / analytical * 100.0
