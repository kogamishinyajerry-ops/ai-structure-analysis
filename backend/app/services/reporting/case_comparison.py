"""Tier 1 candidate case-vs-case comparison (FM-04a Phase 3 B).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Pure builder that takes two ``AcceptancePacket`` instances and emits a
structured side-by-side diff payload a non-author reviewer can use to
inspect two candidate runs. The comparison is **case-vs-case**, NOT
case-vs-experimental-benchmark — every diff axis reads from the two
acceptance packets themselves, and the rendered payload carries the
same Tier 1 boundary wording the source packets do.

Forbidden wording: ``validated against``, ``benchmark agreement``,
``signed validation``, ``perforation completed``, ``validated
physics``, ``bullet-through-steel complete``. The builder asserts the
rendered comparison stays clean against these positive claims; the
``not <claim>`` disclaimer form is preserved.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from ._schema_versions import CASE_COMPARISON_SCHEMA_VERSION
from .acceptance_packet import (
    CLAIM_BOUNDARY,
    AcceptanceArtifact,
    AcceptancePacket,
)

CLAIM_IMPACT_DEFAULT = (
    "Tier 1 candidate case-vs-case comparison only; not signed validation; "
    "not benchmark agreement; not a comparison against experimental data. "
    "Both inputs are Tier 1 candidate acceptance packets."
)


@dataclass(frozen=True)
class CaseComparison:
    """Structured diff between two Tier 1 candidate acceptance packets."""

    case_a: str
    case_b: str
    generated_at_utc: str
    claim_boundary: str
    residual_velocity_diff: dict[str, Any]
    perforation_marker_diff: dict[str, Any]
    energy_balance_error_diff: dict[str, Any]
    energy_audit_status_diff: dict[str, Any]
    convergence_verdict_diff: dict[str, Any]
    deck_artifact_diff: dict[str, Any]
    evidence_artifact_diff: dict[str, Any]
    claim_impact: str


def build_case_comparison(
    packet_a: AcceptancePacket,
    packet_b: AcceptancePacket,
) -> CaseComparison:
    """Build a structured side-by-side diff between two packets."""
    comparison = CaseComparison(
        case_a=packet_a.case_id,
        case_b=packet_b.case_id,
        generated_at_utc=datetime.now(UTC).isoformat(timespec="seconds"),
        claim_boundary=CLAIM_BOUNDARY,
        residual_velocity_diff=_residual_velocity_diff(packet_a, packet_b),
        perforation_marker_diff=_perforation_marker_diff(packet_a, packet_b),
        energy_balance_error_diff=_energy_balance_error_diff(packet_a, packet_b),
        energy_audit_status_diff=_energy_audit_status_diff(packet_a, packet_b),
        convergence_verdict_diff=_convergence_verdict_diff(packet_a, packet_b),
        deck_artifact_diff=_artifact_diff(packet_a.deck_artifacts, packet_b.deck_artifacts),
        evidence_artifact_diff=_artifact_diff(
            packet_a.evidence_artifacts, packet_b.evidence_artifacts
        ),
        claim_impact=CLAIM_IMPACT_DEFAULT,
    )
    _assert_no_overclaim(comparison)
    return comparison


def render_case_comparison_json(comparison: CaseComparison) -> str:
    """Return the comparison as a JSON string."""
    return json.dumps(_comparison_to_dict(comparison), indent=2, sort_keys=True)


# ---------------------------------------------------------------------
# Diff axes
# ---------------------------------------------------------------------


def _residual_velocity_diff(
    packet_a: AcceptancePacket, packet_b: AcceptancePacket
) -> dict[str, Any]:
    a = packet_a.ballistic_metrics_summary.get("residual_velocity_candidate_m_per_s")
    b = packet_b.ballistic_metrics_summary.get("residual_velocity_candidate_m_per_s")
    delta = None
    delta_pct = None
    if isinstance(a, int | float) and isinstance(b, int | float):
        delta = float(b) - float(a)
        if a != 0:
            delta_pct = (delta / float(a)) * 100.0
    return {"a": a, "b": b, "delta": delta, "delta_pct": delta_pct}


def _perforation_marker_diff(
    packet_a: AcceptancePacket, packet_b: AcceptancePacket
) -> dict[str, Any]:
    a = packet_a.ballistic_metrics_summary.get("perforation_marker")
    b = packet_b.ballistic_metrics_summary.get("perforation_marker")
    return {"a": a, "b": b, "same_marker": a == b and a is not None}


def _energy_balance_error_diff(
    packet_a: AcceptancePacket, packet_b: AcceptancePacket
) -> dict[str, Any]:
    a = packet_a.energy_audit_summary.get("energy_balance_error_pct")
    b = packet_b.energy_audit_summary.get("energy_balance_error_pct")
    delta_abs_pct = None
    if isinstance(a, int | float) and isinstance(b, int | float):
        delta_abs_pct = abs(float(b) - float(a))
    return {"a": a, "b": b, "delta_abs_pct": delta_abs_pct}


def _energy_audit_status_diff(
    packet_a: AcceptancePacket, packet_b: AcceptancePacket
) -> dict[str, Any]:
    a = packet_a.energy_audit_summary.get("status", "unavailable")
    b = packet_b.energy_audit_summary.get("status", "unavailable")
    return {
        "a": a,
        "b": b,
        "both_closed": a == "closed_aggregate" and b == "closed_aggregate",
        "same_status": a == b,
    }


def _convergence_verdict_diff(
    packet_a: AcceptancePacket, packet_b: AcceptancePacket
) -> dict[str, Any]:
    a = packet_a.convergence_study_summary.get("combined_verdict", "insufficient_data")
    b = packet_b.convergence_study_summary.get("combined_verdict", "insufficient_data")
    return {"a": a, "b": b, "same_verdict": a == b}


def _artifact_diff(
    a_list: list[AcceptanceArtifact], b_list: list[AcceptanceArtifact]
) -> dict[str, Any]:
    """Compare two artifact lists by `kind`.

    Returns four buckets:
    * a_only: kinds present in A but not B
    * b_only: kinds present in B but not A
    * shared: kinds present in both with the SAME sha256
    * hash_changed: kinds present in both with DIFFERENT sha256
    """
    a_by_kind = {art.kind: art for art in a_list}
    b_by_kind = {art.kind: art for art in b_list}
    a_only = sorted(k for k in a_by_kind if k not in b_by_kind)
    b_only = sorted(k for k in b_by_kind if k not in a_by_kind)
    shared: list[str] = []
    hash_changed: list[dict[str, Any]] = []
    for kind in sorted(set(a_by_kind) & set(b_by_kind)):
        if a_by_kind[kind].sha256 == b_by_kind[kind].sha256:
            shared.append(kind)
        else:
            hash_changed.append(
                {
                    "kind": kind,
                    "a_sha256": a_by_kind[kind].sha256,
                    "b_sha256": b_by_kind[kind].sha256,
                }
            )
    return {
        "a_only": a_only,
        "b_only": b_only,
        "shared": shared,
        "hash_changed": hash_changed,
    }


# ---------------------------------------------------------------------
# Serialization + guard
# ---------------------------------------------------------------------


def _comparison_to_dict(comparison: CaseComparison) -> dict[str, Any]:
    return {
        "schema_version": CASE_COMPARISON_SCHEMA_VERSION,
        "case_a": comparison.case_a,
        "case_b": comparison.case_b,
        "generated_at_utc": comparison.generated_at_utc,
        "claim_boundary": comparison.claim_boundary,
        "residual_velocity_diff": comparison.residual_velocity_diff,
        "perforation_marker_diff": comparison.perforation_marker_diff,
        "energy_balance_error_diff": comparison.energy_balance_error_diff,
        "energy_audit_status_diff": comparison.energy_audit_status_diff,
        "convergence_verdict_diff": comparison.convergence_verdict_diff,
        "deck_artifact_diff": comparison.deck_artifact_diff,
        "evidence_artifact_diff": comparison.evidence_artifact_diff,
        "claim_impact": comparison.claim_impact,
    }


def _assert_no_overclaim(comparison: CaseComparison) -> None:
    forbidden = (
        "validated against",
        "perforation completed",
        "bullet-through-steel complete",
        "validated physics",
    )
    haystack = json.dumps(_comparison_to_dict(comparison), default=str).lower()
    for token in forbidden:
        if token in haystack:
            raise ValueError(f"Case comparison contains forbidden positive claim: {token!r}")
