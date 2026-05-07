"""Tests for FM-04a P7 Tier 1 convergence sidecar writers.

Tier 1 engineering candidate. Not signed validation. Not benchmark agreement.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.parsers.frd_parser import FRDParser
from app.services import candidate_report_spine as spine_module
from app.services.ballistics import (
    ConvergenceRun,
    MeshConvergenceInput,
    TimeStepConvergenceInput,
    write_mesh_convergence,
    write_time_step_convergence,
)
from app.services.ballistics.convergence_writers import CLAIM_BOUNDARY_TIER1
from app.services.report_generator import ReportGenerator


REPO_ROOT = Path(__file__).resolve().parents[2]
GS001_FRD = REPO_ROOT / "golden_samples" / "GS-001" / "gs001_result.frd"


def test_mesh_convergence_writer_marks_stable_within_tolerance(tmp_path: Path) -> None:
    inp = MeshConvergenceInput(
        case_id="CASE-MESH-OK",
        metric="max_von_mises",
        runs=[
            ConvergenceRun("coarse", 0.0, 100.0),
            ConvergenceRun("medium", 1.0, 100.6),
            ConvergenceRun("fine", 2.0, 100.8),
        ],
        tolerance_pct=5.0,
    )
    out = write_mesh_convergence(inp, tmp_path)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert out.name == "mesh_convergence.json"
    assert payload["candidate_stability"] == "candidate_observed_stable"
    assert payload["parameter"] == "mesh_level"
    assert payload["metric"] == "max_von_mises"
    assert payload["claim_boundary"] == CLAIM_BOUNDARY_TIER1
    assert "Tier 1 candidate convergence evidence" in payload["claim_impact"]
    # |100.8 - 100.6| / 100.6 * 100 ≈ 0.1988
    assert abs(payload["relative_change_pct"] - 0.198807) < 1e-4


def test_mesh_convergence_writer_marks_unstable_above_tolerance(tmp_path: Path) -> None:
    inp = MeshConvergenceInput(
        case_id="CASE-MESH-UNSTABLE",
        metric="max_von_mises",
        runs=[
            ConvergenceRun("coarse", 0.0, 80.0),
            ConvergenceRun("medium", 1.0, 100.0),
        ],
        tolerance_pct=5.0,
    )
    out = write_mesh_convergence(inp, tmp_path)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["candidate_stability"] == "candidate_observed_unstable"
    # 25% change vs 5% tolerance
    assert payload["relative_change_pct"] == pytest.approx(25.0)


def test_time_step_convergence_writer_uses_dt_parameter_default(tmp_path: Path) -> None:
    inp = TimeStepConvergenceInput(
        case_id="CASE-DT-DEFAULT",
        metric="residual_velocity_candidate_m_per_s",
        runs=[
            ConvergenceRun("dt_baseline", 8.0e-9, 142.0),
            ConvergenceRun("dt_half", 4.0e-9, 141.0),
            ConvergenceRun("dt_quarter", 2.0e-9, 140.5),
        ],
        tolerance_pct=5.0,
    )
    out = write_time_step_convergence(inp, tmp_path)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert out.name == "time_step_convergence.json"
    assert payload["parameter"] == "time_step_dt"
    assert payload["candidate_stability"] == "candidate_observed_stable"


def test_writer_marks_unknown_when_only_one_run(tmp_path: Path) -> None:
    inp = MeshConvergenceInput(
        case_id="CASE-ONLY-ONE",
        metric="max_plastic_strain",
        runs=[ConvergenceRun("baseline", 0.0, 0.42)],
        tolerance_pct=5.0,
    )
    payload = json.loads(write_mesh_convergence(inp, tmp_path).read_text(encoding="utf-8"))
    assert payload["candidate_stability"] == "unknown"
    assert payload["relative_change_pct"] is None


def test_writer_handles_zero_baseline_safely(tmp_path: Path) -> None:
    inp = MeshConvergenceInput(
        case_id="CASE-ZERO-BASELINE",
        metric="hourglass_energy_j",
        runs=[
            ConvergenceRun("a", 0.0, 0.0),
            ConvergenceRun("b", 1.0, 0.4),
        ],
        tolerance_pct=5.0,
    )
    payload = json.loads(write_mesh_convergence(inp, tmp_path).read_text(encoding="utf-8"))
    assert payload["candidate_stability"] == "unknown"
    assert payload["relative_change_pct"] is None


def test_writer_rejects_zero_tolerance(tmp_path: Path) -> None:
    inp = MeshConvergenceInput(
        case_id="CASE-BAD-TOL",
        metric="x",
        runs=[ConvergenceRun("a", 0.0, 1.0), ConvergenceRun("b", 1.0, 1.05)],
        tolerance_pct=0.0,
    )
    with pytest.raises(ValueError, match="tolerance_pct"):
        write_mesh_convergence(inp, tmp_path)


def test_writer_rejects_empty_runs(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="at least one run"):
        write_mesh_convergence(
            MeshConvergenceInput(
                case_id="CASE-EMPTY", metric="x", runs=[], tolerance_pct=5.0
            ),
            tmp_path,
        )


def test_writer_carries_extra_run_fields(tmp_path: Path) -> None:
    inp = MeshConvergenceInput(
        case_id="CASE-EXTRA",
        metric="max_disp_m",
        runs=[
            ConvergenceRun("coarse", 0.0, 1.0e-3, extra={"element_count": 1000}),
            ConvergenceRun("fine", 2.0, 1.02e-3, extra={"element_count": 4000}),
        ],
        tolerance_pct=5.0,
        notes="cited from test fixture; not benchmark agreement",
    )
    payload = json.loads(write_mesh_convergence(inp, tmp_path).read_text(encoding="utf-8"))
    assert payload["runs"][0]["element_count"] == 1000
    assert payload["runs"][1]["element_count"] == 4000
    assert payload["notes"].startswith("cited from test fixture")


def test_written_sidecar_is_consumable_by_spine(tmp_path: Path, monkeypatch) -> None:
    """End-to-end: writer writes sidecar; spine consumes it; ballistic study populated."""
    if not GS001_FRD.exists():
        pytest.skip(f"GS-001 FRD fixture missing at {GS001_FRD}")

    monkeypatch.setattr(spine_module, "REPO_ROOT", tmp_path)
    case_id = "CASE-DT-WRITER-E2E"
    case_dir = tmp_path / "golden_samples" / case_id
    case_dir.mkdir(parents=True)
    (case_dir / "expected_results.json").write_text(
        json.dumps(
            {
                "case_id": case_id,
                "case_name": "Writer end-to-end fixture",
                "status": "insufficient_evidence",
                "status_reason": "Tier 1 candidate; benchmark agreement deferred",
                "failure_pattern_ref": "FP-TEST-WRITER",
                "ballistic": {"projectile_initial_velocity_m_per_s": 285.0},
            }
        ),
        encoding="utf-8",
    )
    (case_dir / "model.inp").write_text(
        "*NODE\n1,0,0,0\n*ELEMENT, TYPE=C3D4\n1,1,1,1,1\n", encoding="utf-8"
    )

    runtime_ballistic_dir = (
        tmp_path / "project_state" / "graph_executor" / case_id / "ballistic"
    )
    write_time_step_convergence(
        TimeStepConvergenceInput(
            case_id=case_id,
            metric="residual_velocity_candidate_m_per_s",
            runs=[
                ConvergenceRun("dt_baseline", 8.0e-9, 142.0),
                ConvergenceRun("dt_half", 4.0e-9, 141.0),
                ConvergenceRun("dt_quarter", 2.0e-9, 140.5),
            ],
            tolerance_pct=5.0,
        ),
        runtime_ballistic_dir,
    )

    parsed = FRDParser().parse(str(GS001_FRD))
    report = ReportGenerator(case_dir.parent).generate(
        parsed,
        case_id=case_id,
        source_path=GS001_FRD,
        original_filename="gs001_result.frd",
    )

    study = report.candidate_report_spine["ballistic"]["time_step_convergence_study"]
    assert study["status"] == "available"
    assert study["candidate_stability"] == "candidate_observed_stable"
    assert study["run_count"] == 3
