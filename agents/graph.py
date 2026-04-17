"""LangGraph orchestration graph for the AI-FEA pipeline.

Wires together: Architect → Geometry → Mesh → Solver → Reviewer → Viz
with conditional edges for re-runs when the Reviewer Agent rejects.

This module is a stub (AI-FEA-P0-01).  Logic will be filled in P0-02.
"""

from __future__ import annotations


def build_graph():
    """Construct and return a compiled LangGraph StateGraph."""
    raise NotImplementedError("LangGraph orchestration not yet implemented — see AI-FEA-P0-02")
