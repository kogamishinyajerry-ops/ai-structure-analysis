"""Solver Agent — renders the deck and runs the CalculiX solve."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from aeron.protocols import SolveOptions, SolveOutcome, SolveStatusCode
from schemas.sim_state import FaultClass, SimState
from tools.calculix_driver import run_solve

# Deck rendering lives in the LOW driver layer (tools/) so aeron can depend on it DOWNWARD
# (ADR-015); re-exported here under the old private name so the live solver path
# (_build_backend passes render_deck=_render_inp_deck) and the test mock target
# ``agents.solver._render_inp_deck`` keep working with zero churn (audit Rank 7).
from tools.inp_writer import render_inp_deck as _render_inp_deck

logger = logging.getLogger(__name__)


def _build_backend(*, plan: Any, work_root: Path, mesh_input: Path):
    """Build the AERON FEABackend for ``plan.solver.name`` via the aeron
    ``get_backend()`` factory (ADR-028 D4 P2). Imported at call time so the agent
    layer carries no aeron import at module load (circular-dep guard). A
    non-CalculiX plan raises ``NotImplementedError`` here — the caller converts it
    into the node's honest non-retriable failure, never a silent CalculiX fallback.
    """
    from aeron.drivers import get_backend

    return get_backend(
        plan.solver.name,
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


def _unsupported_backend_failure(plan: Any) -> dict[str, Any]:
    message = f"Unsupported solver backend for CalculiX solver node: {plan.solver.name}"
    return {
        "fault_class": FaultClass.UNKNOWN,
        "history": [
            {
                "node": "solver",
                "fault_class": FaultClass.UNKNOWN.value,
                "msg": message,
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
    try:
        backend = _build_backend(plan=plan, work_root=project_dir, mesh_input=mesh_src)
    except NotImplementedError as exc:
        # The factory rejected a non-CalculiX backend honestly (CalculiX-first,
        # ADR-028 D4/D5). Convert the raise into the node's non-retriable failure
        # contract (fault_class=UNKNOWN, no retry_budgets/verdict) — never a silent
        # wrong-physics solve. CalculiXFEABackend.prepare_case keeps its own
        # ValueError guard as the defense-in-depth last line.
        logger.error("Unsupported solver backend: %s", exc)
        return _unsupported_backend_failure(plan)

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
            "backend": outcome.metadata.get("backend"),
            "wall_time_s": outcome.wall_clock_s,
            "ccx_version": outcome.metadata.get("ccx_version"),
        },
    }
