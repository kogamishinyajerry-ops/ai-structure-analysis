"""Tests for the Phase 6 A snapshot manifest + diff schema bump.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Two surfaces under test:

1. ``write_cohort_snapshot`` now copies ``ballistic_metrics.json`` into
   ``snapshots/<label>/metrics/<case>.json`` (manifest schema bumped
   1.0.0 → 1.1.0 MINOR per the documented bump policy).

2. ``diff_cohort_snapshots`` surfaces a new ``numerical_deltas`` field
   per shared case, sourced from each side's ``metrics/<case>.json``.
   When either side is at manifest schema 1.0.0 (no metrics copied),
   the entry for that case is omitted gracefully (no exception).
"""

from __future__ import annotations

import json
from pathlib import Path

from app.services.reporting._schema_versions import (
    COHORT_SNAPSHOT_DIFF_SCHEMA_VERSION,
    COHORT_SNAPSHOT_MANIFEST_SCHEMA_VERSION,
)
from app.services.reporting.cohort_snapshot import (
    SNAPSHOT_MANIFEST_FILENAME,
    SnapshotCaseInput,
    snapshots_root,
    write_cohort_snapshot,
)
from app.services.reporting.cohort_snapshot_diff import diff_cohort_snapshots

# ---------------------------------------------------------------------
# fixtures (mirrors Phase 5 C test fixture style)
# ---------------------------------------------------------------------


def _write_metrics(case_id: str, root: Path, residual_velocity: float) -> Path:
    payload = {
        "case_id": case_id,
        "projectile_initial_velocity_m_per_s": 300.0,
        "perforation": {
            "marker": "candidate_perforation",
            "residual_velocity_m_per_s": residual_velocity,
        },
        "energy_audit": {
            "status": "closed_aggregate",
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
    path = (
        root / "project_state" / "graph_executor" / case_id / "ballistic" / "ballistic_metrics.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _write_convergence(case_id: str, root: Path) -> Path:
    payload = {
        "case_id": case_id,
        "study_metric": "residual_velocity_m_per_s",
        "tolerance_pct": 5.0,
        "combined_verdict": "candidate_observed_stable",
        "mesh_sweep": {"runs": [], "candidate_stability": "candidate_observed_stable"},
        "dt_sweep": {"runs": [], "candidate_stability": "candidate_observed_stable"},
        "row_count": 0,
        "rows": [],
        "claim_boundary": (
            "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"
        ),
        "energy_balance_observation": {"status": "closed_aggregate"},
    }
    path = (
        root
        / "project_state"
        / "graph_executor"
        / case_id
        / "convergence"
        / "convergence_study.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _write_starter_engine(case_id: str, root: Path) -> tuple[Path, Path]:
    case_dir = root / "golden_samples" / case_id / "data"
    case_dir.mkdir(parents=True, exist_ok=True)
    starter = case_dir / "model_00_0000.rad"
    engine = case_dir / "model_00_0001.rad"
    starter.write_text("# starter deck", encoding="utf-8")
    engine.write_text("# engine deck", encoding="utf-8")
    return starter, engine


def _make_case(case_id: str, root: Path, residual_velocity: float) -> SnapshotCaseInput:
    metrics = _write_metrics(case_id, root, residual_velocity)
    convergence = _write_convergence(case_id, root)
    starter, engine = _write_starter_engine(case_id, root)
    return SnapshotCaseInput(
        case_id=case_id,
        starter_deck_path=starter,
        engine_deck_path=engine,
        ballistic_metrics_path=metrics,
        convergence_study_path=convergence,
    )


# ---------------------------------------------------------------------
# Phase 6 A — snapshot manifest schema bump
# ---------------------------------------------------------------------


def test_snapshot_manifest_schema_version_bumped_to_1_2_0() -> None:
    # Bump history (additive MINOR per bump policy):
    #   Phase 5 C  1.0.0
    #   Phase 6 A  1.1.0  (metrics/<case>.json sibling)
    #   Phase 7 A  1.2.0  (convergence/<case>.json sibling)
    #   Phase 9 B  1.3.0  (generator/<case>.py sibling)
    # The test name reflects the original Phase 6 A bump; the constant
    # now tracks Phase 9 B. Old consumers reading 1.2.0 fields continue
    # to work because every bump has been additive.
    assert COHORT_SNAPSHOT_MANIFEST_SCHEMA_VERSION == "1.3.0"


def test_snapshot_diff_schema_version_bumped_to_1_1_0() -> None:
    assert COHORT_SNAPSHOT_DIFF_SCHEMA_VERSION == "1.1.0"


def test_writer_copies_metrics_to_snapshot_dir(tmp_path: Path) -> None:
    case = _make_case("GS-A-candidate", tmp_path, residual_velocity=75.0)
    result = write_cohort_snapshot([case], repo_root=tmp_path)
    metrics_copy = result.snapshot_dir / "metrics" / "GS-A-candidate.json"
    assert metrics_copy.is_file()
    payload = json.loads(metrics_copy.read_text(encoding="utf-8"))
    assert payload["perforation"]["residual_velocity_m_per_s"] == 75.0


def test_writer_lists_metrics_member_in_manifest(tmp_path: Path) -> None:
    case = _make_case("GS-A-candidate", tmp_path, residual_velocity=75.0)
    result = write_cohort_snapshot([case], repo_root=tmp_path)
    manifest = json.loads(
        (result.snapshot_dir / SNAPSHOT_MANIFEST_FILENAME).read_text(encoding="utf-8")
    )
    assert "metrics/GS-A-candidate.json" in manifest["members"]


def test_writer_skips_metrics_copy_when_path_missing(tmp_path: Path) -> None:
    starter, engine = _write_starter_engine("GS-A-candidate", tmp_path)
    case = SnapshotCaseInput(
        case_id="GS-A-candidate",
        starter_deck_path=starter,
        engine_deck_path=engine,
        ballistic_metrics_path=None,
    )
    result = write_cohort_snapshot([case], repo_root=tmp_path)
    metrics_dir = result.snapshot_dir / "metrics"
    assert metrics_dir.is_dir()
    assert list(metrics_dir.iterdir()) == []
    manifest = json.loads(
        (result.snapshot_dir / SNAPSHOT_MANIFEST_FILENAME).read_text(encoding="utf-8")
    )
    assert not any(m.startswith("metrics/") for m in manifest["members"])


# ---------------------------------------------------------------------
# Phase 6 A — snapshot diff numerical_deltas
# ---------------------------------------------------------------------


def test_diff_surfaces_residual_velocity_delta(tmp_path: Path) -> None:
    a_root = tmp_path / "a"
    b_root = tmp_path / "b"
    a_root.mkdir()
    b_root.mkdir()

    case_a = _make_case("GS-A-candidate", a_root, residual_velocity=75.0)
    write_cohort_snapshot([case_a], repo_root=a_root, snapshot_label="2026-05-16T100000Z")

    case_b = _make_case("GS-A-candidate", b_root, residual_velocity=80.0)
    write_cohort_snapshot([case_b], repo_root=b_root, snapshot_label="2026-05-16T200000Z")

    # Move the b snapshot under the a tree so the diff sees both
    import shutil

    shutil.copytree(
        snapshots_root(b_root) / "2026-05-16T200000Z",
        snapshots_root(a_root) / "2026-05-16T200000Z",
    )

    diff = diff_cohort_snapshots(a_root, "2026-05-16T100000Z", "2026-05-16T200000Z")
    assert len(diff.numerical_deltas) == 1
    delta = diff.numerical_deltas[0]
    assert delta.case_id == "GS-A-candidate"
    assert delta.residual_velocity_m_per_s["a"] == 75.0
    assert delta.residual_velocity_m_per_s["b"] == 80.0
    assert delta.residual_velocity_m_per_s["delta"] == 5.0
    # delta_pct rounded to 6 decimals at the builder; tolerance follows
    assert abs(delta.residual_velocity_m_per_s["delta_pct"] - 6.666667) < 1e-6


def test_diff_surfaces_energy_balance_error_delta(tmp_path: Path) -> None:
    case = _make_case("GS-A-candidate", tmp_path, residual_velocity=75.0)
    write_cohort_snapshot([case], repo_root=tmp_path, snapshot_label="2026-05-16T100000Z")

    # Drift the energy balance error
    metrics = _write_metrics("GS-A-candidate", tmp_path, residual_velocity=75.0)
    payload = json.loads(metrics.read_text(encoding="utf-8"))
    payload["energy_audit"]["energy_balance_error_pct"] = 8.5
    metrics.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    case = _make_case("GS-A-candidate", tmp_path, residual_velocity=75.0)
    metrics_path = (
        tmp_path
        / "project_state"
        / "graph_executor"
        / "GS-A-candidate"
        / "ballistic"
        / "ballistic_metrics.json"
    )
    payload = json.loads(metrics_path.read_text(encoding="utf-8"))
    payload["energy_audit"]["energy_balance_error_pct"] = 8.5
    metrics_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    case_b = _make_case("GS-A-candidate", tmp_path, residual_velocity=75.0)
    # Re-overlay the drift onto the live metrics file
    payload = json.loads(case_b.ballistic_metrics_path.read_text(encoding="utf-8"))
    payload["energy_audit"]["energy_balance_error_pct"] = 8.5
    case_b.ballistic_metrics_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    write_cohort_snapshot([case_b], repo_root=tmp_path, snapshot_label="2026-05-16T200000Z")
    diff = diff_cohort_snapshots(tmp_path, "2026-05-16T100000Z", "2026-05-16T200000Z")
    delta = diff.numerical_deltas[0]
    assert delta.energy_balance_error_pct["a"] == 12.0
    assert delta.energy_balance_error_pct["b"] == 8.5
    assert delta.energy_balance_error_pct["delta"] == -3.5
    assert delta.energy_balance_error_pct["delta_abs_pct"] == 3.5


def test_diff_surfaces_unchanged_perforation_marker(tmp_path: Path) -> None:
    case = _make_case("GS-A-candidate", tmp_path, residual_velocity=75.0)
    write_cohort_snapshot([case], repo_root=tmp_path, snapshot_label="2026-05-16T100000Z")
    case_b = _make_case("GS-A-candidate", tmp_path, residual_velocity=80.0)
    write_cohort_snapshot([case_b], repo_root=tmp_path, snapshot_label="2026-05-16T200000Z")
    diff = diff_cohort_snapshots(tmp_path, "2026-05-16T100000Z", "2026-05-16T200000Z")
    delta = diff.numerical_deltas[0]
    assert delta.perforation_marker["a"] == "candidate_perforation"
    assert delta.perforation_marker["b"] == "candidate_perforation"
    assert delta.perforation_marker["same_marker"] is True


def test_diff_falls_back_when_one_snapshot_lacks_metrics(tmp_path: Path) -> None:
    """If we manually delete the metrics file from one side, the diff
    must not crash — it surfaces the case in completeness_deltas but
    drops it from numerical_deltas.
    """
    case = _make_case("GS-A-candidate", tmp_path, residual_velocity=75.0)
    a_result = write_cohort_snapshot(
        [case], repo_root=tmp_path, snapshot_label="2026-05-16T100000Z"
    )
    case_b = _make_case("GS-A-candidate", tmp_path, residual_velocity=80.0)
    write_cohort_snapshot([case_b], repo_root=tmp_path, snapshot_label="2026-05-16T200000Z")
    # Simulate a 1.0.0 snapshot by deleting the metrics file
    (a_result.snapshot_dir / "metrics" / "GS-A-candidate.json").unlink()

    diff = diff_cohort_snapshots(tmp_path, "2026-05-16T100000Z", "2026-05-16T200000Z")
    # Both sides have metrics dir but one is missing the case file →
    # both _load_optional returns None on side a, side b loads fine →
    # delta still emitted with None on a side
    assert len(diff.numerical_deltas) == 1
    delta = diff.numerical_deltas[0]
    assert delta.residual_velocity_m_per_s["a"] is None
    assert delta.residual_velocity_m_per_s["b"] == 80.0
    assert delta.residual_velocity_m_per_s["delta"] is None


def test_diff_omits_numerical_deltas_when_both_snapshots_lack_metrics(
    tmp_path: Path,
) -> None:
    # Phase 7 A note: the diff now also reads convergence/<case>.json
    # when present. To exercise the "no source data on either side"
    # path we must remove both metrics/ and convergence/ files.
    case = _make_case("GS-A-candidate", tmp_path, residual_velocity=75.0)
    a_result = write_cohort_snapshot(
        [case], repo_root=tmp_path, snapshot_label="2026-05-16T100000Z"
    )
    case_b = _make_case("GS-A-candidate", tmp_path, residual_velocity=80.0)
    b_result = write_cohort_snapshot(
        [case_b], repo_root=tmp_path, snapshot_label="2026-05-16T200000Z"
    )
    (a_result.snapshot_dir / "metrics" / "GS-A-candidate.json").unlink()
    (b_result.snapshot_dir / "metrics" / "GS-A-candidate.json").unlink()
    (a_result.snapshot_dir / "convergence" / "GS-A-candidate.json").unlink()
    (b_result.snapshot_dir / "convergence" / "GS-A-candidate.json").unlink()

    diff = diff_cohort_snapshots(tmp_path, "2026-05-16T100000Z", "2026-05-16T200000Z")
    assert diff.numerical_deltas == []


def test_diff_renders_numerical_deltas_into_payload(tmp_path: Path) -> None:
    from app.services.reporting.cohort_snapshot_diff import (
        render_cohort_snapshot_diff_json,
    )

    case = _make_case("GS-A-candidate", tmp_path, residual_velocity=75.0)
    write_cohort_snapshot([case], repo_root=tmp_path, snapshot_label="2026-05-16T100000Z")
    case_b = _make_case("GS-A-candidate", tmp_path, residual_velocity=80.0)
    write_cohort_snapshot([case_b], repo_root=tmp_path, snapshot_label="2026-05-16T200000Z")
    diff = diff_cohort_snapshots(tmp_path, "2026-05-16T100000Z", "2026-05-16T200000Z")
    rendered = json.loads(render_cohort_snapshot_diff_json(diff))
    assert rendered["schema_version"] == "1.1.0"
    assert len(rendered["numerical_deltas"]) == 1
    assert rendered["numerical_deltas"][0]["case_id"] == "GS-A-candidate"
    assert rendered["numerical_deltas"][0]["residual_velocity_m_per_s"]["delta"] == 5.0


def test_metrics_copy_inherits_no_overclaim_audit(tmp_path: Path) -> None:
    """If a ballistic_metrics.json on disk contains a forbidden
    positive claim, the metrics-copy step must reject the snapshot
    write rather than silently propagating the claim into the
    captured snapshot.
    """
    import pytest

    case = _make_case("GS-A-candidate", tmp_path, residual_velocity=75.0)
    # Tamper with the metrics file post-creation to inject a forbidden
    # phrase. (In real life this would be caught much earlier; the
    # test exists to keep the cross-member audit honest.)
    raw = json.loads(case.ballistic_metrics_path.read_text(encoding="utf-8"))
    raw["bad_note"] = "validated against the reference (forbidden phrase)"
    case.ballistic_metrics_path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
    with pytest.raises(ValueError, match="forbidden positive claim"):
        write_cohort_snapshot([case], repo_root=tmp_path)
