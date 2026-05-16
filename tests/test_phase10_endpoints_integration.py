"""FM-04a Phase 10 F — HTTP integration tests for slice D + E surfaces.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Tests the HTTP-layer behavior of the slice 10-D rate limit + slice 10-E
canonical SHA on the existing routes. Complements:

* ``tests/test_phase10_signoff_rate_limit.py`` (service-layer +
  one HTTP smoke for the 429 path).
* ``tests/test_phase10_generator_canonicalization.py`` (service-layer
  semantics of the canonical SHA helper).

This file pushes the boundaries through the real route stack — the
rate-limit gate composes with every other gate in
``post_signoff_history``, and the canonical SHA must surface through
``GET /api/v1/trust-score-provenance``. We use ``httpx.ASGITransport``
+ a synthetic ``now=`` clock (where the route accepts one — currently
the rate limit route does NOT, so we keep wall-clock submissions
inside the 60s window).

Phase 10 anti-gaming guard E: -3 — HTTP integration must walk the
ACTUAL route stack, not a mock of it. Phase 10 anti-gaming guard E: -2
— gate ordering is tested by exercising each gate in turn, not by
inspecting `if` chain ordering in the source.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from app.api.routes import (
    signoff_history as signoff_module,
)
from app.api.routes import (
    trust_score_provenance as provenance_module,
)
from app.main import app
from app.services.reporting.cohort_snapshot import (
    SnapshotCaseInput,
    write_cohort_snapshot,
)
from app.services.reporting.signoff_rate_limit import RATE_LIMIT_MAX_REQUESTS


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

    def post(
        self, url: str, *, json_body: Any, headers: dict[str, str] | None = None
    ) -> httpx.Response:
        async def _run() -> httpx.Response:
            async with httpx.AsyncClient(
                transport=self._transport, base_url="http://testserver"
            ) as client:
                return await client.post(url, json=json_body, headers=headers)

        return asyncio.run(_run())


@pytest.fixture()
def client() -> _SyncASGIClient:
    return _SyncASGIClient(app)


@pytest.fixture()
def fake_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(signoff_module, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(provenance_module, "_repo_root", lambda: tmp_path)
    return tmp_path


def _seed_case(
    root: Path,
    case_id: str,
    *,
    generator_body: bytes = b"# placeholder\n",
) -> SnapshotCaseInput:
    case_dir = root / "golden_samples" / case_id / "data"
    case_dir.mkdir(parents=True, exist_ok=True)
    starter = case_dir / "model_00_0000.rad"
    engine = case_dir / "model_00_0001.rad"
    starter.write_text("# s", encoding="utf-8")
    engine.write_text("# e", encoding="utf-8")
    metrics = (
        root / "project_state" / "graph_executor" / case_id / "ballistic" / "ballistic_metrics.json"
    )
    metrics.parent.mkdir(parents=True, exist_ok=True)
    metrics.write_text(
        json.dumps({"case_id": case_id, "claim_boundary": "tier1"}),
        encoding="utf-8",
    )
    gen = root / "scripts" / f"gen_{case_id.lower().replace('-', '_')}.py"
    gen.parent.mkdir(parents=True, exist_ok=True)
    gen.write_bytes(generator_body)
    return SnapshotCaseInput(
        case_id=case_id,
        starter_deck_path=starter,
        engine_deck_path=engine,
        ballistic_metrics_path=metrics,
        convergence_study_path=None,
        animation_manifest_path=None,
        result_mesh_path=None,
        generator_script_path=gen,
        notes_path=None,
    )


# =====================================================================
# Section 1 — Rate-limit gate composition with peer gates (8 tests)
# =====================================================================


def test_post_signoff_415_when_content_type_is_form_urlencoded(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Content-Type gate runs BEFORE rate-limit; a non-JSON request
    must NOT consume a rate-limit slot."""
    res = client.post(
        "/api/v1/signoff-history/GS-A-candidate",
        json_body={"reviewer": "alice", "verdict": "watching", "notes": "ok"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert res.status_code == 415
    # And the slot wasn't consumed: 5 normal submissions still pass.
    for _ in range(RATE_LIMIT_MAX_REQUESTS):
        ok = client.post(
            "/api/v1/signoff-history/GS-A-candidate",
            json_body={"reviewer": "alice", "verdict": "watching", "notes": "ok"},
        )
        assert ok.status_code == 200, ok.text


def test_post_signoff_422_on_signed_registry_id_does_not_consume_slot(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Signed-registry refusal (GS-001) must fire BEFORE rate limit so
    a malicious caller cannot exhaust someone else's slot by spamming
    refused case ids."""
    refused = client.post(
        "/api/v1/signoff-history/GS-001",
        json_body={"reviewer": "alice", "verdict": "watching", "notes": "ok"},
    )
    assert refused.status_code == 422
    for _ in range(RATE_LIMIT_MAX_REQUESTS):
        ok = client.post(
            "/api/v1/signoff-history/GS-A-candidate",
            json_body={"reviewer": "alice", "verdict": "watching", "notes": "ok"},
        )
        assert ok.status_code == 200


def test_post_signoff_422_on_bad_verdict_does_not_consume_slot(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Verdict whitelist refusal must fire BEFORE rate limit (Phase 10
    blueprint §3.D — slot only consumed on allowed verdicts)."""
    bad = client.post(
        "/api/v1/signoff-history/GS-A-candidate",
        json_body={
            "reviewer": "alice",
            "verdict": "ready_for_tier_2",  # forbidden Tier 2 verb
            "notes": "shipping it",
        },
    )
    assert bad.status_code == 422
    # The 5 follow-up valid submissions all succeed.
    for _ in range(RATE_LIMIT_MAX_REQUESTS):
        ok = client.post(
            "/api/v1/signoff-history/GS-A-candidate",
            json_body={"reviewer": "alice", "verdict": "watching", "notes": "ok"},
        )
        assert ok.status_code == 200


def test_post_signoff_429_after_six_valid_submissions(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Service-layer test pinned this already; this re-pins through
    the route for E coverage."""
    for _ in range(RATE_LIMIT_MAX_REQUESTS):
        client.post(
            "/api/v1/signoff-history/GS-A-candidate",
            json_body={"reviewer": "alice", "verdict": "watching", "notes": "ok"},
        )
    res = client.post(
        "/api/v1/signoff-history/GS-A-candidate",
        json_body={"reviewer": "alice", "verdict": "watching", "notes": "ok"},
    )
    assert res.status_code == 429
    assert res.headers.get("Retry-After") is not None


def test_post_signoff_429_response_carries_retry_after_header(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Retry-After header must parse as a positive integer."""
    for _ in range(RATE_LIMIT_MAX_REQUESTS):
        client.post(
            "/api/v1/signoff-history/GS-A-candidate",
            json_body={"reviewer": "alice", "verdict": "watching", "notes": "ok"},
        )
    res = client.post(
        "/api/v1/signoff-history/GS-A-candidate",
        json_body={"reviewer": "alice", "verdict": "watching", "notes": "ok"},
    )
    retry = res.headers.get("Retry-After")
    assert retry is not None
    assert int(retry) >= 1


def test_post_signoff_rate_limit_keyed_per_reviewer_via_http(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Two reviewers on the same case have independent buckets."""
    for _ in range(RATE_LIMIT_MAX_REQUESTS):
        client.post(
            "/api/v1/signoff-history/GS-A-candidate",
            json_body={"reviewer": "alice", "verdict": "watching", "notes": "ok"},
        )
    bob = client.post(
        "/api/v1/signoff-history/GS-A-candidate",
        json_body={"reviewer": "bob", "verdict": "watching", "notes": "ok"},
    )
    assert bob.status_code == 200


def test_post_signoff_rate_limit_keyed_per_case_via_http(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Same reviewer on a different case has an independent bucket."""
    for _ in range(RATE_LIMIT_MAX_REQUESTS):
        client.post(
            "/api/v1/signoff-history/GS-A-candidate",
            json_body={"reviewer": "alice", "verdict": "watching", "notes": "ok"},
        )
    alice_b = client.post(
        "/api/v1/signoff-history/GS-B-candidate",
        json_body={"reviewer": "alice", "verdict": "watching", "notes": "ok"},
    )
    assert alice_b.status_code == 200


def test_post_signoff_429_detail_carries_case_id_and_reviewer(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """The 429 detail string must surface both the case_id and the
    reviewer so a UI can render a per-reviewer countdown."""
    for _ in range(RATE_LIMIT_MAX_REQUESTS):
        client.post(
            "/api/v1/signoff-history/GS-A-candidate",
            json_body={"reviewer": "alice", "verdict": "watching", "notes": "ok"},
        )
    res = client.post(
        "/api/v1/signoff-history/GS-A-candidate",
        json_body={"reviewer": "alice", "verdict": "watching", "notes": "ok"},
    )
    body = res.json()
    assert "GS-A-candidate" in body["detail"]
    assert "alice" in body["detail"]
    assert "rate limit exceeded" in body["detail"]


# =====================================================================
# Section 2 — Canonical SHA surfaced through provenance endpoint (8 tests)
# =====================================================================


def test_provenance_endpoint_schema_version_is_1_2_0(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    case = _seed_case(fake_repo, "GS-A-candidate")
    write_cohort_snapshot([case], repo_root=fake_repo, snapshot_label="2026-05-16T100000Z")
    res = client.get(
        "/api/v1/trust-score-provenance/GS-A-candidate",
        params={"snapshot": "2026-05-16T100000Z"},
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["schema_version"] == "1.2.0"


def test_provenance_endpoint_emits_canonical_sha_on_generator_row(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    case = _seed_case(fake_repo, "GS-A-candidate", generator_body=b"x = 1\n")
    write_cohort_snapshot([case], repo_root=fake_repo, snapshot_label="2026-05-16T100000Z")
    res = client.get(
        "/api/v1/trust-score-provenance/GS-A-candidate",
        params={"snapshot": "2026-05-16T100000Z"},
    )
    payload = res.json()
    gen = next(r for r in payload["inputs"] if r["kind"] == "generator")
    assert gen["sha256_normalized"] is not None
    assert gen["normalization_method"] == "python-ast-dump-v1"
    assert gen["normalization_error"] is None


def test_provenance_endpoint_emits_none_canonical_on_non_generator_rows(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    case = _seed_case(fake_repo, "GS-A-candidate")
    write_cohort_snapshot([case], repo_root=fake_repo, snapshot_label="2026-05-16T100000Z")
    payload = client.get(
        "/api/v1/trust-score-provenance/GS-A-candidate",
        params={"snapshot": "2026-05-16T100000Z"},
    ).json()
    non_gen = [r for r in payload["inputs"] if r["kind"] != "generator"]
    assert len(non_gen) >= 1
    for row in non_gen:
        assert row["sha256_normalized"] is None
        assert row["normalization_method"] is None
        assert row["normalization_error"] is None


def test_provenance_endpoint_whitespace_equivalence_via_http(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Two snapshots whose generators differ only in whitespace yield
    the same sha256_normalized when read through the HTTP endpoint."""
    case_a = _seed_case(fake_repo, "GS-A-candidate", generator_body=b"x = 1\n")
    case_b = _seed_case(fake_repo, "GS-B-candidate", generator_body=b"x = 1\n\n\n")
    write_cohort_snapshot(
        [case_a, case_b], repo_root=fake_repo, snapshot_label="2026-05-16T100000Z"
    )
    pa = client.get(
        "/api/v1/trust-score-provenance/GS-A-candidate",
        params={"snapshot": "2026-05-16T100000Z"},
    ).json()
    pb = client.get(
        "/api/v1/trust-score-provenance/GS-B-candidate",
        params={"snapshot": "2026-05-16T100000Z"},
    ).json()
    gen_a = next(r for r in pa["inputs"] if r["kind"] == "generator")
    gen_b = next(r for r in pb["inputs"] if r["kind"] == "generator")
    assert gen_a["sha256"] != gen_b["sha256"]
    assert gen_a["sha256_normalized"] == gen_b["sha256_normalized"]


def test_provenance_endpoint_comment_equivalence_via_http(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Two snapshots whose generators differ only in comments yield
    the same sha256_normalized when read through the HTTP endpoint."""
    case_a = _seed_case(fake_repo, "GS-A-candidate", generator_body=b"x = 1\n")
    case_b = _seed_case(
        fake_repo, "GS-B-candidate", generator_body=b"# header\nx = 1  # trailing\n"
    )
    write_cohort_snapshot(
        [case_a, case_b], repo_root=fake_repo, snapshot_label="2026-05-16T100000Z"
    )
    pa = client.get(
        "/api/v1/trust-score-provenance/GS-A-candidate",
        params={"snapshot": "2026-05-16T100000Z"},
    ).json()
    pb = client.get(
        "/api/v1/trust-score-provenance/GS-B-candidate",
        params={"snapshot": "2026-05-16T100000Z"},
    ).json()
    gen_a = next(r for r in pa["inputs"] if r["kind"] == "generator")
    gen_b = next(r for r in pb["inputs"] if r["kind"] == "generator")
    assert gen_a["sha256_normalized"] == gen_b["sha256_normalized"]


def test_provenance_endpoint_logic_change_differs_via_http(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    case_a = _seed_case(fake_repo, "GS-A-candidate", generator_body=b"x = 1\n")
    case_b = _seed_case(fake_repo, "GS-B-candidate", generator_body=b"x = 2\n")
    write_cohort_snapshot(
        [case_a, case_b], repo_root=fake_repo, snapshot_label="2026-05-16T100000Z"
    )
    pa = client.get(
        "/api/v1/trust-score-provenance/GS-A-candidate",
        params={"snapshot": "2026-05-16T100000Z"},
    ).json()
    pb = client.get(
        "/api/v1/trust-score-provenance/GS-B-candidate",
        params={"snapshot": "2026-05-16T100000Z"},
    ).json()
    gen_a = next(r for r in pa["inputs"] if r["kind"] == "generator")
    gen_b = next(r for r in pb["inputs"] if r["kind"] == "generator")
    assert gen_a["sha256_normalized"] != gen_b["sha256_normalized"]


def test_provenance_endpoint_parse_failure_surfaces_through_http(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    case = _seed_case(fake_repo, "GS-A-candidate", generator_body=b"def broken(:\n    pass\n")
    write_cohort_snapshot([case], repo_root=fake_repo, snapshot_label="2026-05-16T100000Z")
    res = client.get(
        "/api/v1/trust-score-provenance/GS-A-candidate",
        params={"snapshot": "2026-05-16T100000Z"},
    )
    assert res.status_code == 200
    payload = res.json()
    gen = next(r for r in payload["inputs"] if r["kind"] == "generator")
    # Raw SHA still present (the bytes ARE on disk), canonical SHA None,
    # error string surfaces the parse failure reason.
    assert gen["sha256"] == hashlib.sha256(b"def broken(:\n    pass\n").hexdigest()
    assert gen["sha256_normalized"] is None
    assert gen["normalization_method"] is None
    assert gen["normalization_error"] is not None
    assert "SyntaxError" in gen["normalization_error"]


def test_provenance_endpoint_preserves_tier1_disclaimer_after_bump(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    case = _seed_case(fake_repo, "GS-A-candidate")
    write_cohort_snapshot([case], repo_root=fake_repo, snapshot_label="2026-05-16T100000Z")
    payload = client.get(
        "/api/v1/trust-score-provenance/GS-A-candidate",
        params={"snapshot": "2026-05-16T100000Z"},
    ).json()
    body_lower = json.dumps(payload).lower()
    assert "tier 1 engineering candidate" in body_lower
    assert "not signed validation" in body_lower
    assert "not benchmark agreement" in body_lower
