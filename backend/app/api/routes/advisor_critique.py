"""Tier 1 candidate AI advisor critique endpoint (FM-04a Phase 11 D).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

``GET /api/v1/advisor-critique/<case_id>?snapshot=<label>`` returns an
:class:`AdvisorCritique` payload for one (case, snapshot) pair. The
endpoint is read-only; never writes inside ``golden_samples/**`` /
``project_state/**`` / ``reports/**``; never proxies a real LLM call
in the default configuration (Phase 11 C ships the env-var seam only).

Status posture (blueprint section 3.D):
  * **200** with ``advisor_status`` in ``{"online", "offline", "stub"}``
    is the happy path. The stub is the load-bearing fallback; the
    endpoint MUST NOT 5xx for an LLM outage.
  * **422** for invalid ``case_id`` shape, signed-registry case_id
    (``^GS-\\d{3}$``), invalid snapshot label shape, or missing
    ``snapshot`` query parameter (FastAPI surfaces the latter as 422
    automatically when ``Query(...)`` is required).
  * **404** when the snapshot dir or per-case metrics file is absent.
  * **422** when the advisor's envelope-level audit refuses the
    critique (forbidden positive claim from a live LLM, or a False
    answer on the four-question gate). The detail echoes the
    underlying ``ValueError`` so the reviewer panel can surface a
    diagnostic without needing server logs.

The HTTP layer is intentionally thin: it validates inputs, calls
:func:`build_advisor_context_from_snapshot`, then
:func:`build_advisor_critique`, then renders the JSON. The audit logic
lives in the service module.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from ...services.reporting.advisor_critique import (
    AdvisorSnapshotNotFound,
    _default_llm_factory,
    build_advisor_context_from_snapshot,
    build_advisor_critique,
    render_advisor_critique_json,
)
from ...services.reporting.cohort_snapshot import SNAPSHOT_LABEL_RE
from ._signed_registry_refusal import assert_not_signed_registry

router = APIRouter(prefix="/advisor-critique", tags=["advisor-critique"])

_CASE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


@router.get("/{case_id}")
async def get_advisor_critique(
    case_id: str,
    snapshot: str = Query(
        ...,
        description=(
            "Snapshot label (UTC compact ISO 8601, e.g. 2026-05-16T120000Z)."
        ),
    ),
) -> Response:
    """Build the Tier 1 candidate advisor critique for one (case, snapshot) pair.

    Validation gate order (each step short-circuits with a distinct status):

    1. **422** if ``case_id`` does not match the candidate id regex.
    2. **422** if ``case_id`` matches the signed-registry pattern
       ``^GS-\\d{3}$``. Tier 1 candidate advisor surface only accepts
       ``*-candidate`` identifiers; signed-registry case ids belong
       to FM-04b sealed packets and are out of scope for this
       endpoint.
    3. **422** if ``snapshot`` does not match the snapshot label shape.
    4. **404** if the snapshot dir is absent OR the snapshot exists
       but has no per-case metrics file for ``case_id``.
    5. **422** if the advisor's envelope-level audit refuses the
       critique (forbidden positive claim from a live LLM response,
       or a False answer on the four-question gate). The audit
       failure is the load-bearing posture statement; we surface 422
       rather than silently scrub.
    6. **200** with the rendered :class:`AdvisorCritique` JSON on
       success. ``advisor_status`` is one of ``online`` / ``offline``
       / ``stub``; ``degrade_reason`` is populated when the live LLM
       had to fall back to the stub.
    """
    # 1. Case id shape gate.
    if not _CASE_ID_RE.fullmatch(case_id):
        raise HTTPException(status_code=422, detail="invalid case_id")

    # 2. Signed-registry refusal via the cross-route SSOT helper
    #    (Phase 14 A). Vocabulary harmonized; the legacy detail
    #    "advisor-critique refuses signed-registry case_id; Tier 1
    #    candidate advisor surface only accepts *-candidate
    #    identifiers (sealed FM-04b packets are out of scope)" is
    #    superseded by the SSOT helper output, which carries the same
    #    three canonical tokens (``signed-registry`` / ``candidate`` /
    #    ``out of scope``) audited by every Phase 11+ test.
    assert_not_signed_registry(case_id, "advisor-critique")

    # 3. Snapshot label shape gate.
    if not SNAPSHOT_LABEL_RE.fullmatch(snapshot):
        raise HTTPException(
            status_code=422,
            detail="invalid snapshot label shape",
        )

    # 4. Build the advisor context from frozen snapshot bytes.
    try:
        context = build_advisor_context_from_snapshot(
            case_id, snapshot, repo_root=_repo_root()
        )
    except AdvisorSnapshotNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        # Should not fire in practice — the shape gates above catch
        # the same conditions. Surfaced as 422 for defense in depth.
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # 5. Build the critique envelope. The default provider is
    #    LLMAdvisor (env-var-gated; falls back to None when unwired);
    #    when provider is None the StubAdvisor is used at status="stub".
    #    Audit failures (forbidden claim from LLM / False 4-Q gate
    #    answer) surface as 422.
    provider = _default_llm_factory()
    try:
        critique = build_advisor_critique(context, provider=provider)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"advisor critique audit refused: {exc}",
        ) from exc

    payload = render_advisor_critique_json(critique)
    return Response(content=payload, media_type="application/json")
