"""Architect Agent — produces a canonical SimPlan from a natural-language spec."""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import Any

from schemas.sim_plan import SimPlan
from schemas.sim_state import FaultClass, SimState

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "architect_golden_prompt.md"
CASE_ID_PATTERN = re.compile(r"^AI-FEA-P\d+-\d+$")


def _load_prompt_template() -> str:
    """Load the golden architect prompt from the repository."""
    return PROMPT_PATH.read_text(encoding="utf-8")


def _build_prompt(user_request: str) -> str:
    template = _load_prompt_template()
    return template.replace("{{USER_REQUEST}}", user_request)


def _valid_case_id(candidate: str | None) -> bool:
    return bool(candidate and CASE_ID_PATTERN.fullmatch(candidate))


def _canonical_case_id(user_request: str, existing_case_id: str | None = None) -> str:
    """Return a deterministic, naming-compliant fallback case id."""
    if _valid_case_id(existing_case_id):
        return str(existing_case_id)

    digest = hashlib.sha1(user_request.encode("utf-8")).hexdigest()
    suffix = (int(digest[:4], 16) % 90) + 10
    return f"AI-FEA-P0-{suffix:02d}"


def _extract_structured_data(**kwargs: Any) -> SimPlan | None:
    """Import the LLM helper lazily so schema tests do not require runtime deps."""
    from agents.llm import extract_structured_data

    return extract_structured_data(**kwargs)


def run(state: SimState) -> dict[str, Any]:
    """Architect agent entrypoint (LangGraph node signature)."""
    logger.info("Architect Agent invoked.")

    user_request = state.get("user_request")
    if not user_request:
        logger.warning("No user_request found in state.")
        return {"fault_class": FaultClass.UNKNOWN}

    try:
        plan = _extract_structured_data(
            prompt=_build_prompt(user_request),
            response_model=SimPlan,
            system_message="You are a professional FEA Architect.",
        )
    except Exception as exc:
        logger.error("LLM extraction failed: %s", exc)
        return {
            "fault_class": FaultClass.UNKNOWN,
            "history": [{"node": "architect", "fault": "logic_error", "msg": str(exc)}],
        }

    if not plan:
        logger.error("Architect failed to produce a valid SimPlan.")
        return {
            "fault_class": FaultClass.UNKNOWN,
            "history": [
                {"node": "architect", "fault": "parsing_failed", "msg": "LLM returned null"}
            ],
        }

    plan.case_id = _canonical_case_id(
        user_request=user_request,
        existing_case_id=state.get("case_id") or plan.case_id,
    )

    logger.info("Architect produced SimPlan: %s", plan.case_id)
    return {"plan": plan, "fault_class": FaultClass.NONE}
