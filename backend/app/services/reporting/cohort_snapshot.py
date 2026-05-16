"""Tier 1 candidate cohort snapshot writer (FM-04a Phase 5 C).

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

A *cohort snapshot* is a time-stamped capture of the entire reviewer-
visible Tier 1 candidate state at one instant. Reviewers can list past
snapshots and diff two of them (Phase 5 D) to see drift over time.

Snapshot layout (always under ``reports/snapshots/<UTC>/``):

    reports/snapshots/2026-05-16T180000Z/
      SNAPSHOT_MANIFEST.json
      cohort_overview.json
      completeness/<case_id>.json
      reproducibility/<case_id>.json
      reviewer_bundle.zip

The writer refuses to write under ``golden_samples/**``. It does NOT
execute solvers; it only re-renders the existing reviewer surfaces and
freezes their bytes under a timestamped directory.

What this is NOT:
* Not a Tier 2 sealed packet (no independent reviewer signoff).
* Not a benchmark archive — every snapshot remains Tier 1 candidate.

Forbidden wording (per ADR-023 + ADR-024 lite): no ``benchmark
agreement``, no ``signed validation``, no ``perforation completed``,
no ``bullet-through-steel complete``, no ``validated physics``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ._schema_versions import COHORT_SNAPSHOT_MANIFEST_SCHEMA_VERSION
from .acceptance_packet import CLAIM_BOUNDARY, DEFAULT_TIER2_BLOCKERS_REMAINING
from .case_completeness import (
    CaseCompletenessInputs,
    render_case_completeness_json,
    score_case_completeness,
)
from .cohort_overview import build_cohort_overview, render_cohort_overview_json
from .reproducibility_manifest import (
    ReproducibilityManifestInputs,
    build_reproducibility_manifest,
    render_reproducibility_manifest_json,
)
from .reviewer_bundle import (
    ReviewerBundleInputs,
    build_reviewer_bundle,
    reviewer_bundle_filename,
)

CLAIM_TIER = "Tier 1 engineering candidate"
CLAIM_IMPACT_DEFAULT = (
    "Tier 1 candidate cohort snapshot only; not signed validation; not "
    "benchmark agreement; not a sealed FM-04b P8 packet. Each snapshot "
    "is a time-stamped view of the same reviewer surfaces a live API "
    "would return; it preserves the Tier 1 candidate claim boundary."
)

SNAPSHOTS_DIRNAME = "snapshots"
SNAPSHOT_MANIFEST_FILENAME = "SNAPSHOT_MANIFEST.json"
SNAPSHOT_LABEL_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{6}Z$")
_CASE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


@dataclass(frozen=True)
class SnapshotCaseInput:
    """One case to capture inside a cohort snapshot."""

    case_id: str
    starter_deck_path: Path | None = None
    engine_deck_path: Path | None = None
    ballistic_metrics_path: Path | None = None
    convergence_study_path: Path | None = None
    animation_manifest_path: Path | None = None
    result_mesh_path: Path | None = None
    generator_script_path: Path | None = None
    notes_path: Path | None = None


@dataclass
class SnapshotResult:
    """Outcome of writing a cohort snapshot."""

    snapshot_dir: Path
    snapshot_label: str
    members: list[str]


def utc_snapshot_label(now: datetime | None = None) -> str:
    """Produce a directory-safe UTC label of the form ``YYYY-MM-DDTHHMMSSZ``."""
    moment = now or datetime.now(UTC)
    return moment.strftime("%Y-%m-%dT%H%M%SZ")


def snapshots_root(repo_root: Path) -> Path:
    """Return the snapshots root directory (creates parent dirs if needed)."""
    return (repo_root / "reports" / SNAPSHOTS_DIRNAME).resolve()


def write_cohort_snapshot(
    cases: list[SnapshotCaseInput],
    repo_root: Path,
    snapshot_label: str | None = None,
) -> SnapshotResult:
    """Render the reviewer surface set for ``cases`` and freeze it under
    ``reports/snapshots/<label>/``.

    Refuses to write under ``golden_samples/**``.
    """
    if not cases:
        raise ValueError("cohort snapshot requires at least one case")

    label = snapshot_label or utc_snapshot_label()
    if not SNAPSHOT_LABEL_RE.fullmatch(label):
        raise ValueError(
            f"invalid snapshot label {label!r}; expected YYYY-MM-DDTHHMMSSZ"
        )

    out_root = snapshots_root(repo_root)
    _assert_not_in_golden_samples(out_root)
    out_dir = out_root / label
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "completeness").mkdir(parents=True, exist_ok=True)
    (out_dir / "reproducibility").mkdir(parents=True, exist_ok=True)
    # Phase 6 A: copy each case's raw ballistic_metrics.json into
    # metrics/<case>.json so future diffs can surface raw numerical
    # deltas (residual_velocity, energy_balance_error) without
    # re-reading the live project_state/ tree.
    (out_dir / "metrics").mkdir(parents=True, exist_ok=True)
    # Phase 7 A: copy each case's raw convergence_study.json into
    # convergence/<case>.json so the timeline + diff can recover the
    # combined verdict from captured bytes (closes Phase 6 carry-
    # forward §1; manifest 1.1.0 -> 1.2.0).
    (out_dir / "convergence").mkdir(parents=True, exist_ok=True)
    # Phase 9 B: copy each case's generator script bytes into
    # generator/<case>.py so the trust-score-provenance trace can
    # surface a SHA over the actual generator that produced the case.
    # Missing generators are silently skipped (the provenance walker
    # yields present=False for the case). Closes Phase 8 carry-
    # forward §2; manifest 1.2.0 -> 1.3.0; provenance 1.0.0 -> 1.1.0.
    (out_dir / "generator").mkdir(parents=True, exist_ok=True)

    members: list[str] = []

    # 1. Cohort overview (re-rendered from on-disk evidence).
    overview = build_cohort_overview(repo_root)
    overview_json = render_cohort_overview_json(overview)
    (out_dir / "cohort_overview.json").write_text(overview_json, encoding="utf-8")
    members.append("cohort_overview.json")

    # 2. Per-case completeness scorecards.
    for case in cases:
        if not _CASE_ID_RE.fullmatch(case.case_id):
            raise ValueError(f"invalid case_id in snapshot input: {case.case_id!r}")
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
        score_json = render_case_completeness_json(score)
        score_path = out_dir / "completeness" / f"{case.case_id}.json"
        score_path.write_text(score_json, encoding="utf-8")
        members.append(f"completeness/{case.case_id}.json")

    # 3. Per-case reproducibility manifests.
    for case in cases:
        manifest = build_reproducibility_manifest(
            ReproducibilityManifestInputs(
                case_id=case.case_id,
                repo_root=repo_root,
                generator_script_path=case.generator_script_path,
            )
        )
        manifest_json = render_reproducibility_manifest_json(manifest)
        manifest_path = out_dir / "reproducibility" / f"{case.case_id}.json"
        manifest_path.write_text(manifest_json, encoding="utf-8")
        members.append(f"reproducibility/{case.case_id}.json")

    # 3b. Phase 6 A — copy the case's raw ballistic_metrics.json into
    # metrics/<case>.json when it exists on disk. Missing metrics are
    # silently skipped (the diff will fall back to "no numerical_deltas"
    # for that case rather than raising).
    for case in cases:
        if (
            case.ballistic_metrics_path is not None
            and case.ballistic_metrics_path.is_file()
        ):
            raw = case.ballistic_metrics_path.read_text(encoding="utf-8")
            _assert_no_overclaim_text(
                f"metrics/{case.case_id}.json", raw
            )
            (out_dir / "metrics" / f"{case.case_id}.json").write_text(
                raw, encoding="utf-8"
            )
            members.append(f"metrics/{case.case_id}.json")

    # 3c. Phase 7 A — copy the case's raw convergence_study.json into
    # convergence/<case>.json when it exists on disk. Same fallback
    # semantics as metrics/: missing files are silently skipped and
    # downstream consumers (diff, timeline) gracefully degrade.
    for case in cases:
        if (
            case.convergence_study_path is not None
            and case.convergence_study_path.is_file()
        ):
            raw = case.convergence_study_path.read_text(encoding="utf-8")
            _assert_no_overclaim_text(
                f"convergence/{case.case_id}.json", raw
            )
            (out_dir / "convergence" / f"{case.case_id}.json").write_text(
                raw, encoding="utf-8"
            )
            members.append(f"convergence/{case.case_id}.json")

    # 3d. Phase 9 B — copy the case's generator_script_path bytes into
    # generator/<case>.py when it exists on disk. Same fallback
    # semantics as metrics/ and convergence/: missing generators are
    # silently skipped and the provenance walker yields present=False.
    # The forbidden-claim audit runs over the bytes decoded as UTF-8
    # with errors="replace" so a binary or non-UTF-8 generator never
    # crashes the snapshot writer; the SHA + present=True still ship.
    for case in cases:
        if (
            case.generator_script_path is not None
            and case.generator_script_path.is_file()
        ):
            raw_bytes = case.generator_script_path.read_bytes()
            decoded = raw_bytes.decode("utf-8", errors="replace")
            _assert_no_overclaim_text(f"generator/{case.case_id}.py", decoded)
            (out_dir / "generator" / f"{case.case_id}.py").write_bytes(raw_bytes)
            members.append(f"generator/{case.case_id}.py")

    # 4. Reviewer bundle (only when every case carries ballistic_metrics).
    bundle_members_written = False
    bundle_cases = [
        ReviewerBundleInputs(
            case_id=c.case_id,
            starter_deck_path=c.starter_deck_path,
            engine_deck_path=c.engine_deck_path,
            ballistic_metrics_path=c.ballistic_metrics_path,
            convergence_study_path=c.convergence_study_path,
            animation_manifest_path=c.animation_manifest_path,
            result_mesh_path=c.result_mesh_path,
            generator_script_path=c.generator_script_path,
            notes_path=c.notes_path,
        )
        for c in cases
        if c.ballistic_metrics_path is not None
        and c.ballistic_metrics_path.is_file()
    ]
    if bundle_cases:
        bundle_bytes = build_reviewer_bundle(bundle_cases, repo_root=repo_root)
        bundle_name = reviewer_bundle_filename(len(bundle_cases))
        (out_dir / bundle_name).write_bytes(bundle_bytes)
        members.append(bundle_name)
        bundle_members_written = True

    # 5. SNAPSHOT_MANIFEST.json (top-level manifest with provenance).
    snapshot_manifest = {
        "schema_version": COHORT_SNAPSHOT_MANIFEST_SCHEMA_VERSION,
        "snapshot_label": label,
        "captured_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "claim_tier": CLAIM_TIER,
        "claim_boundary": CLAIM_BOUNDARY,
        "cohort_count": len(cases),
        "cases": [c.case_id for c in cases],
        "members": sorted(members),
        "reviewer_bundle_written": bundle_members_written,
        "tier2_blockers_remaining": list(DEFAULT_TIER2_BLOCKERS_REMAINING),
        "claim_impact": CLAIM_IMPACT_DEFAULT,
    }
    manifest_text = json.dumps(snapshot_manifest, indent=2, sort_keys=True)
    _assert_no_overclaim_text(SNAPSHOT_MANIFEST_FILENAME, manifest_text)
    (out_dir / SNAPSHOT_MANIFEST_FILENAME).write_text(manifest_text, encoding="utf-8")

    return SnapshotResult(
        snapshot_dir=out_dir,
        snapshot_label=label,
        members=sorted(members),
    )


def list_cohort_snapshots(repo_root: Path) -> list[dict[str, Any]]:
    """Enumerate existing snapshots under ``reports/snapshots/`` ordered
    newest-first by label (which is ISO-ordered).

    Skips entries that do not match the canonical label shape or do not
    contain a readable SNAPSHOT_MANIFEST.json.
    """
    root = snapshots_root(repo_root)
    if not root.is_dir():
        return []
    entries: list[dict[str, Any]] = []
    for child in sorted(root.iterdir(), reverse=True):
        if not child.is_dir():
            continue
        if not SNAPSHOT_LABEL_RE.fullmatch(child.name):
            continue
        manifest_path = child / SNAPSHOT_MANIFEST_FILENAME
        if not manifest_path.is_file():
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        entries.append(
            {
                "snapshot_label": manifest.get("snapshot_label", child.name),
                "captured_at_utc": manifest.get("captured_at_utc"),
                "claim_tier": manifest.get("claim_tier", CLAIM_TIER),
                "claim_boundary": manifest.get("claim_boundary", CLAIM_BOUNDARY),
                "cohort_count": manifest.get("cohort_count", 0),
                "cases": list(manifest.get("cases", [])),
                "reviewer_bundle_written": bool(
                    manifest.get("reviewer_bundle_written", False)
                ),
                "schema_version": manifest.get("schema_version", ""),
            }
        )
    return entries


def render_snapshot_listing_json(repo_root: Path) -> str:
    """Return the snapshot listing as a JSON string."""
    listing = list_cohort_snapshots(repo_root)
    payload = {
        "schema_version": COHORT_SNAPSHOT_MANIFEST_SCHEMA_VERSION,
        "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "claim_tier": CLAIM_TIER,
        "claim_boundary": CLAIM_BOUNDARY,
        "snapshot_count": len(listing),
        "snapshots": listing,
        "claim_impact": (
            "Tier 1 candidate cohort snapshot listing only; not signed "
            "validation; not benchmark agreement"
        ),
    }
    return json.dumps(payload, indent=2, sort_keys=True)


# ---------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------


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
                f"Cohort snapshot member {member_name!r} contains forbidden "
                f"positive claim: {token!r}"
            )


def _assert_not_in_golden_samples(output_dir: Path) -> None:
    resolved = output_dir.resolve()
    for parent in (resolved, *resolved.parents):
        if parent.name == "golden_samples":
            raise ValueError(
                "Cohort snapshot refuses writes under golden_samples/**; "
                "use reports/snapshots/<UTC>/ instead"
            )
