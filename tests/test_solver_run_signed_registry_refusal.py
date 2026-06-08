"""Codex R0 P1 — solver `/run` material_id branch refuses signed registry.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

The `POST /api/v1/solver/run` material_id branch composes and WRITES a fresh
INP into ``gs_root/<case_id>``. For a ``^GS-\\d{3}$`` signed-registry case that
write would overwrite a sealed golden-sample deck (e.g. ``gs001.inp``) and
corrupt reproducibility evidence (ADR-011 §HF1.7a hard-stop read-only). The
route now calls ``assert_not_signed_registry`` BEFORE any filesystem write.

This route takes ``case_id`` in the request BODY (not the path), so it is NOT
covered by the path-template meta-guard in
tests/test_phase14_cross_route_signed_registry_refusal.py; this file pins the
body-param surface directly.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest
from app.main import app


class _SyncASGIClient:
    def __init__(self, asgi_app: Any) -> None:
        self._transport = httpx.ASGITransport(app=asgi_app)

    def post(self, url: str, json: dict) -> httpx.Response:
        async def _run() -> httpx.Response:
            async with httpx.AsyncClient(transport=self._transport, base_url="http://t") as c:
                return await c.post(url, json=json)

        return asyncio.run(_run())


@pytest.fixture()
def client() -> _SyncASGIClient:
    return _SyncASGIClient(app)


@pytest.mark.parametrize("case_id", ["GS-000", "GS-001", "GS-101", "GS-999"])
def test_material_compose_refuses_signed_registry_before_write(
    client: _SyncASGIClient, case_id: str
) -> None:
    """A ``^GS-\\d{3}$`` case_id with material_id is refused 422 BEFORE the
    compose step writes any INP into gs_root/<case_id>."""
    res = client.post(
        "/api/v1/solver/run",
        json={"case_id": case_id, "material_id": "steel-s355", "analysis_type": "static"},
    )
    assert res.status_code == 422, (
        f"{case_id}: expected 422 signed-registry refusal, got "
        f"{res.status_code}; body: {res.text[:200]}"
    )
    detail = res.json().get("detail", "")
    assert "signed-registry" in detail, f"{case_id}: detail missing token: {detail!r}"
    assert "out of scope" in detail, f"{case_id}: detail missing token: {detail!r}"


def test_candidate_case_passes_the_gate(client: _SyncASGIClient) -> None:
    """A ``*-candidate`` case_id with material_id MUST NOT trip the
    signed-registry gate. It may fail downstream (missing case dir → 404),
    but the response must not carry the signed-registry refusal detail."""
    res = client.post(
        "/api/v1/solver/run",
        json={
            "case_id": "some-imaginary-candidate",
            "material_id": "steel-s355",
            "analysis_type": "static",
        },
    )
    # Not a signed-registry refusal: either it reached the case-dir lookup
    # (404) or a downstream material error (422 WITHOUT the registry token).
    if res.status_code == 422:
        detail = res.json().get("detail", "")
        assert "signed-registry" not in detail, (
            f"candidate id incorrectly tripped the signed-registry gate: {detail!r}"
        )
