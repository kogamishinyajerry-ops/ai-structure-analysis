from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from checkers.jacobian import check_mesh_quality
from schemas.sim_state import FaultClass, SimState
from tools.gmsh_driver import generate_mesh

logger = logging.getLogger(__name__)


def run(state: SimState) -> dict[str, Any]:
    """Mesh agent entrypoint (LangGraph node signature)."""
    logger.info("Mesh Agent invoked.")
    
    plan = state.get("plan")
    if not plan:
        raise ValueError("SimState is missing a SimPlan.")
        
    project_dir = Path(state.get("project_state_dir", "."))
    mesh_dir = project_dir / "mesh"
    mesh_dir.mkdir(parents=True, exist_ok=True)
    
    # Locate geometry step file
    artifacts = state.get("artifacts", [])
    step_path_str = next((p for p in artifacts if p.endswith(".step")), None)
    if not step_path_str:
        logger.error("No .step artifact found. Mesh agent cannot proceed.")
        return {"fault_class": FaultClass.GEOMETRY_INVALID}
        
    step_path = Path(step_path_str)
    
    # Read mesh defaults
    mesh_params = plan.mesh.model_dump()
    
    # Calculate adaptive refinement from retry_budgets
    # The default size will be refined by a factor (e.g. 1.0 -> 0.5 -> 0.25) 
    # for each mesh_jacobian failure retry.
    budget = state.get("retry_budgets", {}).get("mesh", 0)
    
    # E.g., budget 0 -> multiplier 1.0 (Coarse)
    # budget 1 -> multiplier 0.5 (Medium)
    # budget 2 -> multiplier 0.25 (Fine)
    refinement_multiplier = 1.0 / (2 ** budget)
    mesh_params["refinement_multiplier"] = refinement_multiplier
    
    try:
        mesh_path = generate_mesh(step_path, mesh_params, mesh_dir)
    except Exception as e:
        logger.error(f"Gmsh driver failed unexpectedly: {e}")
        return {"fault_class": FaultClass.UNKNOWN}
        
    # Run Jacobian Checker
    logger.info(f"Checking quality of {mesh_path}.")
    quality_report = check_mesh_quality(mesh_path)
    
    if not quality_report["passed"]:
        logger.warning(f"Mesh Quality Check failed: {quality_report['findings']}")
        return {
            "fault_class": FaultClass.MESH_JACOBIAN,
            "retry_budgets": {"mesh": 1},
            "history": [{
                "node": "mesh",
                "fault": FaultClass.MESH_JACOBIAN.value,
                "msg": f"Quality failed at refinement {refinement_multiplier}"
            }]
        }
    
    # Success path
    logger.info("Mesh Quality Check passed.")
    new_artifacts = artifacts.copy()
    new_artifacts.append(str(mesh_path))
    
    return {
        "fault_class": FaultClass.NONE,
        "artifacts": new_artifacts,
        "mesh_path": str(mesh_path)
    }
