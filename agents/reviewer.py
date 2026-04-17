"""Reviewer / Corrector Agent — validates results and triggers re-runs."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from schemas.sim_state import FaultClass, SimState
from tools.frd_parser import extract_field_extremes, parse_frd

logger = logging.getLogger(__name__)

# Default relative error tolerance (5%)
DEFAULT_TOLERANCE = 0.05
# Critical error threshold (50%) — likely a setup error (BCs/Loads)
CRITICAL_TOLERANCE = 0.50


def run(state: SimState) -> dict[str, Any]:
    """Reviewer agent entrypoint (LangGraph node signature)."""
    logger.info("Reviewer Agent invoked.")

    plan = state.get("plan")
    if not plan:
        raise ValueError("SimState is missing a SimPlan.")

    # Locate FRD artifact
    frd_path_str = state.get("frd_path")
    if not frd_path_str:
        artifacts = state.get("artifacts", [])
        frd_path_str = next((p for p in artifacts if p.endswith(".frd")), None)

    if not frd_path_str:
        logger.error("No .frd artifact found. Reviewer cannot proceed.")
        return {
            "verdict": "re-run",
            "fault_class": FaultClass.UNKNOWN,
            "history": [{"node": "reviewer", "fault": "missing_artifact", "msg": "No .frd found"}],
        }

    frd_path = Path(frd_path_str)

    # Parse FRD
    try:
        parsed = parse_frd(frd_path)
    except Exception as e:
        logger.error("FRD parsing failed: %s", e)
        return {
            "verdict": "re-run",
            "fault_class": FaultClass.UNKNOWN,
            "history": [{"node": "reviewer", "fault": "parsing_failed", "msg": str(e)}],
        }

    # Comparison Logic
    reference_values = plan.reference_values
    if not reference_values:
        logger.info("No reference values provided. Accepting by default.")
        return {"verdict": "accept", "fault_class": FaultClass.NONE}

    history_entries = []
    fault_to_trigger = FaultClass.NONE
    max_error_found = 0.0

    for field_name, ref_val in reference_values.items():
        if ref_val == 0:
            continue

        extremes = extract_field_extremes(parsed, field_name)
        computed = extremes.get("max_magnitude")

        if computed is None:
            logger.warning(f"Field '{field_name}' not found in results.")
            continue

        rel_error = abs(computed - ref_val) / abs(ref_val)
        max_error_found = max(max_error_found, rel_error)

        logger.info(
            f"Field '{field_name}': Ref={ref_val:.4g}, Comp={computed:.4g}, Error={rel_error:.2%}"
        )

        if rel_error > DEFAULT_TOLERANCE:
            # Determine fault class based on error magnitude
            if rel_error > CRITICAL_TOLERANCE:
                current_fault = FaultClass.REFERENCE_MISMATCH  # Re-run Architect
            else:
                current_fault = FaultClass.MESH_RESOLUTION  # Re-run Mesh

            # Prioritize more severe faults if multiple fail
            if (
                fault_to_trigger == FaultClass.NONE
                or current_fault == FaultClass.REFERENCE_MISMATCH
            ):
                fault_to_trigger = current_fault

            history_entries.append(
                {
                    "node": "reviewer",
                    "fault": current_fault.value,
                    "msg": f"'{field_name}' error {rel_error:.1%} exceeds tolerance",
                }
            )

    if fault_to_trigger != FaultClass.NONE:
        # Optimization: suggest mesh refinement by incrementing the budget for 'mesh' node
        retry_updates = {}
        if fault_to_trigger == FaultClass.MESH_RESOLUTION:
            retry_updates = {"mesh": 1}
        elif fault_to_trigger == FaultClass.REFERENCE_MISMATCH:
            retry_updates = {"architect": 1}

        return {
            "verdict": "re-run",
            "fault_class": fault_to_trigger,
            "retry_budgets": retry_updates,
            "history": history_entries,
        }

    # All checks passed
    logger.info("Verification passed (all errors < 5%).")
    return {
        "verdict": "accept",
        "fault_class": FaultClass.NONE,
    }
