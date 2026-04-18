"""Geometry Agent — generates or imports CAD geometry via FreeCAD.

Responsibility:
  - Accept a SimPlan with geometry spec.
  - Call ``tools.freecad_driver`` to produce STEP/BREP.
  - Map artifacts to SimState.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from checkers.geometry_checker import check_geometry
from schemas.sim_state import FaultClass, SimState
from tools.freecad_driver import generate_geometry

logger = logging.getLogger(__name__)


def run(state: SimState) -> dict[str, Any]:
    """Geometry agent entrypoint (LangGraph node signature)."""
    logger.info("Geometry Agent invoked.")

    plan = state.get("plan")
    if not plan:
        raise ValueError("SimState is missing a SimPlan.")

    project_dir = Path(state.get("project_state_dir", "."))
    geom_dir = project_dir / "geometry"
    geom_dir.mkdir(parents=True, exist_ok=True)

    # We only support naca natively for P0-05 so far
    geom_spec = plan.geometry
    if geom_spec.kind.lower() != "naca":
        raise NotImplementedError(
            f"Geometry kind '{geom_spec.kind}' is not yet supported in freecad_driver."
        )

    # Generate geometry
    step_path = generate_geometry(geom_spec.parameters, geom_dir)
    topo_map_path = geom_dir / "topo_map.json"
    meta_path = geom_dir / "geometry_meta.json"
    geometry_report = check_geometry(step_path)

    # Capture artifacts
    artifacts = state.get("artifacts", []).copy()
    artifacts.append(str(step_path))
    artifacts.append(str(topo_map_path))
    if meta_path.exists():
        artifacts.append(str(meta_path))

    if not geometry_report["valid"]:
        history = state.get("history", []).copy()
        history.append(
            {
                "node": "geometry",
                "fault_class": FaultClass.GEOMETRY_INVALID.value,
                "findings": geometry_report["findings"],
            }
        )
        return {
            "artifacts": artifacts,
            "geometry_path": str(step_path),
            "fault_class": FaultClass.GEOMETRY_INVALID,
            "history": history,
            "verdict": "re-run",
        }

    # Return delta update for SimState
    return {
        "artifacts": artifacts,
        "geometry_path": str(step_path),
        "fault_class": FaultClass.NONE,
    }
