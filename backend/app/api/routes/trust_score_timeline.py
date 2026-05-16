"""Tier 1 candidate trust score timeline endpoint (FM-04a Phase 6 D).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

``GET /api/v1/trust-score-timeline/<case-id>`` walks every cohort
snapshot under ``reports/snapshots/<*>/`` that contains the case and
returns a per-snapshot trust score recomputed from the captured
evidence (oldest-first). Read-only; never touches ``golden_samples/**``.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from ...services.reporting.trust_score_timeline import (
    build_trust_score_timeline,
    render_trust_score_timeline_json,
)

router = APIRouter(prefix="/trust-score-timeline", tags=["trust-score-timeline"])

_CASE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


@router.get("/{case_id}")
async def get_trust_score_timeline(case_id: str):
    """Return the Tier 1 trust score timeline for one case."""
    if not _CASE_ID_RE.fullmatch(case_id):
        raise HTTPException(status_code=400, detail="invalid case_id")
    timeline = build_trust_score_timeline(case_id, _repo_root())
    payload = render_trust_score_timeline_json(timeline)
    return Response(content=payload, media_type="application/json")
