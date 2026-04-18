"""P1-02 hot-smoke E2E test (real CalculiX on GS-001).

ADR-008 N-1: this is the honest P0→P1 demo gate baseline — run the
real ``ccx`` binary inside the P1-01 base image on the existing
``golden_samples/GS-001/gs001.inp`` deck, parse the resulting FRD, and
have ``agents.viz`` emit the real manifest.yaml (with ``replay: false``
/ ``geometry_source: real``) and Markdown report.

The 5% Golden-Sample threshold is explicitly *not* checked here — that
moved to P1-03 per ADR-008 N-1. Hot-smoke DoD is:

  * ccx 2.20+ converges on the GS-001 input inside the container.
  * FRD / dat / sta files are produced.
  * ``agents.viz`` writes manifest.yaml whose ``execution_mode`` field
    carries ``replay: false`` and ``geometry_source: real``.
  * A Markdown report is produced next to the manifest.

Outside the container (``AI_FEA_IN_CONTAINER`` unset) the test skips.
Inside the container we expect a converged run; the test fails hard
on any other outcome so broken base images cannot sneak through.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from agents.viz import run as run_viz
from schemas.sim_plan import BCSpec, GeometrySpec, LoadSpec, MaterialSpec, SimPlan
from schemas.sim_state import FaultClass

IN_CONTAINER = os.getenv("AI_FEA_IN_CONTAINER", "").strip().lower() in {"1", "true", "yes"}

REPO_ROOT = Path(__file__).resolve().parent.parent
GS001_INP = REPO_ROOT / "golden_samples" / "GS-001" / "gs001.inp"


pytestmark = pytest.mark.skipif(
    not IN_CONTAINER,
    reason="hot_smoke requires the P1-01 container (AI_FEA_IN_CONTAINER=1)",
)


def _probe_ccx_version(ccx_bin: str) -> str:
    proc = subprocess.run([ccx_bin, "-v"], capture_output=True, text=True, timeout=30)
    combined = proc.stdout + proc.stderr
    for token in combined.split():
        if token.replace(".", "").isdigit() and "." in token:
            return token
    return "unknown"


def _gs001_plan() -> SimPlan:
    """SimPlan describing GS-001 well enough for the viz / manifest layer.

    The hot-smoke path does *not* use the Architect/Mesh/Solver templates
    — the existing ``gs001.inp`` is the mesh+deck — so the plan only
    has to be consistent enough for viz.run() to produce a valid
    manifest. Values mirror the GS-001 README.
    """
    return SimPlan(
        case_id="AI-FEA-P1-02",
        description="GS-001 cantilever beam — real CalculiX hot-smoke inside P1-01 image.",
        geometry=GeometrySpec(
            kind="prebuilt_inp",
            parameters={"source": "golden_samples/GS-001/gs001.inp"},
        ),
        material=MaterialSpec(
            name="STEEL",
            youngs_modulus_pa=210e9,
            poissons_ratio=0.3,
        ),
        loads=[
            LoadSpec(
                kind="concentrated_force",
                parameters={"magnitude": -400.0, "node_set": "free_end"},
            )
        ],
        boundary_conditions=[BCSpec(kind="fixed", parameters={"node_set": "fixed_base"})],
        reference_values={
            "displacement_mm": 0.7619,
            "stress_MPa": 240.0,
        },
    )


def test_p1_02_hot_smoke_real_ccx(tmp_path):
    assert GS001_INP.exists(), f"GS-001 input missing: {GS001_INP}"

    ccx_bin = shutil.which("ccx")
    assert ccx_bin, "ccx not on PATH inside the P1-01 container"

    run_id = "run-p1-02-hotsmoke-gs001"
    run_dir = tmp_path / "runs" / run_id
    solver_dir = run_dir / "solver"
    solver_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(GS001_INP, solver_dir / "gs001.inp")

    proc = subprocess.run(
        [ccx_bin, "-i", "gs001"],
        cwd=solver_dir,
        capture_output=True,
        text=True,
        timeout=600,
    )
    stdout_tail = (proc.stdout or "")[-1000:]
    stderr_tail = (proc.stderr or "")[-1000:]
    assert proc.returncode == 0, (
        f"ccx returned {proc.returncode}\nSTDOUT tail:\n{stdout_tail}\nSTDERR tail:\n{stderr_tail}"
    )

    frd_path = solver_dir / "gs001.frd"
    dat_path = solver_dir / "gs001.dat"
    sta_path = solver_dir / "gs001.sta"
    assert frd_path.exists(), "ccx did not emit a .frd file"
    assert dat_path.exists(), "ccx did not emit a .dat file"
    assert sta_path.exists(), "ccx did not emit a .sta file"

    ccx_version = _probe_ccx_version(ccx_bin)

    state: dict = {
        "plan": _gs001_plan(),
        "run_id": run_id,
        "project_state_dir": str(run_dir),
        "artifacts": [str(frd_path), str(dat_path), str(sta_path)],
        "history": [],
        "retry_budgets": {},
        "fault_class": FaultClass.NONE,
        "frd_path": str(frd_path),
        "solve_path": str(solver_dir / "gs001.inp"),
        "solve_metadata": {
            "wall_time_s": 0.0,
            "ccx_version": ccx_version,
            "converged": True,
        },
        "verdict": "Needs Review",
        # ADR-008 N-3 honest provenance — this run hit a real solver.
        "execution_mode": {"replay": False, "geometry_source": "real"},
    }

    result = run_viz(state)

    assert result["fault_class"] == FaultClass.NONE
    reports = result["reports"]
    manifest_path = Path(reports["manifest"])
    report_path = Path(reports["markdown"])
    assert manifest_path.exists()
    assert report_path.exists()

    manifest_text = manifest_path.read_text(encoding="utf-8")
    assert "replay: false" in manifest_text
    assert "geometry_source: real" in manifest_text
    assert "calculix" in manifest_text
    assert run_id in manifest_text

    # Copy the artefacts to the repo ``runs/`` tree so the PR can ship
    # them for Kogami's visual review.
    published = REPO_ROOT / "runs" / run_id
    if published.exists():
        shutil.rmtree(published)
    shutil.copytree(run_dir, published)
