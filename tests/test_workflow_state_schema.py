"""Contract tests for the Agentic FEA Workflow Runtime stage state schema.

Pins the plan §3 invariants: the 13-stage / 5-status enums, the camelCase
wire shape matching the per-task JSON contract, the totality of the
WorkflowStage→ws_events.Stage mapping (so every stage can emit an ADR-014
event), and the reuse of FaultClass for stage errors.
"""

from __future__ import annotations

import pytest

from schemas.sim_state import FaultClass
from schemas.workflow_state import (
    CANONICAL_STAGE_ORDER,
    WORKFLOW_STAGE_TO_WS_STAGE,
    StageArtifacts,
    StageError,
    StageMetrics,
    StageProvenance,
    StageState,
    StageStatus,
    WorkflowStage,
    ws_stage_for,
)
from schemas.ws_events import Stage


def test_thirteen_stages_in_canonical_order() -> None:
    assert len(WorkflowStage) == 13
    assert len(CANONICAL_STAGE_ORDER) == 13
    # the worked example in the plan uses this exact value
    assert WorkflowStage.MESH_QUALITY_CHECK.value == "mesh_quality_check"
    # order starts at intake and ends at report
    assert CANONICAL_STAGE_ORDER[0] is WorkflowStage.PROJECT_INTAKE
    assert CANONICAL_STAGE_ORDER[-1] is WorkflowStage.REPORT_GENERATION


def test_five_statuses_including_warning() -> None:
    assert {s.value for s in StageStatus} == {
        "pending",
        "running",
        "success",
        "warning",
        "failed",
    }


def test_every_stage_maps_to_a_valid_ws_stage() -> None:
    """Totality: every fine stage projects onto a coarse ADR-014 Stage so a
    StageState can drive the existing node.* event vocabulary."""
    valid_ws_stages = set(Stage.__args__)  # Literal members
    for stage in WorkflowStage:
        assert stage in WORKFLOW_STAGE_TO_WS_STAGE, f"{stage} missing from mapping"
        mapped = ws_stage_for(stage)
        assert mapped in valid_ws_stages, f"{stage} -> {mapped!r} not a ws Stage"


def test_stage_state_serializes_to_request_json_shape() -> None:
    """by_alias=True yields exactly the plan §3 per-task contract keys."""
    state = StageState(
        run_id="bracket_20260603T120000Z",
        stage=WorkflowStage.MESH_QUALITY_CHECK,
        status=StageStatus.RUNNING,
        progress=0.0,
        current_object="bracket_hole_region",
        description="正在检查支架孔边缘区域网格质量",
        metrics=StageMetrics(
            nodes=0,
            elements=0,
            bad_elements=0,
            max_aspect_ratio=0.0,
            min_jacobian=0.0,
            estimated_solve_time="~12s",
        ),
        agent_explanation="当前步骤在做什么、为什么重要、发现了什么问题、下一步建议是什么",
        next_action="local refinement at bracket_hole_region",
    )
    wire = state.model_dump(by_alias=True)
    # the exact camelCase keys the plan/frontend expect
    for key in (
        "runId",
        "stage",
        "status",
        "progress",
        "currentObject",
        "description",
        "metrics",
        "warnings",
        "errors",
        "artifacts",
        "agentExplanation",
        "nextAction",
    ):
        assert key in wire, f"missing wire key {key}"
    assert wire["runId"] == "bracket_20260603T120000Z"
    assert wire["stage"] == "mesh_quality_check"
    assert wire["status"] == "running"
    assert wire["currentObject"] == "bracket_hole_region"
    assert wire["metrics"]["badElements"] == 0
    assert wire["metrics"]["maxAspectRatio"] == 0.0
    assert wire["metrics"]["estimatedSolveTime"] == "~12s"
    assert set(wire["artifacts"].keys()) == {
        "geometryPreview",
        "meshPreview",
        "resultPreview",
        "logFile",
        "reportFile",
    }


def test_stage_state_accepts_camel_or_snake_input() -> None:
    """populate_by_name=True: inputs may use snake_case or camelCase."""
    a = StageState(run_id="r1", stage=WorkflowStage.SOLVER_RUN)
    b = StageState.model_validate({"runId": "r1", "stage": "solver_run"})
    assert a.run_id == b.run_id == "r1"
    assert a.stage is b.stage is WorkflowStage.SOLVER_RUN


def test_stage_error_uses_faultclass() -> None:
    err = StageError(fault_class=FaultClass.MESH_JACOBIAN, message="negative jacobian")
    state = StageState(
        run_id="r1",
        stage=WorkflowStage.MESH_QUALITY_CHECK,
        status=StageStatus.FAILED,
        errors=[err],
    )
    wire = state.model_dump(by_alias=True)
    assert wire["errors"][0]["faultClass"] == "mesh_jacobian"
    assert wire["status"] == "failed"


def test_progress_is_bounded_0_to_1() -> None:
    with pytest.raises(ValueError):
        StageState(run_id="r1", stage=WorkflowStage.SOLVER_RUN, progress=1.5)
    with pytest.raises(ValueError):
        StageState(run_id="r1", stage=WorkflowStage.SOLVER_RUN, progress=-0.1)


def test_unknown_top_level_field_is_rejected() -> None:
    """extra='forbid' on StageState guards the contract (metrics stays open)."""
    with pytest.raises(ValueError):
        StageState.model_validate({"runId": "r1", "stage": "solver_run", "bogusField": 1})


def test_provenance_defaults_to_scripted_demo_and_serializes() -> None:
    """ADR-028 D2: the additive `provenance` field defaults to SCRIPTED_DEMO so
    every un-wired stage stays honestly labeled as synthetic demo prose, and it
    rides the camelCase wire as a first-class key (NOT inferred by the UI)."""
    state = StageState(run_id="r1", stage=WorkflowStage.PROJECT_INTAKE)
    assert state.provenance is StageProvenance.SCRIPTED_DEMO
    wire = state.model_dump(by_alias=True)
    assert wire["provenance"] == "scripted_demo"


def test_provenance_accepts_agent_classes() -> None:
    """The three honest provenance classes round-trip on the wire."""
    assert {p.value for p in StageProvenance} == {
        "scripted_demo",
        "deterministic_agent",
        "llm_agent",
    }
    state = StageState(
        run_id="r1",
        stage=WorkflowStage.PROJECT_INTAKE,
        provenance=StageProvenance.DETERMINISTIC_AGENT,
    )
    assert state.model_dump(by_alias=True)["provenance"] == "deterministic_agent"
    # snake or camel input both populate the field (populate_by_name=True).
    via_wire = StageState.model_validate(
        {"runId": "r1", "stage": "project_intake", "provenance": "llm_agent"}
    )
    assert via_wire.provenance is StageProvenance.LLM_AGENT


def test_provenance_rejects_unknown_value() -> None:
    with pytest.raises(ValueError):
        StageState.model_validate({"runId": "r1", "stage": "project_intake", "provenance": "human"})


def test_metrics_allows_stage_specific_extras() -> None:
    """StageMetrics is extra='allow' so a stage can attach its own metric."""
    m = StageMetrics.model_validate({"nodes": 100, "customStageMetric": 7})
    dumped = m.model_dump(by_alias=True)
    assert dumped["nodes"] == 100
    assert dumped["customStageMetric"] == 7


def test_artifacts_default_to_null_refs() -> None:
    arts = StageArtifacts()
    wire = arts.model_dump(by_alias=True)
    assert all(v is None for v in wire.values())
