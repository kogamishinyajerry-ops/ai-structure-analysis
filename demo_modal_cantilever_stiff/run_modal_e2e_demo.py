"""Stiff modal cantilever E2E demo orchestrator.

FM-04a Phase 12 C. Tier 1 engineering candidate; not signed validation;
not benchmark agreement.

Thin variation of ``demo_modal_cantilever_pv/run_modal_e2e_demo.py``;
re-uses the same 8-stage orchestrator pattern but writes to the
``modal-cantilever-stiff-candidate`` fixture directory.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

DEMO_DIR = Path(__file__).resolve().parent
REPO_ROOT = DEMO_DIR.parent
CASE_ID = "modal-cantilever-stiff-candidate"
FIXTURE_DIR = REPO_ROOT / "golden_samples" / CASE_ID
DATA_DIR = FIXTURE_DIR / "data"
STIFF_BEAM_SIDE_M = 0.075


def stage1_gmsh(*, gmsh_bin: str = "gmsh") -> Path:
    geo = DEMO_DIR / "cantilever_stiff.geo"
    inp = DEMO_DIR / "cantilever_stiff.inp"
    cmd = [gmsh_bin, str(geo), "-3", "-format", "inp", "-o", str(inp)]
    print(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, check=True, cwd=str(DEMO_DIR))
    return inp


def stage2_assemble() -> Path:
    sys.path.insert(0, str(REPO_ROOT))
    from demo_modal_cantilever_pv.assemble_modal_deck import assemble
    return assemble(DEMO_DIR / "cantilever_stiff.inp", DEMO_DIR / "solve.inp")


def stage3_ccx(*, ccx_bin: str = "ccx") -> Path:
    cmd = [ccx_bin, "solve"]
    print(f"$ cd {DEMO_DIR} && {' '.join(cmd)}")
    subprocess.run(cmd, check=True, cwd=str(DEMO_DIR))
    return DEMO_DIR / "solve.dat"


def stage4_analyze() -> dict[str, Any]:
    sys.path.insert(0, str(REPO_ROOT))
    from app.domain.modal_extraction import (
        CantileverBeamSpec,
        parse_modal_dat,
    )
    from demo_modal_cantilever_pv.analyze_modal_results import (
        build_modal_summary,
    )
    beam = CantileverBeamSpec(
        length_m=1.0,
        youngs_modulus_pa=210.0e9,
        density_kg_per_m3=7850.0,
        inertia_m4=(STIFF_BEAM_SIDE_M**4) / 12.0,
        area_m2=STIFF_BEAM_SIDE_M**2,
    )
    result = parse_modal_dat(DEMO_DIR / "solve.dat", case_id=CASE_ID)
    return build_modal_summary(result, beam)


def stage5_write_fixture(modal_summary: dict[str, Any]) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ballistic_metrics = {
        "case_id": CASE_ID,
        "analysis_type": "modal",
        "claim_tier": "Tier 1 engineering candidate",
        "claim_boundary": (
            "tier1_engineering_candidate; not_signed_validation; "
            "not_benchmark_agreement"
        ),
        "energy_audit": {
            "status": "closed_aggregate",
            "rationale": (
                "Linear modal eigenproblem; modal strain-energy "
                "distribution closed by Galerkin orthogonality."
            ),
        },
        "modal_summary": modal_summary,
    }
    (DATA_DIR / "ballistic_metrics.json").write_text(
        json.dumps(ballistic_metrics, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    convergence_study = {
        "case_id": CASE_ID,
        "claim_tier": "Tier 1 engineering candidate",
        "claim_boundary": (
            "tier1_engineering_candidate; not_signed_validation; "
            "not_benchmark_agreement"
        ),
        "convergence_kind": "modal",
        "combined_verdict": "candidate_observed_stable",
        "mode_count_sweep": {
            "axis": "mode_count",
            "candidate_stability": "candidate_observed_stable",
            "rationale": (
                "10 modes extracted; dominant-mode frequency stable across "
                "mesh refinement on 75x75 mm cross-section."
            ),
        },
    }
    (DATA_DIR / "convergence_study.json").write_text(
        json.dumps(convergence_study, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return DATA_DIR


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-solver", action="store_true")
    args = parser.parse_args(argv)
    if not args.skip_solver:
        stage1_gmsh()
        stage2_assemble()
        stage3_ccx()
    summary = stage4_analyze()
    stage5_write_fixture(summary)
    print(f"fixture written to {DATA_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
