"""Tests for the Tier 1 case-vs-case comparison (FM-04a Phase 3 B).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.services.reporting.acceptance_packet import (
    AcceptancePacketInputs,
    build_acceptance_packet,
)
from app.services.reporting.case_comparison import (
    CLAIM_IMPACT_DEFAULT,
    CaseComparison,
    build_case_comparison,
    render_case_comparison_json,
)


def _write_metrics(
    tmp_path: Path,
    case_id: str,
    *,
    residual_velocity_m_per_s: float = 75.0,
    perforation_marker: str = "perforated_candidate",
    energy_balance_error_pct: float = 19.0,
    energy_audit_status: str = "closed_aggregate",
) -> Path:
    payload = {
        "case_id": case_id,
        "perforation_marker": perforation_marker,
        "projectile_initial_velocity_m_per_s": 600.0,
        "residual_velocity_candidate_m_per_s": residual_velocity_m_per_s,
        "crossing_evidence": {
            "status": "candidate_observed",
            "front_face_crossed": True,
            "back_face_crossed": True,
            "first_back_face_crossing_t_s": 5.0e-5,
        },
        "energy_audit": {
            "status": energy_audit_status,
            "initial_kinetic_energy_j": 1731.0,
            "residual_kinetic_energy_j": 575.5,
            "aggregate_internal_energy_j": 826.6,
            "external_work_j": 0.0,
            "energy_balance_error_pct": energy_balance_error_pct,
            "breakdown_status": "aggregated_into_internal_energy",
            "missing_terms": [],
        },
    }
    out = tmp_path / f"{case_id}_metrics.json"
    out.write_text(json.dumps(payload), encoding="utf-8")
    return out


def _write_convergence(
    tmp_path: Path,
    case_id: str,
    *,
    combined_verdict: str = "candidate_observed_stable",
) -> Path:
    payload = {
        "case_id": case_id,
        "combined_verdict": combined_verdict,
        "mesh_sweep": {"candidate_stability": combined_verdict},
        "dt_sweep": {"candidate_stability": combined_verdict},
        "row_count": 4,
        "tolerance_pct": 5.0,
    }
    out = tmp_path / f"{case_id}_convergence.json"
    out.write_text(json.dumps(payload), encoding="utf-8")
    return out


def _write_deck(tmp_path: Path, name: str, contents: str = "fake deck\n") -> Path:
    path = tmp_path / name
    path.write_text(contents, encoding="utf-8")
    return path


def _make_packet(
    tmp_path: Path,
    case_id: str,
    *,
    residual_velocity_m_per_s: float = 75.0,
    perforation_marker: str = "perforated_candidate",
    energy_balance_error_pct: float = 19.0,
    energy_audit_status: str = "closed_aggregate",
    convergence_verdict: str = "candidate_observed_stable",
    deck_contents: str = "fake deck\n",
    include_convergence: bool = True,
):
    metrics = _write_metrics(
        tmp_path,
        case_id,
        residual_velocity_m_per_s=residual_velocity_m_per_s,
        perforation_marker=perforation_marker,
        energy_balance_error_pct=energy_balance_error_pct,
        energy_audit_status=energy_audit_status,
    )
    convergence = (
        _write_convergence(tmp_path, case_id, combined_verdict=convergence_verdict)
        if include_convergence
        else None
    )
    starter = _write_deck(tmp_path, f"{case_id}_starter.rad", deck_contents)
    return build_acceptance_packet(
        AcceptancePacketInputs(
            case_id=case_id,
            ballistic_metrics_path=metrics,
            convergence_study_path=convergence,
            starter_deck_path=starter,
            repo_root=tmp_path,
        )
    )


def test_comparison_emits_all_diff_axes(tmp_path: Path) -> None:
    packet_a = _make_packet(
        tmp_path,
        "GS-102-phase3-a",
        residual_velocity_m_per_s=75.0,
        energy_balance_error_pct=19.0,
    )
    packet_b = _make_packet(
        tmp_path,
        "GS-102-phase3-b",
        residual_velocity_m_per_s=85.0,
        energy_balance_error_pct=11.0,
    )
    comparison = build_case_comparison(packet_a, packet_b)
    assert isinstance(comparison, CaseComparison)
    assert comparison.case_a == "GS-102-phase3-a"
    assert comparison.case_b == "GS-102-phase3-b"

    rv = comparison.residual_velocity_diff
    assert rv["a"] == 75.0
    assert rv["b"] == 85.0
    assert rv["delta"] == pytest.approx(10.0)
    assert rv["delta_pct"] == pytest.approx((10.0 / 75.0) * 100.0)

    eb = comparison.energy_balance_error_diff
    assert eb["delta_abs_pct"] == pytest.approx(8.0)

    pm = comparison.perforation_marker_diff
    assert pm["same_marker"] is True

    ea = comparison.energy_audit_status_diff
    assert ea["both_closed"] is True
    assert ea["same_status"] is True

    cv = comparison.convergence_verdict_diff
    assert cv["same_verdict"] is True


def test_comparison_identity_case_has_zero_deltas(tmp_path: Path) -> None:
    packet = _make_packet(tmp_path, "GS-102-phase3-a")
    comparison = build_case_comparison(packet, packet)
    assert comparison.residual_velocity_diff["delta"] == pytest.approx(0.0)
    assert comparison.residual_velocity_diff["delta_pct"] == pytest.approx(0.0)
    assert comparison.energy_balance_error_diff["delta_abs_pct"] == pytest.approx(0.0)
    assert comparison.perforation_marker_diff["same_marker"] is True
    assert comparison.energy_audit_status_diff["same_status"] is True
    assert comparison.convergence_verdict_diff["same_verdict"] is True
    deck_diff = comparison.deck_artifact_diff
    assert deck_diff["a_only"] == []
    assert deck_diff["b_only"] == []
    assert deck_diff["shared"] == ["deck_starter"]
    assert deck_diff["hash_changed"] == []


def test_comparison_detects_hash_change_in_decks(tmp_path: Path) -> None:
    packet_a = _make_packet(tmp_path, "GS-102-phase3-a", deck_contents="deck variant A\n")
    packet_b = _make_packet(tmp_path, "GS-102-phase3-b", deck_contents="deck variant B\n")
    comparison = build_case_comparison(packet_a, packet_b)
    hash_changed = comparison.deck_artifact_diff["hash_changed"]
    assert len(hash_changed) == 1
    assert hash_changed[0]["kind"] == "deck_starter"
    assert hash_changed[0]["a_sha256"] != hash_changed[0]["b_sha256"]


def test_comparison_handles_b_only_evidence(tmp_path: Path) -> None:
    packet_a = _make_packet(tmp_path, "GS-102-phase3-a", include_convergence=False)
    packet_b = _make_packet(tmp_path, "GS-102-phase3-b", include_convergence=True)
    comparison = build_case_comparison(packet_a, packet_b)
    ev = comparison.evidence_artifact_diff
    assert "convergence_study" in ev["b_only"]
    assert "convergence_study" not in ev["a_only"]
    # ballistic_metrics is present in both cases but the case_id in the
    # payload differs, so the kind is shared-but-hash-changed (NOT shared).
    assert ev["shared"] == []
    hash_changed_kinds = [item["kind"] for item in ev["hash_changed"]]
    assert "ballistic_metrics" in hash_changed_kinds


def test_comparison_records_perforation_marker_disagreement(tmp_path: Path) -> None:
    packet_a = _make_packet(tmp_path, "GS-102-phase3-a", perforation_marker="perforated_candidate")
    packet_b = _make_packet(
        tmp_path, "GS-102-phase3-b", perforation_marker="non_perforated_candidate"
    )
    comparison = build_case_comparison(packet_a, packet_b)
    pm = comparison.perforation_marker_diff
    assert pm["same_marker"] is False
    assert pm["a"] == "perforated_candidate"
    assert pm["b"] == "non_perforated_candidate"


def test_comparison_records_convergence_verdict_disagreement(tmp_path: Path) -> None:
    packet_a = _make_packet(
        tmp_path, "GS-102-phase3-a", convergence_verdict="candidate_observed_stable"
    )
    packet_b = _make_packet(
        tmp_path, "GS-102-phase3-b", convergence_verdict="candidate_observed_unstable"
    )
    comparison = build_case_comparison(packet_a, packet_b)
    cv = comparison.convergence_verdict_diff
    assert cv["same_verdict"] is False
    assert cv["a"] == "candidate_observed_stable"
    assert cv["b"] == "candidate_observed_unstable"


def test_render_json_includes_all_top_level_keys(tmp_path: Path) -> None:
    packet_a = _make_packet(tmp_path, "GS-102-phase3-a")
    packet_b = _make_packet(tmp_path, "GS-102-phase3-b")
    payload = json.loads(render_case_comparison_json(build_case_comparison(packet_a, packet_b)))
    for key in (
        "case_a",
        "case_b",
        "generated_at_utc",
        "claim_boundary",
        "residual_velocity_diff",
        "perforation_marker_diff",
        "energy_balance_error_diff",
        "energy_audit_status_diff",
        "convergence_verdict_diff",
        "deck_artifact_diff",
        "evidence_artifact_diff",
        "claim_impact",
    ):
        assert key in payload, f"missing top-level key {key!r}"


def test_comparison_preserves_tier1_boundary_wording(tmp_path: Path) -> None:
    packet_a = _make_packet(tmp_path, "GS-102-phase3-a")
    packet_b = _make_packet(tmp_path, "GS-102-phase3-b")
    comparison = build_case_comparison(packet_a, packet_b)
    text = render_case_comparison_json(comparison).lower()
    assert "tier1_engineering_candidate" in text
    assert "not_signed_validation" in text
    assert "not_benchmark_agreement" in text
    for forbidden in (
        "validated against",
        "perforation completed",
        "bullet-through-steel complete",
        "validated physics",
    ):
        assert forbidden not in text
    # Strip the disclaimer phrases, then audit the residue for any
    # leftover positive-claim leakage.
    stripped = (
        text.replace("not_signed_validation", "")
        .replace("not_benchmark_agreement", "")
        .replace("not signed validation", "")
        .replace("not benchmark agreement", "")
    )
    assert "signed validation" not in stripped
    assert "benchmark agreement" not in stripped


def test_claim_impact_default_is_present(tmp_path: Path) -> None:
    packet = _make_packet(tmp_path, "GS-102-phase3-a")
    comparison = build_case_comparison(packet, packet)
    assert comparison.claim_impact == CLAIM_IMPACT_DEFAULT
    assert "case-vs-case" in comparison.claim_impact
    assert "not signed validation" in comparison.claim_impact
