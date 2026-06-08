#!/usr/bin/env python3
"""Generate FALLBACK_CANDIDATE_CASES entries from golden_samples/ disk truth.

FM-04a Phase 38 H — provenance + regeneration tool for the frontend offline
fallback registry (``frontend/src/candidateCaseRegistry.ts``).

Tier 1 / Tier 2 engineering candidate; not signed validation; not benchmark
agreement.

WHY THIS EXISTS
---------------
The static ``FALLBACK_CANDIDATE_CASES`` list is what the Workbench picker
renders when ``/api/v1/candidate-cases`` is unreachable. Eval-fleet finding #3
(Phase 38 E) caught it carrying only 7 of the 24 on-disk ``*-candidate``
cohort directories — 17 cases were invisible offline. This script sources the
missing entries from disk so no field is hand-fabricated:

  * ``claimTier`` / ``claimBoundary``  -> the ``_claim_tier`` SSOT accessors
        (the SAME ones the backend route uses; a PASS ``cross_check_verdict.yaml``
        on a REGISTERED case promotes to tier-2, otherwise tier-1 floor).
  * ``solverKind``                     -> the verdict YAML ``solver_kind`` (omitted
        when there is no verdict — the backend itself would not know either).
  * ``runnerAvailable``                -> whether a ``cross_check_verdict.yaml``
        exists (a real ccx run produced it).
  * ``notesExcerpt``                   -> first 12 lines / 1200 chars of NOTES.md,
        byte-for-byte the backend ``_notes_excerpt`` rule (online<->offline parity).
  * deck / generator paths             -> file-existence checks on disk.

  * ``displayLabel``                   -> a DETERMINISTIC humanisation of the
        caseId + the SSOT tier (e.g. ``wedge-c3d6-candidate`` -> "Wedge C3D6 ·
        Tier 2 validated"). A picker nicety, NOT a validation claim — derived,
        never hand-authored, so it cannot drift into a marketing overclaim.
        (The original 7 curated entries keep their richer hand-written labels;
        ``--all`` would overwrite them, hence the default skips them.)

Strings are emitted double-quoted because several NOTES excerpts contain
apostrophes (Hooke's, Euler's, Young's).

USAGE
-----
    python scripts/gen_fallback_candidate_registry.py            # only-missing (default)
    python scripts/gen_fallback_candidate_registry.py --all      # every case

``--all`` would discard the curated displayLabels / prose excerpts already
hand-written for the original 7 entries, so the default deliberately emits only
cases ABSENT from the current fallback. The drift guard is the test
``frontend/test/Phase38H_fallback_cohort_coverage.test.tsx`` — when it fails
(a new ``*-candidate`` dir landed without a fallback entry) re-run this script
and paste the new block in.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Curated entries already hand-maintained in candidateCaseRegistry.ts. The
# default run skips these so their displayLabels / prose excerpts survive.
_ALREADY_PRESENT = {
    "GS-102-candidate",
    "GS-102-refined-candidate",
    "GS-102-hifi-candidate",
    "rod-wave-impact-energy-leak-candidate",
    "cylinder-pv-candidate",
    "plate-with-hole-candidate",
    "cantilever-beam-candidate",
}

_CASE_DIR_SUFFIX = "-candidate"
_CASE_ID_RE = re.compile(r"^[A-Za-z0-9_-]+-candidate$")
_NOTES_MAX_LINES = 12
_NOTES_MAX_CHARS = 1200


def _repo_root() -> Path:
    # scripts/gen_fallback_candidate_registry.py -> repo root is 1 parent up.
    return Path(__file__).resolve().parents[1]


def _notes_excerpt(case_dir: Path) -> str | None:
    notes = case_dir / "NOTES.md"
    if not notes.is_file():
        return None
    text = notes.read_text(encoding="utf-8", errors="replace")
    head = "\n".join(text.splitlines()[:_NOTES_MAX_LINES])
    if len(head) > _NOTES_MAX_CHARS:
        head = head[: _NOTES_MAX_CHARS - 3] + "..."
    return head


def _guess_generator_relpath(case_id: str, repo_root: Path) -> str | None:
    base = case_id.lower().replace("gs-", "gs").replace("-candidate", "")
    base = base.replace("-", "_")
    path = repo_root / "scripts" / f"gen_{base}_deck.py"
    return f"scripts/gen_{base}_deck.py" if path.is_file() else None


def _verdict_solver_kind(case_dir: Path) -> tuple[str | None, bool]:
    verdict = case_dir / "cross_check_verdict.yaml"
    if not verdict.is_file():
        return None, False
    text = verdict.read_text(encoding="utf-8", errors="replace")
    try:
        payload: object = json.loads(text)
    except json.JSONDecodeError:
        try:
            import yaml

            payload = yaml.safe_load(text)
        except Exception:
            payload = None
    solver_kind: str | None = None
    if isinstance(payload, dict):
        solver_kind = payload.get("solver_kind")
        outcome = payload.get("verdict_outcome")
        if solver_kind is None and isinstance(outcome, dict):
            solver_kind = outcome.get("solver_kind")
    return solver_kind, True


def _js(value: str) -> str:
    """Double-quoted JS/TS string literal (handles embedded apostrophes)."""
    return json.dumps(value, ensure_ascii=False)


# Acronyms / mixed-case tokens that should NOT be naively title-cased when a
# caseId is humanised into a picker displayLabel. Everything else is just
# capitalised. This keeps the label an honest, deterministic rendering of the
# caseId (a UI nicety, not a validation claim) rather than a hand-authored one.
_LABEL_TOKEN_MAP = {
    "pv": "PV",
    "1d": "1D",
    "le10": "LE10",
    "ss": "SS",
    "c3d6": "C3D6",
    "nafems": "NAFEMS",
    "l50": "L50",
}


def _humanize_case_id(case_id: str) -> str:
    stem = case_id[: -len("-candidate")] if case_id.endswith("-candidate") else case_id
    words = [_LABEL_TOKEN_MAP.get(tok, tok.capitalize()) for tok in stem.split("-")]
    return " ".join(words)


def _display_label(case_id: str, tier: str) -> str:
    suffix = "Tier 2 validated" if "Tier 2" in tier else "Tier 1 candidate"
    return f"{_humanize_case_id(case_id)} · {suffix}"


def _entry_block(case_dir: Path, repo_root: Path) -> str:
    # Imported lazily so `--help` works without the backend on sys.path.
    from app.services.reporting._claim_tier import (
        claim_boundary_for,
        claim_tier_label_for,
    )

    case_id = case_dir.name
    solver_kind, has_verdict = _verdict_solver_kind(case_dir)
    tier = claim_tier_label_for(case_id, repo_root)
    boundary = claim_boundary_for(case_id, repo_root)
    starter = case_dir / "data" / "model_00_0000.rad"
    engine = case_dir / "data" / "model_00_0001.rad"
    generator = _guess_generator_relpath(case_id, repo_root)
    excerpt = _notes_excerpt(case_dir)

    lines = ["  {", f"    caseId: {_js(case_id)},"]
    lines.append(f"    runnerAvailable: {'true' if has_verdict else 'false'},")
    if solver_kind:
        lines.append(f"    solverKind: {_js(solver_kind)},")
    lines.append(f"    displayLabel: {_js(_display_label(case_id, tier))},")
    lines.append(f"    claimTier: {_js(tier)},")
    starter_rel = f"golden_samples/{case_id}/data/model_00_0000.rad"
    engine_rel = f"golden_samples/{case_id}/data/model_00_0001.rad"
    lines.append(f"    starterDeckRelpath: {_js(starter_rel) if starter.is_file() else 'null'},")
    lines.append(f"    engineDeckRelpath: {_js(engine_rel) if engine.is_file() else 'null'},")
    lines.append(f"    generatorScriptRelpath: {_js(generator) if generator else 'null'},")
    lines.append(f"    notesExcerpt: {_js(excerpt) if excerpt is not None else 'null'},")
    lines.append(f"    claimBoundary: {_js(boundary)},")
    lines.append("  },")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--all",
        action="store_true",
        help="emit every case (discards curated labels — use with care)",
    )
    args = parser.parse_args()

    repo_root = _repo_root()
    # Make the backend package importable (_claim_tier lives under app.services,
    # which does NOT trip the app.api OpenAI-proxies import crash).
    sys.path.insert(0, str(repo_root / "backend"))

    golden = repo_root / "golden_samples"
    blocks: list[str] = []
    for case_dir in sorted(golden.iterdir(), key=lambda p: p.name):
        if not case_dir.is_dir() or not case_dir.name.endswith(_CASE_DIR_SUFFIX):
            continue
        if not _CASE_ID_RE.match(case_dir.name):
            continue
        if not args.all and case_dir.name in _ALREADY_PRESENT:
            continue
        blocks.append(_entry_block(case_dir, repo_root))

    print("\n".join(blocks))
    print(f"// generated {len(blocks)} entries", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
