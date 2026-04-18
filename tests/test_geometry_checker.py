from __future__ import annotations

import json

from checkers.geometry_checker import check_geometry


def test_check_geometry_accepts_valid_sidecars(tmp_path):
    step_path = tmp_path / "model.step"
    step_path.write_text("solid", encoding="utf-8")
    (tmp_path / "topo_map.json").write_text(
        json.dumps([{"fixed_base": ["Face1"], "tip_load": ["Face3"], "skin": ["Face2"]}]),
        encoding="utf-8",
    )
    (tmp_path / "geometry_meta.json").write_text(
        json.dumps(
            {
                "watertight": True,
                "manifold": True,
                "volume_m3": 1.2,
                "min_feature_size_m": 0.1,
                "bounding_box_mm": [1000.0, 120.0, 5000.0],
            }
        ),
        encoding="utf-8",
    )

    result = check_geometry(step_path)

    assert result["valid"] is True
    assert result["findings"] == []
    assert result["watertight"] is True
    assert result["manifold"] is True


def test_check_geometry_flags_invalid_geometry_and_topology(tmp_path):
    step_path = tmp_path / "model.step"
    step_path.write_text("", encoding="utf-8")
    (tmp_path / "topo_map.json").write_text(
        json.dumps([{"fixed_root": ["Face1"], "tip": ["Face3"]}]),
        encoding="utf-8",
    )
    (tmp_path / "geometry_meta.json").write_text(
        json.dumps(
            {
                "watertight": False,
                "manifold": False,
                "volume_m3": 0.0,
                "min_feature_size_m": 0.0,
                "bounding_box_mm": [0.0, 0.0, 0.0],
            }
        ),
        encoding="utf-8",
    )

    result = check_geometry(step_path)

    assert result["valid"] is False
    assert "empty_step_file" in result["findings"]
    assert "non_watertight_geometry" in result["findings"]
    assert "non_manifold_geometry" in result["findings"]
    assert "zero_volume_geometry" in result["findings"]
    assert any(item.startswith("missing_topology_keys:") for item in result["findings"])
