"""Phase 12 B — modal advisor concerns + modal rubric substantiation.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Pins binding rubric from `.planning/FM-04A_PHASE12_BLUEPRINT.md` §3.B
and the slice-B anti-gaming guards:

* **M:-2**: every modal-rubric weight is a named module-level constant;
  the substantiated modal rubric sum is boundary-pinned.
* **T:-3**: each modal-axis partial-credit boundary is independently
  tested (full / half / zero on each of mode_count_coverage,
  freq_convergence, mode_shape_quality, mass_participation).
* **T:-5**: modal advisor branch surfaces four NAMED concerns; each
  named concern is independently asserted.
* **C:-8**: every modal critique still carries the Tier 1 disclaimer
  trio + no forbidden tokens (re-audited after schema bump).
* **A:-6**: advisor branch reads `context.extra["mode_count_target"]`
  through to the produced concern — closes Phase 11 retro §2.
* **E:-2**: CASE_COMPLETENESS_SCHEMA_VERSION 1.2.0 baseline pin
  (Phase 12 B MINOR bump) lives in the central
  ``tests/test_schema_versions_stamping.py``.

This file ALSO closes the slice-A TAA MEDIUM finding by adding direct
behavioral tests for the trust_score `convergence_kind == "modal"`
branch (stable / unstable / inconclusive / absent → raw_score +
rationale assertions).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from app.services.reporting.advisor_critique import (
    AdvisorContext,
    StubAdvisor,
)
from app.services.reporting.case_completeness import (
    ANALYSIS_TYPE_RUBRIC_WEIGHTS,
    WEIGHT_BALLISTIC_METRICS_MODAL,
    WEIGHT_CONVERGENCE_STABLE_MODAL,
    WEIGHT_ENERGY_AUDIT_CLOSED_MODAL,
    WEIGHT_ENGINE_DECK_MODAL,
    WEIGHT_FREQ_CONVERGENCE,
    WEIGHT_MASS_PARTICIPATION,
    WEIGHT_MODE_COUNT_COVERAGE,
    WEIGHT_MODE_SHAPE_QUALITY,
    WEIGHT_STARTER_DECK_MODAL,
    CaseCompletenessInputs,
    score_case_completeness,
)
from app.services.reporting.trust_score import _score_convergence_axis

# ---------------------------------------------------------------------
# Modal rubric substantiation — weight constants + sum boundary
# ---------------------------------------------------------------------


def test_modal_rubric_named_constants_match_blueprint_spec() -> None:
    """Phase 12 blueprint §3.B pins the four modal-specific weights;
    they must NOT drift silently from a future PR. SSOT for the
    methodology doc."""
    assert WEIGHT_MODE_COUNT_COVERAGE == 15
    assert WEIGHT_FREQ_CONVERGENCE == 15
    assert WEIGHT_MODE_SHAPE_QUALITY == 10
    assert WEIGHT_MASS_PARTICIPATION == 10


def test_modal_universal_axes_all_ten() -> None:
    """Phase 12 blueprint §3.B: universal axes rebalanced to 10 each
    so the four modal-specific axes can carry 50 pts."""
    assert WEIGHT_STARTER_DECK_MODAL == 10
    assert WEIGHT_ENGINE_DECK_MODAL == 10
    assert WEIGHT_BALLISTIC_METRICS_MODAL == 10
    assert WEIGHT_ENERGY_AUDIT_CLOSED_MODAL == 10
    assert WEIGHT_CONVERGENCE_STABLE_MODAL == 10


def test_modal_rubric_sum_is_100() -> None:
    """Anti-gaming guard M:-2: the substantiated modal rubric must
    sum to 100, audited at import time by
    ``_assert_rubric_weights_consistent``. We pin here for an explicit
    test failure that names the modal type rather than a runtime
    RuntimeError on import (which is harder to triage)."""
    assert sum(ANALYSIS_TYPE_RUBRIC_WEIGHTS["modal"].values()) == 100


def test_modal_rubric_axis_keys_match_substantiation() -> None:
    """The modal rubric drops ballistic optional artifacts and adds
    four modal-specific axes. Any future PR that adds/removes a key
    here must update this test in lockstep."""
    keys = set(ANALYSIS_TYPE_RUBRIC_WEIGHTS["modal"].keys())
    assert keys == {
        "starter_deck",
        "engine_deck",
        "ballistic_metrics",
        "energy_audit",
        "convergence_study",
        "mode_count_coverage",
        "freq_convergence",
        "mode_shape_quality",
        "mass_participation",
    }
    # Verify ballistic optional artifacts dropped.
    assert "animation_manifest" not in keys
    assert "result_mesh" not in keys
    assert "notes" not in keys
    assert "generator_script" not in keys


# ---------------------------------------------------------------------
# Modal-specific completeness scoring — per-axis boundary tests (T:-3)
# ---------------------------------------------------------------------


def _write_modal_metrics(
    tmp_path: Path,
    *,
    modal_summary: dict[str, Any] | None,
    case_id: str = "modal-cantilever-candidate",
    energy_audit_status: str = "closed_aggregate",
) -> Path:
    payload: dict[str, Any] = {
        "case_id": case_id,
        "energy_audit": {"status": energy_audit_status},
    }
    if modal_summary is not None:
        payload["modal_summary"] = modal_summary
    metrics = tmp_path / "ballistic_metrics.json"
    metrics.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return metrics


def _write_modal_convergence(
    tmp_path: Path, *, case_id: str = "modal-cantilever-candidate"
) -> Path:
    payload = {
        "case_id": case_id,
        "study_metric": "dominant_mode_freq_hz",
        "combined_verdict": "candidate_observed_stable",
        "convergence_kind": "modal",
        "mode_count_sweep": {"candidate_stability": "candidate_observed_stable"},
        "rows": [],
        "claim_boundary": (
            "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"
        ),
    }
    convergence = tmp_path / "convergence_study.json"
    convergence.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return convergence


def _modal_inputs(
    tmp_path: Path,
    metrics_path: Path,
    convergence_path: Path,
) -> CaseCompletenessInputs:
    starter = tmp_path / "starter.rad"
    starter.write_text("# starter deck", encoding="utf-8")
    engine = tmp_path / "engine.rad"
    engine.write_text("# engine deck", encoding="utf-8")
    return CaseCompletenessInputs(
        case_id="modal-cantilever-candidate",
        starter_deck_path=starter,
        engine_deck_path=engine,
        ballistic_metrics_path=metrics_path,
        convergence_study_path=convergence_path,
        animation_manifest_path=None,
        result_mesh_path=None,
        generator_script_path=None,
        notes_path=None,
        analysis_type="modal",
    )


def _find_axis(score, label: str):
    for entry in score.breakdown:
        if entry.label == label:
            return entry
    raise AssertionError(f"axis {label!r} not in breakdown")


# mode_count_coverage axis: full / half / zero boundary triplet.
def test_mode_count_coverage_full_credit_at_80pct_floor() -> None:
    tmp_path = Path(__import__("tempfile").mkdtemp())
    metrics = _write_modal_metrics(
        tmp_path,
        modal_summary={
            "mode_count_coverage": {"cumulative_y_pct": 80.0, "cumulative_z_pct": 85.0},
        },
    )
    convergence = _write_modal_convergence(tmp_path)
    score = score_case_completeness(_modal_inputs(tmp_path, metrics, convergence))
    entry = _find_axis(score, "mode_count_coverage")
    assert entry.points_awarded == WEIGHT_MODE_COUNT_COVERAGE
    assert entry.evidence_status == "above_engineering_floor"


def test_mode_count_coverage_half_credit_in_50_to_80_band() -> None:
    tmp_path = Path(__import__("tempfile").mkdtemp())
    metrics = _write_modal_metrics(
        tmp_path,
        modal_summary={
            "mode_count_coverage": {"cumulative_y_pct": 65.0, "cumulative_z_pct": 70.0},
        },
    )
    convergence = _write_modal_convergence(tmp_path)
    score = score_case_completeness(_modal_inputs(tmp_path, metrics, convergence))
    entry = _find_axis(score, "mode_count_coverage")
    assert entry.points_awarded == WEIGHT_MODE_COUNT_COVERAGE // 2
    assert entry.evidence_status == "partial_coverage"


def test_mode_count_coverage_zero_below_50pct() -> None:
    tmp_path = Path(__import__("tempfile").mkdtemp())
    metrics = _write_modal_metrics(
        tmp_path,
        modal_summary={
            "mode_count_coverage": {"cumulative_y_pct": 30.0, "cumulative_z_pct": 70.0},
        },
    )
    convergence = _write_modal_convergence(tmp_path)
    score = score_case_completeness(_modal_inputs(tmp_path, metrics, convergence))
    entry = _find_axis(score, "mode_count_coverage")
    assert entry.points_awarded == 0
    assert entry.evidence_status == "below_engineering_floor"


# freq_convergence axis: full / half / zero on |rel err| 1% / 5% / 5%+.
def test_freq_convergence_full_credit_at_1pct_floor() -> None:
    tmp_path = Path(__import__("tempfile").mkdtemp())
    metrics = _write_modal_metrics(
        tmp_path,
        modal_summary={
            "freq_convergence": {"dominant_mode_rel_err_pct": 0.5},
        },
    )
    convergence = _write_modal_convergence(tmp_path)
    score = score_case_completeness(_modal_inputs(tmp_path, metrics, convergence))
    entry = _find_axis(score, "freq_convergence")
    assert entry.points_awarded == WEIGHT_FREQ_CONVERGENCE
    assert entry.evidence_status == "converged_tight"


def test_freq_convergence_half_credit_in_1_to_5_band() -> None:
    tmp_path = Path(__import__("tempfile").mkdtemp())
    metrics = _write_modal_metrics(
        tmp_path,
        modal_summary={
            "freq_convergence": {"dominant_mode_rel_err_pct": 3.0},
        },
    )
    convergence = _write_modal_convergence(tmp_path)
    score = score_case_completeness(_modal_inputs(tmp_path, metrics, convergence))
    entry = _find_axis(score, "freq_convergence")
    assert entry.points_awarded == WEIGHT_FREQ_CONVERGENCE // 2
    assert entry.evidence_status == "converged_engineering"


def test_freq_convergence_zero_above_5pct() -> None:
    tmp_path = Path(__import__("tempfile").mkdtemp())
    metrics = _write_modal_metrics(
        tmp_path,
        modal_summary={
            "freq_convergence": {"dominant_mode_rel_err_pct": 7.5},
        },
    )
    convergence = _write_modal_convergence(tmp_path)
    score = score_case_completeness(_modal_inputs(tmp_path, metrics, convergence))
    entry = _find_axis(score, "freq_convergence")
    assert entry.points_awarded == 0
    assert entry.evidence_status == "exceeds_engineering_tolerance"


# mode_shape_quality axis: full / half / zero on MAC 0.95 / 0.80.
def test_mode_shape_quality_full_credit_at_0p95_floor() -> None:
    tmp_path = Path(__import__("tempfile").mkdtemp())
    metrics = _write_modal_metrics(
        tmp_path,
        modal_summary={
            "mode_shape_quality": {"dominant_mac": 0.97},
        },
    )
    convergence = _write_modal_convergence(tmp_path)
    score = score_case_completeness(_modal_inputs(tmp_path, metrics, convergence))
    entry = _find_axis(score, "mode_shape_quality")
    assert entry.points_awarded == WEIGHT_MODE_SHAPE_QUALITY
    assert entry.evidence_status == "well_resolved"


def test_mode_shape_quality_half_credit_in_0p80_to_0p95_band() -> None:
    tmp_path = Path(__import__("tempfile").mkdtemp())
    metrics = _write_modal_metrics(
        tmp_path,
        modal_summary={
            "mode_shape_quality": {"dominant_mac": 0.85},
        },
    )
    convergence = _write_modal_convergence(tmp_path)
    score = score_case_completeness(_modal_inputs(tmp_path, metrics, convergence))
    entry = _find_axis(score, "mode_shape_quality")
    assert entry.points_awarded == WEIGHT_MODE_SHAPE_QUALITY // 2
    assert entry.evidence_status == "adequately_resolved"


def test_mode_shape_quality_zero_below_0p80() -> None:
    tmp_path = Path(__import__("tempfile").mkdtemp())
    metrics = _write_modal_metrics(
        tmp_path,
        modal_summary={
            "mode_shape_quality": {"dominant_mac": 0.70},
        },
    )
    convergence = _write_modal_convergence(tmp_path)
    score = score_case_completeness(_modal_inputs(tmp_path, metrics, convergence))
    entry = _find_axis(score, "mode_shape_quality")
    assert entry.points_awarded == 0
    assert entry.evidence_status == "poorly_resolved"


# mass_participation axis: full / half / zero on 50% / 20%.
def test_mass_participation_full_credit_at_50pct_floor() -> None:
    tmp_path = Path(__import__("tempfile").mkdtemp())
    metrics = _write_modal_metrics(
        tmp_path,
        modal_summary={
            "mass_participation": {"dominant_mode_pct": 62.0},
        },
    )
    convergence = _write_modal_convergence(tmp_path)
    score = score_case_completeness(_modal_inputs(tmp_path, metrics, convergence))
    entry = _find_axis(score, "mass_participation")
    assert entry.points_awarded == WEIGHT_MASS_PARTICIPATION
    assert entry.evidence_status == "dominant_mode_significant"


def test_mass_participation_half_credit_in_20_to_50_band() -> None:
    tmp_path = Path(__import__("tempfile").mkdtemp())
    metrics = _write_modal_metrics(
        tmp_path,
        modal_summary={
            "mass_participation": {"dominant_mode_pct": 35.0},
        },
    )
    convergence = _write_modal_convergence(tmp_path)
    score = score_case_completeness(_modal_inputs(tmp_path, metrics, convergence))
    entry = _find_axis(score, "mass_participation")
    assert entry.points_awarded == WEIGHT_MASS_PARTICIPATION // 2
    assert entry.evidence_status == "dominant_mode_marginal"


def test_mass_participation_zero_below_20pct() -> None:
    tmp_path = Path(__import__("tempfile").mkdtemp())
    metrics = _write_modal_metrics(
        tmp_path,
        modal_summary={
            "mass_participation": {"dominant_mode_pct": 12.0},
        },
    )
    convergence = _write_modal_convergence(tmp_path)
    score = score_case_completeness(_modal_inputs(tmp_path, metrics, convergence))
    entry = _find_axis(score, "mass_participation")
    assert entry.points_awarded == 0
    assert entry.evidence_status == "dominant_mode_negligible"


# Missing modal_summary block → four absent axes, no crash.
def test_modal_axes_absent_when_modal_summary_missing() -> None:
    tmp_path = Path(__import__("tempfile").mkdtemp())
    metrics = _write_modal_metrics(tmp_path, modal_summary=None)
    convergence = _write_modal_convergence(tmp_path)
    score = score_case_completeness(_modal_inputs(tmp_path, metrics, convergence))
    for label in (
        "mode_count_coverage",
        "freq_convergence",
        "mode_shape_quality",
        "mass_participation",
    ):
        entry = _find_axis(score, label)
        assert entry.points_awarded == 0, label
        assert entry.evidence_status == "absent", label
    # Score should be the universal axes sum only.
    # starter(10) + engine(10) + metrics(10) + energy(10) +
    # convergence stable(10) = 50; modal-specific 0; total 50.
    assert score.score == 50


def test_modal_full_credit_when_every_quality_gate_passes() -> None:
    """Happy path — when every modal-specific axis is at its full-credit
    threshold, the score should hit 100/100."""
    tmp_path = Path(__import__("tempfile").mkdtemp())
    metrics = _write_modal_metrics(
        tmp_path,
        modal_summary={
            "mode_count_coverage": {"cumulative_y_pct": 92.0, "cumulative_z_pct": 88.0},
            "freq_convergence": {"dominant_mode_rel_err_pct": 0.5},
            "mode_shape_quality": {"dominant_mac": 0.98},
            "mass_participation": {"dominant_mode_pct": 75.0},
        },
    )
    convergence = _write_modal_convergence(tmp_path)
    score = score_case_completeness(_modal_inputs(tmp_path, metrics, convergence))
    assert score.score == 100
    assert score.analysis_type == "modal"


# ---------------------------------------------------------------------
# Modal advisor branch (StubAdvisor) — slice-B named concerns (T:-5)
# ---------------------------------------------------------------------


def _modal_context(
    *,
    extra: dict[str, Any] | None = None,
    convergence_combined_verdict: str | None = "candidate_observed_stable",
) -> AdvisorContext:
    return AdvisorContext(
        case_id="modal-cantilever-candidate",
        snapshot_label="modal_2026-05-16",
        trust_score=92,
        completeness_score=100,
        completeness_analysis_type="modal",
        energy_audit_status="closed_aggregate",
        convergence_kind="modal",
        convergence_combined_verdict=convergence_combined_verdict,
        extra=extra or {},
    )


def test_modal_advisor_surfaces_mac_concern() -> None:
    raw = StubAdvisor().produce(_modal_context())
    joined = " | ".join(raw.mesh_quality_concerns)
    assert "Modal Assurance Criterion" in joined or "MAC" in joined
    assert "modal convergence kind" in joined.lower()


def test_modal_advisor_surfaces_lanczos_question() -> None:
    raw = StubAdvisor().produce(_modal_context())
    joined = " | ".join(raw.boundary_condition_questions)
    assert "Lanczos" in joined


def test_modal_advisor_surfaces_mass_participation_question() -> None:
    """Without mode_count_target in context.extra, the advisor still
    surfaces the participation prompt (asking reviewer to supply
    target)."""
    raw = StubAdvisor().produce(_modal_context(extra={}))
    joined = " | ".join(raw.boundary_condition_questions)
    assert "cumulative effective mass participation" in joined
    assert "80%" in joined
    assert "mode_count_target" in joined  # reviewer prompted to supply


def test_modal_advisor_surfaces_frequency_tolerance_failure_mode() -> None:
    raw = StubAdvisor().produce(_modal_context())
    joined = " | ".join(raw.failure_modes_to_consider)
    assert "frequency residual" in joined
    assert "5%" in joined
    assert "Lanczos" in joined


# context.extra["mode_count_target"] passthrough — closes Phase 11 retro §2.
def test_modal_advisor_reads_mode_count_target_from_context_extra() -> None:
    """A:-6 anti-gaming guard. context.extra was an unread slot in
    Phase 11; slice B is required to consume it through to the
    produced concern."""
    raw = StubAdvisor().produce(_modal_context(extra={"mode_count_target": 12}))
    joined = " | ".join(raw.boundary_condition_questions)
    assert "12 extracted modes" in joined


def test_modal_advisor_concerns_are_distinct_from_explicit_dynamics() -> None:
    """The four modal-named concerns must not appear on an
    explicit_dynamics critique (and vice versa); otherwise the named-
    branch dispatch is vacuous."""
    modal_raw = StubAdvisor().produce(_modal_context())
    explicit_ctx = AdvisorContext(
        case_id="explicit-dynamics-case",
        snapshot_label="X",
        trust_score=80,
        completeness_score=80,
        completeness_analysis_type="ballistic",
        energy_audit_status="closed_aggregate",
        convergence_kind="explicit_dynamics",
        convergence_combined_verdict="candidate_observed_stable",
        extra={},
    )
    explicit_raw = StubAdvisor().produce(explicit_ctx)

    modal_joined = " ".join(
        list(modal_raw.mesh_quality_concerns)
        + list(modal_raw.boundary_condition_questions)
        + list(modal_raw.failure_modes_to_consider)
    )
    explicit_joined = " ".join(
        list(explicit_raw.mesh_quality_concerns)
        + list(explicit_raw.boundary_condition_questions)
        + list(explicit_raw.failure_modes_to_consider)
    )

    # Modal-specific tokens must not appear on explicit_dynamics output.
    for token in (
        "Lanczos",
        "Modal Assurance Criterion",
        "cumulative effective mass participation",
    ):
        assert token not in explicit_joined, f"token {token!r} leaked"
    # And explicit-specific tokens must not appear on modal output.
    assert "mass-scaled-to-physical" not in modal_joined
    assert "hourglass control" not in modal_joined


# ---------------------------------------------------------------------
# Slice-A MEDIUM closure — trust_score modal-branch behavioral tests
# ---------------------------------------------------------------------


def _write_convergence_payload(
    tmp_path: Path,
    *,
    mode_count_label: str | None,
    kind: str = "modal",
) -> Path:
    payload: dict[str, Any] = {"convergence_kind": kind}
    if mode_count_label is not None:
        payload["mode_count_sweep"] = {"candidate_stability": mode_count_label}
    path = tmp_path / "convergence_study.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_trust_score_modal_branch_stable_full_credit(tmp_path) -> None:
    """Closes slice-A TAA MEDIUM: trust_score modal branch had no
    direct behavioral tests, only a constant pin. This test asserts
    raw_score==100 + rationale substrings on the stable branch."""
    entry = _score_convergence_axis(
        _write_convergence_payload(tmp_path, mode_count_label="candidate_observed_stable")
    )
    assert entry.raw_score == 100
    assert entry.axis == "convergence_stability"
    assert "modal convergence_kind" in entry.rationale
    assert "mode_count_sweep stable" in entry.rationale
    assert "mesh_sweep and dt_sweep N/A" in entry.rationale


def test_trust_score_modal_branch_unstable_partial_credit(tmp_path) -> None:
    entry = _score_convergence_axis(
        _write_convergence_payload(tmp_path, mode_count_label="candidate_observed_unstable")
    )
    assert entry.raw_score == 30
    assert "modal convergence_kind" in entry.rationale
    assert "mode_count_sweep unstable" in entry.rationale


def test_trust_score_modal_branch_inconclusive_zero_credit(tmp_path) -> None:
    entry = _score_convergence_axis(
        _write_convergence_payload(tmp_path, mode_count_label="insufficient_data")
    )
    assert entry.raw_score == 0
    assert "modal convergence_kind" in entry.rationale
    assert "mode_count_sweep inconclusive" in entry.rationale


def test_trust_score_modal_branch_absent_falls_to_inconclusive(tmp_path) -> None:
    """A modal payload without mode_count_sweep falls to inconclusive
    (raw==0), not silently to the explicit_dynamics two-axis path."""
    entry = _score_convergence_axis(_write_convergence_payload(tmp_path, mode_count_label=None))
    assert entry.raw_score == 0
    assert "modal convergence_kind" in entry.rationale


# ---------------------------------------------------------------------
# Tier 1 disclaimer audit — modal critique still carries trio
# ---------------------------------------------------------------------


def test_modal_completeness_envelope_still_carries_disclaimer_trio() -> None:
    """C:-8 anti-gaming guard re-audited after the Phase 12 B schema
    bump."""
    tmp_path = Path(__import__("tempfile").mkdtemp())
    metrics = _write_modal_metrics(
        tmp_path,
        modal_summary={
            "mode_count_coverage": {"cumulative_y_pct": 90.0, "cumulative_z_pct": 88.0},
            "freq_convergence": {"dominant_mode_rel_err_pct": 0.5},
            "mode_shape_quality": {"dominant_mac": 0.98},
            "mass_participation": {"dominant_mode_pct": 75.0},
        },
    )
    convergence = _write_modal_convergence(tmp_path)
    score = score_case_completeness(_modal_inputs(tmp_path, metrics, convergence))
    assert score.claim_tier == "Tier 1 engineering candidate"
    # The boundary is the project SSOT constant (underscored form).
    assert "not_signed_validation" in score.claim_boundary
    assert "not_benchmark_agreement" in score.claim_boundary
    assert score.analysis_type == "modal"


def test_modal_universe_axis_evidence_status_uses_modal_weights(tmp_path) -> None:
    """Cross-check that the universal axes on a modal case actually
    receive the WEIGHT_*_MODAL (10) point caps, NOT the ballistic
    inherited (15) caps."""
    metrics = _write_modal_metrics(
        tmp_path,
        modal_summary={
            "mode_count_coverage": {"cumulative_y_pct": 90.0, "cumulative_z_pct": 88.0},
            "freq_convergence": {"dominant_mode_rel_err_pct": 0.5},
            "mode_shape_quality": {"dominant_mac": 0.98},
            "mass_participation": {"dominant_mode_pct": 75.0},
        },
    )
    convergence = _write_modal_convergence(tmp_path)
    score = score_case_completeness(_modal_inputs(tmp_path, metrics, convergence))
    for label in (
        "starter_deck",
        "engine_deck",
        "ballistic_metrics",
        "energy_audit",
        "convergence_study",
    ):
        entry = _find_axis(score, label)
        assert entry.points_max == 10, (
            f"{label} points_max should be 10 on modal, got {entry.points_max}"
        )


# ---------------------------------------------------------------------
# Parametrized: every modal advisor concern includes "modal" indicator
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "axis_check",
    [
        ("mesh_quality_concerns", "modal convergence kind"),
        ("boundary_condition_questions", "modal convergence kind"),
        ("failure_modes_to_consider", "modal convergence kind"),
    ],
)
def test_modal_branch_every_axis_carries_modal_indicator(axis_check: tuple[str, str]) -> None:
    """T:-5 named-token discipline — every concern on the modal branch
    explicitly labels itself "modal convergence kind" so a downstream
    grep / dashboard filter never confuses a modal concern with an
    explicit_dynamics or linear_static one."""
    axis_name, token = axis_check
    raw = StubAdvisor().produce(_modal_context())
    items = getattr(raw, axis_name)
    matching = [c for c in items if token in c]
    assert matching, f"no concern on {axis_name} carries token {token!r}"
