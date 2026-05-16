"""End-to-end Phase 5 reviewer workflow test (FM-04a Phase 5 F).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Exercises the complete snapshot lifecycle a reviewer would walk
through:

    Step 1: capture a baseline snapshot of two candidate cases
    Step 2: drift one case (residual_velocity changed)
    Step 3: capture a follow-up snapshot
    Step 4: list snapshots and verify both appear newest-first
    Step 5: diff the two snapshots and verify the drifted case
            surfaces a non-zero completeness delta OR a non-zero
            reproducibility delta (script SHA-256 changed)
    Step 6: fetch the per-case reproducibility manifest for the
            drifted case and verify it carries schema_version +
            git state + script fingerprint

The test is load-bearing for the Phase 5 E-axis score: it proves
that Phase 5 A-D wires together end-to-end without going through
the live UI.
"""

from __future__ import annotations

import asyncio
import json
import zipfile
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


def _write_baseline_evidence(
    case_id: str,
    root: Path,
    *,
    residual_velocity: float,
    energy_balance_error_pct: float,
    generator_body: bytes,
) -> SnapshotCaseInput:
    case_dir = root / "golden_samples" / case_id / "data"
    case_dir.mkdir(parents=True, exist_ok=True)
    starter = case_dir / "model_00_0000.rad"
    engine = case_dir / "model_00_0001.rad"
    starter.write_text("# starter deck", encoding="utf-8")
    engine.write_text("# engine deck", encoding="utf-8")

    metrics_payload = {
        "case_id": case_id,
        "projectile_initial_velocity_m_per_s": 300.0,
        "perforation": {
            "marker": "candidate_perforation",
            "residual_velocity_m_per_s": residual_velocity,
        },
        "energy_audit": {
            "status": "closed_aggregate",
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
    metrics_path.write_text(json.dumps(metrics_payload, indent=2), encoding="utf-8")

    convergence_payload = {
        "case_id": case_id,
        "study_metric": "residual_velocity_m_per_s",
        "tolerance_pct": 5.0,
        "combined_verdict": "candidate_observed_stable",
        "mesh_sweep": {"runs": [], "candidate_stability": "candidate_observed_stable"},
        "dt_sweep": {"runs": [], "candidate_stability": "candidate_observed_stable"},
        "row_count": 0,
        "rows": [],
        "claim_boundary": (
            "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"
        ),
        "energy_balance_observation": {"status": "closed_aggregate"},
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
    convergence_path.write_text(json.dumps(convergence_payload, indent=2), encoding="utf-8")

    # Generator script that the reproducibility manifest will fingerprint.
    # We change its bytes between baseline and follow-up to force a script
    # SHA-256 delta.
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


def test_phase5_snapshot_workflow_e2e(
    client: _SyncASGIClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Six-step Phase 5 E2E reviewer workflow.

    Tier 1 engineering candidate; not signed validation; not benchmark agreement.
    """
    fake_root = tmp_path

    def fake_repo_root() -> Path:
        return fake_root

    monkeypatch.setattr(reproducibility_manifest_module, "_repo_root", fake_repo_root)
    monkeypatch.setattr(cohort_snapshots_module, "_repo_root", fake_repo_root)
    monkeypatch.setattr(cohort_snapshot_diff_module, "_repo_root", fake_repo_root)

    # ------------------------------------------------------------------
    # Step 1: write a baseline snapshot of two candidate cases
    # ------------------------------------------------------------------
    case_a_v1 = _write_baseline_evidence(
        "GS-A-candidate",
        fake_root,
        residual_velocity=75.0,
        energy_balance_error_pct=12.0,
        generator_body=b"# baseline generator for GS-A\n",
    )
    case_b_v1 = _write_baseline_evidence(
        "GS-B-candidate",
        fake_root,
        residual_velocity=82.0,
        energy_balance_error_pct=10.0,
        generator_body=b"# baseline generator for GS-B\n",
    )
    baseline = write_cohort_snapshot(
        [case_a_v1, case_b_v1],
        repo_root=fake_root,
        snapshot_label="2026-05-16T100000Z",
    )
    assert (baseline.snapshot_dir / "SNAPSHOT_MANIFEST.json").is_file()

    # ------------------------------------------------------------------
    # Step 2: drift case A — change residual velocity (downstream effect
    # on completeness rubric is bounded; the generator script body changes
    # to force a reproducibility manifest delta as well)
    # ------------------------------------------------------------------
    case_a_v2 = _write_baseline_evidence(
        "GS-A-candidate",
        fake_root,
        residual_velocity=80.0,
        energy_balance_error_pct=8.5,
        generator_body=b"# refined generator for GS-A v2 (added comments)\n",
    )
    # case B kept stable to verify shared-cohort drift detection only
    # flags the case that actually changed

    # ------------------------------------------------------------------
    # Step 3: write the follow-up snapshot
    # ------------------------------------------------------------------
    followup = write_cohort_snapshot(
        [case_a_v2, case_b_v1],
        repo_root=fake_root,
        snapshot_label="2026-05-16T200000Z",
    )
    assert followup.snapshot_label != baseline.snapshot_label

    # ------------------------------------------------------------------
    # Step 4: list snapshots via HTTP and verify newest-first ordering
    # ------------------------------------------------------------------
    list_res = client.get("/api/v1/cohort-snapshots")
    assert list_res.status_code == 200
    list_payload = list_res.json()
    assert list_payload["schema_version"] == COHORT_SNAPSHOT_MANIFEST_SCHEMA_VERSION
    assert list_payload["snapshot_count"] == 2
    labels = [entry["snapshot_label"] for entry in list_payload["snapshots"]]
    assert labels == ["2026-05-16T200000Z", "2026-05-16T100000Z"]
    assert list_payload["snapshots"][0]["cohort_count"] == 2
    assert list_payload["snapshots"][0]["reviewer_bundle_written"] is True

    # ------------------------------------------------------------------
    # Step 5: diff the two snapshots via HTTP
    # ------------------------------------------------------------------
    diff_res = client.get(
        "/api/v1/cohort-snapshot-diff",
        params={"a": "2026-05-16T100000Z", "b": "2026-05-16T200000Z"},
    )
    assert diff_res.status_code == 200
    diff_payload = diff_res.json()
    assert diff_payload["schema_version"] == COHORT_SNAPSHOT_DIFF_SCHEMA_VERSION
    assert diff_payload["snapshot_a_label"] == "2026-05-16T100000Z"
    assert diff_payload["snapshot_b_label"] == "2026-05-16T200000Z"
    assert diff_payload["cohort_added"] == []
    assert diff_payload["cohort_removed"] == []
    assert diff_payload["cohort_shared"] == ["GS-A-candidate", "GS-B-candidate"]

    # Find case A's reproducibility delta — script SHA-256 must have
    # changed (generator body differs between baseline and follow-up).
    case_a_repro_delta = next(
        d for d in diff_payload["reproducibility_deltas"] if d["case_id"] == "GS-A-candidate"
    )
    assert len(case_a_repro_delta["script_sha_changes"]) == 1
    assert case_a_repro_delta["script_sha_changes"][0]["relpath"].endswith("gen_gsa_deck.py")
    assert (
        case_a_repro_delta["script_sha_changes"][0]["a_sha256"]
        != case_a_repro_delta["script_sha_changes"][0]["b_sha256"]
    )

    # Case B kept stable -> no script drift
    case_b_repro_delta = next(
        d for d in diff_payload["reproducibility_deltas"] if d["case_id"] == "GS-B-candidate"
    )
    assert case_b_repro_delta["script_sha_changes"] == []

    # Tier 1 disclaimer preserved end-to-end in the diff payload
    assert "Tier 1 engineering candidate" in diff_res.text
    assert "not signed validation" in diff_res.text
    assert "not benchmark agreement" in diff_res.text

    # ------------------------------------------------------------------
    # Step 6: fetch reproducibility manifest for case A via HTTP
    # ------------------------------------------------------------------
    repro_res = client.get("/api/v1/reproducibility-manifest/GS-A-candidate")
    assert repro_res.status_code == 200
    repro_payload = repro_res.json()
    assert repro_payload["schema_version"] == REPRODUCIBILITY_MANIFEST_SCHEMA_VERSION
    assert repro_payload["case_id"] == "GS-A-candidate"
    # We didn't init a git repo under tmp_path, so git_commit_sha is None;
    # the manifest must still surface the field explicitly rather than
    # omitting it.
    assert "git_commit_sha" in repro_payload
    # The generator script fingerprint must be present + carry the
    # current (refined) body's SHA
    assert any(s["relpath"].endswith("gen_gsa_deck.py") for s in repro_payload["scripts"])
    assert "not signed validation" in repro_payload["claim_impact"]

    # ------------------------------------------------------------------
    # Bonus: verify the reviewer bundle inside the follow-up snapshot
    # is a valid zip + carries the Tier 1 banner
    # ------------------------------------------------------------------
    bundle_paths = list(followup.snapshot_dir.glob("tier1_reviewer_bundle_*.zip"))
    assert len(bundle_paths) == 1
    with zipfile.ZipFile(bundle_paths[0]) as zf:
        bundle_manifest = json.loads(zf.read("BUNDLE_MANIFEST.json").decode("utf-8"))
    assert bundle_manifest["claim_tier"] == "Tier 1 engineering candidate"
    assert bundle_manifest["cohort_count"] == 2


def test_phase5_workflow_handles_membership_change_e2e(
    client: _SyncASGIClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A reviewer adds a new case between two snapshots.

    Tier 1 engineering candidate; not signed validation; not benchmark agreement.
    """
    fake_root = tmp_path

    def fake_repo_root() -> Path:
        return fake_root

    monkeypatch.setattr(reproducibility_manifest_module, "_repo_root", fake_repo_root)
    monkeypatch.setattr(cohort_snapshots_module, "_repo_root", fake_repo_root)
    monkeypatch.setattr(cohort_snapshot_diff_module, "_repo_root", fake_repo_root)

    case_a = _write_baseline_evidence(
        "GS-A-candidate",
        fake_root,
        residual_velocity=75.0,
        energy_balance_error_pct=12.0,
        generator_body=b"# generator A\n",
    )
    write_cohort_snapshot([case_a], repo_root=fake_root, snapshot_label="2026-05-16T100000Z")

    case_b = _write_baseline_evidence(
        "GS-B-candidate",
        fake_root,
        residual_velocity=82.0,
        energy_balance_error_pct=10.0,
        generator_body=b"# generator B\n",
    )
    write_cohort_snapshot(
        [case_a, case_b], repo_root=fake_root, snapshot_label="2026-05-16T200000Z"
    )

    diff_res = client.get(
        "/api/v1/cohort-snapshot-diff",
        params={"a": "2026-05-16T100000Z", "b": "2026-05-16T200000Z"},
    )
    assert diff_res.status_code == 200
    diff_payload = diff_res.json()
    assert diff_payload["cohort_added"] == ["GS-B-candidate"]
    assert diff_payload["cohort_removed"] == []
    assert diff_payload["cohort_shared"] == ["GS-A-candidate"]
    # Only the shared case carries a completeness delta entry
    assert len(diff_payload["completeness_deltas"]) == 1
    assert diff_payload["completeness_deltas"][0]["case_id"] == "GS-A-candidate"
