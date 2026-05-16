"""HTTP-layer integration tests for FM-04a Phase 5 endpoints.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Drives every Phase 5 endpoint through a real httpx ASGI transport.
Uses the same ``_SyncASGIClient`` shim from Phase 3 E / Phase 4 G
since starlette.testclient remains incompatible with httpx >= 0.28.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from app.api.routes import cohort_snapshot_diff as cohort_snapshot_diff_module
from app.api.routes import cohort_snapshots as cohort_snapshots_module
from app.api.routes import reproducibility_manifest as reproducibility_manifest_module
from app.main import app
from app.services.reporting._schema_versions import (
    COHORT_SNAPSHOT_DIFF_SCHEMA_VERSION,
    COHORT_SNAPSHOT_MANIFEST_SCHEMA_VERSION,
    REPRODUCIBILITY_MANIFEST_SCHEMA_VERSION,
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
    """Repoint every Phase 5 endpoint's _repo_root() to tmp_path."""
    fake_root = tmp_path

    def fake_repo_root() -> Path:
        return fake_root

    monkeypatch.setattr(reproducibility_manifest_module, "_repo_root", fake_repo_root)
    monkeypatch.setattr(cohort_snapshots_module, "_repo_root", fake_repo_root)
    monkeypatch.setattr(cohort_snapshot_diff_module, "_repo_root", fake_repo_root)
    return fake_root


# ---------------------------------------------------------------------
# fixtures: seed snapshots directly on disk (avoid going through the
# CLI in HTTP tests to keep the assertion surface tight)
# ---------------------------------------------------------------------


def _seed_snapshot(
    repo_root: Path,
    label: str,
    *,
    cases: list[str],
    completeness: dict[str, int] | None = None,
    repro: dict[str, dict] | None = None,
) -> Path:
    root = snapshots_root(repo_root) / label
    root.mkdir(parents=True, exist_ok=True)
    (root / "completeness").mkdir(parents=True, exist_ok=True)
    (root / "reproducibility").mkdir(parents=True, exist_ok=True)
    completeness = completeness or {}
    repro = repro or {}

    manifest = {
        "schema_version": COHORT_SNAPSHOT_MANIFEST_SCHEMA_VERSION,
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

    for case_id, score in completeness.items():
        (root / "completeness" / f"{case_id}.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.0.0",
                    "rubric_version": "1.0.0",
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
    for case_id, payload in repro.items():
        (root / "reproducibility" / f"{case_id}.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
        )
    return root


# ---------------------------------------------------------------------
# /api/v1/reproducibility-manifest/<case-id>
# ---------------------------------------------------------------------


def test_reproducibility_endpoint_returns_stamped_payload(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    res = client.get("/api/v1/reproducibility-manifest/GS-102-candidate")
    assert res.status_code == 200
    payload = res.json()
    assert payload["schema_version"] == REPRODUCIBILITY_MANIFEST_SCHEMA_VERSION
    assert payload["case_id"] == "GS-102-candidate"
    assert payload["claim_tier"] == "Tier 1 engineering candidate"
    assert "not signed validation" in payload["claim_impact"]


def test_reproducibility_endpoint_rejects_path_traversal(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    # Phase 13 B — tightened from `in {400, 404, 422}` to exact 404.
    # ``..%2Fescape`` is URL-decoded to ``../escape`` and the Starlette
    # path matcher rejects the traversal at the routing layer with 404
    # ``Not Found`` BEFORE the route's case_id regex runs. Pin the
    # observed code so a future routing change (e.g., a middleware
    # that re-encodes path components) surfaces as a real failure
    # instead of silently passing under the permissive set.
    res = client.get("/api/v1/reproducibility-manifest/..%2Fescape")
    assert res.status_code == 404


def test_reproducibility_endpoint_returns_tier1_disclaimer(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    res = client.get("/api/v1/reproducibility-manifest/GS-A-candidate")
    assert res.status_code == 200
    body = res.text
    assert "not signed validation" in body
    assert "not benchmark agreement" in body


# ---------------------------------------------------------------------
# /api/v1/cohort-snapshots (listing)
# ---------------------------------------------------------------------


def test_cohort_snapshots_endpoint_returns_empty_listing(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    res = client.get("/api/v1/cohort-snapshots")
    assert res.status_code == 200
    payload = res.json()
    assert payload["schema_version"] == COHORT_SNAPSHOT_MANIFEST_SCHEMA_VERSION
    assert payload["snapshot_count"] == 0
    assert payload["snapshots"] == []
    assert "not signed validation" in payload["claim_impact"]


def test_cohort_snapshots_endpoint_lists_seeded_snapshots(
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
        cases=["GS-A-candidate", "GS-B-candidate"],
        completeness={"GS-A-candidate": 85, "GS-B-candidate": 70},
    )
    res = client.get("/api/v1/cohort-snapshots")
    assert res.status_code == 200
    payload = res.json()
    assert payload["snapshot_count"] == 2
    # newest first
    assert payload["snapshots"][0]["snapshot_label"] == "2026-05-16T200000Z"
    assert payload["snapshots"][1]["snapshot_label"] == "2026-05-16T100000Z"
    assert payload["snapshots"][0]["cohort_count"] == 2


# ---------------------------------------------------------------------
# /api/v1/cohort-snapshot-diff
# ---------------------------------------------------------------------


def test_diff_endpoint_returns_stamped_payload(client: _SyncASGIClient, fake_repo: Path) -> None:
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
        completeness={"GS-A-candidate": 85},
    )
    res = client.get(
        "/api/v1/cohort-snapshot-diff",
        params={"a": "2026-05-16T100000Z", "b": "2026-05-16T200000Z"},
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["schema_version"] == COHORT_SNAPSHOT_DIFF_SCHEMA_VERSION
    assert payload["snapshot_a_label"] == "2026-05-16T100000Z"
    assert payload["snapshot_b_label"] == "2026-05-16T200000Z"
    assert payload["completeness_deltas"][0]["delta"] == 5


def test_diff_endpoint_rejects_malformed_label(client: _SyncASGIClient, fake_repo: Path) -> None:
    res = client.get(
        "/api/v1/cohort-snapshot-diff",
        params={"a": "bogus-label", "b": "2026-05-16T100000Z"},
    )
    assert res.status_code == 400


def test_diff_endpoint_returns_404_for_missing_snapshot(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    _seed_snapshot(
        fake_repo,
        "2026-05-16T100000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": 80},
    )
    res = client.get(
        "/api/v1/cohort-snapshot-diff",
        params={"a": "2026-05-16T100000Z", "b": "2026-05-16T999999Z"},
    )
    assert res.status_code == 404


def test_diff_endpoint_surfaces_full_drift_for_shared_cohort(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    repro_a = {
        "schema_version": "1.0.0",
        "case_id": "GS-A-candidate",
        "claim_boundary": "tier1_engineering_candidate",
        "git_commit_sha": "a" * 40,
        "git_dirty": False,
        "python_version": "3.11.15",
        "tracked_packages": [{"name": "fastapi", "version": "0.118.0"}],
        "scripts": [{"relpath": "scripts/gen.py", "sha256": "aa" * 32, "bytes": 100}],
    }
    repro_b = dict(repro_a)
    repro_b["git_commit_sha"] = "b" * 40
    repro_b["tracked_packages"] = [{"name": "fastapi", "version": "0.119.0"}]
    repro_b["scripts"] = [{"relpath": "scripts/gen.py", "sha256": "bb" * 32, "bytes": 120}]

    _seed_snapshot(
        fake_repo,
        "2026-05-16T100000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": 75},
        repro={"GS-A-candidate": repro_a},
    )
    _seed_snapshot(
        fake_repo,
        "2026-05-16T200000Z",
        cases=["GS-A-candidate"],
        completeness={"GS-A-candidate": 85},
        repro={"GS-A-candidate": repro_b},
    )
    res = client.get(
        "/api/v1/cohort-snapshot-diff",
        params={"a": "2026-05-16T100000Z", "b": "2026-05-16T200000Z"},
    )
    assert res.status_code == 200
    payload = res.json()
    repro_delta = payload["reproducibility_deltas"][0]
    assert repro_delta["git_sha_changed"] is True
    assert len(repro_delta["package_version_changes"]) == 1
    assert len(repro_delta["script_sha_changes"]) == 1


def test_diff_endpoint_returns_tier1_disclaimer(client: _SyncASGIClient, fake_repo: Path) -> None:
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
        completeness={"GS-A-candidate": 85},
    )
    res = client.get(
        "/api/v1/cohort-snapshot-diff",
        params={"a": "2026-05-16T100000Z", "b": "2026-05-16T200000Z"},
    )
    body = res.text
    assert "Tier 1 engineering candidate" in body
    assert "not signed validation" in body
    assert "not benchmark agreement" in body


def test_diff_endpoint_handles_cohort_membership_changes(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    _seed_snapshot(
        fake_repo,
        "2026-05-16T100000Z",
        cases=["GS-A-candidate", "GS-B-candidate"],
        completeness={"GS-A-candidate": 80, "GS-B-candidate": 70},
    )
    _seed_snapshot(
        fake_repo,
        "2026-05-16T200000Z",
        cases=["GS-A-candidate", "GS-C-candidate"],
        completeness={"GS-A-candidate": 85, "GS-C-candidate": 60},
    )
    res = client.get(
        "/api/v1/cohort-snapshot-diff",
        params={"a": "2026-05-16T100000Z", "b": "2026-05-16T200000Z"},
    )
    payload = res.json()
    assert payload["cohort_added"] == ["GS-C-candidate"]
    assert payload["cohort_removed"] == ["GS-B-candidate"]
    assert payload["cohort_shared"] == ["GS-A-candidate"]


def test_diff_endpoint_missing_required_params_returns_422(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    res = client.get(
        "/api/v1/cohort-snapshot-diff",
        params={"a": "2026-05-16T100000Z"},
    )
    assert res.status_code == 422
