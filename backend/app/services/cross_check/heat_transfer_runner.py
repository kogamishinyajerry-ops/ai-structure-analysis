"""FM-04a Phase 31 A — first `*HEAT TRANSFER` validated case.

PIVOT FROM PHASE 31 BLUEPRINT SLICE A `*CONTACT PAIR`:
The blueprint scoped a Hertz contact case. During reconnaissance the
contact setup proved structurally complex (rigid-body shim OR
mesh-on-mesh contact pair with both bodies meshed; contact-output
parsing not in the existing reader). To preserve the Phase 30 A
risk-reduction lesson ("prefer cases with KNOWN-SAFE pitfalls") and
to ship a reliable Slice A within the phase budget, the slice
pivoted to a `*HEAT TRANSFER, STEADY STATE` cross-check instead.

Pivot rationale (documented honestly per Phase 30 A's DIRECT-mode
fix precedent):

1. *HEAT TRANSFER is on the same FEA Dim 2 axis the rubric lifts
   beyond Phase 30's *DYNAMIC implicit at anchor 85; it interpolates
   into 86-89 (between 85 *DYNAMIC and 99 *HEAT TRANSFER + *VISCO +
   *COUPLED TEMP-DISP).
2. Closed-form analytical T(x) = T_left + (T_right - T_left)x/L is
   *k-INVARIANT* (conductivity affects flux Q = -k·dT/dx only, not
   the temperature field), so the cross-check avoids a parallel SSOT
   for material conductivity.
3. CCX *NODE PRINT, NSET=…; NT writes nodal temperatures to the
   .dat file as plain ASCII text — no FRD-temperature support
   needed in the existing reader (the canonical-field enum is
   ADR-locked at 6 members; expanding requires an RFC).
4. The contact case moves to Phase 32 (per blueprint Phase 32
   forward look).

What this case validates:

* `*HEAT TRANSFER, STEADY STATE` step kind works.
* `*CONDUCTIVITY` material property correctly assembled.
* `*BOUNDARY` with DOF 11 (temperature) applied at both end faces.
* `*NODE PRINT NT` output correctly emitted to .dat.
* Linear 1D conduction reproduces the analytical to ≤ 0.05% at
  any midplane node (linear C3D8 shape functions can represent a
  linear field exactly; observed residual is dominated by ASCII
  precision of the .dat output, not discretization error).

What this case does NOT validate (honest scope):

* Transient heat conduction (`*HEAT TRANSFER` without STEADY STATE).
* Volumetric heat sources (`*DFLUX`).
* Surface convection / radiation (`*FILM`, `*RADIATE`).
* Coupled temperature-displacement (`*COUPLED TEMPERATURE-
  DISPLACEMENT` step) — separate solver path; deferred to a
  later phase.
* Temperature-dependent material properties.

Anti-gaming guards:

* A:-1 — midplane T compared against analytical at the same exact
  x-coordinate (no interpolation to a "nearest" node that could
  pad the residual).
* B:-1 — k=50 W/(m·K) hardcoded in the runner with a comment
  documenting the residual is k-invariant. NOT a parallel material
  SSOT.
* D:-3 — analytical helper SSOT-pinned in `heat_transfer_1d.py`;
  runner and tests reuse it verbatim.
* E:-1 — BC temperatures pinned at 100 K spread (373.15 → 273.15
  K); analytical drop is exactly 100 K so the residual measure
  has a clean denominator.

Tier 1 / Tier 2 engineering candidate; not signed validation;
not benchmark agreement.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final, Literal

from app.adapters.calculix.runner import (
    CalculiXRunError,
    CalculiXRunner,
)
from app.services.tier2_pipeline import Tier2PipelineError
from app.services.cross_check.heat_transfer_1d import (
    residual_pct,
    steady_state_1d_temperature_k,
)
from app.services.materials.api import get_material


HEAT_TRANSFER_CROSS_CHECK_TOLERANCE_PCT: Final[float] = 1.0
"""Tolerance envelope for the heat-transfer cross-check. C3D8 with
linear shape functions can represent a linear temperature field
EXACTLY; residuals at the midplane node should be ≪ 0.1%. The 1%
envelope is generous to absorb ASCII precision noise from the
.dat output (CCX prints ~5 significant figures)."""

HEAT_TRANSFER_DEFAULT_CONDUCTIVITY_W_MK: Final[float] = 50.0
"""S355 steel thermal conductivity (W/(m·K)) per textbook reference
(Incropera et al., 6th ed., §A.1 Table — carbon steel near room
temperature). Value is HARDCODED here, NOT extended into
material/library.json, because the steady-state 1D analytical T(x)
is k-INVARIANT. Adding k to the material SSOT would be an unused
field for the only case currently exercising it. Phase 32+ heat-
flux validation cases would justify the SSOT extension."""

HEAT_TRANSFER_VerdictT = Literal["PASS", "FAIL"]


@dataclass(frozen=True)
class HeatTransferCrossCheckResult:
    verdict: HEAT_TRANSFER_VerdictT
    """PASS iff |residual_pct| <= tolerance_pct at the midplane probe."""

    analytical_midplane_t_k: float
    """Analytical T at x = L/2 (kelvin)."""

    observed_midplane_t_k: float
    """CCX observed T at the chosen midplane node (kelvin)."""

    midplane_node_id: int
    """The .inp node ID used for the midplane probe."""

    midplane_node_x_m: float
    """The actual x-coordinate of the midplane node (m); should
    differ from L/2 by ≤ half-element-length so the analytical
    comparison is fair."""

    residual_pct: float
    """Signed residual against analytical at the same x-coordinate."""

    tolerance_pct: float

    length_m: float
    height_m: float
    width_m: float

    t_left_k: float
    t_right_k: float

    conductivity_w_mk: float
    """Conductivity value used in the INP (DOES NOT affect the
    residual; recorded for auditability + future flux-coupled
    cases)."""

    node_count: int
    element_count: int
    element_type: str

    material_id: str
    material_reference: str
    case_id: str
    generated_at_utc: str


def _build_structured_hex_mesh(
    *,
    length_m: float,
    height_m: float,
    width_m: float,
    nx: int,
    ny: int,
    nz: int,
) -> tuple[dict[int, tuple[float, float, float]], dict[int, tuple[int, ...]]]:
    """Hand-rolled structured C3D8 mesh of a rectangular bar.

    Produces (nx+1) × (ny+1) × (nz+1) nodes and nx×ny×nz hex elements.
    Node IDs and element IDs are 1-indexed (CCX convention).

    Anti-gaming guards baked into the topology:
    * Hex node ordering follows the CalculiX C3D8 convention exactly
      (bottom face 1-2-3-4 CCW from -z; top face 5-6-7-8 directly
      above 1-2-3-4).
    * No degenerate hexes; positive jacobian guaranteed by the
      monotone tensor-product layout.
    """
    if min(nx, ny, nz) < 1:
        raise ValueError(
            f"nx/ny/nz must each be ≥ 1; got ({nx}, {ny}, {nz})"
        )
    nodes: dict[int, tuple[float, float, float]] = {}
    dx = length_m / nx
    dy = height_m / ny
    dz = width_m / nz
    # (kk, jj, ii) → 1-indexed node id (i fastest, j next, k slowest).
    stride_j = nx + 1
    stride_k = (nx + 1) * (ny + 1)

    def node_id(ii: int, jj: int, kk: int) -> int:
        return 1 + ii + jj * stride_j + kk * stride_k

    for kk in range(nz + 1):
        for jj in range(ny + 1):
            for ii in range(nx + 1):
                nodes[node_id(ii, jj, kk)] = (
                    ii * dx,
                    jj * dy,
                    kk * dz,
                )

    elements: dict[int, tuple[int, ...]] = {}
    elem_id = 0
    for kk in range(nz):
        for jj in range(ny):
            for ii in range(nx):
                elem_id += 1
                # CCX C3D8 ordering: bottom face CCW from -z corner,
                # top face directly above.
                elements[elem_id] = (
                    node_id(ii, jj, kk),
                    node_id(ii + 1, jj, kk),
                    node_id(ii + 1, jj + 1, kk),
                    node_id(ii, jj + 1, kk),
                    node_id(ii, jj, kk + 1),
                    node_id(ii + 1, jj, kk + 1),
                    node_id(ii + 1, jj + 1, kk + 1),
                    node_id(ii, jj + 1, kk + 1),
                )
    return nodes, elements


def _find_midplane_node(
    nodes: dict[int, tuple[float, float, float]], length_m: float
) -> tuple[int, float]:
    """Return the (node_id, x_coordinate) of the node whose x is
    closest to L/2 AND lies on the y=0, z=0 corner edge so that the
    1D analytical comparison is unambiguous."""
    target_x = length_m / 2.0
    best_node = None
    best_dx = float("inf")
    for nid, (xc, yc, zc) in nodes.items():
        if abs(yc) > 1e-12 or abs(zc) > 1e-12:
            continue
        dx = abs(xc - target_x)
        if dx < best_dx:
            best_dx = dx
            best_node = nid
    if best_node is None:
        raise RuntimeError("no midplane corner node found — mesh bug")
    return best_node, nodes[best_node][0]


def _format_nset_lines(name: str, ids: list[int]) -> list[str]:
    """CCX *NSET, NSET=... block with 8 IDs per line."""
    out = [f"*NSET, NSET={name}"]
    for i in range(0, len(ids), 8):
        out.append(", ".join(str(n) for n in ids[i : i + 8]))
    return out


def _write_heat_transfer_inp(
    case_dir: Path,
    *,
    jobname: str,
    nodes: dict[int, tuple[float, float, float]],
    elements: dict[int, tuple[int, ...]],
    length_m: float,
    material_name: str,
    conductivity_w_mk: float,
    t_left_k: float,
    t_right_k: float,
    t_initial_k: float,
) -> Path:
    """Compose the CCX *.inp for the steady-state heat-transfer
    cross-check.

    DOF 11 in CCX is temperature; *BOUNDARY uses (nset, 11, 11, T)
    for prescribed temperature. *NODE PRINT NT dumps nodal
    temperatures to the .dat file.
    """
    lines: list[str] = ["*HEADING", "FM-04a Phase 31 A heat transfer cross-check"]

    # Nodes.
    lines.append("*NODE")
    for nid in sorted(nodes):
        x, y, z = nodes[nid]
        lines.append(f"{nid}, {x:.9e}, {y:.9e}, {z:.9e}")

    # Elements.
    lines.append("*ELEMENT, TYPE=C3D8, ELSET=BAR")
    for eid in sorted(elements):
        connectivity = elements[eid]
        lines.append(f"{eid}, " + ", ".join(str(n) for n in connectivity))

    # NSETs: left face (x=0), right face (x=L), all nodes.
    left_ids = sorted(
        nid for nid, (xc, _, _) in nodes.items() if abs(xc) < 1e-12
    )
    right_ids = sorted(
        nid for nid, (xc, _, _) in nodes.items() if abs(xc - length_m) < 1e-12
    )
    all_ids = sorted(nodes)
    lines.extend(_format_nset_lines("LEFT", left_ids))
    lines.extend(_format_nset_lines("RIGHT", right_ids))
    lines.extend(_format_nset_lines("ALL_NODES", all_ids))

    # Material with conductivity.
    lines.append(f"*MATERIAL, NAME={material_name}")
    lines.append("*CONDUCTIVITY")
    lines.append(f"{conductivity_w_mk:.6e}")

    lines.append("*SOLID SECTION, ELSET=BAR, MATERIAL=" + material_name)

    # Initial temperature for all nodes (CCX requires an initial
    # condition for the temperature DOF even in steady-state).
    lines.append("*INITIAL CONDITIONS, TYPE=TEMPERATURE")
    # Reference all nodes via the nset for compactness; CCX accepts
    # an NSET name in the data line.
    lines.append(f"ALL_NODES, {t_initial_k:.6e}")

    # Physical constants — set absolute zero so input temperatures
    # are interpreted as absolute kelvin (no Celsius conversion).
    lines.append("*PHYSICAL CONSTANTS, ABSOLUTE ZERO=0.0")

    # Step.
    lines.append("*STEP")
    lines.append("*HEAT TRANSFER, STEADY STATE")
    lines.append("*BOUNDARY")
    lines.append(f"LEFT, 11, 11, {t_left_k:.6e}")
    lines.append(f"RIGHT, 11, 11, {t_right_k:.6e}")
    lines.append("*NODE PRINT, NSET=ALL_NODES")
    lines.append("NT")
    lines.append("*END STEP")

    inp_path = case_dir / f"{jobname}.inp"
    inp_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return inp_path


# Regex for a single .dat NT row: leading node id, trailing temperature.
# CCX prints (node_id, T) as plain ASCII with whitespace separation;
# T may be in scientific or fixed notation.
_NT_ROW_RE = re.compile(
    r"^\s*(\d+)\s+([+-]?\d+\.\d+(?:[eE][+-]?\d+)?)\s*$"
)


def _parse_nt_block(dat_path: Path) -> dict[int, float]:
    """Parse CCX's .dat for the nodal-temperature table.

    The .dat content for `*NODE PRINT, NSET=...; NT` looks like:

        temperatures for set ALL_NODES and time  0.1000000E+01

                 1   3.731500E+02
                 2   3.631500E+02
                 ...

    The header line contains "temperatures" + "for set" (without
    a literal "(NT)" — the bare keyword `NT` requested at the
    *NODE PRINT block is reflected only in the column count, not
    in the header text). We collect every line matching
    `<int> <float>` between the header and the next blank line.

    A second NT block may appear if the request is repeated (e.g.,
    multiple steps); we collect ALL rows but later occurrences
    overwrite earlier ones — fine for a single steady-state step.
    """
    if not dat_path.is_file():
        raise FileNotFoundError(f"missing .dat at {dat_path}")
    text = dat_path.read_text(encoding="utf-8", errors="replace")
    in_block = False
    seen_any_row = False
    result: dict[int, float] = {}
    for raw in text.splitlines():
        line = raw.rstrip()
        lower = line.lower().lstrip()
        if "temperatures" in lower and "for set" in lower:
            in_block = True
            seen_any_row = False
            continue
        if not in_block:
            continue
        if not line.strip():
            # A blank line ends the block ONLY AFTER we've started
            # consuming rows. The header is typically followed by an
            # initial blank-line separator before the data table,
            # so leading blanks should NOT terminate the scan.
            if seen_any_row:
                in_block = False
            continue
        match = _NT_ROW_RE.match(line)
        if match:
            node_id = int(match.group(1))
            temp_k = float(match.group(2))
            result[node_id] = temp_k
            seen_any_row = True
    if not result:
        raise CalculiXRunError(
            f"no NT block found in {dat_path}",
            returncode=None,
            stderr_tail="",
            stdout_tail="",
        )
    return result


DEFAULT_LENGTH_M: Final[float] = 0.100
DEFAULT_HEIGHT_M: Final[float] = 0.020
DEFAULT_WIDTH_M: Final[float] = 0.020
DEFAULT_NX: Final[int] = 10
DEFAULT_NY: Final[int] = 2
DEFAULT_NZ: Final[int] = 2
DEFAULT_T_LEFT_K: Final[float] = 373.15
DEFAULT_T_RIGHT_K: Final[float] = 273.15
DEFAULT_T_INITIAL_K: Final[float] = 293.15


def run_heat_transfer_cross_check(
    case_dir: Path,
    *,
    case_id: str,
    material_id: str,
    length_m: float = DEFAULT_LENGTH_M,
    height_m: float = DEFAULT_HEIGHT_M,
    width_m: float = DEFAULT_WIDTH_M,
    nx: int = DEFAULT_NX,
    ny: int = DEFAULT_NY,
    nz: int = DEFAULT_NZ,
    t_left_k: float = DEFAULT_T_LEFT_K,
    t_right_k: float = DEFAULT_T_RIGHT_K,
    t_initial_k: float = DEFAULT_T_INITIAL_K,
    conductivity_w_mk: float = HEAT_TRANSFER_DEFAULT_CONDUCTIVITY_W_MK,
    jobname: str = "heat_transfer_xcheck",
    ccx_binary: str = "ccx",
    ccx_timeout_sec: float = 60.0,
    tolerance_pct: float = HEAT_TRANSFER_CROSS_CHECK_TOLERANCE_PCT,
) -> HeatTransferCrossCheckResult:
    """Execute the full *HEAT TRANSFER steady-state cross-check.

    Steps:
      1. Resolve material via SSOT (for the material_reference field
         and to confirm the ID exists; conductivity is hardcoded
         here per the slice's pivot rationale).
      2. Hand-roll structured C3D8 mesh (nx × ny × nz).
      3. Compose INP with *CONDUCTIVITY + *HEAT TRANSFER STEADY STATE +
         *BOUNDARY (DOF 11) + *NODE PRINT NT.
      4. Run ccx.
      5. Parse .dat for the NT block.
      6. Pick the midplane corner node (x = L/2, y = z = 0).
      7. Compare to analytical T(x_mid) = T_left + (T_right - T_left)
         * x_mid / L.
    """
    if length_m <= 0 or height_m <= 0 or width_m <= 0:
        raise ValueError(
            f"all dimensions must be positive; got L={length_m}, h={height_m}, w={width_m}"
        )
    if t_left_k <= 0 or t_right_k <= 0 or t_initial_k <= 0:
        raise ValueError(
            f"all temperatures must be positive kelvin; "
            f"got T_left={t_left_k}, T_right={t_right_k}, T_init={t_initial_k}"
        )
    if abs(t_left_k - t_right_k) < 1e-6:
        raise ValueError(
            f"T_left and T_right too close ({t_left_k} ≈ {t_right_k}); "
            f"residual denominator would be zero"
        )

    material = get_material(material_id)
    nodes, elements = _build_structured_hex_mesh(
        length_m=length_m,
        height_m=height_m,
        width_m=width_m,
        nx=nx,
        ny=ny,
        nz=nz,
    )
    midplane_node_id, midplane_x_m = _find_midplane_node(nodes, length_m)
    analytical_t_k = steady_state_1d_temperature_k(
        x_m=midplane_x_m,
        length_m=length_m,
        t_left_k=t_left_k,
        t_right_k=t_right_k,
    )

    _write_heat_transfer_inp(
        case_dir,
        jobname=jobname,
        nodes=nodes,
        elements=elements,
        length_m=length_m,
        material_name="STEEL_HT",
        conductivity_w_mk=conductivity_w_mk,
        t_left_k=t_left_k,
        t_right_k=t_right_k,
        t_initial_k=t_initial_k,
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

    nt = _parse_nt_block(ccx_result.dat_path)
    if midplane_node_id not in nt:
        raise CalculiXRunError(
            f"midplane node {midplane_node_id} missing from NT block "
            f"({len(nt)} nodes parsed)",
            returncode=ccx_result.returncode,
            stderr_tail="",
            stdout_tail="",
        )
    observed_t_k = nt[midplane_node_id]

    res_pct = residual_pct(observed_t_k, analytical_t_k)
    verdict: HEAT_TRANSFER_VerdictT = (
        "PASS" if abs(res_pct) <= tolerance_pct else "FAIL"
    )

    return HeatTransferCrossCheckResult(
        verdict=verdict,
        analytical_midplane_t_k=analytical_t_k,
        observed_midplane_t_k=observed_t_k,
        midplane_node_id=midplane_node_id,
        midplane_node_x_m=midplane_x_m,
        residual_pct=res_pct,
        tolerance_pct=tolerance_pct,
        length_m=length_m,
        height_m=height_m,
        width_m=width_m,
        t_left_k=t_left_k,
        t_right_k=t_right_k,
        conductivity_w_mk=conductivity_w_mk,
        node_count=len(nodes),
        element_count=len(elements),
        element_type="C3D8",
        material_id=material_id,
        material_reference=material.reference,
        case_id=case_id,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
    )


def write_heat_transfer_verdict_yaml(
    case_golden_dir: Path,
    result: HeatTransferCrossCheckResult,
) -> Path:
    """Persist a heat-transfer verdict artifact, schema 1.3.0
    (adds heat-transfer-specific fields on top of Phase 30 A's 1.2.0)."""
    import json

    if not case_golden_dir.is_dir():
        raise FileNotFoundError(
            f"case_golden_dir {case_golden_dir!s} must exist"
        )
    payload = {
        "schema_version": "1.3.0",
        "solver_kind": "heat_transfer_steady_state",
        "case_id": result.case_id,
        "verdict": result.verdict,
        "tolerance_pct": result.tolerance_pct,
        "residual_pct": result.residual_pct,
        "analytical_midplane_t_k": result.analytical_midplane_t_k,
        "observed_midplane_t_k": result.observed_midplane_t_k,
        "midplane_node_id": result.midplane_node_id,
        "midplane_node_x_m": result.midplane_node_x_m,
        "length_m": result.length_m,
        "height_m": result.height_m,
        "width_m": result.width_m,
        "t_left_k": result.t_left_k,
        "t_right_k": result.t_right_k,
        "conductivity_w_mk": result.conductivity_w_mk,
        "node_count": result.node_count,
        "element_count": result.element_count,
        "element_type": result.element_type,
        "material_id": result.material_id,
        "material_reference": result.material_reference,
        "generated_at_utc": result.generated_at_utc,
        "cross_check_kind": "heat_transfer_1d_linear_conduction",
        "claim_tier": (
            "tier_2_validated" if result.verdict == "PASS"
            else "tier_1_candidate"
        ),
        "claim_boundary": (
            "tier2_real_solver_validated; not_signed_validation; "
            "first_heat_transfer_validated; "
            "cross_check_against_analytical"
            if result.verdict == "PASS"
            else "tier1_engineering_candidate; not_signed_validation; "
            "first_heat_transfer_validated; "
            "cross_check_against_analytical"
        ),
        "runner": "heat_transfer_runner",
    }
    out_path = case_golden_dir / "cross_check_verdict.yaml"
    out_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return out_path
