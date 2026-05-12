"""Simulation sample manifest conversion.

This module converts the existing Candidate Report Spine into a reusable data
asset record for future AI/surrogate work. It does not run solvers, write files,
change report API shapes, or promote validation claims.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from app.services.analysis_recipes import build_static_structural_calculix_recipe_attachment

SCHEMA_VERSION = "simulation_sample_manifest.v0"
ALLOWED_CLAIM = "engineering candidate data sample, not signed validation"

_SCALAR_UNITS = {
    "max_displacement": "model_length_unit",
    "max_von_mises": "MPa",
    "safety_factor": "dimensionless",
    "residual_velocity_candidate_m_per_s": "m_per_s",
}


def build_simulation_sample_manifest(spine: Mapping[str, Any]) -> dict[str, Any]:
    """Build a simulation sample manifest from a Candidate Report Spine.

    The conversion is intentionally conservative. A sample is marked
    ``training_ready_scalar`` only when the spine has enough machine-readable
    evidence to support a scalar KPI baseline. Otherwise it remains useful for
    review and indexing, but the manifest requires abstention for model use.
    """

    artifact_manifest = _mapping(spine.get("artifact_manifest"))
    artifact_items = _list_of_mappings(artifact_manifest.get("items"))
    metrics = _mapping(spine.get("metrics"))
    metric_values = _mapping(metrics.get("values"))

    case = _build_case(spine)
    solver = _build_solver(spine)
    inputs = _build_inputs(artifact_items)
    geometry_mesh = _build_geometry_mesh(spine)
    physics_setup = _build_physics_setup(spine)
    runtime = _build_runtime(spine)
    outputs = _build_outputs(artifact_items, metrics)

    missing = _missing_required_for_scalar_training(
        case=case,
        solver=solver,
        inputs=inputs,
        physics_setup=physics_setup,
        metrics=metric_values,
    )
    target_candidates = _target_candidates(metric_values, missing)
    scalar_ready = not missing and bool(target_candidates)

    deduplication_key = _deduplication_key(case, solver, inputs)
    data_quality = {
        "sample_status": "training_ready_scalar" if scalar_ready else "not_training_ready",
        "training_ready": scalar_ready,
        "missing_required_for_training": missing,
        "warnings": _warnings(case, solver, inputs),
        "outlier_status": "not_evaluated",
        "deduplication_key": deduplication_key,
    }

    ai_readiness = {
        "intended_use": "scalar_kpi_baseline" if scalar_ready else "review_or_index_only",
        "allowed_model_tasks": (
            ["scalar_kpi_baseline", "similarity_indexing", "outlier_detection"]
            if scalar_ready
            else []
        ),
        "disallowed_model_tasks": _disallowed_model_tasks(scalar_ready),
        "similarity_features_available": _similarity_features_available(
            case,
            geometry_mesh,
            physics_setup,
        ),
        "abstention_required": not scalar_ready,
    }

    manifest_id = _manifest_id(artifact_manifest, case)

    return {
        "schema_version": SCHEMA_VERSION,
        "manifest_id": manifest_id,
        "generated_at_utc": spine.get("generated_at_utc"),
        "claim_tier": str(spine.get("claim_tier") or "Tier 1 engineering candidate"),
        "allowed_claim": ALLOWED_CLAIM,
        "case": case,
        "recipe": _build_recipe(
            case=case,
            solver=solver,
            inputs=inputs,
            physics_setup=physics_setup,
            metric_values=metric_values,
        ),
        "solver": solver,
        "inputs": inputs,
        "geometry_mesh": geometry_mesh,
        "physics_setup": physics_setup,
        "runtime": runtime,
        "outputs": outputs,
        "metrics": {
            "output_metric_keys": list(metrics.get("output_metric_keys") or sorted(metric_values)),
            "values": dict(metric_values),
            "extraction_command": metrics.get("extraction_command"),
            "target_candidates": target_candidates,
        },
        "artifact_manifest": {
            "hash_algorithm": artifact_manifest.get("hash_algorithm", "sha256"),
            "hash_count": artifact_manifest.get("hash_count", 0),
            "items": [dict(item) for item in artifact_items],
        },
        "data_quality": data_quality,
        "ai_readiness": ai_readiness,
        "limitations": list(spine.get("limitations") or []),
        "tier2_blockers": _tier2_blockers(spine),
    }


def _build_case(spine: Mapping[str, Any]) -> dict[str, Any]:
    case = _mapping(spine.get("case"))
    provenance = _mapping(spine.get("provenance"))
    solver = _mapping(spine.get("solver"))
    job_id = solver.get("latest_job_id") or solver.get("job_id")
    case_id = str(case.get("case_id") or "uploaded-artifact")

    return {
        "case_id": case_id,
        "case_name": str(case.get("case_name") or case_id),
        "case_family": _infer_case_family(spine),
        "run_id": str(job_id or case.get("run_id") or case_id),
        "source_surface": provenance.get("report_surface"),
    }


def _build_recipe(
    *,
    case: Mapping[str, Any],
    solver: Mapping[str, Any],
    inputs: Mapping[str, Mapping[str, Any]],
    physics_setup: Mapping[str, Any],
    metric_values: Mapping[str, Any],
) -> dict[str, Any]:
    return build_static_structural_calculix_recipe_attachment(
        case=case,
        solver=solver,
        inputs=inputs,
        physics_setup=physics_setup,
        metrics=metric_values,
    )


def _build_solver(spine: Mapping[str, Any]) -> dict[str, Any]:
    solver = _mapping(spine.get("solver"))
    provenance = _mapping(spine.get("provenance"))
    truth_source = str(
        solver.get("truth_source")
        or provenance.get("solver_truth_source")
        or "unknown"
    )

    return {
        "solver_name": _normalize_solver_name(truth_source),
        "solver_backend": solver.get("backend") or solver.get("solver_backend"),
        "solver_version": solver.get("solver_version") or solver.get("version"),
        "truth_source": truth_source,
        "job_id": solver.get("latest_job_id") or solver.get("job_id"),
        "job_status": solver.get("latest_job_status") or solver.get("job_status"),
        "normal_termination_state": solver.get("normal_termination_state"),
        "log_artifacts": _solver_log_artifacts(solver),
    }


def _build_inputs(artifact_items: list[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        "input_deck": _artifact_role(_first_artifact(artifact_items, "input_deck"), "input_deck"),
        "result_file": _artifact_role(_first_artifact(artifact_items, "result_frd"), "result_frd"),
        "expected_results": _artifact_role(
            _first_artifact(artifact_items, "expected_results"),
            "expected_results",
        ),
        "source_geometry": {"status": "unavailable", "role": "source_geometry"},
        "source_parameters": {"status": "unavailable", "role": "source_parameters"},
    }


def _build_geometry_mesh(spine: Mapping[str, Any]) -> dict[str, Any]:
    provenance = _mapping(spine.get("provenance"))
    mesh = _mapping(spine.get("mesh_evidence"))
    input_deck = _mapping(mesh.get("input_deck"))

    return {
        "node_count": provenance.get("node_count"),
        "element_count": provenance.get("element_count"),
        "element_types": dict(_mapping(input_deck.get("element_types"))),
        "increment_count": provenance.get("increment_count"),
        "mesh_metadata": dict(_mapping(mesh.get("metadata"))),
        "mesh_quality": dict(_mapping(mesh.get("quality"))),
        "mesh_convergence_study": dict(_mapping(mesh.get("convergence_study"))),
    }


def _build_physics_setup(spine: Mapping[str, Any]) -> dict[str, Any]:
    assumptions = _mapping(spine.get("assumptions"))
    ballistic = _mapping(spine.get("ballistic"))
    domain_specific: dict[str, Any] = {}
    if ballistic:
        domain_specific["ballistic"] = dict(ballistic)

    return {
        "unit_system": assumptions.get("unit_system") or {"status": "unavailable"},
        "materials": assumptions.get("material")
        or assumptions.get("material_source")
        or {"status": "unavailable"},
        "boundary_conditions": assumptions.get("boundary_conditions")
        or assumptions.get("boundary_condition_source")
        or {"status": "unavailable"},
        "loads": assumptions.get("loads") or {"status": "unavailable"},
        "contact": assumptions.get("contact") or {"status": "unavailable"},
        "failure_model": assumptions.get("failure_model") or {"status": "unavailable"},
        "domain_specific": domain_specific,
    }


def _build_runtime(spine: Mapping[str, Any]) -> dict[str, Any]:
    metrics = _mapping(spine.get("metrics"))
    source_surface = _mapping(spine.get("provenance")).get("report_surface")
    return {
        "started_at_utc": None,
        "finished_at_utc": None,
        "duration_s": None,
        "host": None,
        "runner": (
            "report_upload"
            if source_surface == "POST /api/v1/report/generate"
            else "unknown"
        ),
        "container_image": None,
        "command": metrics.get("extraction_command"),
        "exit_code": None,
    }


def _build_outputs(
    artifact_items: list[Mapping[str, Any]],
    metrics: Mapping[str, Any],
) -> dict[str, Any]:
    sidecars = [
        dict(item)
        for item in artifact_items
        if item.get("kind")
        not in {
            "result_frd",
            "input_deck",
            "expected_results",
            "solver_log",
        }
    ]
    result_file = _first_artifact(artifact_items, "result_frd")

    return {
        "result_fields": list(metrics.get("output_metric_keys") or []),
        "field_files": [dict(result_file)] if result_file else [],
        "report_artifacts": [],
        "sidecars": sidecars,
    }


def _missing_required_for_scalar_training(
    *,
    case: Mapping[str, Any],
    solver: Mapping[str, Any],
    inputs: Mapping[str, Mapping[str, Any]],
    physics_setup: Mapping[str, Any],
    metrics: Mapping[str, Any],
) -> list[str]:
    missing: list[str] = []
    if case.get("case_family") == "unknown":
        missing.append("stable case family")
    if not solver.get("solver_version"):
        missing.append("solver version")
    if not _has_hash(inputs.get("result_file")):
        missing.append("result artifact hash")
    if not _has_hash(inputs.get("input_deck")):
        missing.append("input deck hash")
    if not _has_normalized_units(physics_setup.get("unit_system")):
        missing.append("unit-system normalization")
    if not _has_declared_descriptor(physics_setup.get("materials")):
        missing.append("material descriptor")
    if not _has_declared_descriptor(physics_setup.get("boundary_conditions")):
        missing.append("boundary-condition descriptor")
    if not any(_is_finite_number(value) for value in metrics.values()):
        missing.append("non-empty target metrics")
    return missing


def _target_candidates(metrics: Mapping[str, Any], missing: list[str]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for name in sorted(metrics):
        value = metrics[name]
        if not _is_finite_number(value):
            continue
        unit = _SCALAR_UNITS.get(str(name), "unknown")
        blocked_by = list(missing)
        if unit == "unknown":
            blocked_by.append("metric unit unknown")
        candidates.append(
            {
                "name": str(name),
                "value": value,
                "unit": unit,
                "target_type": "scalar_regression",
                "training_ready": not blocked_by,
                "blocked_by": blocked_by,
            }
        )
    return candidates


def _warnings(
    case: Mapping[str, Any],
    solver: Mapping[str, Any],
    inputs: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    warnings: list[str] = []
    if case.get("case_id") == "uploaded-artifact":
        warnings.append("manual upload case id is not stable training identity")
    if not solver.get("job_id"):
        warnings.append("solver job runtime context is not attached")
    if not _has_hash(inputs.get("input_deck")):
        warnings.append("input deck hash is not attached")
    return warnings


def _disallowed_model_tasks(scalar_ready: bool) -> list[str]:
    tasks = [
        "tier2_validation_claim",
        "benchmark_agreement_prediction",
        "full_field_training",
    ]
    if not scalar_ready:
        tasks.append("scalar_kpi_training")
    return tasks


def _similarity_features_available(
    case: Mapping[str, Any],
    geometry_mesh: Mapping[str, Any],
    physics_setup: Mapping[str, Any],
) -> bool:
    return (
        case.get("case_family") != "unknown"
        and bool(geometry_mesh.get("node_count"))
        and bool(geometry_mesh.get("element_count"))
        and _has_declared_descriptor(physics_setup.get("materials"))
        and _has_declared_descriptor(physics_setup.get("boundary_conditions"))
    )


def _tier2_blockers(spine: Mapping[str, Any]) -> list[str]:
    blockers = list(spine.get("tier2_blockers") or [])
    ballistic = _mapping(spine.get("ballistic"))
    for blocker in ballistic.get("tier2_blockers_ballistic") or []:
        if blocker not in blockers:
            blockers.append(blocker)
    return blockers


def _manifest_id(artifact_manifest: Mapping[str, Any], case: Mapping[str, Any]) -> str:
    existing = artifact_manifest.get("manifest_id")
    if existing:
        return f"sample-{existing}"
    return f"sample-{case.get('case_id', 'unknown')}"


def _deduplication_key(
    case: Mapping[str, Any],
    solver: Mapping[str, Any],
    inputs: Mapping[str, Mapping[str, Any]],
) -> str | None:
    input_hash = _hash_value(inputs.get("input_deck"))
    result_hash = _hash_value(inputs.get("result_file"))
    if not (input_hash and result_hash):
        return None
    return f"{case.get('case_family')}:{solver.get('solver_name')}:{input_hash}:{result_hash}"


def _infer_case_family(spine: Mapping[str, Any]) -> str:
    ballistic = _mapping(spine.get("ballistic"))
    if ballistic.get("status") == "candidate_observed":
        return "ballistic_candidate"

    metrics = _mapping(_mapping(spine.get("metrics")).get("values"))
    metric_names = set(metrics)
    if {"max_displacement", "max_von_mises"} & metric_names:
        return "static_structural"
    return "unknown"


def _normalize_solver_name(truth_source: str) -> str:
    lowered = truth_source.lower()
    if "calculix" in lowered:
        return "calculix"
    if "openradioss" in lowered or "radioss" in lowered:
        return "openradioss"
    return "unknown"


def _solver_log_artifacts(solver: Mapping[str, Any]) -> list[Any]:
    logs = _mapping(solver.get("logs"))
    artifact_paths = logs.get("artifact_paths")
    return list(artifact_paths) if isinstance(artifact_paths, list) else []


def _first_artifact(items: list[Mapping[str, Any]], kind: str) -> Mapping[str, Any] | None:
    for item in items:
        if item.get("kind") == kind and item.get("status") == "available":
            return item
    return None


def _artifact_role(artifact: Mapping[str, Any] | None, role: str) -> dict[str, Any]:
    if artifact is None:
        return {"status": "unavailable", "role": role}
    result = dict(artifact)
    result["role"] = role
    return result


def _has_hash(value: Mapping[str, Any] | None) -> bool:
    return bool(value and isinstance(value.get("sha256"), str) and len(value["sha256"]) == 64)


def _hash_value(value: Mapping[str, Any] | None) -> str | None:
    return value.get("sha256") if _has_hash(value) else None


def _has_normalized_units(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    normalized = value.get("normalized")
    return isinstance(normalized, Mapping) and bool(normalized)


def _has_declared_descriptor(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return bool(value)
    status = str(value.get("status", "")).lower()
    return status not in {"", "unavailable", "unknown", "not_attached"}


def _is_finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _list_of_mappings(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


__all__ = ["SCHEMA_VERSION", "build_simulation_sample_manifest"]
