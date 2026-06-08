"""Tests for the Tier 1 convergence study sidecar endpoint (FM-04a Phase 3 D).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.api.routes.convergence_study import (
    _CASE_ID_RE,
    _resolve_convergence_path,
)


def test_case_id_regex_accepts_canonical_candidate_ids() -> None:
    assert _CASE_ID_RE.fullmatch("GS-102-candidate")
    assert _CASE_ID_RE.fullmatch("GS-102-refined-candidate")
    assert _CASE_ID_RE.fullmatch("GS-102-hifi-candidate")
    assert _CASE_ID_RE.fullmatch("case_001")


def test_case_id_regex_rejects_path_traversal() -> None:
    for bad in (
        "../escape",
        "GS/102",
        "GS 102",
        "../../etc/passwd",
        "",
        "x" * 65,
    ):
        assert not _CASE_ID_RE.fullmatch(bad), f"regex should reject {bad!r}"


def test_resolve_convergence_path_points_at_project_state(tmp_path: Path) -> None:
    """The resolver must anchor under project_state/graph_executor/<id>/convergence."""
    resolved = _resolve_convergence_path("GS-102-phase3-d")
    parts = resolved.as_posix().split("/")
    # The repo root is parents[4] of the route module; we don't pin the
    # exact prefix here, only the relative path under project_state.
    suffix_parts = parts[-5:]
    assert suffix_parts == [
        "project_state",
        "graph_executor",
        "GS-102-phase3-d",
        "convergence",
        "convergence_study.json",
    ]


def test_endpoint_returns_404_when_metrics_absent(monkeypatch, tmp_path: Path) -> None:
    """Force the resolver to point at a tmp path that does not exist."""
    from app.api.routes import convergence_study as endpoint_mod
    from fastapi import HTTPException

    target = tmp_path / "no_such_case.json"

    def fake_resolve(case_id: str) -> Path:
        return target

    monkeypatch.setattr(endpoint_mod, "_resolve_convergence_path", fake_resolve)

    import asyncio

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(endpoint_mod.get_convergence_study("GS-102-phase3-d"))
    assert exc_info.value.status_code == 404


def test_endpoint_rejects_invalid_case_id() -> None:
    import asyncio

    from app.api.routes import convergence_study as endpoint_mod
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(endpoint_mod.get_convergence_study("../escape"))
    assert exc_info.value.status_code == 400


def test_endpoint_returns_payload_when_file_present(monkeypatch, tmp_path: Path) -> None:
    from app.api.routes import convergence_study as endpoint_mod

    payload = {
        "case_id": "GS-102-phase3-d",
        "combined_verdict": "candidate_observed_stable",
        "tolerance_pct": 5.0,
        "claim_boundary": (
            "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"
        ),
    }
    target = tmp_path / "convergence_study.json"
    target.write_text(json.dumps(payload), encoding="utf-8")

    def fake_resolve(case_id: str) -> Path:
        return target

    monkeypatch.setattr(endpoint_mod, "_resolve_convergence_path", fake_resolve)

    import asyncio

    response = asyncio.run(endpoint_mod.get_convergence_study("GS-102-phase3-d"))
    assert response.status_code == 200
    body = json.loads(response.body)
    assert body["case_id"] == "GS-102-phase3-d"
    assert body["combined_verdict"] == "candidate_observed_stable"
    assert "not_signed_validation" in body["claim_boundary"]
    assert "not_benchmark_agreement" in body["claim_boundary"]
