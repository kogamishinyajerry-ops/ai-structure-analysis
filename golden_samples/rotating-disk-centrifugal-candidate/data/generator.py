"""Rotating annular disk under centrifugal load — real CalculiX agreement.

The project's THIRD public-benchmark agreement, and its FIRST with a CENTRIFUGAL
(rotational body-force) load — a genuinely new load physics after LE10 (mechanical
pressure / bending stress) and LE11 (imposed temperature / thermal stress).

Benchmark: a thin annular disk (inner radius a, outer radius b) rotating at angular
velocity omega about its axis. Classical plane-stress elasticity (Timoshenko &
Goodier, "Theory of Elasticity", 3rd ed., Art. 32 "Rotating Disks") gives a
closed-form stress field:

    sigma_r(r)     = (3+nu)/8 * rho*w^2 * [ b^2 + a^2 - a^2 b^2 / r^2 - r^2 ]
    sigma_theta(r) = (3+nu)/8 * rho*w^2 * [ b^2 + a^2 + a^2 b^2 / r^2
                                            - (1+3nu)/(3+nu) * r^2 ]

The engineering-relevant peak is the hoop stress at the inner bore (r = a), where
the radial stress vanishes (free inner edge):

    sigma_theta(a) = rho*w^2 / 4 * [ (3+nu) b^2 + (1-nu) a^2 ]   <-- HEADLINE TARGET

WHY THIS IS A CLEAN ccx AGREEMENT (unlike LE3 / FV52):
The reference is a CONTINUUM-ELASTICITY quantity — the exact PLANE-STRESS stress field
of the disk — NOT a reduced-KINEMATIC plate/shell/beam theory. ccx solves full 3-D
elasticity; a thin solid converges to the plane-stress elasticity solution directly
(cf. LE10 +1.08%, LE11 +0.38%). LE3 (thin-shell displacement) and FV52 (Mindlin-plate
frequency) were ~6-8% off precisely because their references assume a displacement
KINEMATICS that full 3-D elasticity does not obey. A plane-stress disk stress field
has no such reduced-kinematic gap.

Model (plays to ccx's proven C3D20 strength, like LE10/LE11):
  - 3-D thin QUARTER annulus (double symmetry), C3D20 hexahedra.
  - Half the thickness modelled: uz=0 on the z=0 MID-PLANE (a true symmetry plane),
    z=t/2 top surface free -> plane-stress state (sigma_z ~ 0) for a thin disk.
  - Radial-edge symmetry: uy=0 on the y=0 edge, ux=0 on the x=0 edge.
  - Centrifugal body force via ccx `*DLOAD ... CENTRIF` (magnitude = omega^2, axis
    = global z through the origin).
  - sigma_theta at the bore is read as SYY at the node on the +x axis at r=a
    (there the hoop direction theta coincides with global y).

  python golden_samples/rotating-disk-centrifugal-candidate/data/generator.py [--ladder] [--profile]

Reference: closed-form Timoshenko & Goodier (above) — a canonical plane-stress elasticity
result reproduced across standard mechanics-of-materials/elasticity texts and FE
verification manuals (ANSYS APDL VM, code_aster rotating-disk cases). Tier: registry
baseline tier_1_candidate, overlay-promoted to tier_2_validated on the PASS verdict
(real ccx 2.23); public-benchmark agreement; NOT signed validation (no independent
reviewer signoff per ADR-023 / ADR-027 G-2).
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

# ---- problem constants (SI: m, Pa, kg/m^3, rad/s) --------------------------
A: float = 0.2            # inner radius (m)
B: float = 1.0            # outer radius (m)
T_HALF: float = 0.05      # HALF thickness modelled (mid-plane symmetry); full disk = 0.10 m, thin
E_PA: float = 200.0e9     # Young's modulus (Pa)
NU: float = 0.30          # Poisson ratio
RHO: float = 7850.0       # density (kg/m^3), steel
OMEGA: float = 100.0      # angular velocity (rad/s)
CANONICAL_NR: int = 48    # converged radial/circumferential divisions (headline rung, +0.06%)
TOL_COORD: float = 1e-5

REPO = Path(__file__).resolve().parents[3]
W2: float = OMEGA * OMEGA


def sigma_theta_analytic(r: float) -> float:
    return (3 + NU) / 8 * RHO * W2 * (B * B + A * A + A * A * B * B / (r * r)
                                      - (1 + 3 * NU) / (3 + NU) * r * r)


def sigma_r_analytic(r: float) -> float:
    return (3 + NU) / 8 * RHO * W2 * (B * B + A * A - A * A * B * B / (r * r) - r * r)


# Headline target: hoop stress at the inner bore r = a (free edge, sigma_r = 0).
TARGET_SIGMA_THETA_A_PA: float = RHO * W2 / 4 * ((3 + NU) * B * B + (1 - NU) * A * A)

GEO_TEMPLATE = """SetFactory("Built-in");
Mesh.SecondOrderIncomplete = 1;
a = {A}; b = {B}; nr = {nr}; nc = {nc}; th = {TH}; nz = {nz};
Point(1) = {{0, 0, 0}};            // centre (construction only)
Point(2) = {{a, 0, 0}};            // inner radius on +x
Point(3) = {{b, 0, 0}};            // outer radius on +x
Point(4) = {{0, b, 0}};            // outer radius on +y
Point(5) = {{0, a, 0}};            // inner radius on +y
Line(1) = {{2, 3}};                // radial edge on x-axis (a->b)
Circle(2) = {{3, 1, 4}};           // outer arc r=b
Line(3) = {{4, 5}};                // radial edge on y-axis (b->a)
Circle(4) = {{5, 1, 2}};           // inner arc r=a
Curve Loop(1) = {{1, 2, 3, 4}}; Plane Surface(1) = {{1}};
Transfinite Curve {{1, 3}} = nr + 1;   // radial divisions
Transfinite Curve {{2, 4}} = nc + 1;   // circumferential divisions
Transfinite Surface {{1}}; Recombine Surface {{1}};
Extrude {{0, 0, th}} {{ Surface{{1}}; Layers{{nz}}; Recombine; }}
"""


def run_gmsh(nr: int, nc: int, nz: int, work: Path) -> tuple[dict, list]:
    geo = work / "disk.geo"
    inp = work / "disk.inp"
    geo.write_text(GEO_TEMPLATE.format(A=A, B=B, nr=nr, nc=nc, TH=T_HALF, nz=nz))
    subprocess.run(
        ["gmsh", "-3", "-order", "2", str(geo), "-o", str(inp), "-format", "inp", "-v", "0"],
        check=True,
        capture_output=True,
    )
    nodes: dict[int, tuple[float, float, float]] = {}
    hexes: list[tuple[int, list[int]]] = []
    mode = None
    cur: list[int] | None = None
    for line in inp.read_text().splitlines():
        s = line.strip()
        if s.startswith("*"):
            u = s.upper()
            mode = "n" if u.startswith("*NODE") else ("e" if "C3D20" in u else None)
            continue
        if mode == "n" and s:
            p = s.split(",")
            nodes[int(p[0])] = (float(p[1]), float(p[2]), float(p[3]))
        elif mode == "e" and s:
            v = [int(x) for x in s.split(",") if x.strip()]
            cur = v if cur is None else cur + v
            if len(cur) >= 21:  # id + 20 nodes (C3D20 connectivity wraps over 2 lines)
                hexes.append((cur[0], cur[1:21]))
                cur = None
    used: set[int] = set()
    for _, c in hexes:
        used.update(c)
    nodes = {n: xyz for n, xyz in nodes.items() if n in used}
    return nodes, hexes


def write_deck(nodes: dict, hexes: list, path: Path) -> None:
    L = ["*HEADING", "rotating annular disk, centrifugal load (ccx C3D20, SI)", "*NODE"]
    for n in sorted(nodes):
        x, y, z = nodes[n]
        L.append(f"{n}, {x:.9f}, {y:.9f}, {z:.9f}")
    L.append("*ELEMENT,TYPE=C3D20,ELSET=EALL")
    for eid, c in hexes:
        L.append(f"{eid}, " + ", ".join(map(str, c[:8])) + ",")
        L.append("     " + ", ".join(map(str, c[8:])))
    L += ["*MATERIAL,NAME=STEEL", "*ELASTIC", f"{E_PA}, {NU}", "*DENSITY", f"{RHO}",
          "*SOLID SECTION,ELSET=EALL,MATERIAL=STEEL"]
    L.append("*BOUNDARY")
    for n in nodes:
        if abs(nodes[n][1]) < TOL_COORD:
            L.append(f"{n}, 2, 2")      # y=0 radial edge: uy=0 (symmetry)
        if abs(nodes[n][0]) < TOL_COORD:
            L.append(f"{n}, 1, 1")      # x=0 radial edge: ux=0 (symmetry)
        if abs(nodes[n][2]) < TOL_COORD:
            L.append(f"{n}, 3, 3")      # z=0 mid-plane: uz=0 (symmetry)
    L += ["*STEP", "*STATIC", "*DLOAD",
          f"EALL, CENTRIF, {W2}, 0., 0., 0., 0., 0., 1.",   # omega^2 about global z through origin
          "*EL FILE", "S", "*END STEP"]
    path.write_text("\n".join(L) + "\n")


def read_stress(frd_path: Path) -> tuple[dict, dict]:
    """Return (coords, stress) by node id. stress = [SXX,SYY,SZZ,SXY,SYZ,SZX]."""
    coords: dict[int, tuple[float, float, float]] = {}
    stress: dict[int, list[float]] = {}
    mode = None
    for line in Path(frd_path).read_text().splitlines():
        if line.startswith("    2C"):
            mode = "N"
            continue
        if line.startswith(" -4"):
            mode = "S" if "STRESS" in line else None  # ignore ERROR / other -4 blocks
            continue
        if line.startswith(" -3"):
            mode = None                                # end of the current data block
            continue
        if mode == "N" and line.startswith(" -1"):
            coords[int(line[3:13])] = (
                float(line[13:25]), float(line[25:37]), float(line[37:49]))
        elif mode == "S" and line.startswith(" -1"):
            nid = int(line[3:13])
            stress[nid] = [float(line[13 + 12 * i:25 + 12 * i]) for i in range(6)]
    return coords, stress


def _dist2(p: tuple[float, float, float], q: tuple[float, float, float]) -> float:
    return sum((a - b) ** 2 for a, b in zip(p, q, strict=True))


def _node_at(coords: dict, target: tuple[float, float, float]) -> int:
    return min(coords, key=lambda n: _dist2(coords[n], target))


def solve_one(nr: int, nc: int | None = None, nz: int = 2) -> dict:
    nc = nr if nc is None else nc
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        nodes, hexes = run_gmsh(nr, nc, nz, work)
        deck = work / "solve.inp"
        write_deck(nodes, hexes, deck)
        sys.path.insert(0, str(REPO))
        from tools.calculix_driver import run_solve

        res = run_solve(deck, work, timeout_s=900)
        if not res.get("frd_path"):
            return {"nr": nr, "nc": nc, "nz": nz, "sigma_theta_a_pa": None,
                    "converged": res.get("converged")}
        coords, stress = read_stress(Path(res["frd_path"]))
        nid = _node_at(coords, (A, 0.0, T_HALF))   # inner bore on +x axis, top surface
        syy = stress[nid][1]                        # hoop = SYY on the +x axis
        resid = (syy - TARGET_SIGMA_THETA_A_PA) / TARGET_SIGMA_THETA_A_PA * 100
        return {
            "nr": nr, "nc": nc, "nz": nz, "nodes": len(nodes), "elems": len(hexes),
            "bore_node_xyz": tuple(round(c, 4) for c in coords[nid]),
            "sigma_theta_a_pa": syy, "residual_pct": resid,
            "converged": res.get("converged"), "ccx_version": res.get("ccx_version"),
        }


def profile_check(nr: int = CANONICAL_NR) -> None:
    """Compare sigma_theta(r) / sigma_r(r) ALONG THE +x RADIAL LINE to the analytic
    plane-stress field (one radial line at the top surface, not a circumferential or
    through-thickness sweep)."""
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        nodes, hexes = run_gmsh(nr, nr, 2, work)
        deck = work / "solve.inp"
        write_deck(nodes, hexes, deck)
        sys.path.insert(0, str(REPO))
        from tools.calculix_driver import run_solve

        res = run_solve(deck, work, timeout_s=900)
        coords, stress = read_stress(Path(res["frd_path"]))
        # sample +x-axis nodes (y~0, z~T_HALF): SYY=sigma_theta, SXX=sigma_r
        axis = sorted(
            (n for n in coords if abs(coords[n][1]) < 1e-4 and abs(coords[n][2] - T_HALF) < 1e-4),
            key=lambda n: coords[n][0])
        print("  r (m)   sigma_theta ccx/anal (MPa)        sigma_r ccx/anal (MPa)")
        for n in axis:
            r = coords[n][0]
            if r < A - 1e-6:
                continue
            st_c, sr_c = stress[n][1], stress[n][0]
            st_a, sr_a = sigma_theta_analytic(r), sigma_r_analytic(r)
            print(f"  {r:5.3f}  {st_c/1e6:8.3f} / {st_a/1e6:8.3f}  ({(st_c-st_a)/st_a*100:+5.2f}%)"
                  f"   {sr_c/1e6:8.3f} / {sr_a/1e6:8.3f}")


def main() -> None:
    if "--profile" in sys.argv:
        print(f"Rotating disk sigma_theta / sigma_r profile vs Timoshenko (nr={CANONICAL_NR}):")
        profile_check()
        return
    ladder = "--ladder" in sys.argv
    rungs = [20, 32, 48, 64, 80] if ladder else [CANONICAL_NR]
    tgt = TARGET_SIGMA_THETA_A_PA / 1e6
    print(f"Rotating annular disk: sigma_theta at bore r=a={A} m, target {tgt:.4f} MPa "
          f"(Timoshenko plane stress, omega={OMEGA} rad/s):")
    for r in rungs:
        out = solve_one(r)
        s = out["sigma_theta_a_pa"]
        if s is None:
            print(f"  nr={r:3d}: SOLVE FAILED")
            continue
        print(f"  nr={out['nr']:3d} nz={out['nz']} | nodes={out['nodes']:6d} el={out['elems']:5d} "
              f"| sigma_theta(a)={s/1e6:8.4f} MPa  resid={out['residual_pct']:+.2f}%  "
              f"conv={out['converged']}")


if __name__ == "__main__":
    main()
