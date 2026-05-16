"""FM-04a Phase 8 F — HTTP-layer integration tests across slice A/B/C/D/E surfaces.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Drives every Phase 8 endpoint through real httpx ASGITransport,
asserts status / content-type / envelope shape / Tier 1 disclaimer
trio / cross-endpoint forbidden-claim audit.
"""

from __future__ import annotations

import asyncio
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
from app.services.reporting._schema_versions import (
    COHORT_ANOMALIES_SCHEMA_VERSION,
    COHORT_EXECUTIVE_SUMMARY_SCHEMA_VERSION,
    SIGNOFF_RECORD_SCHEMA_VERSION,
    TRUST_SCORE_PROVENANCE_SCHEMA_VERSION,
)
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
# signoff-history (slice 8-B)
# ---------------------------------------------------------------------


def test_signoff_history_endpoint_empty_case(client: _SyncASGIClient, fake_repo: Path) -> None:
    res = client.get("/api/v1/signoff-history/GS-A-candidate")
    assert res.status_code == 200
    payload = res.json()
    assert payload["record_count"] == 0
    assert payload["schema_version"] == SIGNOFF_RECORD_SCHEMA_VERSION


def test_signoff_history_endpoint_chronology(client: _SyncASGIClient, fake_repo: Path) -> None:
    for hour, verdict in (
        (10, "watching"),
        (14, "blocked_pending_input"),
    ):
        write_signoff_record(
            "GS-A-candidate",
            "alice",
            verdict,
            f"hour {hour}",
            repo_root=fake_repo,
            now_utc=datetime(2026, 5, 16, hour, 0, 0, tzinfo=UTC),
        )
    res = client.get("/api/v1/signoff-history/GS-A-candidate")
    payload = res.json()
    assert payload["record_count"] == 2
    assert payload["records"][-1]["verdict"] == "blocked_pending_input"


def test_signoff_history_endpoint_rejects_signed_registry(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    res = client.get("/api/v1/signoff-history/GS-001")
    assert res.status_code == 400


# ---------------------------------------------------------------------
# trust-score-provenance (slice 8-C)
# ---------------------------------------------------------------------


def test_provenance_endpoint_returns_stamped_payload(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    case = _seed_case(fake_repo, "GS-A-candidate")
    write_cohort_snapshot([case], repo_root=fake_repo, snapshot_label="2026-05-16T100000Z")
    res = client.get(
        "/api/v1/trust-score-provenance/GS-A-candidate",
        params={"snapshot": "2026-05-16T100000Z"},
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["schema_version"] == TRUST_SCORE_PROVENANCE_SCHEMA_VERSION
    assert payload["case_id"] == "GS-A-candidate"
    assert payload["snapshot_label"] == "2026-05-16T100000Z"
    assert len(payload["inputs"]) == 4  # PROVENANCE_INPUT_KINDS


def test_provenance_endpoint_404_on_missing_snapshot(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    res = client.get(
        "/api/v1/trust-score-provenance/GS-A-candidate",
        params={"snapshot": "2099-01-01T000000Z"},
    )
    assert res.status_code == 404


def test_provenance_endpoint_400_on_bad_snapshot_shape(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    res = client.get(
        "/api/v1/trust-score-provenance/GS-A-candidate",
        params={"snapshot": "not-a-snapshot"},
    )
    assert res.status_code == 400


# ---------------------------------------------------------------------
# cohort-executive-summary (slice 8-D)
# ---------------------------------------------------------------------


def test_executive_summary_endpoint_empty_cohort(client: _SyncASGIClient, fake_repo: Path) -> None:
    res = client.get("/api/v1/cohort-executive-summary")
    assert res.status_code == 200
    payload = res.json()
    assert payload["schema_version"] == COHORT_EXECUTIVE_SUMMARY_SCHEMA_VERSION
    assert payload["cohort_count"] == 0
    assert payload["healthy_count"] + payload["watching_count"] + payload["regressed_count"] == 0


def test_executive_summary_endpoint_with_cohort(client: _SyncASGIClient, fake_repo: Path) -> None:
    (fake_repo / "golden_samples" / "GS-A-candidate" / "data").mkdir(parents=True)
    (fake_repo / "golden_samples" / "GS-B-candidate" / "data").mkdir(parents=True)
    res = client.get("/api/v1/cohort-executive-summary")
    payload = res.json()
    assert payload["cohort_count"] == 2
    assert isinstance(payload["cases"], list)


def test_executive_summary_endpoint_blocked_signoff_buckets_regressed(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """blocked_pending_input signoff forces regressed even with no
    snapshot (no trust score)."""
    (fake_repo / "golden_samples" / "GS-Z-candidate" / "data").mkdir(parents=True)
    write_signoff_record(
        "GS-Z-candidate",
        "alice",
        "blocked_pending_input",
        "blocked pending external input.",
        repo_root=fake_repo,
    )
    res = client.get("/api/v1/cohort-executive-summary")
    payload = res.json()
    assert payload["regressed_count"] == 1


# ---------------------------------------------------------------------
# cohort-anomalies (slice 8-E)
# ---------------------------------------------------------------------


def test_anomalies_endpoint_empty_cohort_zero_anomalies(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    res = client.get("/api/v1/cohort-anomalies")
    assert res.status_code == 200
    payload = res.json()
    assert payload["schema_version"] == COHORT_ANOMALIES_SCHEMA_VERSION
    assert payload["cohort_count"] == 0
    assert payload["anomaly_count"] == 0


def test_anomalies_endpoint_under_min_cohort_size_returns_empty(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    _seed_snapshot_with_completeness(fake_repo, "GS-A-candidate", 90, "2026-05-16T100000Z")
    _seed_snapshot_with_completeness(fake_repo, "GS-B-candidate", 70, "2026-05-16T100000Z")
    res = client.get("/api/v1/cohort-anomalies")
    payload = res.json()
    assert payload["cohort_count"] == 2
    assert payload["anomaly_count"] == 0


def test_anomalies_endpoint_engineered_outlier_fires(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    for cid, score in (
        ("GS-A-candidate", 85),
        ("GS-B-candidate", 86),
        ("GS-C-candidate", 87),
        ("GS-D-candidate", 86),
        ("GS-E-candidate", 85),
        ("GS-F-candidate", 86),
        ("GS-Z-candidate", 10),
    ):
        _seed_snapshot_with_completeness(fake_repo, cid, score, "2026-05-16T100000Z")
    res = client.get("/api/v1/cohort-anomalies")
    payload = res.json()
    assert payload["anomaly_count"] >= 1
    outlier_cases = [a["case_id"] for a in payload["anomalies"]]
    assert "GS-Z-candidate" in outlier_cases


# ---------------------------------------------------------------------
# Cross-endpoint disclaimer + audit
# ---------------------------------------------------------------------


def test_all_phase8_endpoints_carry_tier1_disclaimer_trio(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Cross-endpoint Tier 1 disclaimer trio round-trip at HTTP boundary.
    All 4 Phase 8 endpoints must surface "Tier 1 engineering candidate"
    + "not signed validation" + "not benchmark agreement"."""
    case = _seed_case(fake_repo, "GS-A-candidate")
    write_cohort_snapshot([case], repo_root=fake_repo, snapshot_label="2026-05-16T100000Z")

    urls = [
        ("/api/v1/signoff-history/GS-A-candidate", None),
        (
            "/api/v1/trust-score-provenance/GS-A-candidate",
            {"snapshot": "2026-05-16T100000Z"},
        ),
        ("/api/v1/cohort-executive-summary", None),
        ("/api/v1/cohort-anomalies", None),
    ]
    for url, params in urls:
        res = client.get(url, params=params)
        assert res.status_code == 200, f"{url} -> {res.status_code}"
        body = res.text
        assert "Tier 1 engineering candidate" in body, url
        assert "not signed validation" in body, url
        assert "not benchmark agreement" in body, url


def test_all_phase8_endpoints_contain_no_forbidden_positive_claim(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Cross-endpoint forbidden-claim audit. The 4 envelope-level
    forbidden tokens must NEVER appear in any Phase 8 endpoint body
    outside a `not <claim>` disclaimer prefix. (The wider 6-token
    list including "signed validation" + "benchmark agreement" is
    NOT applied here because the envelope's own claim_impact uses
    those tokens inside compound disclaimer sentences — same Phase
    7 B two-list design.)"""
    case = _seed_case(fake_repo, "GS-A-candidate")
    write_cohort_snapshot([case], repo_root=fake_repo, snapshot_label="2026-05-16T100000Z")

    envelope_forbidden = (
        "validated against",
        "perforation completed",
        "bullet-through-steel complete",
        "validated physics",
    )
    urls = [
        ("/api/v1/signoff-history/GS-A-candidate", None),
        (
            "/api/v1/trust-score-provenance/GS-A-candidate",
            {"snapshot": "2026-05-16T100000Z"},
        ),
        ("/api/v1/cohort-executive-summary", None),
        ("/api/v1/cohort-anomalies", None),
    ]
    for url, params in urls:
        res = client.get(url, params=params)
        body = res.text.lower()
        for token in envelope_forbidden:
            assert token not in body, f"{url} contains forbidden token {token!r}"


def test_all_phase8_endpoints_are_application_json(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    case = _seed_case(fake_repo, "GS-A-candidate")
    write_cohort_snapshot([case], repo_root=fake_repo, snapshot_label="2026-05-16T100000Z")
    urls = [
        ("/api/v1/signoff-history/GS-A-candidate", None),
        (
            "/api/v1/trust-score-provenance/GS-A-candidate",
            {"snapshot": "2026-05-16T100000Z"},
        ),
        ("/api/v1/cohort-executive-summary", None),
        ("/api/v1/cohort-anomalies", None),
    ]
    for url, params in urls:
        res = client.get(url, params=params)
        assert res.headers["content-type"].startswith("application/json"), url
        json.loads(res.text)  # parses cleanly
