"""FM-04a Phase 7 A — convergence_study.json snapshot capture tests.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Closes Phase 6 retrospective carry-forward §1: snapshot writer now
captures each case's live ``convergence_study.json`` into
``snapshots/<label>/convergence/<case>.json``, and the timeline + diff
recover the convergence verdict from that captured bytes instead of
from a metrics-inlined ``convergence_summary`` block.

MINOR bump on ``COHORT_SNAPSHOT_MANIFEST_SCHEMA_VERSION`` (1.1.0 → 1.2.0).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.services.reporting._schema_versions import (
    COHORT_SNAPSHOT_MANIFEST_SCHEMA_VERSION,
)
from app.services.reporting.cohort_snapshot import (
    SNAPSHOT_MANIFEST_FILENAME,
    SnapshotCaseInput,
    write_cohort_snapshot,
)
from app.services.reporting.cohort_snapshot_diff import diff_cohort_snapshots
from app.services.reporting.trust_score_timeline import build_trust_score_timeline


def _make_case(
    case_id: str,
    root: Path,
    *,
    convergence_verdict: str,
    residual_velocity: float = 75.0,
) -> SnapshotCaseInput:
    case_dir = root / "golden_samples" / case_id / "data"
    case_dir.mkdir(parents=True, exist_ok=True)
    starter = case_dir / "model_00_0000.rad"
    engine = case_dir / "model_00_0001.rad"
    starter.write_text("# starter", encoding="utf-8")
    engine.write_text("# engine", encoding="utf-8")

    metrics_payload = {
        "case_id": case_id,
        "projectile_initial_velocity_m_per_s": 300.0,
        "perforation": {
            "marker": "candidate_perforation",
            "residual_velocity_m_per_s": residual_velocity,
        },
        "energy_audit": {
            "status": "closed_aggregate",
            "energy_balance_error_pct": 8.0,
        },
        # Deliberately NO convergence_summary inlined so we can prove
        # Phase 7 A's captured convergence file is what recovers the
        # verdict (not the Phase 6 D fallback).
        "claim_boundary": (
            "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"
        ),
    }
    metrics_path = (
        root / "project_state" / "graph_executor" / case_id / "ballistic" / "ballistic_metrics.json"
    )
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(metrics_payload), encoding="utf-8")

    convergence_payload = {
        "case_id": case_id,
        "schema_version": "1.0.0",
        "study_metric": "residual_velocity_m_per_s",
        "tolerance_pct": 5.0,
        "combined_verdict": convergence_verdict,
        "mesh_sweep": {"runs": [], "candidate_stability": convergence_verdict},
        "dt_sweep": {"runs": [], "candidate_stability": convergence_verdict},
        "row_count": 0,
        "rows": [],
        "claim_boundary": (
            "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"
        ),
        "energy_balance_observation": {"status": "closed_aggregate"},
    }
    convergence_path = (
        root
        / "project_state"
        / "graph_executor"
        / case_id
        / "convergence"
        / "convergence_study.json"
    )
    convergence_path.parent.mkdir(parents=True, exist_ok=True)
    convergence_path.write_text(json.dumps(convergence_payload), encoding="utf-8")

    return SnapshotCaseInput(
        case_id=case_id,
        starter_deck_path=starter,
        engine_deck_path=engine,
        ballistic_metrics_path=metrics_path,
        convergence_study_path=convergence_path,
        animation_manifest_path=None,
        result_mesh_path=None,
        generator_script_path=None,
        notes_path=None,
    )


# ---------------------------------------------------------------------
# Schema bump
# ---------------------------------------------------------------------


def test_manifest_schema_version_bumped_to_1_2_0() -> None:
    """Bump history (Phase 7 A added convergence; later bumps additive):

    *  Phase 7 A  1.1.0 -> 1.2.0  (convergence/<case>.json)
    *  Phase 9 B  1.2.0 -> 1.3.0  (generator/<case>.py)

    Test name reflects the Phase 7 A bump; constant tracks current head.
    """
    assert COHORT_SNAPSHOT_MANIFEST_SCHEMA_VERSION == "1.3.0"


# ---------------------------------------------------------------------
# Writer: convergence file capture
# ---------------------------------------------------------------------


def test_writer_copies_convergence_file_into_snapshot(tmp_path: Path) -> None:
    case = _make_case("GS-A-candidate", tmp_path, convergence_verdict="candidate_observed_stable")
    result = write_cohort_snapshot([case], repo_root=tmp_path)
    captured = result.snapshot_dir / "convergence" / "GS-A-candidate.json"
    assert captured.is_file()
    payload = json.loads(captured.read_text(encoding="utf-8"))
    assert payload["combined_verdict"] == "candidate_observed_stable"
    assert payload["case_id"] == "GS-A-candidate"


def test_writer_lists_convergence_member_in_manifest(tmp_path: Path) -> None:
    case = _make_case("GS-A-candidate", tmp_path, convergence_verdict="candidate_observed_stable")
    result = write_cohort_snapshot([case], repo_root=tmp_path)
    manifest = json.loads(
        (result.snapshot_dir / SNAPSHOT_MANIFEST_FILENAME).read_text(encoding="utf-8")
    )
    assert "convergence/GS-A-candidate.json" in manifest["members"]
    # Tracks the current writer's stamp; bumped to 1.3.0 in Phase 9 B.
    assert manifest["schema_version"] == "1.3.0"


def test_writer_skips_convergence_capture_when_source_absent(tmp_path: Path) -> None:
    """A case with no live convergence_study.json on disk produces no
    captured convergence file; the manifest's ``members`` list omits it.
    """
    case = _make_case("GS-A-candidate", tmp_path, convergence_verdict="candidate_observed_stable")
    # Remove the source convergence file before writing the snapshot.
    case.convergence_study_path.unlink()
    result = write_cohort_snapshot([case], repo_root=tmp_path)
    captured = result.snapshot_dir / "convergence" / "GS-A-candidate.json"
    assert not captured.exists()
    manifest = json.loads(
        (result.snapshot_dir / SNAPSHOT_MANIFEST_FILENAME).read_text(encoding="utf-8")
    )
    assert "convergence/GS-A-candidate.json" not in manifest["members"]


def test_writer_runs_forbidden_claim_audit_on_convergence_capture(
    tmp_path: Path,
) -> None:
    """The captured convergence file must pass the cross-member
    ``_assert_no_overclaim_text`` audit, same guarantee Phase 6 A gives
    for ``metrics/<case>.json``. Uses one of the literal forbidden
    tokens (``perforation completed``) so the audit is provoked rather
    than the disclaimer-language allowed form ``not perforation completed``.
    """
    case = _make_case("GS-A-candidate", tmp_path, convergence_verdict="candidate_observed_stable")
    case.convergence_study_path.write_text(
        json.dumps({"note": "perforation completed in this run"}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="forbidden"):
        write_cohort_snapshot([case], repo_root=tmp_path)


# ---------------------------------------------------------------------
# Diff: recover convergence verdict from captured file
# ---------------------------------------------------------------------


def test_diff_recovers_convergence_verdict_from_captured_file(tmp_path: Path) -> None:
    """The metrics file in this test has NO ``convergence_summary``
    block, so Phase 6 D's fallback returns None. The diff must instead
    recover the verdict from the Phase 7 A captured convergence file.
    """
    case_a = _make_case("GS-A-candidate", tmp_path, convergence_verdict="candidate_observed_stable")
    write_cohort_snapshot([case_a], repo_root=tmp_path, snapshot_label="2026-05-16T100000Z")

    case_b = _make_case(
        "GS-A-candidate", tmp_path, convergence_verdict="candidate_observed_unstable"
    )
    write_cohort_snapshot([case_b], repo_root=tmp_path, snapshot_label="2026-05-16T200000Z")

    diff = diff_cohort_snapshots(tmp_path, "2026-05-16T100000Z", "2026-05-16T200000Z")
    assert len(diff.numerical_deltas) == 1
    verdict_pair = diff.numerical_deltas[0].convergence_combined_verdict
    assert verdict_pair["a"] == "candidate_observed_stable"
    assert verdict_pair["b"] == "candidate_observed_unstable"
    assert verdict_pair["same_verdict"] is False


def test_diff_falls_back_to_metrics_inline_when_convergence_capture_absent(
    tmp_path: Path,
) -> None:
    """When the captured convergence/<case>.json is removed but the
    metrics file inlines a ``convergence_summary``, the diff falls back
    to the Phase 6 D inline path. This preserves backward compatibility
    with 1.1.0 snapshots.
    """
    case_a = _make_case("GS-A-candidate", tmp_path, convergence_verdict="candidate_observed_stable")
    a_result = write_cohort_snapshot(
        [case_a], repo_root=tmp_path, snapshot_label="2026-05-16T100000Z"
    )
    case_b = _make_case(
        "GS-A-candidate", tmp_path, convergence_verdict="candidate_observed_unstable"
    )
    b_result = write_cohort_snapshot(
        [case_b], repo_root=tmp_path, snapshot_label="2026-05-16T200000Z"
    )

    # Simulate a 1.1.0 snapshot: remove the captured convergence files
    # but rewrite metrics with an inline convergence_summary fallback.
    (a_result.snapshot_dir / "convergence" / "GS-A-candidate.json").unlink()
    (b_result.snapshot_dir / "convergence" / "GS-A-candidate.json").unlink()

    metrics_a_path = a_result.snapshot_dir / "metrics" / "GS-A-candidate.json"
    payload_a = json.loads(metrics_a_path.read_text(encoding="utf-8"))
    payload_a["convergence_summary"] = {"combined_verdict": "candidate_observed_stable"}
    metrics_a_path.write_text(json.dumps(payload_a), encoding="utf-8")

    metrics_b_path = b_result.snapshot_dir / "metrics" / "GS-A-candidate.json"
    payload_b = json.loads(metrics_b_path.read_text(encoding="utf-8"))
    payload_b["convergence_summary"] = {"combined_verdict": "candidate_observed_unstable"}
    metrics_b_path.write_text(json.dumps(payload_b), encoding="utf-8")

    diff = diff_cohort_snapshots(tmp_path, "2026-05-16T100000Z", "2026-05-16T200000Z")
    verdict_pair = diff.numerical_deltas[0].convergence_combined_verdict
    assert verdict_pair["a"] == "candidate_observed_stable"
    assert verdict_pair["b"] == "candidate_observed_unstable"


# ---------------------------------------------------------------------
# Timeline: score convergence axis from captured file
# ---------------------------------------------------------------------


def test_timeline_scores_convergence_axis_from_captured_file(tmp_path: Path) -> None:
    """A snapshot with a captured convergence/<case>.json (Phase 7 A)
    but no inline convergence_summary must still score the convergence
    axis non-zero. This is the Phase 6 §1 carry-forward closure proof.
    """
    case = _make_case("GS-A-candidate", tmp_path, convergence_verdict="candidate_observed_stable")
    write_cohort_snapshot([case], repo_root=tmp_path, snapshot_label="2026-05-16T100000Z")

    # Seed completeness file so the timeline emits a point.
    snap_dir = tmp_path / "reports" / "snapshots" / "2026-05-16T100000Z"
    (snap_dir / "completeness" / "GS-A-candidate.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "case_id": "GS-A-candidate",
                "score": 80,
                "score_max": 100,
                "claim_boundary": (
                    "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"
                ),
            }
        ),
        encoding="utf-8",
    )

    timeline = build_trust_score_timeline("GS-A-candidate", tmp_path)
    assert timeline.point_count == 1
    point = timeline.points[0]
    # Both axes reported candidate_observed_stable -> raw 100 -> weighted = CONVERGENCE_WEIGHT
    assert point.convergence_weighted > 0


def test_timeline_falls_back_to_zero_when_no_convergence_signal(tmp_path: Path) -> None:
    """When neither the captured convergence file nor an inline
    convergence_summary is available, the timeline conservatively
    scores convergence at 0 (Phase 6 D behavior preserved).
    """
    case = _make_case("GS-A-candidate", tmp_path, convergence_verdict="candidate_observed_stable")
    result = write_cohort_snapshot([case], repo_root=tmp_path, snapshot_label="2026-05-16T100000Z")
    # Remove the captured convergence file (no inline fallback either).
    (result.snapshot_dir / "convergence" / "GS-A-candidate.json").unlink()
    # Seed completeness file so the timeline emits a point.
    (result.snapshot_dir / "completeness" / "GS-A-candidate.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "case_id": "GS-A-candidate",
                "score": 80,
                "score_max": 100,
                "claim_boundary": (
                    "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"
                ),
            }
        ),
        encoding="utf-8",
    )

    timeline = build_trust_score_timeline("GS-A-candidate", tmp_path)
    point = timeline.points[0]
    assert point.convergence_weighted == 0


# ---------------------------------------------------------------------
# Backward compatibility: 1.1.0 snapshots still readable
# ---------------------------------------------------------------------


def test_diff_handles_mixed_1_1_0_and_1_2_0_snapshots(tmp_path: Path) -> None:
    """A 1.1.0 snapshot (no convergence/ directory) on one side and a
    1.2.0 snapshot on the other must still produce a well-formed diff;
    the convergence verdict pair surfaces the captured side as the
    available value and the 1.1.0 side falls back to inline / None.
    """
    case_a = _make_case("GS-A-candidate", tmp_path, convergence_verdict="candidate_observed_stable")
    a_result = write_cohort_snapshot(
        [case_a], repo_root=tmp_path, snapshot_label="2026-05-16T100000Z"
    )
    # Simulate a 1.1.0 snapshot: remove the captured convergence file.
    (a_result.snapshot_dir / "convergence" / "GS-A-candidate.json").unlink()

    case_b = _make_case(
        "GS-A-candidate", tmp_path, convergence_verdict="candidate_observed_unstable"
    )
    write_cohort_snapshot([case_b], repo_root=tmp_path, snapshot_label="2026-05-16T200000Z")

    diff = diff_cohort_snapshots(tmp_path, "2026-05-16T100000Z", "2026-05-16T200000Z")
    verdict_pair = diff.numerical_deltas[0].convergence_combined_verdict
    # 1.1.0 side has no captured file AND no inline summary -> None
    assert verdict_pair["a"] is None
    # 1.2.0 side recovers verdict from captured file
    assert verdict_pair["b"] == "candidate_observed_unstable"
    assert verdict_pair["same_verdict"] is False
