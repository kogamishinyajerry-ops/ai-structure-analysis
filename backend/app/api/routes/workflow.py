"""Agentic FEA Workflow Runtime — M1 read/trigger API.

Drives the Mock pipeline (synthetic solver data, real StageState events) so the
Monitor UI can watch the 13-stage flow run. Endpoints:

* ``POST /api/v1/workflow/trigger``      — start a mock run (``?sync=true`` runs
  it to completion synchronously for tests); returns the run.
* ``GET  /api/v1/workflow/runs/{run_id}``— current snapshot of all 13 stages.
* ``GET  /api/v1/workflow/runs``         — recent runs.
* ``GET  /api/v1/workflow/stages``       — the static 13-stage catalog (lets the
  Monitor draw the node graph before a run starts).

At M2 the same surface is fronted by Trigger.dev; at M4 the Mock backend swaps
for the real CalculiX backend with no contract change.
"""

from __future__ import annotations

import hmac
import logging
from typing import Literal
from urllib.parse import urlparse

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from schemas.workflow_state import (
    CANONICAL_STAGE_ORDER,
    WorkflowStage,
    ws_stage_for,
)

from ...core.config import settings
from ...services.workflow.mock_pipeline import STAGE_SPECS, StageOrderError, store

router = APIRouter(prefix="/workflow", tags=["workflow-runtime"])

# Callback hosts the stage runner is allowed to POST results to (SSRF guard):
# the configured Trigger.dev API host + loopback (fake-orchestrator / self-host).
_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


class WorkflowTriggerRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")

    label: str | None = None
    # ADR-028 P1: the genuine natural-language analysis intent, DISTINCT from the
    # display `label` (the Monitor client defaults that to "monitor"). Only a real
    # request drives the PROJECT_INTAKE agent node; absent it, intake stays
    # scripted_demo (no false provenance=deterministic_agent claim).
    user_request: str | None = None
    fail_at_stage: WorkflowStage | None = None
    # M2: 'self' = M1 behaviour (FastAPI advances all stages). 'external' = a
    # Trigger.dev orchestrator will drive each stage via POST /stage/run.
    trigger_mode: Literal["self", "external"] = "self"


@router.post("/trigger")
async def trigger_workflow(req: WorkflowTriggerRequest | None = None, sync: bool = False) -> dict:
    """Start a mock pipeline run.

    * ``triggerMode='self'`` (default, M1): FastAPI advances the pipeline —
      ``sync=true`` runs to completion (tests); otherwise it advances in the
      background and the caller polls ``GET /runs/{run_id}``.
    * ``triggerMode='external'`` (M2): create a PENDING run only; a Trigger.dev
      orchestrator drives each stage via ``POST /stage/run``. The response
      carries ``orchRunId`` (the run id to subscribe) and ``publicAccessToken``
      (always null here — only the Node ``trigger/`` layer can mint a real
      Trigger.dev token; the Monitor falls back to polling ``GET /runs/{id}``).
    """
    req = req or WorkflowTriggerRequest()
    if req.trigger_mode == "external":
        run = store.create_run(
            label=req.label, fail_at_stage=req.fail_at_stage, user_request=req.user_request
        )
        payload = run.model_dump(by_alias=True)
        payload["orchRunId"] = run.run_id
        payload["publicAccessToken"] = None
        return payload
    if sync:
        run = store.run_sync(
            label=req.label, fail_at_stage=req.fail_at_stage, user_request=req.user_request
        )
    else:
        run = store.trigger(
            label=req.label, fail_at_stage=req.fail_at_stage, user_request=req.user_request
        )
    return run.model_dump(by_alias=True)


class StageRunRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")

    run_id: str
    stage: WorkflowStage
    fail: bool = False
    callback_url: str | None = None


def _require_internal(token: str | None) -> None:
    """Authenticate a server-to-server POST /stage/run call.

    Secure-by-default: the endpoint is DISABLED (503) until
    ``TRIGGER_INTERNAL_SECRET`` is configured, and then requires a matching
    ``X-Internal-Token`` header. It is never browser-callable (the Monitor uses
    /trigger + /runs only)."""
    secret = settings.trigger_internal_secret
    if not secret:
        raise HTTPException(
            status_code=503,
            detail="POST /workflow/stage/run is disabled until TRIGGER_INTERNAL_SECRET is set",
        )
    # Constant-time compare for a shared bearer secret (Codex M2 R0 P3).
    if not hmac.compare_digest(token or "", secret):
        raise HTTPException(status_code=401, detail="invalid or missing X-Internal-Token")


def _effective_port(parsed) -> int:
    """The URL's port, defaulting to the scheme's standard port."""
    if parsed.port is not None:
        return parsed.port
    return 443 if parsed.scheme == "https" else 80


def _validate_callback_host(callback_url: str) -> None:
    """SSRF guard (Codex M2 R0 P1 / R1). Only allow POSTing stage results to:

    * the configured Trigger.dev origin — pinned on scheme + host + port (not
      just host), so ``https://<host>:<arbitrary-port>/`` cannot be reached; and
    * loopback (any port) — but ONLY when ``trigger_allow_loopback_callback`` is
      set (local fake-orchestrator / self-host). Off by default so a token
      holder cannot steer the backend at arbitrary internal services.

    The scheme is restricted to http/https so non-HTTP SSRF vectors
    (file://, gopher://, …) are rejected regardless of host."""
    parsed = urlparse(callback_url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=400, detail=f"callbackUrl scheme {parsed.scheme!r} not allowed"
        )
    # A malformed port (e.g. ':abc', ':99999') makes urlparse raise on .port —
    # surface a clean 400 rather than a 500 (Codex M2 R2 P3).
    try:
        parsed.port
    except ValueError:
        raise HTTPException(status_code=400, detail="callbackUrl has an invalid port")
    host = (parsed.hostname or "").lower()
    # Loopback: dev/self-host only, any port (ephemeral wait-token capture).
    if host in _LOOPBACK_HOSTS:
        if settings.trigger_allow_loopback_callback:
            return
        raise HTTPException(status_code=400, detail=f"callbackUrl host {host!r} not allowed")
    # Production: pin the FULL Trigger.dev origin (scheme + host + port).
    trigger = urlparse(settings.trigger_api_base)
    if (
        parsed.scheme == trigger.scheme
        and host == (trigger.hostname or "").lower()
        and _effective_port(parsed) == _effective_port(trigger)
    ):
        return
    raise HTTPException(
        status_code=400, detail=f"callbackUrl origin {host}:{_effective_port(parsed)} not allowed"
    )


async def _post_callback(callback_url: str, stage_state_json: dict) -> None:
    """POST the StageState to the Trigger.dev wait-token URL.

    Callback delivery is part of the stage contract (Codex M2 R0 P2): a non-2xx
    response or a transport error raises, so :func:`run_stage` can surface a 502
    and the worker's retry re-delivers (the stage itself is idempotent, so the
    retry returns the recorded state without re-executing). Redirects are NOT
    followed (httpx default) so a 3xx cannot bounce the POST to a new host."""
    import httpx

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(callback_url, json={"data": stage_state_json})
    resp.raise_for_status()


@router.post("/stage/run")
async def run_stage(
    req: StageRunRequest, x_internal_token: str | None = Header(default=None)
) -> dict:
    """M2: execute exactly one pipeline stage for an existing run and return its
    StageState. Server-to-server only (Trigger.dev worker / fake orchestrator).
    When ``callbackUrl`` is given, the StageState is also POSTed there (the
    wait-token URL) so the orchestrator's ``wait.forToken`` resolves."""
    _require_internal(x_internal_token)
    # Validate the callback host BEFORE doing any work (fail fast, no side effect).
    if req.callback_url:
        _validate_callback_host(req.callback_url)
    try:
        state = store.run_one_stage(req.run_id, req.stage, fail=req.fail)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"workflow run {req.run_id!r} not found")
    except StageOrderError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    body = state.model_dump(by_alias=True)
    if req.callback_url:
        # The stage already committed (idempotent on retry); if the wait-token
        # callback cannot be delivered, fail with 502 so the worker retries and
        # re-delivers rather than hanging on its token until timeout (R0 P2).
        try:
            await _post_callback(req.callback_url, body)
        except Exception as exc:  # noqa: BLE001 — surface delivery failure to caller
            logging.getLogger(__name__).warning("stage callback POST failed: %s", exc)
            raise HTTPException(
                status_code=502, detail="stage executed but callback delivery failed"
            ) from exc
    return body


@router.get("/runs/{run_id}")
async def get_run(run_id: str) -> dict:
    run = store.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"workflow run {run_id!r} not found")
    return run.model_dump(by_alias=True)


@router.get("/runs")
async def list_runs(limit: int = 20) -> dict:
    return {"runs": [r.model_dump(by_alias=True) for r in store.list_runs(limit=limit)]}


@router.get("/stages")
async def stage_catalog() -> dict:
    """The static 13-stage catalog (order + coarse ADR-014 stage mapping)."""
    return {
        "stages": [
            {
                "order": i,
                "stage": stage.value,
                "wsStage": ws_stage_for(stage),
                "currentObject": STAGE_SPECS[stage].current_object,
                "description": STAGE_SPECS[stage].description,
            }
            for i, stage in enumerate(CANONICAL_STAGE_ORDER)
        ]
    }
