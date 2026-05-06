"""Tests for the AERON CalculiX FEABackend adapter."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from aeron.drivers import CalculiXFEABackend
from aeron.protocols import FEABackend, SolveOptions, SolveStatusCode
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
        case_id="AI-FEA-P0-35",
        analysis_type=AnalysisType.STATIC,
        description="AERON CalculiX backend test",
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
def mesh_input(tmp_path: Path) -> Path:
    mesh = tmp_path / "model.inp"
    mesh.write_text("*NODE\n1, 0, 0, 0\n*ELEMENT\n1, 1\n", encoding="utf-8")
    return mesh


def test_calculix_backend_structurally_satisfies_protocol(tmp_path: Path, mesh_input: Path) -> None:
    backend = CalculiXFEABackend(work_root=tmp_path / "work", mesh_input=mesh_input)

    assert isinstance(backend, FEABackend)


def test_prepare_case_renders_solver_deck(
    sample_plan: SimPlan, tmp_path: Path, mesh_input: Path
) -> None:
    backend = CalculiXFEABackend(work_root=tmp_path / "work", mesh_input=mesh_input)

    case = backend.prepare_case(sample_plan)

    assert case.case_id == sample_plan.case_id
    assert case.case_dir == tmp_path / "work" / sample_plan.case_id
    assert case.primary_input == case.case_dir / "solve.inp"
    assert case.artifacts["mesh_input"] == case.case_dir / "model.inp"
    assert case.metadata["backend"] == "calculix"
    content = case.primary_input.read_text(encoding="utf-8")
    assert "Aluminium" in content
    assert "model.inp" in content
    assert "Ntip" in content
    assert "Nroot" in content


def test_prepare_case_requires_explicit_mesh(sample_plan: SimPlan, tmp_path: Path) -> None:
    backend = CalculiXFEABackend(
        work_root=tmp_path / "work",
        mesh_input=tmp_path / "missing.inp",
    )

    with pytest.raises(FileNotFoundError, match="mesh_input does not exist"):
        backend.prepare_case(sample_plan)


def test_dry_run_solve_does_not_invoke_calculix(
    sample_plan: SimPlan, tmp_path: Path, mesh_input: Path
) -> None:
    run_solve = Mock()
    backend = CalculiXFEABackend(
        work_root=tmp_path / "work",
        mesh_input=mesh_input,
        run_solve=run_solve,
    )
    case = backend.prepare_case(sample_plan)

    outcome = backend.solve(case, SolveOptions(dry_run=True))

    run_solve.assert_not_called()
    assert outcome.status.code is SolveStatusCode.OK
    assert outcome.status.returncode == 0
    assert outcome.metadata["dry_run"] is True
    assert outcome.raw_outputs == {}


def test_solve_maps_successful_driver_result(
    sample_plan: SimPlan, tmp_path: Path, mesh_input: Path
) -> None:
    backend = CalculiXFEABackend(
        work_root=tmp_path / "work",
        mesh_input=mesh_input,
        run_solve=lambda inp_path, work_dir, **kwargs: {
            "frd_path": str(work_dir / "solve.frd"),
            "dat_path": str(work_dir / "solve.dat"),
            "sta_path": str(work_dir / "solve.sta"),
            "converged": True,
            "wall_time_s": 1.23,
            "returncode": 0,
            "ccx_version": "2.21",
            "fault_class": FaultClass.NONE,
            "failure_reason": None,
        },
    )
    case = backend.prepare_case(sample_plan)

    outcome = backend.solve(case, SolveOptions())

    assert outcome.status.code is SolveStatusCode.OK
    assert outcome.status.fault_class is None
    assert outcome.status.returncode == 0
    assert outcome.wall_clock_s == 1.23
    assert outcome.raw_outputs["frd"] == case.case_dir / "solve.frd"
    assert outcome.metadata["ccx_version"] == "2.21"


def test_solve_maps_driver_failure(sample_plan: SimPlan, tmp_path: Path, mesh_input: Path) -> None:
    backend = CalculiXFEABackend(
        work_root=tmp_path / "work",
        mesh_input=mesh_input,
        run_solve=lambda inp_path, work_dir, **kwargs: {
            "frd_path": None,
            "dat_path": str(work_dir / "solve.dat"),
            "sta_path": str(work_dir / "solve.sta"),
            "converged": False,
            "wall_time_s": 0.5,
            "returncode": 1,
            "ccx_version": "2.21",
            "fault_class": FaultClass.SOLVER_CONVERGENCE,
            "failure_reason": "no convergence",
        },
    )
    case = backend.prepare_case(sample_plan)

    outcome = backend.solve(case, SolveOptions())

    assert outcome.status.code is SolveStatusCode.DIVERGED
    assert outcome.status.fault_class is FaultClass.SOLVER_CONVERGENCE
    assert outcome.status.message == "no convergence"
    assert outcome.raw_outputs["dat"] == case.case_dir / "solve.dat"


def test_solve_maps_preflight_exception(
    sample_plan: SimPlan, tmp_path: Path, mesh_input: Path
) -> None:
    def fail_preflight(*args: object, **kwargs: object) -> dict[str, object]:
        raise FileNotFoundError("ccx not found")

    backend = CalculiXFEABackend(
        work_root=tmp_path / "work",
        mesh_input=mesh_input,
        run_solve=fail_preflight,
    )
    case = backend.prepare_case(sample_plan)

    outcome = backend.solve(case, SolveOptions())

    assert outcome.status.code is SolveStatusCode.PREFLIGHT_FAILED
    assert outcome.status.fault_class is FaultClass.UNKNOWN
    assert outcome.status.message == "ccx not found"
    assert outcome.raw_outputs == {}


def test_parse_results_exposes_raw_outputs_without_derivation(
    sample_plan: SimPlan, tmp_path: Path, mesh_input: Path
) -> None:
    backend = CalculiXFEABackend(
        work_root=tmp_path / "work",
        mesh_input=mesh_input,
        run_solve=lambda inp_path, work_dir, **kwargs: {
            "frd_path": str(work_dir / "solve.frd"),
            "dat_path": str(work_dir / "solve.dat"),
            "sta_path": str(work_dir / "solve.sta"),
            "converged": True,
            "wall_time_s": 1.23,
            "returncode": 0,
            "ccx_version": "2.21",
            "fault_class": FaultClass.NONE,
            "failure_reason": None,
        },
    )
    case = backend.prepare_case(sample_plan)
    outcome = backend.solve(case, SolveOptions())

    bundle = backend.parse_results(outcome)

    assert bundle.case_id == sample_plan.case_id
    assert bundle.fields == outcome.raw_outputs
    assert bundle.scalars == {}
    assert bundle.extras["status_code"] == "ok"
    assert bundle.extras["metadata"]["backend"] == "calculix"


def test_health_check_reports_missing_ccx(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import aeron.drivers.calculix_backend as module

    monkeypatch.setattr(module.calculix_driver, "_find_ccx", lambda: None)
    backend = CalculiXFEABackend(work_root=tmp_path / "work", mesh_input=tmp_path / "mesh.inp")

    report = backend.health_check()

    assert report.status.healthy is False
    assert report.status.solver_name == "calculix"
    assert report.checks == {"ccx_on_path": False, "version_readable": False}
