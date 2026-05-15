"""Acceptance evidence packet download endpoint (FM-04a Phase 3 A).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

`GET /api/v1/acceptance-packet/<case-id>` returns a freshly built
`<case-id>_acceptance_packet.json` payload assembled from on-disk
evidence. Read-only across `golden_samples/**`. The packet is a
Tier 1 candidate manifest; FM-04b P8 sealed bundles are NOT produced
by this endpoint.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from ...services.reporting.acceptance_packet import (
    AcceptancePacketInputs,
    build_acceptance_packet,
    render_acceptance_packet_json,
)

router = APIRouter(prefix="/acceptance-packet", tags=["acceptance-packet"])

_CASE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _build_inputs_for(case_id: str) -> AcceptancePacketInputs:
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
    starter_deck = repo_root / "project_state" / "runs" / case_id / "data" / "model_00_0000.rad"
    engine_deck = repo_root / "project_state" / "runs" / case_id / "data" / "model_00_0001.rad"
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
    return AcceptancePacketInputs(
        case_id=case_id,
        ballistic_metrics_path=metrics_path,
        convergence_study_path=convergence_path if convergence_path.is_file() else None,
        starter_deck_path=starter_deck if starter_deck.is_file() else None,
        engine_deck_path=engine_deck if engine_deck.is_file() else None,
        blueprint_image_path=blueprint_path if blueprint_path.is_file() else None,
        animation_manifest_path=(
            animation_manifest_path if animation_manifest_path.is_file() else None
        ),
        result_mesh_path=result_mesh_path if result_mesh_path.is_file() else None,
        repo_root=repo_root,
    )


@router.get("/{case_id}")
async def get_acceptance_packet(case_id: str):
    """Build and stream the Tier 1 candidate acceptance evidence packet."""
    if not _CASE_ID_RE.fullmatch(case_id):
        raise HTTPException(status_code=400, detail="invalid case_id")

    inputs = _build_inputs_for(case_id)
    if not inputs.ballistic_metrics_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="ballistic_metrics.json not found for this case",
        )

    packet = build_acceptance_packet(inputs)
    payload = render_acceptance_packet_json(packet)
    return Response(
        content=payload,
        media_type="application/json",
        headers={
            "Content-Disposition": (f'attachment; filename="{case_id}_acceptance_packet.json"'),
        },
    )


# Tests need a programmatic accessor that does not return a FastAPI Response.
def _build_packet_dict(case_id: str) -> dict:
    if not _CASE_ID_RE.fullmatch(case_id):
        raise ValueError("invalid case_id")
    inputs = _build_inputs_for(case_id)
    packet = build_acceptance_packet(inputs)
    return json.loads(render_acceptance_packet_json(packet))
