"""Tests for agents/solver.py."""

from __future__ import annotations

from unittest.mock import patch

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
    mesh_dir = tmp_path / "mesh"
    mesh_dir.mkdir()
    mesh_inp = mesh_dir / "model.inp"
    mesh_inp.write_text(
        "*NODE, NSET=Nall\n"
        "1, 0.0, 0.0, 0.0\n2, 1.0, 0.0, 0.0\n"
        "*NSET, NSET=Nroot\n1\n"
        "*NSET, NSET=Ntip\n2\n"
        "*ELEMENT, TYPE=C3D8, ELSET=Eall\n"
        "1, 1, 2, 1, 1, 1, 1, 1, 1\n",
        encoding="utf-8",
    )

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
        assert deck.name == "solve.inp"
        content = deck.read_text(encoding="utf-8")
        assert "Aluminium" in content
        assert "70000000000.0" in content
        assert "0.33" in content
        assert "-1000.0" in content
        assert "Ntip" in content
        assert "Nroot" in content


class TestSolverAgent:
    def test_successful_solve(self, solver_state, tmp_path):
        from agents.solver import run as solver_run

        def fake_run_solve(inp_path, work_dir, **kwargs):
            frd = work_dir / "solve.frd"
            dat = work_dir / "solve.dat"
            sta = work_dir / "solve.sta"
            frd.write_text("FRD RESULT", encoding="utf-8")
            dat.write_text("DAT RESULT", encoding="utf-8")
            sta.write_text("STEP 1 converged", encoding="utf-8")
            return {
                "frd_path": str(frd),
                "dat_path": str(dat),
                "sta_path": str(sta),
                "converged": True,
                "wall_time_s": 1.23,
                "returncode": 0,
                "ccx_version": "2.21",
                "fault_class": FaultClass.NONE,
                "failure_reason": None,
            }

        with patch("agents.solver.run_solve", side_effect=fake_run_solve):
            result = solver_run(solver_state)

        assert result["fault_class"] == FaultClass.NONE
        assert result["frd_path"] is not None
        assert any(path.endswith("solve.inp") for path in result["artifacts"])

    def test_classified_failure_retries_solver(self, solver_state):
        from agents.solver import run as solver_run

        with patch(
            "agents.solver.run_solve",
            return_value={
                "frd_path": None,
                "dat_path": None,
                "sta_path": None,
                "converged": False,
                "wall_time_s": 0.5,
                "returncode": 1,
                "ccx_version": "2.21",
                "fault_class": FaultClass.SOLVER_TIMESTEP,
                "failure_reason": "Time increment required is less than the minimum",
            },
        ):
            result = solver_run(solver_state)

        assert result["fault_class"] == FaultClass.SOLVER_TIMESTEP
        assert result["retry_budgets"] == {"solver": 1}
        assert result["history"][0]["fault_class"] == FaultClass.SOLVER_TIMESTEP.value

    def test_version_gate_failure_does_not_retry(self, solver_state):
        from agents.solver import run as solver_run

        with patch(
            "agents.solver.run_solve",
            side_effect=RuntimeError("CalculiX 2.20 is unsupported; AI-FEA requires >= 2.21."),
        ):
            result = solver_run(solver_state)

        assert result["fault_class"] == FaultClass.UNKNOWN
        assert "2.20" in result["history"][0]["msg"]

    def test_template_render_failure_is_solver_syntax(self, solver_state):
        from agents.solver import run as solver_run

        with patch(
            "agents.solver._render_inp_deck",
            side_effect=FileNotFoundError("Solver template not found"),
        ):
            result = solver_run(solver_state)

        assert result["fault_class"] == FaultClass.SOLVER_SYNTAX
        assert result["retry_budgets"] == {"solver": 1}

    def test_gate_solve_lint_short_circuits_before_ccx(self, solver_state, tmp_path):
        """Lint errors in the rendered deck must skip ccx invocation entirely."""
        from agents.solver import run as solver_run
        from tools.inp_linter import LintFinding, LintReport
        from schemas.sim_state import FaultClass as FC

        fake_report = LintReport(
            deck_path="fake",
            findings=[
                LintFinding(
                    severity="error",
                    code="E-TYPO-KEYWORD",
                    line=42,
                    message="*CLAOD is a common misspelling of *CLOAD.",
                    fault_class_hint=FC.SOLVER_SYNTAX,
                )
            ],
        )

        with (
            patch("agents.solver.lint_inp", return_value=fake_report),
            patch("agents.solver.run_solve") as mock_run_solve,
        ):
            result = solver_run(solver_state)

        # ccx MUST NOT have been called — this is the whole point of the gate.
        mock_run_solve.assert_not_called()
        assert result["fault_class"] == FaultClass.SOLVER_SYNTAX
        assert result["retry_budgets"] == {"solver": 1}
        assert result["verdict"] == "re-run"
        assert result["history"][0]["stage"] == "gate_solve_lint"
        assert result["history"][0]["lint_codes"] == ["E-TYPO-KEYWORD"]

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
