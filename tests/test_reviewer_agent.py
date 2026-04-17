"""Tests for agents/reviewer.py — result validation and fault routing."""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from agents.reviewer import run
from schemas.sim_state import FaultClass


@pytest.fixture
def base_state(tmp_path):
    plan = MagicMock()
    plan.reference_values = {"displacement": 1.0e-3}

    return {
        "plan": plan,
        "frd_path": str(tmp_path / "test.frd"),
        "artifacts": [str(tmp_path / "test.frd")],
        "retry_budgets": {},
        "history": [],
    }


def test_reviewer_accept(base_state):
    """Case A: Accept if error is < 5%."""
    # Mocking extract_field_extremes to return 1.02e-3 (2% error)
    mock_extremes = {"max_magnitude": 1.02e-3}

    with patch("agents.reviewer.parse_frd", return_value={}):
        with patch("agents.reviewer.extract_field_extremes", return_value=mock_extremes):
            result = run(base_state)

            assert result["verdict"] == "accept"
            assert result["fault_class"] == FaultClass.NONE


def test_reviewer_mesh_refinement(base_state):
    """Case B: Recommend Mesh Resolution if error is 15%."""
    # 1.15e-3 vs 1.0e-3 -> 15% error
    mock_extremes = {"max_magnitude": 1.15e-3}

    with patch("agents.reviewer.parse_frd", return_value={}):
        with patch("agents.reviewer.extract_field_extremes", return_value=mock_extremes):
            result = run(base_state)

            assert result["verdict"] == "re-run"
            assert result["fault_class"] == FaultClass.MESH_RESOLUTION
            assert result["retry_budgets"] == {"mesh": 1}


def test_reviewer_architect_correction(base_state):
    """Case C: Recommend Architect Correction if error is 80%."""
    # 1.8e-3 vs 1.0e-3 -> 80% error
    mock_extremes = {"max_magnitude": 1.8e-3}

    with patch("agents.reviewer.parse_frd", return_value={}):
        with patch("agents.reviewer.extract_field_extremes", return_value=mock_extremes):
            result = run(base_state)

            assert result["verdict"] == "re-run"
            assert result["fault_class"] == FaultClass.REFERENCE_MISMATCH
            assert result["retry_budgets"] == {"architect": 1}


def test_reviewer_no_references(tmp_path):
    """Should accept by default if no reference values are provided."""
    plan = MagicMock()
    plan.reference_values = {}
    state = {
        "plan": plan,
        "frd_path": str(tmp_path / "test.frd"),
        "artifacts": [str(tmp_path / "test.frd")],
    }

    with patch("agents.reviewer.parse_frd", return_value={}):
        result = run(state)
        assert result["verdict"] == "accept"


def test_reviewer_missing_artifact(base_state):
    """Handle missing .frd gracefully."""
    base_state["frd_path"] = None
    base_state["artifacts"] = []

    result = run(base_state)
    assert result["verdict"] == "re-run"
    assert result["fault_class"] == FaultClass.UNKNOWN
