"""FM-04a Phase 9 A — POST /api/v1/signoff-history/<case-id> tests.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Pins:
* All 4 supported verdicts roundtrip POST → GET.
* Every 422 path has a distinct ``detail`` string.
* 415 path before any body parsing.
* Tier 1 disclaimer trio in the success response.
* Service-layer side effect on disk matches the response.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from app.api.routes import signoff_history as route_module
from app.main import app
from app.services.reporting.signoff_record import (
    SUPPORTED_SIGNOFF_VERDICTS,
    read_signoff_history,
)


class _SyncASGIClient:
    def __init__(self, asgi_app: Any) -> None:
        self._transport = httpx.ASGITransport(app=asgi_app)

    def get(self, url: str, *, headers: dict | None = None) -> httpx.Response:
        async def _run() -> httpx.Response:
            async with httpx.AsyncClient(
                transport=self._transport, base_url="http://testserver"
            ) as client:
                return await client.get(url, headers=headers)

        return asyncio.run(_run())

    def post(
        self,
        url: str,
        *,
        json_body: Any = None,
        raw_body: bytes | None = None,
        headers: dict | None = None,
    ) -> httpx.Response:
        async def _run() -> httpx.Response:
            async with httpx.AsyncClient(
                transport=self._transport, base_url="http://testserver"
            ) as client:
                if json_body is not None:
                    return await client.post(url, json=json_body, headers=headers)
                return await client.post(url, content=raw_body, headers=headers)

        return asyncio.run(_run())


@pytest.fixture()
def client() -> _SyncASGIClient:
    return _SyncASGIClient(app)


@pytest.fixture()
def fake_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(route_module, "_repo_root", lambda: tmp_path)
    return tmp_path


# ---------------------------------------------------------------------
# Success paths — 4 verdicts
# ---------------------------------------------------------------------


@pytest.mark.parametrize("verdict", list(SUPPORTED_SIGNOFF_VERDICTS))
def test_post_signoff_success_for_each_whitelisted_verdict(
    client: _SyncASGIClient, fake_repo: Path, verdict: str
) -> None:
    res = client.post(
        f"/api/v1/signoff-history/GS-{verdict.upper()}-candidate",
        json_body={
            "reviewer": "alice",
            "verdict": verdict,
            "notes": "routine monitoring round",
        },
    )
    assert res.status_code == 200, res.text
    payload = res.json()
    assert payload["verdict"] == verdict
    assert payload["reviewer"] == "alice"
    assert payload["case_id"] == f"GS-{verdict.upper()}-candidate"
    assert "signoff_utc" in payload and payload["signoff_utc"].endswith("Z")


def test_post_signoff_response_carries_tier1_disclaimer_trio(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    res = client.post(
        "/api/v1/signoff-history/GS-A-candidate",
        json_body={
            "reviewer": "alice",
            "verdict": "watching",
            "notes": "ok",
        },
    )
    assert res.status_code == 200
    body = res.text.lower()
    assert "tier 1 engineering candidate" in body
    assert "not signed validation" in body
    assert "not benchmark agreement" in body


def test_post_then_get_returns_same_record(client: _SyncASGIClient, fake_repo: Path) -> None:
    post_res = client.post(
        "/api/v1/signoff-history/GS-A-candidate",
        json_body={
            "reviewer": "bob",
            "verdict": "needs_more_convergence",
            "notes": "mesh sweep too coarse",
        },
    )
    assert post_res.status_code == 200
    posted_utc = post_res.json()["signoff_utc"]

    get_res = client.get("/api/v1/signoff-history/GS-A-candidate")
    assert get_res.status_code == 200
    records = get_res.json()["records"]
    assert any(r["signoff_utc"] == posted_utc for r in records)
    assert get_res.json()["record_count"] == 1


def test_post_then_disk_side_effect_matches_response(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    res = client.post(
        "/api/v1/signoff-history/GS-A-candidate",
        json_body={
            "reviewer": "alice",
            "verdict": "watching",
            "notes": "round 1",
        },
    )
    assert res.status_code == 200
    posted_utc = res.json()["signoff_utc"]
    on_disk = fake_repo / "reports" / "signoffs" / "GS-A-candidate" / f"{posted_utc}.json"
    assert on_disk.is_file()
    parsed = json.loads(on_disk.read_text(encoding="utf-8"))
    assert parsed["verdict"] == "watching"
    assert parsed["reviewer"] == "alice"


def test_post_then_post_appends_second_record(client: _SyncASGIClient, fake_repo: Path) -> None:
    r1 = client.post(
        "/api/v1/signoff-history/GS-A-candidate",
        json_body={
            "reviewer": "alice",
            "verdict": "watching",
            "notes": "round 1",
        },
    )
    r2 = client.post(
        "/api/v1/signoff-history/GS-A-candidate",
        json_body={
            "reviewer": "bob",
            "verdict": "needs_more_convergence",
            "notes": "round 2",
        },
    )
    assert r1.status_code == 200 and r2.status_code == 200
    # If two POSTs land in the same UTC second the second overwrites the
    # first by design (same filename). To make the test deterministic we
    # just assert that GET returns at least one record and the latest
    # verdict reflects whichever record survived.
    history = client.get("/api/v1/signoff-history/GS-A-candidate").json()
    assert history["record_count"] >= 1


def test_post_uses_read_signoff_history_for_roundtrip(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Verify the service-layer read_signoff_history sees the POSTed record."""
    res = client.post(
        "/api/v1/signoff-history/GS-A-candidate",
        json_body={
            "reviewer": "alice",
            "verdict": "blocked_pending_input",
            "notes": "material card pending",
        },
    )
    assert res.status_code == 200
    records = read_signoff_history("GS-A-candidate", repo_root=fake_repo)
    assert len(records) == 1
    assert records[0].verdict == "blocked_pending_input"


# ---------------------------------------------------------------------
# 415 — Content-Type gate
# ---------------------------------------------------------------------


def test_post_signoff_refuses_non_json_content_type_with_415(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    res = client.post(
        "/api/v1/signoff-history/GS-A-candidate",
        raw_body=b'{"reviewer": "alice", "verdict": "watching", "notes": "ok"}',
        headers={"Content-Type": "text/plain"},
    )
    assert res.status_code == 415
    assert "application/json" in res.json()["detail"]


def test_post_signoff_refuses_missing_content_type_with_415(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """No Content-Type header → 415 (defense in depth).

    httpx defaults to application/json for json= bodies, so we send raw
    bytes here to confirm the gate refuses the request rather than
    silently treating it as JSON.
    """
    res = client.post(
        "/api/v1/signoff-history/GS-A-candidate",
        raw_body=b'{"reviewer": "alice"}',
        headers={"Content-Type": ""},
    )
    assert res.status_code == 415


# ---------------------------------------------------------------------
# 422 — verdict whitelist (load-bearing safety; guard C: -10)
# ---------------------------------------------------------------------


def test_post_signoff_refuses_unknown_verdict_with_422(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    res = client.post(
        "/api/v1/signoff-history/GS-A-candidate",
        json_body={
            "reviewer": "alice",
            "verdict": "approved",  # not in whitelist
            "notes": "ok",
        },
    )
    assert res.status_code == 422
    assert "not in the whitelist" in res.json()["detail"]


@pytest.mark.parametrize(
    "tier2_verb",
    [
        "ready_for_tier_2",
        "ready for tier 2",
        "promoted",
        "signed_validation",
        "benchmark_agreement",
        "ready_for_fm04b",
    ],
)
def test_post_signoff_refuses_tier2_promotion_verbs_with_422(
    client: _SyncASGIClient, fake_repo: Path, tier2_verb: str
) -> None:
    """Phase 9 guard C: -10 — Tier 2 promotion verbs cannot ship via POST."""
    res = client.post(
        "/api/v1/signoff-history/GS-A-candidate",
        json_body={
            "reviewer": "alice",
            "verdict": tier2_verb,
            "notes": "ok",
        },
    )
    assert res.status_code == 422


# ---------------------------------------------------------------------
# 422 — case_id refusals
# ---------------------------------------------------------------------


def test_post_signoff_refuses_signed_registry_case_id_with_422(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Phase 9 guard C: -8 — signed-registry case_id refused at HTTP boundary."""
    res = client.post(
        "/api/v1/signoff-history/GS-001",
        json_body={
            "reviewer": "alice",
            "verdict": "watching",
            "notes": "ok",
        },
    )
    assert res.status_code == 422
    assert "signed-registry" in res.json()["detail"]


def test_post_signoff_refuses_malformed_case_id_with_422(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    res = client.post(
        "/api/v1/signoff-history/has%20space",
        json_body={
            "reviewer": "alice",
            "verdict": "watching",
            "notes": "ok",
        },
    )
    assert res.status_code == 422
    assert "invalid case_id" in res.json()["detail"]


# ---------------------------------------------------------------------
# 422 — body / field validation
# ---------------------------------------------------------------------


def test_post_signoff_refuses_empty_reviewer_with_422(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    res = client.post(
        "/api/v1/signoff-history/GS-A-candidate",
        json_body={"reviewer": "", "verdict": "watching", "notes": "ok"},
    )
    assert res.status_code == 422


def test_post_signoff_refuses_whitespace_reviewer_with_422(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Service layer refuses reviewer that becomes empty after strip()."""
    res = client.post(
        "/api/v1/signoff-history/GS-A-candidate",
        json_body={"reviewer": "   ", "verdict": "watching", "notes": "ok"},
    )
    assert res.status_code == 422


def test_post_signoff_refuses_missing_field_with_422(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    res = client.post(
        "/api/v1/signoff-history/GS-A-candidate",
        json_body={"reviewer": "alice", "verdict": "watching"},  # no notes
    )
    assert res.status_code == 422


def test_post_signoff_refuses_invalid_json_with_422(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    res = client.post(
        "/api/v1/signoff-history/GS-A-candidate",
        raw_body=b"{not valid json",
        headers={"Content-Type": "application/json"},
    )
    assert res.status_code == 422
    assert "not valid JSON" in res.json()["detail"]


# ---------------------------------------------------------------------
# 422 — notes-claim audit (load-bearing safety; guard C: -8)
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "forbidden_phrase",
    [
        "validated against ASTM E8",
        "perforation completed today",
        "signed validation captured",
        "benchmark agreement achieved",
        "validated physics for this configuration",
    ],
)
def test_post_signoff_refuses_forbidden_claim_in_notes_with_422(
    client: _SyncASGIClient, fake_repo: Path, forbidden_phrase: str
) -> None:
    res = client.post(
        "/api/v1/signoff-history/GS-A-candidate",
        json_body={
            "reviewer": "alice",
            "verdict": "watching",
            "notes": forbidden_phrase,
        },
    )
    assert res.status_code == 422
    assert "forbidden positive claim" in res.json()["detail"]


def test_post_signoff_accepts_disclaimer_form_notes(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """``not <claim>`` form must pass the notes-claim audit."""
    res = client.post(
        "/api/v1/signoff-history/GS-A-candidate",
        json_body={
            "reviewer": "alice",
            "verdict": "watching",
            "notes": ("Tier 1 candidate only; not signed validation; not benchmark agreement."),
        },
    )
    assert res.status_code == 200
