from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from checkers.jacobian import check_mesh_quality
from schemas.sim_state import FaultClass, SimState
from tools.gmsh_driver import generate_mesh, normalize_mesh_level

logger = logging.getLogger(__name__)

MESH_LEVEL_ORDER = ["coarse", "medium", "fine", "very_fine"]


def _escalate_mesh_level(base_level: str, retries: int) -> str:
    """Tighten the mesh preset after each retry, capped at very_fine."""
    normalized = normalize_mesh_level(base_level)
    base_index = MESH_LEVEL_ORDER.index(normalized)
    return MESH_LEVEL_ORDER[min(base_index + max(retries, 0), len(MESH_LEVEL_ORDER) - 1)]


def _load_json(path: Path) -> dict[str, Any]:
    """Load a JSON sidecar if it exists, otherwise return an empty mapping."""
    if not path.exists():
        return {}

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("JSON sidecar at %s is invalid; continuing without it.", path)
        return {}


def run(state: SimState) -> dict[str, Any]:
    """Mesh agent entrypoint (LangGraph node signature)."""
    logger.info("Mesh Agent invoked.")

    plan = state.get("plan")
    if not plan:
        raise ValueError("SimState is missing a SimPlan.")

    project_dir = Path(state.get("project_state_dir", "."))
    mesh_dir = project_dir / "mesh"
    mesh_dir.mkdir(parents=True, exist_ok=True)

    artifacts = state.get("artifacts", [])
    step_path_str = next((path for path in artifacts if path.endswith(".step")), None) or state.get(
        "geometry_path"
    )
    if not step_path_str:
        logger.error("No .step artifact found. Mesh agent cannot proceed.")
        return {"fault_class": FaultClass.GEOMETRY_INVALID}

    step_path = Path(step_path_str)
    mesh_params = plan.mesh.model_dump()
    retry_budget = state.get("retry_budgets", {}).get("mesh", 0)
    mesh_params["mesh_level"] = _escalate_mesh_level(
        str(mesh_params.get("mesh_level", "medium")), retry_budget
    )

    try:
        mesh_path = generate_mesh(step_path, mesh_params, mesh_dir)
    except Exception as exc:
        logger.error("Gmsh driver failed unexpectedly: %s", exc)
        return {"fault_class": FaultClass.UNKNOWN}

    logger.info("Checking quality of %s.", mesh_path)
    quality_report = check_mesh_quality(
        mesh_path,
        thresholds={
            "min_scaled_jacobian": plan.mesh.min_scaled_jacobian,
            "max_aspect_ratio": plan.mesh.max_aspect_ratio,
        },
    )
    mesh_meta_path = mesh_dir / "mesh_meta.json"
    mesh_meta = _load_json(mesh_meta_path)

    if not quality_report["ok"]:
        logger.warning("Mesh Quality Check failed: %s", quality_report["findings"])
        fault_class = (
            FaultClass.MESH_JACOBIAN
            if quality_report["bad_element_ids"]
            else FaultClass.MESH_RESOLUTION
        )
        return {
            "fault_class": fault_class,
            "retry_budgets": {"mesh": 1},
            "history": [
                {
                    "node": "mesh",
                    "fault_class": fault_class.value,
                    "mesh_level": mesh_params["mesh_level"],
                    "bad_element_ids": quality_report["bad_element_ids"][:10],
                    "findings": quality_report["findings"],
                    "thin_wall_detected": mesh_meta.get("field_config", {}).get(
                        "thin_wall_detected"
                    ),
                }
            ],
            "verdict": "re-run",
        }

    logger.info("Mesh Quality Check passed.")
    new_artifacts = artifacts.copy()
    new_artifacts.append(str(mesh_path))
    if mesh_meta_path.exists():
        new_artifacts.append(str(mesh_meta_path))

    return {
        "fault_class": FaultClass.NONE,
        "artifacts": new_artifacts,
        "mesh_path": str(mesh_path),
    }
