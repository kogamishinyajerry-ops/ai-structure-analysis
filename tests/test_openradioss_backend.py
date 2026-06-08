"""Tests for the AERON OpenRadioss FEABackend adapter (FM-04a P4).

Tier 1 engineering candidate. Not signed validation. Not benchmark agreement.

These tests exercise the adapter without invoking real OpenRadioss binaries:

* dry-run path returns a Tier 1 candidate stub outcome.
* prepare_case enforces solver=openradioss + deck preconditions.
* parse_results passes raw output paths through and re-affirms the
  Tier 1 claim boundary in extras.
* health_check returns ``healthy=False`` when binaries are missing on
  the test environment (the development workstation does not have
  OpenRadioss installed).
* an injected ``run_solve`` callable is honoured so callers can mock
  the solver without monkeypatching ``subprocess``.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from aeron.drivers import (
    BALLISTIC_CANDIDATE_CLAIM_BOUNDARY,
    BALLISTIC_CANDIDATE_TIER,
    OpenRadiossFEABackend,
)
from aeron.protocols import SolveOptions, SolveStatusCode
from schemas.sim_plan import (
    GeometrySpec,
    SimPlan,
    SolverBackend,
    SolverControls,
)


def _make_plan(
    case_id: str = "AI-FEA-P0-99", solver: SolverBackend = SolverBackend.OPENRADIOSS
) -> SimPlan:
    return SimPlan(
        case_id=case_id,
        geometry=GeometrySpec(kind="naca", parameters={"profile": "NACA0012"}),
        solver=SolverControls(name=solver, nonlinear=True, max_increments=10000),
    )


def _seed_decks(tmp_path: Path) -> tuple[Path, Path]:
    starter = tmp_path / "decks" / "model_00_0000.rad"
    engine = tmp_path / "decks" / "model_00_0001.rad"
    starter.parent.mkdir(parents=True, exist_ok=True)
    starter.write_text(
        "# Tier 1 candidate starter deck stub; not signed validation.\n",
        encoding="utf-8",
    )
    engine.write_text(
        "# Tier 1 candidate engine deck stub; not signed validation.\n",
        encoding="utf-8",
    )
    return starter, engine


def test_prepare_case_rejects_non_openradioss_solver(tmp_path: Path) -> None:
    starter, engine = _seed_decks(tmp_path)
    backend = OpenRadiossFEABackend(
        work_root=tmp_path / "work", starter_deck=starter, engine_deck=engine
    )
    plan = _make_plan(solver=SolverBackend.CALCULIX)

    with pytest.raises(ValueError, match="solver.name='openradioss'"):
        backend.prepare_case(plan)


def test_prepare_case_rejects_missing_starter(tmp_path: Path) -> None:
    starter = tmp_path / "decks" / "missing_starter.rad"
    engine = tmp_path / "decks" / "engine.rad"
    engine.parent.mkdir(parents=True, exist_ok=True)
    engine.write_text("# engine deck", encoding="utf-8")

    backend = OpenRadiossFEABackend(
        work_root=tmp_path / "work", starter_deck=starter, engine_deck=engine
    )
    with pytest.raises(FileNotFoundError, match="starter_deck does not exist"):
        backend.prepare_case(_make_plan())


def test_prepare_case_rejects_missing_engine(tmp_path: Path) -> None:
    starter = tmp_path / "decks" / "starter.rad"
    engine = tmp_path / "decks" / "missing_engine.rad"
    starter.parent.mkdir(parents=True, exist_ok=True)
    starter.write_text("# starter deck", encoding="utf-8")

    backend = OpenRadiossFEABackend(
        work_root=tmp_path / "work", starter_deck=starter, engine_deck=engine
    )
    with pytest.raises(FileNotFoundError, match="engine_deck does not exist"):
        backend.prepare_case(_make_plan())


def test_prepare_case_copies_decks_and_marks_tier1_metadata(tmp_path: Path) -> None:
    starter, engine = _seed_decks(tmp_path)
    backend = OpenRadiossFEABackend(
        work_root=tmp_path / "work",
        starter_deck=starter,
        engine_deck=engine,
        case_dir_name="solver",
    )
    case = backend.prepare_case(_make_plan())

    assert case.case_dir == tmp_path / "work" / "solver"
    assert case.primary_input.exists()
    assert case.primary_input.name == "model_00_0000.rad"
    assert (case.case_dir / "model_00_0001.rad").exists()
    assert case.metadata["backend"] == "openradioss"
    assert case.metadata["claim_tier"] == BALLISTIC_CANDIDATE_TIER
    assert case.metadata["claim_boundary"] == BALLISTIC_CANDIDATE_CLAIM_BOUNDARY
    assert "Børvik 2002" in case.metadata["deck_discipline"]
    # source paths are preserved for traceability
    assert case.metadata["starter_deck_source"] == str(starter)
    assert case.metadata["engine_deck_source"] == str(engine)


def test_solve_dry_run_returns_tier1_stub(tmp_path: Path) -> None:
    starter, engine = _seed_decks(tmp_path)
    backend = OpenRadiossFEABackend(
        work_root=tmp_path / "work", starter_deck=starter, engine_deck=engine
    )
    case = backend.prepare_case(_make_plan())
    outcome = backend.solve(case, SolveOptions(dry_run=True))

    assert outcome.status.code is SolveStatusCode.OK
    assert outcome.status.returncode == 0
    assert outcome.metadata["dry_run"] is True
    assert outcome.metadata["claim_tier"] == BALLISTIC_CANDIDATE_TIER
    assert outcome.metadata["claim_boundary"] == BALLISTIC_CANDIDATE_CLAIM_BOUNDARY
    assert outcome.metadata["backend"] == "openradioss"


def test_solve_without_binaries_returns_preflight_failure(tmp_path: Path, monkeypatch) -> None:
    starter, engine = _seed_decks(tmp_path)
    # Force ``shutil.which`` to return None for every candidate name.
    monkeypatch.setattr(shutil, "which", lambda name: None)
    backend = OpenRadiossFEABackend(
        work_root=tmp_path / "work", starter_deck=starter, engine_deck=engine
    )
    case = backend.prepare_case(_make_plan())

    outcome = backend.solve(case, SolveOptions(dry_run=False))

    assert outcome.status.code is SolveStatusCode.PREFLIGHT_FAILED
    assert "OpenRadioss binaries missing on PATH" in outcome.status.message
    assert "starter" in outcome.metadata["preflight_missing"]
    assert "engine" in outcome.metadata["preflight_missing"]
    assert outcome.metadata["claim_tier"] == BALLISTIC_CANDIDATE_TIER


def test_solve_with_injected_run_solve_callable(tmp_path: Path) -> None:
    starter, engine = _seed_decks(tmp_path)

    captured: dict[str, object] = {}

    def fake_run_solve(*, starter_deck: Path, engine_deck: Path, case_dir: Path, timeout_s: int):
        captured["starter_deck"] = starter_deck
        captured["engine_deck"] = engine_deck
        captured["case_dir"] = case_dir
        captured["timeout_s"] = timeout_s
        # produce one "raw" output file so parse_results can pass it through
        anim = case_dir / "model_00_0001.anim"
        anim.write_text("dummy", encoding="utf-8")
        return {
            "converged": True,
            "wall_time_s": 4.5,
            "openradioss_version": "stub-2026.1",
            "anim_path": anim,
        }

    backend = OpenRadiossFEABackend(
        work_root=tmp_path / "work",
        starter_deck=starter,
        engine_deck=engine,
        run_solve=fake_run_solve,
    )
    case = backend.prepare_case(_make_plan())

    outcome = backend.solve(case, SolveOptions(dry_run=False, timeout_s=99.0))

    assert outcome.status.code is SolveStatusCode.OK
    assert outcome.metadata["openradioss_version"] == "stub-2026.1"
    assert outcome.metadata["claim_tier"] == BALLISTIC_CANDIDATE_TIER
    assert outcome.metadata["claim_boundary"] == BALLISTIC_CANDIDATE_CLAIM_BOUNDARY
    assert outcome.wall_clock_s == 4.5
    assert "anim" in outcome.raw_outputs
    assert outcome.raw_outputs["anim"].name == "model_00_0001.anim"
    # injected callable received the right inputs
    assert captured["timeout_s"] == 99
    assert captured["starter_deck"].name == "model_00_0000.rad"


def test_solve_with_injected_run_solve_failure_marks_solver_error(tmp_path: Path) -> None:
    starter, engine = _seed_decks(tmp_path)

    def failing_run_solve(*, starter_deck, engine_deck, case_dir, timeout_s):
        return {
            "converged": False,
            "wall_time_s": 1.0,
            "failure_reason": "Tier 1 candidate divergence (synthetic)",
            "returncode": 7,
        }

    backend = OpenRadiossFEABackend(
        work_root=tmp_path / "work",
        starter_deck=starter,
        engine_deck=engine,
        run_solve=failing_run_solve,
    )
    case = backend.prepare_case(_make_plan())
    outcome = backend.solve(case, SolveOptions(dry_run=False))

    assert outcome.status.code is SolveStatusCode.SOLVER_ERROR
    assert outcome.status.returncode == 7
    assert "synthetic" in outcome.status.message


def test_parse_results_passes_paths_and_reaffirms_claim_boundary(tmp_path: Path) -> None:
    starter, engine = _seed_decks(tmp_path)
    backend = OpenRadiossFEABackend(
        work_root=tmp_path / "work", starter_deck=starter, engine_deck=engine
    )
    case = backend.prepare_case(_make_plan())
    outcome = backend.solve(case, SolveOptions(dry_run=True))
    bundle = backend.parse_results(outcome)

    assert bundle.case_id == case.case_id
    assert bundle.scalars == {}
    assert bundle.extras["status_code"] == SolveStatusCode.OK.value
    assert bundle.extras["claim_tier"] == BALLISTIC_CANDIDATE_TIER
    assert bundle.extras["claim_boundary"] == BALLISTIC_CANDIDATE_CLAIM_BOUNDARY
    assert "residual velocity" in bundle.extras["extraction_note"]
    # raw outputs from a dry-run are empty (solver was not invoked)
    assert bundle.fields == {}


def test_health_check_reports_missing_binaries(tmp_path: Path, monkeypatch) -> None:
    starter, engine = _seed_decks(tmp_path)
    monkeypatch.setattr(shutil, "which", lambda name: None)
    backend = OpenRadiossFEABackend(
        work_root=tmp_path / "work", starter_deck=starter, engine_deck=engine
    )

    report = backend.health_check()

    assert report.status.healthy is False
    assert report.status.solver_name == "openradioss"
    assert report.checks == {"starter_on_path": False, "engine_on_path": False}
    assert "missing on PATH" in report.status.detail


def test_health_check_reports_healthy_when_binaries_present(tmp_path: Path, monkeypatch) -> None:
    starter, engine = _seed_decks(tmp_path)

    def fake_which(name: str) -> str | None:
        if "starter" in name:
            return "/usr/local/bin/starter_linux64_gf"
        if "engine" in name:
            return "/usr/local/bin/engine_linux64_gf"
        return None

    monkeypatch.setattr(shutil, "which", fake_which)
    backend = OpenRadiossFEABackend(
        work_root=tmp_path / "work", starter_deck=starter, engine_deck=engine
    )

    report = backend.health_check()
    assert report.status.healthy is True
    assert report.checks == {"starter_on_path": True, "engine_on_path": True}
    assert "Tier 1 candidate path" in report.status.detail


def test_solver_backend_enum_includes_openradioss() -> None:
    assert SolverBackend.OPENRADIOSS.value == "openradioss"
