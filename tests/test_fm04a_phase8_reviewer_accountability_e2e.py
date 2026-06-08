"""FM-04a Phase 8 — E2E reviewer accountability journeys.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Three load-bearing reviewer journeys composing Phase 5/6/7/8
surfaces end-to-end across the HTTP layer.

  1. test_phase8_signoff_workflow_e2e — write 2 signoffs; fetch
     history; assert chronological order + envelope; verify the
     latest verdict matches.

  2. test_phase8_provenance_trace_e2e — write a snapshot; fetch
     trust score provenance; verify every input SHA matches the
     snapshot bytes; formula_version round-trips.

  3. test_phase8_cohort_outlier_and_signoff_e2e — write 7 candidate
     cases with one engineered outlier (completeness=10 vs rest~85);
     fetch cohort executive summary (cohort_count + buckets); fetch
     anomalies (z-score >2σ on completeness for the outlier); then
     write a blocked signoff on the outlier and re-fetch summary
     to see it flip into the regressed bucket.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import UTC, datetime
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
from app.services.reporting.signoff_record import write_signoff_record


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


@pytest.fixture()
def client() -> _SyncASGIClient:
    return _SyncASGIClient(app)


@pytest.fixture()
def fake_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(signoff_module, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(provenance_module, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(exec_module, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(anomalies_module, "_repo_root", lambda: tmp_path)
    return tmp_path


def _seed_case(root: Path, case_id: str) -> SnapshotCaseInput:
    case_dir = root / "golden_samples" / case_id / "data"
    case_dir.mkdir(parents=True, exist_ok=True)
    starter = case_dir / "model_00_0000.rad"
    engine = case_dir / "model_00_0001.rad"
    starter.write_text("# s", encoding="utf-8")
    engine.write_text("# e", encoding="utf-8")
    mp = (
        root / "project_state" / "graph_executor" / case_id / "ballistic" / "ballistic_metrics.json"
    )
    mp.parent.mkdir(parents=True, exist_ok=True)
    mp.write_text(json.dumps({"case_id": case_id, "claim_boundary": "tier1"}))
    gen = root / "scripts" / f"gen_{case_id.lower().replace('-', '_')}.py"
    gen.parent.mkdir(parents=True, exist_ok=True)
    gen.write_bytes(b"# g")
    return SnapshotCaseInput(
        case_id=case_id,
        starter_deck_path=starter,
        engine_deck_path=engine,
        ballistic_metrics_path=mp,
        convergence_study_path=None,
        animation_manifest_path=None,
        result_mesh_path=None,
        generator_script_path=gen,
        notes_path=None,
    )


def _seed_snapshot_with_completeness(root: Path, case_id: str, score: int, label: str) -> None:
    case = _seed_case(root, case_id)
    write_cohort_snapshot([case], repo_root=root, snapshot_label=label)
    comp_path = root / "reports" / "snapshots" / label / "completeness" / f"{case_id}.json"
    payload = json.loads(comp_path.read_text(encoding="utf-8"))
    payload["score"] = score
    comp_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


# ---------------------------------------------------------------------
# E2E #1 — Signoff workflow
# ---------------------------------------------------------------------


def test_phase8_signoff_workflow_e2e(client: _SyncASGIClient, fake_repo: Path) -> None:
    """Reviewer journey: write 2 signoffs across time; fetch history;
    verify chronological order + envelope; verify latest verdict.

    Tier 1 engineering candidate; not signed validation; not benchmark agreement.
    """
    write_signoff_record(
        "GS-A-candidate",
        "alice",
        "watching",
        "Initial monitoring round; awaiting more snapshots.",
        repo_root=fake_repo,
        now_utc=datetime(2026, 5, 16, 9, 0, 0, tzinfo=UTC),
    )
    write_signoff_record(
        "GS-A-candidate",
        "bob",
        "needs_more_convergence",
        "Mesh sweep too coarse; want finer dt.",
        repo_root=fake_repo,
        now_utc=datetime(2026, 5, 16, 14, 30, 0, tzinfo=UTC),
    )

    res = client.get("/api/v1/signoff-history/GS-A-candidate")
    assert res.status_code == 200
    payload = res.json()
    assert payload["record_count"] == 2
    # Chronological order
    assert payload["records"][0]["signoff_utc"] == "2026-05-16T090000Z"
    assert payload["records"][1]["signoff_utc"] == "2026-05-16T143000Z"
    # Latest verdict
    assert payload["records"][-1]["verdict"] == "needs_more_convergence"
    assert payload["records"][-1]["reviewer"] == "bob"
    # Tier 1 disclaimer trio
    body = res.text.lower()
    assert "tier 1 engineering candidate" in body
    assert "not signed validation" in body
    assert "not benchmark agreement" in body


# ---------------------------------------------------------------------
# E2E #2 — Provenance trace
# ---------------------------------------------------------------------


def test_phase8_provenance_trace_e2e(client: _SyncASGIClient, fake_repo: Path) -> None:
    """Reviewer journey: write a snapshot; fetch provenance trace;
    verify every input SHA matches the snapshot bytes on disk;
    formula_version round-trips.

    Tier 1 engineering candidate; not signed validation; not benchmark agreement.
    """
    case = _seed_case(fake_repo, "GS-A-candidate")
    write_cohort_snapshot([case], repo_root=fake_repo, snapshot_label="2026-05-16T100000Z")
    res = client.get(
        "/api/v1/trust-score-provenance/GS-A-candidate",
        params={"snapshot": "2026-05-16T100000Z"},
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["formula_version"]  # non-empty
    assert payload["snapshot_label"] == "2026-05-16T100000Z"
    snap_dir = fake_repo / "reports" / "snapshots" / "2026-05-16T100000Z"

    # Every input that reports present=True must have a SHA matching
    # the bytes on disk.
    for input_entry in payload["inputs"]:
        if input_entry["present"]:
            captured = (snap_dir / input_entry["path"]).read_bytes()
            assert input_entry["sha256"] == hashlib.sha256(captured).hexdigest(), (
                f"SHA mismatch for {input_entry['path']}"
            )

    # Tier 1 disclaimer trio in body
    body = res.text.lower()
    assert "tier 1 engineering candidate" in body
    assert "not signed validation" in body
    assert "not benchmark agreement" in body


# ---------------------------------------------------------------------
# E2E #3 — Cohort outlier + signoff escalation
# ---------------------------------------------------------------------


def test_phase8_cohort_outlier_and_signoff_e2e(client: _SyncASGIClient, fake_repo: Path) -> None:
    """Reviewer journey: write 7 candidate cases (6 healthy + 1 extreme
    outlier on completeness); fetch cohort summary; fetch anomalies
    (outlier should fire); write a blocked_pending_input signoff on the
    outlier; re-fetch summary and verify it lands in regressed bucket.

    Tier 1 engineering candidate; not signed validation; not benchmark agreement.
    """
    for cid, score in (
        ("GS-A-candidate", 85),
        ("GS-B-candidate", 86),
        ("GS-C-candidate", 87),
        ("GS-D-candidate", 86),
        ("GS-E-candidate", 85),
        ("GS-F-candidate", 86),
        ("GS-Z-candidate", 10),  # extreme outlier
    ):
        _seed_snapshot_with_completeness(fake_repo, cid, score, "2026-05-16T100000Z")

    # 1) Fetch cohort summary
    res_summary = client.get("/api/v1/cohort-executive-summary")
    assert res_summary.status_code == 200
    summary = res_summary.json()
    assert summary["cohort_count"] == 7
    # GS-Z-candidate scores 5 (10 * 50/100) on completeness -> trust_score
    # 5 < 50, so it should be regressed independent of signoff state.
    z_row = next(c for c in summary["cases"] if c["case_id"] == "GS-Z-candidate")
    assert z_row["bucket"] == "regressed"

    # 2) Fetch anomalies — outlier should fire
    res_anomalies = client.get("/api/v1/cohort-anomalies")
    assert res_anomalies.status_code == 200
    anomalies = res_anomalies.json()
    outlier_cases = [a["case_id"] for a in anomalies["anomalies"]]
    assert "GS-Z-candidate" in outlier_cases

    # 3) Write a blocked signoff on the outlier
    write_signoff_record(
        "GS-Z-candidate",
        "alice",
        "blocked_pending_input",
        "Blocked pending material card from supplier.",
        repo_root=fake_repo,
    )

    # 4) Re-fetch summary — GS-Z stays regressed (was already regressed
    # by trust score; signoff just adds reviewer context)
    res_summary2 = client.get("/api/v1/cohort-executive-summary")
    summary2 = res_summary2.json()
    z_row2 = next(c for c in summary2["cases"] if c["case_id"] == "GS-Z-candidate")
    assert z_row2["bucket"] == "regressed"
    assert z_row2["latest_signoff_verdict"] == "blocked_pending_input"

    # Tier 1 disclaimer trio in every body
    for body in (res_summary.text, res_anomalies.text, res_summary2.text):
        body_lower = body.lower()
        assert "tier 1 engineering candidate" in body_lower
        assert "not signed validation" in body_lower
        assert "not benchmark agreement" in body_lower
