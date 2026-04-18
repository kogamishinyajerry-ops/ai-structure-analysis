from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from schemas.sim_state import FaultClass


def test_human_fallback_returns_human_verdict():
    from agents.human_fallback import run

    registrar = MagicMock()
    registrar.build_graph_run_id.return_value = "run-20260418-AI-FEA-P0-02-ebf5f9a"
    registrar.create_standalone_task.return_value = SimpleNamespace(
        attempted=True,
        success=True,
        error_message=None,
    )
    state = {
        "plan": MagicMock(case_id="AI-FEA-P0-02"),
        "retry_budgets": {"solver": 3},
        "fault_class": FaultClass.SOLVER_CONVERGENCE,
    }

    with (
        patch("agents.human_fallback.NotionRunRegistrar.from_default_path", return_value=registrar),
        patch("agents.human_fallback.interrupt", return_value={"verdict": "re-run"}),
    ):
        result = run(state)

    registrar.build_graph_run_id.assert_called_once_with("AI-FEA-P0-02")
    registrar.create_standalone_task.assert_called_once()
    assert (
        registrar.create_standalone_task.call_args.kwargs["run_id"]
        == "run-20260418-AI-FEA-P0-02-ebf5f9a"
    )
    assert "solver_convergence" in registrar.create_standalone_task.call_args.kwargs["summary"]
    assert result["verdict"] == "re-run"
    assert result["run_id"] == "run-20260418-AI-FEA-P0-02-ebf5f9a"


def test_human_fallback_defaults_to_accept_for_non_mapping_interrupt():
    from agents.human_fallback import run

    registrar = MagicMock()
    registrar.build_graph_run_id.return_value = "run-20260418-AI-FEA-P0-02-ebf5f9a"
    registrar.create_standalone_task.return_value = SimpleNamespace(
        attempted=True,
        success=True,
        error_message=None,
    )
    state = {
        "plan": MagicMock(case_id="AI-FEA-P0-02"),
        "retry_budgets": {"mesh": 3},
        "fault_class": FaultClass.UNKNOWN,
    }

    with (
        patch("agents.human_fallback.NotionRunRegistrar.from_default_path", return_value=registrar),
        patch("agents.human_fallback.interrupt", return_value=None),
    ):
        result = run(state)

    assert result["verdict"] == "accept"
    assert result["run_id"] == "run-20260418-AI-FEA-P0-02-ebf5f9a"
