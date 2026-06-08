"""Workbench-agent → wire-state projection + deterministic intake analysis (ADR-028).

This module lives in the **agent layer** (NOT ``backend/app/workbench/``) precisely so
it may import ``schemas.sim_state`` / ``schemas.sim_plan`` freely while honoring
ADR-015 rule 3 ("no file under ``backend/app/workbench/`` imports ``schemas.sim_state``").
The workbench facade (``backend/app/workbench/agent_facade.py``) calls into here; the
``StageState`` returned is the already-projected wire object the facade hands back, so
the facade never touches ``SimState``.

Wired agent nodes (each a deterministic "rule-based agent" stand-in for the LLM
architect's work, per ADR-028 D5 — all hermetic, no LLM/tool/artifact dependency):

* :func:`analyze_intake` (P1) — derives physics type, objectives and a naming-compliant
  case id from the **actual** request text; its explanation varies with input.
* :func:`decide_route` (P3) — runs the real :func:`agents.router.route_reviewer` to pick
  the next agent at the reviewer gate (proceed / re-run / human_fallback).
* :func:`analyze_setup` (P-setup) — decides which material / boundary-condition topology
  / load to apply for the MATERIAL_ASSIGNMENT / BOUNDARY_CONDITIONS / LOAD_CASES stages,
  disclosing whether each was derived from a request hint or fell back to a default.
* :func:`analyze_geometry_plan` (P-geomplan) — decides the geometry FAMILY/source for the
  GEOMETRY_VALIDATION stage. This is geometry **planning, NOT validation**: no CAD kernel
  runs, no STEP is generated, ``checkers.geometry_checker`` is NOT called. It explicitly
  discloses this and pins ``cadKernelRan``/``defectCheckRun`` to ``False`` so the
  ``deterministic_agent`` label can never be read as "the geometry was validated".
* :func:`sim_state_to_stage_state` is the ADR-028 D4 LLM projector — it maps a
  **completed SimState** (the LLM architect's output) to the wire shape with
  ``provenance = llm_agent``.

The remaining tool/artifact-bound stages (CAD import / mesh / solve / post / report — and
the actual CAD-kernel geometry *validation* itself) remain scripted in the demo until they
can run hermetically; the facade raises for them rather than fake it.
"""

from __future__ import annotations

import re
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from agents.architect import _canonical_case_id, _valid_case_id
from agents.router import route_reviewer
from schemas.sim_plan import AnalysisType, GeometrySpec, SimPlan
from schemas.sim_state import FaultClass
from schemas.workflow_state import (
    StageArtifacts,
    StageError,
    StageMetrics,
    StageProvenance,
    StageState,
    StageStatus,
    WorkflowStage,
)

__all__ = [
    "SETUP_STAGES",
    "GeometryPlanOutcome",
    "IntakeOutcome",
    "RecoveryOutcome",
    "RouteOutcome",
    "SetupDecision",
    "SetupOutcome",
    "StageFidelityTier",
    "analyze_geometry_plan",
    "analyze_intake",
    "analyze_setup",
    "decide_recovery",
    "decide_route",
    "fidelity_metrics",
    "geometry_dummy_exec_to_stage_state",
    "geometry_plan_to_stage_state",
    "geometry_stage_state",
    "graph_geometry_to_stage_state",
    "graph_intake_to_stage_state",
    "graph_mesh_to_stage_state",
    "graph_solver_to_stage_state",
    "intake_outcome_to_stage_state",
    "setup_outcome_to_stage_state",
    "sim_state_to_stage_state",
]

_INTAKE_DESCRIPTION = "解析用户输入与确定分析方案"
_INTAKE_CURRENT_OBJECT = "user_request"
_INTAKE_NEXT_ACTION = "进入 CAD 几何导入并做缺陷校验。"
_MAX_SNIPPET = 48


def _ci(pattern: str) -> re.Pattern[str]:
    """Compile a keyword rule case-insensitively so title-cased / uppercase English
    requests ("Modal analysis", "THERMAL stress") classify correctly; Chinese is
    unaffected (Codex ADR-028-P1 R0 P2)."""
    return re.compile(pattern, re.IGNORECASE)


# Physics keyword rules (Chinese + English). First match wins; ordered
# most-specific first so "热-结构耦合" beats the bare "热"/"thermal" rule.
_PHYSICS_RULES: tuple[tuple[re.Pattern[str], AnalysisType], ...] = (
    (
        _ci(r"热\s*[-－]?\s*结构|thermo[\s-]*structural|热应力|thermal\s+stress"),
        AnalysisType.THERMO_STRUCTURAL,
    ),
    (_ci(r"预应力\s*模态|prestress(?:ed)?\s*modal"), AnalysisType.PRESTRESS_MODAL),
    (
        _ci(r"模态|modal|固有频率|natural\s+freq|振动|vibration|频率|eigenfrequenc"),
        AnalysisType.MODAL,
    ),
    (_ci(r"循环对称|cyclic\s*symmetry"), AnalysisType.CYCLIC_SYMMETRY),
    (
        _ci(r"稳态热|steady[\s-]*thermal|传热|heat\s+transfer|温度场|thermal\b|温度"),
        AnalysisType.STEADY_THERMAL,
    ),
)
_NONLINEAR_RE = _ci(
    r"非线性|nonlinear|塑性|plastic|大变形|large\s+deformation|接触|contact|超弹|hyperelastic"
)

# Objective keyword rules — all matches collected (deduped, in rule order).
_OBJECTIVE_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (_ci(r"应力|stress|von\s*mises|屈服|yield"), "max_von_mises"),
    (_ci(r"位移|变形|deformation|displacement|挠度|deflection"), "max_displacement"),
    (_ci(r"安全系数|safety\s*factor|factor\s+of\s+safety|安全裕度"), "safety_factor"),
    (_ci(r"温度|temperature|thermal"), "max_temperature"),
    (_ci(r"频率|frequency|模态|modal|固有"), "natural_frequencies"),
)
# ObjectiveSpec's own default (schemas.sim_plan) — used when nothing matches.
_DEFAULT_OBJECTIVES: tuple[str, ...] = ("max_displacement", "max_von_mises")

_PHYSICS_LABEL_ZH: dict[AnalysisType, str] = {
    AnalysisType.STATIC: "线弹性静力",
    AnalysisType.MODAL: "模态分析",
    AnalysisType.PRESTRESS_MODAL: "预应力模态",
    AnalysisType.CYCLIC_SYMMETRY: "循环对称",
    AnalysisType.STEADY_THERMAL: "稳态热传导",
    AnalysisType.THERMO_STRUCTURAL: "热-结构耦合",
}
_OBJECTIVE_LABEL_ZH: dict[str, str] = {
    "max_von_mises": "应力(von Mises)",
    "max_displacement": "位移",
    "safety_factor": "安全系数",
    "max_temperature": "温度场",
    "natural_frequencies": "固有频率",
}


@dataclass(frozen=True)
class IntakeOutcome:
    """The intake node's result — physics + objectives + case id derived from the
    actual user request, plus the provenance of how it was produced."""

    case_id: str
    analysis_type: AnalysisType
    nonlinear: bool
    objectives: list[str]
    physics_label: str
    agent_explanation: str
    next_action: str
    provenance: StageProvenance


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _snippet(text: str) -> str:
    one_line = " ".join(text.split())
    if len(one_line) <= _MAX_SNIPPET:
        return one_line
    return one_line[: _MAX_SNIPPET - 1] + "…"


def _physics_label(analysis_type: AnalysisType, nonlinear: bool) -> str:
    if analysis_type is AnalysisType.STATIC and nonlinear:
        return "非线性静力"
    return _PHYSICS_LABEL_ZH.get(analysis_type, analysis_type.value)


def _objectives_zh(objectives: list[str]) -> str:
    return "、".join(_OBJECTIVE_LABEL_ZH.get(m, m) for m in objectives)


def analyze_intake(user_request: str, *, existing_case_id: str | None = None) -> IntakeOutcome:
    """Deterministic rule-based intake agent (no LLM).

    Derives the analysis type, requested objectives, and a naming-compliant case
    id from the **actual** request text, so different inputs yield different
    explanations. Reuses the architect agent's deterministic
    :func:`agents.architect._canonical_case_id` for the case id.
    """
    req = (user_request or "").strip()
    case_id = _canonical_case_id(req or "AI-FEA intake", existing_case_id)

    analysis_type = AnalysisType.STATIC
    for pattern, atype in _PHYSICS_RULES:
        if pattern.search(req):
            analysis_type = atype
            break
    nonlinear = bool(_NONLINEAR_RE.search(req))

    objectives: list[str] = []
    for pattern, metric in _OBJECTIVE_RULES:
        if pattern.search(req) and metric not in objectives:
            objectives.append(metric)
    if not objectives:
        objectives = list(_DEFAULT_OBJECTIVES)

    label = _physics_label(analysis_type, nonlinear)
    explanation = (
        f"基于用户输入「{_snippet(req)}」判定：物理类型 = {label}"
        f"（{analysis_type.value}{'，非线性' if nonlinear else ''}）；"
        f"关注量 = {_objectives_zh(objectives)}。"
        f"分配案例号 {case_id}（确定性规则解析，未调用 LLM）。"
    )
    return IntakeOutcome(
        case_id=case_id,
        analysis_type=analysis_type,
        nonlinear=nonlinear,
        objectives=objectives,
        physics_label=label,
        agent_explanation=explanation,
        next_action=_INTAKE_NEXT_ACTION,
        provenance=StageProvenance.DETERMINISTIC_AGENT,
    )


def intake_outcome_to_stage_state(
    run_id: str,
    outcome: IntakeOutcome,
    *,
    status: StageStatus = StageStatus.SUCCESS,
    progress: float = 1.0,
) -> StageState:
    """Project an :class:`IntakeOutcome` into the PROJECT_INTAKE wire ``StageState``."""
    return StageState(
        run_id=run_id,
        stage=WorkflowStage.PROJECT_INTAKE,
        status=status,
        progress=progress,
        current_object=_INTAKE_CURRENT_OBJECT,
        description=_INTAKE_DESCRIPTION,
        metrics=StageMetrics.model_validate(
            {
                "physics": outcome.analysis_type.value,
                "nonlinear": outcome.nonlinear,
                "objectives": len(outcome.objectives),
                "caseId": outcome.case_id,
            }
        ),
        artifacts=StageArtifacts(),
        agent_explanation=outcome.agent_explanation,
        next_action=outcome.next_action,
        provenance=outcome.provenance,
        updated_at=_now_iso(),
    )


def sim_state_to_stage_state(
    sim_state: Mapping[str, object],
    *,
    run_id: str,
    status: StageStatus = StageStatus.SUCCESS,
    progress: float = 1.0,
) -> StageState:
    """Project a **completed SimState** into the PROJECT_INTAKE wire ``StageState``.

    The ADR-028 D4 projector for the LLM path: ``sim_state`` is the architect's
    output merged with the request — ``{"plan": SimPlan, "user_request": str}`` —
    and the result carries ``provenance = llm_agent``. Living here (agent layer)
    keeps ``schemas.sim_state`` out of the workbench package (ADR-015 rule 3).
    """
    plan = sim_state.get("plan")
    if not isinstance(plan, SimPlan):
        raise TypeError(
            "sim_state_to_stage_state requires a completed SimPlan under sim_state['plan']"
        )
    analysis_type = plan.physics.type
    nonlinear = bool(plan.physics.nonlinear or plan.solver.nonlinear)
    objectives = list(plan.objectives.metrics)
    label = _physics_label(analysis_type, nonlinear)
    req = str(sim_state.get("user_request") or "")
    explanation = (
        f"LLM 架构师解析用户输入「{_snippet(req)}」生成 SimPlan：物理类型 = {label}"
        f"（{analysis_type.value}）；目标量 = {_objectives_zh(objectives)}；案例号 {plan.case_id}。"
    )
    outcome = IntakeOutcome(
        case_id=plan.case_id,
        analysis_type=analysis_type,
        nonlinear=nonlinear,
        objectives=objectives,
        physics_label=label,
        agent_explanation=explanation,
        next_action=_INTAKE_NEXT_ACTION,
        provenance=StageProvenance.LLM_AGENT,
    )
    return intake_outcome_to_stage_state(run_id, outcome, status=status, progress=progress)


# --- LangGraph-runtime intake projection (ADR-029 P0) ------------------------
# The graph-wiring north star: this projects a PROJECT_INTAKE StageState from the
# accumulated final SimState of a REAL LangGraph compiled-graph .invoke() (a dedicated
# truncated START->architect->END graph), as opposed to the direct architect.run() the
# facade calls today. The decisive honesty rule (verified empirically: agents.architect
# authors a SimPlan ONLY with an LLM key, else returns fault_class=unknown with no plan):
# "the graph node EXECUTED" and "the graph node AUTHORED content" are DISTINCT facts and
# are surfaced separately, never conflated. Provenance is NOT changed by the runtime swap
# (it stays llm_agent when a plan was authored, deterministic_agent when the rule-based
# projector supplied the text) so the N/13 count is identical to the direct path; the
# graph-execution fact rides metrics (graphNodeRan / graphNodeProducedPlan / graphRunner)
# plus an honest disclosure — mirroring how StageFidelityTier rides metrics off the
# provenance axis. No 4th provenance value (the FE asProvenance() would downgrade an
# unknown value to scripted_demo and DECREASE N/13).

_GRAPH_RUNNER_TAG = "langgraph-truncated-architect"


def graph_intake_to_stage_state(
    final_sim_state: Mapping[str, object],
    user_request: str,
    *,
    run_id: str,
    existing_case_id: str | None = None,
    status: StageStatus = StageStatus.SUCCESS,
    progress: float = 1.0,
) -> StageState:
    """Project the final SimState of a truncated-graph ``.invoke()`` into PROJECT_INTAKE.

    ``final_sim_state`` is the accumulated state returned by the dedicated
    architect-only :class:`langgraph` compiled graph (see :mod:`agents.graph_runner`).
    Branches on plan-presence so a keyless run (no SimPlan authored) can never be
    mislabeled as agent-authored content:

    * **plan present** (LLM key opted in): reuse :func:`sim_state_to_stage_state`
      (provenance ``llm_agent``) and disclose that the architect node authored the plan;
    * **plan absent** (hermetic default): reuse the deterministic
      :func:`analyze_intake` + :func:`intake_outcome_to_stage_state` (provenance
      ``deterministic_agent``) and disclose that the architect node executed but
      authored nothing keyless, so the intake text is rule-based — NOT the graph node's.

    Either way the runtime-execution fact is added to metrics
    (``graphNodeRan`` / ``graphNodeProducedPlan`` / ``graphRunner``) WITHOUT changing
    provenance, so the N/13 agent-driven count is identical to the direct-call path.
    """
    plan = final_sim_state.get("plan")
    produced_plan = isinstance(plan, SimPlan)

    if produced_plan:
        base = sim_state_to_stage_state(
            final_sim_state, run_id=run_id, status=status, progress=progress
        )
        disclosure = (
            "LangGraph 运行时通过 compile(仅含 architect 的 truncated graph).invoke 驱动真实 "
            "architect 节点产出 SimPlan，投影为 PROJECT_INTAKE；仅 START→architect 段执行，下游 "
            "geometry/mesh/solver 节点未运行；无真实 FEA 计算（架构接线证明，非验证）。"
        )
    else:
        outcome = analyze_intake(user_request, existing_case_id=existing_case_id)
        base = intake_outcome_to_stage_state(run_id, outcome, status=status, progress=progress)
        disclosure = (
            "architect 节点经真实 LangGraph 运行时（compiled graph .invoke）执行，但无 LLM key "
            "未产出 SimPlan（fault_class=unknown）；PROJECT_INTAKE 文本由确定性 analyze_intake "
            "投影提供（非图节点计算）；下游节点未执行；无真实求解（架构接线证明，非验证）。"
        )

    merged_metrics = {
        **base.metrics.model_dump(by_alias=True, exclude_none=True),
        # architecture-wiring facts (NOT FEA measurements, NOT a provenance flip):
        "graphNodeRan": True,
        "graphNodeProducedPlan": produced_plan,
        "graphRunner": _GRAPH_RUNNER_TAG,
    }
    explanation = f"{base.agent_explanation or ''}{disclosure}"
    return base.model_copy(
        update={
            "metrics": StageMetrics.model_validate(merged_metrics),
            "agent_explanation": explanation,
            "updated_at": _now_iso(),
        }
    )


# --- Router node projection (ADR-028 P3) -------------------------------------
# The genuine orchestration-decision node: given a reviewer verdict + fault class
# + retry budgets, agents.router.route_reviewer (FAULT_TO_NODE + MAX_RETRIES, pure
# deterministic logic, no LLM/tools) chooses which agent handles the next step —
# proceed to viz, re-run an upstream node, or escalate to human_fallback. Wiring it
# replaces a hardcoded "next step" string with a real division-of-labor decision.

# Friendly Chinese labels for the node route_reviewer selects. Purely for the
# human-readable explanation; the routing token itself is the router's verbatim output.
_ROUTE_LABEL_ZH: dict[str, str] = {
    "viz": "可视化 / 报告生成（viz）",
    "geometry": "重跑几何节点（geometry）",
    "mesh": "重跑网格节点（mesh）",
    "solver": "重跑求解节点（solver）",
    "architect": "回到架构师重定方案（architect）",
    "human_fallback": "转人工兜底复核（human_fallback）",
}


@dataclass(frozen=True)
class RouteOutcome:
    """The router node's decision: which agent runs next, plus how it was reached.

    ``provenance`` is always ``DETERMINISTIC_AGENT`` — the routing is computed by the
    real ``route_reviewer`` logic. It describes the *routing* only; the ``verdict`` it
    consumed may itself be scripted demo state, and the caller's explanation says so.
    """

    next_node: str
    verdict: str
    fault_class: str
    agent_explanation: str
    next_action: str
    provenance: StageProvenance


def decide_route(
    *,
    verdict: str,
    fault_class: FaultClass | str = FaultClass.NONE,
    retry_budgets: Mapping[str, int] | None = None,
    verdict_source: str = "本阶段评审状态",
) -> RouteOutcome:
    """Run the REAL ``agents.router.route_reviewer`` to pick the next agent.

    This is genuine orchestration logic (the ADR-004 fault→node map + a 3-retry cap),
    not a hardcoded transition. Deterministic; no LLM, no tools, no artifacts.

    ``verdict_source`` names where the verdict came from so the explanation never
    over-claims: in the mock demo the verdict is derived from a scripted stage status,
    so only the *routing decision* — not the underlying result — is agent-authored.
    """
    fc = fault_class if isinstance(fault_class, FaultClass) else FaultClass(fault_class)
    state = {
        "verdict": verdict,
        "fault_class": fc,
        "retry_budgets": dict(retry_budgets or {}),
    }
    next_node = route_reviewer(state)  # real router; always returns a node token
    node_label = _ROUTE_LABEL_ZH.get(next_node, next_node)
    explanation = (
        f"路由 agent（route_reviewer）依据{verdict_source}"
        f"（verdict={verdict}，故障类={fc.value}）判定下一步 = {node_label}"
        f"（ADR-004 故障→节点映射 + 最多 3 次重试上限，确定性逻辑，未调用 LLM）。"
    )
    return RouteOutcome(
        next_node=next_node,
        verdict=str(verdict),
        fault_class=fc.value,
        agent_explanation=explanation,
        next_action=f"下一步 → {node_label}。",
        provenance=StageProvenance.DETERMINISTIC_AGENT,
    )


# --- Setup planner node (ADR-028 P-setup) ------------------------------------
# A deterministic rule-based planner that decides WHICH material / boundary-
# condition topology / load to apply from the request text — the same kind of
# architect work the LLM does as part of a SimPlan, here as the honest rule-based
# stand-in (mirrors analyze_intake). When the request gives no hint for a field
# the planner falls back to a documented default AND the explanation discloses it,
# so provenance=deterministic_agent describes ONLY the planning decision — never an
# inference from real geometry (no FreeCAD/gmsh/ccx run here; mock numbers untouched).

# Material rules: (pattern, (name, youngs_modulus_pa, poissons_ratio, density)).
# Most specific first ("不锈钢"/stainless before the bare "钢"/steel rule).
_MATERIAL_RULES: tuple[tuple[re.Pattern[str], tuple[str, float, float, float]], ...] = (
    (_ci(r"不锈钢|stainless"), ("Stainless Steel", 1.93e11, 0.31, 8000.0)),
    (_ci(r"碳钢|结构钢|钢|steel"), ("Structural Steel", 2.1e11, 0.30, 7850.0)),
    (_ci(r"钛合金|钛|titanium|ti-?6al"), ("Ti-6Al-4V", 1.138e11, 0.342, 4430.0)),
    (_ci(r"铝合金|铝|alumin"), ("Aluminum 7075", 7.17e10, 0.33, 2810.0)),
)
# No-hint default: structural steel (the most common structural-FEA material).
_MATERIAL_DEFAULT: tuple[str, float, float, float] = (
    "Structural Steel",
    2.1e11,
    0.30,
    7850.0,
)

# BC rules: (pattern, (semantic, kind, target, label_zh)).
_BC_RULES: tuple[tuple[re.Pattern[str], tuple[str, str, str, str]], ...] = (
    (
        _ci(r"简支|铰支|pinned|simply[\s-]*support"),
        ("pinned_support", "pinned", "Nedge", "简支 / 铰支约束"),
    ),
    (_ci(r"对称|symmetr"), ("symmetry", "symmetry", "Nsym", "对称约束")),
    (
        _ci(r"固定|固支|嵌固|约束|安装面|fixed|clamp|constrain|mount"),
        ("fixed_base", "fixed", "Nroot", "固定约束（固支底面）"),
    ),
)
_BC_DEFAULT: tuple[str, str, str, str] = (
    "fixed_base",
    "fixed",
    "Nroot",
    "固定底面 (fixed_base/Nroot)",
)

# Load kind rules: (pattern, (semantic, kind, target, label_zh)).
_LOAD_KIND_RULES: tuple[tuple[re.Pattern[str], tuple[str, str, str, str]], ...] = (
    (_ci(r"压力|压强|pressure"), ("pressure_load", "pressure", "Sface", "压力")),
    (
        _ci(r"拉力|拉伸|tension|tensile|traction"),
        ("tension_load", "traction", "Sface", "拉力"),
    ),
    (_ci(r"弯矩|扭矩|moment|torque"), ("moment_load", "moment", "Nref", "力矩")),
    (
        _ci(r"集中力|点载荷|tip|末端|端部|concentrated"),
        ("tip_load", "concentrated_force", "Ntip", "集中力"),
    ),
)
_LOAD_DEFAULT: tuple[str, str, str, str] = (
    "tip_load",
    "concentrated_force",
    "Ntip",
    "末端集中力",
)
_LOAD_MAG_RE = _ci(r"(\d+(?:\.\d+)?)\s*(kN|MN|N|MPa|kPa|GPa|Pa)\b")
_UNIT_CANON = {
    "kn": "kN",
    "mn": "MN",
    "n": "N",
    "mpa": "MPa",
    "kpa": "kPa",
    "gpa": "GPa",
    "pa": "Pa",
}


@dataclass(frozen=True)
class SetupDecision:
    """One setup stage's decision (material / BC / load) + how it was reached."""

    description: str
    metrics: dict[str, object]
    agent_explanation: str
    next_action: str
    from_hint: bool


@dataclass(frozen=True)
class SetupOutcome:
    """The setup planner's three decisions + their shared provenance."""

    material: SetupDecision
    bc: SetupDecision
    load: SetupDecision
    provenance: StageProvenance


def _eng(value: float) -> str:
    return f"{value:.3g}"


def _decide_material(req: str) -> SetupDecision:
    matched: tuple[str, float, float, float] | None = None
    for pattern, spec in _MATERIAL_RULES:
        if pattern.search(req):
            matched = spec
            break
    name, e_pa, nu, rho = matched or _MATERIAL_DEFAULT
    from_hint = matched is not None
    if from_hint:
        explanation = (
            f"基于用户输入「{_snippet(req)}」识别材料 = {name}"
            f"（E={_eng(e_pa)} Pa，ν={nu}）。确定性规则解析，未调用 LLM。"
        )
    else:
        explanation = (
            f"请求未指定材料 → 采用默认 {name}"
            f"（E={_eng(e_pa)} Pa，ν={nu}）。确定性规则解析，未调用 LLM。"
        )
    return SetupDecision(
        description=f"赋予各向同性材料（{name}）",
        metrics={
            "materialName": name,
            "youngsModulusPa": e_pa,
            "poissonsRatio": nu,
            "densityKgM3": rho,
            "fromHint": from_hint,
        },
        agent_explanation=explanation,
        next_action="设置边界条件。",
        from_hint=from_hint,
    )


def _decide_bc(req: str) -> SetupDecision:
    matched: tuple[str, str, str, str] | None = None
    for pattern, spec in _BC_RULES:
        if pattern.search(req):
            matched = spec
            break
    semantic, kind, target, label = matched or _BC_DEFAULT
    from_hint = matched is not None
    if from_hint:
        explanation = (
            f"基于用户输入「{_snippet(req)}」识别约束 = {label}"
            f"（{semantic}/{target}）。确定性规则解析，未调用 LLM。"
        )
    else:
        explanation = f"请求未给出约束提示 → 采用默认{label}。确定性规则解析，未调用 LLM。"
    return SetupDecision(
        description=f"设置约束（{label}）",
        metrics={
            "bcSemantic": semantic,
            "bcKind": kind,
            "target": target,
            "fromHint": from_hint,
        },
        agent_explanation=explanation,
        next_action="设置载荷工况。",
        from_hint=from_hint,
    )


def _decide_load(req: str) -> SetupDecision:
    matched: tuple[str, str, str, str] | None = None
    for pattern, spec in _LOAD_KIND_RULES:
        if pattern.search(req):
            matched = spec
            break
    kind_from_hint = matched is not None
    semantic, kind, target, label = matched or _LOAD_DEFAULT
    mag_match = _LOAD_MAG_RE.search(req)
    magnitude: float | None = None
    unit: str | None = None
    if mag_match:
        magnitude = float(mag_match.group(1))
        unit = _UNIT_CANON.get(mag_match.group(2).lower(), mag_match.group(2))
    mag_from_hint = mag_match is not None
    from_hint = kind_from_hint or mag_from_hint
    mag_txt = f" {magnitude:g}{unit}" if magnitude is not None else ""
    if kind_from_hint and mag_from_hint:
        explanation = (
            f"基于用户输入「{_snippet(req)}」识别载荷 = {label}{mag_txt}"
            f"（{semantic}/{target}）。确定性规则解析，未调用 LLM。"
        )
    elif kind_from_hint:
        explanation = (
            f"基于用户输入「{_snippet(req)}」识别载荷类型 = {label}"
            f"（{semantic}/{target}，未指定量级）。确定性规则解析，未调用 LLM。"
        )
    elif mag_from_hint:
        # magnitude given but NO topology hint → disclose that the topology DEFAULTED,
        # so deterministic_agent is never read as "the load topology was identified".
        explanation = (
            f"基于用户输入「{_snippet(req)}」识别载荷量级 ={mag_txt}；"
            f"拓扑未指定 → 采用默认{label}（{semantic}/{target}）。"
            f"确定性规则解析，未调用 LLM。"
        )
    else:
        explanation = (
            f"请求未给出载荷 → 采用默认末端集中力占位"
            f"（{semantic}/{target}，未指定量级）。确定性规则解析，未调用 LLM。"
        )
    return SetupDecision(
        description=f"设置载荷工况（{label}）",
        metrics={
            "loadSemantic": semantic,
            "loadKind": kind,
            "target": target,
            "magnitude": magnitude,
            "unit": unit,
            "fromHint": from_hint,
            # machine-checkable: was the load TOPOLOGY derived from a hint, or defaulted?
            "kindFromHint": kind_from_hint,
        },
        agent_explanation=explanation,
        next_action="生成网格。",
        from_hint=from_hint,
    )


def analyze_setup(user_request: str) -> SetupOutcome:
    """Deterministic rule-based setup planner (no LLM).

    Decides which material, boundary-condition topology, and load to apply from the
    **actual** request text. Each decision discloses whether it was derived from a
    hint or fell back to a documented default, so provenance=deterministic_agent
    describes ONLY the planning decision — never an inference from real geometry
    (no FreeCAD/gmsh/ccx run here; the mock numeric metrics elsewhere are unchanged).
    """
    req = (user_request or "").strip()
    return SetupOutcome(
        material=_decide_material(req),
        bc=_decide_bc(req),
        load=_decide_load(req),
        provenance=StageProvenance.DETERMINISTIC_AGENT,
    )


_SETUP_DECISION_ATTR: dict[WorkflowStage, str] = {
    WorkflowStage.MATERIAL_ASSIGNMENT: "material",
    WorkflowStage.BOUNDARY_CONDITIONS: "bc",
    WorkflowStage.LOAD_CASES: "load",
}
_SETUP_CURRENT_OBJECT: dict[WorkflowStage, str] = {
    WorkflowStage.MATERIAL_ASSIGNMENT: "bracket_solid",
    WorkflowStage.BOUNDARY_CONDITIONS: "mount_face",
    WorkflowStage.LOAD_CASES: "load_face",
}
SETUP_STAGES: frozenset[WorkflowStage] = frozenset(_SETUP_DECISION_ATTR)


def setup_outcome_to_stage_state(
    run_id: str,
    stage: WorkflowStage,
    outcome: SetupOutcome,
    *,
    status: StageStatus = StageStatus.SUCCESS,
    progress: float = 1.0,
) -> StageState:
    """Project one setup stage of a :class:`SetupOutcome` into its wire ``StageState``."""
    attr = _SETUP_DECISION_ATTR.get(stage)
    if attr is None:
        raise ValueError(f"{stage!r} is not a setup stage (expected {sorted(SETUP_STAGES)})")
    decision: SetupDecision = getattr(outcome, attr)
    return StageState(
        run_id=run_id,
        stage=stage,
        status=status,
        progress=progress,
        current_object=_SETUP_CURRENT_OBJECT[stage],
        description=decision.description,
        metrics=StageMetrics.model_validate(decision.metrics),
        artifacts=StageArtifacts(),
        agent_explanation=decision.agent_explanation,
        next_action=decision.next_action,
        provenance=outcome.provenance,
        updated_at=_now_iso(),
    )


# --- Fault-recovery node (ADR-028 P-recover) ---------------------------------
# A genuine TWO-agent decision on the failure path: the reviewer node DERIVES a
# verdict from the actual fault, then the router picks the recovery node. Crucially
# this carries NO provenance field — the demo failure itself is scripted, so the
# failing stage stays scripted_demo (its agent_explanation/next_action text — what
# StageProvenance labels — is the scripted failure prose). The recovery is surfaced
# separately (via metrics.recovery, with its own agentDriven/faultInjected flags), so
# wiring it never relabels the failing stage or inflates the N/13 count (ADR-028 D2).


@dataclass(frozen=True)
class RecoveryOutcome:
    """The reviewer→router fault-recovery decision for an injected failure.

    Has NO ``provenance`` field by design: the failure is scripted demo input (the agent
    did NOT diagnose the fault), so the failing stage stays ``scripted_demo``; only the
    verdict-derivation + node-routing here are agent-computed, surfaced via metrics.
    """

    next_node: str
    verdict: str
    fault_class: str
    agent_explanation: str
    next_action: str


def decide_recovery(
    *,
    fault_class: FaultClass | str,
    retry_budgets: Mapping[str, int] | None = None,
) -> RecoveryOutcome:
    """Derive a recovery decision for an injected fault via the REAL reviewer + router.

    The verdict is NEVER hardcoded: :func:`agents.reviewer._review_upstream_fault`
    (RERUN_FAULTS membership) classifies the actual fault, then
    :func:`agents.router.route_reviewer` (ADR-004 fault→node map + a 3-retry cap) picks
    the recovery node. Honest disclosure: the ``fault_class`` is an injected demo fault
    (NOT an agent diagnosis); only the verdict-derivation + routing are agent-computed,
    deterministically, with no LLM call.
    """
    fc = fault_class if isinstance(fault_class, FaultClass) else FaultClass(fault_class)
    # Intentional cross-module reuse of the reviewer node's fault→verdict rule
    # (RERUN_FAULTS membership) — derive the verdict from the REAL reviewer instead of
    # duplicating the rule here. _review_upstream_fault reads only state["history"].
    from agents.reviewer import _review_upstream_fault

    verdict = str(_review_upstream_fault({"history": []}, fc)["verdict"])
    next_node = route_reviewer(
        {"verdict": verdict, "fault_class": fc, "retry_budgets": dict(retry_budgets or {})}
    )
    label = _ROUTE_LABEL_ZH.get(next_node, next_node)
    explanation = (
        f"故障复核 agent（reviewer._review_upstream_fault）将注入故障"
        f"（{fc.value}，该故障类型为 demo 注入、非 agent 诊断）判定为 verdict={verdict}；"
        f"路由 agent（route_reviewer）据此选择恢复节点 = {label}"
        f"（ADR-004 故障→节点映射 + 最多 3 次重试上限，确定性逻辑，未调用 LLM）。"
    )
    return RecoveryOutcome(
        next_node=next_node,
        verdict=verdict,
        fault_class=fc.value,
        agent_explanation=explanation,
        next_action=f"恢复路由 → {label}（需人工确认是否重跑）。",
    )


# --- Geometry-PLANNING node (ADR-028 P-geomplan) -----------------------------
# A deterministic rule-based agent for the GEOMETRY_VALIDATION stage: it decides the
# geometry FAMILY/source from the actual request (mirroring analyze_setup) and flips the
# stage's provenance scripted_demo -> deterministic_agent. CRITICAL honesty bound: this is
# geometry PLANNING, NOT validation — no CAD kernel runs, no STEP is generated,
# agents.geometry.run / tools.generate_geometry / checkers.check_geometry are NOT called.
# The metrics carry planning-intent fields + explicit cadKernelRan/defectCheckRun=False
# flags (machine-checkable disclosure), NEVER measurement-shaped keys (shortEdges/slivers)
# — surfacing those would lie about a defect check having run. On the genuine-request path
# this REPLACES the scripted spec's fabricated {shortEdges:2,...} metrics (a net honesty
# improvement); the no-request scripted fallback is untouched (stays scripted_demo).

# Geometry-family rules: (pattern, (family, ref_source, label_zh)). Specific first
# ("悬臂梁"/cantilever before the bare "梁"/beam rule).
_GEOMETRY_RULES: tuple[tuple[re.Pattern[str], tuple[str, str, str]], ...] = (
    (_ci(r"机翼|翼型|wing|airfoil|naca"), ("naca_wing", "naca", "NACA 翼型机翼")),
    (_ci(r"支架|托架|bracket"), ("bracket", "bracket_solid", "支架实体")),
    (_ci(r"悬臂|悬臂梁|cantilever"), ("cantilever_beam", "beam", "悬臂梁")),
    (_ci(r"平板|板材|plate"), ("plate", "plate", "平板")),
    (_ci(r"圆柱|圆筒|管|tube|pipe|cylinder"), ("cylinder", "cylinder", "圆柱 / 管")),
    (_ci(r"梁|beam"), ("beam", "beam", "梁")),
)
# No-hint default: a generic structural-solid placeholder (no specific family claimed).
_GEOMETRY_DEFAULT: tuple[str, str, str] = ("structural_solid", "solid", "通用结构实体占位")
_GEOMETRY_PLAN_CURRENT_OBJECT = "geometry_plan"


@dataclass(frozen=True)
class GeometryPlanOutcome:
    """The geometry-PLANNING decision for the GEOMETRY_VALIDATION stage.

    Honesty bound: this records a deterministic geometry-FAMILY plan derived from the
    request — it is NOT a CAD validation. No CAD kernel runs and no defect check is
    performed (``cadKernelRan``/``defectCheckRun`` are pinned ``False`` in ``metrics``);
    ``provenance=deterministic_agent`` therefore labels ONLY the planning text.
    """

    description: str
    metrics: dict[str, object]
    agent_explanation: str
    next_action: str
    provenance: StageProvenance


def analyze_geometry_plan(user_request: str) -> GeometryPlanOutcome:
    """Deterministic rule-based geometry-PLANNING agent (no LLM, no CAD kernel).

    Decides the geometry family/source from the **actual** request text and discloses
    whether it was derived from a hint or fell back to a documented default. It does NOT
    run FreeCAD, generate a STEP, or call ``checkers.geometry_checker`` — so this is
    planning, not the defect VALIDATION the stage name might imply. The explanation says
    so verbatim, and the metrics pin ``cadKernelRan``/``defectCheckRun`` to ``False``.
    """
    req = (user_request or "").strip()
    matched: tuple[str, str, str] | None = None
    for pattern, spec in _GEOMETRY_RULES:
        if pattern.search(req):
            matched = spec
            break
    family, ref_source, label = matched or _GEOMETRY_DEFAULT
    from_hint = matched is not None
    if from_hint:
        plan_txt = f"基于用户输入「{_snippet(req)}」规划几何 = {label}（family={family}）"
    else:
        plan_txt = f"请求未给出几何提示 → 采用默认{label}（family={family}）"
    explanation = (
        f"{plan_txt}。注意：未运行 CAD 内核、未生成 STEP、未做缺陷校验 ——"
        f"仅确定性几何规划（未调用 LLM）。"
    )
    return GeometryPlanOutcome(
        description=f"规划几何方案（{label}）",
        metrics={
            "geometryFamily": family,
            "refSource": ref_source,
            "fromHint": from_hint,
            # machine-checkable honesty flags: NO CAD kernel / defect check ran here, so
            # deterministic_agent can never be misread as "the geometry was validated".
            "cadKernelRan": False,
            "defectCheckRun": False,
        },
        agent_explanation=explanation,
        next_action="进入材料赋予。",
        provenance=StageProvenance.DETERMINISTIC_AGENT,
    )


def geometry_plan_to_stage_state(
    run_id: str,
    outcome: GeometryPlanOutcome,
    *,
    status: StageStatus = StageStatus.SUCCESS,
    progress: float = 1.0,
) -> StageState:
    """Project a :class:`GeometryPlanOutcome` into the GEOMETRY_VALIDATION wire state.

    ``current_object`` is a planning-intent label (``geometry_plan``), NEVER the scripted
    spec's ``bracket_solid`` (which would imply a real solid had been validated).
    """
    return StageState(
        run_id=run_id,
        stage=WorkflowStage.GEOMETRY_VALIDATION,
        status=status,
        progress=progress,
        current_object=_GEOMETRY_PLAN_CURRENT_OBJECT,
        description=outcome.description,
        metrics=StageMetrics.model_validate(outcome.metrics),
        artifacts=StageArtifacts(),
        agent_explanation=outcome.agent_explanation,
        next_action=outcome.next_action,
        provenance=outcome.provenance,
        updated_at=_now_iso(),
    )


# --- Tier-0/Tier-1 fidelity discriminator (ADR-028 P-fidelity) ---------------
# A machine-checkable label distinguishing, for a TOOL-bound stage, whether the real tool
# ran on REAL data (tier_1_real) or on DUMMY/sandbox data (tier_0_dummy). It is the
# anti-over-claim primitive that UNBLOCKS honestly crossing the tool wall (the deferred
# geometry.run dummy-mode): without it a vacuous dummy result could be read as a real
# validation. It rides metrics (StageMetrics extra="allow") and is structurally incapable
# of inflating the N/13 agent-driven count, which is keyed PURELY on StageProvenance:
#   * the FLAT string ``metrics.fidelityTier`` survives the frontend metrics parser
#     (which keeps number|string values) and auto-renders as the user-visible disclosure;
#   * the NESTED ``metrics.fidelity`` dict is DROPPED by that parser (objects discarded),
#     so it can never reach provenanceCoverage — it is the machine-checkable evidence
#     channel asserted by the backend contract test (mirrors metrics.recovery exactly).
# A planning-only / scripted (no-tool) stage emits NEITHER key (implicit not_applicable),
# so existing runs are byte-unchanged (back-compat). This slice ships the vocabulary +
# helper + its contract test; the live PRODUCER is the deferred geometry.run dummy crossing.


class StageFidelityTier(StrEnum):
    """Closed vocabulary for the tool-fidelity of a stage's underlying computation.

    Deliberately NOT a 4th :class:`StageProvenance` value (provenance labels the TEXT
    source; this labels the DATA fidelity of a real tool run — and a 4th provenance value
    would be downgraded to ``scripted_demo`` by the frontend's defensive ``asProvenance``),
    and NOT a :class:`StageState` schema field — it rides ``metrics`` (``extra="allow"``)
    so it never expands the ADR-028 D2-sanctioned schema surface.
    """

    NOT_APPLICABLE = "not_applicable"  # no tool ran (planning-only / scripted stage)
    TIER_0_DUMMY = "tier_0_dummy"  # real tool ran on DUMMY/sandbox data (NOT a validation)
    TIER_1_REAL = "tier_1_real"  # real tool ran on REAL data


def fidelity_metrics(*, tool_ran: bool, data_real: bool, disclosure: str) -> dict[str, object]:
    """Build the fidelity-discriminator metrics for a stage, or ``{}`` if no tool ran.

    Returns the two co-located keys a tool-bound producer merges into its ``metrics``: a
    flat ``fidelityTier`` (user-visible disclosure, survives the FE parser) and a nested
    ``fidelity`` dict (machine-checkable evidence, dropped by the FE parser so it can never
    inflate N/13). The tier is DERIVED from ``data_real`` (``tier_0_dummy`` ⇔ not real), so
    the closed vocabulary cannot drift. A no-tool stage (``tool_ran=False``) returns ``{}``
    — the implicit ``not_applicable`` tier — keeping planning/scripted stages byte-unchanged.

    Intentionally emits NO measurement-shaped keys (watertight/manifold/volume/shortEdges/…):
    a dummy producer MUST suppress those so a vacuous pass can never read as a measured
    validation (the anti-vacuous-pass invariant the next slice depends on).

    A ``tier_0_dummy`` result MUST carry a non-empty ``disclosure`` caveat — this is
    ENFORCED (raises ``ValueError``), not merely conventional, so a dummy/sandbox result
    can never ship without an honesty hedge (ADR-028 anti-over-claim; Codex P-fidelity R0
    P2). A genuine ``tier_1_real`` result may omit the caveat.
    """
    if not tool_ran:
        return {}
    tier = StageFidelityTier.TIER_1_REAL if data_real else StageFidelityTier.TIER_0_DUMMY
    if tier is StageFidelityTier.TIER_0_DUMMY and not disclosure.strip():
        raise ValueError(
            "tier_0_dummy requires a non-empty disclosure caveat — a dummy/sandbox result "
            "must never ship without an honesty hedge (ADR-028 anti-over-claim)."
        )
    return {
        "fidelityTier": tier.value,
        "fidelity": {
            "tier": tier.value,
            "toolRan": True,
            "dataReal": data_real,
            "disclosure": disclosure,
        },
    }


# --- Real geometry-node dummy crossing (ADR-028 P-geomrun) --------------------
# The FIRST time a real tool-bound agent node executes in the live pipeline: for a
# NACA/wing request, CALL the real agents.geometry.run under execution_mode=dummy.
# CRUX (adjudicated by pre-flight wf_2cd96131-8f8, stance REFRAME): on dummy data
# check_geometry's valid=True is a JSON round-trip tautology (read back from the
# sidecars the dummy writer hardcoded), NOT a measurement — so the ONLY net-new honest
# fact over the planning stand-in is toolRan=True (the real node + checker code ran).
# It is therefore an ADDITIVE tier_0_dummy wiring-proof, NOT a validation: NO measurement
# keys surfaced, cadKernelRan/defectCheckRun pinned False, the disclosure says all of it,
# provenance stays deterministic_agent (N/13 UNCHANGED — architecture progress, not a
# coverage increase). Gated to the dummy regime (FREECAD_AVAILABLE=False); a real kernel
# would produce real geometry (tier_1_real) which this tier_0 projection must never
# mislabel, so the dispatcher routes a real-kernel host back to the planning stand-in.


def geometry_dummy_exec_to_stage_state(
    run_id: str,
    user_request: str,
    *,
    upstream_case_id: str | None = None,
    status: StageStatus = StageStatus.SUCCESS,
    progress: float = 1.0,
) -> StageState:
    """Project a real-but-DUMMY ``agents.geometry.run`` execution into the
    GEOMETRY_VALIDATION wire state (ADR-028 P-geomrun + P-handoff).

    Honesty contract (the deliverable): the ONLY net-new *fidelity* claim over the planning
    stand-in is ``toolRan=True``. With no FreeCAD kernel (``FREECAD_AVAILABLE=False``) the
    driver writes a 10-byte placeholder STEP (NOT ISO-10303; ADR-008 N-3) and
    ``check_geometry``'s ``valid=True`` is a sidecar tautology — NOT a measured solid. So
    this rides ``fidelityTier=tier_0_dummy`` with NO measurement keys (watertight/manifold/
    volume), ``cadKernelRan``/``defectCheckRun`` pinned ``False``, the disclosure stating
    all of it, and ``provenance=deterministic_agent`` (N/13 unchanged). Requires the dummy
    regime (raises otherwise) so a real-kernel result can never be mislabeled tier_0.

    P-handoff: ``upstream_case_id`` is the PROJECT_INTAKE node's request-derived case id —
    the FIRST real upstream→downstream inter-agent data dependency in the live pipeline. When
    it is a valid case id the geometry node CONSUMES it (instead of fabricating the legacy
    ``AI-FEA-P0-05`` stand-in); an absent/invalid handoff falls back to that stand-in. Only
    the case *number* flows — the geometry itself is still a fixed NACA0012 placeholder and
    ``analysis_type``/``objectives`` are NOT yet threaded (a partial, honest handoff). This
    adds NO measurement and does NOT change provenance or the N/13 count.
    """
    from agents.geometry import run as run_geometry
    from tools.freecad_driver import FREECAD_AVAILABLE

    if FREECAD_AVAILABLE:
        # Defense-in-depth: a real kernel produces REAL geometry (tier_1_real). This
        # tier_0_dummy projector must never run against it — the dispatcher gates on
        # `not FREECAD_AVAILABLE`, but assert it here too so a direct call can't mislabel.
        raise RuntimeError(
            "geometry_dummy_exec_to_stage_state requires the dummy regime "
            "(FREECAD_AVAILABLE=False); a real kernel must route to a tier_1_real path."
        )

    outcome = analyze_geometry_plan(user_request)  # reuse family / refSource / fromHint
    # P-handoff: consume the upstream intake node's case id when it handed off a valid one;
    # only an absent/invalid handoff falls back to the legacy AI-FEA-P0-05 stand-in. This is
    # the first real upstream→downstream inter-agent data dependency — the geometry node no
    # longer fabricates its own case number.
    case_id = upstream_case_id if _valid_case_id(upstream_case_id) else "AI-FEA-P0-05"
    case_id_from_intake = case_id == upstream_case_id
    # The dummy geometry is a FIXED NACA0012 stand-in — NOT parsed from the request (the
    # 10-byte placeholder makes the specific profile cosmetic). Disclosed below so the stage
    # never reads as "the request's exact profile was executed" (Codex P-geomrun R0 P2).
    plan = SimPlan(
        case_id=case_id,
        geometry=GeometrySpec(kind="naca", parameters={"profile": "NACA0012"}),
    )
    with tempfile.TemporaryDirectory(prefix="geom_dummy_") as psd:
        state = {
            "plan": plan,
            "project_state_dir": psd,
            "execution_mode": {"geometry_source": "dummy"},
        }
        result = run_geometry(state)  # REAL node + checker execute; dummy data
        # Retain NO path/artifact under psd; surface NO measurement from the (tautological)
        # check report — a geometry_path is the wiring fact proving the node executed.
        tool_ran = "geometry_path" in result
    if not tool_ran:
        # The wiring fact is absent → the node did NOT execute as claimed. Refuse to build a
        # SUCCESS stage whose disclosure hard-claims toolRan=True (Codex P-geomrun R0 P1).
        raise RuntimeError(
            "agents.geometry.run returned no geometry_path; refusing to claim toolRan=True."
        )

    # P-handoff disclosure clause: state HOW the case id was obtained so the (real) handoff
    # is never confused with a geometry capability, and a fallback is never read as a handoff.
    handoff = (
        f"案例号 {case_id} 系从上游 PROJECT_INTAKE 节点决策接力消费"
        "（首个真实 upstream→downstream agent 数据依赖；仅案例号流动，"
        "analysis_type/objectives 尚未接力 — partial honest handoff）。"
        if case_id_from_intake
        else f"案例号回退至占位 {case_id}（上游 intake 未提供有效案例号，非真实接力）。"
    )
    disclosure = (
        "真实 agents/geometry.run 节点已在 live pipeline 中执行"
        "（toolRan=True，接线验证 / wiring proof）：但未检测到 FreeCAD 内核"
        "（FREECAD_AVAILABLE=False，cadKernelRan=False），仅写出 10 字节占位 STEP"
        "（非 ISO-10303，ADR-008 N-3「NOT valid for Demo Gate」）；check_geometry 返回的"
        " valid=True 系从硬编码 JSON sidecar 读回的 tautology、非真实测量"
        "（defectCheckRun=False，未做有效缺陷校验）；未验证任何真实几何（tier_0_dummy）。"
        "几何采用固定 NACA0012 占位 profile（非从请求逐字解析）。"
        f"{handoff}"
        "唯一净增事实 = 真实节点已接线执行。"
    )
    family = outcome.metrics["geometryFamily"]
    explanation = f"几何 family = {family}（源自请求确定性规划）。{disclosure}"
    metrics: dict[str, object] = {
        "geometryFamily": family,
        "refSource": outcome.metrics["refSource"],
        "fromHint": outcome.metrics["fromHint"],
        # P-handoff: the case id actually consumed (intake's, or the stand-in fallback). A
        # plain wire string — NOT a measurement — so a downstream consumer / the FE can prove
        # the intake→geometry data dependency without inflating the fidelity tier or N/13.
        "caseId": case_id,
        # no REAL kernel ran and the check was vacuous → both pinned False (carried from
        # the planning floor); the tier_0_dummy + disclosure carry the honest nuance.
        "cadKernelRan": False,
        "defectCheckRun": False,
    }
    metrics.update(fidelity_metrics(tool_ran=tool_ran, data_real=False, disclosure=disclosure))
    return StageState(
        run_id=run_id,
        stage=WorkflowStage.GEOMETRY_VALIDATION,
        status=status,
        progress=progress,
        current_object=_GEOMETRY_PLAN_CURRENT_OBJECT,
        description=f"几何节点 dummy 执行（{family}）",
        metrics=StageMetrics.model_validate(metrics),
        artifacts=StageArtifacts(),  # the dummy STEP lived under the temp dir; nothing real
        agent_explanation=explanation,
        next_action=outcome.next_action,
        provenance=StageProvenance.DETERMINISTIC_AGENT,
        updated_at=_now_iso(),
    )


def geometry_stage_state(
    run_id: str,
    user_request: str,
    *,
    upstream_case_id: str | None = None,
    status: StageStatus = StageStatus.SUCCESS,
    progress: float = 1.0,
) -> StageState:
    """Route the GEOMETRY_VALIDATION stage (ADR-028).

    A NACA/wing request **in the dummy regime** crosses to the real geometry node
    (:func:`geometry_dummy_exec_to_stage_state`, tier_0_dummy wiring proof); every other
    family — and any host with a real FreeCAD kernel (``FREECAD_AVAILABLE=True``, which
    would yield real geometry this tier_0 path must not mislabel) — stays on the planning
    stand-in (:func:`geometry_plan_to_stage_state`). Keeping the ``FREECAD_AVAILABLE``
    check here (agent layer) keeps the facade free of a ``tools.*`` import.

    ``upstream_case_id`` (P-handoff) is the PROJECT_INTAKE node's request-derived case id,
    consumed only on the crossing path (the planning stand-in has no SimPlan to feed it into).
    """
    from tools.freecad_driver import FREECAD_AVAILABLE

    outcome = analyze_geometry_plan(user_request)
    if outcome.metrics["geometryFamily"] == "naca_wing" and not FREECAD_AVAILABLE:
        return geometry_dummy_exec_to_stage_state(
            run_id,
            user_request,
            upstream_case_id=upstream_case_id,
            status=status,
            progress=progress,
        )
    return geometry_plan_to_stage_state(run_id, outcome, status=status, progress=progress)


# --- LangGraph-runtime geometry projection (ADR-029 P1) ----------------------
# P1 extends the dedicated truncated graph to architect→geometry: the geometry node CONSUMES
# the SimPlan from the SHARED graph state that the (preceding) architect step left there —
# the FIRST cross-node graph data dependency. This projector maps the graph's accumulated
# final SimState (geometry has ALREADY run inside the graph; we do NOT re-run it) into the
# GEOMETRY_VALIDATION wire state. It carries the SAME tier_0_dummy honesty pins as the
# direct P-geomrun projector (no measurement key, cadKernelRan/defectCheckRun False,
# disclosure of the 10-byte STEP + tautological valid), and additionally discloses WHO
# authored the consumed plan (``plan_authored_by``): the deterministic rule-based seed
# (keyless — the LLM architect node authored nothing) vs the LLM architect node (key
# present — the real architect→geometry authorship dependency). Provenance stays
# deterministic_agent → N/13 unchanged.

_GRAPH_GEOM_RUNNER_TAG = "langgraph-architect-geometry"
_GRAPH_MESH_RUNNER_TAG = "langgraph-architect-geometry-mesh"
_MESH_CURRENT_OBJECT = "mesh_model"
_GRAPH_SOLVER_RUNNER_TAG = "langgraph-architect-geometry-mesh-solver"
_SOLVER_CURRENT_OBJECT = "solver_model"

# ADR-029 P3 anti-vacuous-pass: every result-shaped key a GREEN ``agents.solver.run`` could
# surface (its success return adds frd_path/solve_path/solve_metadata + parsed scalars). A
# tier_0_dummy faulted-solve projection MUST suppress ALL of these — a dummy/rejected solve can
# never present a measured result. Machine-checked by the wiring test (not "structurally true
# today"), because :func:`graph_solver_to_stage_state` is the load-bearing seam. Both camel + snake.
_SOLVER_MEASUREMENT_KEYS: frozenset[str] = frozenset(
    {
        "frdPath",
        "frd_path",
        "solvePath",
        "solve_path",
        "solveMetadata",
        "solve_metadata",
        "maxVonMisesPa",
        "max_von_mises_pa",
        "maxVonMises",
        "max_von_mises",
        "maxDisplacementM",
        "max_displacement_m",
        "maxDisplacement",
        "max_displacement",
        "safetyFactor",
        "safety_factor",
        "residual",
        "finalResidual",
        "final_residual",
        "converged",
        "wallTimeS",
        "wall_time_s",
        "ccxVersion",
        "ccx_version",
        "frames",
        "fields",
        "yieldPa",
        "yield_pa",
    }
)


def graph_geometry_to_stage_state(
    final_sim_state: Mapping[str, object],
    user_request: str,
    *,
    run_id: str,
    plan_authored_by: str,
    status: StageStatus = StageStatus.SUCCESS,
    progress: float = 1.0,
) -> StageState:
    """Project a 2-node ``architect→geometry`` graph's final SimState into GEOMETRY_VALIDATION.

    ``final_sim_state`` is the accumulated state from
    :func:`agents.graph_runner.run_geometry_via_graph` (the geometry node already executed
    inside the graph under ``execution_mode=dummy``). ``plan_authored_by`` is
    ``"deterministic_seed"`` (keyless — a rule-based plan was seeded so the geometry node had
    something to consume) or ``"architect_llm"`` (the LLM architect node authored the plan the
    geometry node then consumed — the genuine cross-node authorship dependency).

    Refuses to claim ``toolRan=True`` without the ``geometry_path`` wiring fact (mirrors the
    P-geomrun guard). Tier_0_dummy honesty pins are identical to the direct projector; the
    ONLY net-new facts are the cross-node graph dependency + who authored the plan.
    """
    plan = final_sim_state.get("plan")
    if not isinstance(plan, SimPlan):
        raise RuntimeError(
            "graph_geometry_to_stage_state: final SimState carries no SimPlan; the "
            "architect→geometry graph did not produce a consumable plan."
        )
    geometry_path = final_sim_state.get("geometry_path")
    tool_ran = bool(geometry_path)
    if not tool_ran:
        # The wiring fact is absent → the geometry node did NOT execute as claimed. Refuse to
        # build a SUCCESS stage that hard-claims toolRan=True (Codex P-geomrun R0 P1).
        raise RuntimeError(
            "architect→geometry graph returned no geometry_path; refusing to claim toolRan=True."
        )

    case_id = plan.case_id
    outcome = analyze_geometry_plan(user_request)  # reuse family / refSource / fromHint
    family = outcome.metrics["geometryFamily"]

    authored = (
        (
            "本阶段 SimPlan 由 LLM architect 节点产出，并经图状态传递给 geometry 节点消费"
            "（真实 architect→geometry 作者依赖）。"
        )
        if plan_authored_by == "architect_llm"
        else (
            "本阶段 SimPlan 由确定性规则代理（analyze_intake + 固定 NACA 几何 spec）"
            "构造并 seed 进图状态；keyless 的 LLM architect 节点未产出 plan（pass-through）。"
        )
    )
    disclosure = (
        "2-node 图 architect→geometry 经真实 LangGraph 运行时（compiled graph .invoke）执行；"
        "geometry 节点从共享图状态消费 SimPlan（首个跨节点图数据依赖）。"
        f"{authored}"
        "但未检测到 FreeCAD 内核（FREECAD_AVAILABLE=False，cadKernelRan=False），"
        "仅写出 10 字节占位 STEP（非 ISO-10303，ADR-008 N-3「NOT valid for Demo Gate」）；"
        "check_geometry 返回的 valid=True 系从硬编码 JSON sidecar 读回的 tautology、非真实测量"
        "（defectCheckRun=False，未做有效缺陷校验）；未验证任何真实几何（tier_0_dummy）。"
        "几何采用固定 NACA0012 占位 profile（非从请求逐字解析）。"
        f"案例号 {case_id} 经图状态由 intake 决策流入 geometry。"
        "唯一净增事实 = 真实 2-node 图运行时执行 + 跨节点数据依赖接线。"
    )
    explanation = f"几何 family = {family}（源自请求确定性规划）。{disclosure}"
    metrics: dict[str, object] = {
        "geometryFamily": family,
        "refSource": outcome.metrics["refSource"],
        "fromHint": outcome.metrics["fromHint"],
        "caseId": case_id,
        "cadKernelRan": False,
        "defectCheckRun": False,
        # ADR-029 P1 architecture-wiring facts (NOT FEA measurements, NOT a provenance flip):
        "graphNodeRan": True,
        "graphRunner": _GRAPH_GEOM_RUNNER_TAG,
        "planAuthoredBy": plan_authored_by,
    }
    metrics.update(fidelity_metrics(tool_ran=tool_ran, data_real=False, disclosure=disclosure))
    return StageState(
        run_id=run_id,
        stage=WorkflowStage.GEOMETRY_VALIDATION,
        status=status,
        progress=progress,
        current_object=_GEOMETRY_PLAN_CURRENT_OBJECT,
        description=f"几何节点 dummy 执行（{family}，2-node 图驱动）",
        metrics=StageMetrics.model_validate(metrics),
        artifacts=StageArtifacts(),  # the dummy STEP lived under the temp dir; nothing real
        agent_explanation=explanation,
        next_action=outcome.next_action,
        provenance=StageProvenance.DETERMINISTIC_AGENT,
        updated_at=_now_iso(),
    )


def graph_mesh_to_stage_state(
    final_sim_state: Mapping[str, object],
    user_request: str,
    *,
    run_id: str,
    plan_authored_by: str,
    status: StageStatus = StageStatus.SUCCESS,
    progress: float = 1.0,
) -> StageState:
    """Project a 3-node ``architect→geometry→mesh`` graph's final SimState into MESH_GENERATION.

    ``final_sim_state`` is the accumulated state from
    :func:`agents.graph_runner.run_mesh_via_graph` (the mesh node already executed inside the
    graph, consuming the geometry node's ``geometry_path`` — the second cross-node data
    dependency). ``plan_authored_by`` is ``"deterministic_seed"`` (keyless — a NACA plan was
    seeded) or ``"architect_llm"`` (the LLM architect node authored the plan that flowed
    architect→geometry→mesh).

    THE ``dummyFidelityInputs=True`` GUARD (ADR-029 P2 — the load-bearing primitive): the mesh
    node ran ``check_mesh_quality``, which IS a real numpy measurement (scaled Jacobian /
    aspect ratio) — but over a hardcoded 4-node/1-tet C3D4 *fallback* mesh of DUMMY geometry
    (no gmsh kernel, upstream a 10-byte placeholder STEP). So the numbers are tautological (a
    unit tetra trivially passes), NOT validated mesh fidelity. This flag asserts the
    measurement's inputs were dummy, so the real numpy number can never be presented as a
    validated mesh. Honesty pins identical to the geometry crossing: ``tier_0_dummy``,
    ``meshKernelRan=False``, ZERO measurement-shaped keys surfaced (anti-vacuous-pass),
    provenance stays ``deterministic_agent`` (no 4th value; N/13 rises by exactly 1 because a
    real node now drives the stage — architecture progress at dummy fidelity, NOT a validation).
    Refuses to claim ``toolRan=True`` without the ``mesh_path`` wiring fact.
    """
    plan = final_sim_state.get("plan")
    if not isinstance(plan, SimPlan):
        raise RuntimeError(
            "graph_mesh_to_stage_state: final SimState carries no SimPlan; the "
            "architect→geometry→mesh graph did not produce a consumable plan."
        )
    mesh_path = final_sim_state.get("mesh_path")
    tool_ran = bool(mesh_path)
    if not tool_ran:
        # The wiring fact is absent → the mesh node did NOT execute (or quality failed). Refuse
        # to build a SUCCESS stage that hard-claims toolRan=True (mirrors the P-geomrun guard).
        raise RuntimeError(
            "architect→geometry→mesh graph returned no mesh_path; refusing to claim toolRan=True."
        )

    case_id = plan.case_id
    outcome = analyze_geometry_plan(user_request)  # reuse family / refSource / fromHint
    family = outcome.metrics["geometryFamily"]

    authored = (
        (
            "本阶段 SimPlan 由 LLM architect 节点产出，经图状态传递给 geometry→mesh 节点链消费"
            "（真实 architect→geometry→mesh 作者依赖）。"
        )
        if plan_authored_by == "architect_llm"
        else (
            "本阶段 SimPlan 由确定性规则代理（analyze_intake + 固定 NACA 几何 spec）构造并 seed "
            "进图状态；keyless 的 LLM architect 节点未产出 plan（pass-through）。"
        )
    )
    disclosure = (
        "3-node 图 architect→geometry→mesh 经真实 LangGraph 运行时（compiled graph .invoke）执行；"
        "mesh 节点从共享图状态消费 geometry_path（第二个跨节点图数据依赖）。"
        f"{authored}"
        "但未检测到 gmsh 内核（GMSH_AVAILABLE=False，meshKernelRan=False），generate_mesh 仅写出"
        "硬编码 4-node/1-tet C3D4 占位网格（generation_mode=fallback），其上游是 10 字节占位 STEP"
        "（非 ISO-10303）。check_mesh_quality 虽是真实 numpy 测量"
        "（scaled Jacobian / aspect ratio），"
        "但作用于该 dummy 几何派生的单一单位四面体——数值系 tautological（单位四面体必然过阈），"
        "非真实网格保真度（dummyFidelityInputs=True）；故不 surface 任何测量形态的网格指标"
        "（min_scaled_jacobian / max_aspect_ratio / bad_element 一律抑制，anti-vacuous-pass）。"
        "未验证任何真实网格（tier_0_dummy）。"
        f"案例号 {case_id} 经图状态由 intake→geometry 流入 mesh。"
        "唯一净增事实 = 真实 mesh 节点经 3-node 图驱动 MESH_GENERATION（N/13 +1），保真度为 dummy。"
    )
    explanation = f"网格节点 dummy 执行（{family}，3-node 图驱动）。{disclosure}"
    metrics: dict[str, object] = {
        "geometryFamily": family,
        "caseId": case_id,
        "meshKernelRan": False,
        # ADR-029 P2 — the load-bearing honesty guard: real numpy measurement, dummy inputs.
        "dummyFidelityInputs": True,
        # ADR-029 architecture-wiring facts (NOT FEA measurements, NOT a provenance flip):
        "graphNodeRan": True,
        "graphRunner": _GRAPH_MESH_RUNNER_TAG,
        "planAuthoredBy": plan_authored_by,
    }
    metrics.update(fidelity_metrics(tool_ran=tool_ran, data_real=False, disclosure=disclosure))
    return StageState(
        run_id=run_id,
        stage=WorkflowStage.MESH_GENERATION,
        status=status,
        progress=progress,
        current_object=_MESH_CURRENT_OBJECT,
        description=f"网格节点 dummy 执行（{family}，3-node 图驱动）",
        metrics=StageMetrics.model_validate(metrics),
        artifacts=StageArtifacts(),  # the dummy fallback mesh lived under the temp dir
        agent_explanation=explanation,
        # Point to the genuine next stage (mesh_quality_check), NOT geometry-planning's
        # "进入材料赋予" — reusing analyze_geometry_plan's next_action here would misdirect the
        # user past the mesh quality gate (Codex P2 R0 P3).
        next_action="进入网格质量检查（mesh_quality_check）。",
        provenance=StageProvenance.DETERMINISTIC_AGENT,
        updated_at=_now_iso(),
    )


def graph_solver_to_stage_state(
    final_sim_state: Mapping[str, object],
    user_request: str,
    *,
    run_id: str,
    plan_authored_by: str,
    status: StageStatus = StageStatus.SUCCESS,
    progress: float = 1.0,
) -> StageState:
    """Project a 4-node ``architect→geometry→mesh→solver`` graph's final SimState into SOLVER_RUN
    (ADR-029 P3 — the SOLVER ISOLATION GATE; the FIRST graph that launches a real ccx subprocess).

    ``final_sim_state`` is the accumulated state from
    :func:`agents.graph_runner.run_solver_via_graph` (the solver node already executed inside the
    graph, consuming the mesh node's dummy fallback ``mesh_path`` and really invoking ``ccx``).
    ``plan_authored_by`` is ``"deterministic_seed"`` (keyless) or ``"architect_llm"``.

    HONESTY ENVELOPE — the solve is a FAILURE by construction, projected FAILED (never green):
    the dummy fallback mesh (hardcoded 4-node/1-tet C3D4, no gmsh kernel) defines no
    ``Nall/Nfix/Eall`` sets, so a ccx-present host fatal-errors at deck parse (``rc=201``,
    classified ``solver_convergence`` ONLY via the driver's ``returncode!=0`` catch-all — a known
    driver limitation, **NOT** numerical divergence) and a ccx-less host ``PREFLIGHT_FAIL``s.
    Either way NO solve occurred. ``dummyFidelityInputs=True`` hard-blocks any Tier-1/2 implication
    even on a (structurally impossible) green solve. Honesty pins identical to the mesh crossing:
    ``tier_0_dummy``, ZERO measurement-shaped keys surfaced (anti-vacuous-pass — see
    :data:`_SOLVER_MEASUREMENT_KEYS`), provenance stays ``deterministic_agent`` (no 4th value).

    The WIRING FACT is the ``solver`` history entry (``any(h['node']=='solver')``) — NOT a
    tautological ``fault_class`` key (the seed sets ``fault_class`` unconditionally) and NOT
    ``frd_path`` (absent on a faulted solve). Refuses to claim ``toolRan=True`` without it; refuses
    to project a tier_0_dummy FAILED stage if a real ``frd_path`` IS present (that would be a real
    solve this projector must never mislabel). The disclosure is authored from this function's own
    static knowledge — NEVER from the solver history ``msg`` (empirically the ccx banner ``****``).
    """
    plan = final_sim_state.get("plan")
    if not isinstance(plan, SimPlan):
        raise RuntimeError(
            "graph_solver_to_stage_state: final SimState carries no SimPlan; the "
            "architect→geometry→mesh→solver graph did not produce a consumable plan."
        )
    history = final_sim_state.get("history")
    history_list = list(history) if isinstance(history, (list, tuple)) else []
    solver_entries = [
        h for h in history_list if isinstance(h, Mapping) and h.get("node") == "solver"
    ]
    tool_ran = bool(solver_entries)
    if not tool_ran:
        # The non-tautological wiring fact is absent → the solver node did NOT execute as claimed
        # (e.g. the bare missing-mesh early returns append no history). Refuse to claim toolRan.
        raise RuntimeError(
            "architect→geometry→mesh→solver graph produced no solver history entry; "
            "refusing to claim toolRan=True (the solver node did not run)."
        )
    if final_sim_state.get("frd_path"):
        # A real .frd means the solve SUCCEEDED on real data — never mislabel that tier_0_dummy.
        raise RuntimeError(
            "graph_solver_to_stage_state: final SimState carries an frd_path (a successful solve); "
            "this tier_0_dummy faulted-solve projector must not mislabel a real solve."
        )

    # Read the genuine returncode (a clean int, NOT the banner msg). A returncode is present ONLY
    # when a real ccx subprocess ran and returned (the _failed_solve path). _preflight_failure (ccx
    # absent from PATH), _unsupported_backend_failure (non-CalculiX), and _solver_syntax_failure
    # (deck preparation failed pre-solve) ALSO append a solver history entry but launch NO ccx
    # subprocess → returncode is None. So "solver node ran" (graphNodeRan, always true here) MUST be
    # distinguished from "ccx subprocess launched" (ccx_launched) — Codex P3 R0 P1: never claim an
    # attempted solve / deck-parse fault for a preflight/unsupported fault where ccx never launched.
    returncode = solver_entries[-1].get("returncode")
    ccx_launched = returncode is not None
    if ccx_launched:
        launch_clause = "并真实启动 ccx 子进程（dry_run=False，于 tempdir 内隔离、部署即删）"
        fault_clause = (
            f"ccx 返回 rc={returncode}（dummy 网格未定义 Nall/Nfix/Eall 集，deck 解析阶段即致命"
            "报错；驱动层仅凭 returncode!=0 兜底归类 solver_convergence/DIVERGED——"
            "已知驱动局限，非真实数值发散）"
        )
        ccx_net_fact = "并真实启动了 ccx 子进程"
        en_fault = (
            "ccx launched and FAILED at deck parse (rc=201; no Nall/Nfix/Eall sets) — NOT "
            "numerical divergence; the driver labels it solver_convergence only via its "
            "returncode!=0 catch-all"
        )
    else:
        launch_clause = (
            "但 ccx 子进程未启动（环境预检失败/ccx 不在 PATH，"
            "或后端不支持，或求解前 deck 准备失败）"
        )
        fault_clause = "ccx 子进程未启动（环境预检失败 / 后端不支持 / deck 准备失败）"
        ccx_net_fact = "（但本次 ccx 子进程未启动）"
        en_fault = (
            "the ccx subprocess did NOT launch (preflight failed / unsupported backend / "
            "deck-prep error)"
        )

    case_id = plan.case_id
    outcome = analyze_geometry_plan(user_request)  # reuse family / refSource / fromHint
    family = outcome.metrics["geometryFamily"]

    authored = (
        (
            "本阶段 SimPlan 由 LLM architect 节点产出，经图状态传递给 "
            "geometry→mesh→solver 节点链消费"
            "（真实 architect→geometry→mesh→solver 作者依赖）。"
        )
        if plan_authored_by == "architect_llm"
        else (
            "本阶段 SimPlan 由确定性规则代理（analyze_intake + 固定 NACA 几何 spec）构造并 seed "
            "进图状态；keyless 的 LLM architect 节点未产出 plan（pass-through）。"
        )
    )
    disclosure = (
        "4-node 图 architect→geometry→mesh→solver 经真实 LangGraph 运行时（compiled graph .invoke）"
        "执行；solver 节点从共享图状态消费 mesh_path（dummy fallback 网格）"
        f"{launch_clause}。"
        f"{authored}"
        "但上游无 gmsh 内核，generate_mesh 仅写出硬编码 4-node/1-tet C3D4 占位网格"
        "（generation_mode=fallback），其上游是 10 字节占位 STEP（非 ISO-10303）。"
        f"{fault_clause}——故无任何求解发生。"
        "即便某 seed 令其绿色求解，其输入仍为 dummy 保真（单位四面体 + 占位 STEP），任何求解数值"
        "均为 tautological garbage-in（dummyFidelityInputs=True）。"
        "故本阶段状态记为 FAILED（求解被拒，未求解），绝不显示为绿色 SUCCESS；"
        "不 surface 任何测量形态 solver 指标（maxVonMises / maxDisplacement / "
        "safetyFactor / residual / converged / frdPath 一律抑制，anti-vacuous-pass）；"
        "不产出任何持久 artifact（ccx scratch 随 tempdir 删除）。"
        "真实管线在此中止：被拒/未启动的求解无从监控收敛 / 后处理 / 分析结果"
        "（下游阶段保持 PENDING、未到达）。"
        f"唯一净增事实 = 真实 solver 节点经 4-node 图驱动 SOLVER_RUN{ccx_net_fact}，"
        "保真度为 dummy；因管线中止，N/13 代理覆盖净增约为 0（此为接线证明，非覆盖增益）。"
        f"案例号 {case_id} 经图状态由 intake→geometry→mesh 流入 solver。"
        "[EN: the 4-node compiled graph ran; the solver node executed and "
        f"{en_fault}. The stage is FAILED (solve rejected / not run, nothing solved), never green "
        "SUCCESS; the pipeline halts so no convergence/results are fabricated downstream. "
        "dummyFidelityInputs=True hard-blocks any Tier-1/2 implication; tier_0_dummy. Net "
        "agent-driven coverage ~unchanged — the deliverable is the wiring proof + the honest "
        "halt, not a coverage increase.]"
    )
    explanation = f"求解节点 dummy 执行并被拒（{family}，4-node 图驱动，FAILED）。{disclosure}"
    metrics: dict[str, object] = {
        "geometryFamily": family,
        "caseId": case_id,
        # The unambiguous wire story: the solver NODE executed (graphNodeRan, always true here), a
        # real ccx subprocess launched ONLY when a returncode came back (ccxSubprocessLaunched), and
        # solverAttempted tracks that ccx launch — NOT merely the node running — so a preflight /
        # unsupported / deck-prep fault (node ran, ccx never launched) is never over-claimed as an
        # attempted solve (Codex P3 R0 P1). Nothing was ever solved (solverRan=False).
        "solverAttempted": ccx_launched,
        "ccxSubprocessLaunched": ccx_launched,
        "solverRan": False,
        # ADR-029 P3 — the load-bearing honesty guard: the measurement's inputs were DUMMY fidelity.
        "dummyFidelityInputs": True,
        # ADR-029 architecture-wiring facts (NOT FEA measurements, NOT a provenance flip):
        "graphNodeRan": True,
        "graphRunner": _GRAPH_SOLVER_RUNNER_TAG,
        "planAuthoredBy": plan_authored_by,
    }
    metrics.update(fidelity_metrics(tool_ran=tool_ran, data_real=False, disclosure=disclosure))
    return StageState(
        run_id=run_id,
        stage=WorkflowStage.SOLVER_RUN,
        # Hard-set FAILED regardless of the caller's status arg: the ccx solve was rejected, so the
        # badge must never be green (mirrors the real-LE10 solve-failure projection + Codex M4 R0 P2
        # "a failed solve is never shown as a plain green success"). The honest WIRING achievement
        # rides metrics (graphNodeRan / solverAttempted), not the stage badge.
        status=StageStatus.FAILED,
        progress=progress,
        current_object=_SOLVER_CURRENT_OBJECT,
        description=f"求解节点 dummy 执行被拒（{family}，4-node 图驱动）",
        metrics=StageMetrics.model_validate(metrics),
        artifacts=StageArtifacts(),  # ccx scratch lived under the temp dir; nothing real persisted
        agent_explanation=explanation,
        next_action=(
            "真实管线在此中止（dummy 网格求解被拒）；不进入收敛监控 / 后处理。"
            "接入真实网格（LE10 级）后方可得真实求解。"
        ),
        errors=[
            StageError(
                fault_class=(FaultClass.SOLVER_CONVERGENCE if ccx_launched else FaultClass.UNKNOWN),
                message=(
                    "ccx rejected the dummy fallback mesh (no Nall/Nfix/Eall sets)"
                    if ccx_launched
                    else "ccx subprocess did not launch (preflight / unsupported / deck-prep)"
                ),
                detail=(
                    "graph-driven tier_0_dummy solve on the hardcoded 4-node/1-tet fallback mesh. "
                    + (
                        "ccx launched and failed at deck parse (rc=201); classified "
                        "solver_convergence only via the driver's returncode!=0 catch-all "
                        "(known limitation; not numerical divergence)."
                        if ccx_launched
                        else "ccx never launched (preflight failed / unsupported backend / deck "
                        "preparation error); no solve was attempted."
                    )
                    + " Expected for dummy-fidelity inputs — deliverable = the graph-wiring proof."
                ),
            )
        ],
        provenance=StageProvenance.DETERMINISTIC_AGENT,
        updated_at=_now_iso(),
    )
