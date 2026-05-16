"""Tier 1 candidate trust score provenance trace (FM-04a Phase 8 C).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Given a case + snapshot label, walk back to every input file SHA
that fed into the trust score arithmetic for that snapshot. Plus
the formula version. Plus the recomputed score + axis breakdown.

A reviewer reading the provenance gets a deterministic answer to
"exactly what produced this 87?" — input bytes are frozen snapshot
bytes (not live evidence), so the SHA list is reproducible.

This is the deep-dive surface, not the primary UI. The main
reviewer journey reads the gauge / timeline / alerts / narrative;
provenance is what they consult when they want to audit the
score's lineage.

Forbidden wording (per ADR-023 + ADR-024 lite): no ``benchmark
agreement``, no ``signed validation``, no ``perforation completed``,
no ``bullet-through-steel complete``, no ``validated physics``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from ._schema_versions import (
    TRUST_SCORE_FORMULA_VERSION,
    TRUST_SCORE_PROVENANCE_SCHEMA_VERSION,
)
from .acceptance_packet import CLAIM_BOUNDARY
from .cohort_snapshot import SNAPSHOT_MANIFEST_FILENAME, snapshots_root
from .trust_score_timeline import _build_point

CLAIM_TIER = "Tier 1 engineering candidate"
CLAIM_IMPACT_DEFAULT = (
    "Tier 1 candidate trust score provenance trace only; not signed "
    "validation; not benchmark agreement. The provenance lists "
    "input file SHAs + formula version for a deterministic recompute "
    "of the score; it does NOT authorize Tier 2 promotion or "
    "substitute for the FM-04b sealed packet."
)

# Per-axis input kinds the provenance walks. Tuple is the SSOT for both
# the dict key order and the on-disk subdirectory naming.
PROVENANCE_INPUT_KINDS: tuple[str, ...] = (
    "metrics",
    "convergence",
    "completeness",
    "reproducibility",
)


@dataclass(frozen=True)
class ProvenanceInput:
    kind: str
    path: str
    present: bool
    sha256: str | None


@dataclass(frozen=True)
class ProvenanceAxis:
    axis: str
    weighted: int


@dataclass(frozen=True)
class TrustScoreProvenanceReport:
    schema_version: str
    formula_version: str
    case_id: str
    snapshot_label: str
    generated_at_utc: str
    trust_score: int | None
    axes: tuple[ProvenanceAxis, ...]
    inputs: tuple[ProvenanceInput, ...]
    claim_tier: str
    claim_boundary: str
    claim_impact: str


class ProvenanceSnapshotNotFound(LookupError):
    """Raised when ``snapshot_label`` does not exist under ``reports/snapshots/``."""


def build_trust_score_provenance(
    case_id: str,
    snapshot_label: str,
    *,
    repo_root: Path,
    now_utc: datetime | None = None,
) -> TrustScoreProvenanceReport:
    """Build a provenance report for one (case, snapshot) pair.

    Raises ``ValueError`` for empty / signed-registry case_id or
    invalid snapshot label shape.
    Raises ``ProvenanceSnapshotNotFound`` if the snapshot label has no
    on-disk manifest (so the route layer can surface 404).
    """
    if not case_id:
        raise ValueError("Provenance requires a non-empty case_id")
    if not snapshot_label:
        raise ValueError("Provenance requires a non-empty snapshot_label")

    snap_dir = (snapshots_root(repo_root) / snapshot_label).resolve()
    manifest_path = snap_dir / SNAPSHOT_MANIFEST_FILENAME
    if not manifest_path.is_file():
        raise ProvenanceSnapshotNotFound(
            f"snapshot {snapshot_label!r} not found under reports/snapshots/"
        )

    inputs = tuple(_walk_inputs(case_id, snap_dir))
    point = _build_point(case_id, snap_dir)
    axes = (
        tuple()
        if point is None
        else (
            ProvenanceAxis(axis="completeness", weighted=point.completeness_weighted),
            ProvenanceAxis(axis="convergence", weighted=point.convergence_weighted),
            ProvenanceAxis(axis="energy_audit", weighted=point.energy_audit_weighted),
            ProvenanceAxis(
                axis="reproducibility", weighted=point.reproducibility_weighted
            ),
        )
    )

    generated_at = (now_utc or datetime.now(UTC)).isoformat(timespec="seconds")
    report = TrustScoreProvenanceReport(
        schema_version=TRUST_SCORE_PROVENANCE_SCHEMA_VERSION,
        formula_version=TRUST_SCORE_FORMULA_VERSION,
        case_id=case_id,
        snapshot_label=snapshot_label,
        generated_at_utc=generated_at,
        trust_score=None if point is None else point.trust_score,
        axes=axes,
        inputs=inputs,
        claim_tier=CLAIM_TIER,
        claim_boundary=CLAIM_BOUNDARY,
        claim_impact=CLAIM_IMPACT_DEFAULT,
    )
    _assert_no_overclaim(report)
    return report


def render_trust_score_provenance_json(report: TrustScoreProvenanceReport) -> str:
    return json.dumps(_report_to_dict(report), indent=2, sort_keys=True)


def _walk_inputs(case_id: str, snap_dir: Path):
    for kind in PROVENANCE_INPUT_KINDS:
        path = snap_dir / kind / f"{case_id}.json"
        rel = f"{kind}/{case_id}.json"
        if path.is_file():
            data = path.read_bytes()
            yield ProvenanceInput(
                kind=kind,
                path=rel,
                present=True,
                sha256=hashlib.sha256(data).hexdigest(),
            )
        else:
            yield ProvenanceInput(kind=kind, path=rel, present=False, sha256=None)


def _report_to_dict(report: TrustScoreProvenanceReport) -> dict[str, object]:
    return {
        "schema_version": report.schema_version,
        "formula_version": report.formula_version,
        "case_id": report.case_id,
        "snapshot_label": report.snapshot_label,
        "generated_at_utc": report.generated_at_utc,
        "trust_score": report.trust_score,
        "axes": [
            {"axis": a.axis, "weighted": a.weighted} for a in report.axes
        ],
        "inputs": [
            {
                "kind": i.kind,
                "path": i.path,
                "present": i.present,
                "sha256": i.sha256,
            }
            for i in report.inputs
        ],
        "claim_tier": report.claim_tier,
        "claim_boundary": report.claim_boundary,
        "claim_impact": report.claim_impact,
    }


# Envelope-narrowed forbidden list (same Phase 7 B / 8 B pattern):
# Tier 1 ``claim_impact`` legitimately contains "signed validation" /
# "benchmark agreement" inside disclaimer text in compound sentences,
# so the envelope audit excludes those two tokens; the wider 6-token
# notes audit was already enforced at the source (signoff record write).

_ENVELOPE_FORBIDDEN_TOKENS: tuple[str, ...] = (
    "validated against",
    "perforation completed",
    "bullet-through-steel complete",
    "validated physics",
)


def _assert_no_overclaim(report: TrustScoreProvenanceReport) -> None:
    haystack = json.dumps(_report_to_dict(report)).lower()
    for token in _ENVELOPE_FORBIDDEN_TOKENS:
        start = 0
        while True:
            idx = haystack.find(token, start)
            if idx == -1:
                break
            prefix = haystack[max(0, idx - 4) : idx]
            if not prefix.endswith("not "):
                raise ValueError(
                    f"Trust score provenance contains forbidden positive "
                    f"claim {token!r} outside the `not <claim>` disclaimer form."
                )
            start = idx + len(token)
