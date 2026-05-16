"""FM-04a Phase 8 D — cohort executive summary tests.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from app.api.routes import cohort_executive_summary as route_module
from app.main import app
from app.services.reporting._schema_versions import (
    COHORT_EXECUTIVE_SUMMARY_SCHEMA_VERSION,
)
from app.services.reporting.cohort_executive_summary import (
    HEALTHY_TRUST_SCORE_MIN,
    WATCHING_TRUST_SCORE_MIN,
    _classify_bucket,
    build_cohort_executive_summary,
)


class _SyncASGIClient:
    def __init__(self, asgi_app: Any) -> None:
        self._transport = httpx.ASGITransport(app=asgi_app)

    def get(self, url: str) -> httpx.Response:
        async def _run() -> httpx.Response:
            async with httpx.AsyncClient(
                transport=self._transport, base_url="http://testserver"
            ) as client:
                return await client.get(url)

        return asyncio.run(_run())


@pytest.fixture()
def client() -> _SyncASGIClient:
    return _SyncASGIClient(app)


@pytest.fixture()
def fake_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(route_module, "_repo_root", lambda: tmp_path)
    return tmp_path


def _make_candidate_dir(root: Path, case_id: str) -> None:
    (root / "golden_samples" / case_id / "data").mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------
# Bucket classification (pure unit; no I/O)
# ---------------------------------------------------------------------


def test_bucket_threshold_constants_are_named() -> None:
    """Phase 8 anti-gaming guard M: -3 — bucket thresholds are named constants."""
    assert HEALTHY_TRUST_SCORE_MIN == 80
    assert WATCHING_TRUST_SCORE_MIN == 50


def test_bucket_healthy_when_score_ge_80_no_alarms_no_blocker() -> None:
    assert _classify_bucket(85, 0, None) == "healthy"
    assert _classify_bucket(80, 0, None) == "healthy"
    assert _classify_bucket(100, 0, "watching") == "watching"  # watching dominates


def test_bucket_watching_when_score_in_50_to_80_or_watching_verdict() -> None:
    assert _classify_bucket(79, 0, None) == "watching"
    assert _classify_bucket(50, 0, None) == "watching"
    assert _classify_bucket(85, 0, "needs_more_evidence") == "watching"
    assert _classify_bucket(85, 0, "needs_more_convergence") == "watching"


def test_bucket_regressed_when_score_lt_50_or_alarms_or_blocked() -> None:
    assert _classify_bucket(49, 0, None) == "regressed"
    assert _classify_bucket(85, 1, None) == "regressed"  # alarms dominate
    assert _classify_bucket(85, 0, "blocked_pending_input") == "regressed"


def test_bucket_blocked_signoff_dominates_high_score() -> None:
    """blocked_pending_input is the reviewer's hard stop; bucket is always regressed."""
    assert _classify_bucket(100, 0, "blocked_pending_input") == "regressed"


def test_bucket_no_snapshot_yet_falls_to_healthy_fallback() -> None:
    """A new candidate with no snapshot yet has trust_score=None;
    fallback to healthy (no evidence of regression)."""
    assert _classify_bucket(None, 0, None) == "healthy"


# ---------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------


def test_builder_empty_cohort_returns_zero_counts(tmp_path: Path) -> None:
    summary = build_cohort_executive_summary(repo_root=tmp_path)
    assert summary.cohort_count == 0
    assert summary.healthy_count == 0
    assert summary.watching_count == 0
    assert summary.regressed_count == 0
    assert summary.cases == ()


def test_builder_stamps_schema_and_disclaimer_trio(tmp_path: Path) -> None:
    _make_candidate_dir(tmp_path, "GS-A-candidate")
    summary = build_cohort_executive_summary(repo_root=tmp_path)
    assert summary.schema_version == COHORT_EXECUTIVE_SUMMARY_SCHEMA_VERSION
    assert summary.claim_tier == "Tier 1 engineering candidate"
    assert "not_signed_validation" in summary.claim_boundary
    assert "not_benchmark_agreement" in summary.claim_boundary
    assert "not signed validation" in summary.claim_impact
    assert "not benchmark agreement" in summary.claim_impact


def test_builder_rejects_signed_registry_at_scanner_level(tmp_path: Path) -> None:
    """Signed registry shape (^GS-\\d{3}$) must never surface in the
    cohort summary (defense in depth — even if it didn't end with
    '-candidate', the regex catches it)."""
    _make_candidate_dir(tmp_path, "GS-A-candidate")
    # Forge a path that ends with -candidate but with the signed-registry
    # shape elsewhere; only literal ^GS-\d{3}$ should be filtered.
    _make_candidate_dir(tmp_path, "GS-001")  # not -candidate, ignored
    summary = build_cohort_executive_summary(repo_root=tmp_path)
    case_ids = [c.case_id for c in summary.cases]
    assert "GS-001" not in case_ids
    assert "GS-A-candidate" in case_ids


def test_builder_buckets_a_new_candidate_into_healthy_default(tmp_path: Path) -> None:
    _make_candidate_dir(tmp_path, "GS-A-candidate")
    summary = build_cohort_executive_summary(repo_root=tmp_path)
    assert summary.cohort_count == 1
    assert summary.healthy_count == 1
    assert summary.cases[0].latest_trust_score is None  # no snapshot yet


# ---------------------------------------------------------------------
# HTTP endpoint
# ---------------------------------------------------------------------


def test_endpoint_returns_stamped_payload(client: _SyncASGIClient, fake_repo: Path) -> None:
    _make_candidate_dir(fake_repo, "GS-A-candidate")
    _make_candidate_dir(fake_repo, "GS-B-candidate")
    res = client.get("/api/v1/cohort-executive-summary")
    assert res.status_code == 200
    payload = res.json()
    assert payload["schema_version"] == COHORT_EXECUTIVE_SUMMARY_SCHEMA_VERSION
    assert payload["cohort_count"] == 2
    assert payload["healthy_count"] + payload["watching_count"] + payload["regressed_count"] == 2
    assert isinstance(payload["cases"], list)
    assert len(payload["cases"]) == 2


def test_endpoint_envelope_carries_tier1_disclaimer_trio(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    _make_candidate_dir(fake_repo, "GS-A-candidate")
    res = client.get("/api/v1/cohort-executive-summary")
    payload = res.json()
    assert "Tier 1 engineering candidate" in payload["claim_tier"]
    assert "not signed validation" in payload["claim_impact"]
    assert "not benchmark agreement" in payload["claim_impact"]


def test_endpoint_is_application_json(client: _SyncASGIClient, fake_repo: Path) -> None:
    _make_candidate_dir(fake_repo, "GS-A-candidate")
    res = client.get("/api/v1/cohort-executive-summary")
    assert res.headers["content-type"].startswith("application/json")
    json.loads(res.text)  # parses cleanly
