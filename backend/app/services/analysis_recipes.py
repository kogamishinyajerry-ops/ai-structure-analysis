"""Reusable analysis recipe descriptors.

Recipes capture narrow engineering setup contracts for candidate evidence.
They do not run solvers, mutate inputs, change public schemas, or promote
Tier 1 evidence to signed validation.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

STATIC_STRUCTURAL_CALCULIX_RECIPE_ID = "static_structural_calculix_candidate.v1"
STATIC_STRUCTURAL_CALCULIX_RECIPE_VERSION = "v1"
ANALYSIS_RECIPE_ALLOWED_CLAIM = (
    "engineering candidate analysis recipe, not signed validation"
)

_NOT_ATTACHED_REASON = (
    "static_structural_calculix_candidate.v1 applies only to "
    "static_structural CalculiX candidate evidence"
)


def build_static_structural_calculix_recipe_attachment(
    *,
    case: Mapping[str, Any],
    solver: Mapping[str, Any],
    inputs: Mapping[str, Mapping[str, Any]],
    physics_setup: Mapping[str, Any],
    metrics: Mapping[str, Any],
) -> dict[str, Any]:
    """Return recipe attachment metadata for a static CalculiX candidate.

    The recipe attaches only to static structural CalculiX evidence. Eligible
    but incomplete evidence receives an ``incomplete`` status rather than being
    silently treated as training-ready.
    """

    case_family = str(case.get("case_family") or "unknown")
    solver_family = _solver_family(solver)
    if case_family != "static_structural" or solver_family != "calculix":
        return {
            "recipe_id": None,
            "recipe_version": None,
            "recipe_status": "not_attached",
            "recipe_inputs_complete": False,
            "case_family": case_family,
            "solver_family": solver_family,
            "preflight_status": "not_applicable",
            "missing_inputs": [],
            "not_attached_reason": _NOT_ATTACHED_REASON,
        }

    missing_inputs = _missing_static_calculix_inputs(
        case=case,
        solver=solver,
        inputs=inputs,
        physics_setup=physics_setup,
        metrics=metrics,
    )
    complete = not missing_inputs

    return {
        "recipe_id": STATIC_STRUCTURAL_CALCULIX_RECIPE_ID,
        "recipe_version": STATIC_STRUCTURAL_CALCULIX_RECIPE_VERSION,
        "recipe_status": "attached" if complete else "incomplete",
        "recipe_inputs_complete": complete,
        "case_family": "static_structural",
        "solver_family": "calculix",
        "preflight_status": "passed" if complete else "failed",
        "missing_inputs": missing_inputs,
        "allowed_claim": ANALYSIS_RECIPE_ALLOWED_CLAIM,
    }


def _missing_static_calculix_inputs(
    *,
    case: Mapping[str, Any],
    solver: Mapping[str, Any],
    inputs: Mapping[str, Mapping[str, Any]],
    physics_setup: Mapping[str, Any],
    metrics: Mapping[str, Any],
) -> list[str]:
    missing: list[str] = []
    if not _has_stable_case_id(case):
        missing.append("stable_case_id")
    if not _has_hash(inputs.get("input_deck")):
        missing.append("input_deck_hash")
    if not _has_hash(inputs.get("result_file")):
        missing.append("result_file_hash")
    if not solver.get("solver_version"):
        missing.append("solver_version")
    if not _has_normalized_units(physics_setup.get("unit_system")):
        missing.append("unit_system_normalization")
    if not _has_declared_descriptor(physics_setup.get("materials")):
        missing.append("material_descriptor")
    if not _has_declared_descriptor(physics_setup.get("boundary_conditions")):
        missing.append("boundary_condition_descriptor")
    if not solver.get("job_status"):
        missing.append("runtime_status")
    if not any(_is_finite_number(value) for value in metrics.values()):
        missing.append("static_kpi_metric")
    return missing


def _solver_family(solver: Mapping[str, Any]) -> str:
    solver_name = str(solver.get("solver_name") or "").lower()
    solver_backend = str(solver.get("solver_backend") or "").lower()
    truth_source = str(solver.get("truth_source") or "").lower()
    combined = f"{solver_name} {solver_backend} {truth_source}"
    if "calculix" in combined:
        return "calculix"
    if "openradioss" in combined or "radioss" in combined:
        return "openradioss"
    return solver_name or "unknown"


def _has_stable_case_id(case: Mapping[str, Any]) -> bool:
    case_id = str(case.get("case_id") or "").strip().lower()
    return case_id not in {"", "unknown", "uploaded-artifact"}


def _has_hash(value: Mapping[str, Any] | None) -> bool:
    return bool(value and isinstance(value.get("sha256"), str) and len(value["sha256"]) == 64)


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


__all__ = [
    "ANALYSIS_RECIPE_ALLOWED_CLAIM",
    "STATIC_STRUCTURAL_CALCULIX_RECIPE_ID",
    "STATIC_STRUCTURAL_CALCULIX_RECIPE_VERSION",
    "build_static_structural_calculix_recipe_attachment",
]
