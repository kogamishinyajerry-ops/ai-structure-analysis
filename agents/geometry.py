"""Geometry Agent — generates or imports CAD geometry via FreeCAD.

Responsibilities:
  - Accept a SimPlan with geometry spec.
  - Call ``tools.freecad_driver`` to produce STEP/BREP.
  - Run ``checkers.geometry_checker`` before passing to Mesh Agent.

This module is a stub (AI-FEA-P0-01).  Logic will be filled in P0-05.
"""

from __future__ import annotations

from typing import Any


def run(state: dict[str, Any]) -> dict[str, Any]:
    """Geometry agent entrypoint (LangGraph node signature)."""
    raise NotImplementedError("Geometry agent not yet implemented — see AI-FEA-P0-05")
