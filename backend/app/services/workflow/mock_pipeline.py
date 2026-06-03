"""Mock FEA pipeline — drives the 13 WorkflowStages with synthetic data.

Produces real :class:`schemas.workflow_state.StageState` objects (the same wire
contract the real runtime will emit), so the Monitor UI and the stage protocol
are provable before Trigger.dev (M2) and the real solver (M4). No `ccx` runs;
the solve/result stages go through :class:`MockFEABackend` so the FEABackend
seam is exercised end-to-end.

Two drivers share one stage-computation core:
* :meth:`MockWorkflowStore.run_sync` — synchronous, no sleeps (tests + ``?sync``);
* :meth:`MockWorkflowStore._advance` — async with per-tick sleeps so a polling
  Monitor shows live progress.
"""

from __future__ import annotations

import asyncio
import itertools
from dataclasses import dataclass, field
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from aeron.protocols.fea_backend import CasePackage, SolveOptions, SolveStatusCode
from schemas.sim_state import FaultClass
from schemas.workflow_state import (
    CANONICAL_STAGE_ORDER,
    StageArtifacts,
    StageError,
    StageMetrics,
    StageState,
    StageStatus,
    WorkflowStage,
)

from .mock_backend import MockFEABackend

# Stages that complete as WARNING (passing-with-caveats) in the canonical demo.
_WARNING_STAGES = frozenset({WorkflowStage.MESH_QUALITY_CHECK, WorkflowStage.RESULT_ANALYSIS})

# Default wall-clock per progress tick (3 ticks/stage). Small so a full run is
# ~6-9s — watchable but not slow. Tests use run_sync (no sleeps).
DEFAULT_TICK_DELAY_S = 0.45


@dataclass(frozen=True)
class StageSpec:
    """Static demo content for one stage."""

    current_object: str
    description: str
    metrics: dict = field(default_factory=dict)  # camelCase keys
    warnings: list[str] = field(default_factory=list)
    agent_explanation: str = ""
    next_action: str = ""
    artifacts: dict = field(default_factory=dict)
    fault_class: FaultClass = FaultClass.UNKNOWN  # used if this stage is the fail point


STAGE_SPECS: dict[WorkflowStage, StageSpec] = {
    WorkflowStage.PROJECT_INTAKE: StageSpec(
        current_object="user_request",
        description="解析用户输入与分析目标",
        metrics={"physics": "linear_static", "objectives": 3},
        agent_explanation="读取用户的结构分析意图，确定物理类型（线弹性静力）与目标量（应力 / 位移 / 安全系数）。",
        next_action="进入 CAD 几何导入。",
        fault_class=FaultClass.UNKNOWN,
    ),
    WorkflowStage.CAD_IMPORT: StageSpec(
        current_object="bracket.step",
        description="导入 CAD 几何",
        metrics={"parts": 1, "solids": 1, "faces": 34, "format": "STEP"},
        agent_explanation="加载 STEP 几何，统计实体与面数，确认拓扑可用。",
        next_action="对几何做缺陷校验。",
        fault_class=FaultClass.GEOMETRY_INVALID,
    ),
    WorkflowStage.GEOMETRY_VALIDATION: StageSpec(
        current_object="bracket_solid",
        description="检查几何缺陷（短边 / 碎面 / 自交）",
        metrics={"shortEdges": 2, "slivers": 0, "selfIntersections": 0},
        agent_explanation="扫描小特征：发现 2 条短边（<0.5mm），不影响求解但可能拉低局部网格质量。",
        next_action="赋予材料；短边可在网格阶段局部处理。",
        fault_class=FaultClass.GEOMETRY_INVALID,
    ),
    WorkflowStage.MATERIAL_ASSIGNMENT: StageSpec(
        current_object="bracket_solid",
        description="赋予各向同性钢材",
        metrics={"youngsModulusPa": 2.1e11, "poissonRatio": 0.3, "unassignedBodies": 0},
        agent_explanation="E=210 GPa、ν=0.30 赋给全体；检查是否有未赋材料的体（会被标红）。",
        next_action="设置边界条件。",
        fault_class=FaultClass.UNKNOWN,
    ),
    WorkflowStage.BOUNDARY_CONDITIONS: StageSpec(
        current_object="mount_face",
        description="设置约束（固定安装面）",
        metrics={"constraints": 1, "rigidBodyModes": 0},
        agent_explanation="安装面施加全约束；检测是否欠约束（残留刚体模态会导致求解奇异）。",
        next_action="设置载荷工况。",
        fault_class=FaultClass.UNKNOWN,
    ),
    WorkflowStage.LOAD_CASES: StageSpec(
        current_object="load_face",
        description="设置载荷工况",
        metrics={"loadCases": 1, "totalLoadN": 5000, "type": "pressure"},
        agent_explanation="顶面施加 5 kN 等效法向压力，单工况。",
        next_action="生成网格。",
        fault_class=FaultClass.UNKNOWN,
    ),
    WorkflowStage.MESH_GENERATION: StageSpec(
        current_object="bracket_solid",
        description="生成二次四面体网格",
        metrics={"nodes": 18432, "elements": 11260, "elementType": "C3D10"},
        agent_explanation="选用二次单元（C3D10）以捕捉弯曲与应力梯度；生成 11260 单元。",
        next_action="检查网格质量。",
        fault_class=FaultClass.MESH_RESOLUTION,
    ),
    WorkflowStage.MESH_QUALITY_CHECK: StageSpec(
        current_object="bracket_hole_region",
        description="检查网格质量（长宽比 / 雅可比）",
        metrics={
            "nodes": 18432,
            "elements": 11260,
            "badElements": 142,
            "maxAspectRatio": 12.4,
            "minJacobian": 0.03,
            "estimatedSolveTime": "~14s",
        },
        warnings=["142 个低质量单元集中在 bracket_hole_region（aspect ratio > 10）。"],
        agent_explanation="孔边附近 142 个畸形单元，长宽比超过 10，可能影响该处应力精度——但不阻断求解。",
        next_action="建议在孔边做局部加密后重划；当前可继续，但孔边应力结果需谨慎解读。",
        fault_class=FaultClass.MESH_JACOBIAN,
    ),
    WorkflowStage.SOLVER_RUN: StageSpec(
        current_object="full_model",
        description="运行求解器（CalculiX · 此处为 Mock）",
        metrics={"step": "static", "increment": 1},
        agent_explanation="线性静力一步求解；Mock 后端返回合成 .frd，真实接入时此处调用 ccx。",
        next_action="监控收敛与误差。",
        fault_class=FaultClass.SOLVER_CONVERGENCE,
    ),
    WorkflowStage.CONVERGENCE_MONITORING: StageSpec(
        current_object="residual",
        description="监控收敛 / 误差",
        metrics={"finalResidual": 1e-9, "converged": True, "increments": 1},
        agent_explanation="残差降至 1e-9，线性问题一步收敛；若非线性会在此追踪每个增量步。",
        next_action="后处理提取场量。",
        fault_class=FaultClass.SOLVER_TIMESTEP,
    ),
    WorkflowStage.POST_PROCESSING: StageSpec(
        current_object="result_field",
        description="提取应力 / 位移场",
        metrics={"frames": 1, "fields": "S,U"},
        agent_explanation="从 .frd 解析 von Mises 应力场与位移场，准备工程量分析。",
        next_action="分析应力 / 位移 / 安全系数。",
        fault_class=FaultClass.REFERENCE_MISMATCH,
    ),
    WorkflowStage.RESULT_ANALYSIS: StageSpec(
        current_object="hole_edge",
        description="应力 / 位移 / 安全系数分析",
        # metrics filled at runtime from MockFEABackend.parse_results()
        metrics={},
        agent_explanation="定位峰值 von Mises 与最大位移，按屈服强度计算安全系数。",
        next_action="若安全系数偏低，建议孔边圆角或加厚；否则生成报告。",
        fault_class=FaultClass.REFERENCE_MISMATCH,
    ),
    WorkflowStage.REPORT_GENERATION: StageSpec(
        current_object="report",
        description="生成报告",
        metrics={"sections": 7},
        agent_explanation="汇总几何 / 网格 / 材料 / 边界 / 载荷 / 结果 / 安全系数为一份可下载报告。",
        next_action="完成；可下载报告，或调整设计回到 CAD 导入重跑。",
        fault_class=FaultClass.UNKNOWN,
    ),
}

_PROGRESS_TICKS = (0.34, 0.67, 1.0)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class MockRun(BaseModel):
    """A single mock pipeline run + the live state of all 13 stages."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    run_id: str
    label: str | None = None
    status: StageStatus = StageStatus.PENDING
    started_at: str
    finished_at: str | None = None
    fail_at_stage: WorkflowStage | None = None
    current_stage: WorkflowStage | None = None
    stages: list[StageState]


def _initial_stages(run_id: str) -> list[StageState]:
    return [
        StageState(
            run_id=run_id,
            stage=stage,
            status=StageStatus.PENDING,
            current_object=STAGE_SPECS[stage].current_object,
            description=STAGE_SPECS[stage].description,
        )
        for stage in CANONICAL_STAGE_ORDER
    ]


def _build_stage_state(
    run_id: str,
    stage: WorkflowStage,
    status: StageStatus,
    progress: float,
    *,
    backend: MockFEABackend,
    error: StageError | None = None,
) -> StageState:
    spec = STAGE_SPECS[stage]
    metrics_src = dict(spec.metrics)
    artifacts = dict(spec.artifacts)

    # Wire the FEABackend in at the solve + result stages.
    if stage is WorkflowStage.RESULT_ANALYSIS:
        from aeron.protocols.fea_backend import SolveOutcome, SolveStatus

        outcome = SolveOutcome(
            case_id="mock", status=SolveStatus(code=SolveStatusCode.OK), wall_clock_s=0.0
        )
        scalars = backend.parse_results(outcome).scalars
        sf = scalars["safety_factor"]
        metrics_src = {
            "maxVonMisesPa": scalars["max_von_mises_pa"],
            "maxDisplacementM": scalars["max_displacement_m"],
            "yieldPa": scalars["yield_pa"],
            "safetyFactor": round(sf, 3),
        }
    if stage is WorkflowStage.REPORT_GENERATION and status is StageStatus.SUCCESS:
        artifacts = {"report_file": f"/workflow/runs/{run_id}/report.md"}

    warnings = list(spec.warnings) if status is StageStatus.WARNING else []
    return StageState(
        run_id=run_id,
        stage=stage,
        status=status,
        progress=progress,
        current_object=spec.current_object,
        description=spec.description,
        metrics=StageMetrics.model_validate(metrics_src),
        warnings=warnings,
        errors=[error] if error else [],
        artifacts=StageArtifacts.model_validate(artifacts),
        agent_explanation=spec.agent_explanation,
        next_action=spec.next_action,
        updated_at=_now_iso(),
    )


def _terminal_status(stage: WorkflowStage) -> StageStatus:
    return StageStatus.WARNING if stage in _WARNING_STAGES else StageStatus.SUCCESS


def _overall(stages: list[StageState]) -> StageStatus:
    statuses = {s.status for s in stages}
    if StageStatus.FAILED in statuses:
        return StageStatus.FAILED
    if StageStatus.PENDING in statuses or StageStatus.RUNNING in statuses:
        return StageStatus.RUNNING
    if StageStatus.WARNING in statuses:
        return StageStatus.WARNING
    return StageStatus.SUCCESS


class MockWorkflowStore:
    """In-memory run store + async driver (singleton). M1 durability is
    in-process; durable persistence arrives with Trigger.dev at M2."""

    _counter = itertools.count(1)

    def __init__(self) -> None:
        self.runs: dict[str, MockRun] = {}

    def _new_run(self, label: str | None, fail_at_stage: WorkflowStage | None) -> MockRun:
        seq = next(self._counter)
        run_id = f"mock_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}_{seq:04d}"
        run = MockRun(
            run_id=run_id,
            label=label,
            status=StageStatus.PENDING,
            started_at=_now_iso(),
            fail_at_stage=fail_at_stage,
            stages=_initial_stages(run_id),
        )
        self.runs[run_id] = run
        return run

    def _stage_index(self, stage: WorkflowStage) -> int:
        return CANONICAL_STAGE_ORDER.index(stage)

    def _finalize(self, run: MockRun) -> None:
        run.finished_at = _now_iso()
        run.current_stage = None
        run.status = _overall(run.stages)

    def _fail_error(self, stage: WorkflowStage) -> StageError:
        spec = STAGE_SPECS[stage]
        return StageError(
            fault_class=spec.fault_class,
            message=f"injected failure at {stage.value}",
            detail="MockWorkflowStore fail_at_stage demo path",
        )

    def run_sync(
        self, label: str | None = None, fail_at_stage: WorkflowStage | None = None
    ) -> MockRun:
        """Run the whole pipeline with no sleeps (tests / ?sync). Returns the
        terminal run."""
        run = self._new_run(label, fail_at_stage)
        backend = MockFEABackend(
            force_fault=FaultClass.SOLVER_CONVERGENCE
            if fail_at_stage is WorkflowStage.SOLVER_RUN
            else None
        )
        run.status = StageStatus.RUNNING
        for idx, stage in enumerate(CANONICAL_STAGE_ORDER):
            run.current_stage = stage
            if fail_at_stage is stage:
                run.stages[idx] = _build_stage_state(
                    run.run_id, stage, StageStatus.FAILED, 1.0,
                    backend=backend, error=self._fail_error(stage),
                )
                break
            run.stages[idx] = _build_stage_state(
                run.run_id, stage, _terminal_status(stage), 1.0, backend=backend
            )
        self._finalize(run)
        return run

    async def _advance(self, run_id: str, tick_delay_s: float = DEFAULT_TICK_DELAY_S) -> None:
        run = self.runs[run_id]
        backend = MockFEABackend(
            force_fault=FaultClass.SOLVER_CONVERGENCE
            if run.fail_at_stage is WorkflowStage.SOLVER_RUN
            else None
        )
        run.status = StageStatus.RUNNING
        for idx, stage in enumerate(CANONICAL_STAGE_ORDER):
            run.current_stage = stage
            for p in _PROGRESS_TICKS:
                run.stages[idx] = _build_stage_state(
                    run.run_id, stage, StageStatus.RUNNING, p, backend=backend
                )
                await asyncio.sleep(tick_delay_s)
            if run.fail_at_stage is stage:
                run.stages[idx] = _build_stage_state(
                    run.run_id, stage, StageStatus.FAILED, 1.0,
                    backend=backend, error=self._fail_error(stage),
                )
                break
            run.stages[idx] = _build_stage_state(
                run.run_id, stage, _terminal_status(stage), 1.0, backend=backend
            )
        self._finalize(run)

    def trigger(
        self, label: str | None = None, fail_at_stage: WorkflowStage | None = None
    ) -> MockRun:
        """Create a run and schedule the async driver. Returns the initial run."""
        run = self._new_run(label, fail_at_stage)
        asyncio.create_task(self._advance(run.run_id))
        return run

    def get(self, run_id: str) -> MockRun | None:
        return self.runs.get(run_id)

    def list_runs(self, limit: int = 20) -> list[MockRun]:
        return list(self.runs.values())[-limit:][::-1]


# Module-level singleton (mirrors SolverService).
store = MockWorkflowStore()
