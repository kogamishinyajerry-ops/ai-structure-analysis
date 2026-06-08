"""Tier 1 candidate acceptance evidence packet (FM-04a Phase 3 A).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Machine-readable counterpart to the Phase 2 E Tier 1 candidate report
(markdown + DOCX). The acceptance packet is **NOT** a Tier 2 sealed
bundle — it is a Tier 1 candidate manifest a reviewer can hand off /
archive while signed-validation prerequisites remain blocked.

Distinction from FM-04b P8 sealed packet:

* Phase 3 A acceptance packet: Tier 1 candidate JSON, lists artifact
  hashes + claim boundary + assumptions + limitations + blockers.
  Re-buildable from on-disk evidence at any time.
* FM-04b P8 sealed packet: SHA freeze, manifest of manifests, immutable
  bundle, paired with an independent reviewer signoff. Tier 2 only.
  NOT produced by this module.

Forbidden wording: ``validated against``, ``benchmark agreement``,
``signed validation``, ``perforation completed``,
``bullet-through-steel complete``, ``validated physics``. The builder
asserts the rendered packet stays clean against these positive
claims; ``not <claim>`` disclaimer forms remain allowed.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ._schema_versions import ACCEPTANCE_PACKET_SCHEMA_VERSION

CLAIM_TIER = "Tier 1 engineering candidate"
CLAIM_BOUNDARY = "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"
CLAIM_IMPACT_DEFAULT = (
    "Tier 1 candidate acceptance evidence packet only; not signed validation; "
    "not benchmark agreement; not a sealed Tier 2 bundle. The FM-04b P8 sealed "
    "packet remains gated by ADR-024 (full) + independent reviewer signoff."
)

DEFAULT_TIER2_BLOCKERS_REMAINING: tuple[str, ...] = (
    "ADR-024 (full) — locked benchmark case + tolerance + uncertainty interval",
    "benchmark_comparison_candidate.json schema + producer (FM-04b P7)",
    "sealed packet: SHA freeze + manifest of manifests (FM-04b P8)",
    "independent reviewer signoff path (FM-04b P8)",
    "user milestone-experience acceptance (FM-04b P9)",
    "^GS-\\d{3}$ registry flip from -candidate (FM-04b P9)",
    "Linear / Notion mirror writes (user-controlled)",
    "per-term plastic / contact / hourglass energy breakdown via /TH/PART",
)


@dataclass(frozen=True)
class AcceptanceArtifact:
    """One artifact reference in the acceptance packet."""

    relpath: str
    sha256: str | None
    bytes_count: int | None
    kind: str  # e.g. "deck" | "ballistic_metrics" | "convergence_study" | "blueprint"


@dataclass(frozen=True)
class AcceptancePacket:
    """Tier 1 candidate acceptance evidence packet."""

    case_id: str
    generated_at_utc: str
    claim_tier: str
    claim_boundary: str
    deck_artifacts: list[AcceptanceArtifact]
    evidence_artifacts: list[AcceptanceArtifact]
    visualization_artifacts: list[AcceptanceArtifact]
    ballistic_metrics_summary: dict[str, Any]
    energy_audit_summary: dict[str, Any]
    convergence_study_summary: dict[str, Any]
    assumptions: list[str]
    limitations: list[str]
    tier2_blockers_remaining: list[str]
    claim_impact: str


@dataclass
class AcceptancePacketInputs:
    """Builder inputs.

    Paths are absolute or repo-rooted. Optional artifacts may be ``None``
    when their evidence is not yet produced; the builder surfaces empty
    artifact lists rather than failing.
    """

    case_id: str
    ballistic_metrics_path: Path
    convergence_study_path: Path | None = None
    starter_deck_path: Path | None = None
    engine_deck_path: Path | None = None
    blueprint_image_path: Path | None = None
    animation_manifest_path: Path | None = None
    result_mesh_path: Path | None = None
    repo_root: Path | None = None
    additional_assumptions: tuple[str, ...] = field(default_factory=tuple)


def build_acceptance_packet(inputs: AcceptancePacketInputs) -> AcceptancePacket:
    """Build the Tier 1 candidate acceptance evidence packet."""
    if not inputs.ballistic_metrics_path.is_file():
        raise FileNotFoundError(
            f"ballistic_metrics.json not found at {inputs.ballistic_metrics_path}"
        )
    repo_root = inputs.repo_root or Path.cwd()
    metrics_raw = json.loads(inputs.ballistic_metrics_path.read_text(encoding="utf-8"))
    convergence_raw: dict[str, Any] | None = None
    if inputs.convergence_study_path is not None and inputs.convergence_study_path.is_file():
        convergence_raw = json.loads(inputs.convergence_study_path.read_text(encoding="utf-8"))

    deck_artifacts: list[AcceptanceArtifact] = []
    for path, kind in (
        (inputs.starter_deck_path, "deck_starter"),
        (inputs.engine_deck_path, "deck_engine"),
    ):
        if path is not None:
            deck_artifacts.append(_hash_artifact(path, repo_root, kind))

    evidence_artifacts: list[AcceptanceArtifact] = [
        _hash_artifact(inputs.ballistic_metrics_path, repo_root, "ballistic_metrics"),
    ]
    if inputs.convergence_study_path is not None:
        evidence_artifacts.append(
            _hash_artifact(inputs.convergence_study_path, repo_root, "convergence_study")
        )

    visualization_artifacts: list[AcceptanceArtifact] = []
    for path, kind in (
        (inputs.blueprint_image_path, "blueprint"),
        (inputs.animation_manifest_path, "animation_manifest"),
        (inputs.result_mesh_path, "result_mesh"),
    ):
        if path is not None:
            visualization_artifacts.append(_hash_artifact(path, repo_root, kind))

    packet = AcceptancePacket(
        case_id=inputs.case_id,
        generated_at_utc=datetime.now(UTC).isoformat(timespec="seconds"),
        claim_tier=CLAIM_TIER,
        claim_boundary=CLAIM_BOUNDARY,
        deck_artifacts=deck_artifacts,
        evidence_artifacts=evidence_artifacts,
        visualization_artifacts=visualization_artifacts,
        ballistic_metrics_summary=_summarize_ballistic(metrics_raw),
        energy_audit_summary=_summarize_energy(metrics_raw),
        convergence_study_summary=_summarize_convergence(convergence_raw),
        assumptions=list(_default_assumptions()) + list(inputs.additional_assumptions),
        limitations=list(_default_limitations()),
        tier2_blockers_remaining=list(DEFAULT_TIER2_BLOCKERS_REMAINING),
        claim_impact=CLAIM_IMPACT_DEFAULT,
    )
    _assert_no_overclaim(packet)
    return packet


def render_acceptance_packet_json(packet: AcceptancePacket) -> str:
    """Return the acceptance packet as a JSON string."""
    return json.dumps(_packet_to_dict(packet), indent=2, sort_keys=True)


def write_acceptance_packet(
    packet: AcceptancePacket,
    output_dir: Path | str,
) -> Path:
    """Write `<case-id>_acceptance_packet.json` under `output_dir`."""
    out_dir = Path(output_dir)
    _assert_not_in_golden_samples(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{packet.case_id}_acceptance_packet.json"
    out_path.write_text(render_acceptance_packet_json(packet), encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------


def _hash_artifact(path: Path, repo_root: Path, kind: str) -> AcceptanceArtifact:
    if not path.is_file():
        return AcceptanceArtifact(
            relpath=_relpath(path, repo_root),
            sha256=None,
            bytes_count=None,
            kind=kind,
        )
    raw = path.read_bytes()
    return AcceptanceArtifact(
        relpath=_relpath(path, repo_root),
        sha256=hashlib.sha256(raw).hexdigest(),
        bytes_count=len(raw),
        kind=kind,
    )


def _relpath(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path)


def _summarize_ballistic(metrics: dict[str, Any]) -> dict[str, Any]:
    crossing = metrics.get("crossing_evidence") or {}
    return {
        "perforation_marker": metrics.get("perforation_marker"),
        "projectile_initial_velocity_m_per_s": metrics.get("projectile_initial_velocity_m_per_s"),
        "residual_velocity_candidate_m_per_s": metrics.get("residual_velocity_candidate_m_per_s"),
        "front_face_crossed": crossing.get("front_face_crossed"),
        "back_face_crossed": crossing.get("back_face_crossed"),
        "first_back_face_crossing_t_s": crossing.get("first_back_face_crossing_t_s"),
    }


def _summarize_energy(metrics: dict[str, Any]) -> dict[str, Any]:
    audit = metrics.get("energy_audit") or metrics.get("partial_energy_audit") or {}
    return {
        "status": audit.get("status", "unavailable"),
        "initial_kinetic_energy_j": audit.get("initial_kinetic_energy_j"),
        "residual_kinetic_energy_j": audit.get("residual_kinetic_energy_j"),
        "aggregate_internal_energy_j": audit.get("aggregate_internal_energy_j"),
        "external_work_j": audit.get("external_work_j"),
        "energy_balance_error_pct": audit.get("energy_balance_error_pct"),
        "breakdown_status": audit.get("breakdown_status", "unavailable"),
        "missing_terms": audit.get("missing_terms", []),
    }


def _summarize_convergence(
    payload: dict[str, Any] | None,
) -> dict[str, Any]:
    if payload is None:
        return {
            "status": "unavailable",
            "combined_verdict": "insufficient_data",
            "mesh_sweep_stability": "unknown",
            "dt_sweep_stability": "unknown",
            "row_count": 0,
        }
    mesh_sweep = payload.get("mesh_sweep") or {}
    dt_sweep = payload.get("dt_sweep") or {}
    return {
        "status": "available",
        "combined_verdict": payload.get("combined_verdict", "insufficient_data"),
        "mesh_sweep_stability": mesh_sweep.get("candidate_stability", "unknown"),
        "dt_sweep_stability": dt_sweep.get("candidate_stability", "unknown"),
        "row_count": payload.get("row_count", 0),
        "tolerance_pct": payload.get("tolerance_pct"),
    }


def _default_assumptions() -> tuple[str, ...]:
    return (
        "Projectile + plate material parameters per ADR-024 (lite) cite from "
        "Borvik 2002 Part II Table 2.",
        "Case is registered under `golden_samples/*-candidate/`; no "
        "`^GS-\\d{3}$` signed registry entry is referenced.",
        "Energy audit is aggregated into OpenRadioss `I-ENERGY` until "
        "`/TH/PART` or `/TH/MAT` cards are added to the starter.",
        "Values reported in the OpenRadioss deck unit system (kg/mm/ms in "
        "the GS-102-candidate family).",
    )


def _default_limitations() -> tuple[str, ...]:
    return (
        "Not signed validation. Not benchmark agreement. Not perforation completion.",
        "Acceptance packet is Tier 1 candidate manifest only; it is NOT a sealed FM-04b P8 packet.",
        "No comparison vs experimental data; reviewer must source benchmark "
        "claims from a separate Tier 2 path.",
        "No independent reviewer signoff attached; FM-04b P8 governs that gate.",
    )


def _packet_to_dict(packet: AcceptancePacket) -> dict[str, Any]:
    return {
        "schema_version": ACCEPTANCE_PACKET_SCHEMA_VERSION,
        "case_id": packet.case_id,
        "generated_at_utc": packet.generated_at_utc,
        "claim_tier": packet.claim_tier,
        "claim_boundary": packet.claim_boundary,
        "deck_artifacts": [_artifact_to_dict(a) for a in packet.deck_artifacts],
        "evidence_artifacts": [_artifact_to_dict(a) for a in packet.evidence_artifacts],
        "visualization_artifacts": [_artifact_to_dict(a) for a in packet.visualization_artifacts],
        "ballistic_metrics_summary": packet.ballistic_metrics_summary,
        "energy_audit_summary": packet.energy_audit_summary,
        "convergence_study_summary": packet.convergence_study_summary,
        "assumptions": packet.assumptions,
        "limitations": packet.limitations,
        "tier2_blockers_remaining": packet.tier2_blockers_remaining,
        "claim_impact": packet.claim_impact,
    }


def _artifact_to_dict(artifact: AcceptanceArtifact) -> dict[str, Any]:
    return {
        "relpath": artifact.relpath,
        "sha256": artifact.sha256,
        "bytes": artifact.bytes_count,
        "kind": artifact.kind,
    }


def _assert_no_overclaim(packet: AcceptancePacket) -> None:
    forbidden = (
        "validated against",
        "perforation completed",
        "bullet-through-steel complete",
        "validated physics",
    )
    haystack = json.dumps(_packet_to_dict(packet), default=str).lower()
    for token in forbidden:
        if token in haystack:
            raise ValueError(f"Acceptance packet contains forbidden positive claim: {token!r}")


def _assert_not_in_golden_samples(output_dir: Path) -> None:
    resolved = output_dir.resolve()
    for parent in (resolved, *resolved.parents):
        if parent.name == "golden_samples":
            raise ValueError(
                "Acceptance packet refuses writes under golden_samples/**; "
                "use reports/ or project_state/<...>/ instead"
            )
