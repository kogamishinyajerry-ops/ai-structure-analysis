"""FM-04a Phase 8 B — signoff history endpoint tests.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
from app.api.routes import signoff_history as signoff_history_module
from app.main import app
from app.services.reporting._schema_versions import SIGNOFF_RECORD_SCHEMA_VERSION
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
    def fake_repo_root() -> Path:
        return tmp_path

    monkeypatch.setattr(signoff_history_module, "_repo_root", fake_repo_root)
    return tmp_path


# ---------------------------------------------------------------------
# Empty case + populated case
# ---------------------------------------------------------------------


def test_signoff_history_endpoint_returns_empty_for_unseeded_case(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    res = client.get("/api/v1/signoff-history/GS-A-candidate")
    assert res.status_code == 200
    payload = res.json()
    assert payload["schema_version"] == SIGNOFF_RECORD_SCHEMA_VERSION
    assert payload["case_id"] == "GS-A-candidate"
    assert payload["record_count"] == 0
    assert payload["records"] == []


def test_signoff_history_endpoint_returns_chronological_order(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    for hour, verdict in (
        (9, "watching"),
        (11, "needs_more_evidence"),
        (15, "blocked_pending_input"),
    ):
        write_signoff_record(
            "GS-A-candidate",
            "alice",
            verdict,
            f"Round at {hour}.",
            repo_root=fake_repo,
            now_utc=datetime(2026, 5, 16, hour, 0, 0, tzinfo=UTC),
        )
    res = client.get("/api/v1/signoff-history/GS-A-candidate")
    assert res.status_code == 200
    payload = res.json()
    assert payload["record_count"] == 3
    labels = [r["signoff_utc"] for r in payload["records"]]
    assert labels == [
        "2026-05-16T090000Z",
        "2026-05-16T110000Z",
        "2026-05-16T150000Z",
    ]
    verdicts = [r["verdict"] for r in payload["records"]]
    assert verdicts == ["watching", "needs_more_evidence", "blocked_pending_input"]


# ---------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------


def test_signoff_history_endpoint_rejects_invalid_case_id_shape(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    res = client.get("/api/v1/signoff-history/has spaces")
    assert res.status_code == 400


def test_signoff_history_endpoint_rejects_signed_registry_case_id(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Phase 14 A — harmonized from 400 to 422 + canonical detail vocab.
    The route-level ``assert_not_signed_registry`` helper fires BEFORE
    the service-layer's ValueError (which previously surfaced as 400).
    Cross-route consistency: every Tier 1 reviewer-facing surface now
    uses the same 422 + ``signed-registry`` / ``candidate`` /
    ``out of scope`` vocabulary."""
    res = client.get("/api/v1/signoff-history/GS-001")
    assert res.status_code == 422
    detail = res.json()["detail"]
    assert "signed-registry" in detail
    assert "candidate" in detail
    assert "out of scope" in detail


# ---------------------------------------------------------------------
# Schema + Tier 1 disclaimer trio round-trip
# ---------------------------------------------------------------------


def test_signoff_history_endpoint_stamps_schema_and_disclaimer(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    write_signoff_record(
        "GS-A-candidate",
        "alice",
        "watching",
        "Tier 1 monitoring; not signed validation; not benchmark agreement.",
        repo_root=fake_repo,
    )
    res = client.get("/api/v1/signoff-history/GS-A-candidate")
    payload = res.json()
    # Tier 1 disclaimer trio in envelope
    assert "Tier 1 engineering candidate" in payload["claim_tier"]
    assert "not_signed_validation" in payload["claim_boundary"]
    assert "not_benchmark_agreement" in payload["claim_boundary"]
    assert "not signed validation" in payload["claim_impact"]
    assert "not benchmark agreement" in payload["claim_impact"]
    # Schema stamped
    assert payload["schema_version"] == SIGNOFF_RECORD_SCHEMA_VERSION


def test_signoff_history_endpoint_response_is_application_json(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    res = client.get("/api/v1/signoff-history/GS-A-candidate")
    assert res.headers["content-type"].startswith("application/json")
    json.loads(res.text)  # parses cleanly
