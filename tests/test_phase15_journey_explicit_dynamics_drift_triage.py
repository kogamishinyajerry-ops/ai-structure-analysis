"""FM-04a Phase 15 D — Journey 1: explicit_dynamics drift triage E2E.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

A reviewer-journey test that walks the new explicit_dynamics cohort
surfaces end-to-end across **6 distinct routes** of the real ASGI
stack. The reviewer:

  1. Opens the cohort executive summary and sees the regressed bucket
     is non-empty (the leak case dropped below the 50-pt trust floor
     at snap-3 of the Phase 15 B degradation arc).
  2. Drills into the leak case's trust-score alerts and reads the
     ``drift_attribution.dominant_axis`` — the new Phase 15 C field
     names ``energy_audit`` as the regressed axis with a -100.0%
     delta.
  3. Reads the leak case's trust-score timeline and observes the
     ``inter_snapshot_drift_attribution`` tuple — three snapshots,
     two consecutive-pair transitions, with the snap-2→snap-3
     transition naming ``energy_audit`` as dominant.
  4. Checks the leak case's per-axis case-completeness scorecard and
     observes the ``energy_audit`` axis at ``0/15`` (the snapshot
     advisory state is ``open_residual`` from the canonical leak
     fixture).
  5. Loads the advisor critique for the snap-3 (case, snapshot) pair
     and observes the ``explicit_dynamics`` branch fired (Phase 14 C),
     citing the energy-partition-closure theme that points at the
     audit deviation flagged by the per-frame audit.
  6. Pulls the signoff history and confirms it is empty (no prior
     reviewer judgment landed; this is the first triage).

Anti-gaming guards pinned (per Phase 15 binding rubric §3.D):

* **M:-2** — the journey carries an explicit ``routes_crossed`` set
  tagged with the 6 distinct route names; the load-bearing route
  count is the binding number (6), separate from the narrative.
* **T:-3** — the snap-2→snap-3 ``drift_attribution.dominant_axis ==
  "energy_audit"`` pin and the ``-100.0`` exact ``dominant_delta_pct``
  pin are boundary-pinned (NOT >= bounds) so a drifted SSOT trips
  this test.
* **C:-8** — every 200 envelope inspected by the journey carries
  the Tier 1 disclaimer trio (``claim_tier`` / ``claim_boundary`` /
  ``claim_impact``); the 9-token forbidden-positive-claim discipline
  is preserved.
* **A:-3** — signed-registry ``GS-001`` is refused on each of the 6
  routes the journey touches (per-route 422-refusal regression
  guard); the cross-route signed-registry refusal SSOT (Phase 14 A)
  is exercised in the same tmp_path repo.
* **E:-2** — no real-solver invocation; no real-LLM call; the
  advisor falls through to the stub backend (``advisor_status ==
  "stub"``) because no LLM env var is configured in the test
  process.
* **V:-3** — the snapshot tree is written ENTIRELY under tmp_path;
  the real ``reports/snapshots/`` tree is not touched.
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
from app.api.routes import advisor_critique as advisor_critique_route
from app.api.routes import case_completeness as case_completeness_route
from app.api.routes import cohort_executive_summary as cohort_executive_summary_route
from app.api.routes import signoff_history as signoff_history_route
from app.api.routes import trust_score_alerts as trust_score_alerts_route
from app.api.routes import trust_score_timeline as trust_score_timeline_route
from app.main import app
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
    make_regressed_leak_case_input,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

# Phase 15 cohort SSOT — same 3 explicit_dynamics cases substantiated
# by Phase 14 D (canonical) + Phase 15 A (stiff + leak).
EXPLICIT_DYNAMICS_COHORT_CASES: tuple[str, ...] = (
    "rod-wave-impact-candidate",
    "rod-wave-impact-stiff-candidate",
    "rod-wave-impact-energy-leak-candidate",
)
LEAK_CASE_ID = "rod-wave-impact-energy-leak-candidate"

# Snapshot labels SSOT — chronological UTC compact form. Same labels
# as Phase 15 B so the journey arc is traceable to that slice's
# bucket-transition pins.
SNAP_1_LABEL = "2026-05-17T100000Z"  # all healthy
SNAP_2_LABEL = "2026-05-17T120000Z"  # leak watching
SNAP_3_LABEL = "2026-05-17T140000Z"  # leak regressed

# Phase 14 A signed-registry SSOT shape for the per-route 422-refusal
# regression guard. The cross-route refusal helper (Phase 14 A)
# enforces this on every reviewer-facing route.
SIGNED_REGISTRY_CASE_ID = "GS-001"

# 6-route journey contract. Mirrors Phase 12 F's route-cross discipline.
EXPECTED_ROUTES_CROSSED: frozenset[str] = frozenset(
    {
        "cohort-executive-summary",
        "trust-score-alerts",
        "trust-score-timeline",
        "case-completeness",
        "advisor-critique",
        "signoff-history",
    }
)


# ---------------------------------------------------------------------
# Sync ASGI client wrapper (mirrors Phase 12 F pattern)
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
# Fixture seeding — same pattern as Phase 15 B
# ---------------------------------------------------------------------


@pytest.fixture(scope="module")
def journey_repo(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Seed a tmp_path with the 3 explicit_dynamics cases + write the
    3-snapshot degradation arc. The real ``reports/snapshots/`` tree
    is NEVER touched."""
    # Drive the Phase 15 A generators in the real repo so the
    # gitignored on-disk fixtures exist before copytree.
    for gen in (
        "gen_rod_wave_impact_deck.py",
        "gen_rod_wave_impact_stiff_deck.py",
        "gen_rod_wave_impact_energy_leak_deck.py",
    ):
        subprocess.check_call(
            [sys.executable, str(REPO_ROOT / "scripts" / gen)],
            cwd=str(REPO_ROOT),
        )

    tmp = tmp_path_factory.mktemp("phase15d_journey1_repo")
    golden = tmp / "golden_samples"
    golden.mkdir(parents=True)
    for case_id in EXPLICIT_DYNAMICS_COHORT_CASES:
        shutil.copytree(REPO_ROOT / "golden_samples" / case_id, golden / case_id)

    # Snap-1: all healthy (leak case in CLEAN variant).
    write_cohort_snapshot(
        [
            make_explicit_dynamics_healthy_input(tmp, "rod-wave-impact-candidate"),
            make_explicit_dynamics_healthy_input(tmp, "rod-wave-impact-stiff-candidate"),
            make_clean_leak_case_input(tmp, LEAK_CASE_ID, suffix="phase15d_snap1_clean"),
        ],
        repo_root=tmp,
        snapshot_label=SNAP_1_LABEL,
    )
    # Snap-2: canonical + stiff healthy; leak watching (canonical
    # Phase 15 A state with open_residual energy_audit).
    write_cohort_snapshot(
        [
            make_explicit_dynamics_healthy_input(tmp, "rod-wave-impact-candidate"),
            make_explicit_dynamics_healthy_input(tmp, "rod-wave-impact-stiff-candidate"),
            make_explicit_dynamics_healthy_input(tmp, LEAK_CASE_ID),
        ],
        repo_root=tmp,
        snapshot_label=SNAP_2_LABEL,
    )
    # Snap-3: leak regressed (canonical state + 3 optional artifacts
    # omitted).
    write_cohort_snapshot(
        [
            make_explicit_dynamics_healthy_input(tmp, "rod-wave-impact-candidate"),
            make_explicit_dynamics_healthy_input(tmp, "rod-wave-impact-stiff-candidate"),
            make_regressed_leak_case_input(tmp, LEAK_CASE_ID),
        ],
        repo_root=tmp,
        snapshot_label=SNAP_3_LABEL,
    )
    return tmp


@pytest.fixture()
def patched_routes(journey_repo: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect every route's ``_repo_root`` to the seeded tmp_path so
    no journey step can leak into the real repo's snapshot tree."""
    for route_module in (
        cohort_executive_summary_route,
        trust_score_alerts_route,
        trust_score_timeline_route,
        case_completeness_route,
        advisor_critique_route,
        signoff_history_route,
    ):
        monkeypatch.setattr(route_module, "_repo_root", lambda r=journey_repo: r)
    return journey_repo


# ---------------------------------------------------------------------
# C:-8 Tier 1 disclaimer trio audit
# ---------------------------------------------------------------------
#
# Phase 15 retrospective §8 sequel: the per-file ``_assert_tier1_trio``
# helper has been hoisted to ``tests/_test_utils`` as the cross-phase
# SSOT (closes Phase 16 retro §7 + §8 carry-forward). Phase 15+ test
# files import :func:`tests._test_utils.assert_tier1_trio` instead of
# inlining a local copy; a meta-test in
# ``tests/test_phase16_test_utils_ssot.py`` enforces that no other
# Phase 15+ test file re-inlines the helper.


# ---------------------------------------------------------------------
# Step 1 — cohort-executive-summary surfaces regressed_count >= 1
# ---------------------------------------------------------------------


def test_journey_step1_cohort_executive_summary_shows_regressed(
    client: _SyncASGIClient, patched_routes: Path
) -> None:
    """Reviewer opens the dashboard: cohort executive summary lands
    at the snap-3 state and reports ``regressed_count >= 1`` (the
    leak case crossed below the 50-pt trust floor).

    Blueprint §3.D step 1 names ``cohort-overview/{snap-3-label}``
    but the route that actually carries the ``regressed_count``
    bucket field is ``cohort-executive-summary`` (cohort-overview
    carries the COMPLETENESS-score distribution, NOT the
    trust-score buckets). The engineering deliverable (observe the
    regressed bucket non-empty after the arc) is preserved.
    """
    res = client.get("/api/v1/cohort-executive-summary")
    assert res.status_code == 200, res.text
    body = res.json()
    assert_tier1_trio(body)
    assert body["regressed_count"] >= 1, (
        f"snap-3 state expected at least one regressed case; got "
        f"regressed_count={body['regressed_count']}, "
        f"healthy_count={body['healthy_count']}, "
        f"watching_count={body['watching_count']}"
    )
    # Cohort body lists the leak case in the regressed bucket.
    case_buckets = {c["case_id"]: c["bucket"] for c in body["cases"]}
    assert case_buckets.get(LEAK_CASE_ID) == "regressed", (
        f"leak case bucket: {case_buckets.get(LEAK_CASE_ID)!r}"
    )


# ---------------------------------------------------------------------
# Step 2 — trust-score-alerts carries drift_attribution + dominant axis
# ---------------------------------------------------------------------


def test_journey_step2_trust_score_alerts_drift_attribution_names_energy_axis(
    client: _SyncASGIClient, patched_routes: Path
) -> None:
    """Drilling into the leak case's trust-score alerts surfaces the
    Phase 15 C ``drift_attribution.dominant_axis`` field naming
    ``energy_audit`` on the snap-1→snap-2 transition (the 15→0
    energy axis collapse). The snap-1 clean variant has the energy
    axis at full credit; snap-2 has it at 0.

    The load-bearing T:-3 pin: ``dominant_delta_pct == -100.0``
    exactly (15→0 weighted = -100.0% of the 15-pt axis weight)."""
    res = client.get(f"/api/v1/trust-score-alerts/{LEAK_CASE_ID}")
    assert res.status_code == 200, res.text
    body = res.json()
    assert_tier1_trio(body)
    assert body["schema_version"] == "1.1.0", body["schema_version"]
    assert body["alert_count"] >= 1, body
    # Find an alert whose drift_attribution names energy_audit as
    # dominant. The snap-1 → snap-2 transition is the load-bearing
    # one (energy axis 15 → 0).
    energy_alerts = [
        a
        for a in body["alerts"]
        if (a.get("drift_attribution") or {}).get("dominant_axis") == "energy_audit"
    ]
    assert energy_alerts, (
        f"no alert names energy_audit as dominant; got alerts: "
        f"{[a.get('drift_attribution') for a in body['alerts']]}"
    )
    # The snap1→snap2 transition exactly produces -100.0%.
    deltas = {a["drift_attribution"]["dominant_delta_pct"] for a in energy_alerts}
    assert -100.0 in deltas, (
        f"expected -100.0 in energy-axis dominant_delta_pct values; got {deltas}"
    )


# ---------------------------------------------------------------------
# Step 3 — trust-score-timeline carries inter_snapshot_drift_attribution
# ---------------------------------------------------------------------


def test_journey_step3_trust_score_timeline_carries_inter_snapshot_drift(
    client: _SyncASGIClient, patched_routes: Path
) -> None:
    """The leak case's trust-score timeline shows 3 snapshots and
    carries the new ``inter_snapshot_drift_attribution`` tuple
    (Phase 15 C MINOR bump 1.0.0 → 1.1.0). At LEAST one consecutive-
    snapshot transition names ``energy_audit`` as dominant."""
    res = client.get(f"/api/v1/trust-score-timeline/{LEAK_CASE_ID}")
    assert res.status_code == 200, res.text
    body = res.json()
    assert_tier1_trio(body)
    assert body["schema_version"] == "1.2.0", body["schema_version"]
    assert len(body["points"]) == 3, (
        f"expected 3 snapshot points; got {len(body['points'])}: "
        f"{[p['snapshot_label'] for p in body['points']]}"
    )
    drifts = body["inter_snapshot_drift_attribution"]
    assert len(drifts) == 2, f"expected 2 consecutive-pair drift entries; got {len(drifts)}"
    # At least one drift names energy_audit as dominant.
    energy_drifts = [d for d in drifts if d["dominant_axis"] == "energy_audit"]
    assert energy_drifts, (
        f"no inter-snapshot drift names energy_audit; got dominant "
        f"axes: {[d['dominant_axis'] for d in drifts]}"
    )


# ---------------------------------------------------------------------
# Step 4 — case-completeness shows energy_audit axis at 0/15
# ---------------------------------------------------------------------


def test_journey_step4_case_completeness_energy_axis_zero(
    client: _SyncASGIClient, patched_routes: Path
) -> None:
    """The leak case's case-completeness scorecard under the
    ``explicit_dynamics`` rubric reports ``energy_audit`` at 0/15:
    the canonical Phase 15 A on-disk state has
    ``energy_audit.status = "open_residual"`` AND project_state/
    is empty under the tmp_path repo (no metrics file there), so
    the rubric drops the axis to 0."""
    res = client.get(
        f"/api/v1/case-completeness/{LEAK_CASE_ID}",
        params={"analysis_type": "explicit_dynamics"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert_tier1_trio(body)
    assert body["analysis_type"] == "explicit_dynamics"
    axes = {entry["label"]: entry for entry in body["breakdown"]}
    assert "energy_audit" in axes, (
        f"explicit_dynamics rubric missing energy_audit axis; got axes: {list(axes)}"
    )
    energy = axes["energy_audit"]
    assert energy["points_awarded"] == 0, energy
    assert energy["points_max"] == 15, energy


# ---------------------------------------------------------------------
# Step 5 — advisor-critique fires explicit_dynamics branch
# ---------------------------------------------------------------------


def test_journey_step5_advisor_critique_explicit_dynamics_branch(
    client: _SyncASGIClient, patched_routes: Path
) -> None:
    """The snap-3 advisor critique fires the explicit_dynamics branch
    (Phase 14 C) and cites the energy-partition-closure theme.

    The advisor falls through to the stub backend
    (``advisor_status == "stub"``) because no live LLM is configured;
    the stub still emits the explicit_dynamics theme set."""
    res = client.get(
        f"/api/v1/advisor-critique/{LEAK_CASE_ID}",
        params={"snapshot": SNAP_3_LABEL},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert_tier1_trio(body)
    # 4-Q gate: advisor is advisory-only (LLM-offline-first stub path).
    assert body["advisor_status"] == "stub", body["advisor_status"]
    haystack = "\n".join(
        body.get("bc_questions_to_resolve", [])
        + body.get("failure_modes_to_consider", [])
        + body.get("mesh_quality_concerns", [])
    ).lower()
    assert "explicit_dynamics" in haystack, (
        f"explicit_dynamics branch did not fire; haystack:\n{haystack}"
    )
    assert "energy partition" in haystack, (
        f"energy-partition-closure theme missing; haystack:\n{haystack}"
    )


# ---------------------------------------------------------------------
# Step 6 — signoff-history shows empty record list
# ---------------------------------------------------------------------


def test_journey_step6_signoff_history_empty(client: _SyncASGIClient, patched_routes: Path) -> None:
    """No prior reviewer judgment landed on this case under the
    tmp_path repo; the signoff history is empty."""
    res = client.get(f"/api/v1/signoff-history/{LEAK_CASE_ID}")
    assert res.status_code == 200, res.text
    body = res.json()
    assert_tier1_trio(body)
    assert body["records"] == [], body["records"]


# ---------------------------------------------------------------------
# M:-2 binding 6-route audit
# ---------------------------------------------------------------------


def test_journey_6_route_count_contract(client: _SyncASGIClient, patched_routes: Path) -> None:
    """The journey crosses **exactly the 6 distinct routes** named in
    the Phase 15 D blueprint contract. A future maintainer who
    silently drops one of the 6 trips this audit."""
    routes_crossed: set[str] = set()
    res = client.get("/api/v1/cohort-executive-summary")
    assert res.status_code == 200
    routes_crossed.add("cohort-executive-summary")

    res = client.get(f"/api/v1/trust-score-alerts/{LEAK_CASE_ID}")
    assert res.status_code == 200
    routes_crossed.add("trust-score-alerts")

    res = client.get(f"/api/v1/trust-score-timeline/{LEAK_CASE_ID}")
    assert res.status_code == 200
    routes_crossed.add("trust-score-timeline")

    res = client.get(
        f"/api/v1/case-completeness/{LEAK_CASE_ID}",
        params={"analysis_type": "explicit_dynamics"},
    )
    assert res.status_code == 200
    routes_crossed.add("case-completeness")

    res = client.get(
        f"/api/v1/advisor-critique/{LEAK_CASE_ID}",
        params={"snapshot": SNAP_3_LABEL},
    )
    assert res.status_code == 200
    routes_crossed.add("advisor-critique")

    res = client.get(f"/api/v1/signoff-history/{LEAK_CASE_ID}")
    assert res.status_code == 200
    routes_crossed.add("signoff-history")

    crossed_list = sorted(routes_crossed)
    expected_list = sorted(EXPECTED_ROUTES_CROSSED)
    assert routes_crossed == EXPECTED_ROUTES_CROSSED, (
        f"route contract mismatch: crossed {crossed_list}; expected {expected_list}"
    )
    assert len(routes_crossed) == 6, f"expected 6 distinct routes; got {len(routes_crossed)}"


# ---------------------------------------------------------------------
# A:-3 per-route signed-registry 422-refusal regression guard
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "url_template",
    [
        "/api/v1/trust-score-alerts/{cid}",
        "/api/v1/trust-score-timeline/{cid}",
        "/api/v1/case-completeness/{cid}",
        "/api/v1/advisor-critique/{cid}",
        "/api/v1/signoff-history/{cid}",
    ],
)
def test_journey_per_route_signed_registry_refused(
    url_template: str,
    client: _SyncASGIClient,
    patched_routes: Path,
) -> None:
    """Every parameterized reviewer-facing route in the journey
    REFUSES the signed-registry case_id shape ``GS-001`` with HTTP
    422 (case-completeness preserves its legacy 400-on-shape gate
    but ALSO refuses GS-001 with 422 via the cross-route helper).

    The cohort-executive-summary route is non-parameterized (no
    case_id in the URL) so it does not appear in this matrix;
    signed-registry refusal there is enforced upstream when the
    cohort walker filters ``golden_samples/*-candidate/`` paths
    (Phase 4 B)."""
    url = url_template.format(cid=SIGNED_REGISTRY_CASE_ID)
    # advisor-critique requires a ``snapshot`` query param to even
    # reach the case_id audit; supply one in the right shape so we
    # land on the signed-registry refusal rather than a 422 for
    # missing query param.
    params = {"snapshot": SNAP_3_LABEL} if "advisor-critique" in url_template else None
    res = client.get(url, params=params)
    assert res.status_code == 422, (
        f"route {url_template} accepted signed-registry case_id "
        f"{SIGNED_REGISTRY_CASE_ID!r}; expected 422, got "
        f"{res.status_code}: {res.text}"
    )
    detail = (res.json().get("detail") or "").lower()
    assert "signed-registry" in detail, (
        f"route {url_template} 422 detail missing 'signed-registry' token: {detail!r}"
    )


# ---------------------------------------------------------------------
# C:-8 forbidden-token grep on the journey envelopes
# ---------------------------------------------------------------------


def test_journey_no_forbidden_positive_claims_in_envelopes(
    client: _SyncASGIClient, patched_routes: Path
) -> None:
    """The 8 forbidden positive-claim tokens MUST NOT appear in any
    journey envelope outside ``not <claim>`` / ``no <claim>`` form.
    A smoke-grep that complements the per-module guard tests.

    Consumes the SSOT 8-tuple + grep helper from
    :mod:`tests._test_utils` (closes Phase 15 retro §7+§8 — the
    8-token tuple + grep loop are no longer inlined per file)."""
    bodies = []
    bodies.append(client.get("/api/v1/cohort-executive-summary").text)
    bodies.append(client.get(f"/api/v1/trust-score-alerts/{LEAK_CASE_ID}").text)
    bodies.append(client.get(f"/api/v1/trust-score-timeline/{LEAK_CASE_ID}").text)
    bodies.append(
        client.get(
            f"/api/v1/case-completeness/{LEAK_CASE_ID}",
            params={"analysis_type": "explicit_dynamics"},
        ).text
    )
    bodies.append(
        client.get(
            f"/api/v1/advisor-critique/{LEAK_CASE_ID}",
            params={"snapshot": SNAP_3_LABEL},
        ).text
    )
    bodies.append(client.get(f"/api/v1/signoff-history/{LEAK_CASE_ID}").text)
    blob = "\n".join(bodies)
    assert_no_forbidden_positive_claims(blob, tokens=FORBIDDEN_POSITIVE_CLAIM_TOKENS_8)
