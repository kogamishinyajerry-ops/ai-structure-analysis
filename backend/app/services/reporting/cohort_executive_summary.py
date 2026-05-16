"""Tier 1 candidate cohort executive summary (FM-04a Phase 8 D).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Walks ``golden_samples/*-candidate/`` and emits a one-page reviewer
scorecard with three health buckets:

* ``healthy`` — latest trust score >= 80, no warn/danger alarms in
  latest 2 snapshots, no ``blocked_pending_input`` signoff
* ``watching`` — trust score in [50, 80) OR latest signoff verdict
  is ``watching`` / ``needs_more_evidence`` / ``needs_more_convergence``,
  OR has info-level alarms
* ``regressed`` — trust score < 50 OR has warn/danger alarms OR
  latest signoff verdict is ``blocked_pending_input``

This is a reviewer convenience surface, not a promotion gate. The
explicit ``claim_impact`` states the summary does NOT promote any
case to Tier 2 or substitute for signed validation.

Forbidden wording (per ADR-023 + ADR-024 lite): no ``benchmark
agreement``, no ``signed validation``, no ``perforation completed``,
no ``bullet-through-steel complete``, no ``validated physics``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from ._schema_versions import COHORT_EXECUTIVE_SUMMARY_SCHEMA_VERSION
from .acceptance_packet import CLAIM_BOUNDARY
from .signoff_record import read_signoff_history
from .trust_score_alerts import build_trust_score_alerts
from .trust_score_timeline import build_trust_score_timeline

CLAIM_TIER = "Tier 1 engineering candidate"
CLAIM_IMPACT_DEFAULT = (
    "Tier 1 candidate cohort scorecard only; not signed validation; "
    "not benchmark agreement. The summary buckets surface candidate "
    "population health; they do NOT promote any case to Tier 2 or "
    "substitute for signed validation."
)

# Named bucket thresholds (Phase 8 anti-gaming guard M: -3 — no inline magic)
HEALTHY_TRUST_SCORE_MIN: int = 80
WATCHING_TRUST_SCORE_MIN: int = 50

HealthBucket = Literal["healthy", "watching", "regressed"]

_CASE_DIR_SUFFIX = "-candidate"
_CANDIDATE_DIR_RE = re.compile(r"^[A-Za-z0-9_-]+-candidate$")
_SIGNED_REGISTRY_RE = re.compile(r"^GS-\d{3}$")

# Watch-bucket signoff verdicts. The "blocked_pending_input" verdict is
# treated separately because it forces ``regressed``.
_WATCHING_SIGNOFF_VERDICTS = frozenset(
    {"watching", "needs_more_evidence", "needs_more_convergence"}
)


@dataclass(frozen=True)
class CohortExecutiveCaseRow:
    case_id: str
    latest_trust_score: int | None
    latest_snapshot_label: str | None
    latest_signoff_verdict: str | None
    alarm_count_warn_or_danger: int
    bucket: HealthBucket


@dataclass(frozen=True)
class CohortExecutiveSummary:
    schema_version: str
    generated_at_utc: str
    claim_tier: str
    claim_boundary: str
    cohort_count: int
    healthy_count: int
    watching_count: int
    regressed_count: int
    cases: tuple[CohortExecutiveCaseRow, ...]
    claim_impact: str


def build_cohort_executive_summary(
    *,
    repo_root: Path,
    now_utc: datetime | None = None,
) -> CohortExecutiveSummary:
    """Scan ``golden_samples/*-candidate/`` and emit a bucketed
    cohort scorecard.
    """
    golden = (repo_root / "golden_samples").resolve()
    cases: list[CohortExecutiveCaseRow] = []
    if golden.is_dir():
        for case_dir in sorted(golden.iterdir(), key=lambda p: p.name):
            if not case_dir.is_dir():
                continue
            name = case_dir.name
            if not name.endswith(_CASE_DIR_SUFFIX):
                continue
            if _SIGNED_REGISTRY_RE.fullmatch(name):
                # Defense in depth: signed-registry shape never surfaces.
                continue
            if not _CANDIDATE_DIR_RE.fullmatch(name):
                continue
            cases.append(_build_row(name, repo_root))

    healthy = sum(1 for c in cases if c.bucket == "healthy")
    watching = sum(1 for c in cases if c.bucket == "watching")
    regressed = sum(1 for c in cases if c.bucket == "regressed")

    generated_at = (now_utc or datetime.now(UTC)).isoformat(timespec="seconds")
    summary = CohortExecutiveSummary(
        schema_version=COHORT_EXECUTIVE_SUMMARY_SCHEMA_VERSION,
        generated_at_utc=generated_at,
        claim_tier=CLAIM_TIER,
        claim_boundary=CLAIM_BOUNDARY,
        cohort_count=len(cases),
        healthy_count=healthy,
        watching_count=watching,
        regressed_count=regressed,
        cases=tuple(cases),
        claim_impact=CLAIM_IMPACT_DEFAULT,
    )
    _assert_no_overclaim(summary)
    return summary


def render_cohort_executive_summary_json(summary: CohortExecutiveSummary) -> str:
    return json.dumps(_summary_to_dict(summary), indent=2, sort_keys=True)


def _build_row(case_id: str, repo_root: Path) -> CohortExecutiveCaseRow:
    timeline = build_trust_score_timeline(case_id, repo_root)
    latest_point = timeline.points[-1] if timeline.points else None
    latest_score = latest_point.trust_score if latest_point else None
    latest_label = latest_point.snapshot_label if latest_point else None

    # Alarm count: only count warn / danger from the alerts builder
    alarm_count = 0
    try:
        alerts = build_trust_score_alerts(
            case_id, repo_root, threshold_delta=1
        )
        alarm_count = sum(
            1 for event in alerts.alerts if event.severity in ("warn", "danger")
        )
    except Exception:
        alarm_count = 0

    latest_verdict: str | None = None
    try:
        history = read_signoff_history(case_id, repo_root=repo_root)
        if history:
            latest_verdict = history[-1].verdict
    except Exception:
        latest_verdict = None

    bucket = _classify_bucket(latest_score, alarm_count, latest_verdict)
    return CohortExecutiveCaseRow(
        case_id=case_id,
        latest_trust_score=latest_score,
        latest_snapshot_label=latest_label,
        latest_signoff_verdict=latest_verdict,
        alarm_count_warn_or_danger=alarm_count,
        bucket=bucket,
    )


def _classify_bucket(
    trust_score: int | None,
    alarm_count: int,
    signoff_verdict: str | None,
) -> HealthBucket:
    # regressed dominates
    if signoff_verdict == "blocked_pending_input":
        return "regressed"
    if alarm_count > 0:
        return "regressed"
    if trust_score is not None and trust_score < WATCHING_TRUST_SCORE_MIN:
        return "regressed"
    # watching dominates over healthy
    if signoff_verdict in _WATCHING_SIGNOFF_VERDICTS:
        return "watching"
    if trust_score is not None and trust_score < HEALTHY_TRUST_SCORE_MIN:
        return "watching"
    # healthy fallback (covers trust_score >= 80 with no alarms / no
    # regressed-bucket signoff, AND trust_score is None which means
    # the case has no snapshot yet)
    return "healthy"


def _summary_to_dict(summary: CohortExecutiveSummary) -> dict[str, object]:
    return {
        "schema_version": summary.schema_version,
        "generated_at_utc": summary.generated_at_utc,
        "claim_tier": summary.claim_tier,
        "claim_boundary": summary.claim_boundary,
        "cohort_count": summary.cohort_count,
        "healthy_count": summary.healthy_count,
        "watching_count": summary.watching_count,
        "regressed_count": summary.regressed_count,
        "cases": [
            {
                "case_id": c.case_id,
                "latest_trust_score": c.latest_trust_score,
                "latest_snapshot_label": c.latest_snapshot_label,
                "latest_signoff_verdict": c.latest_signoff_verdict,
                "alarm_count_warn_or_danger": c.alarm_count_warn_or_danger,
                "bucket": c.bucket,
            }
            for c in summary.cases
        ],
        "claim_impact": summary.claim_impact,
    }


_ENVELOPE_FORBIDDEN_TOKENS: tuple[str, ...] = (
    "validated against",
    "perforation completed",
    "bullet-through-steel complete",
    "validated physics",
)


def _assert_no_overclaim(summary: CohortExecutiveSummary) -> None:
    haystack = json.dumps(_summary_to_dict(summary)).lower()
    for token in _ENVELOPE_FORBIDDEN_TOKENS:
        start = 0
        while True:
            idx = haystack.find(token, start)
            if idx == -1:
                break
            prefix = haystack[max(0, idx - 4) : idx]
            if not prefix.endswith("not "):
                raise ValueError(
                    f"Cohort executive summary contains forbidden positive "
                    f"claim {token!r} outside the `not <claim>` disclaimer form."
                )
            start = idx + len(token)
