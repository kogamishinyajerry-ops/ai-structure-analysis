"""HTTP-layer integration tests for FM-04a Phase 2 / Phase 3 endpoints.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Drives every reviewer-facing endpoint through FastAPI TestClient and
asserts on status code, content-type, Content-Disposition (where
relevant), and Tier 1 boundary in the response body. Repo file
fixtures are constructed in `tmp_path`; per-module `_repo_root`
functions are monkeypatched so the route handlers anchor at the
fixture root rather than the real repo.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from app.api.routes import (
    acceptance_packet as acceptance_packet_module,
)
from app.api.routes import (
    case_comparison as case_comparison_module,
)
from app.api.routes import (
    convergence_study as convergence_study_module,
)
from app.api.routes import (
    tier1_report as tier1_report_module,
)
from app.main import app


class _SyncASGIClient:
    """Tiny sync wrapper around httpx.AsyncClient + ASGITransport.

    Avoids the starlette.testclient incompatibility with httpx >= 0.28
    where TestClient still passes `app=` to httpx.Client, which httpx
    no longer accepts. Spinning up an AsyncClient with an explicit
    ASGITransport is the supported migration path.
    """

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


def _seed_ballistic_metrics(repo_root: Path, case_id: str) -> Path:
    target = (
        repo_root
        / "project_state"
        / "graph_executor"
        / case_id
        / "ballistic"
        / "ballistic_metrics.json"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "case_id": case_id,
                "claim_boundary": (
                    "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"
                ),
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
                    "status": "closed_aggregate",
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
    return target


def _seed_convergence_study(repo_root: Path, case_id: str) -> Path:
    target = (
        repo_root
        / "project_state"
        / "graph_executor"
        / case_id
        / "convergence"
        / "convergence_study.json"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "case_id": case_id,
                "study_metric": "residual_velocity_m_per_s",
                "tolerance_pct": 5.0,
                "combined_verdict": "candidate_observed_stable",
                "row_count": 2,
                "mesh_sweep": {
                    "axis": "mesh_level",
                    "axis_label": "mesh_level",
                    "candidate_stability": "candidate_observed_stable",
                    "relative_change_pct": 0.05,
                    "run_count": 2,
                    "runs": [
                        {"label": "coarse", "mesh_axis_value": 1, "metric_value": 75.0},
                        {"label": "fine", "mesh_axis_value": 2, "metric_value": 75.05},
                    ],
                    "held_dt_label": "dt_default",
                    "held_dt_axis_value": 1e-6,
                },
                "dt_sweep": {
                    "axis": "time_step_dt_s",
                    "axis_label": "time_step_dt_s",
                    "candidate_stability": "candidate_observed_stable",
                    "relative_change_pct": 0.02,
                    "run_count": 2,
                    "runs": [
                        {"label": "dt_default", "dt_axis_value": 1e-6, "metric_value": 75.0},
                        {"label": "dt_half", "dt_axis_value": 5e-7, "metric_value": 75.02},
                    ],
                    "held_mesh_label": "mesh_coarse",
                    "held_mesh_axis_value": 1,
                },
                "claim_boundary": (
                    "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"
                ),
                "claim_impact": (
                    "Tier 1 candidate mesh and time-step convergence study only; "
                    "not signed validation; not benchmark agreement"
                ),
                "energy_balance_observation": {
                    "status": "unavailable",
                    "rows_with_balance_error": 0,
                    "rows_total": 2,
                },
            }
        ),
        encoding="utf-8",
    )
    return target


@pytest.fixture()
def fixture_repo(tmp_path: Path, monkeypatch) -> Path:
    """Stand up a fake repo root and re-aim every Phase 2/3 route at it."""
    case_id = "GS-102-integration-candidate"
    _seed_ballistic_metrics(tmp_path, case_id)
    _seed_convergence_study(tmp_path, case_id)

    def fake_root() -> Path:
        return tmp_path

    monkeypatch.setattr(acceptance_packet_module, "_repo_root", fake_root)
    monkeypatch.setattr(tier1_report_module, "_repo_root", fake_root)
    monkeypatch.setattr(convergence_study_module, "_repo_root", fake_root)
    # case_comparison reuses acceptance_packet._build_inputs_for, which
    # itself reads acceptance_packet_module._repo_root, so monkeypatching
    # the upstream function above is enough. Pin the equivalent helper
    # in case_comparison_module to the same root for clarity.
    monkeypatch.setattr(
        case_comparison_module, "_build_inputs_for", acceptance_packet_module._build_inputs_for
    )
    return tmp_path


# ---------------------------------------------------------------------
# /api/v1/candidate-cases (Phase 2 C)
# ---------------------------------------------------------------------


def test_candidate_cases_endpoint_returns_200_and_payload(client: _SyncASGIClient) -> None:
    """Live endpoint over the real repo's golden_samples/*-candidate/ dirs."""
    response = client.get("/api/v1/candidate-cases")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    payload = response.json()
    assert payload["claim_tier"] == "Tier 1 engineering candidate"
    assert "not_signed_validation" in payload["claim_boundary"]
    assert "not_benchmark_agreement" in payload["claim_boundary"]
    assert isinstance(payload["cases"], list)
    # Smoke: at least the three known candidate dirs are present.
    case_ids = {c["case_id"] for c in payload["cases"]}
    assert {"GS-102-candidate", "GS-102-refined-candidate", "GS-102-hifi-candidate"} <= case_ids


# ---------------------------------------------------------------------
# /api/v1/tier1-report/<case-id> (Phase 2 E)
# ---------------------------------------------------------------------


def test_tier1_report_returns_markdown_with_tier1_banner(
    client: _SyncASGIClient, fixture_repo: Path
) -> None:
    response = client.get("/api/v1/tier1-report/GS-102-integration-candidate", params={"fmt": "md"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert "attachment" in response.headers["content-disposition"]
    assert "Tier1_candidate_report.md" in response.headers["content-disposition"]
    body = response.text
    assert "Tier 1 engineering candidate" in body
    assert "not signed validation" in body.lower()
    assert "not benchmark agreement" in body.lower()


def test_tier1_report_returns_docx_with_pk_zip_signature(
    client: _SyncASGIClient, fixture_repo: Path
) -> None:
    response = client.get(
        "/api/v1/tier1-report/GS-102-integration-candidate", params={"fmt": "docx"}
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert "attachment" in response.headers["content-disposition"]
    # DOCX is a zip — every valid zip begins with PK\x03\x04.
    assert response.content.startswith(b"PK\x03\x04")


def test_tier1_report_rejects_bogus_format(client: _SyncASGIClient, fixture_repo: Path) -> None:
    response = client.get(
        "/api/v1/tier1-report/GS-102-integration-candidate", params={"fmt": "bogus"}
    )
    assert response.status_code == 400


def test_tier1_report_rejects_bad_case_id(client: _SyncASGIClient, fixture_repo: Path) -> None:
    response = client.get("/api/v1/tier1-report/..%2Fescape", params={"fmt": "md"})
    # FastAPI may either decode the path traversal or 404 via the matcher.
    assert response.status_code in (400, 404)


def test_tier1_report_returns_404_for_missing_case(
    client: _SyncASGIClient, fixture_repo: Path
) -> None:
    response = client.get("/api/v1/tier1-report/GS-999-missing-candidate", params={"fmt": "md"})
    assert response.status_code == 404


# ---------------------------------------------------------------------
# /api/v1/acceptance-packet/<case-id> (Phase 3 A)
# ---------------------------------------------------------------------


def test_acceptance_packet_returns_tier1_json(client: _SyncASGIClient, fixture_repo: Path) -> None:
    response = client.get("/api/v1/acceptance-packet/GS-102-integration-candidate")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert "attachment" in response.headers["content-disposition"]
    payload = response.json()
    assert payload["case_id"] == "GS-102-integration-candidate"
    assert payload["claim_tier"] == "Tier 1 engineering candidate"
    assert "not_signed_validation" in payload["claim_boundary"]
    assert payload["energy_audit_summary"]["status"] == "closed_aggregate"
    assert payload["convergence_study_summary"]["status"] == "available"


def test_acceptance_packet_returns_404_for_missing_case(
    client: _SyncASGIClient, fixture_repo: Path
) -> None:
    response = client.get("/api/v1/acceptance-packet/GS-999-missing-candidate")
    assert response.status_code == 404


def test_acceptance_packet_rejects_invalid_case_id(client: _SyncASGIClient) -> None:
    response = client.get("/api/v1/acceptance-packet/has%20space")
    assert response.status_code in (400, 404)


# ---------------------------------------------------------------------
# /api/v1/case-comparison (Phase 3 B)
# ---------------------------------------------------------------------


def test_case_comparison_identity_returns_zero_deltas(
    client: _SyncASGIClient, fixture_repo: Path
) -> None:
    response = client.get(
        "/api/v1/case-comparison",
        params={
            "a": "GS-102-integration-candidate",
            "b": "GS-102-integration-candidate",
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    payload = response.json()
    assert payload["case_a"] == "GS-102-integration-candidate"
    assert payload["case_b"] == "GS-102-integration-candidate"
    # Identity comparison: every numeric delta is zero.
    assert payload["residual_velocity_diff"]["delta"] == 0.0
    assert payload["residual_velocity_diff"]["delta_pct"] == 0.0
    assert payload["energy_balance_error_diff"]["delta_abs_pct"] == 0.0
    assert payload["perforation_marker_diff"]["same_marker"] is True
    assert payload["convergence_verdict_diff"]["same_verdict"] is True
    assert "case-vs-case" in payload["claim_impact"]
    assert "not signed validation" in payload["claim_impact"]


def test_case_comparison_returns_404_for_missing_input(
    client: _SyncASGIClient, fixture_repo: Path
) -> None:
    response = client.get(
        "/api/v1/case-comparison",
        params={"a": "GS-102-integration-candidate", "b": "GS-999-missing-candidate"},
    )
    assert response.status_code == 404


def test_case_comparison_rejects_invalid_case_id(client: _SyncASGIClient) -> None:
    response = client.get(
        "/api/v1/case-comparison",
        params={"a": "GS-102-integration-candidate", "b": "../escape"},
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------
# /api/v1/convergence-study/<case-id> (Phase 3 D)
# ---------------------------------------------------------------------


def test_convergence_study_endpoint_returns_payload(
    client: _SyncASGIClient, fixture_repo: Path
) -> None:
    response = client.get("/api/v1/convergence-study/GS-102-integration-candidate")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    payload = response.json()
    assert payload["case_id"] == "GS-102-integration-candidate"
    assert payload["combined_verdict"] == "candidate_observed_stable"
    assert "not_signed_validation" in payload["claim_boundary"]
    assert "not_benchmark_agreement" in payload["claim_boundary"]
    assert "not signed validation" in payload["claim_impact"]
    assert payload["mesh_sweep"]["candidate_stability"] == "candidate_observed_stable"


def test_convergence_study_endpoint_returns_404_for_missing(
    client: _SyncASGIClient, fixture_repo: Path
) -> None:
    response = client.get("/api/v1/convergence-study/GS-999-missing-candidate")
    assert response.status_code == 404


def test_convergence_study_endpoint_rejects_invalid_case_id(client: _SyncASGIClient) -> None:
    response = client.get("/api/v1/convergence-study/has%20space")
    assert response.status_code in (400, 404)


# ---------------------------------------------------------------------
# Cross-endpoint Tier 1 banner audit
# ---------------------------------------------------------------------


def test_no_phase23_endpoint_leaks_forbidden_positive_claims(
    client: _SyncASGIClient, fixture_repo: Path
) -> None:
    """Every Phase 2 / Phase 3 endpoint must avoid positive-claim leakage."""
    endpoints = [
        ("/api/v1/candidate-cases", None),
        ("/api/v1/tier1-report/GS-102-integration-candidate", {"fmt": "md"}),
        ("/api/v1/acceptance-packet/GS-102-integration-candidate", None),
        (
            "/api/v1/case-comparison",
            {"a": "GS-102-integration-candidate", "b": "GS-102-integration-candidate"},
        ),
        ("/api/v1/convergence-study/GS-102-integration-candidate", None),
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
        body = resp.text.lower()
        for token in forbidden:
            assert token not in body, f"{url} leaked forbidden wording {token!r}"
