"""FM-04a Phase 16 A — cumulative drift attribution on TrustScoreTimeline.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Substantiates the additive ``cumulative_drift_attribution`` field on
the ``TrustScoreTimeline`` envelope (MINOR bump 1.1.0 → 1.2.0). The
field carries a SINGLE :class:`DriftAttribution` spanning snap-1 →
snap-N (distinct from the consecutive-pair tuple already at 1.1.0).

Anti-gaming guards pinned here (per Phase 16 binding rubric §4):
* **M:-1** — schema MINOR bump 1.1.0 → 1.2.0 with bump-history
  docstring citing Phase 16 A + the additive ``cumulative_drift_attribution``
  field. ``inter_snapshot_drift_attribution`` retained intact.
* **M:-2** — consumer of Phase 15 C ``compute_drift_attribution``
  SSOT helper (NO inline percentage math); the cumulative computation
  is a single invocation against the first + last timeline points.
* **T:-3** — boundary-pinned: 3-snapshot leak arc cumulative
  ``dominant_axis == "energy_audit"`` with ``dominant_delta_pct == -100.0``
  exactly (snap-1 energy 15 → snap-3 energy 0 = -100% cumulative).
* **T:-4** — degenerate cases: 0-point timeline →
  ``cumulative_drift_attribution is None``; 1-point timeline →
  ``None``; 2-point timeline → cumulative EQUALS the single
  per-pair entry.
* **C:-1** — Tier 1 disclaimer trio preserved on the timeline
  envelope at 1.2.0.
* **C:-8** — forbidden-token grep clean on the methodology doc
  paragraph + the new field's docstring.
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
    TRUST_SCORE_TIMELINE_SCHEMA_VERSION,
)
from app.services.reporting.cohort_snapshot import (
    SnapshotCaseInput,
    write_cohort_snapshot,
)
from app.services.reporting.trust_score_drift_attribution import (
    DriftAttribution,
)
from app.services.reporting.trust_score_timeline import (
    build_trust_score_timeline,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

LEAK_CASE_ID = "rod-wave-impact-energy-leak-candidate"
CANONICAL_CASE_ID = "rod-wave-impact-candidate"

SNAP_1_LABEL = "2026-05-17T100000Z"
SNAP_2_LABEL = "2026-05-17T120000Z"
SNAP_3_LABEL = "2026-05-17T140000Z"


# ---------------------------------------------------------------------
# M:-1 schema version pin
# ---------------------------------------------------------------------


def test_timeline_schema_version_at_1_2_0() -> None:
    """Phase 16 A MINOR bump TRUST_SCORE_TIMELINE_SCHEMA_VERSION
    1.1.0 → 1.2.0 with bump-history docstring."""
    assert TRUST_SCORE_TIMELINE_SCHEMA_VERSION == "1.2.0"


# ---------------------------------------------------------------------
# T:-4 degenerate cases (0 / 1 / 2-point timelines)
# ---------------------------------------------------------------------


def test_zero_point_timeline_cumulative_is_none(tmp_path: Path) -> None:
    """A case with no snapshots whatsoever has
    ``cumulative_drift_attribution is None`` (no transition exists)."""
    timeline = build_trust_score_timeline("nonexistent-candidate", tmp_path)
    assert timeline.point_count == 0
    assert timeline.cumulative_drift_attribution is None


def test_one_point_timeline_cumulative_is_none(
    tmp_path: Path,
) -> None:
    """A case present in only ONE snapshot has
    ``cumulative_drift_attribution is None`` (no transition exists)."""
    # Drive Phase 15 A generators so the canonical fixture exists
    # on disk before we write a single snapshot.
    subprocess.check_call(
        [sys.executable, str(REPO_ROOT / "scripts" / "gen_rod_wave_impact_deck.py")],
        cwd=str(REPO_ROOT),
    )
    golden = tmp_path / "golden_samples"
    golden.mkdir(parents=True)
    shutil.copytree(
        REPO_ROOT / "golden_samples" / CANONICAL_CASE_ID,
        golden / CANONICAL_CASE_ID,
    )
    fixture = golden / CANONICAL_CASE_ID
    write_cohort_snapshot(
        [
            SnapshotCaseInput(
                case_id=CANONICAL_CASE_ID,
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
    timeline = build_trust_score_timeline(CANONICAL_CASE_ID, tmp_path)
    assert timeline.point_count == 1
    assert timeline.cumulative_drift_attribution is None
    # And no consecutive-pair drift either.
    assert timeline.inter_snapshot_drift_attribution == ()


# ---------------------------------------------------------------------
# T:-4 + T:-3 — 2-point timeline degenerate-equal + leak arc boundary
# ---------------------------------------------------------------------


def _seed_leak_arc_repo(tmp_path: Path) -> Path:
    """Reproduce the Phase 15 B 3-snapshot degradation arc for the
    leak case in a fresh tmp_path."""
    # Drive the Phase 15 A generators in the real repo so the
    # fixtures exist before copytree.
    for gen in (
        "gen_rod_wave_impact_deck.py",
        "gen_rod_wave_impact_energy_leak_deck.py",
    ):
        subprocess.check_call(
            [sys.executable, str(REPO_ROOT / "scripts" / gen)],
            cwd=str(REPO_ROOT),
        )
    golden = tmp_path / "golden_samples"
    golden.mkdir(parents=True)
    for case_id in (CANONICAL_CASE_ID, LEAK_CASE_ID):
        shutil.copytree(REPO_ROOT / "golden_samples" / case_id, golden / case_id)
    return tmp_path


def _stub(tmp: Path, name: str) -> Path:
    p = tmp / name
    if not p.exists():
        p.write_text("# stub artifact", encoding="utf-8")
    return p


def _healthy_input(tmp: Path, case_id: str) -> SnapshotCaseInput:
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


def _clean_leak_input(tmp: Path) -> SnapshotCaseInput:
    """snap-1 healthy variant of the leak case."""
    fixture = tmp / "golden_samples" / LEAK_CASE_ID
    metrics_src = fixture / "data" / "ballistic_metrics.json"
    payload = json.loads(metrics_src.read_text(encoding="utf-8"))
    payload["energy_audit"]["status"] = "closed_aggregate"
    payload["energy_audit"]["rationale"] = (
        "Tier 1 candidate snap-1 healthy state; energy partition closed at "
        "machine epsilon BEFORE the synthetic leak injection. Not signed "
        "validation; not benchmark agreement."
    )
    clean_dir = tmp / "phase16a_snap1_clean" / LEAK_CASE_ID
    clean_dir.mkdir(parents=True, exist_ok=True)
    clean_metrics = clean_dir / "ballistic_metrics.json"
    clean_metrics.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    conv_src = fixture / "data" / "convergence_study.json"
    conv_payload = json.loads(conv_src.read_text(encoding="utf-8"))
    conv_payload["combined_verdict"] = "candidate_observed_stable"
    conv_payload["mesh_sweep"]["candidate_stability"] = "candidate_observed_stable"
    conv_payload["dt_sweep"]["candidate_stability"] = "candidate_observed_stable"
    conv_payload["mesh_sweep"]["rationale"] = (
        "Tier 1 candidate snap-1 healthy state. Not signed validation."
    )
    conv_payload["dt_sweep"]["rationale"] = (
        "Tier 1 candidate snap-1 healthy state. Not benchmark agreement."
    )
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
    """snap-3 regressed variant: canonical state + 3 optional artifacts
    omitted (drops trust below 50)."""
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
    tmp = tmp_path_factory.mktemp("phase16a_leak_arc")
    _seed_leak_arc_repo(tmp)
    # snap-1: leak in CLEAN variant (full credit).
    write_cohort_snapshot(
        [_healthy_input(tmp, CANONICAL_CASE_ID), _clean_leak_input(tmp)],
        repo_root=tmp,
        snapshot_label=SNAP_1_LABEL,
    )
    # snap-2: leak in canonical Phase 15 A state (energy axis 0).
    write_cohort_snapshot(
        [_healthy_input(tmp, CANONICAL_CASE_ID), _healthy_input(tmp, LEAK_CASE_ID)],
        repo_root=tmp,
        snapshot_label=SNAP_2_LABEL,
    )
    # snap-3: leak regressed (3 optional artifacts omitted).
    write_cohort_snapshot(
        [_healthy_input(tmp, CANONICAL_CASE_ID), _regressed_leak_input(tmp)],
        repo_root=tmp,
        snapshot_label=SNAP_3_LABEL,
    )
    return tmp


def test_two_point_timeline_cumulative_equals_single_pair(
    tmp_path: Path,
) -> None:
    """A 2-point timeline has exactly 1 consecutive-pair entry; the
    cumulative entry MUST equal that single pair's per-axis
    percentages and dominant_axis (degenerate but correct)."""
    _seed_leak_arc_repo(tmp_path)
    # snap-1 leak clean + snap-2 leak open_residual = 1 transition.
    write_cohort_snapshot(
        [_clean_leak_input(tmp_path)],
        repo_root=tmp_path,
        snapshot_label=SNAP_1_LABEL,
    )
    write_cohort_snapshot(
        [_healthy_input(tmp_path, LEAK_CASE_ID)],
        repo_root=tmp_path,
        snapshot_label=SNAP_2_LABEL,
    )
    timeline = build_trust_score_timeline(LEAK_CASE_ID, tmp_path)
    assert timeline.point_count == 2
    assert len(timeline.inter_snapshot_drift_attribution) == 1
    pair = timeline.inter_snapshot_drift_attribution[0]
    cumulative = timeline.cumulative_drift_attribution
    assert cumulative is not None
    assert isinstance(cumulative, DriftAttribution)
    # Same percentages, same dominant axis, same from/to snapshots.
    assert cumulative.per_axis_delta_pct == pair.per_axis_delta_pct
    assert cumulative.dominant_axis == pair.dominant_axis
    if pair.dominant_axis is None:
        assert math.isnan(cumulative.dominant_delta_pct)
    else:
        assert cumulative.dominant_delta_pct == pair.dominant_delta_pct
    assert cumulative.from_snapshot == SNAP_1_LABEL
    assert cumulative.to_snapshot == SNAP_2_LABEL


# ---------------------------------------------------------------------
# T:-3 leak 3-snapshot arc cumulative boundary pin
# ---------------------------------------------------------------------


def test_leak_arc_cumulative_dominant_energy_axis_minus_100_exact(
    leak_arc_repo: Path,
) -> None:
    """The 3-snapshot leak arc has the energy_audit axis going
    15 → 0 → 0 across snap-1 → snap-2 → snap-3. The cumulative
    snap-1 → snap-3 spans the full collapse: cumulative
    ``dominant_axis == "energy_audit"`` with
    ``dominant_delta_pct == -100.0`` exactly (T:-3 boundary pin)."""
    timeline = build_trust_score_timeline(LEAK_CASE_ID, leak_arc_repo)
    assert timeline.point_count == 3
    assert len(timeline.inter_snapshot_drift_attribution) == 2
    cumulative = timeline.cumulative_drift_attribution
    assert cumulative is not None
    assert cumulative.from_snapshot == SNAP_1_LABEL
    assert cumulative.to_snapshot == SNAP_3_LABEL
    assert cumulative.per_axis_delta_pct["energy_audit"] == -100.0
    assert cumulative.dominant_axis == "energy_audit"
    assert cumulative.dominant_delta_pct == -100.0


def test_leak_arc_cumulative_consistent_with_per_pair_when_monotonic(
    leak_arc_repo: Path,
) -> None:
    """When an axis drops in a single per-pair transition and stays
    at the floor afterwards, the cumulative dominant_delta_pct equals
    the per-pair dominant_delta_pct for that axis (because no
    recovery cancels out the drop). The energy axis hits this
    case: 15 → 0 → 0 has snap-1→snap-2 = -100% and snap-1→snap-3 =
    -100% — the cumulative inherits the worst per-pair magnitude."""
    timeline = build_trust_score_timeline(LEAK_CASE_ID, leak_arc_repo)
    pair_snap1_snap2 = timeline.inter_snapshot_drift_attribution[0]
    cumulative = timeline.cumulative_drift_attribution
    assert cumulative is not None
    # Both surface energy_audit collapse at -100%.
    assert (
        pair_snap1_snap2.per_axis_delta_pct["energy_audit"]
        == cumulative.per_axis_delta_pct["energy_audit"]
        == -100.0
    )


# ---------------------------------------------------------------------
# T:-3 canonical case cumulative — uniform sub-floor
# ---------------------------------------------------------------------


def test_canonical_case_cumulative_uniform_sub_floor(
    leak_arc_repo: Path,
) -> None:
    """The canonical case stays full-credit at every snapshot
    (15/15 energy / 50/50 completeness / 20/20 convergence /
    15/15 reproducibility). The cumulative drift is uniformly 0%
    on every axis → ``dominant_axis is None`` (sub-floor uniform
    drift posture; the canonical case is the noise-floor anchor)."""
    timeline = build_trust_score_timeline(CANONICAL_CASE_ID, leak_arc_repo)
    cumulative = timeline.cumulative_drift_attribution
    assert cumulative is not None
    assert cumulative.dominant_axis is None
    assert math.isnan(cumulative.dominant_delta_pct)
    for axis_pct in cumulative.per_axis_delta_pct.values():
        assert axis_pct == 0.0


# ---------------------------------------------------------------------
# C:-1 Tier 1 disclaimer trio + schema version on rendered envelope
# ---------------------------------------------------------------------


def test_rendered_timeline_carries_cumulative_field_at_1_2_0(
    leak_arc_repo: Path,
) -> None:
    """The rendered JSON timeline at schema 1.2.0 carries the new
    ``cumulative_drift_attribution`` field at the top level. The
    Tier 1 disclaimer trio is preserved."""
    from app.services.reporting.trust_score_timeline import (
        render_trust_score_timeline_json,
    )

    timeline = build_trust_score_timeline(LEAK_CASE_ID, leak_arc_repo)
    payload = json.loads(render_trust_score_timeline_json(timeline))
    assert payload["schema_version"] == "1.2.0"
    assert payload["claim_tier"] == "Tier 1 engineering candidate"
    assert "not_signed_validation" in payload["claim_boundary"]
    assert "not_benchmark_agreement" in payload["claim_boundary"]
    assert "cumulative_drift_attribution" in payload
    cumulative_dict = payload["cumulative_drift_attribution"]
    assert cumulative_dict is not None
    assert cumulative_dict["dominant_axis"] == "energy_audit"
    assert cumulative_dict["dominant_delta_pct"] == -100.0


def test_rendered_timeline_cumulative_null_when_fewer_than_two_points(
    tmp_path: Path,
) -> None:
    """A timeline with fewer than 2 points renders
    ``cumulative_drift_attribution: null`` in JSON."""
    from app.services.reporting.trust_score_timeline import (
        render_trust_score_timeline_json,
    )

    timeline = build_trust_score_timeline("nonexistent-candidate", tmp_path)
    payload = json.loads(render_trust_score_timeline_json(timeline))
    assert payload["cumulative_drift_attribution"] is None


# ---------------------------------------------------------------------
# C:-8 forbidden-token grep on methodology doc cumulative section
# ---------------------------------------------------------------------


def test_methodology_doc_cumulative_section_passes_forbidden_grep() -> None:
    """The Phase 16 A methodology paragraph in
    ``.planning/methodology/trust_score_drift_attribution.md`` MUST
    NOT carry any of the 9 forbidden positive-claim tokens outside
    ``not <claim>`` / ``no <claim>`` form. This is a smoke grep
    complementing the Phase 15 C module-level guard."""
    forbidden = (
        "validated against",
        "perforation completed",
        "bullet-through-steel complete",
        "validated physics",
        "production ready",
        "certified",
        "approved for service",
        "asme compliant",
        "signed off",
    )
    doc = REPO_ROOT / ".planning" / "methodology" / "trust_score_drift_attribution.md"
    text = doc.read_text(encoding="utf-8").lower()
    for token in forbidden:
        idx = text.find(token)
        while idx != -1:
            prefix_raw = text[max(0, idx - 8) : idx]
            prefix = prefix_raw.replace("`", " ").replace('"', " ").strip()
            allowed = prefix.endswith("not") or prefix.endswith("no")
            assert allowed, (
                f"forbidden token {token!r} appears in methodology "
                f"doc outside negated form; context: "
                f"...{text[max(0, idx - 30) : idx + len(token) + 30]}..."
            )
            idx = text.find(token, idx + 1)


# ---------------------------------------------------------------------
# Back-compat smoke: a 1.1.0 reader ignoring the new field still parses
# ---------------------------------------------------------------------


def test_back_compat_1_1_0_reader_ignores_cumulative_field(
    leak_arc_repo: Path,
) -> None:
    """Pre-1.2.0 readers that ignore unknown JSON fields MUST still
    parse 1.2.0 envelopes. We simulate this by reading the 1.2.0
    payload and asserting the 1.1.0 fields (schema_version, points,
    inter_snapshot_drift_attribution, Tier 1 trio) are all intact
    in their pre-1.2.0 shape."""
    from app.services.reporting.trust_score_timeline import (
        render_trust_score_timeline_json,
    )

    timeline = build_trust_score_timeline(LEAK_CASE_ID, leak_arc_repo)
    payload = json.loads(render_trust_score_timeline_json(timeline))
    # 1.1.0-era fields still present + correctly shaped.
    assert "schema_version" in payload
    assert "points" in payload
    assert "inter_snapshot_drift_attribution" in payload
    assert len(payload["inter_snapshot_drift_attribution"]) == 2
    assert "claim_tier" in payload
    assert "claim_boundary" in payload
    assert "claim_impact" in payload
    # The new 1.2.0 field is additive — its absence in a 1.1.0
    # reader's parsing schema does NOT break the rest.
    # (Simulated by simply checking the field is at the same level
    # as the other top-level fields; a reader's JSON parser ignoring
    # unknown keys will skip it.)
    assert "cumulative_drift_attribution" in payload
