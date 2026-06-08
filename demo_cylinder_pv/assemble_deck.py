"""Assemble a CalculiX solve.inp from the gmsh-produced cylinder.inp.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Steps:
  1. Read cylinder.inp -> (nodes, C3D20 elements).
  2. Classify each node by geometric face:
       - INNER_SURF : r ~= Ri
       - OUTER_SURF : r ~= Ro
       - THETA0     : y ~= 0
       - THETA5     : y ~= x*tan(theta)
       - ZBOT       : z ~= 0
       - ZTOP       : z ~= L
       - SCL_LINE   : on the radial line at z=L/2, theta=theta/2 -> 5 SCL points
  3. Write solve.inp:
       - *NODE
       - *ELEMENT,TYPE=C3D20,ELSET=BODY
       - *NSET for every face above
       - *SURFACE for INNER -> internal pressure
       - *MATERIAL : SA-516 Gr.70 (E, nu, alpha placeholder)
       - *SOLID SECTION
       - *BOUNDARY : symmetry BCs + axial fix one node
       - *STEP / *STATIC
       - *DLOAD : pressure on INNER_SURF
       - *CLOAD : closed-end axial pull on ZTOP nodes
       - *EL FILE,*NODE FILE : S, U, NT
       - *END STEP
"""

from __future__ import annotations

import math
import re
from pathlib import Path

HERE = Path(__file__).parent
SRC = HERE / "cylinder.inp"
OUT = HERE / "solve.inp"

# -- problem constants (kept in sync with cylinder.geo) --
Ri = 100.0  # mm
Ro = 150.0  # mm
L = 100.0  # mm
THETA_DEG = 5.0
THETA = math.radians(THETA_DEG)
TOL_R = 1.0  # mm tolerance for radial face classification
TOL_AX = 0.5  # mm tolerance for axial / tangential face classification
P_INTERNAL = 10.0  # MPa
SIGMA_AXIAL_CLOSED_END = P_INTERNAL * Ri**2 / (Ro**2 - Ri**2)  # closed-end axial stress

E_PA = 200_000.0  # MPa  (SA-516 Gr.70 elastic modulus at ~50C)
NU = 0.30
SM_AT_TEMP = 138.0  # MPa  (SA-516 Gr.70 design stress intensity at ~100C per ASME II-D)


def parse_inp(path: Path) -> tuple[dict[int, tuple[float, float, float]], dict[int, list[int]]]:
    """Parse a gmsh-emitted Abaqus-style .inp file.

    Returns:
        nodes: {node_id: (x, y, z)}
        elements: {element_id: [n1, ..., n20]} for C3D20 only.
    """
    nodes: dict[int, tuple[float, float, float]] = {}
    elements: dict[int, list[int]] = {}
    mode: str | None = None  # 'node' | 'c3d20' | None
    pending: list[int] | None = None
    pending_id: int | None = None

    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("*"):
            head = line.lower()
            if head.startswith("*node"):
                mode = "node"
            elif head.startswith("*element"):
                m = re.search(r"type\s*=\s*([A-Z0-9]+)", line, re.IGNORECASE)
                etype = m.group(1).upper() if m else ""
                mode = "c3d20" if etype == "C3D20" else "skip"
                pending = None
                pending_id = None
            else:
                mode = None
            continue
        if mode == "node":
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 4:
                nid = int(parts[0])
                nodes[nid] = (float(parts[1]), float(parts[2]), float(parts[3]))
        elif mode == "c3d20":
            parts = [p.strip() for p in line.split(",") if p.strip()]
            if not parts:
                continue
            ints = [int(p) for p in parts]
            if pending is None:
                pending_id = ints[0]
                pending = ints[1:]
            else:
                pending.extend(ints)
            if pending is not None and len(pending) >= 20:
                assert pending_id is not None
                elements[pending_id] = pending[:20]
                pending = None
                pending_id = None
    return nodes, elements


def classify_node(coord: tuple[float, float, float]) -> set[str]:
    """Return the set of named faces this node belongs to (may be multiple at edges)."""
    x, y, z = coord
    r = math.hypot(x, y)
    tags: set[str] = set()
    if abs(r - Ri) < TOL_R:
        tags.add("INNER_SURF")
    if abs(r - Ro) < TOL_R:
        tags.add("OUTER_SURF")
    if abs(y) < TOL_AX:
        tags.add("THETA0")
    # theta = 5 deg face: y = x tan(theta), so dist = | -sin*x + cos*y | * 1 in 2D.
    if abs(-math.sin(THETA) * x + math.cos(THETA) * y) < TOL_AX:
        tags.add("THETA5")
    if abs(z) < TOL_AX:
        tags.add("ZBOT")
    if abs(z - L) < TOL_AX:
        tags.add("ZTOP")
    return tags


def assemble_surface_inner(
    elements: dict[int, list[int]], inner_nodes: set[int]
) -> list[tuple[int, int]]:
    """For each C3D20, pick the face whose 4 corner nodes are all on INNER_SURF.

    CalculiX C3D20 face numbering (per ccx manual): faces 1..6 with corner
    indices into the 20-node list:
       Face S1 (z-): 1, 4, 3, 2
       Face S2 (z+): 5, 6, 7, 8
       Face S3 (r? local y-): 1, 2, 6, 5
       Face S4 (local x+): 2, 3, 7, 6
       Face S5 (local y+): 3, 4, 8, 7
       Face S6 (local x-): 4, 1, 5, 8
    (1-based; the node list of a C3D20 starts with the 8 corners then 12 mid.)
    """
    # gmsh's extrude produces hex with corner ordering c0..c3 on bottom and
    # c4..c7 on top (top = bottom + extrusion). The radial inner face is the
    # one with corner indices spanning the inner-radius nodes.
    face_corners = {
        1: (0, 3, 2, 1),
        2: (4, 5, 6, 7),
        3: (0, 1, 5, 4),
        4: (1, 2, 6, 5),
        5: (2, 3, 7, 6),
        6: (3, 0, 4, 7),
    }
    out: list[tuple[int, int]] = []
    for eid, nlist in elements.items():
        corners = nlist[:8]
        for fid, idxs in face_corners.items():
            face_node_ids = {corners[i] for i in idxs}
            if face_node_ids.issubset(inner_nodes):
                out.append((eid, fid))
                break  # one hex contributes at most one inner face
    return out


def write_solve(nodes, elements, faceset, surf_inner, scl_node_ids, out_path: Path) -> None:
    lines: list[str] = []
    add = lines.append
    add("*HEADING")
    add("Tier 1 engineering candidate; not signed validation; not benchmark agreement.")
    add("Thick-walled pressure cylinder under internal pressure (Lame benchmark).")
    add("** Ri=100 Ro=150 mm, L=100 mm, p=10 MPa, SA-516 Gr.70, E=200 GPa, nu=0.3.")
    add("*NODE,NSET=NALL")
    for nid in sorted(nodes):
        x, y, z = nodes[nid]
        add(f"{nid:8d}, {x: .8e}, {y: .8e}, {z: .8e}")
    add("*ELEMENT,TYPE=C3D20,ELSET=BODY")
    for eid in sorted(elements):
        nlist = elements[eid]
        # CalculiX accepts the 20 connectivity ids on one or multiple lines;
        # gmsh follows abaqus ordering which ccx ingests directly.
        # Break onto two lines for readability: corners (8) then mid (12).
        c = ", ".join(f"{n}" for n in nlist[:8])
        m = ", ".join(f"{n}" for n in nlist[8:])
        add(f"{eid}, {c},")
        add(f"     {m}")
    # NSETs
    for name, ids in sorted(faceset.items()):
        add(f"*NSET,NSET={name}")
        ids = sorted(ids)
        for i in range(0, len(ids), 10):
            add(", ".join(str(x) for x in ids[i : i + 10]) + ("," if i + 10 < len(ids) else ""))
    # SCL nodes (ordered through-thickness from Ri to Ro at z=L/2, theta=THETA/2).
    add("*NSET,NSET=SCL_LINE")
    for nid in scl_node_ids:
        add(f"{nid}")
    # Surface for internal pressure.
    add("*SURFACE,NAME=SURF_INNER,TYPE=ELEMENT")
    for eid, fid in surf_inner:
        add(f"{eid}, S{fid}")
    # Material.
    add("*MATERIAL,NAME=SA516")
    add("*ELASTIC")
    add(f"{E_PA:.6e}, {NU:.4f}")
    add("*SOLID SECTION,ELSET=BODY,MATERIAL=SA516")
    # Reference node for closed-end MPC (added to NALL via *NODE,NSET).
    area_top = (Ro**2 - Ri**2) * math.pi * (THETA / (2 * math.pi))
    total_axial_force = SIGMA_AXIAL_CLOSED_END * area_top
    ref_node = max(nodes) + 1
    add("** Reference node for closed-end plane-sections MPC.")
    add("*NODE,NSET=ZTOP_REF")
    add(f"{ref_node}, 0.0, 0.0, {L}")
    # BCs.
    add("** Symmetry: theta=0 face -> uy=0; theta=5 face -> normal disp = 0.")
    add("*BOUNDARY")
    add("THETA0, 2, 2, 0.0")  # uy = 0 on theta=0 face
    add("ZBOT, 3, 3, 0.0")  # uz = 0 on bottom face
    # Theta5 normal-displacement MPC: -sin(t)*ux + cos(t)*uy = 0
    # AND ZTOP plane-sections MPC: uz(node) = uz(ref) — both must
    # appear BEFORE the *STEP block (ccx model-definition phase).
    sin_t = math.sin(THETA)
    cos_t = math.cos(THETA)
    add("** MPC: THETA5 normal-disp = 0; ZTOP plane-sections-remain-plane.")
    for nid in sorted(faceset["THETA5"]):
        add("*EQUATION")
        add("2")
        add(f"{nid}, 1, {-sin_t: .8f}, {nid}, 2, {cos_t: .8f}")
    ztop_sorted = sorted(faceset["ZTOP"])
    for nid in ztop_sorted:
        add("*EQUATION")
        add("2")
        add(f"{nid}, 3, 1.0, {ref_node}, 3, -1.0")
    # Step.
    add("*STEP,NLGEOM=NO")
    add("*STATIC")
    add(
        f"** Internal pressure {P_INTERNAL} MPa on bore + total axial {total_axial_force:.4f} N on ref node."
    )
    add("*DLOAD")
    add(f"SURF_INNER, P, {P_INTERNAL}")
    add("*CLOAD")
    add(f"{ref_node}, 3, {total_axial_force:.6e}")
    add("*EL FILE")
    add("S")
    add("*NODE FILE")
    add("U")
    add("*END STEP")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    nodes, elements = parse_inp(SRC)
    print(f"Parsed {len(nodes)} nodes and {len(elements)} C3D20 elements.")
    if not elements:
        raise RuntimeError(
            "No C3D20 elements found in cylinder.inp — re-run gmsh with quadratic + recombine."
        )
    # Classify nodes by face.
    faceset: dict[str, set[int]] = {
        k: set() for k in ("INNER_SURF", "OUTER_SURF", "THETA0", "THETA5", "ZBOT", "ZTOP")
    }
    for nid, coord in nodes.items():
        for tag in classify_node(coord):
            faceset[tag].add(nid)
    for k, v in faceset.items():
        print(f"  Face {k}: {len(v)} nodes")

    # Identify the SCL line: nodes at z ~= L/2, theta ~= THETA/2.
    # We pick the unique radial line through the body's interior at midheight,
    # mid-arc.
    scl_candidates: list[tuple[float, int]] = []
    z_mid = L / 2.0
    theta_mid = THETA / 2.0
    for nid, (x, y, z) in nodes.items():
        if abs(z - z_mid) > 1e-3:
            continue
        r = math.hypot(x, y)
        ang = math.atan2(y, x)
        if abs(ang - theta_mid) < 1e-3:
            scl_candidates.append((r, nid))
    scl_candidates.sort()  # ascending r => inner to outer
    scl_node_ids = [nid for _r, nid in scl_candidates]
    print(f"  SCL: {len(scl_node_ids)} nodes through-thickness")
    if len(scl_node_ids) < 5:
        # Fallback: pick the inner-line at theta=0 z=L/2 (corner edge, more nodes).
        scl_candidates = []
        for nid, (x, y, z) in nodes.items():
            if abs(z - z_mid) > 1e-3:
                continue
            if abs(y) > TOL_AX:
                continue
            r = math.hypot(x, y)
            scl_candidates.append((r, nid))
        scl_candidates.sort()
        scl_node_ids = [nid for _r, nid in scl_candidates]
        print(f"  SCL (fallback theta=0): {len(scl_node_ids)} nodes through-thickness")
    if not scl_node_ids:
        raise RuntimeError("Could not locate an SCL line.")

    # Element faces on INNER_SURF.
    surf_inner = assemble_surface_inner(elements, faceset["INNER_SURF"])
    print(f"  SURF_INNER element-faces: {len(surf_inner)}")
    if not surf_inner:
        raise RuntimeError("No inner-surface element faces found — check face_corners map.")

    write_solve(nodes, elements, faceset, surf_inner, scl_node_ids, OUT)
    print(f"Wrote {OUT.name} ({OUT.stat().st_size} bytes).")


if __name__ == "__main__":
    main()
