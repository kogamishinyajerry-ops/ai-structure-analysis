"""Reviewer / Corrector Agent — validates results and triggers re-runs."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from schemas.sim_state import FaultClass, SimState
from tools.frd_parser import extract_field_extremes, parse_frd

logger = logging.getLogger(__name__)

DEFAULT_TOLERANCE = 0.05
CRITICAL_TOLERANCE = 0.50

VERDICT_ACCEPT = "Accept"
VERDICT_ACCEPT_WITH_NOTE = "Accept with Note"
VERDICT_REJECT = "Reject"
VERDICT_NEEDS_REVIEW = "Needs Review"
VERDICT_RERUN = "Re-run"

RERUN_FAULTS = {
    FaultClass.GEOMETRY_INVALID,
    FaultClass.MESH_JACOBIAN,
    FaultClass.MESH_RESOLUTION,
    FaultClass.SOLVER_CONVERGENCE,
    FaultClass.SOLVER_TIMESTEP,
    FaultClass.SOLVER_SYNTAX,
}


def _review_upstream_fault(state: SimState, fault_class: FaultClass) -> dict[str, Any]:
    """Convert an upstream fault into a reviewer verdict without re-parsing FRD."""
    history = state.get("history", []).copy()
    history.append(
        {
            "node": "reviewer",
            "fault_class": fault_class.value,
            "msg": "Reviewer propagated upstream fault classification.",
        }
    )

    if fault_class in RERUN_FAULTS:
        return {
            "verdict": VERDICT_RERUN,
            "fault_class": fault_class,
            "history": history,
        }

    return {
        "verdict": VERDICT_NEEDS_REVIEW,
        "fault_class": fault_class,
        "history": history,
    }


def run(state: SimState) -> dict[str, Any]:
    """Reviewer agent entrypoint (LangGraph node signature)."""
    logger.info("Reviewer Agent invoked.")

    plan = state.get("plan")
    if not plan:
        raise ValueError("SimState is missing a SimPlan.")

    upstream_fault = state.get("fault_class", FaultClass.NONE)
    if upstream_fault != FaultClass.NONE:
        return _review_upstream_fault(state, upstream_fault)

    frd_path_str = state.get("frd_path")
    if not frd_path_str:
        artifacts = state.get("artifacts", [])
        frd_path_str = next((path for path in artifacts if path.endswith(".frd")), None)

    if not frd_path_str:
        logger.error("No .frd artifact found. Reviewer cannot proceed.")
        return {
            "verdict": VERDICT_NEEDS_REVIEW,
            "fault_class": FaultClass.UNKNOWN,
            "history": [
                {
                    "node": "reviewer",
                    "fault_class": FaultClass.UNKNOWN.value,
                    "msg": "No .frd artifact found.",
                }
            ],
        }

    frd_path = Path(frd_path_str)

    try:
        parsed = parse_frd(frd_path)
    except Exception as exc:
        logger.error("FRD parsing failed: %s", exc)
        return {
            "verdict": VERDICT_NEEDS_REVIEW,
            "fault_class": FaultClass.UNKNOWN,
            "history": [
                {
                    "node": "reviewer",
                    "fault_class": FaultClass.UNKNOWN.value,
                    "msg": str(exc),
                }
            ],
        }

    reference_values = plan.reference_values
    if not reference_values:
        logger.info("No reference values provided. Accepting with note.")
        return {
            "verdict": VERDICT_ACCEPT_WITH_NOTE,
            "fault_class": FaultClass.NONE,
            "history": [
                {
                    "node": "reviewer",
                    "fault_class": FaultClass.NONE.value,
                    "msg": "No reference values supplied; accepted with note.",
                }
            ],
        }

    history_entries: list[dict[str, Any]] = []
    max_error_found = 0.0
    missing_fields: list[str] = []

    for field_name, ref_val in reference_values.items():
        if ref_val == 0:
            continue

        extremes = extract_field_extremes(parsed, field_name)
        if extremes.get("max_magnitude") is None:
            logger.warning("Field '%s' not found in parsed results.", field_name)
            missing_fields.append(field_name)
            continue

        computed = extremes["max_magnitude"]
        rel_error = abs(computed - ref_val) / abs(ref_val)
        max_error_found = max(max_error_found, rel_error)
        history_entries.append(
            {
                "node": "reviewer",
                "fault_class": FaultClass.NONE.value,
                "msg": f"{field_name} error={rel_error:.1%}",
            }
        )

    if max_error_found > CRITICAL_TOLERANCE:
        history_entries.append(
            {
                "node": "reviewer",
                "fault_class": FaultClass.REFERENCE_MISMATCH.value,
                "msg": f"Reference mismatch {max_error_found:.1%} exceeds critical tolerance.",
            }
        )
        return {
            "verdict": VERDICT_NEEDS_REVIEW,
            "fault_class": FaultClass.REFERENCE_MISMATCH,
            "history": history_entries,
        }

    if max_error_found > DEFAULT_TOLERANCE:
        history_entries.append(
            {
                "node": "reviewer",
                "fault_class": FaultClass.MESH_RESOLUTION.value,
                "msg": f"Reference mismatch {max_error_found:.1%} exceeds mesh tolerance.",
            }
        )
        return {
            "verdict": VERDICT_RERUN,
            "fault_class": FaultClass.MESH_RESOLUTION,
            "retry_budgets": {"mesh": 1},
            "history": history_entries,
        }

    if missing_fields:
        history_entries.append(
            {
                "node": "reviewer",
                "fault_class": FaultClass.NONE.value,
                "msg": f"Missing reference fields: {', '.join(sorted(missing_fields))}.",
            }
        )
        return {
            "verdict": VERDICT_ACCEPT_WITH_NOTE,
            "fault_class": FaultClass.NONE,
            "history": history_entries,
        }

    logger.info("Verification passed (all errors <= 5%%).")
    return {
        "verdict": VERDICT_ACCEPT,
        "fault_class": FaultClass.NONE,
        "history": history_entries,
    }
