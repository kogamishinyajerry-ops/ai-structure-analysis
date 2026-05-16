"""FM-04a Phase 8 C — trust score provenance tests.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from app.api.routes import trust_score_provenance as route_module
from app.main import app
from app.services.reporting._schema_versions import (
    TRUST_SCORE_FORMULA_VERSION,
    TRUST_SCORE_PROVENANCE_SCHEMA_VERSION,
)
from app.services.reporting.cohort_snapshot import (
    SnapshotCaseInput,
    write_cohort_snapshot,
)
from app.services.reporting.trust_score_provenance import (
    PROVENANCE_INPUT_KINDS,
    ProvenanceSnapshotNotFound,
    build_trust_score_provenance,
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
    monkeypatch.setattr(route_module, "_repo_root", lambda: tmp_path)
    return tmp_path


def _seed_case_evidence(case_id: str, root: Path) -> SnapshotCaseInput:
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
            "residual_velocity_m_per_s": 75.0,
        },
        "energy_audit": {
            "status": "closed_aggregate",
            "energy_balance_error_pct": 8.0,
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
        "combined_verdict": "candidate_observed_stable",
        "mesh_sweep": {"runs": [], "candidate_stability": "candidate_observed_stable"},
        "dt_sweep": {"runs": [], "candidate_stability": "candidate_observed_stable"},
        "claim_boundary": metrics_payload["claim_boundary"],
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

    generator = root / "scripts" / f"gen_{case_id.lower().replace('-', '_')}_deck.py"
    generator.parent.mkdir(parents=True, exist_ok=True)
    generator.write_bytes(b"# generator\n")

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
# Builder — happy path + SHA determinism
# ---------------------------------------------------------------------


def test_provenance_builder_stamps_schema_and_formula(tmp_path: Path) -> None:
    case = _seed_case_evidence("GS-A-candidate", tmp_path)
    write_cohort_snapshot([case], repo_root=tmp_path, snapshot_label="2026-05-16T100000Z")
    report = build_trust_score_provenance(
        "GS-A-candidate", "2026-05-16T100000Z", repo_root=tmp_path
    )
    assert report.schema_version == TRUST_SCORE_PROVENANCE_SCHEMA_VERSION
    assert report.formula_version == TRUST_SCORE_FORMULA_VERSION
    assert report.case_id == "GS-A-candidate"
    assert report.snapshot_label == "2026-05-16T100000Z"


def test_provenance_returns_sha_for_every_present_input(tmp_path: Path) -> None:
    case = _seed_case_evidence("GS-A-candidate", tmp_path)
    write_cohort_snapshot([case], repo_root=tmp_path, snapshot_label="2026-05-16T100000Z")
    report = build_trust_score_provenance(
        "GS-A-candidate", "2026-05-16T100000Z", repo_root=tmp_path
    )
    inputs_by_kind = {i.kind: i for i in report.inputs}
    # All 4 kinds enumerated even when some are missing
    assert tuple(inputs_by_kind.keys()) == PROVENANCE_INPUT_KINDS
    # metrics + convergence + completeness should be present (writer captures all 3)
    assert inputs_by_kind["metrics"].present is True
    assert inputs_by_kind["convergence"].present is True
    assert inputs_by_kind["completeness"].present is True
    # SHA-256 is 64 hex chars
    for kind in ("metrics", "convergence", "completeness"):
        sha = inputs_by_kind[kind].sha256
        assert sha is not None and len(sha) == 64
        assert all(c in "0123456789abcdef" for c in sha)


def test_provenance_sha_matches_underlying_bytes(tmp_path: Path) -> None:
    case = _seed_case_evidence("GS-A-candidate", tmp_path)
    write_cohort_snapshot([case], repo_root=tmp_path, snapshot_label="2026-05-16T100000Z")
    report = build_trust_score_provenance(
        "GS-A-candidate", "2026-05-16T100000Z", repo_root=tmp_path
    )
    snap_dir = tmp_path / "reports" / "snapshots" / "2026-05-16T100000Z"
    metrics_input = next(i for i in report.inputs if i.kind == "metrics")
    captured_bytes = (snap_dir / "metrics" / "GS-A-candidate.json").read_bytes()
    assert metrics_input.sha256 == hashlib.sha256(captured_bytes).hexdigest()


def test_provenance_recomputes_trust_score(tmp_path: Path) -> None:
    case = _seed_case_evidence("GS-A-candidate", tmp_path)
    write_cohort_snapshot([case], repo_root=tmp_path, snapshot_label="2026-05-16T100000Z")
    report = build_trust_score_provenance(
        "GS-A-candidate", "2026-05-16T100000Z", repo_root=tmp_path
    )
    assert report.trust_score is not None
    assert report.trust_score > 0
    axis_names = [a.axis for a in report.axes]
    assert axis_names == [
        "completeness",
        "convergence",
        "energy_audit",
        "reproducibility",
    ]


# ---------------------------------------------------------------------
# Builder — error paths
# ---------------------------------------------------------------------


def test_provenance_raises_when_snapshot_does_not_exist(tmp_path: Path) -> None:
    with pytest.raises(ProvenanceSnapshotNotFound):
        build_trust_score_provenance("GS-A-candidate", "2099-01-01T000000Z", repo_root=tmp_path)


def test_provenance_rejects_empty_case_id(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="non-empty case_id"):
        build_trust_score_provenance("", "2026-05-16T100000Z", repo_root=tmp_path)


def test_provenance_rejects_empty_snapshot_label(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="non-empty snapshot_label"):
        build_trust_score_provenance("GS-A-candidate", "", repo_root=tmp_path)


# ---------------------------------------------------------------------
# Tier 1 disclaimer trio
# ---------------------------------------------------------------------


def test_provenance_envelope_carries_tier1_disclaimer_trio(tmp_path: Path) -> None:
    case = _seed_case_evidence("GS-A-candidate", tmp_path)
    write_cohort_snapshot([case], repo_root=tmp_path, snapshot_label="2026-05-16T100000Z")
    report = build_trust_score_provenance(
        "GS-A-candidate", "2026-05-16T100000Z", repo_root=tmp_path
    )
    assert report.claim_tier == "Tier 1 engineering candidate"
    assert "not_signed_validation" in report.claim_boundary
    assert "not_benchmark_agreement" in report.claim_boundary
    assert "not signed validation" in report.claim_impact
    assert "not benchmark agreement" in report.claim_impact


# ---------------------------------------------------------------------
# HTTP endpoint
# ---------------------------------------------------------------------


def test_provenance_endpoint_returns_stamped_payload(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    case = _seed_case_evidence("GS-A-candidate", fake_repo)
    write_cohort_snapshot([case], repo_root=fake_repo, snapshot_label="2026-05-16T100000Z")
    res = client.get(
        "/api/v1/trust-score-provenance/GS-A-candidate",
        params={"snapshot": "2026-05-16T100000Z"},
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["schema_version"] == TRUST_SCORE_PROVENANCE_SCHEMA_VERSION
    assert payload["formula_version"] == TRUST_SCORE_FORMULA_VERSION
    assert payload["snapshot_label"] == "2026-05-16T100000Z"
    assert payload["case_id"] == "GS-A-candidate"
    assert isinstance(payload["inputs"], list)
    assert len(payload["inputs"]) == len(PROVENANCE_INPUT_KINDS)


def test_provenance_endpoint_returns_404_on_unknown_snapshot(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    res = client.get(
        "/api/v1/trust-score-provenance/GS-A-candidate",
        params={"snapshot": "2099-01-01T000000Z"},
    )
    assert res.status_code == 404


def test_provenance_endpoint_rejects_invalid_case_id(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    res = client.get(
        "/api/v1/trust-score-provenance/has spaces",
        params={"snapshot": "2026-05-16T100000Z"},
    )
    assert res.status_code == 400


def test_provenance_endpoint_rejects_invalid_snapshot_shape(
    client: _SyncASGIClient, fake_repo: Path
) -> None:
    res = client.get(
        "/api/v1/trust-score-provenance/GS-A-candidate",
        params={"snapshot": "not-a-label"},
    )
    assert res.status_code == 400
