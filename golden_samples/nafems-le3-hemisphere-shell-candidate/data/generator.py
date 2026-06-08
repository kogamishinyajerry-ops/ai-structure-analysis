"""NAFEMS LE3 "Hemispherical shell with point loads" — real CalculiX solve.

================================  HONEST FINDING  ============================
This is NOT a tier_2_validated public-benchmark agreement. It is a deliberately
recorded SOLVER-CAPABILITY-LIMIT study (Tier-0/1: software-path evidence +
documented formulation gap).

ccx 2.23 converges to ux@A = +0.2004 m, which is +8.3% ABOVE the NAFEMS thin-shell
reference of 0.185 m (NAFEMS TNSB Rev.3, Test LE3). The gap is CONVERGED — it is
stable across mesh refinement (na = 16 -> 40 all land 0.1998 -> 0.2004) and across
element formulation (S8R reduced-integration AND S8 full-integration both converge
to ~0.2004; S8 merely locks at coarse meshes then climbs to the same value).

ROOT CAUSE (well understood, not a bug): CalculiX has no true thin-shell (Kirchhoff
/Mindlin) element. Every shell is EXPANDED to a solid brick — S8R -> C3D20R, S6 ->
C3D15. A concentrated (point) load applied to a solid shell produces a local 3-D
"dimple" through the thickness that thin-shell theory does not contain. For this
very thin (R/t = 10/0.04 = 250), bending-dominated, point-loaded shell, that local
flexibility adds ~8% to the displacement read AT the loaded node.

CROSS-CHECK (independent, free): Altair OptiStruct OS-V:0030 with CQUAD4 (a true
first-order thin shell) converges DOWN to the reference — normalized result
0.9865 -> 1.0200 -> 1.0076 -> 1.0032 -> 1.0016 at 4/8/16/32/64 per-edge (i.e.
~0.1853 at 64x64). ccx (solid-shell) converges UP to 1.083x. The two element
FAMILIES bracket the answer differently; this is the documented thin-shell-vs-
solid-shell divergence under a point load, NOT a modelling error on either side.

CONSEQUENCE: LE3-as-a-point-load-displacement benchmark is a poor fit for ccx.
We record the honest number and its cause rather than (a) cherry-picking a coarse
mesh that happens to read ~0.185 on the way up, or (b) distributing the point load
to soften the dimple (that would be gaming the target). Thin-shell benchmarks
(LE2/LE3/LE5) are outside ccx's clean-agreement envelope; ccx's strengths are
solid stress (see LE10) and solid thermo-elastic / eigenvalue physics.

DELIBERATELY KEPT OUT OF THE VALIDATED COHORT: there is no cross_check_verdict.yaml
in this directory (so the V2-0 residual-floor glob never admits it) and LE3 is NOT
in CLAIM_TIER_REGISTRY (so the tier_2 overlay never promotes it). The machine-
readable summary lives in solver_limit_finding.yaml (a non-verdict filename).
=============================================================================

Pipeline (same shape as LE10/LE11): author gmsh meridian arc -> revolve pi/2 to a
spherical-quad shell patch -> classify nodes -> write a ccx S8R/S6 deck -> solve
via tools.calculix_driver.run_solve -> read ux at A from the .frd BY COORDINATE.

  python golden_samples/nafems-le3-hemisphere-shell-candidate/data/generator.py [--ladder]

Geometry / material / load (NAFEMS LE3, quarter model by double symmetry):
  R = 10 m (mid-surface), t = 0.04 m, E = 68.25 GPa, nu = 0.30
  Two pairs of 4 kN point loads on the equator free edge (one pair outward on the
  X axis, one pair inward on the Y axis). In the 90-deg quarter the loaded points
  A=(R,0,0) and C=(0,R,0) each lie ON a symmetry plane, so each carries HALF the
  4 kN pair = 2 kN: Fx=+2 kN (outward) at A, Fy=-2 kN (inward) at C.
  BCs: uy=0 on the y=0 meridian edge (AE), ux=0 on the x=0 meridian edge (CE),
  uz=0 at the apex E=(0,0,R). Equator edge AC is free. (Translational-only — see
  the ccx-shell lesson below.)
  Target (thin-shell reference): ux@A = 0.185 m.

ccx-shell lessons baked in (each cost a debugging round in P0):
  1. Read displacement at the .frd node nearest the target COORDINATE — ccx
     renumbers/expands shell nodes, so the original input node id reads ~0.
  2. Symmetry is TRANSLATIONAL-ONLY. Constraining rotational DOFs 4/5/6 on the
     expanded-shell symmetry edges LOCKS the model rigid (ux@A collapses to ~7e-4).
     The translational uy=0 / ux=0 on the original shell nodes already propagates
     through the expanded thickness and enforces the symmetry correctly.
  3. Quadratic elements are mandatory: linear S4 (-> C3D8I) membrane-locks to
     ux@A ~ 4e-5 (rigid). S8R (-> C3D20R) is the working element.
"""

from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path

# ---- problem constants (SI: m, Pa, N) --------------------------------------
R: float = 10.0          # mid-surface radius (m)
T: float = 0.04          # shell thickness (m)
E_PA: float = 68.25e9    # Young's modulus (Pa)
NU: float = 0.30         # Poisson ratio
P_QUARTER_N: float = 2000.0   # N per loaded point (4 kN pair, halved on the symmetry plane)
TARGET_UX_A_M: float = 0.185  # NAFEMS thin-shell reference (m)
CANONICAL_NA: int = 32        # converged rung pinned as the headline ccx value
TOL_COORD: float = 1e-4       # coordinate-match tolerance for node identification (m)

REPO = Path(__file__).resolve().parents[3]

GEO_TEMPLATE = """SetFactory("Built-in");
Mesh.SecondOrderIncomplete = 1;
R = {R}; na = {na}; nt = {nt};
Point(1) = {{0, 0, 0}};       // sphere centre O (construction only)
Point(2) = {{0, 0, R}};       // pole E
Point(3) = {{R, 0, 0}};       // equator point A (on +X)
Circle(1) = {{2, 1, 3}};      // meridian arc E->A about centre O (radius R)
Transfinite Curve {{1}} = na + 1;
Extrude {{ {{0,0,1}}, {{0,0,0}}, Pi/2 }} {{ Curve{{1}}; Layers{{nt}}; Recombine; }}
"""


def run_gmsh(na: int, nt: int, work: Path) -> tuple[dict, list, list]:
    """Mesh a quarter spherical shell patch; return (nodes, quad8, tri6).

    Rotation about z preserves distance from the origin, so every surface node
    lands EXACTLY on R (asserted). gmsh meshes the pole row as 6-node triangles
    (CPS6), avoiding degenerate quads.
    """
    geo = work / "le3.geo"
    inp = work / "le3.inp"
    geo.write_text(GEO_TEMPLATE.format(R=R, na=na, nt=nt))
    subprocess.run(
        ["gmsh", "-2", "-order", "2", str(geo), "-o", str(inp), "-format", "inp", "-v", "0"],
        check=True,
        capture_output=True,
    )
    nodes: dict[int, tuple[float, float, float]] = {}
    quads: list[tuple[int, list[int]]] = []
    tris: list[tuple[int, list[int]]] = []
    mode = None
    for line in inp.read_text().splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("*"):
            u = s.upper()
            if u.startswith("*NODE"):
                mode = "n"
            elif u.startswith("*ELEMENT"):
                mode = "q" if "CPS8" in u else ("t" if "CPS6" in u else None)
            else:
                mode = None
            continue
        p = [x.strip() for x in s.split(",")]
        if mode == "n":
            nodes[int(p[0])] = (float(p[1]), float(p[2]), float(p[3]))
        elif mode == "q":
            quads.append((int(p[0]), [int(x) for x in p[1:9]]))
        elif mode == "t":
            tris.append((int(p[0]), [int(x) for x in p[1:7]]))
    used: set[int] = set()
    for _, c in quads + tris:
        used.update(c)
    nodes = {n: xyz for n, xyz in nodes.items() if n in used}  # drop construction centre O
    radii = [math.sqrt(sum(c * c for c in xyz)) for xyz in nodes.values()]
    if not all(abs(r - R) < 1e-3 for r in radii):
        raise RuntimeError(
            f"off-sphere node(s): r in [{min(radii):.5f}, {max(radii):.5f}], expected {R}"
        )
    return nodes, quads, tris


def _dist2(p: tuple[float, float, float], q: tuple[float, float, float]) -> float:
    return sum((a - b) ** 2 for a, b in zip(p, q, strict=True))


def nearest(nodes: dict, target: tuple[float, float, float]) -> int:
    return min(nodes, key=lambda n: _dist2(nodes[n], target))


def write_deck(nodes: dict, quads: list, tris: list, path: Path) -> tuple[int, int, int]:
    nA = nearest(nodes, (R, 0.0, 0.0))
    nC = nearest(nodes, (0.0, R, 0.0))
    nE = nearest(nodes, (0.0, 0.0, R))
    for nid, want in ((nA, (R, 0, 0)), (nC, (0, R, 0)), (nE, (0, 0, R))):
        d = math.dist(nodes[nid], want)
        if d > TOL_COORD:
            raise RuntimeError(
                f"node {nid} at {nodes[nid]} is {d:.2e} m from target {want} (> {TOL_COORD})"
            )
    L = ["*HEADING", "NAFEMS LE3 hemispherical shell point loads (ccx solid-shell, SI)", "*NODE"]
    for n in sorted(nodes):
        x, y, z = nodes[n]
        L.append(f"{n}, {x:.10f}, {y:.10f}, {z:.10f}")
    L.append("*ELEMENT,TYPE=S8R,ELSET=EQ")
    for eid, c in quads:
        L.append(f"{eid}, " + ", ".join(map(str, c)))
    if tris:
        L.append("*ELEMENT,TYPE=S6,ELSET=ET")
        for eid, c in tris:
            L.append(f"{eid}, " + ", ".join(map(str, c)))
    L += ["*MATERIAL,NAME=STEEL", "*ELASTIC", f"{E_PA}, {NU}",
          "*SHELL SECTION,ELSET=EQ,MATERIAL=STEEL", f"{T}"]
    if tris:
        L += ["*SHELL SECTION,ELSET=ET,MATERIAL=STEEL", f"{T}"]
    # TRANSLATIONAL-only symmetry (rotational DOFs would lock the expanded shell).
    ysym = [n for n in nodes if abs(nodes[n][1]) < TOL_COORD]   # y=0 meridian edge AE
    xsym = [n for n in nodes if abs(nodes[n][0]) < TOL_COORD]   # x=0 meridian edge CE
    L.append("*BOUNDARY")
    for n in ysym:
        L.append(f"{n}, 2, 2")
    for n in xsym:
        L.append(f"{n}, 1, 1")
    L.append(f"{nE}, 3, 3")        # apex E: uz=0 (removes z rigid-body mode)
    L += ["*STEP", "*STATIC", "*CLOAD",
          f"{nA}, 1, {P_QUARTER_N}",     # A: +X outward
          f"{nC}, 2, {-P_QUARTER_N}",    # C: -Y inward
          "*NODE FILE", "U", "*END STEP"]
    path.write_text("\n".join(L) + "\n")
    return nA, nC, nE


def read_ux_at(frd_path: Path, target: tuple[float, float, float]) -> float:
    """Read ux at the .frd node nearest `target` coordinate.

    ccx expands shells and renumbers nodes, so the original input id reads ~0;
    the real displacement lives on the expanded node sitting at the coordinate.
    """
    coords: dict[int, tuple[float, float, float]] = {}
    disp: dict[int, tuple[float, float, float]] = {}
    mode = None
    for line in Path(frd_path).read_text().splitlines():
        if line.startswith("    2C"):
            mode = "N"
            continue
        if line.startswith(" -4") and "DISP" in line:
            mode = "U"
            continue
        if line.startswith(" -3"):
            if mode == "N":
                mode = None
            continue
        if mode in ("N", "U") and line.startswith(" -1"):
            nid = int(line[3:13])
            vals = (float(line[13:25]), float(line[25:37]), float(line[37:49]))
            if mode == "N":
                coords[nid] = vals
            else:
                disp[nid] = vals
    nid = min(coords, key=lambda n: _dist2(coords[n], target))
    return disp.get(nid, (0.0, 0.0, 0.0))[0]


def solve_one(na: int, nt: int | None = None) -> dict:
    nt = na if nt is None else nt
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        nodes, quads, tris = run_gmsh(na, nt, work)
        deck = work / "solve.inp"
        write_deck(nodes, quads, tris, deck)
        sys.path.insert(0, str(REPO))
        from tools.calculix_driver import run_solve

        res = run_solve(deck, work, timeout_s=900)
        uxA = read_ux_at(Path(res["frd_path"]), (R, 0, 0)) if res.get("frd_path") else None
        resid = (uxA - TARGET_UX_A_M) / TARGET_UX_A_M * 100 if uxA is not None else None
        return {
            "na": na, "nt": nt, "shell_nodes": len(nodes),
            "quads": len(quads), "tris": len(tris),
            "ux_A_m": uxA, "residual_pct_vs_thin_shell_ref": resid,
            "converged": res.get("converged"), "ccx_version": res.get("ccx_version"),
        }


def main() -> None:
    ladder = "--ladder" in sys.argv
    rungs = [8, 16, 24, 32, 40] if ladder else [CANONICAL_NA]
    print(f"NAFEMS LE3 ux@A (thin-shell ref {TARGET_UX_A_M} m), ccx S8R solid-shell quarter:")
    print("  *** HONEST: ccx -> ~0.2004 m (+8.3%); documented solid-shell gap, NOT agreement ***")
    for r in rungs:
        out = solve_one(r)
        ux = out["ux_A_m"]
        if ux is None:
            print(f"  na={r:2d}: SOLVE FAILED")
            continue
        print(f"  na={out['na']:2d} | shell_nodes={out['shell_nodes']:5d} "
              f"q={out['quads']:4d} t={out['tris']:2d} | ux@A={ux:+.5f} m  "
              f"resid={out['residual_pct_vs_thin_shell_ref']:+.2f}%  conv={out['converged']}")


if __name__ == "__main__":
    main()
