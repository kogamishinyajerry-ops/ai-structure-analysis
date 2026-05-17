"""Cantilever beam tip-deflection analytical solution — Phase 20 B.

Euler-Bernoulli theory for a slender cantilever with a transverse point
load at the free tip:

    δ_tip = P · L³ / (3 · E · I)

where:
    P = transverse load applied at the free tip (N, positive in the
        load direction)
    L = beam length, root to tip (m)
    E = Young's modulus (Pa)
    I = second moment of area about the bending neutral axis (m⁴)

**Validity envelope (slender-beam assumption):**
* Aspect ratio L / h ≥ 10 where ``h`` is the cross-section depth. Below
  this, shear deformation contributes appreciably and the formula
  under-predicts deflection by ~5-10% (Timoshenko correction).
* Small-deflection theory: δ_tip / L ≤ 0.1. Above this, geometric
  nonlinearity changes the answer (P-δ effects).
* Linear elastic — stress everywhere below yield. Outside this the
  beam yields and δ_tip departs from PL³/3EI.

This module enforces the aspect-ratio bound at the function boundary;
the small-deflection bound is verified by the runner after ccx returns
a tip displacement.

References:
* Roark's Formulas for Stress and Strain, 8th edition, Chapter 8
  (Beams; flexure of straight bars), Table 8.1 Case 1a (cantilever,
  concentrated end load).
* Timoshenko & Gere, Mechanics of Materials, 4th ed., §5.4, eq. 5-15.
"""

from __future__ import annotations

from typing import Final

CROSS_CHECK_TOLERANCE_PCT: Final[float] = 5.0
"""Relative-error tolerance (percent) for the verdict.

A single-element-through-depth C3D8 hex model of a cantilever has an
inherent ~3-5% discretisation error against Euler-Bernoulli (per the
same single-element-discretisation argument as cylinder_hoop). 5% is
honest. Tightening to 2% requires multi-element refinement — Phase 21+
scope (Slice C's Gmsh-meshed pipeline will land that path)."""

CANTILEVER_ASPECT_RATIO_MIN: Final[float] = 10.0
"""Minimum slenderness L/h for the Euler-Bernoulli formula to hold to
~5% accuracy. Below this, Timoshenko shear correction is needed."""

SMALL_DEFLECTION_RATIO_MAX: Final[float] = 0.1
"""Upper bound on δ_tip / L beyond which geometric nonlinearity (P-δ)
makes the linear formula inadequate."""


class CantileverValidityError(ValueError):
    """Raised when the input parameters fall outside the
    Euler-Bernoulli slender-beam validity envelope. Carries a citation
    hint pointing the caller at the Timoshenko shear correction or
    nonlinear-geometry extension path."""


def compute_analytical_tip_deflection(
    *,
    length_m: float,
    youngs_modulus_pa: float,
    second_moment_m4: float,
    tip_load_n: float,
) -> float:
    """Return the analytical tip deflection of a slender cantilever.

    Args:
        length_m: beam length (root to tip) in meters (>0).
        youngs_modulus_pa: Young's modulus in pascals (>0).
        second_moment_m4: second moment of area about the bending
            neutral axis in m⁴ (>0).
        tip_load_n: transverse load at the free tip in newtons.
            Sign is preserved on return (positive load → positive
            deflection in the load direction).

    Returns:
        Tip deflection in meters; sign matches ``tip_load_n``.

    Raises:
        ValueError: if any geometric / material input is non-positive.
    """
    if length_m <= 0:
        raise ValueError(f"length_m must be positive; got {length_m}")
    if youngs_modulus_pa <= 0:
        raise ValueError(
            f"youngs_modulus_pa must be positive; got {youngs_modulus_pa}"
        )
    if second_moment_m4 <= 0:
        raise ValueError(
            f"second_moment_m4 must be positive; got {second_moment_m4}"
        )
    return (
        tip_load_n
        * (length_m ** 3)
        / (3.0 * youngs_modulus_pa * second_moment_m4)
    )


def assert_slender_beam_envelope(
    *,
    length_m: float,
    section_depth_m: float,
) -> None:
    """Verify the slender-beam (Euler-Bernoulli) aspect-ratio bound.

    Args:
        length_m: beam length (root to tip) in meters.
        section_depth_m: cross-section depth in the bending plane (the
            dimension parallel to the load).

    Raises:
        CantileverValidityError: if ``length_m / section_depth_m`` is
            below the slender-beam threshold.
    """
    if section_depth_m <= 0:
        raise ValueError(
            f"section_depth_m must be positive; got {section_depth_m}"
        )
    ratio = length_m / section_depth_m
    if ratio < CANTILEVER_ASPECT_RATIO_MIN:
        raise CantileverValidityError(
            f"L/h = {ratio:.2f} below slender-beam threshold "
            f"{CANTILEVER_ASPECT_RATIO_MIN}; Timoshenko shear "
            f"correction (Roark's eq. 8.4-1) required for short beams"
        )


__all__ = [
    "CROSS_CHECK_TOLERANCE_PCT",
    "CANTILEVER_ASPECT_RATIO_MIN",
    "SMALL_DEFLECTION_RATIO_MAX",
    "CantileverValidityError",
    "compute_analytical_tip_deflection",
    "assert_slender_beam_envelope",
]
