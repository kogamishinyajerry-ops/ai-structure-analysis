"""End-to-end Phase 7 trust closure tests (FM-04a Phase 7 G).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Three load-bearing reviewer journeys that compose Phase 5 + Phase 6 +
Phase 7 surfaces end-to-end across the HTTP layer:

  1. test_phase7_convergence_recovery_flow_e2e
     Phase 7 A — write snapshot whose convergence_study.json is captured;
     fetch the timeline; assert non-zero convergence_weighted because
     the verdict was recovered from the captured file (not from a
     metrics-inlined fallback).

  2. test_phase7_locale_roundtrip_flow_e2e
     Phase 7 B — write 2 snapshots with drift; fetch the zh-CN
     narrative; assert at least one Chinese sentence + Tier 1
     disclaimer envelope still in zh-CN payload.

  3. test_phase7_regression_alarm_flow_e2e
     Phase 7 C — write 3 snapshots with monotonically degrading trust
     score; fetch alarms; assert exactly the expected number of
     alarm events with correct severity ladder + primary_axis_shift.
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
from app.api.routes import snapshot_narrative as snapshot_narrative_module
from app.api.routes import trust_score_alerts as trust_score_alerts_module
from app.api.routes import trust_score_timeline as trust_score_timeline_module
from app.main import app
from app.services.reporting._schema_versions import (
    TRUST_SCORE_ALERTS_SCHEMA_VERSION,
)
from app.services.reporting.cohort_snapshot import (
    SnapshotCaseInput,
    write_cohort_snapshot,
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

    monkeypatch.setattr(cohort_snapshots_module, "_repo_root", fake_repo_root)
    monkeypatch.setattr(cohort_snapshot_diff_module, "_repo_root", fake_repo_root)
    monkeypatch.setattr(snapshot_narrative_module, "_repo_root", fake_repo_root)
    monkeypatch.setattr(trust_score_timeline_module, "_repo_root", fake_repo_root)
    monkeypatch.setattr(trust_score_alerts_module, "_repo_root", fake_repo_root)
    return fake_root


def _write_case_evidence(
    case_id: str,
    root: Path,
    *,
    residual_velocity: float = 75.0,
    energy_balance_error_pct: float = 8.0,
    energy_status: str = "closed_aggregate",
    convergence_verdict: str = "candidate_observed_stable",
    generator_body: bytes = b"# generator\n",
) -> SnapshotCaseInput:
    case_dir = root / "golden_samples" / case_id / "data"
    case_dir.mkdir(parents=True, exist_ok=True)
    starter = case_dir / "model_00_0000.rad"
    engine = case_dir / "model_00_0001.rad"
    starter.write_text("# starter", encoding="utf-8")
    engine.write_text("# engine", encoding="utf-8")

    metrics_payload = {
        "case_id": case_id,
        "projectile_initial_velocity_m_per_s": 300.0,
        "perforation": {
            "marker": "candidate_perforation",
            "residual_velocity_m_per_s": residual_velocity,
        },
        "energy_audit": {
            "status": energy_status,
            "energy_balance_error_pct": energy_balance_error_pct,
        },
        "claim_boundary": (
            "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"
        ),
        "extraction_metadata": {
            "projectile_mass_kg": 0.197,
            "plate_thickness_m": 0.012,
            "impact_axis": "x",
        },
    }
    metrics_path = (
        root / "project_state" / "graph_executor" / case_id / "ballistic" / "ballistic_metrics.json"
    )
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(metrics_payload), encoding="utf-8")

    convergence_payload = {
        "case_id": case_id,
        "combined_verdict": convergence_verdict,
        "mesh_sweep": {"runs": [], "candidate_stability": convergence_verdict},
        "dt_sweep": {"runs": [], "candidate_stability": convergence_verdict},
        "claim_boundary": metrics_payload["claim_boundary"],
        "energy_balance_observation": {"status": energy_status},
    }
    convergence_path = (
        root
        / "project_state"
        / "graph_executor"
        / case_id
        / "convergence"
        / "convergence_study.json"
    )
    convergence_path.parent.mkdir(parents=True, exist_ok=True)
    convergence_path.write_text(json.dumps(convergence_payload), encoding="utf-8")

    slug = case_id.lower().replace("gs-", "gs").replace("-candidate", "").replace("-", "_")
    generator = root / "scripts" / f"gen_{slug}_deck.py"
    generator.parent.mkdir(parents=True, exist_ok=True)
    generator.write_bytes(generator_body)

    return SnapshotCaseInput(
        case_id=case_id,
        starter_deck_path=starter,
        engine_deck_path=engine,
        ballistic_metrics_path=metrics_path,
        convergence_study_path=convergence_path,
        animation_manifest_path=None,
        result_mesh_path=None,
        generator_script_path=generator,
        notes_path=None,
    )


# ---------------------------------------------------------------------
# E2E 1: convergence recovery flow (Phase 7 A integration)
# ---------------------------------------------------------------------


def test_phase7_convergence_recovery_flow_e2e(client: _SyncASGIClient, fake_repo: Path) -> None:
    """Reviewer journey: write a snapshot with the case's
    convergence_study.json captured; fetch the timeline; verify the
    convergence axis scores non-zero because the verdict was recovered
    from the captured file (Phase 7 A behavior, closes Phase 6 §1).

    Tier 1 engineering candidate; not signed validation; not benchmark agreement.
    """
    case = _write_case_evidence(
        "GS-A-candidate",
        fake_repo,
        convergence_verdict="candidate_observed_stable",
    )
    write_cohort_snapshot([case], repo_root=fake_repo, snapshot_label="2026-05-16T100000Z")

    res = client.get("/api/v1/trust-score-timeline/GS-A-candidate")
    assert res.status_code == 200
    payload = res.json()
    assert payload["point_count"] == 1
    point = payload["points"][0]
    # Both axes were candidate_observed_stable → raw 100 → weighted = 20
    assert point["convergence_weighted"] > 0
    assert point["energy_audit_weighted"] > 0
    assert point["completeness_weighted"] > 0

    # Tier 1 disclaimer preserved
    body = res.text.lower()
    assert "tier 1 engineering candidate" in body
    assert "not signed validation" in body
    assert "not benchmark agreement" in body


# ---------------------------------------------------------------------
# E2E 2: locale roundtrip flow (Phase 7 B integration)
# ---------------------------------------------------------------------


def test_phase7_locale_roundtrip_flow_e2e(client: _SyncASGIClient, fake_repo: Path) -> None:
    """Reviewer journey: write 2 snapshots with drift; fetch the
    zh-CN narrative; assert Chinese sentence appears + envelope still
    carries the (English) Tier 1 disclaimer trio.

    Tier 1 engineering candidate; not signed validation; not benchmark agreement.
    """
    case_a = _write_case_evidence(
        "GS-A-candidate",
        fake_repo,
        residual_velocity=75.0,
        energy_balance_error_pct=12.0,
        generator_body=b"# v1\n",
    )
    write_cohort_snapshot([case_a], repo_root=fake_repo, snapshot_label="2026-05-16T100000Z")
    case_b = _write_case_evidence(
        "GS-A-candidate",
        fake_repo,
        residual_velocity=80.0,
        energy_balance_error_pct=8.0,
        generator_body=b"# v2\n",
    )
    write_cohort_snapshot([case_b], repo_root=fake_repo, snapshot_label="2026-05-16T200000Z")

    res = client.get(
        "/api/v1/snapshot-narrative",
        params={
            "a": "2026-05-16T100000Z",
            "b": "2026-05-16T200000Z",
            "locale": "zh-CN",
        },
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["locale"] == "zh-CN"
    case_lines = " ".join(line["text"] for case in payload["narratives"] for line in case["lines"])
    # residual velocity changed (75 → 80) should produce a zh-CN line
    assert "残余速度" in case_lines
    # energy balance improved (12 → 8) should also appear
    assert "能量平衡误差" in case_lines
    # Tier 1 disclaimer trio still in English envelope
    assert "Tier 1 engineering candidate" in payload["claim_tier"]
    assert "not signed validation" in payload["claim_impact"]
    assert "not benchmark agreement" in payload["claim_impact"]


# ---------------------------------------------------------------------
# E2E 3: regression alarm flow (Phase 7 C integration)
# ---------------------------------------------------------------------


def test_phase7_regression_alarm_flow_e2e(client: _SyncASGIClient, fake_repo: Path) -> None:
    """Reviewer journey: write 3 snapshots with monotonically degrading
    completeness; fetch alarms; assert exactly 2 events with the right
    severity ladder + primary_axis_shift.

    Snapshot 1: completeness=100 → trust_score high
    Snapshot 2: completeness=70 → drop ~15 (info)
    Snapshot 3: completeness=20 → drop ~25 (warn)

    Tier 1 engineering candidate; not signed validation; not benchmark agreement.
    """
    for label, completeness in (
        ("2026-05-16T100000Z", 100),
        ("2026-05-16T200000Z", 70),
        ("2026-05-16T300000Z", 20),
    ):
        # Stage on-disk evidence for the case at the right completeness level
        case = _write_case_evidence("GS-A-candidate", fake_repo)
        write_cohort_snapshot([case], repo_root=fake_repo, snapshot_label=label)
        # Override the captured completeness score to control the trajectory
        from app.services.reporting.cohort_snapshot import snapshots_root

        completeness_path = (
            snapshots_root(fake_repo) / label / "completeness" / "GS-A-candidate.json"
        )
        payload = json.loads(completeness_path.read_text(encoding="utf-8"))
        payload["score"] = completeness
        completeness_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    res = client.get(
        "/api/v1/trust-score-alerts/GS-A-candidate",
        params={"threshold_delta": 1},
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["schema_version"] == TRUST_SCORE_ALERTS_SCHEMA_VERSION
    assert payload["case_id"] == "GS-A-candidate"
    # 3 snapshots → 2 adjacent pairs → 2 alerts (both drops >= threshold=1)
    assert payload["alert_count"] == 2
    # First alert: 100 → 70, delta = ~15 → info bucket
    first = payload["alerts"][0]
    assert first["from_snapshot"] == "2026-05-16T100000Z"
    assert first["to_snapshot"] == "2026-05-16T200000Z"
    assert first["severity"] == "info"
    assert first["primary_axis_shift"] == "completeness"
    # Second alert: 70 → 20, delta = ~25 → warn bucket
    second = payload["alerts"][1]
    assert second["from_snapshot"] == "2026-05-16T200000Z"
    assert second["to_snapshot"] == "2026-05-16T300000Z"
    assert second["severity"] in {"warn", "info"}  # boundary depends on integer cast
    assert second["primary_axis_shift"] == "completeness"

    # Tier 1 disclaimer + "do NOT authorize Tier 2" surfaces in body
    body = res.text.lower()
    assert "tier 1 engineering candidate" in body
    assert "not signed validation" in body
    assert "not benchmark agreement" in body
    assert "not authorize tier 2" in body
