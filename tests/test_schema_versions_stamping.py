"""Schema-version stamping audit (FM-04a Phase 5 A).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

This file enforces the binding rubric anti-gaming guard from
``.planning/FM-04A_PHASE5_BLUEPRINT.md``:

    B: -2 per missing ``schema_version`` field on a new output
    T: -2 per missing ``schema_version`` assertion in any new builder test

Every Tier 1 candidate JSON contract MUST stamp the constant from
``app.services.reporting._schema_versions``. If a builder forgets to
stamp, the matching assertion below trips and the score regresses.

We deliberately keep ONE central file rather than scattering assertions
across the six existing builder tests, because the rubric is auditable
in one place and the contracts are central in one module already
(``_schema_versions.py``). A future maintainer who renames or removes
a constant will trip this file immediately and is forced to update
the rubric in lockstep.
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest
from app.services.ballistics.convergence_orchestrator import (
    ConvergenceStudyInput,
    ConvergenceStudyRow,
    build_convergence_study,
)
from app.services.reporting._schema_versions import (
    ACCEPTANCE_PACKET_SCHEMA_VERSION,
    ARCHIVED_PACKET_DIFF_SCHEMA_VERSION,
    CASE_COMPARISON_SCHEMA_VERSION,
    CASE_COMPLETENESS_SCHEMA_VERSION,
    COHORT_OVERVIEW_SCHEMA_VERSION,
    COMPLETENESS_RUBRIC_VERSION,
    CONVERGENCE_STUDY_SCHEMA_VERSION,
    REVIEWER_BUNDLE_MANIFEST_SCHEMA_VERSION,
)
from app.services.reporting.acceptance_packet import (
    AcceptancePacketInputs,
    build_acceptance_packet,
    render_acceptance_packet_json,
)
from app.services.reporting.archived_packet_diff import (
    diff_archived_packets,
    render_archived_packet_diff_json,
)
from app.services.reporting.case_comparison import (
    build_case_comparison,
    render_case_comparison_json,
)
from app.services.reporting.case_completeness import (
    CaseCompletenessInputs,
    render_case_completeness_json,
    score_case_completeness,
)
from app.services.reporting.cohort_overview import (
    build_cohort_overview,
    render_cohort_overview_json,
)
from app.services.reporting.reviewer_bundle import (
    ReviewerBundleInputs,
    build_reviewer_bundle,
)

# ---------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------


def _write_metrics(tmp_path: Path, case_id: str = "GS-102-schema-stamp") -> Path:
    payload = {
        "case_id": case_id,
        "projectile_initial_velocity_m_per_s": 300.0,
        "perforation": {
            "marker": "candidate_perforation",
            "residual_velocity_m_per_s": 75.0,
        },
        "energy_audit": {
            "status": "closed_aggregate",
            "energy_balance_error_pct": 12.0,
        },
        "claim_boundary": (
            "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"
        ),
        "extraction_metadata": {
            "projectile_mass_kg": 0.197,
            "plate_thickness_m": 0.012,
            "impact_axis": "x",
        },
    }
    path = tmp_path / "ballistic_metrics.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _write_convergence(tmp_path: Path) -> Path:
    payload = {
        "case_id": "GS-102-schema-stamp",
        "study_metric": "residual_velocity_m_per_s",
        "tolerance_pct": 5.0,
        "combined_verdict": "candidate_observed_stable",
        "mesh_sweep": {"runs": [], "candidate_stability": "candidate_observed_stable"},
        "dt_sweep": {"runs": [], "candidate_stability": "candidate_observed_stable"},
        "row_count": 0,
        "rows": [],
        "claim_boundary": (
            "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"
        ),
        "energy_balance_observation": {"status": "closed_aggregate"},
    }
    path = tmp_path / "convergence_study.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _build_packet(tmp_path: Path, case_id: str = "GS-102-schema-stamp"):
    metrics_path = _write_metrics(tmp_path, case_id=case_id)
    convergence_path = _write_convergence(tmp_path)
    return build_acceptance_packet(
        AcceptancePacketInputs(
            case_id=case_id,
            repo_root=tmp_path,
            ballistic_metrics_path=metrics_path,
            convergence_study_path=convergence_path,
        )
    )


# ---------------------------------------------------------------------
# schema-version stamping assertions
# ---------------------------------------------------------------------


def test_acceptance_packet_stamps_schema_version(tmp_path: Path) -> None:
    packet = _build_packet(tmp_path)
    rendered = json.loads(render_acceptance_packet_json(packet))
    assert rendered["schema_version"] == ACCEPTANCE_PACKET_SCHEMA_VERSION


def test_case_completeness_stamps_schema_and_rubric_version(tmp_path: Path) -> None:
    metrics_path = _write_metrics(tmp_path)
    convergence_path = _write_convergence(tmp_path)
    score = score_case_completeness(
        CaseCompletenessInputs(
            case_id="GS-102-schema-stamp",
            starter_deck_path=tmp_path / "starter.rad",
            engine_deck_path=tmp_path / "engine.rad",
            ballistic_metrics_path=metrics_path,
            convergence_study_path=convergence_path,
            animation_manifest_path=None,
            result_mesh_path=None,
            generator_script_path=None,
            notes_path=None,
        )
    )
    rendered = json.loads(render_case_completeness_json(score))
    assert rendered["schema_version"] == CASE_COMPLETENESS_SCHEMA_VERSION
    assert rendered["rubric_version"] == COMPLETENESS_RUBRIC_VERSION


def test_cohort_overview_stamps_schema_version(tmp_path: Path) -> None:
    # empty cohort still emits schema_version
    overview = build_cohort_overview(repo_root=tmp_path)
    rendered = json.loads(render_cohort_overview_json(overview))
    assert rendered["schema_version"] == COHORT_OVERVIEW_SCHEMA_VERSION


def test_case_comparison_stamps_schema_version(tmp_path: Path) -> None:
    a_dir = tmp_path / "a"
    b_dir = tmp_path / "b"
    a_dir.mkdir()
    b_dir.mkdir()
    packet_a = _build_packet(a_dir, case_id="GS-A-schema-stamp")
    packet_b = _build_packet(b_dir, case_id="GS-B-schema-stamp")
    cmp_obj = build_case_comparison(packet_a, packet_b)
    rendered = json.loads(render_case_comparison_json(cmp_obj))
    assert rendered["schema_version"] == CASE_COMPARISON_SCHEMA_VERSION


def test_archived_packet_diff_stamps_schema_version(tmp_path: Path) -> None:
    # write two acceptance packets under reports/ and diff them
    reports_a = tmp_path / "reports" / "case_a"
    reports_b = tmp_path / "reports" / "case_b"
    reports_a.mkdir(parents=True)
    reports_b.mkdir(parents=True)

    packet_a = _build_packet(tmp_path, case_id="GS-A-schema-stamp")
    packet_b = _build_packet(tmp_path, case_id="GS-B-schema-stamp")
    (reports_a / "acceptance_packet.json").write_text(
        render_acceptance_packet_json(packet_a), encoding="utf-8"
    )
    (reports_b / "acceptance_packet.json").write_text(
        render_acceptance_packet_json(packet_b), encoding="utf-8"
    )

    diff = diff_archived_packets(
        reports_a / "acceptance_packet.json",
        reports_b / "acceptance_packet.json",
        repo_root=tmp_path,
    )
    rendered = json.loads(render_archived_packet_diff_json(diff))
    assert rendered["schema_version"] == ARCHIVED_PACKET_DIFF_SCHEMA_VERSION


def test_reviewer_bundle_manifest_stamps_schema_version(tmp_path: Path) -> None:
    metrics_path = _write_metrics(tmp_path)
    starter = tmp_path / "starter.rad"
    engine = tmp_path / "engine.rad"
    starter.write_text("# starter deck", encoding="utf-8")
    engine.write_text("# engine deck", encoding="utf-8")

    case = ReviewerBundleInputs(
        case_id="GS-102-schema-stamp",
        starter_deck_path=starter,
        engine_deck_path=engine,
        ballistic_metrics_path=metrics_path,
        convergence_study_path=_write_convergence(tmp_path),
        animation_manifest_path=None,
        result_mesh_path=None,
        generator_script_path=None,
        notes_path=None,
    )
    bundle_bytes = build_reviewer_bundle([case], repo_root=tmp_path)
    with zipfile.ZipFile(io.BytesIO(bundle_bytes)) as zf:
        manifest = json.loads(zf.read("BUNDLE_MANIFEST.json").decode("utf-8"))
    assert manifest["schema_version"] == REVIEWER_BUNDLE_MANIFEST_SCHEMA_VERSION


def test_convergence_orchestrator_stamps_schema_version() -> None:
    payload = build_convergence_study(
        ConvergenceStudyInput(
            case_id="GS-102-schema-stamp",
            rows=[
                ConvergenceStudyRow(
                    mesh_label="coarse",
                    mesh_axis_value=2.0e-3,
                    dt_label="1us",
                    dt_axis_value=1.0e-6,
                    residual_velocity_m_per_s=75.0,
                ),
                ConvergenceStudyRow(
                    mesh_label="fine",
                    mesh_axis_value=1.0e-3,
                    dt_label="1us",
                    dt_axis_value=1.0e-6,
                    residual_velocity_m_per_s=76.0,
                ),
            ],
        )
    )
    assert payload["schema_version"] == CONVERGENCE_STUDY_SCHEMA_VERSION


# ---------------------------------------------------------------------
# negative guard: constants do not drift silently
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "constant_name,expected",
    [
        ("ACCEPTANCE_PACKET_SCHEMA_VERSION", "1.0.0"),
        ("CASE_COMPLETENESS_SCHEMA_VERSION", "1.2.0"),  # Phase 12 B MINOR (modal substantiation)
        ("COHORT_OVERVIEW_SCHEMA_VERSION", "1.0.0"),
        ("CASE_COMPARISON_SCHEMA_VERSION", "1.0.0"),
        ("ARCHIVED_PACKET_DIFF_SCHEMA_VERSION", "1.0.0"),
        ("REVIEWER_BUNDLE_MANIFEST_SCHEMA_VERSION", "1.0.0"),
        ("CONVERGENCE_STUDY_SCHEMA_VERSION", "1.2.0"),  # Phase 12 A MINOR (modal axis)
        ("COMPLETENESS_RUBRIC_VERSION", "1.0.0"),
        ("ADVISOR_CRITIQUE_SCHEMA_VERSION", "1.1.0"),  # Phase 13 A MINOR (refused_claims field)
    ],
)
def test_schema_version_constants_match_phase5_starting_baseline(
    constant_name: str, expected: str
) -> None:
    """Pin each starting constant to ``"1.0.0"``.

    A future PR raising any of these MUST update the parametrization here
    in lockstep, and the SCORECARD line on that commit MUST cite the bump
    category (MAJOR / MINOR / PATCH) per the documented bump policy in
    ``_schema_versions.py``.
    """
    from app.services.reporting import _schema_versions as sv

    assert getattr(sv, constant_name) == expected
