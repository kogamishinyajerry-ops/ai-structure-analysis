"""Analyze the extended PV cylinder candidate's CalculiX output.

FM-04a Phase 12 C. Tier 1 engineering candidate; not signed validation;
not benchmark agreement.

Reuses ``demo_cylinder_pv/analyze_results.py``'s Lame analytical cross-
check + ASME §5.5 SCL computation; only the P / L SSOTs differ.

The PV-extended case stresses Lame closed-form solution scaling: the
analytical hoop / radial / axial stresses scale linearly with internal
pressure (so doubling P doubles every stress component), and are
independent of cylinder length (Lame is a plane-strain result that
holds anywhere away from the end caps). The cohort dashboard sees
within-PV variation in absolute stress magnitudes while the rubric
axes (Lame cross-check / SCL convergence / allowable margin) remain
the same.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


INTERNAL_PRESSURE_MPA = 20.0
LENGTH_MM = 400.0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case-id", default="cylinder-pv-extended-candidate",
    )
    parser.add_argument(
        "--frd", type=Path,
        default=Path(__file__).resolve().parent / "solve.frd",
    )
    parser.add_argument(
        "--out", type=Path,
        default=Path(__file__).resolve().parent / "results.json",
    )
    args = parser.parse_args(argv)

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    # Re-use the existing PV analyzer's stress-linearization + Lame
    # cross-check. The base script supports a --case-id parameter so
    # the same code path serves both baseline and extended cases.
    from demo_cylinder_pv.analyze_results import (  # type: ignore[import-not-found]
        run_analysis,
    )
    summary = run_analysis(
        frd_path=args.frd,
        case_id=args.case_id,
        internal_pressure_mpa=INTERNAL_PRESSURE_MPA,
    )
    args.out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
