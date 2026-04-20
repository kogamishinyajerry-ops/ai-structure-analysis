"""Lint-Deck Agent — static .inp lint gate before solver invocation.

This node runs ``tools.inp_linter.lint_inp`` on the rendered or pre-existing
``.inp`` deck and short-circuits with ``FaultClass.SOLVER_SYNTAX`` when
errors are found, avoiding a wasted ccx container round-trip.

Wiring: ``mesh`` → ``lint_deck`` → (conditional) → ``solver`` | ``reviewer``
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from schemas.sim_state import FaultClass, SimState
from tools.inp_linter import lint_inp

logger = logging.getLogger(__name__)


def run(state: SimState) -> dict[str, Any]:
    """Lint-deck agent entrypoint (LangGraph node signature)."""
    logger.info("Lint-Deck Agent invoked.")

    # Locate the .inp deck to lint.
    # Priority: explicit mesh_path → last .inp artifact
    inp_path: str | None = state.get("mesh_path")
    if not inp_path:
        artifacts = state.get("artifacts", [])
        inp_path = next((p for p in artifacts if p.endswith(".inp")), None)

    if not inp_path or not Path(inp_path).exists():
        logger.warning("No .inp deck found to lint — passing through to solver.")
        return {"fault_class": FaultClass.NONE}

    try:
        report = lint_inp(inp_path)
    except Exception as exc:
        logger.error("inp_linter crashed: %s", exc)
        return {
            "fault_class": FaultClass.SOLVER_SYNTAX,
            "history": [{"node": "lint_deck", "fault": "solver_syntax", "msg": str(exc)}],
        }

    # Persist report dict in state for downstream consumption
    lint_dict = report.to_dict()

    if not report.ok:
        error_summary = "; ".join(f.message for f in report.errors[:5])
        logger.warning(
            "Lint gate blocked: %d error(s) found — %s", len(report.errors), error_summary
        )
        return {
            "fault_class": FaultClass.SOLVER_SYNTAX,
            "lint_report": lint_dict,
            "history": [
                {
                    "node": "lint_deck",
                    "fault": FaultClass.SOLVER_SYNTAX.value,
                    "msg": f"{len(report.errors)} error(s): {error_summary}",
                }
            ],
        }

    logger.info(
        "Lint gate passed (%d warning(s)).", len(report.warnings)
    )
    return {
        "fault_class": FaultClass.NONE,
        "lint_report": lint_dict,
    }
