"""Tier 1 candidate evidence trust score endpoint (FM-04a Phase 6 B).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

``GET /api/v1/trust-score/<case-id>`` returns a JSON composite 0–100
trust score with a transparent per-axis breakdown. The endpoint is
read-only; it does NOT execute the case and does NOT touch
``golden_samples/**``.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from ...services.reporting.trust_score import (
    TrustScoreInputs,
    compute_trust_score,
    render_trust_score_json,
)

router = APIRouter(prefix="/trust-score", tags=["trust-score"])

_CASE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _build_inputs_for(case_id: str) -> TrustScoreInputs:
    repo_root = _repo_root()
    case_dir = repo_root / "golden_samples" / case_id
    starter_deck = case_dir / "data" / "model_00_0000.rad"
    engine_deck = case_dir / "data" / "model_00_0001.rad"
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
    animation_manifest_path = (
        repo_root
        / "project_state"
        / "graph_executor"
        / case_id
        / "visualization"
        / "openradioss_animation_manifest.json"
    )
    result_mesh_path = (
        repo_root / "project_state" / "visualizations" / case_id / "result_mesh.json"
    )

    slug = case_id.lower().replace("gs-", "gs").replace("-candidate", "").replace("-", "_")
    generator_script = repo_root / "scripts" / f"gen_{slug}_deck.py"

    return TrustScoreInputs(
        case_id=case_id,
        repo_root=repo_root,
        starter_deck_path=starter_deck,
        engine_deck_path=engine_deck,
        ballistic_metrics_path=metrics_path,
        convergence_study_path=convergence_path,
        animation_manifest_path=animation_manifest_path,
        result_mesh_path=result_mesh_path,
        generator_script_path=generator_script,
        notes_path=notes,
    )


@router.get("/{case_id}")
async def get_trust_score(case_id: str):
    """Compute the Tier 1 candidate trust score for one case."""
    if not _CASE_ID_RE.fullmatch(case_id):
        raise HTTPException(status_code=400, detail="invalid case_id")
    inputs = _build_inputs_for(case_id)
    score = compute_trust_score(inputs)
    payload = render_trust_score_json(score)
    return Response(content=payload, media_type="application/json")
