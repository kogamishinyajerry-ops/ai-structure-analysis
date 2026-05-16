"""Tier 1 candidate cross-snapshot drift attribution (FM-04a Phase 15 C).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Surfaces per-axis percentage deltas between consecutive trust-score
timeline points. Given a pair (prev_axes, curr_axes) in WEIGHTED points
(0..axis_weight), returns:

* ``per_axis_delta_pct`` — for each of the 4 trust axes, the change
  expressed as a PERCENTAGE OF THE AXIS WEIGHT
  (e.g. energy_audit 15->0 is delta_pct = -100.0).
* ``dominant_axis`` — the axis with the largest absolute delta_pct,
  but ONLY if that absolute delta STRICTLY EXCEEDS the
  ``DRIFT_DOMINANT_AXIS_DELTA_FLOOR_PCT`` SSOT floor (5.0 by default).
  At or below the floor a uniform drift is NOT axis-attributed and
  ``dominant_axis`` is ``None``.
* ``dominant_delta_pct`` — the signed delta_pct of the dominant axis
  (NaN when ``dominant_axis`` is None).

What this is NOT:
* This is NOT a regression root-cause analysis. A delta on one axis
  surfaces WHICH bucket of evidence regressed, not WHY.
* This is NOT a benchmark agreement signal. Tier 1 candidate drift
  attribution flags candidate evidence changes, not validated physics
  shifts.
* The SSOT floor (5.0%) is the boundary between "uniform drift" (all
  axes moved together by a few percent) and "axis-attributed
  regression" (one axis collapsed while others stayed). Bumping the
  floor requires a methodology doc bump-history entry.

Forbidden wording (per ADR-023 + ADR-024 lite): no ``benchmark
agreement``, no ``signed validation``, no ``perforation completed``,
no ``bullet-through-steel complete``, no ``validated physics``,
no ``production ready``, no ``certified``, no ``approved for service``,
no ``asme compliant``, no ``signed off``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping

from .trust_score import (
    COMPLETENESS_WEIGHT,
    CONVERGENCE_WEIGHT,
    ENERGY_AUDIT_WEIGHT,
    REPRODUCIBILITY_WEIGHT,
)

# -- SSOT constants -------------------------------------------------------

DRIFT_DOMINANT_AXIS_DELTA_FLOOR_PCT: float = 5.0
"""Absolute percentage floor that a per-axis delta must STRICTLY
EXCEED to count as a dominant axis. A delta whose absolute value is
``<= 5.0`` lands below the floor and produces
``dominant_axis = None`` (uniform drift, NOT axis-attributed).

Rationale: a 5% drift is the engineering-evidence-cleanliness floor
that separates "noise across all axes" from "one axis collapsed".
Tier 1 candidate posture; NOT a Tier 2 benchmark threshold.

Bumping this constant requires an entry in
``.planning/methodology/trust_score_drift_attribution.md``."""

# Map axis label -> max-weight constant. These are the 4 trust-score
# axes pinned by ``trust_score._ALL_WEIGHTS``; the labels match the
# WEIGHTED-field names used by ``trust_score_timeline.TimelinePoint``
# minus the ``_weighted`` suffix.
TRUST_AXIS_WEIGHTS: Mapping[str, int] = {
    "completeness": COMPLETENESS_WEIGHT,
    "convergence": CONVERGENCE_WEIGHT,
    "energy_audit": ENERGY_AUDIT_WEIGHT,
    "reproducibility": REPRODUCIBILITY_WEIGHT,
}
"""SSOT mapping from trust-score axis label to max weight. Pinned by
``test_trust_axis_weights_sum_to_one_hundred`` so a future weight
rebalance trips this test."""


# -- dataclass ------------------------------------------------------------


@dataclass(frozen=True)
class DriftAttribution:
    """Per-axis percentage deltas between two consecutive trust-score
    timeline points. ``dominant_axis`` names the axis with the largest
    absolute delta when that delta exceeds
    ``DRIFT_DOMINANT_AXIS_DELTA_FLOOR_PCT``; otherwise ``None``."""

    from_snapshot: str
    to_snapshot: str
    per_axis_delta_pct: dict[str, float]
    dominant_axis: str | None
    dominant_delta_pct: float
    """Signed delta_pct of the dominant axis; ``math.nan`` when
    ``dominant_axis`` is None. Always finite when dominant_axis is
    set."""


# -- helpers --------------------------------------------------------------


def _validate_axes(axes: Mapping[str, int], label: str) -> None:
    if not isinstance(axes, Mapping):
        raise ValueError(
            f"{label} axes must be a mapping; got {type(axes).__name__}"
        )
    for axis_label, val in axes.items():
        if axis_label not in TRUST_AXIS_WEIGHTS:
            raise ValueError(
                f"{label}: unknown trust axis label {axis_label!r}; "
                f"expected one of {sorted(TRUST_AXIS_WEIGHTS)}"
            )
        if not isinstance(val, (int, float)):
            raise ValueError(
                f"{label}: axis {axis_label!r} value must be numeric; "
                f"got {type(val).__name__}"
            )
        max_weight = TRUST_AXIS_WEIGHTS[axis_label]
        if val < 0 or val > max_weight:
            raise ValueError(
                f"{label}: axis {axis_label!r} value {val} outside "
                f"[0, {max_weight}]"
            )


def compute_drift_attribution(
    prev_axes: Mapping[str, int],
    curr_axes: Mapping[str, int],
    *,
    from_snapshot: str,
    to_snapshot: str,
    dominant_floor_pct: float = DRIFT_DOMINANT_AXIS_DELTA_FLOOR_PCT,
) -> DriftAttribution:
    """Compute the per-axis percentage delta between two trust-score
    timeline points expressed in WEIGHTED points.

    Args:
        prev_axes: mapping axis_label -> weighted points at the EARLIER
            snapshot. MUST contain every key in
            :data:`TRUST_AXIS_WEIGHTS` (no missing axes).
        curr_axes: same for the LATER snapshot.
        from_snapshot / to_snapshot: snapshot labels stamped on the
            output for traceability.
        dominant_floor_pct: override the SSOT floor (default 5.0).
            Pinned by tests.

    Raises:
        ValueError: when an axis key is unknown, when a value is
            outside the valid [0, axis_weight] band, when an axis is
            missing from either input, or when
            ``dominant_floor_pct`` is non-positive.
    """
    if dominant_floor_pct <= 0.0:
        raise ValueError(
            f"dominant_floor_pct must be > 0; got {dominant_floor_pct}"
        )
    _validate_axes(prev_axes, "prev")
    _validate_axes(curr_axes, "curr")
    expected = set(TRUST_AXIS_WEIGHTS)
    missing_prev = expected - set(prev_axes)
    missing_curr = expected - set(curr_axes)
    if missing_prev:
        raise ValueError(
            f"prev axes missing required keys: {sorted(missing_prev)}"
        )
    if missing_curr:
        raise ValueError(
            f"curr axes missing required keys: {sorted(missing_curr)}"
        )

    per_axis_delta_pct: dict[str, float] = {}
    for axis_label, max_weight in TRUST_AXIS_WEIGHTS.items():
        delta_weighted = float(curr_axes[axis_label]) - float(
            prev_axes[axis_label]
        )
        per_axis_delta_pct[axis_label] = (
            100.0 * delta_weighted / max_weight
        )

    # Dominant axis = axis with largest absolute delta_pct, IF that
    # absolute delta exceeds the floor.
    dominant_axis: str | None = None
    dominant_delta: float = math.nan
    max_abs = 0.0
    for axis_label, delta_pct in per_axis_delta_pct.items():
        if abs(delta_pct) > max_abs:
            max_abs = abs(delta_pct)
            dominant_axis = axis_label
            dominant_delta = delta_pct
    if max_abs <= dominant_floor_pct:
        dominant_axis = None
        dominant_delta = math.nan

    return DriftAttribution(
        from_snapshot=from_snapshot,
        to_snapshot=to_snapshot,
        per_axis_delta_pct=per_axis_delta_pct,
        dominant_axis=dominant_axis,
        dominant_delta_pct=dominant_delta,
    )


def render_drift_attribution_dict(att: DriftAttribution) -> dict:
    """Render a DriftAttribution for JSON serialization inside the
    trust-score-alerts + trust-score-timeline envelopes. The
    ``dominant_delta_pct`` is rendered as ``null`` when NaN so the
    JSON shape stays well-formed."""
    return {
        "from_snapshot": att.from_snapshot,
        "to_snapshot": att.to_snapshot,
        "per_axis_delta_pct": dict(att.per_axis_delta_pct),
        "dominant_axis": att.dominant_axis,
        "dominant_delta_pct": (
            None
            if math.isnan(att.dominant_delta_pct)
            else att.dominant_delta_pct
        ),
    }
