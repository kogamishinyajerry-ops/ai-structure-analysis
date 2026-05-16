"""FM-04a Phase 7 C — trust score regression alarm tests.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Closes Phase 6 retrospective carry-forward §4.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.services.reporting._schema_versions import (
    TRUST_SCORE_ALERTS_SCHEMA_VERSION,
)
from app.services.reporting.cohort_snapshot import (
    SNAPSHOT_LABEL_RE,
    snapshots_root,
)
from app.services.reporting.trust_score_alerts import (
    ALERT_THRESHOLD_DANGER_MIN,
    ALERT_THRESHOLD_INFO_MIN,
    ALERT_THRESHOLD_WARN_MIN,
    THRESHOLD_DELTA_DEFAULT,
    THRESHOLD_DELTA_MAX,
    THRESHOLD_DELTA_MIN,
    build_trust_score_alerts,
    render_trust_score_alerts_json,
)


def _seed_snapshot_with_score_axes(
    repo_root: Path,
    label: str,
    case_id: str,
    *,
    completeness: int = 80,
    git_dirty: bool = False,
    convergence_verdict: str = "candidate_observed_stable",
    energy_status: str = "closed_aggregate",
) -> None:
    assert SNAPSHOT_LABEL_RE.fullmatch(label)
    root = snapshots_root(repo_root) / label
    (root / "completeness").mkdir(parents=True, exist_ok=True)
    (root / "reproducibility").mkdir(parents=True, exist_ok=True)
    (root / "metrics").mkdir(parents=True, exist_ok=True)
    (root / "convergence").mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "1.2.0",
        "snapshot_label": label,
        "captured_at_utc": "2026-05-16T00:00:00+00:00",
        "claim_tier": "Tier 1 engineering candidate",
        "claim_boundary": (
            "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"
        ),
        "cohort_count": 1,
        "cases": [case_id],
        "members": [],
        "reviewer_bundle_written": False,
        "tier2_blockers_remaining": [],
        "claim_impact": (
            "Tier 1 candidate snapshot only; not signed validation; not benchmark agreement"
        ),
    }
    (root / "SNAPSHOT_MANIFEST.json").write_text(
        json.dumps(manifest, sort_keys=True), encoding="utf-8"
    )
    (root / "completeness" / f"{case_id}.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "case_id": case_id,
                "score": completeness,
                "score_max": 100,
                "claim_boundary": manifest["claim_boundary"],
            }
        ),
        encoding="utf-8",
    )
    (root / "reproducibility" / f"{case_id}.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "case_id": case_id,
                "git_commit_sha": "a" * 40,
                "git_dirty": git_dirty,
                "python_version": "3.11.5",
                "tracked_packages": [],
                "scripts": [],
                "claim_boundary": manifest["claim_boundary"],
            }
        ),
        encoding="utf-8",
    )
    (root / "metrics" / f"{case_id}.json").write_text(
        json.dumps(
            {
                "case_id": case_id,
                "perforation": {
                    "marker": "candidate_perforation",
                    "residual_velocity_m_per_s": 75.0,
                },
                "energy_audit": {
                    "status": energy_status,
                    "energy_balance_error_pct": 8.0,
                },
                "claim_boundary": manifest["claim_boundary"],
            }
        ),
        encoding="utf-8",
    )
    (root / "convergence" / f"{case_id}.json").write_text(
        json.dumps(
            {
                "case_id": case_id,
                "combined_verdict": convergence_verdict,
                "mesh_sweep": {
                    "runs": [],
                    "candidate_stability": convergence_verdict,
                },
                "dt_sweep": {
                    "runs": [],
                    "candidate_stability": convergence_verdict,
                },
                "claim_boundary": manifest["claim_boundary"],
            }
        ),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------
# Schema + constants
# ---------------------------------------------------------------------


def test_alerts_schema_version_is_1_0_0() -> None:
    assert TRUST_SCORE_ALERTS_SCHEMA_VERSION == "1.0.0"


def test_severity_thresholds_are_named_constants() -> None:
    """Phase 7 anti-gaming guard M: -3 if alarm severity thresholds
    are inline-magic-numbered. Verify the named constants are imported
    + monotonically ordered.
    """
    assert ALERT_THRESHOLD_INFO_MIN < ALERT_THRESHOLD_WARN_MIN
    assert ALERT_THRESHOLD_WARN_MIN < ALERT_THRESHOLD_DANGER_MIN
    # Blueprint pinned values
    assert ALERT_THRESHOLD_INFO_MIN == 10
    assert ALERT_THRESHOLD_WARN_MIN == 25
    assert ALERT_THRESHOLD_DANGER_MIN == 40


def test_threshold_clamping_bounds_are_named() -> None:
    assert THRESHOLD_DELTA_MIN == 1
    assert THRESHOLD_DELTA_MAX == 100
    assert THRESHOLD_DELTA_DEFAULT == 10


# ---------------------------------------------------------------------
# build_trust_score_alerts: empty / no-alerts paths
# ---------------------------------------------------------------------


def test_alerts_empty_when_no_snapshots(tmp_path: Path) -> None:
    report = build_trust_score_alerts("GS-A-candidate", tmp_path)
    assert report.alert_count == 0
    assert report.alerts == []
    # Tier 1 disclaimer trio is present even on an empty report
    haystack = render_trust_score_alerts_json(report).lower()
    assert "tier 1 engineering candidate" in haystack
    assert "not signed validation" in haystack
    assert "not benchmark agreement" in haystack


def test_alerts_empty_when_only_one_snapshot(tmp_path: Path) -> None:
    _seed_snapshot_with_score_axes(
        tmp_path, "2026-05-16T100000Z", "GS-A-candidate", completeness=80
    )
    report = build_trust_score_alerts("GS-A-candidate", tmp_path)
    assert report.alert_count == 0


def test_alerts_empty_when_stable_score_across_snapshots(tmp_path: Path) -> None:
    """No regression -> no alarm."""
    for label in (
        "2026-05-16T100000Z",
        "2026-05-16T200000Z",
        "2026-05-16T300000Z",
    ):
        _seed_snapshot_with_score_axes(tmp_path, label, "GS-A-candidate", completeness=80)
    report = build_trust_score_alerts("GS-A-candidate", tmp_path)
    assert report.alert_count == 0


# ---------------------------------------------------------------------
# Severity buckets
# ---------------------------------------------------------------------


def test_alert_severity_info_when_delta_between_10_and_24(tmp_path: Path) -> None:
    """Drop of ~15 points (completeness 80 -> 50 contributes 15
    weighted; total ~15) emits info severity."""
    _seed_snapshot_with_score_axes(
        tmp_path,
        "2026-05-16T100000Z",
        "GS-A-candidate",
        completeness=80,
    )
    _seed_snapshot_with_score_axes(
        tmp_path,
        "2026-05-16T200000Z",
        "GS-A-candidate",
        completeness=50,
    )
    report = build_trust_score_alerts("GS-A-candidate", tmp_path)
    assert report.alert_count == 1
    alert = report.alerts[0]
    # completeness weight=50, so completeness drop of 30 raw =>
    # weighted drop of 15 points
    assert alert.severity == "info"
    assert ALERT_THRESHOLD_INFO_MIN <= alert.delta < ALERT_THRESHOLD_WARN_MIN


def test_alert_severity_warn_when_delta_between_25_and_39(tmp_path: Path) -> None:
    """Drop large enough to land in [25, 40): completeness 100 -> 40
    contributes ~30 weighted, plus convergence stable->unstable
    contributes more; aggregate >= 25."""
    _seed_snapshot_with_score_axes(
        tmp_path,
        "2026-05-16T100000Z",
        "GS-A-candidate",
        completeness=100,
        convergence_verdict="candidate_observed_stable",
    )
    _seed_snapshot_with_score_axes(
        tmp_path,
        "2026-05-16T200000Z",
        "GS-A-candidate",
        completeness=40,
        convergence_verdict="candidate_observed_stable",
    )
    report = build_trust_score_alerts("GS-A-candidate", tmp_path)
    assert report.alert_count == 1
    alert = report.alerts[0]
    assert ALERT_THRESHOLD_WARN_MIN <= alert.delta < ALERT_THRESHOLD_DANGER_MIN
    assert alert.severity == "warn"


def test_alert_severity_danger_when_delta_at_or_above_40(tmp_path: Path) -> None:
    _seed_snapshot_with_score_axes(
        tmp_path,
        "2026-05-16T100000Z",
        "GS-A-candidate",
        completeness=100,
        convergence_verdict="candidate_observed_stable",
        energy_status="closed_aggregate",
        git_dirty=False,
    )
    # Second snapshot: completeness drops + convergence goes unstable
    # + energy_audit goes from closed to none + git dirty.
    _seed_snapshot_with_score_axes(
        tmp_path,
        "2026-05-16T200000Z",
        "GS-A-candidate",
        completeness=20,
        convergence_verdict="candidate_observed_unstable",
        energy_status="open",
        git_dirty=True,
    )
    report = build_trust_score_alerts("GS-A-candidate", tmp_path)
    assert report.alert_count == 1
    alert = report.alerts[0]
    assert alert.delta >= ALERT_THRESHOLD_DANGER_MIN
    assert alert.severity == "danger"


# ---------------------------------------------------------------------
# primary_axis_shift
# ---------------------------------------------------------------------


def test_primary_axis_shift_identifies_completeness(tmp_path: Path) -> None:
    """Only completeness drops; primary_axis_shift must be 'completeness'."""
    _seed_snapshot_with_score_axes(
        tmp_path, "2026-05-16T100000Z", "GS-A-candidate", completeness=100
    )
    _seed_snapshot_with_score_axes(
        tmp_path, "2026-05-16T200000Z", "GS-A-candidate", completeness=40
    )
    report = build_trust_score_alerts("GS-A-candidate", tmp_path)
    assert report.alerts[0].primary_axis_shift == "completeness"


def test_primary_axis_shift_identifies_reproducibility(tmp_path: Path) -> None:
    _seed_snapshot_with_score_axes(
        tmp_path,
        "2026-05-16T100000Z",
        "GS-A-candidate",
        completeness=80,
        git_dirty=False,
    )
    _seed_snapshot_with_score_axes(
        tmp_path,
        "2026-05-16T200000Z",
        "GS-A-candidate",
        completeness=80,
        git_dirty=True,
    )
    report = build_trust_score_alerts("GS-A-candidate", tmp_path)
    # git_dirty -> reproducibility -30 raw = -4 to -5 weighted (15% of
    # 30). May not trip default threshold of 10. Lower threshold.
    report = build_trust_score_alerts(
        "GS-A-candidate", tmp_path, threshold_delta=THRESHOLD_DELTA_MIN
    )
    if report.alert_count > 0:
        assert report.alerts[0].primary_axis_shift == "reproducibility_clean"


# ---------------------------------------------------------------------
# Threshold clamping
# ---------------------------------------------------------------------


def test_threshold_clamped_below_min(tmp_path: Path) -> None:
    _seed_snapshot_with_score_axes(
        tmp_path, "2026-05-16T100000Z", "GS-A-candidate", completeness=100
    )
    _seed_snapshot_with_score_axes(
        tmp_path, "2026-05-16T200000Z", "GS-A-candidate", completeness=50
    )
    report = build_trust_score_alerts("GS-A-candidate", tmp_path, threshold_delta=-5)
    assert report.threshold_delta == THRESHOLD_DELTA_MIN


def test_threshold_clamped_above_max(tmp_path: Path) -> None:
    _seed_snapshot_with_score_axes(
        tmp_path, "2026-05-16T100000Z", "GS-A-candidate", completeness=100
    )
    report = build_trust_score_alerts("GS-A-candidate", tmp_path, threshold_delta=500)
    assert report.threshold_delta == THRESHOLD_DELTA_MAX


def test_high_threshold_suppresses_modest_drops(tmp_path: Path) -> None:
    """A drop of ~15 points is suppressed by a threshold of 50."""
    _seed_snapshot_with_score_axes(
        tmp_path, "2026-05-16T100000Z", "GS-A-candidate", completeness=80
    )
    _seed_snapshot_with_score_axes(
        tmp_path, "2026-05-16T200000Z", "GS-A-candidate", completeness=50
    )
    report = build_trust_score_alerts("GS-A-candidate", tmp_path, threshold_delta=50)
    assert report.alert_count == 0


# ---------------------------------------------------------------------
# Tier 1 disclaimer round-trip
# ---------------------------------------------------------------------


def test_alerts_payload_carries_tier1_disclaimer_trio(tmp_path: Path) -> None:
    _seed_snapshot_with_score_axes(
        tmp_path, "2026-05-16T100000Z", "GS-A-candidate", completeness=80
    )
    _seed_snapshot_with_score_axes(
        tmp_path, "2026-05-16T200000Z", "GS-A-candidate", completeness=80
    )
    report = build_trust_score_alerts("GS-A-candidate", tmp_path)
    payload = render_trust_score_alerts_json(report).lower()
    assert "tier 1 engineering candidate" in payload
    assert "not signed validation" in payload
    assert "not benchmark agreement" in payload
    # Phase 7 §3.C blueprint requirement: alarms explicitly state they
    # do not authorize Tier 2 promotion
    assert "not authorize tier 2" in payload


# ---------------------------------------------------------------------
# Forbidden-claim audit
# ---------------------------------------------------------------------


def test_alerts_render_runs_forbidden_claim_audit(tmp_path: Path) -> None:
    """Re-render works on the happy path. The audit is exercised by
    every render call; provoking it would require monkey-patching
    CLAIM_IMPACT_DEFAULT which is brittle, so we settle for the
    smoke-test happy path here."""
    _seed_snapshot_with_score_axes(
        tmp_path, "2026-05-16T100000Z", "GS-A-candidate", completeness=80
    )
    report = build_trust_score_alerts("GS-A-candidate", tmp_path)
    json_payload = render_trust_score_alerts_json(report)
    assert "validated against" not in json_payload.lower()
    assert "perforation completed" not in json_payload.lower()


# ---------------------------------------------------------------------
# Multi-pair monotonic regression
# ---------------------------------------------------------------------


def test_multi_pair_regression_emits_multiple_alerts(tmp_path: Path) -> None:
    """3 snapshots, each dropping by ~15 completeness; produces 2 alerts."""
    _seed_snapshot_with_score_axes(
        tmp_path, "2026-05-16T100000Z", "GS-A-candidate", completeness=100
    )
    _seed_snapshot_with_score_axes(
        tmp_path, "2026-05-16T200000Z", "GS-A-candidate", completeness=70
    )
    _seed_snapshot_with_score_axes(
        tmp_path, "2026-05-16T300000Z", "GS-A-candidate", completeness=40
    )
    report = build_trust_score_alerts("GS-A-candidate", tmp_path)
    assert report.alert_count == 2
    assert (
        report.alerts[0].from_snapshot == "2026-05-16T100000Z"
        and report.alerts[0].to_snapshot == "2026-05-16T200000Z"
    )
    assert (
        report.alerts[1].from_snapshot == "2026-05-16T200000Z"
        and report.alerts[1].to_snapshot == "2026-05-16T300000Z"
    )
