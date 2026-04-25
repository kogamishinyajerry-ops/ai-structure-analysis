#!/usr/bin/env python3
"""HF1 forbidden-zone path guard for AI-Structure-FEA (FF-06).

Implements automated detection of HF1 zone violations as specified in
ADR-011 §Hard-Floor Rules. Two invocation modes:

1. **pre-commit mode** (default): reads staged index via
   ``git diff --cached --name-status -z``. Configured in
   ``.pre-commit-config.yaml`` with ``pass_filenames: false`` so
   pre-commit's own file filter cannot mask renames-old-side or deletes.

2. **CI mode** (``--from-diff <ref>``): reads the diff between
   ``<ref>`` and HEAD via ``git diff <ref>...HEAD --name-status -z``.
   Mode is ready (pure function + tests); workflow integration in
   ``.github/workflows/ci.yml`` is **deferred to ADR-013** per
   AR-2026-04-25-001 §2 (T0 placed CI required-status-check under
   ADR-013 alongside branch protection). Until ADR-013 lands, HF1
   enforcement on PRs is pre-commit only — contributors who skip
   pre-commit can bypass it; this is the gap ADR-013 closes.

Both modes use the same ``parse_name_status_z`` parser, which extracts
both old- and new- paths from rename/copy records (R/C) and includes
deletion paths (D) — covering the BLOCKER from FF-06 R1 review where
pre-commit's filtered file list silently bypassed the zone for ``mv``
and ``rm`` of zone files.

The zone is hard-coded in this file by design — per FF-06 charter, the
guard must not parse ADR-011 markdown at runtime (too fragile against
typos/refactors). When ADR-011 §HF1 changes, the corresponding entry in
``ZONE`` must be updated in the same PR.

**HF1.8 self-protection bootstrap note:** This script is itself in the
HF1 zone under HF1.8 (added per AR-2026-04-25-001 §3). The
self-protection clause takes effect on the **next** modification of
this file — i.e., the PR that introduced HF1.8 (AR-2026-04-25-001
amendment cycle, PR #23) bootstraps the protection but is not itself
blocked by it. Future modifications require either (a) explicit ADR
cover, or (b) ``HF1_GUARD_OVERRIDE='<reason citing ADR>'``.

The same bootstrap applies to HF1.9 (``.github/workflows/**``): the PR
that introduces HF1.9 modifies the workflow file as part of the
bootstrap; subsequent modifications require ADR cover.

Per AR-2026-04-25-001 §3 (T0 ratification), the zone is split into
two surfaces:

  HF1 hard-stop zone (this script enforces; pre-commit + CI):
    - execution truth (solver, router, geometry, schemas, tests)
    - toolchain pin (Dockerfile, Makefile)
    - Gold Standard data (golden_samples/)
    - meta-protection (this script itself; CI workflows)

  PR-protected zone (NOT enforced here; relies on branch protection
  + mandatory Codex per ADR-011 §T2 amendment):
    - docs/adr/**, docs/governance/**, docs/failure_patterns/**

The PR-protected zone was previously HF1 hard-stop (ADR-011 v1
HF1.8), but every governance amendment touched it, creating a
chicken-egg recovery clause. T0 ruling §3 dropped it from HF1 in
favor of branch protection (ADR-013) + mandatory Codex M1 trigger
(ADR-011 §T2 amendment). See AR-2026-04-25-001 §3 for the rationale.

Override mechanism: setting ``HF1_GUARD_OVERRIDE='<non-empty reason>'``
allows the local commit through and emits a stderr warning. **The
override is a local escape hatch only.** This hook cannot enforce that
the reason is cited in the commit message or surfaced to PR review;
that audit trail is FF-07's scope (CI commit-trailer presence + claim
format check). Until FF-07 lands, override usage relies on reviewer
discipline.

Scope caveat for HF1.6 (Dockerfile / Makefile): ADR-011 §HF1.6 names
specific sections (``docker-base`` / ``docker-probe`` / ``hot-smoke``)
rather than whole files, but parsing Makefile/Dockerfile syntax to
detect line-level scope is out of scope for FF-06 (would require a
makefile parser). This guard therefore protects the **whole**
``Dockerfile`` and ``Makefile`` files conservatively. If that becomes
too disruptive in practice, the right fix is either (a) move the
protected targets to dedicated files (e.g., ``Makefile.docker`` /
``Dockerfile.toolchain``), or (b) amend ADR-011 §HF1.6 to whole-file
scope. Both are tracked as follow-up amendments to ADR-011.

Exit codes:
    0  no zone violation (or override active with non-empty reason)
    1  zone violation; commit rejected
    2  CLI usage error
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class ZoneEntry:
    path: str
    match: str  # "exact" | "prefix"
    rule: str
    adr_ref: str


# HF1 forbidden zone — sourced from ADR-011 §Hard-Floor Rules.
# Update both this list AND ADR-011 in the same PR if the zone changes.
# Self-protection (HF1.8 — entry for this script itself) means every
# modification of this file must come through a PR; direct unreviewed
# commits to scripts/hf1_path_guard.py trigger the guard against itself.
ZONE: tuple[ZoneEntry, ...] = (
    ZoneEntry("agents/solver.py", "exact", "HF1.1 — solver implementation", "ADR-011 §HF1 #1"),
    ZoneEntry(
        "tools/calculix_driver.py", "exact", "HF1.1 — solver implementation", "ADR-011 §HF1 #1"
    ),
    ZoneEntry("agents/router.py", "exact", "HF1.2 — ADR-004 fault routing", "ADR-011 §HF1 #2"),
    ZoneEntry(
        "agents/geometry.py", "exact", "HF1.3 — ADR-008 N-3 dummy-geometry guard", "ADR-011 §HF1 #3"
    ),
    ZoneEntry(
        "schemas/sim_state.py",
        "exact",
        "HF1.4 — ADR-004 FaultClass enum (downstream type contract)",
        "ADR-011 §HF1 #4",
    ),
    ZoneEntry(
        "tests/test_toolchain_probes.py",
        "exact",
        "HF1.5 — ADR-002 toolchain pin assertion",
        "ADR-011 §HF1 #5",
    ),
    ZoneEntry(
        "Dockerfile",
        "exact",
        "HF1.6 — ADR-002 CalculiX 2.21 pin (whole-file; narrowing tracked separately)",
        "ADR-011 §HF1 #6",
    ),
    ZoneEntry(
        "Makefile",
        "exact",
        "HF1.6 — ADR-002 CalculiX 2.21 pin (whole-file; narrowing tracked separately)",
        "ADR-011 §HF1 #6",
    ),
    ZoneEntry(
        "golden_samples/", "prefix", "HF1.7 — golden samples are read-only", "ADR-011 §HF1 #7"
    ),
    # NEW per AR-2026-04-25-001 §3 — meta-protection + CI enforcement
    ZoneEntry(
        "scripts/hf1_path_guard.py",
        "exact",
        "HF1.8 — meta-protection: path-guard cannot silently self-modify",
        "ADR-011 §HF1 #8 (per AR-2026-04-25-001)",
    ),
    ZoneEntry(
        ".github/workflows/",
        "prefix",
        "HF1.9 — CI enforcement workflows are governance surface",
        "ADR-011 §HF1 #9 (per AR-2026-04-25-001)",
    ),
)


def path_hits_zone(path: str, entry: ZoneEntry) -> bool:
    if entry.match == "exact":
        return path == entry.path
    if entry.match == "prefix":
        return path.startswith(entry.path)
    raise ValueError(f"unknown match mode: {entry.match}")


def find_violations(paths: list[str]) -> list[tuple[str, ZoneEntry]]:
    hits: list[tuple[str, ZoneEntry]] = []
    seen: set[str] = set()
    for p in paths:
        if p in seen:
            continue
        for entry in ZONE:
            if path_hits_zone(p, entry):
                hits.append((p, entry))
                seen.add(p)
                break
    return hits


def parse_name_status_z(blob: str) -> list[str]:
    """Parse `git diff --cached --name-status -z` output.

    Records:
      - A/M/D/T/U/X/B: ``<status>\\0<path>\\0``
      - R<score>/C<score>: ``<status>\\0<old>\\0<new>\\0``
                           (both old AND new are returned so renaming
                           a zone path away or copying out of zone is
                           still detected)

    Empty input → empty list.
    """
    if not blob:
        return []
    fields = blob.split("\0")
    # `-z` produces a trailing NUL; split() leaves a final empty element.
    if fields and fields[-1] == "":
        fields.pop()
    paths: list[str] = []
    i = 0
    n = len(fields)
    while i < n:
        status = fields[i]
        i += 1
        if not status:
            continue
        if status[0] in ("R", "C"):
            # rename / copy — next two fields are old and new
            if i + 1 < n:
                paths.append(fields[i])
                paths.append(fields[i + 1])
                i += 2
            else:
                # malformed; bail rather than misparse
                break
        else:
            if i < n:
                paths.append(fields[i])
                i += 1
    return paths


def _run_git_diff(args: list[str], context: str) -> str:
    """Run a `git diff` invocation; on failure, print and exit(2)."""
    try:
        result = subprocess.run(
            ["git", "diff", *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        sys.stderr.write(
            f"HF1 path-guard: cannot invoke `git` ({context}); "
            "refusing to allow commit. Install git or configure environment.\n"
        )
        sys.exit(2)
    if result.returncode != 0:
        sys.stderr.write(
            f"HF1 path-guard: `git diff {' '.join(args)}` failed "
            f"(rc={result.returncode}, context={context}); "
            "refusing to allow commit.\n"
            f"stderr: {result.stderr.strip()}\n"
        )
        sys.exit(2)
    return result.stdout


def get_staged_paths() -> list[str]:
    """Run ``git diff --cached --name-status -z`` and return all paths
    affected by the staged index, including both sides of renames/
    copies and the path of staged deletions.

    Returns empty list if git is missing, the call fails, or there is
    nothing staged. The guard's caller treats empty as "nothing to
    check" → exit 0.
    """
    return parse_name_status_z(
        _run_git_diff(["--cached", "--name-status", "-z"], context="pre-commit mode")
    )


def get_paths_from_diff(ref: str) -> list[str]:
    """Run ``git diff <ref>...HEAD --name-status -z`` and return all
    paths in the diff, including both sides of renames/copies and
    deletions. Used by CI mode (``--from-diff <ref>``) to verify HF1
    compliance against a base ref.

    The triple-dot syntax (``<ref>...HEAD``) compares the merge base
    of ``<ref>`` and HEAD against HEAD, which matches the semantics
    of GitHub PR diffs.
    """
    return parse_name_status_z(
        _run_git_diff(
            [f"{ref}...HEAD", "--name-status", "-z"],
            context=f"CI mode (--from-diff {ref})",
        )
    )


def check_paths_and_report(paths: list[str]) -> int:
    """Pure check: take a path list, decide pass/fail, write report.

    Tests call this directly with synthetic paths; main() calls it after
    sourcing paths from the staged index.
    """
    if not paths:
        return 0

    violations = find_violations(paths)
    if not violations:
        return 0

    override_reason = os.environ.get("HF1_GUARD_OVERRIDE", "").strip()
    if override_reason:
        sys.stderr.write(f"HF1 OVERRIDE active. Reason: {override_reason}\n")
        sys.stderr.write("Files allowed past HF1 zone guard:\n")
        for p, entry in violations:
            sys.stderr.write(f"  - {p}\n      {entry.rule}  ({entry.adr_ref})\n")
        sys.stderr.write(
            "Local-only escape hatch: this hook cannot enforce that the\n"
            "  override reason is cited in the commit message or visible at\n"
            "  PR review. CI commit-trailer enforcement is FF-07's scope.\n"
            "  Until FF-07 lands, please cite this override in the commit\n"
            "  message manually so the reviewer can see it.\n"
        )
        return 0

    sys.stderr.write("HF1 forbidden-zone violation — commit rejected.\n\n")
    for p, entry in violations:
        sys.stderr.write(f"  - {p}\n      {entry.rule}\n      see {entry.adr_ref}\n")
    sys.stderr.write(
        "\nResolution paths (per ADR-011 §HF1 Recovery):\n"
        "  1. Open a new ADR (or amend via supersede) before touching this path.\n"
        "  2. If urgent, set HF1_GUARD_OVERRIDE='<reason>' and cite the reason\n"
        "     in the commit message; reviewer must accept the override at PR time.\n"
    )
    return 1


def main(argv: list[str]) -> int:
    """CLI entry point. Two modes:

    - **Default (pre-commit)**: source paths from staged index via
      ``git diff --cached``. Configured with ``pass_filenames: false``
      in ``.pre-commit-config.yaml`` so positional args are ignored
      (pre-commit's own filter would mask renames-old-side and deletes).

    - **--from-diff <ref>** (CI): source paths from the diff between
      ``<ref>`` and HEAD via ``git diff <ref>...HEAD``. Used by
      ``.github/workflows/ci.yml`` to enforce HF1 on every PR.

    For unit testing, call ``check_paths_and_report(paths)`` directly.
    """
    parser = argparse.ArgumentParser(
        description="HF1 forbidden-zone path guard (ADR-011 §HF1)."
    )
    parser.add_argument(
        "--from-diff",
        metavar="REF",
        default=None,
        help="CI mode: check paths in `git diff REF...HEAD` instead of "
        "the staged index. REF is typically `origin/main` or the PR base SHA.",
    )
    # Allow trailing positional args for pre-commit compat (ignored).
    parser.add_argument("positional", nargs="*", help=argparse.SUPPRESS)
    args = parser.parse_args(argv[1:])

    if args.from_diff:
        paths = get_paths_from_diff(args.from_diff)
    else:
        paths = get_staged_paths()
    return check_paths_and_report(paths)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
