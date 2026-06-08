"""Workbench → agent-layer facade (ADR-015 choke point; built at last per ADR-028 D4).

This is the **one** file under ``backend/app/workbench/`` permitted to import
``agents.*`` — enforced by ``tests/test_workbench_facade_discipline.py``. It does
**not** import ``schemas.sim_state`` (ADR-015 rule 3): the ``SimState`` → ``StageState``
projection lives in the agent layer (:mod:`agents.state_projection`), so the facade
only ever returns an already-projected :class:`~schemas.workflow_state.StageState`.

ADR-028 P1 scope: :func:`run_node` drives the ``PROJECT_INTAKE`` stage through a real
agent node — **deterministic** ("rule-based agent") by default, with an explicit,
**key-gated LLM opt-in** that falls back to deterministic on any failure (so CI stays
hermetic). The remaining stages are wired in P3 and raise ``NotImplementedError`` until
then — the facade never silently fabricates agent output for an un-wired stage.
"""

from __future__ import annotations

import logging

from agents import architect, graph_runner, state_projection
from schemas.workflow_state import StageState, StageStatus, WorkflowStage

logger = logging.getLogger(__name__)

__all__ = ["decide_recovery", "decide_route", "run_node", "run_node_via_graph"]


def decide_route(
    *,
    verdict: str,
    fault_class: str = "none",
    retry_budgets: dict[str, int] | None = None,
    verdict_source: str = "本阶段评审状态",
) -> state_projection.RouteOutcome:
    """Run the real router node (``agents.router.route_reviewer``) to choose which
    agent handles the next step (ADR-028 P3).

    ``fault_class`` is a plain wire string (e.g. ``"none"``, ``"mesh_jacobian"``);
    the ``FaultClass`` enum lives entirely in the agent layer
    (:func:`agents.state_projection.decide_route`), so this facade stays free of any
    ``schemas.sim_state`` import (ADR-015 rule 3). Returns the agent layer's
    :class:`~agents.state_projection.RouteOutcome`, whose ``provenance`` is
    ``deterministic_agent`` — the routing decision is genuine orchestration logic.
    """
    return state_projection.decide_route(
        verdict=verdict,
        fault_class=fault_class,
        retry_budgets=retry_budgets,
        verdict_source=verdict_source,
    )


def decide_recovery(
    *,
    fault_class: str,
    retry_budgets: dict[str, int] | None = None,
) -> state_projection.RecoveryOutcome:
    """Derive a two-agent fault-recovery decision for an injected failure (ADR-028
    P-recover): the real reviewer node classifies the fault into a verdict, then the
    real router picks the recovery node.

    ``fault_class`` is a plain wire string (the ``FaultClass`` conversion lives in
    :func:`agents.state_projection.decide_recovery`), so the facade imports no
    ``schemas.sim_state`` (ADR-015 rule 3). This does NOT flip the failing stage's
    provenance — the failure is scripted demo input, so the stage stays
    ``scripted_demo``; the recovery is surfaced via ``metrics.recovery`` with its own
    ``agentDriven`` / ``faultInjected`` flags (it must never increment the N/13 count).
    """
    return state_projection.decide_recovery(fault_class=fault_class, retry_budgets=retry_budgets)


def _try_intake_llm(user_request: str, existing_case_id: str | None) -> dict | None:
    """Run the real LLM architect node; return a completed ``sim_state`` dict
    (``{"plan": SimPlan, "user_request": str}``) or ``None`` on any non-result
    (missing key, parse failure, fault) so the caller falls back to the
    deterministic agent. Key-gating is handled inside ``agents.llm`` (no key →
    ``None`` plan)."""
    result = architect.run({"user_request": user_request, "case_id": existing_case_id})
    plan = result.get("plan")
    if plan is None:
        return None
    return {"plan": plan, "user_request": user_request}


def run_node(
    stage: WorkflowStage,
    *,
    run_id: str,
    user_request: str | None = None,
    existing_case_id: str | None = None,
    status: StageStatus = StageStatus.SUCCESS,
    progress: float = 1.0,
    allow_llm: bool = False,
) -> StageState:
    """Execute ONE workbench-agent stage and return its already-projected wire
    :class:`StageState` (ADR-028 D4).

    Wired stages: ``PROJECT_INTAKE`` (rule-based intake; ``allow_llm`` opts into the
    real LLM architect, key-gated, falling back to deterministic on any failure); the
    three setup-planner stages (``MATERIAL_ASSIGNMENT`` / ``BOUNDARY_CONDITIONS`` /
    ``LOAD_CASES``) via the deterministic :func:`state_projection.analyze_setup`; and
    ``GEOMETRY_VALIDATION`` via :func:`state_projection.geometry_stage_state` — which
    routes a NACA/wing request in the dummy regime to the REAL ``agents.geometry.run``
    node (P-geomrun: a ``tier_0_dummy`` wiring proof — real node executed, NO validation,
    NO measurement surfaced) and every other family to the deterministic geometry
    **planner** (no CAD kernel). Every other (tool/artifact-bound) stage raises
    ``NotImplementedError`` — the facade never silently fabricates agent output.
    """
    if stage in state_projection.SETUP_STAGES:
        outcome = state_projection.analyze_setup(user_request or "")
        return state_projection.setup_outcome_to_stage_state(
            run_id, stage, outcome, status=status, progress=progress
        )

    if stage is WorkflowStage.GEOMETRY_VALIDATION:
        # P-handoff: forward the upstream PROJECT_INTAKE case id so the geometry node consumes
        # intake's decision (the first real inter-agent data dependency) instead of fabricating
        # its own case number. Only the crossing (dummy-NACA) path uses it.
        return state_projection.geometry_stage_state(
            run_id,
            user_request or "",
            upstream_case_id=existing_case_id,
            status=status,
            progress=progress,
        )

    if stage is not WorkflowStage.PROJECT_INTAKE:
        raise NotImplementedError(
            f"agent_facade.run_node: stage {stage.value!r} is not wired yet "
            "(ADR-028 covers project_intake + the 3 setup stages; tool/artifact-bound "
            "stages land later)."
        )

    req = (user_request or "").strip()

    if allow_llm and req:
        try:
            sim_state = _try_intake_llm(req, existing_case_id)
        except Exception as exc:  # never hard-crash the demo path on an LLM hiccup
            logger.warning("intake LLM node failed (%s); falling back to deterministic", exc)
            sim_state = None
        if sim_state is not None:
            return state_projection.sim_state_to_stage_state(
                sim_state, run_id=run_id, status=status, progress=progress
            )

    outcome = state_projection.analyze_intake(req, existing_case_id=existing_case_id)
    return state_projection.intake_outcome_to_stage_state(
        run_id, outcome, status=status, progress=progress
    )


def run_node_via_graph(
    stage: WorkflowStage,
    *,
    run_id: str,
    user_request: str | None = None,
    existing_case_id: str | None = None,
    status: StageStatus = StageStatus.SUCCESS,
    progress: float = 1.0,
) -> StageState:
    """Drive a stage through the REAL LangGraph compiled-graph runtime (ADR-029 P0).

    The facade choke point for the graph-wiring north star: it delegates to
    :mod:`agents.graph_runner`, which compiles a dedicated truncated graph and ``.invoke()``s
    it — proving the orphaned ``agents/graph.py`` machinery can drive live stages. The facade
    imports only ``agents.graph_runner`` (never ``schemas.sim_state``; the ``SimState`` dict is
    built and invoked entirely inside the runner), so ADR-015 rule 3 holds. Wired:
    ``PROJECT_INTAKE`` (P0, truncated architect-only graph), ``GEOMETRY_VALIDATION`` (P1,
    truncated architect→geometry graph — the first cross-node graph data dependency), and
    ``MESH_GENERATION`` (P2, truncated architect→geometry→mesh graph — the second cross-node
    dependency, ``tier_0_dummy`` with the ``dummyFidelityInputs`` guard). The solver stage
    still raises ``NotImplementedError`` — it needs the ccx-subprocess isolation gate of a
    later ADR-029 phase.
    """
    if stage is WorkflowStage.PROJECT_INTAKE:
        return graph_runner.run_intake_via_graph(
            user_request or "",
            run_id=run_id,
            existing_case_id=existing_case_id,
            status=status,
            progress=progress,
        )
    if stage is WorkflowStage.GEOMETRY_VALIDATION:
        return graph_runner.run_geometry_via_graph(
            user_request or "",
            run_id=run_id,
            existing_case_id=existing_case_id,
            status=status,
            progress=progress,
        )
    if stage is WorkflowStage.MESH_GENERATION:
        # ADR-029 P2: the architect→geometry→mesh graph drives MESH_GENERATION as tier_0_dummy.
        # run_mesh_via_graph raises NotImplementedError outside the triple-dummy regime (real
        # FreeCAD/gmsh present, or non-NACA) so the caller falls back to the scripted mesh spec
        # rather than mislabel a real mesh tier_0.
        return graph_runner.run_mesh_via_graph(
            user_request or "",
            run_id=run_id,
            existing_case_id=existing_case_id,
            status=status,
            progress=progress,
        )
    raise NotImplementedError(
        f"agent_facade.run_node_via_graph: stage {stage.value!r} is not graph-wired yet "
        "(ADR-029 P0/P1/P2 wire project_intake + geometry_validation + mesh_generation; the "
        "solver stage lands in a later phase behind the ccx-subprocess isolation gate)."
    )
