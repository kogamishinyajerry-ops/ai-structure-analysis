"""HTTP-layer integration tests for FM-04a Phase 4 endpoints.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Drives every Phase 4 endpoint through a real httpx ASGI transport.
Uses the same `_SyncASGIClient` shim shipped in Phase 3 E since
starlette.testclient remains incompatible with httpx >= 0.28.
"""

from __future__ import annotations

import asyncio
import io
import json
import zipfile
from pathlib import Path
from typing import Any

import httpx
import pytest
from app.api.routes import (
    archived_packet_diff as archived_packet_diff_module,
)
from app.api.routes import (
    case_completeness as case_completeness_module,
)
from app.api.routes import (
    cohort_overview as cohort_overview_module,
)
from app.api.routes import (
    reviewer_bundle as reviewer_bundle_module,
)
from app.main import app


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


# ---------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------


def _seed_case_evidence(
    repo_root: Path,
    case_id: str,
    *,
    with_metrics: bool = True,
    audit_status: str = "closed_aggregate",
    with_convergence: bool = True,
    convergence_verdict: str = "candidate_observed_stable",
    with_decks: bool = True,
) -> None:
    case_dir = repo_root / "golden_samples" / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    if with_decks:
        data = case_dir / "data"
        data.mkdir(parents=True, exist_ok=True)
        (data / "model_00_0000.rad").write_text("starter\n", encoding="utf-8")
        (data / "model_00_0001.rad").write_text("engine\n", encoding="utf-8")
    if with_metrics:
        metrics = (
            repo_root
            / "project_state"
            / "graph_executor"
            / case_id
            / "ballistic"
            / "ballistic_metrics.json"
        )
        metrics.parent.mkdir(parents=True, exist_ok=True)
        metrics.write_text(
            json.dumps(
                {
                    "case_id": case_id,
                    "perforation_marker": "perforated_candidate",
                    "projectile_initial_velocity_m_per_s": 600.0,
                    "residual_velocity_candidate_m_per_s": 75.0,
                    "crossing_evidence": {
                        "status": "candidate_observed",
                        "front_face_crossed": True,
                        "back_face_crossed": True,
                        "first_back_face_crossing_t_s": 5.0e-5,
                    },
                    "energy_audit": {
                        "status": audit_status,
                        "initial_kinetic_energy_j": 1731.0,
                        "residual_kinetic_energy_j": 575.5,
                        "aggregate_internal_energy_j": 826.6,
                        "external_work_j": 0.0,
                        "energy_balance_error_pct": 19.0,
                        "breakdown_status": "aggregated_into_internal_energy",
                        "missing_terms": [],
                    },
                }
            ),
            encoding="utf-8",
        )
    if with_convergence:
        conv = (
            repo_root
            / "project_state"
            / "graph_executor"
            / case_id
            / "convergence"
            / "convergence_study.json"
        )
        conv.parent.mkdir(parents=True, exist_ok=True)
        conv.write_text(
            json.dumps(
                {
                    "case_id": case_id,
                    "combined_verdict": convergence_verdict,
                    "mesh_sweep": {"candidate_stability": convergence_verdict},
                    "dt_sweep": {"candidate_stability": convergence_verdict},
                    "row_count": 2,
                    "tolerance_pct": 5.0,
                    "claim_boundary": (
                        "tier1_engineering_candidate; not_signed_validation; "
                        "not_benchmark_agreement"
                    ),
                    "claim_impact": (
                        "Tier 1 candidate mesh and time-step convergence study only; "
                        "not signed validation; not benchmark agreement"
                    ),
                }
            ),
            encoding="utf-8",
        )


@pytest.fixture()
def fixture_repo(tmp_path: Path, monkeypatch) -> Path:
    """Stand up a synthetic 3-case fixture and re-aim every Phase 4 route at it."""
    # Case A: full evidence (high completeness).
    _seed_case_evidence(tmp_path, "GS-A-candidate")
    # Case B: decks only (low completeness).
    _seed_case_evidence(
        tmp_path,
        "GS-B-candidate",
        with_metrics=False,
        with_convergence=False,
    )
    # Case C: metrics but no convergence; mid completeness.
    _seed_case_evidence(
        tmp_path,
        "GS-C-candidate",
        with_convergence=False,
    )

    def fake_root() -> Path:
        return tmp_path

    monkeypatch.setattr(case_completeness_module, "_repo_root", fake_root)
    monkeypatch.setattr(cohort_overview_module, "_repo_root", fake_root)
    monkeypatch.setattr(reviewer_bundle_module, "_repo_root", fake_root)
    monkeypatch.setattr(archived_packet_diff_module, "_repo_root", fake_root)
    return tmp_path


# ---------------------------------------------------------------------
# /api/v1/case-completeness/<case-id> (Phase 4 A)
# ---------------------------------------------------------------------


def test_case_completeness_returns_scored_payload(
    client: _SyncASGIClient, fixture_repo: Path
) -> None:
    response = client.get("/api/v1/case-completeness/GS-A-candidate")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    payload = response.json()
    assert payload["case_id"] == "GS-A-candidate"
    assert payload["score_max"] == 100
    assert payload["score"] >= 65  # decks + metrics + closed audit + stable conv
    assert "tier1_engineering_candidate" in payload["claim_boundary"]
    assert any("ADR-024 (full)" in b for b in payload["tier2_blockers_remaining"])


def test_case_completeness_rejects_invalid_case_id(client: _SyncASGIClient) -> None:
    # Phase 13 B — tightened from `in (400, 404)` to exact 400. The route at
    # ``backend/app/api/routes/case_completeness.py`` raises a 400 with detail
    # ``"invalid case_id"`` when the URL-decoded id fails the ``_CASE_ID_RE``
    # whitelist; permissive ranges hide route-status drift, which is the
    # blueprint §3.B discipline the slice closes.
    response = client.get("/api/v1/case-completeness/has%20space")
    assert response.status_code == 400
    assert response.json()["detail"] == "invalid case_id"


# ---------------------------------------------------------------------
# /api/v1/cohort-overview (Phase 4 B)
# ---------------------------------------------------------------------


def test_cohort_overview_returns_three_case_rollup(
    client: _SyncASGIClient, fixture_repo: Path
) -> None:
    response = client.get("/api/v1/cohort-overview")
    assert response.status_code == 200
    payload = response.json()
    assert payload["cohort_count"] == 3
    case_ids = {entry["case_id"] for entry in payload["entries"]}
    assert case_ids == {"GS-A-candidate", "GS-B-candidate", "GS-C-candidate"}
    # Distribution buckets sum to 3.
    distribution = payload["completeness_distribution"]
    assert sum(distribution.values()) == 3
    # Tier 1 boundary present.
    assert "tier1_engineering_candidate" in payload["claim_boundary"]


# ---------------------------------------------------------------------
# /api/v1/reviewer-bundle?ids=... (Phase 4 C)
# ---------------------------------------------------------------------


def test_reviewer_bundle_returns_zip_with_expected_members(
    client: _SyncASGIClient, fixture_repo: Path
) -> None:
    response = client.get(
        "/api/v1/reviewer-bundle", params={"ids": "GS-A-candidate,GS-C-candidate"}
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/zip")
    assert "attachment" in response.headers["content-disposition"]
    assert "2cases" in response.headers["content-disposition"]
    body = response.content
    assert body.startswith(b"PK\x03\x04")
    with zipfile.ZipFile(io.BytesIO(body)) as zf:
        names = zf.namelist()
        manifest = json.loads(zf.read("BUNDLE_MANIFEST.json").decode("utf-8"))
    assert any("GS-A-candidate/" in n for n in names)
    assert any("GS-C-candidate/" in n for n in names)
    assert manifest["cohort_count"] == 2
    # Sealed-packet disclaimer in manifest is load-bearing.
    assert "not a sealed FM-04b P8 packet" in manifest["claim_impact"]


def test_reviewer_bundle_rejects_empty_ids(client: _SyncASGIClient) -> None:
    # Phase 13 B — tightened from `in (400, 422)` to exact 422. The route
    # declares the ``ids`` query parameter with ``min_length=1`` in
    # FastAPI's ``Query``; an empty string trips Pydantic validation
    # (``string_too_short``) which surfaces as 422 with a structured
    # detail list. A permissive 400/422 range hid which contract is
    # authoritative — the Pydantic-validation contract is.
    response = client.get("/api/v1/reviewer-bundle", params={"ids": ""})
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert isinstance(detail, list) and detail
    assert detail[0]["type"] == "string_too_short"
    assert "ids" in detail[0]["loc"]


def test_reviewer_bundle_rejects_invalid_case_id(
    client: _SyncASGIClient, fixture_repo: Path
) -> None:
    response = client.get("/api/v1/reviewer-bundle", params={"ids": "../escape"})
    assert response.status_code == 400


def test_reviewer_bundle_returns_404_when_case_missing(
    client: _SyncASGIClient, fixture_repo: Path
) -> None:
    response = client.get(
        "/api/v1/reviewer-bundle", params={"ids": "GS-A-candidate,GS-DOES-NOT-EXIST-candidate"}
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------
# /api/v1/archived-packet-diff?a=...&b=... (Phase 4 D)
# ---------------------------------------------------------------------


def test_archived_packet_diff_round_trips_through_reviewer_bundle(
    client: _SyncASGIClient, fixture_repo: Path
) -> None:
    """End-to-end: build a reviewer bundle, extract two acceptance packets
    into reports/, then diff them via the archive-diff endpoint."""
    bundle_resp = client.get(
        "/api/v1/reviewer-bundle",
        params={"ids": "GS-A-candidate,GS-C-candidate"},
    )
    assert bundle_resp.status_code == 200
    # Extract both per-case acceptance packets into reports/.
    reports = fixture_repo / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(bundle_resp.content)) as zf:
        for case_id in ("GS-A-candidate", "GS-C-candidate"):
            member = f"{case_id}/{case_id}_acceptance_packet.json"
            (reports / f"{case_id}_acceptance_packet.json").write_bytes(zf.read(member))

    response = client.get(
        "/api/v1/archived-packet-diff",
        params={
            "a": "GS-A-candidate_acceptance_packet.json",
            "b": "GS-C-candidate_acceptance_packet.json",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    # Different case ids → same_case False.
    assert payload["same_case"] is False
    assert payload["archive_a"]["case_id"] == "GS-A-candidate"
    assert payload["archive_b"]["case_id"] == "GS-C-candidate"
    # convergence_verdict_diff reflects the fixture: A has stable, C absent
    # (insufficient_data) so same_verdict False.
    assert payload["convergence_verdict_diff"]["same_verdict"] is False


def test_archived_packet_diff_returns_404_for_missing_archive(
    client: _SyncASGIClient, fixture_repo: Path
) -> None:
    (fixture_repo / "reports").mkdir(parents=True, exist_ok=True)
    response = client.get(
        "/api/v1/archived-packet-diff",
        params={"a": "missing_a.json", "b": "missing_b.json"},
    )
    assert response.status_code == 404


def test_archived_packet_diff_rejects_path_traversal(
    client: _SyncASGIClient, fixture_repo: Path
) -> None:
    (fixture_repo / "reports").mkdir(parents=True, exist_ok=True)
    response = client.get(
        "/api/v1/archived-packet-diff",
        params={
            "a": "../golden_samples/GS-A-candidate/data/model_00_0000.rad",
            "b": "../golden_samples/GS-A-candidate/data/model_00_0001.rad",
        },
    )
    # Must reject (400) — never serve content from golden_samples/** via
    # the archive endpoint.
    assert response.status_code == 400


# ---------------------------------------------------------------------
# Cross-endpoint Tier 1 audit + reviewer workflow E2E
# ---------------------------------------------------------------------


def test_phase4_endpoints_emit_no_forbidden_positive_claims(
    client: _SyncASGIClient, fixture_repo: Path
) -> None:
    """No Phase 4 endpoint may emit a forbidden positive claim."""
    endpoints = [
        ("/api/v1/case-completeness/GS-A-candidate", None),
        ("/api/v1/cohort-overview", None),
        ("/api/v1/reviewer-bundle", {"ids": "GS-A-candidate"}),
    ]
    forbidden = (
        "validated against",
        "perforation completed",
        "bullet-through-steel complete",
        "validated physics",
    )
    for url, params in endpoints:
        resp = client.get(url, params=params) if params else client.get(url)
        assert resp.status_code == 200, f"{url} returned {resp.status_code}"
        # Reviewer bundle body is binary; cohort + completeness are JSON.
        if resp.headers["content-type"].startswith("application/zip"):
            # Scan every text member inside the zip.
            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                for name in zf.namelist():
                    text = zf.read(name).decode("utf-8", errors="replace").lower()
                    stripped = (
                        text.replace("not_signed_validation", "")
                        .replace("not_benchmark_agreement", "")
                        .replace("not signed validation", "")
                        .replace("not benchmark agreement", "")
                    )
                    for token in forbidden:
                        assert token not in stripped, (
                            f"bundle member {name!r} (via {url}) leaked {token!r}"
                        )
        else:
            text = resp.text.lower()
            stripped = (
                text.replace("not_signed_validation", "")
                .replace("not_benchmark_agreement", "")
                .replace("not signed validation", "")
                .replace("not benchmark agreement", "")
            )
            for token in forbidden:
                assert token not in stripped, f"{url} leaked forbidden wording {token!r}"
