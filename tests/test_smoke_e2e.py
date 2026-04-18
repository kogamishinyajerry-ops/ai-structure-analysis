"""P0-10 smoke E2E for the full agent graph."""

from __future__ import annotations

import json

from agents.graph import compile_graph
from schemas.sim_plan import BCSpec, GeometrySpec, LoadSpec, MaterialSpec, SimPlan
from schemas.sim_state import FaultClass

SAMPLE_FRD = """\
    1C
    2C                                                                   1
 -1         1 0.00000E+00 0.00000E+00 0.00000E+00
 -1         2 1.00000E+00 0.00000E+00 0.00000E+00
 -3
 100CL 101         1           1PDISP               1  1
 -4  D1
 -4  D2
 -4  D3
 -1         1 0.00000E+00 0.00000E+00 0.00000E+00
 -1         2 1.50000E-03 0.00000E+00-2.00000E-04
 -3
 100CL 102         1           1PSTRESS             1  1
 -4  SXX
 -4  SYY
 -4  SZZ
 -4  SXY
 -4  SYZ
 -4  SZX
 -1         1 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00
 -1         2 1.20000E+06 3.00000E+05 0.00000E+00 1.50000E+05 0.00000E+00 0.00000E+00
 -3
 9999
"""


def _naca_smoke_plan() -> SimPlan:
    return SimPlan(
        case_id="AI-FEA-P0-10",
        description="NACA0012 cantilever smoke E2E",
        geometry=GeometrySpec(
            kind="naca",
            parameters={"profile": "NACA0012", "chord_length": 1.0, "span": 1.0},
        ),
        material=MaterialSpec(
            name="Aluminum 7075",
            youngs_modulus_pa=71.7e9,
            poissons_ratio=0.33,
        ),
        loads=[
            LoadSpec(
                kind="concentrated_force",
                parameters={"magnitude": -500.0, "node_set": "Ntip"},
            )
        ],
        boundary_conditions=[BCSpec(kind="fixed", parameters={"node_set": "Nroot"})],
        reference_values={
            "displacement": 0.0015132745950421555,
            "stress": 1112429.7730643495,
        },
    )


def test_p0_10_smoke_e2e_full_graph(monkeypatch, tmp_path):
    """Run Architect->Geometry->Mesh->Solver->Reviewer->Viz without external binaries."""

    def fake_extract_structured_data(**kwargs):
        return _naca_smoke_plan()

    def fake_generate_mesh(step_path, params, output_dir):
        output_dir.mkdir(parents=True, exist_ok=True)
        mesh_path = output_dir / "model.inp"
        mesh_path.write_text(
            "*NODE\n"
            "1, 0.0, 0.0, 0.0\n"
            "2, 1.0, 0.0, 0.0\n"
            "3, 0.0, 1.0, 0.0\n"
            "4, 0.0, 0.0, 1.0\n"
            "*ELEMENT, TYPE=C3D4, ELSET=Eall\n"
            "1, 1, 2, 3, 4\n"
            "*NSET, NSET=Nroot\n"
            "1\n"
            "*NSET, NSET=Ntip\n"
            "2\n",
            encoding="utf-8",
        )
        (output_dir / "mesh_meta.json").write_text(
            json.dumps({"field_config": {"thin_wall_detected": False}}),
            encoding="utf-8",
        )
        return mesh_path

    def fake_run_solve(inp_path, work_dir, **kwargs):
        frd_path = work_dir / "solve.frd"
        dat_path = work_dir / "solve.dat"
        sta_path = work_dir / "solve.sta"
        frd_path.write_text(SAMPLE_FRD, encoding="utf-8")
        dat_path.write_text("synthetic smoke result", encoding="utf-8")
        sta_path.write_text("STEP 1 converged", encoding="utf-8")
        return {
            "frd_path": str(frd_path),
            "dat_path": str(dat_path),
            "sta_path": str(sta_path),
            "converged": True,
            "wall_time_s": 0.12,
            "returncode": 0,
            "ccx_version": "2.21",
            "fault_class": FaultClass.NONE,
            "failure_reason": None,
        }

    monkeypatch.setattr("agents.architect._extract_structured_data", fake_extract_structured_data)
    monkeypatch.setattr("agents.mesh.generate_mesh", fake_generate_mesh)
    monkeypatch.setattr(
        "agents.mesh.check_mesh_quality",
        lambda path, thresholds=None: {
            "ok": True,
            "passed": True,
            "bad_element_ids": [],
            "resolution_element_ids": [],
            "findings": [],
        },
    )
    monkeypatch.setattr("agents.solver.run_solve", fake_run_solve)

    run_dir = tmp_path / "runs" / "run-20260418-AI-FEA-P0-10-smoke"
    result = compile_graph().invoke(
        {
            "user_request": "NACA0012 cantilever wing, Aluminum 7075, 500N tip load.",
            "run_id": "run-20260418-AI-FEA-P0-10-smoke",
            "project_state_dir": str(run_dir),
            "artifacts": [],
            "history": [],
            "retry_budgets": {},
            "fault_class": FaultClass.NONE,
        }
    )

    report_path = run_dir / "reports" / "report.md"
    vtp_path = run_dir / "reports" / "results.vtp"
    manifest_path = run_dir / "manifest.yaml"

    assert result["fault_class"] == FaultClass.NONE
    assert result["verdict"] == "Accept"
    assert result["reports"]["markdown"] == str(report_path)
    assert result["reports"]["vtp"] == str(vtp_path)
    assert result["reports"]["manifest"] == str(manifest_path)
    assert report_path.exists()
    assert vtp_path.exists()
    assert manifest_path.exists()
    assert "von_mises" in report_path.read_text(encoding="utf-8")
    assert "run-20260418-AI-FEA-P0-10-smoke" in manifest_path.read_text(encoding="utf-8")
