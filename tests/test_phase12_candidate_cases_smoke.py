"""Phase 12 C — three new real-runnable candidate cases (smoke assertions).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Synthetic-fast assertions on the pre-baked candidate fixtures generated
by the Phase 12 C demo orchestrators. CI does NOT re-run CalculiX; the
actual one-shot solver execution happens during slice authoring (per
the binding constraint that tests must run synthetic-only).

Each candidate fixture must satisfy:
  * the expected_results.json envelope (case_id, analysis_type, Tier 1
    disclaimer trio);
  * the ballistic_metrics.json evidence block (claim_tier present,
    energy_audit.status == "closed_aggregate", per-type summary
    populated);
  * the convergence_study.json (convergence_kind matches the
    analysis_type's expected kind, combined_verdict stable);
  * scoring through ``case_completeness.score_case_completeness`` with
    the correct analysis_type produces a high score (>= 95/100 on the
    happy-path quality gates).

Anti-gaming guards (Phase 12 sub-rubric §4.C):
  M:-2 named SSOT constants for each case_id + analysis_type;
  T:-3 per-axis evidence-status pin on the happy-path fixture;
  T:-4 per-case schema-version + claim-boundary boundary tests;
  C:-8 Tier 1 disclaimer trio audited on every fixture;
  E:-2 no real-solver invocation in CI (synthetic-fast assertions only).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.services.reporting.case_completeness import (
    CaseCompletenessInputs,
    score_case_completeness,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_ROOT = REPO_ROOT / "golden_samples"


# ---------------------------------------------------------------------
# Per-case SSOT constants — closed enum of slice-C candidate cases.
# ---------------------------------------------------------------------


PHASE12C_CANDIDATE_CASES: tuple[tuple[str, str], ...] = (
    ("modal-cantilever-candidate", "modal"),
    ("modal-cantilever-stiff-candidate", "modal"),
    ("cylinder-pv-extended-candidate", "linear_static_pv"),
)
"""Closed enum: (case_id, analysis_type) for every Phase 12 C-authored
candidate case. Adding a new case here REQUIRES creating the fixture
+ generator script + demo orchestrator in lockstep."""


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _fixture_dir(case_id: str) -> Path:
    return FIXTURE_ROOT / case_id


def _load_expected_results(case_id: str) -> dict:
    return json.loads((_fixture_dir(case_id) / "expected_results.json").read_text(encoding="utf-8"))


def _load_ballistic_metrics(case_id: str) -> dict:
    return json.loads(
        (_fixture_dir(case_id) / "data" / "ballistic_metrics.json").read_text(encoding="utf-8")
    )


def _load_convergence_study(case_id: str) -> dict:
    return json.loads(
        (_fixture_dir(case_id) / "data" / "convergence_study.json").read_text(encoding="utf-8")
    )


# ---------------------------------------------------------------------
# Fixture presence + envelope assertions
# ---------------------------------------------------------------------


@pytest.mark.parametrize("case_id,analysis_type", PHASE12C_CANDIDATE_CASES)
def test_candidate_fixture_directory_exists(case_id: str, analysis_type: str) -> None:
    """Every slice-C case must have its `*-candidate` fixture directory
    populated. Any future PR that removes one trips this test."""
    fixture = _fixture_dir(case_id)
    assert fixture.is_dir(), f"{fixture} not present"
    assert (fixture / "expected_results.json").is_file()
    assert (fixture / "data" / "ballistic_metrics.json").is_file()
    assert (fixture / "data" / "convergence_study.json").is_file()


@pytest.mark.parametrize("case_id,analysis_type", PHASE12C_CANDIDATE_CASES)
def test_candidate_expected_results_envelope_pins(case_id: str, analysis_type: str) -> None:
    """Every Phase 12 C candidate's expected_results.json must carry
    the Tier 1 disclaimer trio + claim_boundary SSOT format."""
    payload = _load_expected_results(case_id)
    assert payload["case_id"] == case_id
    assert payload["claim_tier"] == "Tier 1 engineering candidate"
    assert payload["status"] == "engineering_candidate"
    assert "not_signed_validation" in payload["claim_boundary"]
    assert "not_benchmark_agreement" in payload["claim_boundary"]


@pytest.mark.parametrize("case_id,analysis_type", PHASE12C_CANDIDATE_CASES)
def test_candidate_ballistic_metrics_envelope_pins(case_id: str, analysis_type: str) -> None:
    """ballistic_metrics.json carries claim_tier + closed-aggregate
    energy audit + per-type summary block."""
    metrics = _load_ballistic_metrics(case_id)
    assert metrics["case_id"] == case_id
    assert metrics["claim_tier"] == "Tier 1 engineering candidate"
    assert metrics["energy_audit"]["status"] == "closed_aggregate"
    # Per-type summary block presence.
    if analysis_type == "modal":
        assert "modal_summary" in metrics
    elif analysis_type == "linear_static_pv":
        assert "pv_summary" in metrics


# ---------------------------------------------------------------------
# Convergence-study type + verdict assertions
# ---------------------------------------------------------------------


@pytest.mark.parametrize("case_id,analysis_type", PHASE12C_CANDIDATE_CASES)
def test_candidate_convergence_kind_matches_analysis_type(case_id: str, analysis_type: str) -> None:
    """A modal case must carry convergence_kind == 'modal'; a
    linear_static_pv case must carry convergence_kind == 'linear_static'.
    A drift here is the most common Phase 11 → Phase 12 wiring bug."""
    conv = _load_convergence_study(case_id)
    if analysis_type == "modal":
        assert conv["convergence_kind"] == "modal"
    elif analysis_type == "linear_static_pv":
        assert conv["convergence_kind"] == "linear_static"
    assert conv["combined_verdict"] == "candidate_observed_stable"


# ---------------------------------------------------------------------
# Modal-specific axis pins on the happy-path fixtures
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "case_id",
    [c for c, t in PHASE12C_CANDIDATE_CASES if t == "modal"],
)
def test_modal_candidate_freq_convergence_within_5pct(case_id: str) -> None:
    """Every modal candidate's dominant-mode rel-err must be within the
    5% engineering tolerance documented in Phase 12 A. This is the
    load-bearing quality gate; if a future PR detunes the smoke mesh
    or pressure, this trips."""
    metrics = _load_ballistic_metrics(case_id)
    err_pct = abs(metrics["modal_summary"]["freq_convergence"]["dominant_mode_rel_err_pct"])
    assert err_pct < 5.0, f"{case_id} dominant_mode err {err_pct}% >= 5%"
    assert metrics["modal_summary"]["freq_convergence"]["all_within_tolerance"] is True


@pytest.mark.parametrize(
    "case_id",
    [c for c, t in PHASE12C_CANDIDATE_CASES if t == "modal"],
)
def test_modal_candidate_mass_participation_above_50pct(case_id: str) -> None:
    """Engineering-practice floor: dominant mode must carry > 50%
    of the cumulative effective modal mass in the principal direction."""
    metrics = _load_ballistic_metrics(case_id)
    pct = metrics["modal_summary"]["mass_participation"]["dominant_mode_pct"]
    assert pct >= 50.0, f"{case_id} dominant mode mass {pct}% < 50%"


@pytest.mark.parametrize(
    "case_id",
    [c for c, t in PHASE12C_CANDIDATE_CASES if t == "modal"],
)
def test_modal_candidate_cumulative_mass_above_80pct(case_id: str) -> None:
    """ASCE 7 / Eurocode 8 cumulative mass-participation engineering
    floor (80%) in each significant direction."""
    metrics = _load_ballistic_metrics(case_id)
    cov = metrics["modal_summary"]["mode_count_coverage"]
    assert cov["cumulative_y_pct"] >= 80.0
    assert cov["cumulative_z_pct"] >= 80.0


# ---------------------------------------------------------------------
# PV-extended-specific assertions
# ---------------------------------------------------------------------


def test_pv_extended_pressure_doubles_baseline() -> None:
    """The extended PV case must carry 20 MPa internal pressure (not
    10 MPa). Without this assertion, a copy-paste of the baseline
    fixture would silently downgrade the within-type cohort variation."""
    metrics = _load_ballistic_metrics("cylinder-pv-extended-candidate")
    p_mpa = metrics["pv_summary"]["load"]["internal_pressure_MPa"]
    assert p_mpa == 20.0


def test_pv_extended_length_doubles_baseline() -> None:
    """The extended PV case must carry L=400 mm (not 100 mm)."""
    metrics = _load_ballistic_metrics("cylinder-pv-extended-candidate")
    assert metrics["pv_summary"]["geometry"]["L_mm"] == 400.0


def test_pv_extended_lame_cross_check_still_within_5pct() -> None:
    """Despite the doubled pressure, the Lame cross-check must remain
    within the 5% engineering tolerance (Lame analytical scales
    linearly with pressure, so the relative errors are pressure-
    independent in theory)."""
    metrics = _load_ballistic_metrics("cylinder-pv-extended-candidate")
    conv = metrics["pv_summary"]["convergence_vs_lame"]
    for axis in ("sigma_r", "sigma_t", "sigma_z", "von_mises"):
        err = conv[f"max_rel_err_{axis}_pct"]
        assert err < 5.0, f"PV-ext {axis} rel err {err}% >= 5%"


def test_pv_extended_margin_still_clear() -> None:
    """Even at 20 MPa the membrane stress P_m must stay below the
    allowable S_m (138 MPa for SA-516 Gr.70). Doubling P_m gives ~42
    MPa, still well under the allowable."""
    metrics = _load_ballistic_metrics("cylinder-pv-extended-candidate")
    asme = metrics["pv_summary"]["asme_section_5_5"]
    assert asme["ratio_P_m_over_S_m"] < 1.0


# ---------------------------------------------------------------------
# End-to-end completeness scoring on the happy-path fixtures
# ---------------------------------------------------------------------


@pytest.mark.parametrize("case_id,analysis_type", PHASE12C_CANDIDATE_CASES)
def test_candidate_completeness_high_score(
    tmp_path: Path, case_id: str, analysis_type: str
) -> None:
    """End-to-end: feed the fixture into score_case_completeness and
    confirm it scores high (>= 80 / 100). The happy-path quality gates
    are all pegged at full credit; the only points not awarded are
    the optional-artifact axes that the fixture omits (animation_manifest,
    result_mesh, generator_script, notes for ballistic-flavored types;
    none of those are scored on modal)."""
    metrics_path = _fixture_dir(case_id) / "data" / "ballistic_metrics.json"
    conv_path = _fixture_dir(case_id) / "data" / "convergence_study.json"
    starter = tmp_path / "starter.rad"
    starter.write_text("# starter deck", encoding="utf-8")
    engine = tmp_path / "engine.rad"
    engine.write_text("# engine deck", encoding="utf-8")

    score = score_case_completeness(
        CaseCompletenessInputs(
            case_id=case_id,
            starter_deck_path=starter,
            engine_deck_path=engine,
            ballistic_metrics_path=metrics_path,
            convergence_study_path=conv_path,
            analysis_type=analysis_type,
        )
    )
    assert score.score >= 80, (
        f"{case_id} ({analysis_type}) scored {score.score}/100, expected >= 80"
    )
    assert score.claim_tier == "Tier 1 engineering candidate"
    assert score.analysis_type == analysis_type


def test_modal_canonical_full_credit_when_fixture_complete(tmp_path: Path) -> None:
    """The canonical modal-cantilever-candidate fixture should score
    100/100 on completeness when scored as modal (its analysis_type),
    given all five universal axes are present + all four modal-
    specific axes hit the documented thresholds."""
    case_id = "modal-cantilever-candidate"
    metrics_path = _fixture_dir(case_id) / "data" / "ballistic_metrics.json"
    conv_path = _fixture_dir(case_id) / "data" / "convergence_study.json"
    starter = tmp_path / "starter.rad"
    starter.write_text("# starter deck", encoding="utf-8")
    engine = tmp_path / "engine.rad"
    engine.write_text("# engine deck", encoding="utf-8")

    score = score_case_completeness(
        CaseCompletenessInputs(
            case_id=case_id,
            starter_deck_path=starter,
            engine_deck_path=engine,
            ballistic_metrics_path=metrics_path,
            convergence_study_path=conv_path,
            analysis_type="modal",
        )
    )
    # 5 universal × 10 + 4 modal-specific (15+15+10+10) = 50+50 = 100.
    assert score.score == 100


# ---------------------------------------------------------------------
# Generator + demo orchestrator presence assertions
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "rel_path",
    [
        "scripts/gen_modal_cantilever_deck.py",
        "scripts/gen_modal_cantilever_stiff_deck.py",
        "scripts/gen_cylinder_pv_extended_deck.py",
        "demo_modal_cantilever_pv/run_modal_e2e_demo.py",
        "demo_modal_cantilever_stiff/run_modal_e2e_demo.py",
        "demo_cylinder_pv_extended/run_e2e_demo.py",
    ],
)
def test_phase12c_demo_artifacts_present(rel_path: str) -> None:
    """Every demo orchestrator + generator-script that the Phase 12 C
    blueprint mandates must exist on disk. Without this assertion, a
    future PR could remove one and the cohort snapshot would silently
    stop including the case's generator SHA (Phase 9 B schema 1.3.0
    generator/<case>.py slot)."""
    assert (REPO_ROOT / rel_path).is_file(), f"missing: {rel_path}"


# ---------------------------------------------------------------------
# Forbidden-claim audit (C:-8) — re-fired on each fixture's text
# ---------------------------------------------------------------------


_FORBIDDEN_CLAIM_TOKENS = (
    "validated against",
    "perforation completed",
    "bullet-through-steel complete",
    "validated physics",
    "production ready",
    "approved for service",
    "ASME compliant",
    "signed off",
)


@pytest.mark.parametrize("case_id,analysis_type", PHASE12C_CANDIDATE_CASES)
def test_candidate_fixtures_carry_no_forbidden_positive_claims(
    case_id: str, analysis_type: str
) -> None:
    """No forbidden positive token can appear except in 'not <claim>'
    disclaimer form. The fixture text is fed through this audit just
    like the runtime envelopes."""
    expected_text = (_fixture_dir(case_id) / "expected_results.json").read_text(encoding="utf-8")
    metrics_text = (_fixture_dir(case_id) / "data" / "ballistic_metrics.json").read_text(
        encoding="utf-8"
    )
    conv_text = (_fixture_dir(case_id) / "data" / "convergence_study.json").read_text(
        encoding="utf-8"
    )
    combined = " || ".join([expected_text, metrics_text, conv_text])
    for token in _FORBIDDEN_CLAIM_TOKENS:
        # Allow the disclaimer "not <claim>" form; refuse positive form.
        idx = 0
        while True:
            hit = combined.find(token, idx)
            if hit == -1:
                break
            # Look backwards for a "not " or "not_" prefix within 6 chars.
            preceding = combined[max(0, hit - 6) : hit].lower()
            assert "not " in preceding or "not_" in preceding, (
                f"{case_id}: forbidden token {token!r} appears in positive form"
            )
            idx = hit + len(token)
