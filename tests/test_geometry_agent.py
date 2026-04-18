from __future__ import annotations

from schemas.sim_plan import GeometrySpec, SimPlan
from schemas.sim_state import FaultClass


def test_geometry_agent_returns_geometry_path_for_valid_geometry(tmp_path, monkeypatch):
    from agents.geometry import run

    step_path = tmp_path / "geometry" / "model.step"

    def fake_generate_geometry(spec, output_dir, *, allow_dummy=None):
        output_dir.mkdir(parents=True, exist_ok=True)
        step_path.write_text("solid", encoding="utf-8")
        (output_dir / "topo_map.json").write_text("[]", encoding="utf-8")
        (output_dir / "geometry_meta.json").write_text("{}", encoding="utf-8")
        return step_path

    monkeypatch.setattr("agents.geometry.generate_geometry", fake_generate_geometry)
    monkeypatch.setattr(
        "agents.geometry.check_geometry",
        lambda path: {"valid": True, "findings": [], "watertight": True, "manifold": True},
    )

    plan = SimPlan(
        case_id="AI-FEA-P0-05",
        geometry=GeometrySpec(kind="naca", parameters={"profile": "NACA0012"}),
    )
    result = run({"plan": plan, "project_state_dir": str(tmp_path)})

    assert result["geometry_path"] == str(step_path)
    assert result["fault_class"] == FaultClass.NONE
    assert str(step_path) in result["artifacts"]


def test_geometry_agent_marks_geometry_invalid_when_checker_fails(tmp_path, monkeypatch):
    from agents.geometry import run

    step_path = tmp_path / "geometry" / "model.step"

    def fake_generate_geometry(spec, output_dir, *, allow_dummy=None):
        output_dir.mkdir(parents=True, exist_ok=True)
        step_path.write_text("solid", encoding="utf-8")
        (output_dir / "topo_map.json").write_text("[]", encoding="utf-8")
        return step_path

    monkeypatch.setattr("agents.geometry.generate_geometry", fake_generate_geometry)
    monkeypatch.setattr(
        "agents.geometry.check_geometry",
        lambda path: {
            "valid": False,
            "findings": ["missing_topology_keys:fixed_base,skin,tip_load"],
            "watertight": True,
            "manifold": True,
        },
    )

    plan = SimPlan(
        case_id="AI-FEA-P0-05",
        geometry=GeometrySpec(kind="naca", parameters={"profile": "NACA0012"}),
    )
    result = run({"plan": plan, "project_state_dir": str(tmp_path), "history": []})

    assert result["fault_class"] == FaultClass.GEOMETRY_INVALID
    assert result["verdict"] == "re-run"
    assert result["history"][0]["node"] == "geometry"
