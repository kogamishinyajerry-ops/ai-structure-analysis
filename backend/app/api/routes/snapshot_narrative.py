"""Tier 1 candidate snapshot narrative endpoint (FM-04a Phase 6 C).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

``GET /api/v1/snapshot-narrative?a=<utc>&b=<utc>`` composes a snapshot
diff (Phase 5 D + 6 A) and returns it as a list of templated drift
sentences. Read-only; no solver invocation; never touches
``golden_samples/**``.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from ...services.reporting.cohort_snapshot import SNAPSHOT_LABEL_RE
from ...services.reporting.cohort_snapshot_diff import diff_cohort_snapshots
from ...services.reporting.snapshot_narrative import (
    build_snapshot_narrative,
    render_snapshot_narrative_json,
)

router = APIRouter(prefix="/snapshot-narrative", tags=["snapshot-narrative"])


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


@router.get("")
async def get_snapshot_narrative(
    a: str = Query(..., description="snapshot label A (YYYY-MM-DDTHHMMSSZ)"),
    b: str = Query(..., description="snapshot label B (YYYY-MM-DDTHHMMSSZ)"),
):
    """Compose templated drift narrative between two snapshots."""
    for label, name in ((a, "a"), (b, "b")):
        if not SNAPSHOT_LABEL_RE.fullmatch(label):
            raise HTTPException(
                status_code=400, detail=f"invalid snapshot label for {name!r}"
            )
    try:
        diff = diff_cohort_snapshots(_repo_root(), a, b)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    narrative = build_snapshot_narrative(diff)
    payload = render_snapshot_narrative_json(narrative)
    return Response(content=payload, media_type="application/json")
