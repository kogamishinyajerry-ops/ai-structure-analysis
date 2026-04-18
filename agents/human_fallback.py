from __future__ import annotations

import datetime

from langgraph.types import interrupt

from schemas.sim_state import SimState


def sync_to_notion_pending_review(case_id: str, run_id: str):
    """Stub to simulate Notion writeback for Pending Review via well_harness."""
    message = (
        f"[{datetime.datetime.now().isoformat()}] NOTION SYNC: "
        f"Task {case_id} set to Pending Review for run {run_id}"
    )
    print(message)


def run(state: SimState) -> dict:
    """Human fallback node to pause the graph using interrupt().

    Triggered when retry budgets are exceeded or fault class is UNKNOWN.
    """
    case_id = (
        state.get("plan", {}).case_id
        if getattr(state.get("plan"), "case_id", None)
        else "UNKNOWN_CASE"
    )
    budgets = state.get("retry_budgets", {})
    fault_class = state.get("fault_class")

    sync_to_notion_pending_review(case_id, "run-human-fallback-req")

    human_decision = interrupt(
        {
            "reason": "Retry budget exceeded or unknown fault",
            "fault_class": fault_class,
            "budgets": budgets,
            "action_required": "Please review the run and specify next action",
        }
    )

    return {
        "verdict": human_decision.get("verdict", "accept")
        if isinstance(human_decision, dict)
        else "accept"
    }
