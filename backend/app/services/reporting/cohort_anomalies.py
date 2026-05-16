"""Tier 1 candidate cohort anomaly detection (FM-04a Phase 8 E).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

For each ``*-candidate`` case + each of the 4 trust-score axes
(completeness / convergence / energy_audit / reproducibility),
compute the cohort mean + standard deviation of the latest axis-
weighted score, then flag any case whose axis-score is more than
2 sigma from the cohort mean.

Severity buckets:

* ``info``  — 2σ <= |z| < 3σ
* ``warn``  — 3σ <= |z| < 4σ
* ``danger`` — |z| >= 4σ

Cohort size edge cases (Phase 8 anti-gaming guard T: -2):

* cohort size 0: no anomalies (no cases).
* cohort size 1 or 2: no anomalies (stdev is degenerate; we require
  at least :data:`COHORT_MIN_SIZE_FOR_ANOMALY` to be honest).
* cohort size >= 3: compute z-scores normally.

The explicit ``claim_impact`` makes the bounded reading clear:
*"anomalies surface statistical outliers from cohort mean; they
do NOT diagnose root cause, validate physics, or authorize Tier 2
promotion."*

Forbidden wording (per ADR-023 + ADR-024 lite): no ``benchmark
agreement``, no ``signed validation``, no ``perforation completed``,
no ``bullet-through-steel complete``, no ``validated physics``.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from ._schema_versions import COHORT_ANOMALIES_SCHEMA_VERSION
from .acceptance_packet import CLAIM_BOUNDARY
from .trust_score_timeline import build_trust_score_timeline

CLAIM_TIER = "Tier 1 engineering candidate"
CLAIM_IMPACT_DEFAULT = (
    "Tier 1 candidate cohort statistical outliers only; not signed "
    "validation; not benchmark agreement. Anomalies surface "
    "statistical outliers from cohort mean; they do NOT diagnose "
    "root cause, validate physics, or authorize Tier 2 promotion. "
    "Severity buckets are cohort-relative signals, not physical-"
    "validity verdicts."
)

# Named z-score thresholds (Phase 8 anti-gaming guard M: -3)
ANOMALY_SIGMA_INFO_MIN: float = 2.0
"""|z| in ``[ANOMALY_SIGMA_INFO_MIN, ANOMALY_SIGMA_WARN_MIN)`` -> ``info``."""

ANOMALY_SIGMA_WARN_MIN: float = 3.0
"""|z| in ``[ANOMALY_SIGMA_WARN_MIN, ANOMALY_SIGMA_DANGER_MIN)`` -> ``warn``."""

ANOMALY_SIGMA_DANGER_MIN: float = 4.0
"""|z| ``>= ANOMALY_SIGMA_DANGER_MIN`` -> ``danger``."""

# Named cohort-size floor (Phase 8 anti-gaming guard M: -3)
COHORT_MIN_SIZE_FOR_ANOMALY: int = 3
"""Below this size, stdev is degenerate; the builder returns no
anomalies. Pinned by ``test_anomaly_cohort_size_one_returns_empty``
and ``test_anomaly_cohort_size_two_returns_empty``."""

Severity = Literal["info", "warn", "danger"]

# Trust-score axes the anomaly walk covers
ANOMALY_AXES: tuple[str, ...] = (
    "completeness",
    "convergence",
    "energy_audit",
    "reproducibility",
)

_CASE_DIR_SUFFIX = "-candidate"
_CANDIDATE_DIR_RE = re.compile(r"^[A-Za-z0-9_-]+-candidate$")
_SIGNED_REGISTRY_RE = re.compile(r"^GS-\d{3}$")


@dataclass(frozen=True)
class AnomalyEvent:
    case_id: str
    axis: str
    score: int
    cohort_mean: float
    cohort_stdev: float
    z_score: float
    severity: Severity


@dataclass(frozen=True)
class CohortAnomaliesReport:
    schema_version: str
    generated_at_utc: str
    claim_tier: str
    claim_boundary: str
    cohort_count: int
    anomaly_count: int
    anomalies: tuple[AnomalyEvent, ...]
    claim_impact: str


def severity_for(z_score: float) -> Severity:
    """Map |z| to severity bucket. Used both internally and exported
    so tests can pin the deterministic boundary values."""
    abs_z = abs(z_score)
    if abs_z >= ANOMALY_SIGMA_DANGER_MIN:
        return "danger"
    if abs_z >= ANOMALY_SIGMA_WARN_MIN:
        return "warn"
    return "info"


def build_cohort_anomalies(
    *,
    repo_root: Path,
    now_utc: datetime | None = None,
) -> CohortAnomaliesReport:
    """Walk ``golden_samples/*-candidate/``, compute per-axis z-scores
    across the cohort, and flag |z| >= :data:`ANOMALY_SIGMA_INFO_MIN`.
    """
    golden = (repo_root / "golden_samples").resolve()
    cases: list[str] = []
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
            cases.append(name)

    # Collect (case_id, axis) -> score for all cohort members with at
    # least one timeline point. Cases with no timeline are omitted.
    per_axis_scores: dict[str, dict[str, int]] = {axis: {} for axis in ANOMALY_AXES}
    cohort_with_scores: list[str] = []
    for case_id in cases:
        timeline = build_trust_score_timeline(case_id, repo_root)
        if not timeline.points:
            continue
        latest = timeline.points[-1]
        cohort_with_scores.append(case_id)
        per_axis_scores["completeness"][case_id] = latest.completeness_weighted
        per_axis_scores["convergence"][case_id] = latest.convergence_weighted
        per_axis_scores["energy_audit"][case_id] = latest.energy_audit_weighted
        per_axis_scores["reproducibility"][case_id] = latest.reproducibility_weighted

    anomalies: list[AnomalyEvent] = []
    if len(cohort_with_scores) >= COHORT_MIN_SIZE_FOR_ANOMALY:
        for axis in ANOMALY_AXES:
            scores = [per_axis_scores[axis][cid] for cid in cohort_with_scores]
            mean = sum(scores) / len(scores)
            variance = sum((s - mean) ** 2 for s in scores) / len(scores)
            stdev = math.sqrt(variance)
            if stdev == 0:
                # No spread -> no statistical outlier possible.
                continue
            for case_id in cohort_with_scores:
                score = per_axis_scores[axis][case_id]
                z = (score - mean) / stdev
                if abs(z) >= ANOMALY_SIGMA_INFO_MIN:
                    anomalies.append(
                        AnomalyEvent(
                            case_id=case_id,
                            axis=axis,
                            score=score,
                            cohort_mean=round(mean, 4),
                            cohort_stdev=round(stdev, 4),
                            z_score=round(z, 4),
                            severity=severity_for(z),
                        )
                    )

    generated_at = (now_utc or datetime.now(UTC)).isoformat(timespec="seconds")
    report = CohortAnomaliesReport(
        schema_version=COHORT_ANOMALIES_SCHEMA_VERSION,
        generated_at_utc=generated_at,
        claim_tier=CLAIM_TIER,
        claim_boundary=CLAIM_BOUNDARY,
        cohort_count=len(cases),
        anomaly_count=len(anomalies),
        anomalies=tuple(anomalies),
        claim_impact=CLAIM_IMPACT_DEFAULT,
    )
    _assert_no_overclaim(report)
    return report


def render_cohort_anomalies_json(report: CohortAnomaliesReport) -> str:
    return json.dumps(_report_to_dict(report), indent=2, sort_keys=True)


def _report_to_dict(report: CohortAnomaliesReport) -> dict[str, object]:
    return {
        "schema_version": report.schema_version,
        "generated_at_utc": report.generated_at_utc,
        "claim_tier": report.claim_tier,
        "claim_boundary": report.claim_boundary,
        "cohort_count": report.cohort_count,
        "anomaly_count": report.anomaly_count,
        "anomalies": [
            {
                "case_id": a.case_id,
                "axis": a.axis,
                "score": a.score,
                "cohort_mean": a.cohort_mean,
                "cohort_stdev": a.cohort_stdev,
                "z_score": a.z_score,
                "severity": a.severity,
            }
            for a in report.anomalies
        ],
        "claim_impact": report.claim_impact,
    }


_ENVELOPE_FORBIDDEN_TOKENS: tuple[str, ...] = (
    "validated against",
    "perforation completed",
    "bullet-through-steel complete",
    "validated physics",
)


def _assert_no_overclaim(report: CohortAnomaliesReport) -> None:
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
                    f"Cohort anomalies report contains forbidden positive "
                    f"claim {token!r} outside the `not <claim>` disclaimer form."
                )
            start = idx + len(token)
