"""FM-04a Phase 9 F — E2E reviewer journeys.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Three load-bearing reviewer journeys that compose Phase 5/6/7/8/9
surfaces end-to-end across the HTTP layer.

  1. test_phase9_post_signoff_round_trip_e2e — POST a signoff via
     HTTP; GET the history; verify it surfaces; then re-fetch the
     cohort summary and confirm the bucket flipped.

  2. test_phase9_generator_provenance_e2e — write a snapshot with a
     generator script; fetch the provenance trace; verify the
     generator row's SHA matches the bytes on disk.

  3. test_phase9_trend_z_score_orthogonality_e2e — write 5 descending
     snapshots for one case; fetch trend anomalies (must fire on
     completeness); fetch z-score anomalies (must NOT fire because
     cohort size 1 < COHORT_MIN_SIZE_FOR_ANOMALY); proves
     orthogonality of the two surfaces.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from app.api.routes import (
    cohort_anomalies as anomalies_module,
)
from app.api.routes import (
    cohort_executive_summary as exec_module,
)
from app.api.routes import (
    cohort_trend_anomalies as trend_module,
)
from app.api.routes import (
    signoff_history as signoff_module,
)
from app.api.routes import (
    trust_score_provenance as provenance_module,
)
from app.main import app
from app.services.reporting.cohort_snapshot import (
    SnapshotCaseInput,
    write_cohort_snapshot,
)


class _SyncASGIClient:
    def __init__(self, asgi_app: Any) -> None:
        self._transport = httpx.ASGITransport(app=asgi_app)

    def get(self, url: str, params: dict | None = None) -> httpx.Response:
        async def _run() -> httpx.Response:
            async with httpx.AsyncClient(
                transport=self._transport, base_url="http://testserver"
            ) as client:
                return await client.get(url, params=params)

        return asyncio.run(_run())

    def post(self, url: str, *, json_body: Any) -> httpx.Response:
        async def _run() -> httpx.Response:
            async with httpx.AsyncClient(
                transport=self._transport, base_url="http://testserver"
            ) as client:
                return await client.post(url, json=json_body)

        return asyncio.run(_run())


@pytest.fixture()
def client() -> _SyncASGIClient:
    return _SyncASGIClient(app)


@pytest.fixture()
def fake_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(signoff_module, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(provenance_module, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(exec_module, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(anomalies_module, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(trend_module, "_repo_root", lambda: tmp_path)
    return tmp_path


def _seed_case(
    root: Path,
    case_id: str,
    *,
    generator_body: bytes = b"# generator placeholder\n",
) -> SnapshotCaseInput:
    case_dir = root / "golden_samples" / case_id / "data"
    case_dir.mkdir(parents=True, exist_ok=True)
    starter = case_dir / "model_00_0000.rad"
    engine = case_dir / "model_00_0001.rad"
    starter.write_text("# s", encoding="utf-8")
    engine.write_text("# e", encoding="utf-8")
    metrics = (
        root / "project_state" / "graph_executor" / case_id / "ballistic" / "ballistic_metrics.json"
    )
    metrics.parent.mkdir(parents=True, exist_ok=True)
    metrics.write_text(
        json.dumps({"case_id": case_id, "claim_boundary": "tier1"}), encoding="utf-8"
    )
    generator = root / "scripts" / f"gen_{case_id.lower().replace('-', '_')}.py"
    generator.parent.mkdir(parents=True, exist_ok=True)
    generator.write_bytes(generator_body)
    return SnapshotCaseInput(
        case_id=case_id,
        starter_deck_path=starter,
        engine_deck_path=engine,
        ballistic_metrics_path=metrics,
        convergence_study_path=None,
        animation_manifest_path=None,
        result_mesh_path=None,
        generator_script_path=generator,
        notes_path=None,
    )


def _seed_snapshot_with_score(
    root: Path,
    case_id: str,
    label: str,
    score: int,
    *,
    generator_body: bytes = b"# generator placeholder\n",
) -> None:
    case = _seed_case(root, case_id, generator_body=generator_body)
    write_cohort_snapshot([case], repo_root=root, snapshot_label=label)
    comp_path = root / "reports" / "snapshots" / label / "completeness" / f"{case_id}.json"
    payload = json.loads(comp_path.read_text(encoding="utf-8"))
    payload["score"] = score
    comp_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


# ---------------------------------------------------------------------
# E2E #1 — POST signoff round-trip → cohort summary mirror
# ---------------------------------------------------------------------


def test_phase9_post_signoff_round_trip_e2e(client: _SyncASGIClient, fake_repo: Path) -> None:
    """Reviewer journey: POST a signoff over HTTP, GET the history,
    re-fetch cohort executive summary and confirm the bucket flipped.

    Tier 1 engineering candidate; not signed validation; not benchmark agreement.
    """
    _seed_snapshot_with_score(fake_repo, "GS-A-candidate", "2026-05-16T100000Z", 90)

    # 1) Cohort summary pre-signoff: no verdict yet (bucket depends on
    # trust score sum across all 4 axes; we don't pin it precisely
    # here, only the no-signoff invariant).
    pre = client.get("/api/v1/cohort-executive-summary").json()
    row_pre = next(c for c in pre["cases"] if c["case_id"] == "GS-A-candidate")
    assert row_pre["latest_signoff_verdict"] is None
    starting_bucket = row_pre["bucket"]

    # 2) POST a blocked_pending_input signoff
    post_res = client.post(
        "/api/v1/signoff-history/GS-A-candidate",
        json_body={
            "reviewer": "alice",
            "verdict": "blocked_pending_input",
            "notes": "waiting on material card",
        },
    )
    assert post_res.status_code == 200
    posted = post_res.json()
    assert posted["verdict"] == "blocked_pending_input"

    # 3) GET history confirms the record is queryable
    history = client.get("/api/v1/signoff-history/GS-A-candidate").json()
    assert history["record_count"] == 1
    assert history["records"][0]["reviewer"] == "alice"

    # 4) Cohort summary post-signoff: blocked_pending_input is rule #1
    # in the precedence ladder; bucket flips to regressed regardless of
    # the starting bucket.
    post_sum = client.get("/api/v1/cohort-executive-summary").json()
    row_post = next(c for c in post_sum["cases"] if c["case_id"] == "GS-A-candidate")
    assert row_post["latest_signoff_verdict"] == "blocked_pending_input"
    assert row_post["bucket"] == "regressed"
    # If the starting bucket was already regressed (low trust score),
    # the verdict still landed; if it was watching/healthy, the verdict
    # forced regressed. Either path closes the carry-forward.
    assert starting_bucket in {"healthy", "watching", "regressed"}

    # 5) Tier 1 disclaimer trio in every response body
    for body_text in (
        post_res.text,
        history,
        post_sum,
    ):
        body_lower = (body_text if isinstance(body_text, str) else json.dumps(body_text)).lower()
        assert "tier 1 engineering candidate" in body_lower
        assert "not signed validation" in body_lower
        assert "not benchmark agreement" in body_lower


# ---------------------------------------------------------------------
# E2E #2 — Generator-frozen provenance
# ---------------------------------------------------------------------


def test_phase9_generator_provenance_e2e(client: _SyncASGIClient, fake_repo: Path) -> None:
    """Reviewer journey: write a snapshot with a generator script; fetch
    the provenance trace; verify the generator row's SHA matches the
    captured bytes on disk.

    Tier 1 engineering candidate; not signed validation; not benchmark agreement.
    """
    body = b"# slice 9-F E2E #2 generator script\nprint('frozen')\n"
    _seed_snapshot_with_score(
        fake_repo,
        "GS-A-candidate",
        "2026-05-16T100000Z",
        87,
        generator_body=body,
    )

    res = client.get(
        "/api/v1/trust-score-provenance/GS-A-candidate",
        params={"snapshot": "2026-05-16T100000Z"},
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["schema_version"] == "1.1.0"

    gen_row = next(i for i in payload["inputs"] if i["kind"] == "generator")
    assert gen_row["present"] is True
    captured = (
        fake_repo
        / "reports"
        / "snapshots"
        / "2026-05-16T100000Z"
        / "generator"
        / "GS-A-candidate.py"
    )
    captured_bytes = captured.read_bytes()
    assert captured_bytes == body
    assert gen_row["sha256"] == hashlib.sha256(captured_bytes).hexdigest()

    # Every other input row has present True or False with consistent SHA
    # treatment (None when missing, full SHA when captured).
    for input_entry in payload["inputs"]:
        if input_entry["present"]:
            on_disk = (
                fake_repo / "reports" / "snapshots" / "2026-05-16T100000Z" / input_entry["path"]
            )
            assert on_disk.is_file()
            assert input_entry["sha256"] == hashlib.sha256(on_disk.read_bytes()).hexdigest()
        else:
            assert input_entry["sha256"] is None

    body_lower = res.text.lower()
    assert "tier 1 engineering candidate" in body_lower
    assert "not signed validation" in body_lower
    assert "not benchmark agreement" in body_lower


# ---------------------------------------------------------------------
# E2E #3 — Trend / z-score orthogonality
# ---------------------------------------------------------------------


def test_phase9_trend_z_score_orthogonality_e2e(client: _SyncASGIClient, fake_repo: Path) -> None:
    """Reviewer journey: write 5 descending snapshots for a single case.

    * GET /api/v1/cohort-trend-anomalies MUST fire (slope is steeply
      negative, well past TREND_SLOPE_DANGER_MAX).
    * GET /api/v1/cohort-anomalies MUST NOT fire (cohort size 1 is
      below COHORT_MIN_SIZE_FOR_ANOMALY=3).

    This is the load-bearing proof that the two surfaces answer
    different reviewer questions and a case can fire one without the
    other.

    Tier 1 engineering candidate; not signed validation; not benchmark agreement.
    """
    for offset, score in enumerate([90, 80, 70, 60, 50]):
        label = f"2026-05-{16 + offset:02d}T100000Z"
        _seed_snapshot_with_score(fake_repo, "GS-A-candidate", label, score)

    trend = client.get("/api/v1/cohort-trend-anomalies").json()
    zscore = client.get("/api/v1/cohort-anomalies").json()

    assert trend["cohort_count"] == 1
    assert trend["anomaly_count"] >= 1, "trend must fire on a 5-snapshot descending timeline"
    completeness_events = [a for a in trend["anomalies"] if a["axis"] == "completeness"]
    assert len(completeness_events) == 1
    assert completeness_events[0]["case_id"] == "GS-A-candidate"
    assert completeness_events[0]["severity"] in {"warn", "danger"}

    assert zscore["cohort_count"] == 1
    assert zscore["anomaly_count"] == 0, (
        "z-score MUST NOT fire on cohort size 1 (below COHORT_MIN_SIZE_FOR_ANOMALY)"
    )

    # Tier 1 disclaimer trio on both responses
    for payload_text in (trend, zscore):
        body_lower = json.dumps(payload_text).lower()
        assert "tier 1 engineering candidate" in body_lower
        assert "not signed validation" in body_lower
        assert "not benchmark agreement" in body_lower
