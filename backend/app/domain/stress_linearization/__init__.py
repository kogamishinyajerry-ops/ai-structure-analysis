"""Layer-3 stress linearization through a Stress Classification Line
(SCL) — RFC-001 §6.4 + ASME VIII Div 2 §5.5.

Pressure-vessel local-stress assessment requires decomposing the
stress-tensor field along an SCL (a line through the wall thickness)
into three components:

  * **Membrane** (σ_m): through-thickness *average* of the stress
    tensor. The "uniform" part of the load.
  * **Bending** (σ_b): linearly-varying-through-thickness component,
    fitted by least-squares to the tensor field. Reported here as the
    bending tensor *at the outer surface* (s = t); the inner-surface
    bending tensor is its negative (σ_b varies linearly through
    thickness with zero at the midplane).
  * **Peak** (σ_F): residual at each input SCL point after subtracting
    membrane and bending — the part of the field that cannot be
    captured by a linear-in-s decomposition.

ASME VIII Div 2 §5.5.3 then forms the categorised stresses:

  * P_m         = von_mises(σ_m)
  * P_m + P_b   = von_mises(σ_m + σ_b_outer)   — at the outer surface
                  von_mises(σ_m - σ_b_outer)   — at the inner surface
                  (caller takes the larger.)
  * P_m + P_b + Q  ≈ von_mises(σ(s))            — pointwise; the max
                  over s is the worst-case primary+secondary stress.

This module is *Layer 3*: it only touches numpy. Layer-2 readers
deliver the SCL tensors (e.g. by extracting STRESS_TENSOR values at
nodes the engineer has identified as on the SCL); Layer-4 producers
decide which categorised stress to report and how to label it.

What this module does NOT do:
  * SCL line specification or interpolation across elements. The
    caller passes the (already-extracted) tensor field.
  * Stress allowable lookup (S_m, S_mt). That's RFC §6.4 W4+ when
    standards-citation lookup lands.
  * F (peak) categorisation. The "peak" returned here is the raw
    residual; ASME's F category is what's left after removing both
    Q AND the linear σ_m+σ_b. Domain-experts can build the further
    split atop this module.

Component convention: tensors are `[σ_xx, σ_yy, σ_zz, σ_xy, σ_yz,
σ_xz]` — the same 6-component layout used elsewhere in
:mod:`app.domain.stress_derivatives` and the reader contract.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt


__all__ = ["LinearizedStress", "linearize_through_thickness"]


@dataclass(frozen=True)
class LinearizedStress:
    """Membrane / bending / peak decomposition along a single SCL.

    ``membrane`` (shape ``(6,)``) is the through-thickness-averaged
    stress tensor.

    ``bending`` (shape ``(6,)``) is the bending tensor evaluated at
    the *outer* surface (s = t). Reconstruct the bending tensor at
    any other point: ``σ_b(s) = bending * (2*(s - s_mid) / t)`` where
    ``s_mid = (s_inner + s_outer) / 2``. At the inner surface this is
    ``-bending``.

    ``peak`` (shape ``(N, 6)``) is the per-SCL-point residual after
    subtracting membrane and bending. For a pure linear-in-s field,
    ``peak`` is identically zero.
    """

    membrane: npt.NDArray[np.float64]
    bending: npt.NDArray[np.float64]
    peak: npt.NDArray[np.float64]


def linearize_through_thickness(
    tensors: npt.NDArray[np.float64],
    distances: npt.NDArray[np.float64],
) -> LinearizedStress:
    """Decompose a stress-tensor field along an SCL into membrane /
    bending / peak per ASME VIII Div 2 §5.5.3.

    Parameters
    ----------
    tensors:
        Shape ``(N, 6)``. Stress tensor at each SCL sample point.
        Component order is ``[σ_xx, σ_yy, σ_zz, σ_xy, σ_yz, σ_xz]``.
    distances:
        Shape ``(N,)``. Strictly-monotonically-increasing position
        along the SCL — typically distance from the inner surface.
        Need not start at zero.

    Returns
    -------
    LinearizedStress

    Raises
    ------
    ValueError
        On shape mismatch, fewer than 2 SCL points, or non-strictly-
        monotonic distances.

    Notes
    -----
    The decomposition is a discrete weighted least-squares projection
    of the input tensor field onto the basis ``{1, (s - s_mid)}``,
    using trapezoidal weights consistent with the SCL parametrisation
    ``s``. This makes recovery *exact* for any linear-in-s input
    regardless of sampling — pure-membrane inputs yield
    ``bending == 0`` and ``peak == 0``, pure-linear-bending inputs
    yield ``membrane == 0`` and ``peak == 0``. Quadratic and higher-
    order fields incur the standard O(h²) discretisation error in
    the membrane average; the linear-fit recovery for the bending
    coefficient remains exact under the discrete inner product the
    weights define (so a pure-quadratic input still yields
    ``bending == 0`` by parity, with the parabola-vs-mean residual
    showing up cleanly in ``peak``).
    """
    if tensors.ndim != 2 or tensors.shape[1] != 6:
        raise ValueError(
            f"tensors must be shape (N, 6); got {tensors.shape}"
        )
    if distances.ndim != 1 or distances.shape[0] != tensors.shape[0]:
        raise ValueError(
            "distances must be shape (N,) and match tensors along axis 0; "
            f"got distances shape {distances.shape} vs "
            f"tensors.shape[0]={tensors.shape[0]}"
        )
    n = tensors.shape[0]
    if n < 2:
        raise ValueError(
            f"linearization requires at least 2 SCL points; got {n}"
        )

    if np.any(np.diff(distances) <= 0):
        raise ValueError(
            "distances must be strictly monotonically increasing"
        )

    # Use float64 throughout to keep numerical error well below the
    # engineering-tolerance ladder.
    s = distances.astype(np.float64, copy=False)
    sigma = tensors.astype(np.float64, copy=False)

    s_inner = float(s[0])
    s_outer = float(s[-1])
    t = s_outer - s_inner
    s_mid = (s_inner + s_outer) / 2.0

    # Trapezoidal weights for the SCL parametrisation. Sum equals t.
    diffs = np.diff(s)
    weights = np.empty(n, dtype=np.float64)
    weights[0] = diffs[0] / 2.0
    weights[-1] = diffs[-1] / 2.0
    if n > 2:
        weights[1:-1] = (diffs[:-1] + diffs[1:]) / 2.0

    s_offset = s - s_mid  # shape (N,)

    # Membrane = weighted mean = (Σ w_i σ_i) / (Σ w_i).
    # Equivalent to trapz(σ, s) / t.
    weight_sum = float(weights.sum())  # == t
    membrane: npt.NDArray[np.float64] = (
        (weights[:, None] * sigma).sum(axis=0) / weight_sum
    ).astype(np.float64, copy=False)

    # Bending: discrete weighted-LS slope of σ against s_offset.
    # b_coeff = <σ - m, s_offset> / <s_offset, s_offset>
    # where <f, g> = Σ w_i f_i g_i.
    # bending at outer surface = b_coeff * (s_outer - s_mid) = b_coeff * t/2.
    weighted_s_sq = float((weights * s_offset**2).sum())
    sigma_centered = sigma - membrane  # shape (N, 6)
    weighted_moment = (
        weights[:, None] * s_offset[:, None] * sigma_centered
    ).sum(axis=0)
    b_coeff = weighted_moment / weighted_s_sq  # shape (6,)
    bending: npt.NDArray[np.float64] = (
        b_coeff * (t / 2.0)
    ).astype(np.float64, copy=False)

    # Peak = σ(s_i) - membrane - σ_b(s_i)
    # σ_b(s) = bending * (2 * (s - s_mid) / t) — linear from -bending
    # at s_inner to +bending at s_outer.
    s_normalised = (s_offset / (t / 2.0))[:, None]
    bending_pointwise = s_normalised * bending  # shape (N, 6)
    peak: npt.NDArray[np.float64] = (
        sigma - membrane - bending_pointwise
    ).astype(np.float64, copy=False)

    return LinearizedStress(
        membrane=membrane,
        bending=bending,
        peak=peak,
    )
