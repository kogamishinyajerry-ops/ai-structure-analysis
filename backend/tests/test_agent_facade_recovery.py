"""ADR-028 P-recover — the two-agent fault-recovery decision on the failure path.

When a demo failure is INJECTED, the real reviewer node DERIVES a verdict from the
ACTUAL injected fault (agents.reviewer._review_upstream_fault, RERUN_FAULTS membership)
and the real router picks the recovery node — a genuine reviewer→router decision with
ZERO fabrication. These tests prove:

* the verdict is DERIVED, never hardcoded (the reference_mismatch trip-wire: a non-rerun
  fault must yield "Needs Review"→human_fallback, NOT "Re-run"→architect); and
* surfacing the recovery does NOT relabel the failing stage — its provenance stays
  scripted_demo (the failure prose is scripted; StageProvenance labels that text) and the
  recovery rides metrics.recovery with its own agentDriven/faultInjected flags, so the
  N/13 agent-driven count never moves on a failure run (ADR-028 D2); and
* the real-LE10 failure path gets no recovery overlay (mock-demo path only).
"""

from __future__ import annotations

from app.services.workflow.mock_backend import MockFEABackend
from app.services.workflow.mock_pipeline import (
    LE10_STAGE_SPECS,
    MockWorkflowStore,
    _build_stage_state,
)
from app.workbench.agent_facade import decide_recovery
from schemas.sim_state import FaultClass
from schemas.workflow_state import StageError, StageProvenance, StageStatus, WorkflowStage


# --- the verdict is DERIVED from the real reviewer, never hardcoded ----------


def test_rerun_fault_derives_rerun_verdict_and_routes() -> None:
    r = decide_recovery(fault_class="mesh_jacobian")
    assert r.verdict == "Re-run"  # MESH_JACOBIAN ∈ RERUN_FAULTS (real reviewer)
    assert r.next_node == "mesh"


def test_geometry_invalid_routes_to_geometry() -> None:
    r = decide_recovery(fault_class="geometry_invalid")
    assert r.verdict == "Re-run"
    assert r.next_node == "geometry"


def test_solver_convergence_routes_to_solver() -> None:
    r = decide_recovery(fault_class="solver_convergence")
    assert r.verdict == "Re-run"
    assert r.next_node == "solver"


def test_non_rerun_fault_derives_needs_review_not_rerun() -> None:
    """THE anti-fabrication trip-wire: reference_mismatch is NOT in RERUN_FAULTS, so the
    real reviewer yields 'Needs Review' → router → human_fallback. A hardcoded
    verdict='Re-run' would wrongly route it to 'architect' (FAULT_TO_NODE), failing here."""
    r = decide_recovery(fault_class="reference_mismatch")
    assert r.verdict == "Needs Review"
    assert r.next_node == "human_fallback"


def test_unknown_fault_routes_to_human_fallback() -> None:
    r = decide_recovery(fault_class="unknown")
    assert r.verdict == "Needs Review"
    assert r.next_node == "human_fallback"


def test_rerun_over_budget_escalates_to_human_fallback() -> None:
    # The real MAX_RETRIES=3 cap is honored: a re-runnable fault with the budget exhausted
    # escalates to human_fallback instead of looping.
    r = decide_recovery(fault_class="mesh_jacobian", retry_budgets={"mesh": 3})
    assert r.next_node == "human_fallback"


def test_recovery_explanation_names_both_agents_and_discloses_injection() -> None:
    expl = decide_recovery(fault_class="mesh_jacobian").agent_explanation
    assert "reviewer" in expl  # names the reviewer node
    assert "路由 agent" in expl or "route_reviewer" in expl  # names the router node
    assert "未调用 LLM" in expl  # deterministic, no LLM
    assert "注入" in expl  # the fault is injected demo input
    assert "非 agent 诊断" in expl  # the agent did NOT diagnose the fault (honesty hedge)


# --- the live pipeline seam: recovery surfaced, stage stays scripted ---------


def test_failure_injection_surfaces_recovery_in_metrics_but_stays_scripted() -> None:
    run = MockWorkflowStore().run_sync(fail_at_stage=WorkflowStage.MESH_GENERATION)
    stage = next(s for s in run.stages if s.stage is WorkflowStage.MESH_GENERATION)
    # the failure prose + label are UNTOUCHED — provenance stays scripted_demo
    assert stage.status is StageStatus.FAILED
    assert stage.provenance is StageProvenance.SCRIPTED_DEMO
    metrics = stage.metrics.model_dump(by_alias=True, exclude_none=True)
    assert "routedTo" not in metrics  # recovery is NOT the P3 routing channel
    rec = metrics["recovery"]
    assert rec["nextNode"] == "mesh"  # MESH_RESOLUTION fault → re-run mesh
    assert rec["verdict"] == "Re-run"
    assert rec["agentDriven"] is True
    assert rec["faultInjected"] is True


def test_failure_injection_needs_review_branch_routes_human_fallback() -> None:
    # PROJECT_INTAKE's injected fault is UNKNOWN (not re-runnable) → the LIVE path derives
    # 'Needs Review' → human_fallback (exercises the non-rerun branch end-to-end).
    run = MockWorkflowStore().run_sync(fail_at_stage=WorkflowStage.PROJECT_INTAKE)
    stage = run.stages[0]
    assert stage.provenance is StageProvenance.SCRIPTED_DEMO
    rec = stage.metrics.model_dump(by_alias=True, exclude_none=True)["recovery"]
    assert rec["verdict"] == "Needs Review"
    assert rec["nextNode"] == "human_fallback"


def test_real_le10_failure_path_gets_no_recovery_overlay() -> None:
    """The real-LE10 specs path is excluded (specs is not STAGE_SPECS) → a real failure
    keeps its honest error with NO fabricated recovery overlay."""
    err = StageError(fault_class=FaultClass.MESH_RESOLUTION, message="real solve failed")
    st = _build_stage_state(
        "r",
        WorkflowStage.MESH_GENERATION,
        StageStatus.FAILED,
        1.0,
        backend=MockFEABackend(),
        specs=LE10_STAGE_SPECS,
        error=err,
    )
    assert st.provenance is StageProvenance.SCRIPTED_DEMO
    assert "recovery" not in st.metrics.model_dump(by_alias=True, exclude_none=True)
