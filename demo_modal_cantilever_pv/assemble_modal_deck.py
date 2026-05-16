"""Assemble a CalculiX modal *FREQUENCY deck for the cantilever candidate.

FM-04a Phase 12 C. Tier 1 engineering candidate; not signed validation;
not benchmark agreement.

Reads a gmsh-emitted .inp (from cantilever.geo via
``gmsh cantilever.geo -3 -format inp -o cantilever.inp``) and rewrites
it as a CalculiX-runnable modal-extraction deck:

  - Material: SA-516 Gr.70 properties (E = 210 GPa, nu = 0.30, density = 7850 kg/m^3).
    These are the same engineering-mean numbers used in the Phase 12 A
    smoke validation; not signed material data.
  - Boundary: clamped face (physical surface 200) gets all 6 DOFs fixed.
  - Step: *FREQUENCY, SOLVER=SPOOLES extracting 10 modes.
  - Output: NODE FILE U + PE; EL FILE S, ENER; NODE PRINT U; EL PRINT S.

This module is intentionally read-only with respect to project artifacts;
it writes only into the demo directory. The actual CalculiX subprocess
is launched by ``run_modal_e2e_demo.py``, not here.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent

# ----------------------------------------------------------------------
# Material + boundary SSOTs (engineering-mean, not signed data).
# ----------------------------------------------------------------------

YOUNGS_MODULUS_PA = 210.0e9
POISSON_RATIO = 0.30
DENSITY_KG_M3 = 7850.0

CLAMPED_FACE_PHYSICAL = 200  # cantilever.geo Physical Surface tag
BEAM_VOLUME_PHYSICAL = 100   # cantilever.geo Physical Volume tag
MODE_COUNT = 10


def _calculix_block_for_freq(n_modes: int = MODE_COUNT) -> str:
    """Return the CalculiX-runnable header + step block that pairs
    with the gmsh-emitted node/element blocks. The reviewer can replay
    this exactly by running ``ccx solve`` after gmsh has emitted the
    mesh."""
    return dedent(f"""
        ** FM-04a Phase 12 C — modal cantilever candidate
        ** Tier 1 engineering candidate; not signed validation;
        ** not benchmark agreement.

        *MATERIAL, NAME=STEEL_SA516
        *ELASTIC
        {YOUNGS_MODULUS_PA:.6E}, {POISSON_RATIO}
        *DENSITY
        {DENSITY_KG_M3}

        *SOLID SECTION, ELSET=PSURF_{BEAM_VOLUME_PHYSICAL}, MATERIAL=STEEL_SA516

        *BOUNDARY
        PSURF_{CLAMPED_FACE_PHYSICAL}, 1, 6, 0.0

        *STEP
        *FREQUENCY, SOLVER=SPOOLES
        {n_modes}

        *NODE FILE
        U, PE
        *EL FILE
        S, ENER
        *NODE PRINT, NSET=NALL
        U
        *EL PRINT, ELSET=EALL
        S
        *END STEP
        """).strip()


def assemble(
    gmsh_inp_path: Path,
    out_deck_path: Path,
    *,
    n_modes: int = MODE_COUNT,
) -> Path:
    """Read ``gmsh_inp_path`` (gmsh's emitted CalculiX-style .inp with
    *NODE / *ELEMENT / *NSET / *ELSET blocks), append the modal step
    block, and write to ``out_deck_path``.

    Returns the path written (so a caller can chain).
    """
    gmsh_text = gmsh_inp_path.read_text(encoding="utf-8")
    step_block = _calculix_block_for_freq(n_modes=n_modes)
    out_deck_path.write_text(gmsh_text + "\n" + step_block + "\n", encoding="utf-8")
    return out_deck_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gmsh-inp",
        type=Path,
        default=Path(__file__).resolve().parent / "cantilever.inp",
    )
    parser.add_argument(
        "--out-deck",
        type=Path,
        default=Path(__file__).resolve().parent / "solve.inp",
    )
    parser.add_argument(
        "--n-modes", type=int, default=MODE_COUNT,
    )
    args = parser.parse_args(argv)
    out = assemble(args.gmsh_inp, args.out_deck, n_modes=args.n_modes)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
