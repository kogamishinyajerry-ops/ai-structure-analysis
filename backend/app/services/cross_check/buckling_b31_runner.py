"""B31 Timoshenko beam-element buckling Tier 2 cross-check runner — Phase 23 A.

Phase 22 A shipped a C3D8 solid-element buckling runner whose
eigenvalue landed ~10× the Euler-Bernoulli analytical on the canonical
1 m × 10×10 mm steel-S355 column (37,360 N solid vs 1,727 N Euler).
The root cause was the idealization gap: a 1-hex-per-cross-section
solid-element column under fully-clamped end nodes overconstraints
relative to the pinned-pinned 1D-beam analytical, and the buckling
mode shape can't capture properly on a 4-hex-across-length mesh.

Phase 23 A ships a B31 beam-element runner that DOES match the 1D
analytical. CalculiX's B31 is a 2-node Timoshenko beam element; the
`*BEAM SECTION` keyword carries the cross-section properties (A,
I_xx, I_yy). The buckling problem reduces to the same 1D eigenvalue
problem Euler solved analytically, so the runner observed P_cr should
match P_Euler within the tolerance.

**Honest scope (Phase 23 A):**
* Pinned-pinned end conditions only (same as Phase 22 A canonical).
  k=1, so P_cr = π² · E · I_min / L².
* Rectangular cross-section only. Composer accepts depth + width,
  computes A = depth·width and I_min = depth·width³/12 (assuming
  width ≤ depth so the buckling axis is the y axis with the smaller
  moment of inertia).
* Single-step `*STEP, PERTURBATION` + `*BUCKLE 4` — same shape as
  Phase 22 A. Reference axial load 1000 N; observed P_cr = λ · 1000.
* N elements along the column length (default 20); B31 needs at
  least ~10 elements to capture the half-sine mode shape, which is
  cheap on 1D elements.
* Boundary conditions: pinned both ends. Node 1 fixed DOF 1-3 +
  rotation about the beam axis (DOF 4). Node N+1 fixed DOF 2-3 +
  rotation DOF 4 (free to translate axially so the axial load can
  apply). Both ends free to rotate about the buckling axes 5/6 →
  pinned-pinned per Euler.

Tier 1 / Tier 2 engineering candidate; not signed validation; not
benchmark agreement.
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
from app.services.cross_check.buckling_euler import (
    BUCKLING_CROSS_CHECK_TOLERANCE_PCT,
    EULER_K_FACTOR,
    compute_euler_critical_load,
)
from app.services.materials import get_material


EndCondition = Literal[
    "pinned-pinned", "fixed-fixed", "fixed-pinned", "fixed-free"
]


@dataclass(frozen=True)
class BucklingB31RunResult:
    """End-to-end result of a B31 buckling cross-check."""

    case_id: str
    case_dir: Path
    inp_path: Path
    ccx_returncode: int
    ccx_stdout_tail: str
    p_ref_n: float
    eigenvalue: float
    observed_p_cr_n: float
    analytical_p_cr_n: float
    residual_pct: float
    tolerance_pct: float
    verdict: Literal["PASS", "FAIL"]
    verdict_path: Path


# Canonical Phase 22 / 23 column geometry.
_CANONICAL_LENGTH_M: Final[float] = 1.0
_CANONICAL_DEPTH_M: Final[float] = 0.010
_CANONICAL_WIDTH_M: Final[float] = 0.010
_DEFAULT_P_REF_N: Final[float] = 1000.0
_DEFAULT_N_ELEMENTS: Final[int] = 20


def _compose_b31_buckling_inp(
    case_dir: Path,
    *,
    jobname: str,
    length_m: float,
    section_depth_m: float,
    section_width_m: float,
    youngs_modulus_pa: float,
    poisson_ratio: float,
    end_condition: EndCondition,
    p_ref_n: float,
    n_elements: int,
) -> Path:
    """Write the procedural ccx INP for a B31 beam-element buckling run.

    The mesh is a chain of N B31 elements along the column length
    (x-axis). Node N+1 nodes are generated at evenly-spaced x
    positions. The `*BEAM SECTION` block carries A, I_xx, I_yy plus
    the orientation vector (the n1 direction defining the local
    section axis).
    """
    if n_elements < 4:
        raise ValueError(
            f"n_elements must be ≥ 4 to capture the buckling mode shape "
            f"(got {n_elements})"
        )

    # Cross-section properties for a solid rectangle:
    # A = b·h, I_xx = b·h³/12, I_yy = h·b³/12.
    # b = section_width_m, h = section_depth_m.
    # Whichever is smaller dictates the buckling axis.
    area_m2 = section_depth_m * section_width_m
    i_xx = section_width_m * section_depth_m**3 / 12.0
    i_yy = section_depth_m * section_width_m**3 / 12.0
    i_min = min(i_xx, i_yy)
    _ = i_min  # documented; ccx picks the lower I automatically from the section block

    dx = length_m / n_elements

    lines: list[str] = []
    lines.append(
        f"** FM-04a Phase 23 A — B31 Timoshenko beam buckling INP "
        f"for {jobname}"
    )
    lines.append(
        f"** L = {length_m:.6f} m, b×h = {section_width_m:.6f} × "
        f"{section_depth_m:.6f} m, n_elements = {n_elements}"
    )
    lines.append("*HEADING")
    lines.append(f"Buckling B31 cross-check · {jobname}")

    # Nodes — N+1 along the x axis.
    lines.append("*NODE, NSET=NALL")
    for i in range(n_elements + 1):
        x = i * dx
        lines.append(f"{i + 1}, {x:.9e}, 0.0, 0.0")

    # B31 elements — pairs of consecutive nodes.
    lines.append("*ELEMENT, TYPE=B31, ELSET=EALL")
    for i in range(n_elements):
        lines.append(f"{i + 1}, {i + 1}, {i + 2}")

    # Material block — same SSOT as the C3D8 runner.
    lines.append("*MATERIAL, NAME=MAT")
    lines.append("*ELASTIC")
    lines.append(f"{youngs_modulus_pa:.9e}, {poisson_ratio:.6f}")

    # *BEAM SECTION — section is a RECT b×h; orientation defines
    # the local n1 axis (y axis in global coords here).
    lines.append("*BEAM SECTION, ELSET=EALL, MATERIAL=MAT, SECTION=RECT")
    # Format: width-along-n1, height-along-n2
    lines.append(f"{section_width_m:.9e}, {section_depth_m:.9e}")
    # Section orientation: local n1 axis = global y (0, 1, 0)
    lines.append("0.0, 1.0, 0.0")

    # Boundary conditions.
    # End node 1 (x=0): pinned — fixes translations DOF 1-3 + rotation DOF 4
    # (about the beam axis to suppress torsion). Free to rotate DOF 5,6.
    # End node N+1 (x=L): pinned — fixes DOF 2-3 + rotation DOF 4. Free
    # to translate axially (DOF 1) so the axial load can apply.
    if end_condition == "pinned-pinned":
        lines.append("*BOUNDARY")
        lines.append("1, 1, 4")  # DOF 1, 2, 3, 4 fixed
        lines.append(f"{n_elements + 1}, 2, 4")  # DOF 2, 3, 4 fixed
    elif end_condition == "fixed-fixed":
        lines.append("*BOUNDARY")
        lines.append("1, 1, 6")  # all 6 DOFs fixed
        lines.append(f"{n_elements + 1}, 2, 6")  # all but axial fixed
    elif end_condition == "fixed-pinned":
        lines.append("*BOUNDARY")
        lines.append("1, 1, 6")  # all 6 DOFs fixed (fixed end)
        lines.append(f"{n_elements + 1}, 2, 4")  # pinned end
    elif end_condition == "fixed-free":
        lines.append("*BOUNDARY")
        lines.append("1, 1, 6")  # all 6 DOFs fixed (fixed end)
        # free end has no BC
    else:
        raise ValueError(f"unknown end_condition: {end_condition}")

    # Step: PERTURBATION + BUCKLE + axial compressive load at x=L.
    lines.append("*STEP, PERTURBATION")
    lines.append("*BUCKLE")
    lines.append("4")
    lines.append("*CLOAD")
    # Axial compression: -p_ref along x at the free / pinned end.
    lines.append(f"{n_elements + 1}, 1, {-p_ref_n:.9e}")
    lines.append("*NODE PRINT, NSET=NALL")
    lines.append("U")
    lines.append("*EL PRINT, ELSET=EALL")
    lines.append("S")
    lines.append("*END STEP")
    lines.append("")

    inp_path = case_dir / f"{jobname}.inp"
    inp_path.write_text("\n".join(lines), encoding="utf-8")
    return inp_path


def run_buckling_b31_cross_check(
    case_dir: Path,
    *,
    case_id: str,
    material_id: str,
    length_m: float = _CANONICAL_LENGTH_M,
    section_depth_m: float = _CANONICAL_DEPTH_M,
    section_width_m: float = _CANONICAL_WIDTH_M,
    end_condition: EndCondition = "pinned-pinned",
    p_ref_n: float = _DEFAULT_P_REF_N,
    n_elements: int = _DEFAULT_N_ELEMENTS,
    persist_verdict: bool = True,
    tolerance_pct: float = BUCKLING_CROSS_CHECK_TOLERANCE_PCT,
) -> BucklingB31RunResult:
    """Run the B31 beam-element buckling cross-check end-to-end."""
    case_dir = Path(case_dir)
    case_dir.mkdir(parents=True, exist_ok=True)

    material = get_material(material_id)
    youngs_modulus_pa = material.youngs_modulus_pa
    poisson_ratio = material.poisson_ratio

    # Compute the analytical Euler critical load.
    i_min = min(
        section_width_m * section_depth_m**3 / 12.0,
        section_depth_m * section_width_m**3 / 12.0,
    )
    analytical = compute_euler_critical_load(
        length_m=length_m,
        youngs_modulus_pa=youngs_modulus_pa,
        second_moment_m4=i_min,
        end_condition=end_condition,
    )

    # Compose the INP.
    jobname = f"{case_id}_b31"
    inp_path = _compose_b31_buckling_inp(
        case_dir,
        jobname=jobname,
        length_m=length_m,
        section_depth_m=section_depth_m,
        section_width_m=section_width_m,
        youngs_modulus_pa=youngs_modulus_pa,
        poisson_ratio=poisson_ratio,
        end_condition=end_condition,
        p_ref_n=p_ref_n,
        n_elements=n_elements,
    )

    # Run ccx.
    runner = CalculiXRunner()
    result = runner.run(case_dir, jobname)

    # Parse the lowest eigenvalue.
    dat_path = case_dir / f"{jobname}.dat"
    eigenvalue = parse_lowest_buckling_eigenvalue(dat_path)
    observed_p_cr_n = abs(eigenvalue * p_ref_n)

    # Residual + verdict.
    residual_pct = (observed_p_cr_n - analytical) / analytical * 100.0
    verdict: Literal["PASS", "FAIL"] = (
        "PASS" if abs(residual_pct) <= tolerance_pct else "FAIL"
    )

    verdict_path = case_dir / "cross_check_verdict.yaml"
    if persist_verdict:
        verdict_payload = {
            "case_id": case_id,
            "claim_tier": "tier_2_validated" if verdict == "PASS" else "tier_1_candidate",
            "verdict": verdict,
            "runner": "buckling_b31_runner",
            "material_id": material_id,
            "length_m": length_m,
            "section_depth_m": section_depth_m,
            "section_width_m": section_width_m,
            "end_condition": end_condition,
            "k_factor": EULER_K_FACTOR[end_condition],
            "p_ref_n": p_ref_n,
            "n_elements": n_elements,
            "eigenvalue": eigenvalue,
            "observed_p_cr_n": observed_p_cr_n,
            "analytical_p_cr_n": analytical,
            "residual_pct": residual_pct,
            "tolerance_pct": tolerance_pct,
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "claim_boundary": (
                "Tier 1 engineering candidate; not signed validation; "
                "not benchmark agreement"
                if verdict != "PASS"
                else "tier2_real_solver_validated; not_signed_validation; "
                "cross_check_against_analytical"
            ),
        }
        verdict_path.write_text(
            json.dumps(verdict_payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    try:
        stdout_text = result.stdout_path.read_text(encoding="utf-8", errors="replace")
    except (OSError, FileNotFoundError):
        stdout_text = ""
    stdout_tail = stdout_text[-2048:]
    return BucklingB31RunResult(
        case_id=case_id,
        case_dir=case_dir,
        inp_path=inp_path,
        ccx_returncode=result.returncode,
        ccx_stdout_tail=stdout_tail,
        p_ref_n=p_ref_n,
        eigenvalue=eigenvalue,
        observed_p_cr_n=observed_p_cr_n,
        analytical_p_cr_n=analytical,
        residual_pct=residual_pct,
        tolerance_pct=tolerance_pct,
        verdict=verdict,
        verdict_path=verdict_path,
    )


__all__ = [
    "BucklingB31RunResult",
    "EndCondition",
    "run_buckling_b31_cross_check",
]
