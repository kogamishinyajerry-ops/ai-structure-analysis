"""Workbench-agent → wire-state projection + deterministic intake analysis (ADR-028).

This module lives in the **agent layer** (NOT ``backend/app/workbench/``) precisely so
it may import ``schemas.sim_state`` / ``schemas.sim_plan`` freely while honoring
ADR-015 rule 3 ("no file under ``backend/app/workbench/`` imports ``schemas.sim_state``").
The workbench facade (``backend/app/workbench/agent_facade.py``) calls into here; the
``StageState`` returned is the already-projected wire object the facade hands back, so
the facade never touches ``SimState``.

ADR-028 P1 scope (D6): the ``PROJECT_INTAKE`` stage only.

* :func:`analyze_intake` is the **deterministic** ("rule-based agent", per ADR-028 D5)
  intake node — it derives physics type, objectives and a naming-compliant case id
  from the **actual** request text with **no LLM call**, so its explanation varies
  with input (the honest improvement over the former single hardcoded constant).
* :func:`sim_state_to_stage_state` is the ADR-028 D4-named projector — it maps a
  **completed SimState** (the LLM architect's output) into the same wire shape with
  ``provenance = llm_agent``.

Remaining stages are wired in P3, which extends the projector beyond intake.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime

from agents.architect import _canonical_case_id
from agents.router import route_reviewer
from schemas.sim_plan import AnalysisType, SimPlan
from schemas.sim_state import FaultClass
from schemas.workflow_state import (
    StageArtifacts,
    StageMetrics,
    StageProvenance,
    StageState,
    StageStatus,
    WorkflowStage,
)

__all__ = [
    "IntakeOutcome",
    "RouteOutcome",
    "analyze_intake",
    "decide_route",
    "intake_outcome_to_stage_state",
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
