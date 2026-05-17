"""FM-04a Phase 16 D — Journey 1: drift_attribution audit trail E2E.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

A reviewer-journey test that walks the Phase 16 ``drift_attribution``
surface end-to-end across **4 distinct routes** carrying the new
field (cohort + cumulative + per-pair + signoff-pinned). The
reviewer:

  1. Opens ``cohort-anomalies`` and observes the Phase 16 B
     ``cohort_drift_attribution`` field. The cohort SSOT (5 cases,
     1 evolving leak case) yields a non-null cohort-scope dominant
     axis naming ``energy_audit`` and ``dominant_case_id`` ==
     the leak case (the cohort-wide latest-pair transition is
     snap-2 → snap-3 = 15 → 0 on the energy axis = -100.0%).
  2. Drills into the leak case's ``trust-score-timeline`` and sees
     BOTH the per-pair ``inter_snapshot_drift_attribution`` (Phase
     15 C) AND the new Phase 16 A ``cumulative_drift_attribution``
     spanning snap-1 → snap-3 (=full 15→0 collapse).
  3. Pulls the empty ``signoff-history`` (no prior judgment landed
     on this tmp_path repo).
  4. POSTs a new ``hold_for_followup`` signoff via
     ``signoff-history``.
  5. Re-GETs ``signoff-history`` and sees the new record carries
     the Phase 16 C ``drift_attribution_at_signoff_time`` field
     (server-computed at write time from the latest snapshot
     pair, NOT client-supplied).

Anti-gaming guards pinned (per Phase 16 binding rubric §3.D):

* **M:-2** — the journey carries an explicit ``routes_crossed`` set
  tagged with the 4 distinct route names (the load-bearing route
  count is the binding number, separate from the narrative).
* **T:-3** — boundary pins (NOT >= bounds):
    * cohort-scope dominant axis == ``energy_audit`` AND
      ``dominant_case_id`` == ``LEAK_CASE_ID`` AND
      ``cohort_max_abs_delta_pct`` == 100.0 exactly.
    * timeline cumulative ``dominant_axis`` == ``energy_audit``
      AND ``dominant_delta_pct`` == -100.0 exactly.
    * signoff ``drift_attribution_at_signoff_time.dominant_axis``
      == ``energy_audit`` AND ``dominant_delta_pct`` == -100.0
      exactly (snap-2 → snap-3 transition, the latest pair at
      signoff time).
* **C:-8** — every 200 envelope in the journey carries the Tier 1
  disclaimer trio (verified via the SSOT
  :func:`tests._test_utils.assert_tier1_trio`); the 9-token
  forbidden-positive-claim discipline holds across all 4 envelopes.
* **A:-3** — signed-registry ``GS-001`` is refused on the 3
  parameterized routes the journey touches (cohort-anomalies has
  no case_id in URL; signed-registry refusal there is upstream).
* **A:-3 server-computed** — the POST request DOES NOT carry any
  ``drift_attribution_at_signoff_time`` field in its body; the
  field appears in the GET response strictly because the service
  layer computed it from the snapshot tree (pinned via runtime
  body audit).
* **E:-2** — no real-solver invocation; no real-LLM call.
* **V:-3** — the snapshot tree is written ENTIRELY under tmp_path.
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
from app.api.routes import signoff_history as signoff_history_route
from app.api.routes import trust_score_timeline as trust_score_timeline_route
from app.main import app
from app.services.reporting.cohort_snapshot import (
    SnapshotCaseInput,
    write_cohort_snapshot,
)

from tests._test_utils import assert_no_forbidden_positive_claims, assert_tier1_trio

REPO_ROOT = Path(__file__).resolve().parent.parent

# Phase 16 D Journey 1 cohort SSOT — same 5-case shape as Phase 15 D
# Journey 2 (3 explicit_dynamics + 2 linear_static_pv) so the cohort
# >= COHORT_MIN_SIZE_FOR_ANOMALY (3) and the leak case's evolution
# stands out against 4 flat cases at the latest snapshot pair.
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
# Phase 16 D Journey 1 arc-shape choice (DIFFERS from Phase 15 D Journey
# 2's arc): snap-1 and snap-2 BOTH carry the CLEAN leak variant
# (energy_audit closed = 15). Snap-3 is the regressed variant (energy
# 0 + optional artifacts omitted). This shape places the dramatic
# energy collapse on the LATEST snapshot pair (snap-2 → snap-3),
# which is the pair used by the Phase 16 B cohort_drift_attribution
# and the Phase 16 C signoff drift_attribution_at_signoff_time pins.
# Phase 15 D Journey 2's arc placed the collapse on snap-1 → snap-2
# instead, which is correct for that journey's per-pair audit but
# would land cohort_drift on the COMPLETENESS axis here (energy is
# already 0 at snap-2 in that shape, so snap-2 → snap-3 carries only
# the artifact-drop completeness delta). Both arcs are valid Tier 1
# evidence; they exercise the surface at different transitions.
SNAP_1_LABEL = "2026-05-17T100000Z"  # leak CLEAN (energy 15)
SNAP_2_LABEL = "2026-05-17T120000Z"  # leak CLEAN (energy 15)
SNAP_3_LABEL = "2026-05-17T140000Z"  # leak REGRESSED (energy 0 + artifacts dropped)

SIGNED_REGISTRY_CASE_ID = "GS-001"

# Phase 16 D Journey 1 route contract. The 4 distinct routes that
# carry the drift_attribution surface end-to-end.
EXPECTED_ROUTES_CROSSED: frozenset[str] = frozenset(
    {
        "cohort-anomalies",
        "trust-score-timeline",
        "signoff-history-GET",
        "signoff-history-POST",
    }
)


# ---------------------------------------------------------------------
# Sync ASGI client (mirrors Phase 15 D)
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


# ---------------------------------------------------------------------
# Fixture seeding — same shape as Phase 15 D Journey 2
# ---------------------------------------------------------------------


def _stub_path(tmp: Path, name: str) -> Path:
    p = tmp / name
    if not p.exists():
        p.write_text("# stub artifact for Phase 16 D journey 1", encoding="utf-8")
    return p


def _explicit_dynamics_healthy_input(tmp: Path, case_id: str) -> SnapshotCaseInput:
    fixture = tmp / "golden_samples" / case_id
    return SnapshotCaseInput(
        case_id=case_id,
        starter_deck_path=fixture / "data" / "model_00_0000.rad",
        engine_deck_path=fixture / "data" / "model_00_0001.rad",
        ballistic_metrics_path=fixture / "data" / "ballistic_metrics.json",
        convergence_study_path=fixture / "data" / "convergence_study.json",
        animation_manifest_path=fixture / "data" / "animation_manifest.json",
        result_mesh_path=None,
        generator_script_path=_stub_path(tmp, f"gen_{case_id.replace('-', '_')}_deck.py"),
        notes_path=fixture / "NOTES.md",
        analysis_type="explicit_dynamics",
    )


def _pv_case_input(tmp: Path, case_id: str) -> SnapshotCaseInput:
    fixture = tmp / "golden_samples" / case_id
    starter = fixture / "data" / "model_00_0000.rad"
    engine = fixture / "data" / "model_00_0001.rad"
    generator = fixture / "data" / "generator.py"
    return SnapshotCaseInput(
        case_id=case_id,
        starter_deck_path=starter
        if starter.is_file()
        else _stub_path(tmp, f"{case_id}_starter.rad"),
        engine_deck_path=engine if engine.is_file() else _stub_path(tmp, f"{case_id}_engine.rad"),
        ballistic_metrics_path=fixture / "data" / "ballistic_metrics.json",
        convergence_study_path=fixture / "data" / "convergence_study.json",
        animation_manifest_path=None,
        result_mesh_path=None,
        generator_script_path=generator
        if generator.is_file()
        else _stub_path(tmp, f"{case_id}_gen.py"),
        notes_path=None,
        analysis_type="linear_static_pv",
    )


def _clean_leak_case_input(tmp: Path, case_id: str) -> SnapshotCaseInput:
    """snap-1 healthy variant of the leak case (energy_audit closed)."""
    fixture = tmp / "golden_samples" / case_id
    metrics_src = fixture / "data" / "ballistic_metrics.json"
    payload = json.loads(metrics_src.read_text(encoding="utf-8"))
    payload["energy_audit"]["status"] = "closed_aggregate"
    payload["energy_audit"]["rationale"] = (
        "Tier 1 candidate snap-1 healthy state. Not signed validation; not benchmark agreement."
    )
    clean_dir = tmp / "phase16d_journey1_snap1_clean" / case_id
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
        case_id=case_id,
        starter_deck_path=fixture / "data" / "model_00_0000.rad",
        engine_deck_path=fixture / "data" / "model_00_0001.rad",
        ballistic_metrics_path=clean_metrics,
        convergence_study_path=clean_conv,
        animation_manifest_path=fixture / "data" / "animation_manifest.json",
        result_mesh_path=None,
        generator_script_path=_stub_path(tmp, f"gen_{case_id.replace('-', '_')}_deck.py"),
        notes_path=fixture / "NOTES.md",
        analysis_type="explicit_dynamics",
    )


def _regressed_leak_case_input(tmp: Path, case_id: str) -> SnapshotCaseInput:
    """snap-3 regressed variant of the leak case."""
    fixture = tmp / "golden_samples" / case_id
    return SnapshotCaseInput(
        case_id=case_id,
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

    tmp = tmp_path_factory.mktemp("phase16d_journey1_repo")
    golden = tmp / "golden_samples"
    golden.mkdir(parents=True)
    for case_id, _atype in COHORT_CASES:
        shutil.copytree(REPO_ROOT / "golden_samples" / case_id, golden / case_id)

    # Snap-1: all 5 healthy (leak case in CLEAN variant).
    snap1 = [
        _explicit_dynamics_healthy_input(tmp, "rod-wave-impact-candidate"),
        _explicit_dynamics_healthy_input(tmp, "rod-wave-impact-stiff-candidate"),
        _clean_leak_case_input(tmp, LEAK_CASE_ID),
        _pv_case_input(tmp, "cylinder-pv-candidate"),
        _pv_case_input(tmp, "cylinder-pv-extended-candidate"),
    ]
    write_cohort_snapshot(snap1, repo_root=tmp, snapshot_label=SNAP_1_LABEL)

    # Snap-2: leak still CLEAN (energy 15). Others flat. Phase 16 D
    # Journey 1 arc-shape choice: keep the leak in clean state at
    # snap-2 so the dramatic energy collapse lands on snap-2 → snap-3
    # (the LATEST pair used by cohort_drift_attribution and the
    # signoff drift_attribution_at_signoff_time pin).
    snap2 = [
        _explicit_dynamics_healthy_input(tmp, "rod-wave-impact-candidate"),
        _explicit_dynamics_healthy_input(tmp, "rod-wave-impact-stiff-candidate"),
        _clean_leak_case_input(tmp, LEAK_CASE_ID),
        _pv_case_input(tmp, "cylinder-pv-candidate"),
        _pv_case_input(tmp, "cylinder-pv-extended-candidate"),
    ]
    write_cohort_snapshot(snap2, repo_root=tmp, snapshot_label=SNAP_2_LABEL)

    # Snap-3: leak regressed (canonical state + 3 optional artifacts
    # omitted, dropping the trust below the 50-pt floor).
    snap3 = [
        _explicit_dynamics_healthy_input(tmp, "rod-wave-impact-candidate"),
        _explicit_dynamics_healthy_input(tmp, "rod-wave-impact-stiff-candidate"),
        _regressed_leak_case_input(tmp, LEAK_CASE_ID),
        _pv_case_input(tmp, "cylinder-pv-candidate"),
        _pv_case_input(tmp, "cylinder-pv-extended-candidate"),
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
        trust_score_timeline_route,
        signoff_history_route,
    ):
        monkeypatch.setattr(route_module, "_repo_root", lambda r=journey_repo: r)
    return journey_repo


# ---------------------------------------------------------------------
# Step 1 — cohort-anomalies carries Phase 16 B cohort_drift_attribution
# ---------------------------------------------------------------------


def test_journey_step1_cohort_anomalies_carries_cohort_drift(
    client: _SyncASGIClient, patched_routes: Path
) -> None:
    """The cohort-anomalies envelope carries the new Phase 16 B
    ``cohort_drift_attribution`` field. The 5-case cohort's latest
    snapshot pair (snap-2 → snap-3) is dominated by the leak case's
    energy_audit axis collapse (15 → 0 = -100.0%).

    Boundary pins (T:-3):
      * cohort_drift_attribution.cohort_dominant_axis == "energy_audit"
      * cohort_drift_attribution.dominant_case_id == LEAK_CASE_ID
      * cohort_drift_attribution.cohort_max_abs_delta_pct == 100.0
    """
    res = client.get("/api/v1/cohort-anomalies")
    assert res.status_code == 200, res.text
    body = res.json()
    assert_tier1_trio(body)
    # Phase 17 A bumped cohort-anomalies 1.1.0 → 1.2.0 additively
    # (cohort_cumulative_drift_attribution field). The Phase 16 B
    # cohort_drift_attribution field is preserved at 1.2.0.
    assert body["schema_version"] == "1.2.0", body["schema_version"]
    drift = body.get("cohort_drift_attribution")
    assert drift is not None, (
        f"cohort-anomalies envelope missing cohort_drift_attribution; keys: {sorted(body.keys())}"
    )
    assert drift["cohort_dominant_axis"] == "energy_audit", drift
    assert drift["dominant_case_id"] == LEAK_CASE_ID, drift
    assert drift["cohort_max_abs_delta_pct"] == 100.0, drift
    # The per-case attribution tuple includes the leak case.
    per_case_ids = {c["case_id"] for c in drift["per_case_drift_attribution"]}
    assert LEAK_CASE_ID in per_case_ids, (
        f"leak case missing from per_case_drift_attribution; got cases {sorted(per_case_ids)}"
    )
    # The cohort-wide latest pair labels match the snapshot SSOT.
    assert drift["from_snapshot"] == SNAP_2_LABEL, drift
    assert drift["to_snapshot"] == SNAP_3_LABEL, drift


# ---------------------------------------------------------------------
# Step 2 — trust-score-timeline carries Phase 16 A cumulative_drift
# ---------------------------------------------------------------------


def test_journey_step2_trust_score_timeline_carries_cumulative_drift(
    client: _SyncASGIClient, patched_routes: Path
) -> None:
    """The leak case's trust-score-timeline carries BOTH the per-pair
    ``inter_snapshot_drift_attribution`` (Phase 15 C) AND the new
    Phase 16 A ``cumulative_drift_attribution`` spanning snap-1 →
    snap-3 (=full 15 → 0 energy-axis collapse).

    Boundary pins (T:-3):
      * len(points) == 3
      * len(inter_snapshot_drift_attribution) == 2
      * cumulative_drift_attribution.dominant_axis == "energy_audit"
      * cumulative_drift_attribution.dominant_delta_pct == -100.0
      * cumulative_drift_attribution.from_snapshot == SNAP_1_LABEL
      * cumulative_drift_attribution.to_snapshot == SNAP_3_LABEL
    """
    res = client.get(f"/api/v1/trust-score-timeline/{LEAK_CASE_ID}")
    assert res.status_code == 200, res.text
    body = res.json()
    assert_tier1_trio(body)
    assert body["schema_version"] == "1.2.0", body["schema_version"]
    assert len(body["points"]) == 3, len(body["points"])
    assert len(body["inter_snapshot_drift_attribution"]) == 2, body[
        "inter_snapshot_drift_attribution"
    ]
    cumulative = body.get("cumulative_drift_attribution")
    assert cumulative is not None, (
        f"timeline missing cumulative_drift_attribution; keys: {sorted(body.keys())}"
    )
    assert cumulative["dominant_axis"] == "energy_audit", cumulative
    assert cumulative["dominant_delta_pct"] == -100.0, cumulative
    assert cumulative["from_snapshot"] == SNAP_1_LABEL, cumulative
    assert cumulative["to_snapshot"] == SNAP_3_LABEL, cumulative


# ---------------------------------------------------------------------
# Step 3 — signoff-history GET initially empty
# ---------------------------------------------------------------------


def test_journey_step3_signoff_history_empty_before_post(
    client: _SyncASGIClient, patched_routes: Path
) -> None:
    """No prior reviewer judgment landed on this case under the
    tmp_path repo; the signoff history is empty before the POST."""
    res = client.get(f"/api/v1/signoff-history/{LEAK_CASE_ID}")
    assert res.status_code == 200, res.text
    body = res.json()
    assert_tier1_trio(body)
    assert body["records"] == [], body["records"]


# ---------------------------------------------------------------------
# Step 4 — signoff-history POST without client-supplied drift
# ---------------------------------------------------------------------


SIGNOFF_BODY: dict[str, Any] = {
    "reviewer": "phase16-journey-reviewer",
    "verdict": "needs_more_evidence",
    "notes": (
        "Tier 1 engineering candidate review under the Phase 16 D journey; "
        "energy axis collapsed under the leak arc. Not signed validation; "
        "not benchmark agreement."
    ),
}


def test_journey_step4_signoff_post_succeeds_without_client_drift(
    client: _SyncASGIClient, patched_routes: Path
) -> None:
    """POST a new signoff. The request body carries NO
    ``drift_attribution_at_signoff_time`` field — the service layer
    is responsible for computing it from the snapshot tree at write
    time (A:-3 server-computed pin). The POST returns 200."""
    # A:-3 server-computed body audit: the client never supplies drift.
    assert "drift_attribution_at_signoff_time" not in SIGNOFF_BODY, SIGNOFF_BODY
    res = client.post(
        f"/api/v1/signoff-history/{LEAK_CASE_ID}",
        json_body=SIGNOFF_BODY,
        headers={"Content-Type": "application/json"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["case_id"] == LEAK_CASE_ID, body
    assert body["verdict"] == "needs_more_evidence", body
    assert body["reviewer"] == "phase16-journey-reviewer", body


# ---------------------------------------------------------------------
# Step 5 — signoff-history GET shows new record with drift pinned
# ---------------------------------------------------------------------


def test_journey_step5_signoff_history_get_shows_server_computed_drift(
    client: _SyncASGIClient, patched_routes: Path
) -> None:
    """After the POST, the signoff-history GET returns the new
    record with ``drift_attribution_at_signoff_time`` populated from
    the snap-2 → snap-3 transition (the latest snapshot pair at
    write time = the energy-axis -100.0% collapse).

    The Phase 16 D Journey 1 explicit step-ordering is module-scope
    `journey_repo` + function-scope `patched_routes` — Step 4 runs
    before Step 5 because pytest collects in file order; the on-disk
    signoff record persists in the module-scope tmp_path between
    test functions."""
    res = client.get(f"/api/v1/signoff-history/{LEAK_CASE_ID}")
    assert res.status_code == 200, res.text
    body = res.json()
    assert_tier1_trio(body)
    assert body["schema_version"] == "1.1.0", body["schema_version"]
    records = body["records"]
    assert len(records) == 1, (
        f"expected exactly 1 record after the POST; got {len(records)}: {records}"
    )
    record = records[0]
    assert record["verdict"] == "needs_more_evidence", record
    drift = record.get("drift_attribution_at_signoff_time")
    assert drift is not None, (
        f"record missing server-computed drift_attribution_at_signoff_time; "
        f"keys: {sorted(record.keys())}"
    )
    # T:-3 boundary pins: snap-2 → snap-3 transition exactly produces
    # -100.0% on energy_audit (the latest pair at signoff time).
    assert drift["dominant_axis"] == "energy_audit", drift
    assert drift["dominant_delta_pct"] == -100.0, drift
    assert drift["from_snapshot"] == SNAP_2_LABEL, drift
    assert drift["to_snapshot"] == SNAP_3_LABEL, drift


# ---------------------------------------------------------------------
# M:-2 binding 4-route audit
# ---------------------------------------------------------------------


def test_journey_4_route_count_contract(client: _SyncASGIClient, patched_routes: Path) -> None:
    """The journey crosses **exactly the 4 distinct route/verb pairs**
    named in the Phase 16 D blueprint contract. A future maintainer
    who silently drops one of the 4 trips this audit.

    The 4 routes correspond to the 4 envelopes carrying the new
    drift_attribution surface:
      * cohort-anomalies (Phase 16 B cohort_drift_attribution)
      * trust-score-timeline (Phase 16 A cumulative_drift_attribution)
      * signoff-history GET (Phase 16 C drift_attribution_at_signoff_time
        on rendered records)
      * signoff-history POST (the server-computed entry-point)
    """
    routes_crossed: set[str] = set()

    res = client.get("/api/v1/cohort-anomalies")
    assert res.status_code == 200
    routes_crossed.add("cohort-anomalies")

    res = client.get(f"/api/v1/trust-score-timeline/{LEAK_CASE_ID}")
    assert res.status_code == 200
    routes_crossed.add("trust-score-timeline")

    res = client.get(f"/api/v1/signoff-history/{LEAK_CASE_ID}")
    assert res.status_code == 200
    routes_crossed.add("signoff-history-GET")

    # Use a unique reviewer per route-audit call so the per-(case,
    # reviewer) sliding-window rate limit (Phase 10 D) does NOT trip
    # on the journey's earlier Step 4 POST. The route-existence
    # contract is independent of the reviewer identity; we just need
    # a 200.
    res = client.post(
        f"/api/v1/signoff-history/{LEAK_CASE_ID}",
        json_body={
            "reviewer": "phase16-route-audit-reviewer",
            "verdict": "needs_more_evidence",
            "notes": (
                "Phase 16 D route-count audit; the load-bearing assertion is the "
                "route's existence + 200 status. Not signed validation; not "
                "benchmark agreement."
            ),
        },
        headers={"Content-Type": "application/json"},
    )
    assert res.status_code == 200, res.text
    routes_crossed.add("signoff-history-POST")

    crossed_list = sorted(routes_crossed)
    expected_list = sorted(EXPECTED_ROUTES_CROSSED)
    assert routes_crossed == EXPECTED_ROUTES_CROSSED, (
        f"route contract mismatch: crossed {crossed_list}; expected {expected_list}"
    )
    assert len(routes_crossed) == 4, f"expected 4 distinct routes; got {len(routes_crossed)}"


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
    cohort-anomalies route is non-parameterized (no case_id in URL)
    so it is not in this matrix; signed-registry refusal there is
    upstream when the cohort walker filters
    ``golden_samples/*-candidate/`` paths (Phase 4 B)."""
    url = url_template.format(cid=SIGNED_REGISTRY_CASE_ID)
    if verb == "GET":
        res = client.get(url)
    elif verb == "POST":
        res = client.post(
            url,
            json_body={
                "reviewer": "phase16-signed-registry-probe",
                "verdict": "needs_more_evidence",
                "notes": "probe; not signed validation; not benchmark agreement.",
            },
            headers={"Content-Type": "application/json"},
        )
    else:
        raise AssertionError(f"unexpected verb {verb!r}")
    assert res.status_code == 422, (
        f"{verb} {url_template} accepted signed-registry case_id "
        f"{SIGNED_REGISTRY_CASE_ID!r}; expected 422, got {res.status_code}: {res.text}"
    )
    detail_raw = res.json().get("detail") or ""
    detail = (detail_raw if isinstance(detail_raw, str) else str(detail_raw)).lower()
    assert "signed-registry" in detail or "signed_registry" in detail, (
        f"{verb} {url_template} 422 detail missing 'signed-registry' token: {detail!r}"
    )


# ---------------------------------------------------------------------
# C:-8 forbidden-token grep on the journey envelopes (via SSOT helper)
# ---------------------------------------------------------------------


def test_journey_no_forbidden_positive_claims_in_envelopes(
    client: _SyncASGIClient, patched_routes: Path
) -> None:
    """The 8-token forbidden positive-claim tuple MUST NOT appear in
    any journey envelope outside ``not <claim>`` / ``no <claim>``
    form. Audits all 4 distinct envelopes via the SSOT
    :func:`tests._test_utils.assert_no_forbidden_positive_claims`
    (closes Phase 15 retro §7)."""
    bodies = [
        client.get("/api/v1/cohort-anomalies").text,
        client.get(f"/api/v1/trust-score-timeline/{LEAK_CASE_ID}").text,
        client.get(f"/api/v1/signoff-history/{LEAK_CASE_ID}").text,
    ]
    blob = "\n".join(bodies)
    assert_no_forbidden_positive_claims(blob)
