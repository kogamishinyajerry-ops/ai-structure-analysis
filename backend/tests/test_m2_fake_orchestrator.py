"""M2: the Trigger.dev integration contract, proven WITHOUT a Trigger.dev account.

A Python "fake orchestrator" drives the exact HTTP contract the Trigger.dev v4
orchestrator task will drive: create an external run, then POST /workflow/stage/run
once per stage (with the internal-secret header), optionally delivering each
StageState to a wait-token callback URL. Also pins the M2 security must-fixes:
internal-secret auth + secure-by-default disable, callbackUrl SSRF guard, the
run_one_stage idempotency/ordering guards, and the well_harness signed-registry
patch. Route handlers are awaited directly (Starlette TestClient is unusable in
this env — see test_workflow_mock_pipeline.py).
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.services.workflow.mock_pipeline import (
    MockWorkflowStore,
    StageOrderError,
)
from schemas.workflow_state import CANONICAL_STAGE_ORDER, StageStatus, WorkflowStage

INTERNAL = "test-internal-secret"


def _wf():
    # Deferred import + openai-key mute (mirrors CI; see test_workflow_mock_pipeline).
    settings.openai_api_key = None
    from app.api.routes import workflow

    return workflow


@pytest.fixture(autouse=True)
def _internal_secret():
    old = settings.trigger_internal_secret
    old_lb = settings.trigger_allow_loopback_callback
    settings.trigger_internal_secret = INTERNAL
    # Local tests drive loopback wait-token callbacks; production rejects them.
    settings.trigger_allow_loopback_callback = True
    yield
    settings.trigger_internal_secret = old
    settings.trigger_allow_loopback_callback = old_lb


# --- store-level single-stage contract ---

def test_create_run_is_pending_no_execution() -> None:
    s = MockWorkflowStore()
    run = s.create_run(label="ext")
    assert run.status is StageStatus.PENDING
    assert all(st.status is StageStatus.PENDING for st in run.stages)
    assert run.finished_at is None


def test_run_one_stage_drives_to_completion() -> None:
    s = MockWorkflowStore()
    run = s.create_run()
    for stage in CANONICAL_STAGE_ORDER:
        st = s.run_one_stage(run.run_id, stage)
        assert st.run_id == run.run_id
        assert st.progress == 1.0
    final = s.runs[run.run_id]
    assert final.status is StageStatus.WARNING  # mesh_quality + result_analysis warn
    assert final.finished_at is not None


def test_run_one_stage_is_idempotent() -> None:
    """A Trigger.dev retry re-POSTs a completed stage — must NOT re-execute /
    overwrite (e.g. flip a WARNING to SUCCESS)."""
    s = MockWorkflowStore()
    run = s.create_run()
    for stage in CANONICAL_STAGE_ORDER:
        if stage is WorkflowStage.MESH_QUALITY_CHECK:
            break
        s.run_one_stage(run.run_id, stage)
    w1 = s.run_one_stage(run.run_id, WorkflowStage.MESH_QUALITY_CHECK)
    w2 = s.run_one_stage(run.run_id, WorkflowStage.MESH_QUALITY_CHECK)  # replay
    assert w1.status is w2.status is StageStatus.WARNING
    assert w1.warnings == w2.warnings


def test_run_one_stage_out_of_order_raises() -> None:
    s = MockWorkflowStore()
    run = s.create_run()
    with pytest.raises(StageOrderError):
        s.run_one_stage(run.run_id, WorkflowStage.SOLVER_RUN)  # prior stages pending


def test_run_one_stage_after_failure_raises() -> None:
    s = MockWorkflowStore()
    run = s.create_run()
    s.run_one_stage(run.run_id, WorkflowStage.PROJECT_INTAKE)
    s.run_one_stage(run.run_id, WorkflowStage.CAD_IMPORT, fail=True)
    assert s.runs[run.run_id].status is StageStatus.FAILED
    with pytest.raises(StageOrderError):
        s.run_one_stage(run.run_id, WorkflowStage.GEOMETRY_VALIDATION)


def test_run_one_stage_unknown_run() -> None:
    with pytest.raises(KeyError):
        MockWorkflowStore().run_one_stage("nope", WorkflowStage.PROJECT_INTAKE)


# --- the fake orchestrator: full HTTP contract via the route handlers ---

def test_fake_orchestrator_drives_full_pipeline() -> None:
    wf = _wf()
    created = asyncio.run(
        wf.trigger_workflow(wf.WorkflowTriggerRequest(trigger_mode="external"))
    )
    run_id = created["runId"]
    assert created["status"] == "pending"
    assert created["orchRunId"] == run_id
    assert created["publicAccessToken"] is None  # only the Node layer mints it

    for stage in CANONICAL_STAGE_ORDER:
        body = asyncio.run(
            wf.run_stage(
                wf.StageRunRequest(run_id=run_id, stage=stage),
                x_internal_token=INTERNAL,
            )
        )
        assert body["runId"] == run_id
        assert body["progress"] == 1.0
        assert body["status"] in ("success", "warning")

    final = asyncio.run(wf.get_run(run_id))
    assert final["status"] in ("success", "warning")
    assert final["finishedAt"] is not None


def test_fake_orchestrator_failure_halts() -> None:
    wf = _wf()
    run_id = asyncio.run(
        wf.trigger_workflow(wf.WorkflowTriggerRequest(trigger_mode="external"))
    )["runId"]
    for stage in CANONICAL_STAGE_ORDER:
        fail = stage is WorkflowStage.SOLVER_RUN
        body = asyncio.run(
            wf.run_stage(
                wf.StageRunRequest(run_id=run_id, stage=stage, fail=fail),
                x_internal_token=INTERNAL,
            )
        )
        if fail:
            assert body["status"] == "failed"
            assert body["errors"][0]["faultClass"] == "solver_convergence"
            break
    assert asyncio.run(wf.get_run(run_id))["status"] == "failed"


# --- security: auth, secure-by-default, SSRF ---

def test_stage_run_requires_valid_token() -> None:
    wf = _wf()
    run_id = asyncio.run(
        wf.trigger_workflow(wf.WorkflowTriggerRequest(trigger_mode="external"))
    )["runId"]
    with pytest.raises(HTTPException) as e:
        asyncio.run(
            wf.run_stage(
                wf.StageRunRequest(run_id=run_id, stage=WorkflowStage.PROJECT_INTAKE),
                x_internal_token="wrong",
            )
        )
    assert e.value.status_code == 401


def test_stage_run_disabled_without_secret() -> None:
    wf = _wf()
    old = settings.trigger_internal_secret
    settings.trigger_internal_secret = None
    try:
        with pytest.raises(HTTPException) as e:
            asyncio.run(
                wf.run_stage(
                    wf.StageRunRequest(run_id="x", stage=WorkflowStage.PROJECT_INTAKE),
                    x_internal_token=None,
                )
            )
        assert e.value.status_code == 503  # secure-by-default
    finally:
        settings.trigger_internal_secret = old


def test_stage_run_rejects_ssrf_callback_host() -> None:
    wf = _wf()
    run_id = asyncio.run(
        wf.trigger_workflow(wf.WorkflowTriggerRequest(trigger_mode="external"))
    )["runId"]
    with pytest.raises(HTTPException) as e:
        asyncio.run(
            wf.run_stage(
                wf.StageRunRequest(
                    run_id=run_id,
                    stage=WorkflowStage.PROJECT_INTAKE,
                    callback_url="http://evil.example.com/steal",
                ),
                x_internal_token=INTERNAL,
            )
        )
    assert e.value.status_code == 400
    # the stage must NOT have executed (fail-fast before side effects)
    assert asyncio.run(wf.get_run(run_id))["stages"][0]["status"] == "pending"


def test_stage_run_delivers_callback_to_loopback() -> None:
    """The wait-token callback path: FastAPI POSTs {data: StageState} to a
    loopback URL (allowed by the SSRF guard). Proven with a local capture
    server — this is the wait.forToken side, without Trigger.dev."""
    wf = _wf()
    run_id = asyncio.run(
        wf.trigger_workflow(wf.WorkflowTriggerRequest(trigger_mode="external"))
    )["runId"]
    received: dict[str, str] = {}

    async def scenario() -> dict:
        async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            header = await reader.readuntil(b"\r\n\r\n")
            htxt = header.decode("latin1")
            clen = 0
            for line in htxt.split("\r\n"):
                if line.lower().startswith("content-length:"):
                    clen = int(line.split(":", 1)[1].strip())
            body = await reader.readexactly(clen) if clen else b""
            received["raw"] = htxt + body.decode("utf-8", "replace")
            writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok")
            await writer.drain()
            writer.close()

        server = await asyncio.start_server(handle, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        async with server:
            cb = f"http://127.0.0.1:{port}/complete"
            body = await wf.run_stage(
                wf.StageRunRequest(
                    run_id=run_id, stage=WorkflowStage.PROJECT_INTAKE, callback_url=cb
                ),
                x_internal_token=INTERNAL,
            )
            await asyncio.sleep(0.15)  # let the capture server read the POST
        return body

    body = asyncio.run(scenario())
    assert body["stage"] == "project_intake"
    raw = received.get("raw", "")
    assert '"data"' in raw  # StageState wrapped per Trigger.dev waitpoint contract
    assert "project_intake" in raw


# --- security: well_harness signed-registry guard (threat model P2) ---

def test_calculix_executor_refuses_signed_registry() -> None:
    from app.well_harness.executors import CalculixExecutor

    with pytest.raises(ValueError, match="HF1.7a"):
        # Guard fires before any store/subprocess access, so None args are fine.
        CalculixExecutor().execute("GS-001", None, None)  # type: ignore[arg-type]


# --- Codex M2 R0 fixes (R1 regression pins) ---

def test_loopback_callback_rejected_when_flag_off() -> None:
    """R0 P1: loopback is NOT an open SSRF target — only allowed when the
    self-host flag is set. With it off, a loopback callbackUrl is rejected and
    the stage does not execute."""
    wf = _wf()
    run_id = asyncio.run(
        wf.trigger_workflow(wf.WorkflowTriggerRequest(trigger_mode="external"))
    )["runId"]
    old = settings.trigger_allow_loopback_callback
    settings.trigger_allow_loopback_callback = False
    try:
        with pytest.raises(HTTPException) as e:
            asyncio.run(
                wf.run_stage(
                    wf.StageRunRequest(
                        run_id=run_id,
                        stage=WorkflowStage.PROJECT_INTAKE,
                        callback_url="http://127.0.0.1:9/closed",
                    ),
                    x_internal_token=INTERNAL,
                )
            )
        assert e.value.status_code == 400
    finally:
        settings.trigger_allow_loopback_callback = old
    assert asyncio.run(wf.get_run(run_id))["stages"][0]["status"] == "pending"


def test_callback_origin_pinned_to_scheme_host_port() -> None:
    """R1 P2: the non-loopback callback is pinned to the FULL Trigger.dev origin
    (scheme + host + port), so a same-host different-port (or scheme-mismatched)
    URL is rejected — not just same-host."""
    wf = _wf()
    # Exact configured origin (https://api.trigger.dev, default :443) -> allowed.
    wf._validate_callback_host("https://api.trigger.dev/api/v3/waitpoints/complete")
    # Same host, non-standard port -> rejected.
    with pytest.raises(HTTPException) as e1:
        wf._validate_callback_host("https://api.trigger.dev:8443/x")
    assert e1.value.status_code == 400
    # Scheme mismatch (configured base is https) -> rejected.
    with pytest.raises(HTTPException) as e2:
        wf._validate_callback_host("http://api.trigger.dev/x")
    assert e2.value.status_code == 400
    # Malformed port -> clean 400, not a 500 (R2 P3).
    for bad in ("https://api.trigger.dev:abc/x", "https://api.trigger.dev:99999/x"):
        with pytest.raises(HTTPException) as e3:
            wf._validate_callback_host(bad)
        assert e3.value.status_code == 400


def test_non_http_callback_scheme_rejected() -> None:
    """R0 P1: a non-http(s) scheme (file://, gopher://, …) is rejected before
    any work, closing the non-HTTP SSRF vector."""
    wf = _wf()
    run_id = asyncio.run(
        wf.trigger_workflow(wf.WorkflowTriggerRequest(trigger_mode="external"))
    )["runId"]
    with pytest.raises(HTTPException) as e:
        asyncio.run(
            wf.run_stage(
                wf.StageRunRequest(
                    run_id=run_id,
                    stage=WorkflowStage.PROJECT_INTAKE,
                    callback_url="file:///etc/passwd",
                ),
                x_internal_token=INTERNAL,
            )
        )
    assert e.value.status_code == 400
    assert asyncio.run(wf.get_run(run_id))["stages"][0]["status"] == "pending"


def test_callback_delivery_failure_returns_502_but_commits_stage() -> None:
    """R0 P2: if the wait-token callback returns non-2xx, /stage/run returns 502
    (so the worker retries + re-delivers) — but the stage IS committed, so the
    retry hits the idempotent path rather than re-executing."""
    wf = _wf()
    run_id = asyncio.run(
        wf.trigger_workflow(wf.WorkflowTriggerRequest(trigger_mode="external"))
    )["runId"]

    async def scenario() -> None:
        async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            await reader.readuntil(b"\r\n\r\n")
            writer.write(b"HTTP/1.1 500 Server Error\r\nContent-Length: 3\r\nConnection: close\r\n\r\nbad")
            await writer.drain()
            writer.close()

        server = await asyncio.start_server(handle, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        async with server:
            cb = f"http://127.0.0.1:{port}/complete"
            with pytest.raises(HTTPException) as e:
                await wf.run_stage(
                    wf.StageRunRequest(
                        run_id=run_id, stage=WorkflowStage.PROJECT_INTAKE, callback_url=cb
                    ),
                    x_internal_token=INTERNAL,
                )
            assert e.value.status_code == 502

    asyncio.run(scenario())
    # Stage committed despite the failed callback; a retry is idempotent.
    assert asyncio.run(wf.get_run(run_id))["stages"][0]["status"] == "success"


def test_run_one_stage_concurrent_calls_execute_once() -> None:
    """R0 P2: the run_one_stage lock makes concurrent same-stage calls
    single-execution — only one runs, the rest replay the recorded state."""
    s = MockWorkflowStore()
    run = s.create_run()

    import threading

    barrier = threading.Barrier(8)
    results: list[StageState] = []
    lock = threading.Lock()

    def worker() -> None:
        barrier.wait()
        st = s.run_one_stage(run.run_id, WorkflowStage.PROJECT_INTAKE)
        with lock:
            results.append(st)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # All 8 observe the SAME StageState object (one execution, replayed).
    assert len({id(r) for r in results}) == 1
    assert results[0].status is StageStatus.SUCCESS
