from __future__ import annotations

import json

from agents.mesh import run
from schemas.sim_plan import GeometrySpec, MeshStrategy, SimPlan
from schemas.sim_state import FaultClass


def _build_plan(mesh_level: str = "medium") -> SimPlan:
    return SimPlan(
        case_id="AI-FEA-P0-06",
        geometry=GeometrySpec(kind="naca", parameters={"profile": "NACA0012"}),
        mesh=MeshStrategy(mesh_level=mesh_level),
    )


def _geometry_artifacts(tmp_path) -> list[str]:
    geom_dir = tmp_path / "geometry"
    geom_dir.mkdir(parents=True, exist_ok=True)
    step_path = geom_dir / "model.step"
    meta_path = geom_dir / "geometry_meta.json"
    step_path.write_text("solid", encoding="utf-8")
    meta_path.write_text(
        json.dumps({"bounding_box_mm": [100.0, 12.0, 500.0], "min_feature_size_m": 2.5e-4}),
        encoding="utf-8",
    )
    return [str(step_path), str(meta_path)]


def test_mesh_agent_routes_mesh_jacobian_failures(tmp_path, monkeypatch):
    def fake_generate_mesh(step_path, params, output_dir):
        output_dir.mkdir(parents=True, exist_ok=True)
        mesh_path = output_dir / "model.inp"
        mesh_path.write_text("*mesh*", encoding="utf-8")
        (output_dir / "mesh_meta.json").write_text(
            json.dumps({"field_config": {"thin_wall_detected": True}}),
            encoding="utf-8",
        )
        return mesh_path

    monkeypatch.setattr("agents.mesh.generate_mesh", fake_generate_mesh)
    monkeypatch.setattr(
        "agents.mesh.check_mesh_quality",
        lambda path, thresholds=None: {
            "ok": False,
            "passed": False,
            "bad_element_ids": [3, 4],
            "resolution_element_ids": [],
            "findings": ["Minimum Jacobian 0.10 is below threshold 0.2."],
        },
    )

    result = run(
        {
            "plan": _build_plan(),
            "project_state_dir": str(tmp_path),
            "artifacts": _geometry_artifacts(tmp_path),
            "history": [],
            "retry_budgets": {},
        }
    )

    assert result["fault_class"] == FaultClass.MESH_JACOBIAN
    assert result["retry_budgets"] == {"mesh": 1}
    assert result["history"][0]["fault_class"] == FaultClass.MESH_JACOBIAN.value
    assert result["history"][0]["bad_element_ids"] == [3, 4]


def test_mesh_agent_routes_resolution_failures(tmp_path, monkeypatch):
    def fake_generate_mesh(step_path, params, output_dir):
        output_dir.mkdir(parents=True, exist_ok=True)
        mesh_path = output_dir / "model.inp"
        mesh_path.write_text("*mesh*", encoding="utf-8")
        (output_dir / "mesh_meta.json").write_text(
            json.dumps({"field_config": {"thin_wall_detected": False}}),
            encoding="utf-8",
        )
        return mesh_path

    monkeypatch.setattr("agents.mesh.generate_mesh", fake_generate_mesh)
    monkeypatch.setattr(
        "agents.mesh.check_mesh_quality",
        lambda path, thresholds=None: {
            "ok": False,
            "passed": False,
            "bad_element_ids": [],
            "resolution_element_ids": [8],
            "findings": ["Maximum Aspect Ratio 14.0 is above threshold 10.0."],
        },
    )

    result = run(
        {
            "plan": _build_plan(),
            "project_state_dir": str(tmp_path),
            "artifacts": _geometry_artifacts(tmp_path),
            "history": [],
            "retry_budgets": {},
        }
    )

    assert result["fault_class"] == FaultClass.MESH_RESOLUTION
    assert result["history"][0]["fault_class"] == FaultClass.MESH_RESOLUTION.value
    assert result["verdict"] == "re-run"


def test_mesh_agent_escalates_mesh_level_on_retry(tmp_path, monkeypatch):
    seen_params = {}

    def fake_generate_mesh(step_path, params, output_dir):
        seen_params.update(params)
        output_dir.mkdir(parents=True, exist_ok=True)
        mesh_path = output_dir / "model.inp"
        mesh_path.write_text("*mesh*", encoding="utf-8")
        (output_dir / "mesh_meta.json").write_text(
            json.dumps({"field_config": {"thin_wall_detected": True}}),
            encoding="utf-8",
        )
        return mesh_path

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

    result = run(
        {
            "plan": _build_plan(mesh_level="medium"),
            "project_state_dir": str(tmp_path),
            "artifacts": _geometry_artifacts(tmp_path),
            "history": [],
            "retry_budgets": {"mesh": 2},
        }
    )

    assert seen_params["mesh_level"] == "very_fine"
    assert result["fault_class"] == FaultClass.NONE
    assert any(path.endswith("mesh_meta.json") for path in result["artifacts"])
