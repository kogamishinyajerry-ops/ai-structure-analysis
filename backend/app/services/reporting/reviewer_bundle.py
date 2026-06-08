"""Tier 1 reviewer bundle exporter (FM-04a Phase 4 C).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Builds an in-memory zip containing per-case artifacts plus a top-level
``BUNDLE_MANIFEST.json``. Output is **NOT** a sealed FM-04b P8 packet —
it is a Tier 1 candidate bundle a reviewer can hand off / archive
while signed-validation prerequisites remain blocked.

Per case the bundle includes (only files that exist):
  * `<case-id>/<case-id>_acceptance_packet.json`
  * `<case-id>/<case-id>_convergence_study.json` (when present)
  * `<case-id>/<case-id>_Tier1_candidate_report.md`
  * `<case-id>/<case-id>_completeness_scorecard.json`

Top-level `BUNDLE_MANIFEST.json` lists every member case with the
Tier 1 banner + claim boundary + tier2_blockers_remaining +
generated_at_utc.

Forbidden wording is audited at build time across the manifest +
every per-case rendered text artifact; the bundle refuses to emit
``validated against``, ``benchmark agreement``, ``signed validation``,
``perforation completed``, ``bullet-through-steel complete``, or
``validated physics`` in any member.
"""

from __future__ import annotations

import io
import json
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ._schema_versions import REVIEWER_BUNDLE_MANIFEST_SCHEMA_VERSION
from .acceptance_packet import (
    CLAIM_BOUNDARY,
    DEFAULT_TIER2_BLOCKERS_REMAINING,
    AcceptancePacketInputs,
    build_acceptance_packet,
    render_acceptance_packet_json,
)
from .case_completeness import (
    CaseCompletenessInputs,
    render_case_completeness_json,
    score_case_completeness,
)
from .tier1_candidate_report import (
    Tier1CandidateReportInputs,
    build_tier1_candidate_report,
    render_tier1_report_markdown,
)

CLAIM_TIER = "Tier 1 engineering candidate"
BUNDLE_MANIFEST_CLAIM_IMPACT = (
    "Tier 1 candidate reviewer bundle only; not signed validation; not "
    "benchmark agreement; not a sealed FM-04b P8 packet. Every per-case "
    "artifact preserves the Tier 1 boundary."
)


@dataclass(frozen=True)
class ReviewerBundleInputs:
    """Per-case input bundle. Mirrors the shape used by the route layer."""

    case_id: str
    starter_deck_path: Path | None = None
    engine_deck_path: Path | None = None
    ballistic_metrics_path: Path | None = None
    convergence_study_path: Path | None = None
    animation_manifest_path: Path | None = None
    result_mesh_path: Path | None = None
    blueprint_image_path: Path | None = None
    generator_script_path: Path | None = None
    notes_path: Path | None = None


def build_reviewer_bundle(
    cases: list[ReviewerBundleInputs], repo_root: Path | None = None
) -> bytes:
    """Build an in-memory Tier 1 reviewer bundle zip across `cases`.

    Returns the zip bytes; never writes to disk (caller decides).
    """
    if not cases:
        raise ValueError("reviewer bundle requires at least one case")

    repo_root_effective = repo_root or Path.cwd()
    buffer = io.BytesIO()
    manifest_cases: list[dict[str, Any]] = []

    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for case in cases:
            if case.ballistic_metrics_path is None or not case.ballistic_metrics_path.is_file():
                raise FileNotFoundError(
                    f"reviewer bundle: ballistic_metrics.json missing for case {case.case_id!r}"
                )
            members = _emit_case_members(case, repo_root_effective, zf)
            manifest_cases.append(members)

        manifest = {
            "schema_version": REVIEWER_BUNDLE_MANIFEST_SCHEMA_VERSION,
            "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "claim_tier": CLAIM_TIER,
            "claim_boundary": CLAIM_BOUNDARY,
            "cohort_count": len(cases),
            "cases": manifest_cases,
            "tier2_blockers_remaining": list(DEFAULT_TIER2_BLOCKERS_REMAINING),
            "claim_impact": BUNDLE_MANIFEST_CLAIM_IMPACT,
        }
        manifest_json = json.dumps(manifest, indent=2, sort_keys=True)
        _assert_no_overclaim_text("BUNDLE_MANIFEST.json", manifest_json)
        zf.writestr("BUNDLE_MANIFEST.json", manifest_json)

    return buffer.getvalue()


def reviewer_bundle_filename(case_count: int) -> str:
    """Canonical filename for a reviewer bundle download."""
    return f"tier1_reviewer_bundle_{case_count}cases.zip"


# ---------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------


def _emit_case_members(
    case: ReviewerBundleInputs, repo_root: Path, zf: zipfile.ZipFile
) -> dict[str, Any]:
    """Build + write per-case bundle members; return manifest entry."""
    case_dir = case.case_id

    # 1. Acceptance packet JSON.
    packet = build_acceptance_packet(
        AcceptancePacketInputs(
            case_id=case.case_id,
            ballistic_metrics_path=case.ballistic_metrics_path,
            convergence_study_path=case.convergence_study_path,
            starter_deck_path=case.starter_deck_path,
            engine_deck_path=case.engine_deck_path,
            blueprint_image_path=case.blueprint_image_path,
            animation_manifest_path=case.animation_manifest_path,
            result_mesh_path=case.result_mesh_path,
            repo_root=repo_root,
        )
    )
    packet_text = render_acceptance_packet_json(packet)
    packet_name = f"{case_dir}/{case.case_id}_acceptance_packet.json"
    _assert_no_overclaim_text(packet_name, packet_text)
    zf.writestr(packet_name, packet_text)

    # 2. Convergence study JSON (passthrough if present).
    convergence_present = (
        case.convergence_study_path is not None and case.convergence_study_path.is_file()
    )
    convergence_name: str | None = None
    if convergence_present:
        convergence_text = case.convergence_study_path.read_text(encoding="utf-8")
        convergence_name = f"{case_dir}/{case.case_id}_convergence_study.json"
        _assert_no_overclaim_text(convergence_name, convergence_text)
        zf.writestr(convergence_name, convergence_text)

    # 3. Tier 1 markdown report.
    report = build_tier1_candidate_report(
        Tier1CandidateReportInputs(
            case_id=case.case_id,
            ballistic_metrics_path=case.ballistic_metrics_path,
            convergence_study_path=case.convergence_study_path,
            blueprint_image_path=case.blueprint_image_path,
            animation_manifest_path=case.animation_manifest_path,
            result_mesh_path=case.result_mesh_path,
            repo_root=repo_root,
        )
    )
    report_text = render_tier1_report_markdown(report)
    report_name = f"{case_dir}/{case.case_id}_Tier1_candidate_report.md"
    _assert_no_overclaim_text(report_name, report_text)
    zf.writestr(report_name, report_text)

    # 4. Completeness scorecard JSON.
    score = score_case_completeness(
        CaseCompletenessInputs(
            case_id=case.case_id,
            starter_deck_path=case.starter_deck_path,
            engine_deck_path=case.engine_deck_path,
            ballistic_metrics_path=case.ballistic_metrics_path,
            convergence_study_path=case.convergence_study_path,
            animation_manifest_path=case.animation_manifest_path,
            result_mesh_path=case.result_mesh_path,
            generator_script_path=case.generator_script_path,
            notes_path=case.notes_path,
        )
    )
    score_text = render_case_completeness_json(score)
    score_name = f"{case_dir}/{case.case_id}_completeness_scorecard.json"
    _assert_no_overclaim_text(score_name, score_text)
    zf.writestr(score_name, score_text)

    return {
        "case_id": case.case_id,
        "members": {
            "acceptance_packet": packet_name,
            "convergence_study": convergence_name,
            "tier1_report_md": report_name,
            "completeness_scorecard": score_name,
        },
        "completeness_score": score.score,
        "completeness_score_max": score.score_max,
    }


def _assert_no_overclaim_text(member_name: str, text: str) -> None:
    forbidden = (
        "validated against",
        "perforation completed",
        "bullet-through-steel complete",
        "validated physics",
    )
    haystack = text.lower()
    for token in forbidden:
        if token in haystack:
            raise ValueError(
                f"reviewer bundle member {member_name!r} contains forbidden "
                f"positive claim: {token!r}"
            )
