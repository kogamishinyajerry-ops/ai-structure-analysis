"""FM-04a Phase 16 B — cohort-scoped drift attribution on cohort-anomalies.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Substantiates the new SSOT module
``backend/app/services/reporting/cohort_drift_attribution.py`` and its
wiring into the ``cohort-anomalies`` envelope (MINOR bump
COHORT_ANOMALIES_SCHEMA_VERSION 1.0.0 → 1.1.0).

Anti-gaming guards pinned here (per Phase 16 binding rubric §3.B):
* **M:-1** — schema MINOR bump 1.0.0 → 1.1.0 with bump-history
  docstring citing Phase 16 B + the additive ``cohort_drift_attribution``
  field. Z-score view preserved (additive, not replacement).
* **M:-2** — ``COHORT_DOMINANT_AXIS_FLOOR_PCT`` SSOT constant lives
  at module level with the documented value (5.0); consumer
  (``cohort_anomalies.py``) IMPORTS ``compute_cohort_drift_attribution``
  rather than inline-aggregating per-case math.
* **T:-3** — boundary-pinned: 5-case cohort with one leak case at
  energy_audit 15→0 produces ``cohort_dominant_axis == "energy_audit"``
  + ``dominant_case_id == LEAK_CASE_ID`` + ``cohort_max_abs_delta_pct
  == 100.0`` exactly.
* **A:-2** — defensive parser raises on non-positive floor; returns
  ``None`` (not raises) when fewer than 2 snapshots exist.
* **C:-1** — Tier 1 disclaimer trio preserved on the cohort-anomalies
  envelope at 1.1.0.
* **C:-8** — forbidden-token grep clean on new module + methodology doc.
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
    COHORT_ANOMALIES_SCHEMA_VERSION,
)
from app.services.reporting.cohort_anomalies import build_cohort_anomalies
from app.services.reporting.cohort_drift_attribution import (
    COHORT_DOMINANT_AXIS_FLOOR_PCT,
    CohortDriftAttribution,
    compute_cohort_drift_attribution,
    render_cohort_drift_attribution_dict,
)
from app.services.reporting.cohort_snapshot import (
    SnapshotCaseInput,
    write_cohort_snapshot,
)
from app.services.reporting.trust_score_drift_attribution import (
    DriftAttribution,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

LEAK_CASE_ID = "rod-wave-impact-energy-leak-candidate"
COHORT_CASES: tuple[tuple[str, str], ...] = (
    ("rod-wave-impact-candidate", "explicit_dynamics"),
    ("rod-wave-impact-stiff-candidate", "explicit_dynamics"),
    ("rod-wave-impact-energy-leak-candidate", "explicit_dynamics"),
    ("cylinder-pv-candidate", "linear_static_pv"),
    ("cylinder-pv-extended-candidate", "linear_static_pv"),
)

SNAP_1_LABEL = "2026-05-17T100000Z"
SNAP_2_LABEL = "2026-05-17T120000Z"
SNAP_3_LABEL = "2026-05-17T140000Z"


# ---------------------------------------------------------------------
# M:-1 schema-version pin
# ---------------------------------------------------------------------


def test_cohort_anomalies_schema_at_1_2_0() -> None:
    """Phase 16 B introduced MINOR bump 1.0.0 → 1.1.0; Phase 17 A
    introduced the subsequent 1.1.0 → 1.2.0 bump. The current SSOT
    is 1.2.0; this test pins that. (Phase 16 B's
    ``cohort_drift_attribution`` field is preserved intact at 1.2.0
    — see ``test_back_compat_1_0_0_reader_still_parses`` for the
    additive-bump back-compat audit.)"""
    assert COHORT_ANOMALIES_SCHEMA_VERSION == "1.2.0"


# ---------------------------------------------------------------------
# M:-2 SSOT constant pins
# ---------------------------------------------------------------------


def test_cohort_dominant_axis_floor_pct_is_5_0() -> None:
    """SSOT 5%-floor pin matching the per-case floor (parallel
    thresholds for coherent reviewer cross-reading)."""
    assert isinstance(COHORT_DOMINANT_AXIS_FLOOR_PCT, float)
    assert COHORT_DOMINANT_AXIS_FLOOR_PCT == 5.0


# ---------------------------------------------------------------------
# A:-2 defensive parser
# ---------------------------------------------------------------------


def test_compute_raises_on_non_positive_floor(tmp_path: Path) -> None:
    """A non-positive floor MUST raise ValueError."""
    with pytest.raises(ValueError, match="dominant_floor_pct must be > 0"):
        compute_cohort_drift_attribution(repo_root=tmp_path, dominant_floor_pct=0.0)
    with pytest.raises(ValueError, match="dominant_floor_pct must be > 0"):
        compute_cohort_drift_attribution(repo_root=tmp_path, dominant_floor_pct=-1.0)


def test_compute_returns_none_when_fewer_than_two_snapshots(
    tmp_path: Path,
) -> None:
    """With 0 or 1 snapshots in reports/snapshots/, the cohort-wide
    pair cannot be computed; the function returns None (graceful
    degrade, NOT raises)."""
    # No snapshots at all.
    result = compute_cohort_drift_attribution(repo_root=tmp_path)
    assert result is None


# ---------------------------------------------------------------------
# Fixture seeding for the boundary-pinned T:-3 tests
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
        generator_script_path=_stub(tmp, f"gen_{case_id.replace('-', '_')}_deck.py"),
        notes_path=fixture / "NOTES.md",
        analysis_type="explicit_dynamics",
    )


def _pv_input(tmp: Path, case_id: str) -> SnapshotCaseInput:
    fixture = tmp / "golden_samples" / case_id
    starter = fixture / "data" / "model_00_0000.rad"
    engine = fixture / "data" / "model_00_0001.rad"
    generator = fixture / "data" / "generator.py"
    return SnapshotCaseInput(
        case_id=case_id,
        starter_deck_path=starter if starter.is_file() else _stub(tmp, f"{case_id}_starter.rad"),
        engine_deck_path=engine if engine.is_file() else _stub(tmp, f"{case_id}_engine.rad"),
        ballistic_metrics_path=fixture / "data" / "ballistic_metrics.json",
        convergence_study_path=fixture / "data" / "convergence_study.json",
        animation_manifest_path=None,
        result_mesh_path=None,
        generator_script_path=generator if generator.is_file() else _stub(tmp, f"{case_id}_gen.py"),
        notes_path=None,
        analysis_type="linear_static_pv",
    )


def _clean_leak_input(tmp: Path) -> SnapshotCaseInput:
    fixture = tmp / "golden_samples" / LEAK_CASE_ID
    metrics_src = fixture / "data" / "ballistic_metrics.json"
    payload = json.loads(metrics_src.read_text(encoding="utf-8"))
    payload["energy_audit"]["status"] = "closed_aggregate"
    payload["energy_audit"]["rationale"] = (
        "Tier 1 candidate snap-1 healthy. Not signed validation; not benchmark agreement."
    )
    clean_dir = tmp / "phase16b_snap1_clean" / LEAK_CASE_ID
    clean_dir.mkdir(parents=True, exist_ok=True)
    clean_metrics = clean_dir / "ballistic_metrics.json"
    clean_metrics.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    conv_src = fixture / "data" / "convergence_study.json"
    conv_payload = json.loads(conv_src.read_text(encoding="utf-8"))
    conv_payload["combined_verdict"] = "candidate_observed_stable"
    conv_payload["mesh_sweep"]["candidate_stability"] = "candidate_observed_stable"
    conv_payload["dt_sweep"]["candidate_stability"] = "candidate_observed_stable"
    conv_payload["mesh_sweep"]["rationale"] = "Tier 1 candidate snap-1. Not signed validation."
    conv_payload["dt_sweep"]["rationale"] = "Tier 1 candidate snap-1. Not benchmark agreement."
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


@pytest.fixture(scope="module")
def seeded_5_case_arc(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Seed the same 5-case Phase 15 D Journey 2 cohort: 3
    explicit_dynamics + 2 linear_static_pv, with a 2-snapshot arc
    (snap-2 → snap-3) where the leak case's energy axis collapses
    15 → 0 between the two snapshots and every other case stays
    healthy."""
    for gen in (
        "gen_rod_wave_impact_deck.py",
        "gen_rod_wave_impact_stiff_deck.py",
        "gen_rod_wave_impact_energy_leak_deck.py",
    ):
        subprocess.check_call(
            [sys.executable, str(REPO_ROOT / "scripts" / gen)],
            cwd=str(REPO_ROOT),
        )
    tmp = tmp_path_factory.mktemp("phase16b_5_case_arc")
    golden = tmp / "golden_samples"
    golden.mkdir(parents=True)
    for case_id, _atype in COHORT_CASES:
        shutil.copytree(REPO_ROOT / "golden_samples" / case_id, golden / case_id)

    # Snap-2: ALL healthy (leak case in CLEAN variant).
    write_cohort_snapshot(
        [
            _ed_healthy_input(tmp, "rod-wave-impact-candidate"),
            _ed_healthy_input(tmp, "rod-wave-impact-stiff-candidate"),
            _clean_leak_input(tmp),
            _pv_input(tmp, "cylinder-pv-candidate"),
            _pv_input(tmp, "cylinder-pv-extended-candidate"),
        ],
        repo_root=tmp,
        snapshot_label=SNAP_2_LABEL,
    )
    # Snap-3: leak case in canonical Phase 15 A state (energy 0);
    # others stay healthy.
    write_cohort_snapshot(
        [
            _ed_healthy_input(tmp, "rod-wave-impact-candidate"),
            _ed_healthy_input(tmp, "rod-wave-impact-stiff-candidate"),
            _ed_healthy_input(tmp, LEAK_CASE_ID),
            _pv_input(tmp, "cylinder-pv-candidate"),
            _pv_input(tmp, "cylinder-pv-extended-candidate"),
        ],
        repo_root=tmp,
        snapshot_label=SNAP_3_LABEL,
    )
    return tmp


# ---------------------------------------------------------------------
# T:-3 boundary-pinned cohort drift attribution
# ---------------------------------------------------------------------


def test_cohort_dominant_axis_is_energy_audit_on_leak_case(
    seeded_5_case_arc: Path,
) -> None:
    """The load-bearing T:-3 pin: a 5-case cohort with one leak case
    going 15→0 on the energy axis surfaces ``cohort_dominant_axis ==
    "energy_audit"`` + ``dominant_case_id == LEAK_CASE_ID`` +
    ``cohort_max_abs_delta_pct == 100.0`` exactly."""
    result = compute_cohort_drift_attribution(repo_root=seeded_5_case_arc)
    assert result is not None
    assert isinstance(result, CohortDriftAttribution)
    assert result.from_snapshot == SNAP_2_LABEL
    assert result.to_snapshot == SNAP_3_LABEL
    assert result.cohort_dominant_axis == "energy_audit"
    assert result.dominant_case_id == LEAK_CASE_ID
    assert result.cohort_max_abs_delta_pct == 100.0


def test_cohort_per_case_carries_all_5_members(
    seeded_5_case_arc: Path,
) -> None:
    """``per_case_drift_attribution`` carries 5 entries (one per cohort
    member; both PV cases present in both snapshots)."""
    result = compute_cohort_drift_attribution(repo_root=seeded_5_case_arc)
    assert result is not None
    case_ids = {cid for cid, _ in result.per_case_drift_attribution}
    assert case_ids == {cid for cid, _ in COHORT_CASES}


def test_cohort_leak_case_per_case_dominant_energy_minus_100_exact(
    seeded_5_case_arc: Path,
) -> None:
    """The leak case's per-case DriftAttribution within the cohort
    summary names energy_audit dominant at -100.0% exactly."""
    result = compute_cohort_drift_attribution(repo_root=seeded_5_case_arc)
    assert result is not None
    leak_entries = [att for cid, att in result.per_case_drift_attribution if cid == LEAK_CASE_ID]
    assert len(leak_entries) == 1
    leak_att = leak_entries[0]
    assert isinstance(leak_att, DriftAttribution)
    assert leak_att.per_axis_delta_pct["energy_audit"] == -100.0
    assert leak_att.dominant_axis == "energy_audit"
    assert leak_att.dominant_delta_pct == -100.0


def test_cohort_healthy_cases_have_no_dominant_axis(
    seeded_5_case_arc: Path,
) -> None:
    """All 4 non-leak cohort members stay healthy across snap-2 →
    snap-3 (full credit at every axis); their per-case
    DriftAttribution has dominant_axis = None (sub-floor uniform
    drift)."""
    result = compute_cohort_drift_attribution(repo_root=seeded_5_case_arc)
    assert result is not None
    for cid, att in result.per_case_drift_attribution:
        if cid == LEAK_CASE_ID:
            continue
        assert att.dominant_axis is None, (
            f"{cid} unexpectedly has dominant_axis={att.dominant_axis!r}"
        )


# ---------------------------------------------------------------------
# Floor behavior — sub-floor uniform drift surfaces None
# ---------------------------------------------------------------------


def test_below_floor_cohort_has_no_dominant(
    seeded_5_case_arc: Path,
) -> None:
    """If we bump the floor above the leak case's 100% delta, the
    cohort dominant axis becomes None (sub-floor uniform drift
    cohort posture). NaN is the sentinel for absent magnitude."""
    result = compute_cohort_drift_attribution(repo_root=seeded_5_case_arc, dominant_floor_pct=101.0)
    assert result is not None
    assert result.cohort_dominant_axis is None
    assert result.dominant_case_id is None
    assert math.isnan(result.cohort_max_abs_delta_pct)


# ---------------------------------------------------------------------
# Live ASGI integration — cohort-anomalies envelope carries the field
# ---------------------------------------------------------------------


def test_cohort_anomalies_envelope_carries_cohort_drift_field(
    seeded_5_case_arc: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The Phase 16 B wiring lands the new ``cohort_drift_attribution``
    field on the rendered cohort-anomalies envelope; the new field
    is additive (z-score view + Tier 1 trio preserved)."""
    from app.services.reporting.cohort_anomalies import (
        render_cohort_anomalies_json,
    )

    report = build_cohort_anomalies(repo_root=seeded_5_case_arc)
    payload = json.loads(render_cohort_anomalies_json(report))
    # Phase 17 A bumped 1.1.0 → 1.2.0 (additive); the Phase 16 B
    # ``cohort_drift_attribution`` field is preserved at 1.2.0.
    assert payload["schema_version"] == "1.2.0"
    assert payload["claim_tier"] == "Tier 1 engineering candidate"
    assert "not_signed_validation" in payload["claim_boundary"]
    assert "not_benchmark_agreement" in payload["claim_boundary"]
    # Z-score view preserved (additive).
    assert "anomalies" in payload
    # New Phase 16 B field at the same level.
    assert "cohort_drift_attribution" in payload
    cohort_dict = payload["cohort_drift_attribution"]
    assert cohort_dict is not None
    assert cohort_dict["cohort_dominant_axis"] == "energy_audit"
    assert cohort_dict["dominant_case_id"] == LEAK_CASE_ID
    assert cohort_dict["cohort_max_abs_delta_pct"] == 100.0
    # Per-case entries each carry a case_id field.
    for entry in cohort_dict["per_case_drift_attribution"]:
        assert "case_id" in entry
        assert "per_axis_delta_pct" in entry


def test_cohort_anomalies_envelope_null_drift_when_no_snapshots(
    tmp_path: Path,
) -> None:
    """When fewer than 2 snapshots exist, the envelope carries
    ``cohort_drift_attribution: null`` (graceful degrade)."""
    from app.services.reporting.cohort_anomalies import (
        render_cohort_anomalies_json,
    )

    report = build_cohort_anomalies(repo_root=tmp_path)
    payload = json.loads(render_cohort_anomalies_json(report))
    assert payload["cohort_drift_attribution"] is None


# ---------------------------------------------------------------------
# Render helper — None handling
# ---------------------------------------------------------------------


def test_render_helper_passes_through_none() -> None:
    """``render_cohort_drift_attribution_dict(None)`` returns
    ``None`` for the JSON-null path."""
    assert render_cohort_drift_attribution_dict(None) is None


def test_render_helper_nan_becomes_null() -> None:
    """``cohort_max_abs_delta_pct`` rendered as ``None`` when NaN
    (matches the per-case Phase 15 C ``dominant_delta_pct`` pattern)."""
    att = CohortDriftAttribution(
        from_snapshot="t1",
        to_snapshot="t2",
        per_case_drift_attribution=(),
        cohort_dominant_axis=None,
        cohort_max_abs_delta_pct=math.nan,
        dominant_case_id=None,
    )
    rendered = render_cohort_drift_attribution_dict(att)
    assert rendered is not None
    assert rendered["cohort_max_abs_delta_pct"] is None


# ---------------------------------------------------------------------
# C:-8 forbidden-token grep on new module + methodology doc
# ---------------------------------------------------------------------


def test_no_forbidden_positive_claims_in_new_module() -> None:
    """The 9 forbidden positive-claim tokens MUST NOT appear in the
    new module / methodology doc outside ``not <claim>`` / ``no
    <claim>`` form.

    Consumes the SSOT 9-tuple + grep helper from
    :mod:`tests._test_utils` (closes Phase 15 retro §7)."""
    from tests._test_utils import (
        FORBIDDEN_POSITIVE_CLAIM_TOKENS_9,
        assert_no_forbidden_positive_claims,
    )

    sources = [
        REPO_ROOT / "backend" / "app" / "services" / "reporting" / "cohort_drift_attribution.py",
        REPO_ROOT / ".planning" / "methodology" / "cohort_drift_attribution.md",
    ]
    for src in sources:
        text = src.read_text(encoding="utf-8")
        assert_no_forbidden_positive_claims(text, tokens=FORBIDDEN_POSITIVE_CLAIM_TOKENS_9)


# ---------------------------------------------------------------------
# Back-compat smoke — 1.0.0-era fields still present in 1.1.0 envelope
# ---------------------------------------------------------------------


def test_back_compat_1_0_0_reader_still_parses(
    seeded_5_case_arc: Path,
) -> None:
    """Pre-1.1.0 readers ignoring unknown JSON fields MUST still
    parse 1.1.0 envelopes. The 1.0.0-era fields (schema_version,
    anomalies, cohort_count, anomaly_count, Tier 1 trio) are all
    intact in 1.1.0."""
    from app.services.reporting.cohort_anomalies import (
        render_cohort_anomalies_json,
    )

    report = build_cohort_anomalies(repo_root=seeded_5_case_arc)
    payload = json.loads(render_cohort_anomalies_json(report))
    for required_field in (
        "schema_version",
        "generated_at_utc",
        "claim_tier",
        "claim_boundary",
        "cohort_count",
        "anomaly_count",
        "anomalies",
        "claim_impact",
    ):
        assert required_field in payload, (
            f"1.0.0-era field {required_field!r} missing from 1.1.0 envelope"
        )
    # The new 1.1.0 field is additive.
    assert "cohort_drift_attribution" in payload
