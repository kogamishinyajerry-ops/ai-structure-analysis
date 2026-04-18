"""Tests for agents/architect.py — NL to canonical SimPlan conversion."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from agents.architect import PROMPT_PATH, _build_prompt, _canonical_case_id, run
from schemas.sim_plan import AnalysisType, GeometrySpec, PhysicsSpec, SimPlan
from schemas.sim_state import FaultClass


@pytest.fixture()
def mock_sim_state():
    return {
        "user_request": "Run a static analysis on a NACA0012 cantilever wing with a 500N tip load.",
        "plan": None,
        "history": [],
        "retry_budgets": {},
    }


def _sample_plan(case_id: str = "AI-FEA-P0-11") -> SimPlan:
    return SimPlan(
        case_id=case_id,
        physics=PhysicsSpec(type=AnalysisType.STATIC),
        geometry=GeometrySpec(
            mode="knowledge",
            ref="naca",
            params={"profile": "NACA0012", "span": 1.2, "chord": 0.3},
        ),
    )


def test_architect_success(mock_sim_state):
    with patch(
        "agents.architect._extract_structured_data",
        return_value=_sample_plan(),
    ) as mock_extract:
        result = run(mock_sim_state)

    assert result["fault_class"] == FaultClass.NONE
    assert result["plan"].case_id == "AI-FEA-P0-11"
    assert result["plan"].physics.type == AnalysisType.STATIC
    mock_extract.assert_called_once()


def test_architect_missing_input():
    result = run({"user_request": None})
    assert result["fault_class"] == FaultClass.UNKNOWN


def test_architect_extraction_failure(mock_sim_state):
    with patch("agents.architect._extract_structured_data", return_value=None):
        result = run(mock_sim_state)

    assert result["fault_class"] == FaultClass.UNKNOWN
    assert any("parsing_failed" in entry["fault"] for entry in result["history"])


def test_architect_canonicalizes_invalid_case_id(mock_sim_state):
    invalid_plan = _sample_plan()
    invalid_plan.case_id = "INVALID"

    with patch(
        "agents.architect._extract_structured_data",
        return_value=invalid_plan,
    ):
        result = run(mock_sim_state)

    assert result["plan"].case_id == _canonical_case_id(mock_sim_state["user_request"])
    assert result["plan"].case_id.startswith("AI-FEA-P0-")


def test_architect_prefers_existing_state_case_id(mock_sim_state):
    state = dict(mock_sim_state)
    state["case_id"] = "AI-FEA-P4-02"

    with patch(
        "agents.architect._extract_structured_data",
        return_value=_sample_plan(case_id="AI-FEA-P0-11"),
    ):
        result = run(state)

    assert result["plan"].case_id == "AI-FEA-P4-02"


def test_architect_prompt_is_externalized():
    assert PROMPT_PATH.exists()
    prompt = _build_prompt("Solve a cantilever wing.")
    assert "Solve a cantilever wing." in prompt
    assert "case_id" in prompt
