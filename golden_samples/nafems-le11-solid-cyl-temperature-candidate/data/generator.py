"""NAFEMS LE11 "Solid Cylinder/Taper/Sphere — Temperature" — real ccx thermal-stress solve.

Second INDEPENDENT NAFEMS public-benchmark agreement for this repo (after LE10
thick-plate-pressure). Independent on every axis: thermoelastic physics (imposed
temperature field, NO mechanical load / NO *DLOAD), solid-of-revolution geometry,
and a different ccx keyword path (*INITIAL CONDITIONS,TYPE=TEMPERATURE +
*EXPANSION + *TEMPERATURE in a purely-mechanical *STATIC step — the exact recipe
ccx 2.23 ships in beamt.inp).

Pipeline mirrors the LE10 generator:
    author a gmsh .geo template -> `gmsh -3 file.geo -o out.inp -format inp`
    -> parse the Abaqus-format .inp (C3D20) -> classify node sets by coordinate
    -> compute the per-node temperature field T = sqrt(x^2+y^2) + z
    -> write a ccx deck -> run via tools.calculix_driver.run_solve
    -> read sigma_zz at point A from the .frd.

Geometry (axis of revolution = z; meridian authored in the x-z plane at y=0) is
ported verbatim from the FeenoX nafems-le11.geo (a FREE, runnable gmsh byte-oracle
in the same source family the LE10 geometry came from; FeenoX reproduces
sigma_z(A) = -105.04 MPa). Point A = (1, 0, 0), the inner-radius base corner.

Published target: sigma_zz(A) = -105 MPa (compressive, ccx tension-positive
convention), triangulated from 7 FREE independent reproductions (Abaqus-MIT,
FeenoX, bConverged, FEATool, Altair, OnScale, DIANA). NAFEMS TNSB Rev.3 (primary)
NOT purchased — same disclosed Tier-1/2 limitation as the LE10 candidate.

Usage:
    python generator.py            # canonical mesh, single solve
    python generator.py --ladder   # convergence ladder

Honesty boundary: Tier-1 engineering candidate / public-benchmark agreement.
NOT signed validation (no independent reviewer signoff per ADR-023 / ADR-027 G-2).
"""

from __future__ import annotations

import math
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]  # data -> nafems-le11-...-candidate -> golden_samples -> repo

# --- spec constants (FeenoX byte-oracle + NAFEMS LE11) ----------------------
E_PA, NU = 210.0e9, 0.30  # NAFEMS canonical (FeenoX .fee uses 2.11e11; 0.5% — noted)
ALPHA = 2.3e-4  # thermal expansion coefficient [1/degC]
TREF = 0.0  # stress-free reference temperature (T field is r+z, zero at origin base)
TARGET_PA = -105.0e6  # published NAFEMS LE11 reference sigma_zz at A (compressive)
TOL_PCT = 3.0
A_COORD = (1.0, 0.0, 0.0)  # point A: inner-radius base corner (FeenoX frame)
ZTOP = 1.0 * math.sin(math.pi / 4) + 0.345 + 0.345 + 0.400  # top face z
TOL_PLANE = 1e-4
CANONICAL_REFINE = 4  # canonical mesh refinement factor (finest converged rung; 1 = FeenoX-coarse)

# Meridian points (x, z) at y=0, ported verbatim from FeenoX nafems-le11.geo.
_S = math.sin(math.pi / 4)  # 0.70710678...
GEO_TEMPLATE = """SetFactory("Built-in");
g1 = {g1}; g2 = {g2}; g3 = {g3}; g4 = {g4}; nlay = {nlay};
s = Sin(Pi/4);
Point(1) = {{0, 0, 0}};
Point(2) = {{1.000, 0, 0}};
Point(3) = {{1.400, 0, 0}};
Point(4) = {{1.000*s, 0, 1.000*s}};
Point(5) = {{Sqrt(1.400^2-(1.000*s)^2), 0, 1.000*s}};
Point(6) = {{1.000*s, 0, 1.000*s+0.345+0.345}};
Point(7) = {{1.000,   0, 1.000*s+0.345+0.345}};
Point(8) = {{1.000*s, 0, 1.000*s+0.345+0.345+0.400}};
Point(9) = {{1.000,   0, 1.000*s+0.345+0.345+0.400}};
Circle(1) = {{2, 1, 4}};
Circle(2) = {{3, 1, 5}};
Line(3) = {{4, 6}};
Line(4) = {{6, 8}};
Line(5) = {{8, 9}};
Line(6) = {{9, 7}};
Line(7) = {{7, 5}};
Line(8) = {{3, 2}};
Line(9) = {{4, 5}};
Line(10) = {{6, 7}};
Curve Loop(1) = {{8, 1, 9, -2}};   Plane Surface(1) = {{1}};
Curve Loop(2) = {{3, 10, 7, -9}};  Plane Surface(2) = {{2}};
Curve Loop(3) = {{4, 5, 6, -10}};  Plane Surface(3) = {{3}};
Transfinite Curve {{1, 2}} = g1;
Transfinite Curve {{8, 9, 10, 5}} = g2;
Transfinite Curve {{3, 7}} = g3;
Transfinite Curve {{4, 6}} = g4;
Transfinite Surface {{1, 2, 3}};
Recombine Surface {{1, 2, 3}};
Extrude {{ {{0,0,1}}, {{0,0,0}}, Pi/2 }} {{ Surface{{1, 2, 3}}; Layers{{nlay}}; Recombine; }}
Mesh.ElementOrder = 2;
Mesh.SecondOrderIncomplete = 1;
"""

FACE_CORNERS = {
    1: (0, 3, 2, 1),
    2: (4, 5, 6, 7),
    3: (0, 1, 5, 4),
    4: (1, 2, 6, 5),
    5: (2, 3, 7, 6),
    6: (3, 0, 4, 7),
}


def run_gmsh(refine: int, inp: Path) -> None:
    geo = inp.with_suffix(".geo")
    geo.write_text(
        GEO_TEMPLATE.format(
            g1=4 * refine + 1,
            g2=2 * refine + 1,
            g3=5 * refine + 1,
            g4=2 * refine + 1,
            nlay=4 * refine,
        )
    )
    subprocess.run(
        ["gmsh", "-3", str(geo), "-o", str(inp), "-format", "inp", "-v", "1"],
        check=True,
        capture_output=True,
        text=True,
        timeout=600,
    )


def parse_inp(path: Path):
    nodes, elements, mode, pending, pid = {}, {}, None, None, None
    for raw in path.read_text(errors="ignore").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("*"):
            h = line.lower()
            if h.startswith("*node"):
                mode = "node"
            elif h.startswith("*element"):
                m = re.search(r"type\s*=\s*([A-Za-z0-9]+)", line)
                mode = "c3d20" if (m and m.group(1).upper() == "C3D20") else "skip"
                pending = pid = None
            else:
                mode = None
            continue
        if mode == "node":
            p = [s.strip() for s in line.split(",")]
            if len(p) >= 4:
                nodes[int(p[0])] = (float(p[1]), float(p[2]), float(p[3]))
        elif mode == "c3d20":
            ints = [int(s) for s in line.split(",") if s.strip()]
            if not ints:
                continue
            if pending is None:
                pid, pending = ints[0], ints[1:]
            else:
                pending.extend(ints)
            if len(pending) >= 20:
                elements[pid] = pending[:20]
                pending = pid = None
    return nodes, elements


def classify(nodes: dict) -> dict:
    """Node sets by coordinate after the pi/2 revolution about z.

    XSYM (x=0, the swept-to yz plane) -> ux=0; YSYM (y=0, the meridian xz plane)
    -> uy=0; ZBOT (z=0 base) -> uz=0; ZTOP (top face) -> uz=0. (FeenoX BCs:
    xz symmetry, yz symmetry, xy w=0, HIH'I' w=0.)
    """
    s = {k: set() for k in ("XSYM", "YSYM", "ZBOT", "ZTOP")}
    for nid, (x, y, z) in nodes.items():
        if abs(x) < TOL_PLANE:
            s["XSYM"].add(nid)
        if abs(y) < TOL_PLANE:
            s["YSYM"].add(nid)
        if abs(z) < TOL_PLANE:
            s["ZBOT"].add(nid)
        if abs(z - ZTOP) < TOL_PLANE:
            s["ZTOP"].add(nid)
    return s


def node_A(nodes: dict) -> int:
    """Nearest mesh node to point A = (1, 0, 0). A is an exact construction point
    (P2), so the nearest node must coincide with it; assert the distance is within
    tolerance so a geometry/sweep regression cannot silently validate a wrong node."""
    na = min(nodes, key=lambda n: math.dist(nodes[n], A_COORD))
    d = math.dist(nodes[na], A_COORD)
    if d > TOL_PLANE:
        raise RuntimeError(
            f"point A node {na} at {nodes[na]} is {d:.2e} m from {A_COORD} "
            f"(> {TOL_PLANE}); geometry/sweep regression?"
        )
    return na


def write_solve(nodes: dict, elements: dict, sets: dict, out: Path, etype: str) -> None:
    L: list[str] = []
    a = L.append
    a("*HEADING")
    a("NAFEMS LE11 solid cyl/taper/sphere temperature - real ccx thermal-stress solve (m/Pa/degC).")
    a("*NODE,NSET=NALL")
    for nid in sorted(nodes):
        x, y, z = nodes[nid]
        a(f"{nid:8d}, {x: .9e}, {y: .9e}, {z: .9e}")
    a(f"*ELEMENT,TYPE={etype},ELSET=BODY")
    for eid in sorted(elements):
        nl = elements[eid]
        a(f"{eid}, " + ", ".join(str(n) for n in nl[:8]) + ",")
        a("     " + ", ".join(str(n) for n in nl[8:]))
    for name in ("XSYM", "YSYM", "ZBOT", "ZTOP"):
        ids = sorted(sets[name])
        a(f"*NSET,NSET={name}")
        for i in range(0, len(ids), 10):
            a(", ".join(str(v) for v in ids[i : i + 10]) + ("," if i + 10 < len(ids) else ""))
    a("*MATERIAL,NAME=STEEL")
    a("*ELASTIC")
    a(f"{E_PA:.6e}, {NU:.4f}")
    a("*EXPANSION,ZERO=0.0")
    a(f"{ALPHA:.6e}")
    a("*SOLID SECTION,ELSET=BODY,MATERIAL=STEEL")
    a("*INITIAL CONDITIONS,TYPE=TEMPERATURE")
    a(f"NALL, {TREF:.4f}")
    a("*STEP")
    a("*STATIC")
    a("*BOUNDARY")
    a("XSYM, 1, 1, 0.0")
    a("YSYM, 2, 2, 0.0")
    a("ZBOT, 3, 3, 0.0")
    a("ZTOP, 3, 3, 0.0")
    a("*TEMPERATURE")
    for nid in sorted(nodes):
        x, y, z = nodes[nid]
        t = math.sqrt(x * x + y * y) + z
        a(f"{nid}, {t:.9e}")
    a("*EL FILE")
    a("S")
    a("*NODE FILE")
    a("U")
    a("*END STEP")
    out.write_text("\n".join(L) + "\n")


def parse_frd_szz(frd: Path, node_id: int):
    """sigma_zz = 3rd normal stress component (SXX SYY SZZ ...) -> index 2."""
    in_stress, szz = False, None
    for line in frd.read_text(errors="ignore").splitlines():
        if line.startswith(" -4") and "STRESS" in line:
            in_stress = True
            continue
        if in_stress and line.startswith(" -3"):
            in_stress = False
            continue
        if in_stress and line.startswith(" -1"):
            try:
                nid = int(line[3:13])
            except ValueError:
                continue
            if nid == node_id:
                vals = re.findall(r"[-+]?\d*\.\d+E[-+]\d+", line[13:])
                if len(vals) >= 3:
                    szz = float(vals[2])
    return szz


def solve_one(refine: int, etype: str = "C3D20") -> dict:
    work = HERE / f"run_r{refine}_{etype}"
    work.mkdir(exist_ok=True)
    inp = work / "le11.inp"
    run_gmsh(refine, inp)
    nodes, elements = parse_inp(inp)
    if not elements:
        raise RuntimeError("no C3D20 elements — check gmsh recombine/order")
    sets = classify(nodes)
    na = node_A(nodes)
    solve = work / "solve.inp"
    write_solve(nodes, elements, sets, solve, etype)
    sys.path.insert(0, str(REPO))
    from tools.calculix_driver import run_solve  # noqa: E402

    res = run_solve(solve, work, timeout_s=900)
    szz = parse_frd_szz(Path(res["frd_path"]), na) if res.get("frd_path") else None
    resid = (szz - TARGET_PA) / TARGET_PA * 100 if szz is not None else None
    return {
        "refine": refine,
        "etype": etype,
        "nodes": len(nodes),
        "elements": len(elements),
        "node_A": na,
        "A_coord": nodes[na],
        "sigma_zz_pa": szz,
        "residual_pct": resid,
        "converged": res.get("converged"),
        "ccx_version": res.get("ccx_version"),
    }


def main() -> None:
    ladder = "--ladder" in sys.argv
    rungs = [1, 2, 3, 4] if ladder else [CANONICAL_REFINE]
    print(f"NAFEMS LE11 sigma_zz@A (target {TARGET_PA / 1e6:+.1f} MPa), C3D20:")
    for r in rungs:
        out = solve_one(r)
        s = out["sigma_zz_pa"]
        smpa = f"{s / 1e6:+.4f}" if s is not None else "None"
        rp = f"{out['residual_pct']:+.2f}%" if out["residual_pct"] is not None else "None"
        print(
            f"  r={r} | el={out['elements']:>5} nd={out['nodes']:>6} "
            f"| A={out['node_A']}@{tuple(round(c, 4) for c in out['A_coord'])} "
            f"| sigma_zz@A={smpa} MPa | resid={rp} | converged={out['converged']}"
        )


if __name__ == "__main__":
    main()
