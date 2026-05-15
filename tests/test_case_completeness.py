"""Tests for the Tier 1 evidence completeness scoring engine (FM-04a Phase 4 A).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.services.reporting.case_completeness import (
    CaseCompletenessInputs,
    CaseCompletenessScore,
    render_case_completeness_json,
    score_case_completeness,
)


def _make_metrics(
    tmp_path: Path,
    name: str = "metrics.json",
    *,
    energy_audit_status: str = "closed_aggregate",
) -> Path:
    payload = {
        "case_id": "GS-102-phase4-a",
        "perforation_marker": "perforated_candidate",
        "energy_audit": {
            "status": energy_audit_status,
            "initial_kinetic_energy_j": 1731.0,
            "energy_balance_error_pct": 19.0,
        },
    }
    out = tmp_path / name
    out.write_text(json.dumps(payload), encoding="utf-8")
    return out


def _make_convergence(
    tmp_path: Path, name: str = "convergence.json", *, verdict: str = "candidate_observed_stable"
) -> Path:
    payload = {
        "case_id": "GS-102-phase4-a",
        "combined_verdict": verdict,
        "mesh_sweep": {"candidate_stability": verdict},
        "dt_sweep": {"candidate_stability": verdict},
    }
    out = tmp_path / name
    out.write_text(json.dumps(payload), encoding="utf-8")
    return out


def _make_file(tmp_path: Path, name: str, content: str = "fake\n") -> Path:
    out = tmp_path / name
    out.write_text(content, encoding="utf-8")
    return out


def test_empty_inputs_score_zero(tmp_path: Path) -> None:
    inputs = CaseCompletenessInputs(case_id="GS-102-phase4-a")
    score = score_case_completeness(inputs)
    assert isinstance(score, CaseCompletenessScore)
    assert score.score == 0
    assert score.score_max == 100
    assert {"starter_deck", "engine_deck", "ballistic_metrics", "energy_audit"} <= set(
        score.missing_evidence
    )
    # Even at 0, the FM-04b blockers list must still be rendered.
    assert any("ADR-024 (full)" in b for b in score.tier2_blockers_remaining)


def test_decks_only_scores_thirty(tmp_path: Path) -> None:
    starter = _make_file(tmp_path, "starter.rad")
    engine = _make_file(tmp_path, "engine.rad")
    inputs = CaseCompletenessInputs(
        case_id="GS-102-phase4-a",
        starter_deck_path=starter,
        engine_deck_path=engine,
    )
    score = score_case_completeness(inputs)
    # 15 + 15 = 30
    assert score.score == 30
    assert "ballistic_metrics" in score.missing_evidence


def test_decks_metrics_closed_audit_scores_sixty_five(tmp_path: Path) -> None:
    starter = _make_file(tmp_path, "starter.rad")
    engine = _make_file(tmp_path, "engine.rad")
    metrics = _make_metrics(tmp_path, energy_audit_status="closed_aggregate")
    inputs = CaseCompletenessInputs(
        case_id="GS-102-phase4-a",
        starter_deck_path=starter,
        engine_deck_path=engine,
        ballistic_metrics_path=metrics,
    )
    score = score_case_completeness(inputs)
    # 15 + 15 + 20 + 15 = 65
    assert score.score == 65
    assert "convergence_study" in score.missing_evidence
    audit_entry = next(b for b in score.breakdown if b.label == "energy_audit")
    assert audit_entry.points_awarded == 15
    assert audit_entry.evidence_status == "closed_aggregate"


def test_full_evidence_scores_one_hundred(tmp_path: Path) -> None:
    starter = _make_file(tmp_path, "starter.rad")
    engine = _make_file(tmp_path, "engine.rad")
    metrics = _make_metrics(tmp_path)
    convergence = _make_convergence(tmp_path)
    animation = _make_file(tmp_path, "anim.json")
    mesh = _make_file(tmp_path, "mesh.json")
    generator = _make_file(tmp_path, "gen.py")
    notes = _make_file(tmp_path, "NOTES.md")
    inputs = CaseCompletenessInputs(
        case_id="GS-102-phase4-a",
        starter_deck_path=starter,
        engine_deck_path=engine,
        ballistic_metrics_path=metrics,
        convergence_study_path=convergence,
        animation_manifest_path=animation,
        result_mesh_path=mesh,
        generator_script_path=generator,
        notes_path=notes,
    )
    score = score_case_completeness(inputs)
    assert score.score == 100
    assert score.missing_evidence == []
    # FM-04b blockers list MUST still be present at full score — this is
    # the load-bearing assertion that 100/100 ≠ Tier 2 readiness.
    assert any("ADR-024 (full)" in b for b in score.tier2_blockers_remaining)


def test_partial_audit_scores_in_between_band(tmp_path: Path) -> None:
    starter = _make_file(tmp_path, "starter.rad")
    engine = _make_file(tmp_path, "engine.rad")
    metrics = _make_metrics(tmp_path, energy_audit_status="partial_candidate")
    inputs = CaseCompletenessInputs(
        case_id="GS-102-phase4-a",
        starter_deck_path=starter,
        engine_deck_path=engine,
        ballistic_metrics_path=metrics,
    )
    score = score_case_completeness(inputs)
    # 15 + 15 + 20 + 10 (partial audit) = 60
    assert score.score == 60
    audit_entry = next(b for b in score.breakdown if b.label == "energy_audit")
    assert audit_entry.points_awarded == 10
    assert audit_entry.evidence_status == "partial_candidate"
    # The closed_aggregate band is now a tracked gap.
    assert "energy_audit_closed_aggregate" in score.missing_evidence


def test_unstable_convergence_scores_partial_band(tmp_path: Path) -> None:
    convergence = _make_convergence(tmp_path, verdict="candidate_observed_unstable")
    inputs = CaseCompletenessInputs(
        case_id="GS-102-phase4-a",
        convergence_study_path=convergence,
    )
    score = score_case_completeness(inputs)
    conv_entry = next(b for b in score.breakdown if b.label == "convergence_study")
    assert conv_entry.points_awarded == 10
    assert conv_entry.evidence_status == "candidate_observed_unstable"
    assert "convergence_study_stable" in score.missing_evidence


def test_render_json_emits_all_top_level_keys(tmp_path: Path) -> None:
    inputs = CaseCompletenessInputs(case_id="GS-102-phase4-a")
    score = score_case_completeness(inputs)
    payload = json.loads(render_case_completeness_json(score))
    for key in (
        "case_id",
        "generated_at_utc",
        "claim_tier",
        "claim_boundary",
        "score",
        "score_max",
        "breakdown",
        "missing_evidence",
        "tier2_blockers_remaining",
        "claim_impact",
    ):
        assert key in payload, f"missing top-level key {key!r}"


def test_score_preserves_tier1_boundary_wording(tmp_path: Path) -> None:
    starter = _make_file(tmp_path, "starter.rad")
    engine = _make_file(tmp_path, "engine.rad")
    metrics = _make_metrics(tmp_path)
    convergence = _make_convergence(tmp_path)
    inputs = CaseCompletenessInputs(
        case_id="GS-102-phase4-a",
        starter_deck_path=starter,
        engine_deck_path=engine,
        ballistic_metrics_path=metrics,
        convergence_study_path=convergence,
    )
    score = score_case_completeness(inputs)
    text = render_case_completeness_json(score).lower()
    # Required disclaimers present.
    assert "tier1_engineering_candidate" in text
    assert "not_signed_validation" in text
    assert "not_benchmark_agreement" in text
    assert "not signed validation" in text  # claim_impact prose form
    # Forbidden positive-claim audit: strip disclaimers first, then check
    # for any leakage in the residue.
    stripped = (
        text.replace("not_signed_validation", "")
        .replace("not_benchmark_agreement", "")
        .replace("not signed validation", "")
        .replace("not benchmark agreement", "")
    )
    for forbidden in (
        "validated against",
        "signed validation",
        "benchmark agreement",
        "perforation completed",
        "bullet-through-steel complete",
        "validated physics",
    ):
        assert forbidden not in stripped, f"leak: {forbidden}"


def test_unreadable_metrics_file_scores_zero_for_metrics_block(tmp_path: Path) -> None:
    """If the metrics file exists but is corrupt, do not crash; score 0 for it."""
    bad = tmp_path / "broken_metrics.json"
    bad.write_text("not-valid-json{", encoding="utf-8")
    inputs = CaseCompletenessInputs(
        case_id="GS-102-phase4-a",
        ballistic_metrics_path=bad,
    )
    score = score_case_completeness(inputs)
    metrics_entry = next(b for b in score.breakdown if b.label == "ballistic_metrics")
    audit_entry = next(b for b in score.breakdown if b.label == "energy_audit")
    assert metrics_entry.evidence_status == "unreadable"
    assert metrics_entry.points_awarded == 0
    assert audit_entry.points_awarded == 0
