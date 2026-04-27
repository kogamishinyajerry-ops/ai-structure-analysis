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
from typing import Any

import numpy as np
import numpy.typing as npt


__all__ = [
    "LinearizedStress",
    "linearize_through_thickness",
    "resample_to_uniform",
]


@dataclass(frozen=True)
class LinearizedStress:
    """Membrane / bending / peak decomposition along a single SCL.

    ``membrane`` (shape ``(6,)``) is the through-thickness-averaged
    stress tensor.

    ``bending_outer`` (shape ``(6,)``) is the bending tensor at the
    *outer* surface (``s = s[-1]``). The bending tensor at any other
    point is ``bending_outer * (2*(s - s_mid) / t)`` where
    ``s_mid = (s_inner + s_outer) / 2``. At the inner surface this is
    ``-bending_outer`` — i.e. ``σ_inner = membrane - bending_outer``,
    ``σ_outer = membrane + bending_outer``. The explicit ``_outer``
    suffix is intentional: callers writing ``membrane + bending`` for
    the inner face is the foot-gun that motivated the rename
    (Codex R1 MEDIUM).

    ``peak`` (shape ``(N, 6)``) is the per-SCL-point residual after
    subtracting membrane and the linear bending term. For a pure
    linear-in-s field, ``peak`` is identically zero.
    """

    membrane: npt.NDArray[np.float64]
    bending_outer: npt.NDArray[np.float64]
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
    ``s``. Linear-in-s recovery is exact for any monotone spacing.

    Spacing must be **uniform** (equal Δs between consecutive points).
    On non-uniform grids the weighted antisymmetric integrand
    ``Σ w_i (s_i - s_mid)³`` no longer vanishes, and an even-symmetric
    field (e.g. pure peak ``σ ∝ (s - s_mid)²``) leaks a non-zero
    bending coefficient — Codex R1 HIGH demonstrated this with
    ``s = [0, 0.1, 0.4, 1.0, 1.6, 2.0]`` and σ = (s - s_mid)² yielding
    ``bending_outer ≈ 0.02`` instead of zero, which would silently
    inflate the reported P_b. Engineers extracting SCL data from
    irregular meshes must resample onto a uniform grid before calling
    this function (RFC-002 candidate: a Layer-3 resampler helper).

    For uniform spacing, pure-membrane inputs yield
    ``bending_outer == 0`` and ``peak == 0`` exactly; pure-linear
    bending yields ``membrane == 0`` and ``peak == 0`` exactly;
    pure-quadratic peak yields ``bending_outer == 0`` exactly by
    parity, with the parabola-vs-mean residual cleanly in ``peak``
    (and an O(h²) error in the membrane average).
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

    diffs = np.diff(distances.astype(np.float64, copy=False))
    if np.any(diffs <= 0):
        raise ValueError(
            "distances must be strictly monotonically increasing"
        )
    if n > 2:
        # Reject non-uniform spacing. Use a relative tolerance against
        # the median spacing so float-precision wobble doesn't trip a
        # strict-equality check. ``rtol=1e-6`` accommodates float32
        # quantization (~1e-7 relative error) while still catching
        # real non-uniformity at the ≥0.0001% level — well below the
        # threshold at which the antisymmetric-integrand leak
        # (Codex R1 HIGH) becomes engineering-significant. Codex R3
        # numeric probe: an at-edge-of-band grid produces
        # bending_outer ≈ 4e-8 for a unit-magnitude quadratic field,
        # which scales to ~4e-5 even at 1000-unit stress.
        ref = float(np.median(diffs))
        if not np.allclose(diffs, ref, rtol=1e-6, atol=0.0):
            raise ValueError(
                "linearize_through_thickness requires uniformly-spaced "
                f"SCL points; got diffs min/max = "
                f"{float(diffs.min())!r} / {float(diffs.max())!r}. "
                "Resample onto a uniform grid (e.g. via numpy.interp) "
                "before calling — non-uniform spacing biases the "
                "bending coefficient on even-symmetric fields."
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
    bending_outer: npt.NDArray[np.float64] = (
        b_coeff * (t / 2.0)
    ).astype(np.float64, copy=False)

    # Peak = σ(s_i) - membrane - σ_b(s_i)
    # σ_b(s) = bending_outer * (2 * (s - s_mid) / t) — linear from
    # -bending_outer at s_inner to +bending_outer at s_outer.
    s_normalised = (s_offset / (t / 2.0))[:, None]
    bending_pointwise = s_normalised * bending_outer  # shape (N, 6)
    peak: npt.NDArray[np.float64] = (
        sigma - membrane - bending_pointwise
    ).astype(np.float64, copy=False)

    return LinearizedStress(
        membrane=membrane,
        bending_outer=bending_outer,
        peak=peak,
    )


def resample_to_uniform(
    tensors: npt.NDArray[Any],
    distances: npt.NDArray[Any],
    *,
    n_points: int = 21,
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """Linear-interpolate a per-component stress-tensor SCL field onto
    a uniform grid spanning ``[distances[0], distances[-1]]``.

    Engineers extracting SCL data from CalculiX (or any other FE
    solver) routinely get *non-uniform* node spacing because the mesh
    refines toward stress concentrators. :func:`linearize_through_thickness`
    rejects non-uniform inputs (the antisymmetric integrand
    ``Σ w_i (s_i - s_mid)³`` no longer vanishes, leaking spurious
    bending into pure-peak fields — Codex R1 HIGH on PR #76). This
    helper resamples a non-uniform input onto a uniform grid so the
    linearizer's contract is satisfied.

    Parameters
    ----------
    tensors
        Shape ``(N, 6)``. The 6 stress-tensor components in
        ``[σ_xx, σ_yy, σ_zz, σ_xy, σ_yz, σ_xz]`` order.
    distances
        Shape ``(N,)``. Strictly monotonically increasing distance
        along the SCL. Need not start at zero.
    n_points
        Number of uniformly-spaced output points. Default ``21`` is
        a project convention — enough density for through-thickness
        peak resolution under ASME §5.5.3 reads, and odd so the
        centre sample sits exactly at ``s_mid`` (useful when
        engineers manually inspect the resampled field). Even values
        are accepted; the linearizer handles them identically. Must
        be ≥ 2.

    Returns
    -------
    (tensors_resampled, distances_resampled)
        ``tensors_resampled`` shape ``(n_points, 6)`` is the linearly-
        interpolated tensor field; ``distances_resampled`` shape
        ``(n_points,)`` is ``np.linspace(distances[0], distances[-1],
        n_points)``.

    Raises
    ------
    ValueError
        On shape mismatch, fewer than 2 input points, non-strictly-
        monotonic input distances, or ``n_points < 2``.

    Notes
    -----
    The interpolation is per-component linear (``np.interp``) — the
    simplest possible scheme. Higher-order spline / Hermite
    reconstruction is intentionally NOT offered: ASME stress
    classification is a *macro-scale* read of the through-thickness
    field, and any smoothing scheme richer than linear lets you
    accidentally invent peak that wasn't in the source data.

    Linear-interp recovery preserves:
      * the input value at every output point that coincides with an
        input point (exact match)
      * monotonicity in the floating-point sense: a non-decreasing
        component stays non-decreasing (a *strictly* increasing
        component may flatten into FP plateaus when adjacent input
        points sit very close to one another, but never reverses)
      * a globally-linear input field, *to float64 precision* — for
        slopes that aren't representable exactly in binary (1/3, π,
        very large coefficients, etc.) the residual stays at
        machine-epsilon relative scale, not bit-exact

    It does NOT preserve through-thickness average (the resampled
    membrane will differ from the source membrane by O(h²) wherever
    the field has non-zero curvature). For ASME §5.5.3 P_m the
    practical effect is below engineering tolerance once ``n_points``
    is in the typical 11-41 range.

    Engineers using this helper should:
      1. Resample once with ``n_points`` chosen for the desired
         through-thickness resolution.
      2. Pass the resampled outputs to
         :func:`linearize_through_thickness` for the M/B/Q decomposition.

    Example
    -------
    >>> import numpy as np
    >>> # Non-uniform CalculiX nodes along the SCL.
    >>> s_raw = np.array([0.0, 0.1, 0.4, 1.0, 1.6, 2.0])
    >>> sigma_raw = np.zeros((6, 6))
    >>> sigma_raw[:, 0] = 50.0 + 30.0 * (s_raw - 1.0)  # linear bending
    >>> sigma, s = resample_to_uniform(sigma_raw, s_raw, n_points=21)
    >>> result = linearize_through_thickness(sigma, s)
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
            f"resampling requires at least 2 SCL points; got {n}"
        )
    if n_points < 2:
        raise ValueError(
            f"n_points must be >= 2; got {n_points}"
        )

    s_in = distances.astype(np.float64, copy=False)
    diffs = np.diff(s_in)
    if np.any(diffs <= 0):
        raise ValueError(
            "distances must be strictly monotonically increasing"
        )

    s_out = np.linspace(s_in[0], s_in[-1], n_points, dtype=np.float64)
    sigma_in = tensors.astype(np.float64, copy=False)
    sigma_out = np.empty((n_points, 6), dtype=np.float64)
    for k in range(6):
        sigma_out[:, k] = np.interp(s_out, s_in, sigma_in[:, k])

    return sigma_out, s_out
