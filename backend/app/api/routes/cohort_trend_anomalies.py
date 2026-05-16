"""Tier 1 candidate cohort trend-slope anomaly endpoint (FM-04a Phase 9 D).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

``GET /api/v1/cohort-trend-anomalies`` returns the cohort's per-axis
trend-slope outliers. Orthogonal to the Phase 8 E z-score endpoint —
that one looks at the cohort's latest snapshot, this one looks at
each case's own timeline through time.

Read-only; no solver invocation; never touches ``golden_samples/**``.

Closes Phase 8 retrospective carry-forward §4.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import Response

from ...services.reporting.cohort_trend_anomalies import (
    build_cohort_trend_anomalies,
    render_cohort_trend_anomalies_json,
)

router = APIRouter(prefix="/cohort-trend-anomalies", tags=["cohort-trend-anomalies"])


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


@router.get("")
async def get_cohort_trend_anomalies() -> Response:
    report = build_cohort_trend_anomalies(repo_root=_repo_root())
    payload = render_cohort_trend_anomalies_json(report)
    return Response(content=payload, media_type="application/json")
