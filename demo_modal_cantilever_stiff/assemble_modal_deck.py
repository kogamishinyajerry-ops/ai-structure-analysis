"""Stiff modal cantilever — assemble CalculiX *FREQUENCY deck.

FM-04a Phase 12 C. Tier 1 engineering candidate; not signed validation;
not benchmark agreement.

Thin variation of ``demo_modal_cantilever_pv/assemble_modal_deck.py``;
imports the shared module to avoid duplicating the assembly logic.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    # Re-use the canonical assembler from the 50mm demo.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from demo_modal_cantilever_pv.assemble_modal_deck import (  # noqa: E402
        assemble,
    )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gmsh-inp", type=Path,
        default=Path(__file__).resolve().parent / "cantilever_stiff.inp",
    )
    parser.add_argument(
        "--out-deck", type=Path,
        default=Path(__file__).resolve().parent / "solve.inp",
    )
    parser.add_argument("--n-modes", type=int, default=10)
    args = parser.parse_args(argv)
    out = assemble(args.gmsh_inp, args.out_deck, n_modes=args.n_modes)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
