"""Tests for reusable analysis recipe descriptors.

Tier 1 engineering-candidate infrastructure only; not signed validation.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.services.analysis_recipes import (  # noqa: E402
    STATIC_STRUCTURAL_CALCULIX_RECIPE_ID,
    build_static_structural_calculix_recipe_attachment,
)


def _artifact(role: str, sha_prefix: str = "a") -> dict:
    return {
        "status": "available",
        "role": role,
        "path": f"project_state/runs/CASE-001/{role}",
        "sha256": sha_prefix * 64,
    }


def _complete_context() -> dict:
    return {
        "case": {
            "case_id": "CASE-001",
            "case_family": "static_structural",
        },
        "solver": {
            "solver_name": "calculix",
            "solver_version": "CalculiX 2.21",
            "job_status": "COMPLETED",
        },
        "inputs": {
            "input_deck": _artifact("input_deck", "i"),
            "result_file": _artifact("result_frd", "r"),
        },
        "physics_setup": {
            "unit_system": {
                "status": "declared",
                "normalized": {"length": "mm", "stress": "MPa"},
            },
            "materials": {"status": "declared", "source": "material card"},
            "boundary_conditions": {"status": "declared", "source": "bc card"},
        },
        "metrics": {
            "max_displacement": 0.12,
            "max_von_mises": 123.4,
            "safety_factor": 2.8,
        },
    }


def test_static_structural_calculix_recipe_attaches_when_evidence_is_complete() -> None:
    context = _complete_context()

    recipe = build_static_structural_calculix_recipe_attachment(**context)

    assert recipe["recipe_id"] == STATIC_STRUCTURAL_CALCULIX_RECIPE_ID
    assert recipe["recipe_version"] == "v1"
    assert recipe["recipe_status"] == "attached"
    assert recipe["recipe_inputs_complete"] is True
    assert recipe["case_family"] == "static_structural"
    assert recipe["solver_family"] == "calculix"
    assert recipe["preflight_status"] == "passed"
    assert recipe["missing_inputs"] == []
    assert recipe["allowed_claim"] == (
        "engineering candidate analysis recipe, not signed validation"
    )


def test_static_structural_calculix_recipe_reports_incomplete_evidence() -> None:
    context = _complete_context()
    context["case"]["case_id"] = "uploaded-artifact"
    context["solver"]["solver_version"] = None
    context["solver"]["job_status"] = None
    context["inputs"]["input_deck"] = {"status": "unavailable", "role": "input_deck"}
    context["physics_setup"]["unit_system"] = {"status": "declared"}
    context["physics_setup"]["materials"] = {"status": "unavailable"}

    recipe = build_static_structural_calculix_recipe_attachment(**context)

    assert recipe["recipe_id"] == STATIC_STRUCTURAL_CALCULIX_RECIPE_ID
    assert recipe["recipe_status"] == "incomplete"
    assert recipe["recipe_inputs_complete"] is False
    assert recipe["preflight_status"] == "failed"
    assert recipe["missing_inputs"] == [
        "stable_case_id",
        "input_deck_hash",
        "solver_version",
        "unit_system_normalization",
        "material_descriptor",
        "runtime_status",
    ]


def test_static_structural_calculix_recipe_abstains_outside_scope() -> None:
    context = _complete_context()
    context["case"]["case_family"] = "ballistic_candidate"
    context["solver"]["solver_name"] = "openradioss"

    recipe = build_static_structural_calculix_recipe_attachment(**context)

    assert recipe["recipe_id"] is None
    assert recipe["recipe_status"] == "not_attached"
    assert recipe["recipe_inputs_complete"] is False
    assert recipe["preflight_status"] == "not_applicable"
    assert recipe["not_attached_reason"] == (
        "static_structural_calculix_candidate.v1 applies only to "
        "static_structural CalculiX candidate evidence"
    )
