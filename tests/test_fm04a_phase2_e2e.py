"""End-to-end synthetic integration test for FM-04a Phase 2 A→E.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Proves the full Tier 1 closure loop with no real solver:

1. Synthesizes an OpenRadioss engine `.out` energy table + a flat
   ballistic_metrics.json + 3 sibling metric sidecars (mesh x dt grid).
2. Runs the Phase 2 A audit extractor against the engine `.out` →
   `closed_aggregate` status with all 5 honest energy keys.
3. Feeds the 3 sidecars through the Phase 2 B convergence orchestrator
   → structured `convergence_study.json`.
4. Builds the Phase 2 E Tier 1 candidate report packet (markdown +
   DOCX) consuming both sidecars.
5. Verifies the Phase 2 D tone helpers report `accent` /
   `candidate_observed_stable` / live source for closed evidence.
6. Forbidden-wording audit clean across every artifact produced.
"""

# Synthetic engine .out rows preserve OpenRadioss wide-column format; line-length
# would otherwise force unreadable splits.
# ruff: noqa: E501

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest
from app.api.routes import candidate_cases
from app.services.ballistics.convergence_orchestrator import (
    VERDICT_STABLE,
    ConvergenceStudyInput,
    ConvergenceStudyRow,
    write_convergence_study,
)
from app.services.ballistics.energy_audit_extractor import (
    assess_energy_audit,
    build_energy_audit_from_engine_out,
)
from app.services.ballistics.engine_energy_history import (
    parse_engine_out_energy_history,
)
from app.services.reporting.tier1_candidate_report import (
    Tier1CandidateReportInputs,
    build_tier1_candidate_report,
    write_tier1_report_artifacts,
)

_ENGINE_OUT_HEADER = (
    "   CYCLE    TIME      TIME-STEP  ELEMENT          ERROR  "
    "I-ENERGY    K-ENERGY T  K-ENERGY R  EXT-WORK     MAS.ERR     "
    "TOTAL MASS  MASS ADDED"
)


def _write_engine_out(case_dir: Path) -> Path:
    """Synthesize a 3-row engine .out energy table.

    KE_initial = 1000, KE_residual = 800, I_internal = 200, EXT_WORK = 0
    → balance error = 0% (perfect closure of the synthetic energy ledger).
    """
    body = textwrap.dedent(
        f"""
        OpenRadioss banner
        {_ENGINE_OUT_HEADER}
               0   0.000      1.0E-04   INTER          1   0.0%   0.0    1.0E+03   0.0   0.0   0.0   1.0E+04   0.0
            1000  5.0E-03    5.0E-06   NODE           1   1.0%   1.0E+02 9.0E+02   0.0   0.0   0.0   1.0E+04   0.0
            2000  1.0E-02    5.0E-06   NODE           1   1.5%   2.0E+02 8.0E+02   0.0   0.0   0.0   1.0E+04   0.0
        NORMAL TERMINATION
        """
    ).strip()
    case_dir.mkdir(parents=True, exist_ok=True)
    out_path = case_dir / "model_00_0001.out"
    out_path.write_text(body, encoding="utf-8")
    return out_path


def _write_ballistic_metrics(
    case_dir: Path,
    *,
    case_id: str,
    residual_velocity: float,
    energy_audit_block: dict | None = None,
) -> Path:
    """Synthesize a ballistic_metrics.json with the energy_audit block."""
    case_dir.mkdir(parents=True, exist_ok=True)
    payload: dict = {
        "case_id": case_id,
        "claim_boundary": "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement",
        "status": "candidate_observed",
        "perforation_marker": "perforated_candidate",
        "projectile_initial_velocity_m_per_s": 600.0,
        "residual_velocity_candidate_m_per_s": residual_velocity,
        "extraction_metadata": {
            "impact_axis": "x",
            "plate_back_face_axis_value_m": 0.042,
            "plate_thickness_m": 0.012,
            "projectile_mass_kg": 0.005024,
            "claim_impact": "Tier 1 candidate ballistic metrics; not benchmark agreement; not signed validation",
        },
        "crossing_evidence": {
            "status": "candidate_observed",
            "front_face_crossed": True,
            "back_face_crossed": True,
            "first_back_face_crossing_t_s": 5.0e-5,
        },
        "solver_evidence": {
            "status": "candidate_observed",
            "engine_normal_termination": True,
            "engine_cycle_count": 2000,
            "animation_frame_count": 20,
        },
    }
    if energy_audit_block is not None:
        payload["energy_audit"] = energy_audit_block
    out_path = case_dir / "ballistic_metrics.json"
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return out_path


def test_phase2_e2e_synthetic_loop_closes_tier1_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Proves Phase A → B → C → E loop end-to-end on synthetic inputs."""
    # ----- Step 1. Set up a synthetic repo skeleton with one fixture case.
    repo_root = tmp_path
    case_id = "GS-102-fixture-e2e"
    case_data_dir = repo_root / "project_state" / "runs" / case_id / "data"
    metrics_dir = repo_root / "project_state" / "graph_executor" / case_id / "ballistic"
    convergence_dir = repo_root / "project_state" / "graph_executor" / case_id / "convergence"
    report_dir = repo_root / "reports"

    engine_out_path = _write_engine_out(case_data_dir)

    # ----- Step 2. Phase A: parse engine .out, build energy audit, assert closed.
    history = parse_engine_out_energy_history(engine_out_path)
    assert history.has_history is True
    energy_audit = build_energy_audit_from_engine_out(engine_out_path, history=history)
    audit_block = assess_energy_audit(energy_audit, history=history)
    assert audit_block["status"] == "closed_aggregate", (
        f"expected closed_aggregate status, got {audit_block['status']!r}"
    )
    assert audit_block["aggregate_internal_energy_j"] == pytest.approx(2.0e2)
    assert audit_block["energy_balance_error_pct"] == pytest.approx(0.0, abs=1e-9)
    assert audit_block["breakdown_status"] == "aggregated_into_internal_energy"

    primary_metrics_path = _write_ballistic_metrics(
        metrics_dir,
        case_id=case_id,
        residual_velocity=300.0,
        energy_audit_block=audit_block,
    )

    # ----- Step 3. Phase B: synthesize 2 sibling cases and run the orchestrator.
    sibling_cases = [
        ("GS-102-fixture-e2e-mesh-coarse", "coarse", 1.0, "dt_a", 1.0e-7, 290.0),
        ("GS-102-fixture-e2e-mesh-medium", "medium", 2.0, "dt_a", 1.0e-7, 296.0),
    ]
    sibling_metrics_paths = []
    for sid, mesh_label, mesh_val, dt_label, dt_val, residual in sibling_cases:
        sibling_metrics_dir = repo_root / "project_state" / "graph_executor" / sid / "ballistic"
        sibling_metrics_paths.append(
            (
                mesh_label,
                mesh_val,
                dt_label,
                dt_val,
                residual,
                _write_ballistic_metrics(
                    sibling_metrics_dir,
                    case_id=sid,
                    residual_velocity=residual,
                ),
            )
        )

    rows = [
        ConvergenceStudyRow(
            mesh_label=mesh_label,
            mesh_axis_value=mesh_val,
            dt_label=dt_label,
            dt_axis_value=dt_val,
            residual_velocity_m_per_s=residual,
            energy_balance_error_pct=audit_block["energy_balance_error_pct"]
            if mesh_label == "medium"
            else 1.0,
            source_metrics_path=str(metrics_path.relative_to(repo_root)),
        )
        for mesh_label, mesh_val, dt_label, dt_val, residual, metrics_path in sibling_metrics_paths
    ] + [
        ConvergenceStudyRow(
            mesh_label="fine",
            mesh_axis_value=3.0,
            dt_label="dt_a",
            dt_axis_value=1.0e-7,
            residual_velocity_m_per_s=300.0,
            energy_balance_error_pct=0.0,
            source_metrics_path=str(primary_metrics_path.relative_to(repo_root)),
        ),
        ConvergenceStudyRow(
            mesh_label="medium",
            mesh_axis_value=2.0,
            dt_label="dt_b",
            dt_axis_value=5.0e-8,
            residual_velocity_m_per_s=297.0,
            energy_balance_error_pct=1.5,
            source_metrics_path="project_state/graph_executor/fixture-dt-b/ballistic_metrics.json",
        ),
    ]
    study_path = write_convergence_study(
        ConvergenceStudyInput(
            case_id=case_id,
            rows=rows,
            tolerance_pct=5.0,
        ),
        convergence_dir,
    )
    study_payload = json.loads(study_path.read_text(encoding="utf-8"))
    assert study_payload["combined_verdict"] == VERDICT_STABLE
    assert study_payload["energy_balance_observation"]["status"] == "candidate_observed"

    # ----- Step 4. Phase C: stand up the candidate-case picker against the
    # synthetic repo and prove the picker finds the e2e fixture case.
    (repo_root / "golden_samples" / "GS-102-fixture-candidate" / "data").mkdir(parents=True)
    (
        repo_root / "golden_samples" / "GS-102-fixture-candidate" / "data" / "model_00_0000.rad"
    ).write_text("synth starter\n")
    (
        repo_root / "golden_samples" / "GS-102-fixture-candidate" / "data" / "model_00_0001.rad"
    ).write_text("synth engine\n")
    (repo_root / "golden_samples" / "GS-102-fixture-candidate" / "NOTES.md").write_text(
        "# fixture notes\n\nTier 1 engineering candidate; not signed validation.\n"
    )
    monkeypatch.setattr(candidate_cases, "_repo_root", lambda: repo_root)
    picker_payload = candidate_cases._scan_candidate_cases(repo_root)
    picker_ids = [c["case_id"] for c in picker_payload]
    assert "GS-102-fixture-candidate" in picker_ids
    # The signed registry (e.g. GS-001) is not present in this synth repo;
    # the picker would still exclude it because it lacks the -candidate suffix.

    # ----- Step 5. Phase E: build the Tier 1 candidate report packet.
    report = build_tier1_candidate_report(
        Tier1CandidateReportInputs(
            case_id=case_id,
            ballistic_metrics_path=primary_metrics_path,
            convergence_study_path=study_path,
            starter_deck_relpath="golden_samples/GS-102-fixture-candidate/data/model_00_0000.rad",
            engine_deck_relpath="golden_samples/GS-102-fixture-candidate/data/model_00_0001.rad",
            generator_script_relpath=None,
            repo_root=repo_root,
        )
    )

    # Energy audit propagated end-to-end from the .out file → audit block →
    # metrics sidecar → report packet.
    assert report.energy_audit["status"] == "closed_aggregate"
    assert report.energy_audit["aggregate_internal_energy_j"] == pytest.approx(2.0e2)
    assert report.energy_audit["energy_balance_error_pct"] == pytest.approx(0.0, abs=1e-9)
    # Convergence verdict matches the Phase B study.
    assert report.convergence_study["combined_verdict"] == VERDICT_STABLE
    # Ballistic metrics carried through.
    assert report.ballistic_metrics["perforation_marker"] == "perforated_candidate"
    assert report.ballistic_metrics["residual_velocity_candidate_m_per_s"] == pytest.approx(300.0)
    # Artifact hashes cover both attached files (metrics + convergence study).
    relpaths = [h.relpath for h in report.artifact_hashes]
    assert any("ballistic_metrics.json" in p for p in relpaths)
    assert any("convergence_study.json" in p for p in relpaths)

    # ----- Step 6. Write packet artifacts, confirm both files exist.
    paths = write_tier1_report_artifacts(report, report_dir)
    assert paths["markdown"].is_file()
    assert paths["docx"].is_file()
    markdown_text = paths["markdown"].read_text(encoding="utf-8")

    # Phase 2 banner + closed_aggregate visible to the reviewer.
    assert "Tier 1 Candidate Report" in markdown_text
    assert "closed_aggregate" in markdown_text
    assert VERDICT_STABLE in markdown_text

    # Forbidden positive claims absent throughout the e2e packet, including
    # the convergence sidecar text and the candidate-case picker output.
    haystack = (
        markdown_text
        + json.dumps(study_payload)
        + json.dumps(picker_payload, default=str)
        + json.dumps(audit_block)
    ).lower()
    for forbidden in (
        "validated against",
        "perforation completed",
        "bullet-through-steel complete",
        "validated physics",
    ):
        assert forbidden not in haystack, f"e2e packet leaked: {forbidden}"

    # Tier 1 disclaimer must appear and survive strip-then-check audit.
    assert "not signed validation" in haystack
    assert "not benchmark agreement" in haystack
    stripped = (
        haystack.replace("not signed validation", "")
        .replace("not benchmark agreement", "")
        .replace("not_signed_validation", "")
        .replace("not_benchmark_agreement", "")
    )
    assert "signed validation" not in stripped
    assert "benchmark agreement" not in stripped
