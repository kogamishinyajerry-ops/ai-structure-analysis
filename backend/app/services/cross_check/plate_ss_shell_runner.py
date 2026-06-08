"""S4 shell simply-supported plate cross-check runner — Phase 29 A.

The FIRST validated case to use **shell elements** (S4). Closes the
Phase 22-28 FEA-Dim-1-hard-cap-at-≤75 issue: every prior case used
C3D4 / C3D8 / C3D10 / B31. Shell discretization is core to thin-
walled structures (plates, panels, skins) and a ballistic-FEA
workbench without ANY shell validated case is a load-bearing gap.

The analytical helper from ``plate_simply_supported`` is reused
verbatim — Timoshenko α·q·a⁴/D is element-discretization-agnostic.
Only the MESH and BC representation change vs the C3D10 case
(``plate_ss_runner.py``).

Key differences from the C3D10 runner:
  * **Hand-rolled structured 2D quad mesh** — no gmsh dependency.
    20×20 quads → 441 nodes. This is the standard convergence-study
    mesh for thin-plate S4 problems; analytical α=0.00406 is
    expected to reproduce to within a few percent at this
    refinement.
  * **No 3D solid extrusion** — shell IS the midplane. BC pattern
    simplifies to: u_z = 0 along all 4 edges + corner u_x = u_y = 0
    (RBM kill). No 3-corner-pin convolution needed.
  * **Pressure via *DLOAD P2** — S4 face label P2 = positive-normal
    side. CalculiX convention: positive pressure value = compressive
    (pushing INTO the face), so P2 with positive value deflects the
    plate in -z. Matches the analytical convention of negative
    pressure_pa.
  * **Pure shell representation** of simply-supported BC: u_z = 0
    on edges, rotations FREE (the defining simply-supported
    constraint). C3D10 runner approximated this with edge-line
    clamps at z=0; the S4 representation is exact for thin-plate
    theory.

**Anti-gaming guard A:-1:** the runner reads w at the NODE NEAREST
the plate center (a/2, a/2, 0), NOT max|w| across the mesh. Edge
or corner artifacts cannot pad the verdict.

**Anti-gaming guard E:-1:** convergence pin — the 20×20 mesh is
required by the runner default; a strict pin at the test level
prevents a future "drop to 4×4 and live with the inflation" path.

This runner is intentionally SELF-CONTAINED (does not call
``run_tier2_meshed_pipeline``) — same rationale as the C3D10 runner.

Tier 1 / Tier 2 engineering candidate; not signed validation; not
benchmark agreement.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final, Literal

from app.adapters.calculix import (
    CalculiXReader,
    CalculiXRunError,
    CalculiXRunner,
)
from app.core.types import CanonicalField, UnitSystem
from app.services.materials import get_material
from app.services.tier2_pipeline import (
    Tier2PipelineError,
    material_to_hex_descriptor,
)

from .cylinder_pv_runner import VERDICT_YAML_FILENAME
from .plate_simply_supported import (
    PLATE_SS_CROSS_CHECK_TOLERANCE_PCT,
    PLATE_SS_SMALL_DEFLECTION_RATIO_MAX,
    compute_simply_supported_plate_center_deflection_m,
    plate_flexural_rigidity_d_n_m,
)

PlateSSShellCrossCheckVerdict = Literal["PASS", "FAIL"]

DEFAULT_N_PER_SIDE: Final[int] = 20
"""Default mesh resolution: 20 quad elements per side → 400 elements
total, 441 nodes. Convergence pin (E:-1) enforces this at the test
level; coarser meshes would inflate the residual and softer-pad the
verdict."""

_NSET_ROW_MAX: Final[int] = 16


@dataclass(frozen=True)
class PlateSSShellCrossCheckResult:
    """Outcome of the S4 shell simply-supported plate cross-check.

    Same fields as PlateSSCrossCheckResult, with `n_per_side` added
    for the convergence pin and `element_type` fixed to 'S4'.
    """

    verdict: PlateSSShellCrossCheckVerdict
    analytical_w_center_m: float
    observed_w_center_m: float
    residual_pct: float
    tolerance_pct: float
    flexural_rigidity_d: float
    side_length_m: float
    thickness_m: float
    pressure_pa: float
    applied_force_n: float
    node_count: int
    element_count: int
    n_per_side: int
    element_type: Literal["S4"]
    material_id: str
    material_reference: str
    case_id: str
    generated_at_utc: str
    small_deflection_ratio: float


def make_structured_quad_mesh(
    side_length_m: float, n_per_side: int
) -> tuple[
    dict[int, tuple[float, float, float]], dict[int, tuple[int, int, int, int]]
]:
    """Return (nodes_dict, elements_dict) for a structured n×n quad
    mesh on the plane z=0, spanning [0, a]² in (x, y).

    Node numbering is row-major (i first, then j), starting at 1.
    Element connectivity follows the S4 right-hand-rule winding
    (CCW when viewed from +z), giving a +z face normal.

    Returns:
        nodes: 1-indexed dict of node_id → (x, y, z).
        elements: 1-indexed dict of element_id → (n1, n2, n3, n4).
    """
    if side_length_m <= 0:
        raise ValueError(f"side_length_m must be positive; got {side_length_m}")
    if n_per_side < 2:
        raise ValueError(f"n_per_side must be >= 2; got {n_per_side}")
    nodes: dict[int, tuple[float, float, float]] = {}
    h = side_length_m / n_per_side
    nid = 1
    for j in range(n_per_side + 1):
        for i in range(n_per_side + 1):
            nodes[nid] = (i * h, j * h, 0.0)
            nid += 1
    elements: dict[int, tuple[int, int, int, int]] = {}
    eid = 1
    stride = n_per_side + 1
    for j in range(n_per_side):
        for i in range(n_per_side):
            n1 = j * stride + i + 1
            n2 = n1 + 1
            n3 = n2 + stride
            n4 = n1 + stride
            elements[eid] = (n1, n2, n3, n4)
            eid += 1
    return nodes, elements


def _classify_node(
    x: float, y: float, side_length_m: float, tol_m: float
) -> Literal["corner", "edge", "interior"]:
    """Boundary status for consistent-lumping / BC purposes."""
    on_x_edge = abs(x) <= tol_m or abs(x - side_length_m) <= tol_m
    on_y_edge = abs(y) <= tol_m or abs(y - side_length_m) <= tol_m
    if on_x_edge and on_y_edge:
        return "corner"
    if on_x_edge or on_y_edge:
        return "edge"
    return "interior"


def _find_center_node(
    nodes: dict[int, tuple[float, float, float]], side_length_m: float
) -> int:
    """Return the node_id closest to the plate center (a/2, a/2, 0)."""
    cx = cy = side_length_m / 2
    best_nid = next(iter(nodes))
    best_d2 = math.inf
    for nid, (x, y, _z) in nodes.items():
        d2 = (x - cx) ** 2 + (y - cy) ** 2
        if d2 < best_d2:
            best_d2 = d2
            best_nid = nid
    return best_nid


def _format_nset(name: str, node_ids: list[int]) -> list[str]:
    """Format a `*NSET, NSET=name` block with continuation lines."""
    lines = [f"*NSET, NSET={name}"]
    chunk: list[str] = []
    for nid in node_ids:
        chunk.append(str(nid))
        if len(chunk) >= _NSET_ROW_MAX:
            lines.append(",".join(chunk))
            chunk = []
    if chunk:
        lines.append(",".join(chunk))
    return lines


def _write_plate_ss_shell_inp(
    case_dir: Path,
    *,
    jobname: str,
    nodes: dict[int, tuple[float, float, float]],
    elements: dict[int, tuple[int, int, int, int]],
    material_name: str,
    youngs_modulus_pa: float,
    poisson_ratio: float,
    thickness_m: float,
    pressure_pa: float,
    side_length_m: float,
) -> Path:
    """Compose the S4 plate INP. Returns the .inp path."""
    tol = side_length_m / 1.0e6
    edge_nodes: list[int] = []
    corner_nodes: list[int] = []
    for nid, (x, y, _z) in nodes.items():
        kind = _classify_node(x, y, side_length_m, tol)
        if kind == "corner":
            corner_nodes.append(nid)
            edge_nodes.append(nid)  # corners are ALSO on the edge
        elif kind == "edge":
            edge_nodes.append(nid)
    edge_nodes.sort()
    corner_nodes.sort()

    lines: list[str] = [
        "*HEADING",
        f"Phase 29 A — S4 shell simply-supported plate · case {jobname}",
        "*NODE, NSET=ALL_NODES",
    ]
    for nid in sorted(nodes):
        x, y, z = nodes[nid]
        lines.append(f"{nid}, {x:.6e}, {y:.6e}, {z:.6e}")

    lines.append("*ELEMENT, TYPE=S4, ELSET=PLATE")
    for eid in sorted(elements):
        n1, n2, n3, n4 = elements[eid]
        lines.append(f"{eid}, {n1}, {n2}, {n3}, {n4}")

    lines.append(f"*MATERIAL, NAME={material_name}")
    lines.append("*ELASTIC")
    lines.append(f"{youngs_modulus_pa:.6e}, {poisson_ratio:.6e}")
    lines.append(f"*SHELL SECTION, ELSET=PLATE, MATERIAL={material_name}")
    lines.append(f"{thickness_m:.6e}")

    lines.extend(_format_nset("NEDGES_ALL", edge_nodes))
    lines.extend(_format_nset("NCORNERS", corner_nodes))

    # BC: u_z=0 along all 4 edges (simply-supported); corners
    # additionally u_x=u_y=0 to kill in-plane RBM. Rotational DOFs
    # remain FREE (defining simply-supported constraint).
    lines.append("*BOUNDARY")
    lines.append("NEDGES_ALL, 3, 3, 0.0")
    lines.append("NCORNERS, 1, 2, 0.0")

    # Load: *DLOAD P2 = pressure on +z face. CalculiX convention:
    # positive pressure value = compressive (pushing INTO the face).
    # We want plate to deflect in -z under positive |pressure_pa|; use
    # |pressure_pa| with P2 to get that.
    lines.append("*STEP")
    lines.append("*STATIC")
    lines.append("*DLOAD")
    lines.append(f"PLATE, P2, {abs(pressure_pa):.6e}")
    lines.append("*NODE FILE")
    lines.append("U")
    lines.append("*END STEP")

    inp_path = case_dir / f"{jobname}.inp"
    inp_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return inp_path


def run_plate_ss_shell_cross_check(
    case_dir: Path,
    *,
    case_id: str,
    material_id: str,
    side_length_m: float = 1.0,
    thickness_m: float = 0.020,
    pressure_pa: float = 1.0e4,
    n_per_side: int = DEFAULT_N_PER_SIDE,
    jobname: str = "plate_ss_shell_xcheck",
    ccx_binary: str = "ccx",
    ccx_timeout_sec: float = 180.0,
    tolerance_pct: float = PLATE_SS_CROSS_CHECK_TOLERANCE_PCT,
) -> PlateSSShellCrossCheckResult:
    """Execute the full S4-shell simply-supported plate cross-check.

    Steps:
      1. Resolve material via the SSOT library.
      2. Hand-roll structured n_per_side × n_per_side quad mesh.
      3. Compose INP with S4 elements + simply-supported BC + *DLOAD P2.
      4. Run ccx.
      5. Read u_z at the plate-center node (A:-1 guard).
      6. Compare to Timoshenko α·q·a⁴/D analytical.
    """
    if side_length_m <= 0:
        raise ValueError(f"side_length_m must be positive; got {side_length_m}")
    if thickness_m <= 0:
        raise ValueError(f"thickness_m must be positive; got {thickness_m}")
    if pressure_pa == 0:
        raise ValueError("pressure_pa must be non-zero")
    if n_per_side < 4:
        raise ValueError(
            f"n_per_side must be >= 4 (convergence); got {n_per_side}"
        )

    material = get_material(material_id)
    hex_descriptor = material_to_hex_descriptor(material)

    analytical_w = compute_simply_supported_plate_center_deflection_m(
        side_length_m=side_length_m,
        thickness_m=thickness_m,
        youngs_modulus_pa=hex_descriptor.youngs_modulus_pa,
        poisson_ratio=hex_descriptor.poisson_ratio,
        pressure_pa=-abs(pressure_pa),  # negative = downward
    )
    d = plate_flexural_rigidity_d_n_m(
        youngs_modulus_pa=hex_descriptor.youngs_modulus_pa,
        thickness_m=thickness_m,
        poisson_ratio=hex_descriptor.poisson_ratio,
    )

    nodes, elements = make_structured_quad_mesh(side_length_m, n_per_side)

    inp_path = _write_plate_ss_shell_inp(
        case_dir,
        jobname=jobname,
        nodes=nodes,
        elements=elements,
        material_name=hex_descriptor.name,
        youngs_modulus_pa=hex_descriptor.youngs_modulus_pa,
        poisson_ratio=hex_descriptor.poisson_ratio,
        thickness_m=thickness_m,
        pressure_pa=pressure_pa,
        side_length_m=side_length_m,
    )
    _ = inp_path

    ccx_runner = CalculiXRunner(ccx_binary=ccx_binary, timeout_sec=ccx_timeout_sec)
    try:
        ccx_result = ccx_runner.run(case_dir, jobname)
    except CalculiXRunError as exc:
        raise Tier2PipelineError(
            f"ccx subprocess failed: {exc}", stage="run_ccx", cause=exc
        ) from exc
    assert ccx_result.frd_path is not None, "ccx success without .frd"

    reader = CalculiXReader(ccx_result.frd_path, unit_system=UnitSystem.SI)
    disp_field = reader.get_field(CanonicalField.DISPLACEMENT, step_id=1)
    if disp_field is None:
        raise CalculiXRunError(
            f"no displacement field in {ccx_result.frd_path}",
            returncode=None,
            stderr_tail="",
            stdout_tail="",
        )
    arr = disp_field.at_nodes()
    sorted_ids = sorted(nodes)
    center_node_id = _find_center_node(nodes, side_length_m)
    center_idx = sorted_ids.index(center_node_id)
    observed_w = float(arr[center_idx, 2])  # DOF 3 = u_z

    # A:-1 audit-trail sanity: center node lies in the central
    # characteristic-length disk (mesh-half-cell radius is sufficient
    # for a structured mesh).
    cx, cy, _ = nodes[center_node_id]
    half_cell = side_length_m / n_per_side / 2.0
    if math.hypot(cx - side_length_m / 2, cy - side_length_m / 2) > half_cell + 1e-9:
        raise CalculiXRunError(
            f"center node ({cx},{cy}) lies > half-cell from plate-center "
            f"on a structured {n_per_side}×{n_per_side} mesh — "
            f"node lookup bug",
            returncode=None,
            stderr_tail="",
            stdout_tail="",
        )

    residual_pct = (
        (abs(observed_w) - abs(analytical_w)) / abs(analytical_w) * 100.0
    )
    small_deflection_ratio = abs(observed_w) / thickness_m

    verdict: PlateSSShellCrossCheckVerdict
    if small_deflection_ratio > PLATE_SS_SMALL_DEFLECTION_RATIO_MAX:
        verdict = "FAIL"
    elif abs(residual_pct) <= tolerance_pct:
        verdict = "PASS"
    else:
        verdict = "FAIL"

    return PlateSSShellCrossCheckResult(
        verdict=verdict,
        analytical_w_center_m=analytical_w,
        observed_w_center_m=observed_w,
        residual_pct=residual_pct,
        tolerance_pct=tolerance_pct,
        flexural_rigidity_d=d,
        side_length_m=side_length_m,
        thickness_m=thickness_m,
        pressure_pa=pressure_pa,
        applied_force_n=abs(pressure_pa) * side_length_m * side_length_m,
        node_count=len(nodes),
        element_count=len(elements),
        n_per_side=n_per_side,
        element_type="S4",
        material_id=material_id,
        material_reference=material.reference,
        case_id=case_id,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        small_deflection_ratio=small_deflection_ratio,
    )


def write_plate_ss_shell_verdict_yaml(
    case_golden_dir: Path,
    result: PlateSSShellCrossCheckResult,
) -> Path:
    """Persist a plate-SS-shell verdict artifact (schema 1.1.0 — adds
    tolerance_pct + element_type + n_per_side over the 1.0.0 schema
    used by the other 8 cases)."""
    if not case_golden_dir.is_dir():
        raise FileNotFoundError(
            f"case_golden_dir {case_golden_dir!s} must exist"
        )
    payload = {
        "schema_version": "1.1.0",
        "solver_kind": "linear_static",
        "case_id": result.case_id,
        "verdict": result.verdict,
        "tolerance_pct": result.tolerance_pct,
        "residual_pct": result.residual_pct,
        "analytical_w_center_m": result.analytical_w_center_m,
        "observed_w_center_m": result.observed_w_center_m,
        "flexural_rigidity_d": result.flexural_rigidity_d,
        "side_length_m": result.side_length_m,
        "thickness_m": result.thickness_m,
        "pressure_pa": result.pressure_pa,
        "applied_force_n": result.applied_force_n,
        "small_deflection_ratio": result.small_deflection_ratio,
        "node_count": result.node_count,
        "element_count": result.element_count,
        "n_per_side": result.n_per_side,
        "element_type": result.element_type,
        "material_id": result.material_id,
        "material_reference": result.material_reference,
        "generated_at_utc": result.generated_at_utc,
        "cross_check_kind": "plate_simply_supported_shell_timoshenko",
        "runner": "plate_ss_shell_runner",
        "claim_tier": (
            "tier_2_validated" if result.verdict == "PASS"
            else "tier_1_candidate"
        ),
        "claim_boundary": (
            "tier2_real_solver_validated; not_signed_validation; "
            "cross_check_against_analytical"
            if result.verdict == "PASS"
            else "tier1_engineering_candidate; not_signed_validation; "
                 "not_benchmark_agreement"
        ),
    }
    path = case_golden_dir / VERDICT_YAML_FILENAME
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


__all__ = [
    "DEFAULT_N_PER_SIDE",
    "PlateSSShellCrossCheckResult",
    "PlateSSShellCrossCheckVerdict",
    "make_structured_quad_mesh",
    "run_plate_ss_shell_cross_check",
    "write_plate_ss_shell_verdict_yaml",
]
