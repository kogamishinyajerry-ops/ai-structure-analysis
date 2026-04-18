from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from tools.gmsh_driver import build_field_config, generate_mesh


@patch("tools.gmsh_driver.GMSH_AVAILABLE", False)
def test_generate_mesh_fallback(tmp_path):
    """Fallback meshing still emits a mesh artifact + sidecar metadata."""
    geom_path = tmp_path / "model.step"
    geom_path.write_text("Dummy STEP", encoding="utf-8")

    out_path = generate_mesh(geom_path, {"global_size": 1.0}, tmp_path)

    assert out_path.exists()
    assert out_path.name == "model.inp"
    assert "C3D4" in out_path.read_text(encoding="utf-8")

    mesh_meta = json.loads((tmp_path / "mesh_meta.json").read_text(encoding="utf-8"))
    assert mesh_meta["generation_mode"] == "fallback"
    assert mesh_meta["field_config"]["mesh_level"] == "medium"


def test_build_field_config_detects_thin_wall():
    config = build_field_config(
        {"mesh_level": "coarse", "thin_wall_threshold_m": 5e-4},
        {"bounding_box_mm": [100.0, 12.0, 500.0], "min_feature_size_m": 2.5e-4},
    )

    assert config["mesh_level"] == "coarse"
    assert config["thin_wall_detected"] is True
    assert config["thin_wall_size"] is not None
    assert config["field_min_size"] <= config["thin_wall_size"]


def test_generate_mesh_with_gmsh_mocks(tmp_path):
    """The gmsh path should build Distance/Threshold background fields."""
    mock_gmsh = MagicMock()
    mock_option = MagicMock()
    mock_model = MagicMock()
    mock_mesh = MagicMock()
    mock_field = MagicMock()

    mock_gmsh.option = mock_option
    mock_gmsh.model = mock_model
    mock_model.mesh = mock_mesh
    mock_mesh.field = mock_field
    mock_field.add.side_effect = [7, 8, 9, 10]
    mock_model.getEntities.side_effect = lambda dim: [(2, 11), (2, 12)] if dim == 2 else [(3, 21)]

    geom_path = tmp_path / "model.step"
    geom_path.write_text("Dummy STEP", encoding="utf-8")
    geom_path.with_name("geometry_meta.json").write_text(
        json.dumps({"bounding_box_mm": [100.0, 12.0, 500.0], "min_feature_size_m": 2.5e-4}),
        encoding="utf-8",
    )

    def _write_stub(path: str) -> None:
        Path(path).write_text("*dummy*", encoding="utf-8")

    with (
        patch.dict("sys.modules", {"gmsh": mock_gmsh}),
        patch("tools.gmsh_driver.GMSH_AVAILABLE", True),
    ):
        import tools.gmsh_driver as drv

        drv.gmsh = mock_gmsh
        mock_gmsh.write.side_effect = _write_stub

        out_path = drv.generate_mesh(
            geom_path,
            {"global_size": 0.01, "mesh_level": "fine", "element_order": "linear"},
            tmp_path,
        )

        assert out_path.name == "model.inp"
        mock_gmsh.initialize.assert_called_once()
        mock_model.occ.importShapes.assert_called_with(str(geom_path))
        mock_option.setNumber.assert_any_call("Mesh.MeshSizeMin", 8.333333333333333e-05)
        mock_option.setNumber.assert_any_call("Mesh.MeshSizeMax", 0.01)
        mock_option.setNumber.assert_any_call("Mesh.ElementOrder", 1)
        mock_option.setNumber.assert_any_call("Mesh.Format", 39)

        mock_field.setNumbers.assert_any_call(7, "FacesList", [11, 12])
        mock_field.setNumber.assert_any_call(8, "IField", 7)
        mock_field.setNumber.assert_any_call(9, "IField", 7)
        mock_field.setNumbers.assert_any_call(10, "FieldsList", [8, 9])
        mock_field.setAsBackgroundMesh.assert_called_with(10)

        mock_mesh.generate.assert_called_with(3)
        mock_gmsh.write.assert_called_with(str(out_path))
        mock_gmsh.finalize.assert_called_once()

        mesh_meta = json.loads((tmp_path / "mesh_meta.json").read_text(encoding="utf-8"))
        assert mesh_meta["generation_mode"] == "gmsh"
        assert mesh_meta["field_config"]["thin_wall_detected"] is True
