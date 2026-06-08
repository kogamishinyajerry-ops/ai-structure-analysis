"""Tests for the Tier 1 cohort snapshot writer + listing (FM-04a Phase 5 C).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest
from app.services.reporting._schema_versions import (
    COHORT_SNAPSHOT_MANIFEST_SCHEMA_VERSION,
)
from app.services.reporting.cohort_snapshot import (
    SNAPSHOT_LABEL_RE,
    SNAPSHOT_MANIFEST_FILENAME,
    SnapshotCaseInput,
    list_cohort_snapshots,
    render_snapshot_listing_json,
    snapshots_root,
    utc_snapshot_label,
    write_cohort_snapshot,
)

# ---------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------


def _write_metrics(case_id: str, root: Path) -> Path:
    payload = {
        "case_id": case_id,
        "projectile_initial_velocity_m_per_s": 300.0,
        "perforation": {
            "marker": "candidate_perforation",
            "residual_velocity_m_per_s": 75.0,
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


def _make_case_input(case_id: str, tmp_path: Path) -> SnapshotCaseInput:
    metrics = _write_metrics(case_id, tmp_path)
    convergence = _write_convergence(case_id, tmp_path)
    starter, engine = _write_starter_engine(case_id, tmp_path)
    return SnapshotCaseInput(
        case_id=case_id,
        starter_deck_path=starter,
        engine_deck_path=engine,
        ballistic_metrics_path=metrics,
        convergence_study_path=convergence,
        animation_manifest_path=None,
        result_mesh_path=None,
        generator_script_path=None,
        notes_path=None,
    )


# ---------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------


def test_label_format_matches_regex() -> None:
    label = utc_snapshot_label()
    assert SNAPSHOT_LABEL_RE.fullmatch(label)


def test_write_snapshot_creates_full_directory(tmp_path: Path) -> None:
    case = _make_case_input("GS-A-candidate", tmp_path)
    result = write_cohort_snapshot([case], repo_root=tmp_path)
    assert result.snapshot_dir.is_dir()
    assert result.snapshot_dir.parent.parent.name == "reports"
    assert SNAPSHOT_LABEL_RE.fullmatch(result.snapshot_label)
    # required files
    assert (result.snapshot_dir / "cohort_overview.json").is_file()
    assert (result.snapshot_dir / "completeness" / "GS-A-candidate.json").is_file()
    assert (result.snapshot_dir / "reproducibility" / "GS-A-candidate.json").is_file()
    assert (result.snapshot_dir / SNAPSHOT_MANIFEST_FILENAME).is_file()


def test_snapshot_manifest_stamps_schema_version_and_provenance(tmp_path: Path) -> None:
    case = _make_case_input("GS-A-candidate", tmp_path)
    result = write_cohort_snapshot([case], repo_root=tmp_path)
    manifest = json.loads(
        (result.snapshot_dir / SNAPSHOT_MANIFEST_FILENAME).read_text(encoding="utf-8")
    )
    assert manifest["schema_version"] == COHORT_SNAPSHOT_MANIFEST_SCHEMA_VERSION
    assert manifest["snapshot_label"] == result.snapshot_label
    assert manifest["claim_tier"] == "Tier 1 engineering candidate"
    assert "not_signed_validation" in manifest["claim_boundary"]
    assert manifest["cases"] == ["GS-A-candidate"]
    assert manifest["cohort_count"] == 1
    assert manifest["reviewer_bundle_written"] is True
    assert "not signed validation" in manifest["claim_impact"]


def test_snapshot_includes_reviewer_bundle_zip(tmp_path: Path) -> None:
    case = _make_case_input("GS-A-candidate", tmp_path)
    result = write_cohort_snapshot([case], repo_root=tmp_path)
    bundles = list(result.snapshot_dir.glob("tier1_reviewer_bundle_*.zip"))
    assert len(bundles) == 1
    with zipfile.ZipFile(bundles[0]) as zf:
        names = zf.namelist()
    assert any(n.endswith("acceptance_packet.json") for n in names)


def test_snapshot_skips_reviewer_bundle_when_no_metrics(tmp_path: Path) -> None:
    # build a case input with NO ballistic_metrics_path
    starter, engine = _write_starter_engine("GS-B-candidate", tmp_path)
    case = SnapshotCaseInput(
        case_id="GS-B-candidate",
        starter_deck_path=starter,
        engine_deck_path=engine,
        ballistic_metrics_path=None,
    )
    result = write_cohort_snapshot([case], repo_root=tmp_path)
    bundles = list(result.snapshot_dir.glob("tier1_reviewer_bundle_*.zip"))
    assert bundles == []
    manifest = json.loads(
        (result.snapshot_dir / SNAPSHOT_MANIFEST_FILENAME).read_text(encoding="utf-8")
    )
    assert manifest["reviewer_bundle_written"] is False


def test_write_snapshot_refuses_under_golden_samples(tmp_path: Path) -> None:
    # Place the repo root under a directory named "golden_samples" so the
    # writer's snapshots_root resolves to .../golden_samples/.../reports/snapshots
    bad_root = tmp_path / "outer" / "golden_samples"
    bad_root.mkdir(parents=True)
    case = _make_case_input("GS-A-candidate", bad_root)
    with pytest.raises(ValueError, match="golden_samples"):
        write_cohort_snapshot([case], repo_root=bad_root)


def test_write_snapshot_rejects_invalid_case_id(tmp_path: Path) -> None:
    case = _make_case_input("GS-A-candidate", tmp_path)
    bad = SnapshotCaseInput(
        case_id="../escape",
        starter_deck_path=case.starter_deck_path,
        engine_deck_path=case.engine_deck_path,
        ballistic_metrics_path=case.ballistic_metrics_path,
    )
    with pytest.raises(ValueError, match="invalid case_id"):
        write_cohort_snapshot([bad], repo_root=tmp_path)


def test_write_snapshot_rejects_invalid_label(tmp_path: Path) -> None:
    case = _make_case_input("GS-A-candidate", tmp_path)
    with pytest.raises(ValueError, match="invalid snapshot label"):
        write_cohort_snapshot([case], repo_root=tmp_path, snapshot_label="not-a-label")


def test_write_snapshot_requires_at_least_one_case(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="at least one case"):
        write_cohort_snapshot([], repo_root=tmp_path)


def test_listing_returns_empty_when_no_snapshots(tmp_path: Path) -> None:
    assert list_cohort_snapshots(tmp_path) == []


def test_listing_returns_one_entry_per_written_snapshot(tmp_path: Path) -> None:
    case_a = _make_case_input("GS-A-candidate", tmp_path)
    case_b = _make_case_input("GS-B-candidate", tmp_path)
    r1 = write_cohort_snapshot([case_a], repo_root=tmp_path, snapshot_label="2026-05-16T100000Z")
    r2 = write_cohort_snapshot(
        [case_a, case_b],
        repo_root=tmp_path,
        snapshot_label="2026-05-16T200000Z",
    )
    listing = list_cohort_snapshots(tmp_path)
    assert len(listing) == 2
    # newest-first ordering
    assert listing[0]["snapshot_label"] == "2026-05-16T200000Z"
    assert listing[1]["snapshot_label"] == "2026-05-16T100000Z"
    assert listing[0]["cohort_count"] == 2
    assert listing[1]["cohort_count"] == 1
    assert r1.snapshot_label == "2026-05-16T100000Z"
    assert r2.snapshot_label == "2026-05-16T200000Z"


def test_listing_skips_directories_without_manifest(tmp_path: Path) -> None:
    root = snapshots_root(tmp_path)
    root.mkdir(parents=True)
    (root / "2026-05-16T100000Z").mkdir()  # no SNAPSHOT_MANIFEST
    (root / "not-a-label").mkdir()
    assert list_cohort_snapshots(tmp_path) == []


def test_listing_json_envelope_stamps_schema_version(tmp_path: Path) -> None:
    case = _make_case_input("GS-A-candidate", tmp_path)
    write_cohort_snapshot([case], repo_root=tmp_path)
    rendered = json.loads(render_snapshot_listing_json(tmp_path))
    assert rendered["schema_version"] == COHORT_SNAPSHOT_MANIFEST_SCHEMA_VERSION
    assert rendered["snapshot_count"] == 1
    assert rendered["claim_tier"] == "Tier 1 engineering candidate"
    assert "not benchmark agreement" in rendered["claim_impact"]


def test_listing_skips_unparseable_manifests(tmp_path: Path) -> None:
    case = _make_case_input("GS-A-candidate", tmp_path)
    result = write_cohort_snapshot([case], repo_root=tmp_path)
    # corrupt the manifest
    (result.snapshot_dir / SNAPSHOT_MANIFEST_FILENAME).write_text("not json", encoding="utf-8")
    listing = list_cohort_snapshots(tmp_path)
    assert listing == []


def test_snapshot_preserves_claim_tier_disclaimer_in_every_member(tmp_path: Path) -> None:
    case = _make_case_input("GS-A-candidate", tmp_path)
    result = write_cohort_snapshot([case], repo_root=tmp_path)
    for path in result.snapshot_dir.rglob("*.json"):
        text = path.read_text(encoding="utf-8")
        # Tier 1 disclaimer trio must remain in every emitted JSON
        # member. We do not check it inside the zip here because the
        # bundle's claim tier is enforced by reviewer_bundle's tests.
        assert "not signed validation" in text or "not_signed_validation" in text
        assert "not benchmark agreement" in text or "not_benchmark_agreement" in text


def test_snapshot_zip_members_carry_tier1_banner(tmp_path: Path) -> None:
    case = _make_case_input("GS-A-candidate", tmp_path)
    result = write_cohort_snapshot([case], repo_root=tmp_path)
    bundle_path = next(result.snapshot_dir.glob("tier1_reviewer_bundle_*.zip"))
    with zipfile.ZipFile(bundle_path) as zf:
        manifest_text = zf.read("BUNDLE_MANIFEST.json").decode("utf-8")
    assert "not signed validation" in manifest_text
    assert "Tier 1 engineering candidate" in manifest_text


def test_writing_two_snapshots_does_not_overwrite_earlier(tmp_path: Path) -> None:
    case = _make_case_input("GS-A-candidate", tmp_path)
    r1 = write_cohort_snapshot([case], repo_root=tmp_path, snapshot_label="2026-05-16T100000Z")
    r2 = write_cohort_snapshot([case], repo_root=tmp_path, snapshot_label="2026-05-16T200000Z")
    assert r1.snapshot_dir.is_dir()
    assert r2.snapshot_dir.is_dir()
    assert r1.snapshot_dir != r2.snapshot_dir
    assert (r1.snapshot_dir / SNAPSHOT_MANIFEST_FILENAME).is_file()
    assert (r2.snapshot_dir / SNAPSHOT_MANIFEST_FILENAME).is_file()


def test_snapshot_zip_round_trips_through_zipfile(tmp_path: Path) -> None:
    case = _make_case_input("GS-A-candidate", tmp_path)
    result = write_cohort_snapshot([case], repo_root=tmp_path)
    bundle = next(result.snapshot_dir.glob("tier1_reviewer_bundle_*.zip"))
    raw = bundle.read_bytes()
    assert len(raw) > 0
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        # spot-check at least the manifest is parseable
        json.loads(zf.read("BUNDLE_MANIFEST.json").decode("utf-8"))
