"""Stiff modal cantilever — parse + cross-check.

FM-04a Phase 12 C. Tier 1 engineering candidate; not signed validation;
not benchmark agreement.

Builds the same modal_summary structure as the 50 mm canonical case,
but against the 75 mm × 75 mm beam SSOT.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


STIFF_BEAM_SIDE_M = 0.075


def main(argv: list[str] | None = None) -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from app.domain.modal_extraction import (
        CantileverBeamSpec,
        parse_modal_dat,
    )
    from demo_modal_cantilever_pv.analyze_modal_results import (  # noqa: E402
        build_modal_summary,
    )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dat", type=Path,
        default=Path(__file__).resolve().parent / "solve.dat",
    )
    parser.add_argument(
        "--case-id", default="modal-cantilever-stiff-candidate",
    )
    parser.add_argument(
        "--out", type=Path,
        default=Path(__file__).resolve().parent / "results.json",
    )
    args = parser.parse_args(argv)
    beam = CantileverBeamSpec(
        length_m=1.0,
        youngs_modulus_pa=210.0e9,
        density_kg_per_m3=7850.0,
        inertia_m4=(STIFF_BEAM_SIDE_M**4) / 12.0,
        area_m2=STIFF_BEAM_SIDE_M**2,
    )
    result = parse_modal_dat(args.dat, case_id=args.case_id)
    summary = build_modal_summary(result, beam)
    args.out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
