"""Tier 1 candidate trust score regression alarms (FM-04a Phase 7 C).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Walks a case's trust-score timeline (Phase 6 D) and surfaces
snapshot-to-snapshot regression events whose magnitude exceeds a
configurable ``threshold_delta``. Each event reports:

* the snapshot pair (older / newer label)
* the trust-score pair (older / newer integer value)
* the integer ``delta`` (older - newer; positive means the score
  dropped between the two snapshots)
* a severity bucket determined by named thresholds (NO inline magic
  numbers per Phase 7 anti-gaming guard ``M: -3``)
* per-axis weighted-delta breakdown so the reviewer can see which
  axis(es) drove the regression
* the ``primary_axis_shift`` (axis with the largest absolute drop)

This is a passive surface: a reviewer polls the endpoint and decides
what to do. There is no email / Slack / webhook side effect (Phase 7
blueprint §7 non-goal). The alarms are Tier 1 candidate observations,
NOT a substitute for the FM-04b P8 sealed packet.

Closes Phase 6 retrospective carry-forward §4.

Forbidden wording (per ADR-023 + ADR-024 lite): no ``benchmark
agreement``, no ``signed validation``, no ``perforation completed``,
no ``bullet-through-steel complete``, no ``validated physics``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from ._schema_versions import TRUST_SCORE_ALERTS_SCHEMA_VERSION
from .acceptance_packet import CLAIM_BOUNDARY
from .trust_score_drift_attribution import (
    DriftAttribution,
    compute_drift_attribution,
    render_drift_attribution_dict,
)
from .trust_score_timeline import TimelinePoint, build_trust_score_timeline

CLAIM_TIER = "Tier 1 engineering candidate"
CLAIM_IMPACT_DEFAULT = (
    "Tier 1 candidate trust score regression alarms only; not signed "
    "validation; not benchmark agreement. Alarms surface candidate "
    "drift; they do NOT authorize Tier 2 promotion or reject signed "
    "validation. Severity buckets are evidence-cleanliness signals, "
    "not physical-validity verdicts."
)

# ----- named severity thresholds (Phase 7 anti-gaming guard M: -3) -----

ALERT_THRESHOLD_INFO_MIN: int = 10
"""A trust-score drop in ``[ALERT_THRESHOLD_INFO_MIN,
ALERT_THRESHOLD_WARN_MIN)`` emits severity ``info``."""

ALERT_THRESHOLD_WARN_MIN: int = 25
"""A trust-score drop in ``[ALERT_THRESHOLD_WARN_MIN,
ALERT_THRESHOLD_DANGER_MIN)`` emits severity ``warn``."""

ALERT_THRESHOLD_DANGER_MIN: int = 40
"""A trust-score drop ``>= ALERT_THRESHOLD_DANGER_MIN`` emits
severity ``danger``."""

# ----- threshold input clamping -----

THRESHOLD_DELTA_MIN: int = 1
THRESHOLD_DELTA_MAX: int = 100
THRESHOLD_DELTA_DEFAULT: int = 10

Severity = Literal["info", "warn", "danger"]

_AXIS_FIELDS: tuple[str, ...] = (
    "completeness_weighted",
    "convergence_weighted",
    "energy_audit_weighted",
    "reproducibility_weighted",
)


@dataclass(frozen=True)
class TrustScoreAlertEvent:
    from_snapshot: str
    to_snapshot: str
    from_trust_score: int
    to_trust_score: int
    delta: int
    severity: Severity
    primary_axis_shift: str
    axis_deltas: dict[str, int]
    drift_attribution: DriftAttribution
    """Phase 15 C — per-axis PERCENTAGE deltas + dominant_axis when
    the absolute delta exceeds the SSOT 5.0% floor. Carries the same
    drift information as ``axis_deltas`` but expressed as percentages
    of each axis's weight, making cross-axis comparison meaningful
    (e.g. a 15-point drop on convergence vs a 15-point drop on
    completeness are both reported, but the convergence drop is
    -75% of its 20-pt axis while the completeness drop is -30% of
    its 50-pt axis). Schema 1.1.0 additive field."""


@dataclass
class TrustScoreAlertReport:
    schema_version: str
    case_id: str
    claim_tier: str
    claim_boundary: str
    generated_at_utc: str
    threshold_delta: int
    alert_count: int
    alerts: list[TrustScoreAlertEvent]
    claim_impact: str


def _severity_for(delta: int) -> Severity:
    if delta >= ALERT_THRESHOLD_DANGER_MIN:
        return "danger"
    if delta >= ALERT_THRESHOLD_WARN_MIN:
        return "warn"
    return "info"


def _clamp_threshold(threshold_delta: int) -> int:
    return max(THRESHOLD_DELTA_MIN, min(THRESHOLD_DELTA_MAX, threshold_delta))


def _axis_delta(
    older: TimelinePoint, newer: TimelinePoint, axis_field: str
) -> int:
    """Returns ``older - newer`` for the per-axis weighted score.

    Positive means the axis *dropped* between older and newer (matches
    the convention used for ``delta`` at the report level).
    """
    return int(getattr(older, axis_field)) - int(getattr(newer, axis_field))


def _primary_axis(axis_deltas: dict[str, int]) -> str:
    """The axis name whose absolute drop is largest; ties broken by
    insertion order (`_AXIS_FIELDS` ordering)."""
    best = _AXIS_FIELDS[0]
    best_abs = abs(axis_deltas[best])
    for axis in _AXIS_FIELDS[1:]:
        if abs(axis_deltas[axis]) > best_abs:
            best = axis
            best_abs = abs(axis_deltas[axis])
    return best


def build_trust_score_alerts(
    case_id: str,
    repo_root: Path,
    threshold_delta: int = THRESHOLD_DELTA_DEFAULT,
) -> TrustScoreAlertReport:
    """Compose a regression-alarm report for ``case_id``.

    Walks the case's trust-score timeline (oldest-first) and emits an
    event for every adjacent pair whose ``older.trust_score -
    newer.trust_score >= threshold_delta``. ``threshold_delta`` is
    clamped to ``[THRESHOLD_DELTA_MIN, THRESHOLD_DELTA_MAX]``.

    A case with fewer than two timeline points produces an empty
    report; the Tier 1 disclaimer trio is still present.
    """
    clamped = _clamp_threshold(threshold_delta)
    timeline = build_trust_score_timeline(case_id, repo_root)
    alerts: list[TrustScoreAlertEvent] = []
    for older, newer in zip(timeline.points, timeline.points[1:], strict=False):
        delta = int(older.trust_score) - int(newer.trust_score)
        if delta < clamped:
            continue
        axis_deltas = {
            "completeness": _axis_delta(older, newer, "completeness_weighted"),
            "convergence_stability": _axis_delta(
                older, newer, "convergence_weighted"
            ),
            "energy_audit_closure": _axis_delta(
                older, newer, "energy_audit_weighted"
            ),
            "reproducibility_clean": _axis_delta(
                older, newer, "reproducibility_weighted"
            ),
        }
        # primary_axis name maps from the timeline-field axis name to
        # the trust score breakdown axis name
        _axis_field_to_breakdown = {
            "completeness_weighted": "completeness",
            "convergence_weighted": "convergence_stability",
            "energy_audit_weighted": "energy_audit_closure",
            "reproducibility_weighted": "reproducibility_clean",
        }
        primary_field = _primary_axis(
            {field: _axis_delta(older, newer, field) for field in _AXIS_FIELDS}
        )
        # Phase 15 C — per-axis percentage deltas via the cross-
        # snapshot drift attribution SSOT. Axis labels match
        # TRUST_AXIS_WEIGHTS in trust_score_drift_attribution.py
        # ({completeness, convergence, energy_audit, reproducibility}).
        prev_axes_pct = {
            "completeness": int(older.completeness_weighted),
            "convergence": int(older.convergence_weighted),
            "energy_audit": int(older.energy_audit_weighted),
            "reproducibility": int(older.reproducibility_weighted),
        }
        curr_axes_pct = {
            "completeness": int(newer.completeness_weighted),
            "convergence": int(newer.convergence_weighted),
            "energy_audit": int(newer.energy_audit_weighted),
            "reproducibility": int(newer.reproducibility_weighted),
        }
        attribution = compute_drift_attribution(
            prev_axes_pct,
            curr_axes_pct,
            from_snapshot=older.snapshot_label,
            to_snapshot=newer.snapshot_label,
        )
        alerts.append(
            TrustScoreAlertEvent(
                from_snapshot=older.snapshot_label,
                to_snapshot=newer.snapshot_label,
                from_trust_score=int(older.trust_score),
                to_trust_score=int(newer.trust_score),
                delta=delta,
                severity=_severity_for(delta),
                primary_axis_shift=_axis_field_to_breakdown[primary_field],
                axis_deltas=axis_deltas,
                drift_attribution=attribution,
            )
        )

    report = TrustScoreAlertReport(
        schema_version=TRUST_SCORE_ALERTS_SCHEMA_VERSION,
        case_id=case_id,
        claim_tier=CLAIM_TIER,
        claim_boundary=CLAIM_BOUNDARY,
        generated_at_utc=datetime.now(UTC).isoformat(timespec="seconds"),
        threshold_delta=clamped,
        alert_count=len(alerts),
        alerts=alerts,
        claim_impact=CLAIM_IMPACT_DEFAULT,
    )
    _assert_no_overclaim(report)
    return report


def render_trust_score_alerts_json(report: TrustScoreAlertReport) -> str:
    return json.dumps(_report_to_dict(report), indent=2, sort_keys=True)


def _event_to_dict(event: TrustScoreAlertEvent) -> dict[str, object]:
    return {
        "from_snapshot": event.from_snapshot,
        "to_snapshot": event.to_snapshot,
        "from_trust_score": event.from_trust_score,
        "to_trust_score": event.to_trust_score,
        "delta": event.delta,
        "severity": event.severity,
        "primary_axis_shift": event.primary_axis_shift,
        "axis_deltas": event.axis_deltas,
        # Phase 15 C — schema 1.1.0 additive field.
        "drift_attribution": render_drift_attribution_dict(
            event.drift_attribution
        ),
    }


def _report_to_dict(report: TrustScoreAlertReport) -> dict[str, object]:
    return {
        "schema_version": report.schema_version,
        "case_id": report.case_id,
        "claim_tier": report.claim_tier,
        "claim_boundary": report.claim_boundary,
        "generated_at_utc": report.generated_at_utc,
        "threshold_delta": report.threshold_delta,
        "alert_count": report.alert_count,
        "alerts": [_event_to_dict(a) for a in report.alerts],
        "claim_impact": report.claim_impact,
    }


def _assert_no_overclaim(report: TrustScoreAlertReport) -> None:
    forbidden = (
        "validated against",
        "perforation completed",
        "bullet-through-steel complete",
        "validated physics",
    )
    haystack = json.dumps(_report_to_dict(report), default=str).lower()
    for token in forbidden:
        if token in haystack:
            raise ValueError(
                f"Trust score alerts contain forbidden positive claim: {token!r}"
            )
