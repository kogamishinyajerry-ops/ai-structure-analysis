"""Solver Agent — renders the deck and runs the CalculiX solve."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

import jinja2

from schemas.sim_state import FaultClass, SimState
from tools.calculix_driver import run_solve
from tools.inp_linter import lint_inp

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


def _render_inp_deck(plan: Any, mesh_inp_path: str, output_dir: Path) -> Path:
    """Render a CalculiX ``solve.inp`` deck from SimPlan + Jinja2 template."""
    template_name = "linear_static.inp.j2"
    template_path = TEMPLATE_DIR / template_name
    if not template_path.exists():
        raise FileNotFoundError(f"Solver template not found: {template_path}")

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATE_DIR), encoding="utf-8"),
        undefined=jinja2.StrictUndefined,
    )
    template = env.get_template(template_name)

    material = plan.material
    load_magnitude = 0.0
    load_node_set = "Nall"
    for load in plan.loads:
        if load.kind == "concentrated_force":
            load_magnitude = load.parameters.get("magnitude", 0.0)
            load_node_set = load.parameters.get("node_set", "Nall")
            break

    fixed_node_set = "Nfix"
    for bc in plan.boundary_conditions:
        if bc.kind == "fixed":
            fixed_node_set = bc.parameters.get("node_set", "Nfix")
            break

    rendered = template.render(
        mesh_include=mesh_inp_path,
        material_name=material.name,
        youngs_modulus=material.youngs_modulus_pa,
        poissons_ratio=material.poissons_ratio,
        load_magnitude=load_magnitude,
        load_node_set=load_node_set,
        fixed_node_set=fixed_node_set,
    )

    deck_path = output_dir / "solve.inp"
    deck_path.write_text(rendered, encoding="utf-8")
    logger.info("Rendered solver deck -> %s", deck_path)
    return deck_path


def run(state: SimState) -> dict[str, Any]:
    """Solver agent entrypoint (LangGraph node signature)."""
    logger.info("Solver Agent invoked.")

    plan = state.get("plan")
    if not plan:
        raise ValueError("SimState is missing a SimPlan.")

    project_dir = Path(state.get("project_state_dir", "."))
    solver_dir = project_dir / "solver"
    solver_dir.mkdir(parents=True, exist_ok=True)

    artifacts = state.get("artifacts", [])
    mesh_inp = state.get("mesh_path") or next(
        (path for path in artifacts if path.endswith(".inp")), None
    )
    if not mesh_inp:
        logger.error("No .inp mesh artifact found for solver.")
        return {"fault_class": FaultClass.UNKNOWN}

    mesh_src = Path(mesh_inp)
    mesh_dst = solver_dir / mesh_src.name
    if mesh_src.exists() and mesh_src != mesh_dst:
        shutil.copy2(mesh_src, mesh_dst)

    try:
        deck_path = _render_inp_deck(plan, mesh_dst.name, solver_dir)
    except Exception as exc:
        logger.error("Template rendering failed: %s", exc)
        return {
            "fault_class": FaultClass.SOLVER_SYNTAX,
            "retry_budgets": {"solver": 1},
            "history": [
                {
                    "node": "solver",
                    "fault_class": FaultClass.SOLVER_SYNTAX.value,
                    "msg": str(exc),
                }
            ],
            "verdict": "re-run",
        }

    lint_report = lint_inp(deck_path)
    if not lint_report.ok:
        error_codes = [f.code for f in lint_report.errors]
        first_error = lint_report.errors[0]
        msg = (
            f"Gate-Solve lint rejected deck before ccx: {len(lint_report.errors)} "
            f"error(s); first: {first_error.code} — {first_error.message}"
        )
        logger.warning("Gate-Solve lint rejected deck: %s", error_codes)
        return {
            "fault_class": FaultClass.SOLVER_SYNTAX,
            "retry_budgets": {"solver": 1},
            "history": [
                {
                    "node": "solver",
                    "fault_class": FaultClass.SOLVER_SYNTAX.value,
                    "msg": msg,
                    "lint_codes": error_codes,
                    "lint_findings": [f.to_dict() for f in lint_report.errors],
                    "stage": "gate_solve_lint",
                }
            ],
            "verdict": "re-run",
        }

    try:
        result = run_solve(deck_path, solver_dir)
    except (FileNotFoundError, RuntimeError) as exc:
        logger.warning("CalculiX environment check failed: %s", exc)
        return {
            "fault_class": FaultClass.UNKNOWN,
            "history": [
                {
                    "node": "solver",
                    "fault_class": FaultClass.UNKNOWN.value,
                    "msg": str(exc),
                }
            ],
        }

    if not result["converged"]:
        fault_class = result["fault_class"]
        logger.warning("CalculiX solve failed as %s (rc=%s).", fault_class, result["returncode"])
        return {
            "fault_class": fault_class,
            "retry_budgets": {"solver": 1},
            "history": [
                {
                    "node": "solver",
                    "fault_class": fault_class.value,
                    "msg": result["failure_reason"],
                    "ccx_version": result["ccx_version"],
                    "returncode": result["returncode"],
                    "wall_time_s": result["wall_time_s"],
                }
            ],
            "verdict": "re-run",
        }

    logger.info("CalculiX solve converged in %.1fs.", result["wall_time_s"])
    new_artifacts = artifacts.copy()
    new_artifacts.append(str(deck_path))
    for key in ("frd_path", "dat_path", "sta_path"):
        if result.get(key):
            new_artifacts.append(result[key])

    return {
        "fault_class": FaultClass.NONE,
        "frd_path": result["frd_path"],
        "artifacts": new_artifacts,
        "solve_path": str(deck_path),
        "solve_metadata": {
            "wall_time_s": result["wall_time_s"],
            "ccx_version": result["ccx_version"],
        },
    }
