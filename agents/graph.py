from __future__ import annotations

from typing import Any, cast

from langgraph.graph import END, START, StateGraph

from agents import architect, geometry, human_fallback, mesh, reviewer, solver, viz
from agents.router import route_reviewer
from schemas.sim_state import SimState


def build_graph() -> StateGraph:
    """Construct the LangGraph workflow definition for the AI-FEA pipeline."""
    workflow = StateGraph(SimState)

    # 1. Add nodes
    workflow.add_node("architect", cast(Any, architect.run))
    workflow.add_node("geometry", cast(Any, geometry.run))
    workflow.add_node("mesh", cast(Any, mesh.run))
    workflow.add_node("solver", cast(Any, solver.run))
    workflow.add_node("reviewer", cast(Any, reviewer.run))
    workflow.add_node("viz", cast(Any, viz.run))
    workflow.add_node("human_fallback", cast(Any, human_fallback.run))

    # 2. Add structural edges
    workflow.add_edge(START, "architect")
    workflow.add_edge("architect", "geometry")
    workflow.add_edge("geometry", "mesh")
    workflow.add_edge("mesh", "solver")
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
            "solver": "solver",
            "architect": "architect",
            "human_fallback": "human_fallback",
        },
    )

    return workflow


def compile_graph(checkpointer=None):
    """Compile the workflow, optionally with a persistent checkpointer."""
    workflow = build_graph()
    if checkpointer is None:
        return workflow.compile()
    return workflow.compile(checkpointer=checkpointer)
