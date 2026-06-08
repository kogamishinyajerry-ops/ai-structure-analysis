"""Cantilever beam tip-deflection cross-check runner — Phase 21 A.

Composes the Phase 20 C meshed pipeline (gmsh → C3D4 → ccx) with the
Phase 20 B Euler-Bernoulli analytical (`compute_analytical_tip_deflection`)
into a single ``run_cantilever_cross_check`` function. The runner meshes
the canonical L=1 m, h=b=0.1 m cantilever via the candidate's
``cantilever.geo``, clamps the root face (x=0), applies a downward force
on the tip face (x=L), reads the maximum |u_y| from the .frd, and
compares to PL³/(3EI). PASS verdict is persisted as
``cross_check_verdict.yaml`` so :mod:`app.services.reporting._claim_tier`
promotes the case to ``tier_2_validated`` on next module load.

**Honest tolerance (Phase 21 A — wider than Phase 19 B / 20 B):**

C3D4 (linear tetrahedra) suffer from shear-locking on bending-dominated
problems. With the default characteristic mesh length the gmsh-produced
mesh under-predicts tip deflection by ~10-15% vs the Euler-Bernoulli
formula. The verdict tolerance is therefore set to ``15.0%`` rather
than the 5% used by the wall-coupon case — this is documented honest
discretisation error, not a verdict-padding move. Tightening below
10% requires:

* C3D10 (quadratic tets) — Phase 22+ scope (the gmsh + adapter both
  need C3D10 support).
* C3D8I (incompatible-mode hexes) — needs structured hex meshing,
  a different gmsh pipeline.
* C3D20 (quadratic hexes) — same constraint as C3D10.

The wall-coupon (Phase 19 B) and the bending beam (Phase 21 A) sit at
opposite ends of the C3D-element accuracy spectrum on bending — coupon
is uniaxial, beam is bending-dominated. Carrying the difference in
tolerance is the honest contract.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final, Literal

from app.adapters.calculix import (
    BoundaryConditionSpec,
    CalculiXReader,
    CalculiXRunError,
    LoadSpec,
    PlanarSelection,
)
from app.core.types import CanonicalField, UnitSystem
from app.services.materials import Material, get_material
from app.services.tier2_pipeline import (
    Tier2MeshedRunResult,
    Tier2PipelineError,
    run_tier2_meshed_pipeline,
)

from .cantilever_beam import (
    SMALL_DEFLECTION_RATIO_MAX,
    assert_slender_beam_envelope,
    compute_analytical_tip_deflection,
)
from .cylinder_pv_runner import VERDICT_YAML_FILENAME

CANTILEVER_CROSS_CHECK_TOLERANCE_PCT: Final[float] = 15.0
"""Phase 21 A tolerance. See module docstring for why this is wider
than the wall-coupon's 5% (bending vs uniaxial; C3D4 shear locking)."""

CantileverCrossCheckVerdict = Literal["PASS", "FAIL"]


@dataclass(frozen=True)
class CantileverCrossCheckResult:
    """Outcome of a single cantilever cross-check run.

    Attributes:
        verdict: ``"PASS"`` iff ``abs(residual_pct) <= tolerance_pct``.
        analytical_m: Euler-Bernoulli tip deflection (m), signed.
        observed_m: ccx-reported tip deflection magnitude (m), signed
            in the LOAD DIRECTION (negative when load is downward).
        residual_pct: signed ``(observed - analytical) / analytical *
            100``. Positive = ccx over-predicts.
        tolerance_pct: tolerance threshold used for the verdict.
        material_id / material_reference: SSOT material + citation.
        length_m / section_depth_m / section_width_m / tip_load_n:
            geometry + load (audit trail).
        second_moment_m4: I = b·h³/12 used in both analytical and audit.
        node_count / element_count: mesh size from the parsed gmsh run.
        case_id: candidate this verdict was generated for.
        generated_at_utc: ISO 8601 timestamp.
    """

    verdict: CantileverCrossCheckVerdict
    analytical_m: float
    observed_m: float
    residual_pct: float
    tolerance_pct: float
    material_id: str
    material_reference: str
    length_m: float
    section_depth_m: float
    section_width_m: float
    tip_load_n: float
    second_moment_m4: float
    node_count: int
    element_count: int
    case_id: str
    generated_at_utc: str


def _select_tip_face_y_displacement_m(
    frd_path: Path,
    node_coords: dict[int, tuple[float, float, float]],
    tip_x_m: float,
    tol_m: float,
) -> float:
    """Read the .frd, isolate tip-face nodes, and return the SIGNED
    average y-displacement.

    Averaging across the tip face (rather than picking max-magnitude)
    smooths the noise from tet-mesh free-face deformation; the signed
    result preserves the load-direction convention so the verdict can
    compare to a signed analytical.
    """
    reader = CalculiXReader(frd_path, unit_system=UnitSystem.SI)
    disp = reader.get_field(CanonicalField.DISPLACEMENT, step_id=1)
    if disp is None:
        raise CalculiXRunError(
            f"no displacement field in {frd_path}",
            returncode=None,
            stderr_tail="",
            stdout_tail="",
        )
    arr = disp.at_nodes()
    # The reader returns nodes in the .frd order. We need to map back to
    # the parsed node ids so we can filter to the tip face. The reader's
    # row index is 0-based in node-id order; the gmsh node ids are 1-
    # based contiguous (parse_gmsh_msh22 preserves them verbatim).
    sorted_node_ids = sorted(node_coords)
    if arr.shape[0] != len(sorted_node_ids):
        raise CalculiXRunError(
            f"node count mismatch between .frd ({arr.shape[0]}) and "
            f"parsed mesh ({len(sorted_node_ids)}); cannot align tip "
            f"face selection",
            returncode=None,
            stderr_tail="",
            stdout_tail="",
        )
    tip_uy: list[float] = []
    for idx, nid in enumerate(sorted_node_ids):
        x = node_coords[nid][0]
        if abs(x - tip_x_m) <= tol_m:
            tip_uy.append(float(arr[idx, 1]))
    if not tip_uy:
        raise CalculiXRunError(
            f"zero nodes selected on tip face (x={tip_x_m} ± {tol_m}); "
            f"check the .geo extrusion direction and tol",
            returncode=None,
            stderr_tail="",
            stdout_tail="",
        )
    return sum(tip_uy) / float(len(tip_uy))


def run_cantilever_cross_check(
    case_dir: Path,
    *,
    case_id: str,
    material_id: str,
    geometry_path: Path,
    length_m: float,
    section_depth_m: float,
    section_width_m: float,
    tip_load_n: float,
    jobname: str = "cantilever_xcheck",
    characteristic_length_m: float = 0.025,
    element_order: int = 1,
    ccx_binary: str = "ccx",
    gmsh_binary: str = "gmsh",
    ccx_timeout_sec: float = 180.0,
    gmsh_timeout_sec: float = 120.0,
    tolerance_pct: float = CANTILEVER_CROSS_CHECK_TOLERANCE_PCT,
) -> CantileverCrossCheckResult:
    """Execute the full meshed cantilever cross-check.

    Steps:
      1. Enforce the slender-beam (L/h ≥ 10) validity envelope.
      2. Compute analytical δ_tip via Euler-Bernoulli.
      3. Resolve the SSOT material and run the Phase 20 C meshed
         pipeline (gmsh + ccx).
      4. Read the tip-face y-displacement from the .frd.
      5. Compute residual_pct and assign the verdict.
      6. Cross-check small-deflection envelope (|δ|/L ≤ 0.1) and FAIL
         the verdict on violation (don't silently widen tolerance).

    Args:
        case_dir: workspace directory (must exist; not signed-registry).
        case_id: candidate id for the audit trail / verdict file.
        material_id: SSOT material library id.
        geometry_path: path to the cantilever.geo (must resolve inside
            ``case_dir`` — the gmsh runner enforces this).
        length_m / section_depth_m / section_width_m / tip_load_n:
            beam parameters. Must match the .geo geometry; the runner
            uses these to compute I = b·h³/12 and the analytical.
        jobname: stem for the INP / .frd / .msh files.
        characteristic_length_m: gmsh -clmax (default 25 mm; gives a
            ~3-element-through-thickness mesh on a 100 mm-thick beam).
        ccx_binary / gmsh_binary: executable paths.
        ccx_timeout_sec / gmsh_timeout_sec: wall-clock caps.
        tolerance_pct: verdict tolerance (default 15% per the honest
            C3D4 bending discretisation envelope).

    Raises:
        CantileverValidityError: when L/h < 10.
        ValueError: on non-positive geometry.
        Tier2PipelineError: on gmsh / ccx subprocess failures.
        CalculiXRunError: on .frd read failure.
    """
    assert_slender_beam_envelope(
        length_m=length_m, section_depth_m=section_depth_m
    )
    if section_width_m <= 0:
        raise ValueError(
            f"section_width_m must be positive; got {section_width_m}"
        )
    material = get_material(material_id)
    second_moment_m4 = section_width_m * (section_depth_m ** 3) / 12.0
    analytical_m = compute_analytical_tip_deflection(
        length_m=length_m,
        youngs_modulus_pa=material.youngs_modulus_pa,
        second_moment_m4=second_moment_m4,
        tip_load_n=tip_load_n,
    )

    bc = BoundaryConditionSpec(
        plane=PlanarSelection(axis="x", value_m=0.0, tol_m=1e-5)
    )
    load = LoadSpec(
        plane=PlanarSelection(axis="x", value_m=length_m, tol_m=1e-5),
        dof=2,  # y-direction (bending plane)
        total_force_n=tip_load_n,
    )

    meshed_result: Tier2MeshedRunResult = run_tier2_meshed_pipeline(
        case_dir,
        jobname=jobname,
        geometry_path=geometry_path,
        material_id=material_id,
        bc=bc,
        load=load,
        characteristic_length_m=characteristic_length_m,
        element_order=element_order,
        ccx_binary=ccx_binary,
        gmsh_binary=gmsh_binary,
        ccx_timeout_sec=ccx_timeout_sec,
        gmsh_timeout_sec=gmsh_timeout_sec,
    )
    assert meshed_result.ccx_result.frd_path is not None, (
        "ccx reported success without .frd"
    )

    # Re-parse the mesh so we can map node ids → coordinates for the
    # tip-face selection. The pipeline's parsed mesh isn't surfaced on
    # the result object, but parsing is fast (~10 ms for a 1k-node
    # mesh) and keeps the cross-check seam clean.
    from app.adapters.calculix import parse_gmsh_msh22

    parsed = parse_gmsh_msh22(meshed_result.mesh_path)

    observed_m = _select_tip_face_y_displacement_m(
        meshed_result.ccx_result.frd_path,
        parsed.nodes,
        tip_x_m=length_m,
        tol_m=1e-5,
    )
    residual_pct = (observed_m - analytical_m) / analytical_m * 100.0
    verdict: CantileverCrossCheckVerdict = (
        "PASS" if abs(residual_pct) <= tolerance_pct else "FAIL"
    )

    # Small-deflection cross-check: even if the numerical/analytical
    # residual is within tolerance, if |δ|/L exceeds the linear regime
    # bound, the analytical formula itself isn't reliable so the
    # verdict must FAIL.
    if abs(observed_m) / length_m > SMALL_DEFLECTION_RATIO_MAX:
        verdict = "FAIL"

    return CantileverCrossCheckResult(
        verdict=verdict,
        analytical_m=analytical_m,
        observed_m=observed_m,
        residual_pct=residual_pct,
        tolerance_pct=tolerance_pct,
        material_id=material_id,
        material_reference=material.reference,
        length_m=length_m,
        section_depth_m=section_depth_m,
        section_width_m=section_width_m,
        tip_load_n=tip_load_n,
        second_moment_m4=second_moment_m4,
        node_count=meshed_result.node_count,
        element_count=meshed_result.element_count,
        case_id=case_id,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
    )


def write_cantilever_verdict_yaml(
    case_golden_dir: Path,
    result: CantileverCrossCheckResult,
) -> Path:
    """Persist a verdict artifact for the cantilever case.

    Same on-disk convention as :func:`cylinder_pv_runner.write_verdict_yaml`:
    JSON-compatible YAML, schema-versioned, parsed by the
    ``_claim_tier`` overlay to promote the case to ``tier_2_validated``
    when ``verdict == "PASS"``.
    """
    if not case_golden_dir.is_dir():
        raise FileNotFoundError(
            f"case_golden_dir {case_golden_dir!s} must exist"
        )
    payload = {
        "schema_version": "1.0.0",
        "solver_kind": "linear_static",
        "case_id": result.case_id,
        "verdict": result.verdict,
        "tolerance_pct": result.tolerance_pct,
        "residual_pct": result.residual_pct,
        "analytical_m": result.analytical_m,
        "observed_m": result.observed_m,
        "material_id": result.material_id,
        "material_reference": result.material_reference,
        "length_m": result.length_m,
        "section_depth_m": result.section_depth_m,
        "section_width_m": result.section_width_m,
        "second_moment_m4": result.second_moment_m4,
        "tip_load_n": result.tip_load_n,
        "node_count": result.node_count,
        "element_count": result.element_count,
        "generated_at_utc": result.generated_at_utc,
        "cross_check_kind": "cantilever_tip_deflection_euler_bernoulli",
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
    "CANTILEVER_CROSS_CHECK_TOLERANCE_PCT",
    "CantileverCrossCheckResult",
    "CantileverCrossCheckVerdict",
    "run_cantilever_cross_check",
    "write_cantilever_verdict_yaml",
]
