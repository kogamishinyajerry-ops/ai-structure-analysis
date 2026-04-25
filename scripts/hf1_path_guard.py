#!/usr/bin/env python3
"""HF1 forbidden-zone path guard for AI-Structure-FEA (FF-06).

Implements automated detection of HF1 zone violations as specified in
ADR-011 §Hard-Floor Rules. Designed to run as a `pre-commit` local hook
receiving staged file paths via positional arguments
(`pass_filenames: true`).

The zone is hard-coded in this file by design — per FF-06 charter, the
guard must not parse ADR-011 markdown at runtime (too fragile against
typos/refactors). When ADR-011 §HF1 changes, the corresponding entry in
`ZONE` must be updated in the same PR (and that PR is itself an HF1
trigger, requiring a new/superseding ADR per ADR-011 §HF1 Recovery).

Override mechanism: setting `HF1_GUARD_OVERRIDE='<non-empty reason>'`
allows the commit through but emits a stderr warning that the reviewer
must see. The reason is required (empty string is treated as not set);
this mirrors ADR-011 §Calibration Mode practice for HF2.

Exit codes:
    0  no zone violation (or override active with reason)
    1  zone violation; commit rejected
    2  CLI usage error
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class ZoneEntry:
    path: str
    match: str  # "exact" | "prefix"
    rule: str
    adr_ref: str


# HF1 forbidden zone — sourced from ADR-011 §Hard-Floor Rules (Forbidden zone (HF1) 完整清单).
# Update both this list AND ADR-011 in the same PR if the zone changes.
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
        "HF1.6 — ADR-002 CalculiX 2.21 pin (docker-base/docker-probe/hot-smoke)",
        "ADR-011 §HF1 #6",
    ),
    ZoneEntry(
        "Makefile",
        "exact",
        "HF1.6 — ADR-002 CalculiX 2.21 pin (docker-base/docker-probe/hot-smoke)",
        "ADR-011 §HF1 #6",
    ),
    ZoneEntry(
        "golden_samples/", "prefix", "HF1.7 — golden samples are read-only", "ADR-011 §HF1 #7"
    ),
    ZoneEntry(
        "docs/governance/",
        "prefix",
        "HF1.8 — governance docs require new/superseding ADR",
        "ADR-011 §HF1 #8",
    ),
    ZoneEntry(
        "docs/adr/", "prefix", "HF1.8 — ADR docs require new/superseding ADR", "ADR-011 §HF1 #8"
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
    for p in paths:
        for entry in ZONE:
            if path_hits_zone(p, entry):
                hits.append((p, entry))
                break
    return hits


def main(argv: list[str]) -> int:
    paths = [a for a in argv[1:] if a]
    if not paths:
        # No staged files — pre-commit may invoke us with no args on amend.
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
            "Reviewer note: HF1_GUARD_OVERRIDE must be cited in the commit "
            "message and inspected at PR review time.\n"
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


if __name__ == "__main__":
    sys.exit(main(sys.argv))
