"""HTTP-layer integration tests for FM-04a Phase 6 endpoints.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Drives every Phase 6 endpoint through a real httpx ASGI transport.
Uses the same ``_SyncASGIClient`` shim shipped in Phase 3 E.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from app.api.routes import snapshot_narrative as snapshot_narrative_module
from app.api.routes import trust_score as trust_score_module
from app.api.routes import trust_score_timeline as trust_score_timeline_module
from app.main import app
from app.services.reporting._schema_versions import (
    SNAPSHOT_NARRATIVE_SCHEMA_VERSION,
    TRUST_SCORE_FORMULA_VERSION,
    TRUST_SCORE_SCHEMA_VERSION,
    TRUST_SCORE_TIMELINE_SCHEMA_VERSION,
)
from app.services.reporting.cohort_snapshot import (
    SNAPSHOT_MANIFEST_FILENAME,
    snapshots_root,
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


@pytest.fixture()
def client() -> _SyncASGIClient:
    return _SyncASGIClient(app)


@pytest.fixture()
def fake_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    fake_root = tmp_path

    def fake_repo_root() -> Path:
        return fake_root

    monkeypatch.setattr(trust_score_module, "_repo_root", fake_repo_root)
    monkeypatch.setattr(trust_score_timeline_module, "_repo_root", fake_repo_root)
    monkeypatch.setattr(snapshot_narrative_module, "_repo_root", fake_repo_root)
    return fake_root


def _seed_snapshot(
    repo_root: Path,
    label: str,
    *,
    cases: list[str],
    completeness: dict[str, int] | None = None,
) -> Path:
    root = snapshots_root(repo_root) / label
    root.mkdir(parents=True, exist_ok=True)
    (root / "completeness").mkdir(parents=True, exist_ok=True)
    (root / "reproducibility").mkdir(parents=True, exist_ok=True)
    (root / "metrics").mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "1.1.0",
        "snapshot_label": label,
        "captured_at_utc": f"2026-05-16T{label[11:13]}:00:00+00:00",
        "claim_tier": "Tier 1 engineering candidate",
        "claim_boundary": (
            "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"
        ),
        "cohort_count": len(cases),
        "cases": cases,
        "members": [],
        "reviewer_bundle_written": False,
        "tier2_blockers_remaining": [],
        "claim_impact": (
            "Tier 1 candidate cohort snapshot only; not signed validation; not benchmark agreement"
        ),
    }
    (root / SNAPSHOT_MANIFEST_FILENAME).write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    for case_id, score in (completeness or {}).items():
        (root / "completeness" / f"{case_id}.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.0.0",
                    "case_id": case_id,
                    "claim_boundary": (
                        "tier1_engineering_candidate; not_signed_validation; "
                        "not_benchmark_agreement"
                    ),
                    "score": score,
                    "score_max": 100,
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
    return root


# ---------------------------------------------------------------------
# /api/v1/trust-score/<case-id>
# ---------------------------------------------------------------------


def test_trust_score_endpoint_returns_stamped_payload(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    res = client.get("/api/v1/trust-score/GS-A-candidate")
    assert res.status_code == 200
    payload = res.json()
    assert payload["schema_version"] == TRUST_SCORE_SCHEMA_VERSION
    assert payload["formula_version"] == TRUST_SCORE_FORMULA_VERSION
    assert payload["claim_tier"] == "Tier 1 engineering candidate"
    assert "not signed validation" in payload["claim_impact"]
    assert 0 <= payload["trust_score"] <= 100
    axes = {entry["axis"] for entry in payload["breakdown"]}
    assert axes == {
        "completeness",
        "convergence_stability",
        "energy_audit_closure",
        "reproducibility_clean",
    }


def test_trust_score_endpoint_rejects_path_traversal(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    # Phase 13 B — tightened from `in {400, 404, 422}` to exact 404.
    # The Starlette path matcher rejects the URL-decoded traversal
    # before the route handler runs; permissive ranges hid which
    # layer is authoritative.
    res = client.get("/api/v1/trust-score/..%2Fescape")
    assert res.status_code == 404


def test_trust_score_endpoint_returns_tier1_disclaimer(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    res = client.get("/api/v1/trust-score/GS-X-candidate")
    assert res.status_code == 200
    body = res.text
    assert "Tier 1 engineering candidate" in body
    assert "not signed validation" in body
    assert "not benchmark agreement" in body


# ---------------------------------------------------------------------
# /api/v1/snapshot-narrative
# ---------------------------------------------------------------------


def test_snapshot_narrative_endpoint_returns_stamped_payload(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    _seed_snapshot(
        fake_repo,
        "2026-05-16T100000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": 80},
    )
    _seed_snapshot(
        fake_repo,
        "2026-05-16T200000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": 90},
    )
    res = client.get(
        "/api/v1/snapshot-narrative",
        params={"a": "2026-05-16T100000Z", "b": "2026-05-16T200000Z"},
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["schema_version"] == SNAPSHOT_NARRATIVE_SCHEMA_VERSION
    assert payload["snapshot_a_label"] == "2026-05-16T100000Z"
    assert payload["snapshot_b_label"] == "2026-05-16T200000Z"
    assert payload["claim_tier"] == "Tier 1 engineering candidate"


def test_snapshot_narrative_endpoint_rejects_malformed_label(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    res = client.get(
        "/api/v1/snapshot-narrative",
        params={"a": "bogus", "b": "2026-05-16T100000Z"},
    )
    assert res.status_code == 400


def test_snapshot_narrative_endpoint_returns_404_for_missing_snapshot(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    _seed_snapshot(
        fake_repo,
        "2026-05-16T100000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": 80},
    )
    res = client.get(
        "/api/v1/snapshot-narrative",
        params={"a": "2026-05-16T100000Z", "b": "2026-05-16T999999Z"},
    )
    assert res.status_code == 404


def test_snapshot_narrative_endpoint_surfaces_completeness_improved(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    _seed_snapshot(
        fake_repo,
        "2026-05-16T100000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": 70},
    )
    _seed_snapshot(
        fake_repo,
        "2026-05-16T200000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": 90},
    )
    res = client.get(
        "/api/v1/snapshot-narrative",
        params={"a": "2026-05-16T100000Z", "b": "2026-05-16T200000Z"},
    )
    payload = res.json()
    template_ids = [
        line["template_id"] for narrative in payload["narratives"] for line in narrative["lines"]
    ]
    assert "completeness_improved" in template_ids


def test_snapshot_narrative_endpoint_missing_query_params_returns_422(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    res = client.get("/api/v1/snapshot-narrative", params={"a": "2026-05-16T100000Z"})
    assert res.status_code == 422


# ---------------------------------------------------------------------
# /api/v1/trust-score-timeline/<case-id>
# ---------------------------------------------------------------------


def test_trust_score_timeline_endpoint_returns_stamped_payload(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    _seed_snapshot(
        fake_repo,
        "2026-05-16T100000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": 80},
    )
    res = client.get("/api/v1/trust-score-timeline/GS-A-candidate")
    assert res.status_code == 200
    payload = res.json()
    assert payload["schema_version"] == TRUST_SCORE_TIMELINE_SCHEMA_VERSION
    assert payload["formula_version"] == TRUST_SCORE_FORMULA_VERSION
    assert payload["case_id"] == "GS-A-candidate"
    assert payload["point_count"] == 1


def test_trust_score_timeline_endpoint_rejects_invalid_case_id(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    # Phase 13 B — tightened from `in {400, 404, 422}` to exact 404.
    # The Starlette path matcher rejects the URL-decoded traversal
    # before the route handler's case_id regex runs.
    res = client.get("/api/v1/trust-score-timeline/..%2Fescape")
    assert res.status_code == 404


def test_trust_score_timeline_endpoint_returns_empty_timeline_when_no_snapshots(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    res = client.get("/api/v1/trust-score-timeline/GS-X-candidate")
    assert res.status_code == 200
    payload = res.json()
    assert payload["point_count"] == 0
    assert payload["points"] == []
    # Tier 1 disclaimer still present
    assert "not signed validation" in payload["claim_impact"]


def test_trust_score_timeline_endpoint_orders_oldest_first(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    _seed_snapshot(
        fake_repo,
        "2026-05-16T200000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": 90},
    )
    _seed_snapshot(
        fake_repo,
        "2026-05-16T100000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": 70},
    )
    res = client.get("/api/v1/trust-score-timeline/GS-A-candidate")
    payload = res.json()
    labels = [p["snapshot_label"] for p in payload["points"]]
    assert labels == ["2026-05-16T100000Z", "2026-05-16T200000Z"]


def test_trust_score_timeline_endpoint_preserves_tier1_disclaimer(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    _seed_snapshot(
        fake_repo,
        "2026-05-16T100000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": 80},
    )
    res = client.get("/api/v1/trust-score-timeline/GS-A-candidate")
    body = res.text
    assert "Tier 1 engineering candidate" in body
    assert "not signed validation" in body
    assert "not benchmark agreement" in body


# ---------------------------------------------------------------------
# /api/v1/cohort-snapshot-diff with numerical_deltas (Phase 6 A bump)
# ---------------------------------------------------------------------


def test_diff_endpoint_returns_v1_1_0_with_numerical_deltas_field(
    client: _SyncASGIClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from app.api.routes import cohort_snapshot_diff as cohort_snapshot_diff_module

    def fake_repo_root() -> Path:
        return tmp_path

    monkeypatch.setattr(cohort_snapshot_diff_module, "_repo_root", fake_repo_root)
    _seed_snapshot(
        tmp_path,
        "2026-05-16T100000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": 80},
    )
    _seed_snapshot(
        tmp_path,
        "2026-05-16T200000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": 85},
    )
    res = client.get(
        "/api/v1/cohort-snapshot-diff",
        params={"a": "2026-05-16T100000Z", "b": "2026-05-16T200000Z"},
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["schema_version"] == "1.1.0"
    # numerical_deltas is the new sibling list; empty here because we
    # did not seed metrics/<case>.json in either snapshot
    assert "numerical_deltas" in payload
    assert payload["numerical_deltas"] == []
