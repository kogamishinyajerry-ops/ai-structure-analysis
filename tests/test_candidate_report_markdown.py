"""Tests for candidate_report_markdown — Tier 1 spine → Markdown renderer.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.services.candidate_report_markdown import (  # noqa: E402
    _affirmative_forbidden_hits,
    render_candidate_report,
)


def _full_spine() -> dict:
    """A spine populated like the FM-04a synthetic pipeline produces."""
    return {
        "schema_version": "fm03-candidate-report-spine.v2",
        "generated_at_utc": "2026-05-10T08:00:00+00:00",
        "claim_tier": "Tier 1 engineering candidate",
        "allowed_claim": "engineering candidate, not signed validation",
        "no_overclaim": "not signed validation",
        "case": {
            "case_id": "CASE-FM04A-RENDERTEST",
            "case_name": "render-test fixture",
            "expected_results_status": "insufficient_evidence",
            "status_reason": "synthetic candidate; Tier 2 promotion deferred to FM-04b",
            "failure_pattern_ref": "not surfaced",
        },
        "provenance": {
            "report_surface": "POST /api/v1/report/generate",
            "parser": "FRDParser",
            "result_file_name": "gs001_result.frd",
            "original_filename": "gs001_result.frd",
            "file_size_bytes": 16568,
            "parse_time_s": 0.00124,
            "is_binary_frd": False,
            "node_count": 44,
            "element_count": 10,
            "increment_count": 2,
            "solver_truth_source": "CalculiX FRD artifact",
        },
        "solver": {
            "truth_source": "CalculiX artifact",
            "latest_job_id": None,
            "latest_job_status": None,
            "normal_termination_state": "unavailable",
            "logs": {
                "status": "unavailable",
                "line_count": 0,
                "tail": [],
                "artifact_paths": [],
                "unavailable_reason": "no solver job logs visible",
            },
        },
        "assumptions": {
            "unit_system": {
                "status": "partially_declared",
                "stress_unit": "MPa per ReportGenerator convention",
                "length_unit": "model-dependent",
            },
            "material": {
                "status": "unavailable",
                "unavailable_reason": "material source not declared",
            },
            "boundary_conditions": {
                "status": "unavailable",
                "unavailable_reason": "BC not surfaced",
            },
            "contact": {
                "status": "unavailable",
                "unavailable_reason": "contact not surfaced",
            },
        },
        "mesh_evidence": {
            "status": "partial",
            "claim_impact": "mesh topology surfaced for Tier 1 reproducibility only",
            "result_mesh": {
                "source": "FRDParser",
                "node_count": 44,
                "element_count": 10,
                "increment_count": 2,
            },
            "input_deck": {
                "status": "available",
                "path": "project_state/synthetic_cases/CASE-FM04A-RENDERTEST/model.inp",
                "node_count": 1,
                "element_count": 1,
                "include_count": 0,
                "element_types": {"C3D4": 1},
            },
            "metadata": {
                "status": "unavailable",
                "artifacts": [],
                "unavailable_reason": "no mesh_meta.json visible",
            },
            "quality": {
                "status": "unavailable",
                "source": None,
                "metrics": {},
                "artifact_count": 0,
                "unavailable_reason": "mesh quality artifact not attached",
            },
            "convergence_study": {
                "status": "available",
                "source": (
                    "project_state/graph_executor/CASE-FM04A-RENDERTEST/mesh/mesh_convergence.json"
                ),
                "study_status": "candidate_observed",
                "parameter": "mesh_level",
                "metric": "max_plastic_strain",
                "tolerance_pct": 5.0,
                "relative_change_pct": 0.689655,
                "candidate_stability": "candidate_observed_stable",
                "run_count": 3,
                "runs": [
                    {"label": "coarse", "parameter_value": 0.0, "metric_value": 0.42},
                    {"label": "medium", "parameter_value": 1.0, "metric_value": 0.435},
                    {"label": "fine", "parameter_value": 2.0, "metric_value": 0.438},
                ],
                "claim_boundary": "tier1_engineering_candidate; not_signed_validation",
                "claim_impact": "Tier 1 candidate convergence evidence only",
            },
        },
        "convergence_evidence": {
            "status": "unavailable",
            "claim_impact": "solver status surfaced for Tier 1 review only",
            "normal_termination": "unavailable",
            "latest_job_status": None,
            "source_artifacts": [],
            "mesh_refinement_study": {"status": "available"},
            "signals": [],
            "missing_reasons": [
                "CalculiX .sta normal-termination artifact is not attached",
                "no solver job status visible",
            ],
        },
        "ballistic": {
            "status": "candidate_observed",
            "claim_impact": "Tier 1 candidate ballistic evidence only",
            "claim_boundary": (
                "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"
            ),
            "projectile_initial_velocity": {
                "status": "declared",
                "value_m_per_s": 285.0,
                "source": "ballistic_metrics.json",
            },
            "residual_velocity_candidate": {
                "status": "candidate_observed",
                "value_m_per_s": 142.0,
                "extraction_source": "project_state/.../ballistic_metrics.json",
                "claim_impact": "Tier 1 candidate ballistic evidence only",
            },
            "perforation_marker": {
                "status": "perforated_candidate",
                "evidence_path": "project_state/.../ballistic_metrics.json",
                "claim_impact": "Tier 1 candidate ballistic evidence only",
            },
            "energy_balance_candidate": {
                "status": "available",
                "source": "project_state/.../ballistic_metrics.json",
                "initial_kinetic_energy_j": 812.0,
                "plastic_dissipation_j": 540.0,
                "contact_friction_j": 40.0,
                "hourglass_energy_j": 20.0,
                "residual_kinetic_energy_j": 212.0,
                "energy_ratio": 1.0,
                "claim_impact": "Tier 1 health indicator only",
            },
            "animation_manifest": {"status": "unavailable", "unavailable_reason": "no manifest"},
            "time_step_series_summary": {
                "status": "unavailable",
                "unavailable_reason": "no series",
            },
            "time_step_convergence_study": {
                "status": "available",
                "source": "project_state/.../time_step_convergence.json",
                "study_status": "candidate_observed",
                "parameter": "time_step_dt",
                "metric": "residual_velocity_candidate_m_per_s",
                "tolerance_pct": 5.0,
                "relative_change_pct": 0.35461,
                "candidate_stability": "candidate_observed_stable",
                "run_count": 3,
                "runs": [
                    {"label": "dt_baseline", "parameter_value": 8e-9, "metric_value": 142.0},
                    {"label": "dt_half", "parameter_value": 4e-9, "metric_value": 141.0},
                    {"label": "dt_quarter", "parameter_value": 2e-9, "metric_value": 140.5},
                ],
                "claim_boundary": (
                    "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"
                ),
                "claim_impact": "Tier 1 candidate time-step convergence evidence only",
            },
            "tier2_blockers_ballistic": [
                "public ballistic benchmark/source not attached",
                "tolerance comparison vs benchmark residual velocity not attached",
                "independent reviewer/signoff for ballistic claim not attached",
                "this payload is explicitly not benchmark agreement and not signed validation",
            ],
        },
        "metrics": {
            "output_metric_keys": ["max_displacement", "max_von_mises", "safety_factor", "status"],
            "values": {
                "max_displacement": 0.49493543630539955,
                "max_von_mises": 0.0,
                "safety_factor": float("inf"),
                "status": "SAFE",
            },
            "extraction_command": "POST /api/v1/report/generate",
        },
        "validation": {"error_percentage": 0.0, "status": "N/A"},
        "artifact_manifest": {
            "manifest_id": "fm03-CASE-FM04A-RENDERTEST-abc123def456",
            "hash_algorithm": "sha256",
            "hash_count": 3,
            "items": [
                {
                    "kind": "ballistic_metrics",
                    "status": "available",
                    "path": "project_state/.../ballistic_metrics.json",
                    "file_name": "ballistic_metrics.json",
                    "size_bytes": 542,
                    "sha256": "a" * 64,
                    "description": "Ballistic candidate metrics sidecar",
                },
            ],
        },
        "limitations": [
            "not signed validation",
            "no public benchmark agreement is claimed",
            "independent reviewer/signoff is not attached",
        ],
        "reviewer_summary": {
            "verdict": "needs_review",
            "summary": (
                "Candidate spine is generated, but blockers must be resolved "
                "before stronger claims."
            ),
            "blocked_findings": [
                "synthetic candidate fixture; Tier 2 promotion deferred to FM-04b",
                "material provenance unavailable",
            ],
            "next_actions": [
                "attach reviewer/signoff evidence before any claim promotion",
                "attach convergence and benchmark evidence before Tier 2 signed validation",
            ],
        },
        "tier2_blockers": [
            "public benchmark/source is not attached",
            "Tier 2 tolerance comparison and signed convergence evidence are not attached",
            "independent reviewer/signoff is not attached",
            "this payload is explicitly not signed validation",
        ],
    }


# ---------------------------------------------------------------------------


def test_renders_full_spine_to_markdown() -> None:
    md = render_candidate_report(_full_spine())

    # Header surfaces case + claim tier verbatim
    assert "# Candidate Report — render-test fixture" in md
    assert "Tier 1 engineering candidate" in md
    assert "case_id`: `CASE-FM04A-RENDERTEST`" in md or "`CASE-FM04A-RENDERTEST`" in md

    # Each top-level section appears
    for header in (
        "## Case",
        "## Provenance",
        "## Solver",
        "## Assumptions",
        "## Mesh evidence",
        "## Solver-side convergence evidence",
        "## Ballistic candidate evidence",
        "## Metrics",
        "## Artifact manifest",
        "## Limitations",
        "## Reviewer summary",
        "## Tier 2 blockers (always present at Tier 1)",
    ):
        assert header in md, f"missing section: {header}"


def test_renders_ballistic_payload_values() -> None:
    md = render_candidate_report(_full_spine())
    assert "285" in md  # V0
    assert "142" in md  # vR
    assert "perforated_candidate" in md
    assert "candidate_observed_stable" in md  # both convergence studies
    assert "energy_ratio" in md and "1" in md
    # Time-step refinement runs render
    assert "dt_baseline" in md
    assert "dt_quarter" in md


def test_renders_mesh_convergence_runs() -> None:
    md = render_candidate_report(_full_spine())
    assert "coarse" in md and "fine" in md
    assert "max_plastic_strain" in md


def test_no_affirmative_forbidden_claims() -> None:
    """Forbidden phrases may appear in negation/precondition contexts
    ("not benchmark agreement", "before Tier 2 signed validation"). They
    must NEVER appear as bare affirmative claims.
    """
    md = render_candidate_report(_full_spine())
    hits = _affirmative_forbidden_hits(md)
    assert hits == [], f"renderer leaked affirmative forbidden claims: {hits!r}"


def test_forbidden_phrases_present_only_in_negation_context() -> None:
    """Sanity: spine *does* legitimately mention forbidden phrases in
    Tier 2-blocker / claim-boundary lines. Confirm at least one such
    legitimate occurrence exists, so the affirmative-only check above
    isn't trivially passing on a renderer that drops the boundary text
    entirely."""
    md = render_candidate_report(_full_spine()).lower()
    # "not signed validation" and "not benchmark agreement" are both
    # required Tier 1 boundary phrases.
    assert "not signed validation" in md
    assert "not benchmark agreement" in md


def test_required_boundary_tokens_present() -> None:
    md = render_candidate_report(_full_spine())
    assert "Tier 1 engineering candidate" in md
    assert "not signed validation" in md


def test_unavailable_blocks_render_reason() -> None:
    md = render_candidate_report(_full_spine())
    # Material is unavailable in the fixture
    assert "material source not declared" in md
    # Solver logs unavailable
    assert "no solver job logs visible" in md
    # Mesh quality unavailable
    assert "mesh quality artifact not attached" in md


def test_empty_optional_sections_omitted() -> None:
    """Spine without optional sections should still render header + required boundary."""
    minimal = {
        "schema_version": "fm03-candidate-report-spine.v2",
        "claim_tier": "Tier 1 engineering candidate",
        "no_overclaim": "not signed validation",
        "case": {"case_id": "minimal", "case_name": "minimal"},
        "tier2_blockers": ["this payload is explicitly not signed validation"],
    }
    md = render_candidate_report(minimal)
    assert "# Candidate Report — minimal" in md
    assert "Tier 1 engineering candidate" in md
    assert "not signed validation" in md
    # No ballistic block when ballistic key absent
    assert "## Ballistic candidate evidence" not in md


def test_rejects_unknown_schema_version() -> None:
    with pytest.raises(ValueError, match="unsupported spine schema_version"):
        render_candidate_report({"schema_version": "some-other-spine.v1"})


def test_renderer_raises_when_required_boundary_missing() -> None:
    bad = {
        "schema_version": "fm03-candidate-report-spine.v2",
        "claim_tier": "Tier 7 cosmic agreement",  # drops both required tokens
        "no_overclaim": "all good vibes",
        "case": {"case_id": "X", "case_name": "X"},
    }
    with pytest.raises(ValueError, match="omitted required Tier 1 boundary tokens"):
        render_candidate_report(bad)


def test_renderer_raises_when_forbidden_phrase_appears() -> None:
    bad = _full_spine()
    bad["reviewer_summary"]["summary"] = "This run achieves benchmark agreement."
    with pytest.raises(ValueError, match="forbidden Tier-2 wording"):
        render_candidate_report(bad)
