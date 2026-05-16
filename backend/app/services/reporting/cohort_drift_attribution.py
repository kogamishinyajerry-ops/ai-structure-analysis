"""Tier 1 candidate cohort-scoped drift attribution (FM-04a Phase 16 B).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Aggregates the per-case :class:`DriftAttribution` (Phase 15 C SSOT)
across every ``golden_samples/*-candidate/`` cohort member, surfaces
the cohort-level dominant (axis, case) pair, and renders a
serializable summary suitable for the ``cohort-anomalies`` envelope.

What this surface answers
-------------------------

``cohort-anomalies`` already surfaces statistical outliers via per-axis
z-scores on the LATEST snapshot's weighted axis scores. A reviewer
reads "case X has z = -2.0 on energy_audit" and asks "by HOW MUCH
did the energy axis drop, expressed as a percentage of the axis
weight?". Phase 15 C answered this PER CASE on the alerts + timeline
envelopes. Phase 16 B answers the same question AT COHORT SCOPE on
the cohort-anomalies envelope:

* For every case in the cohort, compute the per-axis percentage delta
  between the cohort's latest two snapshots (consumer of the SSOT
  :func:`compute_drift_attribution`).
* Find the (case, axis) pair with the largest absolute delta_pct.
* Surface that pair as ``dominant_case_id`` + ``cohort_dominant_axis``
  + ``cohort_max_abs_delta_pct``.

What this surface does NOT do
-----------------------------

* It does NOT perform regression root-cause analysis. The dominant
  axis-case pair names WHICH bucket of evidence regressed on WHICH
  case, not WHY.
* It does NOT replace the existing z-score view on cohort-anomalies;
  both are surfaced (additive, parallel views).
* It does NOT certify a Tier 2 benchmark.

Forbidden wording (per ADR-023 + ADR-024 lite): no ``benchmark
agreement``, no ``signed validation``, no ``perforation completed``,
no ``bullet-through-steel complete``, no ``validated physics``,
no ``production ready``, no ``certified``, no ``approved for service``,
no ``asme compliant``, no ``signed off``.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

from .cohort_snapshot import SNAPSHOT_LABEL_RE, snapshots_root
from .trust_score_drift_attribution import (
    DriftAttribution,
    compute_drift_attribution,
    render_drift_attribution_dict,
)
from .trust_score_timeline import build_trust_score_timeline

# -- SSOT constants -------------------------------------------------------

COHORT_DOMINANT_AXIS_FLOOR_PCT: float = 5.0
"""Absolute percentage floor that a per-axis cohort-scoped delta MUST
STRICTLY EXCEED to count as the cohort dominant axis. Parallel to
the per-case :data:`DRIFT_DOMINANT_AXIS_DELTA_FLOOR_PCT` from
Phase 15 C; tuned independently because cohort-scale noise patterns
may differ from per-case (a future bump-down would require a
methodology bump-history entry naming the consumer needing finer-
grained cohort attribution).

Rationale: matches per-case floor at 5.0% so reviewers reading the
two surfaces side-by-side see a coherent threshold. Bumping this
constant requires an entry in
``.planning/methodology/cohort_drift_attribution.md``."""

# Cohort discovery filters mirroring ``cohort_anomalies.py``.
_CASE_DIR_SUFFIX = "-candidate"
_CANDIDATE_DIR_RE = re.compile(r"^[A-Za-z0-9_-]+-candidate$")
_SIGNED_REGISTRY_RE = re.compile(r"^GS-\d{3}$")


# -- dataclass ------------------------------------------------------------


@dataclass(frozen=True)
class CohortDriftAttribution:
    """Cohort-scoped aggregation of per-case :class:`DriftAttribution`.

    ``per_case_drift_attribution`` carries one ``(case_id, attribution)``
    tuple per cohort member with at least 2 timeline points landing on
    the cohort-wide latest snapshot pair. Cases that did not appear in
    BOTH of the latest 2 snapshots are silently skipped (the per-case
    timeline walker already enforces case-presence per snapshot).

    ``cohort_dominant_axis`` is the axis with the largest absolute
    delta_pct across ANY case in the cohort. Strictly-exceed floor:
    a cohort whose worst |delta_pct| is <= 5% lands
    ``cohort_dominant_axis = None`` (uniform-drift cohort posture).
    """

    from_snapshot: str
    to_snapshot: str
    per_case_drift_attribution: tuple[tuple[str, DriftAttribution], ...]
    cohort_dominant_axis: str | None
    cohort_max_abs_delta_pct: float
    dominant_case_id: str | None


# -- helpers --------------------------------------------------------------


def _discover_latest_snapshot_pair(repo_root: Path) -> tuple[str, str] | None:
    """Walk ``reports/snapshots/`` and return the (prev, latest) pair
    of snapshot labels (chronological, snapshot labels sort ISO-order).
    Returns ``None`` when fewer than 2 valid snapshots exist."""
    root = snapshots_root(repo_root)
    if not root.is_dir():
        return None
    labels = sorted(
        child.name
        for child in root.iterdir()
        if child.is_dir() and SNAPSHOT_LABEL_RE.fullmatch(child.name)
    )
    if len(labels) < 2:
        return None
    return labels[-2], labels[-1]


def _discover_cohort_cases(repo_root: Path) -> list[str]:
    """Walk ``golden_samples/`` and return signed-registry-filtered
    ``*-candidate`` case ids."""
    golden = (repo_root / "golden_samples").resolve()
    cases: list[str] = []
    if not golden.is_dir():
        return cases
    for case_dir in sorted(golden.iterdir(), key=lambda p: p.name):
        if not case_dir.is_dir():
            continue
        name = case_dir.name
        if not name.endswith(_CASE_DIR_SUFFIX):
            continue
        if _SIGNED_REGISTRY_RE.fullmatch(name):
            continue
        if not _CANDIDATE_DIR_RE.fullmatch(name):
            continue
        cases.append(name)
    return cases


def compute_cohort_drift_attribution(
    *,
    repo_root: Path,
    dominant_floor_pct: float = COHORT_DOMINANT_AXIS_FLOOR_PCT,
) -> CohortDriftAttribution | None:
    """Compute the cohort-scoped drift attribution across the latest
    two cohort-wide snapshot labels.

    Returns ``None`` when fewer than 2 snapshots exist in
    ``reports/snapshots/`` (no cohort-wide transition can be computed).

    Args:
        repo_root: project root (must contain ``golden_samples/`` and
            ``reports/snapshots/``).
        dominant_floor_pct: override the SSOT floor (default 5.0).
            MUST be positive.

    Raises:
        ValueError: when ``dominant_floor_pct`` is non-positive.
    """
    if dominant_floor_pct <= 0.0:
        raise ValueError(
            f"dominant_floor_pct must be > 0; got {dominant_floor_pct}"
        )

    pair = _discover_latest_snapshot_pair(repo_root)
    if pair is None:
        return None
    prev_label, curr_label = pair

    cases = _discover_cohort_cases(repo_root)
    per_case: list[tuple[str, DriftAttribution]] = []
    cohort_dominant_axis: str | None = None
    cohort_max_abs = 0.0
    dominant_case_id: str | None = None

    for case_id in cases:
        timeline = build_trust_score_timeline(case_id, repo_root)
        # Find the two timeline points matching the cohort-wide pair.
        prev_point = next(
            (p for p in timeline.points if p.snapshot_label == prev_label),
            None,
        )
        curr_point = next(
            (p for p in timeline.points if p.snapshot_label == curr_label),
            None,
        )
        if prev_point is None or curr_point is None:
            # Case absent in one of the two latest snapshots.
            continue
        att = compute_drift_attribution(
            {
                "completeness": int(prev_point.completeness_weighted),
                "convergence": int(prev_point.convergence_weighted),
                "energy_audit": int(prev_point.energy_audit_weighted),
                "reproducibility": int(prev_point.reproducibility_weighted),
            },
            {
                "completeness": int(curr_point.completeness_weighted),
                "convergence": int(curr_point.convergence_weighted),
                "energy_audit": int(curr_point.energy_audit_weighted),
                "reproducibility": int(curr_point.reproducibility_weighted),
            },
            from_snapshot=prev_label,
            to_snapshot=curr_label,
        )
        per_case.append((case_id, att))
        # Find the largest absolute delta_pct across this case's axes.
        for axis_label, delta_pct in att.per_axis_delta_pct.items():
            abs_delta = abs(delta_pct)
            if abs_delta > cohort_max_abs:
                cohort_max_abs = abs_delta
                cohort_dominant_axis = axis_label
                dominant_case_id = case_id

    # Apply the strictly-exceed floor at cohort scope.
    if cohort_max_abs <= dominant_floor_pct:
        cohort_dominant_axis = None
        dominant_case_id = None
        cohort_max_abs_emit = math.nan
    else:
        cohort_max_abs_emit = cohort_max_abs

    return CohortDriftAttribution(
        from_snapshot=prev_label,
        to_snapshot=curr_label,
        per_case_drift_attribution=tuple(per_case),
        cohort_dominant_axis=cohort_dominant_axis,
        cohort_max_abs_delta_pct=cohort_max_abs_emit,
        dominant_case_id=dominant_case_id,
    )


def render_cohort_drift_attribution_dict(
    att: CohortDriftAttribution | None,
) -> dict | None:
    """Render a CohortDriftAttribution for JSON serialization inside
    the ``cohort-anomalies`` envelope. Renders ``cohort_max_abs_delta_pct``
    as ``null`` when NaN; returns ``None`` when the attribution itself
    is None (cohort with < 2 snapshots)."""
    if att is None:
        return None
    return {
        "from_snapshot": att.from_snapshot,
        "to_snapshot": att.to_snapshot,
        "per_case_drift_attribution": [
            {"case_id": case_id, **render_drift_attribution_dict(d)}
            for case_id, d in att.per_case_drift_attribution
        ],
        "cohort_dominant_axis": att.cohort_dominant_axis,
        "cohort_max_abs_delta_pct": (
            None
            if math.isnan(att.cohort_max_abs_delta_pct)
            else att.cohort_max_abs_delta_pct
        ),
        "dominant_case_id": att.dominant_case_id,
    }
