import json
from pathlib import Path

import pytest

from app.parsers.frd_parser import FRDParser
from app.services import candidate_report_spine as spine_module
from app.services.report_generator import ReportGenerator


REPO_ROOT = Path(__file__).resolve().parents[2]
GS_ROOT = REPO_ROOT / "golden_samples"
GS001_FRD = GS_ROOT / "GS-001" / "gs001_result.frd"


def test_candidate_report_spine_exposes_tier1_payload_shape() -> None:
    if not GS001_FRD.exists():
        pytest.skip(f"GS-001 FRD fixture missing at {GS001_FRD}")

    parsed = FRDParser().parse(str(GS001_FRD))
    report = ReportGenerator(GS_ROOT).generate(
        parsed,
        case_id="GS-001",
        source_path=GS001_FRD,
        original_filename="gs001_result.frd",
    )

    spine = report.candidate_report_spine
    assert spine["schema_version"] == "fm03-candidate-report-spine.v1"
    assert spine["claim_tier"] == "Tier 1 engineering candidate"
    assert spine["no_overclaim"] == "not signed validation"
    assert spine["allowed_claim"] == "engineering candidate, not signed validation"

    assert spine["case"]["case_id"] == "GS-001"
    assert spine["case"]["expected_results_status"] == "insufficient_evidence"
    assert spine["provenance"]["parser"] == "FRDParser"
    assert spine["provenance"]["node_count"] > 0
    assert spine["provenance"]["element_count"] > 0

    mesh_evidence = spine["mesh_evidence"]
    assert mesh_evidence["claim_impact"] == (
        "mesh topology is surfaced for Tier 1 reproducibility only; "
        "mesh adequacy or convergence is not proven"
    )
    assert mesh_evidence["result_mesh"]["source"] == "FRDParser"
    assert mesh_evidence["result_mesh"]["node_count"] == spine["provenance"]["node_count"]
    assert mesh_evidence["result_mesh"]["element_count"] == spine["provenance"]["element_count"]
    assert mesh_evidence["input_deck"]["status"] == "available"
    assert mesh_evidence["input_deck"]["node_count"] == 44
    assert mesh_evidence["input_deck"]["element_count"] == 10
    assert mesh_evidence["input_deck"]["element_types"] == {"C3D8": 10}
    assert mesh_evidence["quality"]["status"] in {"unavailable", "metadata_only"}
    assert "not signed validation" in mesh_evidence["quality"]["unavailable_reason"]

    convergence_evidence = spine["convergence_evidence"]
    assert convergence_evidence["claim_impact"] == (
        "solver status artifacts are surfaced for Tier 1 review only; "
        "this is not a mesh convergence study or signed validation"
    )
    assert convergence_evidence["status"] in {
        "artifact_reference_only",
        "solver_artifact_converged",
        "job_completed",
    }
    assert convergence_evidence["normal_termination"] in {
        "available",
        "completed",
        "unavailable",
    }
    assert any(item["kind"] == "dat" for item in convergence_evidence["source_artifacts"])
    assert convergence_evidence["missing_reasons"]

    manifest = spine["artifact_manifest"]
    assert manifest["hash_algorithm"] == "sha256"
    assert manifest["hash_count"] >= 3
    artifact_kinds = {item["kind"] for item in manifest["items"]}
    assert {"result_frd", "input_deck", "expected_results"}.issubset(artifact_kinds)
    for item in manifest["items"]:
        if item["status"] == "available":
            assert len(item["sha256"]) == 64
            assert not item["path"].startswith("/")

    assert "not signed validation" in spine["limitations"]
    assert "independent reviewer/signoff is not attached" in spine["tier2_blockers"]
    assert spine["reviewer_summary"]["verdict"] == "needs_review"


def test_candidate_report_spine_consumes_mesh_quality_sidecar(tmp_path, monkeypatch) -> None:
    if not GS001_FRD.exists():
        pytest.skip(f"GS-001 FRD fixture missing at {GS001_FRD}")

    monkeypatch.setattr(spine_module, "REPO_ROOT", tmp_path)
    case_id = "CASE-QUALITY"
    case_dir = tmp_path / "golden_samples" / case_id
    case_dir.mkdir(parents=True)
    (case_dir / "expected_results.json").write_text(
        json.dumps(
            {
                "case_id": case_id,
                "case_name": "Mesh quality sidecar fixture",
                "status": "insufficient_evidence",
                "status_reason": "test fixture is not signed validation",
                "failure_pattern_ref": "FP-TEST",
            }
        ),
        encoding="utf-8",
    )
    (case_dir / "model.inp").write_text(
        "\n".join(
            [
                "*NODE",
                "1,0,0,0",
                "2,1,0,0",
                "3,0,1,0",
                "4,0,0,1",
                "*ELEMENT, TYPE=C3D4",
                "1,1,2,3,4",
            ]
        ),
        encoding="utf-8",
    )
    runtime_mesh_dir = tmp_path / "project_state" / "graph_executor" / case_id / "mesh"
    runtime_mesh_dir.mkdir(parents=True)
    (runtime_mesh_dir / "mesh_quality.json").write_text(
        json.dumps(
            {
                "status": "available",
                "metrics": {
                    "min_scaled_jacobian": 0.82,
                    "max_aspect_ratio": 3.4,
                    "degenerate_pct": 0.0,
                    "passed": True,
                },
                "thresholds": {
                    "min_scaled_jacobian": 0.2,
                    "max_aspect_ratio": 10.0,
                },
                "findings": [],
                "claim_boundary": "tier1_engineering_candidate; not_signed_validation",
            }
        ),
        encoding="utf-8",
    )

    parsed = FRDParser().parse(str(GS001_FRD))
    report = ReportGenerator(case_dir.parent).generate(
        parsed,
        case_id=case_id,
        source_path=GS001_FRD,
        original_filename="gs001_result.frd",
    )

    quality = report.candidate_report_spine["mesh_evidence"]["quality"]
    assert quality["status"] == "available"
    assert quality["source"] == "project_state/graph_executor/CASE-QUALITY/mesh/mesh_quality.json"
    assert quality["metrics"]["min_scaled_jacobian"] == 0.82
    assert quality["thresholds"]["max_aspect_ratio"] == 10.0
    assert quality["claim_impact"] == "Tier 1 only; mesh quality metrics do not prove mesh convergence or signed validation"


def test_candidate_report_spine_consumes_mesh_refinement_convergence_study(
    tmp_path,
    monkeypatch,
) -> None:
    if not GS001_FRD.exists():
        pytest.skip(f"GS-001 FRD fixture missing at {GS001_FRD}")

    monkeypatch.setattr(spine_module, "REPO_ROOT", tmp_path)
    case_id = "CASE-CONVERGENCE"
    case_dir = tmp_path / "golden_samples" / case_id
    case_dir.mkdir(parents=True)
    (case_dir / "expected_results.json").write_text(
        json.dumps(
            {
                "case_id": case_id,
                "case_name": "Mesh convergence sidecar fixture",
                "status": "insufficient_evidence",
                "status_reason": "test fixture is not signed validation",
                "failure_pattern_ref": "FP-TEST",
            }
        ),
        encoding="utf-8",
    )
    (case_dir / "model.inp").write_text("*NODE\n1,0,0,0\n*ELEMENT, TYPE=C3D4\n1,1,1,1,1\n", encoding="utf-8")
    runtime_mesh_dir = tmp_path / "project_state" / "graph_executor" / case_id / "mesh"
    runtime_mesh_dir.mkdir(parents=True)
    (runtime_mesh_dir / "mesh_convergence.json").write_text(
        json.dumps(
            {
                "status": "candidate_observed",
                "parameter": "mesh_level",
                "metric": "max_von_mises",
                "tolerance_pct": 5.0,
                "runs": [
                    {"label": "coarse", "element_count": 100, "metric_value": 120.0},
                    {"label": "medium", "element_count": 220, "metric_value": 124.0},
                    {"label": "fine", "element_count": 480, "metric_value": 125.0},
                ],
                "relative_change_pct": 0.8,
                "claim_boundary": "tier1_engineering_candidate; not_signed_validation",
            }
        ),
        encoding="utf-8",
    )

    parsed = FRDParser().parse(str(GS001_FRD))
    report = ReportGenerator(case_dir.parent).generate(
        parsed,
        case_id=case_id,
        source_path=GS001_FRD,
        original_filename="gs001_result.frd",
    )

    spine = report.candidate_report_spine
    study = spine["mesh_evidence"]["convergence_study"]
    assert study["status"] == "available"
    assert study["source"] == "project_state/graph_executor/CASE-CONVERGENCE/mesh/mesh_convergence.json"
    assert study["parameter"] == "mesh_level"
    assert study["metric"] == "max_von_mises"
    assert study["run_count"] == 3
    assert study["relative_change_pct"] == 0.8
    assert study["claim_impact"] == (
        "Tier 1 candidate convergence evidence only; benchmark agreement and signed validation remain blocked"
    )
    assert "mesh refinement convergence study is not attached" not in spine["convergence_evidence"]["missing_reasons"]
    assert "mesh convergence evidence is not attached" not in spine["limitations"]
