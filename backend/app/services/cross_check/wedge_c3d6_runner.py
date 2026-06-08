"""Single-C3D6 wedge uniaxial Hooke's-law cross-check runner — Phase 38 B.

Adds the **6th element class** (C3D6) to the validated cohort
(prior 5: C3D4 / C3D8 / C3D10 / S4 / B31). Writes the single-wedge
uniaxial INP (``app.adapters.calculix.inp_writer.
write_single_c3d6_wedge_uniaxial_inp``), runs **real ccx**, reads the
axial stress ``sigma_zz``, and cross-checks it against the closed-form
Hooke's law ``sigma = E * epsilon``.

Because C3D6 is a constant-strain element and the model is held in a
pure uniaxial-stress state (lateral faces traction-free), the agreement
is exact to discretisation/rounding error — a clean genuine cross-check,
NOT an analytical-only reference (cf. the cylinder-pv-candidate /
nafems-le10 reference precedents).

The verdict is persisted to
``golden_samples/<case_id>/cross_check_verdict.yaml`` so the
:mod:`app.services.reporting._claim_tier` loader promotes the case to
``tier_2_validated`` on a PASS verdict at next module-load — without
re-running ccx every import. Re-running the cross-check is a deliberate
offline action.

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
    CalculiXReader,
    CalculiXRunError,
    CalculiXRunner,
)
from app.adapters.calculix.inp_writer import (
    DEFAULT_STEEL,
    MinimalHexMaterial,
    write_single_c3d6_wedge_uniaxial_inp,
)
from app.core.types import CanonicalField, UnitSystem

VERDICT_YAML_FILENAME: Final[str] = "cross_check_verdict.yaml"
"""Conventional per-case verdict filename (HF1.7b candidate carve-out)."""

# Constant-strain C3D6 in pure uniaxial stress recovers E·ε exactly;
# a 1% envelope is generous and only guards gross regressions (a bad
# BC / wrong stress component would miss by tens of percent).
CROSS_CHECK_TOLERANCE_PCT: Final[float] = 1.0

CrossCheckVerdict = Literal["PASS", "FAIL"]


@dataclass(frozen=True)
class WedgeC3D6Result:
    """Outcome of the single-C3D6 uniaxial Hooke's-law cross-check."""

    verdict: CrossCheckVerdict
    analytical_pa: float
    observed_pa: float
    residual_pct: float
    tolerance_pct: float
    youngs_modulus_pa: float
    poisson_ratio: float
    applied_strain: float
    case_id: str
    generated_at_utc: str


def _extract_observed_axial_stress_pa(frd_path: Path) -> float:
    """Read the mean nodal ``sigma_zz`` (signed) from the .frd.

    In pure uniaxial-z stress, ``sigma_zz`` is the only non-trivial
    component and equals ``E * applied_strain`` (signed) to within
    discretisation error. Stress tensor is Voigt-ordered
    ``[sxx, syy, szz, sxy, syz, sxz]`` so ``szz`` is column index 2.
    """
    reader = CalculiXReader(frd_path, unit_system=UnitSystem.SI)
    stress = reader.get_field(CanonicalField.STRESS_TENSOR, step_id=1)
    if stress is None:
        raise CalculiXRunError(
            f"no stress field in {frd_path}",
            returncode=None,
            stderr_tail="",
            stdout_tail="",
        )
    arr = stress.at_nodes()
    szz_per_node = arr[:, 2]
    return float(szz_per_node.mean())


def run_wedge_c3d6_cross_check(
    case_dir: Path,
    *,
    case_id: str,
    material: MinimalHexMaterial = DEFAULT_STEEL,
    applied_strain: float = 1.0e-3,
    jobname: str = "wedge_c3d6_xcheck",
    ccx_binary: str = "ccx",
    timeout_sec: float = 30.0,
    tolerance_pct: float = CROSS_CHECK_TOLERANCE_PCT,
) -> WedgeC3D6Result:
    """Execute the full analytical + numerical C3D6 cross-check.

    Steps: compute analytical ``sigma_zz = -E * applied_strain`` →
    write the single-C3D6 wedge INP → run ccx → read observed
    ``sigma_zz`` → residual + verdict.

    Raises:
        CalculiXRunError: on ccx failure (caller decides FAIL vs propagate).
    """
    analytical_pa = -material.youngs_modulus_pa * applied_strain  # compressive
    write_single_c3d6_wedge_uniaxial_inp(
        case_dir,
        jobname=jobname,
        material=material,
        applied_strain=applied_strain,
    )
    runner = CalculiXRunner(ccx_binary=ccx_binary, timeout_sec=timeout_sec)
    ccx_result = runner.run(case_dir, jobname)
    assert ccx_result.frd_path is not None, "ccx reported success without .frd"
    observed_pa = _extract_observed_axial_stress_pa(ccx_result.frd_path)
    residual_pct = (observed_pa - analytical_pa) / analytical_pa * 100.0
    verdict: CrossCheckVerdict = (
        "PASS" if abs(residual_pct) <= tolerance_pct else "FAIL"
    )
    return WedgeC3D6Result(
        verdict=verdict,
        analytical_pa=analytical_pa,
        observed_pa=observed_pa,
        residual_pct=residual_pct,
        tolerance_pct=tolerance_pct,
        youngs_modulus_pa=material.youngs_modulus_pa,
        poisson_ratio=material.poisson_ratio,
        applied_strain=applied_strain,
        case_id=case_id,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
    )


def write_verdict_yaml(case_golden_dir: Path, result: WedgeC3D6Result) -> Path:
    """Persist the verdict artifact (JSON-compatible subset; the
    _claim_tier loader uses ``json.loads``)."""
    if not case_golden_dir.is_dir():
        raise FileNotFoundError(
            f"case_golden_dir {case_golden_dir!s} must exist"
        )
    payload = {
        "schema_version": "1.0.0",
        "solver_kind": "linear_static",
        "case_id": result.case_id,
        "cross_check_kind": "c3d6_wedge_uniaxial_hookes_law",
        "element_class": "C3D6",
        "verdict": result.verdict,
        "tolerance_pct": result.tolerance_pct,
        "residual_pct": result.residual_pct,
        "analytical_pa": result.analytical_pa,
        "observed_pa": result.observed_pa,
        "youngs_modulus_pa": result.youngs_modulus_pa,
        "poisson_ratio": result.poisson_ratio,
        "applied_strain": result.applied_strain,
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


__all__ = [
    "WedgeC3D6Result",
    "CrossCheckVerdict",
    "VERDICT_YAML_FILENAME",
    "CROSS_CHECK_TOLERANCE_PCT",
    "run_wedge_c3d6_cross_check",
    "write_verdict_yaml",
]
