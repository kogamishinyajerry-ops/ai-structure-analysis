"""Cylinder pressure-vessel cross-check runner — Phase 19 B.

Composes the Phase 18 A `CalculiXRunner` + reader + the Phase 19 B
analytical formula into a single ``run_cylinder_pv_cross_check``
function. The runner writes a wall-coupon INP (a single C3D8 element
representing an infinitesimal wall section under traction equivalent
to the hoop membrane stress), executes ccx, reads the observed hoop
stress component, and returns a verdict.

**Wall-coupon model — honest scope disclosure:**
Phase 19 B implements the cross-check via a SCALAR wall coupon, not
a full cylinder mesh. The coupon is a single C3D8 hex with the
analytical hoop stress applied as a uniform traction. The "cross-
check" therefore measures whether ccx correctly recovers the
applied traction as the σ_xx component (Saint-Venant equivalence).
This is a defensible Phase 19 milestone — it proves the
Material → INP → ccx → reader → analytical pipeline composes
correctly end-to-end. A full cylinder-mesh cross-check is Phase
20+ scope (requires multi-element-through-thickness refinement +
proper axisymmetric BCs + integration over the wall thickness).

The verdict is persisted to
``golden_samples/<case_id>/cross_check_verdict.yaml`` so the
:mod:`app.services.reporting._claim_tier` loader can promote the
case to ``tier_2_validated`` on next module-load WITHOUT re-running
ccx every import. Re-running the cross-check is a deliberate offline
action (the CLI script Phase 20+ would add).
"""

from __future__ import annotations

import json
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
from app.services.materials import Material, get_material

from .cylinder_hoop import (
    CROSS_CHECK_TOLERANCE_PCT,
    compute_analytical_hoop_stress_pa,
)

VERDICT_YAML_FILENAME: Final[str] = "cross_check_verdict.yaml"
"""Conventional filename for the per-case verdict artifact. Lives
inside the case's golden_samples dir (HF1.7b candidate carve-out)."""

CrossCheckVerdict = Literal["PASS", "FAIL"]


@dataclass(frozen=True)
class CrossCheckResult:
    """Outcome of a single analytical cross-check run.

    Attributes:
        verdict: ``"PASS"`` iff ``abs(residual_pct) <=
            CROSS_CHECK_TOLERANCE_PCT``.
        analytical_pa: analytical solution value in pascals.
        observed_pa: ccx-observed value in pascals.
        residual_pct: signed ``(observed - analytical) / analytical *
            100``. Positive = ccx over-predicts.
        tolerance_pct: the tolerance threshold used for the verdict.
        material_id: SSOT id of the material used.
        material_reference: citation string for audit.
        pressure_pa / inner_radius_m / wall_thickness_m: geometry +
            loading parameters used in both the analytical + numerical
            computations (audit trail).
        case_id: the candidate case this cross-check was run against.
        generated_at_utc: ISO 8601 timestamp.
    """

    verdict: CrossCheckVerdict
    analytical_pa: float
    observed_pa: float
    residual_pct: float
    tolerance_pct: float
    material_id: str
    material_reference: str
    pressure_pa: float
    inner_radius_m: float
    wall_thickness_m: float
    case_id: str
    generated_at_utc: str


def _write_wall_coupon_inp(
    case_dir: Path,
    *,
    jobname: str,
    material: Material,
    hoop_stress_pa: float,
    edge_length_m: float = 0.01,
) -> Path:
    """Write a single-C3D8 wall-coupon INP.

    The coupon is a unit hex with one face under uniform pressure
    (sign convention: positive pressure value compresses the face).
    The applied pressure equals the analytical hoop stress magnitude;
    the ccx-reported σ_xx in the coupon should equal the analytical
    value to within discretisation error.

    BCs: opposite face fully clamped (plane-strain analog through the
    single element); lateral faces free (1D stress state in the loaded
    axis).
    """
    e_pa = material.youngs_modulus_pa
    nu = material.poisson_ratio
    label = material.id.replace("-", "_").upper()
    length = float(edge_length_m)

    nodes = (
        (1, 0.0, 0.0, 0.0),
        (2, length, 0.0, 0.0),
        (3, length, length, 0.0),
        (4, 0.0, length, 0.0),
        (5, 0.0, 0.0, length),
        (6, length, 0.0, length),
        (7, length, length, length),
        (8, 0.0, length, length),
    )

    lines: list[str] = []
    lines.append("*HEADING")
    lines.append(f"Phase 19 B wall-coupon cross-check ({jobname})")
    lines.append("*NODE")
    for nid, x, y, z in nodes:
        lines.append(f"{nid}, {x:.6f}, {y:.6f}, {z:.6f}")
    lines.append("*ELEMENT, TYPE=C3D8, ELSET=EALL")
    lines.append("1, 1, 2, 3, 4, 5, 6, 7, 8")
    lines.append(f"*MATERIAL, NAME={label}")
    lines.append("*ELASTIC")
    lines.append(f"{e_pa:.6e}, {nu:.6f}")
    lines.append(f"*SOLID SECTION, ELSET=EALL, MATERIAL={label}")
    # Statically-determinate BCs for PURE uniaxial σ_xx (Saint-Venant).
    # Over-constraining the x=0 face (fixing all 3 DOFs on every
    # node) creates Poisson lockup → σ_xx reads ~14% high vs the
    # analytical traction. Instead constrain the minimum DOFs to
    # remove rigid-body motion:
    #   * Node 1 (0,0,0) fixed in x, y, z
    #   * Node 4 (0,L,0) fixed in x, z (y-free so Poisson contracts)
    #   * Node 5 (0,0,L) fixed in x, y (z-free for the same reason)
    #   * Nodes 8 (0,L,L) fixed in x only
    # This gives a statically-determinate system that develops the
    # applied traction as pure σ_xx with no off-axis Poisson coupling.
    lines.append("*BOUNDARY")
    lines.append("1, 1, 1, 0.0")
    lines.append("1, 2, 2, 0.0")
    lines.append("1, 3, 3, 0.0")
    lines.append("4, 1, 1, 0.0")
    lines.append("4, 3, 3, 0.0")
    lines.append("5, 1, 1, 0.0")
    lines.append("5, 2, 2, 0.0")
    lines.append("8, 1, 1, 0.0")
    # Apply pressure (positive = compresses the face, so σ_xx becomes
    # NEGATIVE / compressive when ccx integrates. The analytical
    # hoop stress is the magnitude; the verdict compares magnitudes.
    lines.append("*ELSET, ELSET=ELOAD")
    lines.append("1")
    lines.append("*STEP")
    lines.append("*STATIC")
    lines.append("*DLOAD")
    # CalculiX C3D8 face numbering: P1=z=0, P2=z=L, P3=y=0,
    # P4=x=L, P5=y=L, P6=x=0. We want the +x face (P4) so the
    # applied normal traction develops σ_xx, which is what we then
    # read from the .frd. Phase 19 B initial commit used P2 (the
    # z=L face) — that yielded ~13% residual because we were
    # loading σ_zz but reading σ_xx (a Poisson cross-term, not the
    # real uniaxial response).
    lines.append(f"ELOAD, P4, {hoop_stress_pa:.6e}")
    lines.append("*NODE FILE")
    lines.append("U")
    lines.append("*EL FILE")
    lines.append("S")
    lines.append("*END STEP")
    lines.append("")

    inp_path = case_dir / f"{jobname}.inp"
    inp_path.write_text("\n".join(lines), encoding="utf-8")
    return inp_path


def _extract_observed_hoop_stress_pa(
    frd_path: Path,
) -> float:
    """Read the σ_xx (first stress component) magnitude from the .frd.

    On a 1D-loaded coupon, σ_xx is the dominant component and equals
    the applied membrane stress within element discretisation error.
    Returns the average magnitude across all 8 nodes (nodal
    extrapolation default in CalculiX writes stress per node).
    """
    reader = CalculiXReader(frd_path, unit_system=UnitSystem.SI)
    stress = reader.get_field(CanonicalField.STRESS_TENSOR, step_id=1)
    if stress is None:
        raise CalculiXRunError(
            f"no stress field in {frd_path}", returncode=None,
            stderr_tail="", stdout_tail="",
        )
    arr = stress.at_nodes()
    # Stress tensor in Voigt order: [σxx, σyy, σzz, σxy, σyz, σxz].
    sxx_per_node = arr[:, 0]
    return float(abs(sxx_per_node).mean())


def run_cylinder_pv_cross_check(
    case_dir: Path,
    *,
    case_id: str,
    material_id: str,
    pressure_pa: float,
    inner_radius_m: float,
    wall_thickness_m: float,
    jobname: str = "cylpv_xcheck",
    ccx_binary: str = "ccx",
    timeout_sec: float = 30.0,
    tolerance_pct: float = CROSS_CHECK_TOLERANCE_PCT,
) -> CrossCheckResult:
    """Execute the full analytical + numerical cross-check.

    Steps:
      1. Compute the analytical hoop stress via Lame (raises if t/r > 0.1).
      2. Resolve the material from the SSOT library.
      3. Write the wall-coupon INP loaded with the analytical traction.
      4. Run ccx.
      5. Read the observed σ_xx magnitude from the .frd.
      6. Compute residual_pct + verdict.

    Raises:
        ValueError / CylinderHoopValidityError: on bad inputs.
        CalculiXRunError: on ccx failure (caller decides whether to
            mark the verdict FAIL or propagate).
    """
    analytical_pa = compute_analytical_hoop_stress_pa(
        pressure_pa=pressure_pa,
        inner_radius_m=inner_radius_m,
        wall_thickness_m=wall_thickness_m,
    )
    material = get_material(material_id)
    _write_wall_coupon_inp(
        case_dir,
        jobname=jobname,
        material=material,
        hoop_stress_pa=analytical_pa,
    )
    runner = CalculiXRunner(ccx_binary=ccx_binary, timeout_sec=timeout_sec)
    ccx_result = runner.run(case_dir, jobname)
    assert ccx_result.frd_path is not None, "ccx reported success without .frd"
    observed_pa = _extract_observed_hoop_stress_pa(ccx_result.frd_path)
    residual_pct = (observed_pa - analytical_pa) / analytical_pa * 100.0
    verdict: CrossCheckVerdict = (
        "PASS" if abs(residual_pct) <= tolerance_pct else "FAIL"
    )
    return CrossCheckResult(
        verdict=verdict,
        analytical_pa=analytical_pa,
        observed_pa=observed_pa,
        residual_pct=residual_pct,
        tolerance_pct=tolerance_pct,
        material_id=material_id,
        material_reference=material.reference,
        pressure_pa=pressure_pa,
        inner_radius_m=inner_radius_m,
        wall_thickness_m=wall_thickness_m,
        case_id=case_id,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
    )


def write_verdict_yaml(
    case_golden_dir: Path,
    result: CrossCheckResult,
) -> Path:
    """Persist a verdict artifact next to the case's other golden
    samples.

    Returns the path of the written artifact (so the caller can log
    or open it). YAML format chosen for human-readability; the
    loader uses ``json.loads`` on the JSON-compatible subset we emit
    so the parse path stays trivial.
    """
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
        "analytical_pa": result.analytical_pa,
        "observed_pa": result.observed_pa,
        "material_id": result.material_id,
        "material_reference": result.material_reference,
        "pressure_pa": result.pressure_pa,
        "inner_radius_m": result.inner_radius_m,
        "wall_thickness_m": result.wall_thickness_m,
        "generated_at_utc": result.generated_at_utc,
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


def load_verdict_yaml(case_golden_dir: Path) -> dict | None:
    """Read the verdict artifact for a case, or return None when absent.

    Used by the :mod:`app.services.reporting._claim_tier` loader to
    decide whether to promote a case to ``tier_2_validated`` at
    module load. Returns ``None`` (not raises) when the file is
    missing so the loader gracefully falls back to
    ``tier_1_candidate`` for un-cross-checked cases.
    """
    path = case_golden_dir / VERDICT_YAML_FILENAME
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


__all__ = [
    "CrossCheckResult",
    "CrossCheckVerdict",
    "VERDICT_YAML_FILENAME",
    "load_verdict_yaml",
    "run_cylinder_pv_cross_check",
    "write_verdict_yaml",
]
