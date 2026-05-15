"""Tier 1 archived acceptance packet diff endpoint (FM-04a Phase 4 D).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

``GET /api/v1/archived-packet-diff?a=<relpath>&b=<relpath>`` reads
two archived ``<case>_acceptance_packet.json`` files (relative paths,
both anchored under ``reports/``) and returns a structured diff plus
per-side provenance metadata. Read-only; refuses any path that
escapes ``reports/`` or lands inside ``golden_samples/**``.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from ...services.reporting.archived_packet_diff import (
    diff_archived_packets,
    render_archived_packet_diff_json,
)

router = APIRouter(prefix="/archived-packet-diff", tags=["archived-packet-diff"])


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _resolve_archive_path(repo_root: Path, relpath: str) -> Path:
    """Resolve a user-supplied relpath under reports/ with strict anchoring."""
    if not relpath:
        raise ValueError("relpath is empty")
    # Normalize the supplied path: forbid absolute paths and any
    # component that would escape the reports/ anchor.
    candidate = (repo_root / "reports" / relpath).resolve()
    reports_root = (repo_root / "reports").resolve()
    try:
        candidate.relative_to(reports_root)
    except ValueError as exc:
        raise ValueError("archive path must resolve inside reports/") from exc
    # Belt and suspenders: never accept a path that traverses into
    # golden_samples/ via reports/.
    for parent in (candidate, *candidate.parents):
        if parent.name == "golden_samples":
            raise ValueError("archive path may not lie under golden_samples/**")
    return candidate


@router.get("")
async def get_archived_packet_diff(a: str, b: str):
    """Diff two archived Tier 1 acceptance packet JSON files under reports/."""
    repo_root = _repo_root()
    try:
        path_a = _resolve_archive_path(repo_root, a)
        path_b = _resolve_archive_path(repo_root, b)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not path_a.is_file():
        raise HTTPException(status_code=404, detail=f"archive a not found: {a}")
    if not path_b.is_file():
        raise HTTPException(status_code=404, detail=f"archive b not found: {b}")

    try:
        diff = diff_archived_packets(path_a, path_b, repo_root=repo_root)
    except ValueError as exc:
        # Boundary or schema rejection from the builder maps to 400.
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    payload = render_archived_packet_diff_json(diff)
    return Response(content=payload, media_type="application/json")
