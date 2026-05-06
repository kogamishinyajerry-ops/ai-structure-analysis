"""Solver Agent — renders the deck and runs the CalculiX solve."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import jinja2

from aeron.protocols import SolveOptions, SolveOutcome, SolveStatusCode
from schemas.sim_state import FaultClass, SimState
from tools.calculix_driver import run_solve

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


def _build_calculix_backend(*, work_root: Path, mesh_input: Path):
    """Create the AERON CalculiX backend without importing it at module load time."""
    from aeron.drivers import CalculiXFEABackend

    return CalculiXFEABackend(
        work_root=work_root,
        mesh_input=mesh_input,
        run_solve=run_solve,
        render_deck=_render_inp_deck,
        case_dir_name="solver",
    )


def _solver_syntax_failure(exc: Exception) -> dict[str, Any]:
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


def _preflight_failure(outcome: SolveOutcome) -> dict[str, Any]:
    return {
        "fault_class": FaultClass.UNKNOWN,
        "history": [
            {
                "node": "solver",
                "fault_class": FaultClass.UNKNOWN.value,
                "msg": outcome.status.message,
            }
        ],
    }


def _failed_solve(outcome: SolveOutcome) -> dict[str, Any]:
    fault_class = outcome.status.fault_class or FaultClass.UNKNOWN
    logger.warning(
        "CalculiX solve failed as %s (rc=%s).",
        fault_class,
        outcome.status.returncode,
    )
    return {
        "fault_class": fault_class,
        "retry_budgets": {"solver": 1},
        "history": [
            {
                "node": "solver",
                "fault_class": fault_class.value,
                "msg": outcome.status.message,
                "ccx_version": outcome.metadata.get("ccx_version"),
                "returncode": outcome.status.returncode,
                "wall_time_s": outcome.wall_clock_s,
            }
        ],
        "verdict": "re-run",
    }


def run(state: SimState) -> dict[str, Any]:
    """Solver agent entrypoint (LangGraph node signature)."""
    logger.info("Solver Agent invoked.")

    plan = state.get("plan")
    if not plan:
        raise ValueError("SimState is missing a SimPlan.")

    project_dir = Path(state.get("project_state_dir", "."))
    artifacts = state.get("artifacts", [])
    mesh_inp = state.get("mesh_path") or next(
        (path for path in artifacts if path.endswith(".inp")), None
    )
    if not mesh_inp:
        logger.error("No .inp mesh artifact found for solver.")
        return {"fault_class": FaultClass.UNKNOWN}

    mesh_src = Path(mesh_inp)
    backend = _build_calculix_backend(work_root=project_dir, mesh_input=mesh_src)

    try:
        case = backend.prepare_case(plan)
    except Exception as exc:
        if "mesh_input" in str(exc):
            logger.error("Mesh input validation failed: %s", exc)
            return {"fault_class": FaultClass.UNKNOWN}
        logger.error("Solver case preparation failed: %s", exc)
        return _solver_syntax_failure(exc)

    outcome = backend.solve(case, SolveOptions())

    if outcome.status.code is SolveStatusCode.PREFLIGHT_FAILED:
        logger.warning("CalculiX environment check failed: %s", outcome.status.message)
        return _preflight_failure(outcome)

    if outcome.status.code is not SolveStatusCode.OK:
        return _failed_solve(outcome)

    logger.info("CalculiX solve converged in %.1fs.", outcome.wall_clock_s)
    result_bundle = backend.parse_results(outcome)
    new_artifacts = artifacts.copy()
    new_artifacts.append(str(case.primary_input))
    for path in result_bundle.fields.values():
        new_artifacts.append(str(path))

    return {
        "fault_class": FaultClass.NONE,
        "frd_path": str(result_bundle.fields["frd"]) if "frd" in result_bundle.fields else None,
        "artifacts": new_artifacts,
        "solve_path": str(case.primary_input),
        "solve_metadata": {
            "wall_time_s": outcome.wall_clock_s,
            "ccx_version": outcome.metadata.get("ccx_version"),
        },
    }
