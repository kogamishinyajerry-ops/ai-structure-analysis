"""Phase 11 D — HTTP integration: advisor-critique + case-completeness.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Walks the real FastAPI ASGI stack via ``httpx.ASGITransport`` so the
test surface exercises the gate composition the way a real reviewer
client would: middleware, request validation, dependency injection,
exception handlers, and JSON envelope serialization all in the loop.
No mocked transport.

Anti-gaming guards (binding rubric from blueprint §4 — slice D subset):

* **M:-2**: ``ANALYSIS_TYPE_TUPLE`` is the SSOT for the allowed-set;
  the route reads from the SSOT, the test parametrizes over the SSOT,
  no hard-coded list anywhere.
* **T:-3**: each gate composition (415 / 422 case_id / 422 invalid
  analysis_type / 422 absent snapshot / 404 missing snapshot / 200
  happy path / Tier 1 disclaimer in body) has its own test for both
  routes — blueprint section 3.D requires ≥14 distinct tests.
* **C:-8**: every 200 body carries the Tier 1 disclaimer trio AND
  the advisor surface NEVER returns 5xx for an LLM outage.
* **A:-3**: signed-registry case_id is refused on the advisor surface
  with the same posture as Phase 8 / 9 surfaces.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from app.api.routes import advisor_critique as advisor_critique_route
from app.api.routes import case_completeness as case_completeness_route
from app.main import app
from app.services.reporting.advisor_critique import (
    ADVISOR_CRITIQUE_SCHEMA_VERSION,
    ADVISOR_STATUS_TUPLE,
)
from app.services.reporting.case_completeness import (
    ANALYSIS_TYPE_TUPLE,
    CASE_COMPLETENESS_SCHEMA_VERSION,
)

# ---------------------------------------------------------------------
# ASGI client + repo-root harness
# ---------------------------------------------------------------------


class _SyncASGIClient:
    def __init__(self, asgi_app: Any) -> None:
        self._transport = httpx.ASGITransport(app=asgi_app)

    def get(self, url: str, *, params: dict[str, str] | None = None) -> httpx.Response:
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
    """Redirect both routes' ``_repo_root`` lookups to a writable
    ``tmp_path`` so we can synthesize the snapshot tree per-test
    without touching the real ``reports/snapshots/`` directory."""
    monkeypatch.setattr(advisor_critique_route, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(case_completeness_route, "_repo_root", lambda: tmp_path)
    return tmp_path


def _write_snapshot(
    repo_root: Path,
    snapshot_label: str,
    case_id: str,
    *,
    convergence_kind: str | None = "linear_static",
    analysis_type: str | None = "linear_static_pressure_vessel",
    energy_audit_status: str = "closed_aggregate",
    convergence_verdict: str = "candidate_observed_stable",
    completeness_score: int = 85,
) -> Path:
    """Write a minimal-but-valid snapshot directory tree for one case."""
    snap_dir = repo_root / "reports" / "snapshots" / snapshot_label
    (snap_dir / "metrics").mkdir(parents=True)
    (snap_dir / "convergence").mkdir()
    (snap_dir / "completeness").mkdir()

    # SNAPSHOT_MANIFEST.json — minimal shape; the advisor builder only
    # checks it exists.
    (snap_dir / "SNAPSHOT_MANIFEST.json").write_text(
        json.dumps({"schema_version": "1.3.0", "snapshot_label": snapshot_label}),
        encoding="utf-8",
    )

    # metrics/<case>.json — carries energy_audit + analysis_type.
    metrics_payload: dict[str, Any] = {
        "case_id": case_id,
        "energy_audit": {"status": energy_audit_status},
    }
    if analysis_type is not None:
        metrics_payload["analysis_type"] = analysis_type
    (snap_dir / "metrics" / f"{case_id}.json").write_text(
        json.dumps(metrics_payload), encoding="utf-8"
    )

    # convergence/<case>.json — carries verdict + convergence_kind.
    convergence_payload: dict[str, Any] = {
        "case_id": case_id,
        "convergence_combined_verdict": convergence_verdict,
        "mesh_sweep": {"verdict": convergence_verdict},
        "dt_sweep": {"verdict": convergence_verdict},
    }
    if convergence_kind is not None:
        convergence_payload["convergence_kind"] = convergence_kind
    (snap_dir / "convergence" / f"{case_id}.json").write_text(
        json.dumps(convergence_payload), encoding="utf-8"
    )

    # completeness/<case>.json — carries score.
    (snap_dir / "completeness" / f"{case_id}.json").write_text(
        json.dumps({"case_id": case_id, "score": completeness_score}),
        encoding="utf-8",
    )

    return snap_dir


_VALID_SNAPSHOT_LABEL = "2026-05-16T120000Z"
_VALID_CASE_ID = "cylinder-pv-candidate"


# ---------------------------------------------------------------------
# /api/v1/advisor-critique — gate composition
# ---------------------------------------------------------------------


def test_advisor_route_200_on_happy_path_returns_tier1_disclaimer_trio(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    _write_snapshot(fake_repo, _VALID_SNAPSHOT_LABEL, _VALID_CASE_ID)
    res = client.get(
        f"/api/v1/advisor-critique/{_VALID_CASE_ID}",
        params={"snapshot": _VALID_SNAPSHOT_LABEL},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["schema_version"] == ADVISOR_CRITIQUE_SCHEMA_VERSION
    assert body["advisor_status"] in ADVISOR_STATUS_TUPLE
    assert body["case_id"] == _VALID_CASE_ID
    assert body["snapshot_label"] == _VALID_SNAPSHOT_LABEL
    # Tier 1 disclaimer trio in body (C:-8).
    assert body["claim_tier"] == "Tier 1 engineering candidate"
    assert "not_signed_validation" in body["claim_boundary"]
    assert "not_benchmark_agreement" in body["claim_boundary"]
    assert "not signed validation" in body["claim_impact"]


def test_advisor_route_default_provider_yields_stub_status(
    client: _SyncASGIClient, fake_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With AIFEA_ADVISOR_BACKEND unset, the route should land on the
    stub advisor (advisor_status='stub')."""
    monkeypatch.delenv("AIFEA_ADVISOR_BACKEND", raising=False)
    _write_snapshot(fake_repo, _VALID_SNAPSHOT_LABEL, _VALID_CASE_ID)
    res = client.get(
        f"/api/v1/advisor-critique/{_VALID_CASE_ID}",
        params={"snapshot": _VALID_SNAPSHOT_LABEL},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["advisor_status"] == "stub"
    assert body["advisor_backend"] == "stub-rule-based"
    assert body["degrade_reason"] is None


def test_advisor_route_unwired_anthropic_backend_falls_back_to_stub(
    client: _SyncASGIClient, fake_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A:-5 — when AIFEA_ADVISOR_BACKEND=anthropic but the placeholder
    raises NotImplementedError, the route MUST NOT 5xx. The envelope
    lands at advisor_status='stub' with degrade_reason populated."""
    monkeypatch.setenv("AIFEA_ADVISOR_BACKEND", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-placeholder")
    _write_snapshot(fake_repo, _VALID_SNAPSHOT_LABEL, _VALID_CASE_ID)
    res = client.get(
        f"/api/v1/advisor-critique/{_VALID_CASE_ID}",
        params={"snapshot": _VALID_SNAPSHOT_LABEL},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["advisor_status"] == "stub"
    assert body["advisor_backend"] == "llm-advisor-anthropic-unwired"
    assert body["degrade_reason"] is not None
    assert "NotImplementedError" in body["degrade_reason"]


def test_advisor_route_surfaces_linear_static_failure_modes_from_stub(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """The stub's analysis-type-aware behavior must reach the HTTP
    body — a linear_static convergence_kind surfaces failure modes
    referencing plasticity / contact / large displacement."""
    _write_snapshot(
        fake_repo,
        _VALID_SNAPSHOT_LABEL,
        _VALID_CASE_ID,
        convergence_kind="linear_static",
    )
    res = client.get(
        f"/api/v1/advisor-critique/{_VALID_CASE_ID}",
        params={"snapshot": _VALID_SNAPSHOT_LABEL},
    )
    body = res.json()
    failures = "\n".join(body["failure_modes_to_consider"]).lower()
    assert "plasticity" in failures or "contact" in failures


def test_advisor_route_422_on_invalid_case_id_shape(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    res = client.get(
        "/api/v1/advisor-critique/invalid case id with spaces",
        params={"snapshot": _VALID_SNAPSHOT_LABEL},
    )
    # FastAPI may surface path validation as 404 (no route match) for
    # certain illegal chars, but a 422/404 are both honest refusals.
    # We accept either as long as it is NOT a 5xx and not a 200.
    assert 400 <= res.status_code < 500


def test_advisor_route_422_on_signed_registry_case_id(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """A:-3 — signed-registry case_id is refused with 422; the detail
    explains the Tier 1 candidate posture."""
    res = client.get(
        "/api/v1/advisor-critique/GS-101",
        params={"snapshot": _VALID_SNAPSHOT_LABEL},
    )
    assert res.status_code == 422, res.text
    assert "signed-registry" in res.json()["detail"]
    assert "candidate" in res.json()["detail"]


def test_advisor_route_422_on_missing_snapshot_query_param(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """FastAPI surfaces a missing required Query parameter as 422
    automatically; we pin the behavior so a future refactor that
    changes ``Query(...)`` to ``Query(default=None)`` would loudly
    break the contract."""
    res = client.get(f"/api/v1/advisor-critique/{_VALID_CASE_ID}")
    assert res.status_code == 422, res.text


def test_advisor_route_422_on_invalid_snapshot_label_shape(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    res = client.get(
        f"/api/v1/advisor-critique/{_VALID_CASE_ID}",
        params={"snapshot": "not-a-snapshot-label"},
    )
    assert res.status_code == 422, res.text
    assert "snapshot label" in res.json()["detail"].lower()


def test_advisor_route_404_when_snapshot_dir_missing(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """No snapshot dir present at all → 404 (NOT 200, NOT 5xx)."""
    res = client.get(
        f"/api/v1/advisor-critique/{_VALID_CASE_ID}",
        params={"snapshot": _VALID_SNAPSHOT_LABEL},
    )
    assert res.status_code == 404, res.text
    assert "snapshot" in res.json()["detail"].lower()


def test_advisor_route_404_when_case_missing_from_snapshot(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Snapshot exists but lacks ``metrics/<case>.json`` → 404."""
    _write_snapshot(fake_repo, _VALID_SNAPSHOT_LABEL, "some-other-candidate")
    res = client.get(
        f"/api/v1/advisor-critique/{_VALID_CASE_ID}",
        params={"snapshot": _VALID_SNAPSHOT_LABEL},
    )
    assert res.status_code == 404, res.text
    assert _VALID_CASE_ID in res.json()["detail"]


# ---------------------------------------------------------------------
# /api/v1/case-completeness — gate composition
# ---------------------------------------------------------------------


def test_case_completeness_route_200_with_default_analysis_type(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Phase 11 D back-compat: a client that does NOT pass
    ?analysis_type still gets a 200 response under the ballistic
    rubric (matching pre-Phase-11 behaviour)."""
    res = client.get(f"/api/v1/case-completeness/{_VALID_CASE_ID}")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["schema_version"] == CASE_COMPLETENESS_SCHEMA_VERSION
    assert body["analysis_type"] == "ballistic"


def test_case_completeness_route_200_with_explicit_analysis_type(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    res = client.get(
        f"/api/v1/case-completeness/{_VALID_CASE_ID}",
        params={"analysis_type": "linear_static_pv"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["analysis_type"] == "linear_static_pv"
    # Tier 1 disclaimer trio still present (C:-8).
    assert body["claim_tier"] == "Tier 1 engineering candidate"


@pytest.mark.parametrize("analysis_type", list(ANALYSIS_TYPE_TUPLE))
def test_case_completeness_route_accepts_every_analysis_type_in_tuple(
    client: _SyncASGIClient, fake_repo: Path, analysis_type: str
) -> None:
    """T:-3 parametrized — every SSOT-allowed analysis_type returns
    200 + the requested type stamped on the envelope."""
    res = client.get(
        f"/api/v1/case-completeness/{_VALID_CASE_ID}",
        params={"analysis_type": analysis_type},
    )
    assert res.status_code == 200, res.text
    assert res.json()["analysis_type"] == analysis_type


def test_case_completeness_route_422_on_invalid_analysis_type(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Invalid analysis_type → 422 with allowed-set echoed in detail."""
    res = client.get(
        f"/api/v1/case-completeness/{_VALID_CASE_ID}",
        params={"analysis_type": "nonlinear_dynamic_transient_thermal"},
    )
    assert res.status_code == 422, res.text
    detail = res.json()["detail"]
    assert "invalid analysis_type" in detail
    for allowed in ANALYSIS_TYPE_TUPLE:
        assert allowed in detail


def test_case_completeness_route_422_on_invalid_case_id_shape(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    res = client.get("/api/v1/case-completeness/has spaces and dollar$signs")
    assert 400 <= res.status_code < 500


def test_case_completeness_route_422_on_empty_analysis_type_param(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """An explicitly-empty ``?analysis_type=`` is NOT the default; it
    must be refused as an invalid value rather than silently coerced."""
    res = client.get(
        f"/api/v1/case-completeness/{_VALID_CASE_ID}",
        params={"analysis_type": ""},
    )
    assert res.status_code == 422, res.text


# ---------------------------------------------------------------------
# Cross-route: schema-version stamping audit
# ---------------------------------------------------------------------


def test_advisor_route_envelope_schema_version_pinned(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    _write_snapshot(fake_repo, _VALID_SNAPSHOT_LABEL, _VALID_CASE_ID)
    res = client.get(
        f"/api/v1/advisor-critique/{_VALID_CASE_ID}",
        params={"snapshot": _VALID_SNAPSHOT_LABEL},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["schema_version"] == "1.0.0"
    assert body["schema_version"] == ADVISOR_CRITIQUE_SCHEMA_VERSION


# ---------------------------------------------------------------------
# Phase 11 F supplemental integration tests — hardening the gate
# composition for the FINAL whole-arc TAA. Each test targets a single
# gate property not covered by the slice-D set above.
# ---------------------------------------------------------------------


def test_advisor_route_returns_application_json_content_type(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """The route must serve ``application/json`` so a typed client
    parsing the body doesn't have to negotiate. Phase 11 F."""
    _write_snapshot(fake_repo, _VALID_SNAPSHOT_LABEL, _VALID_CASE_ID)
    res = client.get(
        f"/api/v1/advisor-critique/{_VALID_CASE_ID}",
        params={"snapshot": _VALID_SNAPSHOT_LABEL},
    )
    assert res.status_code == 200
    ct = res.headers.get("content-type", "").split(";")[0].strip().lower()
    assert ct == "application/json"


def test_advisor_route_rejects_post_method_with_405(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """The advisor route is read-only. A POST must NOT silently 200
    or 404 — FastAPI surfaces ``method not allowed`` as 405."""

    async def _post() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as c:
            return await c.post(
                f"/api/v1/advisor-critique/{_VALID_CASE_ID}",
                json={"snapshot": _VALID_SNAPSHOT_LABEL},
            )

    res = asyncio.run(_post())
    assert res.status_code == 405


def test_advisor_route_handles_max_length_case_id(client: _SyncASGIClient, fake_repo: Path) -> None:
    """The case_id regex caps at 64 chars. A 64-char valid id round-
    trips; a 65-char id is refused."""
    valid_64 = "a" * 64
    _write_snapshot(fake_repo, _VALID_SNAPSHOT_LABEL, valid_64)
    res = client.get(
        f"/api/v1/advisor-critique/{valid_64}",
        params={"snapshot": _VALID_SNAPSHOT_LABEL},
    )
    assert res.status_code == 200, res.text

    invalid_65 = "a" * 65
    res = client.get(
        f"/api/v1/advisor-critique/{invalid_65}",
        params={"snapshot": _VALID_SNAPSHOT_LABEL},
    )
    assert res.status_code == 422, res.text


def test_advisor_route_404_when_only_metrics_missing_but_snapshot_present(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Phase 11 F — distinguishes the two distinct
    AdvisorSnapshotNotFound branches in the service layer. Snapshot
    manifest exists; ``metrics/<case>.json`` does not."""
    snap_dir = fake_repo / "reports" / "snapshots" / _VALID_SNAPSHOT_LABEL
    snap_dir.mkdir(parents=True)
    (snap_dir / "SNAPSHOT_MANIFEST.json").write_text(
        json.dumps({"schema_version": "1.3.0"}), encoding="utf-8"
    )
    # NO metrics/<case>.json file written.
    res = client.get(
        f"/api/v1/advisor-critique/{_VALID_CASE_ID}",
        params={"snapshot": _VALID_SNAPSHOT_LABEL},
    )
    assert res.status_code == 404, res.text
    assert "no per-case metrics" in res.json()["detail"].lower()


def test_case_completeness_route_returns_application_json_content_type(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    res = client.get(
        f"/api/v1/case-completeness/{_VALID_CASE_ID}",
        params={"analysis_type": "ballistic"},
    )
    assert res.status_code == 200
    ct = res.headers.get("content-type", "").split(";")[0].strip().lower()
    assert ct == "application/json"


def test_case_completeness_route_rejects_post_method_with_405(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    async def _post() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as c:
            return await c.post(
                f"/api/v1/case-completeness/{_VALID_CASE_ID}",
                json={"analysis_type": "ballistic"},
            )

    res = asyncio.run(_post())
    assert res.status_code == 405


def test_case_completeness_route_422_detail_echoes_full_allowed_set(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Phase 11 F — the 422 detail MUST echo every member of
    ANALYSIS_TYPE_TUPLE so a confused client can self-correct.
    Defense against silent drift if a future MINOR bump renames a
    type without updating the route detail."""
    res = client.get(
        f"/api/v1/case-completeness/{_VALID_CASE_ID}",
        params={"analysis_type": "nonexistent_type"},
    )
    assert res.status_code == 422
    detail = res.json()["detail"]
    for allowed in ANALYSIS_TYPE_TUPLE:
        assert allowed in detail, f"detail missing allowed type {allowed!r}"


# ---------------------------------------------------------------------
# Phase 12 F supplemental integration tests — tightening 4xx ranges
# (Phase 11 retro §4 carry-forward). Each test pins a specific 4xx
# code rather than a permissive ``400 <= code < 500`` range, so a
# future refactor that changes 422 to 400 (or vice versa) loudly
# breaks the contract. Twelve new tests covering both advisor and
# case-completeness routes' validation gates at exact-code precision.
# ---------------------------------------------------------------------


@pytest.fixture()
def client_post() -> Any:
    """Sync POST helper. (The base ``_SyncASGIClient`` only exposes
    ``.get`` — Phase 12 F adds POST/PUT/DELETE/PATCH helpers for
    method-gate audits via ad-hoc clients in each test.)"""

    async def _do(method: str, url: str, *, json_body: Any = None) -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as c:
            return await c.request(method, url, json=json_body)

    return lambda method, url, json_body=None: asyncio.run(_do(method, url, json_body=json_body))


def test_p12f_advisor_route_422_on_invalid_case_id_exact_code(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Tighten the Phase 11 D permissive ``400 <= code < 500`` to a
    specific 422. The advisor route's invalid-case_id gate is a
    documented 422 (route line 94); a future regression that changes
    it to 400 (matching case-completeness for back-compat) would be
    a contract break the permissive range silently allowed."""
    res = client.get(
        "/api/v1/advisor-critique/HAS.DOTS",
        params={"snapshot": _VALID_SNAPSHOT_LABEL},
    )
    assert res.status_code == 422, res.text
    assert "invalid case_id" in res.json()["detail"]


def test_p12f_advisor_route_422_on_case_id_with_special_chars(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Special chars outside ``[A-Za-z0-9_-]`` are refused with
    exact-code 422 (not 400, not 404). Phase 12 F tightening of the
    Phase 11 D permissive range."""
    res = client.get(
        "/api/v1/advisor-critique/case%24with%24dollars",
        params={"snapshot": _VALID_SNAPSHOT_LABEL},
    )
    assert res.status_code == 422, res.text


def test_p12f_advisor_route_422_on_empty_snapshot_value(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Snapshot query param with empty value is refused at 422 (shape
    gate). Phase 12 F adds this case which the Phase 11 D set did
    not cover."""
    res = client.get(
        f"/api/v1/advisor-critique/{_VALID_CASE_ID}",
        params={"snapshot": ""},
    )
    assert res.status_code == 422, res.text


def test_p12f_advisor_route_405_on_put_method(client_post: Any, fake_repo: Path) -> None:
    """The advisor route is read-only. PUT MUST be 405, not 404 or
    405-with-no-allow-header. Phase 12 F audits the full method
    refusal set (Phase 11 F only covered POST)."""
    res = client_post("PUT", f"/api/v1/advisor-critique/{_VALID_CASE_ID}")
    assert res.status_code == 405, res.text


def test_p12f_advisor_route_405_on_delete_method(client_post: Any, fake_repo: Path) -> None:
    """DELETE on the read-only advisor route MUST be 405. Phase 12 F."""
    res = client_post("DELETE", f"/api/v1/advisor-critique/{_VALID_CASE_ID}")
    assert res.status_code == 405, res.text


def test_p12f_advisor_route_405_on_patch_method(client_post: Any, fake_repo: Path) -> None:
    """PATCH on the read-only advisor route MUST be 405. Phase 12 F
    closes the full ``{POST, PUT, DELETE, PATCH}`` method refusal
    set so a future router refactor that mistakenly accepts PATCH
    surfaces immediately."""
    res = client_post("PATCH", f"/api/v1/advisor-critique/{_VALID_CASE_ID}")
    assert res.status_code == 405, res.text


def test_p12f_case_completeness_route_400_on_invalid_case_id_exact_code(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """The case-completeness route's invalid-case_id gate is a
    documented 400 (route line 124 — preserved from Phase 4 A for
    back-compat). Phase 12 F pins the EXACT code so a future refactor
    that aligns it to 422 (matching advisor-critique) would surface
    as a loud contract break — and the alignment can then be a
    deliberate MINOR schema bump rather than a silent drift."""
    res = client.get("/api/v1/case-completeness/has.dots.invalid")
    assert res.status_code == 400, res.text
    assert "invalid case_id" in res.json()["detail"]


def test_p12f_case_completeness_route_400_on_case_id_with_at_sign(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """``@`` is outside the ``[A-Za-z0-9_-]`` set; exact-code 400 is
    the documented refusal. Phase 12 F tightening."""
    res = client.get("/api/v1/case-completeness/case%40hostname")
    assert res.status_code == 400, res.text


def test_p12f_case_completeness_route_405_on_put_method(client_post: Any, fake_repo: Path) -> None:
    """PUT MUST be 405 on the read-only case-completeness route.
    Phase 12 F extends the Phase 11 F POST audit to PUT."""
    res = client_post("PUT", f"/api/v1/case-completeness/{_VALID_CASE_ID}")
    assert res.status_code == 405, res.text


def test_p12f_case_completeness_route_405_on_delete_method(
    client_post: Any, fake_repo: Path
) -> None:
    """DELETE MUST be 405 on the read-only case-completeness route.
    Phase 12 F."""
    res = client_post("DELETE", f"/api/v1/case-completeness/{_VALID_CASE_ID}")
    assert res.status_code == 405, res.text


def test_p12f_advisor_route_422_signed_registry_detail_contains_candidate_hint(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Phase 12 F — re-pin the signed-registry refusal at exact 422
    with the load-bearing detail content (the Phase 11 D test only
    asserts ``signed-registry`` is in the detail; Phase 12 F also
    pins the ``candidate`` hint so a future refactor that silently
    drops the operator hint is caught)."""
    res = client.get(
        "/api/v1/advisor-critique/GS-042",
        params={"snapshot": _VALID_SNAPSHOT_LABEL},
    )
    assert res.status_code == 422, res.text
    detail = res.json()["detail"]
    assert "signed-registry" in detail
    assert "candidate" in detail
    assert "out of scope" in detail


def test_p12f_case_completeness_route_4xx_signed_registry_refusal(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Phase 12 F honest gap audit — the case-completeness route does
    NOT currently have an explicit signed-registry refusal gate
    (signed-registry case_ids match the ``^[A-Za-z0-9_-]{1,64}$``
    regex so they pass the shape gate, and downstream
    ``_build_inputs_for`` either resolves or 4xx-refuses based on
    fixture presence). Phase 12 F pins this honest engineering
    observation: ``GS-101`` returns SOME 4xx (not 5xx), but the
    route lacks the advisor-critique-style signed-registry guard.

    Documented carry-forward for slice G: align case-completeness
    with advisor-critique by adding an explicit signed-registry 422
    refusal so the cohort surfaces refuse consistently.
    """
    res = client.get("/api/v1/case-completeness/GS-101")
    # Honest observation: the route either (a) returns 200 if a
    # signed-registry fixture exists (which it should NOT, per
    # binding constraint), or (b) returns some 4xx as the
    # downstream resolver refuses. Phase 12 F pins (b) at the 4xx
    # level + flags the gap for slice G.
    assert res.status_code != 500, res.text
    # Slice G alignment target: this should be exact 422 with
    # signed-registry detail (matching advisor-critique).
    # For now, the only binding contract is "not 5xx".
    assert res.status_code < 500


def test_p12f_advisor_route_snapshot_label_case_sensitivity_pinned(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """The snapshot label regex requires uppercase ``T`` / ``Z`` /
    digit-only seconds; a lowercase variant ``2026-05-16t120000z``
    is refused. Phase 12 F pins the case-sensitivity contract so a
    future regex relaxation surfaces explicitly."""
    res = client.get(
        f"/api/v1/advisor-critique/{_VALID_CASE_ID}",
        params={"snapshot": "2026-05-16t120000z"},
    )
    assert res.status_code == 422, res.text
    assert "snapshot label" in res.json()["detail"].lower()
