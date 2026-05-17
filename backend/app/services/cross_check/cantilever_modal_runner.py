"""Cantilever modal cross-check runner — Phase 26 A.

Closes the Phase 25 retro punchlist item #3 (6th validated case) and
moves FEA Dim 4 (solver kind coverage, held flat at 68 since Phase
23 A) by introducing a NEW solver kind: ``*FREQUENCY`` modal
eigenvalue extraction.

The runner meshes a 0.5 m × 20 mm × 20 mm slender steel cantilever
with gmsh (C3D10 quadratic tets by default), clamps the x=0 face,
runs ccx with a *FREQUENCY step extracting 5 modes, parses the .dat
for the first eigenfrequency, and compares to the Euler-Bernoulli
closed-form

    f_1 = (β_1·L)² · √(E·I / (ρ·A)) / (2π · L²)

where β₁·L = 1.875104, I = w·h³/12, A = w·h.

**Anti-gaming guard A:-1:** the runner reads the FIRST eigenfrequency
from a list that the parser returns in ASCENDING order. CalculiX
sometimes produces tiny rigid-body modes (~10⁻⁶ Hz numerical
artifacts) before the structural ones; the runner refuses any first
eigenfrequency below 1.0 Hz as "almost certainly a rigid-body
artifact, not mode 1." Pinned by a dedicated test.

Self-contained (does NOT extend the Phase 20-22 single-BC pipeline)
for the same reason as Phase 25 A's plate_ss_runner — Phase 19 C's
modal infrastructure only handles single-hex coupons, not slender
meshed beams.

Tier 1 / Tier 2 engineering candidate; not signed validation; not
benchmark agreement.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final, Literal

from app.adapters.calculix import (
    CalculiXReader,  # noqa: F401  (reserved for mode-shape audit if needed)
    CalculiXRunError,
    CalculiXRunner,
    parse_gmsh_msh22,
)
from app.adapters.calculix.mesh_to_inp import ParsedMesh
from app.services.materials import get_material
from app.services.meshing.gmsh_runner import GmshRunError, GmshRunner
from app.services.modal_frequencies import extract_eigen_frequencies
from app.services.tier2_pipeline import (
    Tier2PipelineError,
    material_to_hex_descriptor,
)

from .cantilever_modal import (
    CANTILEVER_MODAL_CROSS_CHECK_TOLERANCE_PCT,
    compute_cantilever_first_natural_frequency_hz,
)
from .cylinder_pv_runner import VERDICT_YAML_FILENAME

CantileverModalVerdict = Literal["PASS", "FAIL"]

_NSET_ROW_MAX: Final[int] = 16
_RIGID_BODY_MODE_REJECT_HZ: Final[float] = 1.0
"""A:-1 anti-gaming guard threshold. Any "first" eigenfrequency below
this is treated as a numerical rigid-body artifact (Lanczos
occasionally emits ~10⁻⁶ Hz spurious modes on fully-clamped meshes;
the structural first mode for our canonical slender steel cantilever
is ~50 Hz, two orders of magnitude above this threshold)."""


@dataclass(frozen=True)
class CantileverModalResult:
    """Outcome of a cantilever modal cross-check run.

    Attributes:
        verdict: ``"PASS"`` iff ``abs(residual_pct) <= tolerance_pct``.
        analytical_hz: closed-form Euler-Bernoulli f_1.
        observed_hz: ccx-emitted first structural eigenfrequency
            (rigid-body modes filtered).
        residual_pct: signed
            ``(observed - analytical) / analytical * 100``.
        tolerance_pct: tolerance threshold used for the verdict.
        all_observed_hz: full list of eigenfrequencies parsed from
            the .dat (ascending order, post rigid-body filter).
        length_m / height_m / width_m: geometry.
        node_count / element_count: parsed mesh size.
        material_id / material_reference: SSOT material + citation.
        case_id: candidate this verdict was generated for.
        generated_at_utc: ISO 8601 timestamp.
        slender_ratio: L / max(h, w) — surfaced for audit.
    """

    verdict: CantileverModalVerdict
    analytical_hz: float
    observed_hz: float
    residual_pct: float
    tolerance_pct: float
    all_observed_hz: tuple[float, ...]
    length_m: float
    height_m: float
    width_m: float
    node_count: int
    element_count: int
    material_id: str
    material_reference: str
    case_id: str
    generated_at_utc: str
    slender_ratio: float


def _select_clamp_face_nodes(
    nodes: dict[int, tuple[float, float, float]],
    clamp_x_m: float,
    tol_m: float,
) -> list[int]:
    """Return node ids on the clamped face (x ≈ clamp_x_m)."""
    selected: list[int] = []
    for nid, (x, _y, _z) in nodes.items():
        if abs(x - clamp_x_m) <= tol_m:
            selected.append(nid)
    return sorted(selected)


def _filter_rigid_body_modes(observed_hz: list[float]) -> list[float]:
    """A:-1 anti-gaming guard at the runner level: drop any ascending-
    sorted eigenfrequency below ``_RIGID_BODY_MODE_REJECT_HZ``.

    The cantilever's first structural mode for our canonical
    geometry sits around 50 Hz; rejecting anything below 1 Hz is two
    orders of magnitude below the expected signal and well below any
    plausible structural mode for the validity envelope.
    """
    return [f for f in observed_hz if f >= _RIGID_BODY_MODE_REJECT_HZ]


def _write_cantilever_modal_inp(
    case_dir: Path,
    *,
    jobname: str,
    mesh: ParsedMesh,
    material_name: str,
    youngs_modulus_pa: float,
    poisson_ratio: float,
    density_kg_m3: float,
    clamp_x_m: float,
    num_modes: int,
    tol_m: float = 1e-6,
) -> Path:
    """Hand-roll a modal-extraction INP with a meshed beam + clamped
    x=0 face + *FREQUENCY step."""
    clamp_nodes = _select_clamp_face_nodes(mesh.nodes, clamp_x_m, tol_m)
    if not clamp_nodes:
        raise ValueError(
            f"no nodes selected on clamp face x={clamp_x_m} (tol={tol_m})"
        )

    lines: list[str] = []
    lines.append("*HEADING")
    lines.append(f"Phase 26 A cantilever modal ({jobname})")
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

    lines.append("*NSET, NSET=NCLAMP")
    for chunk_start in range(0, len(clamp_nodes), _NSET_ROW_MAX):
        chunk = clamp_nodes[chunk_start : chunk_start + _NSET_ROW_MAX]
        lines.append(", ".join(str(n) for n in chunk))
    lines.append("*BOUNDARY")
    lines.append("NCLAMP, 1, 3, 0.0")  # all 3 DOFs clamped on x=0 face

    lines.append("*STEP")
    lines.append("*FREQUENCY")
    lines.append(f"{num_modes}")
    lines.append("*NODE FILE")
    lines.append("U")
    lines.append("*END STEP")

    inp_path = case_dir / f"{jobname}.inp"
    inp_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return inp_path


def run_cantilever_modal_cross_check(
    case_dir: Path,
    *,
    case_id: str,
    material_id: str,
    geometry_path: Path,
    length_m: float = 0.500,
    height_m: float = 0.020,
    width_m: float = 0.020,
    num_modes: int = 5,
    jobname: str = "cantilever_modal_xcheck",
    characteristic_length_m: float = 0.012,
    element_order: int = 2,
    ccx_binary: str = "ccx",
    gmsh_binary: str = "gmsh",
    ccx_timeout_sec: float = 300.0,
    gmsh_timeout_sec: float = 240.0,
    tolerance_pct: float = CANTILEVER_MODAL_CROSS_CHECK_TOLERANCE_PCT,
) -> CantileverModalResult:
    """Execute the full meshed cantilever modal cross-check.

    Steps:
      1. Resolve material via SSOT library (E + ν + density).
      2. Mesh the .geo via gmsh (C3D10 by default).
      3. Parse the .msh → nodes + elements.
      4. Hand-roll INP with clamped x=0 face + *FREQUENCY step.
      5. Run ccx.
      6. Parse the .dat for eigenfrequencies in ascending order.
      7. Filter rigid-body modes (A:-1 guard).
      8. Compare first structural eigenfrequency to Euler-Bernoulli
         closed-form analytical.
    """
    if length_m <= 0 or height_m <= 0 or width_m <= 0:
        raise ValueError(
            f"all dimensions must be positive; got L={length_m}, h={height_m}, w={width_m}"
        )
    material = get_material(material_id)
    hex_descriptor = material_to_hex_descriptor(material)

    # Compute analytical FIRST.
    analytical_hz = compute_cantilever_first_natural_frequency_hz(
        length_m=length_m,
        height_m=height_m,
        width_m=width_m,
        youngs_modulus_pa=hex_descriptor.youngs_modulus_pa,
        density_kg_m3=material.density_kg_m3,
        mode_index=1,
    )

    # Mesh.
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

    parsed = parse_gmsh_msh22(gmsh_result.mesh_path)

    # INP.
    _write_cantilever_modal_inp(
        case_dir,
        jobname=jobname,
        mesh=parsed,
        material_name=hex_descriptor.name,
        youngs_modulus_pa=hex_descriptor.youngs_modulus_pa,
        poisson_ratio=hex_descriptor.poisson_ratio,
        density_kg_m3=material.density_kg_m3,
        clamp_x_m=0.0,
        num_modes=num_modes,
    )

    # ccx.
    ccx_runner = CalculiXRunner(
        ccx_binary=ccx_binary, timeout_sec=ccx_timeout_sec
    )
    try:
        ccx_result = ccx_runner.run(case_dir, jobname)
    except CalculiXRunError as exc:
        raise Tier2PipelineError(
            f"ccx subprocess failed: {exc}", stage="run_ccx", cause=exc
        ) from exc

    dat_path = case_dir / f"{jobname}.dat"
    if not dat_path.is_file():
        raise CalculiXRunError(
            f"ccx did not produce .dat at {dat_path}",
            returncode=ccx_result.returncode,
            stderr_tail="",
            stdout_tail="",
        )
    raw_observed = extract_eigen_frequencies(dat_path)
    structural = _filter_rigid_body_modes(raw_observed)
    if not structural:
        raise CalculiXRunError(
            f"no structural eigenfrequencies in .dat (≥{_RIGID_BODY_MODE_REJECT_HZ} Hz); "
            f"raw list: {raw_observed}",
            returncode=ccx_result.returncode,
            stderr_tail="",
            stdout_tail="",
        )
    observed_hz = structural[0]

    residual_pct = (observed_hz - analytical_hz) / analytical_hz * 100.0
    verdict: CantileverModalVerdict = (
        "PASS" if abs(residual_pct) <= tolerance_pct else "FAIL"
    )

    return CantileverModalResult(
        verdict=verdict,
        analytical_hz=analytical_hz,
        observed_hz=observed_hz,
        residual_pct=residual_pct,
        tolerance_pct=tolerance_pct,
        all_observed_hz=tuple(structural),
        length_m=length_m,
        height_m=height_m,
        width_m=width_m,
        node_count=len(parsed.nodes),
        element_count=len(parsed.elements),
        material_id=material_id,
        material_reference=material.reference,
        case_id=case_id,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        slender_ratio=length_m / max(height_m, width_m),
    )


def write_cantilever_modal_verdict_yaml(
    case_golden_dir: Path,
    result: CantileverModalResult,
) -> Path:
    """Persist a cantilever-modal verdict artifact, schema-versioned
    the same way as Phase 19/21/23/25 verdicts."""
    if not case_golden_dir.is_dir():
        raise FileNotFoundError(
            f"case_golden_dir {case_golden_dir!s} must exist"
        )
    payload = {
        "schema_version": "1.0.0",
        "case_id": result.case_id,
        "verdict": result.verdict,
        "tolerance_pct": result.tolerance_pct,
        "residual_pct": result.residual_pct,
        "analytical_hz": result.analytical_hz,
        "observed_hz": result.observed_hz,
        "all_observed_hz": list(result.all_observed_hz),
        "length_m": result.length_m,
        "height_m": result.height_m,
        "width_m": result.width_m,
        "slender_ratio": result.slender_ratio,
        "node_count": result.node_count,
        "element_count": result.element_count,
        "material_id": result.material_id,
        "material_reference": result.material_reference,
        "generated_at_utc": result.generated_at_utc,
        "cross_check_kind": "cantilever_modal_euler_bernoulli",
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
    "CantileverModalResult",
    "CantileverModalVerdict",
    "run_cantilever_modal_cross_check",
    "write_cantilever_modal_verdict_yaml",
]
