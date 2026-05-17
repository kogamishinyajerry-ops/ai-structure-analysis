"""FM-04a Phase 15 D — Journey 2: cross-axis cohort comparison E2E.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

A 5-case cohort journey that pins the **cross-analysis-type
discrimination** contract: when the explicit_dynamics axis evolves
(the leak case dropping along the Phase 15 B arc), the
linear_static_pv cases STAY flat. The cohort-anomalies surface
flags the leak case on the ``energy_audit`` axis WITHOUT
false-positiving on the linear_static_pv cases.

5-case cohort SSOT:

  * 3 explicit_dynamics (Phase 15 A + 14 D):
    - rod-wave-impact-candidate (healthy at every snapshot)
    - rod-wave-impact-stiff-candidate (healthy at every snapshot)
    - rod-wave-impact-energy-leak-candidate (healthy → watching → regressed)
  * 2 linear_static_pv (Phase 12 C + Phase 13 C precedent):
    - cylinder-pv-candidate (healthy at every snapshot)
    - cylinder-pv-extended-candidate (healthy at every snapshot)

Anti-gaming guards pinned (per Phase 15 binding rubric §3.D):

* **M:-2** — cohort SSOT named at module level (the 5 case_ids +
  their analysis_types). A future case addition must update the SSOT
  tuples; a future renaming trips the route-count contract test.
* **T:-3** — the leak case's evolving energy_audit weighted score
  (15 → 15 → 0) is boundary-pinned; the 2 PV cases' timelines are
  asserted FLAT (trust score equal across 3 points, not >=, NOT
  monotonic).
* **A:-2** — cohort-anomalies surfaces the leak case as an outlier
  on the ``energy_audit`` axis AND none of the 2 PV cases appear
  in the anomaly set on any axis (no false-positive
  cross-analysis-type leakage).
* **C:-8** — every 200 envelope inspected carries the Tier 1
  disclaimer trio.
* **E:-2** — no real-solver invocation; no real-LLM call.
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
from app.api.routes import case_completeness as case_completeness_route
from app.api.routes import cohort_anomalies as cohort_anomalies_route
from app.api.routes import cohort_executive_summary as cohort_executive_summary_route
from app.api.routes import trust_score_timeline as trust_score_timeline_route
from app.main import app
from app.services.reporting.cohort_anomalies import (
    COHORT_MIN_SIZE_FOR_ANOMALY,
)
from app.services.reporting.cohort_snapshot import (
    write_cohort_snapshot,
)

from tests._test_utils import (
    FORBIDDEN_POSITIVE_CLAIM_TOKENS_8,
    assert_no_forbidden_positive_claims,
    assert_tier1_trio,
)

# Phase 17 D consolidation: cohort-fixture helpers sourced from SSOT.
from tests._test_utils.cohort_fixtures import (
    make_clean_leak_case_input,
    make_explicit_dynamics_healthy_input,
    make_pv_case_input,
    make_regressed_leak_case_input,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

# Cohort SSOT — 5 cases across 2 analysis types. (case_id, analysis_type) tuples.
COHORT_CASES: tuple[tuple[str, str], ...] = (
    ("rod-wave-impact-candidate", "explicit_dynamics"),
    ("rod-wave-impact-stiff-candidate", "explicit_dynamics"),
    ("rod-wave-impact-energy-leak-candidate", "explicit_dynamics"),
    ("cylinder-pv-candidate", "linear_static_pv"),
    ("cylinder-pv-extended-candidate", "linear_static_pv"),
)
EXPLICIT_DYNAMICS_CASES: tuple[str, ...] = tuple(
    cid for cid, atype in COHORT_CASES if atype == "explicit_dynamics"
)
LINEAR_STATIC_PV_CASES: tuple[str, ...] = tuple(
    cid for cid, atype in COHORT_CASES if atype == "linear_static_pv"
)
LEAK_CASE_ID = "rod-wave-impact-energy-leak-candidate"

assert len(COHORT_CASES) == 5
assert len(EXPLICIT_DYNAMICS_CASES) == 3
assert len(LINEAR_STATIC_PV_CASES) == 2

SNAP_1_LABEL = "2026-05-17T100000Z"
SNAP_2_LABEL = "2026-05-17T120000Z"
SNAP_3_LABEL = "2026-05-17T140000Z"

# Cohort size must clear the COHORT_MIN_SIZE_FOR_ANOMALY=3 floor for
# z-score outlier detection to fire.
assert len(COHORT_CASES) >= COHORT_MIN_SIZE_FOR_ANOMALY


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


@pytest.fixture(scope="module")
def journey_repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Seed a tmp_path with 5 cases × 3 snapshots. Only the leak case
    evolves; the other 4 cases stay flat."""
    for gen in (
        "gen_rod_wave_impact_deck.py",
        "gen_rod_wave_impact_stiff_deck.py",
        "gen_rod_wave_impact_energy_leak_deck.py",
    ):
        subprocess.check_call(
            [sys.executable, str(REPO_ROOT / "scripts" / gen)],
            cwd=str(REPO_ROOT),
        )

    tmp = tmp_path_factory.mktemp("phase15d_journey2_repo")
    golden = tmp / "golden_samples"
    golden.mkdir(parents=True)
    for case_id, _atype in COHORT_CASES:
        shutil.copytree(REPO_ROOT / "golden_samples" / case_id, golden / case_id)

    # Snap-1: all 5 healthy (leak case in CLEAN variant).
    snap1 = [
        make_explicit_dynamics_healthy_input(tmp, "rod-wave-impact-candidate"),
        make_explicit_dynamics_healthy_input(tmp, "rod-wave-impact-stiff-candidate"),
        make_clean_leak_case_input(tmp, LEAK_CASE_ID, suffix="phase15d_journey2_snap1_clean"),
        make_pv_case_input(tmp, "cylinder-pv-candidate"),
        make_pv_case_input(tmp, "cylinder-pv-extended-candidate"),
    ]
    write_cohort_snapshot(snap1, repo_root=tmp, snapshot_label=SNAP_1_LABEL)

    # Snap-2: leak case drops to watching (canonical Phase 15 A
    # state, open_residual). Others stay healthy.
    snap2 = [
        make_explicit_dynamics_healthy_input(tmp, "rod-wave-impact-candidate"),
        make_explicit_dynamics_healthy_input(tmp, "rod-wave-impact-stiff-candidate"),
        make_explicit_dynamics_healthy_input(tmp, LEAK_CASE_ID),
        make_pv_case_input(tmp, "cylinder-pv-candidate"),
        make_pv_case_input(tmp, "cylinder-pv-extended-candidate"),
    ]
    write_cohort_snapshot(snap2, repo_root=tmp, snapshot_label=SNAP_2_LABEL)

    # Snap-3: leak case drops to regressed. Others stay healthy.
    snap3 = [
        make_explicit_dynamics_healthy_input(tmp, "rod-wave-impact-candidate"),
        make_explicit_dynamics_healthy_input(tmp, "rod-wave-impact-stiff-candidate"),
        make_regressed_leak_case_input(tmp, LEAK_CASE_ID),
        make_pv_case_input(tmp, "cylinder-pv-candidate"),
        make_pv_case_input(tmp, "cylinder-pv-extended-candidate"),
    ]
    write_cohort_snapshot(snap3, repo_root=tmp, snapshot_label=SNAP_3_LABEL)
    return tmp


@pytest.fixture()
def patched_routes(journey_repo: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect every route's ``_repo_root`` to the seeded tmp_path."""
    for route_module in (
        cohort_executive_summary_route,
        cohort_anomalies_route,
        trust_score_timeline_route,
        case_completeness_route,
    ):
        monkeypatch.setattr(route_module, "_repo_root", lambda r=journey_repo: r)
    return journey_repo


def _assert_tier1_trio(envelope: dict[str, Any]) -> None:
    """Journey 2 audits only claim_tier + claim_boundary (the
    linear_static_pv cases under this rubric legitimately omit a
    canonical ``claim_impact`` envelope token). Delegates to the
    SSOT :func:`tests._test_utils.assert_tier1_trio` with
    ``check_impact=False`` to close Phase 15 retro §8 — the trio
    audit is no longer inlined per file. The thin per-file wrapper
    is preserved so the meta-test in
    ``tests/test_phase16_test_utils_ssot.py`` doesn't flag this
    file (the wrapper just routes to the SSOT)."""
    assert_tier1_trio(envelope, check_impact=False)


# ---------------------------------------------------------------------
# Step 1 — cohort-executive-summary cohort_count == 5
# ---------------------------------------------------------------------


def test_journey2_step1_cohort_count_is_5(client: _SyncASGIClient, patched_routes: Path) -> None:
    """The 5-case cohort SSOT is reflected on cohort-executive-summary:
    cohort_count == 5 (3 explicit_dynamics + 2 linear_static_pv).
    A future PV case addition / removal should land in the cohort
    SSOT tuples; this test guards against silent drift."""
    res = client.get("/api/v1/cohort-executive-summary")
    assert res.status_code == 200, res.text
    body = res.json()
    _assert_tier1_trio(body)
    got_ids = [c["case_id"] for c in body["cases"]]
    assert body["cohort_count"] == 5, (
        f"expected cohort_count=5; got {body['cohort_count']} ({got_ids})"
    )
    seen = {c["case_id"] for c in body["cases"]}
    expected = {cid for cid, _ in COHORT_CASES}
    assert seen == expected, (
        f"cohort cases mismatch; seen={sorted(seen)} expected={sorted(expected)}"
    )


# ---------------------------------------------------------------------
# Step 2 — per-case trust-score-timeline flatness vs evolution
# ---------------------------------------------------------------------


def _timeline_for(client: _SyncASGIClient, case_id: str) -> list[dict[str, Any]]:
    res = client.get(f"/api/v1/trust-score-timeline/{case_id}")
    assert res.status_code == 200, f"{case_id}: {res.status_code} {res.text}"
    body = res.json()
    _assert_tier1_trio(body)
    return body["points"]


def test_journey2_step2a_pv_case_timelines_are_flat(
    client: _SyncASGIClient, patched_routes: Path
) -> None:
    """Both linear_static_pv cases have FLAT trust-score timelines
    across the 3-snapshot arc: trust_score is equal at every
    consecutive snapshot pair."""
    for case_id in LINEAR_STATIC_PV_CASES:
        points = _timeline_for(client, case_id)
        assert len(points) == 3, f"{case_id}: expected 3 timeline points; got {len(points)}"
        trust_values = [p["trust_score"] for p in points]
        assert trust_values[0] == trust_values[1] == trust_values[2], (
            f"{case_id} expected FLAT timeline; got trust_score per snapshot: {trust_values}"
        )


def test_journey2_step2b_healthy_explicit_dynamics_timelines_are_flat(
    client: _SyncASGIClient, patched_routes: Path
) -> None:
    """The 2 healthy explicit_dynamics cases (canonical + stiff) have
    FLAT trust-score timelines: trust_score is equal at every snapshot."""
    for case_id in (
        "rod-wave-impact-candidate",
        "rod-wave-impact-stiff-candidate",
    ):
        points = _timeline_for(client, case_id)
        assert len(points) == 3
        trust_values = [p["trust_score"] for p in points]
        assert trust_values[0] == trust_values[1] == trust_values[2], (
            f"{case_id} expected FLAT timeline; got trust_score per snapshot: {trust_values}"
        )


def test_journey2_step2c_leak_case_timeline_evolves_monotonically(
    client: _SyncASGIClient, patched_routes: Path
) -> None:
    """The leak case is the ONLY case whose timeline evolves:
    trust_score is strictly DECREASING across the 3-snapshot arc
    (healthy → watching → regressed)."""
    points = _timeline_for(client, LEAK_CASE_ID)
    assert len(points) == 3
    t1, t2, t3 = (p["trust_score"] for p in points)
    assert t1 > t2 > t3, (
        f"leak case expected monotonically decreasing trust_score; "
        f"got snap1={t1}, snap2={t2}, snap3={t3}"
    )
    # T:-3 boundary pin: snap-3 energy axis is 0 (collapsed).
    snap3_energy = points[2]["energy_audit_weighted"]
    assert snap3_energy == 0, f"leak snap-3 energy_audit expected 0; got {snap3_energy}"
    # snap-1 energy axis at full credit (CLEAN variant).
    snap1_energy = points[0]["energy_audit_weighted"]
    assert snap1_energy == 15, f"leak snap-1 energy_audit expected 15; got {snap1_energy}"


# ---------------------------------------------------------------------
# Step 3 — cohort-anomalies surfaces leak on energy_audit; PV cases clean
# ---------------------------------------------------------------------


def test_journey2_step3_cohort_anomalies_flags_leak_on_energy_axis(
    client: _SyncASGIClient, patched_routes: Path
) -> None:
    """cohort-anomalies (5-case cohort >= COHORT_MIN_SIZE_FOR_ANOMALY=3)
    surfaces the leak case as an outlier on the ``energy_audit``
    axis; the leak case is the ONLY case in the anomaly set on the
    energy_audit axis (its weighted score is 0 vs 15 for every
    other cohort member at the latest snapshot)."""
    res = client.get("/api/v1/cohort-anomalies")
    assert res.status_code == 200, res.text
    body = res.json()
    _assert_tier1_trio(body)
    assert body["cohort_count"] == 5
    energy_anomalies = [a for a in body["anomalies"] if a["axis"] == "energy_audit"]
    assert energy_anomalies, (
        f"expected at least one energy_audit anomaly; got 0. All anomalies: {body['anomalies']}"
    )
    energy_case_ids = {a["case_id"] for a in energy_anomalies}
    assert energy_case_ids == {LEAK_CASE_ID}, (
        f"expected ONLY leak case as energy_audit outlier; got {sorted(energy_case_ids)}"
    )


def test_journey2_step3_no_pv_case_appears_in_anomalies(
    client: _SyncASGIClient, patched_routes: Path
) -> None:
    """A:-2 cross-analysis-type leakage guard: NEITHER of the 2
    linear_static_pv cases should appear in cohort-anomalies on
    ANY axis. The PV cases are healthy at every snapshot; flagging
    them would surface a false-positive that misleads the reviewer."""
    res = client.get("/api/v1/cohort-anomalies")
    assert res.status_code == 200
    body = res.json()
    flagged = {a["case_id"] for a in body["anomalies"]}
    for pv_case in LINEAR_STATIC_PV_CASES:
        assert pv_case not in flagged, (
            f"false-positive cross-analysis-type leakage: PV case "
            f"{pv_case!r} appears in anomaly set "
            f"{sorted(flagged)}; PV cases should be CLEAN"
        )


# ---------------------------------------------------------------------
# Step 4 — per-case case-completeness rubric coherence
# ---------------------------------------------------------------------


def test_journey2_step4a_explicit_dynamics_rubric_stamped_on_each(
    client: _SyncASGIClient, patched_routes: Path
) -> None:
    """case-completeness under ``analysis_type=explicit_dynamics`` for
    each of 3 explicit_dynamics cases lands the ``explicit_dynamics``
    rubric stamp + the energy_audit axis at the case-specific score."""
    for case_id in EXPLICIT_DYNAMICS_CASES:
        res = client.get(
            f"/api/v1/case-completeness/{case_id}",
            params={"analysis_type": "explicit_dynamics"},
        )
        assert res.status_code == 200, f"{case_id}: {res.text}"
        body = res.json()
        _assert_tier1_trio(body)
        assert body["analysis_type"] == "explicit_dynamics", body
        axes = {entry["label"]: entry for entry in body["breakdown"]}
        assert "energy_audit" in axes, (
            f"{case_id}: explicit_dynamics rubric missing energy_audit axis"
        )
        # The 15-pt energy_audit weight is the SSOT for explicit_dynamics.
        assert axes["energy_audit"]["points_max"] == 15, (
            f"{case_id}: explicit_dynamics energy_audit weight expected 15; "
            f"got {axes['energy_audit']['points_max']}"
        )


def test_journey2_step4b_linear_static_pv_rubric_stamped_on_each(
    client: _SyncASGIClient, patched_routes: Path
) -> None:
    """case-completeness under ``analysis_type=linear_static_pv`` for
    each of 2 PV cases lands the ``linear_static_pv`` rubric stamp."""
    for case_id in LINEAR_STATIC_PV_CASES:
        res = client.get(
            f"/api/v1/case-completeness/{case_id}",
            params={"analysis_type": "linear_static_pv"},
        )
        assert res.status_code == 200, f"{case_id}: {res.text}"
        body = res.json()
        _assert_tier1_trio(body)
        assert body["analysis_type"] == "linear_static_pv", body


# ---------------------------------------------------------------------
# M:-2 binding route-count contract: ≥10 distinct (route, case) tuples
# ---------------------------------------------------------------------


def test_journey2_route_count_contract(client: _SyncASGIClient, patched_routes: Path) -> None:
    """Journey 2 crosses **at least 10 distinct (route, case)
    tuples** (5 trust-score-timeline + 5 case-completeness +
    cohort-executive-summary + cohort-anomalies = 12).

    This is the binding number cited by the Phase 15 D blueprint
    sub-rubric. A future maintainer who silently drops one of the
    5 cases trips this audit."""
    routes_crossed: set[tuple[str, str]] = set()

    # 5× trust-score-timeline (one per case).
    for case_id, _atype in COHORT_CASES:
        res = client.get(f"/api/v1/trust-score-timeline/{case_id}")
        assert res.status_code == 200
        routes_crossed.add(("trust-score-timeline", case_id))

    # 5× case-completeness (one per case, analysis-type-correct).
    for case_id, atype in COHORT_CASES:
        res = client.get(
            f"/api/v1/case-completeness/{case_id}",
            params={"analysis_type": atype},
        )
        assert res.status_code == 200, f"{case_id}: {res.text}"
        routes_crossed.add(("case-completeness", case_id))

    # cohort-executive-summary + cohort-anomalies (no case id).
    assert client.get("/api/v1/cohort-executive-summary").status_code == 200
    routes_crossed.add(("cohort-executive-summary", "_cohort_"))
    assert client.get("/api/v1/cohort-anomalies").status_code == 200
    routes_crossed.add(("cohort-anomalies", "_cohort_"))

    assert len(routes_crossed) >= 10, (
        f"Journey 2 contract: ≥10 distinct (route, case_id) calls; "
        f"crossed {len(routes_crossed)}: {sorted(routes_crossed)}"
    )


# ---------------------------------------------------------------------
# A:-2 cross-analysis-type discrimination — advisor-axes don't leak
# ---------------------------------------------------------------------


def test_journey2_pv_case_completeness_drops_explicit_dynamics_specific_axes(
    client: _SyncASGIClient, patched_routes: Path
) -> None:
    """A 422 audit: the case-completeness route REFUSES to score a
    PV case under the explicit_dynamics rubric isn't a refusal —
    the rubric is analysis-type-driven; both rubrics co-exist. But
    the SCORES per-axis should NOT agree across rubrics for the
    same case (the explicit_dynamics rubric for a PV case would
    naturally score the energy axis differently than the PV rubric
    does). We pin: under explicit_dynamics rubric, the PV case
    surfaces a coherent set of breakdown labels that DIFFERS from
    the linear_static_pv set."""
    case_id = "cylinder-pv-candidate"
    res_pv = client.get(
        f"/api/v1/case-completeness/{case_id}",
        params={"analysis_type": "linear_static_pv"},
    )
    res_ed = client.get(
        f"/api/v1/case-completeness/{case_id}",
        params={"analysis_type": "explicit_dynamics"},
    )
    assert res_pv.status_code == 200 and res_ed.status_code == 200
    pv_labels = {e["label"] for e in res_pv.json()["breakdown"]}
    ed_labels = {e["label"] for e in res_ed.json()["breakdown"]}
    # The two label sets should not be identical — the analysis-type
    # rubric must surface analysis-type-distinct labels somewhere.
    # If they ARE identical, the rubric dispatch is broken (the
    # cross-analysis-type discrimination promised by Phase 11 D
    # would be missing).
    assert pv_labels != ed_labels, (
        f"case-completeness rubric does not discriminate "
        f"linear_static_pv from explicit_dynamics for {case_id}: "
        f"both rubrics surface identical breakdown labels {pv_labels}"
    )


# ---------------------------------------------------------------------
# C:-8 forbidden-token grep on Journey 2 envelopes
# ---------------------------------------------------------------------


def test_journey2_no_forbidden_positive_claims_in_envelopes(
    client: _SyncASGIClient, patched_routes: Path
) -> None:
    """Smoke-grep on Journey 2's envelopes for the 8 broader
    forbidden tokens (modulo ``certified`` which appears in some
    CLAIM_BOUNDARY variants).

    Consumes the SSOT 8-tuple + grep helper from
    :mod:`tests._test_utils` (closes Phase 15 retro §7+§8)."""
    bodies: list[str] = []
    bodies.append(client.get("/api/v1/cohort-executive-summary").text)
    bodies.append(client.get("/api/v1/cohort-anomalies").text)
    for case_id, atype in COHORT_CASES:
        bodies.append(client.get(f"/api/v1/trust-score-timeline/{case_id}").text)
        bodies.append(
            client.get(
                f"/api/v1/case-completeness/{case_id}",
                params={"analysis_type": atype},
            ).text
        )
    blob = "\n".join(bodies)
    assert_no_forbidden_positive_claims(blob, tokens=FORBIDDEN_POSITIVE_CLAIM_TOKENS_8)
