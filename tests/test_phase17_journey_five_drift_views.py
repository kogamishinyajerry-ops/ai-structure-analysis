"""FM-04a Phase 17 D — Journey 1: Five-drift-view audit trail E2E.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

A reviewer-journey test that walks the FIVE distinct drift-attribution
views surfaced across the post-Phase-17 6-envelope surface, in a single
reviewer pass across **5 distinct route/verb pairs**:

  1. ``GET /api/v1/trust-score-timeline/<LEAK_CASE_ID>`` — pin both the
     per-pair ``inter_snapshot_drift_attribution`` (Phase 15 C) AND the
     cumulative ``cumulative_drift_attribution`` (Phase 16 A) both name
     ``energy_audit`` as the dominant axis.
  2. ``GET /api/v1/cohort-anomalies`` — pin BOTH the Phase 16 B
     latest-pair ``cohort_drift_attribution`` AND the Phase 17 A
     ``cohort_cumulative_drift_attribution`` name the leak case as
     dominant on ``energy_audit``.
  3. ``GET /api/v1/cohort-trend-anomalies`` — pin the leak case's
     energy-axis trend event carries both the raw ``slope`` (Phase 9 D)
     AND the Phase 17 C ``percentage_delta_slope`` (both negative).
  4. ``POST /api/v1/signoff-history/<LEAK_CASE_ID>`` — issue a
     ``needs_more_evidence`` signoff; the request body carries NO drift
     fields (server-computed pattern preserved per A:-3 SSOT).
  5. ``GET /api/v1/signoff-history/<LEAK_CASE_ID>`` — pin the new
     record carries BOTH the Phase 16 C ``drift_attribution_at_signoff_time``
     (latest pair) AND the Phase 17 B
     ``cumulative_drift_attribution_at_signoff_time`` (cumulative).

Anti-gaming guards pinned (per Phase 17 binding rubric §3.D):

* **M:-2** — the journey carries an explicit ``routes_crossed`` set
  tagged with the 5 distinct route names (the load-bearing route
  count is the binding number, separate from the narrative).
* **T:-3** — boundary pins (== bounds, NOT >=):
    * cohort latest-pair: ``cohort_dominant_axis == "energy_audit"``,
      ``dominant_case_id == LEAK_CASE_ID``,
      ``cohort_max_abs_delta_pct == 100.0`` exactly.
    * cohort cumulative: same dominant axis + case + 100.0 magnitude.
    * timeline per-pair entries == 2; cumulative
      ``dominant_axis == "energy_audit"`` AND
      ``dominant_delta_pct == -100.0`` exactly.
    * cohort-trend-anomalies for leak case carries a NEGATIVE
      energy_audit slope + a NEGATIVE percentage_delta_slope.
    * signoff latest-pair AND signoff cumulative both name
      ``energy_audit`` + carry signed dominant_delta_pct.
* **C:-8** — every 200 envelope carries the Tier 1 disclaimer trio
  (verified via the SSOT :func:`tests._test_utils.assert_tier1_trio`);
  the 8-token forbidden-positive-claim discipline holds across all
  5 envelopes (via the SSOT :func:`tests._test_utils.
  assert_no_forbidden_positive_claims`).
* **A:-3** — signed-registry ``GS-001`` is refused on the 4
  parameterized routes the journey touches with HTTP 422
  (cohort-anomalies + cohort-trend-anomalies are non-parameterized).
* **A:-3 server-computed** — the POST request DOES NOT carry any
  ``drift_attribution_at_signoff_time`` NOR any
  ``cumulative_drift_attribution_at_signoff_time`` field; the fields
  appear in the GET response strictly because the service layer
  computed them from the snapshot tree (pinned via runtime body audit).
* **E:-2** — no real-solver invocation; no real-LLM call.
* **V:-3** — the snapshot tree is written ENTIRELY under tmp_path.
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
from app.api.routes import cohort_anomalies as cohort_anomalies_route
from app.api.routes import cohort_trend_anomalies as cohort_trend_anomalies_route
from app.api.routes import signoff_history as signoff_history_route
from app.api.routes import trust_score_timeline as trust_score_timeline_route
from app.main import app
from app.services.reporting.cohort_snapshot import write_cohort_snapshot

from tests._test_utils import (
    assert_no_forbidden_positive_claims,
    assert_tier1_trio,
)
from tests._test_utils.cohort_fixtures import (
    make_clean_leak_case_input,
    make_explicit_dynamics_healthy_input,
    make_pv_case_input,
    make_regressed_leak_case_input,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

# Phase 17 D Journey 1 cohort SSOT — 5-case shape (3 explicit_dynamics
# + 2 linear_static_pv) so the cohort >= COHORT_MIN_SIZE_FOR_ANOMALY
# (3) and the leak case's evolution stands out against 4 flat cases.
COHORT_CASES: tuple[tuple[str, str], ...] = (
    ("rod-wave-impact-candidate", "explicit_dynamics"),
    ("rod-wave-impact-stiff-candidate", "explicit_dynamics"),
    ("rod-wave-impact-energy-leak-candidate", "explicit_dynamics"),
    ("cylinder-pv-candidate", "linear_static_pv"),
    ("cylinder-pv-extended-candidate", "linear_static_pv"),
)
LEAK_CASE_ID = "rod-wave-impact-energy-leak-candidate"

# Snapshot labels SSOT — chronological compact UTC.
#
# Arc shape: snap-1 + snap-2 CLEAN for the leak case (energy 15);
# snap-3 REGRESSED (energy 0). This places the cumulative collapse
# (snap-1 → snap-3 = 15 → 0 = -100.0%) AND the latest-pair collapse
# (snap-2 → snap-3 = 15 → 0 = -100.0%) BOTH on the energy_audit axis,
# so the FIVE drift views all coherently name energy_audit as dominant.
SNAP_1_LABEL = "2026-05-17T100000Z"  # leak CLEAN
SNAP_2_LABEL = "2026-05-17T120000Z"  # leak CLEAN
SNAP_3_LABEL = "2026-05-17T140000Z"  # leak REGRESSED

SIGNED_REGISTRY_CASE_ID = "GS-001"

# Phase 17 D Journey 1 route contract: 5 distinct route/verb pairs
# carrying the 5 drift views.
EXPECTED_ROUTES_CROSSED: frozenset[str] = frozenset(
    {
        "trust-score-timeline",
        "cohort-anomalies",
        "cohort-trend-anomalies",
        "signoff-history-GET",
        "signoff-history-POST",
    }
)


# ---------------------------------------------------------------------
# Sync ASGI client (mirrors Phase 16 D Journey 1 pattern)
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

    def post(
        self,
        url: str,
        *,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        async def _run() -> httpx.Response:
            async with httpx.AsyncClient(
                transport=self._transport, base_url="http://testserver"
            ) as client:
                return await client.post(url, json=json_body, headers=headers)

        return asyncio.run(_run())


@pytest.fixture()
def client() -> _SyncASGIClient:
    return _SyncASGIClient(app)


@pytest.fixture(scope="module")
def journey_repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Seed a tmp_path with 5 cases × 3 snapshots. Only the leak case
    evolves; the other 4 cases stay flat. The real ``reports/snapshots/``
    tree is NEVER touched."""
    for gen in (
        "gen_rod_wave_impact_deck.py",
        "gen_rod_wave_impact_stiff_deck.py",
        "gen_rod_wave_impact_energy_leak_deck.py",
    ):
        subprocess.check_call(
            [sys.executable, str(REPO_ROOT / "scripts" / gen)],
            cwd=str(REPO_ROOT),
        )

    tmp = tmp_path_factory.mktemp("phase17d_journey1_repo")
    golden = tmp / "golden_samples"
    golden.mkdir(parents=True)
    for case_id, _atype in COHORT_CASES:
        shutil.copytree(REPO_ROOT / "golden_samples" / case_id, golden / case_id)

    # Snap-1: all 5 healthy (leak case in CLEAN variant).
    snap1 = [
        make_explicit_dynamics_healthy_input(tmp, "rod-wave-impact-candidate"),
        make_explicit_dynamics_healthy_input(tmp, "rod-wave-impact-stiff-candidate"),
        make_clean_leak_case_input(tmp, LEAK_CASE_ID, suffix="phase17d_journey1_snap1"),
        make_pv_case_input(tmp, "cylinder-pv-candidate"),
        make_pv_case_input(tmp, "cylinder-pv-extended-candidate"),
    ]
    write_cohort_snapshot(snap1, repo_root=tmp, snapshot_label=SNAP_1_LABEL)

    # Snap-2: leak still CLEAN; others flat.
    snap2 = [
        make_explicit_dynamics_healthy_input(tmp, "rod-wave-impact-candidate"),
        make_explicit_dynamics_healthy_input(tmp, "rod-wave-impact-stiff-candidate"),
        make_clean_leak_case_input(tmp, LEAK_CASE_ID, suffix="phase17d_journey1_snap2"),
        make_pv_case_input(tmp, "cylinder-pv-candidate"),
        make_pv_case_input(tmp, "cylinder-pv-extended-candidate"),
    ]
    write_cohort_snapshot(snap2, repo_root=tmp, snapshot_label=SNAP_2_LABEL)

    # Snap-3: leak regressed (canonical state + 3 optional artifacts
    # omitted, dropping the trust below the 50-pt floor).
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
    """Redirect every touched route's ``_repo_root`` to the seeded
    tmp_path so no journey step can leak into the real repo's
    snapshot tree."""
    for route_module in (
        cohort_anomalies_route,
        cohort_trend_anomalies_route,
        trust_score_timeline_route,
        signoff_history_route,
    ):
        monkeypatch.setattr(route_module, "_repo_root", lambda r=journey_repo: r)
    return journey_repo


# ---------------------------------------------------------------------
# Step 1 — trust-score-timeline carries per-pair + cumulative drift
# ---------------------------------------------------------------------


def test_journey_step1_trust_score_timeline_carries_both_drift_views(
    client: _SyncASGIClient, patched_routes: Path
) -> None:
    """The leak case's trust-score-timeline carries BOTH the per-pair
    drift entries (Phase 15 C) AND the cumulative drift (Phase 16 A);
    BOTH name energy_audit as dominant."""
    res = client.get(f"/api/v1/trust-score-timeline/{LEAK_CASE_ID}")
    assert res.status_code == 200, res.text
    body = res.json()
    assert_tier1_trio(body)
    assert body["schema_version"] == "1.2.0", body["schema_version"]
    assert len(body["points"]) == 3, len(body["points"])
    inter = body["inter_snapshot_drift_attribution"]
    assert len(inter) == 2, inter
    # Latest pair (snap-2 → snap-3) is the dramatic collapse on energy.
    latest_pair = inter[-1]
    assert latest_pair["dominant_axis"] == "energy_audit", latest_pair
    assert latest_pair["dominant_delta_pct"] == -100.0, latest_pair
    assert latest_pair["from_snapshot"] == SNAP_2_LABEL, latest_pair
    assert latest_pair["to_snapshot"] == SNAP_3_LABEL, latest_pair
    # Cumulative (snap-1 → snap-3) also energy because cumulative
    # delta is also 15 → 0 = -100.0% (snap-1 and snap-2 are both clean).
    cumulative = body["cumulative_drift_attribution"]
    assert cumulative is not None
    assert cumulative["dominant_axis"] == "energy_audit", cumulative
    assert cumulative["dominant_delta_pct"] == -100.0, cumulative
    assert cumulative["from_snapshot"] == SNAP_1_LABEL, cumulative
    assert cumulative["to_snapshot"] == SNAP_3_LABEL, cumulative


# ---------------------------------------------------------------------
# Step 2 — cohort-anomalies carries latest-pair AND cumulative drift
# ---------------------------------------------------------------------


def test_journey_step2_cohort_anomalies_carries_latest_and_cumulative_drift(
    client: _SyncASGIClient, patched_routes: Path
) -> None:
    """The cohort-anomalies envelope carries BOTH the Phase 16 B
    ``cohort_drift_attribution`` (latest pair) AND the Phase 17 A
    ``cohort_cumulative_drift_attribution`` (cumulative)."""
    res = client.get("/api/v1/cohort-anomalies")
    assert res.status_code == 200, res.text
    body = res.json()
    assert_tier1_trio(body)
    assert body["schema_version"] == "1.2.0", body["schema_version"]

    latest = body.get("cohort_drift_attribution")
    assert latest is not None
    assert latest["cohort_dominant_axis"] == "energy_audit", latest
    assert latest["dominant_case_id"] == LEAK_CASE_ID, latest
    assert latest["cohort_max_abs_delta_pct"] == 100.0, latest
    assert latest["from_snapshot"] == SNAP_2_LABEL, latest
    assert latest["to_snapshot"] == SNAP_3_LABEL, latest

    cumulative = body.get("cohort_cumulative_drift_attribution")
    assert cumulative is not None, sorted(body.keys())
    # Cumulative cohort drift also names energy_audit on the leak case.
    assert cumulative["cohort_dominant_axis"] == "energy_audit", cumulative
    assert cumulative["dominant_case_id"] == LEAK_CASE_ID, cumulative
    assert cumulative["cohort_max_abs_delta_pct"] == 100.0, cumulative
    assert cumulative["from_snapshot"] == SNAP_1_LABEL, cumulative
    assert cumulative["to_snapshot"] == SNAP_3_LABEL, cumulative


# ---------------------------------------------------------------------
# Step 3 — cohort-trend-anomalies carries raw + percentage slope
# ---------------------------------------------------------------------


def test_journey_step3_cohort_trend_anomalies_carries_raw_and_pct_slope(
    client: _SyncASGIClient, patched_routes: Path
) -> None:
    """The cohort-trend-anomalies envelope at Phase 17 C bump 1.1.0
    carries BOTH the raw ``slope`` (Phase 9 D) AND the
    ``percentage_delta_slope`` (Phase 17 C) on every anomaly. The leak
    case's energy_audit axis is a downward trend (the trend walker
    sees weighted-energy 15 → 15 → 0 across 3 snapshots = slope
    -7.5 weighted-pts/snap → -50.0 %/snap)."""
    res = client.get("/api/v1/cohort-trend-anomalies")
    assert res.status_code == 200, res.text
    body = res.json()
    assert_tier1_trio(body)
    assert body["schema_version"] == "1.1.0", body["schema_version"]

    # The leak case's energy_audit axis must fire as a trend anomaly
    # (slope <= -0.5 / -1.5 / -3.0 floor; 15 → 15 → 0 yields a
    # least-squares slope steep enough to clear the floor).
    leak_events = [
        a for a in body["anomalies"] if a["case_id"] == LEAK_CASE_ID and a["axis"] == "energy_audit"
    ]
    assert len(leak_events) == 1, leak_events
    evt = leak_events[0]
    assert "slope" in evt, evt
    assert "percentage_delta_slope" in evt, evt
    assert evt["slope"] < 0, evt
    assert evt["percentage_delta_slope"] < 0, evt
    # Cross-axis comparability sanity: percentage_delta_slope equals
    # raw slope / TRUST_AXIS_WEIGHTS[axis] * 100; for energy_audit
    # (weight 15), -7.5 raw → -50.0 pct.
    expected_pct = round(evt["slope"] / 15 * 100.0, 6)
    assert evt["percentage_delta_slope"] == pytest.approx(expected_pct, abs=1e-6), evt


# ---------------------------------------------------------------------
# Step 4 — signoff-history POST without client-supplied drift
# ---------------------------------------------------------------------


SIGNOFF_BODY: dict[str, Any] = {
    "reviewer": "phase17-journey-five-drift-reviewer",
    "verdict": "needs_more_evidence",
    "notes": (
        "Tier 1 engineering candidate review under Phase 17 D Journey 1; "
        "energy axis collapsed under the leak arc. Not signed validation; "
        "not benchmark agreement."
    ),
}


def test_journey_step4_signoff_post_succeeds_without_client_drift(
    client: _SyncASGIClient, patched_routes: Path
) -> None:
    """POST a new signoff. The request body carries NEITHER the
    Phase 16 C ``drift_attribution_at_signoff_time`` NOR the Phase
    17 B ``cumulative_drift_attribution_at_signoff_time``; both
    fields are server-computed at write time (A:-3 SSOT). The POST
    returns 200."""
    # A:-3 server-computed body audit on BOTH fields.
    assert "drift_attribution_at_signoff_time" not in SIGNOFF_BODY, SIGNOFF_BODY
    assert "cumulative_drift_attribution_at_signoff_time" not in SIGNOFF_BODY, SIGNOFF_BODY
    res = client.post(
        f"/api/v1/signoff-history/{LEAK_CASE_ID}",
        json_body=SIGNOFF_BODY,
        headers={"Content-Type": "application/json"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["case_id"] == LEAK_CASE_ID, body
    assert body["verdict"] == "needs_more_evidence", body
    assert body["reviewer"] == "phase17-journey-five-drift-reviewer", body


# ---------------------------------------------------------------------
# Step 5 — signoff-history GET shows BOTH drift fields
# ---------------------------------------------------------------------


def test_journey_step5_signoff_history_get_shows_both_server_computed_drift(
    client: _SyncASGIClient, patched_routes: Path
) -> None:
    """After the POST, the signoff-history GET returns the new
    record with BOTH:
      * ``drift_attribution_at_signoff_time`` (Phase 16 C; latest pair
        = snap-2 → snap-3 = -100.0% on energy)
      * ``cumulative_drift_attribution_at_signoff_time`` (Phase 17 B;
        cumulative = snap-1 → snap-3 = -100.0% on energy)
    """
    res = client.get(f"/api/v1/signoff-history/{LEAK_CASE_ID}")
    assert res.status_code == 200, res.text
    body = res.json()
    assert_tier1_trio(body)
    assert body["schema_version"] == "1.2.0", body["schema_version"]
    records = body["records"]
    assert len(records) == 1, records
    record = records[0]
    assert record["verdict"] == "needs_more_evidence", record

    latest = record.get("drift_attribution_at_signoff_time")
    assert latest is not None
    assert latest["dominant_axis"] == "energy_audit", latest
    assert latest["dominant_delta_pct"] == -100.0, latest
    assert latest["from_snapshot"] == SNAP_2_LABEL, latest
    assert latest["to_snapshot"] == SNAP_3_LABEL, latest

    cumulative = record.get("cumulative_drift_attribution_at_signoff_time")
    assert cumulative is not None, sorted(record.keys())
    assert cumulative["dominant_axis"] == "energy_audit", cumulative
    assert cumulative["dominant_delta_pct"] == -100.0, cumulative
    assert cumulative["from_snapshot"] == SNAP_1_LABEL, cumulative
    assert cumulative["to_snapshot"] == SNAP_3_LABEL, cumulative


# ---------------------------------------------------------------------
# M:-2 binding 5-route audit
# ---------------------------------------------------------------------


def test_journey_5_route_count_contract(client: _SyncASGIClient, patched_routes: Path) -> None:
    """The journey crosses **exactly the 5 distinct route/verb pairs**
    named in the Phase 17 D blueprint contract. A future maintainer
    who silently drops one of the 5 trips this audit.

    The 5 routes correspond to the FIVE distinct drift views surfaced
    by Phase 17:
      * trust-score-timeline (Phase 15 C per-pair + Phase 16 A cumulative)
      * cohort-anomalies (Phase 16 B latest-pair + Phase 17 A cumulative)
      * cohort-trend-anomalies (Phase 9 D raw + Phase 17 C pct-slope)
      * signoff-history GET (Phase 16 C latest + Phase 17 B cumulative)
      * signoff-history POST (the server-computed entry point)
    """
    routes_crossed: set[str] = set()

    res = client.get(f"/api/v1/trust-score-timeline/{LEAK_CASE_ID}")
    assert res.status_code == 200
    routes_crossed.add("trust-score-timeline")

    res = client.get("/api/v1/cohort-anomalies")
    assert res.status_code == 200
    routes_crossed.add("cohort-anomalies")

    res = client.get("/api/v1/cohort-trend-anomalies")
    assert res.status_code == 200
    routes_crossed.add("cohort-trend-anomalies")

    res = client.get(f"/api/v1/signoff-history/{LEAK_CASE_ID}")
    assert res.status_code == 200
    routes_crossed.add("signoff-history-GET")

    # Unique reviewer per call so the per-(case, reviewer) sliding-
    # window rate limit (Phase 10 D) does NOT trip on Step 4's earlier
    # POST.
    res = client.post(
        f"/api/v1/signoff-history/{LEAK_CASE_ID}",
        json_body={
            "reviewer": "phase17-route-audit-reviewer",
            "verdict": "needs_more_evidence",
            "notes": (
                "Phase 17 D route-count audit. Not signed validation; not benchmark agreement."
            ),
        },
        headers={"Content-Type": "application/json"},
    )
    assert res.status_code == 200, res.text
    routes_crossed.add("signoff-history-POST")

    assert routes_crossed == EXPECTED_ROUTES_CROSSED, (
        f"route contract mismatch: crossed {sorted(routes_crossed)}; "
        f"expected {sorted(EXPECTED_ROUTES_CROSSED)}"
    )
    assert len(routes_crossed) == 5, f"expected 5 distinct routes; got {len(routes_crossed)}"


# ---------------------------------------------------------------------
# A:-3 per-route signed-registry 422-refusal regression guard
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "verb,url_template",
    [
        ("GET", "/api/v1/trust-score-timeline/{cid}"),
        ("GET", "/api/v1/signoff-history/{cid}"),
        ("POST", "/api/v1/signoff-history/{cid}"),
    ],
)
def test_journey_per_route_signed_registry_refused(
    verb: str,
    url_template: str,
    client: _SyncASGIClient,
    patched_routes: Path,
) -> None:
    """Every parameterized reviewer-facing route in the journey
    REFUSES the signed-registry case_id shape ``GS-001`` with HTTP
    422, on BOTH GET and POST verbs of signoff-history. The
    cohort-anomalies + cohort-trend-anomalies routes are
    non-parameterized (no case_id in URL); signed-registry refusal
    there is upstream when the cohort walker filters
    ``golden_samples/*-candidate/`` paths (Phase 4 B)."""
    url = url_template.format(cid=SIGNED_REGISTRY_CASE_ID)
    if verb == "GET":
        res = client.get(url)
    elif verb == "POST":
        res = client.post(
            url,
            json_body={
                "reviewer": "phase17-signed-registry-probe",
                "verdict": "needs_more_evidence",
                "notes": ("probe; not signed validation; not benchmark agreement."),
            },
            headers={"Content-Type": "application/json"},
        )
    else:
        raise AssertionError(f"unexpected verb {verb!r}")
    assert res.status_code == 422, (
        f"{verb} {url_template} accepted signed-registry case_id "
        f"{SIGNED_REGISTRY_CASE_ID!r}; expected 422, got {res.status_code}: "
        f"{res.text}"
    )
    detail_raw = res.json().get("detail") or ""
    detail = (detail_raw if isinstance(detail_raw, str) else str(detail_raw)).lower()
    assert "signed-registry" in detail or "signed_registry" in detail, (
        f"{verb} {url_template} 422 detail missing 'signed-registry' token: {detail!r}"
    )


# ---------------------------------------------------------------------
# C:-8 forbidden-token grep across all 5 envelopes
# ---------------------------------------------------------------------


def test_journey_no_forbidden_positive_claims_in_envelopes(
    client: _SyncASGIClient, patched_routes: Path
) -> None:
    """The 8-token forbidden positive-claim tuple MUST NOT appear in
    any journey envelope outside ``not <claim>`` / ``no <claim>``
    form. Audits all 5 distinct envelopes via the SSOT helper."""
    bodies = [
        client.get(f"/api/v1/trust-score-timeline/{LEAK_CASE_ID}").text,
        client.get("/api/v1/cohort-anomalies").text,
        client.get("/api/v1/cohort-trend-anomalies").text,
        client.get(f"/api/v1/signoff-history/{LEAK_CASE_ID}").text,
    ]
    blob = "\n".join(bodies)
    assert_no_forbidden_positive_claims(blob)


# ---------------------------------------------------------------------
# Cross-envelope coherence audit
# ---------------------------------------------------------------------


def test_journey_cross_envelope_drift_coherence(
    client: _SyncASGIClient, patched_routes: Path
) -> None:
    """The 5 drift views all coherently name ``energy_audit`` as the
    dominant axis for the LEAK_CASE_ID under this stuck arc:

      1. trust-score-timeline cumulative
      2. cohort-anomalies latest-pair
      3. cohort-anomalies cumulative
      4. cohort-trend-anomalies (negative pct slope)
      5. signoff-history record latest-pair AND cumulative

    This is the cross-envelope coherence pin: a stuck regression on
    one axis surfaces consistently across every drift view.
    """
    # 1. Timeline cumulative
    tl_body = client.get(f"/api/v1/trust-score-timeline/{LEAK_CASE_ID}").json()
    assert tl_body["cumulative_drift_attribution"]["dominant_axis"] == "energy_audit"

    # 2 + 3. Cohort latest + cumulative
    co_body = client.get("/api/v1/cohort-anomalies").json()
    assert co_body["cohort_drift_attribution"]["cohort_dominant_axis"] == "energy_audit"
    assert co_body["cohort_cumulative_drift_attribution"]["cohort_dominant_axis"] == "energy_audit"

    # 4. cohort-trend negative pct slope on energy axis for leak case
    tr_body = client.get("/api/v1/cohort-trend-anomalies").json()
    leak_energy = [
        a
        for a in tr_body["anomalies"]
        if a["case_id"] == LEAK_CASE_ID and a["axis"] == "energy_audit"
    ]
    assert len(leak_energy) == 1, leak_energy
    assert leak_energy[0]["percentage_delta_slope"] < 0

    # 5. Signoff: POST a fresh signoff under a unique reviewer to
    # avoid the rate-limit window, then GET.
    client.post(
        f"/api/v1/signoff-history/{LEAK_CASE_ID}",
        json_body={
            "reviewer": "phase17-coherence-reviewer",
            "verdict": "needs_more_evidence",
            "notes": "coherence audit; not signed validation; not benchmark agreement.",
        },
        headers={"Content-Type": "application/json"},
    )
    so_body = client.get(f"/api/v1/signoff-history/{LEAK_CASE_ID}").json()
    coherence_records = [
        r for r in so_body["records"] if r["reviewer"] == "phase17-coherence-reviewer"
    ]
    assert len(coherence_records) == 1, coherence_records
    record = coherence_records[0]
    assert record["drift_attribution_at_signoff_time"]["dominant_axis"] == "energy_audit"
    assert record["cumulative_drift_attribution_at_signoff_time"]["dominant_axis"] == "energy_audit"


# ---------------------------------------------------------------------
# V:-3 fixture-isolation audit
# ---------------------------------------------------------------------


def test_journey_does_not_touch_real_snapshot_tree(
    journey_repo: Path,
) -> None:
    """The journey_repo must be under tmp_path, NOT under REPO_ROOT/
    reports/snapshots/."""
    assert journey_repo.is_dir()
    real_snapshots = REPO_ROOT / "reports" / "snapshots"
    # Confirm journey_repo is NOT a subdirectory of real_snapshots.
    journey_resolved = journey_repo.resolve()
    real_resolved = real_snapshots.resolve()
    assert real_resolved not in journey_resolved.parents, (
        f"journey_repo {journey_resolved} is under real reports/snapshots "
        f"{real_resolved}; V:-3 violation"
    )
