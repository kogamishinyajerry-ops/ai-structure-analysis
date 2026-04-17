"""Tests for agents/solver.py — Jinja2 rendering + CalculiX invocation routing."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from schemas.sim_plan import (
    AnalysisType,
    BCSpec,
    GeometrySpec,
    LoadSpec,
    MaterialSpec,
    MeshStrategy,
    SimPlan,
    SolverControls,
)
from schemas.sim_state import FaultClass


@pytest.fixture()
def sample_plan() -> SimPlan:
    return SimPlan(
        case_id="AI-FEA-P0-07",
        analysis_type=AnalysisType.STATIC,
        description="Cantilever test",
        geometry=GeometrySpec(kind="naca", parameters={"profile": "NACA0012"}),
        material=MaterialSpec(
            name="Aluminium",
            youngs_modulus_pa=70e9,
            poissons_ratio=0.33,
        ),
        loads=[
            LoadSpec(
                kind="concentrated_force",
                parameters={"magnitude": -1000.0, "node_set": "Ntip"},
            )
        ],
        boundary_conditions=[BCSpec(kind="fixed", parameters={"node_set": "Nroot"})],
        mesh=MeshStrategy(),
        solver=SolverControls(),
    )


@pytest.fixture()
def solver_state(sample_plan, tmp_path) -> dict:
    # Create a dummy mesh inp
    mesh_dir = tmp_path / "mesh"
    mesh_dir.mkdir()
    mesh_inp = mesh_dir / "model.inp"
    mesh_inp.write_text("*NODE\n1, 0, 0, 0\n*ELEMENT\n1, 1\n")

    return {
        "plan": sample_plan,
        "project_state_dir": str(tmp_path),
        "artifacts": [str(mesh_inp)],
        "mesh_path": str(mesh_inp),
        "retry_budgets": {},
        "history": [],
    }


class TestRenderInpDeck:
    def test_renders_valid_deck(self, sample_plan, tmp_path):
        from agents.solver import _render_inp_deck

        deck = _render_inp_deck(sample_plan, "model.inp", tmp_path)

        assert deck.exists()
        content = deck.read_text(encoding="utf-8")
        # Check key substitutions
        assert "Aluminium" in content
        assert "70000000000.0" in content
        assert "0.33" in content
        assert "-1000.0" in content
        assert "Ntip" in content
        assert "Nroot" in content


class TestSolverAgent:
    def test_successful_solve(self, solver_state, tmp_path):
        from agents.solver import run as solver_run

        solver_dir = tmp_path / "solver"
        solver_dir.mkdir(parents=True, exist_ok=True)

        # Simulate ccx producing output files
        def fake_run_solve(inp_path, work_dir, **kwargs):
            frd = work_dir / "solver_deck.frd"
            frd.write_text("FRD RESULT")
            return {
                "frd_path": str(frd),
                "dat_path": None,
                "sta_path": None,
                "converged": True,
                "wall_time_s": 1.23,
                "returncode": 0,
            }

        with patch("agents.solver.run_solve", side_effect=fake_run_solve):
            result = solver_run(solver_state)

        assert result["fault_class"] == FaultClass.NONE
        assert result["frd_path"] is not None

    def test_diverged_solve(self, solver_state):
        from agents.solver import run as solver_run

        def fake_diverge(inp_path, work_dir, **kwargs):
            return {
                "frd_path": None,
                "dat_path": None,
                "sta_path": None,
                "converged": False,
                "wall_time_s": 0.5,
                "returncode": 1,
            }

        with patch("agents.solver.run_solve", side_effect=fake_diverge):
            result = solver_run(solver_state)

        assert result["fault_class"] == FaultClass.SOLVER_CONVERGENCE
        assert result["retry_budgets"] == {"solver": 1}

    def test_ccx_not_found(self, solver_state):
        from agents.solver import run as solver_run

        with patch(
            "agents.solver.run_solve",
            side_effect=FileNotFoundError("ccx not on PATH"),
        ):
            result = solver_run(solver_state)

        assert result["fault_class"] == FaultClass.UNKNOWN

    def test_missing_mesh_artifact(self, sample_plan, tmp_path):
        from agents.solver import run as solver_run

        state = {
            "plan": sample_plan,
            "project_state_dir": str(tmp_path),
            "artifacts": [],
            "mesh_path": None,
            "retry_budgets": {},
            "history": [],
        }
        result = solver_run(state)
        assert result["fault_class"] == FaultClass.UNKNOWN
