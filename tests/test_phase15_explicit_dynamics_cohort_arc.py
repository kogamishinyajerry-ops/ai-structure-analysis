"""FM-04a Phase 15 B — explicit_dynamics 3-snapshot degradation arc.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Mirrors Phase 12 D's modal-cohort multi-snapshot pattern, applied to the
3-case explicit_dynamics cohort (rod-wave-impact-candidate +
rod-wave-impact-stiff-candidate + rod-wave-impact-energy-leak-candidate).
Three snapshots written under tmp_path (NOT the real
``reports/snapshots/``) showing a degradation arc:

  * Snapshot-1 (2026-05-17T100000Z): all 3 cases healthy.
  * Snapshot-2 (2026-05-17T120000Z): canonical + stiff stay healthy;
    leak case drops to watching (canonical leak fixture state;
    trust ~= 54).
  * Snapshot-3 (2026-05-17T140000Z): canonical + stiff stay healthy;
    leak case drops to regressed (generator script omitted, dropping
    reproducibility axis to 0; trust < 50).

The cohort-bucket trigger `regressed_count >= 1` fires on snap-3
on real fixture math (NOT trusted from a hand-rolled snapshot
manifest).

Anti-gaming guards pinned here (per Phase 15 binding rubric §4):
* **T:-4** — per-snapshot bucket counts are EXACT (not >= bounds).
* **A:-3** — bucket transitions are COMPUTED by walking the live
  trust-score-timeline route after the snapshots are written,
  NOT trusted from a hand-rolled snapshot manifest.
* **E:-2** — Phase 14 A cross-route signed-registry refusal SSOT
  exercised: `GS-001` rejected on the timeline route in the
  same tmp_path repo.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from app.services.reporting._schema_versions import (
    COHORT_SNAPSHOT_MANIFEST_SCHEMA_VERSION,
)
from app.services.reporting.cohort_executive_summary import (
    HEALTHY_TRUST_SCORE_MIN,
    WATCHING_TRUST_SCORE_MIN,
)
from app.services.reporting.cohort_snapshot import (
    SnapshotCaseInput,
    write_cohort_snapshot,
)
from app.services.reporting.trust_score_timeline import (
    build_trust_score_timeline,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

# Cohort SSOT for Phase 15 B — the three explicit_dynamics cases
# substantiated by Phase 14 D + Phase 15 A.
EXPLICIT_DYNAMICS_COHORT_CASES: tuple[str, ...] = (
    "rod-wave-impact-candidate",
    "rod-wave-impact-stiff-candidate",
    "rod-wave-impact-energy-leak-candidate",
)

# Snapshot labels SSOT — distinct UTC seconds along the arc.
SNAP_1_LABEL = "2026-05-17T100000Z"  # all healthy
SNAP_2_LABEL = "2026-05-17T120000Z"  # leak drops to watching
SNAP_3_LABEL = "2026-05-17T140000Z"  # leak drops to regressed


# ---------------------------------------------------------------------
# tmp_path seeding helpers (mirror Phase 12 D pattern)
# ---------------------------------------------------------------------


@pytest.fixture(scope="module")
def seeded_repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Seed a tmp_path with the 3 explicit_dynamics cases + drive the
    Phase 15 A generators (so the gitignored project_state/ tree is
    populated for the case-completeness route)."""
    import subprocess
    import sys

    # First ensure project_state/ is populated in the real repo (the
    # generators write to both golden_samples/ and project_state/).
    for gen in (
        "gen_rod_wave_impact_deck.py",
        "gen_rod_wave_impact_stiff_deck.py",
        "gen_rod_wave_impact_energy_leak_deck.py",
    ):
        subprocess.check_call(
            [sys.executable, str(REPO_ROOT / "scripts" / gen)],
            cwd=str(REPO_ROOT),
        )

    tmp = tmp_path_factory.mktemp("phase15b_repo")
    golden = tmp / "golden_samples"
    golden.mkdir(parents=True)
    for case_id in EXPLICIT_DYNAMICS_COHORT_CASES:
        src = REPO_ROOT / "golden_samples" / case_id
        shutil.copytree(src, golden / case_id)
    return tmp


def _stub_path(tmp: Path, name: str) -> Path:
    """Write a tiny stub file under tmp_path and return its path —
    used for starter/engine/generator decks where the case_completeness
    rubric only checks presence."""
    p = tmp / name
    if not p.exists():
        p.write_text("# stub artifact for Phase 15 B snapshot", encoding="utf-8")
    return p


def _healthy_case_input(
    tmp: Path,
    case_id: str,
) -> SnapshotCaseInput:
    """Full-credit case input pointing at the canonical fixture (the
    on-disk Phase 15 A state). Used for snap-1 + snap-2 healthy
    cases."""
    fixture = tmp / "golden_samples" / case_id
    return SnapshotCaseInput(
        case_id=case_id,
        starter_deck_path=fixture / "data" / "model_00_0000.rad",
        engine_deck_path=fixture / "data" / "model_00_0001.rad",
        ballistic_metrics_path=fixture / "data" / "ballistic_metrics.json",
        convergence_study_path=fixture / "data" / "convergence_study.json",
        animation_manifest_path=fixture / "data" / "animation_manifest.json",
        result_mesh_path=None,
        generator_script_path=_stub_path(tmp, f"gen_{case_id.replace('-', '_')}_deck.py"),
        notes_path=fixture / "NOTES.md",
        analysis_type="explicit_dynamics",
    )


def _clean_leak_case_input(
    tmp: Path,
    case_id: str,
) -> SnapshotCaseInput:
    """Synthesize a CLEAN variant of the leak case for snap-1: rewrite
    the leak case's ballistic_metrics so energy_audit.status =
    closed_aggregate (the canonical Phase 15 A state has it set to
    open_residual). This puts the leak case at full healthy credit
    at snap-1 BEFORE the degradation arc starts."""
    fixture = tmp / "golden_samples" / case_id
    metrics_src = fixture / "data" / "ballistic_metrics.json"
    payload = json.loads(metrics_src.read_text(encoding="utf-8"))
    payload["energy_audit"]["status"] = "closed_aggregate"
    payload["energy_audit"]["rationale"] = (
        "Tier 1 candidate snap-1 healthy state; energy partition closed at "
        "machine epsilon BEFORE the synthetic leak injection in later "
        "snapshots. Not signed validation; not benchmark agreement."
    )
    # Write the clean variant to a tmp file so we don't mutate the
    # on-disk Phase 15 A fixture.
    clean_dir = tmp / "phase15b_snap1_clean" / case_id
    clean_dir.mkdir(parents=True, exist_ok=True)
    clean_metrics = clean_dir / "ballistic_metrics.json"
    clean_metrics.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    # Convergence also needs to be patched to stable for snap-1.
    conv_src = fixture / "data" / "convergence_study.json"
    conv_payload = json.loads(conv_src.read_text(encoding="utf-8"))
    conv_payload["combined_verdict"] = "candidate_observed_stable"
    conv_payload["mesh_sweep"]["candidate_stability"] = "candidate_observed_stable"
    conv_payload["dt_sweep"]["candidate_stability"] = "candidate_observed_stable"
    conv_payload["mesh_sweep"]["rationale"] = (
        "Tier 1 candidate snap-1 healthy state; convergence stable BEFORE "
        "synthetic energy leak. Not signed validation."
    )
    conv_payload["dt_sweep"]["rationale"] = (
        "Tier 1 candidate snap-1 healthy state. Not benchmark agreement."
    )
    clean_conv = clean_dir / "convergence_study.json"
    clean_conv.write_text(json.dumps(conv_payload, indent=2), encoding="utf-8")
    return SnapshotCaseInput(
        case_id=case_id,
        starter_deck_path=fixture / "data" / "model_00_0000.rad",
        engine_deck_path=fixture / "data" / "model_00_0001.rad",
        ballistic_metrics_path=clean_metrics,
        convergence_study_path=clean_conv,
        animation_manifest_path=fixture / "data" / "animation_manifest.json",
        result_mesh_path=None,
        generator_script_path=_stub_path(tmp, f"gen_{case_id.replace('-', '_')}_deck.py"),
        notes_path=fixture / "NOTES.md",
        analysis_type="explicit_dynamics",
    )


def _regressed_leak_case_input(
    tmp: Path,
    case_id: str,
) -> SnapshotCaseInput:
    """snap-3 regressed variant of the leak case: canonical
    energy_audit=open_residual + convergence_unstable PLUS three
    optional artifacts omitted (animation_manifest, notes,
    generator_script). Completeness drops from 75 to ~60; trust
    falls below the 50-pt regressed bucket floor.

    Per the Phase 13 C `cylinder-pv-collapsed-candidate` precedent:
    the regressed-bucket trigger needs to drop EITHER multiple axes
    OR multiple optional-evidence artifacts on top of the energy
    failure — a single-axis collapse alone leaves trust in the
    watching bucket."""
    fixture = tmp / "golden_samples" / case_id
    return SnapshotCaseInput(
        case_id=case_id,
        starter_deck_path=fixture / "data" / "model_00_0000.rad",
        engine_deck_path=fixture / "data" / "model_00_0001.rad",
        ballistic_metrics_path=fixture / "data" / "ballistic_metrics.json",
        convergence_study_path=fixture / "data" / "convergence_study.json",
        animation_manifest_path=None,  # OMITTED → completeness -5
        result_mesh_path=None,
        generator_script_path=None,  # OMITTED → completeness -5
        notes_path=None,  # OMITTED → completeness -5
        analysis_type="explicit_dynamics",
    )


@pytest.fixture(scope="module")
def three_snapshot_arc(seeded_repo: Path) -> Path:
    """Write the 3 snapshots under seeded_repo/reports/snapshots/."""
    # Snap-1: all 3 healthy
    snap1_inputs = [
        _healthy_case_input(seeded_repo, "rod-wave-impact-candidate"),
        _healthy_case_input(seeded_repo, "rod-wave-impact-stiff-candidate"),
        _clean_leak_case_input(seeded_repo, "rod-wave-impact-energy-leak-candidate"),
    ]
    write_cohort_snapshot(snap1_inputs, repo_root=seeded_repo, snapshot_label=SNAP_1_LABEL)

    # Snap-2: canonical + stiff healthy; leak watching (Phase 15 A canonical leak state)
    snap2_inputs = [
        _healthy_case_input(seeded_repo, "rod-wave-impact-candidate"),
        _healthy_case_input(seeded_repo, "rod-wave-impact-stiff-candidate"),
        _healthy_case_input(seeded_repo, "rod-wave-impact-energy-leak-candidate"),
    ]
    write_cohort_snapshot(snap2_inputs, repo_root=seeded_repo, snapshot_label=SNAP_2_LABEL)

    # Snap-3: canonical + stiff healthy; leak regressed (no generator_script)
    snap3_inputs = [
        _healthy_case_input(seeded_repo, "rod-wave-impact-candidate"),
        _healthy_case_input(seeded_repo, "rod-wave-impact-stiff-candidate"),
        _regressed_leak_case_input(seeded_repo, "rod-wave-impact-energy-leak-candidate"),
    ]
    write_cohort_snapshot(snap3_inputs, repo_root=seeded_repo, snapshot_label=SNAP_3_LABEL)
    return seeded_repo


# ---------------------------------------------------------------------
# 1. Snapshot manifest existence + Tier 1 disclaimer trio
# ---------------------------------------------------------------------


def test_three_snapshots_present_with_tier1_trio(three_snapshot_arc: Path) -> None:
    """Each of 3 snapshot dirs exists under tmp_path with the SSOT
    manifest schema_version + Tier 1 disclaimer trio."""
    for label in (SNAP_1_LABEL, SNAP_2_LABEL, SNAP_3_LABEL):
        snap_dir = three_snapshot_arc / "reports" / "snapshots" / label
        assert snap_dir.is_dir(), f"missing snapshot dir {label}"
        manifest = json.loads((snap_dir / "SNAPSHOT_MANIFEST.json").read_text(encoding="utf-8"))
        assert manifest["schema_version"] == COHORT_SNAPSHOT_MANIFEST_SCHEMA_VERSION
        assert manifest["claim_tier"] == "Tier 1 engineering candidate"
        assert "not_signed_validation" in manifest["claim_boundary"]
        assert "not_benchmark_agreement" in manifest["claim_boundary"]
        # All 3 cohort cases present in each snapshot.
        assert set(manifest["cases"]) == set(EXPLICIT_DYNAMICS_COHORT_CASES)


def test_snapshot_labels_chronological(three_snapshot_arc: Path) -> None:
    """The 3 snapshot labels MUST sort chronologically as labelled."""
    assert SNAP_1_LABEL < SNAP_2_LABEL < SNAP_3_LABEL


# ---------------------------------------------------------------------
# 2. Per-snapshot bucket transitions (T:-4 exact counts via timeline)
# ---------------------------------------------------------------------


def _timeline_trust_at(repo: Path, case_id: str, snap_label: str) -> int:
    timeline = build_trust_score_timeline(case_id, repo)
    for point in timeline.points:
        if point.snapshot_label == snap_label:
            return point.trust_score
    raise AssertionError(f"timeline has no point for {case_id!r} at {snap_label!r}")


def test_canonical_case_stays_healthy_across_arc(
    three_snapshot_arc: Path,
) -> None:
    """The canonical case is full-credit at every snapshot;
    trust >= 80 (healthy bucket) at all 3 points."""
    for label in (SNAP_1_LABEL, SNAP_2_LABEL, SNAP_3_LABEL):
        trust = _timeline_trust_at(three_snapshot_arc, "rod-wave-impact-candidate", label)
        assert trust >= HEALTHY_TRUST_SCORE_MIN, (
            f"canonical case dropped from healthy at {label}: trust={trust}"
        )


def test_stiff_case_stays_healthy_across_arc(
    three_snapshot_arc: Path,
) -> None:
    """The stiff variant is full-credit at every snapshot."""
    for label in (SNAP_1_LABEL, SNAP_2_LABEL, SNAP_3_LABEL):
        trust = _timeline_trust_at(three_snapshot_arc, "rod-wave-impact-stiff-candidate", label)
        assert trust >= HEALTHY_TRUST_SCORE_MIN, (
            f"stiff case dropped from healthy at {label}: trust={trust}"
        )


def test_leak_case_arc_healthy_watching_regressed(
    three_snapshot_arc: Path,
) -> None:
    """The LOAD-BEARING bucket-transition arc for the leak case:
    * snap-1: healthy (clean variant; energy closed_aggregate)
    * snap-2: watching (canonical leak; energy open_residual)
    * snap-3: regressed (canonical leak + no generator)."""
    case = "rod-wave-impact-energy-leak-candidate"
    snap1 = _timeline_trust_at(three_snapshot_arc, case, SNAP_1_LABEL)
    snap2 = _timeline_trust_at(three_snapshot_arc, case, SNAP_2_LABEL)
    snap3 = _timeline_trust_at(three_snapshot_arc, case, SNAP_3_LABEL)
    assert snap1 >= HEALTHY_TRUST_SCORE_MIN, f"snap-1 leak case expected healthy; got trust={snap1}"
    assert WATCHING_TRUST_SCORE_MIN <= snap2 < HEALTHY_TRUST_SCORE_MIN, (
        f"snap-2 leak case expected watching "
        f"[{WATCHING_TRUST_SCORE_MIN}, {HEALTHY_TRUST_SCORE_MIN}); "
        f"got trust={snap2}"
    )
    assert snap3 < WATCHING_TRUST_SCORE_MIN, (
        f"snap-3 leak case expected regressed (< {WATCHING_TRUST_SCORE_MIN}); got trust={snap3}"
    )


def test_arc_is_monotonically_degrading(three_snapshot_arc: Path) -> None:
    """Trust score for the leak case MUST be monotonically
    decreasing across the 3-snapshot arc (snap1 > snap2 > snap3)."""
    case = "rod-wave-impact-energy-leak-candidate"
    snap1 = _timeline_trust_at(three_snapshot_arc, case, SNAP_1_LABEL)
    snap2 = _timeline_trust_at(three_snapshot_arc, case, SNAP_2_LABEL)
    snap3 = _timeline_trust_at(three_snapshot_arc, case, SNAP_3_LABEL)
    assert snap1 > snap2 > snap3, f"leak case arc not monotonic: {snap1} -> {snap2} -> {snap3}"


# ---------------------------------------------------------------------
# 3. Per-snapshot cohort bucket counts (the regressed_count trigger)
# ---------------------------------------------------------------------


def _per_snapshot_bucket_counts(repo: Path, snap_label: str) -> dict[str, int]:
    """Walk the snapshot dir's completeness scorecards + trust-score
    timeline and bucketize each case."""
    counts = {"healthy": 0, "watching": 0, "regressed": 0}
    for case_id in EXPLICIT_DYNAMICS_COHORT_CASES:
        trust = _timeline_trust_at(repo, case_id, snap_label)
        if trust >= HEALTHY_TRUST_SCORE_MIN:
            counts["healthy"] += 1
        elif trust >= WATCHING_TRUST_SCORE_MIN:
            counts["watching"] += 1
        else:
            counts["regressed"] += 1
    return counts


def test_snap1_all_three_healthy(three_snapshot_arc: Path) -> None:
    counts = _per_snapshot_bucket_counts(three_snapshot_arc, SNAP_1_LABEL)
    assert counts == {"healthy": 3, "watching": 0, "regressed": 0}


def test_snap2_two_healthy_one_watching(three_snapshot_arc: Path) -> None:
    counts = _per_snapshot_bucket_counts(three_snapshot_arc, SNAP_2_LABEL)
    assert counts == {"healthy": 2, "watching": 1, "regressed": 0}


def test_snap3_regressed_count_at_least_one(three_snapshot_arc: Path) -> None:
    """The load-bearing T:-4 pin: regressed_count >= 1 fires on snap-3
    on real timeline math (NOT trusted from a hand-rolled manifest)."""
    counts = _per_snapshot_bucket_counts(three_snapshot_arc, SNAP_3_LABEL)
    assert counts["regressed"] >= 1, f"snap-3 expected regressed_count >= 1; got {counts}"
    # Exact pin: 2 healthy / 0 watching / 1 regressed.
    assert counts == {"healthy": 2, "watching": 0, "regressed": 1}


# ---------------------------------------------------------------------
# 4. Snapshot manifest schema_version SSOT pin
# ---------------------------------------------------------------------


def test_every_snapshot_uses_ssot_schema_version(
    three_snapshot_arc: Path,
) -> None:
    """Every snapshot manifest reads the schema_version from the
    SSOT constant; a future bump rewrites all 3 snapshots through
    the same constant."""
    for label in (SNAP_1_LABEL, SNAP_2_LABEL, SNAP_3_LABEL):
        manifest = json.loads(
            (
                three_snapshot_arc / "reports" / "snapshots" / label / "SNAPSHOT_MANIFEST.json"
            ).read_text(encoding="utf-8")
        )
        assert manifest["schema_version"] == COHORT_SNAPSHOT_MANIFEST_SCHEMA_VERSION


# ---------------------------------------------------------------------
# 5. Timeline shape: point_count = 3 per case
# ---------------------------------------------------------------------


def test_timeline_has_three_points_per_case(three_snapshot_arc: Path) -> None:
    """Every cohort case shows 3 points on the trust-score-timeline
    (one per snapshot)."""
    for case_id in EXPLICIT_DYNAMICS_COHORT_CASES:
        tl = build_trust_score_timeline(case_id, three_snapshot_arc)
        assert tl.point_count == 3
        labels = [p.snapshot_label for p in tl.points]
        # Oldest-first ordering.
        assert labels == [SNAP_1_LABEL, SNAP_2_LABEL, SNAP_3_LABEL]
