"""Candidate-case picker endpoint (FM-04a Phase 2 C).

Tier 1 engineering candidate. Not signed validation. Not benchmark agreement.

Enumerates `golden_samples/*-candidate/` directories so the Workbench can
let users switch between candidate fixtures (e.g.
`GS-102-candidate / -refined-candidate / -hifi-candidate`) without code
changes. Read-only: never writes inside `golden_samples/**`.

Output shape per case is intentionally narrow so the frontend can render
a dropdown + NOTES excerpt + claim-tier banner with no extra parsing:

    {
      "case_id": "GS-102-refined-candidate",
      "claim_tier": "Tier 1 engineering candidate"  # or "Tier 2 real-solver
                  # validated" when a PASS cross_check_verdict.yaml promoted it,
      "starter_deck_relpath": "golden_samples/GS-102-refined-candidate/data/model_00_0000.rad",
      "engine_deck_relpath":  "golden_samples/GS-102-refined-candidate/data/model_00_0001.rad",
      "generator_script_relpath": "scripts/gen_gs102_refined_deck.py" | null,
      "notes_excerpt": "first ~12 lines of NOTES.md when present",
      "claim_boundary": "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement",
    }
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from fastapi import APIRouter

from app.services.reporting._claim_tier import (
    claim_boundary_for,
    claim_tier_label_for,
)

router = APIRouter(prefix="/candidate-cases", tags=["candidate-cases"])

_CASE_DIR_SUFFIX = "-candidate"
_CASE_ID_RE = re.compile(r"^[A-Za-z0-9_-]+-candidate$")
_NOTES_EXCERPT_MAX_LINES = 12
_NOTES_EXCERPT_MAX_CHARS = 1200

CLAIM_TIER = "Tier 1 engineering candidate"
CLAIM_BOUNDARY = (
    "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"
)


def _repo_root() -> Path:
    """Resolve the repository root from this module's path.

    backend/app/api/routes/candidate_cases.py -> repo root is 4 parents up.
    """
    return Path(__file__).resolve().parents[4]


def _scan_candidate_cases(repo_root: Path) -> list[dict[str, object]]:
    golden = (repo_root / "golden_samples").resolve()
    if not golden.is_dir():
        return []
    results: list[dict[str, object]] = []
    for entry in sorted(golden.iterdir(), key=lambda p: p.name):
        if not entry.is_dir():
            continue
        if not entry.name.endswith(_CASE_DIR_SUFFIX):
            continue
        if not _CASE_ID_RE.match(entry.name):
            continue
        results.append(_describe_case(entry, repo_root))
    return results


def _describe_case(case_dir: Path, repo_root: Path) -> dict[str, object]:
    starter = case_dir / "data" / "model_00_0000.rad"
    engine = case_dir / "data" / "model_00_0001.rad"
    notes = case_dir / "NOTES.md"

    return {
        "case_id": case_dir.name,
        # Per-case tier resolved from the _claim_tier SSOT (ADR-025): a case
        # promoted to tier_2_validated by a PASS cross_check_verdict.yaml
        # surfaces "Tier 2 real-solver validated" here instead of the cohort
        # floor. Previously hard-coded CLAIM_TIER for every case, which hid
        # every real-solver promotion from the picker (FM-04a Phase 38 F fix).
        # `*-candidate` names never match the ^GS-\d{3}$ shape, so the accessor
        # cannot raise the HF1.7a ValueError here. Pass repo_root so the tier is
        # resolved against THIS scan's tree's verdict files, not the module-load
        # registry (Codex R1 — keeps tmp/alternate worktrees correct).
        "claim_tier": claim_tier_label_for(case_dir.name, repo_root),
        "starter_deck_relpath": _relpath_if_file(starter, repo_root),
        "engine_deck_relpath": _relpath_if_file(engine, repo_root),
        "generator_script_relpath": _guess_generator_relpath(case_dir.name, repo_root),
        "notes_excerpt": _notes_excerpt(notes),
        "claim_boundary": claim_boundary_for(case_dir.name, repo_root),
    }


def _relpath_if_file(path: Path, repo_root: Path) -> Optional[str]:
    if not path.is_file():
        return None
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path)


def _guess_generator_relpath(case_id: str, repo_root: Path) -> Optional[str]:
    # GS-102-refined-candidate -> scripts/gen_gs102_refined_deck.py
    base = case_id.lower()
    base = base.replace("gs-", "gs").replace("-candidate", "").replace("-", "_")
    candidate_path = repo_root / "scripts" / f"gen_{base}_deck.py"
    if candidate_path.is_file():
        return str(candidate_path.resolve().relative_to(repo_root.resolve()))
    return None


def _notes_excerpt(notes_path: Path) -> Optional[str]:
    if not notes_path.is_file():
        return None
    text = notes_path.read_text(encoding="utf-8", errors="replace")
    head = "\n".join(text.splitlines()[:_NOTES_EXCERPT_MAX_LINES])
    if len(head) > _NOTES_EXCERPT_MAX_CHARS:
        head = head[: _NOTES_EXCERPT_MAX_CHARS - 3] + "..."
    return head


@router.get("")
async def list_candidate_cases() -> dict[str, object]:
    """List Tier 1 candidate case directories under `golden_samples/`.

    Filters to entries whose directory name ends in `-candidate` so the
    `^GS-\\d{3}$` signed registry (per ADR-011 §HF1.7 / ADR-013) is never
    surfaced through this endpoint. Read-only; refuses to enumerate paths
    outside `golden_samples/`.
    """
    cases = _scan_candidate_cases(_repo_root())
    return {
        "claim_tier": CLAIM_TIER,
        "claim_boundary": CLAIM_BOUNDARY,
        "claim_impact": (
            "Tier 1 candidate-case picker listing only; never authorizes "
            "promotion to signed GS-<id> registry; not signed validation; "
            "not benchmark agreement"
        ),
        "count": len(cases),
        "cases": cases,
    }
