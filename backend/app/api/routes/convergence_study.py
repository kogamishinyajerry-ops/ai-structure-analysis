"""Convergence study sidecar endpoint (FM-04a Phase 3 D).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

``GET /api/v1/convergence-study/<case-id>`` streams the on-disk
`project_state/graph_executor/<case-id>/convergence/convergence_study.json`
sidecar for the Workbench convergence viewer. Read-only across
``golden_samples/**``; rejects path traversal via the same
``^[A-Za-z0-9_-]{1,64}$`` shape the Phase 2 C / 3 A / 3 B endpoints use.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

router = APIRouter(prefix="/convergence-study", tags=["convergence-study"])

_CASE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _resolve_convergence_path(case_id: str) -> Path:
    repo_root = _repo_root()
    return (
        repo_root
        / "project_state"
        / "graph_executor"
        / case_id
        / "convergence"
        / "convergence_study.json"
    )


@router.get("/{case_id}")
async def get_convergence_study(case_id: str):
    """Stream the Tier 1 candidate convergence_study.json sidecar."""
    if not _CASE_ID_RE.fullmatch(case_id):
        raise HTTPException(status_code=400, detail="invalid case_id")
    path = _resolve_convergence_path(case_id)
    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail="convergence_study.json not found for this case",
        )
    payload = path.read_text(encoding="utf-8")
    return Response(content=payload, media_type="application/json")
