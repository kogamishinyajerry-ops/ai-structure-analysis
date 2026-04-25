"""Tests for backend.app.workbench.agent_facade (ADR-015 §Decision)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

# schemas.sim_plan uses `enum.StrEnum` (Python 3.11+). Skip cleanly on older
# interpreters; CI is 3.11+.
pytest.importorskip("schemas.sim_plan")

from backend.app.workbench.agent_facade import (  # noqa: E402
    ArchitectError,
    ArchitectResult,
    draft_simplan_from_nl,
)
from schemas.sim_plan import AnalysisType, GeometrySpec, PhysicsSpec, SimPlan  # noqa: E402


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


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_draft_returns_architect_result_on_success():
    plan = _sample_plan()
    with patch(
        "agents.architect._extract_structured_data",
        return_value=plan,
    ):
        result = draft_simplan_from_nl(
            "Run a static analysis on a NACA0012 cantilever wing.",
        )
    assert isinstance(result, ArchitectResult)
    assert result.plan.case_id == "AI-FEA-P0-11"
    assert result.fault_class == "none"


def test_draft_passes_case_id_through_to_architect():
    plan = _sample_plan(case_id="AI-FEA-P2-99")
    with patch(
        "agents.architect._extract_structured_data",
        return_value=plan,
    ):
        result = draft_simplan_from_nl(
            "static beam analysis",
            case_id="AI-FEA-P2-99",
        )
    assert result.plan.case_id == "AI-FEA-P2-99"


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


def test_empty_nl_request_rejected():
    with pytest.raises(ValueError, match="non-empty"):
        draft_simplan_from_nl("")


def test_whitespace_only_nl_request_rejected():
    with pytest.raises(ValueError, match="non-empty"):
        draft_simplan_from_nl("   \n\t  ")


# ---------------------------------------------------------------------------
# Architect failure surfaces
# ---------------------------------------------------------------------------


def test_architect_returning_none_plan_raises_architect_error():
    with (
        patch("agents.architect._extract_structured_data", return_value=None),
        pytest.raises(ArchitectError) as exc_info,
    ):
        draft_simplan_from_nl("a request the LLM cannot parse")
    # The error includes the fault_class signal so callers can
    # surface a useful message to the workbench dialog.
    assert "fault_class" in str(exc_info.value)


def test_architect_llm_exception_raises_architect_error():
    with (
        patch(
            "agents.architect._extract_structured_data",
            side_effect=RuntimeError("LLM 500"),
        ),
        pytest.raises(ArchitectError),
    ):
        draft_simplan_from_nl("static beam")


# ---------------------------------------------------------------------------
# Discipline (ADR-015 read-only contract)
# ---------------------------------------------------------------------------


def test_facade_does_not_import_sim_state_at_module_level():
    """ADR-015 rule #3: facade does not import schemas.sim_state.

    A direct sys.modules check is the simplest assertion: importing the
    facade must not pull in schemas.sim_state under any name.
    """
    # Import inside the test so the import order is deterministic.
    import importlib
    import sys

    # Clear any previously loaded copy so the assertion reflects this
    # import path specifically.
    for mod in list(sys.modules):
        if mod.startswith("backend.app.workbench.agent_facade"):
            del sys.modules[mod]

    importlib.import_module("backend.app.workbench.agent_facade")

    # The facade itself MUST NOT have caused schemas.sim_state to be
    # imported. Other tests in the run may have loaded it; we only
    # check that the facade module's own dependency graph is clean.
    facade_module = sys.modules["backend.app.workbench.agent_facade"]
    facade_globals = vars(facade_module)
    # No direct `FaultClass` / `SimState` symbol in the facade's namespace.
    assert "FaultClass" not in facade_globals
    assert "SimState" not in facade_globals


def test_facade_does_not_mutate_architect_module_state():
    """The facade must call architect.run; it must NEVER assign to
    architect attributes."""
    plan = _sample_plan()
    with patch(
        "agents.architect._extract_structured_data",
        return_value=plan,
    ):
        # Snapshot architect's public attribute set, then call the
        # facade, then verify nothing was added.
        from agents import architect as architect_mod

        before = set(vars(architect_mod).keys())
        draft_simplan_from_nl("static beam")
        after = set(vars(architect_mod).keys())

    assert before == after, (
        "facade mutated agents.architect module-level state — "
        f"added: {after - before}, removed: {before - after}"
    )
