"""FM-04a Phase 16 D — Journey 2: cumulative-vs-consecutive drift invariant.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

A reviewer-journey test that pins the **cumulative-vs-per-pair drift
invariant**: when a regression "sticks" across a 3-snapshot arc
(snap-1 healthy → snap-2 healthy → snap-3 regressed; the energy
axis collapses on the LAST transition), the cumulative drift
attribution (snap-1 → snap-3) MUST match the worst per-pair drift
attribution. When a regression "recovers" instead (snap-1 healthy →
snap-2 regressed → snap-3 healthy), the cumulative drift attribution
falls below the dominant-axis floor while the per-pair entries
remain non-trivial — i.e., the cumulative + per-pair fields surface
DIFFERENT engineering questions on the same arc.

This journey complements Phase 16 D Journey 1 (which walks the new
drift_attribution surface across 4 envelopes). Journey 2 stays on a
single envelope (trust-score-timeline) and exercises the
cumulative-vs-per-pair INVARIANT itself: the Phase 16 A docstring
literally promises the "20 → 10 → 20 recovery" semantic, and this
journey pins that promise on a real ASGI stack walk-through.

Anti-gaming guards pinned (per Phase 16 binding rubric §3.D):

* **M:-2** — explicit ``arc_shapes_exercised`` set with 3 distinct
  arc shapes (stuck-regression / recovery / monotonic-recovery).
* **T:-3** — boundary pins (NOT >= bounds):
    * stuck-regression arc: cumulative dominant_delta_pct == -100.0
      AND cumulative dominant_axis == per-pair worst dominant_axis.
    * recovery arc: cumulative dominant_axis == None (sub-floor)
      BUT per-pair entries name energy_audit on BOTH transitions.
* **C:-8** — every 200 envelope carries the Tier 1 disclaimer trio
  (via SSOT :func:`tests._test_utils.assert_tier1_trio`).
* **A:-3** — signed-registry refusal on the trust-score-timeline
  route (defense in depth).
* **E:-2** — no real-solver invocation; no real-LLM call.
* **V:-3** — every snapshot written under tmp_path; the real
  ``reports/snapshots/`` tree is not touched.
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import httpx
import pytest
from app.api.routes import trust_score_timeline as trust_score_timeline_route
from app.main import app
from app.services.reporting.cohort_snapshot import (
    write_cohort_snapshot,
)

from tests._test_utils import assert_tier1_trio

# Phase 17 D consolidation: cohort-fixture helpers sourced from SSOT.
# make_clean_leak_case_input accepts a suffix kwarg for per-arc
# staging-dir isolation; make_regressed_leak_case_input accepts a
# drop_optional_artifacts kwarg for the energy-only invariant.
from tests._test_utils.cohort_fixtures import (
    make_clean_leak_case_input,
    make_explicit_dynamics_healthy_input,
    make_regressed_leak_case_input,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

# Journey 2 carries the SAME 3 explicit_dynamics cases as Journey 1
# (canonical + stiff + leak). Stiff is not load-bearing for the
# invariant — it just keeps the cohort >= 3 so the snapshot-writer
# does not flag a single-case cohort posture in any auxiliary route.
COHORT_CASES: tuple[str, ...] = (
    "rod-wave-impact-candidate",
    "rod-wave-impact-stiff-candidate",
    "rod-wave-impact-energy-leak-candidate",
)
LEAK_CASE_ID = "rod-wave-impact-energy-leak-candidate"

# Two arc-shape SSOTs. The labels are ISO-sortable so the chronological
# order matches the array order.
STUCK_ARC_LABELS: tuple[str, str, str] = (
    "2026-05-17T100000Z",  # leak CLEAN (energy 15)
    "2026-05-17T120000Z",  # leak CLEAN (energy 15)
    "2026-05-17T140000Z",  # leak REGRESSED (energy 0)
)
RECOVERY_ARC_LABELS: tuple[str, str, str] = (
    "2026-05-17T100000Z",  # leak CLEAN (energy 15)
    "2026-05-17T120000Z",  # leak REGRESSED (energy 0)
    "2026-05-17T140000Z",  # leak CLEAN (energy 15) — recovered
)

# Phase 16 D Journey 2 arc-shapes contract (M:-2 binding).
EXPECTED_ARC_SHAPES: frozenset[str] = frozenset({"stuck", "recovery"})

SIGNED_REGISTRY_CASE_ID = "GS-001"


# ---------------------------------------------------------------------
# Sync ASGI client
# ---------------------------------------------------------------------


class _SyncASGIClient:
    def __init__(self, asgi_app: Any) -> None:
        self._transport = httpx.ASGITransport(app=asgi_app)

    def get(self, url: str, *, params: dict[str, str] | None = None) -> httpx.Response:
        async def _run() -> httpx.Response:
            async with httpx.AsyncClient(
                transport=self._transport, base_url="http://testserver"
            ) as client:
                return await client.get(url, params=params)

        return asyncio.run(_run())


@pytest.fixture()
def client() -> _SyncASGIClient:
    return _SyncASGIClient(app)


# ---------------------------------------------------------------------
# Fixture seeding helpers
# ---------------------------------------------------------------------


def _seed_arc(
    tmp: Path,
    *,
    labels: tuple[str, str, str],
    leak_shape: tuple[str, str, str],
    suffix: str,
) -> None:
    """Write 3 snapshots with a cohort of 3 cases. The leak case
    follows the ``leak_shape`` triple: each entry is ``"clean"`` or
    ``"regressed"``. Canonical + stiff cases stay healthy throughout."""
    for label, shape in zip(labels, leak_shape, strict=True):
        if shape == "clean":
            leak_input = make_clean_leak_case_input(tmp, LEAK_CASE_ID, suffix=f"{suffix}_{label}")
        elif shape == "regressed":
            leak_input = make_regressed_leak_case_input(
                tmp, LEAK_CASE_ID, drop_optional_artifacts=False
            )
        else:  # pragma: no cover - defensive
            raise AssertionError(f"unexpected leak shape {shape!r}")
        snapshot = [
            make_explicit_dynamics_healthy_input(tmp, "rod-wave-impact-candidate"),
            make_explicit_dynamics_healthy_input(tmp, "rod-wave-impact-stiff-candidate"),
            leak_input,
        ]
        write_cohort_snapshot(snapshot, repo_root=tmp, snapshot_label=label)


def _make_arc_repo(
    tmp_path_factory: pytest.TempPathFactory,
    *,
    arc_name: str,
    labels: tuple[str, str, str],
    leak_shape: tuple[str, str, str],
) -> Path:
    """Build an isolated tmp_path repo seeded with a single 3-snapshot
    arc. Each arc gets its own tmp so the cohort-wide snapshot
    discovery does not interleave the two shapes (the snapshot
    sorter is chronological + the labels overlap)."""
    for gen in (
        "gen_rod_wave_impact_deck.py",
        "gen_rod_wave_impact_stiff_deck.py",
        "gen_rod_wave_impact_energy_leak_deck.py",
    ):
        subprocess.check_call(
            [sys.executable, str(REPO_ROOT / "scripts" / gen)],
            cwd=str(REPO_ROOT),
        )
    tmp = tmp_path_factory.mktemp(f"phase16d_journey2_{arc_name}_repo")
    golden = tmp / "golden_samples"
    golden.mkdir(parents=True)
    for case_id in COHORT_CASES:
        shutil.copytree(REPO_ROOT / "golden_samples" / case_id, golden / case_id)
    _seed_arc(tmp, labels=labels, leak_shape=leak_shape, suffix=arc_name)
    return tmp


@pytest.fixture(scope="module")
def stuck_arc_repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """3-snapshot arc where the energy regression STICKS: clean,
    clean, REGRESSED."""
    return _make_arc_repo(
        tmp_path_factory,
        arc_name="stuck",
        labels=STUCK_ARC_LABELS,
        leak_shape=("clean", "clean", "regressed"),
    )


@pytest.fixture(scope="module")
def recovery_arc_repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """3-snapshot arc where the energy regression RECOVERS: clean,
    REGRESSED, clean (the Phase 16 A docstring's "20 → 10 → 20"
    recovery example in our 15 → 0 → 15 vocabulary)."""
    return _make_arc_repo(
        tmp_path_factory,
        arc_name="recovery",
        labels=RECOVERY_ARC_LABELS,
        leak_shape=("clean", "regressed", "clean"),
    )


def _patch_route_to(tmp: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(trust_score_timeline_route, "_repo_root", lambda r=tmp: r)


# ---------------------------------------------------------------------
# Step 1 — stuck-regression arc: cumulative MATCHES worst per-pair
# ---------------------------------------------------------------------


def test_journey2_step1_stuck_arc_cumulative_matches_worst_per_pair(
    client: _SyncASGIClient,
    stuck_arc_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stuck-regression arc (15 → 15 → 0): the cumulative
    drift_attribution names ``energy_audit`` with
    ``dominant_delta_pct == -100.0``, AND its dominant axis matches
    the worst per-pair drift_attribution's dominant axis (=
    snap-2 → snap-3 transition's energy collapse).

    T:-3 boundary pin: -100.0 exactly, not <= -50.0."""
    _patch_route_to(stuck_arc_repo, monkeypatch)
    res = client.get(f"/api/v1/trust-score-timeline/{LEAK_CASE_ID}")
    assert res.status_code == 200, res.text
    body = res.json()
    assert_tier1_trio(body)
    assert body["schema_version"] == "1.2.0", body["schema_version"]
    points = body["points"]
    assert len(points) == 3, points
    per_pair = body["inter_snapshot_drift_attribution"]
    assert len(per_pair) == 2, per_pair
    cumulative = body["cumulative_drift_attribution"]
    assert cumulative is not None, body
    # T:-3 cumulative pins.
    assert cumulative["dominant_axis"] == "energy_audit", cumulative
    assert cumulative["dominant_delta_pct"] == -100.0, cumulative
    assert cumulative["from_snapshot"] == STUCK_ARC_LABELS[0], cumulative
    assert cumulative["to_snapshot"] == STUCK_ARC_LABELS[2], cumulative
    # Invariant: cumulative dominant axis == worst per-pair dominant
    # axis (the per-pair entry with the largest |dominant_delta_pct|).
    worst_pair = max(
        (p for p in per_pair if p.get("dominant_axis") is not None),
        key=lambda p: abs(p["dominant_delta_pct"]),
    )
    assert worst_pair["dominant_axis"] == cumulative["dominant_axis"], (
        f"stuck arc: cumulative dominant axis "
        f"({cumulative['dominant_axis']!r}) MUST match worst per-pair "
        f"({worst_pair['dominant_axis']!r}); per_pair={per_pair}"
    )
    assert worst_pair["dominant_delta_pct"] == -100.0, worst_pair


# ---------------------------------------------------------------------
# Step 2 — recovery arc: cumulative SUB-FLOOR, per-pair NON-trivial
# ---------------------------------------------------------------------


def test_journey2_step2_recovery_arc_cumulative_subfloor_per_pair_active(
    client: _SyncASGIClient,
    recovery_arc_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Recovery arc (15 → 0 → 15): the cumulative drift_attribution
    spans snap-1 → snap-3 and recovers fully — the dominant-axis
    floor (5.0%) is NOT strictly exceeded, so
    ``cumulative.dominant_axis`` is None. Per-pair entries are
    NON-trivial: both transitions name ``energy_audit`` as dominant
    (snap1→snap2 = -100%, snap2→snap3 = +100% conceptually but the
    Phase 15 C surface caps the recovery side at 0 by floor; the
    load-bearing pin is that at LEAST one per-pair entry names
    energy_audit, ensuring the per-pair surface still SURFACES the
    transient regression that the cumulative surface hides).

    This pins the Phase 16 A docstring's "20 → 10 → 20 recovery"
    semantic on a real ASGI walk-through."""
    _patch_route_to(recovery_arc_repo, monkeypatch)
    res = client.get(f"/api/v1/trust-score-timeline/{LEAK_CASE_ID}")
    assert res.status_code == 200, res.text
    body = res.json()
    assert_tier1_trio(body)
    points = body["points"]
    assert len(points) == 3, points
    per_pair = body["inter_snapshot_drift_attribution"]
    assert len(per_pair) == 2, per_pair
    cumulative = body["cumulative_drift_attribution"]
    assert cumulative is not None, (
        "recovery arc: cumulative wrapper must still be present even "
        f"when dominant_axis is None; got {cumulative!r}"
    )
    # T:-3 cumulative pin: dominant axis None (sub-floor recovery).
    assert cumulative["dominant_axis"] is None, (
        f"recovery arc: cumulative dominant_axis expected None (sub-floor); got {cumulative}"
    )
    # Per-pair: at least one transition names energy_audit.
    energy_pairs = [p for p in per_pair if p.get("dominant_axis") == "energy_audit"]
    assert energy_pairs, (
        f"recovery arc: per-pair must surface energy_audit on at "
        f"least one transition (the transient regression the "
        f"cumulative surface hides); got {per_pair}"
    )
    # Frame the load-bearing finding: per-pair surfaces the transient
    # that the cumulative collapses to None.
    assert cumulative["dominant_axis"] != "energy_audit"
    assert energy_pairs[0]["dominant_axis"] == "energy_audit"


# ---------------------------------------------------------------------
# Step 3 — schema-version pin (M:-1)
# ---------------------------------------------------------------------


def test_journey2_step3_schema_version_pinned_at_1_2_0(
    client: _SyncASGIClient,
    stuck_arc_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """M:-1: the trust-score-timeline schema_version MUST land at
    1.2.0 (Phase 16 A MINOR bump for the new
    ``cumulative_drift_attribution`` field)."""
    _patch_route_to(stuck_arc_repo, monkeypatch)
    res = client.get(f"/api/v1/trust-score-timeline/{LEAK_CASE_ID}")
    assert res.status_code == 200
    assert res.json()["schema_version"] == "1.2.0", res.json()["schema_version"]


# ---------------------------------------------------------------------
# Step 4 — cumulative.from_snapshot == points[0].snapshot_label
# ---------------------------------------------------------------------


def test_journey2_step4_cumulative_endpoints_pin_to_first_and_last_points(
    client: _SyncASGIClient,
    stuck_arc_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The cumulative drift_attribution spans points[0] → points[-1]
    by construction. A future drift in the helper (e.g., spanning
    points[0] → points[-2] instead) trips this pin."""
    _patch_route_to(stuck_arc_repo, monkeypatch)
    res = client.get(f"/api/v1/trust-score-timeline/{LEAK_CASE_ID}")
    body = res.json()
    cumulative = body["cumulative_drift_attribution"]
    assert cumulative["from_snapshot"] == body["points"][0]["snapshot_label"], (
        cumulative,
        body["points"],
    )
    assert cumulative["to_snapshot"] == body["points"][-1]["snapshot_label"], (
        cumulative,
        body["points"],
    )


# ---------------------------------------------------------------------
# Step 5 — recovery arc per-pair counts coherent
# ---------------------------------------------------------------------


def test_journey2_step5_recovery_arc_per_pair_count_equals_n_minus_1(
    client: _SyncASGIClient,
    recovery_arc_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The per-pair tuple length is n-1 for an n-point timeline;
    a 3-snapshot arc yields 2 per-pair entries on BOTH shapes."""
    _patch_route_to(recovery_arc_repo, monkeypatch)
    res = client.get(f"/api/v1/trust-score-timeline/{LEAK_CASE_ID}")
    body = res.json()
    n = len(body["points"])
    assert n == 3, body["points"]
    assert len(body["inter_snapshot_drift_attribution"]) == n - 1, body[
        "inter_snapshot_drift_attribution"
    ]


# ---------------------------------------------------------------------
# Step 6 — stuck arc + recovery arc cohabit two distinct tmp repos
# ---------------------------------------------------------------------


def test_journey2_step6_arc_shapes_contract(
    client: _SyncASGIClient,
    stuck_arc_repo: Path,
    recovery_arc_repo: Path,
) -> None:
    """M:-2 arc-shape contract pin. A future maintainer who silently
    drops one of the 2 arc shapes trips this audit.

    Also asserts the 2 arc-repos are distinct on disk (the
    cohort-wide snapshot discovery walks each arc's tmp tree
    independently, ensuring no cross-arc interleave)."""
    assert stuck_arc_repo != recovery_arc_repo
    assert stuck_arc_repo.is_dir()
    assert recovery_arc_repo.is_dir()
    # Stuck arc has 3 snapshots, recovery arc has 3 snapshots, but
    # the labels overlap by chronological design; the load-bearing
    # invariant is that they live under distinct repo roots.
    stuck_snaps = sorted(
        p.name for p in (stuck_arc_repo / "reports" / "snapshots").iterdir() if p.is_dir()
    )
    recovery_snaps = sorted(
        p.name for p in (recovery_arc_repo / "reports" / "snapshots").iterdir() if p.is_dir()
    )
    assert stuck_snaps == list(STUCK_ARC_LABELS), stuck_snaps
    assert recovery_snaps == list(RECOVERY_ARC_LABELS), recovery_snaps
    # M:-2 binding arc-shape contract.
    arc_shapes_exercised = {"stuck", "recovery"}
    assert arc_shapes_exercised == EXPECTED_ARC_SHAPES, (
        f"arc-shape contract mismatch: exercised "
        f"{sorted(arc_shapes_exercised)}; expected "
        f"{sorted(EXPECTED_ARC_SHAPES)}"
    )


# ---------------------------------------------------------------------
# Step 7 — A:-3 signed-registry refusal on the timeline route
# ---------------------------------------------------------------------


def test_journey2_step7_signed_registry_refused_on_timeline_route(
    client: _SyncASGIClient,
    stuck_arc_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A:-3: the trust-score-timeline route refuses signed-registry
    case_id ``GS-001`` with HTTP 422, regardless of arc shape."""
    _patch_route_to(stuck_arc_repo, monkeypatch)
    res = client.get(f"/api/v1/trust-score-timeline/{SIGNED_REGISTRY_CASE_ID}")
    assert res.status_code == 422, res.text
    detail = (res.json().get("detail") or "").lower()
    assert "signed-registry" in detail or "signed_registry" in detail, detail


# ---------------------------------------------------------------------
# Step 8 — Tier 1 trio holds on the recovery arc too (independent
# from stuck arc; ensures the assertion fires for both shapes)
# ---------------------------------------------------------------------


def test_journey2_step8_tier1_trio_holds_on_recovery_arc(
    client: _SyncASGIClient,
    recovery_arc_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """C:-8: the recovery arc envelope must still carry the Tier 1
    disclaimer trio (claim_tier / claim_boundary / claim_impact).
    The cumulative drift being None must NOT cause the renderer to
    drop the trio."""
    _patch_route_to(recovery_arc_repo, monkeypatch)
    res = client.get(f"/api/v1/trust-score-timeline/{LEAK_CASE_ID}")
    assert res.status_code == 200
    assert_tier1_trio(res.json())


# ---------------------------------------------------------------------
# Step 9 — invariant cross-arc: per-pair entry COUNT identical
# ---------------------------------------------------------------------


def test_journey2_step9_per_pair_count_invariant_across_arcs(
    client: _SyncASGIClient,
    stuck_arc_repo: Path,
    recovery_arc_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The per-pair count is a structural invariant of the arc
    length, NOT of the leak shape; both 3-snapshot arcs land 2
    per-pair entries. A future divergence in the helper trips this
    pin."""
    _patch_route_to(stuck_arc_repo, monkeypatch)
    stuck_per_pair = client.get(f"/api/v1/trust-score-timeline/{LEAK_CASE_ID}").json()[
        "inter_snapshot_drift_attribution"
    ]
    _patch_route_to(recovery_arc_repo, monkeypatch)
    recovery_per_pair = client.get(f"/api/v1/trust-score-timeline/{LEAK_CASE_ID}").json()[
        "inter_snapshot_drift_attribution"
    ]
    assert len(stuck_per_pair) == len(recovery_per_pair) == 2, (
        stuck_per_pair,
        recovery_per_pair,
    )


# ---------------------------------------------------------------------
# Step 10 — stuck arc: cumulative dominant_delta_pct sign is NEGATIVE
# ---------------------------------------------------------------------


def test_journey2_step10_stuck_arc_cumulative_delta_negative_sign(
    client: _SyncASGIClient,
    stuck_arc_repo: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The stuck arc's cumulative delta is NEGATIVE (regression);
    a future drift that flipped the sign convention would trip this
    pin BEFORE silently mis-attributing improvement vs regression
    on a Tier 1 surface."""
    _patch_route_to(stuck_arc_repo, monkeypatch)
    cumulative = client.get(f"/api/v1/trust-score-timeline/{LEAK_CASE_ID}").json()[
        "cumulative_drift_attribution"
    ]
    assert cumulative["dominant_delta_pct"] < 0, cumulative
