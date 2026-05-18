"""FM-04a Phase 31 A — analytical helpers for 1D steady-state heat conduction.

Closed-form reference for a rectangular bar of length L with prescribed
temperatures at the two end faces and INSULATED lateral surfaces. With
uniform isotropic conductivity k > 0 and no volumetric heat source,
the steady-state temperature distribution satisfies the Laplace
equation d²T/dx² = 0, giving the linear profile:

    T(x) = T_left + (T_right - T_left) × x / L

Crucially, the temperature distribution is INDEPENDENT of k — the
conductivity value affects only the heat flux Q = -k · dT/dx, not
the temperature field. This is why Phase 31 A's first `*HEAT
TRANSFER` cross-check uses a hardcoded k=50 W/(m·K) without
extending the material SSOT: the residual is k-invariant.

Anti-gaming guards:
* B:-1 — analytical is a SINGLE pure function with explicit
  preconditions (L > 0, valid x ∈ [0, L]); no hidden k-dependence.
* D:-3 — SSOT for the formula is THIS module; runner and tests
  reuse it verbatim. No parallel re-definition.

Tier 1 / Tier 2 engineering candidate; not signed validation;
not benchmark agreement.
"""

from __future__ import annotations


def steady_state_1d_temperature_k(
    *,
    x_m: float,
    length_m: float,
    t_left_k: float,
    t_right_k: float,
) -> float:
    """Closed-form analytical T(x) for 1D steady-state conduction
    through a bar of length `length_m` with fixed T at both ends.

    The result is in the SAME units as `t_left_k` and `t_right_k`
    (kelvin if the inputs are kelvin; celsius if both inputs are
    celsius — the formula is unit-agnostic over T since it's a
    linear combination).

    Raises:
        ValueError: if length_m ≤ 0 or x_m is outside [0, length_m]
            (with a small tolerance for floating-point boundary
            evaluation).
    """
    if length_m <= 0.0:
        raise ValueError(f"length_m must be positive; got {length_m}")
    # Allow tiny negative / over-length for FE node coordinates that
    # land on the boundary with float noise.
    tol = 1e-9 * length_m
    if x_m < -tol or x_m > length_m + tol:
        raise ValueError(
            f"x_m {x_m} outside the bar [0, {length_m}] (tol {tol})"
        )
    x_clamped = min(max(x_m, 0.0), length_m)
    return t_left_k + (t_right_k - t_left_k) * x_clamped / length_m


def residual_pct(observed: float, analytical: float) -> float:
    """Signed (observed - analytical) / |analytical| × 100 with a
    guard against analytical=0 (returns the absolute difference
    times 100 as a degraded indicator)."""
    if analytical == 0.0:
        return abs(observed) * 100.0
    return (observed - analytical) / abs(analytical) * 100.0
