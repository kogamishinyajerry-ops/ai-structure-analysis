import json
from unittest.mock import MagicMock, patch

import pytest

from tools.freecad_driver import generate_geometry, generate_naca_points, parse_naca_4digit


def test_parse_naca_4digit():
    """Verify parsing of aerodynamic parameters."""
    m, p, t = parse_naca_4digit("NACA2412")
    assert m == 0.02
    assert p == 0.4
    assert t == 0.12

    m, p, t = parse_naca_4digit("NACA0012")
    assert m == 0.0
    assert p == 0.0
    assert t == 0.12

    with pytest.raises(ValueError):
        parse_naca_4digit("NACA001")


def test_generate_naca_points():
    """Verify math output for analytical NACA equations."""
    # Symmetrical 0012
    points = generate_naca_points(0.0, 0.0, 0.12, chord=1.0, num_points=10)

    # Check leading edge (should be around origin)
    # The middle of the array is the leading edge because the ordering is
    # trailing -> upper -> leading -> lower -> trailing.

    # Calculate expected points count
    # 10 points * 2 (upper/lower) = 20 points, but leading edge is shared. Also trailing edge loops.
    assert len(points) == 21

    # Check trailing edge is closed
    assert points[0] == points[-1]


@patch("tools.freecad_driver.FREECAD_AVAILABLE", False)
def test_generate_geometry_without_freecad_raises(tmp_path):
    """ADR-008 N-3: missing FreeCAD must hard-fail unless opt-in is set."""
    spec = {"profile": "NACA0012", "chord_length": 2.0, "span": 5.0}

    with pytest.raises(RuntimeError, match="AI_FEA_ALLOW_DUMMY_GEOMETRY"):
        generate_geometry(spec, tmp_path)


@patch("tools.freecad_driver.FREECAD_AVAILABLE", False)
def test_generate_geometry_dummy_opt_in_via_kwarg(tmp_path):
    """ADR-008 N-3: explicit allow_dummy=True produces the placeholder STEP."""
    spec = {"profile": "NACA0012", "chord_length": 2.0, "span": 5.0}

    step_path = generate_geometry(spec, tmp_path, allow_dummy=True)

    assert step_path.exists()
    assert step_path.name == "model.step"
    assert (tmp_path / "model.FCStd").exists()

    topo_map_path = tmp_path / "topo_map.json"
    assert topo_map_path.exists()
    with open(topo_map_path) as f:
        data = json.load(f)
        assert len(data) == 1
        assert "fixed_base" in data[0]
        assert "skin" in data[0]
        assert "tip_load" in data[0]

    meta_path = tmp_path / "geometry_meta.json"
    assert meta_path.exists()
    meta = json.loads(meta_path.read_text())
    assert meta["watertight"] is True
    assert meta["manifold"] is True
    assert meta["volume_m3"] > 0


@patch("tools.freecad_driver.FREECAD_AVAILABLE", False)
def test_generate_geometry_dummy_opt_in_via_env(tmp_path, monkeypatch):
    """ADR-008 N-3: env var AI_FEA_ALLOW_DUMMY_GEOMETRY=1 also unlocks the stub."""
    monkeypatch.setenv("AI_FEA_ALLOW_DUMMY_GEOMETRY", "1")
    spec = {"profile": "NACA0012", "chord_length": 1.0, "span": 1.0}

    step_path = generate_geometry(spec, tmp_path)

    assert step_path.exists()
    assert step_path.name == "model.step"

    # Verify topo_map
    topo_map_path = tmp_path / "topo_map.json"
    assert topo_map_path.exists()
    with open(topo_map_path) as f:
        data = json.load(f)
        assert len(data) == 1
        assert "fixed_base" in data[0]
        assert "skin" in data[0]
        assert "tip_load" in data[0]

    meta_path = tmp_path / "geometry_meta.json"
    assert meta_path.exists()
    meta = json.loads(meta_path.read_text())
    assert meta["watertight"] is True
    assert meta["manifold"] is True
    assert meta["volume_m3"] > 0


def test_generate_geometry_with_freecad_mocks(tmp_path):
    """Test the full Part and FreeCAD invocation logic via Mocks."""

    mock_freecad = MagicMock()
    mock_freecad.newDocument.return_value = MagicMock()

    mock_part = MagicMock()
    mock_face = MagicMock()
    mock_solid = MagicMock()
    mock_solid.Volume = 12.5
    mock_solid.isClosed.return_value = True
    mock_solid.isValid.return_value = True
    mock_solid.BoundBox = MagicMock(XLength=1500.0, YLength=120.0, ZLength=5000.0)

    mock_part.Face.return_value = mock_face
    mock_face.extrude.return_value = mock_solid

    # Mock bounds for 3 faces: root (z=0), tip (z=5), skin (z=2.5)
    class MockBoundBox:
        def __init__(self, z_center):
            self.ZMin = z_center - 0.5
            self.ZMax = z_center + 0.5

    face1 = MagicMock()
    face1.BoundBox = MockBoundBox(0.0)  # Root

    face2 = MagicMock()
    face2.BoundBox = MockBoundBox(2.5)  # Skin

    face3 = MagicMock()
    face3.BoundBox = MockBoundBox(5.0)  # Tip

    mock_solid.Faces = [face1, face2, face3]

    with (
        patch.dict("sys.modules", {"FreeCAD": mock_freecad, "Part": mock_part}),
        patch("tools.freecad_driver.FREECAD_AVAILABLE", True),
    ):
        # Also patch the module-level FreeCAD references
        import tools.freecad_driver as drv

        drv.FreeCAD = mock_freecad
        drv.Part = mock_part

        spec = {"profile": "NACA0015", "chord_length": 1.5, "span": 5.0}

        step_path = drv.generate_geometry(spec, tmp_path)

        assert step_path.name == "model.step"

        mock_part.makePolygon.assert_called_once()
        mock_part.Face.assert_called_once()
        mock_face.extrude.assert_called_once()

        # Verify the topology mapping logic with the mocked bounding boxes
        topo_map_path = tmp_path / "topo_map.json"
        assert topo_map_path.exists()
        with open(topo_map_path) as f:
            data = json.load(f)

        assert data[0]["fixed_base"] == ["Face1"]
        assert data[0]["skin"] == ["Face2"]
        assert data[0]["tip_load"] == ["Face3"]

        meta_path = tmp_path / "geometry_meta.json"
        meta = json.loads(meta_path.read_text())
        assert meta["bounding_box_mm"] == [1500.0, 120.0, 5000.0]
