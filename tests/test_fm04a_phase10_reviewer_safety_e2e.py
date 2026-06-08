"""FM-04a Phase 10 F — E2E reviewer journeys for slice D + E.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Three load-bearing reviewer journeys that compose the Phase 10 D rate
limit + Phase 10 E canonical SHA surfaces with the prior Phase 8/9
surfaces end-to-end across the HTTP layer:

  1. test_phase10_rate_limit_recovery_then_signoff_e2e — Reviewer hits
     the rate-limit ceiling on a case, receives 429 + Retry-After,
     waits past the window (mocked-window via `_reset_state_for_tests`,
     not a real sleep), submits a 6th valid signoff, then re-fetches
     the cohort summary and confirms the verdict landed.

  2. test_phase10_generator_whitespace_equivalence_round_trip_e2e —
     Two snapshots of the same case differ only in whitespace in the
     generator script. The HTTP provenance endpoint reports the same
     `sha256_normalized` on both, despite different raw `sha256`.
     Proves the canonicalization is a useful equivalence over the
     wire, not just at the service layer.

  3. test_phase10_parse_failure_does_not_break_other_endpoints_e2e —
     A case with a broken generator (SyntaxError on `ast.parse`) is
     served by the provenance endpoint with `normalization_error`
     surfaced and `sha256_normalized=None`; the cohort summary +
     signoff history endpoints still serve normally and the
     reviewer can still POST a signoff. Proves a corrupt generator
     does not poison the rest of the reviewer surface.

Phase 10 anti-gaming guard E: -3 — these tests walk the real route
stack, not a mock. Phase 10 anti-gaming guard E: -4 — each journey
crosses ≥2 routes (rate-limit + signoff history + executive summary
for #1; provenance + cohort summary for #2; provenance + signoff +
history + summary for #3).
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
    cohort_executive_summary as exec_module,
)
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
from app.services.reporting.signoff_rate_limit import (
    RATE_LIMIT_MAX_REQUESTS,
    _reset_state_for_tests,
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

    def post(self, url: str, *, json_body: Any) -> httpx.Response:
        async def _run() -> httpx.Response:
            async with httpx.AsyncClient(
                transport=self._transport, base_url="http://testserver"
            ) as client:
                return await client.post(url, json=json_body)

        return asyncio.run(_run())


@pytest.fixture()
def client() -> _SyncASGIClient:
    return _SyncASGIClient(app)


@pytest.fixture()
def fake_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(signoff_module, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(provenance_module, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(exec_module, "_repo_root", lambda: tmp_path)
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


# ---------------------------------------------------------------------
# E2E #1 — Rate-limit recovery → signoff lands in cohort summary
# ---------------------------------------------------------------------


def test_phase10_rate_limit_recovery_then_signoff_e2e(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Reviewer journey: hit the 5-per-window ceiling, receive a 429
    with Retry-After, the rate-limit state is reset (simulating window
    expiry — no real sleep), the 6th valid signoff lands, history
    surfaces it, cohort summary bucket flips to ``regressed``.
    """
    case = _seed_case(fake_repo, "GS-A-candidate")
    write_cohort_snapshot([case], repo_root=fake_repo, snapshot_label="2026-05-16T100000Z")

    # 1) Fill the bucket with 5 valid submissions.
    for i in range(RATE_LIMIT_MAX_REQUESTS):
        res = client.post(
            "/api/v1/signoff-history/GS-A-candidate",
            json_body={
                "reviewer": "alice",
                "verdict": "watching",
                "notes": f"submission #{i + 1}",
            },
        )
        assert res.status_code == 200, res.text

    # 2) The 6th submission is refused with 429 + Retry-After.
    refused = client.post(
        "/api/v1/signoff-history/GS-A-candidate",
        json_body={
            "reviewer": "alice",
            "verdict": "blocked_pending_input",
            "notes": "waiting on material card",
        },
    )
    assert refused.status_code == 429
    retry = refused.headers.get("Retry-After")
    assert retry is not None and int(retry) >= 1
    assert "rate limit exceeded" in refused.json()["detail"]

    # 3) Simulate window expiry by resetting the state (the autouse
    # conftest fixture only fires between tests). In production the
    # bucket would drain naturally as 60-second-old entries evict.
    _reset_state_for_tests()

    # 4) The next submission lands cleanly.
    landed = client.post(
        "/api/v1/signoff-history/GS-A-candidate",
        json_body={
            "reviewer": "alice",
            "verdict": "blocked_pending_input",
            "notes": "waiting on material card",
        },
    )
    assert landed.status_code == 200
    landed_body = landed.json()
    assert landed_body["verdict"] == "blocked_pending_input"

    # 5) History surfaces at least one record. (Record filenames are
    # UTC-second-precision, so multiple submissions inside the same
    # second collapse to a single on-disk record — the cohort summary
    # below reads the latest verdict regardless.)
    history = client.get("/api/v1/signoff-history/GS-A-candidate").json()
    assert history["record_count"] >= 1
    # The most recent record carries the post-recovery verdict.
    assert history["records"][-1]["verdict"] == "blocked_pending_input"

    # 6) Cohort summary bucket flips: blocked_pending_input is the
    # precedence-#1 verdict, so the cohort bucket must be ``regressed``.
    summary = client.get("/api/v1/cohort-executive-summary").json()
    row = next(c for c in summary["cases"] if c["case_id"] == "GS-A-candidate")
    assert row["latest_signoff_verdict"] == "blocked_pending_input"
    assert row["bucket"] == "regressed"

    # 7) Tier 1 disclaimer trio survives every response.
    for body in (landed_body, history, summary):
        text = json.dumps(body).lower()
        assert "tier 1 engineering candidate" in text
        assert "not signed validation" in text
        assert "not benchmark agreement" in text


# ---------------------------------------------------------------------
# E2E #2 — Generator whitespace equivalence over the wire
# ---------------------------------------------------------------------


def test_phase10_generator_whitespace_equivalence_round_trip_e2e(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Reviewer journey: two cases whose generators differ only in
    whitespace produce the same `sha256_normalized` over the HTTP
    provenance endpoint, even though raw `sha256` differs. Proves the
    canonical SHA is useful as an equivalence over the wire.
    """
    case_a = _seed_case(
        fake_repo,
        "GS-A-candidate",
        generator_body=b"def f():\n    return 1\n",
    )
    case_b = _seed_case(
        fake_repo,
        "GS-B-candidate",
        generator_body=b"def f():\n\n    return 1\n\n\n",
    )
    write_cohort_snapshot(
        [case_a, case_b],
        repo_root=fake_repo,
        snapshot_label="2026-05-16T100000Z",
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

    # Raw bytes differ.
    assert gen_a["sha256"] != gen_b["sha256"]
    # Canonical (AST-dump) SHAs match — whitespace-insensitive equivalence.
    assert gen_a["sha256_normalized"] == gen_b["sha256_normalized"]
    assert gen_a["normalization_method"] == "python-ast-dump-v1"
    assert gen_a["normalization_error"] is None

    # Both cases co-exist in the cohort summary.
    summary = client.get("/api/v1/cohort-executive-summary").json()
    case_ids = {c["case_id"] for c in summary["cases"]}
    assert {"GS-A-candidate", "GS-B-candidate"}.issubset(case_ids)

    # Tier 1 disclaimer trio on both provenance responses.
    for body in (pa, pb):
        text = json.dumps(body).lower()
        assert "tier 1 engineering candidate" in text
        assert "not signed validation" in text
        assert "not benchmark agreement" in text


# ---------------------------------------------------------------------
# E2E #3 — Broken generator does not poison the reviewer surface
# ---------------------------------------------------------------------


def test_phase10_parse_failure_does_not_break_other_endpoints_e2e(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Reviewer journey: a case with a generator script that fails
    `ast.parse` surfaces the parse error in the provenance endpoint
    but does NOT break the signoff POST + history GET + cohort
    summary endpoints. The reviewer can still record a verdict.
    """
    broken_body = b"def broken(:\n    return 1\n"  # SyntaxError
    case = _seed_case(fake_repo, "GS-A-candidate", generator_body=broken_body)
    write_cohort_snapshot([case], repo_root=fake_repo, snapshot_label="2026-05-16T100000Z")

    # 1) Provenance endpoint serves 200 with the parse error surfaced.
    prov = client.get(
        "/api/v1/trust-score-provenance/GS-A-candidate",
        params={"snapshot": "2026-05-16T100000Z"},
    )
    assert prov.status_code == 200
    prov_body = prov.json()
    gen = next(r for r in prov_body["inputs"] if r["kind"] == "generator")
    assert gen["sha256"] == hashlib.sha256(broken_body).hexdigest()
    assert gen["sha256_normalized"] is None
    assert gen["normalization_method"] is None
    assert gen["normalization_error"] is not None
    assert "SyntaxError" in gen["normalization_error"]

    # 2) Signoff POST still works — broken generator does not block
    # the reviewer from recording a verdict.
    posted = client.post(
        "/api/v1/signoff-history/GS-A-candidate",
        json_body={
            "reviewer": "alice",
            "verdict": "needs_more_evidence",
            "notes": "generator script is broken, needs maintainer attention",
        },
    )
    assert posted.status_code == 200
    assert posted.json()["verdict"] == "needs_more_evidence"

    # 3) History GET surfaces the new record.
    history = client.get("/api/v1/signoff-history/GS-A-candidate").json()
    assert history["record_count"] == 1
    assert history["records"][0]["verdict"] == "needs_more_evidence"

    # 4) Cohort summary still serves the case and reflects the verdict.
    summary = client.get("/api/v1/cohort-executive-summary").json()
    row = next(c for c in summary["cases"] if c["case_id"] == "GS-A-candidate")
    assert row["latest_signoff_verdict"] == "needs_more_evidence"

    # 5) Tier 1 disclaimer trio still on every body.
    for body in (prov_body, posted.json(), history, summary):
        text = json.dumps(body).lower()
        assert "tier 1 engineering candidate" in text
        assert "not signed validation" in text
        assert "not benchmark agreement" in text
