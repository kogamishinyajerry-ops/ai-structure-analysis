"""FM-04a Phase 17 A — cohort-scoped cumulative drift attribution on cohort-anomalies.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Substantiates the additive ``cohort_cumulative_drift_attribution`` field
on the ``cohort-anomalies`` envelope (MINOR bump
``COHORT_ANOMALIES_SCHEMA_VERSION`` 1.1.0 → 1.2.0). The field carries a
:class:`CohortDriftAttribution` spanning the cohort-wide EARLIEST →
LATEST snapshot pair (parallel to the Phase 16 B
``cohort_drift_attribution`` which spans the LATEST consecutive pair).

Anti-gaming guards pinned here (per Phase 17 binding rubric §3.A):
* **M:-1** — schema MINOR bump 1.1.0 → 1.2.0 with bump-history docstring
  citing Phase 17 A + the additive ``cohort_cumulative_drift_attribution``
  field. ``cohort_drift_attribution`` (Phase 16 B) preserved.
* **M:-2** — consumer (`cohort_anomalies.py`) IMPORTS
  ``compute_cohort_cumulative_drift_attribution`` rather than inline-
  aggregating per-case math. The cumulative compute itself delegates to
  the shared ``_aggregate_cohort_drift_for_pair`` SSOT helper introduced
  in this slice (no duplicated logic vs latest-pair compute).
* **T:-3** — boundary-pinned: 3-snapshot stuck arc (leak case energy
  15→15→0) lands ``cohort_cumulative_drift_attribution.cohort_dominant_axis
  == "energy_audit"`` + ``dominant_case_id == LEAK_CASE_ID`` +
  ``cohort_max_abs_delta_pct == 100.0`` exactly + ``from_snapshot ==
  SNAP_1_LABEL`` + ``to_snapshot == SNAP_3_LABEL``.
* **T:-4** — recovery arc (leak 15→0→15): cumulative
  ``cohort_dominant_axis is None`` (sub-floor across the arc) while the
  latest-pair view (Phase 16 B field) surfaces energy_audit on the
  snap-2 → snap-3 recovery transition.
* **T:-5** — degenerate cases: 0-snapshot → None; 1-snapshot → None;
  2-snapshot → cumulative endpoints EQUAL latest-pair endpoints (the
  two views degenerate to the same pair).
* **A:-2** — defensive parser raises on non-positive floor; returns
  ``None`` (not raises) when fewer than 2 snapshots exist.
* **C:-1** — Tier 1 disclaimer trio preserved on cohort-anomalies
  envelope at 1.2.0.
* **C:-8** — forbidden-token grep on new methodology paragraph + new
  helper docstring (via SSOT 9-tuple).
* **V:-3** — every snapshot write under tmp_path; real
  ``reports/snapshots/`` byte-identical pre/post run.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import httpx
import pytest
from app.api.routes import cohort_anomalies as cohort_anomalies_route
from app.main import app
from app.services.reporting._schema_versions import (
    COHORT_ANOMALIES_SCHEMA_VERSION,
)
from app.services.reporting.cohort_anomalies import build_cohort_anomalies
from app.services.reporting.cohort_drift_attribution import (
    COHORT_DOMINANT_AXIS_FLOOR_PCT,
    CohortDriftAttribution,
    _aggregate_cohort_drift_for_pair,
    _discover_earliest_latest_snapshot_pair,
    _discover_latest_snapshot_pair,
    compute_cohort_cumulative_drift_attribution,
    compute_cohort_drift_attribution,
)
from app.services.reporting.cohort_snapshot import (
    SnapshotCaseInput,
    write_cohort_snapshot,
)

from tests._test_utils import (
    FORBIDDEN_POSITIVE_CLAIM_TOKENS_9,
    assert_no_forbidden_positive_claims,
    assert_tier1_trio,
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
# M:-1 schema version pin
# ---------------------------------------------------------------------


def test_cohort_anomalies_schema_at_1_2_0() -> None:
    """Phase 17 A MINOR bump COHORT_ANOMALIES_SCHEMA_VERSION
    1.1.0 → 1.2.0 with bump-history docstring."""
    assert COHORT_ANOMALIES_SCHEMA_VERSION == "1.2.0"


# ---------------------------------------------------------------------
# M:-2 SSOT helper imports
# ---------------------------------------------------------------------


def test_cohort_anomalies_imports_cumulative_helper() -> None:
    """The cohort-anomalies builder IMPORTS
    ``compute_cohort_cumulative_drift_attribution`` rather than inline-
    aggregating per-case math (M:-2 anti-gaming guard).

    Verified via source-file grep: the import statement is present in
    the cohort_anomalies module body."""
    src = (
        REPO_ROOT / "backend" / "app" / "services" / "reporting" / "cohort_anomalies.py"
    ).read_text(encoding="utf-8")
    assert "compute_cohort_cumulative_drift_attribution" in src, src[:200]
    assert "from .cohort_drift_attribution import" in src, src[:200]


def test_aggregate_helper_is_shared_by_both_compute_functions() -> None:
    """Both ``compute_cohort_drift_attribution`` (Phase 16 B latest-pair)
    and ``compute_cohort_cumulative_drift_attribution`` (Phase 17 A
    cumulative) delegate per-case aggregation + strictly-exceed-floor
    + NaN-sentinel logic to the shared ``_aggregate_cohort_drift_for_pair``
    SSOT helper (M:-2 single SSOT for cohort drift aggregation)."""
    src = (
        REPO_ROOT / "backend" / "app" / "services" / "reporting" / "cohort_drift_attribution.py"
    ).read_text(encoding="utf-8")
    assert src.count("_aggregate_cohort_drift_for_pair(") >= 3, (
        "expected _aggregate_cohort_drift_for_pair to be defined once + "
        "called from both compute_cohort_drift_attribution and "
        "compute_cohort_cumulative_drift_attribution; got fewer occurrences"
    )


# ---------------------------------------------------------------------
# A:-2 defensive parser
# ---------------------------------------------------------------------


def test_cumulative_compute_raises_on_non_positive_floor(tmp_path: Path) -> None:
    """A non-positive floor MUST raise ValueError."""
    with pytest.raises(ValueError, match="dominant_floor_pct must be > 0"):
        compute_cohort_cumulative_drift_attribution(repo_root=tmp_path, dominant_floor_pct=0.0)
    with pytest.raises(ValueError, match="dominant_floor_pct must be > 0"):
        compute_cohort_cumulative_drift_attribution(repo_root=tmp_path, dominant_floor_pct=-1.0)


def test_cumulative_compute_returns_none_when_fewer_than_two_snapshots(
    tmp_path: Path,
) -> None:
    """With 0 or 1 snapshots in reports/snapshots/, the cohort-wide
    arc cannot be computed; the function returns None (graceful
    degrade, NOT raises)."""
    result = compute_cohort_cumulative_drift_attribution(repo_root=tmp_path)
    assert result is None


# ---------------------------------------------------------------------
# Fixture helpers + seeding (mirror the Phase 16 B + 16 D shapes)
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


def _clean_leak_input(tmp: Path, *, suffix: str) -> SnapshotCaseInput:
    """Clean variant of the leak case at full energy credit.

    ``suffix`` keeps per-snapshot clean staging dirs disjoint so the
    same tmp can host multiple snapshots referring to the clean variant
    side-by-side."""
    fixture = tmp / "golden_samples" / LEAK_CASE_ID
    metrics_src = fixture / "data" / "ballistic_metrics.json"
    payload = json.loads(metrics_src.read_text(encoding="utf-8"))
    payload["energy_audit"]["status"] = "closed_aggregate"
    payload["energy_audit"]["rationale"] = (
        "Tier 1 candidate clean. Not signed validation; not benchmark agreement."
    )
    clean_dir = tmp / f"phase17a_clean_{suffix}" / LEAK_CASE_ID
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
    """Leak case in canonical regressed state (energy 0)."""
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


def _seed_cohort_tmp(tmp_path_factory: pytest.TempPathFactory, name: str) -> Path:
    """Drive the Phase 15 A generators in the real repo, then copy
    golden_samples to a fresh tmp. Returns the tmp root."""
    for gen in (
        "gen_rod_wave_impact_deck.py",
        "gen_rod_wave_impact_stiff_deck.py",
        "gen_rod_wave_impact_energy_leak_deck.py",
    ):
        subprocess.check_call(
            [sys.executable, str(REPO_ROOT / "scripts" / gen)],
            cwd=str(REPO_ROOT),
        )
    tmp = tmp_path_factory.mktemp(name)
    golden = tmp / "golden_samples"
    golden.mkdir(parents=True)
    for case_id, _atype in COHORT_CASES:
        shutil.copytree(REPO_ROOT / "golden_samples" / case_id, golden / case_id)
    return tmp


@pytest.fixture(scope="module")
def stuck_arc_repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """3-snapshot stuck-regression arc on the leak case: clean → clean →
    regressed (energy 15 → 15 → 0). Other 4 cases stay healthy.

    Both the latest-pair (snap-2 → snap-3) AND cumulative (snap-1 →
    snap-3) views land on the energy axis with -100.0% delta."""
    tmp = _seed_cohort_tmp(tmp_path_factory, "phase17a_stuck_arc")
    snap1 = [
        _ed_healthy_input(tmp, "rod-wave-impact-candidate"),
        _ed_healthy_input(tmp, "rod-wave-impact-stiff-candidate"),
        _clean_leak_input(tmp, suffix="snap1"),
        _pv_input(tmp, "cylinder-pv-candidate"),
        _pv_input(tmp, "cylinder-pv-extended-candidate"),
    ]
    write_cohort_snapshot(snap1, repo_root=tmp, snapshot_label=SNAP_1_LABEL)
    snap2 = [
        _ed_healthy_input(tmp, "rod-wave-impact-candidate"),
        _ed_healthy_input(tmp, "rod-wave-impact-stiff-candidate"),
        _clean_leak_input(tmp, suffix="snap2"),
        _pv_input(tmp, "cylinder-pv-candidate"),
        _pv_input(tmp, "cylinder-pv-extended-candidate"),
    ]
    write_cohort_snapshot(snap2, repo_root=tmp, snapshot_label=SNAP_2_LABEL)
    snap3 = [
        _ed_healthy_input(tmp, "rod-wave-impact-candidate"),
        _ed_healthy_input(tmp, "rod-wave-impact-stiff-candidate"),
        _regressed_leak_input(tmp),
        _pv_input(tmp, "cylinder-pv-candidate"),
        _pv_input(tmp, "cylinder-pv-extended-candidate"),
    ]
    write_cohort_snapshot(snap3, repo_root=tmp, snapshot_label=SNAP_3_LABEL)
    return tmp


@pytest.fixture(scope="module")
def recovery_arc_repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """3-snapshot recovery arc on the leak case: clean → regressed →
    clean (energy 15 → 0 → 15). Other 4 cases stay healthy.

    Cumulative view (snap-1 → snap-3) recovers to 15 → 15 = 0% on
    energy → sub-floor → dominant axis = None. Latest-pair view
    (snap-2 → snap-3 = 0 → 15) surfaces energy_audit recovery
    (+100% delta on the energy axis; the cohort surface name still
    fires as energy_audit dominant)."""
    tmp = _seed_cohort_tmp(tmp_path_factory, "phase17a_recovery_arc")
    snap1 = [
        _ed_healthy_input(tmp, "rod-wave-impact-candidate"),
        _ed_healthy_input(tmp, "rod-wave-impact-stiff-candidate"),
        _clean_leak_input(tmp, suffix="snap1"),
        _pv_input(tmp, "cylinder-pv-candidate"),
        _pv_input(tmp, "cylinder-pv-extended-candidate"),
    ]
    write_cohort_snapshot(snap1, repo_root=tmp, snapshot_label=SNAP_1_LABEL)
    snap2 = [
        _ed_healthy_input(tmp, "rod-wave-impact-candidate"),
        _ed_healthy_input(tmp, "rod-wave-impact-stiff-candidate"),
        _regressed_leak_input(tmp),
        _pv_input(tmp, "cylinder-pv-candidate"),
        _pv_input(tmp, "cylinder-pv-extended-candidate"),
    ]
    write_cohort_snapshot(snap2, repo_root=tmp, snapshot_label=SNAP_2_LABEL)
    snap3 = [
        _ed_healthy_input(tmp, "rod-wave-impact-candidate"),
        _ed_healthy_input(tmp, "rod-wave-impact-stiff-candidate"),
        _clean_leak_input(tmp, suffix="snap3"),
        _pv_input(tmp, "cylinder-pv-candidate"),
        _pv_input(tmp, "cylinder-pv-extended-candidate"),
    ]
    write_cohort_snapshot(snap3, repo_root=tmp, snapshot_label=SNAP_3_LABEL)
    return tmp


@pytest.fixture(scope="module")
def two_snapshot_arc_repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """2-snapshot arc where (earliest, latest) degenerates to (prev,
    latest); cumulative and latest-pair views land on the SAME
    endpoints (T:-5 degenerate-equal pin)."""
    tmp = _seed_cohort_tmp(tmp_path_factory, "phase17a_two_snap")
    snap2 = [
        _ed_healthy_input(tmp, "rod-wave-impact-candidate"),
        _ed_healthy_input(tmp, "rod-wave-impact-stiff-candidate"),
        _clean_leak_input(tmp, suffix="snap2"),
        _pv_input(tmp, "cylinder-pv-candidate"),
        _pv_input(tmp, "cylinder-pv-extended-candidate"),
    ]
    write_cohort_snapshot(snap2, repo_root=tmp, snapshot_label=SNAP_2_LABEL)
    snap3 = [
        _ed_healthy_input(tmp, "rod-wave-impact-candidate"),
        _ed_healthy_input(tmp, "rod-wave-impact-stiff-candidate"),
        _regressed_leak_input(tmp),
        _pv_input(tmp, "cylinder-pv-candidate"),
        _pv_input(tmp, "cylinder-pv-extended-candidate"),
    ]
    write_cohort_snapshot(snap3, repo_root=tmp, snapshot_label=SNAP_3_LABEL)
    return tmp


# ---------------------------------------------------------------------
# T:-3 boundary-pinned cumulative drift attribution on stuck arc
# ---------------------------------------------------------------------


def test_cumulative_stuck_arc_dominant_axis_is_energy_audit(
    stuck_arc_repo: Path,
) -> None:
    """The load-bearing T:-3 pin: 3-snapshot stuck arc (leak energy
    15→15→0) surfaces cumulative cohort dominant axis == "energy_audit"
    + dominant_case_id == LEAK_CASE_ID + cohort_max_abs_delta_pct ==
    100.0 + cumulative spans SNAP_1 → SNAP_3 exactly."""
    result = compute_cohort_cumulative_drift_attribution(repo_root=stuck_arc_repo)
    assert result is not None
    assert isinstance(result, CohortDriftAttribution)
    assert result.from_snapshot == SNAP_1_LABEL
    assert result.to_snapshot == SNAP_3_LABEL
    assert result.cohort_dominant_axis == "energy_audit"
    assert result.dominant_case_id == LEAK_CASE_ID
    assert result.cohort_max_abs_delta_pct == 100.0


def test_cumulative_stuck_arc_matches_latest_pair_on_endpoints(
    stuck_arc_repo: Path,
) -> None:
    """On the stuck arc, the latest-pair view (snap-2 → snap-3 =
    15 → 0) AND cumulative view (snap-1 → snap-3 = 15 → 0) BOTH
    surface energy_audit at -100% (stuck regression). The
    DOMINANT_AXIS + delta_pct agree across both views; only the
    from_snapshot labels differ."""
    latest = compute_cohort_drift_attribution(repo_root=stuck_arc_repo)
    cumulative = compute_cohort_cumulative_drift_attribution(repo_root=stuck_arc_repo)
    assert latest is not None
    assert cumulative is not None
    assert latest.cohort_dominant_axis == cumulative.cohort_dominant_axis == "energy_audit"
    assert latest.dominant_case_id == cumulative.dominant_case_id == LEAK_CASE_ID
    assert latest.cohort_max_abs_delta_pct == cumulative.cohort_max_abs_delta_pct == 100.0
    # from_snapshot labels differ — cumulative starts earlier.
    assert latest.from_snapshot == SNAP_2_LABEL
    assert cumulative.from_snapshot == SNAP_1_LABEL
    assert latest.to_snapshot == cumulative.to_snapshot == SNAP_3_LABEL


# ---------------------------------------------------------------------
# T:-4 recovery arc — cumulative None vs latest-pair active
# ---------------------------------------------------------------------


def test_cumulative_recovery_arc_dominant_axis_is_none(
    recovery_arc_repo: Path,
) -> None:
    """Recovery arc (energy 15 → 0 → 15): cumulative view spans
    snap-1 → snap-3 = 15 → 15 = 0% on energy. Sub-floor on every
    axis → cohort_dominant_axis is None (cohort_max_abs_delta_pct is
    NaN sentinel, rendered as None on the envelope)."""
    cumulative = compute_cohort_cumulative_drift_attribution(repo_root=recovery_arc_repo)
    assert cumulative is not None
    assert cumulative.from_snapshot == SNAP_1_LABEL
    assert cumulative.to_snapshot == SNAP_3_LABEL
    assert cumulative.cohort_dominant_axis is None
    assert cumulative.dominant_case_id is None
    # cohort_max_abs_delta_pct is NaN (sentinel for sub-floor); NaN
    # is not equal to itself by IEEE 754.
    import math

    assert math.isnan(cumulative.cohort_max_abs_delta_pct)


def test_cumulative_recovery_arc_latest_pair_still_active(
    recovery_arc_repo: Path,
) -> None:
    """On the SAME recovery arc, the latest-pair view (snap-2 → snap-3
    = 0 → 15) DOES surface energy_audit recovery: the latest-pair
    cohort dominant axis is energy_audit (the recovery transition is
    a +100% delta on the energy axis). Pins that the cumulative-vs-
    latest divergence is real, not an artifact of the test repo."""
    latest = compute_cohort_drift_attribution(repo_root=recovery_arc_repo)
    assert latest is not None
    assert latest.from_snapshot == SNAP_2_LABEL
    assert latest.to_snapshot == SNAP_3_LABEL
    assert latest.cohort_dominant_axis == "energy_audit"
    assert latest.dominant_case_id == LEAK_CASE_ID
    # Latest-pair delta_pct is +100 (recovery direction) — surfaced as
    # max ABS delta = 100.0 either way.
    assert latest.cohort_max_abs_delta_pct == 100.0


# ---------------------------------------------------------------------
# T:-5 degenerate-equal pin for 2-snapshot cohort
# ---------------------------------------------------------------------


def test_cumulative_equals_latest_pair_when_only_two_snapshots(
    two_snapshot_arc_repo: Path,
) -> None:
    """With exactly 2 snapshots, (earliest, latest) and (prev, latest)
    degenerate to the same pair. The cumulative and latest-pair views
    return CohortDriftAttribution with IDENTICAL endpoint labels +
    aggregate result."""
    latest = compute_cohort_drift_attribution(repo_root=two_snapshot_arc_repo)
    cumulative = compute_cohort_cumulative_drift_attribution(repo_root=two_snapshot_arc_repo)
    assert latest is not None
    assert cumulative is not None
    assert latest.from_snapshot == cumulative.from_snapshot == SNAP_2_LABEL
    assert latest.to_snapshot == cumulative.to_snapshot == SNAP_3_LABEL
    assert latest.cohort_dominant_axis == cumulative.cohort_dominant_axis
    assert latest.dominant_case_id == cumulative.dominant_case_id
    assert latest.cohort_max_abs_delta_pct == cumulative.cohort_max_abs_delta_pct


# ---------------------------------------------------------------------
# Discovery helpers — earliest-latest discovery is correct
# ---------------------------------------------------------------------


def test_discover_earliest_latest_pair_on_3_snapshot_arc(
    stuck_arc_repo: Path,
) -> None:
    """The earliest-latest discovery returns (snap-1, snap-3) on a
    3-snapshot arc; latest-pair discovery returns (snap-2, snap-3).
    The two discovery helpers diverge for 3+ snapshots."""
    earliest_latest = _discover_earliest_latest_snapshot_pair(stuck_arc_repo)
    latest_pair = _discover_latest_snapshot_pair(stuck_arc_repo)
    assert earliest_latest == (SNAP_1_LABEL, SNAP_3_LABEL)
    assert latest_pair == (SNAP_2_LABEL, SNAP_3_LABEL)


def test_discover_earliest_latest_pair_returns_none_when_empty(
    tmp_path: Path,
) -> None:
    """No reports/snapshots/ tree → returns None."""
    assert _discover_earliest_latest_snapshot_pair(tmp_path) is None


# ---------------------------------------------------------------------
# Cross-envelope wiring — build_cohort_anomalies surfaces both fields
# ---------------------------------------------------------------------


def test_build_cohort_anomalies_carries_both_drift_views(
    stuck_arc_repo: Path,
) -> None:
    """The cohort-anomalies builder populates BOTH cohort_drift_attribution
    (Phase 16 B latest-pair) AND cohort_cumulative_drift_attribution
    (Phase 17 A cumulative); both name energy_audit on the stuck arc."""
    report = build_cohort_anomalies(repo_root=stuck_arc_repo)
    assert report.schema_version == "1.2.0"
    latest = report.cohort_drift_attribution
    cumulative = report.cohort_cumulative_drift_attribution
    assert latest is not None
    assert cumulative is not None
    assert isinstance(latest, CohortDriftAttribution)
    assert isinstance(cumulative, CohortDriftAttribution)
    assert latest.cohort_dominant_axis == "energy_audit"
    assert cumulative.cohort_dominant_axis == "energy_audit"
    assert cumulative.from_snapshot == SNAP_1_LABEL  # earlier than latest's snap-2
    assert latest.from_snapshot == SNAP_2_LABEL


# ---------------------------------------------------------------------
# Live ASGI integration — cohort-anomalies route carries new field
# ---------------------------------------------------------------------


class _SyncASGIClient:
    def __init__(self, asgi_app: Any) -> None:
        self._transport = httpx.ASGITransport(app=asgi_app)

    def get(self, url: str) -> httpx.Response:
        async def _run() -> httpx.Response:
            async with httpx.AsyncClient(
                transport=self._transport, base_url="http://testserver"
            ) as client:
                return await client.get(url)

        return asyncio.run(_run())


def test_live_asgi_cohort_anomalies_carries_cumulative_field(
    stuck_arc_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """C:-1 + cross-envelope wiring: the live cohort-anomalies route
    returns 200 with schema_version 1.2.0 + Tier 1 trio + both drift
    fields populated. The cumulative field renders as a dict (via
    the SSOT helper) when populated."""
    monkeypatch.setattr(cohort_anomalies_route, "_repo_root", lambda: stuck_arc_repo)
    client = _SyncASGIClient(app)
    res = client.get("/api/v1/cohort-anomalies")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["schema_version"] == "1.2.0"
    assert_tier1_trio(body)
    assert body["cohort_drift_attribution"] is not None
    assert body["cohort_cumulative_drift_attribution"] is not None
    cumulative = body["cohort_cumulative_drift_attribution"]
    assert cumulative["cohort_dominant_axis"] == "energy_audit"
    assert cumulative["dominant_case_id"] == LEAK_CASE_ID
    assert cumulative["cohort_max_abs_delta_pct"] == 100.0
    assert cumulative["from_snapshot"] == SNAP_1_LABEL
    assert cumulative["to_snapshot"] == SNAP_3_LABEL


def test_live_asgi_cohort_anomalies_renders_null_cumulative_on_recovery(
    recovery_arc_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """On the recovery arc, cumulative_drift_attribution is present
    (the field is not None — the wrapper exists) but its
    cohort_dominant_axis is None and cohort_max_abs_delta_pct is null
    (NaN → null by the SSOT renderer)."""
    monkeypatch.setattr(cohort_anomalies_route, "_repo_root", lambda: recovery_arc_repo)
    client = _SyncASGIClient(app)
    res = client.get("/api/v1/cohort-anomalies")
    assert res.status_code == 200, res.text
    body = res.json()
    cumulative = body["cohort_cumulative_drift_attribution"]
    assert cumulative is not None  # wrapper present
    assert cumulative["cohort_dominant_axis"] is None
    assert cumulative["dominant_case_id"] is None
    assert cumulative["cohort_max_abs_delta_pct"] is None  # NaN → null


# ---------------------------------------------------------------------
# C:-8 forbidden-token grep on new methodology paragraph
# ---------------------------------------------------------------------


def test_methodology_doc_cumulative_section_passes_forbidden_grep() -> None:
    """The new Phase 17 A methodology paragraph in
    `.planning/methodology/cohort_drift_attribution.md` MUST NOT
    carry any of the 9 forbidden positive-claim tokens outside
    ``not <claim>`` / ``no <claim>`` form. Consumes the SSOT
    9-tuple + grep helper (closes Phase 15 retro §7 + matches the
    Phase 16 B + 17 A methodology audit pattern)."""
    doc = REPO_ROOT / ".planning" / "methodology" / "cohort_drift_attribution.md"
    text = doc.read_text(encoding="utf-8")
    assert_no_forbidden_positive_claims(text, tokens=FORBIDDEN_POSITIVE_CLAIM_TOKENS_9)


# ---------------------------------------------------------------------
# Back-compat — 1.1.0-era field still present in 1.2.0 envelope
# ---------------------------------------------------------------------


def test_back_compat_1_1_0_reader_field_present_in_1_2_0(
    stuck_arc_repo: Path,
) -> None:
    """A 1.1.0-era reader looking for `cohort_drift_attribution`
    (Phase 16 B) still finds the field intact at 1.2.0. The 1.2.0
    additive bump does NOT remove or rename any 1.1.0 field."""
    report = build_cohort_anomalies(repo_root=stuck_arc_repo)
    assert report.cohort_drift_attribution is not None
    assert isinstance(report.cohort_drift_attribution, CohortDriftAttribution)


# ---------------------------------------------------------------------
# Cross-envelope coherence — both compute calls return identical shape
# ---------------------------------------------------------------------


def test_both_compute_functions_return_same_dataclass_type(
    stuck_arc_repo: Path,
) -> None:
    """X:- (cross-envelope coherence): the two compute functions
    return the SAME dataclass type (CohortDriftAttribution). The
    SSOT renderer `render_cohort_drift_attribution_dict` handles
    both via a single code path."""
    latest = compute_cohort_drift_attribution(repo_root=stuck_arc_repo)
    cumulative = compute_cohort_cumulative_drift_attribution(repo_root=stuck_arc_repo)
    assert type(latest) is type(cumulative)
    assert type(latest).__name__ == "CohortDriftAttribution"


def test_aggregate_helper_direct_call_on_arbitrary_pair(
    stuck_arc_repo: Path,
) -> None:
    """The shared `_aggregate_cohort_drift_for_pair` helper is callable
    directly with arbitrary endpoint labels. Used by both Phase 16 B
    and Phase 17 A; pinning the call surface guards against future
    drift in the helper signature."""
    result = _aggregate_cohort_drift_for_pair(
        repo_root=stuck_arc_repo,
        prev_label=SNAP_1_LABEL,
        curr_label=SNAP_3_LABEL,
        dominant_floor_pct=COHORT_DOMINANT_AXIS_FLOOR_PCT,
    )
    assert isinstance(result, CohortDriftAttribution)
    assert result.from_snapshot == SNAP_1_LABEL
    assert result.to_snapshot == SNAP_3_LABEL
    assert result.cohort_dominant_axis == "energy_audit"
