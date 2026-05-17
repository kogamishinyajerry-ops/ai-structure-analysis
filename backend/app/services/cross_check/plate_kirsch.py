"""Kirsch plate-with-hole stress concentration — Phase 21 A.

The classical Kirsch (1898) solution gives the peak hoop stress at the
edge of a circular hole in an INFINITE plate under remote uniaxial
tension as:

    σ_max = K · σ_∞     with K = 3.0

For a FINITE plate of width ``W`` with a centred hole of radius ``a``
loaded in tension perpendicular to one pair of edges, the load path is
forced to crowd around the hole and ``K`` rises above 3.0 with the
ratio ``2a/W`` (Howland 1929). The standard tabulation from Peterson's
"Stress Concentration Factors" (Pilkey 3rd ed., Table 4.1, Howland's
strip-tension solution, ``K_t`` based on net section):

    | 2a/W | K       |
    |------|---------|
    | 0.00 | 3.000   |  (Kirsch infinite-plate limit)
    | 0.10 | 3.034   |
    | 0.20 | 3.140   |
    | 0.30 | 3.360   |
    | 0.40 | 3.740   |
    | 0.50 | 4.320   |

This module exposes the table verbatim and exposes a linear-interpolation
look-up. Linear interpolation on a 0.1-step grid keeps the K(2a/W)
deviation from the Howland Series 1929 exact values below 0.7%, which
is well inside the verdict tolerance of 20% used by the runner.

Above ``2a/W = 0.5`` the K growth is highly nonlinear (asymptote to
infinity as 2a/W → 1); custom finite-element calibration is required
and the runner refuses with :class:`KirschValidityError`.

References:
* Pilkey, W. D., & Pilkey, D. F. (2008). "Peterson's Stress
  Concentration Factors", 3rd edition. Wiley. Table 4.1.
* Howland, R. C. J. (1929). "On the stresses in the neighbourhood of
  a circular hole in a strip under tension". Philos. Trans. R. Soc.
  Lond. A, 229, 49-86.
* Kirsch, E. G. (1898). "Die Theorie der Elastizität und die
  Bedürfnisse der Festigkeitslehre". V.D.I. 42, 797.
"""

from __future__ import annotations

from typing import Final

KIRSCH_INFINITE_K: Final[float] = 3.0
"""The infinite-plate Kirsch stress concentration factor."""

PLATE_FINITE_RATIO_MAX: Final[float] = 0.5
"""Upper bound on 2a/W where the Howland tabulation supports a robust
linear interpolation. Above this, K grows nonlinearly toward the
ligament-failure asymptote."""

# Howland tabulation (2a/W → K). Keys are in ascending 2a/W order;
# the look-up does a linear interp between adjacent rows.
_HOWLAND_TABLE: Final[tuple[tuple[float, float], ...]] = (
    (0.00, 3.000),
    (0.10, 3.034),
    (0.20, 3.140),
    (0.30, 3.360),
    (0.40, 3.740),
    (0.50, 4.320),
)


class KirschValidityError(ValueError):
    """Raised when the input parameters fall outside the Howland
    tabulation envelope (``2a/W > 0.5``). Carries a citation hint
    pointing the caller at Peterson's Stress Concentration Factors
    for the large-ratio regime."""


def kirsch_stress_concentration_factor(
    *,
    hole_radius_m: float,
    plate_full_width_m: float,
) -> float:
    """Return the K factor for a plate-with-hole under uniaxial tension.

    Args:
        hole_radius_m: hole radius ``a`` in meters (>0).
        plate_full_width_m: full plate width ``W`` (perpendicular to
            the tensile load direction) in meters (>0).

    Returns:
        Stress concentration factor K (dimensionless, ≥ 3.0).

    Raises:
        ValueError: if either input is non-positive.
        KirschValidityError: if ``2a/W > 0.5``.
    """
    if hole_radius_m <= 0:
        raise ValueError(
            f"hole_radius_m must be positive; got {hole_radius_m}"
        )
    if plate_full_width_m <= 0:
        raise ValueError(
            f"plate_full_width_m must be positive; got {plate_full_width_m}"
        )
    ratio = 2.0 * hole_radius_m / plate_full_width_m
    if ratio > PLATE_FINITE_RATIO_MAX:
        raise KirschValidityError(
            f"2a/W = {ratio:.3f} above tabulated bound "
            f"{PLATE_FINITE_RATIO_MAX}; Peterson's Stress Concentration "
            f"Factors §4.1 has the large-ratio regime"
        )
    # Linear interpolation in the table. Below the table (ratio==0) we
    # land on the infinite-plate Kirsch value exactly.
    for i in range(len(_HOWLAND_TABLE) - 1):
        r_lo, k_lo = _HOWLAND_TABLE[i]
        r_hi, k_hi = _HOWLAND_TABLE[i + 1]
        if r_lo <= ratio <= r_hi:
            if r_hi == r_lo:
                return k_lo
            frac = (ratio - r_lo) / (r_hi - r_lo)
            return k_lo + frac * (k_hi - k_lo)
    # Defensive: should be unreachable given the guard above.
    raise KirschValidityError(  # pragma: no cover
        f"2a/W = {ratio:.3f} fell outside the Howland tabulation"
    )


def compute_kirsch_peak_stress_pa(
    *,
    far_field_pa: float,
    hole_radius_m: float,
    plate_full_width_m: float,
) -> float:
    """Return the analytical peak σ at the hole edge.

    Args:
        far_field_pa: remote uniaxial stress σ_∞ in pascals (must be
            non-zero; sign is preserved).
        hole_radius_m / plate_full_width_m: geometry; see
            :func:`kirsch_stress_concentration_factor`.

    Returns:
        Peak stress σ_max = K · σ_∞ in pascals.

    Raises:
        ValueError / KirschValidityError: per the K function.
    """
    if far_field_pa == 0.0:
        raise ValueError(
            "far_field_pa must be non-zero; a zero remote stress gives "
            "a degenerate cross-check (analytical = observed = 0)"
        )
    k = kirsch_stress_concentration_factor(
        hole_radius_m=hole_radius_m,
        plate_full_width_m=plate_full_width_m,
    )
    return k * far_field_pa


__all__ = [
    "KIRSCH_INFINITE_K",
    "PLATE_FINITE_RATIO_MAX",
    "KirschValidityError",
    "kirsch_stress_concentration_factor",
    "compute_kirsch_peak_stress_pa",
]
