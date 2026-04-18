"""Tests for agents/viz.py."""

from __future__ import annotations

from agents.viz import run
from schemas.sim_plan import GeometrySpec, SimPlan
from schemas.sim_state import FaultClass
from tests.test_frd_parser import SAMPLE_FRD


def test_viz_agent_generates_report_vtp_and_manifest(tmp_path):
    frd_path = tmp_path / "solve.frd"
    frd_path.write_text(SAMPLE_FRD, encoding="utf-8")

    plan = SimPlan(
        case_id="AI-FEA-P0-09",
        geometry=GeometrySpec(kind="naca", parameters={"profile": "NACA0012"}),
        reference_values={"displacement": 1.6e-3, "stress": 1.1e6},
    )
    state = {
        "plan": plan,
        "project_state_dir": str(tmp_path),
        "run_id": "run-20260418-AI-FEA-P0-09-d678e5a",
        "frd_path": str(frd_path),
        "artifacts": [str(frd_path)],
        "verdict": "Accept with Note",
        "solve_metadata": {"wall_time_s": 1.23, "ccx_version": "2.21"},
    }

    result = run(state)

    assert result["fault_class"] == FaultClass.NONE
    assert result["reports"]["markdown"].endswith("report.md")
    assert result["reports"]["vtp"].endswith("results.vtp")
    assert result["reports"]["manifest"].endswith("manifest.yaml")

    report_content = (tmp_path / "reports" / "report.md").read_text(encoding="utf-8")
    manifest_content = (tmp_path / "manifest.yaml").read_text(encoding="utf-8")

    assert "von_mises" in report_content
    assert "Accept with Note" in report_content
    assert "tool_versions:" in manifest_content
    assert "sha:" in manifest_content
