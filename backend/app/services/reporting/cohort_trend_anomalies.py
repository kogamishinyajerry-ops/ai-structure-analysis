"""Tier 1 candidate cohort trend-slope anomalies (FM-04a Phase 9 D).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

For each ``*-candidate`` case, walk its trust-score timeline (which
the Phase 6 D service already builds from frozen snapshot bytes),
compute a least-squares slope per axis (treating point index
``0..N-1`` as the x-axis), and flag any axis whose slope is more
negative than the named thresholds.

Slope semantics: ``slope`` is in units of *weighted axis points per
snapshot*. So a slope of ``-1.5`` on the completeness axis means the
case's weighted completeness contribution drops by 1.5 points per
snapshot, on average. This is **orthogonal** to the Phase 8 E
cohort-anomaly endpoint:

* Phase 8 E walks the **cohort's latest snapshot** and flags cases
  that are outliers from the cohort mean.
* Phase 9 D walks **each case's own timeline through time** and
  flags within-case negative drift.

A case can fire one, both, or neither — they answer different
reviewer questions.

Severity buckets (more negative = worse):

* ``info``   — ``-1.5  < slope <= -0.5``
* ``warn``   — ``-3.0  < slope <= -1.5``
* ``danger`` — ``slope <= -3.0``

A slope >= ``TREND_SLOPE_INFO_MAX`` (i.e. flatter or positive) does
not fire (the case is not regressing on that axis).

Cohort size edge cases (Phase 9 anti-gaming guard T: -2):

* A case timeline with fewer than :data:`TREND_MIN_POINTS` snapshots
  yields no anomaly for that case (slope is under-determined).
* The endpoint's ``cohort_count`` counts every ``*-candidate`` case
  regardless of timeline length, but ``anomaly_count`` and
  ``anomalies`` only include cases that cleared the floor and fired.

The explicit ``claim_impact`` makes the bounded reading clear:
*"trend anomalies surface within-case degradation over time; they
do NOT diagnose root cause, validate physics, or authorize Tier 2
promotion."*

Forbidden wording (per ADR-023 + ADR-024 lite): no ``benchmark
agreement``, no ``signed validation``, no ``perforation completed``,
no ``bullet-through-steel complete``, no ``validated physics``.

Closes Phase 8 retrospective carry-forward §4.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from ._schema_versions import COHORT_TREND_ANOMALIES_SCHEMA_VERSION
from .acceptance_packet import CLAIM_BOUNDARY
from .trust_score_timeline import build_trust_score_timeline

CLAIM_TIER = "Tier 1 engineering candidate"
CLAIM_IMPACT_DEFAULT = (
    "Tier 1 candidate cohort trend-slope outliers only; not signed "
    "validation; not benchmark agreement. Trend anomalies surface "
    "within-case degradation over time; they do NOT diagnose root "
    "cause, validate physics, or authorize Tier 2 promotion. "
    "Severity buckets are slope-magnitude signals, not physical-"
    "validity verdicts."
)

# Named slope thresholds (Phase 9 anti-gaming guard M: -2).
# Convention: slope is in units of weighted-axis-points per snapshot.
# More-negative is worse. A slope == threshold goes into the WORSE
# bucket (the threshold inequality is `slope <= threshold`).
TREND_SLOPE_INFO_MAX: float = -0.5
"""``slope <= TREND_SLOPE_INFO_MAX`` and ``slope > TREND_SLOPE_WARN_MAX`` -> ``info``."""

TREND_SLOPE_WARN_MAX: float = -1.5
"""``slope <= TREND_SLOPE_WARN_MAX`` and ``slope > TREND_SLOPE_DANGER_MAX`` -> ``warn``."""

TREND_SLOPE_DANGER_MAX: float = -3.0
"""``slope <= TREND_SLOPE_DANGER_MAX`` -> ``danger``."""

# Named timeline-length floor (Phase 9 anti-gaming guard T: -2).
TREND_MIN_POINTS: int = 3
"""Below this point count, slope is under-determined; the builder
yields no anomaly for the case. Pinned by
``test_trend_cohort_with_two_points_returns_no_anomalies`` and
``test_trend_cohort_with_one_point_returns_no_anomalies``."""

Severity = Literal["info", "warn", "danger"]

# Trust-score axes the trend walk covers — kept in lock-step with
# ANOMALY_AXES in cohort_anomalies.py so a future axis addition lands
# in both surfaces consistently.
TREND_AXES: tuple[str, ...] = (
    "completeness",
    "convergence",
    "energy_audit",
    "reproducibility",
)

# Per-axis attribute name on the TimelinePoint dataclass; SSOT for the
# trend walker (so a future TimelinePoint refactor surfaces the
# breakage in one place).
_TREND_AXIS_ATTRIBUTE: dict[str, str] = {
    "completeness": "completeness_weighted",
    "convergence": "convergence_weighted",
    "energy_audit": "energy_audit_weighted",
    "reproducibility": "reproducibility_weighted",
}

_CASE_DIR_SUFFIX = "-candidate"
_CANDIDATE_DIR_RE = re.compile(r"^[A-Za-z0-9_-]+-candidate$")
_SIGNED_REGISTRY_RE = re.compile(r"^GS-\d{3}$")


@dataclass(frozen=True)
class TrendEvent:
    case_id: str
    axis: str
    slope: float
    point_count: int
    severity: Severity


@dataclass(frozen=True)
class CohortTrendAnomaliesReport:
    schema_version: str
    generated_at_utc: str
    claim_tier: str
    claim_boundary: str
    cohort_count: int
    point_count_floor: int
    anomaly_count: int
    anomalies: tuple[TrendEvent, ...]
    claim_impact: str


def severity_for_slope(slope: float) -> Severity:
    """Map slope to severity bucket. Used both internally and exported
    so tests can pin the deterministic boundary values.

    Convention: more-negative is worse. A slope at the exact boundary
    goes into the *worse* bucket (the threshold inequality is
    ``slope <= threshold``).

    Standalone calls with slope > TREND_SLOPE_INFO_MAX (i.e. flatter
    or positive) return ``"info"`` as the most-conservative bucket;
    those calls bypass the firing gate so the test surface remains
    deterministic. (The builder's firing gate at line :func:`_build_event_for_axis`
    refuses to emit an event for non-negative drift, so the
    standalone-call result never surfaces in production.)
    """
    if slope <= TREND_SLOPE_DANGER_MAX:
        return "danger"
    if slope <= TREND_SLOPE_WARN_MAX:
        return "warn"
    return "info"


def _least_squares_slope(values: list[int]) -> float:
    """Slope of the least-squares fit treating index ``i`` as x and
    ``values[i]`` as y. Caller guarantees ``len(values) >= 2``.

    Returns 0.0 when all values are identical (slope is well-defined
    as zero in that case).
    """
    n = len(values)
    sum_x = sum(range(n))
    sum_y = sum(values)
    sum_xy = sum(i * v for i, v in enumerate(values))
    sum_x2 = sum(i * i for i in range(n))
    denominator = n * sum_x2 - sum_x * sum_x
    if denominator == 0:
        return 0.0
    return (n * sum_xy - sum_x * sum_y) / denominator


def build_cohort_trend_anomalies(
    *,
    repo_root: Path,
    now_utc: datetime | None = None,
) -> CohortTrendAnomaliesReport:
    """Build the cohort trend-slope anomaly report.

    Walks ``golden_samples/*-candidate/`` (refuses signed-registry
    shape as defense in depth), builds each case's timeline, computes
    per-axis least-squares slope, fires anomaly when slope is more
    negative than :data:`TREND_SLOPE_INFO_MAX`.
    """
    golden = (repo_root / "golden_samples").resolve()
    case_ids: list[str] = []
    if golden.is_dir():
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
            case_ids.append(name)

    events: list[TrendEvent] = []
    for case_id in case_ids:
        timeline = build_trust_score_timeline(case_id, repo_root)
        if timeline.point_count < TREND_MIN_POINTS:
            continue
        for axis in TREND_AXES:
            event = _build_event_for_axis(case_id, timeline, axis)
            if event is not None:
                events.append(event)

    generated_at = (now_utc or datetime.now(UTC)).isoformat(timespec="seconds")
    report = CohortTrendAnomaliesReport(
        schema_version=COHORT_TREND_ANOMALIES_SCHEMA_VERSION,
        generated_at_utc=generated_at,
        claim_tier=CLAIM_TIER,
        claim_boundary=CLAIM_BOUNDARY,
        cohort_count=len(case_ids),
        point_count_floor=TREND_MIN_POINTS,
        anomaly_count=len(events),
        anomalies=tuple(events),
        claim_impact=CLAIM_IMPACT_DEFAULT,
    )
    _assert_no_overclaim(report)
    return report


def _build_event_for_axis(case_id: str, timeline, axis: str) -> TrendEvent | None:
    attr = _TREND_AXIS_ATTRIBUTE[axis]
    values = [getattr(p, attr) for p in timeline.points]
    if len(values) < TREND_MIN_POINTS:
        return None
    slope = _least_squares_slope(values)
    if slope > TREND_SLOPE_INFO_MAX:
        return None  # not regressing on this axis
    return TrendEvent(
        case_id=case_id,
        axis=axis,
        slope=round(slope, 6),
        point_count=len(values),
        severity=severity_for_slope(slope),
    )


def render_cohort_trend_anomalies_json(report: CohortTrendAnomaliesReport) -> str:
    return json.dumps(_report_to_dict(report), indent=2, sort_keys=True)


def _report_to_dict(report: CohortTrendAnomaliesReport) -> dict[str, object]:
    return {
        "schema_version": report.schema_version,
        "generated_at_utc": report.generated_at_utc,
        "claim_tier": report.claim_tier,
        "claim_boundary": report.claim_boundary,
        "cohort_count": report.cohort_count,
        "point_count_floor": report.point_count_floor,
        "anomaly_count": report.anomaly_count,
        "anomalies": [
            {
                "case_id": e.case_id,
                "axis": e.axis,
                "slope": e.slope,
                "point_count": e.point_count,
                "severity": e.severity,
            }
            for e in report.anomalies
        ],
        "claim_impact": report.claim_impact,
    }


# Envelope-narrowed forbidden list (same Phase 7 B / 8 B / 8 C / 8 D /
# 8 E / 9 A pattern):
_ENVELOPE_FORBIDDEN_TOKENS: tuple[str, ...] = (
    "validated against",
    "perforation completed",
    "bullet-through-steel complete",
    "validated physics",
)


def _assert_no_overclaim(report: CohortTrendAnomaliesReport) -> None:
    haystack = json.dumps(_report_to_dict(report)).lower()
    for token in _ENVELOPE_FORBIDDEN_TOKENS:
        start = 0
        while True:
            idx = haystack.find(token, start)
            if idx == -1:
                break
            prefix = haystack[max(0, idx - 4) : idx]
            if not prefix.endswith("not "):
                raise ValueError(
                    f"Cohort trend anomalies envelope contains forbidden "
                    f"positive claim {token!r} outside the 'not <claim>' "
                    "disclaimer form."
                )
            start = idx + len(token)
