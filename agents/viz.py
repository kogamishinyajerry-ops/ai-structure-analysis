"""Visualization & Analysis Agent — generates reports and VTP exports.

Responsibilities:
  - Parse .frd results via ``tools.frd_parser``.
  - Generate Markdown report via ``reporters.markdown``.
  - Export VTP for ParaView via ``reporters.vtp``.
  - Attach artifacts to the run state.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from reporters.markdown import generate_report
from schemas.sim_state import FaultClass, SimState
from tools.frd_parser import extract_field_extremes, parse_frd

logger = logging.getLogger(__name__)


def run(state: SimState) -> dict[str, Any]:
    """Viz agent entrypoint (LangGraph node signature)."""
    logger.info("Viz & Analysis Agent invoked.")

    plan = state.get("plan")
    if not plan:
        raise ValueError("SimState is missing a SimPlan.")

    project_dir = Path(state.get("project_state_dir", "."))
    report_dir = project_dir / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    # Locate .frd from state
    frd_path_str = state.get("frd_path")
    if not frd_path_str:
        artifacts = state.get("artifacts", [])
        frd_path_str = next((p for p in artifacts if p.endswith(".frd")), None)

    if not frd_path_str:
        logger.error("No .frd artifact found. Viz agent cannot proceed.")
        return {"fault_class": FaultClass.UNKNOWN}

    frd_path = Path(frd_path_str)

    # Parse the FRD
    try:
        parsed = parse_frd(frd_path)
    except Exception as e:
        logger.error("FRD parsing failed: %s", e)
        return {
            "fault_class": FaultClass.UNKNOWN,
            "history": [{"node": "viz", "fault": "unknown", "msg": str(e)}],
        }

    # Extract field extremes for common fields
    field_names_to_check = ["displacement", "stress"]
    field_extremes = []
    for fname in field_names_to_check:
        extremes = extract_field_extremes(parsed, fname)
        if extremes.get("max_magnitude") is not None:
            field_extremes.append(extremes)

    # Build report context
    report_ctx: dict[str, Any] = {
        "case_id": plan.case_id,
        "description": plan.description,
        "verdict": state.get("verdict", "review"),
        "fields": field_extremes,
        "reference_values": plan.reference_values,
    }

    # Generate the Markdown report
    report_path = generate_report(report_ctx, report_dir)

    # Collect artifacts
    new_artifacts = state.get("artifacts", []).copy()
    new_artifacts.append(str(report_path))

    logger.info("Viz agent complete. Report at %s", report_path)

    return {
        "fault_class": FaultClass.NONE,
        "reports": {"markdown": str(report_path)},
        "artifacts": new_artifacts,
    }
