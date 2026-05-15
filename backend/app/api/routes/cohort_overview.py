"""Tier 1 candidate cohort overview endpoint (FM-04a Phase 4 B).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

``GET /api/v1/cohort-overview`` enumerates every
``golden_samples/*-candidate/`` directory and returns a scored
overview (one entry per case + cohort aggregates). Read-only;
strictly filters out any ``^GS-\\d{3}$`` signed-registry shape.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import Response

from ...services.reporting.cohort_overview import (
    build_cohort_overview,
    render_cohort_overview_json,
)

router = APIRouter(prefix="/cohort-overview", tags=["cohort-overview"])


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


@router.get("")
async def get_cohort_overview():
    """Return the Tier 1 candidate cohort overview."""
    overview = build_cohort_overview(_repo_root())
    return Response(content=render_cohort_overview_json(overview), media_type="application/json")
