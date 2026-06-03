"""NAFEMS LE10 "Thick Plate Pressure" — real ccx benchmark-agreement solve.

Tier 2 real-solver validated; **public-benchmark agreement** (NAFEMS LE10);
NOT signed validation (no independent signoff per ADR-023 Tier-2-signed).

Units: METERS / Pa. Frame: mid-plane at z=0 (z in [-0.3, +0.3]).
Spec triangulated 2026-06-03 from FeenoX/Code_Aster + ESRD StressCheck
Benchmarks Guide + Abaqus/Altair (see ../NOTES.md):
  outer ellipse a=3.25 (x), b=2.75 (y); inner a=2.0 (x), b=1.0 (y); t=0.6.
  Point D = (2.0, 0, +0.3) on the UPPER (loaded) surface — inner-ellipse
  major-axis tip on the y=0 symmetry plane. Target sigma_yy(D) = -5.38 MPa
  (Code_Aster/FeenoX sign convention; magnitude 5.38 MPa is community-canonical).

Pipeline (mirrors golden_samples/cylinder-pv-candidate/data/generator.py idiom):
  1. gmsh CLI meshes a structured transfinite quad -> recombine -> extrude
     -> C3D20 hex (gmsh emits Abaqus ordering that ccx ingests directly).
  2. classify node sets by geometry; find the top pressure faces; locate D.
  3. write solve.inp (BCs + 1 MPa top pressure + S/U output).
  4. run ccx (tools.calculix_driver.run_solve); read sigma_yy@D from the .frd.

Run:  python generator.py            # canonical 40x20x6 C3D20 solve
      python generator.py --ladder   # the convergence ladder
"""
from __future__ import annotations

import math
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]  # data -> nafems-...-candidate -> golden_samples -> repo

AI, BI = 2.0, 1.0
AO, BO = 3.25, 2.75
T = 0.6
ZTOP, ZMID = +0.3, 0.0
E_PA, NU = 210.0e9, 0.30
P_TOP = 1.0e6
TARGET_PA = -5.38e6           # published NAFEMS LE10 reference (signed, ccx convention)
D_COORD = (AI, 0.0, ZTOP)
TOL_PLANE, TOL_ELL = 1e-4, 2e-3
CANONICAL = (40, 20, 6, "C3D20")

FACE_CORNERS = {1: (0, 3, 2, 1), 2: (4, 5, 6, 7), 3: (0, 1, 5, 4),
                4: (1, 2, 6, 5), 5: (2, 3, 7, 6), 6: (3, 0, 4, 7)}

GEO_TEMPLATE = """SetFactory("Built-in");
nc = {nc}; nr = {nr}; nt = {nt};
ai = 2.0;  bi = 1.0;  ao = 3.25; bo = 2.75;  t = 0.6;  z0 = -0.3;
Point(1) = {{0,0,z0}}; Point(2) = {{ai,0,z0}}; Point(3) = {{0,bi,z0}};
Point(4) = {{ao,0,z0}}; Point(5) = {{0,bo,z0}};
Ellipse(1) = {{2,1,2,3}};  Ellipse(2) = {{4,1,4,5}};
Line(3) = {{2,4}};  Line(4) = {{3,5}};
Curve Loop(1) = {{3,2,-4,-1}};  Plane Surface(1) = {{1}};
Transfinite Curve {{1,2}} = nc+1;  Transfinite Curve {{3,4}} = nr+1;
Transfinite Surface {{1}};  Recombine Surface {{1}};
Extrude {{0,0,t}} {{ Surface{{1}}; Layers{{nt}}; Recombine; }}
Mesh.ElementOrder = 2;  Mesh.SecondOrderIncomplete = 1;
"""


def run_gmsh(nc, nr, nt, inp):
    geo = inp.with_suffix(".geo")
    geo.write_text(GEO_TEMPLATE.format(nc=nc, nr=nr, nt=nt))
    subprocess.run(["gmsh", "-3", str(geo), "-o", str(inp), "-format", "inp", "-v", "1"],
                   check=True, capture_output=True, text=True, timeout=600)


def parse_inp(path):
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


def classify(nodes):
    s = {k: set() for k in ("XSYM", "YSYM", "OUTER", "TOP", "ZMID_OUTER")}
    for nid, (x, y, z) in nodes.items():
        if abs(x) < TOL_PLANE:
            s["XSYM"].add(nid)
        if abs(y) < TOL_PLANE:
            s["YSYM"].add(nid)
        if abs((x / AO) ** 2 + (y / BO) ** 2 - 1.0) < TOL_ELL:
            s["OUTER"].add(nid)
            if abs(z - ZMID) < TOL_PLANE:
                s["ZMID_OUTER"].add(nid)
        if abs(z - ZTOP) < TOL_PLANE:
            s["TOP"].add(nid)
    return s


def top_faces(elements, top):
    out = []
    for eid, nl in elements.items():
        c = nl[:8]
        for fid, idx in FACE_CORNERS.items():
            if all(c[i] in top for i in idx):
                out.append((eid, fid))
                break
    return out


def node_D(nodes):
    return min(nodes, key=lambda n: math.dist(nodes[n], D_COORD))


def write_solve(nodes, elements, sets, faces, out, etype):
    L, a = [], None
    L = []
    a = L.append
    a("*HEADING")
    a("NAFEMS LE10 thick plate pressure - real ccx benchmark solve (meters/Pa).")
    a("*NODE,NSET=NALL")
    for nid in sorted(nodes):
        x, y, z = nodes[nid]
        a(f"{nid:8d}, {x: .9e}, {y: .9e}, {z: .9e}")
    a(f"*ELEMENT,TYPE={etype},ELSET=BODY")
    for eid in sorted(elements):
        nl = elements[eid]
        a(f"{eid}, " + ", ".join(str(n) for n in nl[:8]) + ",")
        a("     " + ", ".join(str(n) for n in nl[8:]))
    for name in ("XSYM", "YSYM", "OUTER", "ZMID_OUTER"):
        ids = sorted(sets[name])
        a(f"*NSET,NSET={name}")
        for i in range(0, len(ids), 10):
            a(", ".join(str(v) for v in ids[i:i + 10]) + ("," if i + 10 < len(ids) else ""))
    a("*SURFACE,NAME=TOP,TYPE=ELEMENT")
    for eid, fid in faces:
        a(f"{eid}, S{fid}")
    a("*MATERIAL,NAME=STEEL")
    a("*ELASTIC")
    a(f"{E_PA:.6e}, {NU:.4f}")
    a("*SOLID SECTION,ELSET=BODY,MATERIAL=STEEL")
    a("*BOUNDARY")
    a("XSYM, 1, 1, 0.0")
    a("YSYM, 2, 2, 0.0")
    a("OUTER, 1, 1, 0.0")
    a("OUTER, 2, 2, 0.0")
    a("ZMID_OUTER, 3, 3, 0.0")
    a("*STEP")
    a("*STATIC")
    a("*DLOAD")
    a(f"TOP, P, {P_TOP:.6e}")
    a("*EL FILE")
    a("S")
    a("*NODE FILE")
    a("U")
    a("*END STEP")
    out.write_text("\n".join(L) + "\n")


def parse_frd_syy(frd, node_id):
    in_stress, syy = False, None
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
                if len(vals) >= 2:
                    syy = float(vals[1])
    return syy


def solve_one(nc, nr, nt, etype):
    work = HERE / f"run_{nc}_{nr}_{nt}_{etype}"
    work.mkdir(exist_ok=True)
    inp = work / "le10.inp"
    run_gmsh(nc, nr, nt, inp)
    nodes, elements = parse_inp(inp)
    if not elements:
        raise RuntimeError("no C3D20 elements — check gmsh recombine/order")
    sets = classify(nodes)
    faces = top_faces(elements, sets["TOP"])
    nd = node_D(nodes)
    solve = work / "solve.inp"
    write_solve(nodes, elements, sets, faces, solve, etype)
    sys.path.insert(0, str(REPO))
    from tools.calculix_driver import run_solve  # noqa: E402
    res = run_solve(solve, work, timeout_s=900)
    syy = parse_frd_syy(Path(res["frd_path"]), nd) if res.get("frd_path") else None
    resid = (syy - TARGET_PA) / TARGET_PA * 100 if syy is not None else None
    return {"nc": nc, "nr": nr, "nt": nt, "etype": etype, "nodes": len(nodes),
            "elements": len(elements), "node_D": nd, "sigma_yy_pa": syy,
            "residual_pct": resid, "converged": res.get("converged"),
            "ccx_version": res.get("ccx_version")}


def main():
    ladder = "--ladder" in sys.argv
    rungs = [(12, 6, 3), (16, 8, 4), (24, 12, 4), (32, 16, 5), (40, 20, 6)] if ladder else [CANONICAL[:3]]
    print(f"NAFEMS LE10 sigma_yy@D (target {TARGET_PA/1e6:+.2f} MPa), C3D20:")
    for r in rungs:
        out = solve_one(r[0], r[1], r[2], CANONICAL[3])
        s = out["sigma_yy_pa"]
        print(f"  {r[0]:>2}x{r[1]:>2}x{r[2]:<2} | el={out['elements']:>5} nd={out['nodes']:>6} "
              f"| sigma_yy@D={s/1e6:+.4f} MPa | resid={out['residual_pct']:+.2f}% "
              f"| converged={out['converged']}")


if __name__ == "__main__":
    main()
