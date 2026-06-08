"""ADR-028 P-geomplan — the deterministic geometry-PLANNING node behind the facade.

The GEOMETRY_VALIDATION stage is now decided by a real rule-based planner
(agents.state_projection.analyze_geometry_plan) instead of a hardcoded string. The
honesty-critical point: this is geometry PLANNING, NOT validation — no CAD kernel runs,
no STEP is generated, checkers.geometry_checker is NOT called. These tests prove:

* the decision is INPUT-DEPENDENT (different requests -> different geometry family), and
* it DISCLOSES (hard assertion) that no CAD kernel / defect check ran, and the metrics
  carry NO measurement-shaped keys (shortEdges/slivers) — so provenance=deterministic_agent
  can never be read as "the geometry was validated"; and
* the live pipeline flips GEOMETRY_VALIDATION to deterministic_agent ONLY on a genuine
  request — a no-request run keeps the scripted_demo fallback (incl. its fabricated
  shortEdges metric), and a failure injection stays scripted (ADR-028 D2).
"""

from __future__ import annotations

import pytest

from app.services.workflow.mock_pipeline import MockWorkflowStore
from app.workbench.agent_facade import run_node
from schemas.workflow_state import StageProvenance, StageStatus, WorkflowStage

from agents.state_projection import analyze_geometry_plan

_MEASUREMENT_KEYS = ("shortEdges", "slivers", "selfIntersections")


# --- the planner is genuine + input-dependent --------------------------------


def test_geometry_plan_family_input_dependent() -> None:
    wing = analyze_geometry_plan("分析这个机翼的气动结构强度")
    bracket = analyze_geometry_plan("钢制支架静力分析")
    assert wing.metrics["geometryFamily"] == "naca_wing"
    assert wing.metrics["fromHint"] is True
    assert bracket.metrics["geometryFamily"] == "bracket"
    assert bracket.metrics["fromHint"] is True
    # genuine rule-based agent: different inputs -> different geometry-family decisions
    assert wing.metrics["geometryFamily"] != bracket.metrics["geometryFamily"]


def test_geometry_plan_defaults_when_no_hint() -> None:
    """No geometry keyword -> documented placeholder family, AND the explanation discloses
    the default (the D2 honesty condition, asserted hard — not just prose)."""
    out = analyze_geometry_plan("随便帮我分析一下")
    assert out.metrics["fromHint"] is False
    assert out.metrics["geometryFamily"] == "structural_solid"
    assert "默认" in out.agent_explanation


# --- the honesty contract: planning, NOT validation --------------------------


def test_geometry_plan_discloses_no_cad_kernel() -> None:
    """provenance=deterministic_agent must never be read as "geometry validated": the
    explanation MUST state no CAD kernel / no defect check / no LLM ran."""
    expl = analyze_geometry_plan("钢制支架静力分析").agent_explanation
    assert "未运行 CAD 内核" in expl
    assert "未做缺陷校验" in expl
    assert "未调用 LLM" in expl


def test_geometry_plan_metrics_have_no_measurement_keys() -> None:
    """The metrics must carry planning-intent + machine-checkable honesty flags ONLY —
    NEVER measurement-shaped defect keys, which would lie about a check having run."""
    out = analyze_geometry_plan("钢制支架静力分析")
    assert out.metrics["cadKernelRan"] is False
    assert out.metrics["defectCheckRun"] is False
    assert "geometryFamily" in out.metrics
    for key in _MEASUREMENT_KEYS:
        assert key not in out.metrics


# --- the facade seam ---------------------------------------------------------


def test_geometry_validation_provenance_deterministic_agent() -> None:
    st = run_node(WorkflowStage.GEOMETRY_VALIDATION, run_id="r", user_request="钢制支架静力分析")
    assert st.stage is WorkflowStage.GEOMETRY_VALIDATION
    assert st.provenance is StageProvenance.DETERMINISTIC_AGENT
    assert st.agent_explanation
    assert st.next_action


def test_geometry_validation_current_object_not_bracket_solid() -> None:
    """current_object must be a planning-intent label, NEVER 'bracket_solid' (the scripted
    spec value) which would imply a real solid had been validated."""
    st = run_node(WorkflowStage.GEOMETRY_VALIDATION, run_id="r", user_request="钢制支架静力分析")
    assert st.current_object == "geometry_plan"
    assert st.current_object != "bracket_solid"


# --- the live pipeline seam --------------------------------------------------


def test_pipeline_geometry_agent_driven_on_genuine_request() -> None:
    run = MockWorkflowStore().run_sync(user_request="铝合金支架，固定安装面，顶面 5kN 压力")
    geom = next(s for s in run.stages if s.stage is WorkflowStage.GEOMETRY_VALIDATION)
    assert geom.provenance is StageProvenance.DETERMINISTIC_AGENT
    metrics = geom.metrics.model_dump(by_alias=True, exclude_none=True)
    assert metrics["geometryFamily"] == "bracket"
    # the fabricated scripted defect metrics are GONE on the agent-driven path
    for key in _MEASUREMENT_KEYS:
        assert key not in metrics


def test_pipeline_geometry_scripted_without_request() -> None:
    """No genuine user_request -> GEOMETRY_VALIDATION stays scripted_demo, and the scripted
    fallback (incl. its fabricated shortEdges metric) is UNCHANGED by this slice."""
    for run in (
        MockWorkflowStore().run_sync(label=None),
        MockWorkflowStore().run_sync(label="monitor"),
    ):
        geom = next(s for s in run.stages if s.stage is WorkflowStage.GEOMETRY_VALIDATION)
        assert geom.provenance is StageProvenance.SCRIPTED_DEMO
        metrics = geom.metrics.model_dump(by_alias=True, exclude_none=True)
        assert metrics["shortEdges"] == 2  # scripted Tier-0 demo metric, left intact


def test_pipeline_geometry_scripted_on_failure_injection() -> None:
    """A demo failure injected at GEOMETRY_VALIDATION is NOT an agent decision (error set)
    -> the stage stays scripted_demo (ADR-028 D2)."""
    run = MockWorkflowStore().run_sync(
        user_request="钢制支架静力分析",
        fail_at_stage=WorkflowStage.GEOMETRY_VALIDATION,
    )
    geom = next(s for s in run.stages if s.stage is WorkflowStage.GEOMETRY_VALIDATION)
    assert geom.status is StageStatus.FAILED
    assert geom.provenance is StageProvenance.SCRIPTED_DEMO
