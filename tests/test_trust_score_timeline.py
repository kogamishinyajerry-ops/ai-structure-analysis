"""Tests for the Phase 6 D trust score timeline.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.services.reporting._schema_versions import (
    TRUST_SCORE_FORMULA_VERSION,
    TRUST_SCORE_TIMELINE_SCHEMA_VERSION,
)
from app.services.reporting.cohort_snapshot import (
    SNAPSHOT_MANIFEST_FILENAME,
    snapshots_root,
)
from app.services.reporting.trust_score_timeline import (
    build_trust_score_timeline,
    render_trust_score_timeline_json,
)


def _seed_snapshot(
    repo_root: Path,
    label: str,
    *,
    cases: list[str],
    completeness: dict[str, int] | None = None,
    reproducibility: dict[str, dict] | None = None,
    metrics: dict[str, dict] | None = None,
) -> Path:
    root = snapshots_root(repo_root) / label
    root.mkdir(parents=True, exist_ok=True)
    (root / "completeness").mkdir(parents=True, exist_ok=True)
    (root / "reproducibility").mkdir(parents=True, exist_ok=True)
    (root / "metrics").mkdir(parents=True, exist_ok=True)

    completeness = completeness or {}
    reproducibility = reproducibility or {}
    metrics = metrics or {}

    manifest = {
        "schema_version": "1.1.0",
        "snapshot_label": label,
        "captured_at_utc": f"2026-05-16T{label[11:13]}:00:00+00:00",
        "claim_tier": "Tier 1 engineering candidate",
        "claim_boundary": (
            "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"
        ),
        "cohort_count": len(cases),
        "cases": cases,
        "members": [],
        "reviewer_bundle_written": False,
        "tier2_blockers_remaining": [],
        "claim_impact": (
            "Tier 1 candidate cohort snapshot only; not signed validation; not benchmark agreement"
        ),
    }
    (root / SNAPSHOT_MANIFEST_FILENAME).write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )

    for case_id, score in completeness.items():
        (root / "completeness" / f"{case_id}.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.0.0",
                    "case_id": case_id,
                    "claim_boundary": (
                        "tier1_engineering_candidate; not_signed_validation; "
                        "not_benchmark_agreement"
                    ),
                    "score": score,
                    "score_max": 100,
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
    for case_id, payload in reproducibility.items():
        (root / "reproducibility" / f"{case_id}.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
        )
    for case_id, payload in metrics.items():
        (root / "metrics" / f"{case_id}.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
        )
    return root


# ---------------------------------------------------------------------
# envelope assertions
# ---------------------------------------------------------------------


def test_timeline_stamps_schema_and_formula_versions(tmp_path: Path) -> None:
    _seed_snapshot(
        tmp_path,
        "2026-05-16T100000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": 80},
    )
    timeline = build_trust_score_timeline("GS-A-candidate", tmp_path)
    rendered = json.loads(render_trust_score_timeline_json(timeline))
    assert rendered["schema_version"] == TRUST_SCORE_TIMELINE_SCHEMA_VERSION
    assert rendered["formula_version"] == TRUST_SCORE_FORMULA_VERSION
    assert rendered["case_id"] == "GS-A-candidate"
    assert rendered["claim_tier"] == "Tier 1 engineering candidate"


def test_timeline_preserves_tier1_disclaimer(tmp_path: Path) -> None:
    _seed_snapshot(
        tmp_path,
        "2026-05-16T100000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": 80},
    )
    rendered = render_trust_score_timeline_json(
        build_trust_score_timeline("GS-A-candidate", tmp_path)
    )
    assert "not signed validation" in rendered
    assert "not benchmark agreement" in rendered


# ---------------------------------------------------------------------
# ordering + skipping behavior
# ---------------------------------------------------------------------


def test_timeline_orders_points_oldest_first(tmp_path: Path) -> None:
    _seed_snapshot(
        tmp_path,
        "2026-05-16T200000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": 90},
    )
    _seed_snapshot(
        tmp_path,
        "2026-05-16T100000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": 70},
    )
    timeline = build_trust_score_timeline("GS-A-candidate", tmp_path)
    labels = [p.snapshot_label for p in timeline.points]
    assert labels == ["2026-05-16T100000Z", "2026-05-16T200000Z"]


def test_timeline_skips_snapshots_missing_the_case(tmp_path: Path) -> None:
    _seed_snapshot(
        tmp_path,
        "2026-05-16T100000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": 80},
    )
    _seed_snapshot(
        tmp_path,
        "2026-05-16T200000Z",
        cases=["GS-B-candidate"],
        completeness={"GS-B-candidate": 70},
    )
    timeline = build_trust_score_timeline("GS-A-candidate", tmp_path)
    assert len(timeline.points) == 1
    assert timeline.points[0].snapshot_label == "2026-05-16T100000Z"


def test_timeline_skips_non_label_directories(tmp_path: Path) -> None:
    _seed_snapshot(
        tmp_path,
        "2026-05-16T100000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": 80},
    )
    # add a bogus directory under reports/snapshots/
    bogus = snapshots_root(tmp_path) / "not-a-label"
    bogus.mkdir()
    timeline = build_trust_score_timeline("GS-A-candidate", tmp_path)
    assert timeline.point_count == 1


def test_timeline_empty_when_no_snapshots(tmp_path: Path) -> None:
    timeline = build_trust_score_timeline("GS-A-candidate", tmp_path)
    assert timeline.points == []
    assert timeline.point_count == 0


# ---------------------------------------------------------------------
# per-axis weighted scores
# ---------------------------------------------------------------------


def test_timeline_completeness_weight_applied(tmp_path: Path) -> None:
    _seed_snapshot(
        tmp_path,
        "2026-05-16T100000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": 80},  # raw 80 -> weighted 40 (weight 50)
    )
    timeline = build_trust_score_timeline("GS-A-candidate", tmp_path)
    point = timeline.points[0]
    assert point.completeness_weighted == 40


def test_timeline_energy_audit_closed_aggregate_weight(tmp_path: Path) -> None:
    _seed_snapshot(
        tmp_path,
        "2026-05-16T100000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": 80},
        metrics={
            "GS-A-candidate": {
                "case_id": "GS-A-candidate",
                "energy_audit": {"status": "closed_aggregate"},
            }
        },
    )
    timeline = build_trust_score_timeline("GS-A-candidate", tmp_path)
    point = timeline.points[0]
    # closed_aggregate -> raw 100 -> weighted 15
    assert point.energy_audit_weighted == 15


def test_timeline_energy_audit_partial_candidate_weight(tmp_path: Path) -> None:
    _seed_snapshot(
        tmp_path,
        "2026-05-16T100000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": 80},
        metrics={
            "GS-A-candidate": {
                "case_id": "GS-A-candidate",
                "energy_audit": {"status": "partial_candidate"},
            }
        },
    )
    timeline = build_trust_score_timeline("GS-A-candidate", tmp_path)
    point = timeline.points[0]
    # partial_candidate raw 60 -> weighted 9
    assert point.energy_audit_weighted == 9


def test_timeline_reproducibility_clean_weight(tmp_path: Path) -> None:
    _seed_snapshot(
        tmp_path,
        "2026-05-16T100000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": 80},
        reproducibility={
            "GS-A-candidate": {
                "case_id": "GS-A-candidate",
                "git_commit_sha": "a" * 40,
                "git_dirty": False,
                "tracked_packages": [
                    {"name": "fastapi", "version": "0.118.0"},
                    {"name": "numpy", "version": "2.0.0"},
                ],
            }
        },
    )
    timeline = build_trust_score_timeline("GS-A-candidate", tmp_path)
    point = timeline.points[0]
    # raw 100 -> weighted 15
    assert point.reproducibility_weighted == 15


def test_timeline_reproducibility_dirty_deducts(tmp_path: Path) -> None:
    _seed_snapshot(
        tmp_path,
        "2026-05-16T100000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": 80},
        reproducibility={
            "GS-A-candidate": {
                "case_id": "GS-A-candidate",
                "git_commit_sha": "a" * 40,
                "git_dirty": True,
                "tracked_packages": [],
            }
        },
    )
    timeline = build_trust_score_timeline("GS-A-candidate", tmp_path)
    point = timeline.points[0]
    # dirty -30 -> raw 70 -> weighted 11 (rounded)
    assert point.reproducibility_weighted == round(70 * 15 / 100)


def test_timeline_total_equals_sum_of_axes(tmp_path: Path) -> None:
    _seed_snapshot(
        tmp_path,
        "2026-05-16T100000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": 100},
        reproducibility={
            "GS-A-candidate": {
                "case_id": "GS-A-candidate",
                "git_commit_sha": "a" * 40,
                "git_dirty": False,
                "tracked_packages": [],
            }
        },
        metrics={
            "GS-A-candidate": {
                "case_id": "GS-A-candidate",
                "energy_audit": {"status": "closed_aggregate"},
                "convergence_summary": {
                    "mesh_sweep": {"candidate_stability": "candidate_observed_stable"},
                    "dt_sweep": {"candidate_stability": "candidate_observed_stable"},
                },
            }
        },
    )
    timeline = build_trust_score_timeline("GS-A-candidate", tmp_path)
    point = timeline.points[0]
    assert point.trust_score == (
        point.completeness_weighted
        + point.convergence_weighted
        + point.energy_audit_weighted
        + point.reproducibility_weighted
    )
    # All maxed → 50 + 20 + 15 + 15 = 100
    assert point.trust_score == 100


def test_timeline_skips_snapshots_with_unparseable_completeness(tmp_path: Path) -> None:
    _seed_snapshot(
        tmp_path,
        "2026-05-16T100000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": 80},
    )
    bad = snapshots_root(tmp_path) / "2026-05-16T200000Z"
    bad.mkdir(parents=True)
    (bad / "completeness").mkdir()
    (bad / SNAPSHOT_MANIFEST_FILENAME).write_text("{}", encoding="utf-8")
    (bad / "completeness" / "GS-A-candidate.json").write_text("not json", encoding="utf-8")
    timeline = build_trust_score_timeline("GS-A-candidate", tmp_path)
    # the corrupt snapshot scores 0 across all axes but still appears
    # (completeness file existed, it just doesn't parse)
    assert len(timeline.points) == 2
    bad_point = next(p for p in timeline.points if p.snapshot_label == "2026-05-16T200000Z")
    assert bad_point.completeness_weighted == 0
    assert bad_point.trust_score == 0
