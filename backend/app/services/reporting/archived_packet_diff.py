"""Tier 1 archived acceptance packet diff (FM-04a Phase 4 D).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Reads two archived ``<case>_acceptance_packet.json`` files on disk and
emits a structured diff payload using the same axis vocabulary as the
Phase 3 B case-comparison builder, plus an ``archive_provenance``
block per side (file path relative to repo root, sha256, mtime,
generated_at_utc lifted from the packet body).

Validates that **both** packets carry the Tier 1
``claim_boundary`` field. A file that does not carry Tier 1 wording
is rejected at read time — the diff is strictly Tier 1 candidate
vs Tier 1 candidate.

The diff is **archive-vs-archive only**: it does not re-run any
builders or touch live evidence. Reviewer uses this to audit
provenance ("did the manifest I saved last week still match the
current state?") without re-generating.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ._schema_versions import ARCHIVED_PACKET_DIFF_SCHEMA_VERSION
from .acceptance_packet import CLAIM_BOUNDARY

CLAIM_IMPACT_DEFAULT = (
    "Tier 1 candidate archived-acceptance-packet diff only; not signed "
    "validation; not benchmark agreement; not a comparison against "
    "experimental benchmark data. Both inputs are archived Tier 1 "
    "candidate manifests."
)


@dataclass(frozen=True)
class ArchiveProvenance:
    """Provenance metadata for one archived packet."""

    relpath: str
    sha256: str
    mtime_utc: str
    case_id: str
    generated_at_utc: str
    claim_tier: str
    claim_boundary: str


@dataclass(frozen=True)
class ArchivedPacketDiff:
    """Structured diff over two archived Tier 1 acceptance packets."""

    generated_at_utc: str
    claim_boundary: str
    archive_a: ArchiveProvenance
    archive_b: ArchiveProvenance
    residual_velocity_diff: dict[str, Any]
    perforation_marker_diff: dict[str, Any]
    energy_balance_error_diff: dict[str, Any]
    energy_audit_status_diff: dict[str, Any]
    convergence_verdict_diff: dict[str, Any]
    artifact_hash_diff: dict[str, Any]
    same_case: bool
    claim_impact: str


def diff_archived_packets(
    path_a: Path, path_b: Path, *, repo_root: Path | None = None
) -> ArchivedPacketDiff:
    """Diff two archived Tier 1 acceptance packet JSON files."""
    provenance_a, payload_a = _load_archived_packet(path_a, repo_root)
    provenance_b, payload_b = _load_archived_packet(path_b, repo_root)

    diff = ArchivedPacketDiff(
        generated_at_utc=datetime.now(UTC).isoformat(timespec="seconds"),
        claim_boundary=CLAIM_BOUNDARY,
        archive_a=provenance_a,
        archive_b=provenance_b,
        residual_velocity_diff=_residual_velocity_diff(payload_a, payload_b),
        perforation_marker_diff=_perforation_marker_diff(payload_a, payload_b),
        energy_balance_error_diff=_energy_balance_error_diff(payload_a, payload_b),
        energy_audit_status_diff=_energy_audit_status_diff(payload_a, payload_b),
        convergence_verdict_diff=_convergence_verdict_diff(payload_a, payload_b),
        artifact_hash_diff=_artifact_hash_diff(payload_a, payload_b),
        same_case=provenance_a.case_id == provenance_b.case_id,
        claim_impact=CLAIM_IMPACT_DEFAULT,
    )
    _assert_no_overclaim(diff)
    return diff


def render_archived_packet_diff_json(diff: ArchivedPacketDiff) -> str:
    """Return the archived packet diff as a JSON string."""
    return json.dumps(_diff_to_dict(diff), indent=2, sort_keys=True)


# ---------------------------------------------------------------------
# Reader + provenance
# ---------------------------------------------------------------------


def _load_archived_packet(
    path: Path, repo_root: Path | None
) -> tuple[ArchiveProvenance, dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"archived packet not found: {path}")
    raw_bytes = path.read_bytes()
    try:
        payload = json.loads(raw_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"archived packet {path} is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"archived packet {path} did not decode to an object")

    claim_boundary = str(payload.get("claim_boundary", ""))
    if "tier1_engineering_candidate" not in claim_boundary:
        raise ValueError(
            f"archived packet {path} is not a Tier 1 candidate manifest "
            "(missing 'tier1_engineering_candidate' in claim_boundary)"
        )

    case_id = payload.get("case_id")
    if not isinstance(case_id, str) or not case_id:
        raise ValueError(f"archived packet {path} is missing case_id")

    relpath = _relpath(path, repo_root)
    sha = hashlib.sha256(raw_bytes).hexdigest()
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).isoformat(timespec="seconds")
    return (
        ArchiveProvenance(
            relpath=relpath,
            sha256=sha,
            mtime_utc=mtime,
            case_id=case_id,
            generated_at_utc=str(payload.get("generated_at_utc", "")),
            claim_tier=str(payload.get("claim_tier", "")),
            claim_boundary=claim_boundary,
        ),
        payload,
    )


def _relpath(path: Path, repo_root: Path | None) -> str:
    if repo_root is None:
        return str(path)
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path)


# ---------------------------------------------------------------------
# Diff axes (mirror Phase 3 B case_comparison)
# ---------------------------------------------------------------------


def _residual_velocity_diff(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    a_val = (a.get("ballistic_metrics_summary") or {}).get("residual_velocity_candidate_m_per_s")
    b_val = (b.get("ballistic_metrics_summary") or {}).get("residual_velocity_candidate_m_per_s")
    delta = None
    delta_pct = None
    if isinstance(a_val, int | float) and isinstance(b_val, int | float):
        delta = float(b_val) - float(a_val)
        if a_val != 0:
            delta_pct = (delta / float(a_val)) * 100.0
    return {"a": a_val, "b": b_val, "delta": delta, "delta_pct": delta_pct}


def _perforation_marker_diff(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    a_val = (a.get("ballistic_metrics_summary") or {}).get("perforation_marker")
    b_val = (b.get("ballistic_metrics_summary") or {}).get("perforation_marker")
    return {"a": a_val, "b": b_val, "same_marker": a_val == b_val and a_val is not None}


def _energy_balance_error_diff(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    a_val = (a.get("energy_audit_summary") or {}).get("energy_balance_error_pct")
    b_val = (b.get("energy_audit_summary") or {}).get("energy_balance_error_pct")
    delta_abs_pct = None
    if isinstance(a_val, int | float) and isinstance(b_val, int | float):
        delta_abs_pct = abs(float(b_val) - float(a_val))
    return {"a": a_val, "b": b_val, "delta_abs_pct": delta_abs_pct}


def _energy_audit_status_diff(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    a_val = (a.get("energy_audit_summary") or {}).get("status", "unavailable")
    b_val = (b.get("energy_audit_summary") or {}).get("status", "unavailable")
    return {
        "a": a_val,
        "b": b_val,
        "both_closed": a_val == "closed_aggregate" and b_val == "closed_aggregate",
        "same_status": a_val == b_val,
    }


def _convergence_verdict_diff(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    a_val = (a.get("convergence_study_summary") or {}).get("combined_verdict", "insufficient_data")
    b_val = (b.get("convergence_study_summary") or {}).get("combined_verdict", "insufficient_data")
    return {"a": a_val, "b": b_val, "same_verdict": a_val == b_val}


def _artifact_hash_diff(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """Compare archived deck + evidence artifact hashes by kind."""
    a_artifacts = (a.get("deck_artifacts") or []) + (a.get("evidence_artifacts") or [])
    b_artifacts = (b.get("deck_artifacts") or []) + (b.get("evidence_artifacts") or [])
    a_by_kind = {item.get("kind"): item for item in a_artifacts if item.get("kind")}
    b_by_kind = {item.get("kind"): item for item in b_artifacts if item.get("kind")}
    a_only = sorted(k for k in a_by_kind if k not in b_by_kind)
    b_only = sorted(k for k in b_by_kind if k not in a_by_kind)
    shared: list[str] = []
    hash_changed: list[dict[str, Any]] = []
    for kind in sorted(set(a_by_kind) & set(b_by_kind)):
        if a_by_kind[kind].get("sha256") == b_by_kind[kind].get("sha256"):
            shared.append(kind)
        else:
            hash_changed.append(
                {
                    "kind": kind,
                    "a_sha256": a_by_kind[kind].get("sha256"),
                    "b_sha256": b_by_kind[kind].get("sha256"),
                }
            )
    return {
        "a_only": a_only,
        "b_only": b_only,
        "shared": shared,
        "hash_changed": hash_changed,
    }


# ---------------------------------------------------------------------
# Serialization + audit
# ---------------------------------------------------------------------


def _provenance_to_dict(p: ArchiveProvenance) -> dict[str, Any]:
    return {
        "relpath": p.relpath,
        "sha256": p.sha256,
        "mtime_utc": p.mtime_utc,
        "case_id": p.case_id,
        "generated_at_utc": p.generated_at_utc,
        "claim_tier": p.claim_tier,
        "claim_boundary": p.claim_boundary,
    }


def _diff_to_dict(diff: ArchivedPacketDiff) -> dict[str, Any]:
    return {
        "schema_version": ARCHIVED_PACKET_DIFF_SCHEMA_VERSION,
        "generated_at_utc": diff.generated_at_utc,
        "claim_boundary": diff.claim_boundary,
        "archive_a": _provenance_to_dict(diff.archive_a),
        "archive_b": _provenance_to_dict(diff.archive_b),
        "residual_velocity_diff": diff.residual_velocity_diff,
        "perforation_marker_diff": diff.perforation_marker_diff,
        "energy_balance_error_diff": diff.energy_balance_error_diff,
        "energy_audit_status_diff": diff.energy_audit_status_diff,
        "convergence_verdict_diff": diff.convergence_verdict_diff,
        "artifact_hash_diff": diff.artifact_hash_diff,
        "same_case": diff.same_case,
        "claim_impact": diff.claim_impact,
    }


def _assert_no_overclaim(diff: ArchivedPacketDiff) -> None:
    forbidden = (
        "validated against",
        "perforation completed",
        "bullet-through-steel complete",
        "validated physics",
    )
    haystack = json.dumps(_diff_to_dict(diff), default=str).lower()
    for token in forbidden:
        if token in haystack:
            raise ValueError(f"Archived packet diff contains forbidden positive claim: {token!r}")
