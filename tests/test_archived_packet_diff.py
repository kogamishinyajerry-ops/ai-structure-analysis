"""Tests for the Tier 1 archived packet diff (FM-04a Phase 4 D).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.services.reporting.archived_packet_diff import (
    ArchivedPacketDiff,
    diff_archived_packets,
    render_archived_packet_diff_json,
)


def _write_archived_packet(
    tmp_path: Path,
    name: str,
    *,
    case_id: str = "GS-102-phase4d",
    residual_velocity: float = 75.0,
    energy_balance_error: float = 19.0,
    perforation_marker: str = "perforated_candidate",
    audit_status: str = "closed_aggregate",
    convergence_verdict: str = "candidate_observed_stable",
    deck_starter_sha: str = "a" * 64,
    claim_boundary: str = (
        "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"
    ),
) -> Path:
    payload = {
        "case_id": case_id,
        "generated_at_utc": "2026-05-16T03:00:00+00:00",
        "claim_tier": "Tier 1 engineering candidate",
        "claim_boundary": claim_boundary,
        "deck_artifacts": [
            {
                "relpath": "golden_samples/case/data/model_00_0000.rad",
                "sha256": deck_starter_sha,
                "bytes": 123,
                "kind": "deck_starter",
            },
            {
                "relpath": "golden_samples/case/data/model_00_0001.rad",
                "sha256": "b" * 64,
                "bytes": 456,
                "kind": "deck_engine",
            },
        ],
        "evidence_artifacts": [
            {
                "relpath": "project_state/x/ballistic/ballistic_metrics.json",
                "sha256": "c" * 64,
                "bytes": 789,
                "kind": "ballistic_metrics",
            },
        ],
        "visualization_artifacts": [],
        "ballistic_metrics_summary": {
            "perforation_marker": perforation_marker,
            "projectile_initial_velocity_m_per_s": 600.0,
            "residual_velocity_candidate_m_per_s": residual_velocity,
            "front_face_crossed": True,
            "back_face_crossed": True,
            "first_back_face_crossing_t_s": 5e-5,
        },
        "energy_audit_summary": {
            "status": audit_status,
            "energy_balance_error_pct": energy_balance_error,
        },
        "convergence_study_summary": {
            "status": "available",
            "combined_verdict": convergence_verdict,
        },
        "assumptions": [],
        "limitations": [],
        "tier2_blockers_remaining": [
            "ADR-024 (full) — locked benchmark case + tolerance + uncertainty interval",
        ],
        "claim_impact": (
            "Tier 1 candidate acceptance evidence packet only; not signed "
            "validation; not benchmark agreement; not a sealed Tier 2 bundle."
        ),
    }
    out = tmp_path / name
    out.write_text(json.dumps(payload), encoding="utf-8")
    return out


def test_identity_diff_yields_zero_deltas(tmp_path: Path) -> None:
    path_a = _write_archived_packet(tmp_path, "packet_a.json")
    path_b = _write_archived_packet(tmp_path, "packet_b.json")  # same content
    diff = diff_archived_packets(path_a, path_b, repo_root=tmp_path)
    assert isinstance(diff, ArchivedPacketDiff)
    assert diff.same_case is True
    assert diff.residual_velocity_diff["delta"] == 0.0
    assert diff.residual_velocity_diff["delta_pct"] == 0.0
    assert diff.energy_balance_error_diff["delta_abs_pct"] == 0.0
    assert diff.perforation_marker_diff["same_marker"] is True
    assert diff.energy_audit_status_diff["both_closed"] is True
    assert diff.convergence_verdict_diff["same_verdict"] is True


def test_archive_provenance_carries_sha_mtime_and_relpath(tmp_path: Path) -> None:
    path_a = _write_archived_packet(tmp_path, "packet_a.json")
    path_b = _write_archived_packet(tmp_path, "packet_b.json", residual_velocity=80.0)
    diff = diff_archived_packets(path_a, path_b, repo_root=tmp_path)
    assert diff.archive_a.sha256 != diff.archive_b.sha256
    assert diff.archive_a.relpath == "packet_a.json"
    assert diff.archive_b.relpath == "packet_b.json"
    assert diff.archive_a.case_id == "GS-102-phase4d"
    assert diff.archive_a.claim_boundary.startswith("tier1_engineering_candidate")


def test_diff_detects_hash_change_in_archived_decks(tmp_path: Path) -> None:
    path_a = _write_archived_packet(tmp_path, "packet_a.json", deck_starter_sha="a" * 64)
    path_b = _write_archived_packet(tmp_path, "packet_b.json", deck_starter_sha="d" * 64)
    diff = diff_archived_packets(path_a, path_b, repo_root=tmp_path)
    hash_changed = diff.artifact_hash_diff["hash_changed"]
    kinds_changed = [item["kind"] for item in hash_changed]
    assert "deck_starter" in kinds_changed
    # deck_engine hash is unchanged in both fixtures.
    assert "deck_engine" in diff.artifact_hash_diff["shared"]


def test_diff_rejects_non_tier1_packet(tmp_path: Path) -> None:
    bad = _write_archived_packet(
        tmp_path,
        "non_tier1.json",
        claim_boundary="tier2_engineering_promotion; not_signed_validation",
    )
    good = _write_archived_packet(tmp_path, "good.json")
    with pytest.raises(ValueError, match="not a Tier 1 candidate manifest"):
        diff_archived_packets(bad, good, repo_root=tmp_path)


def test_diff_raises_when_file_missing(tmp_path: Path) -> None:
    good = _write_archived_packet(tmp_path, "good.json")
    with pytest.raises(FileNotFoundError, match="archived packet not found"):
        diff_archived_packets(tmp_path / "nope.json", good, repo_root=tmp_path)


def test_diff_preserves_tier1_boundary_wording(tmp_path: Path) -> None:
    path_a = _write_archived_packet(tmp_path, "packet_a.json")
    path_b = _write_archived_packet(tmp_path, "packet_b.json")
    diff = diff_archived_packets(path_a, path_b, repo_root=tmp_path)
    text = render_archived_packet_diff_json(diff).lower()
    assert "tier1_engineering_candidate" in text
    assert "not_signed_validation" in text
    assert "not_benchmark_agreement" in text
    stripped = (
        text.replace("not_signed_validation", "")
        .replace("not_benchmark_agreement", "")
        .replace("not signed validation", "")
        .replace("not benchmark agreement", "")
    )
    for forbidden in (
        "validated against",
        "signed validation",
        "benchmark agreement",
        "perforation completed",
        "bullet-through-steel complete",
        "validated physics",
    ):
        assert forbidden not in stripped, f"leak: {forbidden}"
