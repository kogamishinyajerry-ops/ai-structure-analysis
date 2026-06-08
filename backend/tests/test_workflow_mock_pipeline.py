"""M1 Mock pipeline + workflow API tests (Agentic FEA Workflow Runtime).

Pins: MockFEABackend conforms to the FEABackend Protocol; the 13-stage Mock
pipeline produces real StageStates with the canonical success/warning pattern;
failure injection halts the pipeline at the chosen stage; the read/trigger API
returns the run. Tests mount ONLY the workflow router (not app.main) to avoid
the unrelated nl_parser/openai import breakage in the full app.
"""

from __future__ import annotations

import asyncio

import pytest

from aeron.protocols.fea_backend import FEABackend
from app.services.workflow.mock_backend import MockFEABackend
from app.services.workflow.mock_pipeline import MockWorkflowStore
from schemas.sim_state import FaultClass
from schemas.workflow_state import CANONICAL_STAGE_ORDER, StageStatus, WorkflowStage


def test_mock_backend_satisfies_protocol() -> None:
    assert isinstance(MockFEABackend(), FEABackend)


def test_happy_run_completes_all_13_stages() -> None:
    run = MockWorkflowStore().run_sync(label="happy")
    assert len(run.stages) == 13
    assert [s.stage for s in run.stages] == list(CANONICAL_STAGE_ORDER)
    # no failures; overall reflects the per-stage warnings
    assert all(s.status is not StageStatus.FAILED for s in run.stages)
    assert run.status is StageStatus.WARNING  # mesh_quality + result_analysis warn
    assert run.finished_at is not None
    assert run.current_stage is None


def test_warning_stages_are_warning_others_success() -> None:
    run = MockWorkflowStore().run_sync()
    by_stage = {s.stage: s for s in run.stages}
    assert by_stage[WorkflowStage.MESH_QUALITY_CHECK].status is StageStatus.WARNING
    assert by_stage[WorkflowStage.MESH_QUALITY_CHECK].warnings  # non-empty
    assert by_stage[WorkflowStage.RESULT_ANALYSIS].status is StageStatus.WARNING
    assert by_stage[WorkflowStage.SOLVER_RUN].status is StageStatus.SUCCESS
    assert by_stage[WorkflowStage.CAD_IMPORT].status is StageStatus.SUCCESS


def test_result_metrics_come_from_backend() -> None:
    run = MockWorkflowStore().run_sync()
    result = next(s for s in run.stages if s.stage is WorkflowStage.RESULT_ANALYSIS)
    # safety factor = yield / von Mises = 2.5e8 / 2.18e8 ~= 1.147
    assert result.metrics.safety_factor == pytest.approx(1.147, abs=0.01)
    assert result.metrics.max_von_mises_pa == pytest.approx(2.18e8)


def test_report_stage_emits_report_artifact() -> None:
    run = MockWorkflowStore().run_sync()
    report = next(s for s in run.stages if s.stage is WorkflowStage.REPORT_GENERATION)
    assert report.status is StageStatus.SUCCESS
    assert report.artifacts.report_file is not None
    assert report.artifacts.report_file.endswith("report.md")


def test_failure_injection_halts_pipeline() -> None:
    run = MockWorkflowStore().run_sync(fail_at_stage=WorkflowStage.MESH_GENERATION)
    by_stage = {s.stage: s for s in run.stages}
    assert by_stage[WorkflowStage.MESH_GENERATION].status is StageStatus.FAILED
    assert by_stage[WorkflowStage.MESH_GENERATION].errors
    # stages before the failure ran; stages after stay PENDING (halted)
    assert by_stage[WorkflowStage.CAD_IMPORT].status is StageStatus.SUCCESS
    assert by_stage[WorkflowStage.SOLVER_RUN].status is StageStatus.PENDING
    assert run.status is StageStatus.FAILED


def test_solver_failure_carries_convergence_fault() -> None:
    run = MockWorkflowStore().run_sync(fail_at_stage=WorkflowStage.SOLVER_RUN)
    solver = next(s for s in run.stages if s.stage is WorkflowStage.SOLVER_RUN)
    assert solver.status is StageStatus.FAILED
    assert solver.errors[0].fault_class is FaultClass.SOLVER_CONVERGENCE


# --- API: call the route-handler coroutines directly ---
# (Starlette TestClient is unusable in this env — the local httpx is newer than
# starlette/openai expect, so httpx.Client(app=...) raises. We exercise the real
# handler functions instead; FastAPI's routing/serialization is framework code.)

def _wf():
    # Deferred import: pulling app.api.* runs app.api.__init__ -> NLParser() ->
    # OpenAI(). With OPENAI_API_KEY set locally that trips the same openai/httpx
    # mismatch; CI runs with the key unset (client=None). Mirror the CI condition.
    from app.core.config import settings

    settings.openai_api_key = None
    from app.api.routes import workflow

    return workflow


def test_api_trigger_sync_returns_full_run() -> None:
    wf = _wf()
    body = asyncio.run(wf.trigger_workflow(wf.WorkflowTriggerRequest(label="demo"), sync=True))
    assert body["label"] == "demo"
    assert len(body["stages"]) == 13
    assert body["status"] in {"success", "warning"}
    # camelCase wire shape on a nested stage
    mq = next(s for s in body["stages"] if s["stage"] == "mesh_quality_check")
    assert mq["metrics"]["badElements"] == 142
    assert "agentExplanation" in mq and "nextAction" in mq


def test_api_get_run_roundtrip_and_404() -> None:
    from fastapi import HTTPException

    wf = _wf()
    run_id = asyncio.run(wf.trigger_workflow(wf.WorkflowTriggerRequest(), sync=True))["runId"]
    got = asyncio.run(wf.get_run(run_id))
    assert got["runId"] == run_id
    with pytest.raises(HTTPException):
        asyncio.run(wf.get_run("does-not-exist"))


def test_api_stage_catalog_lists_13() -> None:
    wf = _wf()
    body = asyncio.run(wf.stage_catalog())
    assert len(body["stages"]) == 13
    assert body["stages"][0]["stage"] == "project_intake"
    assert body["stages"][-1]["stage"] == "report_generation"
    # every fine stage carries its coarse ADR-014 wsStage
    assert all("wsStage" in s for s in body["stages"])
