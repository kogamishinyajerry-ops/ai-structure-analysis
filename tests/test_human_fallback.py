from __future__ import annotations

from unittest.mock import MagicMock, patch

from schemas.sim_state import FaultClass


def test_human_fallback_returns_human_verdict():
    from agents.human_fallback import run

    state = {
        "plan": MagicMock(case_id="AI-FEA-P0-02"),
        "retry_budgets": {"solver": 3},
        "fault_class": FaultClass.SOLVER_CONVERGENCE,
    }

    with (
        patch("agents.human_fallback.sync_to_notion_pending_review") as sync_mock,
        patch("agents.human_fallback.interrupt", return_value={"verdict": "re-run"}),
    ):
        result = run(state)

    sync_mock.assert_called_once_with("AI-FEA-P0-02", "run-human-fallback-req")
    assert result["verdict"] == "re-run"


def test_human_fallback_defaults_to_accept_for_non_mapping_interrupt():
    from agents.human_fallback import run

    state = {
        "plan": MagicMock(case_id="AI-FEA-P0-02"),
        "retry_budgets": {"mesh": 3},
        "fault_class": FaultClass.UNKNOWN,
    }

    with (
        patch("agents.human_fallback.sync_to_notion_pending_review"),
        patch("agents.human_fallback.interrupt", return_value=None),
    ):
        result = run(state)

    assert result["verdict"] == "accept"
