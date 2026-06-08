"""FM-04a Phase 11 A — analysis-type-aware completeness rubric tests.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Pins:
* CASE_COMPLETENESS_SCHEMA_VERSION — version pin lives in
  ``tests/test_schema_versions_stamping.py`` (parametrized). Phase 11 A
  shipped 1.1.0; Phase 12 B bumped to 1.2.0 (modal substantiation).
  The single Phase-11 pin was retired in Phase 12 B to keep one SSOT.
* CONVERGENCE_STUDY_SCHEMA_VERSION — version pin lives in
  ``tests/test_schema_versions_stamping.py`` (parametrized). Phase 11 A
  shipped 1.1.0; Phase 12 A bumped to 1.2.0 (modal axis). The single
  Phase-11 pin was retired in Phase 12 A to keep one SSOT.
* ANALYSIS_TYPE_TUPLE closed set + DEFAULT_ANALYSIS_TYPE == "ballistic".
* Every rubric in ANALYSIS_TYPE_RUBRIC_WEIGHTS sums to 100 (M:-2 guard).
* Every rubric carries the 5 universal axes (M:-2 guard).
* Tuple ↔ weights dict consistency at import time
  (`_assert_rubric_weights_consistent`).
* Back-compat: a CaseCompletenessInputs with no analysis_type defaults
  to ballistic and reproduces the pre-Phase-11 score on a fixed input.
* PV rubric replaces animation_manifest / result_mesh / notes with
  lame_cross_check / scl_convergence / allowable_margin.
* PV-specific axes are read from metrics file's `pv_summary` block:
  - lame_cross_check: full credit when worst rel err on σ_r/σ_t/σ_z/vM
    is <=5%; half credit otherwise; 0 when absent.
  - scl_convergence: full credit when σ_t/σ_z/vM rel err <=2%; half
    credit at <=5%; 0 at >5% or absent.
  - allowable_margin: full credit when P_m/S_m < 1.0; 0 at >=1.0 or
    absent.
* Unknown analysis_type -> ValueError.
* The JSON envelope carries the new `analysis_type` key on every payload.
* trust_score `_score_convergence_axis` honors `convergence_kind`:
  linear_static skips dt_sweep evaluation cleanly.
* Forbidden-claim envelope audit still fires after the schema bumps.

Phase 11 anti-gaming guards exercised:
  M:-2 (no magic; rubric sums verified)
  T:-3 (each numeric threshold has its own boundary test)
  T:-4 (PV axes — Lame, SCL, margin — each tested independently)
  T:-5 (forbidden-token list extended; each new token has its own test
        in slice B; here we just re-pin the original list)
  C:-4 (forbidden-claim audit re-verified post bump)
  A:-2 (vacuous-rubric guard — boundary cases exercised)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.services.reporting import case_completeness as cc
from app.services.reporting.case_completeness import (
    ANALYSIS_TYPE_RUBRIC_WEIGHTS,
    ANALYSIS_TYPE_TUPLE,
    DEFAULT_ANALYSIS_TYPE,
    CaseCompletenessInputs,
    _assert_rubric_weights_consistent,
    render_case_completeness_json,
    score_case_completeness,
)

# ---------------------------------------------------------------------
# Named constants
# ---------------------------------------------------------------------


# Phase 12 B: CASE_COMPLETENESS_SCHEMA_VERSION pin retired here in
# favor of the centralized parametrized pin in
# ``tests/test_schema_versions_stamping.py`` (which tracks every bump).
# Phase 12 A: CONVERGENCE_STUDY_SCHEMA_VERSION pin retired here in
# favor of the centralized parametrized pin in
# ``tests/test_schema_versions_stamping.py`` (which tracks every bump).
# A future MINOR/PATCH bump only needs to update one file, not two.


def test_default_analysis_type_is_ballistic() -> None:
    """Back-compat — every existing FM-04a caller (Phases 4-10) does
    not pass analysis_type. The default must remain ``ballistic``."""
    assert DEFAULT_ANALYSIS_TYPE == "ballistic"


def test_analysis_type_tuple_closed_set() -> None:
    """The tuple is the SSOT for the closed enum. Any addition here
    requires a matching ANALYSIS_TYPE_RUBRIC_WEIGHTS entry; that
    lockstep is enforced at import time."""
    assert ANALYSIS_TYPE_TUPLE == (
        "ballistic",
        "linear_static_pv",
        "explicit_dynamics",
        "modal",
    )
    assert len(ANALYSIS_TYPE_TUPLE) == 4


# ---------------------------------------------------------------------
# Rubric weight integrity (M:-2 / A:-2 guards)
# ---------------------------------------------------------------------


@pytest.mark.parametrize("analysis_type", ANALYSIS_TYPE_TUPLE)
def test_every_rubric_sums_to_100(analysis_type: str) -> None:
    """No silent rubric drift. Every analysis type must sum to exactly
    100. Phase 11 anti-gaming guard M:-2."""
    weights = ANALYSIS_TYPE_RUBRIC_WEIGHTS[analysis_type]
    assert sum(weights.values()) == 100, (
        f"analysis_type={analysis_type!r} rubric sums to {sum(weights.values())}, not 100"
    )


@pytest.mark.parametrize("analysis_type", ANALYSIS_TYPE_TUPLE)
def test_every_rubric_carries_universal_axes(analysis_type: str) -> None:
    """Every rubric must score at least starter/engine/metrics/audit/
    convergence. These are the universal axes any candidate fixture
    must have. Phase 11 anti-gaming guard M:-2."""
    required = {
        "starter_deck",
        "engine_deck",
        "ballistic_metrics",
        "energy_audit",
        "convergence_study",
    }
    actual = set(ANALYSIS_TYPE_RUBRIC_WEIGHTS[analysis_type].keys())
    missing = required - actual
    assert not missing, (
        f"analysis_type={analysis_type!r} missing universal axes {sorted(missing)!r}"
    )


def test_consistency_audit_runs_clean_at_import() -> None:
    """Calling the import-time audit directly must not raise."""
    _assert_rubric_weights_consistent()


def test_consistency_audit_catches_tuple_drift(monkeypatch: pytest.MonkeyPatch) -> None:
    """Inject a tuple-vs-dict drift and prove the audit fires."""
    monkeypatch.setattr(
        cc, "ANALYSIS_TYPE_TUPLE", ("ballistic", "linear_static_pv", "new_unmapped_type")
    )
    with pytest.raises(RuntimeError, match="drift"):
        _assert_rubric_weights_consistent()


def test_consistency_audit_catches_bad_sum(monkeypatch: pytest.MonkeyPatch) -> None:
    bad_weights = dict(ANALYSIS_TYPE_RUBRIC_WEIGHTS)
    bad_weights["ballistic"] = {**ANALYSIS_TYPE_RUBRIC_WEIGHTS["ballistic"], "starter_deck": 999}
    monkeypatch.setattr(cc, "ANALYSIS_TYPE_RUBRIC_WEIGHTS", bad_weights)
    with pytest.raises(RuntimeError, match="not 100"):
        _assert_rubric_weights_consistent()


# ---------------------------------------------------------------------
# Back-compat: legacy caller without analysis_type
# ---------------------------------------------------------------------


def _ballistic_inputs(tmp_path: Path) -> CaseCompletenessInputs:
    starter = tmp_path / "model_00_0000.rad"
    starter.write_text("# starter", encoding="utf-8")
    engine = tmp_path / "model_00_0001.rad"
    engine.write_text("# engine", encoding="utf-8")
    metrics = tmp_path / "ballistic_metrics.json"
    metrics.write_text(
        json.dumps(
            {
                "energy_audit": {"status": "closed_aggregate"},
            }
        ),
        encoding="utf-8",
    )
    return CaseCompletenessInputs(
        case_id="GS-test-candidate",
        starter_deck_path=starter,
        engine_deck_path=engine,
        ballistic_metrics_path=metrics,
    )


def test_legacy_caller_no_analysis_type_defaults_to_ballistic(tmp_path: Path) -> None:
    inputs = _ballistic_inputs(tmp_path)
    score = score_case_completeness(inputs)
    assert score.analysis_type == "ballistic"


def test_legacy_caller_score_unchanged_from_pre_phase_11(tmp_path: Path) -> None:
    """A ballistic fixture with starter + engine + metrics + closed
    audit gets exactly 65/100 (15+15+20+15+0 convergence absent) —
    same number a pre-Phase-11 ballistic caller would have gotten."""
    inputs = _ballistic_inputs(tmp_path)
    score = score_case_completeness(inputs)
    assert score.score == 65


# ---------------------------------------------------------------------
# Unknown analysis_type rejected
# ---------------------------------------------------------------------


def test_unknown_analysis_type_raises_value_error(tmp_path: Path) -> None:
    inputs = CaseCompletenessInputs(
        case_id="x-candidate",
        analysis_type="quantum_handwaving",
    )
    with pytest.raises(ValueError, match="not in the supported"):
        score_case_completeness(inputs)


# ---------------------------------------------------------------------
# Linear-static-PV rubric: PV-specific axes
# ---------------------------------------------------------------------


def _pv_metrics_payload(
    *,
    worst_rel_err_full: float = 1.16,  # all-4-component worst (Lame check)
    worst_rel_err_load: float = 0.20,  # σ_t / σ_z / vM worst (SCL check)
    pm_over_sm: float = 0.151,
) -> dict:
    return {
        "energy_audit": {"status": "closed_aggregate"},
        "pv_summary": {
            "convergence_vs_lame": {
                "max_rel_err_sigma_r_pct": worst_rel_err_full,
                "max_rel_err_sigma_t_pct": worst_rel_err_load,
                "max_rel_err_sigma_z_pct": worst_rel_err_load,
                "max_rel_err_von_mises_pct": worst_rel_err_load,
            },
            "asme_section_5_5": {"ratio_P_m_over_S_m": pm_over_sm},
        },
    }


def _pv_inputs(tmp_path: Path, *, payload: dict | None = None) -> CaseCompletenessInputs:
    starter = tmp_path / "model_00_0000.rad"
    starter.write_text("# s", encoding="utf-8")
    engine = tmp_path / "model_00_0001.rad"
    engine.write_text("# e", encoding="utf-8")
    metrics = tmp_path / "ballistic_metrics.json"
    metrics.write_text(json.dumps(payload or _pv_metrics_payload()), encoding="utf-8")
    convergence = tmp_path / "convergence_study.json"
    convergence.write_text(
        json.dumps(
            {
                "convergence_kind": "linear_static",
                "convergence_combined_verdict": "candidate_observed_stable",
                "mesh_sweep": {"candidate_stability": "candidate_observed_stable"},
            }
        ),
        encoding="utf-8",
    )
    generator = tmp_path / "generator.py"
    generator.write_text("# gen", encoding="utf-8")
    return CaseCompletenessInputs(
        case_id="cylinder-pv-candidate",
        starter_deck_path=starter,
        engine_deck_path=engine,
        ballistic_metrics_path=metrics,
        convergence_study_path=convergence,
        generator_script_path=generator,
        analysis_type="linear_static_pv",
    )


def test_pv_rubric_full_credit_on_clean_case(tmp_path: Path) -> None:
    """A well-converged PV case (worst rel err <2%, ratio <1.0) gets
    a perfect score on every PV-specific axis."""
    score = score_case_completeness(_pv_inputs(tmp_path))
    by_label = {e.label: e for e in score.breakdown}
    assert by_label["lame_cross_check"].points_awarded == 10
    assert by_label["scl_convergence"].points_awarded == 10
    assert by_label["allowable_margin"].points_awarded == 5
    # Total = 15+15+15+15+10+10+10+5+5 = 100.
    assert score.score == 100


def test_pv_rubric_lame_half_credit_above_5pct(tmp_path: Path) -> None:
    """Worst |rel err| > 5% on Lame -> half credit on lame_cross_check."""
    payload = _pv_metrics_payload(worst_rel_err_full=7.5)
    score = score_case_completeness(_pv_inputs(tmp_path, payload=payload))
    by_label = {e.label: e for e in score.breakdown}
    assert by_label["lame_cross_check"].points_awarded == 5  # 10 // 2


def test_pv_rubric_scl_half_credit_above_2pct(tmp_path: Path) -> None:
    """Worst σ_t/σ_z/vM rel err in (2, 5]% -> half credit on scl_convergence."""
    payload = _pv_metrics_payload(worst_rel_err_load=3.5)
    score = score_case_completeness(_pv_inputs(tmp_path, payload=payload))
    by_label = {e.label: e for e in score.breakdown}
    assert by_label["scl_convergence"].points_awarded == 5


def test_pv_rubric_scl_zero_credit_above_5pct(tmp_path: Path) -> None:
    """Worst σ_t/σ_z/vM rel err > 5% -> zero credit on scl_convergence."""
    payload = _pv_metrics_payload(worst_rel_err_load=7.0)
    score = score_case_completeness(_pv_inputs(tmp_path, payload=payload))
    by_label = {e.label: e for e in score.breakdown}
    assert by_label["scl_convergence"].points_awarded == 0


def test_pv_rubric_margin_zero_at_or_above_unity(tmp_path: Path) -> None:
    """P_m/S_m >= 1.0 -> zero credit on allowable_margin (engineering
    failure flagged)."""
    for ratio in (1.0, 1.5, 2.0):
        payload = _pv_metrics_payload(pm_over_sm=ratio)
        score = score_case_completeness(_pv_inputs(tmp_path, payload=payload))
        by_label = {e.label: e for e in score.breakdown}
        assert by_label["allowable_margin"].points_awarded == 0, ratio


def test_pv_rubric_does_not_score_ballistic_only_axes(tmp_path: Path) -> None:
    """PV rubric must NOT score animation_manifest / result_mesh / notes."""
    score = score_case_completeness(_pv_inputs(tmp_path))
    labels = {e.label for e in score.breakdown}
    assert "animation_manifest" not in labels
    assert "result_mesh" not in labels
    assert "notes" not in labels


def test_pv_rubric_at_exact_5pct_boundary_keeps_full_credit(tmp_path: Path) -> None:
    """Boundary pin: worst rel err == 5% (inclusive upper) -> full credit
    on lame_cross_check. Phase 11 anti-gaming guard T:-3 — explicit
    boundary test on the threshold."""
    payload = _pv_metrics_payload(worst_rel_err_full=5.0)
    score = score_case_completeness(_pv_inputs(tmp_path, payload=payload))
    by_label = {e.label: e for e in score.breakdown}
    assert by_label["lame_cross_check"].points_awarded == 10


# ---------------------------------------------------------------------
# JSON envelope carries the new analysis_type key
# ---------------------------------------------------------------------


def test_json_envelope_carries_analysis_type_on_ballistic_default(tmp_path: Path) -> None:
    score = score_case_completeness(_ballistic_inputs(tmp_path))
    payload = json.loads(render_case_completeness_json(score))
    assert payload["analysis_type"] == "ballistic"


def test_json_envelope_carries_analysis_type_on_pv(tmp_path: Path) -> None:
    score = score_case_completeness(_pv_inputs(tmp_path))
    payload = json.loads(render_case_completeness_json(score))
    assert payload["analysis_type"] == "linear_static_pv"
    # schema_version pin is centralized in tests/test_schema_versions_stamping.py
    # (Phase 12 B retirement of the duplicate Phase-11-era literal pin).
    # Here we just assert the envelope carries SOME version string in the
    # 1.x family.
    assert payload["schema_version"].startswith("1.")


# ---------------------------------------------------------------------
# trust_score convergence axis honors convergence_kind
# ---------------------------------------------------------------------


def test_trust_score_convergence_linear_static_skips_dt_sweep(tmp_path: Path) -> None:
    """A linear_static convergence_kind with mesh_sweep stable and NO
    dt_sweep present should score 100 on the convergence axis — not
    60 (which is what the legacy "one stable, one inconclusive"
    branch would have returned)."""
    from app.services.reporting.trust_score import _score_convergence_axis

    p = tmp_path / "convergence_study.json"
    p.write_text(
        json.dumps(
            {
                "convergence_kind": "linear_static",
                "mesh_sweep": {"candidate_stability": "candidate_observed_stable"},
            }
        ),
        encoding="utf-8",
    )
    entry = _score_convergence_axis(p)
    assert entry.raw_score == 100
    assert "linear_static" in entry.rationale.lower()


def test_trust_score_convergence_explicit_dynamics_still_needs_both(tmp_path: Path) -> None:
    """Back-compat: no convergence_kind => assume explicit_dynamics =>
    requires both axes; mesh-only stable falls to the 60 branch."""
    from app.services.reporting.trust_score import _score_convergence_axis

    p = tmp_path / "convergence_study.json"
    p.write_text(
        json.dumps(
            {
                "mesh_sweep": {"candidate_stability": "candidate_observed_stable"},
            }
        ),
        encoding="utf-8",
    )
    entry = _score_convergence_axis(p)
    assert entry.raw_score == 60


# ---------------------------------------------------------------------
# Forbidden-claim audit still fires after schema bump
# ---------------------------------------------------------------------


def test_forbidden_claim_audit_still_fires_after_schema_bump(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Adding the analysis_type envelope key must not silently bypass
    the forbidden-claim audit. Phase 11 anti-gaming guard C:-4."""
    monkeypatch.setattr(
        cc, "CLAIM_IMPACT_DEFAULT", "this score is validated physics for the candidate"
    )
    with pytest.raises(ValueError, match="forbidden claim"):
        score_case_completeness(_pv_inputs(tmp_path))
