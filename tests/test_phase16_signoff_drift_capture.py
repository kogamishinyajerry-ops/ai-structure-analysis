"""FM-04a Phase 16 C — drift_attribution_at_signoff_time on signoff records.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Substantiates the additive ``drift_attribution_at_signoff_time`` field
on the ``SignoffRecord`` schema (MINOR bump SIGNOFF_RECORD_SCHEMA_VERSION
1.0.0 → 1.1.0). The field captures the per-case
:class:`DriftAttribution` for the case's latest snapshot pair AT WRITE
TIME — server-computed (A:-3 NOT trusted from any client POST body),
embedded in the immutable signoff record, closing the audit-trail gap
between "WHAT regressed" (drift surface) and "WHO judged it" (signoff
record).

Anti-gaming guards pinned here (per Phase 16 binding rubric §3.C):
* **M:-1** — schema MINOR bump 1.0.0 → 1.1.0 with bump-history
  docstring citing Phase 16 C + the additive field + the A:-3
  server-computed posture.
* **A:-3** — drift is computed at write time from the live snapshot
  tree via ``build_trust_score_timeline``; NOT trusted from a
  client-supplied field. ``write_signoff_record`` accepts NO drift
  parameter — the server computes it unilaterally.
* **T:-3** — boundary pin: writing a signoff after the Phase 15 B
  3-snapshot leak arc captures
  ``drift_attribution_at_signoff_time.dominant_axis == "energy_audit"``
  + ``dominant_delta_pct == -100.0`` (the snap-2 → snap-3 transition
  is the load-bearing pair; per-case timeline's last
  inter_snapshot_drift_attribution entry equals snap-2 → snap-3).
* **C:-1** — Tier 1 disclaimer trio preserved on signoff-history
  envelope at 1.1.0.
* **Back-compat** — pre-1.1.0 on-disk records read as
  ``drift_attribution_at_signoff_time = None`` (graceful degrade).
"""

from __future__ import annotations

import json
import math
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
    build_signoff_history_report,
    read_signoff_history,
    render_signoff_history_json,
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
# M:-1 schema-version pin
# ---------------------------------------------------------------------


def test_signoff_record_schema_at_1_2_0() -> None:
    """Phase 16 C introduced MINOR bump 1.0.0 → 1.1.0; Phase 17 B
    introduced the subsequent 1.1.0 → 1.2.0 bump. The current SSOT
    is 1.2.0; the Phase 16 C
    ``drift_attribution_at_signoff_time`` field is preserved
    intact (see the back-compat test below)."""
    assert SIGNOFF_RECORD_SCHEMA_VERSION == "1.2.0"


# ---------------------------------------------------------------------
# Graceful degrade — no snapshots, drift is None
# ---------------------------------------------------------------------


def test_signoff_with_no_snapshots_has_null_drift(tmp_path: Path) -> None:
    """A signoff written before any snapshots exist for the case has
    ``drift_attribution_at_signoff_time = None`` (graceful degrade)."""
    record = write_signoff_record(
        case_id="alpha-candidate",
        reviewer="alice",
        verdict="watching",
        notes="Tier 1 candidate first observation.",
        repo_root=tmp_path,
    )
    assert record.drift_attribution_at_signoff_time is None


def test_signoff_with_one_snapshot_has_null_drift(tmp_path: Path) -> None:
    """A signoff written when the case has exactly ONE snapshot has
    drift = None (no transition exists yet)."""
    # Drive Phase 15 A generator + seed one snapshot.
    subprocess.check_call(
        [sys.executable, str(REPO_ROOT / "scripts" / "gen_rod_wave_impact_deck.py")],
        cwd=str(REPO_ROOT),
    )
    golden = tmp_path / "golden_samples"
    golden.mkdir(parents=True)
    shutil.copytree(
        REPO_ROOT / "golden_samples" / "rod-wave-impact-candidate",
        golden / "rod-wave-impact-candidate",
    )
    fixture = golden / "rod-wave-impact-candidate"
    write_cohort_snapshot(
        [
            SnapshotCaseInput(
                case_id="rod-wave-impact-candidate",
                starter_deck_path=fixture / "data" / "model_00_0000.rad",
                engine_deck_path=fixture / "data" / "model_00_0001.rad",
                ballistic_metrics_path=fixture / "data" / "ballistic_metrics.json",
                convergence_study_path=fixture / "data" / "convergence_study.json",
                animation_manifest_path=fixture / "data" / "animation_manifest.json",
                result_mesh_path=None,
                generator_script_path=None,
                notes_path=fixture / "NOTES.md",
                analysis_type="explicit_dynamics",
            )
        ],
        repo_root=tmp_path,
        snapshot_label=SNAP_1_LABEL,
    )
    record = write_signoff_record(
        case_id="rod-wave-impact-candidate",
        reviewer="alice",
        verdict="watching",
        notes="Tier 1 candidate.",
        repo_root=tmp_path,
    )
    assert record.drift_attribution_at_signoff_time is None


# ---------------------------------------------------------------------
# T:-3 boundary pin — signoff after the 3-snapshot leak arc
# ---------------------------------------------------------------------


def _stub(tmp: Path, name: str) -> Path:
    p = tmp / name
    if not p.exists():
        p.write_text("# stub", encoding="utf-8")
    return p


def _ed_healthy_input(tmp: Path, case_id: str) -> SnapshotCaseInput:
    fixture = tmp / "golden_samples" / case_id
    return SnapshotCaseInput(
        case_id=case_id,
        starter_deck_path=fixture / "data" / "model_00_0000.rad",
        engine_deck_path=fixture / "data" / "model_00_0001.rad",
        ballistic_metrics_path=fixture / "data" / "ballistic_metrics.json",
        convergence_study_path=fixture / "data" / "convergence_study.json",
        animation_manifest_path=fixture / "data" / "animation_manifest.json",
        result_mesh_path=None,
        generator_script_path=_stub(tmp, f"gen_{case_id.replace('-', '_')}.py"),
        notes_path=fixture / "NOTES.md",
        analysis_type="explicit_dynamics",
    )


def _clean_leak_input(tmp: Path) -> SnapshotCaseInput:
    fixture = tmp / "golden_samples" / LEAK_CASE_ID
    metrics_src = fixture / "data" / "ballistic_metrics.json"
    payload = json.loads(metrics_src.read_text(encoding="utf-8"))
    payload["energy_audit"]["status"] = "closed_aggregate"
    payload["energy_audit"]["rationale"] = (
        "Tier 1 candidate snap-1 healthy. Not signed validation; not benchmark agreement."
    )
    clean_dir = tmp / "phase16c_snap1_clean" / LEAK_CASE_ID
    clean_dir.mkdir(parents=True, exist_ok=True)
    clean_metrics = clean_dir / "ballistic_metrics.json"
    clean_metrics.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    conv_src = fixture / "data" / "convergence_study.json"
    conv_payload = json.loads(conv_src.read_text(encoding="utf-8"))
    conv_payload["combined_verdict"] = "candidate_observed_stable"
    conv_payload["mesh_sweep"]["candidate_stability"] = "candidate_observed_stable"
    conv_payload["dt_sweep"]["candidate_stability"] = "candidate_observed_stable"
    conv_payload["mesh_sweep"]["rationale"] = "Tier 1 candidate snap-1."
    conv_payload["dt_sweep"]["rationale"] = "Tier 1 candidate snap-1."
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
        generator_script_path=_stub(tmp, "gen_leak_clean.py"),
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
        animation_manifest_path=None,
        result_mesh_path=None,
        generator_script_path=None,
        notes_path=None,
        analysis_type="explicit_dynamics",
    )


@pytest.fixture(scope="module")
def leak_arc_repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Seed the Phase 15 B 3-snapshot leak arc for the leak case."""
    for gen in (
        "gen_rod_wave_impact_deck.py",
        "gen_rod_wave_impact_energy_leak_deck.py",
    ):
        subprocess.check_call(
            [sys.executable, str(REPO_ROOT / "scripts" / gen)],
            cwd=str(REPO_ROOT),
        )
    tmp = tmp_path_factory.mktemp("phase16c_leak_arc")
    golden = tmp / "golden_samples"
    golden.mkdir(parents=True)
    for case_id in ("rod-wave-impact-candidate", LEAK_CASE_ID):
        shutil.copytree(REPO_ROOT / "golden_samples" / case_id, golden / case_id)
    # snap-1: leak in CLEAN variant (full credit).
    write_cohort_snapshot(
        [
            _ed_healthy_input(tmp, "rod-wave-impact-candidate"),
            _clean_leak_input(tmp),
        ],
        repo_root=tmp,
        snapshot_label=SNAP_1_LABEL,
    )
    # snap-2: leak in canonical (energy axis 0).
    write_cohort_snapshot(
        [
            _ed_healthy_input(tmp, "rod-wave-impact-candidate"),
            _ed_healthy_input(tmp, LEAK_CASE_ID),
        ],
        repo_root=tmp,
        snapshot_label=SNAP_2_LABEL,
    )
    # snap-3: leak regressed (3 optional artifacts dropped).
    write_cohort_snapshot(
        [
            _ed_healthy_input(tmp, "rod-wave-impact-candidate"),
            _regressed_leak_input(tmp),
        ],
        repo_root=tmp,
        snapshot_label=SNAP_3_LABEL,
    )
    return tmp


def test_signoff_captures_drift_on_latest_pair_for_leak_case(
    leak_arc_repo: Path,
) -> None:
    """The load-bearing T:-3 pin: writing a watching signoff on the
    leak case AFTER the 3-snapshot degradation arc captures the
    snap-2 → snap-3 transition's drift in
    ``drift_attribution_at_signoff_time``.

    The snap-2 → snap-3 transition has energy axis 0 → 0 = 0%
    (the energy collapse happened earlier at snap-1 → snap-2). What
    drops at snap-2 → snap-3 is completeness (the 3 optional
    artifacts dropped) — so the dominant axis on this pair is
    completeness, NOT energy_audit. We pin both: (a) the from/to
    labels are snap-2 / snap-3, and (b) the dominant_axis is
    completeness."""
    record = write_signoff_record(
        case_id=LEAK_CASE_ID,
        reviewer="alice",
        verdict="watching",
        notes="Tier 1 candidate signoff; observed energy regression.",
        repo_root=leak_arc_repo,
    )
    drift = record.drift_attribution_at_signoff_time
    assert drift is not None
    assert isinstance(drift, DriftAttribution)
    # Latest pair = snap-2 → snap-3.
    assert drift.from_snapshot == SNAP_2_LABEL
    assert drift.to_snapshot == SNAP_3_LABEL
    # Energy axis stayed at 0 across snap-2 → snap-3 (no further change).
    assert drift.per_axis_delta_pct["energy_audit"] == 0.0
    # Completeness dropped 75 → 60 = -30% (3 optional artifacts
    # omitted, 5 pts each on the 50-pt axis = -15 weighted = -30%).
    assert drift.per_axis_delta_pct["completeness"] < 0


def test_signoff_drift_dominant_axis_when_only_first_pair_has_drop(
    tmp_path: Path,
) -> None:
    """A 2-snapshot timeline with energy 15 → 0 produces a signoff
    whose drift captures the energy collapse: dominant_axis ==
    "energy_audit" with dominant_delta_pct == -100.0 exactly.

    This is the "fresh signoff after the FIRST regression event"
    pattern — reviewer reads the alarm and judges immediately."""
    subprocess.check_call(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "gen_rod_wave_impact_energy_leak_deck.py"),
        ],
        cwd=str(REPO_ROOT),
    )
    golden = tmp_path / "golden_samples"
    golden.mkdir(parents=True)
    shutil.copytree(
        REPO_ROOT / "golden_samples" / LEAK_CASE_ID,
        golden / LEAK_CASE_ID,
    )
    # snap-1 clean (energy_audit closed_aggregate), snap-2 canonical
    # (energy_audit open_residual). Only 2 snapshots → drift captures
    # the 15 → 0 transition.
    write_cohort_snapshot(
        [_clean_leak_input(tmp_path)],
        repo_root=tmp_path,
        snapshot_label=SNAP_1_LABEL,
    )
    write_cohort_snapshot(
        [_ed_healthy_input(tmp_path, LEAK_CASE_ID)],
        repo_root=tmp_path,
        snapshot_label=SNAP_2_LABEL,
    )
    record = write_signoff_record(
        case_id=LEAK_CASE_ID,
        reviewer="alice",
        verdict="watching",
        notes="Tier 1 candidate; energy_audit just collapsed.",
        repo_root=tmp_path,
    )
    drift = record.drift_attribution_at_signoff_time
    assert isinstance(drift, DriftAttribution)
    assert drift.from_snapshot == SNAP_1_LABEL
    assert drift.to_snapshot == SNAP_2_LABEL
    assert drift.per_axis_delta_pct["energy_audit"] == -100.0
    assert drift.dominant_axis == "energy_audit"
    assert drift.dominant_delta_pct == -100.0


# ---------------------------------------------------------------------
# A:-3 server-computed (NOT client-trusted)
# ---------------------------------------------------------------------


def test_write_signoff_record_accepts_no_client_drift_parameter(
    tmp_path: Path,
) -> None:
    """A:-3 server-computed anti-gaming guard: ``write_signoff_record``
    signature MUST NOT accept a ``drift_attribution_at_signoff_time``
    parameter from the caller. The drift is computed server-side
    from the on-disk snapshot tree. A client that tries to inject
    a forged drift gets a TypeError on call (no kwarg)."""
    import inspect

    sig = inspect.signature(write_signoff_record)
    assert "drift_attribution_at_signoff_time" not in sig.parameters, (
        f"write_signoff_record signature MUST NOT accept "
        f"drift_attribution_at_signoff_time; got params: "
        f"{list(sig.parameters)}"
    )


# ---------------------------------------------------------------------
# Round-trip read/write — JSON serialization preserved
# ---------------------------------------------------------------------


def test_round_trip_read_write_preserves_drift_attribution(
    leak_arc_repo: Path,
) -> None:
    """Write a signoff with drift captured, read it back via
    read_signoff_history, assert the drift dataclass survives the
    JSON round-trip with identical from/to/percentages/dominant_axis."""
    written = write_signoff_record(
        case_id=LEAK_CASE_ID,
        reviewer="bob",
        verdict="needs_more_evidence",
        notes="Tier 1 candidate roundtrip test.",
        repo_root=leak_arc_repo,
    )
    history = read_signoff_history(LEAK_CASE_ID, repo_root=leak_arc_repo)
    assert len(history) >= 1
    # Find the record we just wrote.
    read_back = next(r for r in history if r.signoff_utc == written.signoff_utc)
    rb_drift = read_back.drift_attribution_at_signoff_time
    wr_drift = written.drift_attribution_at_signoff_time
    assert isinstance(rb_drift, DriftAttribution)
    assert isinstance(wr_drift, DriftAttribution)
    assert rb_drift.from_snapshot == wr_drift.from_snapshot
    assert rb_drift.to_snapshot == wr_drift.to_snapshot
    assert rb_drift.per_axis_delta_pct == wr_drift.per_axis_delta_pct
    assert rb_drift.dominant_axis == wr_drift.dominant_axis


# ---------------------------------------------------------------------
# C:-1 rendered envelope at 1.1.0 carries the field
# ---------------------------------------------------------------------


def test_history_envelope_carries_drift_field_at_1_1_0(
    leak_arc_repo: Path,
) -> None:
    """The signoff-history envelope at schema 1.1.0 carries the new
    ``drift_attribution_at_signoff_time`` field on each record's
    dict. The Tier 1 disclaimer trio is preserved."""
    write_signoff_record(
        case_id=LEAK_CASE_ID,
        reviewer="alice",
        verdict="watching",
        notes="Tier 1 candidate.",
        repo_root=leak_arc_repo,
    )
    report = build_signoff_history_report(LEAK_CASE_ID, repo_root=leak_arc_repo)
    payload = json.loads(render_signoff_history_json(report))
    # Phase 17 B bumped 1.1.0 → 1.2.0 additively; the Phase 16 C
    # drift_attribution_at_signoff_time field is preserved at 1.2.0.
    assert payload["schema_version"] == "1.2.0"
    assert payload["claim_tier"] == "Tier 1 engineering candidate"
    assert "not_signed_validation" in payload["claim_boundary"]
    assert "not_benchmark_agreement" in payload["claim_boundary"]
    assert payload["record_count"] >= 1
    for record_dict in payload["records"]:
        assert "drift_attribution_at_signoff_time" in record_dict
    # At least one record carries non-null drift (the leak arc has 3
    # snapshots, so writes after snap-3 carry the snap-2 → snap-3
    # transition).
    drift_dicts = [
        r["drift_attribution_at_signoff_time"]
        for r in payload["records"]
        if r["drift_attribution_at_signoff_time"] is not None
    ]
    assert drift_dicts, "expected at least one record with non-null drift"
    sample = drift_dicts[0]
    assert sample["from_snapshot"] == SNAP_2_LABEL
    assert sample["to_snapshot"] == SNAP_3_LABEL


# ---------------------------------------------------------------------
# Back-compat — 1.0.0-era on-disk record reads as None drift
# ---------------------------------------------------------------------


def test_back_compat_1_0_0_record_reads_as_null_drift(tmp_path: Path) -> None:
    """A pre-1.1.0 on-disk record (no ``drift_attribution_at_signoff_time``
    key) MUST read as ``drift = None`` via read_signoff_history
    (graceful degrade; the back-compat reader defaults missing
    fields)."""
    case_dir = tmp_path / "reports" / "signoffs" / "back-compat-candidate"
    case_dir.mkdir(parents=True)
    payload = {
        "schema_version": "1.0.0",
        "case_id": "back-compat-candidate",
        "reviewer": "alice",
        "verdict": "watching",
        "signoff_utc": "2026-05-16T100000Z",
        "notes": "1.0.0-era record without drift field.",
        "claim_tier": "Tier 1 engineering candidate",
        "claim_boundary": (
            "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"
        ),
        "claim_impact": (
            "Tier 1 candidate review judgments only; not signed validation; "
            "not benchmark agreement."
        ),
    }
    (case_dir / "2026-05-16T100000Z.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    history = read_signoff_history("back-compat-candidate", repo_root=tmp_path)
    assert len(history) == 1
    assert history[0].drift_attribution_at_signoff_time is None


# ---------------------------------------------------------------------
# C:-8 forbidden-token discipline — runtime audit on rendered envelope
# (NOT a source-file grep — the signoff_record.py module legitimately
# carries the forbidden-token tuples ``_FORBIDDEN_NOTES_TOKENS`` +
# ``_ENVELOPE_FORBIDDEN_TOKENS`` as DATA — they're the audit subject,
# not positive claims. Runtime audit on a rendered envelope is the
# right pin for Phase 16 C; a source-file grep would false-positive on
# the existing Phase 8 A data literals.)
# ---------------------------------------------------------------------


def test_history_envelope_runtime_audit_clean(leak_arc_repo: Path) -> None:
    """The runtime ``_assert_no_overclaim_in_report`` audit fires on
    every report build (Phase 8 B) and refuses any envelope carrying
    a forbidden positive claim outside ``not <claim>`` form. Phase
    16 C's additive ``drift_attribution_at_signoff_time`` field does
    NOT introduce forbidden-token-bearing copy (it's a structured
    dataclass with numeric percentages + axis labels + snapshot
    labels only). A clean build returns without raising."""
    write_signoff_record(
        case_id=LEAK_CASE_ID,
        reviewer="alice",
        verdict="watching",
        notes="Tier 1 candidate.",
        repo_root=leak_arc_repo,
    )
    # If a forbidden token had leaked into the envelope, this would
    # raise ValueError; reaching the return statement is the pin.
    report = build_signoff_history_report(LEAK_CASE_ID, repo_root=leak_arc_repo)
    assert report.record_count >= 1


# ---------------------------------------------------------------------
# Signed-registry refusal preserved on POST path
# ---------------------------------------------------------------------


def test_write_signoff_refuses_signed_registry(tmp_path: Path) -> None:
    """Phase 14 A cross-route signed-registry refusal SSOT preserved
    on the POST path (Phase 16 C wiring MUST NOT regress this)."""
    with pytest.raises(ValueError, match="signed.registry"):
        write_signoff_record(
            case_id="GS-001",
            reviewer="alice",
            verdict="watching",
            notes="Tier 1 candidate.",
            repo_root=tmp_path,
        )


# ---------------------------------------------------------------------
# Round-trip with None drift renders as null
# ---------------------------------------------------------------------


def test_record_with_none_drift_renders_as_null(tmp_path: Path) -> None:
    """A SignoffRecord with drift = None renders
    ``drift_attribution_at_signoff_time: null`` in the JSON."""
    record = write_signoff_record(
        case_id="no-snapshots-candidate",
        reviewer="alice",
        verdict="watching",
        notes="Tier 1 candidate; first observation.",
        repo_root=tmp_path,
    )
    assert record.drift_attribution_at_signoff_time is None
    # Re-read the file from disk to verify JSON rendering.
    case_dir = tmp_path / "reports" / "signoffs" / "no-snapshots-candidate"
    record_files = list(case_dir.glob("*.json"))
    assert len(record_files) == 1
    payload = json.loads(record_files[0].read_text(encoding="utf-8"))
    assert payload["drift_attribution_at_signoff_time"] is None
    # Phase 17 B bumped 1.1.0 → 1.2.0 additively; the Phase 16 C
    # drift_attribution_at_signoff_time field is preserved at 1.2.0.
    assert payload["schema_version"] == "1.2.0"


# ---------------------------------------------------------------------
# NaN rendering — dominant_delta_pct null when None dominant
# ---------------------------------------------------------------------


def test_record_with_null_dominant_axis_renders_nan_as_null(
    tmp_path: Path,
) -> None:
    """When the captured drift has dominant_axis = None (sub-floor
    uniform drift), ``dominant_delta_pct`` renders as JSON null
    (matches the Phase 15 C NaN-rendering convention)."""
    # Seed 2 identical snapshots — the leak case (or any case) has
    # zero drift across them.
    subprocess.check_call(
        [sys.executable, str(REPO_ROOT / "scripts" / "gen_rod_wave_impact_deck.py")],
        cwd=str(REPO_ROOT),
    )
    golden = tmp_path / "golden_samples"
    golden.mkdir(parents=True)
    shutil.copytree(
        REPO_ROOT / "golden_samples" / "rod-wave-impact-candidate",
        golden / "rod-wave-impact-candidate",
    )
    fixture = golden / "rod-wave-impact-candidate"
    case_input = SnapshotCaseInput(
        case_id="rod-wave-impact-candidate",
        starter_deck_path=fixture / "data" / "model_00_0000.rad",
        engine_deck_path=fixture / "data" / "model_00_0001.rad",
        ballistic_metrics_path=fixture / "data" / "ballistic_metrics.json",
        convergence_study_path=fixture / "data" / "convergence_study.json",
        animation_manifest_path=fixture / "data" / "animation_manifest.json",
        result_mesh_path=None,
        generator_script_path=None,
        notes_path=fixture / "NOTES.md",
        analysis_type="explicit_dynamics",
    )
    # Write the same healthy state twice → zero drift between them.
    write_cohort_snapshot([case_input], repo_root=tmp_path, snapshot_label=SNAP_1_LABEL)
    write_cohort_snapshot([case_input], repo_root=tmp_path, snapshot_label=SNAP_2_LABEL)
    record = write_signoff_record(
        case_id="rod-wave-impact-candidate",
        reviewer="alice",
        verdict="watching",
        notes="Tier 1 candidate; identical snaps for null-dominant test.",
        repo_root=tmp_path,
    )
    drift = record.drift_attribution_at_signoff_time
    assert isinstance(drift, DriftAttribution)
    # All axes zero delta → dominant_axis None, dominant_delta_pct NaN.
    assert drift.dominant_axis is None
    assert math.isnan(drift.dominant_delta_pct)
    # Re-read the file from disk.
    case_dir = tmp_path / "reports" / "signoffs" / "rod-wave-impact-candidate"
    record_files = list(case_dir.glob("*.json"))
    assert len(record_files) == 1
    payload = json.loads(record_files[0].read_text(encoding="utf-8"))
    rendered = payload["drift_attribution_at_signoff_time"]
    assert rendered is not None
    assert rendered["dominant_axis"] is None
    assert rendered["dominant_delta_pct"] is None
