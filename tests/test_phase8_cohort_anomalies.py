"""FM-04a Phase 8 E — cohort anomaly detection tests.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
from app.api.routes import cohort_anomalies as route_module
from app.main import app
from app.services.reporting._schema_versions import (
    COHORT_ANOMALIES_SCHEMA_VERSION,
)
from app.services.reporting.cohort_anomalies import (
    ANOMALY_AXES,
    ANOMALY_SIGMA_DANGER_MIN,
    ANOMALY_SIGMA_INFO_MIN,
    ANOMALY_SIGMA_WARN_MIN,
    COHORT_MIN_SIZE_FOR_ANOMALY,
    build_cohort_anomalies,
    severity_for,
)
from app.services.reporting.cohort_snapshot import (
    SnapshotCaseInput,
    write_cohort_snapshot,
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


def _seed_case_with_completeness(
    root: Path, case_id: str, completeness_score: int, snapshot_label: str
) -> None:
    """Seed a candidate case with a snapshot whose completeness/<case>.json
    has the given score (out of 100). Other axes will be 0 since we
    don't seed convergence/metrics/reproducibility for these tests."""
    case_dir = root / "golden_samples" / case_id / "data"
    case_dir.mkdir(parents=True, exist_ok=True)
    starter = case_dir / "model_00_0000.rad"
    engine = case_dir / "model_00_0001.rad"
    starter.write_text("# s", encoding="utf-8")
    engine.write_text("# e", encoding="utf-8")
    metrics_path = (
        root / "project_state" / "graph_executor" / case_id / "ballistic" / "ballistic_metrics.json"
    )
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(
        json.dumps({"case_id": case_id, "claim_boundary": "tier1"}),
        encoding="utf-8",
    )
    generator = root / "scripts" / f"gen_{case_id.lower().replace('-', '_')}.py"
    generator.parent.mkdir(parents=True, exist_ok=True)
    generator.write_bytes(b"# g")
    case_input = SnapshotCaseInput(
        case_id=case_id,
        starter_deck_path=starter,
        engine_deck_path=engine,
        ballistic_metrics_path=metrics_path,
        convergence_study_path=None,
        animation_manifest_path=None,
        result_mesh_path=None,
        generator_script_path=generator,
        notes_path=None,
    )
    write_cohort_snapshot([case_input], repo_root=root, snapshot_label=snapshot_label)

    # Override the captured completeness score
    comp_path = root / "reports" / "snapshots" / snapshot_label / "completeness" / f"{case_id}.json"
    payload = json.loads(comp_path.read_text(encoding="utf-8"))
    payload["score"] = completeness_score
    comp_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


# ---------------------------------------------------------------------
# severity_for boundary pins (Phase 8 guard T: -2 per bucket)
# ---------------------------------------------------------------------


def test_severity_for_info_at_lower_bound() -> None:
    assert severity_for(ANOMALY_SIGMA_INFO_MIN) == "info"
    assert severity_for(-ANOMALY_SIGMA_INFO_MIN) == "info"


def test_severity_for_warn_at_lower_bound() -> None:
    assert severity_for(ANOMALY_SIGMA_WARN_MIN) == "warn"
    assert severity_for(-ANOMALY_SIGMA_WARN_MIN) == "warn"


def test_severity_for_danger_at_lower_bound() -> None:
    assert severity_for(ANOMALY_SIGMA_DANGER_MIN) == "danger"
    assert severity_for(-ANOMALY_SIGMA_DANGER_MIN) == "danger"


def test_severity_for_below_info_returns_info_default() -> None:
    """|z| < 2 still routes to info bucket since severity_for is only
    called *after* the abs(z) >= ANOMALY_SIGMA_INFO_MIN gate in the
    builder; standalone calls below the floor map to info (the
    most-conservative bucket if anyone bypasses the gate)."""
    assert severity_for(0.0) == "info"
    assert severity_for(1.9) == "info"


# ---------------------------------------------------------------------
# Cohort-size edge cases (Phase 8 guard T: -2)
# ---------------------------------------------------------------------


def test_cohort_size_one_returns_empty(tmp_path: Path) -> None:
    _seed_case_with_completeness(tmp_path, "GS-A-candidate", 90, "2026-05-16T100000Z")
    report = build_cohort_anomalies(repo_root=tmp_path)
    assert report.cohort_count == 1
    assert report.anomaly_count == 0


def test_cohort_size_two_returns_empty(tmp_path: Path) -> None:
    _seed_case_with_completeness(tmp_path, "GS-A-candidate", 90, "2026-05-16T100000Z")
    _seed_case_with_completeness(tmp_path, "GS-B-candidate", 70, "2026-05-16T100000Z")
    report = build_cohort_anomalies(repo_root=tmp_path)
    assert report.cohort_count == 2
    assert report.anomaly_count == 0


def test_cohort_min_size_constant_is_named() -> None:
    """Phase 8 anti-gaming guard M: -3 — cohort size floor is named."""
    assert COHORT_MIN_SIZE_FOR_ANOMALY == 3


# ---------------------------------------------------------------------
# Anomaly detection — engineered outlier
# ---------------------------------------------------------------------


def test_anomaly_detected_when_one_case_is_outlier(tmp_path: Path) -> None:
    """Seed 6 cases tightly clustered at score ~85 and 1 extreme outlier
    at score=10. The outlier should fire an anomaly on the completeness
    axis with |z| comfortably above the 2σ threshold."""
    for cid, score in (
        ("GS-A-candidate", 85),
        ("GS-B-candidate", 86),
        ("GS-C-candidate", 87),
        ("GS-D-candidate", 86),
        ("GS-E-candidate", 85),
        ("GS-F-candidate", 86),
        ("GS-Z-candidate", 10),  # extreme outlier
    ):
        _seed_case_with_completeness(tmp_path, cid, score, "2026-05-16T100000Z")
    report = build_cohort_anomalies(repo_root=tmp_path)
    completeness_anomalies = [a for a in report.anomalies if a.axis == "completeness"]
    assert any(a.case_id == "GS-Z-candidate" for a in completeness_anomalies)
    outlier = next(a for a in completeness_anomalies if a.case_id == "GS-Z-candidate")
    assert abs(outlier.z_score) >= ANOMALY_SIGMA_INFO_MIN


def test_uniform_cohort_has_zero_anomalies(tmp_path: Path) -> None:
    """All cases at the same score => stdev=0 => no anomalies."""
    for cid in ("GS-A-candidate", "GS-B-candidate", "GS-C-candidate"):
        _seed_case_with_completeness(tmp_path, cid, 85, "2026-05-16T100000Z")
    report = build_cohort_anomalies(repo_root=tmp_path)
    assert report.cohort_count == 3
    assert report.anomaly_count == 0


# ---------------------------------------------------------------------
# Envelope / schema
# ---------------------------------------------------------------------


def test_anomaly_envelope_stamps_schema_and_disclaimer(tmp_path: Path) -> None:
    report = build_cohort_anomalies(
        repo_root=tmp_path, now_utc=datetime(2026, 5, 16, 0, 0, 0, tzinfo=UTC)
    )
    assert report.schema_version == COHORT_ANOMALIES_SCHEMA_VERSION
    assert report.claim_tier == "Tier 1 engineering candidate"
    assert "not_signed_validation" in report.claim_boundary
    assert "not_benchmark_agreement" in report.claim_boundary
    assert "not signed validation" in report.claim_impact
    assert "not benchmark agreement" in report.claim_impact
    assert "do NOT diagnose root cause" in report.claim_impact


def test_anomaly_axes_constant_covers_four_trust_score_axes() -> None:
    assert ANOMALY_AXES == (
        "completeness",
        "convergence",
        "energy_audit",
        "reproducibility",
    )


# ---------------------------------------------------------------------
# HTTP endpoint
# ---------------------------------------------------------------------


def test_endpoint_returns_stamped_payload(client: _SyncASGIClient, fake_repo: Path) -> None:
    res = client.get("/api/v1/cohort-anomalies")
    assert res.status_code == 200
    payload = res.json()
    assert payload["schema_version"] == COHORT_ANOMALIES_SCHEMA_VERSION
    assert payload["cohort_count"] == 0
    assert payload["anomaly_count"] == 0
    assert isinstance(payload["anomalies"], list)


def test_endpoint_envelope_carries_disclaimer_trio(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    res = client.get("/api/v1/cohort-anomalies")
    payload = res.json()
    assert "Tier 1 engineering candidate" in payload["claim_tier"]
    assert "not signed validation" in payload["claim_impact"]
    assert "not benchmark agreement" in payload["claim_impact"]
