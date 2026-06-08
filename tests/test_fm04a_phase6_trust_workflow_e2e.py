"""End-to-end Phase 6 reviewer trust workflow test (FM-04a Phase 6 F).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Exercises the 7-step Phase 6 reviewer journey end-to-end without going
through the live UI:

    Step 1: write a baseline snapshot of two candidate cases
    Step 2: drift case A — residual velocity changes, generator script
            body changes (forces script SHA delta) — write a fresh
            ballistic_metrics.json with the drifted values
    Step 3: write the follow-up snapshot
    Step 4: list snapshots via HTTP (newest-first)
    Step 5: fetch the live trust score for case A
    Step 6: fetch the trust score timeline for case A (oldest-first,
            two points, formula_version stamped)
    Step 7: fetch the snapshot narrative for the two snapshots and
            assert specific templated lines fire with the documented
            severity (residual_velocity_delta info; script_sha_changed
            warn; energy_balance_improved or _degraded info/warn)

Two tests:
    test_phase6_trust_workflow_e2e            — baseline journey
    test_phase6_trust_workflow_handles_edge_e2e — edge case (a case
        that exists in only one snapshot is reported via cohort_added
        with severity info; no false-positive numerical delta lines)

The test is load-bearing for Phase 6 F: it proves Phase 6 A through E
wires together end-to-end across the HTTP layer.
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
from app.api.routes import reproducibility_manifest as reproducibility_manifest_module
from app.api.routes import snapshot_narrative as snapshot_narrative_module
from app.api.routes import trust_score as trust_score_module
from app.api.routes import trust_score_timeline as trust_score_timeline_module
from app.main import app
from app.services.reporting._schema_versions import (
    COHORT_SNAPSHOT_MANIFEST_SCHEMA_VERSION,
    SNAPSHOT_NARRATIVE_SCHEMA_VERSION,
    TRUST_SCORE_FORMULA_VERSION,
    TRUST_SCORE_SCHEMA_VERSION,
    TRUST_SCORE_TIMELINE_SCHEMA_VERSION,
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

    monkeypatch.setattr(reproducibility_manifest_module, "_repo_root", fake_repo_root)
    monkeypatch.setattr(cohort_snapshots_module, "_repo_root", fake_repo_root)
    monkeypatch.setattr(cohort_snapshot_diff_module, "_repo_root", fake_repo_root)
    monkeypatch.setattr(snapshot_narrative_module, "_repo_root", fake_repo_root)
    monkeypatch.setattr(trust_score_module, "_repo_root", fake_repo_root)
    monkeypatch.setattr(trust_score_timeline_module, "_repo_root", fake_repo_root)
    return fake_root


def _write_case_evidence(
    case_id: str,
    root: Path,
    *,
    residual_velocity: float,
    energy_balance_error_pct: float,
    energy_status: str = "closed_aggregate",
    convergence_verdict: str = "candidate_observed_stable",
    generator_body: bytes,
) -> SnapshotCaseInput:
    """Seed the same on-disk evidence the live FM-04a builders read.

    Returns a SnapshotCaseInput so the test can hand it to
    ``write_cohort_snapshot()``.
    """
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
            "status": energy_status,
            "energy_balance_error_pct": energy_balance_error_pct,
        },
        # Inline a convergence_summary so the snapshot's metrics/<case>.json
        # carries the verdict the timeline + diff can recover later.
        "convergence_summary": {
            "combined_verdict": convergence_verdict,
            "mesh_sweep": {"candidate_stability": convergence_verdict},
            "dt_sweep": {"candidate_stability": convergence_verdict},
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
        "combined_verdict": convergence_verdict,
        "mesh_sweep": {"runs": [], "candidate_stability": convergence_verdict},
        "dt_sweep": {"runs": [], "candidate_stability": convergence_verdict},
        "row_count": 0,
        "rows": [],
        "claim_boundary": (
            "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"
        ),
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
    convergence_path.write_text(json.dumps(convergence_payload, indent=2), encoding="utf-8")

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


def test_phase6_trust_workflow_e2e(
    client: _SyncASGIClient,
    fake_repo: Path,
) -> None:
    """7-step Phase 6 reviewer trust workflow.

    Tier 1 engineering candidate; not signed validation; not benchmark agreement.
    """

    # ------------------------------------------------------------------
    # Step 1: baseline snapshot
    # ------------------------------------------------------------------
    case_a_v1 = _write_case_evidence(
        "GS-A-candidate",
        fake_repo,
        residual_velocity=75.0,
        energy_balance_error_pct=12.0,
        energy_status="closed_aggregate",
        convergence_verdict="candidate_observed_stable",
        generator_body=b"# baseline generator for GS-A\n",
    )
    case_b_v1 = _write_case_evidence(
        "GS-B-candidate",
        fake_repo,
        residual_velocity=82.0,
        energy_balance_error_pct=10.0,
        energy_status="closed_aggregate",
        convergence_verdict="candidate_observed_stable",
        generator_body=b"# baseline generator for GS-B\n",
    )
    baseline = write_cohort_snapshot(
        [case_a_v1, case_b_v1],
        repo_root=fake_repo,
        snapshot_label="2026-05-16T100000Z",
    )
    assert (baseline.snapshot_dir / "SNAPSHOT_MANIFEST.json").is_file()

    # ------------------------------------------------------------------
    # Step 2: drift case A — residual velocity changes, energy tightens,
    # generator script body changes (forces script SHA delta)
    # ------------------------------------------------------------------
    case_a_v2 = _write_case_evidence(
        "GS-A-candidate",
        fake_repo,
        residual_velocity=88.0,
        energy_balance_error_pct=8.0,
        energy_status="closed_aggregate",
        convergence_verdict="candidate_observed_stable",
        generator_body=b"# refined generator for GS-A v2 (added comments)\n",
    )

    # ------------------------------------------------------------------
    # Step 3: follow-up snapshot
    # ------------------------------------------------------------------
    followup = write_cohort_snapshot(
        [case_a_v2, case_b_v1],
        repo_root=fake_repo,
        snapshot_label="2026-05-16T200000Z",
    )
    assert followup.snapshot_label != baseline.snapshot_label

    # ------------------------------------------------------------------
    # Step 4: list snapshots via HTTP (newest-first)
    # ------------------------------------------------------------------
    list_res = client.get("/api/v1/cohort-snapshots")
    assert list_res.status_code == 200
    list_payload = list_res.json()
    assert list_payload["schema_version"] == COHORT_SNAPSHOT_MANIFEST_SCHEMA_VERSION
    assert list_payload["snapshot_count"] == 2
    labels = [entry["snapshot_label"] for entry in list_payload["snapshots"]]
    assert labels == ["2026-05-16T200000Z", "2026-05-16T100000Z"]

    # ------------------------------------------------------------------
    # Step 5: fetch the live trust score for case A
    # ------------------------------------------------------------------
    score_res = client.get("/api/v1/trust-score/GS-A-candidate")
    assert score_res.status_code == 200
    score_payload = score_res.json()
    assert score_payload["schema_version"] == TRUST_SCORE_SCHEMA_VERSION
    assert score_payload["formula_version"] == TRUST_SCORE_FORMULA_VERSION
    assert score_payload["case_id"] == "GS-A-candidate"
    assert score_payload["trust_score_max"] == 100
    assert 0 <= score_payload["trust_score"] <= 100
    axes = {entry["axis"] for entry in score_payload["breakdown"]}
    assert axes == {
        "completeness",
        "convergence_stability",
        "energy_audit_closure",
        "reproducibility_clean",
    }
    # tmp_path is not a git repo; the reproducibility axis should
    # penalize the missing git_commit_sha (REPRO_PENALTY_GIT_SHA_MISSING=25)
    repro_entry = next(
        e for e in score_payload["breakdown"] if e["axis"] == "reproducibility_clean"
    )
    assert repro_entry["raw_score"] <= 75

    # Tier 1 disclaimer preserved end-to-end
    assert "Tier 1 engineering candidate" in score_res.text
    assert "not signed validation" in score_res.text
    assert "not benchmark agreement" in score_res.text

    # ------------------------------------------------------------------
    # Step 6: fetch the trust score timeline for case A
    # ------------------------------------------------------------------
    timeline_res = client.get("/api/v1/trust-score-timeline/GS-A-candidate")
    assert timeline_res.status_code == 200
    timeline_payload = timeline_res.json()
    assert timeline_payload["schema_version"] == TRUST_SCORE_TIMELINE_SCHEMA_VERSION
    assert timeline_payload["formula_version"] == TRUST_SCORE_FORMULA_VERSION
    assert timeline_payload["case_id"] == "GS-A-candidate"
    assert timeline_payload["point_count"] == 2
    point_labels = [p["snapshot_label"] for p in timeline_payload["points"]]
    # oldest-first ordering
    assert point_labels == ["2026-05-16T100000Z", "2026-05-16T200000Z"]
    # Both snapshots captured a closed_aggregate energy block, so
    # energy_audit_weighted should be non-zero on both points.
    for point in timeline_payload["points"]:
        assert point["energy_audit_weighted"] > 0
        assert point["completeness_weighted"] > 0
        # Convergence verdict was inlined in metrics/<case>.json, so the
        # timeline can recover stability and score it non-zero
        assert point["convergence_weighted"] > 0

    # Tier 1 disclaimer preserved
    assert "not signed validation" in timeline_res.text

    # ------------------------------------------------------------------
    # Step 7: fetch snapshot narrative — assert specific templated lines
    # fire with the documented severity
    # ------------------------------------------------------------------
    narrative_res = client.get(
        "/api/v1/snapshot-narrative",
        params={"a": "2026-05-16T100000Z", "b": "2026-05-16T200000Z"},
    )
    assert narrative_res.status_code == 200
    narrative_payload = narrative_res.json()
    assert narrative_payload["schema_version"] == SNAPSHOT_NARRATIVE_SCHEMA_VERSION
    assert narrative_payload["snapshot_a_label"] == "2026-05-16T100000Z"
    assert narrative_payload["snapshot_b_label"] == "2026-05-16T200000Z"

    # Find case A's narrative
    case_a_narrative = next(
        n for n in narrative_payload["narratives"] if n["case_id"] == "GS-A-candidate"
    )
    template_lines = {line["template_id"]: line for line in case_a_narrative["lines"]}

    # residual_velocity_delta — info severity (75 -> 88)
    assert "residual_velocity_delta" in template_lines
    assert template_lines["residual_velocity_delta"]["severity"] == "info"
    assert "75" in template_lines["residual_velocity_delta"]["text"]
    assert "88" in template_lines["residual_velocity_delta"]["text"]

    # energy_balance_improved — info severity (12% -> 8% is improvement)
    assert "energy_balance_improved" in template_lines
    assert template_lines["energy_balance_improved"]["severity"] == "info"

    # script_sha_changed — warn severity (generator body changed)
    assert "script_sha_changed" in template_lines
    assert template_lines["script_sha_changed"]["severity"] == "warn"
    assert "gen_gsa_deck.py" in template_lines["script_sha_changed"]["text"]

    # Case B kept stable — narrative may be empty OR carry only
    # _unchanged lines; it must NOT carry warn/danger lines
    case_b_narrative = next(
        n for n in narrative_payload["narratives"] if n["case_id"] == "GS-B-candidate"
    )
    for line in case_b_narrative["lines"]:
        assert line["severity"] != "warn"
        assert line["severity"] != "danger"

    # Tier 1 disclaimer preserved end-to-end in narrative payload
    assert "Tier 1 engineering candidate" in narrative_res.text
    assert "not signed validation" in narrative_res.text
    assert "not benchmark agreement" in narrative_res.text


def test_phase6_trust_workflow_handles_edge_e2e(
    client: _SyncASGIClient,
    fake_repo: Path,
) -> None:
    """Edge case: cohort membership change between snapshots.

    Case B exists only in the follow-up snapshot. Verifies:
      - the narrative endpoint surfaces ``cohort_added`` for case B
        with severity ``info``
      - the trust score timeline for case B has exactly 1 point
      - the timeline for a case that never appears is empty
      - shared-case narrative for case A surfaces convergence regression
        as warn (verdict went from stable -> unstable)

    Tier 1 engineering candidate; not signed validation; not benchmark agreement.
    """

    # baseline: only case A, stable
    case_a_v1 = _write_case_evidence(
        "GS-A-candidate",
        fake_repo,
        residual_velocity=75.0,
        energy_balance_error_pct=12.0,
        energy_status="closed_aggregate",
        convergence_verdict="candidate_observed_stable",
        generator_body=b"# generator A\n",
    )
    write_cohort_snapshot(
        [case_a_v1],
        repo_root=fake_repo,
        snapshot_label="2026-05-16T100000Z",
    )

    # follow-up: case A's convergence degrades to candidate_observed_unstable;
    # case B newly added
    case_a_v2 = _write_case_evidence(
        "GS-A-candidate",
        fake_repo,
        residual_velocity=75.0,
        energy_balance_error_pct=12.0,
        energy_status="closed_aggregate",
        convergence_verdict="candidate_observed_unstable",
        generator_body=b"# generator A\n",  # same bytes => no script SHA delta
    )
    case_b_v1 = _write_case_evidence(
        "GS-B-candidate",
        fake_repo,
        residual_velocity=82.0,
        energy_balance_error_pct=10.0,
        energy_status="closed_aggregate",
        convergence_verdict="candidate_observed_stable",
        generator_body=b"# generator B\n",
    )
    write_cohort_snapshot(
        [case_a_v2, case_b_v1],
        repo_root=fake_repo,
        snapshot_label="2026-05-16T200000Z",
    )

    # ------------------------------------------------------------------
    # Snapshot narrative — assert cohort_added (case B) + convergence
    # regression line (case A) fire with documented severities
    # ------------------------------------------------------------------
    narrative_res = client.get(
        "/api/v1/snapshot-narrative",
        params={"a": "2026-05-16T100000Z", "b": "2026-05-16T200000Z"},
    )
    assert narrative_res.status_code == 200
    narrative_payload = narrative_res.json()

    case_b_narrative = next(
        n for n in narrative_payload["narratives"] if n["case_id"] == "GS-B-candidate"
    )
    cohort_added_lines = [
        line for line in case_b_narrative["lines"] if line["template_id"] == "cohort_added"
    ]
    assert len(cohort_added_lines) == 1
    assert cohort_added_lines[0]["severity"] == "info"
    # Case B is brand-new — must NOT carry any numerical-delta or
    # script-sha lines (no diff is possible against an absent baseline)
    template_ids_b = {line["template_id"] for line in case_b_narrative["lines"]}
    assert "residual_velocity_delta" not in template_ids_b
    assert "script_sha_changed" not in template_ids_b

    # Case A's convergence verdict went stable -> unstable. Per the
    # Phase 6 C template severity table, the convergence_verdict_changed
    # template escalates to "danger" when the b-side is
    # candidate_observed_unstable.
    case_a_narrative = next(
        n for n in narrative_payload["narratives"] if n["case_id"] == "GS-A-candidate"
    )
    template_lines_a = {line["template_id"]: line for line in case_a_narrative["lines"]}
    assert "convergence_verdict_changed" in template_lines_a
    assert template_lines_a["convergence_verdict_changed"]["severity"] == "danger"
    assert "candidate_observed_unstable" in template_lines_a["convergence_verdict_changed"]["text"]

    # ------------------------------------------------------------------
    # Timeline — case B appears in only one snapshot (point_count == 1);
    # an unknown case returns an empty timeline (point_count == 0)
    # ------------------------------------------------------------------
    timeline_b_res = client.get("/api/v1/trust-score-timeline/GS-B-candidate")
    assert timeline_b_res.status_code == 200
    timeline_b = timeline_b_res.json()
    assert timeline_b["point_count"] == 1
    assert timeline_b["points"][0]["snapshot_label"] == "2026-05-16T200000Z"

    timeline_unknown_res = client.get("/api/v1/trust-score-timeline/GS-NEVER-candidate")
    assert timeline_unknown_res.status_code == 200
    timeline_unknown = timeline_unknown_res.json()
    assert timeline_unknown["point_count"] == 0
    assert timeline_unknown["points"] == []
    # Tier 1 disclaimer still present on the empty payload
    assert "not signed validation" in timeline_unknown["claim_impact"]
