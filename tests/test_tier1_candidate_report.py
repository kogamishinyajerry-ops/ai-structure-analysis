"""Tests for the Tier 1 candidate report builder (FM-04a Phase 2 E).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.services.reporting.tier1_candidate_report import (
    CLAIM_BOUNDARY,
    CLAIM_TIER,
    TIER1_BANNER,
    Tier1CandidateReport,
    Tier1CandidateReportInputs,
    build_tier1_candidate_report,
    render_tier1_report_docx_bytes,
    render_tier1_report_markdown,
    write_tier1_report_artifacts,
)


def _write_minimal_metrics(tmp_path: Path) -> Path:
    payload = {
        "case_id": "GS-102-phase2-e",
        "claim_boundary": CLAIM_BOUNDARY,
        "perforation_marker": "perforated_candidate",
        "projectile_initial_velocity_m_per_s": 830.0,
        "residual_velocity_candidate_m_per_s": 74.5,
        "extraction_metadata": {
            "impact_axis": "x",
            "plate_back_face_axis_value_m": 0.042,
            "plate_thickness_m": 0.012,
            "projectile_mass_kg": 0.005024,
            "claim_impact": "Tier 1 candidate inputs only",
        },
        "crossing_evidence": {
            "status": "candidate_observed",
            "front_face_crossed": True,
            "back_face_crossed": True,
            "first_back_face_crossing_t_s": 3.27e-5,
        },
        "energy_audit": {
            "status": "closed_aggregate",
            "initial_kinetic_energy_j": 1731.0,
            "residual_kinetic_energy_j": 575.5,
            "plastic_dissipation_j": None,
            "contact_friction_j": None,
            "hourglass_energy_j": None,
            "aggregate_internal_energy_j": 826.6,
            "external_work_j": 0.0,
            "energy_balance_error_pct": 19.0,
            "breakdown_status": "aggregated_into_internal_energy",
            "missing_terms": [
                "plastic_dissipation_j",
                "contact_friction_j",
                "hourglass_energy_j",
            ],
            "unit_system_note": "OpenRadioss deck unit system (kg/mm/ms)",
            "claim_impact": "Tier 1 closed aggregate energy audit",
        },
        "solver_evidence": {
            "status": "candidate_observed",
            "starter_error_count": 0,
            "starter_warning_count": 6,
            "engine_normal_termination": True,
            "engine_cycle_count": 14645,
            "animation_frame_count": 240,
            "live_solid_count": 68,
            "total_solid_count": 80,
            "deleted_element_count": 12,
            "claim_impact": "Tier 1 solver evidence only; not signed validation",
        },
    }
    metrics_path = tmp_path / "ballistic_metrics.json"
    metrics_path.write_text(json.dumps(payload), encoding="utf-8")
    return metrics_path


def _write_minimal_convergence(tmp_path: Path) -> Path:
    payload = {
        "case_id": "GS-102-phase2-e",
        "study_metric": "residual_velocity_m_per_s",
        "tolerance_pct": 5.0,
        "combined_verdict": "candidate_observed_unstable",
        "mesh_sweep": {
            "candidate_stability": "unknown",
            "run_count": 1,
            "relative_change_pct": None,
        },
        "dt_sweep": {
            "candidate_stability": "candidate_observed_unstable",
            "run_count": 4,
            "relative_change_pct": 56.24,
        },
        "row_count": 4,
        "claim_impact": (
            "Tier 1 candidate mesh and time-step convergence study only; not "
            "signed validation; not benchmark agreement"
        ),
        "claim_boundary": CLAIM_BOUNDARY,
    }
    out = tmp_path / "convergence_study.json"
    out.write_text(json.dumps(payload), encoding="utf-8")
    return out


def test_builder_assembles_all_sections_from_minimal_metrics(tmp_path: Path) -> None:
    metrics = _write_minimal_metrics(tmp_path)
    convergence = _write_minimal_convergence(tmp_path)
    report = build_tier1_candidate_report(
        Tier1CandidateReportInputs(
            case_id="GS-102-phase2-e",
            ballistic_metrics_path=metrics,
            convergence_study_path=convergence,
            starter_deck_relpath="golden_samples/GS-102-candidate/data/model_00_0000.rad",
            engine_deck_relpath="golden_samples/GS-102-candidate/data/model_00_0001.rad",
            generator_script_relpath="scripts/gen_gs102_refined_deck.py",
            repo_root=tmp_path,
        )
    )
    assert isinstance(report, Tier1CandidateReport)
    assert report.case_id == "GS-102-phase2-e"
    assert report.claim_tier == CLAIM_TIER
    assert report.claim_boundary == CLAIM_BOUNDARY

    # Inputs section keys
    assert report.inputs["starter_deck_relpath"].endswith("model_00_0000.rad")
    assert report.inputs["engine_deck_relpath"].endswith("model_00_0001.rad")
    assert report.inputs["projectile_initial_velocity_m_per_s"] == pytest.approx(830.0)

    # Solver section
    assert report.solver_evidence["engine_normal_termination"] is True
    assert report.solver_evidence["engine_cycle_count"] == 14645

    # Ballistic metrics
    assert report.ballistic_metrics["perforation_marker"] == "perforated_candidate"
    assert report.ballistic_metrics["residual_velocity_candidate_m_per_s"] == pytest.approx(74.5)

    # Energy audit graduated to closed_aggregate
    assert report.energy_audit["status"] == "closed_aggregate"
    assert report.energy_audit["aggregate_internal_energy_j"] == pytest.approx(826.6)
    assert report.energy_audit["energy_balance_error_pct"] == pytest.approx(19.0)
    assert set(report.energy_audit["missing_terms"]) == {
        "plastic_dissipation_j",
        "contact_friction_j",
        "hourglass_energy_j",
    }

    # Convergence section
    assert report.convergence_study["combined_verdict"] == "candidate_observed_unstable"
    assert report.convergence_study["dt_sweep_stability"] == "candidate_observed_unstable"
    assert report.convergence_study["row_count"] == 4

    # Artifact hashes: 2 files (metrics + convergence) on disk → both hashed.
    relpaths = [h.relpath for h in report.artifact_hashes]
    assert any("ballistic_metrics.json" in p for p in relpaths)
    assert any("convergence_study.json" in p for p in relpaths)
    for h in report.artifact_hashes:
        assert h.sha256 is not None
        assert h.bytes_count is not None and h.bytes_count > 0


def test_builder_handles_missing_convergence_study(tmp_path: Path) -> None:
    metrics = _write_minimal_metrics(tmp_path)
    report = build_tier1_candidate_report(
        Tier1CandidateReportInputs(
            case_id="GS-102-phase2-e",
            ballistic_metrics_path=metrics,
            convergence_study_path=None,
            repo_root=tmp_path,
        )
    )
    assert report.convergence_study["status"] == "unavailable"
    assert report.convergence_study["combined_verdict"] == "insufficient_data"


def test_builder_raises_when_metrics_file_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        build_tier1_candidate_report(
            Tier1CandidateReportInputs(
                case_id="missing",
                ballistic_metrics_path=tmp_path / "nope.json",
                repo_root=tmp_path,
            )
        )


def test_markdown_renderer_contains_every_section_heading(tmp_path: Path) -> None:
    metrics = _write_minimal_metrics(tmp_path)
    report = build_tier1_candidate_report(
        Tier1CandidateReportInputs(
            case_id="GS-102-phase2-e",
            ballistic_metrics_path=metrics,
            convergence_study_path=_write_minimal_convergence(tmp_path),
            repo_root=tmp_path,
        )
    )
    md = render_tier1_report_markdown(report)
    for heading in (
        "# Tier 1 Candidate Report",
        "## Inputs",
        "## Solver evidence",
        "## Ballistic metrics",
        "## Energy audit",
        "## Convergence study",
        "## Visualization artifacts",
        "## Artifact hashes",
        "## Assumptions",
        "## Limitations",
        "## Claim boundary",
    ):
        assert heading in md, f"missing section: {heading}"

    # Tier 1 banner appears in the header AND in the closing claim boundary.
    assert TIER1_BANNER in md
    # No positive overclaim leaked into the rendered markdown.
    text = md.lower()
    for forbidden in (
        "validated against",
        "perforation completed",
        "bullet-through-steel complete",
        "validated physics",
    ):
        assert forbidden not in text


def test_markdown_renderer_surfaces_all_five_energy_terms(tmp_path: Path) -> None:
    metrics = _write_minimal_metrics(tmp_path)
    report = build_tier1_candidate_report(
        Tier1CandidateReportInputs(
            case_id="GS-102-phase2-e",
            ballistic_metrics_path=metrics,
            repo_root=tmp_path,
        )
    )
    md = render_tier1_report_markdown(report)
    for key in (
        "initial_kinetic_energy_j",
        "residual_kinetic_energy_j",
        "aggregate_internal_energy_j",
        "external_work_j",
        "energy_balance_error_pct",
    ):
        assert key in md, f"energy key missing from markdown: {key}"


def test_docx_renderer_produces_a_zip_compatible_archive(tmp_path: Path) -> None:
    metrics = _write_minimal_metrics(tmp_path)
    report = build_tier1_candidate_report(
        Tier1CandidateReportInputs(
            case_id="GS-102-phase2-e",
            ballistic_metrics_path=metrics,
            repo_root=tmp_path,
        )
    )
    blob = render_tier1_report_docx_bytes(report)
    # DOCX is a zip; first bytes should be the PK\x03\x04 signature.
    assert blob[:4] == b"PK\x03\x04", "DOCX output is not a valid ZIP archive"
    assert len(blob) > 4_000  # non-trivial doc


def test_write_artifacts_emits_both_md_and_docx(tmp_path: Path) -> None:
    metrics = _write_minimal_metrics(tmp_path)
    report = build_tier1_candidate_report(
        Tier1CandidateReportInputs(
            case_id="GS-102-phase2-e",
            ballistic_metrics_path=metrics,
            repo_root=tmp_path,
        )
    )
    out_dir = tmp_path / "reports"
    paths = write_tier1_report_artifacts(report, out_dir)
    assert paths["markdown"].is_file()
    assert paths["markdown"].name == "GS-102-phase2-e_Tier1_candidate_report.md"
    assert paths["docx"].is_file()
    assert paths["docx"].name == "GS-102-phase2-e_Tier1_candidate_report.docx"
    # Markdown round-trip starts with the right heading.
    assert (
        paths["markdown"]
        .read_text(encoding="utf-8")
        .startswith("# Tier 1 Candidate Report — GS-102-phase2-e")
    )


def test_write_artifacts_refuses_paths_under_golden_samples(tmp_path: Path) -> None:
    metrics = _write_minimal_metrics(tmp_path)
    report = build_tier1_candidate_report(
        Tier1CandidateReportInputs(
            case_id="GS-102-phase2-e",
            ballistic_metrics_path=metrics,
            repo_root=tmp_path,
        )
    )
    forbidden_dir = tmp_path / "golden_samples" / "GS-102-some-candidate" / "reports"
    with pytest.raises(ValueError, match="golden_samples"):
        write_tier1_report_artifacts(report, forbidden_dir)


def test_builder_refuses_a_forbidden_positive_claim_in_notes(tmp_path: Path) -> None:
    metrics = _write_minimal_metrics(tmp_path)
    inputs = Tier1CandidateReportInputs(
        case_id="GS-102-phase2-e",
        ballistic_metrics_path=metrics,
        notes="This run is validated against the benchmark.",
        repo_root=tmp_path,
    )
    with pytest.raises(ValueError, match="forbidden positive claim"):
        build_tier1_candidate_report(inputs)


def test_report_preserves_claim_boundary_in_every_section_text(tmp_path: Path) -> None:
    metrics = _write_minimal_metrics(tmp_path)
    report = build_tier1_candidate_report(
        Tier1CandidateReportInputs(
            case_id="GS-102-phase2-e",
            ballistic_metrics_path=metrics,
            convergence_study_path=_write_minimal_convergence(tmp_path),
            repo_root=tmp_path,
        )
    )
    md = render_tier1_report_markdown(report)
    # The Tier 1 banner appears at the top; the claim boundary string appears
    # multiple times across section "claim_impact" fields. Strip the explicit
    # disclaimer phrases and verify no positive form leaks.
    stripped = (
        md.lower()
        .replace("not signed validation", "")
        .replace("not benchmark agreement", "")
        .replace("not_signed_validation", "")
        .replace("not_benchmark_agreement", "")
    )
    assert "signed validation" not in stripped
    assert "benchmark agreement" not in stripped
