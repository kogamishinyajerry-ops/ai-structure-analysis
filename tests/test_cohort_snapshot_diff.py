"""Tests for the Tier 1 cohort snapshot diff (FM-04a Phase 5 D).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.services.reporting._schema_versions import (
    COHORT_SNAPSHOT_DIFF_SCHEMA_VERSION,
)
from app.services.reporting.cohort_snapshot import (
    SNAPSHOT_MANIFEST_FILENAME,
    snapshots_root,
)
from app.services.reporting.cohort_snapshot_diff import (
    diff_cohort_snapshots,
    render_cohort_snapshot_diff_json,
)

# ---------------------------------------------------------------------
# fixtures: assemble two snapshot directories directly (don't depend
# on the full write_cohort_snapshot pipeline)
# ---------------------------------------------------------------------


def _seed_snapshot(
    tmp_path: Path,
    label: str,
    *,
    cases: list[str],
    completeness: dict[str, int | None] | None = None,
    repro: dict[str, dict] | None = None,
) -> Path:
    root = snapshots_root(tmp_path) / label
    root.mkdir(parents=True, exist_ok=True)
    (root / "completeness").mkdir(parents=True, exist_ok=True)
    (root / "reproducibility").mkdir(parents=True, exist_ok=True)
    completeness = completeness or {}
    repro = repro or {}

    manifest = {
        "schema_version": "1.0.0",
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

    for case_id in cases:
        score = completeness.get(case_id)
        if score is not None:
            (root / "completeness" / f"{case_id}.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "rubric_version": "1.0.0",
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
        repro_payload = repro.get(case_id)
        if repro_payload is not None:
            (root / "reproducibility" / f"{case_id}.json").write_text(
                json.dumps(repro_payload, indent=2, sort_keys=True), encoding="utf-8"
            )
    return root


# ---------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------


def test_diff_stamps_schema_version(tmp_path: Path) -> None:
    _seed_snapshot(
        tmp_path,
        "2026-05-16T100000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": 80},
    )
    _seed_snapshot(
        tmp_path,
        "2026-05-16T200000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": 85},
    )
    diff = diff_cohort_snapshots(tmp_path, "2026-05-16T100000Z", "2026-05-16T200000Z")
    rendered = json.loads(render_cohort_snapshot_diff_json(diff))
    assert rendered["schema_version"] == COHORT_SNAPSHOT_DIFF_SCHEMA_VERSION
    assert rendered["snapshot_a_label"] == "2026-05-16T100000Z"
    assert rendered["snapshot_b_label"] == "2026-05-16T200000Z"


def test_diff_detects_cohort_additions_and_removals(tmp_path: Path) -> None:
    _seed_snapshot(
        tmp_path,
        "2026-05-16T100000Z",
        cases=["GS-A-candidate", "GS-B-candidate"],
        completeness={"GS-A-candidate": 80, "GS-B-candidate": 70},
    )
    _seed_snapshot(
        tmp_path,
        "2026-05-16T200000Z",
        cases=["GS-A-candidate", "GS-C-candidate"],
        completeness={"GS-A-candidate": 85, "GS-C-candidate": 60},
    )
    diff = diff_cohort_snapshots(tmp_path, "2026-05-16T100000Z", "2026-05-16T200000Z")
    assert diff.cohort_added == ["GS-C-candidate"]
    assert diff.cohort_removed == ["GS-B-candidate"]
    assert diff.cohort_shared == ["GS-A-candidate"]
    assert diff.a_cohort_count == 2
    assert diff.b_cohort_count == 2


def test_diff_reports_completeness_score_delta(tmp_path: Path) -> None:
    _seed_snapshot(
        tmp_path,
        "2026-05-16T100000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": 70},
    )
    _seed_snapshot(
        tmp_path,
        "2026-05-16T200000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": 85},
    )
    diff = diff_cohort_snapshots(tmp_path, "2026-05-16T100000Z", "2026-05-16T200000Z")
    assert len(diff.completeness_deltas) == 1
    entry = diff.completeness_deltas[0]
    assert entry.case_id == "GS-A-candidate"
    assert entry.a_score == 70
    assert entry.b_score == 85
    assert entry.delta == 15


def test_diff_handles_missing_completeness_files(tmp_path: Path) -> None:
    _seed_snapshot(
        tmp_path,
        "2026-05-16T100000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": None},  # do not write the file
    )
    _seed_snapshot(
        tmp_path,
        "2026-05-16T200000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": 85},
    )
    diff = diff_cohort_snapshots(tmp_path, "2026-05-16T100000Z", "2026-05-16T200000Z")
    entry = diff.completeness_deltas[0]
    assert entry.a_score is None
    assert entry.b_score == 85
    assert entry.delta is None


def test_diff_detects_git_sha_drift(tmp_path: Path) -> None:
    repro_a = {
        "schema_version": "1.0.0",
        "case_id": "GS-A-candidate",
        "claim_boundary": "tier1_engineering_candidate",
        "git_commit_sha": "a" * 40,
        "git_dirty": False,
        "python_version": "3.11.15",
        "tracked_packages": [{"name": "fastapi", "version": "0.118.0"}],
        "scripts": [{"relpath": "scripts/gen.py", "sha256": "aa" * 32, "bytes": 100}],
    }
    repro_b = {
        "schema_version": "1.0.0",
        "case_id": "GS-A-candidate",
        "claim_boundary": "tier1_engineering_candidate",
        "git_commit_sha": "b" * 40,
        "git_dirty": True,
        "python_version": "3.11.16",
        "tracked_packages": [{"name": "fastapi", "version": "0.119.0"}],
        "scripts": [{"relpath": "scripts/gen.py", "sha256": "bb" * 32, "bytes": 120}],
    }
    _seed_snapshot(
        tmp_path,
        "2026-05-16T100000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": 80},
        repro={"GS-A-candidate": repro_a},
    )
    _seed_snapshot(
        tmp_path,
        "2026-05-16T200000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": 80},
        repro={"GS-A-candidate": repro_b},
    )
    diff = diff_cohort_snapshots(tmp_path, "2026-05-16T100000Z", "2026-05-16T200000Z")
    entry = diff.reproducibility_deltas[0]
    assert entry.git_sha_changed is True
    assert entry.dirty_changed is True
    assert entry.python_version_changed is True
    assert len(entry.package_version_changes) == 1
    assert entry.package_version_changes[0]["name"] == "fastapi"
    assert entry.package_version_changes[0]["a_version"] == "0.118.0"
    assert entry.package_version_changes[0]["b_version"] == "0.119.0"
    assert len(entry.script_sha_changes) == 1
    assert entry.script_sha_changes[0]["relpath"] == "scripts/gen.py"


def test_diff_omits_unchanged_packages_and_scripts(tmp_path: Path) -> None:
    repro = {
        "schema_version": "1.0.0",
        "case_id": "GS-A-candidate",
        "claim_boundary": "tier1_engineering_candidate",
        "git_commit_sha": "a" * 40,
        "git_dirty": False,
        "python_version": "3.11.15",
        "tracked_packages": [{"name": "fastapi", "version": "0.118.0"}],
        "scripts": [{"relpath": "scripts/gen.py", "sha256": "aa" * 32, "bytes": 100}],
    }
    _seed_snapshot(
        tmp_path,
        "2026-05-16T100000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": 80},
        repro={"GS-A-candidate": repro},
    )
    _seed_snapshot(
        tmp_path,
        "2026-05-16T200000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": 80},
        repro={"GS-A-candidate": repro},
    )
    diff = diff_cohort_snapshots(tmp_path, "2026-05-16T100000Z", "2026-05-16T200000Z")
    entry = diff.reproducibility_deltas[0]
    assert entry.git_sha_changed is False
    assert entry.dirty_changed is False
    assert entry.python_version_changed is False
    assert entry.package_version_changes == []
    assert entry.script_sha_changes == []


def test_diff_rejects_invalid_label(tmp_path: Path) -> None:
    _seed_snapshot(
        tmp_path,
        "2026-05-16T100000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": 80},
    )
    with pytest.raises(ValueError, match="invalid snapshot label"):
        diff_cohort_snapshots(tmp_path, "bogus", "2026-05-16T100000Z")


def test_diff_raises_when_snapshot_missing(tmp_path: Path) -> None:
    _seed_snapshot(
        tmp_path,
        "2026-05-16T100000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": 80},
    )
    with pytest.raises(FileNotFoundError):
        diff_cohort_snapshots(tmp_path, "2026-05-16T100000Z", "2026-05-16T999999Z")


def test_diff_preserves_tier1_disclaimer_in_payload(tmp_path: Path) -> None:
    _seed_snapshot(
        tmp_path,
        "2026-05-16T100000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": 80},
    )
    _seed_snapshot(
        tmp_path,
        "2026-05-16T200000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": 85},
    )
    diff = diff_cohort_snapshots(tmp_path, "2026-05-16T100000Z", "2026-05-16T200000Z")
    rendered = render_cohort_snapshot_diff_json(diff)
    assert "Tier 1 engineering candidate" in rendered
    assert "not signed validation" in rendered
    assert "not benchmark agreement" in rendered


def test_diff_handles_empty_shared_cohort(tmp_path: Path) -> None:
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
    diff = diff_cohort_snapshots(tmp_path, "2026-05-16T100000Z", "2026-05-16T200000Z")
    assert diff.completeness_deltas == []
    assert diff.reproducibility_deltas == []
    assert diff.cohort_added == ["GS-B-candidate"]
    assert diff.cohort_removed == ["GS-A-candidate"]
