"""ADR-028 P3 — the router node behind the facade.

The reviewer gate's "next step" is a REAL orchestration decision made by
``agents.router.route_reviewer`` (ADR-004 fault→node map + a 3-retry cap), not a
hardcoded transition. These tests prove:

* the facade ``decide_route`` exercises every genuine routing branch (accept→viz,
  re-run→upstream node, retry-budget-exceeded→human_fallback, unknown→human_fallback),
  always tagged ``provenance=deterministic_agent``; and
* the live pipeline wires it onto the RESULT_ANALYSIS stage on the mock-demo happy path
  ONLY — a failure injection or the real-LE10 path keeps the honest ``scripted_demo``
  (ADR-028 D2: wiring the router must not relabel stages it did not decide).

The demo happy path only ever exercises accept→viz; the re-run / fallback branches are
real code, proven here rather than by the canned demo.
"""

from __future__ import annotations

from app.services.workflow.mock_backend import MockFEABackend
from app.services.workflow.mock_pipeline import (
    LE10_STAGE_SPECS,
    STAGE_SPECS,
    MockWorkflowStore,
    _build_stage_state,
)
from app.workbench.agent_facade import decide_route

from schemas.workflow_state import StageProvenance, StageStatus, WorkflowStage

# --- the real router branches, via the facade -------------------------------


def test_accept_routes_to_viz() -> None:
    route = decide_route(verdict="Accept", fault_class="none")
    assert route.next_node == "viz"
    assert route.provenance is StageProvenance.DETERMINISTIC_AGENT


def test_accept_with_note_routes_to_viz() -> None:
    # The mock-demo reviewer gate completes as WARNING → "Accept with Note".
    assert decide_route(verdict="Accept with Note", fault_class="none").next_node == "viz"


def test_rerun_mesh_fault_within_budget_routes_to_mesh() -> None:
    route = decide_route(verdict="Re-run", fault_class="mesh_jacobian", retry_budgets={})
    assert route.next_node == "mesh"


def test_rerun_mesh_fault_over_budget_escalates_to_human_fallback() -> None:
    # MAX_RETRIES (3) exhausted → the router escalates instead of looping forever.
    route = decide_route(verdict="Re-run", fault_class="mesh_jacobian", retry_budgets={"mesh": 3})
    assert route.next_node == "human_fallback"


def test_rerun_reference_mismatch_routes_to_architect() -> None:
    assert decide_route(verdict="Re-run", fault_class="reference_mismatch").next_node == "architect"


def test_non_accept_non_rerun_routes_to_human_fallback() -> None:
    assert decide_route(verdict="Needs Review", fault_class="none").next_node == "human_fallback"


def test_route_explanation_is_transparent_and_deterministic() -> None:
    route = decide_route(verdict="Accept", fault_class="none")
    # Names the real router and is explicit that no LLM was used — and the explanation
    # attributes only the ROUTING (not the underlying result) to the agent.
    assert "route_reviewer" in route.agent_explanation
    assert "未调用 LLM" in route.agent_explanation
    assert "路由 agent" in route.agent_explanation
    assert "viz" in route.next_action


def test_agent_layer_decide_route_accepts_faultclass_enum() -> None:
    """The agent-layer projector accepts a FaultClass enum directly (the facade hands it
    a plain wire string); both normalize to the same routing token + value."""
    from agents.state_projection import decide_route as _proj_decide
    from schemas.sim_state import FaultClass

    route = _proj_decide(verdict="Re-run", fault_class=FaultClass.MESH_JACOBIAN, retry_budgets={})
    assert route.next_node == "mesh"
    assert route.fault_class == "mesh_jacobian"
    assert route.provenance is StageProvenance.DETERMINISTIC_AGENT


# --- the live pipeline seam --------------------------------------------------


def test_pipeline_result_analysis_routing_is_agent_driven() -> None:
    """On the mock-demo happy path, RESULT_ANALYSIS carries the real routing decision:
    provenance=deterministic_agent, a routedTo metric, and an accept→viz next step."""
    run = MockWorkflowStore().run_sync()
    result = next(s for s in run.stages if s.stage is WorkflowStage.RESULT_ANALYSIS)
    assert result.provenance is StageProvenance.DETERMINISTIC_AGENT
    metrics = result.metrics.model_dump(by_alias=True, exclude_none=True)
    assert metrics.get("routedTo") == "viz"
    assert "viz" in result.next_action
    # The explanation must disclose that the verdict is scripted demo state and only the
    # routing is agent-authored — so deterministic_agent here is never an over-claim that
    # the result itself was computed by an agent (Codex ADR-028-P3 R0 P2).
    assert "脚本化" in result.agent_explanation


def test_pipeline_result_analysis_failure_injection_stays_scripted() -> None:
    """A demo failure injected at the reviewer gate is NOT an agent routing decision
    (error is set) → the stage keeps scripted_demo (ADR-028 D2)."""
    run = MockWorkflowStore().run_sync(fail_at_stage=WorkflowStage.RESULT_ANALYSIS)
    result = next(s for s in run.stages if s.stage is WorkflowStage.RESULT_ANALYSIS)
    assert result.status is StageStatus.FAILED
    assert result.provenance is StageProvenance.SCRIPTED_DEMO
    metrics = result.metrics.model_dump(by_alias=True, exclude_none=True)
    assert "routedTo" not in metrics


def test_real_le10_specs_path_stays_scripted() -> None:
    """The real-LE10 specs path is excluded from router wiring (specs is not the mock
    STAGE_SPECS) → no false agent provenance until the real path is wired later."""
    st = _build_stage_state(
        "r",
        WorkflowStage.RESULT_ANALYSIS,
        StageStatus.WARNING,
        1.0,
        backend=MockFEABackend(),
        specs=LE10_STAGE_SPECS,
        solve_ctx=None,
    )
    assert st.provenance is StageProvenance.SCRIPTED_DEMO
    assert "routedTo" not in st.metrics.model_dump(by_alias=True, exclude_none=True)


def test_real_solve_ctx_path_stays_scripted() -> None:
    """Even on the mock STAGE_SPECS, a present solve_ctx (real-solve hybrid) is excluded
    from router wiring (solve_ctx is None guard), so a real solve is never relabelled."""
    st = _build_stage_state(
        "r",
        WorkflowStage.RESULT_ANALYSIS,
        StageStatus.WARNING,
        1.0,
        backend=MockFEABackend(),
        specs=STAGE_SPECS,
        solve_ctx={"benchmark": {"verdict": "PASS"}},
    )
    assert st.provenance is StageProvenance.SCRIPTED_DEMO
    assert "routedTo" not in st.metrics.model_dump(by_alias=True, exclude_none=True)
