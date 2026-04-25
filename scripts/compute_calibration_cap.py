#!/usr/bin/env python3
"""Calibration cap computation for T1 self-pass-rate (ADR-012 · AR-2026-04-25-001).

Replaces RETRO-V61-001's per-PR honesty discipline with a mechanical formula
derived from the rolling window of the last 5 PRs' Codex Round 1 outcomes.
T1 cannot self-rate; T1 reads the ceiling. PR template prefills the
self-pass field by calling this script; the field is read-only to T1.

Formula (canonical, ratified in AR-2026-04-25-001 §1):

    Rolling window:  last 5 PRs to main, ordered by `merged_at` (ISO 8601).
                     ≥ ADR-011 baseline; pre-ADR excluded.
    Outcome canon:   APPROVE | APPROVE_WITH_NITS | CHANGES_REQUIRED | BLOCKER
                     (NITS counts as APPROVE; CR/BLOCKER count as CHANGES_REQUIRED)

    Base ceiling (per next PR):
      0 of last 5 = CR  → 95%  · honor system   · pre-merge Codex OPTIONAL
      1-2 of last 5     → 80%  · pre-merge Codex RECOMMENDED
      3-4 of last 5     → 50%  · pre-merge Codex MANDATORY
      5 of last 5       → 30%  · pre-merge Codex MANDATORY · BLOCKING

    Recovery (override):
      2 consecutive R1=APPROVE  → ceiling steps up one rung from base
      3 consecutive R1=APPROVE  → ceiling returns to 95%

Invocations:
    python3 scripts/compute_calibration_cap.py
        emits JSON to stdout (ceiling, mandatory_codex, blocking, basis, entry_count)
    python3 scripts/compute_calibration_cap.py --human
        emits human-readable summary to stdout
    python3 scripts/compute_calibration_cap.py --check <CEILING>
        exits 1 if claimed CEILING > computed ceiling (PR-template / CI use)

State source: reports/calibration_state.json (append-only, hard-validated).
The script is a pure function over its contents and FAILS CLOSED on any
shape violation: missing file, schema mismatch, duplicate PR, missing
merged_at, unknown outcome — all exit non-zero with a clear stderr message.

Honesty caveat (T0 self-rated 88% on ratification): the recovery thresholds
(2 → step up, 3 → reset) are reasonable but not empirically grounded yet;
revisit after 10 more PRs of post-ADR-012 data.

R2 changes (post Codex R1 CHANGES_REQUIRED, 2026-04-26):
  * load_state() now sorts by merged_at, not PR number — the repo already
    has a counterexample (PR #20 merged before #18 and #19).
  * Missing/malformed state file is now a hard error (was: returned [] →
    fail-open at 95%/OPTIONAL).
  * schema_version, duplicate PRs, missing merged_at, and unknown outcomes
    are all hard-validated.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

# Canonical: NITS counts as APPROVE; everything else (CR, BLOCKER) counts as CR.
APPROVE_OUTCOMES = frozenset({"APPROVE", "APPROVE_WITH_NITS"})
CANONICAL_OUTCOMES = frozenset({"APPROVE", "APPROVE_WITH_NITS", "CHANGES_REQUIRED", "BLOCKER"})

# Rung ladder, low → high. Recovery moves one index up.
RUNGS: tuple[int, ...] = (30, 50, 80, 95)

# Schema version this script supports. Bump only with a corresponding ADR.
SUPPORTED_SCHEMA_VERSION = 1


class CalibrationStateError(Exception):
    """Hard error reading or validating the calibration state file."""


@dataclass(frozen=True)
class CalibrationResult:
    ceiling: int
    mandatory_codex: bool
    blocking: bool
    basis: str
    entry_count: int


def step_up(ceiling: int) -> int:
    """Move ceiling one rung up (saturate at 95)."""
    if ceiling not in RUNGS:
        raise ValueError(f"unknown ceiling rung: {ceiling}")
    idx = RUNGS.index(ceiling)
    return RUNGS[min(idx + 1, len(RUNGS) - 1)]


def base_ceiling_from_cr_count(cr_count: int) -> int:
    """Map count of CHANGES_REQUIRED in last 5 entries to base ceiling.

    Per AR-2026-04-25-001 §1.
    """
    if cr_count < 0:
        raise ValueError(f"cr_count must be >= 0, got {cr_count}")
    if cr_count == 0:
        return 95
    if cr_count <= 2:
        return 80
    if cr_count <= 4:
        return 50
    return 30


def trailing_approve_count(outcomes: list[str]) -> int:
    """Count consecutive APPROVE/NITS at the END of the list (most recent first)."""
    n = 0
    for o in reversed(outcomes):
        if o in APPROVE_OUTCOMES:
            n += 1
        else:
            break
    return n


def compute_calibration(outcomes: list[str]) -> CalibrationResult:
    """Compute calibration ceiling from a chronologically-ordered list of R1 outcomes."""
    last5 = outcomes[-5:]
    cr_count = sum(1 for o in last5 if o not in APPROVE_OUTCOMES)
    base = base_ceiling_from_cr_count(cr_count)
    trailing = trailing_approve_count(outcomes)

    if trailing >= 3:
        ceiling = 95
        basis = "3+ trailing APPROVE → ceiling reset to 95% (recovery)"
    elif trailing >= 2:
        stepped = step_up(base)
        ceiling = stepped
        basis = (
            f"{cr_count} of last 5 = CHANGES_REQUIRED (base {base}%) + "
            f"2 trailing APPROVE → step up to {ceiling}%"
        )
    else:
        ceiling = base
        basis = f"{cr_count} of last 5 = CHANGES_REQUIRED → ceiling {ceiling}%"

    # Codex gate derivation from final ceiling
    if ceiling <= 30:
        mandatory_codex = True
        blocking = True
    elif ceiling <= 50:
        mandatory_codex = True
        blocking = False
    else:
        # 80 = recommended; 95 = optional. Both are "not mandatory" for the
        # ceiling itself; M1-M5 triggers in ADR-011 §T2 may still mandate
        # Codex independently of the ceiling.
        mandatory_codex = False
        blocking = False

    return CalibrationResult(
        ceiling=ceiling,
        mandatory_codex=mandatory_codex,
        blocking=blocking,
        basis=basis,
        entry_count=len(outcomes),
    )


def _validate_state_dict(data: object) -> list[dict]:
    """Hard-validate a parsed calibration_state.json document.

    Raises CalibrationStateError on any shape violation. Returns the
    validated entries list (each entry guaranteed to have pr/merged_at/
    r1_outcome of the right type).
    """
    if not isinstance(data, dict):
        raise CalibrationStateError("state file root must be a JSON object")

    schema_version = data.get("schema_version")
    if schema_version != SUPPORTED_SCHEMA_VERSION:
        raise CalibrationStateError(
            f"schema_version must be {SUPPORTED_SCHEMA_VERSION}, got {schema_version!r}"
        )

    entries = data.get("entries")
    if not isinstance(entries, list):
        raise CalibrationStateError("'entries' must be a list")

    seen_prs: set[int] = set()
    for i, e in enumerate(entries):
        if not isinstance(e, dict):
            raise CalibrationStateError(f"entries[{i}] must be a JSON object")

        pr = e.get("pr")
        if not isinstance(pr, int) or pr <= 0:
            raise CalibrationStateError(
                f"entries[{i}].pr must be a positive int, got {pr!r}"
            )
        if pr in seen_prs:
            raise CalibrationStateError(
                f"entries[{i}].pr={pr} is a duplicate of an earlier entry"
            )
        seen_prs.add(pr)

        merged_at = e.get("merged_at")
        if not isinstance(merged_at, str) or not merged_at:
            raise CalibrationStateError(
                f"entries[{i}].merged_at (ISO 8601 string) is required"
            )

        outcome = e.get("r1_outcome")
        if outcome not in CANONICAL_OUTCOMES:
            raise CalibrationStateError(
                f"entries[{i}].r1_outcome must be one of "
                f"{sorted(CANONICAL_OUTCOMES)}, got {outcome!r}"
            )

    return entries


def load_state(state_path: Path) -> list[str]:
    """Read calibration_state.json and return chronologically-ordered R1 outcomes.

    Raises CalibrationStateError on missing file, invalid JSON, schema-version
    mismatch, duplicate PR rows, missing merged_at, or unknown outcomes.

    Sorting is by `merged_at` ISO 8601 timestamp (lexicographic == chronological
    for ISO 8601). This is the fix for Codex R1 HIGH #1: the previous
    implementation sorted by PR number, but the repo already contains a
    counterexample (PR #20 merged_at 2026-04-25T08:33:51Z is BEFORE
    PR #18 at 08:53:09Z).
    """
    if not state_path.exists():
        raise CalibrationStateError(
            f"calibration state file not found: {state_path}. "
            "This file is required; it must be initialised by the ADR-012 "
            "establishing PR and append-only thereafter."
        )

    try:
        with state_path.open() as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise CalibrationStateError(
            f"calibration state file is not valid JSON: {state_path}: {e}"
        ) from e

    entries = _validate_state_dict(data)

    # Sort by merged_at (ISO 8601 lexicographic == chronological).
    entries_sorted = sorted(entries, key=lambda e: e["merged_at"])
    return [e["r1_outcome"] for e in entries_sorted]


def gate_label(result: CalibrationResult) -> str:
    if result.blocking:
        return "BLOCKING"
    if result.mandatory_codex:
        return "MANDATORY"
    if result.ceiling <= 80:
        return "RECOMMENDED"
    return "OPTIONAL"


def main(argv: list[str]) -> int:
    default_state = Path(__file__).resolve().parent.parent / "reports" / "calibration_state.json"
    parser = argparse.ArgumentParser(
        description="Compute T1 calibration ceiling per ADR-012 / AR-2026-04-25-001."
    )
    parser.add_argument(
        "--human",
        action="store_true",
        help="emit human-readable summary instead of JSON",
    )
    parser.add_argument(
        "--check",
        type=int,
        metavar="CEILING",
        help="exit 1 if claimed CEILING exceeds the computed ceiling",
    )
    parser.add_argument(
        "--state",
        type=Path,
        default=default_state,
        help=f"path to calibration_state.json (default: {default_state})",
    )
    args = parser.parse_args(argv[1:])

    try:
        outcomes = load_state(args.state)
    except CalibrationStateError as e:
        sys.stderr.write(f"calibration state error: {e}\n")
        return 1

    result = compute_calibration(outcomes)

    if args.check is not None:
        if args.check > result.ceiling:
            sys.stderr.write(
                f"calibration check FAILED: claimed {args.check}% exceeds "
                f"computed ceiling {result.ceiling}%\n"
                f"  basis: {result.basis}\n"
                f"  Codex gate: {gate_label(result)}\n"
            )
            return 1
        return 0

    if args.human:
        print(f"T1 calibration ceiling : {result.ceiling}%")
        print(f"Codex pre-merge gate   : {gate_label(result)}")
        print(f"Basis                  : {result.basis}")
        print(f"State entries          : {result.entry_count} (last 5 used)")
    else:
        out = {
            "ceiling": result.ceiling,
            "mandatory_codex": result.mandatory_codex,
            "blocking": result.blocking,
            "basis": result.basis,
            "entry_count": result.entry_count,
            "gate_label": gate_label(result),
        }
        print(json.dumps(out, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
