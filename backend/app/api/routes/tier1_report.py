"""Tier 1 candidate report download endpoint (FM-04a Phase 2 E).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

`GET /api/v1/tier1-report/<case-id>` streams a freshly built
`<case-id>_Tier1_candidate_report.docx` packet built from the existing
`project_state/graph_executor/<case-id>/ballistic/ballistic_metrics.json`
plus optional `convergence_study.json` and visualization artifacts.
Read-only across `golden_samples/**`; writes only to a tempfile.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from ...services.reporting.tier1_candidate_report import (
    Tier1CandidateReportInputs,
    build_tier1_candidate_report,
    render_tier1_report_docx_bytes,
    render_tier1_report_markdown,
)
from ._signed_registry_refusal import assert_not_signed_registry

router = APIRouter(prefix="/tier1-report", tags=["tier1-report"])

_CASE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _build_inputs_for(case_id: str) -> Tier1CandidateReportInputs:
    repo_root = _repo_root()
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
        repo_root
        / "docs"
        / "visualization"
        / "blueprints"
        / "bullet_plate_target_blueprint.png"
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
        repo_root
        / "project_state"
        / "visualizations"
        / case_id
        / "result_mesh.json"
    )
    return Tier1CandidateReportInputs(
        case_id=case_id,
        ballistic_metrics_path=metrics_path,
        convergence_study_path=convergence_path if convergence_path.is_file() else None,
        blueprint_image_path=blueprint_path if blueprint_path.is_file() else None,
        animation_manifest_path=(
            animation_manifest_path if animation_manifest_path.is_file() else None
        ),
        result_mesh_path=result_mesh_path if result_mesh_path.is_file() else None,
        repo_root=repo_root,
    )


@router.get("/{case_id}")
async def get_tier1_report(case_id: str, fmt: str = "docx"):
    """Build and stream a Tier 1 candidate report packet.

    `fmt=docx` (default) returns the DOCX packet; `fmt=md` returns the
    Markdown rendering as `text/markdown`.
    """
    if not _CASE_ID_RE.fullmatch(case_id):
        raise HTTPException(status_code=400, detail="invalid case_id")
    # Phase 14 A — cross-route signed-registry refusal (SSOT helper).
    assert_not_signed_registry(case_id, "tier1-report")
    if fmt not in ("docx", "md"):
        raise HTTPException(
            status_code=400, detail="fmt must be 'docx' or 'md'"
        )

    inputs = _build_inputs_for(case_id)
    if not inputs.ballistic_metrics_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="ballistic_metrics.json not found for this case",
        )

    report = build_tier1_candidate_report(inputs)

    if fmt == "md":
        markdown = render_tier1_report_markdown(report)
        return Response(
            content=markdown,
            media_type="text/markdown",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{case_id}_Tier1_candidate_report.md"'
                ),
            },
        )

    docx_bytes = render_tier1_report_docx_bytes(report)
    return Response(
        content=docx_bytes,
        media_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        headers={
            "Content-Disposition": (
                f'attachment; filename="{case_id}_Tier1_candidate_report.docx"'
            ),
        },
    )
