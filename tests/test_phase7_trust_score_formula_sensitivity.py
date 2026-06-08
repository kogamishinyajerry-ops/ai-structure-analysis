"""FM-04a Phase 7 D — formula sensitivity / rebalance methodology tests.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Closes Phase 6 retrospective carry-forward §5 (rebalance methodology).

The trust score module docstring's "Sensitivity & Rebalance Methodology"
section names this file as the canonical rebalance harness: a future
weight change is testable in isolation by monkey-patching the constant
and asserting an expected score delta. This file ships four such
canonical cases proving the linearity contract holds.

All tests are deterministic (no Hypothesis). The methodology:

1. Stage on-disk evidence with known scores on all four axes.
2. Capture the baseline trust score.
3. monkeypatch.setattr() a single weight or penalty constant by a known
   delta.
4. Re-import / re-call compute_trust_score and assert the expected
   delta lands.

The tests deliberately do NOT modify pyproject or the live module —
monkeypatch confines the perturbation to the test's scope.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.services.reporting import trust_score as trust_score_module
from app.services.reporting.trust_score import (
    TrustScoreInputs,
    compute_trust_score,
)


def _stage_full_evidence_case(
    case_id: str,
    repo_root: Path,
    *,
    completeness_target: int = 80,
    energy_status: str = "closed_aggregate",
    convergence_verdict: str = "candidate_observed_stable",
) -> TrustScoreInputs:
    """Stage a case whose completeness scorecard yields the requested
    target by including/excluding evidence files. Easier path: stage
    every evidence file present so completeness = score_max (full).
    The caller's ``completeness_target`` is honored on a best-effort
    basis (full evidence = 100; we stop here)."""
    case_dir = repo_root / "golden_samples" / case_id / "data"
    case_dir.mkdir(parents=True, exist_ok=True)
    starter = case_dir / "model_00_0000.rad"
    engine = case_dir / "model_00_0001.rad"
    starter.write_text("# starter", encoding="utf-8")
    engine.write_text("# engine", encoding="utf-8")
    notes = repo_root / "golden_samples" / case_id / "NOTES.md"
    notes.write_text("# notes", encoding="utf-8")

    ballistic_path = (
        repo_root
        / "project_state"
        / "graph_executor"
        / case_id
        / "ballistic"
        / "ballistic_metrics.json"
    )
    ballistic_path.parent.mkdir(parents=True, exist_ok=True)
    ballistic_path.write_text(
        json.dumps(
            {
                "case_id": case_id,
                "projectile_initial_velocity_m_per_s": 300.0,
                "perforation": {
                    "marker": "candidate_perforation",
                    "residual_velocity_m_per_s": 75.0,
                },
                "energy_audit": {
                    "status": energy_status,
                    "energy_balance_error_pct": 8.0,
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
        ),
        encoding="utf-8",
    )

    convergence_path = (
        repo_root
        / "project_state"
        / "graph_executor"
        / case_id
        / "convergence"
        / "convergence_study.json"
    )
    convergence_path.parent.mkdir(parents=True, exist_ok=True)
    convergence_path.write_text(
        json.dumps(
            {
                "case_id": case_id,
                "study_metric": "residual_velocity_m_per_s",
                "tolerance_pct": 5.0,
                "combined_verdict": convergence_verdict,
                "mesh_sweep": {
                    "runs": [],
                    "candidate_stability": convergence_verdict,
                },
                "dt_sweep": {
                    "runs": [],
                    "candidate_stability": convergence_verdict,
                },
                "row_count": 0,
                "rows": [],
                "claim_boundary": (
                    "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"
                ),
                "energy_balance_observation": {"status": energy_status},
            }
        ),
        encoding="utf-8",
    )

    animation_manifest_path = (
        repo_root
        / "project_state"
        / "graph_executor"
        / case_id
        / "visualization"
        / "openradioss_animation_manifest.json"
    )
    result_mesh_path = repo_root / "project_state" / "visualizations" / case_id / "result_mesh.json"
    slug = case_id.lower().replace("gs-", "gs").replace("-candidate", "").replace("-", "_")
    generator = repo_root / "scripts" / f"gen_{slug}_deck.py"
    generator.parent.mkdir(parents=True, exist_ok=True)
    generator.write_bytes(b"# generator\n")

    return TrustScoreInputs(
        case_id=case_id,
        repo_root=repo_root,
        starter_deck_path=starter,
        engine_deck_path=engine,
        ballistic_metrics_path=ballistic_path,
        convergence_study_path=convergence_path,
        animation_manifest_path=animation_manifest_path,
        result_mesh_path=result_mesh_path,
        generator_script_path=generator,
        notes_path=notes,
    )


# ---------------------------------------------------------------------
# Sensitivity Test 1: completeness weight perturbation
# ---------------------------------------------------------------------


def test_sensitivity_completeness_weight_perturbation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Doubling COMPLETENESS_WEIGHT (50 → 100) and zeroing the other
    three (so the sum still = 100) should redistribute the score:
    if completeness raw_score was R%, the new trust_score == R.

    This is the canonical "future rebalance" proof. A real rebalance
    would bump TRUST_SCORE_FORMULA_VERSION accordingly.
    """
    inputs = _stage_full_evidence_case("GS-A-candidate", tmp_path)
    baseline = compute_trust_score(inputs)
    completeness_entry = next(e for e in baseline.breakdown if e.axis == "completeness")
    completeness_raw = completeness_entry.raw_score

    # Perturbation: all weight on completeness
    monkeypatch.setattr(trust_score_module, "COMPLETENESS_WEIGHT", 100)
    monkeypatch.setattr(trust_score_module, "CONVERGENCE_WEIGHT", 0)
    monkeypatch.setattr(trust_score_module, "ENERGY_AUDIT_WEIGHT", 0)
    monkeypatch.setattr(trust_score_module, "REPRODUCIBILITY_WEIGHT", 0)
    monkeypatch.setattr(
        trust_score_module,
        "_ALL_WEIGHTS",
        (100, 0, 0, 0),
    )

    perturbed = compute_trust_score(inputs)
    # New trust score should equal the completeness raw_score
    # (weighted = raw * 100 / 100 = raw)
    assert perturbed.trust_score == completeness_raw


# ---------------------------------------------------------------------
# Sensitivity Test 2: reproducibility penalty perturbation
# ---------------------------------------------------------------------


def test_sensitivity_repro_git_dirty_penalty_perturbation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Doubling REPRO_PENALTY_GIT_DIRTY from 30 to 60 must NOT change
    the trust score when git_dirty is False (the penalty doesn't fire).
    """
    inputs = _stage_full_evidence_case("GS-A-candidate", tmp_path)
    baseline = compute_trust_score(inputs)

    monkeypatch.setattr(trust_score_module, "REPRO_PENALTY_GIT_DIRTY", 60)

    perturbed = compute_trust_score(inputs)
    # Same evidence -> same score (penalty didn't fire because the
    # repo is not a git repo)
    repro_baseline = next(e for e in baseline.breakdown if e.axis == "reproducibility_clean")
    repro_perturbed = next(e for e in perturbed.breakdown if e.axis == "reproducibility_clean")
    assert repro_baseline.raw_score == repro_perturbed.raw_score


# ---------------------------------------------------------------------
# Sensitivity Test 3: completeness vs convergence weight swap
# ---------------------------------------------------------------------


def test_sensitivity_completeness_convergence_weight_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Swapping COMPLETENESS_WEIGHT (50) with CONVERGENCE_WEIGHT (20)
    must change the trust score by exactly:
        (50 - 20) * (convergence_raw - completeness_raw) / 100
    rounded per the int() cast in the per-axis weighting.
    """
    inputs = _stage_full_evidence_case("GS-A-candidate", tmp_path)
    baseline = compute_trust_score(inputs)
    comp_raw = next(e for e in baseline.breakdown if e.axis == "completeness").raw_score
    conv_raw = next(e for e in baseline.breakdown if e.axis == "convergence_stability").raw_score

    # Swap weights
    monkeypatch.setattr(trust_score_module, "COMPLETENESS_WEIGHT", 20)
    monkeypatch.setattr(trust_score_module, "CONVERGENCE_WEIGHT", 50)
    monkeypatch.setattr(
        trust_score_module,
        "_ALL_WEIGHTS",
        (20, 50, 15, 15),
    )

    perturbed = compute_trust_score(inputs)

    # Expected delta on the trust score: completeness loses 30 weight
    # points, convergence gains 30 weight points; the actual delta in
    # the integer-cast world is:
    expected_comp_weighted_baseline = int(round(comp_raw * 50 / 100))
    expected_comp_weighted_perturbed = int(round(comp_raw * 20 / 100))
    expected_conv_weighted_baseline = int(round(conv_raw * 20 / 100))
    expected_conv_weighted_perturbed = int(round(conv_raw * 50 / 100))
    expected_delta = (expected_comp_weighted_perturbed - expected_comp_weighted_baseline) + (
        expected_conv_weighted_perturbed - expected_conv_weighted_baseline
    )
    actual_delta = perturbed.trust_score - baseline.trust_score
    assert actual_delta == expected_delta


# ---------------------------------------------------------------------
# Sensitivity Test 4: weight sum invariant guard
# ---------------------------------------------------------------------


def test_sensitivity_assert_weights_sum_to_100_fires_when_violated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The compute_trust_score builder asserts the weight constants sum
    to 100. A rebalance that forgets to update _ALL_WEIGHTS would trip
    this guard before producing a wrong score.
    """
    inputs = _stage_full_evidence_case("GS-A-candidate", tmp_path)

    # Break the sum-to-100 invariant explicitly
    monkeypatch.setattr(trust_score_module, "_ALL_WEIGHTS", (50, 20, 15, 14))

    with pytest.raises(AssertionError, match="trust score weights must sum to 100"):
        compute_trust_score(inputs)
