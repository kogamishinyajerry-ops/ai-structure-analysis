"""FM-04a Phase 17 B — cumulative drift_attribution_at_signoff_time on signoff records.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Substantiates the additive ``cumulative_drift_attribution_at_signoff_time``
field on the ``SignoffRecord`` dataclass (MINOR bump
``SIGNOFF_RECORD_SCHEMA_VERSION`` 1.1.0 → 1.2.0). The new field captures
the per-case CUMULATIVE drift (snap-1 → snap-N) at signoff write time,
parallel to the Phase 16 C ``drift_attribution_at_signoff_time`` field
which captures the LATEST snapshot pair.

Anti-gaming guards pinned here (per Phase 17 binding rubric §3.B):
* **M:-1** — schema MINOR bump 1.1.0 → 1.2.0 with bump-history docstring.
* **M:-2** — server-side helper
  ``_compute_cumulative_drift_attribution_at_signoff_time`` IMPORTS the
  Phase 16 A ``timeline.cumulative_drift_attribution`` SSOT (no inline
  percentage / cumulative math at the signoff call site).
* **T:-3** — boundary-pinned: 3-snapshot stuck arc (leak energy
  15→15→0) lands signoff cumulative ``dominant_axis == "energy_audit"``
  + ``dominant_delta_pct == -100.0`` exactly + ``from_snapshot ==
  SNAP_1_LABEL`` + ``to_snapshot == SNAP_3_LABEL``.
* **T:-4** — recovery arc (leak 15→0→15): cumulative captured at
  signoff is None / dominant_axis None (sub-floor across the arc);
  latest-pair captured at signoff still surfaces energy_audit.
* **A:-3 LOAD-BEARING SERVER-COMPUTED PIN EXTENDED**: ``write_signoff_record``
  signature accepts NEITHER ``drift_attribution_at_signoff_time`` NOR
  ``cumulative_drift_attribution_at_signoff_time`` as a kwarg
  (``inspect.signature`` audit on BOTH fields). Forged kwargs raise
  TypeError on both.
* **D:-1** — round-trip JSON preservation: write + re-read parses BOTH
  drift fields correctly.
* **D:-2** — back-compat: pre-1.2.0 on-disk records (carrying only the
  Phase 16 C latest-pair field, or even pre-1.1.0 records carrying
  neither field) read with ``cumulative_drift_attribution_at_signoff_time
  = None``.
* **C:-1** — Tier 1 disclaimer trio preserved on signoff envelope at 1.2.0.
* **V:-3** — all snapshot writes under tmp_path.
"""

from __future__ import annotations

import inspect
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from app.services.reporting._schema_versions import (
    SIGNOFF_RECORD_SCHEMA_VERSION,
)
from app.services.reporting.cohort_snapshot import (
    SnapshotCaseInput,
    write_cohort_snapshot,
)
from app.services.reporting.signoff_record import (
    _compute_cumulative_drift_attribution_at_signoff_time,
    _compute_drift_attribution_at_signoff_time,
    _parse_drift_attribution,
    _record_to_dict,
    read_signoff_history,
    write_signoff_record,
)
from app.services.reporting.trust_score_drift_attribution import (
    DriftAttribution,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

LEAK_CASE_ID = "rod-wave-impact-energy-leak-candidate"

SNAP_1_LABEL = "2026-05-17T100000Z"
SNAP_2_LABEL = "2026-05-17T120000Z"
SNAP_3_LABEL = "2026-05-17T140000Z"


# ---------------------------------------------------------------------
# M:-1 schema version pin
# ---------------------------------------------------------------------


def test_signoff_record_schema_at_1_2_0() -> None:
    """Phase 17 B MINOR bump SIGNOFF_RECORD_SCHEMA_VERSION 1.1.0 → 1.2.0
    with bump-history docstring."""
    assert SIGNOFF_RECORD_SCHEMA_VERSION == "1.2.0"


# ---------------------------------------------------------------------
# A:-3 LOAD-BEARING: write_signoff_record accepts NEITHER drift kwarg
# ---------------------------------------------------------------------


def test_write_signoff_record_accepts_no_latest_pair_drift_kwarg() -> None:
    """A:-3 server-computed pin (Phase 16 C): the
    ``drift_attribution_at_signoff_time`` field is NOT in the
    signature of ``write_signoff_record``. Preserved at 1.2.0."""
    sig = inspect.signature(write_signoff_record)
    assert "drift_attribution_at_signoff_time" not in sig.parameters, (
        f"A:-3 violation — write_signoff_record carries a "
        f"drift_attribution_at_signoff_time parameter; the field MUST be "
        f"server-computed: {list(sig.parameters)}"
    )


def test_write_signoff_record_accepts_no_cumulative_drift_kwarg() -> None:
    """A:-3 server-computed pin EXTENDED (Phase 17 B): the new
    ``cumulative_drift_attribution_at_signoff_time`` field is also
    NOT in the signature of ``write_signoff_record``. Both drift
    fields are server-computed only — no client can forge either."""
    sig = inspect.signature(write_signoff_record)
    assert "cumulative_drift_attribution_at_signoff_time" not in sig.parameters, (
        f"A:-3 violation — write_signoff_record carries a "
        f"cumulative_drift_attribution_at_signoff_time parameter; the "
        f"field MUST be server-computed: {list(sig.parameters)}"
    )


def test_forged_latest_pair_kwarg_raises_type_error(tmp_path: Path) -> None:
    """Defense-in-depth: even if a client somehow reaches the
    function, passing ``drift_attribution_at_signoff_time`` as a
    kwarg raises TypeError (Python signature enforcement).

    Phase 16 C A:-3 pin extended: this test exercises the kwarg
    rejection in addition to the inspect.signature audit above."""
    with pytest.raises(TypeError, match="drift_attribution_at_signoff_time"):
        write_signoff_record(
            "rod-wave-impact-candidate",
            "test-reviewer",
            "watching",
            "Tier 1 engineering candidate. Not signed validation; not benchmark agreement.",
            repo_root=tmp_path,
            drift_attribution_at_signoff_time={"forged": True},  # type: ignore[call-arg]
        )


def test_forged_cumulative_kwarg_raises_type_error(tmp_path: Path) -> None:
    """A:-3 EXTENDED defense-in-depth (Phase 17 B): passing
    ``cumulative_drift_attribution_at_signoff_time`` as a kwarg
    raises TypeError. Pins the new field's server-computed posture."""
    with pytest.raises(TypeError, match="cumulative_drift_attribution_at_signoff_time"):
        write_signoff_record(
            "rod-wave-impact-candidate",
            "test-reviewer",
            "watching",
            "Tier 1 engineering candidate. Not signed validation; not benchmark agreement.",
            repo_root=tmp_path,
            cumulative_drift_attribution_at_signoff_time={"forged": True},  # type: ignore[call-arg]
        )


# ---------------------------------------------------------------------
# M:-2 helper SSOT — cumulative compute IMPORTS timeline cumulative SSOT
# ---------------------------------------------------------------------


def test_cumulative_helper_imports_timeline_cumulative_ssot() -> None:
    """M:-2 anti-gaming guard: the cumulative drift compute at signoff
    time IMPORTS the Phase 16 A ``timeline.cumulative_drift_attribution``
    SSOT field rather than inline-computing snap-1 → snap-N percentage
    math. Verified by source-file grep."""
    src = (
        REPO_ROOT / "backend" / "app" / "services" / "reporting" / "signoff_record.py"
    ).read_text(encoding="utf-8")
    # The new helper must reference timeline.cumulative_drift_attribution.
    assert "timeline.cumulative_drift_attribution" in src, src[:500]
    # And must NOT inline-compute per-axis percentages at the signoff
    # call site (the helper delegates to the timeline SSOT).
    assert "per_axis_delta_pct[" not in src, src[:500]


# ---------------------------------------------------------------------
# Fixture: 3-snapshot stuck arc for the leak case
# ---------------------------------------------------------------------


def _stub(tmp: Path, name: str) -> Path:
    p = tmp / name
    if not p.exists():
        p.write_text("# stub", encoding="utf-8")
    return p


def _clean_leak_input(tmp: Path, suffix: str) -> SnapshotCaseInput:
    fixture = tmp / "golden_samples" / LEAK_CASE_ID
    metrics_src = fixture / "data" / "ballistic_metrics.json"
    payload = json.loads(metrics_src.read_text(encoding="utf-8"))
    payload["energy_audit"]["status"] = "closed_aggregate"
    payload["energy_audit"]["rationale"] = (
        "Tier 1 candidate clean. Not signed validation; not benchmark agreement."
    )
    clean_dir = tmp / f"phase17b_clean_{suffix}" / LEAK_CASE_ID
    clean_dir.mkdir(parents=True, exist_ok=True)
    clean_metrics = clean_dir / "ballistic_metrics.json"
    clean_metrics.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    conv_src = fixture / "data" / "convergence_study.json"
    conv_payload = json.loads(conv_src.read_text(encoding="utf-8"))
    conv_payload["combined_verdict"] = "candidate_observed_stable"
    conv_payload["mesh_sweep"]["candidate_stability"] = "candidate_observed_stable"
    conv_payload["dt_sweep"]["candidate_stability"] = "candidate_observed_stable"
    conv_payload["mesh_sweep"]["rationale"] = "Tier 1 candidate clean. Not signed validation."
    conv_payload["dt_sweep"]["rationale"] = "Tier 1 candidate clean. Not benchmark agreement."
    clean_conv = clean_dir / "convergence_study.json"
    clean_conv.write_text(json.dumps(conv_payload, indent=2), encoding="utf-8")
    return SnapshotCaseInput(
        case_id=LEAK_CASE_ID,
        starter_deck_path=fixture / "data" / "model_00_0000.rad",
        engine_deck_path=fixture / "data" / "model_00_0001.rad",
        ballistic_metrics_path=clean_metrics,
        convergence_study_path=clean_conv,
        animation_manifest_path=fixture / "data" / "animation_manifest.json",
        result_mesh_path=None,
        generator_script_path=_stub(tmp, f"gen_leak_clean_{suffix}.py"),
        notes_path=fixture / "NOTES.md",
        analysis_type="explicit_dynamics",
    )


def _regressed_leak_input(tmp: Path) -> SnapshotCaseInput:
    fixture = tmp / "golden_samples" / LEAK_CASE_ID
    return SnapshotCaseInput(
        case_id=LEAK_CASE_ID,
        starter_deck_path=fixture / "data" / "model_00_0000.rad",
        engine_deck_path=fixture / "data" / "model_00_0001.rad",
        ballistic_metrics_path=fixture / "data" / "ballistic_metrics.json",
        convergence_study_path=fixture / "data" / "convergence_study.json",
        animation_manifest_path=fixture / "data" / "animation_manifest.json",
        result_mesh_path=None,
        generator_script_path=_stub(tmp, "gen_leak_regressed.py"),
        notes_path=fixture / "NOTES.md",
        analysis_type="explicit_dynamics",
    )


def _seed_leak_only(tmp_path: Path) -> None:
    """Drive the Phase 15 A generators in the real repo, then copy
    only the leak case fixture to tmp_path/golden_samples/."""
    subprocess.check_call(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "gen_rod_wave_impact_energy_leak_deck.py"),
        ],
        cwd=str(REPO_ROOT),
    )
    golden = tmp_path / "golden_samples"
    golden.mkdir(parents=True, exist_ok=True)
    shutil.copytree(REPO_ROOT / "golden_samples" / LEAK_CASE_ID, golden / LEAK_CASE_ID)


@pytest.fixture()
def stuck_arc_tmp(tmp_path: Path) -> Path:
    """3-snapshot stuck arc on the leak case alone: clean → clean →
    regressed (energy 15 → 15 → 0). Latest-pair = snap-2 → snap-3 =
    15 → 0; cumulative = snap-1 → snap-3 = 15 → 0; both surface
    energy_audit dominant with -100.0% delta."""
    _seed_leak_only(tmp_path)
    write_cohort_snapshot(
        [_clean_leak_input(tmp_path, "snap1")],
        repo_root=tmp_path,
        snapshot_label=SNAP_1_LABEL,
    )
    write_cohort_snapshot(
        [_clean_leak_input(tmp_path, "snap2")],
        repo_root=tmp_path,
        snapshot_label=SNAP_2_LABEL,
    )
    write_cohort_snapshot(
        [_regressed_leak_input(tmp_path)],
        repo_root=tmp_path,
        snapshot_label=SNAP_3_LABEL,
    )
    return tmp_path


@pytest.fixture()
def recovery_arc_tmp(tmp_path: Path) -> Path:
    """3-snapshot recovery arc on the leak case alone: clean →
    regressed → clean (energy 15 → 0 → 15). Latest-pair = snap-2 →
    snap-3 = 0 → 15 surfaces energy_audit recovery (+100% delta);
    cumulative = snap-1 → snap-3 = 15 → 15 = 0% recovers below the
    floor → cumulative dominant_axis is None."""
    _seed_leak_only(tmp_path)
    write_cohort_snapshot(
        [_clean_leak_input(tmp_path, "snap1")],
        repo_root=tmp_path,
        snapshot_label=SNAP_1_LABEL,
    )
    write_cohort_snapshot(
        [_regressed_leak_input(tmp_path)],
        repo_root=tmp_path,
        snapshot_label=SNAP_2_LABEL,
    )
    write_cohort_snapshot(
        [_clean_leak_input(tmp_path, "snap3")],
        repo_root=tmp_path,
        snapshot_label=SNAP_3_LABEL,
    )
    return tmp_path


# ---------------------------------------------------------------------
# T:-3 stuck arc — cumulative + latest both name energy_audit -100.0
# ---------------------------------------------------------------------


def test_stuck_arc_signoff_carries_cumulative_drift_named_energy_axis(
    stuck_arc_tmp: Path,
) -> None:
    """The load-bearing T:-3 boundary pin: on a 3-snapshot stuck arc,
    write_signoff_record captures
    ``cumulative_drift_attribution_at_signoff_time.dominant_axis ==
    "energy_audit"`` + ``dominant_delta_pct == -100.0`` exactly +
    ``from_snapshot == SNAP_1_LABEL`` + ``to_snapshot == SNAP_3_LABEL``.
    The latest-pair captures (snap-2 → snap-3 = 15 → 0 = -100%) also
    surfaces energy_audit; both agree on the stuck arc."""
    record = write_signoff_record(
        LEAK_CASE_ID,
        "phase17b-test-reviewer",
        "needs_more_evidence",
        "Tier 1 engineering candidate. Not signed validation; not benchmark agreement.",
        repo_root=stuck_arc_tmp,
    )
    assert record.schema_version == "1.2.0"
    # Latest-pair drift pin (Phase 16 C surface, preserved at 1.2.0).
    latest = record.drift_attribution_at_signoff_time
    assert latest is not None
    assert isinstance(latest, DriftAttribution)
    assert latest.dominant_axis == "energy_audit"
    assert latest.dominant_delta_pct == -100.0
    assert latest.from_snapshot == SNAP_2_LABEL
    assert latest.to_snapshot == SNAP_3_LABEL
    # Cumulative drift pin (Phase 17 B new field).
    cumulative = record.cumulative_drift_attribution_at_signoff_time
    assert cumulative is not None
    assert isinstance(cumulative, DriftAttribution)
    assert cumulative.dominant_axis == "energy_audit"
    assert cumulative.dominant_delta_pct == -100.0
    assert cumulative.from_snapshot == SNAP_1_LABEL
    assert cumulative.to_snapshot == SNAP_3_LABEL


# ---------------------------------------------------------------------
# T:-4 recovery arc — cumulative None, latest-pair active
# ---------------------------------------------------------------------


def test_recovery_arc_cumulative_signoff_is_subfloor(
    recovery_arc_tmp: Path,
) -> None:
    """Recovery arc (energy 15 → 0 → 15): cumulative captured at
    signoff is a DriftAttribution wrapper with
    ``dominant_axis is None`` (sub-floor across the arc).
    Latest-pair captured at signoff names energy_audit recovery
    (+100% on the snap-2 → snap-3 transition)."""
    record = write_signoff_record(
        LEAK_CASE_ID,
        "phase17b-recovery-reviewer",
        "watching",
        "Tier 1 engineering candidate. Not signed validation; not benchmark agreement.",
        repo_root=recovery_arc_tmp,
    )
    cumulative = record.cumulative_drift_attribution_at_signoff_time
    assert cumulative is not None
    assert isinstance(cumulative, DriftAttribution)
    assert cumulative.dominant_axis is None
    # cumulative_delta_pct sentinel is NaN; NaN is not equal to itself
    import math

    assert math.isnan(cumulative.dominant_delta_pct)
    assert cumulative.from_snapshot == SNAP_1_LABEL
    assert cumulative.to_snapshot == SNAP_3_LABEL
    # Latest-pair still active on snap-2 → snap-3.
    latest = record.drift_attribution_at_signoff_time
    assert latest is not None
    assert isinstance(latest, DriftAttribution)
    assert latest.dominant_axis == "energy_audit"
    # +100% recovery direction (sign matters); abs == 100.
    assert latest.dominant_delta_pct == 100.0


# ---------------------------------------------------------------------
# Degenerate-case: 0/1 snapshots → both drift fields None
# ---------------------------------------------------------------------


def test_no_snapshots_signoff_carries_none_for_both_drift_fields(
    tmp_path: Path,
) -> None:
    """When the case has no snapshots at write time, both drift
    fields are None (graceful degrade; no exception)."""
    record = write_signoff_record(
        "rod-wave-impact-candidate",
        "test-reviewer",
        "watching",
        "Tier 1 engineering candidate. Not signed validation; not benchmark agreement.",
        repo_root=tmp_path,
    )
    assert record.schema_version == "1.2.0"
    assert record.drift_attribution_at_signoff_time is None
    assert record.cumulative_drift_attribution_at_signoff_time is None


# ---------------------------------------------------------------------
# D:-1 round-trip JSON preservation
# ---------------------------------------------------------------------


def test_round_trip_json_preserves_both_drift_fields(
    stuck_arc_tmp: Path,
) -> None:
    """Write a signoff with both drift fields populated → read it
    back via read_signoff_history → both drift fields parse
    identically (same DriftAttribution dataclass shape, same
    dominant_axis, same dominant_delta_pct, same endpoint labels)."""
    written = write_signoff_record(
        LEAK_CASE_ID,
        "phase17b-round-trip-reviewer",
        "needs_more_evidence",
        "Tier 1 engineering candidate. Not signed validation; not benchmark agreement.",
        repo_root=stuck_arc_tmp,
    )
    history = read_signoff_history(LEAK_CASE_ID, repo_root=stuck_arc_tmp)
    assert len(history) == 1
    read_back = history[0]
    assert read_back.schema_version == "1.2.0"
    # Latest-pair drift round-trips intact.
    assert isinstance(read_back.drift_attribution_at_signoff_time, DriftAttribution)
    assert (
        read_back.drift_attribution_at_signoff_time.dominant_axis
        == written.drift_attribution_at_signoff_time.dominant_axis  # type: ignore[union-attr]
    )
    # Cumulative drift round-trips intact.
    assert isinstance(read_back.cumulative_drift_attribution_at_signoff_time, DriftAttribution)
    assert (
        read_back.cumulative_drift_attribution_at_signoff_time.dominant_axis
        == written.cumulative_drift_attribution_at_signoff_time.dominant_axis  # type: ignore[union-attr]
    )
    assert read_back.cumulative_drift_attribution_at_signoff_time.from_snapshot == SNAP_1_LABEL
    assert read_back.cumulative_drift_attribution_at_signoff_time.to_snapshot == SNAP_3_LABEL


# ---------------------------------------------------------------------
# D:-2 back-compat: pre-1.2.0 on-disk record reads cumulative=None
# ---------------------------------------------------------------------


def test_back_compat_pre_1_2_0_record_reads_cumulative_as_none(
    tmp_path: Path,
) -> None:
    """A pre-1.2.0 on-disk record (e.g. a 1.1.0 record carrying
    only the Phase 16 C latest-pair drift field, OR a 1.0.0 record
    carrying neither) reads with
    ``cumulative_drift_attribution_at_signoff_time = None`` via the
    back-compat reader. The Phase 16 C
    ``drift_attribution_at_signoff_time`` is still parsed when
    present."""
    case_id = "rod-wave-impact-candidate"
    case_dir = tmp_path / "reports" / "signoffs" / case_id
    case_dir.mkdir(parents=True)
    # Write a pre-1.2.0 record: schema_version 1.1.0 carries
    # drift_attribution_at_signoff_time but NO cumulative field.
    pre_1_2_0_payload = {
        "schema_version": "1.1.0",
        "case_id": case_id,
        "reviewer": "legacy-reviewer",
        "verdict": "watching",
        "signoff_utc": "2026-05-17T120000Z",
        "notes": "Tier 1 engineering candidate. Not signed validation.",
        "claim_tier": "Tier 1 engineering candidate",
        "claim_boundary": "not_signed_validation_and_not_benchmark_agreement",
        "claim_impact": "not signed validation; not benchmark agreement",
        "drift_attribution_at_signoff_time": {
            "from_snapshot": "2026-05-17T100000Z",
            "to_snapshot": "2026-05-17T120000Z",
            "per_axis_delta_pct": {
                "completeness": 0.0,
                "convergence": 0.0,
                "energy_audit": -100.0,
                "reproducibility": 0.0,
            },
            "dominant_axis": "energy_audit",
            "dominant_delta_pct": -100.0,
        },
        # No "cumulative_drift_attribution_at_signoff_time" key.
    }
    (case_dir / "2026-05-17T120000Z.json").write_text(
        json.dumps(pre_1_2_0_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    history = read_signoff_history(case_id, repo_root=tmp_path)
    assert len(history) == 1
    record = history[0]
    # Phase 16 C field reads as parsed DriftAttribution.
    assert isinstance(record.drift_attribution_at_signoff_time, DriftAttribution)
    assert record.drift_attribution_at_signoff_time.dominant_axis == "energy_audit"
    # Phase 17 B field reads as None (back-compat).
    assert record.cumulative_drift_attribution_at_signoff_time is None


def test_back_compat_pre_1_1_0_record_reads_both_drift_fields_as_none(
    tmp_path: Path,
) -> None:
    """A pre-1.1.0 on-disk record carries NEITHER drift field; both
    read as None via back-compat (Phase 16 C + 17 B chained
    back-compat)."""
    case_id = "rod-wave-impact-candidate"
    case_dir = tmp_path / "reports" / "signoffs" / case_id
    case_dir.mkdir(parents=True)
    pre_1_1_0_payload = {
        "schema_version": "1.0.0",
        "case_id": case_id,
        "reviewer": "ancient-reviewer",
        "verdict": "watching",
        "signoff_utc": "2026-05-17T120000Z",
        "notes": "Tier 1 engineering candidate. Not signed validation.",
        "claim_tier": "Tier 1 engineering candidate",
        "claim_boundary": "not_signed_validation_and_not_benchmark_agreement",
        "claim_impact": "not signed validation; not benchmark agreement",
    }
    (case_dir / "2026-05-17T120000Z.json").write_text(
        json.dumps(pre_1_1_0_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    history = read_signoff_history(case_id, repo_root=tmp_path)
    assert len(history) == 1
    record = history[0]
    assert record.drift_attribution_at_signoff_time is None
    assert record.cumulative_drift_attribution_at_signoff_time is None


# ---------------------------------------------------------------------
# D:-3 corrupted JSON graceful-degrade preserved on cumulative field
# ---------------------------------------------------------------------


def test_corrupted_cumulative_drift_blob_reads_as_none(tmp_path: Path) -> None:
    """If a 1.2.0 record carries a malformed
    ``cumulative_drift_attribution_at_signoff_time`` field (e.g. a
    string, a list, a malformed dict), the back-compat reader
    returns None for that field (graceful degrade)."""
    case_id = "rod-wave-impact-candidate"
    case_dir = tmp_path / "reports" / "signoffs" / case_id
    case_dir.mkdir(parents=True)
    # Test cases: (label, malformed_blob)
    test_cases = [
        ("string", "not_a_dict"),
        ("list", [1, 2, 3]),
    ]
    for label, malformed in test_cases:
        payload = {
            "schema_version": "1.2.0",
            "case_id": case_id,
            "reviewer": "test-reviewer",
            "verdict": "watching",
            "signoff_utc": f"2026-05-17T1200{test_cases.index((label, malformed))}0Z",
            "notes": "Tier 1 candidate. Not signed validation.",
            "claim_tier": "Tier 1 engineering candidate",
            "claim_boundary": "not_signed_validation_and_not_benchmark_agreement",
            "claim_impact": "not signed validation",
            "drift_attribution_at_signoff_time": None,
            "cumulative_drift_attribution_at_signoff_time": malformed,
        }
        fname = f"2026-05-17T1200{test_cases.index((label, malformed))}0Z.json"
        (case_dir / fname).write_text(
            json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
        )
    history = read_signoff_history(case_id, repo_root=tmp_path)
    assert len(history) == 2
    for record in history:
        # Malformed cumulative blob → None.
        assert record.cumulative_drift_attribution_at_signoff_time is None


# ---------------------------------------------------------------------
# C:-1 Tier 1 disclaimer trio at 1.2.0
# ---------------------------------------------------------------------


def test_record_to_dict_preserves_tier1_trio_at_1_2_0(
    stuck_arc_tmp: Path,
) -> None:
    """C:-1 Tier 1 disclaimer trio preserved at signoff schema 1.2.0.
    The new cumulative drift field landing does NOT cause the trio to
    drop on the serialized envelope."""
    record = write_signoff_record(
        LEAK_CASE_ID,
        "phase17b-trio-reviewer",
        "needs_more_evidence",
        "Tier 1 engineering candidate. Not signed validation; not benchmark agreement.",
        repo_root=stuck_arc_tmp,
    )
    rendered = _record_to_dict(record)
    assert rendered["schema_version"] == "1.2.0"
    assert rendered["claim_tier"] == "Tier 1 engineering candidate"
    assert "not_signed_validation" in rendered["claim_boundary"]  # type: ignore[operator]
    assert "not_benchmark_agreement" in rendered["claim_boundary"]  # type: ignore[operator]
    # Both drift fields present in the envelope (latest non-null,
    # cumulative non-null on stuck arc).
    assert "drift_attribution_at_signoff_time" in rendered
    assert "cumulative_drift_attribution_at_signoff_time" in rendered
    assert rendered["cumulative_drift_attribution_at_signoff_time"] is not None


# ---------------------------------------------------------------------
# Cross-helper coherence — both helpers callable directly
# ---------------------------------------------------------------------


def test_both_helpers_callable_directly(stuck_arc_tmp: Path) -> None:
    """The two server-side helpers
    (_compute_drift_attribution_at_signoff_time +
    _compute_cumulative_drift_attribution_at_signoff_time) are
    callable directly and return DriftAttribution / None for the
    same case. Pinning the call surface guards against future drift
    in the helper signatures."""
    latest = _compute_drift_attribution_at_signoff_time(LEAK_CASE_ID, repo_root=stuck_arc_tmp)
    cumulative = _compute_cumulative_drift_attribution_at_signoff_time(
        LEAK_CASE_ID, repo_root=stuck_arc_tmp
    )
    assert isinstance(latest, DriftAttribution)
    assert isinstance(cumulative, DriftAttribution)
    assert latest.dominant_axis == cumulative.dominant_axis == "energy_audit"


# ---------------------------------------------------------------------
# Parse helper — used for BOTH drift fields
# ---------------------------------------------------------------------


def test_parse_drift_attribution_handles_both_field_shapes() -> None:
    """The single ``_parse_drift_attribution`` helper handles BOTH
    drift fields' JSON blob → DriftAttribution reconstruction. It
    is the SSOT for back-compat reading; a future drift field can
    reuse it by adding another `_parse_drift_attribution(payload.get(key))`
    call site."""
    blob = {
        "from_snapshot": SNAP_1_LABEL,
        "to_snapshot": SNAP_3_LABEL,
        "per_axis_delta_pct": {
            "completeness": 0.0,
            "convergence": 0.0,
            "energy_audit": -100.0,
            "reproducibility": 0.0,
        },
        "dominant_axis": "energy_audit",
        "dominant_delta_pct": -100.0,
    }
    parsed = _parse_drift_attribution(blob)
    assert isinstance(parsed, DriftAttribution)
    assert parsed.dominant_axis == "energy_audit"
    assert parsed.dominant_delta_pct == -100.0
    # NaN-sentinel preservation (cumulative None sub-floor case).
    nan_blob = {
        **blob,
        "dominant_axis": None,
        "dominant_delta_pct": None,
    }
    parsed_nan = _parse_drift_attribution(nan_blob)
    assert isinstance(parsed_nan, DriftAttribution)
    assert parsed_nan.dominant_axis is None
    import math

    assert math.isnan(parsed_nan.dominant_delta_pct)
