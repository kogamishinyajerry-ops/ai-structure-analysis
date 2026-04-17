from __future__ import annotations

import datetime

from langgraph.types import interrupt

from backend.app.well_harness.notion_sync import NotionRunRegistrar
from schemas.sim_state import SimState


def sync_to_notion_pending_review(case_id: str, run_id: str):
    """Real Notion writeback for Pending Review via well_harness."""
    print(
        f"[{datetime.datetime.now().isoformat()}] NOTION SYNC: Task {case_id} set to Pending Review for run {run_id}"
    )
    registrar = NotionRunRegistrar.from_default_path()
    res = registrar.create_standalone_task(
        case_id=case_id,
        run_id=run_id,
        status="Pending Review",
        summary="Graph execution paused by human_fallback interrupt due to limit or unknown fault.",
    )
    if res.attempted and not res.success:
        print(f"Failed to sync Notion task: {res.error_message}")


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
