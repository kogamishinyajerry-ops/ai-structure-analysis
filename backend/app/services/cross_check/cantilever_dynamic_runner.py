"""Cantilever free-vibration *DYNAMIC cross-check runner — Phase 30 A.

The FIRST validated case to use CalculiX `*DYNAMIC` (transient
implicit time integration). Closes the FEA Dim 6 ballistic-readiness
floor (50/100 since the project's inception) — every prior case used
`*STATIC` / `*BUCKLE` / `*FREQUENCY` only.

The test: pluck the cantilever, release, and verify the observed
period matches the Euler-Bernoulli analytical T_1 = 1/f_1. Same
geometry + analytical as Phase 26 A's `cantilever-beam-modal-
candidate` — only the SOLVER PATH is new (time-domain integration
vs eigenvalue extraction).

CalculiX `*DYNAMIC` implements Hilber-Hughes-Taylor implicit
integration. With ALPHA=0 it reduces to Newmark trapezoidal — no
numerical damping. The natural period should reproduce exactly
(within mesh-discretization + time-step truncation error).

Load shape: half-sine impulse at the tip-face nodes (200 N peak,
1 ms duration via `*AMPLITUDE`). After the impulse ends, the beam
oscillates freely with mode-1 dominance.

Period extraction (anti-gaming guard A:-1): zero-crossing detection
on the tip y-displacement time-history, NOT max-amplitude tracking
(which could pad the verdict via numerical-noise bias). Observed
period = mean spacing between successive zero crossings × 2.

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
    CalculiXRunError,
    CalculiXRunner,
    parse_gmsh_msh22,
)
from app.adapters.calculix.mesh_to_inp import ParsedMesh
from app.parsers.frd_parser import FRDParser
from app.services.materials import get_material
from app.services.meshing.gmsh_runner import GmshRunError, GmshRunner
from app.services.tier2_pipeline import (
    Tier2PipelineError,
    material_to_hex_descriptor,
)

from .cantilever_modal import (
    compute_cantilever_first_natural_frequency_hz,
)
from .cylinder_pv_runner import VERDICT_YAML_FILENAME

CantileverDynamicCrossCheckVerdict = Literal["PASS", "FAIL"]

_NSET_ROW_MAX: Final[int] = 16

# Time-integration defaults. dt_initial = 1e-4 s gives ~150 steps
# per period at f_1 ≈ 66.84 Hz (T_1 ≈ 14.96 ms); E:-1 guard
# ensures dt << T_analytical / 20.
DEFAULT_DT_INITIAL_S: Final[float] = 1.0e-4
DEFAULT_T_TOTAL_S: Final[float] = 0.060  # ≈ 4 periods
DEFAULT_IMPULSE_PEAK_N: Final[float] = 200.0
DEFAULT_IMPULSE_DURATION_S: Final[float] = 0.001

# Verdict envelope for the period-match test. Phase 26 A's *FREQUENCY
# case showed +0.13% residual; time-domain integration adds
# discretization error (~1-3%). 8% gives ~3× safety vs honest 3%
# baseline.
CANTILEVER_DYNAMIC_CROSS_CHECK_TOLERANCE_PCT: Final[float] = 8.0


@dataclass(frozen=True)
class CantileverDynamicCrossCheckResult:
    """Outcome of the cantilever free-vibration *DYNAMIC cross-check."""

    verdict: CantileverDynamicCrossCheckVerdict
    analytical_period_s: float
    observed_period_s: float
    analytical_f1_hz: float
    residual_pct: float
    tolerance_pct: float
    length_m: float
    height_m: float
    width_m: float
    youngs_modulus_pa: float
    density_kg_m3: float
    dt_initial_s: float
    t_total_s: float
    impulse_peak_n: float
    impulse_duration_s: float
    n_zero_crossings: int
    n_increments: int
    node_count: int
    element_count: int
    material_id: str
    material_reference: str
    case_id: str
    generated_at_utc: str


def _select_clamp_face_nodes(
    nodes: dict[int, tuple[float, float, float]],
    clamp_x_m: float,
    tol_m: float,
) -> list[int]:
    return sorted(
        nid for nid, (x, _y, _z) in nodes.items()
        if abs(x - clamp_x_m) <= tol_m
    )


def _select_tip_face_nodes(
    nodes: dict[int, tuple[float, float, float]],
    tip_x_m: float,
    tol_m: float,
) -> list[int]:
    return sorted(
        nid for nid, (x, _y, _z) in nodes.items()
        if abs(x - tip_x_m) <= tol_m
    )


def _find_tip_centerline_node(
    nodes: dict[int, tuple[float, float, float]],
    tip_x_m: float,
    height_m: float,
    width_m: float,
    tol_m: float,
) -> int:
    """Pick the node closest to (L, h/2, w/2) on the tip face.
    A:-1 audit-trail: midpoint of the tip face is the cleanest
    location for u_y(t) sampling (least cross-section contamination)."""
    target_y = height_m / 2.0
    target_z = width_m / 2.0
    best_nid = -1
    best_d2 = math.inf
    for nid, (x, y, z) in nodes.items():
        if abs(x - tip_x_m) > tol_m:
            continue
        d2 = (y - target_y) ** 2 + (z - target_z) ** 2
        if d2 < best_d2:
            best_d2 = d2
            best_nid = nid
    if best_nid < 0:
        raise ValueError(
            f"no tip-face nodes found at x={tip_x_m} (tol={tol_m})"
        )
    return best_nid


def _write_cantilever_dynamic_inp(
    case_dir: Path,
    *,
    jobname: str,
    mesh: ParsedMesh,
    material_name: str,
    youngs_modulus_pa: float,
    poisson_ratio: float,
    density_kg_m3: float,
    clamp_x_m: float,
    tip_x_m: float,
    dt_initial_s: float,
    t_total_s: float,
    impulse_peak_n: float,
    impulse_duration_s: float,
    tol_m: float = 1e-6,
) -> Path:
    """Compose the *DYNAMIC INP for a clamped-free cantilever twang-
    test. Returns (inp_path, tip_centerline_node_id)."""
    clamp_nodes = _select_clamp_face_nodes(mesh.nodes, clamp_x_m, tol_m)
    if not clamp_nodes:
        raise ValueError(
            f"no nodes selected on clamp face x={clamp_x_m} (tol={tol_m})"
        )
    tip_nodes = _select_tip_face_nodes(mesh.nodes, tip_x_m, tol_m)
    if not tip_nodes:
        raise ValueError(f"no nodes on tip face x={tip_x_m}")

    lines: list[str] = []
    lines.append("*HEADING")
    lines.append(f"Phase 30 A cantilever dynamic ({jobname})")
    lines.append("*NODE")
    for nid, (x, y, z) in mesh.nodes.items():
        lines.append(f"{nid}, {x:.6f}, {y:.6f}, {z:.6f}")

    by_type: dict[str, list[tuple[int, list[int]]]] = {}
    for elem_id, ccx_type, node_ids in mesh.elements:
        by_type.setdefault(ccx_type, []).append((elem_id, node_ids))
    for ccx_type, rows in by_type.items():
        lines.append(f"*ELEMENT, TYPE={ccx_type}, ELSET=EALL_{ccx_type}")
        for elem_id, node_ids in rows:
            lines.append(f"{elem_id}, " + ", ".join(str(n) for n in node_ids))

    lines.append(f"*MATERIAL, NAME={material_name}")
    lines.append("*ELASTIC")
    lines.append(f"{youngs_modulus_pa:.6e}, {poisson_ratio:.6f}")
    lines.append("*DENSITY")
    lines.append(f"{density_kg_m3:.6f}")
    for ccx_type in by_type:
        lines.append(
            f"*SOLID SECTION, ELSET=EALL_{ccx_type}, MATERIAL={material_name}"
        )

    # Clamp + tip nset
    lines.append("*NSET, NSET=NCLAMP")
    for chunk_start in range(0, len(clamp_nodes), _NSET_ROW_MAX):
        chunk = clamp_nodes[chunk_start : chunk_start + _NSET_ROW_MAX]
        lines.append(", ".join(str(n) for n in chunk))
    lines.append("*NSET, NSET=NTIP")
    for chunk_start in range(0, len(tip_nodes), _NSET_ROW_MAX):
        chunk = tip_nodes[chunk_start : chunk_start + _NSET_ROW_MAX]
        lines.append(", ".join(str(n) for n in chunk))

    lines.append("*BOUNDARY")
    lines.append("NCLAMP, 1, 3, 0.0")  # all 3 DOFs clamped on x=0 face

    # Half-sine impulse amplitude.
    # Pin the curve through (0, 0), (tau/2, 1), (tau, 0), (t_total, 0).
    tau = impulse_duration_s
    lines.append("*AMPLITUDE, NAME=IMPULSE")
    lines.append(f"0.0, 0.0, {tau/2:.6e}, 1.0, {tau:.6e}, 0.0, {t_total_s:.6e}, 0.0")

    lines.append("*STEP, INC=20000")
    # ALPHA=0 → Newmark trapezoidal (no numerical damping).
    # DIRECT forces CCX to honor the requested time step instead of
    # adaptively scaling up (which produced ~4 samples per period at
    # first attempt, way under-sampled for zero-crossing analysis).
    lines.append("*DYNAMIC, ALPHA=0, DIRECT")
    # dt, t_total
    lines.append(f"{dt_initial_s:.6e}, {t_total_s:.6e}")
    # Apply the impulse load to all tip-face nodes (force per node
    # = peak / len(tip_nodes); aggregate = impulse_peak_n).
    force_per_node = impulse_peak_n / len(tip_nodes)
    lines.append("*CLOAD, AMPLITUDE=IMPULSE")
    lines.append(f"NTIP, 2, {force_per_node:.6e}")  # DOF 2 = y
    # Output u_y at tip face nodes at every step.
    lines.append("*NODE FILE, NSET=NTIP, FREQUENCY=1")
    lines.append("U")
    lines.append("*END STEP")

    inp_path = case_dir / f"{jobname}.inp"
    inp_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return inp_path


def extract_zero_crossings(
    times_s: list[float], values: list[float]
) -> list[float]:
    """Return time stamps of zero crossings (linear interpolation
    between adjacent samples). A zero crossing occurs whenever the
    sign of `values` changes between consecutive samples.

    Anti-gaming guard A:-1 — the period is later computed from the
    SPACING of these crossings, not from peak detection. Numerical
    noise near the peaks cannot pad the verdict."""
    if len(times_s) != len(values):
        raise ValueError(
            f"times_s ({len(times_s)}) and values ({len(values)}) "
            f"must be the same length"
        )
    crossings: list[float] = []
    for i in range(len(values) - 1):
        v0 = values[i]
        v1 = values[i + 1]
        if v0 == 0.0 and v1 != 0.0:
            crossings.append(times_s[i])
            continue
        if v0 * v1 < 0.0:
            # Linear interpolation: t* = t0 + (t1 - t0) * (-v0) / (v1 - v0)
            t0 = times_s[i]
            t1 = times_s[i + 1]
            t_cross = t0 + (t1 - t0) * (-v0) / (v1 - v0)
            crossings.append(t_cross)
    return crossings


def compute_observed_period_s(zero_crossings_s: list[float]) -> float:
    """Compute the observed period from a list of zero-crossing times.

    Period = 2 × mean spacing between consecutive crossings (each
    crossing = half a cycle). The first crossing is dropped to avoid
    transient contamination from the impulse-load phase.

    Raises ValueError if fewer than 3 crossings are available."""
    if len(zero_crossings_s) < 3:
        raise ValueError(
            f"need >= 3 zero crossings to compute period; got "
            f"{len(zero_crossings_s)}"
        )
    # Drop the first crossing (transient from impulse).
    cleaned = zero_crossings_s[1:]
    spacings = [cleaned[i + 1] - cleaned[i] for i in range(len(cleaned) - 1)]
    mean_spacing = sum(spacings) / len(spacings)
    return 2.0 * mean_spacing


def run_cantilever_dynamic_cross_check(
    case_dir: Path,
    *,
    case_id: str,
    material_id: str,
    geometry_path: Path,
    length_m: float = 0.500,
    height_m: float = 0.020,
    width_m: float = 0.020,
    characteristic_length_m: float = 0.012,
    element_order: int = 2,
    dt_initial_s: float = DEFAULT_DT_INITIAL_S,
    t_total_s: float = DEFAULT_T_TOTAL_S,
    impulse_peak_n: float = DEFAULT_IMPULSE_PEAK_N,
    impulse_duration_s: float = DEFAULT_IMPULSE_DURATION_S,
    jobname: str = "cantilever_dynamic_xcheck",
    ccx_binary: str = "ccx",
    gmsh_binary: str = "gmsh",
    ccx_timeout_sec: float = 300.0,
    gmsh_timeout_sec: float = 240.0,
    tolerance_pct: float = CANTILEVER_DYNAMIC_CROSS_CHECK_TOLERANCE_PCT,
) -> CantileverDynamicCrossCheckResult:
    """Execute the full cantilever free-vibration *DYNAMIC cross-check.

    Steps:
      1. Resolve material from SSOT library.
      2. Compute analytical f_1 via Phase 26 A's helper.
      3. Mesh the .geo with gmsh (C3D10 quadratic tets by default).
      4. Hand-roll INP with clamped x=0 face + *DYNAMIC step +
         half-sine tip impulse.
      5. Run ccx.
      6. Parse FRD time-history; extract tip-centerline u_y(t).
      7. Detect zero crossings; compute observed period.
      8. Compare to T_analytical = 1/f_1.
    """
    if length_m <= 0:
        raise ValueError(f"length_m must be positive; got {length_m}")
    if height_m <= 0:
        raise ValueError(f"height_m must be positive; got {height_m}")
    if width_m <= 0:
        raise ValueError(f"width_m must be positive; got {width_m}")
    if dt_initial_s <= 0:
        raise ValueError(f"dt_initial_s must be positive; got {dt_initial_s}")
    if t_total_s <= 0:
        raise ValueError(f"t_total_s must be positive; got {t_total_s}")
    if impulse_duration_s <= 0:
        raise ValueError(
            f"impulse_duration_s must be positive; got {impulse_duration_s}"
        )

    material = get_material(material_id)
    hex_descriptor = material_to_hex_descriptor(material)

    analytical_f1 = compute_cantilever_first_natural_frequency_hz(
        length_m=length_m,
        height_m=height_m,
        width_m=width_m,
        youngs_modulus_pa=hex_descriptor.youngs_modulus_pa,
        density_kg_m3=material.density_kg_m3,
        mode_index=1,
    )
    analytical_period = 1.0 / analytical_f1

    # E:-1 time-step Courant guard: dt must be << T_analytical / 20
    courant_limit = analytical_period / 20.0
    if dt_initial_s > courant_limit:
        raise ValueError(
            f"dt_initial_s={dt_initial_s:.3e} exceeds Courant limit "
            f"{courant_limit:.3e} (T_analytical / 20). Reduce dt or "
            f"refine the analytical baseline."
        )

    # Mesh via gmsh.
    gmsh_runner = GmshRunner(
        gmsh_binary=gmsh_binary, timeout_sec=gmsh_timeout_sec
    )
    try:
        gmsh_result = gmsh_runner.run(
            case_dir,
            geometry_path,
            output_name=jobname,
            characteristic_length_m=characteristic_length_m,
            element_order=element_order,
            output_format="msh22",
        )
    except GmshRunError as exc:
        raise Tier2PipelineError(
            f"gmsh subprocess failed: {exc}", stage="run_gmsh", cause=exc
        ) from exc

    parsed_mesh = parse_gmsh_msh22(gmsh_result.mesh_path)

    # Find the tip-centerline node before composing INP (used later
    # for time-history extraction).
    tip_centerline_node = _find_tip_centerline_node(
        parsed_mesh.nodes,
        tip_x_m=length_m,
        height_m=height_m,
        width_m=width_m,
        tol_m=1e-6,
    )

    inp_path = _write_cantilever_dynamic_inp(
        case_dir,
        jobname=jobname,
        mesh=parsed_mesh,
        material_name=hex_descriptor.name,
        youngs_modulus_pa=hex_descriptor.youngs_modulus_pa,
        poisson_ratio=hex_descriptor.poisson_ratio,
        density_kg_m3=material.density_kg_m3,
        clamp_x_m=0.0,
        tip_x_m=length_m,
        dt_initial_s=dt_initial_s,
        t_total_s=t_total_s,
        impulse_peak_n=impulse_peak_n,
        impulse_duration_s=impulse_duration_s,
    )
    _ = inp_path

    # Run ccx.
    ccx_runner = CalculiXRunner(
        ccx_binary=ccx_binary, timeout_sec=ccx_timeout_sec
    )
    try:
        ccx_result = ccx_runner.run(case_dir, jobname)
    except CalculiXRunError as exc:
        raise Tier2PipelineError(
            f"ccx subprocess failed: {exc}", stage="run_ccx", cause=exc
        ) from exc
    assert ccx_result.frd_path is not None, "ccx success without .frd"

    # Parse FRD multi-increment data via the legacy parser.
    frd_parser = FRDParser()
    parsed_frd = frd_parser.parse(str(ccx_result.frd_path))
    if not parsed_frd.success:
        raise CalculiXRunError(
            f"frd parse failed: {parsed_frd.error_message}",
            returncode=None,
            stderr_tail="",
            stdout_tail="",
        )
    increments = parsed_frd.increments
    if not increments:
        raise CalculiXRunError(
            "no increments parsed from FRD — *DYNAMIC step did not "
            "write time-history output",
            returncode=None,
            stderr_tail="",
            stdout_tail="",
        )

    # Build time-history: (t, u_y) at the tip-centerline node.
    times: list[float] = []
    u_y_values: list[float] = []
    for inc in increments:
        if tip_centerline_node not in inc.displacements:
            continue
        times.append(float(inc.value))
        # FRDIncrement.displacements[nid] = (u_x, u_y, u_z)
        u_y_values.append(float(inc.displacements[tip_centerline_node][1]))

    if len(times) < 10:
        raise CalculiXRunError(
            f"only {len(times)} time-history samples at tip — "
            f"insufficient for zero-crossing analysis",
            returncode=None,
            stderr_tail="",
            stdout_tail="",
        )

    # Subtract DC offset (the impulse can leave a small static bias
    # depending on the rise/fall asymmetry). Zero-crossing analysis
    # operates on the AC-component only.
    dc_offset = sum(u_y_values) / len(u_y_values)
    u_y_ac = [v - dc_offset for v in u_y_values]

    zero_crossings = extract_zero_crossings(times, u_y_ac)
    observed_period = compute_observed_period_s(zero_crossings)

    residual_pct = (
        (observed_period - analytical_period) / analytical_period * 100.0
    )

    verdict: CantileverDynamicCrossCheckVerdict
    if abs(residual_pct) <= tolerance_pct:
        verdict = "PASS"
    else:
        verdict = "FAIL"

    return CantileverDynamicCrossCheckResult(
        verdict=verdict,
        analytical_period_s=analytical_period,
        observed_period_s=observed_period,
        analytical_f1_hz=analytical_f1,
        residual_pct=residual_pct,
        tolerance_pct=tolerance_pct,
        length_m=length_m,
        height_m=height_m,
        width_m=width_m,
        youngs_modulus_pa=hex_descriptor.youngs_modulus_pa,
        density_kg_m3=material.density_kg_m3,
        dt_initial_s=dt_initial_s,
        t_total_s=t_total_s,
        impulse_peak_n=impulse_peak_n,
        impulse_duration_s=impulse_duration_s,
        n_zero_crossings=len(zero_crossings),
        n_increments=len(increments),
        node_count=len(parsed_mesh.nodes),
        element_count=len(parsed_mesh.elements),
        material_id=material_id,
        material_reference=material.reference,
        case_id=case_id,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
    )


def write_cantilever_dynamic_verdict_yaml(
    case_golden_dir: Path,
    result: CantileverDynamicCrossCheckResult,
) -> Path:
    """Persist the verdict artifact (schema 1.2.0 — adds
    `observed_period_s` + `analytical_period_s` + `solver_kind=dynamic`
    over the 1.1.0 baseline)."""
    if not case_golden_dir.is_dir():
        raise FileNotFoundError(
            f"case_golden_dir {case_golden_dir!s} must exist"
        )
    payload = {
        "schema_version": "1.2.0",
        "case_id": result.case_id,
        "verdict": result.verdict,
        "tolerance_pct": result.tolerance_pct,
        "residual_pct": result.residual_pct,
        "analytical_period_s": result.analytical_period_s,
        "observed_period_s": result.observed_period_s,
        "analytical_f1_hz": result.analytical_f1_hz,
        "length_m": result.length_m,
        "height_m": result.height_m,
        "width_m": result.width_m,
        "youngs_modulus_pa": result.youngs_modulus_pa,
        "density_kg_m3": result.density_kg_m3,
        "dt_initial_s": result.dt_initial_s,
        "t_total_s": result.t_total_s,
        "impulse_peak_n": result.impulse_peak_n,
        "impulse_duration_s": result.impulse_duration_s,
        "n_zero_crossings": result.n_zero_crossings,
        "n_increments": result.n_increments,
        "node_count": result.node_count,
        "element_count": result.element_count,
        "material_id": result.material_id,
        "material_reference": result.material_reference,
        "generated_at_utc": result.generated_at_utc,
        "cross_check_kind": "cantilever_free_vibration_dynamic",
        "solver_kind": "dynamic",
        "runner": "cantilever_dynamic_runner",
        "claim_tier": (
            "tier_2_validated" if result.verdict == "PASS"
            else "tier_1_candidate"
        ),
        "claim_boundary": (
            "tier2_real_solver_validated; not_signed_validation; "
            "cross_check_against_analytical; first_dynamic_validated"
            if result.verdict == "PASS"
            else "tier1_engineering_candidate; not_signed_validation; "
                 "not_benchmark_agreement"
        ),
    }
    path = case_golden_dir / VERDICT_YAML_FILENAME
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


__all__ = [
    "CANTILEVER_DYNAMIC_CROSS_CHECK_TOLERANCE_PCT",
    "CantileverDynamicCrossCheckResult",
    "CantileverDynamicCrossCheckVerdict",
    "DEFAULT_DT_INITIAL_S",
    "DEFAULT_IMPULSE_DURATION_S",
    "DEFAULT_IMPULSE_PEAK_N",
    "DEFAULT_T_TOTAL_S",
    "compute_observed_period_s",
    "extract_zero_crossings",
    "run_cantilever_dynamic_cross_check",
    "write_cantilever_dynamic_verdict_yaml",
]
