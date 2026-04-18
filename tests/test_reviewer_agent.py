"""Tests for agents/reviewer.py — result validation and fault routing."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from agents.reviewer import (
    VERDICT_ACCEPT,
    VERDICT_ACCEPT_WITH_NOTE,
    VERDICT_NEEDS_REVIEW,
    VERDICT_RERUN,
    run,
)
from schemas.sim_state import FaultClass


@pytest.fixture()
def base_state(tmp_path):
    plan = MagicMock()
    plan.reference_values = {"displacement": 1.0e-3}

    return {
        "plan": plan,
        "frd_path": str(tmp_path / "test.frd"),
        "artifacts": [str(tmp_path / "test.frd")],
        "retry_budgets": {},
        "history": [],
        "fault_class": FaultClass.NONE,
    }


def test_reviewer_accepts_within_tolerance(base_state):
    parsed = {"fields": {"displacement": {"values": [1.02e-3]}}}

    with patch("agents.reviewer.parse_frd", return_value=parsed):
        result = run(base_state)

    assert result["verdict"] == VERDICT_ACCEPT
    assert result["fault_class"] == FaultClass.NONE


def test_reviewer_accepts_with_note_when_no_references(tmp_path):
    plan = MagicMock()
    plan.reference_values = {}
    state = {
        "plan": plan,
        "frd_path": str(tmp_path / "test.frd"),
        "artifacts": [str(tmp_path / "test.frd")],
        "fault_class": FaultClass.NONE,
    }

    with patch("agents.reviewer.parse_frd", return_value={"fields": {}}):
        result = run(state)

    assert result["verdict"] == VERDICT_ACCEPT_WITH_NOTE
    assert result["fault_class"] == FaultClass.NONE


def test_reviewer_reruns_mesh_for_reference_drift(base_state):
    parsed = {"fields": {"displacement": {"values": [1.15e-3]}}}

    with patch("agents.reviewer.parse_frd", return_value=parsed):
        result = run(base_state)

    assert result["verdict"] == VERDICT_RERUN
    assert result["fault_class"] == FaultClass.MESH_RESOLUTION
    assert result["retry_budgets"] == {"mesh": 1}


def test_reviewer_requests_review_for_critical_reference_mismatch(base_state):
    parsed = {"fields": {"displacement": {"values": [1.8e-3]}}}

    with patch("agents.reviewer.parse_frd", return_value=parsed):
        result = run(base_state)

    assert result["verdict"] == VERDICT_NEEDS_REVIEW
    assert result["fault_class"] == FaultClass.REFERENCE_MISMATCH


def test_reviewer_accepts_with_note_when_reference_field_missing(base_state):
    with patch("agents.reviewer.parse_frd", return_value={"fields": {}}):
        result = run(base_state)

    assert result["verdict"] == VERDICT_ACCEPT_WITH_NOTE
    assert result["fault_class"] == FaultClass.NONE


def test_reviewer_needs_review_when_artifact_missing(base_state):
    base_state["frd_path"] = None
    base_state["artifacts"] = []

    result = run(base_state)
    assert result["verdict"] == VERDICT_NEEDS_REVIEW
    assert result["fault_class"] == FaultClass.UNKNOWN


def test_reviewer_needs_review_when_parse_fails(base_state):
    with patch("agents.reviewer.parse_frd", side_effect=RuntimeError("parse failed")):
        result = run(base_state)

    assert result["verdict"] == VERDICT_NEEDS_REVIEW
    assert result["fault_class"] == FaultClass.UNKNOWN


@pytest.mark.parametrize(
    ("fault_class", "expected_verdict"),
    [
        (FaultClass.GEOMETRY_INVALID, VERDICT_RERUN),
        (FaultClass.MESH_JACOBIAN, VERDICT_RERUN),
        (FaultClass.MESH_RESOLUTION, VERDICT_RERUN),
        (FaultClass.SOLVER_CONVERGENCE, VERDICT_RERUN),
        (FaultClass.SOLVER_TIMESTEP, VERDICT_RERUN),
        (FaultClass.SOLVER_SYNTAX, VERDICT_RERUN),
        (FaultClass.REFERENCE_MISMATCH, VERDICT_NEEDS_REVIEW),
        (FaultClass.UNKNOWN, VERDICT_NEEDS_REVIEW),
    ],
)
def test_reviewer_covers_all_fault_classes(base_state, fault_class, expected_verdict):
    base_state["fault_class"] = fault_class
    result = run(base_state)

    assert result["verdict"] == expected_verdict
    assert result["fault_class"] == fault_class
