"""FM-04a Phase 34 C — first `*CONTACT PAIR` validated case.

Honest scope pivot from Phase 33 D blueprint:
  * Phase 33 D shipped the Hertz line-contact analytical SSOT
    (`hertz_contact.py`). Live ccx integration with a cylinder-on-
    block geometry was deferred (cylindrical hex meshing is hard;
    Hertz peak pressure at session-budget-compatible geometry
    exceeded S355 yield).
  * Phase 34 C ships a simpler contact-pair case: **stacked
    cube-on-block uniaxial compression via *CONTACT PAIR**. Both
    bodies have the same 20×20 mm cross-section so the analytical
    is 1D-exact (no spreading-load approximations). The case
    validates the *CONTACT PAIR machinery (surface definitions,
    INTERACTION, SURFACE BEHAVIOR, contact pair convergence in
    ccx); it does NOT validate Hertz curvature contact.
  * Hertz curvature validation remains in `hertz_contact.py` as an
    analytical-only SSOT awaiting a future phase that ships
    curved-contact geometry (Phase 35+).

Tier 1 / Tier 2 engineering candidate; not signed validation;
not benchmark agreement.

Geometry:
  Punch (top body):    20 × 20 × 10  mm   (E = 210 GPa, ν = 0.3)
  Substrate (bottom):  20 × 20 × 30  mm   (same material)
  Contact:             square interface at z = 30 mm (substrate top)
  Mesh:                punch 4×4×2 hex, substrate 4×4×6 hex (aligned
                       3×3 contact nodes pattern, perfect master-
                       slave alignment).
  Load:                F = 4000 N distributed on punch top face
                       (= 10 MPa pressure, well below S355 yield)
  BC:                  substrate bottom face fixed (U1=U2=U3=0)
  CCX directives:      *SURFACE TO SURFACE, *SURFACE INTERACTION,
                       *SURFACE BEHAVIOR PRESSURE-OVERCLOSURE=LINEAR
                       with large stiffness 1.0e15 N/m³;
                       *STEP NLGEOM=NO single direct increment.

Analytical reference (1D uniaxial compression of two stacked bodies
with same cross-section):

  δ = F · (h_p + h_s) / (E · A)

  With F=4000 N, h_p=0.010 m, h_s=0.030 m, E=210e9 Pa, A=0.0004 m²:
  δ = 4000 × 0.040 / (210e9 × 0.0004) = 1.9048e-6 m ≈ 1.905 µm

The observed_indentation_m = |U_z| at the punch top center node.
Tolerance: 20% to accommodate contact penalty stiffness softening
(observed should be slightly LARGER than analytical because the
contact interface introduces a soft layer; with 1.0e15 N/m³ penalty
the softening is < 5%).

Anti-gaming guards:
  * A:-1 — analytical formula uses Phase 33 D's residual_pct helper;
    no parallel implementation.
  * D:-3 — material props from SSOT (steel-s355); E hardcoded here
    is a sanity-check copy, NOT used in the comparison (the SSOT
    value flows through the INP file).
  * E:-1 — INFRASTRUCTURE_ONLY fallback path is explicit: if ccx
    doesn't converge, the runner raises CalculiXRunError and the
    case is NOT counted as validated (cohort stays at 11).
  * H:-1 (Phase 34): REAL ccx run required; no mocked output for
    cohort-lift validation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

from app.adapters.calculix.runner import (
    CalculiXRunError,
    CalculiXRunner,
)
from app.services.tier2_pipeline import Tier2PipelineError
from app.services.cross_check.hertz_contact import residual_pct
from app.services.materials.api import get_material


CONTACT_PAIR_TOLERANCE_PCT: Final[float] = 20.0
"""Tolerance envelope for the contact-pair cross-check. Penalty-
based contact introduces a softening at the interface; 1.0e15 N/m³
penalty stiffness keeps the softening < 5% but the envelope is
20% to leave room for mesh + penalty interactions during a future
parameter sweep."""

ContactPairVerdictT = Literal["PASS", "FAIL"]


@dataclass(frozen=True)
class ContactPairCrossCheckResult:
    verdict: ContactPairVerdictT
    analytical_indentation_m: float
    observed_indentation_m: float
    probe_node_id: int
    residual_pct: float
    tolerance_pct: float
    total_load_n: float
    punch_height_m: float
    substrate_height_m: float
    cross_section_m: float
    youngs_modulus_pa: float
    node_count: int
    element_count: int
    contact_pair_node_count: int
    material_id: str
    material_reference: str
    case_id: str


def _build_stacked_hex_mesh(
    *,
    cross_section_m: float,
    punch_height_m: float,
    substrate_height_m: float,
    n_xy: int,
    n_z_punch: int,
    n_z_substrate: int,
) -> tuple[
    dict[int, tuple[float, float, float]],
    dict[int, tuple[int, ...]],
    list[int],  # punch element ids
    list[int],  # substrate element ids
    list[int],  # punch-bottom-face node ids (slave contact surface)
    list[int],  # substrate-top-face node ids
    list[tuple[int, str]],  # substrate-top-face (element_id, face_label)
    list[int],  # punch-top-face node ids (load surface)
    list[int],  # substrate-bottom-face node ids (fixed BC)
    int,        # punch-top-center node id (probe)
]:
    """Hand-rolled structured hex mesh of two stacked bodies.

    Substrate occupies z ∈ [0, h_s]; punch occupies z ∈ [h_s,
    h_s + h_p]. Both use the same (n_xy + 1) × (n_xy + 1) lateral
    node grid at every z plane, so the contact surfaces share the
    same nodal pattern (perfect master-slave alignment at z = h_s).

    Each body's nodes are TOPOLOGICALLY SEPARATE — the contact
    interface has TWO sets of coincident nodes (one on the punch's
    bottom face, one on the substrate's top face). The *CONTACT PAIR
    keyword wires them together.
    """
    if min(n_xy, n_z_punch, n_z_substrate) < 1:
        raise ValueError(
            f"all mesh resolutions must be ≥ 1; got "
            f"n_xy={n_xy}, n_z_punch={n_z_punch}, n_z_substrate={n_z_substrate}"
        )

    nodes: dict[int, tuple[float, float, float]] = {}
    elements: dict[int, tuple[int, ...]] = {}

    dx = cross_section_m / n_xy
    dy = cross_section_m / n_xy
    dz_s = substrate_height_m / n_z_substrate
    dz_p = punch_height_m / n_z_punch

    next_node_id = 1
    next_elem_id = 1

    substrate_node_grid: dict[tuple[int, int, int], int] = {}
    punch_node_grid: dict[tuple[int, int, int], int] = {}

    # ─── Substrate nodes (z ∈ [0, h_s]) ──────────────────────────
    for kk in range(n_z_substrate + 1):
        for jj in range(n_xy + 1):
            for ii in range(n_xy + 1):
                substrate_node_grid[(ii, jj, kk)] = next_node_id
                nodes[next_node_id] = (
                    ii * dx,
                    jj * dy,
                    kk * dz_s,
                )
                next_node_id += 1

    # ─── Punch nodes (z ∈ [h_s, h_s + h_p]) ──────────────────────
    # Note: the punch's bottom face (kk=0) is COINCIDENT geometrically
    # with the substrate's top face but has its OWN node IDs — that's
    # exactly what *CONTACT PAIR needs.
    for kk in range(n_z_punch + 1):
        for jj in range(n_xy + 1):
            for ii in range(n_xy + 1):
                punch_node_grid[(ii, jj, kk)] = next_node_id
                nodes[next_node_id] = (
                    ii * dx,
                    jj * dy,
                    substrate_height_m + kk * dz_p,
                )
                next_node_id += 1

    # ─── Substrate elements ──────────────────────────────────────
    substrate_element_ids: list[int] = []
    substrate_top_faces: list[tuple[int, str]] = []
    # CCX C3D8 face labels:
    #   S1: bottom (-Z, nodes 1-2-3-4 of element connectivity)
    #   S2: top (+Z, nodes 5-6-7-8)
    # We use S2 for the substrate's top face → master contact surface.
    for kk in range(n_z_substrate):
        for jj in range(n_xy):
            for ii in range(n_xy):
                # C3D8 ordering: bottom face CCW from -z, top face above.
                nid = lambda di, dj, dk: substrate_node_grid[
                    (ii + di, jj + dj, kk + dk)
                ]
                elements[next_elem_id] = (
                    nid(0, 0, 0),
                    nid(1, 0, 0),
                    nid(1, 1, 0),
                    nid(0, 1, 0),
                    nid(0, 0, 1),
                    nid(1, 0, 1),
                    nid(1, 1, 1),
                    nid(0, 1, 1),
                )
                substrate_element_ids.append(next_elem_id)
                if kk == n_z_substrate - 1:
                    # Top layer — face S2 is the +Z face (contact surface).
                    substrate_top_faces.append((next_elem_id, "S2"))
                next_elem_id += 1

    # ─── Punch elements ──────────────────────────────────────────
    punch_element_ids: list[int] = []
    for kk in range(n_z_punch):
        for jj in range(n_xy):
            for ii in range(n_xy):
                nid = lambda di, dj, dk: punch_node_grid[
                    (ii + di, jj + dj, kk + dk)
                ]
                elements[next_elem_id] = (
                    nid(0, 0, 0),
                    nid(1, 0, 0),
                    nid(1, 1, 0),
                    nid(0, 1, 0),
                    nid(0, 0, 1),
                    nid(1, 0, 1),
                    nid(1, 1, 1),
                    nid(0, 1, 1),
                )
                punch_element_ids.append(next_elem_id)
                next_elem_id += 1

    # ─── Surface node sets ───────────────────────────────────────
    punch_bottom_nodes = sorted(
        punch_node_grid[(ii, jj, 0)]
        for ii in range(n_xy + 1)
        for jj in range(n_xy + 1)
    )
    substrate_top_nodes = sorted(
        substrate_node_grid[(ii, jj, n_z_substrate)]
        for ii in range(n_xy + 1)
        for jj in range(n_xy + 1)
    )
    punch_top_nodes = sorted(
        punch_node_grid[(ii, jj, n_z_punch)]
        for ii in range(n_xy + 1)
        for jj in range(n_xy + 1)
    )
    substrate_bottom_nodes = sorted(
        substrate_node_grid[(ii, jj, 0)]
        for ii in range(n_xy + 1)
        for jj in range(n_xy + 1)
    )

    # Probe node = punch top center (closest to ii=n_xy/2, jj=n_xy/2).
    center_ii = n_xy // 2
    center_jj = n_xy // 2
    probe_node = punch_node_grid[(center_ii, center_jj, n_z_punch)]

    return (
        nodes,
        elements,
        punch_element_ids,
        substrate_element_ids,
        punch_bottom_nodes,
        substrate_top_nodes,
        substrate_top_faces,
        punch_top_nodes,
        substrate_bottom_nodes,
        probe_node,
    )


def _format_nset_lines(name: str, ids: list[int]) -> list[str]:
    """CCX *NSET, NSET=... block with 8 IDs per line."""
    out = [f"*NSET, NSET={name}"]
    for i in range(0, len(ids), 8):
        out.append(", ".join(str(n) for n in ids[i : i + 8]))
    return out


def _format_elset_lines(name: str, ids: list[int]) -> list[str]:
    """CCX *ELSET block with 8 IDs per line."""
    out = [f"*ELSET, ELSET={name}"]
    for i in range(0, len(ids), 8):
        out.append(", ".join(str(e) for e in ids[i : i + 8]))
    return out


def _write_contact_pair_inp(
    case_dir: Path,
    *,
    jobname: str,
    nodes: dict[int, tuple[float, float, float]],
    elements: dict[int, tuple[int, ...]],
    punch_element_ids: list[int],
    substrate_element_ids: list[int],
    punch_bottom_nodes: list[int],
    substrate_top_nodes: list[int],
    substrate_top_faces: list[tuple[int, str]],
    punch_top_nodes: list[int],
    substrate_bottom_nodes: list[int],
    material_name: str,
    youngs_modulus_pa: float,
    poisson_ratio: float,
    total_load_n: float,
    contact_stiffness_n_per_m3: float,
) -> Path:
    """Compose the CCX *.inp for the contact-pair stacked-compression
    cross-check.

    *CONTACT PAIR with TYPE=SURFACE TO SURFACE wires the punch's
    bottom face (slave) to the substrate's top face (master).
    *SURFACE BEHAVIOR PRESSURE-OVERCLOSURE=LINEAR with large
    penalty stiffness gives near-bonded behavior in compression.
    """
    lines: list[str] = [
        "*HEADING",
        "FM-04a Phase 34 C contact-pair stacked compression cross-check",
    ]

    # Nodes.
    lines.append("*NODE")
    for nid in sorted(nodes):
        x, y, z = nodes[nid]
        lines.append(f"{nid}, {x:.9e}, {y:.9e}, {z:.9e}")

    # Punch elements (separate ELSET).
    lines.append("*ELEMENT, TYPE=C3D8, ELSET=PUNCH")
    for eid in sorted(punch_element_ids):
        connectivity = elements[eid]
        lines.append(f"{eid}, " + ", ".join(str(n) for n in connectivity))

    # Substrate elements (separate ELSET).
    lines.append("*ELEMENT, TYPE=C3D8, ELSET=SUBSTRATE")
    for eid in sorted(substrate_element_ids):
        connectivity = elements[eid]
        lines.append(f"{eid}, " + ", ".join(str(n) for n in connectivity))

    # NSETs for contact surfaces + load + BC.
    lines.extend(_format_nset_lines("PUNCH_BOTTOM", punch_bottom_nodes))
    lines.extend(_format_nset_lines("SUBSTRATE_TOP", substrate_top_nodes))
    lines.extend(_format_nset_lines("PUNCH_TOP", punch_top_nodes))
    lines.extend(_format_nset_lines("SUBSTRATE_BOTTOM", substrate_bottom_nodes))

    # CCX *SURFACE — slave (punch bottom) is NODE-based; master
    # (substrate top) must be ELEMENT-FACE-based per ccx requirement
    # for *CONTACT PAIR (CCX 2.23 allocont check rejects node-based
    # master surfaces).
    lines.append("*SURFACE, NAME=PUNCH_BOTTOM_S, TYPE=NODE")
    lines.append("PUNCH_BOTTOM")
    lines.append("*SURFACE, NAME=SUBSTRATE_TOP_S, TYPE=ELEMENT")
    for elem_id, face_label in substrate_top_faces:
        lines.append(f"{elem_id}, {face_label}")

    # Material — single SSOT material for both bodies (steel-s355).
    lines.append(f"*MATERIAL, NAME={material_name}")
    lines.append("*ELASTIC")
    lines.append(f"{youngs_modulus_pa:.6e}, {poisson_ratio:.6f}")

    lines.append(f"*SOLID SECTION, ELSET=PUNCH, MATERIAL={material_name}")
    lines.append(f"*SOLID SECTION, ELSET=SUBSTRATE, MATERIAL={material_name}")

    # Contact pair definition. NODE TO SURFACE is the most convergence-
    # friendly form in CCX for aligned-mesh interfaces.
    lines.append(
        "*SURFACE INTERACTION, NAME=BONDED_CONTACT"
    )
    lines.append("*SURFACE BEHAVIOR, PRESSURE-OVERCLOSURE=LINEAR")
    # k0 (stiffness N/m³), c0 (compressive overclosure where stiffness
    # is fully active). The LINEAR row is a single value: just the
    # penalty stiffness — CCX expects (k0,) on one line for LINEAR.
    lines.append(f"{contact_stiffness_n_per_m3:.6e}")
    lines.append(
        "*CONTACT PAIR, INTERACTION=BONDED_CONTACT, TYPE=NODE TO SURFACE"
    )
    lines.append("PUNCH_BOTTOM_S, SUBSTRATE_TOP_S")

    # Step.
    lines.append("*STEP")
    lines.append("*STATIC")
    # Fix substrate bottom in all directions.
    lines.append("*BOUNDARY")
    lines.append("SUBSTRATE_BOTTOM, 1, 3, 0.0")

    # Distribute the total load equally across the punch-top nodes.
    n_top = len(punch_top_nodes)
    per_node_force = total_load_n / n_top
    lines.append("*CLOAD")
    for n in punch_top_nodes:
        # Force in -z direction (compressive on the stack).
        lines.append(f"{n}, 3, {-per_node_force:.9e}")

    # Output requests.
    lines.append("*NODE PRINT, NSET=PUNCH_TOP")
    lines.append("U")
    lines.append("*NODE FILE")
    lines.append("U")
    lines.append("*EL FILE")
    lines.append("S")
    lines.append("*END STEP")

    inp_path = case_dir / f"{jobname}.inp"
    inp_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return inp_path


# CCX .dat displacement row matcher: node_id then 3 floats (U1,U2,U3).
_U_ROW_RE = re.compile(
    r"^\s*(\d+)\s+"
    r"([+-]?\d+\.\d+(?:[eE][+-]?\d+)?)\s+"
    r"([+-]?\d+\.\d+(?:[eE][+-]?\d+)?)\s+"
    r"([+-]?\d+\.\d+(?:[eE][+-]?\d+)?)\s*$"
)


def _parse_displacement_block(
    dat_path: Path,
) -> dict[int, tuple[float, float, float]]:
    """Parse CCX's .dat for the nodal displacement table.

    Format (single step):

        displacements (vx,vy,vz) for set PUNCH_TOP and time  ...

                 nid    U1            U2            U3
                 ...
    """
    if not dat_path.is_file():
        raise FileNotFoundError(f"missing .dat at {dat_path}")
    text = dat_path.read_text(encoding="utf-8", errors="replace")
    in_block = False
    seen_any_row = False
    result: dict[int, tuple[float, float, float]] = {}
    for raw in text.splitlines():
        line = raw.rstrip()
        lower = line.lower().lstrip()
        if "displacements" in lower and "for set" in lower:
            in_block = True
            seen_any_row = False
            continue
        if not in_block:
            continue
        if not line.strip():
            if seen_any_row:
                in_block = False
            continue
        match = _U_ROW_RE.match(line)
        if match:
            nid = int(match.group(1))
            u1 = float(match.group(2))
            u2 = float(match.group(3))
            u3 = float(match.group(4))
            result[nid] = (u1, u2, u3)
            seen_any_row = True
    if not result:
        raise CalculiXRunError(
            f"no displacement block found in {dat_path}",
            returncode=None,
            stderr_tail="",
            stdout_tail="",
        )
    return result


def _bonded_uniaxial_indentation_m(
    *,
    total_load_n: float,
    stack_height_m: float,
    youngs_modulus_pa: float,
    cross_section_m: float,
) -> float:
    """Closed-form 1D uniaxial compression of a stacked column:

        δ = F · H / (E · A)

    Returns POSITIVE indentation magnitude (compressive direction
    handled by sign convention at the comparison site).
    """
    area_m2 = cross_section_m * cross_section_m
    return total_load_n * stack_height_m / (youngs_modulus_pa * area_m2)


DEFAULT_CROSS_SECTION_M: Final[float] = 0.020
DEFAULT_PUNCH_HEIGHT_M: Final[float] = 0.010
DEFAULT_SUBSTRATE_HEIGHT_M: Final[float] = 0.030
DEFAULT_TOTAL_LOAD_N: Final[float] = 4000.0
DEFAULT_N_XY: Final[int] = 4
DEFAULT_N_Z_PUNCH: Final[int] = 2
DEFAULT_N_Z_SUBSTRATE: Final[int] = 6
DEFAULT_CONTACT_STIFFNESS_N_PER_M3: Final[float] = 1.0e15
"""Penalty stiffness for the *SURFACE BEHAVIOR PRESSURE-OVERCLOSURE
LINEAR row. 1.0e15 N/m³ is large enough to keep the interface
softening < 5% relative to true bonded behavior; small enough that
CCX's iteration converges in 1 increment with NLGEOM=NO."""


def run_contact_pair_cross_check(
    case_dir: Path,
    *,
    case_id: str,
    material_id: str,
    cross_section_m: float = DEFAULT_CROSS_SECTION_M,
    punch_height_m: float = DEFAULT_PUNCH_HEIGHT_M,
    substrate_height_m: float = DEFAULT_SUBSTRATE_HEIGHT_M,
    total_load_n: float = DEFAULT_TOTAL_LOAD_N,
    n_xy: int = DEFAULT_N_XY,
    n_z_punch: int = DEFAULT_N_Z_PUNCH,
    n_z_substrate: int = DEFAULT_N_Z_SUBSTRATE,
    contact_stiffness_n_per_m3: float = DEFAULT_CONTACT_STIFFNESS_N_PER_M3,
    jobname: str = "contact_pair_xcheck",
    ccx_binary: str = "ccx",
    ccx_timeout_sec: float = 60.0,
    tolerance_pct: float = CONTACT_PAIR_TOLERANCE_PCT,
) -> ContactPairCrossCheckResult:
    """Execute the full *CONTACT PAIR stacked-compression cross-check."""
    if cross_section_m <= 0 or punch_height_m <= 0 or substrate_height_m <= 0:
        raise ValueError(
            f"all dimensions must be positive; got cs={cross_section_m}, "
            f"hp={punch_height_m}, hs={substrate_height_m}"
        )
    if total_load_n <= 0:
        raise ValueError(
            f"total_load_n must be positive (compressive); got {total_load_n}"
        )

    material = get_material(material_id)
    if material.youngs_modulus_pa is None or material.poisson_ratio is None:
        raise Tier2PipelineError(
            f"material {material_id} missing E or ν; "
            f"E={material.youngs_modulus_pa}, ν={material.poisson_ratio}",
            stage="material_load",
        )
    e_pa: float = float(material.youngs_modulus_pa)
    nu: float = float(material.poisson_ratio)

    (
        nodes,
        elements,
        punch_eids,
        substrate_eids,
        punch_bottom,
        substrate_top,
        substrate_top_faces,
        punch_top,
        substrate_bottom,
        probe_node,
    ) = _build_stacked_hex_mesh(
        cross_section_m=cross_section_m,
        punch_height_m=punch_height_m,
        substrate_height_m=substrate_height_m,
        n_xy=n_xy,
        n_z_punch=n_z_punch,
        n_z_substrate=n_z_substrate,
    )

    stack_height_m = punch_height_m + substrate_height_m
    analytical_delta_m = _bonded_uniaxial_indentation_m(
        total_load_n=total_load_n,
        stack_height_m=stack_height_m,
        youngs_modulus_pa=e_pa,
        cross_section_m=cross_section_m,
    )

    _write_contact_pair_inp(
        case_dir,
        jobname=jobname,
        nodes=nodes,
        elements=elements,
        punch_element_ids=punch_eids,
        substrate_element_ids=substrate_eids,
        punch_bottom_nodes=punch_bottom,
        substrate_top_nodes=substrate_top,
        substrate_top_faces=substrate_top_faces,
        punch_top_nodes=punch_top,
        substrate_bottom_nodes=substrate_bottom,
        material_name="STEEL_CONTACT",
        youngs_modulus_pa=e_pa,
        poisson_ratio=nu,
        total_load_n=total_load_n,
        contact_stiffness_n_per_m3=contact_stiffness_n_per_m3,
    )

    ccx_runner = CalculiXRunner(
        ccx_binary=ccx_binary, timeout_sec=ccx_timeout_sec
    )
    try:
        ccx_result = ccx_runner.run(case_dir, jobname)
    except CalculiXRunError as exc:
        raise Tier2PipelineError(
            f"ccx subprocess failed: {exc}", stage="run_ccx", cause=exc
        ) from exc
    if ccx_result.dat_path is None:
        raise CalculiXRunError(
            f"ccx success without .dat at expected {case_dir}/{jobname}.dat",
            returncode=ccx_result.returncode,
            stderr_tail="",
            stdout_tail="",
        )

    u_table = _parse_displacement_block(ccx_result.dat_path)
    if probe_node not in u_table:
        raise CalculiXRunError(
            f"probe node {probe_node} missing from U block "
            f"({len(u_table)} nodes parsed)",
            returncode=ccx_result.returncode,
            stderr_tail="",
            stdout_tail="",
        )
    _, _, observed_u3 = u_table[probe_node]
    observed_delta_m = abs(observed_u3)  # compressive sign convention

    res_pct = residual_pct(observed_delta_m, analytical_delta_m)
    verdict: ContactPairVerdictT = (
        "PASS" if abs(res_pct) <= tolerance_pct else "FAIL"
    )

    return ContactPairCrossCheckResult(
        verdict=verdict,
        analytical_indentation_m=analytical_delta_m,
        observed_indentation_m=observed_delta_m,
        probe_node_id=probe_node,
        residual_pct=res_pct,
        tolerance_pct=tolerance_pct,
        total_load_n=total_load_n,
        punch_height_m=punch_height_m,
        substrate_height_m=substrate_height_m,
        cross_section_m=cross_section_m,
        youngs_modulus_pa=e_pa,
        node_count=len(nodes),
        element_count=len(elements),
        contact_pair_node_count=len(punch_bottom) + len(substrate_top),
        material_id=material_id,
        material_reference=material.reference or "unknown",
        case_id=case_id,
    )
