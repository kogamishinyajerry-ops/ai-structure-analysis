#!/usr/bin/env python3
"""Generate GS-102-hifi-candidate decks: realistic 7.62x51 AP-class
projectile (cylindrical body + tangent ogive nose) impacting a 100x100x8 mm
Weldox 460E plate.

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Geometry (units kg/mm/ms):
  Projectile (M61 AP-class stand-in):
    - Cylindrical body  : dia 7.62 mm, length 20 mm
    - Tangent ogive nose: dia 7.62 mm -> point, length 10 mm
    - Total length      : 30 mm
    - Mesh              : O-grid hex topology
                          (center 4x4 hex + 4 surrounding sectors x 2 radial layers)
                          x 30 longitudinal slices in body + 12 in nose
  Plate (Weldox 460E):
    - 100 mm x 100 mm x 8 mm (uniform 25x25x4 hex)
    - Cell size 4 x 4 x 2 mm
    - Back face clamped (BCS all 6 DOF)

  Impact: V0 = 600 m/s along +X (well above Borvik 2002 ballistic limit).
  Initial gap: 0.5 mm between projectile tip and plate front face.

Materials & failure: PLAS_JOHNS + /FAIL/JOHNSON Borvik 2002 Part II Table 2
cited values; EPS_p_max=0.6 hard cap on plate plastic strain to ensure
clean element deletion at this mesh density.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

CASE = Path(__file__).resolve().parents[1] / "golden_samples" / "GS-102-hifi-candidate" / "data"


# ---------- bullet geometry ----------

def _butterfly_section(radius: float, n_radial_outer: int = 2,
                       n_inner: int = 4) -> tuple[np.ndarray, list[tuple[int, int, int, int]]]:
    """Return (yz_points, quad_connectivity) for an O-grid disk cross section.

    The O-grid uses an inner Cartesian square block (n_inner x n_inner cells)
    and surrounds it with 4 sectors of radial cells (n_radial_outer per sector).
    All cells are quads. Points are 2D (y,z); the caller extrudes along x.
    """
    pts: list[tuple[float, float]] = []
    pt_id: dict[tuple[float, float], int] = {}

    def add_pt(y: float, z: float) -> int:
        key = (round(y, 6), round(z, 6))
        if key in pt_id:
            return pt_id[key]
        pid = len(pts)
        pts.append((y, z))
        pt_id[key] = pid
        return pid

    # Inner square: from -inner_half to +inner_half, n_inner x n_inner cells
    inner_half = radius / math.sqrt(2.0) * 0.6   # 60% of inscribed-square half side
    inner_grid = np.linspace(-inner_half, inner_half, n_inner + 1)
    inner_ids = [[add_pt(inner_grid[i], inner_grid[j]) for j in range(n_inner + 1)]
                 for i in range(n_inner + 1)]

    quads: list[tuple[int, int, int, int]] = []
    for i in range(n_inner):
        for j in range(n_inner):
            quads.append((
                inner_ids[i][j],
                inner_ids[i + 1][j],
                inner_ids[i + 1][j + 1],
                inner_ids[i][j + 1],
            ))

    # 4 sectors mapping square edges -> circular arc with n_radial_outer layers
    # Each sector spans n_inner cells along the inner edge.
    # For each "radial line" perpendicular to a side, point is interpolated from
    # square edge towards corresponding angle on the circle.
    def square_edge_pt(side: int, t: float) -> tuple[float, float]:
        """t in [0,1] along side. side: 0=top(z=+inner_half), 1=right(y=+inner_half),
        2=bottom(z=-inner_half), 3=left(y=-inner_half)."""
        if side == 0:
            y = -inner_half + 2 * inner_half * t
            z = +inner_half
        elif side == 1:
            y = +inner_half
            z = +inner_half - 2 * inner_half * t
        elif side == 2:
            y = +inner_half - 2 * inner_half * t
            z = -inner_half
        else:
            y = -inner_half
            z = -inner_half + 2 * inner_half * t
        return y, z

    def sector_circle_pt(side: int, t: float) -> tuple[float, float]:
        """Angle range per side: 45..135 (top), -45..45 (right), -135..-45 (bottom),
        135..225 (left). t in [0,1] from one corner to next."""
        if side == 0:
            angle = math.radians(135 - 90 * t)  # 135 -> 45
        elif side == 1:
            angle = math.radians(45 - 90 * t)   # 45 -> -45
        elif side == 2:
            angle = math.radians(-45 - 90 * t)  # -45 -> -135
        else:
            angle = math.radians(225 - 90 * t)  # 225 -> 135
        return radius * math.cos(angle), radius * math.sin(angle)

    # For each side, build n_radial_outer rings between square edge and circle
    # Connect square corner pts <-> circle pts
    side_layers: list[list[list[int]]] = []
    for side in range(4):
        layers_for_side = []
        for r in range(n_radial_outer + 1):
            f = r / n_radial_outer
            ring = []
            for k in range(n_inner + 1):
                t = k / n_inner
                py_sq, pz_sq = square_edge_pt(side, t)
                py_ci, pz_ci = sector_circle_pt(side, t)
                py = py_sq * (1 - f) + py_ci * f
                pz = pz_sq * (1 - f) + pz_ci * f
                pid = add_pt(py, pz)
                ring.append(pid)
            layers_for_side.append(ring)
        side_layers.append(layers_for_side)

    # Quads in each sector
    for side in range(4):
        layers = side_layers[side]
        for r in range(n_radial_outer):
            ring0 = layers[r]
            ring1 = layers[r + 1]
            for k in range(n_inner):
                quads.append((ring0[k], ring0[k + 1], ring1[k + 1], ring1[k]))

    return np.array(pts), quads


def _ogive_radius(x_from_tip: float, ogive_length: float, body_radius: float) -> float:
    """Tangent ogive radius vs distance from tip.
    Standard tangent ogive: radius(x) = sqrt(rho^2 - (ogive_length - x)^2) - rho + body_radius
    where rho = (body_radius^2 + ogive_length^2) / (2*body_radius)
    """
    if x_from_tip <= 0:
        return 0.0
    if x_from_tip >= ogive_length:
        return body_radius
    rho = (body_radius * body_radius + ogive_length * ogive_length) / (2 * body_radius)
    return math.sqrt(rho * rho - (ogive_length - x_from_tip) ** 2) - rho + body_radius


def gen_projectile(start_nid: int = 1, start_eid: int = 1):
    """Generate AP-class bullet hex mesh.

    Geometry: cylindrical body + truncated tangent ogive nose.
      - Body  : dia 7.62 mm, length 22 mm, 22 axial layers (1 mm cells)
      - Ogive : tangent ogive, length 8 mm, 5 axial layers (1.6 mm cells),
                truncated at min radius 0.5 * body_radius = 1.9 mm
                (real M61 AP has a similar small meplat at the tip).
    Truncation prevents the degenerate tip cells that caused the bullet to
    ablate against the plate in earlier attempts.
    """
    body_radius = 7.62 / 2.0
    body_length = 22.0
    ogive_length = 8.0
    body_nx = 22
    ogive_nx = 5

    pts2d, quads = _butterfly_section(body_radius, n_radial_outer=2, n_inner=4)

    body_x = np.linspace(0.0, body_length, body_nx + 1)
    ogive_x = np.linspace(body_length, body_length + ogive_length, ogive_nx + 1)[1:]
    all_x = np.concatenate([body_x, ogive_x])

    nodes = []
    nid = start_nid
    section_nids: list[list[int]] = []
    for ix, x in enumerate(all_x):
        if ix < len(body_x):
            scale = 1.0
        else:
            x_from_tip = (body_length + ogive_length) - x
            r = _ogive_radius(x_from_tip, ogive_length, body_radius)
            # 0.5 truncation = 1.9 mm meplat (3.8 mm flat front diameter).
            # Keeps tip cells at min ~1.5 mm minimum dimension.
            scale = max(r / body_radius, 0.5)
        slice_nids = []
        for (py, pz) in pts2d:
            nodes.append((nid, x, py * scale, pz * scale))
            slice_nids.append(nid)
            nid += 1
        section_nids.append(slice_nids)

    # Hex elements: connect quads of slice i with slice i+1
    elements = []
    eid = start_eid
    for ix in range(len(all_x) - 1):
        s0 = section_nids[ix]
        s1 = section_nids[ix + 1]
        for q in quads:
            n1, n2, n3, n4 = q
            # OpenRadioss /BRICK 8-node order: bottom CCW (n1..n4 at z=zmin),
            # top CCW (n5..n8 at z=zmax). Here "z" axis = projectile +x.
            elements.append((eid, 1,
                             s0[n1], s0[n2], s0[n3], s0[n4],
                             s1[n1], s1[n2], s1[n3], s1[n4]))
            eid += 1
    all_nids = [n[0] for n in nodes]
    return nodes, elements, all_nids


# ---------- plate geometry ----------

def gen_plate(start_nid: int, start_eid: int,
              plate_x0: float = 30.5, thickness: float = 8.0,
              ny: int = 25, nz: int = 25, nx: int = 4,
              y_extent: float = 100.0, z_extent: float = 100.0):
    """Uniform hex plate mesh.
    plate_x0 = front face x. Thickness extends to plate_x0+thickness.
    Returns (nodes, elements, back_face_nids).
    """
    xs = np.linspace(plate_x0, plate_x0 + thickness, nx + 1)
    ys = np.linspace(-y_extent / 2, y_extent / 2, ny + 1)
    zs = np.linspace(-z_extent / 2, z_extent / 2, nz + 1)

    nodes = []
    nid = start_nid
    grid: dict[tuple[int, int, int], int] = {}
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            for k, z in enumerate(zs):
                nodes.append((nid, x, y, z))
                grid[(i, j, k)] = nid
                nid += 1

    elements = []
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
                elements.append((eid, 2, n1, n2, n3, n4, n5, n6, n7, n8))
                eid += 1

    back_face_nids = [grid[(nx, j, k)] for j in range(ny + 1) for k in range(nz + 1)]
    return nodes, elements, back_face_nids


# ---------- deck writer ----------

def write_starter():
    proj_nodes, proj_elems, proj_nids = gen_projectile(start_nid=1, start_eid=1)
    next_nid = max(n[0] for n in proj_nodes) + 1
    next_eid = max(e[0] for e in proj_elems) + 1
    # Plate front face at x=30.5, projectile tip at x=30 (gap=0.5mm > GAP_MIN=0.1)
    # Refined plate mesh: 50x50x6 = 15,000 cells, 2x2x~1.3 mm element size.
    # 4 cells across the 7.62 mm bullet diameter -> smooth perforation hole.
    # Refined plate mesh for "soft dish" demo: 60x60x4 = 14,400 cells.
    # 5 mm-thick aluminium plate, 120x120 mm extent so the dish bowl has
    # room to develop before edge effects stiffen the response.
    plate_nodes, plate_elems, back_face_nids = gen_plate(
        start_nid=next_nid, start_eid=next_eid,
        plate_x0=30.5, thickness=5.0,
        ny=60, nz=60, nx=4,
        y_extent=120.0, z_extent=120.0,
    )

    L: list[str] = [
        "#RADIOSS STARTER",
        "#" + "-" * 98 + "|",
        "# GS-102-hifi-candidate / FM-04a Tier 1 ballistic candidate (HI-FI mesh)",
        "#",
        "# WORDING DISCIPLINE (per ADR-023 + ADR-024 lite):",
        "#   * Tier 1 engineering candidate; not signed validation; not benchmark agreement.",
        "#   * 7.62 mm AP-class projectile geometry (cylindrical body + tangent",
        "#     ogive nose) vs 100x100x8 mm Weldox 460E plate. Hi-fi mesh chosen",
        "#     for visual realism, NOT for benchmark validation.",
        "#",
        "# Mesh:",
        f"#   Projectile: {len(proj_elems)} hex, {len(proj_nodes)} nodes",
        f"#   Plate     : {len(plate_elems)} hex, {len(plate_nodes)} nodes",
        f"#   Total     : {len(proj_elems) + len(plate_elems)} hex, {len(proj_nodes) + len(plate_nodes)} nodes",
        "#" + "-" * 98 + "|",
        "/BEGIN",
        "gs102_hifi_candidate",
        "      2022         0",
        "                  kg                  mm                  ms",
        "                  kg                  mm                  ms",
        "/TITLE",
        "GS-102-hifi-candidate 7.62 AP perforating 8 mm Weldox 460E (NOT validated)",
        "#-  1. MATERIALS",
        "# Projectile = AP hardened steel core: high yield + stress cap +",
        "# no failure -> bullet stays nearly rigid through perforation.",
        "/MAT/PLAS_JOHNS/1",
        "projectile_hardened_steel_AP_candidate",
        "#              RHO_I",
        "              7.85E-6                   0",
        "#                  E                  Nu     Iflag",
        "                 210                  .30         0",
        "#                  a                   b                   n           EPS_p_max            SIG_max0",
        "                2500                 250                  .3                1E30                3500",
        "#                  c           EPS_DOT_0       ICC   Fsmooth               F_cut               Chard",
        "                   0                   0         0         0                   0                   0",
        "#                  m              T_melt              rhoC_p                 T_r",
        "                   0                   0                   0                   0",
        "# Plate = annealed soft mild steel (sigma_y=120 MPa, between Al-1100",
        "# and S235). Keep steel density + modulus so the contact-wave numerics",
        "# stay stable, but use very low yield + heavy strain hardening (b=350)",
        "# so the plate dishes deeply before failing. EPS_p_max=0.40 lets the",
        "# bowl develop visibly before the centre tears.",
        "/MAT/PLAS_JOHNS/2",
        "soft_mild_steel_plate_candidate",
        "#              RHO_I",
        "              7.85E-6                   0",
        "#                  E                  Nu     Iflag",
        "                 200                  .30         0",
        "#                  a                   b                   n           EPS_p_max            SIG_max0",
        "                 120                 350                  .4                 0.4                 600",
        "#                  c           EPS_DOT_0       ICC   Fsmooth               F_cut               Chard",
        "                .005                1.E-3         0         0                   0                   0",
        "#                  m              T_melt              rhoC_p                 T_r",
        "                 .94                1800                   0                 293",
        "/FAIL/JOHNSON/2",
        "#                 D1                  D2                  D3                  D4                  D5",
        "                0.05                 0.5                -.54               -.015                   0",
        "#      EPSILON_DOT_0  IFAIL_SH  IFAIL_SO            EPSF_MIN                DADV               IXFEM",
        "                .001         2         1                   0                   0                    0",
        "#-  2. NODES",
        "/NODE",
    ]
    for n in proj_nodes + plate_nodes:
        nid, x, y, z = n
        L.append(f"{nid:10d}{x:20.6f}{y:20.6f}{z:20.6f}")

    L += [
        "#-  3. SOLID PROPERTIES + PARTS",
        "/PROP/SOLID/1",
        "projectile_solid",
        "# Isolid=24 (1pt + hourglass control) + h=0.15 (stiff hourglass).",
        "# Bullet stays nearly rigid (PLAS_JOHNS sigma_y=2500 capped at 3500),",
        "# so 1pt is fine and the higher h suppresses the spike artefact.",
        "#   Isolid    Ismstr      Iale     Icpre  Itetra10     Inpts   Itetra4    Iframe                  Dn",
        "        24         2         0         0         0         0         0         0                   0",
        "#                 qa                  qb                   h              Lambda                  Mu",
        "                 1.1                 .05                 .15                   0                   0",
        "#         deltaT_min            vdef_min            vdef_max             ASP_max             COL_min",
        "                   0                   0                   0                   0                   0",
        "#     Ndir sphpartID  Icontrol",
        "         0         0         0",
        "/PROP/SOLID/2",
        "plate_solid",
        "# Isolid=17 (HEPH 4-point integration). HEPH is hourglass-free by",
        "# construction (uses physical hourglass stabilisation, not numerical),",
        "# so the plate deforms as a smooth dished bend rather than the spiky",
        "# 1-pt-integration mode. Slower but worth it for visual fidelity.",
        "# Ismstr=2 (engineering strain, the Ismstr value PLAS_JOHNS LAW2 supports).",
        "#   Isolid    Ismstr      Iale     Icpre  Itetra10     Inpts   Itetra4    Iframe                  Dn",
        "        17         2         0         0         0         0         0         0                   0",
        "#                 qa                  qb                   h              Lambda                  Mu",
        "                 1.1                 .05                   0                   0                   0",
        "#         deltaT_min            vdef_min            vdef_max             ASP_max             COL_min",
        "                   0                   0                   0                   0                   0",
        "#     Ndir sphpartID  Icontrol",
        "         0         0         0",
        "/PART/1",
        "projectile_762_AP",
        "         1         1",
        "/PART/2",
        "plate_weldox_460E_100x100x8",
        "         2         2",
        "#-  4. ELEMENTS",
        "/BRICK/1",
    ]
    for elem in proj_elems:
        eid, _pid, *ns = elem
        L.append(f"{eid:10d}" + "".join(f"{n:10d}" for n in ns))
    L.append("/BRICK/2")
    for elem in plate_elems:
        eid, _pid, *ns = elem
        L.append(f"{eid:10d}" + "".join(f"{n:10d}" for n in ns))

    L += [
        "#-  5. NODE GROUPS",
        "/GRNOD/NODE/100",
        "projectile_nodes_for_inivel",
    ]
    for chunk_start in range(0, len(proj_nids), 8):
        chunk = proj_nids[chunk_start : chunk_start + 8]
        L.append("".join(f"{n:10d}" for n in chunk))
    L += [
        "/GRNOD/NODE/200",
        "plate_back_face_nodes_for_clamp",
    ]
    for chunk_start in range(0, len(back_face_nids), 8):
        chunk = back_face_nids[chunk_start : chunk_start + 8]
        L.append("".join(f"{n:10d}" for n in chunk))

    L += [
        "#-  6. BOUNDARY CONDITIONS",
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
        "# STFAC=1.0, Iform=2 (smooth penalty), INACTI=6 (clean initial pen).",
        "#              STFAC                FRIC             GAP_MIN              Tstart               Tstop",
        "                 1.0                  .2                 0.4                   0                   0",
        "#     I_BC                        INACTI               VIS_S               VIS_F              BUMULT",
        "       000                             6                  .2                  .2                   0",
        "#    Ifric    Ifiltr               Xfreq     Iform",
        "         0         0                   0         2",
        "#-  8. INITIAL VELOCITY (V0=180 m/s).",
        "#       Slower impact + soft plate -> deep dish + clean perforation.",
        "/INIVEL/TRA/1",
        "projectile_initial_velocity_candidate",
        "#                 Vx                  Vy                  Vz   Gnod_id   Skew_id",
        "                 180                   0                   0       100         0",
        "/END",
        "",
    ]

    starter = CASE / "model_00_0000.rad"
    starter.write_text("\n".join(L))
    n_proj = len(proj_nodes)
    n_plate = len(plate_nodes)
    e_proj = len(proj_elems)
    e_plate = len(plate_elems)
    print(f"  wrote starter: {starter.relative_to(CASE.parents[2])}")
    print(f"    nodes   : {n_proj + n_plate}  (proj {n_proj}, plate {n_plate})")
    print(f"    elements: {e_proj + e_plate}  (proj {e_proj}, plate {e_plate})")
    print(f"    plate back-face clamp nodes: {len(back_face_nids)}")
    return e_proj + e_plate


def write_engine(total_elems: int):
    L = [
        "#RADIOSS ENGINE",
        "#" + "-" * 98 + "|",
        "# GS-102-hifi-candidate / FM-04a Tier 1 hi-fi perforation engine deck",
        "#",
        "# Tier 1 engineering candidate; not signed validation; not benchmark agreement.",
        "#" + "-" * 98 + "|",
        "/RUN/gs102_hifi_candidate/1/",
        "  0.40",
        "#",
        "/PRINT/-1000",
        "#",
        "# 100 frames over 0.40 ms run (frame every 0.004 ms). At V0=200 m/s",
        "# the slower impact + softer aluminium plate -> dishing develops over",
        "# tens of microseconds before perforation; need longer T_end.",
        "/ANIM/DT",
        "0.0  0.004",
        "/ANIM/BRICK/EPSP",
        "/ANIM/BRICK/TENS/STRESS",
        "/ANIM/VECT/VEL",
        "#",
        "# CFL-driven dt with no mass scaling.",
        "/DT/NODA/CST/0",
        "0.9 0.0",
        "#",
        "# Brick deletion safety net at 1e-6 ms — catches only truly degenerate",
        "# hexes (volume going to zero), not normal ogive tip cells which sit",
        "# at dt ~1.6e-4 ms (1.5 mm chord / c=5048 mm/ms).",
        "/DT/BRICK/DEL",
        "0.0 1.0E-6",
        "",
    ]
    engine = CASE / "model_00_0001.rad"
    engine.write_text("\n".join(L))
    print(f"  wrote engine : {engine.relative_to(CASE.parents[2])}")


def main() -> int:
    CASE.mkdir(parents=True, exist_ok=True)
    print(f"Generating GS-102-hifi-candidate decks in {CASE}")
    n = write_starter()
    write_engine(n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
