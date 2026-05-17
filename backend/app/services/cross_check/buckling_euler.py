"""Euler critical-load analytical — Phase 22 A.

Classical Euler buckling solution for a slender straight column under
axial compression:

    P_cr = π² · E · I / (k · L)²

where:
    E = Young's modulus (Pa)
    I = minimum second moment of area about the bending axis (m⁴)
    L = column length, end to end (m)
    k = effective-length factor depending on end-condition:

        | end condition          | k    | k² |
        |------------------------|------|----|
        | pinned-pinned          | 1.0  | 1.0 |
        | fixed-fixed            | 0.5  | 0.25 |
        | fixed-pinned           | 0.7  | 0.49 |
        | fixed-free (cantilever)| 2.0  | 4.0 |

The fixed-free P_cr is 1/4 the pinned-pinned (longer effective length
because only one end is restrained); the fixed-fixed is 4× the pinned-
pinned (both ends restrained → shorter effective length).

**Validity envelope (slender column assumption):**
* Slenderness ratio L/r ≥ ~100 where r = sqrt(I/A) is the radius of
  gyration. Below this, the column yields before buckling and the
  Euler formula over-predicts.
* Linear elastic — stress everywhere below yield.
* No initial geometric imperfections / no eccentricity in the axial
  load.

This module enforces neither bound at the function boundary — the
caller (a runner or test) is responsible for using the formula inside
its validity envelope. Following the Phase 19 B / 21 A pattern.

References:
* Roark's Formulas for Stress and Strain, 8th ed., Table 12.1
  (Euler columns).
* Timoshenko & Gere, Theory of Elastic Stability, 2nd ed., §2.2.
"""

from __future__ import annotations

import math
from typing import Final, Literal

EndCondition = Literal[
    "pinned-pinned",
    "fixed-fixed",
    "fixed-pinned",
    "fixed-free",
]

# Effective-length factor k for each canonical end condition.
EULER_K_FACTOR: Final[dict[EndCondition, float]] = {
    "pinned-pinned": 1.0,
    "fixed-fixed": 0.5,
    "fixed-pinned": 0.7,
    "fixed-free": 2.0,
}

BUCKLING_CROSS_CHECK_TOLERANCE_PCT: Final[float] = 10.0
"""Phase 22 A tolerance for the Euler vs ccx buckling-eigenvalue
cross-check. CalculiX's `*BUCKLE` step solves a generalised eigenvalue
problem on the stress-stiffness matrix; for a slender column with
linear C3D8 hex meshing the lowest eigenvalue typically lands within
5-8% of the Euler analytical at the slenderness ratios we'll test.
10% gives honest headroom for nodal extrapolation noise."""


class EulerValidityError(ValueError):
    """Raised when buckling inputs are invalid (non-positive length /
    modulus / area-moment, unknown end condition)."""


def compute_euler_critical_load(
    *,
    length_m: float,
    youngs_modulus_pa: float,
    second_moment_m4: float,
    end_condition: EndCondition,
) -> float:
    """Return the analytical Euler critical load.

    Args:
        length_m: column length (m, >0).
        youngs_modulus_pa: Young's modulus (Pa, >0).
        second_moment_m4: minimum second moment of area (m⁴, >0).
        end_condition: one of the EndCondition Literal values.

    Returns:
        Critical compressive force in newtons. Positive value; sign
        convention is "magnitude of compressive load at which the
        column buckles".

    Raises:
        EulerValidityError: on non-positive geometric inputs.
        KeyError: when end_condition isn't a recognised string.
    """
    if length_m <= 0:
        raise EulerValidityError(
            f"length_m must be positive; got {length_m}"
        )
    if youngs_modulus_pa <= 0:
        raise EulerValidityError(
            f"youngs_modulus_pa must be positive; got {youngs_modulus_pa}"
        )
    if second_moment_m4 <= 0:
        raise EulerValidityError(
            f"second_moment_m4 must be positive; got {second_moment_m4}"
        )
    if end_condition not in EULER_K_FACTOR:
        raise EulerValidityError(
            f"end_condition must be one of {sorted(EULER_K_FACTOR)}; "
            f"got {end_condition!r}"
        )
    k = EULER_K_FACTOR[end_condition]
    eff_len = k * length_m
    return (math.pi ** 2) * youngs_modulus_pa * second_moment_m4 / (eff_len ** 2)


__all__ = [
    "BUCKLING_CROSS_CHECK_TOLERANCE_PCT",
    "EULER_K_FACTOR",
    "EndCondition",
    "EulerValidityError",
    "compute_euler_critical_load",
]
