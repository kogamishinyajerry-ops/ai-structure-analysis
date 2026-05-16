"""Assemble a CalculiX linear-static deck for the extended PV cylinder.

FM-04a Phase 12 C. Tier 1 engineering candidate; not signed validation;
not benchmark agreement.

Variant of ``demo_cylinder_pv/assemble_deck.py`` with:
  - Higher internal pressure P = 20 MPa (vs 10 MPa baseline).
  - Longer cylinder L = 400 mm (vs 200 mm baseline) — reflected in the
    geometry file ``cylinder_extended.geo``.

Same material (SA-516 Gr.70, E = 210 GPa, nu = 0.30), same axial
constraint topology (z-symmetric on z=0 + z=L planes), same wedge
symmetry on the radial faces.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from textwrap import dedent


INTERNAL_PRESSURE_MPA = 20.0  # vs 10 MPa baseline
YOUNGS_MODULUS_MPA = 210_000.0
POISSON_RATIO = 0.30
DENSITY_TONNE_MM3 = 7.85e-9  # tonne / mm^3 (CalculiX consistent unit set)


def _calculix_step_block(p_mpa: float = INTERNAL_PRESSURE_MPA) -> str:
    return dedent(f"""
        ** FM-04a Phase 12 C — extended PV cylinder candidate
        ** Tier 1 engineering candidate; not signed validation;
        ** not benchmark agreement. Internal pressure {p_mpa} MPa.

        *MATERIAL, NAME=STEEL_SA516
        *ELASTIC
        {YOUNGS_MODULUS_MPA}, {POISSON_RATIO}
        *DENSITY
        {DENSITY_TONNE_MM3}

        *SOLID SECTION, ELSET=PSURF_100, MATERIAL=STEEL_SA516

        ** Wedge symmetry boundary conditions on radial faces.
        ** (Same SSOT logic as demo_cylinder_pv/assemble_deck.py.)
        ** Axial symmetry: bottom and top axial faces fully constrained
        ** in z; in-plane motion still allowed in r-θ.
        *BOUNDARY
        PSURF_201, 3, 3, 0.0
        PSURF_202, 3, 3, 0.0

        *STEP
        *STATIC, SOLVER=SPOOLES
        *DLOAD
        PSURF_200, P, {p_mpa}

        *NODE FILE
        U, RF
        *EL FILE
        S, E
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
    pressure_mpa: float = INTERNAL_PRESSURE_MPA,
) -> Path:
    text = gmsh_inp_path.read_text(encoding="utf-8")
    step_block = _calculix_step_block(p_mpa=pressure_mpa)
    out_deck_path.write_text(text + "\n" + step_block + "\n", encoding="utf-8")
    return out_deck_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gmsh-inp", type=Path,
        default=Path(__file__).resolve().parent / "cylinder_extended.inp",
    )
    parser.add_argument(
        "--out-deck", type=Path,
        default=Path(__file__).resolve().parent / "solve.inp",
    )
    parser.add_argument(
        "--pressure-mpa", type=float, default=INTERNAL_PRESSURE_MPA,
    )
    args = parser.parse_args(argv)
    out = assemble(args.gmsh_inp, args.out_deck, pressure_mpa=args.pressure_mpa)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
