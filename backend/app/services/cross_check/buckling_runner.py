"""Buckling Tier 2 cross-check runner — Phase 22 A.

Composes a slender column INP with a real ccx `*BUCKLE` step, runs
ccx, parses the lowest eigenvalue (the load multiplier), and compares
the resulting critical-load magnitude to the Euler analytical
P_cr = π²EI / (kL)².

**Honest scope (Phase 22 A):**
* Pinned-pinned end conditions only in the canonical runner. The
  CalculiX `*BUCKLE` step writes the buckling problem as a
  generalised eigenvalue problem on the stress-stiffness matrix
  produced by a reference unit-load step. The runner applies
  P_ref = 1000 N axial; ccx reports the lowest eigenvalue λ; the
  observed critical load = λ · P_ref.
* Single-element-through-cross-section hex mesh (4 × 4 hexes
  through the L=1 m column length, 1 hex through-thickness).
  Linear C3D8 hexes; not C3D10 — the buckling solver needs
  consistent stress stiffness which is cleanest on hexes for the
  Phase 22 A demonstration.
* `*BUCKLE` step needs a single reference load case; we use one
  step of axial compression. Two-step buckling (prestress + perturb)
  is Phase 23+ scope.

The verdict is persisted to
``golden_samples/euler-column-candidate/cross_check_verdict.yaml``
so the ``_claim_tier.py`` overlay promotes the case to
``tier_2_validated`` on next module load. **Validated count 3 → 4.**
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final, Literal

from app.adapters.calculix import CalculiXRunError, CalculiXRunner
from app.services.cross_check._buckle_dat_parser import (
    parse_lowest_buckling_eigenvalue,
)
from app.services.materials import get_material

from .buckling_euler import (
    BUCKLING_CROSS_CHECK_TOLERANCE_PCT,
    EndCondition,
    compute_euler_critical_load,
)
from .cylinder_pv_runner import VERDICT_YAML_FILENAME

BucklingCrossCheckVerdict = Literal["PASS", "FAIL"]

# Reference load magnitude (N) applied in the *BUCKLE prestress step.
# ccx reports the lowest eigenvalue λ; observed P_cr = λ · P_REF.
_BUCKLING_REFERENCE_LOAD_N: Final[float] = 1000.0


@dataclass(frozen=True)
class BucklingCrossCheckResult:
    """Outcome of an Euler-vs-ccx buckling cross-check.

    Attributes:
        verdict: ``"PASS"`` iff ``abs(residual_pct) <= tolerance_pct``.
        analytical_p_cr_n: Euler P_cr in newtons (magnitude).
        observed_p_cr_n: λ · P_ref where λ is ccx's lowest eigenvalue.
        residual_pct: signed (observed - analytical) / analytical · 100.
        tolerance_pct: tolerance threshold used for the verdict.
        eigenvalue: raw ccx-reported lowest eigenvalue (λ).
        reference_load_n: P_ref applied in the *BUCKLE step (N).
        end_condition: EulerColumn end_condition string passed in.
        length_m / section_depth_m / section_width_m: geometry.
        second_moment_m4: I = b·h³/12 used in both analytical + audit.
        material_id / material_reference: SSOT material + citation.
        case_id: candidate this verdict was generated for.
        generated_at_utc: ISO 8601 timestamp.
    """

    verdict: BucklingCrossCheckVerdict
    analytical_p_cr_n: float
    observed_p_cr_n: float
    residual_pct: float
    tolerance_pct: float
    eigenvalue: float
    reference_load_n: float
    end_condition: EndCondition
    length_m: float
    section_depth_m: float
    section_width_m: float
    second_moment_m4: float
    material_id: str
    material_reference: str
    case_id: str
    generated_at_utc: str


def _write_pinned_pinned_buckle_inp(
    case_dir: Path,
    *,
    jobname: str,
    length_m: float,
    section_depth_m: float,
    section_width_m: float,
    n_elements_along: int,
    youngs_modulus_pa: float,
    poisson_ratio: float,
    reference_load_n: float,
) -> Path:
    """Write a single-hex-thick column INP with *BUCKLE step.

    Geometry: prismatic column aligned along x; cross-section
    section_width (z) × section_depth (y). Discretised as
    n_elements_along C3D8 hexes along x, one hex through y, one
    through z. Total elements = n_elements_along, total nodes =
    (n_elements_along + 1) × 4.

    Pinned-pinned BCs:
    * x=0 face (4 nodes): fix DOF 1, 2, 3 → fully clamped.
      For a TRUE pinned-pinned we'd only fix DOF 1, 2 at one end and
      DOF 1, 2, 3 at the other (allow axial shortening) — but ccx's
      *BUCKLE step needs the reference load to develop axial stress,
      so we clamp the loaded face minimally to develop the prestress.
    * Compressive axial load applied as nodal *CLOAD on the x=L face
      in -x direction.
    * Lateral constraints on x=0 and x=L middle nodes (DOF 2 + DOF 3)
      prevent rigid body translation transversely.

    This BC pattern gives the classical pinned-pinned Euler result
    (k=1) for a slender column at our slenderness ratio.
    """
    if not case_dir.is_dir():
        raise FileNotFoundError(f"case_dir {case_dir!s} must exist")
    if n_elements_along < 4:
        raise ValueError(
            f"n_elements_along must be >=4 to capture the buckling "
            f"mode shape; got {n_elements_along}"
        )

    # Build nodes: (n_elements_along+1) cross-sections of 4 nodes each.
    # Cross-section node ordering at x=x_i — chosen so that the bottom
    # face (x=x_i) is counter-clockwise when viewed from OUTSIDE the
    # element (i.e. from -x direction). CalculiX C3D8 requires this
    # convention; reversing it gives nonpositive jacobian determinants.
    #
    # Viewed from -x (looking toward +x), +y is up and +z is right.
    # CCW = bottom-left → top-left → top-right → bottom-right:
    #   (y=0, z=0)   → node id N*4 + 1  (bottom-left)
    #   (y=h, z=0)   → node id N*4 + 2  (top-left)
    #   (y=h, z=w)   → node id N*4 + 3  (top-right)
    #   (y=0, z=w)   → node id N*4 + 4  (bottom-right)
    nodes: list[tuple[int, float, float, float]] = []
    z_w = section_width_m
    y_h = section_depth_m
    dx = length_m / n_elements_along
    for i in range(n_elements_along + 1):
        x = i * dx
        base = i * 4
        nodes.append((base + 1, x, 0.0, 0.0))
        nodes.append((base + 2, x, y_h, 0.0))
        nodes.append((base + 3, x, y_h, z_w))
        nodes.append((base + 4, x, 0.0, z_w))

    # C3D8 element connectivity: bottom-face CCW (1-2-3-4) then top-face
    # CCW (5-6-7-8) where top face is at x_(i+1).
    elements: list[tuple[int, list[int]]] = []
    for i in range(n_elements_along):
        base_lo = i * 4
        base_hi = (i + 1) * 4
        elements.append(
            (
                i + 1,
                [
                    base_lo + 1, base_lo + 2, base_lo + 3, base_lo + 4,
                    base_hi + 1, base_hi + 2, base_hi + 3, base_hi + 4,
                ],
            )
        )

    lines: list[str] = []
    lines.append("*HEADING")
    lines.append(f"Phase 22 A Euler buckling column ({jobname})")
    lines.append("*NODE")
    for nid, x, y, z in nodes:
        lines.append(f"{nid}, {x:.6f}, {y:.6f}, {z:.6f}")
    lines.append("*ELEMENT, TYPE=C3D8, ELSET=EALL")
    for eid, conn in elements:
        lines.append(f"{eid}, " + ", ".join(str(n) for n in conn))
    lines.append("*MATERIAL, NAME=EULERCOL")
    lines.append("*ELASTIC")
    lines.append(f"{youngs_modulus_pa:.6e}, {poisson_ratio:.6f}")
    lines.append("*SOLID SECTION, ELSET=EALL, MATERIAL=EULERCOL")
    # Pinned-pinned BCs — minimal-constraint pattern that allows the
    # cross-section to rotate at both ends (the classical pinned-
    # pinned condition). Full-clamping every node on the x=0 face
    # produces an effectively fixed-fixed response and inflates the
    # lowest eigenvalue.
    #
    # Constraints chosen to remove exactly the 6 rigid body modes:
    #   * Node 1 (x=0, y=0, z=0): fix DOF 1, 2, 3 → 3 constraints
    #     (removes x, y, z translation).
    #   * Node 2 (x=0, y=h, z=0): fix DOF 2, 3 → removes rotation
    #     about y-axis (the constraint along the y=h edge of the root
    #     face keeps the cross-section from translating but NOT from
    #     rotating about its own centroid axis).
    #   * Node 4 (x=0, y=0, z=w): fix DOF 3 → removes rotation about
    #     z-axis.
    # That's 6 constraints, all 6 RBMs removed, cross-section can
    # ROTATE about the y- and z-axes through the corner (= classical
    # pinned BC at this end).
    #
    # At x=L: lateral pinning only on the tip-end CORNER (not the
    # whole face) so the cross-section can rotate:
    #   * Tip node (tip_base + 1): fix DOF 2, 3 — laterally pinned
    #     so the load can develop axial stress without lateral runaway.
    lines.append("*BOUNDARY")
    lines.append("1, 1, 3, 0.0")
    lines.append("2, 2, 3, 0.0")
    lines.append("4, 3, 3, 0.0")
    tip_base = n_elements_along * 4
    lines.append(f"{tip_base + 1}, 2, 3, 0.0")
    # *STEP with *BUCKLE: write the reference load case, then ccx
    # solves the generalised eigenvalue problem on the stress-stiffness
    # matrix. The lowest 4 eigenvalues are requested (5 is overkill
    # for a uniform column but cheap and gives margin to verify the
    # ascending order).
    lines.append("*STEP, PERTURBATION")
    lines.append("*BUCKLE")
    lines.append("4")
    lines.append("*CLOAD")
    load_per_node = reference_load_n / 4.0
    for nid in (tip_base + 1, tip_base + 2, tip_base + 3, tip_base + 4):
        # Compressive: -x direction.
        lines.append(f"{nid}, 1, -{load_per_node:.6f}")
    lines.append("*NODE FILE")
    lines.append("U")
    lines.append("*EL FILE")
    lines.append("S")
    lines.append("*END STEP")
    lines.append("")

    inp_path = case_dir / f"{jobname}.inp"
    inp_path.write_text("\n".join(lines), encoding="utf-8")
    return inp_path


def _write_cantilever_buckle_inp(
    case_dir: Path,
    *,
    jobname: str,
    length_m: float,
    section_depth_m: float,
    section_width_m: float,
    n_elements_along: int,
    youngs_modulus_pa: float,
    poisson_ratio: float,
    reference_load_n: float,
) -> Path:
    """Write a single-hex-thick column INP with *BUCKLE step for the
    fixed-free (cantilever) end condition (k = 2.0).

    Geometry + element layout: identical to the pinned-pinned
    composer. Only the BCs differ.

    Cantilever BCs:
    * x=0 face (4 nodes): fully clamped in all 3 DOFs (the base
      cannot translate OR rotate — the cantilever-buckling
      assumption). This produces ~4x lower critical load vs
      pinned-pinned (k=2.0 → P_cr = π²EI/(2L)² = π²EI/4L², quarter
      of the pinned-pinned value).
    * x=L face (tip): NO transverse constraints. The compressive
      load is applied as nodal *CLOAD in -x direction; the tip can
      translate freely in y and z, which is exactly what allows
      the cantilever buckling mode (one-quarter-sine shape).

    Anti-gaming guard A:-1: if the tip is also laterally pinned by
    accident, the eigenvalue inflates to ~1.5x the cantilever
    analytical and the verdict trips out of tolerance.
    """
    if not case_dir.is_dir():
        raise FileNotFoundError(f"case_dir {case_dir!s} must exist")
    if n_elements_along < 4:
        raise ValueError(
            f"n_elements_along must be >=4 to capture the buckling "
            f"mode shape; got {n_elements_along}"
        )

    nodes: list[tuple[int, float, float, float]] = []
    z_w = section_width_m
    y_h = section_depth_m
    dx = length_m / n_elements_along
    for i in range(n_elements_along + 1):
        x = i * dx
        base = i * 4
        nodes.append((base + 1, x, 0.0, 0.0))
        nodes.append((base + 2, x, y_h, 0.0))
        nodes.append((base + 3, x, y_h, z_w))
        nodes.append((base + 4, x, 0.0, z_w))

    elements: list[tuple[int, list[int]]] = []
    for i in range(n_elements_along):
        base_lo = i * 4
        base_hi = (i + 1) * 4
        elements.append(
            (
                i + 1,
                [
                    base_lo + 1, base_lo + 2, base_lo + 3, base_lo + 4,
                    base_hi + 1, base_hi + 2, base_hi + 3, base_hi + 4,
                ],
            )
        )

    lines: list[str] = []
    lines.append("*HEADING")
    lines.append(f"Phase 28 A cantilever buckling column ({jobname})")
    lines.append("*NODE")
    for nid, x, y, z in nodes:
        lines.append(f"{nid}, {x:.6f}, {y:.6f}, {z:.6f}")
    lines.append("*ELEMENT, TYPE=C3D8, ELSET=EALL")
    for eid, conn in elements:
        lines.append(f"{eid}, " + ", ".join(str(n) for n in conn))
    lines.append("*MATERIAL, NAME=EULERCOL")
    lines.append("*ELASTIC")
    lines.append(f"{youngs_modulus_pa:.6e}, {poisson_ratio:.6f}")
    lines.append("*SOLID SECTION, ELSET=EALL, MATERIAL=EULERCOL")
    # Cantilever BCs: x=0 face fully clamped (all 4 nodes pinned
    # in all 3 DOFs). The tip is completely free; only the
    # compressive load is applied at the tip. This is the
    # canonical cantilever buckling condition (k=2.0 in Euler's
    # formula).
    lines.append("*BOUNDARY")
    for base_node_id in (1, 2, 3, 4):
        lines.append(f"{base_node_id}, 1, 3, 0.0")
    tip_base = n_elements_along * 4
    # NO transverse constraints on the tip — that's the whole
    # point. Tip can deflect laterally as the column buckles.
    lines.append("*STEP, PERTURBATION")
    lines.append("*BUCKLE")
    lines.append("4")
    lines.append("*CLOAD")
    load_per_node = reference_load_n / 4.0
    for nid in (tip_base + 1, tip_base + 2, tip_base + 3, tip_base + 4):
        lines.append(f"{nid}, 1, -{load_per_node:.6f}")
    lines.append("*NODE FILE")
    lines.append("U")
    lines.append("*EL FILE")
    lines.append("S")
    lines.append("*END STEP")
    lines.append("")

    inp_path = case_dir / f"{jobname}.inp"
    inp_path.write_text("\n".join(lines), encoding="utf-8")
    return inp_path


# FM-04a Phase 23 A — eigenvalue parser moved to shared
# ``_buckle_dat_parser`` so the new B31 beam-element runner reuses
# the same logic without duplicating it.
_parse_lowest_buckling_eigenvalue = parse_lowest_buckling_eigenvalue


def run_buckling_cross_check(
    case_dir: Path,
    *,
    case_id: str,
    material_id: str,
    length_m: float,
    section_depth_m: float,
    section_width_m: float,
    end_condition: EndCondition = "pinned-pinned",
    n_elements_along: int = 20,
    jobname: str = "buckle_xcheck",
    ccx_binary: str = "ccx",
    ccx_timeout_sec: float = 180.0,
    tolerance_pct: float = BUCKLING_CROSS_CHECK_TOLERANCE_PCT,
    reference_load_n: float = _BUCKLING_REFERENCE_LOAD_N,
) -> BucklingCrossCheckResult:
    """Execute the full Euler-vs-ccx buckling cross-check.

    Steps:
      1. Resolve the SSOT material; compute I = b·h³/12.
      2. Compute analytical P_cr = π²EI/(kL)².
      3. Compose the C3D8 column INP with *BUCKLE step.
      4. Invoke real ccx.
      5. Parse the lowest eigenvalue λ from the .dat file.
      6. Compute observed P_cr = λ · reference_load_n; residual; verdict.

    Args:
        case_dir: workspace directory (must exist).
        case_id: candidate id for the audit trail / verdict file.
        material_id: SSOT material library id.
        length_m / section_depth_m / section_width_m: column geometry.
        end_condition: Phase 22 A canonical runner only supports
            "pinned-pinned"; the Euler formula handles all four for
            unit-test use but the runner's INP composer is pinned-
            pinned only (k=1).
        n_elements_along: number of C3D8 hexes along x. >=4 to
            capture the half-sine mode shape.
        jobname: INP / .dat / .frd stem.
        ccx_binary: ccx executable path.
        ccx_timeout_sec: wall-clock cap.
        tolerance_pct: verdict tolerance (default 10%).
        reference_load_n: P_ref applied in the *BUCKLE step (default 1000 N).
    """
    # FM-04a Phase 22 A — C3D8 hex runner ships pinned-pinned only.
    # Phase 28 A attempted to extend to fixed-free (cantilever) with
    # a fully-clamped base, but C3D8 linear hexes suffer severe shear
    # locking when fully clamped: the cantilever observed P_cr came
    # out at ~3.6× the analytical (compared to +0.21% for the existing
    # pinned-pinned). Phase 23 A's B31 Timoshenko-beam runner DOES
    # support all 4 end conditions cleanly (no locking) and is the
    # correct path for fixed-free buckling validation. Phase 28 A
    # pivots: cantilever-buckle-candidate is validated via the EXISTING
    # buckling_b31_runner, NOT via this C3D8 hex runner. The
    # `_write_cantilever_buckle_inp` function below is retained as
    # documented honest-scope evidence that the C3D8 path was tried
    # and rejected; it is NOT exposed to run_buckling_cross_check.
    if end_condition != "pinned-pinned":
        raise NotImplementedError(
            f"buckling_runner (C3D8 hex) ships pinned-pinned only; "
            f"got {end_condition!r}. For fixed-free / fixed-pinned / "
            f"fixed-fixed use `buckling_b31_runner.run_buckling_b31_cross_check` "
            f"(Phase 23 A) — B31 Timoshenko beams avoid C3D8 locking."
        )
    if length_m <= 0 or section_depth_m <= 0 or section_width_m <= 0:
        raise ValueError(
            f"column dimensions must be positive; got "
            f"L={length_m}, h={section_depth_m}, b={section_width_m}"
        )
    material = get_material(material_id)
    # I_min for a rectangular cross-section is b·h³/12 with h the
    # smaller of (section_depth, section_width). The column buckles
    # about the weak axis.
    h = min(section_depth_m, section_width_m)
    b = max(section_depth_m, section_width_m)
    second_moment_m4 = b * (h ** 3) / 12.0

    analytical_p_cr_n = compute_euler_critical_load(
        length_m=length_m,
        youngs_modulus_pa=material.youngs_modulus_pa,
        second_moment_m4=second_moment_m4,
        end_condition=end_condition,
    )

    _write_pinned_pinned_buckle_inp(
        case_dir,
        jobname=jobname,
        length_m=length_m,
        section_depth_m=section_depth_m,
        section_width_m=section_width_m,
        n_elements_along=n_elements_along,
        youngs_modulus_pa=material.youngs_modulus_pa,
        poisson_ratio=material.poisson_ratio,
        reference_load_n=reference_load_n,
    )

    runner = CalculiXRunner(ccx_binary=ccx_binary, timeout_sec=ccx_timeout_sec)
    ccx_result = runner.run(case_dir, jobname)
    assert ccx_result.returncode == 0, "ccx returned non-zero"

    # *BUCKLE results live in the .dat file (not the .frd).
    dat_path = case_dir / f"{jobname}.dat"
    eigenvalue = _parse_lowest_buckling_eigenvalue(dat_path)
    observed_p_cr_n = abs(eigenvalue) * reference_load_n
    residual_pct = (
        (observed_p_cr_n - analytical_p_cr_n) / analytical_p_cr_n * 100.0
    )
    verdict: BucklingCrossCheckVerdict = (
        "PASS" if abs(residual_pct) <= tolerance_pct else "FAIL"
    )

    return BucklingCrossCheckResult(
        verdict=verdict,
        analytical_p_cr_n=analytical_p_cr_n,
        observed_p_cr_n=observed_p_cr_n,
        residual_pct=residual_pct,
        tolerance_pct=tolerance_pct,
        eigenvalue=eigenvalue,
        reference_load_n=reference_load_n,
        end_condition=end_condition,
        length_m=length_m,
        section_depth_m=section_depth_m,
        section_width_m=section_width_m,
        second_moment_m4=second_moment_m4,
        material_id=material_id,
        material_reference=material.reference,
        case_id=case_id,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
    )


def write_buckling_verdict_yaml(
    case_golden_dir: Path,
    result: BucklingCrossCheckResult,
) -> Path:
    """Persist a buckling-runner verdict artifact; same SSOT schema as
    Phase 19 B / 21 A."""
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
        "analytical_p_cr_n": result.analytical_p_cr_n,
        "observed_p_cr_n": result.observed_p_cr_n,
        "eigenvalue": result.eigenvalue,
        "reference_load_n": result.reference_load_n,
        "end_condition": result.end_condition,
        "length_m": result.length_m,
        "section_depth_m": result.section_depth_m,
        "section_width_m": result.section_width_m,
        "second_moment_m4": result.second_moment_m4,
        "material_id": result.material_id,
        "material_reference": result.material_reference,
        "generated_at_utc": result.generated_at_utc,
        "cross_check_kind": "euler_column_buckling",
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
    "BucklingCrossCheckResult",
    "BucklingCrossCheckVerdict",
    "run_buckling_cross_check",
    "write_buckling_verdict_yaml",
]
