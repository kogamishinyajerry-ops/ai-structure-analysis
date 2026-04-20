from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from agents import architect, geometry, human_fallback, lint_deck, mesh, reviewer, solver, viz
from agents.router import route_architect, route_lint, route_reviewer
from schemas.sim_state import SimState


def build_graph() -> StateGraph:
    """Construct and return a compiled LangGraph StateGraph."""
    workflow = StateGraph(SimState)

    # 1. Add nodes
    workflow.add_node("architect", architect.run)
    workflow.add_node("geometry", geometry.run)
    workflow.add_node("mesh", mesh.run)
    workflow.add_node("solver", solver.run)
    workflow.add_node("lint_deck", lint_deck.run)
    workflow.add_node("reviewer", reviewer.run)
    workflow.add_node("viz", viz.run)
    workflow.add_node("human_fallback", human_fallback.run)

    # 2. Add structural edges
    workflow.add_edge(START, "architect")
    
    # 3. Add conditional routing for the Architect
    workflow.add_conditional_edges(
        "architect",
        route_architect,
        {
            "geometry": "geometry",
            "lint_deck": "lint_deck",
            "human_fallback": "human_fallback",
        },
    )

    workflow.add_edge("geometry", "mesh")
    workflow.add_edge("mesh", "lint_deck")

    # 3b. Lint gate: pass → solver, fail → reviewer (short-circuit)
    workflow.add_conditional_edges(
        "lint_deck",
        route_lint,
        {
            "solver": "solver",
            "reviewer": "reviewer",
        },
    )

    workflow.add_edge("solver", "reviewer")
    workflow.add_edge("viz", END)

    workflow.add_edge("human_fallback", END)

    # 3. Add conditional routing for the Reviewer
    workflow.add_conditional_edges(
        "reviewer",
        route_reviewer,
        {
            "viz": "viz",
            "geometry": "geometry",
            "mesh": "mesh",
            "lint_deck": "lint_deck",
            "solver": "solver",
            "architect": "architect",
            "human_fallback": "human_fallback",
        },
    )

    return workflow
