"""Cantilever beam first natural frequency — Phase 26 A.

Closed-form Euler-Bernoulli analytical for the natural frequencies
of a slender CLAMPED-FREE cantilever beam under transverse bending
vibration.

The eigenvalue equation cosh(βL)·cos(βL) + 1 = 0 has the roots:

    β₁·L = 1.875104    (mode 1)
    β₂·L = 4.694091    (mode 2)
    β₃·L = 7.854757    (mode 3)
    β₄·L = 10.99554    (mode 4)
    β₅·L = 14.13717    (mode 5)

The natural frequency in radians/s is

    ω_n = (β_n · L)² · √(EI / (ρ·A)) / L²

and in Hz is f_n = ω_n / (2π).

References:
* Rao, S. S. (2017). "Mechanical Vibrations", 6th ed., Pearson,
  §8.5 ("Free Vibration of a Uniform Beam"). Table 8.4 lists the
  roots (β_n·L) to 7-digit precision for clamped-free beams.
* Inman, D. J. (2014). "Engineering Vibration", 4th ed., Pearson,
  §6.4, Equation (6.62) and Table 6.1.
* Blevins, R. D. (2016). "Formulas for Dynamics, Acoustics and
  Vibration", Wiley, Table 4-1.

**Validity envelope (the runner enforces this):**

* L / max(h, w) ≥ 10 — Euler-Bernoulli slender-beam regime
  (Timoshenko shear correction < 5% on ω_1 at L/h = 10; rises
  steeply below). The runner refuses thicker beams.
* Mode 1 only at this phase. Higher modes require finer mesh and
  capture mode-shape complexity; deferred.

Tier 1 / Tier 2 engineering candidate; not signed validation; not
benchmark agreement.
"""

from __future__ import annotations

import math
from typing import Final

CANTILEVER_BETA_LX_MODES: Final[tuple[float, ...]] = (
    1.8751040687119611,  # β₁·L (mode 1)
    4.6940911329741745,  # β₂·L (mode 2)
    7.854757438237613,   # β₃·L (mode 3)
    10.995540734875467,  # β₄·L (mode 4)
    14.137168391046470,  # β₅·L (mode 5)
)
"""β_n·L roots of cosh(βL)·cos(βL) + 1 = 0, 16-digit precision.
Computed via Newton iteration on the characteristic equation."""

CANTILEVER_SLENDER_RATIO_MIN: Final[float] = 10.0
"""Lower bound on L / max(h, w) for the Euler-Bernoulli regime."""

CANTILEVER_MODAL_CROSS_CHECK_TOLERANCE_PCT: Final[float] = 12.0
"""Phase 26 A verdict tolerance. The honest envelope decomposes as:
* Euler-Bernoulli-vs-3D-solid (transverse shear ignored by
  analytical): ~3-5% on ω_1 for L/h = 10-20 (Timoshenko correction
  rises as 1/(L/h)²).
* C3D10 mesh-discretization of slender beam (gmsh coarseness):
  ~3-6% with the default characteristic length.
* Numerical extrapolation gmsh → ccx → eig parser: ~1-2%.
Total honest envelope: ~10-12%. 12% gives a small margin without
verdict-padding."""


class CantileverModalValidityError(ValueError):
    """Raised when input parameters fall outside the Euler-Bernoulli
    slender-beam regime."""


def compute_cantilever_first_natural_frequency_hz(
    *,
    length_m: float,
    height_m: float,
    width_m: float,
    youngs_modulus_pa: float,
    density_kg_m3: float,
    mode_index: int = 1,
) -> float:
    """Return the n-th natural frequency in Hz of a slender clamped-
    free cantilever beam with rectangular cross-section.

    Args:
        length_m: beam length L in meters (>0).
        height_m: cross-section height h (vibration direction) in m.
        width_m: cross-section width w (transverse to vibration) in m.
        youngs_modulus_pa: E in pascals (>0).
        density_kg_m3: ρ in kg/m³ (>0).
        mode_index: 1-based mode (1..5).

    Returns:
        f_n in Hz.

    Raises:
        ValueError: on non-physical inputs.
        CantileverModalValidityError: if L/max(h,w) < 10.
    """
    if length_m <= 0:
        raise ValueError(f"length_m must be positive; got {length_m}")
    if height_m <= 0:
        raise ValueError(f"height_m must be positive; got {height_m}")
    if width_m <= 0:
        raise ValueError(f"width_m must be positive; got {width_m}")
    if youngs_modulus_pa <= 0:
        raise ValueError(
            f"youngs_modulus_pa must be positive; got {youngs_modulus_pa}"
        )
    if density_kg_m3 <= 0:
        raise ValueError(
            f"density_kg_m3 must be positive; got {density_kg_m3}"
        )
    if not (1 <= mode_index <= len(CANTILEVER_BETA_LX_MODES)):
        raise ValueError(
            f"mode_index must be in [1, {len(CANTILEVER_BETA_LX_MODES)}]; "
            f"got {mode_index}"
        )
    slender_ratio = length_m / max(height_m, width_m)
    if slender_ratio < CANTILEVER_SLENDER_RATIO_MIN:
        raise CantileverModalValidityError(
            f"L/max(h,w) = {slender_ratio:.2f} below the Euler-Bernoulli "
            f"slender-beam lower bound {CANTILEVER_SLENDER_RATIO_MIN}; "
            f"Timoshenko shear correction becomes large for stubby beams"
        )

    # Cross-section properties for rectangular section vibrating in the
    # `height` direction: I = w·h³/12, A = w·h.
    second_moment_i = width_m * height_m**3 / 12.0
    area_a = width_m * height_m

    beta_l = CANTILEVER_BETA_LX_MODES[mode_index - 1]
    # ω_n = (β·L)² · √(EI / (ρA)) / L²
    omega_n = (beta_l**2) * math.sqrt(
        youngs_modulus_pa * second_moment_i / (density_kg_m3 * area_a)
    ) / (length_m**2)
    return omega_n / (2.0 * math.pi)


__all__ = [
    "CANTILEVER_BETA_LX_MODES",
    "CANTILEVER_MODAL_CROSS_CHECK_TOLERANCE_PCT",
    "CANTILEVER_SLENDER_RATIO_MIN",
    "CantileverModalValidityError",
    "compute_cantilever_first_natural_frequency_hz",
]
