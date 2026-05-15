"""Tier 1 candidate evidence completeness endpoint (FM-04a Phase 4 A).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

``GET /api/v1/case-completeness/<case-id>`` reads the case's evidence
inventory off disk and returns a structured completeness score.
Read-only; never writes inside ``golden_samples/**``. The score is an
evidence-presence signal, NOT a validation-quality signal: even
100/100 keeps every FM-04b blocker visible in the rendered output.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from ...services.reporting.case_completeness import (
    CaseCompletenessInputs,
    render_case_completeness_json,
    score_case_completeness,
)

router = APIRouter(prefix="/case-completeness", tags=["case-completeness"])

_CASE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _build_inputs_for(case_id: str) -> CaseCompletenessInputs:
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
    result_mesh_path = repo_root / "project_state" / "visualizations" / case_id / "result_mesh.json"

    # Generator script lives in scripts/gen_<slug>_deck.py.
    slug = case_id.lower().replace("gs-", "gs").replace("-candidate", "").replace("-", "_")
    generator_script = repo_root / "scripts" / f"gen_{slug}_deck.py"

    return CaseCompletenessInputs(
        case_id=case_id,
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
async def get_case_completeness(case_id: str):
    """Score one Tier 1 candidate case's evidence completeness."""
    if not _CASE_ID_RE.fullmatch(case_id):
        raise HTTPException(status_code=400, detail="invalid case_id")
    inputs = _build_inputs_for(case_id)
    score = score_case_completeness(inputs)
    payload = render_case_completeness_json(score)
    return Response(content=payload, media_type="application/json")
