"""Tier 1 candidate cohort snapshot diff endpoint (FM-04a Phase 5 D).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

``GET /api/v1/cohort-snapshot-diff?a=<utc>&b=<utc>`` returns the
reviewer-visible diff between two cohort snapshots previously written
by Phase 5 C's CLI. The diff surfaces cohort membership changes and
per-case completeness / reproducibility drift.

The endpoint does NOT execute cases and does NOT touch
``golden_samples/**``. Both snapshot labels are validated against the
canonical ``YYYY-MM-DDTHHMMSSZ`` regex before any disk access.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from ...services.reporting.cohort_snapshot import SNAPSHOT_LABEL_RE
from ...services.reporting.cohort_snapshot_diff import (
    diff_cohort_snapshots,
    render_cohort_snapshot_diff_json,
)

router = APIRouter(prefix="/cohort-snapshot-diff", tags=["cohort-snapshot-diff"])


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


@router.get("")
async def get_cohort_snapshot_diff(
    a: str = Query(..., description="snapshot label A (YYYY-MM-DDTHHMMSSZ)"),
    b: str = Query(..., description="snapshot label B (YYYY-MM-DDTHHMMSSZ)"),
):
    """Diff two cohort snapshots already written under
    ``reports/snapshots/<UTC>/``."""
    for label, name in ((a, "a"), (b, "b")):
        if not SNAPSHOT_LABEL_RE.fullmatch(label):
            raise HTTPException(
                status_code=400, detail=f"invalid snapshot label for {name!r}"
            )
    try:
        diff = diff_cohort_snapshots(_repo_root(), a, b)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    payload = render_cohort_snapshot_diff_json(diff)
    return Response(content=payload, media_type="application/json")
