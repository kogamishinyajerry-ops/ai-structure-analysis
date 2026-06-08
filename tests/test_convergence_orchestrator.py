"""Tests for the Tier 1 convergence study orchestrator (FM-04a Phase 2 B).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.services.ballistics.convergence_orchestrator import (
    VERDICT_INSUFFICIENT,
    VERDICT_STABLE,
    VERDICT_UNSTABLE,
    ConvergenceStudyInput,
    ConvergenceStudyRow,
    build_convergence_study,
    write_convergence_study,
)


def _row(
    mesh_label: str,
    mesh_axis_value: float,
    dt_label: str,
    dt_axis_value: float,
    residual: float,
    *,
    balance_error_pct: float | None = None,
) -> ConvergenceStudyRow:
    return ConvergenceStudyRow(
        mesh_label=mesh_label,
        mesh_axis_value=mesh_axis_value,
        dt_label=dt_label,
        dt_axis_value=dt_axis_value,
        residual_velocity_m_per_s=residual,
        energy_balance_error_pct=balance_error_pct,
        source_metrics_path=f"project_state/graph_executor/{mesh_label}-{dt_label}/ballistic/ballistic_metrics.json",
    )


def _input(rows: list[ConvergenceStudyRow], *, tolerance_pct: float = 5.0) -> ConvergenceStudyInput:
    return ConvergenceStudyInput(
        case_id="GS-102-phase2-orchestrator",
        rows=rows,
        tolerance_pct=tolerance_pct,
    )


def test_stable_verdict_when_both_sweeps_converge_within_tolerance() -> None:
    rows = [
        _row("coarse", 1.0, "dt_a", 1.0e-7, 350.0, balance_error_pct=12.0),
        _row("medium", 2.0, "dt_a", 1.0e-7, 358.0, balance_error_pct=10.0),
        _row("fine", 3.0, "dt_a", 1.0e-7, 360.0, balance_error_pct=9.0),  # 0.56% change vs medium
        _row("medium", 2.0, "dt_b", 5.0e-8, 359.0, balance_error_pct=8.0),  # 0.28% vs dt_a@medium
    ]
    payload = build_convergence_study(_input(rows))
    assert payload["combined_verdict"] == VERDICT_STABLE
    assert payload["mesh_sweep"]["candidate_stability"] == VERDICT_STABLE
    assert payload["dt_sweep"]["candidate_stability"] == VERDICT_STABLE
    assert payload["row_count"] == 4


def test_unstable_verdict_when_mesh_sweep_crosses_tolerance() -> None:
    rows = [
        _row("coarse", 1.0, "dt_a", 1.0e-7, 200.0),
        _row("medium", 2.0, "dt_a", 1.0e-7, 300.0),
        _row("fine", 3.0, "dt_a", 1.0e-7, 360.0),  # 20% change vs medium
        _row("medium", 2.0, "dt_b", 5.0e-8, 302.0),  # 0.67% on dt sweep
    ]
    payload = build_convergence_study(_input(rows))
    assert payload["combined_verdict"] == VERDICT_UNSTABLE
    assert payload["mesh_sweep"]["candidate_stability"] == VERDICT_UNSTABLE
    assert payload["dt_sweep"]["candidate_stability"] == VERDICT_STABLE


def test_unstable_verdict_when_dt_sweep_crosses_tolerance() -> None:
    rows = [
        _row("medium", 2.0, "dt_a", 1.0e-7, 350.0),
        _row("fine", 3.0, "dt_a", 1.0e-7, 358.0),  # 2.3% mesh sweep
        _row("medium", 2.0, "dt_b", 5.0e-8, 410.0),  # ~17% dt sweep
    ]
    payload = build_convergence_study(_input(rows))
    assert payload["combined_verdict"] == VERDICT_UNSTABLE
    assert payload["mesh_sweep"]["candidate_stability"] == VERDICT_STABLE
    assert payload["dt_sweep"]["candidate_stability"] == VERDICT_UNSTABLE


def test_insufficient_data_when_either_sweep_has_under_two_rows() -> None:
    rows = [
        _row("medium", 2.0, "dt_a", 1.0e-7, 350.0),
        _row("fine", 3.0, "dt_a", 1.0e-7, 358.0),  # mesh sweep has 2 rows → stable
        # dt sweep at the most-common mesh level "medium" (or "fine"): only 1 row each → unknown
    ]
    payload = build_convergence_study(_input(rows))
    assert payload["combined_verdict"] == VERDICT_INSUFFICIENT
    assert payload["dt_sweep"]["candidate_stability"] == "unknown"


def test_insufficient_data_when_single_row_total() -> None:
    rows = [_row("medium", 2.0, "dt_a", 1.0e-7, 350.0)]
    payload = build_convergence_study(_input(rows))
    assert payload["combined_verdict"] == VERDICT_INSUFFICIENT
    assert payload["mesh_sweep"]["run_count"] == 1
    assert payload["dt_sweep"]["run_count"] == 1


def test_empty_input_rejected() -> None:
    with pytest.raises(ValueError, match="at least one row"):
        build_convergence_study(_input([]))


def test_zero_or_negative_tolerance_rejected() -> None:
    with pytest.raises(ValueError, match="tolerance_pct must be > 0"):
        build_convergence_study(_input([_row("m", 1.0, "d", 1.0e-7, 100.0)], tolerance_pct=0.0))


def test_energy_balance_summary_reports_aggregate_when_present() -> None:
    rows = [
        _row("coarse", 1.0, "dt_a", 1.0e-7, 350.0, balance_error_pct=12.0),
        _row("medium", 2.0, "dt_a", 1.0e-7, 360.0, balance_error_pct=10.0),
        _row("fine", 3.0, "dt_a", 1.0e-7, 365.0, balance_error_pct=8.0),
    ]
    payload = build_convergence_study(_input(rows))
    summary = payload["energy_balance_observation"]
    assert summary["status"] == "candidate_observed"
    assert summary["rows_with_balance_error"] == 3
    assert summary["min_pct"] == pytest.approx(8.0)
    assert summary["max_pct"] == pytest.approx(12.0)
    assert summary["mean_pct"] == pytest.approx(10.0)


def test_energy_balance_summary_reports_unavailable_when_absent() -> None:
    rows = [
        _row("coarse", 1.0, "dt_a", 1.0e-7, 350.0),
        _row("medium", 2.0, "dt_a", 1.0e-7, 360.0),
    ]
    payload = build_convergence_study(_input(rows))
    summary = payload["energy_balance_observation"]
    assert summary["status"] == "unavailable"
    assert summary["rows_total"] == 2


def test_payload_carries_tier1_claim_boundary_and_no_overclaim() -> None:
    rows = [
        _row("coarse", 1.0, "dt_a", 1.0e-7, 350.0),
        _row("medium", 2.0, "dt_a", 1.0e-7, 358.0),
        _row("medium", 2.0, "dt_b", 5.0e-8, 359.0),
    ]
    payload = build_convergence_study(_input(rows))
    boundary = payload["claim_boundary"].lower()
    impact = payload["claim_impact"].lower()
    assert "tier1_engineering_candidate" in boundary
    assert "not_signed_validation" in boundary
    assert "not_benchmark_agreement" in boundary
    for positive_claim in (
        "validated against",
        "perforation completed",
        "bullet-through-steel complete",
        "validated physics",
    ):
        assert positive_claim not in impact
    # The 'not signed validation' / 'not benchmark agreement' disclaimers are
    # expected; strip them and verify no leftover positive claim.
    stripped = impact.replace("not signed validation", "").replace("not benchmark agreement", "")
    assert "signed validation" not in stripped
    assert "benchmark agreement" not in stripped


def test_writer_refuses_output_under_golden_samples(tmp_path: Path) -> None:
    fake_golden = tmp_path / "golden_samples" / "GS-102-some-candidate" / "convergence"
    rows = [_row("c", 1.0, "d", 1.0e-7, 100.0), _row("m", 2.0, "d", 1.0e-7, 101.0)]
    with pytest.raises(ValueError, match="golden_samples"):
        write_convergence_study(_input(rows), fake_golden)


def test_writer_writes_under_project_state_path(tmp_path: Path) -> None:
    out_dir = tmp_path / "project_state" / "graph_executor" / "GS-102-x" / "convergence"
    rows = [
        _row("coarse", 1.0, "dt_a", 1.0e-7, 350.0),
        _row("medium", 2.0, "dt_a", 1.0e-7, 360.0),
        _row("medium", 2.0, "dt_b", 5.0e-8, 361.0),
    ]
    path = write_convergence_study(_input(rows), out_dir)
    assert path.is_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["case_id"] == "GS-102-phase2-orchestrator"
    assert data["combined_verdict"] in (VERDICT_STABLE, VERDICT_UNSTABLE)
    assert data["row_count"] == 3


def test_most_common_dt_and_mesh_selection_is_deterministic() -> None:
    """When two dt values appear with equal count, pick the smaller dt
    (most refined) for the mesh-sweep group. Symmetric for dt sweep."""
    rows = [
        _row("coarse", 1.0, "dt_a", 1.0e-7, 350.0),
        _row("medium", 2.0, "dt_a", 1.0e-7, 360.0),
        _row("coarse", 1.0, "dt_b", 5.0e-8, 320.0),
        _row("medium", 2.0, "dt_b", 5.0e-8, 330.0),
    ]
    payload = build_convergence_study(_input(rows))
    # Both dt values have count=2 → tie-breaker picks smaller float
    # (most refined dt) = 5e-8
    assert payload["mesh_sweep"]["held_dt_axis_value"] == pytest.approx(5.0e-8)
    # Both mesh values have count=2 → tie-breaker picks smaller (mesh level 1)
    assert payload["dt_sweep"]["held_mesh_axis_value"] == pytest.approx(1.0)


def test_payload_preserves_per_row_source_metrics_path() -> None:
    rows = [
        _row("coarse", 1.0, "dt_a", 1.0e-7, 350.0),
        _row("medium", 2.0, "dt_a", 1.0e-7, 358.0),
    ]
    payload = build_convergence_study(_input(rows))
    paths = [r["source_metrics_path"] for r in payload["rows"]]
    assert all("project_state/graph_executor" in p for p in paths)
    assert all("ballistic_metrics.json" in p for p in paths)
