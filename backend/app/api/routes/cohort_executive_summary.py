"""Tier 1 candidate cohort executive summary endpoint (FM-04a Phase 8 D).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import Response

from ...services.reporting.cohort_executive_summary import (
    build_cohort_executive_summary,
    render_cohort_executive_summary_json,
)

router = APIRouter(
    prefix="/cohort-executive-summary", tags=["cohort-executive-summary"]
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


@router.get("")
async def get_cohort_executive_summary():
    summary = build_cohort_executive_summary(repo_root=_repo_root())
    payload = render_cohort_executive_summary_json(summary)
    return Response(content=payload, media_type="application/json")
