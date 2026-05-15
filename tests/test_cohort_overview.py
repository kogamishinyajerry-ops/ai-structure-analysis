"""Tests for the Tier 1 cohort overview (FM-04a Phase 4 B).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.services.reporting.cohort_overview import (
    CohortOverview,
    build_cohort_overview,
    render_cohort_overview_json,
)


def _seed_decks(case_dir: Path) -> None:
    data_dir = case_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "model_00_0000.rad").write_text("starter\n", encoding="utf-8")
    (data_dir / "model_00_0001.rad").write_text("engine\n", encoding="utf-8")


def _seed_notes(case_dir: Path, text: str = "notes\n") -> None:
    (case_dir / "NOTES.md").write_text(text, encoding="utf-8")


def _seed_metrics(
    repo_root: Path,
    case_id: str,
    *,
    perforation_marker: str = "perforated_candidate",
    residual_velocity: float = 75.0,
    energy_audit_status: str = "closed_aggregate",
    energy_balance_error: float = 19.0,
) -> None:
    target = (
        repo_root
        / "project_state"
        / "graph_executor"
        / case_id
        / "ballistic"
        / "ballistic_metrics.json"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "case_id": case_id,
                "perforation_marker": perforation_marker,
                "projectile_initial_velocity_m_per_s": 600.0,
                "residual_velocity_candidate_m_per_s": residual_velocity,
                "energy_audit": {
                    "status": energy_audit_status,
                    "energy_balance_error_pct": energy_balance_error,
                },
            }
        ),
        encoding="utf-8",
    )


def _seed_convergence(
    repo_root: Path, case_id: str, *, verdict: str = "candidate_observed_stable"
) -> None:
    target = (
        repo_root
        / "project_state"
        / "graph_executor"
        / case_id
        / "convergence"
        / "convergence_study.json"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "case_id": case_id,
                "combined_verdict": verdict,
                "mesh_sweep": {"candidate_stability": verdict},
                "dt_sweep": {"candidate_stability": verdict},
            }
        ),
        encoding="utf-8",
    )


def test_empty_repo_returns_empty_cohort(tmp_path: Path) -> None:
    overview = build_cohort_overview(tmp_path)
    assert isinstance(overview, CohortOverview)
    assert overview.cohort_count == 0
    assert overview.entries == []
    assert overview.mean_score is None
    # FM-04b blockers list must still be present even at empty cohort.
    assert any("ADR-024 (full)" in b for b in overview.tier2_blockers_remaining)


def test_single_candidate_case_with_full_evidence(tmp_path: Path) -> None:
    case_id = "GS-102-phase4b-candidate"
    case_dir = tmp_path / "golden_samples" / case_id
    case_dir.mkdir(parents=True)
    _seed_decks(case_dir)
    _seed_notes(case_dir)
    _seed_metrics(tmp_path, case_id)
    _seed_convergence(tmp_path, case_id)

    overview = build_cohort_overview(tmp_path)
    assert overview.cohort_count == 1
    assert len(overview.entries) == 1
    entry = overview.entries[0]
    assert entry.case_id == case_id
    # decks + metrics + closed audit + stable convergence + notes
    # = 15+15+20+15+15+5 = 85
    assert entry.completeness_score == 85
    assert entry.perforation_marker == "perforated_candidate"
    assert entry.residual_velocity_candidate_m_per_s == 75.0
    assert entry.energy_audit_status == "closed_aggregate"
    assert entry.convergence_combined_verdict == "candidate_observed_stable"
    assert entry.last_modified_utc is not None
    assert overview.mean_score == 85.0


def test_cohort_filters_signed_registry_shape(tmp_path: Path) -> None:
    """A directory named exactly GS-001 must not be surfaced even if it
    ends with no -candidate suffix; defense in depth even though the
    suffix filter already rejects it."""
    (tmp_path / "golden_samples" / "GS-001").mkdir(parents=True)
    _seed_decks(tmp_path / "golden_samples" / "GS-001")
    # A real -candidate directory alongside.
    real = tmp_path / "golden_samples" / "GS-200-candidate"
    real.mkdir(parents=True)
    _seed_decks(real)
    overview = build_cohort_overview(tmp_path)
    assert overview.cohort_count == 1
    assert overview.entries[0].case_id == "GS-200-candidate"


def test_mixed_cohort_aggregates_distribution(tmp_path: Path) -> None:
    # Case A: full evidence at 100
    case_a = "GS-A-candidate"
    case_a_dir = tmp_path / "golden_samples" / case_a
    case_a_dir.mkdir(parents=True)
    _seed_decks(case_a_dir)
    _seed_notes(case_a_dir)
    (tmp_path / "scripts").mkdir(parents=True, exist_ok=True)
    # _build_inputs_for slug: "GS-A-candidate" → "gsa"; the generator path
    # must match that or the 5-pt generator_script band is not awarded.
    (tmp_path / "scripts" / "gen_gsa_deck.py").write_text("# gen\n", encoding="utf-8")
    _seed_metrics(tmp_path, case_a)
    _seed_convergence(tmp_path, case_a)
    anim_dir = tmp_path / "project_state" / "graph_executor" / case_a / "visualization"
    anim_dir.mkdir(parents=True, exist_ok=True)
    (anim_dir / "openradioss_animation_manifest.json").write_text("{}", encoding="utf-8")
    mesh_dir = tmp_path / "project_state" / "visualizations" / case_a
    mesh_dir.mkdir(parents=True, exist_ok=True)
    (mesh_dir / "result_mesh.json").write_text("{}", encoding="utf-8")

    # Case B: decks only
    case_b = "GS-B-candidate"
    case_b_dir = tmp_path / "golden_samples" / case_b
    case_b_dir.mkdir(parents=True)
    _seed_decks(case_b_dir)

    # Case C: decks + metrics only
    case_c = "GS-C-candidate"
    case_c_dir = tmp_path / "golden_samples" / case_c
    case_c_dir.mkdir(parents=True)
    _seed_decks(case_c_dir)
    _seed_metrics(tmp_path, case_c)

    overview = build_cohort_overview(tmp_path)
    assert overview.cohort_count == 3
    scores = {e.case_id: e.completeness_score for e in overview.entries}
    assert scores[case_a] == 100
    assert scores[case_b] == 30
    assert scores[case_c] == 65
    # Distribution buckets: 0-49=1, 50-79=1, 80-99=0, 100=1
    distribution = overview.completeness_distribution
    assert distribution["0-49"] == 1
    assert distribution["50-79"] == 1
    assert distribution["80-99"] == 0
    assert distribution["100"] == 1
    assert overview.mean_score == round((100 + 30 + 65) / 3, 2)


def test_unreadable_metrics_does_not_crash(tmp_path: Path) -> None:
    case_id = "GS-broken-candidate"
    case_dir = tmp_path / "golden_samples" / case_id
    case_dir.mkdir(parents=True)
    _seed_decks(case_dir)
    metrics = (
        tmp_path
        / "project_state"
        / "graph_executor"
        / case_id
        / "ballistic"
        / "ballistic_metrics.json"
    )
    metrics.parent.mkdir(parents=True, exist_ok=True)
    metrics.write_text("not-valid-json{", encoding="utf-8")

    overview = build_cohort_overview(tmp_path)
    assert overview.cohort_count == 1
    entry = overview.entries[0]
    # Decks present (30), metrics unreadable (0), audit absent (0).
    assert entry.completeness_score == 30
    assert entry.perforation_marker is None
    assert entry.energy_audit_status == "unavailable"


def test_render_json_emits_all_top_level_keys(tmp_path: Path) -> None:
    overview = build_cohort_overview(tmp_path)
    payload = json.loads(render_cohort_overview_json(overview))
    for key in (
        "generated_at_utc",
        "claim_tier",
        "claim_boundary",
        "cohort_count",
        "mean_score",
        "completeness_distribution",
        "entries",
        "tier2_blockers_remaining",
        "claim_impact",
    ):
        assert key in payload, f"missing top-level key {key!r}"


def test_cohort_preserves_tier1_boundary_wording(tmp_path: Path) -> None:
    case_id = "GS-X-candidate"
    case_dir = tmp_path / "golden_samples" / case_id
    case_dir.mkdir(parents=True)
    _seed_decks(case_dir)
    _seed_metrics(tmp_path, case_id)
    _seed_convergence(tmp_path, case_id)

    overview = build_cohort_overview(tmp_path)
    text = render_cohort_overview_json(overview).lower()
    assert "tier1_engineering_candidate" in text
    assert "not_signed_validation" in text
    assert "not_benchmark_agreement" in text
    assert "not signed validation" in text  # claim_impact prose form
    # Forbidden positive-claim audit with disclaimer strip.
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
