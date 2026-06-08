#!/usr/bin/env python3
"""FM-04a Phase 19 B — cylinder-pv-candidate cross-check runner CLI.

Tier 1 → Tier 2 promotion utility. Runs the analytical hoop-stress
cross-check (Lame thin-walled formula) against a real CalculiX wall-
coupon model with the same material + pressure + geometry, computes
the residual percentage, writes a verdict artifact to
``golden_samples/cylinder-pv-candidate/cross_check_verdict.yaml``.

The next module-load of :mod:`app.services.reporting._claim_tier`
reads the artifact and promotes ``cylinder-pv-candidate`` to
``tier_2_validated`` when the verdict is "PASS".

Usage:

    python scripts/cross_check_cylinder_pv.py [--ccx /opt/homebrew/bin/ccx]

Run from the repo root; it locates ``golden_samples/`` via the script
location.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

# Repo root is the directory containing this script's parent.
REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.cross_check import (  # noqa: E402
    run_cylinder_pv_cross_check,
    write_verdict_yaml,
)

NOMINAL_PRESSURE_PA = 5_000_000.0
NOMINAL_INNER_RADIUS_M = 1.0
NOMINAL_WALL_THICKNESS_M = 0.05


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ccx",
        default="/opt/homebrew/bin/ccx",
        help="Path to the ccx binary (default: /opt/homebrew/bin/ccx)",
    )
    parser.add_argument(
        "--material-id",
        default="steel-s355",
        help="Material library id (default: steel-s355)",
    )
    parser.add_argument(
        "--case-id",
        default="cylinder-pv-candidate",
        help="Candidate case id (default: cylinder-pv-candidate)",
    )
    args = parser.parse_args()

    case_golden = REPO_ROOT / "golden_samples" / args.case_id
    if not case_golden.is_dir():
        print(
            f"error: case golden dir {case_golden!s} does not exist",
            file=sys.stderr,
        )
        return 2

    # Run the cross-check in a tmp workspace; only the verdict
    # artifact lands in golden_samples (HF1.7b carve-out).
    with tempfile.TemporaryDirectory(prefix="phase19b-xcheck-") as tmp:
        case_dir = Path(tmp) / "phase19b-cli-candidate"
        case_dir.mkdir()
        print(
            f"Running cross-check on {args.case_id!r} with material "
            f"{args.material_id!r}, P={NOMINAL_PRESSURE_PA:.2e} Pa, "
            f"r={NOMINAL_INNER_RADIUS_M} m, t={NOMINAL_WALL_THICKNESS_M} m"
        )
        result = run_cylinder_pv_cross_check(
            case_dir,
            case_id=args.case_id,
            material_id=args.material_id,
            pressure_pa=NOMINAL_PRESSURE_PA,
            inner_radius_m=NOMINAL_INNER_RADIUS_M,
            wall_thickness_m=NOMINAL_WALL_THICKNESS_M,
            ccx_binary=args.ccx,
            timeout_sec=30.0,
        )

    print(f"  analytical: {result.analytical_pa:.3e} Pa")
    print(f"  observed:   {result.observed_pa:.3e} Pa")
    print(f"  residual:   {result.residual_pct:+.3f}%")
    print(f"  tolerance:  {result.tolerance_pct}%")
    print(f"  verdict:    {result.verdict}")

    artifact = write_verdict_yaml(case_golden, result)
    print(f"  wrote: {artifact}")

    if result.verdict == "PASS":
        print(
            f"  → on next import, app.services.reporting._claim_tier "
            f"will promote {args.case_id!r} to tier_2_validated"
        )
        return 0
    print("  → registry stays at tier_1_candidate")
    return 1


if __name__ == "__main__":
    sys.exit(main())
