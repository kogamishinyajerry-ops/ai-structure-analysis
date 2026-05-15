"""Tier 1 candidate evidence completeness scoring (FM-04a Phase 4 A).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Scores how *complete* a Tier 1 candidate case's on-disk evidence
inventory is — strictly an evidence-presence signal, NOT a validation
quality signal. Even a 100/100 score keeps every FM-04b blocker
visible in the rendered output. The score is bounded to 100 and
deterministic given the same inputs.

Rubric (sums to 100):

* Starter deck present: 15 pts
* Engine deck present: 15 pts
* `ballistic_metrics.json` present: 20 pts
* Energy audit `closed_aggregate` (vs `partial_candidate` / `unavailable`): 15 pts
  (10 pts for `partial_candidate`; 0 for `unavailable` / unknown)
* `convergence_study.json` present with `candidate_observed_stable`
  verdict: 15 pts (10 if present but `candidate_observed_unstable`;
  5 if present with any other verdict; 0 if absent)
* Animation manifest: 5 pts
* Result mesh: 5 pts
* Generator script: 5 pts
* NOTES.md: 5 pts

Forbidden wording: ``validated against``, ``benchmark agreement``,
``signed validation``, ``perforation completed``,
``bullet-through-steel complete``, ``validated physics``. The builder
asserts the rendered JSON stays clean against these positive claims;
``not <claim>`` disclaimers remain allowed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .acceptance_packet import (
    CLAIM_BOUNDARY,
    DEFAULT_TIER2_BLOCKERS_REMAINING,
)

CLAIM_TIER = "Tier 1 engineering candidate"
CLAIM_IMPACT_DEFAULT = (
    "Tier 1 candidate evidence-presence score only; not signed validation; "
    "not benchmark agreement; not a measure of validation quality. Even a "
    "100/100 score does NOT authorize promotion to Tier 2 — every FM-04b "
    "prerequisite remains gated."
)

# Rubric weights (sum = 100).
WEIGHT_STARTER_DECK = 15
WEIGHT_ENGINE_DECK = 15
WEIGHT_BALLISTIC_METRICS = 20
WEIGHT_ENERGY_AUDIT_CLOSED = 15
WEIGHT_ENERGY_AUDIT_PARTIAL = 10
WEIGHT_CONVERGENCE_STABLE = 15
WEIGHT_CONVERGENCE_UNSTABLE = 10
WEIGHT_CONVERGENCE_OTHER = 5
WEIGHT_ANIMATION_MANIFEST = 5
WEIGHT_RESULT_MESH = 5
WEIGHT_GENERATOR_SCRIPT = 5
WEIGHT_NOTES = 5


@dataclass(frozen=True)
class CaseCompletenessInputs:
    """Paths probed for evidence presence. All optional except case_id."""

    case_id: str
    starter_deck_path: Path | None = None
    engine_deck_path: Path | None = None
    ballistic_metrics_path: Path | None = None
    convergence_study_path: Path | None = None
    animation_manifest_path: Path | None = None
    result_mesh_path: Path | None = None
    generator_script_path: Path | None = None
    notes_path: Path | None = None


@dataclass(frozen=True)
class CompletenessBreakdownEntry:
    """One rubric line in the score breakdown."""

    label: str
    points_awarded: int
    points_max: int
    evidence_status: str  # e.g. "present", "absent", "closed_aggregate"
    notes: str | None = None


@dataclass(frozen=True)
class CaseCompletenessScore:
    """Tier 1 evidence-presence score for one candidate case."""

    case_id: str
    generated_at_utc: str
    claim_tier: str
    claim_boundary: str
    score: int
    score_max: int
    breakdown: list[CompletenessBreakdownEntry]
    missing_evidence: list[str]
    tier2_blockers_remaining: list[str]
    claim_impact: str


def score_case_completeness(inputs: CaseCompletenessInputs) -> CaseCompletenessScore:
    """Score one case's evidence completeness against the rubric."""
    breakdown: list[CompletenessBreakdownEntry] = []
    missing: list[str] = []

    # Starter / engine decks: 15 pts each.
    breakdown.append(
        _score_simple_presence(
            "starter_deck", inputs.starter_deck_path, WEIGHT_STARTER_DECK, missing
        )
    )
    breakdown.append(
        _score_simple_presence("engine_deck", inputs.engine_deck_path, WEIGHT_ENGINE_DECK, missing)
    )

    # ballistic_metrics.json: 20 pts plus energy audit sub-score.
    metrics_entry, audit_entry = _score_ballistic_metrics(inputs.ballistic_metrics_path, missing)
    breakdown.append(metrics_entry)
    breakdown.append(audit_entry)

    # convergence_study.json: 15 / 10 / 5 / 0 pts by verdict.
    breakdown.append(_score_convergence_study(inputs.convergence_study_path, missing))

    # Optional artifacts: 5 pts each.
    breakdown.append(
        _score_simple_presence(
            "animation_manifest",
            inputs.animation_manifest_path,
            WEIGHT_ANIMATION_MANIFEST,
            missing,
        )
    )
    breakdown.append(
        _score_simple_presence("result_mesh", inputs.result_mesh_path, WEIGHT_RESULT_MESH, missing)
    )
    breakdown.append(
        _score_simple_presence(
            "generator_script",
            inputs.generator_script_path,
            WEIGHT_GENERATOR_SCRIPT,
            missing,
        )
    )
    breakdown.append(_score_simple_presence("notes", inputs.notes_path, WEIGHT_NOTES, missing))

    total = sum(entry.points_awarded for entry in breakdown)
    score = CaseCompletenessScore(
        case_id=inputs.case_id,
        generated_at_utc=datetime.now(UTC).isoformat(timespec="seconds"),
        claim_tier=CLAIM_TIER,
        claim_boundary=CLAIM_BOUNDARY,
        score=total,
        score_max=100,
        breakdown=breakdown,
        missing_evidence=missing,
        tier2_blockers_remaining=list(DEFAULT_TIER2_BLOCKERS_REMAINING),
        claim_impact=CLAIM_IMPACT_DEFAULT,
    )
    _assert_no_overclaim(score)
    return score


def render_case_completeness_json(score: CaseCompletenessScore) -> str:
    """Return the completeness score as a JSON string."""
    return json.dumps(_score_to_dict(score), indent=2, sort_keys=True)


# ---------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------


def _score_simple_presence(
    label: str, path: Path | None, weight: int, missing: list[str]
) -> CompletenessBreakdownEntry:
    if path is not None and path.is_file():
        return CompletenessBreakdownEntry(
            label=label,
            points_awarded=weight,
            points_max=weight,
            evidence_status="present",
        )
    missing.append(label)
    return CompletenessBreakdownEntry(
        label=label,
        points_awarded=0,
        points_max=weight,
        evidence_status="absent",
    )


def _score_ballistic_metrics(
    metrics_path: Path | None, missing: list[str]
) -> tuple[CompletenessBreakdownEntry, CompletenessBreakdownEntry]:
    """Score ballistic_metrics.json presence (20) + energy audit band (15/10/0)."""
    if metrics_path is None or not metrics_path.is_file():
        missing.append("ballistic_metrics")
        missing.append("energy_audit")
        return (
            CompletenessBreakdownEntry(
                label="ballistic_metrics",
                points_awarded=0,
                points_max=WEIGHT_BALLISTIC_METRICS,
                evidence_status="absent",
            ),
            CompletenessBreakdownEntry(
                label="energy_audit",
                points_awarded=0,
                points_max=WEIGHT_ENERGY_AUDIT_CLOSED,
                evidence_status="absent",
            ),
        )

    try:
        raw = json.loads(metrics_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        missing.append("ballistic_metrics")
        missing.append("energy_audit")
        return (
            CompletenessBreakdownEntry(
                label="ballistic_metrics",
                points_awarded=0,
                points_max=WEIGHT_BALLISTIC_METRICS,
                evidence_status="unreadable",
            ),
            CompletenessBreakdownEntry(
                label="energy_audit",
                points_awarded=0,
                points_max=WEIGHT_ENERGY_AUDIT_CLOSED,
                evidence_status="unreadable",
            ),
        )

    metrics_entry = CompletenessBreakdownEntry(
        label="ballistic_metrics",
        points_awarded=WEIGHT_BALLISTIC_METRICS,
        points_max=WEIGHT_BALLISTIC_METRICS,
        evidence_status="present",
    )

    audit = raw.get("energy_audit") or raw.get("partial_energy_audit") or {}
    audit_status = audit.get("status", "unavailable")
    if audit_status == "closed_aggregate":
        audit_entry = CompletenessBreakdownEntry(
            label="energy_audit",
            points_awarded=WEIGHT_ENERGY_AUDIT_CLOSED,
            points_max=WEIGHT_ENERGY_AUDIT_CLOSED,
            evidence_status="closed_aggregate",
        )
    elif audit_status == "partial_candidate":
        audit_entry = CompletenessBreakdownEntry(
            label="energy_audit",
            points_awarded=WEIGHT_ENERGY_AUDIT_PARTIAL,
            points_max=WEIGHT_ENERGY_AUDIT_CLOSED,
            evidence_status="partial_candidate",
            notes="KE-only audit; per-term split blocked on /TH/PART cards.",
        )
        missing.append("energy_audit_closed_aggregate")
    else:
        audit_entry = CompletenessBreakdownEntry(
            label="energy_audit",
            points_awarded=0,
            points_max=WEIGHT_ENERGY_AUDIT_CLOSED,
            evidence_status=audit_status or "unavailable",
        )
        missing.append("energy_audit")

    return metrics_entry, audit_entry


def _score_convergence_study(
    convergence_path: Path | None, missing: list[str]
) -> CompletenessBreakdownEntry:
    """Score convergence_study.json by combined_verdict band."""
    if convergence_path is None or not convergence_path.is_file():
        missing.append("convergence_study")
        return CompletenessBreakdownEntry(
            label="convergence_study",
            points_awarded=0,
            points_max=WEIGHT_CONVERGENCE_STABLE,
            evidence_status="absent",
        )

    try:
        raw = json.loads(convergence_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        missing.append("convergence_study")
        return CompletenessBreakdownEntry(
            label="convergence_study",
            points_awarded=0,
            points_max=WEIGHT_CONVERGENCE_STABLE,
            evidence_status="unreadable",
        )

    verdict = raw.get("combined_verdict", "insufficient_data")
    if verdict == "candidate_observed_stable":
        return CompletenessBreakdownEntry(
            label="convergence_study",
            points_awarded=WEIGHT_CONVERGENCE_STABLE,
            points_max=WEIGHT_CONVERGENCE_STABLE,
            evidence_status=verdict,
        )
    if verdict == "candidate_observed_unstable":
        missing.append("convergence_study_stable")
        return CompletenessBreakdownEntry(
            label="convergence_study",
            points_awarded=WEIGHT_CONVERGENCE_UNSTABLE,
            points_max=WEIGHT_CONVERGENCE_STABLE,
            evidence_status=verdict,
            notes="sweep crosses tolerance; refine grid before reporting.",
        )
    # Any other verdict (insufficient_data, unknown).
    missing.append("convergence_study_verdict")
    return CompletenessBreakdownEntry(
        label="convergence_study",
        points_awarded=WEIGHT_CONVERGENCE_OTHER,
        points_max=WEIGHT_CONVERGENCE_STABLE,
        evidence_status=verdict,
    )


def _entry_to_dict(entry: CompletenessBreakdownEntry) -> dict[str, Any]:
    out: dict[str, Any] = {
        "label": entry.label,
        "points_awarded": entry.points_awarded,
        "points_max": entry.points_max,
        "evidence_status": entry.evidence_status,
    }
    if entry.notes is not None:
        out["notes"] = entry.notes
    return out


def _score_to_dict(score: CaseCompletenessScore) -> dict[str, Any]:
    return {
        "case_id": score.case_id,
        "generated_at_utc": score.generated_at_utc,
        "claim_tier": score.claim_tier,
        "claim_boundary": score.claim_boundary,
        "score": score.score,
        "score_max": score.score_max,
        "breakdown": [_entry_to_dict(entry) for entry in score.breakdown],
        "missing_evidence": score.missing_evidence,
        "tier2_blockers_remaining": score.tier2_blockers_remaining,
        "claim_impact": score.claim_impact,
    }


def _assert_no_overclaim(score: CaseCompletenessScore) -> None:
    forbidden = (
        "validated against",
        "perforation completed",
        "bullet-through-steel complete",
        "validated physics",
    )
    haystack = json.dumps(_score_to_dict(score), default=str).lower()
    for token in forbidden:
        if token in haystack:
            raise ValueError(f"Completeness score contains forbidden claim: {token!r}")
