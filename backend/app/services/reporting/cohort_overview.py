r"""Tier 1 candidate cohort overview (FM-04a Phase 4 B).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Scans `golden_samples/*-candidate/` and emits one structured row per
case (case_id, completeness score, perforation marker, residual
velocity, energy balance error, convergence verdict, last_modified)
plus aggregate fields (cohort_count, mean_score,
completeness_distribution). Read-only across `golden_samples/**`;
strictly filters out any `^GS-\d{3}$` signed-registry directory shape.

The cohort score is evidence-presence only — the same FM-04b
blockers list is rendered alongside the aggregate so 100% mean score
still surfaces the Tier 2 boundary.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ._schema_versions import COHORT_OVERVIEW_SCHEMA_VERSION
from .acceptance_packet import (
    CLAIM_BOUNDARY,
    DEFAULT_TIER2_BLOCKERS_REMAINING,
)
from .case_completeness import (
    CaseCompletenessInputs,
    score_case_completeness,
)

CLAIM_TIER = "Tier 1 engineering candidate"
CLAIM_IMPACT_DEFAULT = (
    "Tier 1 candidate cohort overview only; not signed validation; not "
    "benchmark agreement; not a cohort-level validation report. Per-case "
    "scores are evidence-presence only — every FM-04b prerequisite "
    "remains gated for every case regardless of score."
)

_CASE_DIR_SUFFIX = "-candidate"
_CANDIDATE_DIR_RE = re.compile(r"^[A-Za-z0-9_-]+-candidate$")
# Mirror the candidate_cases endpoint's filter so the signed
# ^GS-\d{3}$ registry shape is NEVER surfaced through cohort overview.
_SIGNED_REGISTRY_RE = re.compile(r"^GS-\d{3}$")


@dataclass(frozen=True)
class CohortOverviewEntry:
    """One scored row in the cohort overview."""

    case_id: str
    completeness_score: int
    completeness_score_max: int
    perforation_marker: str | None
    projectile_initial_velocity_m_per_s: float | None
    residual_velocity_candidate_m_per_s: float | None
    energy_balance_error_pct: float | None
    energy_audit_status: str
    convergence_combined_verdict: str
    last_modified_utc: str | None
    missing_evidence_count: int


@dataclass(frozen=True)
class CohortOverview:
    """Aggregate Tier 1 cohort summary."""

    generated_at_utc: str
    claim_tier: str
    claim_boundary: str
    cohort_count: int
    mean_score: float | None
    completeness_distribution: dict[str, int]
    entries: list[CohortOverviewEntry]
    tier2_blockers_remaining: list[str]
    claim_impact: str


def build_cohort_overview(repo_root: Path) -> CohortOverview:
    """Scan golden_samples/*-candidate/ and emit a scored cohort overview."""
    golden = (repo_root / "golden_samples").resolve()
    entries: list[CohortOverviewEntry] = []
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
            entries.append(_build_entry(name, repo_root))

    mean_score: float | None = None
    if entries:
        mean_score = round(sum(e.completeness_score for e in entries) / len(entries), 2)

    distribution = _build_distribution(entries)

    overview = CohortOverview(
        generated_at_utc=datetime.now(UTC).isoformat(timespec="seconds"),
        claim_tier=CLAIM_TIER,
        claim_boundary=CLAIM_BOUNDARY,
        cohort_count=len(entries),
        mean_score=mean_score,
        completeness_distribution=distribution,
        entries=entries,
        tier2_blockers_remaining=list(DEFAULT_TIER2_BLOCKERS_REMAINING),
        claim_impact=CLAIM_IMPACT_DEFAULT,
    )
    _assert_no_overclaim(overview)
    return overview


def render_cohort_overview_json(overview: CohortOverview) -> str:
    """Return the cohort overview as a JSON string."""
    return json.dumps(_overview_to_dict(overview), indent=2, sort_keys=True)


# ---------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------


def _build_entry(case_id: str, repo_root: Path) -> CohortOverviewEntry:
    case_dir = repo_root / "golden_samples" / case_id
    starter = case_dir / "data" / "model_00_0000.rad"
    engine = case_dir / "data" / "model_00_0001.rad"
    notes = case_dir / "NOTES.md"
    metrics_path = (
        repo_root
        / "project_state"
        / "graph_executor"
        / case_id
        / "ballistic"
        / "ballistic_metrics.json"
    )
    convergence_path = (
        repo_root
        / "project_state"
        / "graph_executor"
        / case_id
        / "convergence"
        / "convergence_study.json"
    )
    animation_path = (
        repo_root
        / "project_state"
        / "graph_executor"
        / case_id
        / "visualization"
        / "openradioss_animation_manifest.json"
    )
    result_mesh_path = repo_root / "project_state" / "visualizations" / case_id / "result_mesh.json"
    slug = case_id.lower().replace("gs-", "gs").replace("-candidate", "").replace("-", "_")
    generator_script = repo_root / "scripts" / f"gen_{slug}_deck.py"

    score = score_case_completeness(
        CaseCompletenessInputs(
            case_id=case_id,
            starter_deck_path=starter,
            engine_deck_path=engine,
            ballistic_metrics_path=metrics_path,
            convergence_study_path=convergence_path,
            animation_manifest_path=animation_path,
            result_mesh_path=result_mesh_path,
            generator_script_path=generator_script,
            notes_path=notes,
        )
    )

    metrics_payload = _safe_read_json(metrics_path)
    convergence_payload = _safe_read_json(convergence_path)
    audit = (
        (metrics_payload or {}).get("energy_audit")
        or (metrics_payload or {}).get("partial_energy_audit")
        or {}
    )

    return CohortOverviewEntry(
        case_id=case_id,
        completeness_score=score.score,
        completeness_score_max=score.score_max,
        perforation_marker=(metrics_payload or {}).get("perforation_marker"),
        projectile_initial_velocity_m_per_s=(metrics_payload or {}).get(
            "projectile_initial_velocity_m_per_s"
        ),
        residual_velocity_candidate_m_per_s=(metrics_payload or {}).get(
            "residual_velocity_candidate_m_per_s"
        ),
        energy_balance_error_pct=audit.get("energy_balance_error_pct"),
        energy_audit_status=audit.get("status", "unavailable"),
        convergence_combined_verdict=(convergence_payload or {}).get(
            "combined_verdict", "insufficient_data"
        ),
        last_modified_utc=_latest_mtime_utc([starter, engine, metrics_path, convergence_path]),
        missing_evidence_count=len(score.missing_evidence),
    )


def _build_distribution(entries: list[CohortOverviewEntry]) -> dict[str, int]:
    """Bucket entries into score bands for at-a-glance reading."""
    buckets = {"0-49": 0, "50-79": 0, "80-99": 0, "100": 0}
    for entry in entries:
        score = entry.completeness_score
        if score >= 100:
            buckets["100"] += 1
        elif score >= 80:
            buckets["80-99"] += 1
        elif score >= 50:
            buckets["50-79"] += 1
        else:
            buckets["0-49"] += 1
    return buckets


def _safe_read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _latest_mtime_utc(paths: list[Path]) -> str | None:
    """Most-recent mtime across the supplied paths, ISO-formatted UTC."""
    timestamps: list[float] = []
    for path in paths:
        try:
            if path.is_file():
                timestamps.append(path.stat().st_mtime)
        except OSError:
            continue
    if not timestamps:
        return None
    latest = max(timestamps)
    return datetime.fromtimestamp(latest, tz=UTC).isoformat(timespec="seconds")


def _entry_to_dict(entry: CohortOverviewEntry) -> dict[str, Any]:
    return {
        "case_id": entry.case_id,
        "completeness_score": entry.completeness_score,
        "completeness_score_max": entry.completeness_score_max,
        "perforation_marker": entry.perforation_marker,
        "projectile_initial_velocity_m_per_s": entry.projectile_initial_velocity_m_per_s,
        "residual_velocity_candidate_m_per_s": entry.residual_velocity_candidate_m_per_s,
        "energy_balance_error_pct": entry.energy_balance_error_pct,
        "energy_audit_status": entry.energy_audit_status,
        "convergence_combined_verdict": entry.convergence_combined_verdict,
        "last_modified_utc": entry.last_modified_utc,
        "missing_evidence_count": entry.missing_evidence_count,
    }


def _overview_to_dict(overview: CohortOverview) -> dict[str, Any]:
    return {
        "schema_version": COHORT_OVERVIEW_SCHEMA_VERSION,
        "generated_at_utc": overview.generated_at_utc,
        "claim_tier": overview.claim_tier,
        "claim_boundary": overview.claim_boundary,
        "cohort_count": overview.cohort_count,
        "mean_score": overview.mean_score,
        "completeness_distribution": overview.completeness_distribution,
        "entries": [_entry_to_dict(e) for e in overview.entries],
        "tier2_blockers_remaining": overview.tier2_blockers_remaining,
        "claim_impact": overview.claim_impact,
    }


def _assert_no_overclaim(overview: CohortOverview) -> None:
    forbidden = (
        "validated against",
        "perforation completed",
        "bullet-through-steel complete",
        "validated physics",
    )
    haystack = json.dumps(_overview_to_dict(overview), default=str).lower()
    for token in forbidden:
        if token in haystack:
            raise ValueError(f"Cohort overview contains forbidden claim: {token!r}")
