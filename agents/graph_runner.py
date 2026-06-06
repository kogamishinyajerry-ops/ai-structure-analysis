"""LangGraph compiled-graph runtime adapter (ADR-029 P0 — the graph-wiring north star).

Every ADR-028 slice so far (P1..P-handoff) drove a stage by calling an agent node's
``run()`` DIRECTLY through the facade; none exercised the actual LangGraph **compiled-graph
runtime**. This module closes that gap minimally and safely: it builds a *dedicated*
truncated ``StateGraph(SimState)`` containing ONLY the architect node
(``START -> architect -> END``), compiles it, and ``.invoke()``s it to drive the live
PROJECT_INTAKE stage — the first time the orphaned graph machinery touches the runtime.

Why a dedicated truncated graph instead of ``agents.graph.compile_graph()`` (verified, not
assumed):

* Importing ``agents.graph`` transitively pulls ``app.well_harness.notion_sync`` into the
  import closure (via ``agents.human_fallback``), and running the FULL graph would fire a
  real, **non-revertible** Notion writeback + ``interrupt()`` on the fault-recovery path.
  Importing ``agents.architect`` alone pulls none of that.
* ``ccx`` IS present on this host, so the full graph's solver node would launch a real
  subprocess (faulting on a dummy mesh). Truncating BEFORE geometry/mesh/solver removes
  that by construction — there is no downstream node to reach.

Honesty rule (the deliverable): ``agents.architect`` authors a ``SimPlan`` ONLY when an LLM
key is present; keyless it returns ``fault_class=unknown`` with no plan. So "the graph node
EXECUTED" and "the graph node AUTHORED content" are DISTINCT facts — the projection
(:func:`agents.state_projection.graph_intake_to_stage_state`) surfaces them separately and
never conflates them, and the stage provenance / N-13 count are unchanged by the runtime swap.
"""

from __future__ import annotations

import logging

from langgraph.graph import END, START, StateGraph

from agents import architect, state_projection
from schemas.sim_state import FaultClass, SimState
from schemas.workflow_state import StageState, StageStatus

logger = logging.getLogger(__name__)

__all__ = ["build_intake_graph", "run_intake_via_graph"]


def build_intake_graph():
    """Compile a DEDICATED truncated ``StateGraph(SimState)``: ``START -> architect -> END``.

    Adds the architect node by importing :mod:`agents.architect` DIRECTLY — it must never
    import :func:`agents.graph.compile_graph`, whose import closure pulls backend code
    (``app.well_harness.notion_sync``) into the agent layer. No checkpointer: ``interrupt`` /
    ``human_fallback`` is structurally unreachable in a one-node graph.
    """
    workflow: StateGraph = StateGraph(SimState)
    workflow.add_node("architect", architect.run)
    workflow.add_edge(START, "architect")
    workflow.add_edge("architect", END)
    return workflow.compile()


def _seed_state(user_request: str, run_id: str, existing_case_id: str | None) -> dict:
    """A hermetic initial SimState. The reducer-managed fields (``history`` /
    ``retry_budgets``) MUST be seeded with their identity values (``[]`` / ``{}``): the
    keyless architect returns a ``history`` delta, so the append reducer fires and would
    crash on a ``None`` seed. ``project_state_dir`` is unused by the architect node (only
    geometry/mesh/solver write files), so no artifact is produced on disk."""
    return {
        "user_request": user_request,
        "case_id": existing_case_id or "",
        "run_id": run_id,
        "project_state_dir": ".",
        "artifacts": [],
        "geometry_path": None,
        "mesh_path": None,
        "frd_path": None,
        "solve_path": None,
        "solve_metadata": {},
        "verdict": None,
        "fault_class": FaultClass.NONE,
        "retry_budgets": {},
        "history": [],
        "reports": None,
        "execution_mode": {"geometry_source": "dummy", "replay": True},
    }


def run_intake_via_graph(
    user_request: str,
    *,
    run_id: str,
    existing_case_id: str | None = None,
    status: StageStatus = StageStatus.SUCCESS,
    progress: float = 1.0,
) -> StageState:
    """Drive PROJECT_INTAKE through the real LangGraph compiled-graph runtime.

    Compiles the truncated architect-only graph, ``.invoke()``s it on a hermetic seed
    SimState, and projects the accumulated final state via
    :func:`agents.state_projection.graph_intake_to_stage_state` (which branches on
    plan-presence and discloses whether the node authored content). On any runtime error
    the call degrades gracefully to the proven deterministic intake projection (mirroring
    the facade's ``_try_intake_llm`` catch-and-fallback), so a graph-runtime bug never
    hard-crashes the demo path.
    """
    seed = _seed_state(user_request, run_id, existing_case_id)
    try:
        final_state = build_intake_graph().invoke(seed)
    except Exception as exc:  # never hard-crash the live pipeline on a graph-runtime hiccup
        logger.warning(
            "intake graph runtime failed (%s); falling back to deterministic intake", exc
        )
        outcome = state_projection.analyze_intake(user_request, existing_case_id=existing_case_id)
        return state_projection.intake_outcome_to_stage_state(
            run_id, outcome, status=status, progress=progress
        )
    return state_projection.graph_intake_to_stage_state(
        final_state,
        user_request,
        run_id=run_id,
        existing_case_id=existing_case_id,
        status=status,
        progress=progress,
    )
