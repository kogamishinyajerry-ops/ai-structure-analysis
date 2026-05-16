"""Tier 1 candidate trust score provenance trace endpoint (FM-04a Phase 8 C).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

``GET /api/v1/trust-score-provenance/<case-id>?snapshot=<label>``
returns the per-input SHA list + formula version + recomputed score
for one (case, snapshot) pair. Read-only; no solver invocation;
never touches ``golden_samples/**``.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from ...services.reporting.cohort_snapshot import SNAPSHOT_LABEL_RE
from ...services.reporting.trust_score_provenance import (
    ProvenanceSnapshotNotFound,
    build_trust_score_provenance,
    render_trust_score_provenance_json,
)
from ._signed_registry_refusal import assert_not_signed_registry

router = APIRouter(
    prefix="/trust-score-provenance", tags=["trust-score-provenance"]
)

_CASE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


@router.get("/{case_id}")
async def get_trust_score_provenance(
    case_id: str,
    snapshot: str = Query(..., description="Snapshot label (UTC compact ISO 8601)."),
):
    if not _CASE_ID_RE.fullmatch(case_id):
        raise HTTPException(status_code=400, detail="invalid case_id")
    # Phase 14 A — cross-route signed-registry refusal (SSOT helper).
    assert_not_signed_registry(case_id, "trust-score-provenance")
    if not SNAPSHOT_LABEL_RE.fullmatch(snapshot):
        raise HTTPException(status_code=400, detail="invalid snapshot label shape")
    try:
        report = build_trust_score_provenance(
            case_id, snapshot, repo_root=_repo_root()
        )
    except ProvenanceSnapshotNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    payload = render_trust_score_provenance_json(report)
    return Response(content=payload, media_type="application/json")
