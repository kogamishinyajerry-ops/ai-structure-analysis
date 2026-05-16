"""Tier 1 candidate cohort anomaly detection endpoint (FM-04a Phase 8 E).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import Response

from ...services.reporting.cohort_anomalies import (
    build_cohort_anomalies,
    render_cohort_anomalies_json,
)

router = APIRouter(prefix="/cohort-anomalies", tags=["cohort-anomalies"])


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


@router.get("")
async def get_cohort_anomalies():
    report = build_cohort_anomalies(repo_root=_repo_root())
    payload = render_cohort_anomalies_json(report)
    return Response(content=payload, media_type="application/json")
