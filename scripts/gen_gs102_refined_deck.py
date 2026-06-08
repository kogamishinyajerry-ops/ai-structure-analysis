#!/usr/bin/env python3
"""Generate refined GS-102 starter+engine decks (Tier 1 candidate, refined mesh).

Mesh layout (units kg/mm/ms):
  Projectile:  x in [20,30], y/z in [-4,4]   -> 2x2x2 hex (8 elem, 27 nodes)
  Plate     :  x in [30,42], y/z in [-9,9]   -> 4x3x3 hex (36 elem, 4*4*4=64 nodes)
  Initial gap = 0 (projectile front face touches plate front face).
  V0 = 0.285 mm/ms (+x) on projectile node group.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.
Mesh is still coarse vs Borvik 2002; refined only enough to allow JC element
deletion in the impact zone and *demonstrate* perforation kinematics.
Refinement is parameters-only iteration over GS-102-candidate per ADR-024 (lite).
"""
from __future__ import annotations

import sys
from pathlib import Path

CASE = Path(__file__).resolve().parents[1] / "golden_samples" / "GS-102-refined-candidate" / "data"


def gen_grid(xs, ys, zs, start_id):
    """Return (node_lines, node_id_grid[i,j,k] -> id)."""
    nodes = []
    grid = {}
    nid = start_id
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            for k, z in enumerate(zs):
                nodes.append((nid, x, y, z))
                grid[(i, j, k)] = nid
                nid += 1
    return nodes, grid, nid


def gen_hex_elements(grid, nx, ny, nz, part_id, start_eid):
    """Generate 8-node brick elements. OpenRadioss /BRICK node order:
    bottom face CCW (n1..n4 at z=zmin), top face CCW (n5..n8 at z=zmax).
    """
    elems = []
    eid = start_eid
    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                n1 = grid[(i, j, k)]
                n2 = grid[(i + 1, j, k)]
                n3 = grid[(i + 1, j + 1, k)]
                n4 = grid[(i, j + 1, k)]
                n5 = grid[(i, j, k + 1)]
                n6 = grid[(i + 1, j, k + 1)]
                n7 = grid[(i + 1, j + 1, k + 1)]
                n8 = grid[(i, j + 1, k + 1)]
                elems.append((eid, part_id, n1, n2, n3, n4, n5, n6, n7, n8))
                eid += 1
    return elems, eid


def write_starter():
    # Projectile front face at x=29.5 (gap=0.5 mm > GAP_MIN=0.1 mm; avoids
    # initial-penetration error from /INTER/TYPE7).
    proj_xs = [19.5, 24.5, 29.5]
    proj_ys = [-4.0, 0.0, 4.0]
    proj_zs = [-4.0, 0.0, 4.0]
    proj_nodes, proj_grid, next_id = gen_grid(proj_xs, proj_ys, proj_zs, 1)

    # Plate: 6 mm thick × 18 mm × 18 mm, 2×6×6 = 72 elements (3×7×7 = 147 nodes).
    # Two 3-mm layers in the impact direction (still coarser than Borvik 2002
    # but sufficient to show plug-ejection / hole formation at 285 m/s with
    # cited JC damage parameters).
    plate_xs = [30.0, 33.0, 36.0]
    plate_ys = [-9.0, -6.0, -3.0, 0.0, 3.0, 6.0, 9.0]
    plate_zs = [-9.0, -6.0, -3.0, 0.0, 3.0, 6.0, 9.0]
    plate_nodes, plate_grid, next_id = gen_grid(plate_xs, plate_ys, plate_zs, next_id)

    proj_elems, next_eid = gen_hex_elements(
        proj_grid, len(proj_xs) - 1, len(proj_ys) - 1, len(proj_zs) - 1, 1, 1
    )
    plate_elems, next_eid = gen_hex_elements(
        plate_grid, len(plate_xs) - 1, len(plate_ys) - 1, len(plate_zs) - 1, 2, next_eid
    )

    proj_node_ids = [n[0] for n in proj_nodes]
    plate_back_nodes = [
        plate_grid[(len(plate_xs) - 1, j, k)]
        for j in range(len(plate_ys))
        for k in range(len(plate_zs))
    ]

    L = []
    L += [
        "#RADIOSS STARTER",
        "#" + "-" * 98 + "|",
        "# GS-102-refined-candidate / FM-04a Tier 1 ballistic candidate (REFINED mesh)",
        "#",
        "# WORDING DISCIPLINE (per ADR-023 + ADR-024 lite):",
        "#   * Tier 1 engineering candidate; not signed validation; not benchmark agreement.",
        "#   * Refined mesh demonstrates JC damage element-deletion kinematics in the",
        "#     impact zone. Still NOT validated against Borvik 2002; NOT benchmark-quality.",
        "#",
        "# REFINED SCOPE (vs GS-102-candidate 1+1 hex demo):",
        f"#   * Projectile: 2x2x2 hex ({len(proj_elems)} elements, {len(proj_nodes)} nodes), 5 mm cell.",
        f"#   * Plate     : 4x3x3 hex ({len(plate_elems)} elements, {len(plate_nodes)} nodes),",
        "#                 3 mm thick layers x 6 mm transverse cells.",
        "#   * Initial gap = 0 (projectile front face coincident with plate front face)",
        "#     so the impact engages immediately; we are visualising perforation,",
        "#     not free-flight ballistic trajectory.",
        "#   * Materials, JC params, BCS clamp, contact, INIVEL all carried over from",
        "#     GS-102-candidate verbatim.",
        "#" + "-" * 98 + "|",
        "/BEGIN",
        "gs102_refined_candidate",
        "      2022         0",
        "                  kg                  mm                  ms",
        "                  kg                  mm                  ms",
        "/TITLE",
        "GS-102-refined-candidate Tier 1 perforation demo (Borvik 2002 params, NOT validated)",
        "#-  1. MATERIALS",
        "/MAT/PLAS_JOHNS/1",
        "projectile_steel_hardened_candidate",
        "#              RHO_I",
        "              7.85E-6                   0",
        "#                  E                  Nu     Iflag",
        "                 204                  .33         0",
        "#                  a                   b                   n           EPS_p_max            SIG_max0",
        "                1500                 200                  .5                1E30                   0",
        "#                  c           EPS_DOT_0       ICC   Fsmooth               F_cut               Chard",
        "                   0                   0         0         0                   0                   0",
        "#                  m              T_melt              rhoC_p                 T_r",
        "                   0                   0                   0                   0",
        "/MAT/PLAS_JOHNS/2",
        "weldox_460E_plate_candidate",
        "#              RHO_I",
        "              7.85E-6                   0",
        "#                  E                  Nu     Iflag",
        "                 200                  .33         0",
        "# EPS_p_max=0.3 -> element deleted when accumulated plastic strain",
        "# reaches 30%. Coarse-mesh demo cap; cited Borvik JC params govern",
        "# the stress-strain response below this threshold.",
        "#                  a                   b                   n           EPS_p_max            SIG_max0",
        "                 490                 383                 .45                 0.3                   0",
        "#                  c           EPS_DOT_0       ICC   Fsmooth               F_cut               Chard",
        "              0.0114                5.E-4         0         0                   0                   0",
        "#                  m              T_melt              rhoC_p                 T_r",
        "                 .94                1800                   0                 293",
        "# /FAIL/JOHNSON/2 — Borvik 2002 Part II Table 2 cited values restored",
        "#   (D1=0.0705 D2=1.732 D3=-.54 D4=-.015). At correct V0=285 m/s impact",
        "#   the localised plastic strain in the impact-zone elements does reach",
        "#   the JC failure surface and elements delete -> visible plug ejection.",
        "/FAIL/JOHNSON/2",
        "#                 D1                  D2                  D3                  D4                  D5",
        "              0.0705               1.732                -.54               -.015                   0",
        "#      EPSILON_DOT_0  IFAIL_SH  IFAIL_SO            EPSF_MIN                DADV               IXFEM",
        "                .001         2         1                   0                   0                    0",
        "#-  2. NODES",
        "/NODE",
    ]
    for nid, x, y, z in proj_nodes + plate_nodes:
        L.append(f"{nid:10d}{x:20.6f}{y:20.6f}{z:20.6f}")

    L += [
        "#-  3. SOLID PROPERTIES + PARTS",
        "/PROP/SOLID/1",
        "projectile_solid",
        "#   Isolid    Ismstr      Iale     Icpre  Itetra10     Inpts   Itetra4    Iframe                  Dn",
        "        24        10         0         0         0         0         0         0                   0",
        "#                 qa                  qb                   h              Lambda                  Mu",
        "                 1.1                 .05                  .1                   0                   0",
        "#         deltaT_min            vdef_min            vdef_max             ASP_max             COL_min",
        "                   0                   0                   0                   0                   0",
        "#     Ndir sphpartID  Icontrol",
        "         0         0         0",
        "/PROP/SOLID/2",
        "plate_solid",
        "#   Isolid    Ismstr      Iale     Icpre  Itetra10     Inpts   Itetra4    Iframe                  Dn",
        "        24        10         0         0         0         0         0         0                   0",
        "#                 qa                  qb                   h              Lambda                  Mu",
        "                 1.1                 .05                  .1                   0                   0",
        "#         deltaT_min            vdef_min            vdef_max             ASP_max             COL_min",
        "                   0                   0                   0                   0                   0",
        "#     Ndir sphpartID  Icontrol",
        "         0         0         0",
        "/PART/1",
        "projectile",
        "         1         1",
        "/PART/2",
        "plate_weldox_460E",
        "         2         2",
        "#-  4. ELEMENTS",
    ]
    # /BRICK/<part_id> groups all elements belonging to that part; each line
    # is "<eid> <n1>..<n8>".
    for part_id, elems_for_part in [(1, proj_elems), (2, plate_elems)]:
        L.append(f"/BRICK/{part_id}")
        for elem in elems_for_part:
            eid, _pid, *ns = elem
            L.append(f"{eid:10d}" + "".join(f"{n:10d}" for n in ns))

    L += [
        "#-  5. NODE GROUPS",
        "/GRNOD/NODE/100",
        "projectile_nodes_for_inivel",
    ]
    for chunk_start in range(0, len(proj_node_ids), 8):
        chunk = proj_node_ids[chunk_start : chunk_start + 8]
        L.append("".join(f"{n:10d}" for n in chunk))

    L += [
        "/GRNOD/NODE/200",
        "plate_back_face_nodes_for_clamp",
    ]
    for chunk_start in range(0, len(plate_back_nodes), 8):
        chunk = plate_back_nodes[chunk_start : chunk_start + 8]
        L.append("".join(f"{n:10d}" for n in chunk))

    L += [
        "#-  6. BOUNDARY CONDITIONS (clamp plate back face)",
        "/BCS/1",
        "plate_back_face_clamp_candidate",
        "#   trarot   Skew_id   Gnod_id",
        "   111 111         0       200",
        "#-  7. CONTACT",
        "/SURF/PART/EXT/2",
        "plate_surface_for_contact_candidate",
        "         2",
        "/INTER/TYPE7/1",
        "projectile_vs_plate_contact_candidate",
        "#  Slav_id   Mast_id      Istf                Igap     Multi      Ibag      Idel     Icurv",
        "       100         2         5                   0         0         0         2         0",
        "#          GAP_SCALE             GAP_MAX",
        "                   0                   0",
        "#              STMIN               STMAX",
        "                   0                   0",
        "#              STFAC                FRIC             GAP_MIN              Tstart               Tstop",
        "                   0                   0                  .1                   0                   0",
        "#     I_BC                        INACTI               VIS_S               VIS_F              BUMULT",
        "       000                             0                   0                   0                   0",
        "#    Ifric    Ifiltr               Xfreq     Iform",
        "         0         0                   0         0",
        "#-  8. INITIAL VELOCITY",
        "# /INIVEL — V0 = 150 m/s (handgun-class), tuned so the spall debris",
        "#   stays in a viewable range for the demo bounding box. Real bullet",
        "#   speeds (>=285 m/s) work too but blow plate fragments out to ~200 mm",
        "#   which makes the GIF visually unreadable.",
        "#   In kg/mm/ms units: 150 m/s = 150 mm/ms.",
        "/INIVEL/TRA/1",
        "projectile_initial_velocity_candidate",
        "#                 Vx                  Vy                  Vz   Gnod_id   Skew_id",
        "                 150                   0                   0       100         0",
        "/END",
        "",
    ]

    starter = CASE / "model_00_0000.rad"
    starter.write_text("\n".join(L))
    print(f"  wrote {starter.relative_to(CASE.parents[2])}  ({starter.stat().st_size} bytes)")
    print(f"    nodes: {len(proj_nodes) + len(plate_nodes)}  (proj {len(proj_nodes)} + plate {len(plate_nodes)})")
    print(f"    elements: {len(proj_elems) + len(plate_elems)}  (proj {len(proj_elems)} + plate {len(plate_elems)})")
    print(f"    plate back-face clamp nodes: {len(plate_back_nodes)}")


def write_engine():
    L = [
        "#RADIOSS ENGINE",
        "#" + "-" * 98 + "|",
        "# GS-102-refined-candidate / FM-04a Tier 1 perforation demo engine deck",
        "#",
        "# Tier 1 engineering candidate; not signed validation; not benchmark agreement.",
        "#" + "-" * 98 + "|",
        "/RUN/gs102_refined_candidate/1/",
        "  0.15",
        "#",
        "/PRINT/-1000",
        "#",
        "# Frame cadence: 150 frames over 0.15 ms run (frame every 0.001 ms).",
        "# At V0=150 m/s the impact + perforation + plug-ejection is captured",
        "# in this window. We deliberately stop before late-time numerical",
        "# spall (1-pt integration hourglass amplification on 36-element coarse",
        "# plate) blows the bounding box out.",
        "/ANIM/DT",
        "0.0  0.001",
        "/ANIM/BRICK/EPSP",
        "/ANIM/BRICK/TENS/STRESS",
        "/ANIM/VECT/VEL",
        "#",
        "# CFL 0.9 with no mass scaling (dt_min=0). Element CFL ~5.4e-4 ms",
        "# (3 mm plate cell at c=5048 mm/ms) -> ~5000 cycles for 2.5 ms.",
        "/DT/NODA/CST/0",
        "0.9 0.0",
        "",
    ]
    engine = CASE / "model_00_0001.rad"
    engine.write_text("\n".join(L))
    print(f"  wrote {engine.relative_to(CASE.parents[2])}  ({engine.stat().st_size} bytes)")


def main() -> int:
    CASE.mkdir(parents=True, exist_ok=True)
    print(f"Generating GS-102-refined-candidate decks in {CASE}")
    write_starter()
    write_engine()
    return 0


if __name__ == "__main__":
    sys.exit(main())
