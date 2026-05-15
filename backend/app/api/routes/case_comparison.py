"""Case comparison endpoint (FM-04a Phase 3 B).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

``GET /api/v1/case-comparison?a=<case-id>&b=<case-id>`` builds two
acceptance packets from on-disk evidence and returns a structured
side-by-side diff. Read-only across ``golden_samples/**``. Both
inputs are Tier 1 candidate packets; the diff is NEVER a comparison
against experimental benchmark data.
"""

from __future__ import annotations

import json
import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from ...services.reporting.acceptance_packet import build_acceptance_packet
from ...services.reporting.case_comparison import (
    build_case_comparison,
    render_case_comparison_json,
)
from .acceptance_packet import _build_inputs_for

router = APIRouter(prefix="/case-comparison", tags=["case-comparison"])

_CASE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


@router.get("")
async def get_case_comparison(a: str, b: str):
    """Build and stream the Tier 1 candidate case-vs-case comparison."""
    for label, case_id in (("a", a), ("b", b)):
        if not _CASE_ID_RE.fullmatch(case_id):
            raise HTTPException(status_code=400, detail=f"invalid case_id for {label!r}")

    inputs_a = _build_inputs_for(a)
    inputs_b = _build_inputs_for(b)
    if not inputs_a.ballistic_metrics_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"ballistic_metrics.json not found for case {a!r}",
        )
    if not inputs_b.ballistic_metrics_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"ballistic_metrics.json not found for case {b!r}",
        )

    packet_a = build_acceptance_packet(inputs_a)
    packet_b = build_acceptance_packet(inputs_b)
    comparison = build_case_comparison(packet_a, packet_b)
    payload = render_case_comparison_json(comparison)
    return Response(content=payload, media_type="application/json")


def _build_comparison_dict(case_a: str, case_b: str) -> dict:
    """Programmatic accessor used by tests."""
    for label, case_id in (("a", case_a), ("b", case_b)):
        if not _CASE_ID_RE.fullmatch(case_id):
            raise ValueError(f"invalid case_id for {label!r}")
    inputs_a = _build_inputs_for(case_a)
    inputs_b = _build_inputs_for(case_b)
    packet_a = build_acceptance_packet(inputs_a)
    packet_b = build_acceptance_packet(inputs_b)
    comparison = build_case_comparison(packet_a, packet_b)
    return json.loads(render_case_comparison_json(comparison))
