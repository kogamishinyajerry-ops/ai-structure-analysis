"""FM-04a Phase 9 F — HTTP integration tests across Phase 9 A/B/D + cross-phase.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Composes the new POST signoff endpoint, the generator-extended provenance
endpoint, and the new trend-slope endpoint with the existing Phase 8 D
cohort executive summary so a reviewer using the live API touches every
new surface in a single test.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
from app.api.routes import (
    cohort_anomalies as anomalies_module,
)
from app.api.routes import (
    cohort_executive_summary as exec_module,
)
from app.api.routes import (
    cohort_trend_anomalies as trend_module,
)
from app.api.routes import (
    signoff_history as signoff_module,
)
from app.api.routes import (
    trust_score_provenance as provenance_module,
)
from app.main import app
from app.services.reporting._schema_versions import (
    COHORT_TREND_ANOMALIES_SCHEMA_VERSION,
    SIGNOFF_RECORD_SCHEMA_VERSION,
    TRUST_SCORE_PROVENANCE_SCHEMA_VERSION,
)
from app.services.reporting.cohort_snapshot import (
    SnapshotCaseInput,
    write_cohort_snapshot,
)
from app.services.reporting.cohort_trend_anomalies import (
    TREND_MIN_POINTS,
    TREND_SLOPE_WARN_MAX,
)
from app.services.reporting.trust_score_provenance import PROVENANCE_INPUT_KINDS


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
    monkeypatch.setattr(anomalies_module, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(trend_module, "_repo_root", lambda: tmp_path)
    return tmp_path


def _seed_case_with_generator(
    root: Path,
    case_id: str,
    *,
    completeness_score: int = 85,
    generator_body: bytes = b"# generator placeholder\n",
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
        json.dumps({"case_id": case_id, "claim_boundary": "tier1"}), encoding="utf-8"
    )
    generator = root / "scripts" / f"gen_{case_id.lower().replace('-', '_')}.py"
    generator.parent.mkdir(parents=True, exist_ok=True)
    generator.write_bytes(generator_body)
    return SnapshotCaseInput(
        case_id=case_id,
        starter_deck_path=starter,
        engine_deck_path=engine,
        ballistic_metrics_path=metrics,
        convergence_study_path=None,
        animation_manifest_path=None,
        result_mesh_path=None,
        generator_script_path=generator,
        notes_path=None,
    )


def _write_snapshot_with_score(
    root: Path,
    case_id: str,
    snapshot_label: str,
    completeness_score: int,
    *,
    generator_body: bytes = b"# generator placeholder\n",
) -> None:
    case = _seed_case_with_generator(
        root, case_id, completeness_score=completeness_score, generator_body=generator_body
    )
    write_cohort_snapshot([case], repo_root=root, snapshot_label=snapshot_label)
    comp_path = root / "reports" / "snapshots" / snapshot_label / "completeness" / f"{case_id}.json"
    payload = json.loads(comp_path.read_text(encoding="utf-8"))
    payload["score"] = completeness_score
    comp_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


# ---------------------------------------------------------------------
# Slice F.1 — POST signoff endpoint integration
# ---------------------------------------------------------------------


def test_post_signoff_then_get_history_chains(client: _SyncASGIClient, fake_repo: Path) -> None:
    """Reviewer workflow: POST a signoff via HTTP, GET the history via HTTP,
    confirm the record appears + envelope carries schema_version."""
    res = client.post(
        "/api/v1/signoff-history/GS-A-candidate",
        json_body={"reviewer": "alice", "verdict": "watching", "notes": "ok"},
    )
    assert res.status_code == 200
    history = client.get("/api/v1/signoff-history/GS-A-candidate").json()
    assert history["schema_version"] == SIGNOFF_RECORD_SCHEMA_VERSION
    assert history["record_count"] == 1
    assert history["records"][0]["verdict"] == "watching"


def test_post_signoff_propagates_to_cohort_executive_summary(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Reviewer workflow: POST a blocked_pending_input signoff, then GET
    cohort summary; the row must surface latest_signoff_verdict + force
    bucket to regressed (the verdict overrides whatever bucket the
    score-only path produced)."""
    _write_snapshot_with_score(fake_repo, "GS-A-candidate", "2026-05-16T100000Z", 90)
    summary_before = client.get("/api/v1/cohort-executive-summary").json()
    row_before = next(c for c in summary_before["cases"] if c["case_id"] == "GS-A-candidate")
    # The starting bucket depends on the full trust score (completeness +
    # convergence + energy + reproducibility weighted sum). We don't
    # pin it precisely here — we only assert no signoff is recorded yet.
    assert row_before["latest_signoff_verdict"] is None

    res = client.post(
        "/api/v1/signoff-history/GS-A-candidate",
        json_body={
            "reviewer": "alice",
            "verdict": "blocked_pending_input",
            "notes": "material card pending",
        },
    )
    assert res.status_code == 200

    summary_after = client.get("/api/v1/cohort-executive-summary").json()
    row_after = next(c for c in summary_after["cases"] if c["case_id"] == "GS-A-candidate")
    assert row_after["latest_signoff_verdict"] == "blocked_pending_input"
    # blocked_pending_input is rule #1 in the precedence ladder; it
    # forces regressed regardless of the prior bucket.
    assert row_after["bucket"] == "regressed"


def test_post_signoff_refuses_signed_registry_at_http_422(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Defense in depth at the HTTP boundary — signed-registry case_id
    refused by route before any service-layer call."""
    res = client.post(
        "/api/v1/signoff-history/GS-001",
        json_body={"reviewer": "alice", "verdict": "watching", "notes": "ok"},
    )
    assert res.status_code == 422


def test_post_signoff_refuses_tier2_promotion_verb_at_http_422(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Phase 9 anti-gaming guard C: -10 enforced via HTTP."""
    res = client.post(
        "/api/v1/signoff-history/GS-A-candidate",
        json_body={
            "reviewer": "alice",
            "verdict": "ready_for_tier_2",
            "notes": "ok",
        },
    )
    assert res.status_code == 422


# ---------------------------------------------------------------------
# Slice F.2 — generator-extended provenance
# ---------------------------------------------------------------------


def test_provenance_endpoint_carries_generator_input(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Phase 9 B closure pinned at the HTTP boundary: provenance trace
    returns 5 input rows including generator, with SHA over captured bytes."""
    body = b"# slice 9-F generator probe\n"
    _write_snapshot_with_score(
        fake_repo,
        "GS-A-candidate",
        "2026-05-16T100000Z",
        90,
        generator_body=body,
    )
    res = client.get(
        "/api/v1/trust-score-provenance/GS-A-candidate",
        params={"snapshot": "2026-05-16T100000Z"},
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["schema_version"] == TRUST_SCORE_PROVENANCE_SCHEMA_VERSION
    assert payload["schema_version"] == "1.2.0"
    assert len(payload["inputs"]) == len(PROVENANCE_INPUT_KINDS)
    gen_row = next(i for i in payload["inputs"] if i["kind"] == "generator")
    assert gen_row["present"] is True
    assert gen_row["path"] == "generator/GS-A-candidate.py"
    assert gen_row["sha256"] == hashlib.sha256(body).hexdigest()


def test_provenance_endpoint_handles_missing_generator(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """A snapshot without a generator yields present=False for that row."""
    case = SnapshotCaseInput(
        case_id="GS-A-candidate",
        starter_deck_path=fake_repo / "x.rad",
        engine_deck_path=fake_repo / "y.rad",
        ballistic_metrics_path=None,
        convergence_study_path=None,
        animation_manifest_path=None,
        result_mesh_path=None,
        generator_script_path=None,
        notes_path=None,
    )
    (fake_repo / "x.rad").write_text("# s", encoding="utf-8")
    (fake_repo / "y.rad").write_text("# e", encoding="utf-8")
    write_cohort_snapshot([case], repo_root=fake_repo, snapshot_label="2026-05-16T100000Z")
    res = client.get(
        "/api/v1/trust-score-provenance/GS-A-candidate",
        params={"snapshot": "2026-05-16T100000Z"},
    )
    payload = res.json()
    gen_row = next(i for i in payload["inputs"] if i["kind"] == "generator")
    assert gen_row["present"] is False
    assert gen_row["sha256"] is None


# ---------------------------------------------------------------------
# Slice F.3 — trend anomaly endpoint
# ---------------------------------------------------------------------


def test_trend_endpoint_empty_cohort_returns_stamped_payload(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    res = client.get("/api/v1/cohort-trend-anomalies")
    assert res.status_code == 200
    payload = res.json()
    assert payload["schema_version"] == COHORT_TREND_ANOMALIES_SCHEMA_VERSION
    assert payload["cohort_count"] == 0
    assert payload["anomaly_count"] == 0
    assert payload["point_count_floor"] == TREND_MIN_POINTS


def test_trend_endpoint_carries_tier1_disclaimer_trio(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    res = client.get("/api/v1/cohort-trend-anomalies")
    body = res.text.lower()
    assert "tier 1 engineering candidate" in body
    assert "not signed validation" in body
    assert "not benchmark agreement" in body


def test_trend_endpoint_warn_boundary_pinned(client: _SyncASGIClient, fake_repo: Path) -> None:
    """Engineered case engineered to fire on the completeness axis.

    Five snapshots [90, 80, 70, 60, 50] -> slope = -10 on the raw
    completeness scores, which scales by 50/100 (the completeness
    axis weight) -> roughly slope == -5.0 in weighted units. The
    completeness axis weight is COMPLETENESS_WEIGHT = 50.
    A slope around -5 lands in danger (<=-3.0)."""
    for i, score in enumerate([90, 80, 70, 60, 50]):
        label = f"2026-05-{16 + i:02d}T100000Z"
        _write_snapshot_with_score(fake_repo, "GS-A-candidate", label, score)

    res = client.get("/api/v1/cohort-trend-anomalies")
    payload = res.json()
    assert payload["cohort_count"] == 1
    assert payload["anomaly_count"] >= 1
    completeness_events = [a for a in payload["anomalies"] if a["axis"] == "completeness"]
    assert len(completeness_events) == 1
    assert completeness_events[0]["case_id"] == "GS-A-candidate"
    assert completeness_events[0]["slope"] < TREND_SLOPE_WARN_MAX


# ---------------------------------------------------------------------
# Slice F.4 — orthogonality between trend and z-score
# ---------------------------------------------------------------------


def test_descending_single_case_fires_trend_but_not_zscore(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """A single case with a descending timeline: the trend endpoint
    must fire (slope is negative), but the z-score endpoint must NOT
    fire (cohort size 1 -> below COHORT_MIN_SIZE_FOR_ANOMALY = 3).

    This pins the orthogonality between Phase 9 D and Phase 8 E.
    """
    for i, score in enumerate([90, 80, 70, 60, 50]):
        label = f"2026-05-{16 + i:02d}T100000Z"
        _write_snapshot_with_score(fake_repo, "GS-A-candidate", label, score)

    trend = client.get("/api/v1/cohort-trend-anomalies").json()
    zscore = client.get("/api/v1/cohort-anomalies").json()

    assert trend["anomaly_count"] >= 1, "trend must fire on descending timeline"
    assert zscore["anomaly_count"] == 0, "z-score must NOT fire (cohort size 1 is below floor)"


# ---------------------------------------------------------------------
# Slice F.5 — cross-phase chained reads
# ---------------------------------------------------------------------


def test_chained_summary_trend_anomalies_provenance(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """Chain reads across summary + trend + anomalies + provenance for
    a single case. Smoke-pins that all four surfaces return 200 against
    the same on-disk state."""
    for i, score in enumerate([90, 80, 70]):
        label = f"2026-05-{16 + i:02d}T100000Z"
        _write_snapshot_with_score(fake_repo, "GS-A-candidate", label, score)

    assert client.get("/api/v1/cohort-executive-summary").status_code == 200
    assert client.get("/api/v1/cohort-anomalies").status_code == 200
    assert client.get("/api/v1/cohort-trend-anomalies").status_code == 200
    assert (
        client.get(
            "/api/v1/trust-score-provenance/GS-A-candidate",
            params={"snapshot": "2026-05-16T100000Z"},
        ).status_code
        == 200
    )


def test_summary_envelope_unchanged_after_phase9(client: _SyncASGIClient, fake_repo: Path) -> None:
    """Phase 9 must NOT have silently broken the Phase 8 D envelope."""
    _write_snapshot_with_score(fake_repo, "GS-A-candidate", "2026-05-16T100000Z", 85)
    res = client.get("/api/v1/cohort-executive-summary")
    payload = res.json()
    assert "schema_version" in payload
    assert "cohort_count" in payload
    assert "healthy_count" in payload
    assert "watching_count" in payload
    assert "regressed_count" in payload
    assert "cases" in payload


# ---------------------------------------------------------------------
# Slice F.6 — POST endpoint validation pins
# ---------------------------------------------------------------------


def test_post_signoff_each_supported_verdict_succeeds(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    """4 verdicts × 4 cases — each must roundtrip with 200."""
    verdicts = [
        "watching",
        "needs_more_evidence",
        "needs_more_convergence",
        "blocked_pending_input",
    ]
    for verdict in verdicts:
        case_id = f"GS-VERDICT-{verdict.replace('_', '-').upper()}-candidate"
        res = client.post(
            f"/api/v1/signoff-history/{case_id}",
            json_body={"reviewer": "alice", "verdict": verdict, "notes": "ok"},
        )
        assert res.status_code == 200, f"verdict {verdict} should succeed; body={res.text}"


def test_post_signoff_refuses_forbidden_claim_in_notes(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    res = client.post(
        "/api/v1/signoff-history/GS-A-candidate",
        json_body={
            "reviewer": "alice",
            "verdict": "watching",
            "notes": "this case is validated against ASTM E8",
        },
    )
    assert res.status_code == 422
    assert "forbidden positive claim" in res.json()["detail"]


def test_post_signoff_accepts_disclaimer_form_notes_via_http(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    res = client.post(
        "/api/v1/signoff-history/GS-A-candidate",
        json_body={
            "reviewer": "alice",
            "verdict": "watching",
            "notes": "Tier 1 only; not signed validation; not benchmark agreement.",
        },
    )
    assert res.status_code == 200


# ---------------------------------------------------------------------
# Generated UTC stamp format pin (cross-cutting guard M: -3)
# ---------------------------------------------------------------------


def test_trend_endpoint_generated_at_is_utc_iso(client: _SyncASGIClient, fake_repo: Path) -> None:
    res = client.get("/api/v1/cohort-trend-anomalies")
    payload = res.json()
    stamp = payload["generated_at_utc"]
    # Must parse cleanly as ISO 8601; presence of '+00:00' OR a Z suffix
    # confirms UTC anchoring (the service uses isoformat(timespec='seconds')).
    parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None
    assert parsed.tzinfo.utcoffset(parsed) == UTC.utcoffset(parsed)
