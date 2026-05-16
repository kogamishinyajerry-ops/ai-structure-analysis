"""Tier 1 candidate trust score timeline (FM-04a Phase 6 D).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Walks every cohort snapshot under ``reports/snapshots/<*>/`` that
contains the requested case, recomputes a trust score from the
*captured* snapshot evidence (completeness scorecard +
reproducibility manifest + optional metrics file from Phase 6 A),
and emits an ordered timeline.

The timeline reads frozen snapshot bytes, NOT live evidence. A
reviewer reading the timeline sees how the case's trust score has
*evolved* across past snapshots, not its current state. The live
state surface is ``/api/v1/trust-score/<case-id>`` (Phase 6 B).

The recomputation uses the same constants as ``trust_score.py`` so
formula_version is shared. The schema_version stamped on the
timeline envelope is separate (TRUST_SCORE_TIMELINE_SCHEMA_VERSION).

Forbidden wording (per ADR-023 + ADR-024 lite): no ``benchmark
agreement``, no ``signed validation``, no ``perforation completed``,
no ``bullet-through-steel complete``, no ``validated physics``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ._schema_versions import (
    TRUST_SCORE_FORMULA_VERSION,
    TRUST_SCORE_TIMELINE_SCHEMA_VERSION,
)
from .acceptance_packet import CLAIM_BOUNDARY
from .cohort_snapshot import (
    SNAPSHOT_LABEL_RE,
    SNAPSHOT_MANIFEST_FILENAME,
    snapshots_root,
)
from .trust_score import (
    COMPLETENESS_WEIGHT,
    CONVERGENCE_WEIGHT,
    ENERGY_AUDIT_WEIGHT,
    REPRO_PENALTY_GIT_DIRTY,
    REPRO_PENALTY_GIT_SHA_MISSING,
    REPRO_PENALTY_PER_NOT_INSTALLED_PACKAGE,
    REPRODUCIBILITY_WEIGHT,
)

CLAIM_TIER = "Tier 1 engineering candidate"
CLAIM_IMPACT_DEFAULT = (
    "Tier 1 candidate trust score timeline only; not signed "
    "validation; not benchmark agreement. Timeline points are "
    "recomputed from captured snapshot evidence, not from live "
    "project_state/ files; they show evolution over time, not "
    "current state."
)


@dataclass(frozen=True)
class TimelinePoint:
    snapshot_label: str
    captured_at_utc: str | None
    trust_score: int
    completeness_weighted: int
    convergence_weighted: int
    energy_audit_weighted: int
    reproducibility_weighted: int


@dataclass
class TrustScoreTimeline:
    schema_version: str
    formula_version: str
    case_id: str
    claim_tier: str
    claim_boundary: str
    generated_at_utc: str
    point_count: int
    points: list[TimelinePoint]
    claim_impact: str


def build_trust_score_timeline(
    case_id: str, repo_root: Path
) -> TrustScoreTimeline:
    """Walk reports/snapshots/<*>/ and compose a trust score timeline
    for ``case_id``.

    Snapshots that do not contain the case (no completeness/<case>.json
    file) are skipped. Order is oldest-first by snapshot_label (which
    is ISO-ordered).
    """
    root = snapshots_root(repo_root)
    points: list[TimelinePoint] = []
    if root.is_dir():
        for child in sorted(root.iterdir()):
            if not child.is_dir():
                continue
            if not SNAPSHOT_LABEL_RE.fullmatch(child.name):
                continue
            point = _build_point(case_id, child)
            if point is not None:
                points.append(point)

    timeline = TrustScoreTimeline(
        schema_version=TRUST_SCORE_TIMELINE_SCHEMA_VERSION,
        formula_version=TRUST_SCORE_FORMULA_VERSION,
        case_id=case_id,
        claim_tier=CLAIM_TIER,
        claim_boundary=CLAIM_BOUNDARY,
        generated_at_utc=datetime.now(UTC).isoformat(timespec="seconds"),
        point_count=len(points),
        points=points,
        claim_impact=CLAIM_IMPACT_DEFAULT,
    )
    _assert_no_overclaim(timeline)
    return timeline


def render_trust_score_timeline_json(timeline: TrustScoreTimeline) -> str:
    """Return the timeline as a JSON string."""
    return json.dumps(_timeline_to_dict(timeline), indent=2, sort_keys=True)


# ---------------------------------------------------------------------
# per-snapshot point construction
# ---------------------------------------------------------------------


def _build_point(case_id: str, snapshot_dir: Path) -> TimelinePoint | None:
    manifest_path = snapshot_dir / SNAPSHOT_MANIFEST_FILENAME
    if not manifest_path.is_file():
        return None
    completeness_path = snapshot_dir / "completeness" / f"{case_id}.json"
    if not completeness_path.is_file():
        return None

    manifest = _load_optional_json(manifest_path) or {}
    completeness = _load_optional_json(completeness_path) or {}
    repro = _load_optional_json(
        snapshot_dir / "reproducibility" / f"{case_id}.json"
    )
    metrics = _load_optional_json(
        snapshot_dir / "metrics" / f"{case_id}.json"
    )
    convergence = _convergence_block_from_metrics(metrics)

    completeness_w = _completeness_weighted(completeness)
    convergence_w = _convergence_weighted(convergence)
    energy_w = _energy_weighted(metrics)
    repro_w = _reproducibility_weighted(repro)

    trust = completeness_w + convergence_w + energy_w + repro_w
    return TimelinePoint(
        snapshot_label=snapshot_dir.name,
        captured_at_utc=manifest.get("captured_at_utc"),
        trust_score=trust,
        completeness_weighted=completeness_w,
        convergence_weighted=convergence_w,
        energy_audit_weighted=energy_w,
        reproducibility_weighted=repro_w,
    )


def _completeness_weighted(payload: dict[str, Any]) -> int:
    score = payload.get("score")
    score_max = payload.get("score_max")
    if not isinstance(score, (int, float)) or not isinstance(score_max, (int, float)):
        return 0
    if score_max == 0:
        return 0
    raw = int(round(score / score_max * 100))
    return int(round(raw * COMPLETENESS_WEIGHT / 100))


def _convergence_block_from_metrics(metrics: dict[str, Any] | None) -> dict[str, Any] | None:
    """Phase 6 D — when the snapshot captured a metrics file that
    inlines a convergence_summary, surface it; otherwise return None
    so the timeline conservatively scores the convergence axis at 0.

    This is intentionally lenient: the live convergence_study.json
    does not get copied into the snapshot today, so we cannot recover
    its verdict from the historical snapshot. The timeline is
    accurate when the verdict slot was captured and conservative
    when it wasn't.
    """
    if metrics is None:
        return None
    block = metrics.get("convergence_summary")
    if isinstance(block, dict):
        return block
    return None


def _convergence_weighted(block: dict[str, Any] | None) -> int:
    if not isinstance(block, dict):
        return 0
    mesh = _stability_label(block.get("mesh_sweep"))
    dt = _stability_label(block.get("dt_sweep"))
    if mesh == "candidate_observed_stable" and dt == "candidate_observed_stable":
        raw = 100
    elif (
        mesh == "candidate_observed_unstable"
        and dt == "candidate_observed_unstable"
    ):
        raw = 30
    elif "candidate_observed_stable" in (mesh, dt):
        raw = 60
    else:
        raw = 0
    return int(round(raw * CONVERGENCE_WEIGHT / 100))


def _energy_weighted(metrics: dict[str, Any] | None) -> int:
    if metrics is None:
        return 0
    block = metrics.get("energy_audit") or {}
    status = block.get("status")
    if status == "closed_aggregate":
        raw = 100
    elif status == "partial_candidate":
        raw = 60
    else:
        raw = 0
    return int(round(raw * ENERGY_AUDIT_WEIGHT / 100))


def _reproducibility_weighted(repro: dict[str, Any] | None) -> int:
    if repro is None:
        return 0
    raw = 100
    if repro.get("git_dirty") is True:
        raw -= REPRO_PENALTY_GIT_DIRTY
    if repro.get("git_commit_sha") is None:
        raw -= REPRO_PENALTY_GIT_SHA_MISSING
    not_installed = sum(
        1
        for pkg in repro.get("tracked_packages") or []
        if isinstance(pkg, dict) and pkg.get("version") == "not_installed"
    )
    raw -= not_installed * REPRO_PENALTY_PER_NOT_INSTALLED_PACKAGE
    raw = max(0, raw)
    return int(round(raw * REPRODUCIBILITY_WEIGHT / 100))


# ---------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------


def _stability_label(sweep_block: Any) -> str | None:
    if not isinstance(sweep_block, dict):
        return None
    value = sweep_block.get("candidate_stability")
    if isinstance(value, str):
        return value
    return None


def _load_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _point_to_dict(point: TimelinePoint) -> dict[str, Any]:
    return {
        "snapshot_label": point.snapshot_label,
        "captured_at_utc": point.captured_at_utc,
        "trust_score": point.trust_score,
        "completeness_weighted": point.completeness_weighted,
        "convergence_weighted": point.convergence_weighted,
        "energy_audit_weighted": point.energy_audit_weighted,
        "reproducibility_weighted": point.reproducibility_weighted,
    }


def _timeline_to_dict(timeline: TrustScoreTimeline) -> dict[str, Any]:
    return {
        "schema_version": timeline.schema_version,
        "formula_version": timeline.formula_version,
        "case_id": timeline.case_id,
        "claim_tier": timeline.claim_tier,
        "claim_boundary": timeline.claim_boundary,
        "generated_at_utc": timeline.generated_at_utc,
        "point_count": timeline.point_count,
        "points": [_point_to_dict(p) for p in timeline.points],
        "claim_impact": timeline.claim_impact,
    }


def _assert_no_overclaim(timeline: TrustScoreTimeline) -> None:
    forbidden = (
        "validated against",
        "perforation completed",
        "bullet-through-steel complete",
        "validated physics",
    )
    haystack = json.dumps(_timeline_to_dict(timeline), default=str).lower()
    for token in forbidden:
        if token in haystack:
            raise ValueError(
                f"Trust score timeline contains forbidden positive claim: {token!r}"
            )
