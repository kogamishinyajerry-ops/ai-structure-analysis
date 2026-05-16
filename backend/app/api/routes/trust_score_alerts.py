"""Tier 1 candidate trust score regression alarms endpoint (FM-04a Phase 7 C).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

``GET /api/v1/trust-score-alerts/<case-id>?threshold_delta=N`` walks
a case's trust-score timeline and surfaces regression events whose
magnitude exceeds the (clamped) threshold. Read-only; no solver
invocation; never touches ``golden_samples/**``.

Closes Phase 6 retrospective carry-forward §4.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from ...services.reporting.trust_score_alerts import (
    THRESHOLD_DELTA_DEFAULT,
    THRESHOLD_DELTA_MAX,
    THRESHOLD_DELTA_MIN,
    build_trust_score_alerts,
    render_trust_score_alerts_json,
)

router = APIRouter(prefix="/trust-score-alerts", tags=["trust-score-alerts"])

_CASE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


@router.get("/{case_id}")
async def get_trust_score_alerts(
    case_id: str,
    threshold_delta: int = Query(
        THRESHOLD_DELTA_DEFAULT,
        ge=THRESHOLD_DELTA_MIN,
        le=THRESHOLD_DELTA_MAX,
        description=(
            "Minimum trust-score drop (older - newer) to emit as an "
            f"alarm. Clamped server-side to [{THRESHOLD_DELTA_MIN}, "
            f"{THRESHOLD_DELTA_MAX}]."
        ),
    ),
):
    if not _CASE_ID_RE.fullmatch(case_id):
        raise HTTPException(status_code=400, detail="invalid case_id")
    report = build_trust_score_alerts(
        case_id, _repo_root(), threshold_delta=threshold_delta
    )
    payload = render_trust_score_alerts_json(report)
    return Response(content=payload, media_type="application/json")
