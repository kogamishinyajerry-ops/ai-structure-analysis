"""End-to-end Tier 1 reviewer workflow on a synthetic 3-case cohort
(FM-04a Phase 4 G).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Drives the full reviewer-cohort workflow on synthetic fixtures:
  1. Seed 3 candidate cases with different evidence completeness.
  2. Score each via `score_case_completeness`.
  3. Build cohort overview; assert distribution buckets.
  4. Build reviewer bundle for 2 of the 3 cases; unzip in memory.
  5. Verify every bundle member preserves the Tier 1 banner.
  6. Archive one acceptance packet, then diff archive-vs-current-state.

Runs without real OpenRadioss, without Docker, without any external
service call. Designed to live in CI as the load-bearing proof that
the reviewer-cohort workflow composes cleanly end-to-end.
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from app.services.reporting.archived_packet_diff import (
    diff_archived_packets,
    render_archived_packet_diff_json,
)
from app.services.reporting.case_completeness import (
    CaseCompletenessInputs,
    render_case_completeness_json,
    score_case_completeness,
)
from app.services.reporting.cohort_overview import build_cohort_overview
from app.services.reporting.reviewer_bundle import (
    ReviewerBundleInputs,
    build_reviewer_bundle,
)


def _seed_case(
    repo_root: Path,
    case_id: str,
    *,
    with_metrics: bool = True,
    audit_status: str = "closed_aggregate",
    with_convergence: bool = True,
    convergence_verdict: str = "candidate_observed_stable",
) -> None:
    case_dir = repo_root / "golden_samples" / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    data = case_dir / "data"
    data.mkdir(parents=True, exist_ok=True)
    (data / "model_00_0000.rad").write_text("starter\n", encoding="utf-8")
    (data / "model_00_0001.rad").write_text("engine\n", encoding="utf-8")

    if with_metrics:
        metrics = (
            repo_root
            / "project_state"
            / "graph_executor"
            / case_id
            / "ballistic"
            / "ballistic_metrics.json"
        )
        metrics.parent.mkdir(parents=True, exist_ok=True)
        metrics.write_text(
            json.dumps(
                {
                    "case_id": case_id,
                    "perforation_marker": "perforated_candidate",
                    "projectile_initial_velocity_m_per_s": 600.0,
                    "residual_velocity_candidate_m_per_s": 75.0,
                    "crossing_evidence": {
                        "status": "candidate_observed",
                        "front_face_crossed": True,
                        "back_face_crossed": True,
                        "first_back_face_crossing_t_s": 5e-5,
                    },
                    "energy_audit": {
                        "status": audit_status,
                        "initial_kinetic_energy_j": 1731.0,
                        "residual_kinetic_energy_j": 575.5,
                        "aggregate_internal_energy_j": 826.6,
                        "external_work_j": 0.0,
                        "energy_balance_error_pct": 19.0,
                        "breakdown_status": "aggregated_into_internal_energy",
                        "missing_terms": [],
                    },
                }
            ),
            encoding="utf-8",
        )

    if with_convergence:
        conv = (
            repo_root
            / "project_state"
            / "graph_executor"
            / case_id
            / "convergence"
            / "convergence_study.json"
        )
        conv.parent.mkdir(parents=True, exist_ok=True)
        conv.write_text(
            json.dumps(
                {
                    "case_id": case_id,
                    "combined_verdict": convergence_verdict,
                    "mesh_sweep": {"candidate_stability": convergence_verdict},
                    "dt_sweep": {"candidate_stability": convergence_verdict},
                    "row_count": 2,
                    "tolerance_pct": 5.0,
                    "claim_boundary": (
                        "tier1_engineering_candidate; not_signed_validation; "
                        "not_benchmark_agreement"
                    ),
                    "claim_impact": (
                        "Tier 1 candidate mesh and time-step convergence study only; "
                        "not signed validation; not benchmark agreement"
                    ),
                }
            ),
            encoding="utf-8",
        )


def _bundle_inputs_for(repo_root: Path, case_id: str) -> ReviewerBundleInputs:
    case_dir = repo_root / "golden_samples" / case_id
    starter = case_dir / "data" / "model_00_0000.rad"
    engine = case_dir / "data" / "model_00_0001.rad"
    metrics = (
        repo_root
        / "project_state"
        / "graph_executor"
        / case_id
        / "ballistic"
        / "ballistic_metrics.json"
    )
    convergence = (
        repo_root
        / "project_state"
        / "graph_executor"
        / case_id
        / "convergence"
        / "convergence_study.json"
    )
    return ReviewerBundleInputs(
        case_id=case_id,
        starter_deck_path=starter if starter.is_file() else None,
        engine_deck_path=engine if engine.is_file() else None,
        ballistic_metrics_path=metrics if metrics.is_file() else None,
        convergence_study_path=convergence if convergence.is_file() else None,
    )


def _completeness_inputs_for(repo_root: Path, case_id: str) -> CaseCompletenessInputs:
    case_dir = repo_root / "golden_samples" / case_id
    return CaseCompletenessInputs(
        case_id=case_id,
        starter_deck_path=case_dir / "data" / "model_00_0000.rad",
        engine_deck_path=case_dir / "data" / "model_00_0001.rad",
        ballistic_metrics_path=(
            repo_root
            / "project_state"
            / "graph_executor"
            / case_id
            / "ballistic"
            / "ballistic_metrics.json"
        ),
        convergence_study_path=(
            repo_root
            / "project_state"
            / "graph_executor"
            / case_id
            / "convergence"
            / "convergence_study.json"
        ),
    )


def test_reviewer_workflow_end_to_end_on_three_case_synthetic_cohort(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path

    # Step 1: seed 3 candidate cases with different completeness profiles.
    _seed_case(repo_root, "GS-A-candidate")  # full evidence
    _seed_case(
        repo_root,
        "GS-B-candidate",
        with_metrics=False,
        with_convergence=False,
    )
    _seed_case(repo_root, "GS-C-candidate", with_convergence=False)

    # Step 2: score each case via the completeness scorer.
    score_a = score_case_completeness(_completeness_inputs_for(repo_root, "GS-A-candidate"))
    score_b = score_case_completeness(_completeness_inputs_for(repo_root, "GS-B-candidate"))
    score_c = score_case_completeness(_completeness_inputs_for(repo_root, "GS-C-candidate"))
    assert score_a.score >= 65  # decks + metrics + closed audit + stable convergence
    assert score_b.score == 30  # decks only
    assert 50 <= score_c.score < score_a.score  # decks + metrics + audit, no convergence
    # Each score keeps the FM-04b blockers list explicit, regardless of score.
    for score in (score_a, score_b, score_c):
        assert any("ADR-024 (full)" in b for b in score.tier2_blockers_remaining)

    # Step 3: cohort overview emits all 3 cases + distribution.
    overview = build_cohort_overview(repo_root)
    assert overview.cohort_count == 3
    cohort_case_ids = {e.case_id for e in overview.entries}
    assert cohort_case_ids == {"GS-A-candidate", "GS-B-candidate", "GS-C-candidate"}
    assert sum(overview.completeness_distribution.values()) == 3

    # Step 4: build reviewer bundle for 2 of the 3 cases; unzip in memory.
    bundle_inputs = [
        _bundle_inputs_for(repo_root, "GS-A-candidate"),
        _bundle_inputs_for(repo_root, "GS-C-candidate"),
    ]
    bundle_bytes = build_reviewer_bundle(bundle_inputs, repo_root=repo_root)
    assert bundle_bytes.startswith(b"PK\x03\x04")

    with zipfile.ZipFile(io.BytesIO(bundle_bytes)) as zf:
        names = zf.namelist()
        manifest = json.loads(zf.read("BUNDLE_MANIFEST.json").decode("utf-8"))

    assert manifest["cohort_count"] == 2
    assert {c["case_id"] for c in manifest["cases"]} == {
        "GS-A-candidate",
        "GS-C-candidate",
    }
    # Expected member set: 4 files for A (full evidence), 3 for C (no convergence).
    expected_a_members = {
        "GS-A-candidate/GS-A-candidate_acceptance_packet.json",
        "GS-A-candidate/GS-A-candidate_convergence_study.json",
        "GS-A-candidate/GS-A-candidate_Tier1_candidate_report.md",
        "GS-A-candidate/GS-A-candidate_completeness_scorecard.json",
    }
    expected_c_members = {
        "GS-C-candidate/GS-C-candidate_acceptance_packet.json",
        "GS-C-candidate/GS-C-candidate_Tier1_candidate_report.md",
        "GS-C-candidate/GS-C-candidate_completeness_scorecard.json",
    }
    assert expected_a_members <= set(names)
    assert expected_c_members <= set(names)
    assert "GS-C-candidate/GS-C-candidate_convergence_study.json" not in names

    # Step 5: every bundle member preserves the Tier 1 banner; no
    # forbidden positive-claim leakage across the full bundle.
    forbidden = (
        "validated against",
        "perforation completed",
        "bullet-through-steel complete",
        "validated physics",
    )
    with zipfile.ZipFile(io.BytesIO(bundle_bytes)) as zf:
        for name in zf.namelist():
            text = zf.read(name).decode("utf-8").lower()
            stripped = (
                text.replace("not_signed_validation", "")
                .replace("not_benchmark_agreement", "")
                .replace("not signed validation", "")
                .replace("not benchmark agreement", "")
            )
            for token in forbidden:
                assert token not in stripped, f"member {name!r} leaked {token!r}"
            # Positive disclaimer must be present.
            assert any(
                marker in text
                for marker in (
                    "tier 1",
                    "tier1_engineering_candidate",
                    "not signed validation",
                )
            ), f"member {name!r} lacks Tier 1 marker"

    # Step 6: archive one acceptance packet, then diff archived-vs-current.
    reports = repo_root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    archive_path = reports / "GS-A-candidate_acceptance_packet.archive.json"
    with zipfile.ZipFile(io.BytesIO(bundle_bytes)) as zf:
        archive_path.write_bytes(zf.read("GS-A-candidate/GS-A-candidate_acceptance_packet.json"))

    # Build a "current state" acceptance packet from the live evidence
    # (this is also what /acceptance-packet would produce). Mutate the
    # underlying ballistic metrics first so the diff shows non-trivial
    # deltas — this proves the archive-vs-current workflow detects drift.
    metrics_path = (
        repo_root
        / "project_state"
        / "graph_executor"
        / "GS-A-candidate"
        / "ballistic"
        / "ballistic_metrics.json"
    )
    payload = json.loads(metrics_path.read_text(encoding="utf-8"))
    payload["residual_velocity_candidate_m_per_s"] = 80.0  # was 75
    payload["energy_audit"]["energy_balance_error_pct"] = 12.0  # was 19
    metrics_path.write_text(json.dumps(payload), encoding="utf-8")

    # Build the current packet via the reviewer bundle path so the schema
    # matches; extract just its acceptance packet member into reports/.
    new_bundle_bytes = build_reviewer_bundle(
        [_bundle_inputs_for(repo_root, "GS-A-candidate")], repo_root=repo_root
    )
    current_path = reports / "GS-A-candidate_acceptance_packet.current.json"
    with zipfile.ZipFile(io.BytesIO(new_bundle_bytes)) as zf:
        current_path.write_bytes(zf.read("GS-A-candidate/GS-A-candidate_acceptance_packet.json"))

    diff = diff_archived_packets(archive_path, current_path, repo_root=repo_root)
    assert diff.same_case is True
    # Residual velocity drifted 75 → 80 ⇒ delta 5, delta_pct ≈ 6.67%.
    assert diff.residual_velocity_diff["delta"] == 5.0
    assert (
        diff.residual_velocity_diff["delta_pct"] is not None
        and abs(diff.residual_velocity_diff["delta_pct"] - (5 / 75 * 100)) < 1e-6
    )
    # Energy balance error drifted 19 → 12 ⇒ |delta| = 7%.
    assert diff.energy_balance_error_diff["delta_abs_pct"] == 7.0
    # Perforation marker unchanged.
    assert diff.perforation_marker_diff["same_marker"] is True

    # Final audit: rendered diff JSON preserves the Tier 1 boundary
    # wording verbatim.
    diff_text = render_archived_packet_diff_json(diff).lower()
    assert "tier1_engineering_candidate" in diff_text
    assert "not_signed_validation" in diff_text
    assert "not_benchmark_agreement" in diff_text

    # Also re-confirm the scorer JSON for the post-drift state still
    # carries the FM-04b blockers list (load-bearing assertion that
    # completeness scoring does not auto-promote at drift time).
    drifted_score = score_case_completeness(_completeness_inputs_for(repo_root, "GS-A-candidate"))
    drifted_text = render_case_completeness_json(drifted_score).lower()
    assert "tier1_engineering_candidate" in drifted_text
    assert any("adr-024 (full)" in b.lower() for b in drifted_score.tier2_blockers_remaining)
