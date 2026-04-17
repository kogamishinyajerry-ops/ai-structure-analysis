"""Architect Agent — produces a SimPlan from a natural-language spec."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from agents.llm import extract_structured_data
from schemas.sim_plan import SimPlan
from schemas.sim_state import FaultClass, SimState

logger = logging.getLogger(__name__)

GOLDEN_ARCHITECT_PROMPT = """
You are a Lead Structural Engineer. Your task is to extract a complete FEA Simulation Plan (SimPlan) from a user's natural language request.

CONTEXT:
We specialize in NACA airfoil cantilever beams. 
- The root (fixed end) is always 'Nroot'.
- The tip (loading end) is always 'Ntip'.
- Default material is Aluminum 7075 if not specified.
- Current analysis focus: STATIC.

USER REQUEST:
"{user_request}"

INSTRUCTIONS:
1. Identify geometry parameters (profile, span, chord).
2. Identify material properties.
3. Identify loads (magnitude, direction, location).
4. Identify boundary conditions (usually fixed at Nroot).
5. Generate a unique case_id in the format 'AI-FEA-P0-99' where 99 is a random number or based on intent.
6. If the request is incomplete, use sensible engineering defaults.

Output must be a single JSON object.
"""


def run(state: SimState) -> dict[str, Any]:
    """Architect agent entrypoint (LangGraph node signature)."""
    logger.info("Architect Agent invoked.")

    user_request = state.get("user_request")
    if not user_request:
        logger.warning("No user_request found in state. Falling back to default plan.")
        # This shouldn't normally happen if the graph is started correctly.
        return {"fault_class": FaultClass.UNKNOWN}

    # Invoke LLM for structured extraction
    try:
        plan = extract_structured_data(
            prompt=GOLDEN_ARCHITECT_PROMPT.format(user_request=user_request),
            response_model=SimPlan,
            system_message="You are a professional FEA Architect.",
        )
    except Exception as e:
        logger.error(f"LLM extraction failed: {e}")
        return {
            "fault_class": FaultClass.UNKNOWN,
            "history": [{"node": "architect", "fault": "logic_error", "msg": str(e)}],
        }

    if not plan:
        logger.error("Architect failed to produce a valid SimPlan.")
        return {
            "fault_class": FaultClass.UNKNOWN,
            "history": [
                {"node": "architect", "fault": "parsing_failed", "msg": "LLM returned null"}
            ],
        }

    # Ensure Case ID is valid if LLM messed it up
    if not plan.case_id or plan.case_id == "UNKNOWN":
        timestamp = datetime.now(timezone.utc).strftime("%m%d-%H%M")
        plan.case_id = f"AI-FEA-P0-{timestamp}"

    logger.info(f"Architect produced SimPlan: {plan.case_id}")

    return {
        "plan": plan,
        "fault_class": FaultClass.NONE,
    }
