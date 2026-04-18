from __future__ import annotations

import pytest

from agents.router import MAX_RETRIES, route_reviewer
from schemas.sim_state import FaultClass, SimState


class TestRouter:
    def test_accept_routes_to_viz(self):
        state = SimState(verdict="Accept")
        assert route_reviewer(state) == "viz"

    def test_accept_with_note_routes_to_viz(self):
        state = SimState(verdict="Accept with Note")
        assert route_reviewer(state) == "viz"

    @pytest.mark.parametrize(
        "fault_class, expected_node",
        [
            (FaultClass.GEOMETRY_INVALID, "geometry"),
            (FaultClass.MESH_JACOBIAN, "mesh"),
            (FaultClass.MESH_RESOLUTION, "mesh"),
            (FaultClass.SOLVER_CONVERGENCE, "solver"),
            (FaultClass.SOLVER_TIMESTEP, "solver"),
            (FaultClass.SOLVER_SYNTAX, "solver"),
            (FaultClass.REFERENCE_MISMATCH, "architect"),
            (FaultClass.UNKNOWN, "human_fallback"),
            (
                FaultClass.NONE,
                "human_fallback",
            ),  # default fallback for re-run but NO fault class specified
        ],
    )
    def test_rerun_routes_by_fault_class(self, fault_class: FaultClass, expected_node: str):
        state = SimState(verdict="Re-run", fault_class=fault_class, retry_budgets={})
        assert route_reviewer(state) == expected_node

    def test_rerun_routes_to_human_fallback_when_budget_exceeded(self):
        # Even if fault class is solver, if budget is exceeded, it should go to human_fallback
        state = SimState(
            verdict="Re-run",
            fault_class=FaultClass.SOLVER_CONVERGENCE,
            retry_budgets={"solver": MAX_RETRIES},
        )
        assert route_reviewer(state) == "human_fallback"

        # Test just below budget
        state_below = SimState(
            verdict="Re-run",
            fault_class=FaultClass.SOLVER_CONVERGENCE,
            retry_budgets={"solver": MAX_RETRIES - 1},
        )
        assert route_reviewer(state_below) == "solver"

    @pytest.mark.parametrize("verdict", ["Needs Review", "Reject", None])
    def test_non_rerun_failures_route_to_human_fallback(self, verdict):
        state = SimState(verdict=verdict, fault_class=FaultClass.UNKNOWN, retry_budgets={})
        assert route_reviewer(state) == "human_fallback"
