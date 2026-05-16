"""Tier 1 candidate signoff history endpoint (FM-04a Phase 8 B + Phase 9 A).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

``GET /api/v1/signoff-history/<case-id>`` returns the chronological
list of reviewer signoff records persisted by Phase 8 A. Read-only;
no solver invocation; never touches ``golden_samples/**``.

``POST /api/v1/signoff-history/<case-id>`` writes a new reviewer
signoff record via the existing :func:`write_signoff_record` service
API. The HTTP layer enforces the same verdict whitelist + notes-claim
audit as the Python API but surfaces every refusal as **HTTP 422** so
client code can branch on the failure mode (separate from server
errors). The signed-registry case_id pattern (``^GS-\\d{3}$``) is also
refused at request validation time. Non-JSON request bodies are
refused with **HTTP 415** before any body parsing happens.

Closes Phase 7 retrospective's "reviewer judgments have nowhere to
land" gap and Phase 8 carry-forward §1 ("no POST endpoint for
write_signoff_record").
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field, ValidationError

from ...services.reporting.signoff_record import (
    SUPPORTED_SIGNOFF_VERDICTS,
    build_signoff_history_report,
    render_signoff_history_json,
    write_signoff_record,
)

router = APIRouter(prefix="/signoff-history", tags=["signoff-history"])

_CASE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_SIGNED_REGISTRY_RE = re.compile(r"^GS-\d{3}$")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


class SignoffWriteRequest(BaseModel):
    """Request body for the POST endpoint.

    All three fields are required. Empty / whitespace-only ``reviewer``
    is rejected by the service layer; empty ``verdict`` is rejected by
    the whitelist check.
    """

    reviewer: str = Field(..., min_length=1)
    verdict: str = Field(..., min_length=1)
    notes: str = Field(..., min_length=0)


@router.get("/{case_id}")
async def get_signoff_history(case_id: str) -> Response:
    if not _CASE_ID_RE.fullmatch(case_id):
        raise HTTPException(status_code=400, detail="invalid case_id")
    try:
        report = build_signoff_history_report(case_id, repo_root=_repo_root())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    payload = render_signoff_history_json(report)
    return Response(content=payload, media_type="application/json")


@router.post("/{case_id}")
async def post_signoff_history(case_id: str, request: Request) -> JSONResponse:
    """Write a new signoff record for ``case_id`` via the existing service API.

    Order of validation gates (each fails fast with a distinct status):

    1. **415** if ``Content-Type`` is not ``application/json`` (case +
       parameter tolerant).
    2. **422** if ``case_id`` does not match the candidate id regex.
    3. **422** if ``case_id`` matches the signed-registry pattern
       ``^GS-\\d{3}$`` (defense in depth — the service layer refuses
       it again).
    4. **422** if the request body is not valid JSON or is missing
       required fields.
    5. **422** if the verdict is not in
       :data:`SUPPORTED_SIGNOFF_VERDICTS` (Phase 9 anti-gaming guard
       C: -10 — the load-bearing whitelist refusal happens at the
       request-validation boundary).
    6. **422** if the notes contain a forbidden positive claim outside
       ``not <claim>`` form (Phase 9 anti-gaming guard C: -8).
    7. **200** + the new record JSON on success.
    """
    # 1. Content-Type gate (must run before body parsing).
    content_type = (request.headers.get("content-type") or "").split(";", 1)[0].strip().lower()
    if content_type != "application/json":
        raise HTTPException(
            status_code=415,
            detail="signoff POST requires Content-Type: application/json",
        )

    # 2 + 3. Case id gates (refuse before reading body).
    if not _CASE_ID_RE.fullmatch(case_id):
        raise HTTPException(status_code=422, detail="invalid case_id")
    if _SIGNED_REGISTRY_RE.fullmatch(case_id):
        raise HTTPException(
            status_code=422,
            detail=(
                "signoff POST refuses signed-registry case_id; "
                "Tier 1 candidate signoffs only accept *-candidate identifiers"
            ),
        )

    # 4. Body parse + Pydantic validation.
    try:
        raw_body = await request.json()
    except Exception as exc:  # noqa: BLE001 - covers JSONDecodeError + decode errors
        raise HTTPException(
            status_code=422,
            detail=f"signoff POST body is not valid JSON: {exc}",
        ) from exc
    try:
        body = SignoffWriteRequest.model_validate(raw_body)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    # 5. Verdict whitelist (HTTP-side mirror of the service-layer audit;
    #    the service layer also enforces, so this is defense in depth).
    if body.verdict not in SUPPORTED_SIGNOFF_VERDICTS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"signoff verdict {body.verdict!r} is not in the whitelist "
                f"{SUPPORTED_SIGNOFF_VERDICTS!r}"
            ),
        )

    # 6 + 7. Hand off to the service layer; any remaining ValueError
    #         (notes-claim audit, empty reviewer after strip, signed
    #         registry, golden_samples path containment) maps to 422.
    try:
        record = write_signoff_record(
            case_id,
            body.reviewer,
            body.verdict,
            body.notes,
            repo_root=_repo_root(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    payload: dict[str, Any] = {
        "schema_version": record.schema_version,
        "case_id": record.case_id,
        "reviewer": record.reviewer,
        "verdict": record.verdict,
        "signoff_utc": record.signoff_utc,
        "notes": record.notes,
        "claim_tier": record.claim_tier,
        "claim_boundary": record.claim_boundary,
        "claim_impact": record.claim_impact,
    }
    return JSONResponse(status_code=200, content=payload)
