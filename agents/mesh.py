"""Mesh Agent — generates FE mesh via Gmsh with adaptive refinement.

Responsibilities:
  - Receive geometry (STEP/BREP) from Geometry Agent.
  - Call ``tools.gmsh_driver`` to produce mesh.
  - Run ``checkers.jacobian`` quality checks.
  - Emit mesh path and quality metrics into state.

This module is a stub (AI-FEA-P0-01).  Logic will be filled in P0-06.
"""

from __future__ import annotations

from typing import Any


def run(state: dict[str, Any]) -> dict[str, Any]:
    """Mesh agent entrypoint (LangGraph node signature)."""
    raise NotImplementedError("Mesh agent not yet implemented — see AI-FEA-P0-06")
