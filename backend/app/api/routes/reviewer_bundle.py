"""Tier 1 reviewer bundle endpoint (FM-04a Phase 4 C).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

``GET /api/v1/reviewer-bundle?ids=<csv>`` streams an in-memory zip
containing the Tier 1 candidate manifest, convergence study, Tier 1
markdown report, and completeness scorecard for each requested case
plus a top-level ``BUNDLE_MANIFEST.json``. Read-only; never writes
inside ``golden_samples/**``. The bundle is a Tier 1 reviewer hand-off,
NOT a sealed FM-04b P8 packet.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from ...services.reporting.reviewer_bundle import (
    ReviewerBundleInputs,
    build_reviewer_bundle,
    reviewer_bundle_filename,
)

router = APIRouter(prefix="/reviewer-bundle", tags=["reviewer-bundle"])

_CASE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_MAX_BUNDLE_CASES = 32


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _build_inputs_for(case_id: str) -> ReviewerBundleInputs:
    repo_root = _repo_root()
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
    blueprint_path = (
        repo_root / "docs" / "visualization" / "blueprints" / "bullet_plate_target_blueprint.png"
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
    slug = case_id.lower().replace("gs-", "gs").replace("-candidate", "").replace("-", "_")
    generator_script = repo_root / "scripts" / f"gen_{slug}_deck.py"

    return ReviewerBundleInputs(
        case_id=case_id,
        starter_deck_path=starter if starter.is_file() else None,
        engine_deck_path=engine if engine.is_file() else None,
        ballistic_metrics_path=metrics_path,
        convergence_study_path=convergence_path if convergence_path.is_file() else None,
        animation_manifest_path=(
            animation_manifest_path if animation_manifest_path.is_file() else None
        ),
        result_mesh_path=result_mesh_path if result_mesh_path.is_file() else None,
        blueprint_image_path=blueprint_path if blueprint_path.is_file() else None,
        generator_script_path=generator_script if generator_script.is_file() else None,
        notes_path=notes if notes.is_file() else None,
    )


@router.get("")
async def get_reviewer_bundle(ids: str = Query(..., min_length=1)):
    """Build and stream the Tier 1 reviewer bundle for `ids` (CSV)."""
    case_ids = [token.strip() for token in ids.split(",") if token.strip()]
    if not case_ids:
        raise HTTPException(status_code=400, detail="ids must include at least one case_id")
    if len(case_ids) > _MAX_BUNDLE_CASES:
        raise HTTPException(status_code=400, detail=f"bundle limit is {_MAX_BUNDLE_CASES} cases")
    for case_id in case_ids:
        if not _CASE_ID_RE.fullmatch(case_id):
            raise HTTPException(status_code=400, detail=f"invalid case_id {case_id!r}")

    inputs: list[ReviewerBundleInputs] = []
    for case_id in case_ids:
        per_case = _build_inputs_for(case_id)
        if per_case.ballistic_metrics_path is None or not per_case.ballistic_metrics_path.is_file():
            raise HTTPException(
                status_code=404,
                detail=f"ballistic_metrics.json not found for case {case_id!r}",
            )
        inputs.append(per_case)

    zip_bytes = build_reviewer_bundle(inputs, repo_root=_repo_root())
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{reviewer_bundle_filename(len(case_ids))}"'
            ),
        },
    )
