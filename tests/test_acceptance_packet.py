"""Tests for the Tier 1 acceptance evidence packet (FM-04a Phase 3 A).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.services.reporting.acceptance_packet import (
    CLAIM_BOUNDARY,
    CLAIM_TIER,
    AcceptancePacket,
    AcceptancePacketInputs,
    build_acceptance_packet,
    render_acceptance_packet_json,
    write_acceptance_packet,
)


def _write_minimal_metrics(tmp_path: Path) -> Path:
    payload = {
        "case_id": "GS-102-phase3-a",
        "claim_boundary": CLAIM_BOUNDARY,
        "perforation_marker": "perforated_candidate",
        "projectile_initial_velocity_m_per_s": 600.0,
        "residual_velocity_candidate_m_per_s": 75.0,
        "crossing_evidence": {
            "status": "candidate_observed",
            "front_face_crossed": True,
            "back_face_crossed": True,
            "first_back_face_crossing_t_s": 5.0e-5,
        },
        "energy_audit": {
            "status": "closed_aggregate",
            "initial_kinetic_energy_j": 1731.0,
            "residual_kinetic_energy_j": 575.5,
            "aggregate_internal_energy_j": 826.6,
            "external_work_j": 0.0,
            "energy_balance_error_pct": 19.0,
            "breakdown_status": "aggregated_into_internal_energy",
            "missing_terms": [
                "plastic_dissipation_j",
                "contact_friction_j",
                "hourglass_energy_j",
            ],
        },
    }
    metrics_path = tmp_path / "ballistic_metrics.json"
    metrics_path.write_text(json.dumps(payload), encoding="utf-8")
    return metrics_path


def _write_minimal_convergence(tmp_path: Path) -> Path:
    payload = {
        "case_id": "GS-102-phase3-a",
        "combined_verdict": "candidate_observed_stable",
        "mesh_sweep": {"candidate_stability": "candidate_observed_stable"},
        "dt_sweep": {"candidate_stability": "candidate_observed_stable"},
        "row_count": 4,
        "tolerance_pct": 5.0,
    }
    out = tmp_path / "convergence_study.json"
    out.write_text(json.dumps(payload), encoding="utf-8")
    return out


def _write_fake_deck(tmp_path: Path, name: str) -> Path:
    path = tmp_path / name
    path.write_text(f"fake deck {name}\n", encoding="utf-8")
    return path


def test_packet_assembles_all_sections_from_minimal_evidence(tmp_path: Path) -> None:
    metrics = _write_minimal_metrics(tmp_path)
    convergence = _write_minimal_convergence(tmp_path)
    starter = _write_fake_deck(tmp_path, "model_00_0000.rad")
    engine = _write_fake_deck(tmp_path, "model_00_0001.rad")

    packet = build_acceptance_packet(
        AcceptancePacketInputs(
            case_id="GS-102-phase3-a",
            ballistic_metrics_path=metrics,
            convergence_study_path=convergence,
            starter_deck_path=starter,
            engine_deck_path=engine,
            repo_root=tmp_path,
        )
    )
    assert isinstance(packet, AcceptancePacket)
    assert packet.case_id == "GS-102-phase3-a"
    assert packet.claim_tier == CLAIM_TIER
    assert packet.claim_boundary == CLAIM_BOUNDARY

    deck_kinds = {a.kind for a in packet.deck_artifacts}
    assert deck_kinds == {"deck_starter", "deck_engine"}
    evidence_kinds = {a.kind for a in packet.evidence_artifacts}
    assert "ballistic_metrics" in evidence_kinds
    assert "convergence_study" in evidence_kinds

    # Every present artifact carries SHA-256 + bytes.
    for artifact in packet.deck_artifacts + packet.evidence_artifacts:
        assert artifact.sha256 is not None
        assert artifact.bytes_count is not None and artifact.bytes_count > 0

    # Summaries populated from on-disk evidence.
    assert packet.ballistic_metrics_summary["perforation_marker"] == "perforated_candidate"
    assert packet.energy_audit_summary["status"] == "closed_aggregate"
    assert packet.energy_audit_summary["aggregate_internal_energy_j"] == pytest.approx(826.6)
    assert packet.convergence_study_summary["status"] == "available"
    assert packet.convergence_study_summary["combined_verdict"] == "candidate_observed_stable"


def test_packet_handles_missing_convergence_and_decks(tmp_path: Path) -> None:
    metrics = _write_minimal_metrics(tmp_path)
    packet = build_acceptance_packet(
        AcceptancePacketInputs(
            case_id="GS-102-phase3-a",
            ballistic_metrics_path=metrics,
            convergence_study_path=None,
            starter_deck_path=None,
            engine_deck_path=None,
            repo_root=tmp_path,
        )
    )
    assert packet.deck_artifacts == []
    # ballistic metrics is still the lone evidence artifact.
    assert len(packet.evidence_artifacts) == 1
    assert packet.evidence_artifacts[0].kind == "ballistic_metrics"
    assert packet.convergence_study_summary["status"] == "unavailable"
    assert packet.convergence_study_summary["combined_verdict"] == "insufficient_data"


def test_packet_raises_when_metrics_file_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        build_acceptance_packet(
            AcceptancePacketInputs(
                case_id="missing",
                ballistic_metrics_path=tmp_path / "nope.json",
                repo_root=tmp_path,
            )
        )


def test_render_json_serializes_packet_with_all_top_level_keys(tmp_path: Path) -> None:
    metrics = _write_minimal_metrics(tmp_path)
    packet = build_acceptance_packet(
        AcceptancePacketInputs(
            case_id="GS-102-phase3-a",
            ballistic_metrics_path=metrics,
            repo_root=tmp_path,
        )
    )
    payload = json.loads(render_acceptance_packet_json(packet))
    for key in (
        "case_id",
        "generated_at_utc",
        "claim_tier",
        "claim_boundary",
        "deck_artifacts",
        "evidence_artifacts",
        "visualization_artifacts",
        "ballistic_metrics_summary",
        "energy_audit_summary",
        "convergence_study_summary",
        "assumptions",
        "limitations",
        "tier2_blockers_remaining",
        "claim_impact",
    ):
        assert key in payload, f"missing top-level key {key!r}"


def test_packet_listing_tier2_blockers_keeps_fm04b_path_explicit(tmp_path: Path) -> None:
    metrics = _write_minimal_metrics(tmp_path)
    packet = build_acceptance_packet(
        AcceptancePacketInputs(
            case_id="GS-102-phase3-a",
            ballistic_metrics_path=metrics,
            repo_root=tmp_path,
        )
    )
    blockers = " ".join(packet.tier2_blockers_remaining)
    assert "ADR-024 (full)" in blockers
    assert "sealed packet" in blockers
    assert "independent reviewer signoff" in blockers
    assert "user milestone-experience" in blockers
    assert "Linear / Notion" in blockers


def test_writer_writes_canonical_filename(tmp_path: Path) -> None:
    metrics = _write_minimal_metrics(tmp_path)
    packet = build_acceptance_packet(
        AcceptancePacketInputs(
            case_id="GS-102-phase3-a",
            ballistic_metrics_path=metrics,
            repo_root=tmp_path,
        )
    )
    out_dir = tmp_path / "reports"
    path = write_acceptance_packet(packet, out_dir)
    assert path.name == "GS-102-phase3-a_acceptance_packet.json"
    parsed = json.loads(path.read_text(encoding="utf-8"))
    assert parsed["case_id"] == "GS-102-phase3-a"


def test_writer_refuses_paths_under_golden_samples(tmp_path: Path) -> None:
    metrics = _write_minimal_metrics(tmp_path)
    packet = build_acceptance_packet(
        AcceptancePacketInputs(
            case_id="GS-102-phase3-a",
            ballistic_metrics_path=metrics,
            repo_root=tmp_path,
        )
    )
    forbidden = tmp_path / "golden_samples" / "GS-102-some-candidate" / "reports"
    with pytest.raises(ValueError, match="golden_samples"):
        write_acceptance_packet(packet, forbidden)


def test_packet_preserves_tier1_boundary_wording(tmp_path: Path) -> None:
    metrics = _write_minimal_metrics(tmp_path)
    packet = build_acceptance_packet(
        AcceptancePacketInputs(
            case_id="GS-102-phase3-a",
            ballistic_metrics_path=metrics,
            repo_root=tmp_path,
        )
    )
    text = render_acceptance_packet_json(packet).lower()
    assert "tier1_engineering_candidate" in text
    assert "not_signed_validation" in text
    assert "not_benchmark_agreement" in text
    # Forbidden positive claims absent.
    for forbidden in (
        "validated against",
        "perforation completed",
        "bullet-through-steel complete",
        "validated physics",
    ):
        assert forbidden not in text
    # Strip-then-check audit: no leftover positive claim.
    stripped = (
        text.replace("not_signed_validation", "")
        .replace("not_benchmark_agreement", "")
        .replace("not signed validation", "")
        .replace("not benchmark agreement", "")
    )
    assert "signed validation" not in stripped
    assert "benchmark agreement" not in stripped


def test_packet_is_not_sealed_tier2_bundle(tmp_path: Path) -> None:
    metrics = _write_minimal_metrics(tmp_path)
    packet = build_acceptance_packet(
        AcceptancePacketInputs(
            case_id="GS-102-phase3-a",
            ballistic_metrics_path=metrics,
            repo_root=tmp_path,
        )
    )
    # The Tier 1 packet must explicitly NOT claim to be a sealed Tier 2 bundle.
    text = render_acceptance_packet_json(packet).lower()
    assert "not a sealed tier 2 bundle" in text or "not a sealed" in text
    # Sealed packet path is named in the deferred blockers list.
    assert any("sealed packet" in b.lower() for b in packet.tier2_blockers_remaining)
