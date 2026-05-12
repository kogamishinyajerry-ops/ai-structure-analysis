"""Tests for simulation sample manifest conversion.

Tier 1 engineering-candidate infrastructure only; not signed validation.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.services.simulation_sample_manifest import build_simulation_sample_manifest  # noqa: E402


def _available_artifact(kind: str, path: str) -> dict:
    return {
        "kind": kind,
        "status": "available",
        "path": path,
        "file_name": Path(path).name,
        "size_bytes": 128,
        "sha256": kind[0] * 64,
        "description": f"{kind} fixture",
    }


def _scalar_ready_spine() -> dict:
    return {
        "schema_version": "fm03-candidate-report-spine.v2",
        "generated_at_utc": "2026-05-12T00:00:00+00:00",
        "claim_tier": "Tier 1 engineering candidate",
        "allowed_claim": "engineering candidate, not signed validation",
        "no_overclaim": "not signed validation",
        "case": {
            "case_id": "CASE-STATIC-READY",
            "case_name": "static scalar ready fixture",
            "expected_results_status": "insufficient_evidence",
            "status_reason": "candidate only",
            "failure_pattern_ref": "not surfaced",
        },
        "provenance": {
            "report_surface": "POST /api/v1/report/generate",
            "parser": "FRDParser",
            "result_file_name": "ready.frd",
            "original_filename": "ready.frd",
            "file_size_bytes": 4096,
            "parse_time_s": 0.012,
            "is_binary_frd": False,
            "node_count": 44,
            "element_count": 10,
            "increment_count": 2,
            "solver_truth_source": "CalculiX FRD artifact",
        },
        "solver": {
            "truth_source": "CalculiX artifact",
            "solver_version": "CalculiX 2.21",
            "backend": "CalculiXFEABackend",
            "latest_job_id": "job-123",
            "latest_job_status": "COMPLETED",
            "normal_termination_state": "completed",
            "logs": {
                "status": "available",
                "line_count": 3,
                "tail": ["normal termination"],
                "artifact_paths": ["project_state/runs/CASE-STATIC-READY/solver.dat"],
            },
        },
        "assumptions": {
            "unit_system": {
                "status": "declared",
                "normalized": {"stress": "MPa", "length": "mm"},
            },
            "material": {
                "status": "declared",
                "source": "test material card",
            },
            "boundary_conditions": {
                "status": "declared",
                "source": "test support/load card",
            },
            "contact": {"status": "not_applicable"},
        },
        "mesh_evidence": {
            "status": "partial",
            "result_mesh": {
                "source": "FRDParser",
                "node_count": 44,
                "element_count": 10,
                "increment_count": 2,
            },
            "input_deck": {
                "status": "available",
                "path": "project_state/runs/CASE-STATIC-READY/model.inp",
                "node_count": 44,
                "element_count": 10,
                "include_count": 0,
                "element_types": {"C3D8": 10},
            },
            "metadata": {"status": "unavailable", "artifacts": []},
            "quality": {
                "status": "available",
                "source": "project_state/runs/CASE-STATIC-READY/mesh_quality.json",
                "metrics": {"min_scaled_jacobian": 0.8},
            },
            "convergence_study": {
                "status": "available",
                "candidate_stability": "candidate_observed_stable",
                "run_count": 3,
            },
        },
        "convergence_evidence": {
            "status": "job_completed",
            "normal_termination": "completed",
            "source_artifacts": [
                {
                    "kind": "dat",
                    "status": "available",
                    "path": "project_state/runs/CASE-STATIC-READY/solver.dat",
                }
            ],
            "missing_reasons": [],
        },
        "metrics": {
            "output_metric_keys": ["max_displacement", "max_von_mises", "safety_factor"],
            "values": {
                "max_displacement": 0.24,
                "max_von_mises": 123.4,
                "safety_factor": 2.5,
            },
            "extraction_command": "POST /api/v1/report/generate",
        },
        "validation": {"status": "N/A", "error_percentage": 0.0},
        "artifact_manifest": {
            "manifest_id": "fm03-CASE-STATIC-READY-abc123",
            "hash_algorithm": "sha256",
            "hash_count": 4,
            "items": [
                _available_artifact(
                    "result_frd",
                    "project_state/runs/CASE-STATIC-READY/ready.frd",
                ),
                _available_artifact(
                    "input_deck",
                    "project_state/runs/CASE-STATIC-READY/model.inp",
                ),
                _available_artifact(
                    "solver_log",
                    "project_state/runs/CASE-STATIC-READY/solver.dat",
                ),
                _available_artifact(
                    "mesh_quality",
                    "project_state/runs/CASE-STATIC-READY/mesh_quality.json",
                ),
            ],
        },
        "limitations": ["not signed validation", "no public benchmark agreement is claimed"],
        "tier2_blockers": [
            "public benchmark/source is not attached",
            "independent reviewer/signoff is not attached",
            "this payload is explicitly not signed validation",
        ],
    }


def test_converts_scalar_ready_spine_to_training_ready_scalar_manifest() -> None:
    manifest = build_simulation_sample_manifest(_scalar_ready_spine())

    assert manifest["schema_version"] == "simulation_sample_manifest.v0"
    assert manifest["manifest_id"] == "sample-fm03-CASE-STATIC-READY-abc123"
    assert manifest["claim_tier"] == "Tier 1 engineering candidate"
    assert manifest["allowed_claim"] == "engineering candidate data sample, not signed validation"
    assert manifest["case"]["case_family"] == "static_structural"
    assert manifest["recipe"]["recipe_id"] == "static_structural_calculix_candidate.v1"
    assert manifest["recipe"]["recipe_status"] == "attached"
    assert manifest["recipe"]["recipe_inputs_complete"] is True
    assert manifest["recipe"]["preflight_status"] == "passed"
    assert manifest["solver"]["solver_name"] == "calculix"
    assert manifest["solver"]["solver_version"] == "CalculiX 2.21"
    assert manifest["inputs"]["result_file"]["sha256"] == "r" * 64
    assert manifest["inputs"]["input_deck"]["sha256"] == "i" * 64
    assert manifest["geometry_mesh"]["element_types"] == {"C3D8": 10}
    assert manifest["data_quality"]["sample_status"] == "training_ready_scalar"
    assert manifest["data_quality"]["training_ready"] is True
    assert manifest["ai_readiness"]["allowed_model_tasks"] == [
        "scalar_kpi_baseline",
        "similarity_indexing",
        "outlier_detection",
    ]
    assert manifest["ai_readiness"]["abstention_required"] is False
    ready_targets = [
        item for item in manifest["metrics"]["target_candidates"] if item["training_ready"]
    ]
    assert {item["name"] for item in ready_targets} == {
        "max_displacement",
        "max_von_mises",
        "safety_factor",
    }


def test_report_upload_without_runtime_context_is_not_training_ready() -> None:
    spine = _scalar_ready_spine()
    spine["case"]["case_id"] = "uploaded-artifact"
    spine["case"]["case_name"] = "manual upload"
    spine["solver"]["solver_version"] = None
    spine["solver"]["latest_job_id"] = None
    spine["solver"]["latest_job_status"] = None
    spine["artifact_manifest"]["items"] = [
        _available_artifact("result_frd", "upload:manual.frd"),
    ]
    spine["artifact_manifest"]["hash_count"] = 1
    spine["assumptions"]["unit_system"].pop("normalized")
    spine["assumptions"]["material"] = {"status": "unavailable"}

    manifest = build_simulation_sample_manifest(spine)

    assert manifest["case"]["case_id"] == "uploaded-artifact"
    assert manifest["data_quality"]["sample_status"] == "not_training_ready"
    assert manifest["recipe"]["recipe_id"] == "static_structural_calculix_candidate.v1"
    assert manifest["recipe"]["recipe_status"] == "incomplete"
    assert manifest["recipe"]["recipe_inputs_complete"] is False
    assert "input_deck_hash" in manifest["recipe"]["missing_inputs"]
    assert manifest["data_quality"]["training_ready"] is False
    assert manifest["ai_readiness"]["abstention_required"] is True
    assert "solver version" in manifest["data_quality"]["missing_required_for_training"]
    assert "input deck hash" in manifest["data_quality"]["missing_required_for_training"]
    assert "unit-system normalization" in manifest["data_quality"]["missing_required_for_training"]
    assert manifest["inputs"]["input_deck"]["status"] == "unavailable"
    assert all(
        not candidate["training_ready"] for candidate in manifest["metrics"]["target_candidates"]
    )


def test_preserves_tier1_boundaries_without_validation_claim_promotion() -> None:
    spine = _scalar_ready_spine()
    spine["ballistic"] = {
        "status": "candidate_observed",
        "tier2_blockers_ballistic": [
            "public ballistic benchmark/source not attached",
            "this payload is explicitly not benchmark agreement and not signed validation",
        ],
    }

    manifest = build_simulation_sample_manifest(spine)
    text = str(manifest).lower()

    assert "not signed validation" in manifest["allowed_claim"]
    assert "tier2_validation_claim" in manifest["ai_readiness"]["disallowed_model_tasks"]
    assert "benchmark_agreement_prediction" in manifest["ai_readiness"]["disallowed_model_tasks"]
    assert manifest["recipe"]["recipe_status"] == "not_attached"
    assert "public ballistic benchmark/source not attached" in manifest["tier2_blockers"]
    assert "validated physics" not in text
    assert "benchmark agreement achieved" not in text
    assert "signed validation complete" not in text
