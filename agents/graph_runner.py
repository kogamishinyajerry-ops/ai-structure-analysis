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
import tempfile

from langgraph.graph import END, START, StateGraph

from agents import architect, geometry, state_projection
from schemas.sim_plan import GeometrySpec, SimPlan
from schemas.sim_state import FaultClass, SimState
from schemas.workflow_state import StageState, StageStatus

logger = logging.getLogger(__name__)

__all__ = [
    "build_intake_geometry_graph",
    "build_intake_geometry_mesh_graph",
    "build_intake_graph",
    "run_geometry_via_graph",
    "run_intake_via_graph",
    "run_mesh_via_graph",
]

# A SimPlan.description sentinel: when the keyless architect node authors nothing, the
# deterministically-seeded plan persists with this marker, so the projector can honestly
# report planAuthoredBy="deterministic_seed". When an LLM key is present the architect node
# returns its OWN plan (last-write on the `plan` key), erasing the sentinel → "architect_llm".
# Runtime detection — no backend / env import needed in the agent layer (ADR-015).
_SEED_SENTINEL = "__adr029_p1_deterministic_seed__"


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


def build_intake_geometry_graph():
    """Compile a DEDICATED truncated ``StateGraph(SimState)``: ``START→architect→geometry→END``.

    Adds the architect AND geometry nodes by importing :mod:`agents.architect` /
    :mod:`agents.geometry` DIRECTLY — never :func:`agents.graph.compile_graph` (whose closure
    pulls backend ``app.well_harness.notion_sync``). Truncated BEFORE mesh/solver, so no ccx
    subprocess and no human_fallback/Notion node is reachable. This is the first graph with a
    cross-node EDGE (architect→geometry): the geometry node consumes the SimPlan the architect
    step left in the shared SimState.
    """
    workflow: StateGraph = StateGraph(SimState)
    workflow.add_node("architect", architect.run)
    workflow.add_node("geometry", geometry.run)
    workflow.add_edge(START, "architect")
    workflow.add_edge("architect", "geometry")
    workflow.add_edge("geometry", END)
    return workflow.compile()


def run_geometry_via_graph(
    user_request: str,
    *,
    run_id: str,
    existing_case_id: str | None = None,
    status: StageStatus = StageStatus.SUCCESS,
    progress: float = 1.0,
) -> StageState:
    """Drive GEOMETRY_VALIDATION through the real 2-node ``architect→geometry`` LangGraph
    runtime (ADR-029 P1 — the first cross-node graph data dependency).

    Only the NACA dummy regime (``geometryFamily=="naca_wing"`` AND ``not FREECAD_AVAILABLE``)
    crosses via the graph; every other family — and any host with a real FreeCAD kernel (which
    would yield real geometry this tier_0 path must not mislabel) — falls back to the existing
    :func:`agents.state_projection.geometry_stage_state` (P-geomrun/P-handoff path).

    Because the keyless architect node authors NO SimPlan and ``agents.geometry.run`` REQUIRES
    one, a DETERMINISTIC plan (rule-based intake case id + a fixed NACA geometry spec) is seeded
    into the graph state so the geometry node has something to consume; the seed carries a
    sentinel so the projection can honestly report whether the plan was seeded
    (``deterministic_seed``) or authored by the LLM architect node (``architect_llm``, key
    present — the genuine architect→geometry authorship dependency). On any runtime error the
    call degrades gracefully to the deterministic ``geometry_stage_state`` projection.
    """
    from tools.freecad_driver import FREECAD_AVAILABLE

    outcome = state_projection.analyze_geometry_plan(user_request)
    if outcome.metrics["geometryFamily"] != "naca_wing" or FREECAD_AVAILABLE:
        # not the dummy NACA regime → no graph crossing; use the existing projector
        return state_projection.geometry_stage_state(
            run_id,
            user_request,
            upstream_case_id=existing_case_id,
            status=status,
            progress=progress,
        )

    intake = state_projection.analyze_intake(user_request, existing_case_id=existing_case_id)
    seed_plan = SimPlan(
        case_id=intake.case_id,
        description=_SEED_SENTINEL,
        geometry=GeometrySpec(kind="naca", parameters={"profile": "NACA0012"}),
    )
    try:
        with tempfile.TemporaryDirectory(prefix="graph_geom_") as psd:
            seed = _seed_state(user_request, run_id, existing_case_id)
            seed["plan"] = seed_plan
            seed["project_state_dir"] = psd
            final_state = build_intake_geometry_graph().invoke(seed)
            final_plan = final_state.get("plan")
            plan_authored_by = (
                "deterministic_seed"
                if isinstance(final_plan, SimPlan) and final_plan.description == _SEED_SENTINEL
                else "architect_llm"
            )
            if not final_state.get("geometry_path"):
                raise RuntimeError("architect→geometry graph produced no geometry_path")
            return state_projection.graph_geometry_to_stage_state(
                final_state,
                user_request,
                run_id=run_id,
                plan_authored_by=plan_authored_by,
                status=status,
                progress=progress,
            )
    except Exception as exc:  # never hard-crash the live pipeline on a graph-runtime hiccup
        logger.warning(
            "geometry graph runtime failed (%s); falling back to deterministic geometry", exc
        )
        return state_projection.geometry_stage_state(
            run_id,
            user_request,
            upstream_case_id=existing_case_id,
            status=status,
            progress=progress,
        )


def build_intake_geometry_mesh_graph():
    """Compile a DEDICATED truncated ``StateGraph(SimState)``: architect→geometry→mesh.

    Extends :func:`build_intake_geometry_graph` with the mesh node, imported from
    :mod:`agents.mesh` DIRECTLY — never :func:`agents.graph.compile_graph` (whose closure pulls
    backend ``app.well_harness.notion_sync``). Truncated BEFORE the solver, so no ``ccx``
    subprocess and no ``human_fallback``/Notion node is reachable. This is the SECOND cross-node
    edge (geometry→mesh): the mesh node consumes the ``geometry_path`` the geometry node left in
    the shared SimState, then runs the real ``generate_mesh`` + ``check_mesh_quality`` code.
    """
    # Lazy import so the flag-off facade import closure does NOT eagerly pull mesh's heavier deps
    # (checkers.jacobian→meshio, tools.gmsh_driver probing) until a mesh crossing actually builds
    # this graph — preserving default-off inertness (Codex P2 R0 P3).
    from agents import mesh

    workflow: StateGraph = StateGraph(SimState)
    workflow.add_node("architect", architect.run)
    workflow.add_node("geometry", geometry.run)
    workflow.add_node("mesh", mesh.run)
    workflow.add_edge(START, "architect")
    workflow.add_edge("architect", "geometry")
    workflow.add_edge("geometry", "mesh")
    workflow.add_edge("mesh", END)
    return workflow.compile()


def run_mesh_via_graph(
    user_request: str,
    *,
    run_id: str,
    existing_case_id: str | None = None,
    status: StageStatus = StageStatus.SUCCESS,
    progress: float = 1.0,
) -> StageState:
    """Drive MESH_GENERATION through the real 3-node ``architect→geometry→mesh`` LangGraph
    runtime (ADR-029 P2 — the second cross-node graph data dependency).

    HONESTY ENVELOPE — the mesh stage may be projected as a graph-driven ``tier_0_dummy`` ONLY
    in the strict triple-dummy regime: ``geometryFamily=="naca_wing"`` AND
    ``not FREECAD_AVAILABLE`` AND ``not GMSH_AVAILABLE``. Rationale (verified, not assumed):

    * a real FreeCAD kernel would yield a real STEP, and a real gmsh kernel would mesh it into a
      REAL mesh whose ``check_mesh_quality`` numbers are genuine — which this ``tier_0`` projection
      must NEVER mislabel as dummy;
    * with no gmsh, ``generate_mesh`` writes a hardcoded 4-node/1-tet C3D4 fallback ``.inp``
      (``generation_mode="fallback"``), over which ``check_mesh_quality`` IS a real numpy
      measurement — but of DUMMY geometry, so the numbers are tautological, never validated.

    Outside the triple-dummy regime (or on any graph-runtime error) this RAISES
    :class:`NotImplementedError` — the established facade signal for "not honestly graph-driven
    here": the caller (mock_pipeline) falls back to the scripted mesh spec, so a real mesh is
    never mislabeled tier_0 and a runtime hiccup never hard-crashes the demo path.

    The mesh node REQUIRES a ``SimPlan`` and a ``geometry_path``; the keyless architect node
    authors no plan, so a DETERMINISTIC NACA plan is seeded (carrying ``_SEED_SENTINEL``) for the
    graph to consume. ``mesh_path`` is the wiring fact (present ⇔ the mesh node ran AND quality
    passed); its absence raises (refusing to claim ``toolRan=True`` without it).
    """
    from tools.freecad_driver import FREECAD_AVAILABLE
    from tools.gmsh_driver import GMSH_AVAILABLE

    outcome = state_projection.analyze_geometry_plan(user_request)
    if outcome.metrics["geometryFamily"] != "naca_wing" or FREECAD_AVAILABLE or GMSH_AVAILABLE:
        # Not the triple-dummy regime → no honest tier_0 mesh crossing. Signal the caller to use
        # the scripted mesh spec (never mislabel a real gmsh mesh / real-kernel geometry tier_0).
        raise NotImplementedError(
            "run_mesh_via_graph: mesh is graph-driven only in the triple-dummy regime "
            "(naca_wing + no FreeCAD + no gmsh); refusing to mislabel a real mesh as tier_0."
        )

    intake = state_projection.analyze_intake(user_request, existing_case_id=existing_case_id)
    seed_plan = SimPlan(
        case_id=intake.case_id,
        description=_SEED_SENTINEL,
        geometry=GeometrySpec(kind="naca", parameters={"profile": "NACA0012"}),
    )
    try:
        with tempfile.TemporaryDirectory(prefix="graph_mesh_") as psd:
            seed = _seed_state(user_request, run_id, existing_case_id)
            seed["plan"] = seed_plan
            seed["project_state_dir"] = psd
            final_state = build_intake_geometry_mesh_graph().invoke(seed)
            final_plan = final_state.get("plan")
            plan_authored_by = (
                "deterministic_seed"
                if isinstance(final_plan, SimPlan) and final_plan.description == _SEED_SENTINEL
                else "architect_llm"
            )
            if not final_state.get("mesh_path"):
                raise RuntimeError(
                    "architect→geometry→mesh graph produced no mesh_path "
                    "(mesh node faulted or quality failed)"
                )
            return state_projection.graph_mesh_to_stage_state(
                final_state,
                user_request,
                run_id=run_id,
                plan_authored_by=plan_authored_by,
                status=status,
                progress=progress,
            )
    except Exception as exc:  # never hard-crash the live pipeline on a graph-runtime hiccup
        logger.warning("mesh graph runtime failed (%s); falling back to scripted mesh", exc)
        raise NotImplementedError(
            f"run_mesh_via_graph: graph runtime error ({exc}); fall back to scripted mesh."
        ) from exc
