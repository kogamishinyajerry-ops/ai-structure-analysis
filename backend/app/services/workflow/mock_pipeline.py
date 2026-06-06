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
import tempfile
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import settings
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from aeron.protocols.fea_backend import SolveStatusCode
from schemas.sim_state import FaultClass
from schemas.workflow_state import (
    CANONICAL_STAGE_ORDER,
    StageArtifacts,
    StageError,
    StageMetrics,
    StageProvenance,
    StageState,
    StageStatus,
    WorkflowStage,
)

from . import real_le10
from .mock_backend import MockFEABackend


class StageOrderError(Exception):
    """Raised by run_one_stage when a stage is driven out of order or after a
    terminal failure (the M2 route maps this to HTTP 409)."""


# Stages that complete as WARNING (passing-with-caveats) in the canonical demo.
_WARNING_STAGES = frozenset({WorkflowStage.MESH_QUALITY_CHECK, WorkflowStage.RESULT_ANALYSIS})

# Stages routed through the real agent facade when a genuine user_request is present
# (ADR-028): intake (P1) + the three deterministic setup-planner stages (P-setup).
# Defined locally from schema enums — mock_pipeline must NOT import agents.* (ADR-015;
# only agent_facade.py may). The facade raises NotImplementedError for any other stage.
_AGENT_REQUEST_STAGES = frozenset(
    {
        WorkflowStage.PROJECT_INTAKE,
        WorkflowStage.MATERIAL_ASSIGNMENT,
        WorkflowStage.BOUNDARY_CONDITIONS,
        WorkflowStage.LOAD_CASES,
    }
)

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

# M4 — LE10-accurate stage content, used when settings.workflow_real_solver is on.
# The solver_run / post_processing / result_analysis metrics are OVERWRITTEN at
# runtime from the real ccx solve (see _build_stage_state's real branch); the rest
# describe the actual NAFEMS LE10 case so the displayed narrative is not a lie.
LE10_STAGE_SPECS: dict[WorkflowStage, StageSpec] = {
    WorkflowStage.PROJECT_INTAKE: StageSpec(
        current_object="user_request",
        description="解析分析目标（NAFEMS LE10 基准）",
        metrics={"physics": "linear_static", "benchmark": "NAFEMS LE10", "target": "sigma_yy@D"},
        agent_explanation="目标：复现 NAFEMS LE10「厚板受压」基准，比对发布参考 σ_yy(D) = −5.38 MPa。",
        next_action="导入 LE10 厚板几何。",
    ),
    WorkflowStage.CAD_IMPORT: StageSpec(
        current_object="le10_thick_plate",
        description="导入 LE10 厚板几何（椭圆板，四分之一对称）",
        metrics={"outerEllipseM": "3.25 x 2.75", "innerEllipseM": "2.0 x 1.0", "thicknessM": 0.6},
        agent_explanation="LE10 厚椭圆板：外椭圆半轴 3.25×2.75 m，内椭圆孔 2.0×1.0 m，厚 0.6 m，取四分之一对称模型。",
        next_action="校验几何。",
    ),
    WorkflowStage.GEOMETRY_VALIDATION: StageSpec(
        current_object="le10_quarter",
        description="校验四分之一对称几何",
        metrics={"quarterModel": 1, "symmetryPlanes": 2},
        agent_explanation="确认 x=0 与 y=0 两个对称面、外椭圆边与厚度方向（z∈[−0.3,+0.3]）。",
        next_action="赋予材料。",
    ),
    WorkflowStage.MATERIAL_ASSIGNMENT: StageSpec(
        current_object="le10_steel",
        description="赋予各向同性钢材（LE10 规范）",
        metrics={"youngsModulusPa": 2.1e11, "poissonRatio": 0.3},
        agent_explanation="E=210 GPa、ν=0.30（LE10 规范材料；密度对线性静力目标无关）。",
        next_action="设置对称与边界约束。",
    ),
    WorkflowStage.BOUNDARY_CONDITIONS: StageSpec(
        current_object="symmetry_and_rim",
        description="设置对称面与外缘约束",
        metrics={"constraints": 4, "rigidBodyModes": 0},
        agent_explanation="x=0 面 ux=0；y=0 面 uy=0（含 D 点）；外椭圆缘面内固定 ux=uy=0；外缘中面 uz=0（替代 NAFEMS EE' 线，去除 z 刚体）。",
        next_action="施加压力载荷。",
    ),
    WorkflowStage.LOAD_CASES: StageSpec(
        current_object="upper_surface",
        description="上表面施加均布压力",
        metrics={"loadCases": 1, "pressurePa": 1.0e6, "type": "normal_pressure"},
        agent_explanation="上表面施加 1.0 MPa 法向均布压力（向下 −z），单工况。",
        next_action="生成网格。",
    ),
    WorkflowStage.MESH_GENERATION: StageSpec(
        current_object="le10_quarter",
        description="生成二次六面体网格（C3D20）",
        metrics={
            "nodes": real_le10.LE10_NODE_COUNT,
            "elements": real_le10.LE10_ELEMENT_COUNT,
            "elementType": real_le10.LE10_ELEMENT_TYPE,
            "meshNcNrNt": "40 x 20 x 6",
        },
        agent_explanation="结构化六面体 C3D20 全积分单元，40×20×6（4800 单元 / 22815 节点）；该网格已通过单调收敛验证。",
        next_action="检查网格质量。",
    ),
    WorkflowStage.MESH_QUALITY_CHECK: StageSpec(
        current_object="inner_edge",
        description="检查网格质量",
        metrics={
            "nodes": real_le10.LE10_NODE_COUNT,
            "elements": real_le10.LE10_ELEMENT_COUNT,
            "badElements": 0,
            "structured": True,
        },
        agent_explanation="结构化 transfinite 网格，无畸形单元；孔内缘（含 D 点）应力梯度由全积分 C3D20 捕捉。",
        next_action="运行 CalculiX 求解。",
    ),
    WorkflowStage.SOLVER_RUN: StageSpec(
        current_object="le10_model",
        description="运行求解器（CalculiX · 真实 ccx）",
        metrics={"step": "static", "increment": 1},  # overwritten with real solve metrics
        agent_explanation="对 LE10 模型做线性静力一步求解，调用真实 ccx（版本见 ccxVersion 指标）。",
        next_action="监控收敛。",
        fault_class=FaultClass.SOLVER_CONVERGENCE,
    ),
    WorkflowStage.CONVERGENCE_MONITORING: StageSpec(
        current_object="residual",
        description="监控收敛",
        metrics={"converged": True, "increments": 1, "analysis": "linear_static"},
        agent_explanation="线性静力一步收敛；ccx SPOOLES 直接求解，无迭代残差曲线。",
        next_action="后处理提取场量。",
    ),
    WorkflowStage.POST_PROCESSING: StageSpec(
        current_object="result_field",
        description="从 .frd 提取应力 / 位移场",
        metrics={"frames": 1, "fields": "S,U"},  # nodes filled at runtime
        agent_explanation="解析 ccx 输出 .frd，提取应力张量 S 与位移 U（逐节点，未平均）。",
        next_action="提取 D 点 σ_yy 并比对基准。",
    ),
    WorkflowStage.RESULT_ANALYSIS: StageSpec(
        current_object="point_D",
        description="提取 σ_yy(D) 并比对 NAFEMS 基准",
        metrics={},  # filled at runtime from the real benchmark extraction
        agent_explanation="在 D 点 (2.0, 0, +0.3) 读取 σ_yy，按 ±3% 容差比对发布参考 −5.38 MPa。",
        next_action="生成基准吻合报告。",
        fault_class=FaultClass.REFERENCE_MISMATCH,
    ),
    WorkflowStage.REPORT_GENERATION: StageSpec(
        current_object="report",
        description="生成基准吻合报告",
        metrics={"sections": 5},
        agent_explanation="汇总几何 / 材料 / 边界 / 载荷 / 网格 / σ_yy(D) 与残差为一份基准吻合报告。",
        next_action="完成（Tier 1 真求解，比对 Tier-2 公开基准；非签字验证）。",
    ),
}

_PROGRESS_TICKS = (0.34, 0.67, 1.0)


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class MockRun(BaseModel):
    """A single mock pipeline run + the live state of all 13 stages."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    run_id: str
    label: str | None = None
    # ADR-028 P1: the genuine natural-language analysis intent, DISTINCT from the
    # display `label`. Only a real request drives the PROJECT_INTAKE agent node;
    # a display label (the Monitor defaults it to "monitor") must NOT be treated
    # as intake text, or the stage would falsely claim provenance=deterministic_agent
    # for a run with no real user request (Codex ADR-028-P1 R0 P1).
    user_request: str | None = None
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


def _le10_real_metrics(stage: WorkflowStage, solve_ctx: dict) -> dict | None:
    """Real-solve metrics for the three number-stages (M4). None → use the spec's."""
    if stage is WorkflowStage.SOLVER_RUN:
        return {
            "step": "static",
            "increment": 1,
            "ccxVersion": solve_ctx.get("ccx_version"),
            "wallTimeS": round(solve_ctx.get("wall_time_s") or 0.0, 2),
            "converged": bool(solve_ctx.get("converged")),
        }
    if stage is WorkflowStage.POST_PROCESSING:
        return {"frames": 1, "fields": "S,U", "nodes": solve_ctx.get("node_count")}
    if stage is WorkflowStage.RESULT_ANALYSIS:
        b = solve_ctx.get("benchmark", {})
        return {
            "benchmark": "NAFEMS LE10",
            "observedSigmaYyMpa": round((b.get("sigma_yy_pa") or 0.0) / 1e6, 4),
            "targetSigmaYyMpa": round((b.get("target_pa") or 0.0) / 1e6, 2),
            "residualPct": round(b.get("residual_pct") or 0.0, 2),
            "tolerancePct": b.get("tolerance_pct"),
            "verdict": b.get("verdict"),
        }
    return None


def _build_stage_state(
    run_id: str,
    stage: WorkflowStage,
    status: StageStatus,
    progress: float,
    *,
    backend: MockFEABackend,
    specs: dict[WorkflowStage, StageSpec] = STAGE_SPECS,
    solve_ctx: dict | None = None,
    error: StageError | None = None,
    user_request: str | None = None,
) -> StageState:
    # ADR-028 (D4 facade seam): route the genuinely agent-driven stages through the
    # real agent nodes when there is genuine user input to analyze and we are on the
    # mock-demo specs path. Wired today: PROJECT_INTAKE (rule-based intake, P1) and the
    # three setup-planner stages MATERIAL_ASSIGNMENT / BOUNDARY_CONDITIONS / LOAD_CASES
    # (deterministic analyze_setup, P-setup). Delegation goes through the ADR-015 choke
    # point backend/app/workbench/agent_facade.py. Guards keeping this surgical + honest:
    #   * error set       → demo failure injection is NOT agent-authored → scripted;
    #   * specs ≠ mock     → the LE10 real-benchmark path stays scripted until later;
    #   * no user_request  → nothing for the agent to analyze → scripted_demo.
    # Each returned StageState carries provenance=deterministic_agent; every OTHER stage
    # keeps the default scripted_demo, so wiring these cannot relabel the rest (ADR-028
    # D2). The tool/artifact-bound stages stay scripted (the facade raises for them).
    if (
        stage in _AGENT_REQUEST_STAGES
        and error is None
        and specs is STAGE_SPECS
        and user_request
        and user_request.strip()
    ):
        from app.workbench.agent_facade import run_node as _run_agent_node

        return _run_agent_node(
            stage,
            run_id=run_id,
            user_request=user_request,
            status=status,
            progress=progress,
            allow_llm=False,
        )

    spec = specs[stage]
    metrics_src = dict(spec.metrics)
    artifacts = dict(spec.artifacts)

    if solve_ctx is not None:
        # M4 real path: real ccx solve metrics for solve/post/result stages.
        real_metrics = _le10_real_metrics(stage, solve_ctx)
        if real_metrics is not None:
            metrics_src = real_metrics
        if stage is WorkflowStage.SOLVER_RUN and solve_ctx.get("frd_path"):
            artifacts = {"log_file": solve_ctx["frd_path"]}
    elif stage is WorkflowStage.RESULT_ANALYSIS and specs is STAGE_SPECS:
        # Mock path ONLY (canned scalars from MockFEABackend). Gated on the mock
        # specs so the real path NEVER synthesizes mock numbers when solve_ctx is
        # absent (e.g. process restart / cache miss) — it emits the spec's empty
        # metrics instead, which a verdict-aware terminal status flags (Codex M4 R0 P1).
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

    # ADR-028 P3 (D4 facade seam): the reviewer gate's "next step" is a REAL routing
    # decision, not a hardcoded string. At RESULT_ANALYSIS, on the mock-demo happy path
    # (no injected failure, mock specs, stage completed), consult the real router node
    # (agents.router.route_reviewer) via the facade for which agent runs next. Only this
    # stage's provenance flips to deterministic_agent; the verdict it consumes is the
    # (scripted) demo stage status, so the explanation attributes ONLY the routing — not
    # the result — to the agent (ADR-028 D2; mirrors the PROJECT_INTAKE intake guard).
    # The full re-run / human_fallback branches are proven by unit tests; the demo
    # happy path only exercises accept -> viz.
    provenance = StageProvenance.SCRIPTED_DEMO
    agent_explanation = spec.agent_explanation
    next_action = spec.next_action
    if (
        stage is WorkflowStage.RESULT_ANALYSIS
        and error is None
        and specs is STAGE_SPECS
        and solve_ctx is None
        and status in (StageStatus.SUCCESS, StageStatus.WARNING)
    ):
        from app.workbench.agent_facade import decide_route as _decide_route

        verdict = "Accept" if status is StageStatus.SUCCESS else "Accept with Note"
        # Be explicit that the verdict itself is scripted demo state — only the ROUTING
        # decision is agent-authored — so the deterministic_agent provenance on this
        # stage can never be misread as "the result was computed by an agent" (Codex
        # ADR-028-P3 R0 P2).
        route = _decide_route(
            verdict=verdict,
            fault_class="none",
            verdict_source="本阶段 demo 评审状态（脚本化，非 agent 计算）",
        )
        provenance = route.provenance
        agent_explanation = route.agent_explanation
        next_action = route.next_action
        metrics_src = {**metrics_src, "routedTo": route.next_node}

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
        agent_explanation=agent_explanation,
        next_action=next_action,
        provenance=provenance,
        updated_at=_now_iso(),
    )


def _terminal_status(
    stage: WorkflowStage, real: bool = False, solve_ctx: dict | None = None
) -> StageStatus:
    # The synthetic WARNING stages are mock-demo artifacts (e.g. 142 bad bracket
    # elements). In real mode every stage completes SUCCESS EXCEPT result_analysis,
    # whose status follows the real benchmark verdict: PASS -> SUCCESS, a
    # disagreement OR a missing solve context -> WARNING, so a failed benchmark
    # check is never shown as a plain green success (Codex M4 R0 P2).
    if real:
        if stage is WorkflowStage.RESULT_ANALYSIS:
            verdict = (solve_ctx or {}).get("benchmark", {}).get("verdict")
            return StageStatus.SUCCESS if verdict == "PASS" else StageStatus.WARNING
        return StageStatus.SUCCESS
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
        # Serialises the run_one_stage check-and-set so two concurrent
        # POST /workflow/stage/run for the same run/stage cannot both pass the
        # pending check and double-execute (Codex M2 R0 P2). The critical
        # section is tiny + synchronous, so a single process-wide lock is
        # cheap; it matters most once M4 swaps in a real (non-idempotent)
        # solver backend.
        self._stage_lock = threading.Lock()
        # M4: per-run real-solve context (frd path, ccx metadata, benchmark
        # verdict), set at the SOLVER_RUN stage and read by the later
        # post_processing / result_analysis stages (which are separate calls in
        # the M2 external path). Keyed by run_id; only used when the real-solver
        # flag is on.
        self._solve_ctx: dict[str, dict] = {}

    def _run_real_le10(self, run_id: str) -> dict:
        """Run the real LE10 ccx solve + benchmark extraction; cache per run.

        Raises RuntimeError if the solve did not converge (surfaced as a FAILED
        solver_run stage by the callers).
        """
        work = Path(tempfile.mkdtemp(prefix=f"le10_{run_id}_"))
        solve = real_le10.run_le10_solve(work)
        frd = solve.get("frd_path")
        if not solve.get("converged") or not frd:
            raise RuntimeError(
                str(solve.get("failure_reason") or "LE10 ccx solve did not converge")
            )
        benchmark = real_le10.extract_le10_benchmark(Path(solve["deck_path"]), Path(frd))
        ctx = {**solve, "benchmark": benchmark}
        self._solve_ctx[run_id] = ctx
        return ctx

    def _new_run(
        self,
        label: str | None,
        fail_at_stage: WorkflowStage | None,
        user_request: str | None = None,
    ) -> MockRun:
        seq = next(self._counter)
        run_id = f"mock_{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}_{seq:04d}"
        run = MockRun(
            run_id=run_id,
            label=label,
            user_request=user_request,
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

    # --- M2: external (Trigger.dev) single-stage orchestration ---------------

    def create_run(
        self,
        label: str | None = None,
        fail_at_stage: WorkflowStage | None = None,
        user_request: str | None = None,
    ) -> MockRun:
        """M2: mint + store a PENDING run WITHOUT starting any execution.

        The external orchestrator (Trigger.dev) then drives each stage via
        :meth:`run_one_stage`. The M1 self-advancing path (``trigger`` /
        ``run_sync``) is unaffected."""
        return self._new_run(label, fail_at_stage, user_request)

    def run_one_stage(
        self, run_id: str, stage: WorkflowStage, fail: bool = False
    ) -> StageState:
        """M2: execute exactly ONE stage for an existing run (sync, no sleeps).

        Idempotent + order-guarded so a Trigger.dev retry (same idempotency key)
        re-POSTing a completed stage returns the existing StageState rather than
        re-executing (which would, e.g., overwrite a WARNING with SUCCESS).

        Raises:
            KeyError: unknown ``run_id`` (route -> 404).
            StageOrderError: the run already failed, or a prior stage has not
                completed (out-of-order drive) (route -> 409).
        """
        # One lock over the whole check-and-set: concurrent calls for the same
        # run/stage serialise, so only the first executes and the rest hit the
        # idempotent-replay branch (Codex M2 R0 P2).
        with self._stage_lock:
            run = self.runs.get(run_id)
            if run is None:
                raise KeyError(run_id)
            idx = CANONICAL_STAGE_ORDER.index(stage)
            existing = run.stages[idx]
            # Idempotent replay: a terminal stage returns its recorded state as-is.
            if existing.status in (StageStatus.SUCCESS, StageStatus.WARNING, StageStatus.FAILED):
                return existing
            # A run that already failed cannot be driven further.
            if run.status is StageStatus.FAILED:
                raise StageOrderError(
                    f"run {run_id} already failed; cannot run stage {stage.value}"
                )
            # Strict ordering: every prior stage must be terminal-success/warning.
            for prior in CANONICAL_STAGE_ORDER[:idx]:
                if run.stages[CANONICAL_STAGE_ORDER.index(prior)].status not in (
                    StageStatus.SUCCESS,
                    StageStatus.WARNING,
                ):
                    raise StageOrderError(
                        f"out-of-order: stage {stage.value} requested before "
                        f"{prior.value} completed"
                    )
            backend = MockFEABackend(
                force_fault=FaultClass.SOLVER_CONVERGENCE
                if (fail and stage is WorkflowStage.SOLVER_RUN)
                else None
            )
            real = settings.workflow_real_solver
            specs = LE10_STAGE_SPECS if real else STAGE_SPECS
            run.current_stage = stage
            run.status = StageStatus.RUNNING
            if fail:
                st = _build_stage_state(
                    run.run_id, stage, StageStatus.FAILED, 1.0,
                    backend=backend, specs=specs, error=self._fail_error(stage),
                )
            else:
                solve_ctx: dict | None = None
                if real and stage is WorkflowStage.SOLVER_RUN:
                    try:
                        solve_ctx = self._run_real_le10(run.run_id)
                    except Exception as exc:  # honest failure, not a silent mock
                        st = _build_stage_state(
                            run.run_id, stage, StageStatus.FAILED, 1.0,
                            backend=backend, specs=specs,
                            error=StageError(
                                fault_class=FaultClass.SOLVER_CONVERGENCE,
                                message=str(exc),
                                detail="real LE10 ccx solve failed",
                            ),
                        )
                        run.stages[idx] = st
                        self._finalize(run)
                        return st
                elif real:
                    solve_ctx = self._solve_ctx.get(run.run_id)
                st = _build_stage_state(
                    run.run_id, stage, _terminal_status(stage, real, solve_ctx), 1.0,
                    backend=backend, specs=specs, solve_ctx=solve_ctx, user_request=run.user_request,
                )
            run.stages[idx] = st
            if fail or stage is CANONICAL_STAGE_ORDER[-1]:
                self._finalize(run)
            return st

    def run_sync(
        self,
        label: str | None = None,
        fail_at_stage: WorkflowStage | None = None,
        user_request: str | None = None,
    ) -> MockRun:
        """Run the whole pipeline with no sleeps (tests / ?sync). Returns the
        terminal run."""
        run = self._new_run(label, fail_at_stage, user_request)
        backend = MockFEABackend(
            force_fault=FaultClass.SOLVER_CONVERGENCE
            if fail_at_stage is WorkflowStage.SOLVER_RUN
            else None
        )
        real = settings.workflow_real_solver
        specs = LE10_STAGE_SPECS if real else STAGE_SPECS
        run.status = StageStatus.RUNNING
        solve_ctx: dict | None = None
        for idx, stage in enumerate(CANONICAL_STAGE_ORDER):
            run.current_stage = stage
            if fail_at_stage is stage:
                run.stages[idx] = _build_stage_state(
                    run.run_id, stage, StageStatus.FAILED, 1.0,
                    backend=backend, specs=specs, error=self._fail_error(stage),
                )
                break
            if real and stage is WorkflowStage.SOLVER_RUN:
                try:
                    solve_ctx = self._run_real_le10(run.run_id)
                except Exception as exc:
                    run.stages[idx] = _build_stage_state(
                        run.run_id, stage, StageStatus.FAILED, 1.0,
                        backend=backend, specs=specs,
                        error=StageError(
                            fault_class=FaultClass.SOLVER_CONVERGENCE,
                            message=str(exc),
                            detail="real LE10 ccx solve failed",
                        ),
                    )
                    break
            run.stages[idx] = _build_stage_state(
                run.run_id, stage, _terminal_status(stage, real, solve_ctx), 1.0,
                backend=backend, specs=specs, solve_ctx=solve_ctx, user_request=run.user_request,
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
        real = settings.workflow_real_solver
        specs = LE10_STAGE_SPECS if real else STAGE_SPECS
        run.status = StageStatus.RUNNING
        solve_ctx: dict | None = None
        for idx, stage in enumerate(CANONICAL_STAGE_ORDER):
            run.current_stage = stage
            for p in _PROGRESS_TICKS:
                run.stages[idx] = _build_stage_state(
                    run.run_id, stage, StageStatus.RUNNING, p,
                    backend=backend, specs=specs, solve_ctx=solve_ctx, user_request=run.user_request,
                )
                await asyncio.sleep(tick_delay_s)
            if run.fail_at_stage is stage:
                run.stages[idx] = _build_stage_state(
                    run.run_id, stage, StageStatus.FAILED, 1.0,
                    backend=backend, specs=specs, error=self._fail_error(stage),
                )
                break
            if real and stage is WorkflowStage.SOLVER_RUN:
                try:
                    # Off-thread so the ~8s ccx subprocess does not block the loop.
                    solve_ctx = await asyncio.to_thread(self._run_real_le10, run.run_id)
                except Exception as exc:
                    run.stages[idx] = _build_stage_state(
                        run.run_id, stage, StageStatus.FAILED, 1.0,
                        backend=backend, specs=specs,
                        error=StageError(
                            fault_class=FaultClass.SOLVER_CONVERGENCE,
                            message=str(exc),
                            detail="real LE10 ccx solve failed",
                        ),
                    )
                    break
            run.stages[idx] = _build_stage_state(
                run.run_id, stage, _terminal_status(stage, real, solve_ctx), 1.0,
                backend=backend, specs=specs, solve_ctx=solve_ctx, user_request=run.user_request,
            )
        self._finalize(run)

    def trigger(
        self,
        label: str | None = None,
        fail_at_stage: WorkflowStage | None = None,
        user_request: str | None = None,
    ) -> MockRun:
        """Create a run and schedule the async driver. Returns the initial run."""
        run = self._new_run(label, fail_at_stage, user_request)
        asyncio.create_task(self._advance(run.run_id))
        return run

    def get(self, run_id: str) -> MockRun | None:
        return self.runs.get(run_id)

    def list_runs(self, limit: int = 20) -> list[MockRun]:
        return list(self.runs.values())[-limit:][::-1]


# Module-level singleton (mirrors SolverService).
store = MockWorkflowStore()
