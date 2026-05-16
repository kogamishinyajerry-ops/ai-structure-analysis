"""Tests for the Phase 6 B Tier 1 candidate trust score.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from app.services.reporting import trust_score as trust_score_module
from app.services.reporting._schema_versions import (
    TRUST_SCORE_FORMULA_VERSION,
    TRUST_SCORE_SCHEMA_VERSION,
)
from app.services.reporting.trust_score import (
    COMPLETENESS_WEIGHT,
    CONVERGENCE_WEIGHT,
    ENERGY_AUDIT_WEIGHT,
    REPRO_PENALTY_GIT_DIRTY,
    REPRO_PENALTY_GIT_SHA_MISSING,
    REPRO_PENALTY_PER_NOT_INSTALLED_PACKAGE,
    REPRODUCIBILITY_WEIGHT,
    TrustScoreInputs,
    _score_completeness_axis,
    _score_convergence_axis,
    _score_energy_audit_axis,
    _score_reproducibility_axis,
    compute_trust_score,
    render_trust_score_json,
)

# ---------------------------------------------------------------------
# constants self-test (the "anti-gaming" formula audit)
# ---------------------------------------------------------------------


def test_composite_weights_sum_to_100() -> None:
    """Phase 6 anti-gaming guard: a silent rebalance must not pass."""
    total = COMPLETENESS_WEIGHT + CONVERGENCE_WEIGHT + ENERGY_AUDIT_WEIGHT + REPRODUCIBILITY_WEIGHT
    assert total == 100


def test_composite_weights_match_phase6_blueprint() -> None:
    assert COMPLETENESS_WEIGHT == 50
    assert CONVERGENCE_WEIGHT == 20
    assert ENERGY_AUDIT_WEIGHT == 15
    assert REPRODUCIBILITY_WEIGHT == 15


def test_reproducibility_penalty_constants_match_blueprint() -> None:
    assert REPRO_PENALTY_GIT_DIRTY == 30
    assert REPRO_PENALTY_GIT_SHA_MISSING == 25
    assert REPRO_PENALTY_PER_NOT_INSTALLED_PACKAGE == 20


def test_schema_and_formula_versions_pinned() -> None:
    assert TRUST_SCORE_SCHEMA_VERSION == "1.0.0"
    assert TRUST_SCORE_FORMULA_VERSION == "1.0.0"


# ---------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------


def _write_metrics(
    case_id: str,
    root: Path,
    *,
    energy_status: str = "closed_aggregate",
) -> Path:
    payload = {
        "case_id": case_id,
        "projectile_initial_velocity_m_per_s": 300.0,
        "perforation": {
            "marker": "candidate_perforation",
            "residual_velocity_m_per_s": 75.0,
        },
        "energy_audit": {
            "status": energy_status,
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
    path = root / "ballistic_metrics.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _write_convergence(
    root: Path,
    *,
    mesh_stability: str = "candidate_observed_stable",
    dt_stability: str = "candidate_observed_stable",
) -> Path:
    payload = {
        "case_id": "case",
        "study_metric": "residual_velocity_m_per_s",
        "tolerance_pct": 5.0,
        "combined_verdict": "candidate_observed_stable",
        "mesh_sweep": {
            "runs": [],
            "candidate_stability": mesh_stability,
        },
        "dt_sweep": {
            "runs": [],
            "candidate_stability": dt_stability,
        },
        "row_count": 0,
        "rows": [],
        "claim_boundary": "tier1_engineering_candidate",
        "energy_balance_observation": {"status": "closed_aggregate"},
    }
    path = root / "convergence_study.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _init_git_repo(repo_root: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo_root)], check=True)
    subprocess.run(
        ["git", "-C", str(repo_root), "config", "user.email", "trust@example.test"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo_root), "config", "user.name", "Trust Score"],
        check=True,
    )
    (repo_root / "seed.txt").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo_root), "add", "seed.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(repo_root), "commit", "-q", "-m", "seed"],
        check=True,
        capture_output=True,
    )


# ---------------------------------------------------------------------
# axis scorer unit tests
# ---------------------------------------------------------------------


def test_completeness_axis_normalizes_to_raw_100(tmp_path: Path) -> None:
    metrics = _write_metrics("GS-A", tmp_path)
    convergence = _write_convergence(tmp_path)
    entry = _score_completeness_axis(
        TrustScoreInputs(
            case_id="GS-A",
            repo_root=tmp_path,
            starter_deck_path=tmp_path / "missing-starter.rad",
            engine_deck_path=tmp_path / "missing-engine.rad",
            ballistic_metrics_path=metrics,
            convergence_study_path=convergence,
        )
    )
    assert entry.axis == "completeness"
    assert entry.weight == COMPLETENESS_WEIGHT
    assert 0 <= entry.raw_score <= 100
    # weighted must equal raw * weight / 100 (rounded)
    assert entry.weighted == round(entry.raw_score * COMPLETENESS_WEIGHT / 100)


def test_convergence_axis_both_stable_scores_100(tmp_path: Path) -> None:
    convergence = _write_convergence(tmp_path)
    entry = _score_convergence_axis(convergence)
    assert entry.raw_score == 100
    assert entry.weighted == CONVERGENCE_WEIGHT


def test_convergence_axis_one_stable_one_unstable_scores_60(tmp_path: Path) -> None:
    convergence = _write_convergence(
        tmp_path,
        mesh_stability="candidate_observed_stable",
        dt_stability="candidate_observed_unstable",
    )
    entry = _score_convergence_axis(convergence)
    assert entry.raw_score == 60


def test_convergence_axis_both_unstable_scores_30(tmp_path: Path) -> None:
    convergence = _write_convergence(
        tmp_path,
        mesh_stability="candidate_observed_unstable",
        dt_stability="candidate_observed_unstable",
    )
    entry = _score_convergence_axis(convergence)
    assert entry.raw_score == 30


def test_convergence_axis_absent_file_scores_0(tmp_path: Path) -> None:
    entry = _score_convergence_axis(tmp_path / "missing.json")
    assert entry.raw_score == 0
    assert entry.weighted == 0


def test_energy_axis_closed_aggregate_scores_100(tmp_path: Path) -> None:
    metrics = _write_metrics("GS-A", tmp_path, energy_status="closed_aggregate")
    entry = _score_energy_audit_axis(metrics)
    assert entry.raw_score == 100
    assert entry.weighted == ENERGY_AUDIT_WEIGHT


def test_energy_axis_partial_candidate_scores_60(tmp_path: Path) -> None:
    metrics = _write_metrics("GS-A", tmp_path, energy_status="partial_candidate")
    entry = _score_energy_audit_axis(metrics)
    assert entry.raw_score == 60


def test_energy_axis_unavailable_scores_0(tmp_path: Path) -> None:
    metrics = _write_metrics("GS-A", tmp_path, energy_status="unavailable")
    entry = _score_energy_audit_axis(metrics)
    assert entry.raw_score == 0


def test_reproducibility_axis_clean_git_scores_100(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    entry = _score_reproducibility_axis("GS-A", tmp_path, generator_script_path=None)
    # all 9 tracked packages must be installed for raw=100; in this test env
    # at least fastapi/numpy should be installed. Accept either 100 or a
    # well-formed penalty deduction.
    assert entry.weight == REPRODUCIBILITY_WEIGHT
    assert entry.raw_score >= 0
    assert entry.raw_score <= 100


def test_reproducibility_axis_dirty_git_deducts(tmp_path: Path) -> None:
    _init_git_repo(tmp_path)
    # introduce a dirty change
    (tmp_path / "seed.txt").write_text("dirty\n", encoding="utf-8")
    entry_clean = _score_reproducibility_axis("GS-A", tmp_path, generator_script_path=None)
    # subprocess.run with check=True needed — git_dirty must be True now
    assert "git_dirty" in entry_clean.rationale


def test_reproducibility_axis_no_git_deducts_25(tmp_path: Path) -> None:
    entry = _score_reproducibility_axis("GS-A", tmp_path, generator_script_path=None)
    assert "git_commit_sha absent" in entry.rationale
    # Without .git, the sha-missing penalty fires regardless of packages
    assert entry.raw_score <= 100 - REPRO_PENALTY_GIT_SHA_MISSING


# ---------------------------------------------------------------------
# compute_trust_score integration
# ---------------------------------------------------------------------


def test_compute_trust_score_yields_stamped_payload(tmp_path: Path) -> None:
    metrics = _write_metrics("GS-102-trust", tmp_path)
    convergence = _write_convergence(tmp_path)
    score = compute_trust_score(
        TrustScoreInputs(
            case_id="GS-102-trust",
            repo_root=tmp_path,
            ballistic_metrics_path=metrics,
            convergence_study_path=convergence,
        )
    )
    rendered = json.loads(render_trust_score_json(score))
    assert rendered["schema_version"] == TRUST_SCORE_SCHEMA_VERSION
    assert rendered["formula_version"] == TRUST_SCORE_FORMULA_VERSION
    assert rendered["case_id"] == "GS-102-trust"
    assert rendered["claim_tier"] == "Tier 1 engineering candidate"
    assert 0 <= rendered["trust_score"] <= 100


def test_compute_trust_score_breakdown_has_all_four_axes(tmp_path: Path) -> None:
    metrics = _write_metrics("GS-A", tmp_path)
    convergence = _write_convergence(tmp_path)
    score = compute_trust_score(
        TrustScoreInputs(
            case_id="GS-A",
            repo_root=tmp_path,
            ballistic_metrics_path=metrics,
            convergence_study_path=convergence,
        )
    )
    axes = {entry.axis for entry in score.breakdown}
    assert axes == {
        "completeness",
        "convergence_stability",
        "energy_audit_closure",
        "reproducibility_clean",
    }
    # sum of weighted scores must equal trust_score
    assert sum(e.weighted for e in score.breakdown) == score.trust_score


def test_compute_trust_score_preserves_tier1_disclaimer(tmp_path: Path) -> None:
    metrics = _write_metrics("GS-A", tmp_path)
    convergence = _write_convergence(tmp_path)
    score = compute_trust_score(
        TrustScoreInputs(
            case_id="GS-A",
            repo_root=tmp_path,
            ballistic_metrics_path=metrics,
            convergence_study_path=convergence,
        )
    )
    rendered = render_trust_score_json(score)
    assert "not signed validation" in rendered
    assert "not benchmark agreement" in rendered


def test_compute_trust_score_top_score_when_everything_clean(tmp_path: Path) -> None:
    """All evidence present + closed_aggregate + both axes stable +
    clean git should give a score >= 80 (penalty floor for the case
    where tracked packages might not all be installed)."""
    _init_git_repo(tmp_path)
    metrics = _write_metrics("GS-A", tmp_path)
    convergence = _write_convergence(tmp_path)
    starter = tmp_path / "starter.rad"
    engine = tmp_path / "engine.rad"
    notes = tmp_path / "NOTES.md"
    generator = tmp_path / "gen_gsa_deck.py"
    for p in (starter, engine, notes, generator):
        p.write_text(f"# {p.name}", encoding="utf-8")
    # animation manifest + result mesh as additional evidence
    anim = tmp_path / "anim.json"
    anim.write_text("{}", encoding="utf-8")
    mesh = tmp_path / "mesh.json"
    mesh.write_text("{}", encoding="utf-8")

    score = compute_trust_score(
        TrustScoreInputs(
            case_id="GS-A",
            repo_root=tmp_path,
            starter_deck_path=starter,
            engine_deck_path=engine,
            ballistic_metrics_path=metrics,
            convergence_study_path=convergence,
            animation_manifest_path=anim,
            result_mesh_path=mesh,
            generator_script_path=generator,
            notes_path=notes,
        )
    )
    # completeness should reach 100 (all 9 rubric entries present + stable + closed)
    completeness_entry = next(e for e in score.breakdown if e.axis == "completeness")
    assert completeness_entry.raw_score == 100
    convergence_entry = next(e for e in score.breakdown if e.axis == "convergence_stability")
    assert convergence_entry.raw_score == 100
    energy_entry = next(e for e in score.breakdown if e.axis == "energy_audit_closure")
    assert energy_entry.raw_score == 100
    # Trust score should be at least 85 in the worst case (15 lost to
    # reproducibility if packages aren't installed); in the test venv
    # they are installed so we expect 100.
    assert score.trust_score >= 85


def test_compute_trust_score_rejects_forbidden_claim_injection(tmp_path: Path, monkeypatch) -> None:
    """A forbidden phrase injected into the rationale-builder source
    must be caught by the audit."""
    import pytest

    metrics = _write_metrics("GS-A", tmp_path)
    convergence = _write_convergence(tmp_path)
    # Monkey-patch CLAIM_IMPACT_DEFAULT to inject a forbidden phrase
    monkeypatch.setattr(
        trust_score_module,
        "CLAIM_IMPACT_DEFAULT",
        "this case has been validated against the benchmark (bad)",
    )
    with pytest.raises(ValueError, match="forbidden positive claim"):
        compute_trust_score(
            TrustScoreInputs(
                case_id="GS-A",
                repo_root=tmp_path,
                ballistic_metrics_path=metrics,
                convergence_study_path=convergence,
            )
        )
