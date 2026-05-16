"""Tier 1 candidate signoff history endpoint (FM-04a Phase 8 B).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

``GET /api/v1/signoff-history/<case-id>`` returns the chronological
list of reviewer signoff records persisted by Phase 8 A. Read-only;
no solver invocation; never touches ``golden_samples/**``.

Closes Phase 7 retrospective's "reviewer judgments have nowhere to
land" gap.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from ...services.reporting.signoff_record import (
    build_signoff_history_report,
    render_signoff_history_json,
)

router = APIRouter(prefix="/signoff-history", tags=["signoff-history"])

_CASE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


@router.get("/{case_id}")
async def get_signoff_history(case_id: str):
    if not _CASE_ID_RE.fullmatch(case_id):
        raise HTTPException(status_code=400, detail="invalid case_id")
    try:
        report = build_signoff_history_report(case_id, repo_root=_repo_root())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    payload = render_signoff_history_json(report)
    return Response(content=payload, media_type="application/json")
