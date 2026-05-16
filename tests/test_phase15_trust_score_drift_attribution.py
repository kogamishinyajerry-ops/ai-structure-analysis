"""FM-04a Phase 15 C — cross-snapshot drift attribution tests.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Substantiates ``backend/app/services/reporting/trust_score_drift_attribution.py``
+ its wiring into the alerts + timeline envelopes (schema 1.1.0 MINOR bumps).

Anti-gaming guards pinned here (per Phase 15 binding rubric §4):
* **M:-2** — `DRIFT_DOMINANT_AXIS_DELTA_FLOOR_PCT` SSOT constant lives
  at module level with the documented value (5.0); `TRUST_AXIS_WEIGHTS`
  sums to 100 (matches the 4 trust-score axes).
* **T:-3** — boundary-pinned: energy_audit 15→0 produces
  `delta_pct == -100.0` exactly; completeness 50→42 produces
  `delta_pct == -16.0` exactly.
* **A:-2** — defensive parser raises on (a) missing axes; (b)
  out-of-band values; (c) unknown axis labels; (d) non-positive floor.
* **C:-8** — Tier 1 disclaimer trio preserved on alerts + timeline
  envelopes; 9 forbidden tokens absent from the new module + doc.
"""

from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

import pytest
from app.services.reporting._schema_versions import (
    TRUST_SCORE_ALERTS_SCHEMA_VERSION,
    TRUST_SCORE_TIMELINE_SCHEMA_VERSION,
)
from app.services.reporting.cohort_snapshot import (
    SnapshotCaseInput,
    write_cohort_snapshot,
)
from app.services.reporting.trust_score_alerts import build_trust_score_alerts
from app.services.reporting.trust_score_drift_attribution import (
    DRIFT_DOMINANT_AXIS_DELTA_FLOOR_PCT,
    TRUST_AXIS_WEIGHTS,
    compute_drift_attribution,
    render_drift_attribution_dict,
)
from app.services.reporting.trust_score_timeline import (
    build_trust_score_timeline,
)

from tests._test_utils import (
    FORBIDDEN_POSITIVE_CLAIM_TOKENS_9,
    assert_no_forbidden_positive_claims,
)

# ---------------------------------------------------------------------
# M:-2 SSOT constant pins
# ---------------------------------------------------------------------


def test_drift_floor_pct_is_5_0() -> None:
    """SSOT 5%-floor pin. Bumping this constant MUST update the
    methodology doc bump-history per
    ``.planning/methodology/trust_score_drift_attribution.md``."""
    assert isinstance(DRIFT_DOMINANT_AXIS_DELTA_FLOOR_PCT, float)
    assert DRIFT_DOMINANT_AXIS_DELTA_FLOOR_PCT == 5.0


def test_trust_axis_weights_sum_to_one_hundred() -> None:
    """Anti-gaming guard M:-2 — the 4 trust-score axes MUST sum to
    100. A future rebalance MUST also update the methodology doc."""
    assert sum(TRUST_AXIS_WEIGHTS.values()) == 100
    assert set(TRUST_AXIS_WEIGHTS) == {
        "completeness",
        "convergence",
        "energy_audit",
        "reproducibility",
    }


def test_trust_axis_individual_weights() -> None:
    """Per-axis weights match the SSOT in trust_score.py."""
    assert TRUST_AXIS_WEIGHTS["completeness"] == 50
    assert TRUST_AXIS_WEIGHTS["convergence"] == 20
    assert TRUST_AXIS_WEIGHTS["energy_audit"] == 15
    assert TRUST_AXIS_WEIGHTS["reproducibility"] == 15


# ---------------------------------------------------------------------
# T:-3 boundary-pinned delta_pct tests
# ---------------------------------------------------------------------


def test_energy_audit_collapse_lands_at_minus_100_pct() -> None:
    """The load-bearing T:-3 pin: a 15→0 collapse on the 15-pt
    energy_audit axis produces `delta_pct = -100.0` exactly."""
    prev = {"completeness": 50, "convergence": 20, "energy_audit": 15, "reproducibility": 15}
    curr = {"completeness": 50, "convergence": 20, "energy_audit": 0, "reproducibility": 15}
    att = compute_drift_attribution(prev, curr, from_snapshot="t1", to_snapshot="t2")
    assert att.per_axis_delta_pct["energy_audit"] == -100.0
    assert att.dominant_axis == "energy_audit"
    assert att.dominant_delta_pct == -100.0


def test_completeness_eight_pt_drop_lands_at_minus_16_pct() -> None:
    """50→42 on the 50-pt completeness axis -> -16.0% exactly."""
    prev = {"completeness": 50, "convergence": 20, "energy_audit": 15, "reproducibility": 15}
    curr = {"completeness": 42, "convergence": 20, "energy_audit": 15, "reproducibility": 15}
    att = compute_drift_attribution(prev, curr, from_snapshot="t1", to_snapshot="t2")
    assert att.per_axis_delta_pct["completeness"] == -16.0
    assert att.dominant_axis == "completeness"
    assert att.dominant_delta_pct == -16.0


def test_positive_drift_recovers_signed_delta() -> None:
    """An axis IMPROVING (e.g., reproducibility 10→15) produces
    positive delta_pct."""
    prev = {"completeness": 50, "convergence": 20, "energy_audit": 15, "reproducibility": 10}
    curr = {"completeness": 50, "convergence": 20, "energy_audit": 15, "reproducibility": 15}
    att = compute_drift_attribution(prev, curr, from_snapshot="t1", to_snapshot="t2")
    # 5/15 * 100 = 33.33...%
    assert 33.0 < att.per_axis_delta_pct["reproducibility"] < 34.0
    assert att.dominant_axis == "reproducibility"
    assert att.dominant_delta_pct > 0


# ---------------------------------------------------------------------
# Floor behavior (uniform drift vs axis-attributed)
# ---------------------------------------------------------------------


def test_uniform_subfloor_drift_has_no_dominant_axis() -> None:
    """Every axis dropping by < 5% absolute -> no dominant axis."""
    prev = {"completeness": 50, "convergence": 20, "energy_audit": 15, "reproducibility": 15}
    # Each axis loses 1 weighted point: completeness -2%, convergence -5%, etc.
    # But convergence at 20→19 = -5% exactly; we want every axis ABS < 5.
    curr = {"completeness": 49, "convergence": 20, "energy_audit": 15, "reproducibility": 15}
    att = compute_drift_attribution(prev, curr, from_snapshot="t1", to_snapshot="t2")
    # All deltas absolute below 5%.
    for axis_pct in att.per_axis_delta_pct.values():
        assert abs(axis_pct) < DRIFT_DOMINANT_AXIS_DELTA_FLOOR_PCT
    assert att.dominant_axis is None
    assert math.isnan(att.dominant_delta_pct)


def test_at_floor_exact_does_not_count_as_dominant() -> None:
    """An axis whose absolute delta equals the floor exactly does
    NOT count as dominant (strict > floor, not >=)."""
    prev = {"completeness": 50, "convergence": 20, "energy_audit": 15, "reproducibility": 15}
    # convergence 20 → 19 = -5.0% exactly.
    curr = {"completeness": 50, "convergence": 19, "energy_audit": 15, "reproducibility": 15}
    att = compute_drift_attribution(prev, curr, from_snapshot="t1", to_snapshot="t2")
    assert att.per_axis_delta_pct["convergence"] == -5.0
    assert att.dominant_axis is None


def test_just_above_floor_counts_as_dominant() -> None:
    """A 6% drop on convergence (20→18.8 if it existed; here use a
    cleaner reproducibility 15→14 -> -6.67%) DOES count as dominant."""
    prev = {"completeness": 50, "convergence": 20, "energy_audit": 15, "reproducibility": 15}
    curr = {"completeness": 50, "convergence": 20, "energy_audit": 15, "reproducibility": 14}
    att = compute_drift_attribution(prev, curr, from_snapshot="t1", to_snapshot="t2")
    # 1/15 * 100 = 6.67% > 5%
    assert abs(att.per_axis_delta_pct["reproducibility"]) > 5.0
    assert att.dominant_axis == "reproducibility"


# ---------------------------------------------------------------------
# A:-2 defensive parser
# ---------------------------------------------------------------------


def test_compute_raises_on_missing_axes() -> None:
    """Every axis MUST be present in both prev + curr."""
    full = {"completeness": 50, "convergence": 20, "energy_audit": 15, "reproducibility": 15}
    partial = {"completeness": 50, "convergence": 20, "energy_audit": 15}
    with pytest.raises(ValueError, match="missing required keys"):
        compute_drift_attribution(partial, full, from_snapshot="t1", to_snapshot="t2")
    with pytest.raises(ValueError, match="missing required keys"):
        compute_drift_attribution(full, partial, from_snapshot="t1", to_snapshot="t2")


def test_compute_raises_on_unknown_axis_label() -> None:
    """A typo axis label like ``compleeteness`` MUST raise."""
    bad = {"compleeteness": 50, "convergence": 20, "energy_audit": 15, "reproducibility": 15}
    full = {"completeness": 50, "convergence": 20, "energy_audit": 15, "reproducibility": 15}
    with pytest.raises(ValueError, match="unknown trust axis label"):
        compute_drift_attribution(bad, full, from_snapshot="t1", to_snapshot="t2")


def test_compute_raises_on_out_of_band_value() -> None:
    """Negative values or values above the axis weight MUST raise."""
    full = {"completeness": 50, "convergence": 20, "energy_audit": 15, "reproducibility": 15}
    over = {"completeness": 51, "convergence": 20, "energy_audit": 15, "reproducibility": 15}
    neg = {"completeness": -1, "convergence": 20, "energy_audit": 15, "reproducibility": 15}
    with pytest.raises(ValueError, match="outside"):
        compute_drift_attribution(over, full, from_snapshot="t1", to_snapshot="t2")
    with pytest.raises(ValueError, match="outside"):
        compute_drift_attribution(neg, full, from_snapshot="t1", to_snapshot="t2")


def test_compute_raises_on_non_positive_floor() -> None:
    """`dominant_floor_pct` MUST be positive."""
    full = {"completeness": 50, "convergence": 20, "energy_audit": 15, "reproducibility": 15}
    with pytest.raises(ValueError, match="must be > 0"):
        compute_drift_attribution(
            full, full, from_snapshot="t1", to_snapshot="t2", dominant_floor_pct=0.0
        )
    with pytest.raises(ValueError, match="must be > 0"):
        compute_drift_attribution(
            full, full, from_snapshot="t1", to_snapshot="t2", dominant_floor_pct=-1.0
        )


# ---------------------------------------------------------------------
# JSON rendering
# ---------------------------------------------------------------------


def test_render_dict_nan_becomes_null() -> None:
    """When dominant_axis is None (uniform drift), the rendered
    dominant_delta_pct MUST serialize as null (NaN is not valid JSON)."""
    prev = {"completeness": 50, "convergence": 20, "energy_audit": 15, "reproducibility": 15}
    att = compute_drift_attribution(prev, prev, from_snapshot="t1", to_snapshot="t2")
    rendered = render_drift_attribution_dict(att)
    assert rendered["dominant_axis"] is None
    assert rendered["dominant_delta_pct"] is None
    # Round-trip through JSON to confirm well-formed.
    json.dumps(rendered)


def test_render_dict_round_trips() -> None:
    prev = {"completeness": 50, "convergence": 20, "energy_audit": 15, "reproducibility": 15}
    curr = {"completeness": 50, "convergence": 20, "energy_audit": 0, "reproducibility": 15}
    att = compute_drift_attribution(prev, curr, from_snapshot="t1", to_snapshot="t2")
    rendered = render_drift_attribution_dict(att)
    json.dumps(rendered)  # well-formed
    assert rendered["from_snapshot"] == "t1"
    assert rendered["to_snapshot"] == "t2"
    assert rendered["dominant_axis"] == "energy_audit"
    assert rendered["dominant_delta_pct"] == -100.0


# ---------------------------------------------------------------------
# Schema version pins (MINOR bumps)
# ---------------------------------------------------------------------


def test_alerts_schema_at_1_1_0() -> None:
    assert TRUST_SCORE_ALERTS_SCHEMA_VERSION == "1.1.0"


def test_timeline_schema_at_1_2_0() -> None:
    # Phase 16 A bumped the timeline schema to 1.2.0 with the
    # additive ``cumulative_drift_attribution`` field. The Phase 15 C
    # ``inter_snapshot_drift_attribution`` field remains intact at
    # 1.1.0 level; the 1.2.0 bump is purely additive.
    assert TRUST_SCORE_TIMELINE_SCHEMA_VERSION == "1.2.0"


# ---------------------------------------------------------------------
# End-to-end: live alerts + timeline carry drift_attribution
# ---------------------------------------------------------------------


REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def seeded_repo_for_drift(
    tmp_path_factory: pytest.TempPathFactory,
) -> Path:
    """Seed a tmp_path repo with 2 snapshots of the leak case so the
    alerts + timeline endpoints emit drift_attribution between them."""
    import subprocess
    import sys

    for gen in ("gen_rod_wave_impact_energy_leak_deck.py",):
        subprocess.check_call(
            [sys.executable, str(REPO_ROOT / "scripts" / gen)],
            cwd=str(REPO_ROOT),
        )

    tmp = tmp_path_factory.mktemp("phase15c_repo")
    golden = tmp / "golden_samples"
    golden.mkdir(parents=True)
    case_id = "rod-wave-impact-energy-leak-candidate"
    shutil.copytree(REPO_ROOT / "golden_samples" / case_id, golden / case_id)
    fixture = tmp / "golden_samples" / case_id

    # Snap-1: clean variant (energy closed_aggregate, convergence stable)
    clean_dir = tmp / "snap1_clean"
    clean_dir.mkdir()
    metrics_payload = json.loads(
        (fixture / "data" / "ballistic_metrics.json").read_text(encoding="utf-8")
    )
    metrics_payload["energy_audit"]["status"] = "closed_aggregate"
    metrics_payload["energy_audit"]["rationale"] = (
        "Tier 1 candidate clean snapshot; energy closed. Not signed "
        "validation; not benchmark agreement."
    )
    clean_metrics = clean_dir / "ballistic_metrics.json"
    clean_metrics.write_text(json.dumps(metrics_payload, indent=2), encoding="utf-8")
    conv_payload = json.loads(
        (fixture / "data" / "convergence_study.json").read_text(encoding="utf-8")
    )
    conv_payload["combined_verdict"] = "candidate_observed_stable"
    conv_payload["mesh_sweep"]["candidate_stability"] = "candidate_observed_stable"
    conv_payload["dt_sweep"]["candidate_stability"] = "candidate_observed_stable"
    conv_payload["mesh_sweep"]["rationale"] = (
        "Tier 1 candidate clean snapshot. Not signed validation."
    )
    conv_payload["dt_sweep"]["rationale"] = (
        "Tier 1 candidate clean snapshot. Not benchmark agreement."
    )
    clean_conv = clean_dir / "convergence_study.json"
    clean_conv.write_text(json.dumps(conv_payload, indent=2), encoding="utf-8")

    starter = tmp / "starter.rad"
    starter.write_text("# stub", encoding="utf-8")
    engine = tmp / "engine.rad"
    engine.write_text("# stub", encoding="utf-8")
    gen = tmp / "gen.py"
    gen.write_text("# stub generator", encoding="utf-8")

    snap1_input = SnapshotCaseInput(
        case_id=case_id,
        starter_deck_path=starter,
        engine_deck_path=engine,
        ballistic_metrics_path=clean_metrics,
        convergence_study_path=clean_conv,
        animation_manifest_path=fixture / "data" / "animation_manifest.json",
        result_mesh_path=None,
        generator_script_path=gen,
        notes_path=fixture / "NOTES.md",
        analysis_type="explicit_dynamics",
    )
    write_cohort_snapshot([snap1_input], repo_root=tmp, snapshot_label="2026-05-17T100000Z")

    # Snap-2: full Phase 15 A leak state (energy open_residual,
    # convergence unstable, no generator)
    snap2_input = SnapshotCaseInput(
        case_id=case_id,
        starter_deck_path=starter,
        engine_deck_path=engine,
        ballistic_metrics_path=fixture / "data" / "ballistic_metrics.json",
        convergence_study_path=fixture / "data" / "convergence_study.json",
        animation_manifest_path=None,
        result_mesh_path=None,
        generator_script_path=None,
        notes_path=None,
        analysis_type="explicit_dynamics",
    )
    write_cohort_snapshot([snap2_input], repo_root=tmp, snapshot_label="2026-05-17T140000Z")
    return tmp


def test_live_timeline_carries_inter_snapshot_drift(
    seeded_repo_for_drift: Path,
) -> None:
    """The live timeline's `inter_snapshot_drift_attribution` field
    has length = point_count - 1 (one entry per consecutive pair)."""
    timeline = build_trust_score_timeline(
        "rod-wave-impact-energy-leak-candidate", seeded_repo_for_drift
    )
    assert timeline.point_count == 2
    assert len(timeline.inter_snapshot_drift_attribution) == 1


def test_live_alerts_carry_drift_attribution_on_energy_axis(
    seeded_repo_for_drift: Path,
) -> None:
    """The leak-case snap-1 → snap-2 alarm event MUST identify
    `energy_audit` as the dominant axis (it collapses 15 → 0)."""
    report = build_trust_score_alerts(
        "rod-wave-impact-energy-leak-candidate", seeded_repo_for_drift
    )
    assert report.alert_count >= 1
    event = report.alerts[0]
    assert event.drift_attribution.dominant_axis == "energy_audit"
    assert event.drift_attribution.dominant_delta_pct == -100.0


# ---------------------------------------------------------------------
# C:-8 forbidden-token grep
# ---------------------------------------------------------------------


def test_no_forbidden_positive_claims_in_new_module() -> None:
    """The drift attribution module + methodology doc MUST carry no
    forbidden positive-claim tokens outside `not <claim>` /
    `no <claim>` form.

    Consumes the SSOT 9-tuple + grep helper from
    :mod:`tests._test_utils` (closes Phase 15 retro §7 — the 9-tuple
    + grep loop are no longer inlined per file). The stricter
    9-tuple is used for source-file grep (it rejects bare
    ``certified``); the narrower 8-tuple is used for envelope audits
    where CLAIM_BOUNDARY legitimately carries
    ``not_signed_validation_or_certified_simulation``."""
    sources = [
        REPO_ROOT
        / "backend"
        / "app"
        / "services"
        / "reporting"
        / "trust_score_drift_attribution.py",
        REPO_ROOT / ".planning" / "methodology" / "trust_score_drift_attribution.md",
    ]
    for src in sources:
        text = src.read_text(encoding="utf-8")
        assert_no_forbidden_positive_claims(text, tokens=FORBIDDEN_POSITIVE_CLAIM_TOKENS_9)
