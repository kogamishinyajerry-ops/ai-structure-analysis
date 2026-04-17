"""Tests for agents/architect.py — NL to SimPlan conversion."""

import pytest
from unittest.mock import MagicMock, patch
from agents.architect import run
from schemas.sim_plan import AnalysisType
from schemas.sim_state import FaultClass


@pytest.fixture
def mock_sim_state():
    return {
        "user_request": "Run a static analysis on a NACA0012 beam with 500N load and Aluminum 7075 material.",
        "plan": None,
        "history": [],
        "retry_budgets": {},
    }


def test_architect_success(mock_sim_state):
    """Test successful extraction of a SimPlan from natural language."""

    # Mocking the extract_structured_data function
    mock_plan = MagicMock()
    mock_plan.case_id = "AI-FEA-P0-11"
    mock_plan.analysis_type = AnalysisType.STATIC

    # We patch the utility function that uses OpenAI
    with patch("agents.architect.extract_structured_data", return_value=mock_plan) as mock_extract:
        result = run(mock_sim_state)

        assert result["fault_class"] == FaultClass.NONE
        assert result["plan"].case_id == "AI-FEA-P0-11"
        mock_extract.assert_called_once()


def test_architect_missing_input():
    """Test handling of missing user request."""
    state = {"user_request": None}
    result = run(state)
    assert result["fault_class"] == FaultClass.UNKNOWN


def test_architect_extraction_failure(mock_sim_state):
    """Test handling of LLM returning None."""
    with patch("agents.architect.extract_structured_data", return_value=None):
        result = run(mock_sim_state)
        assert result["fault_class"] == FaultClass.UNKNOWN
        assert any("parsing_failed" in h["fault"] for h in result["history"])


def test_architect_case_id_autogen(mock_sim_state):
    """Test that Architect generates a case ID if the LLM doesn't."""
    mock_plan = MagicMock()
    mock_plan.case_id = None  # Mocking missing case_id

    with patch("agents.architect.extract_structured_data", return_value=mock_plan):
        result = run(mock_sim_state)
        assert result["plan"].case_id.startswith("AI-FEA-P0-")
