"""ADR-028 P1 — workbench facade seam + intake agent node + pipeline delegation.

Proves the ADR-015 facade (`app.workbench.agent_facade.run_node`) drives the ONE
PROJECT_INTAKE stage through a real agent node — deterministic by default, LLM
opt-in — and that `mock_pipeline` delegates exactly that stage while every other
stage keeps the honest `scripted_demo` provenance (ADR-028 D2). The facade-import
discipline itself is pinned by `tests/test_workbench_facade_discipline.py`.
"""

from __future__ import annotations

import pytest
from app.services.workflow.mock_pipeline import MockWorkflowStore
from app.workbench.agent_facade import run_node

from agents import architect
from agents.state_projection import analyze_intake, sim_state_to_stage_state
from schemas.sim_plan import AnalysisType, GeometrySpec, ObjectiveSpec, PhysicsSpec, SimPlan
from schemas.workflow_state import StageProvenance, StageState, StageStatus, WorkflowStage


def _modal_plan(case_id: str = "AI-FEA-P0-42") -> SimPlan:
    return SimPlan(
        case_id=case_id,
        geometry=GeometrySpec(),
        physics=PhysicsSpec(type=AnalysisType.MODAL),
        objectives=ObjectiveSpec(metrics=["natural_frequencies"]),
    )


# --- facade: deterministic default ------------------------------------------


def test_run_node_intake_deterministic_default() -> None:
    st = run_node(
        WorkflowStage.PROJECT_INTAKE,
        run_id="r1",
        user_request="对支架做线弹性静力分析，关注最大应力与安全系数",
    )
    assert isinstance(st, StageState)
    assert st.stage is WorkflowStage.PROJECT_INTAKE
    assert st.status is StageStatus.SUCCESS
    assert st.provenance is StageProvenance.DETERMINISTIC_AGENT
    # explanation is genuinely derived from the input, not a constant
    assert "支架做线弹性静力" in st.agent_explanation
    assert "应力(von Mises)" in st.agent_explanation
    assert "安全系数" in st.agent_explanation
    assert "未调用 LLM" in st.agent_explanation
    assert st.agent_explanation and st.next_action


def test_run_node_is_input_dependent() -> None:
    """Different requests → different agent output (the honest improvement over the
    former single hardcoded constant)."""
    a = run_node(WorkflowStage.PROJECT_INTAKE, run_id="r", user_request="钢梁模态分析，求固有频率")
    b = run_node(WorkflowStage.PROJECT_INTAKE, run_id="r", user_request="稳态热传导，关注温度场")
    assert a.agent_explanation != b.agent_explanation
    assert a.metrics.model_dump()["physics"] == AnalysisType.MODAL.value
    assert b.metrics.model_dump()["physics"] == AnalysisType.STEADY_THERMAL.value


def test_run_node_rejects_unwired_stage() -> None:
    """P1 wires intake only; any other stage must raise, never silently fabricate
    agent output (ADR-028 D2)."""
    with pytest.raises(NotImplementedError):
        run_node(WorkflowStage.CAD_IMPORT, run_id="r", user_request="x")


# --- facade: LLM opt-in + fallback ------------------------------------------


def test_run_node_llm_optin_uses_llm_provenance(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(architect, "run", lambda state: {"plan": _modal_plan("AI-FEA-P0-77")})
    st = run_node(
        WorkflowStage.PROJECT_INTAKE,
        run_id="r1",
        user_request="梁的模态分析",
        allow_llm=True,
    )
    assert st.provenance is StageProvenance.LLM_AGENT
    assert "AI-FEA-P0-77" in st.agent_explanation
    assert "LLM 架构师" in st.agent_explanation


def test_run_node_llm_falls_back_to_deterministic(monkeypatch: pytest.MonkeyPatch) -> None:
    """No usable plan (e.g. no API key → architect returns a fault) falls back to
    the deterministic node — hermetic, never a hard crash."""
    monkeypatch.setattr(architect, "run", lambda state: {"fault_class": "unknown"})
    st = run_node(
        WorkflowStage.PROJECT_INTAKE,
        run_id="r1",
        user_request="支架静力分析",
        allow_llm=True,
    )
    assert st.provenance is StageProvenance.DETERMINISTIC_AGENT


def test_run_node_llm_swallows_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(state):
        raise RuntimeError("llm down")

    monkeypatch.setattr(architect, "run", _boom)
    st = run_node(
        WorkflowStage.PROJECT_INTAKE, run_id="r", user_request="支架静力", allow_llm=True
    )
    assert st.provenance is StageProvenance.DETERMINISTIC_AGENT


# --- projection layer --------------------------------------------------------


def test_analyze_intake_is_deterministic() -> None:
    req = "对铝合金支架做非线性静力分析，关注最大位移"
    a, b = analyze_intake(req), analyze_intake(req)
    assert a == b
    assert a.provenance is StageProvenance.DETERMINISTIC_AGENT
    assert a.nonlinear is True


def test_analyze_intake_english_is_case_insensitive() -> None:
    """Title-cased / uppercase English must classify correctly (Codex R0 P2)."""
    assert analyze_intake("Modal analysis of a beam").analysis_type is AnalysisType.MODAL
    assert analyze_intake("MODAL ANALYSIS").analysis_type is AnalysisType.MODAL
    # "THERMAL stress" is the thermo-structural rule (most-specific first)
    assert (
        analyze_intake("THERMAL stress on bracket").analysis_type
        is AnalysisType.THERMO_STRUCTURAL
    )
    assert "max_von_mises" in analyze_intake("Compute STRESS and Displacement").objectives


def test_sim_state_to_stage_state_requires_plan() -> None:
    with pytest.raises(TypeError):
        sim_state_to_stage_state({"user_request": "x"}, run_id="r")


def test_sim_state_to_stage_state_projects_llm_plan() -> None:
    st = sim_state_to_stage_state(
        {"plan": _modal_plan("AI-FEA-P0-90"), "user_request": "梁模态"},
        run_id="r9",
    )
    assert st.stage is WorkflowStage.PROJECT_INTAKE
    assert st.provenance is StageProvenance.LLM_AGENT
    assert st.metrics.model_dump()["physics"] == AnalysisType.MODAL.value
    assert "AI-FEA-P0-90" in st.agent_explanation


# --- pipeline delegation (the live seam) ------------------------------------


def test_pipeline_intake_agent_driven_on_genuine_request() -> None:
    run = MockWorkflowStore().run_sync(user_request="对支架做静力分析，关注应力与位移")
    assert run.stages[0].stage is WorkflowStage.PROJECT_INTAKE
    assert run.stages[0].provenance is StageProvenance.DETERMINISTIC_AGENT
    # wiring one stage must NOT relabel the other twelve (ADR-028 D2)
    assert all(s.provenance is StageProvenance.SCRIPTED_DEMO for s in run.stages[1:])


def test_pipeline_display_label_alone_stays_scripted() -> None:
    """The Monitor defaults `label` to "monitor"; a display label is NOT intake
    text, so without a genuine user_request intake stays scripted_demo — never a
    false provenance=deterministic_agent on a no-request run (Codex R0 P1)."""
    run = MockWorkflowStore().run_sync(label="monitor")
    assert run.stages[0].provenance is StageProvenance.SCRIPTED_DEMO


def test_pipeline_no_request_intake_stays_scripted() -> None:
    run = MockWorkflowStore().run_sync(label=None)
    assert run.stages[0].provenance is StageProvenance.SCRIPTED_DEMO


def test_pipeline_intake_failure_injection_stays_scripted() -> None:
    """A demo failure injected at intake is NOT agent-authored prose → scripted."""
    run = MockWorkflowStore().run_sync(
        user_request="支架静力分析", fail_at_stage=WorkflowStage.PROJECT_INTAKE
    )
    assert run.stages[0].status is StageStatus.FAILED
    assert run.stages[0].provenance is StageProvenance.SCRIPTED_DEMO
