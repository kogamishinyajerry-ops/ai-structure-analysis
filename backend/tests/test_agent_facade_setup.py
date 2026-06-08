"""ADR-028 P-setup — the deterministic setup-planner node behind the facade.

The MATERIAL_ASSIGNMENT / BOUNDARY_CONDITIONS / LOAD_CASES stages are now decided by a
real rule-based planner (agents.state_projection.analyze_setup) — the honest deterministic
stand-in for the architect work the LLM does in a SimPlan. These tests prove:

* the decision is INPUT-DEPENDENT (different requests -> different material/load), and
* when the request gives no hint, the planner falls back to a documented default AND the
  explanation DISCLOSES it (hard assertion) — so provenance=deterministic_agent is never
  read as "derived from real geometry"; and
* the facade wires ONLY these 3 stages + intake (every tool/artifact-bound stage still
  raises), and the live pipeline keeps them scripted_demo without a genuine request /
  under failure injection (ADR-028 D2).
"""

from __future__ import annotations

import pytest

from app.services.workflow.mock_pipeline import MockWorkflowStore
from app.workbench.agent_facade import run_node
from schemas.workflow_state import StageProvenance, StageStatus, WorkflowStage

from agents.state_projection import analyze_setup

_SETUP_STAGES = (
    WorkflowStage.MATERIAL_ASSIGNMENT,
    WorkflowStage.BOUNDARY_CONDITIONS,
    WorkflowStage.LOAD_CASES,
)


# --- the planner is genuine + input-dependent --------------------------------


def test_setup_material_input_dependent() -> None:
    steel = analyze_setup("用钢做静力分析")
    alu = analyze_setup("用铝合金做支架分析")
    assert "Steel" in steel.material.metrics["materialName"]
    assert steel.material.metrics["youngsModulusPa"] == 2.1e11
    assert steel.material.from_hint is True
    assert "Aluminum" in alu.material.metrics["materialName"]
    assert alu.material.metrics["youngsModulusPa"] == 7.17e10
    assert alu.material.from_hint is True
    # genuine rule-based agent: different inputs -> different material decisions
    assert steel.material.metrics["materialName"] != alu.material.metrics["materialName"]


def test_setup_load_magnitude_input_dependent() -> None:
    out = analyze_setup("顶面施加 5 kN 压力")
    assert out.load.from_hint is True
    assert out.load.metrics["magnitude"] == 5.0
    assert out.load.metrics["unit"] == "kN"
    assert out.load.metrics["loadSemantic"] == "pressure_load"


def test_setup_load_magnitude_only_discloses_default_topology() -> None:
    """A magnitude WITHOUT a topology keyword ("施加 100N") must NOT claim it identified
    the load topology — the explanation discloses the topology defaulted (Codex P-setup
    R0 P2: no partial over-claim)."""
    out = analyze_setup("施加 100N")
    assert out.load.metrics["magnitude"] == 100.0
    assert out.load.metrics["kindFromHint"] is False  # topology defaulted, not identified
    assert out.load.metrics["loadSemantic"] == "tip_load"
    assert "默认" in out.load.agent_explanation


def test_setup_default_discloses_no_hint() -> None:
    """No material/BC/load hint -> documented schema defaults, BUT each explanation MUST
    disclose the default (the D2 honesty condition, asserted hard — not just prose)."""
    out = analyze_setup("随便帮我分析一下")
    assert out.material.from_hint is False
    assert out.bc.from_hint is False
    assert out.load.from_hint is False
    assert "默认" in out.material.agent_explanation
    assert "默认" in out.bc.agent_explanation
    assert "默认" in out.load.agent_explanation
    # documented defaults
    assert out.bc.metrics["bcSemantic"] == "fixed_base"
    assert out.load.metrics["loadSemantic"] == "tip_load"
    assert out.load.metrics["magnitude"] is None


# --- the facade seam ---------------------------------------------------------


@pytest.mark.parametrize("stage", _SETUP_STAGES)
def test_setup_stage_provenance_deterministic_agent(stage: WorkflowStage) -> None:
    st = run_node(stage, run_id="r", user_request="钢制支架，固定底面，端部 5kN 集中力")
    assert st.stage is stage
    assert st.provenance is StageProvenance.DETERMINISTIC_AGENT
    assert st.agent_explanation
    assert st.next_action


@pytest.mark.parametrize(
    "stage",
    [WorkflowStage.CAD_IMPORT, WorkflowStage.MESH_GENERATION, WorkflowStage.SOLVER_RUN],
)
def test_facade_unwired_stage_still_raises(stage: WorkflowStage) -> None:
    # The barrier holds for every tool/artifact-bound stage — the facade never silently
    # fabricates agent output for an un-wired stage.
    with pytest.raises(NotImplementedError):
        run_node(stage, run_id="r", user_request="钢制支架静力分析")


# --- the live pipeline seam: honest scripted fallbacks -----------------------


def test_pipeline_setup_stages_scripted_without_request() -> None:
    """No genuine user_request (label-only / no-label) -> the 3 setup stages stay
    scripted_demo (the guard chain holds, mirroring PROJECT_INTAKE)."""
    for run in (
        MockWorkflowStore().run_sync(label=None),
        MockWorkflowStore().run_sync(label="monitor"),
    ):
        by_stage = {s.stage: s for s in run.stages}
        for stage in _SETUP_STAGES:
            assert by_stage[stage].provenance is StageProvenance.SCRIPTED_DEMO


def test_pipeline_setup_agent_driven_on_genuine_request() -> None:
    run = MockWorkflowStore().run_sync(user_request="铝合金支架，固定安装面，顶面 5kN 压力")
    by_stage = {s.stage: s for s in run.stages}
    for stage in _SETUP_STAGES:
        assert by_stage[stage].provenance is StageProvenance.DETERMINISTIC_AGENT
    # the material decision reflects the request (aluminum), not a hardcoded string
    mat_metrics = by_stage[WorkflowStage.MATERIAL_ASSIGNMENT].metrics.model_dump(
        by_alias=True, exclude_none=True
    )
    assert "Aluminum" in mat_metrics["materialName"]


def test_pipeline_setup_scripted_on_failure_injection() -> None:
    """A demo failure injected at a setup stage is NOT an agent decision (error set)
    -> that stage stays scripted_demo (ADR-028 D2)."""
    run = MockWorkflowStore().run_sync(
        user_request="钢制支架静力分析",
        fail_at_stage=WorkflowStage.MATERIAL_ASSIGNMENT,
    )
    mat = next(s for s in run.stages if s.stage is WorkflowStage.MATERIAL_ASSIGNMENT)
    assert mat.status is StageStatus.FAILED
    assert mat.provenance is StageProvenance.SCRIPTED_DEMO
