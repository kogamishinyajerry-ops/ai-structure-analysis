import numpy as np
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from checkers.jacobian import compute_tetra_volume, check_mesh_quality


def test_compute_tetra_volume():
    # Regular tetrahedron with edge length 1
    # Coordinates for a regular tet:
    pts = [
        np.array([0, 0, 0]),
        np.array([1, 0, 0]),
        np.array([0.5, np.sqrt(3)/2, 0]),
        np.array([0.5, np.sqrt(3)/6, np.sqrt(2/3)])
    ]
    vol = compute_tetra_volume(pts)
    # Expected volume of regular tet with edge l=1 is l^3 / (6*sqrt(2))
    expected = 1.0 / (6 * np.sqrt(2))
    np.testing.assert_almost_equal(vol, expected)


@patch("checkers.jacobian.MESHIO_AVAILABLE", False)
def test_check_mesh_quality_fallback(tmp_path):
    """Test fallback when meshio is not available."""
    mesh_path = tmp_path / "model.inp"
    mesh_path.write_text("Hello mesh")
    
    # Passing mock
    res = check_mesh_quality(mesh_path)
    assert res["passed"] is True
    assert res["min_jacobian"] == 0.8
    
    # Failing mock
    mesh_path.write_text("BAD_JACOBIAN triggers fail mock")
    res2 = check_mesh_quality(mesh_path)
    assert res2["passed"] is False
    assert res2["min_jacobian"] == 0.05
    assert len(res2["findings"]) > 0


def test_check_mesh_quality_with_meshio_mock(tmp_path):
    """Test full evaluation using meshio on a mocked mesh."""
    
    # Create an ideal mesh mock
    mock_meshio = MagicMock()
    
    class MockMesh:
        def __init__(self):
            # 4 points for a standard regular tet (edge length 1.0 approx)
            self.points = np.array([
                [0, 0, 0],
                [1, 0, 0],
                [0.5, np.sqrt(3)/2, 0],
                [0.5, np.sqrt(3)/6, np.sqrt(2/3)]
            ])
            
            # 1 tetra cell
            class MockCellBlock:
                type = "tetra"
                data = np.array([[0, 1, 2, 3]])
            self.cells = [MockCellBlock()]
            
    mock_meshio.read.return_value = MockMesh()
    
    mesh_path = tmp_path / "model.inp"
    mesh_path.touch()
    
    with patch.dict('sys.modules', {'meshio': mock_meshio}):
        with patch('checkers.jacobian.MESHIO_AVAILABLE', True):
            import checkers.jacobian as jac
            jac.meshio = mock_meshio
            
            res = jac.check_mesh_quality(mesh_path, thresholds={"min_jacobian": 0.5})
            
            # Since it's a regular tet, Jacobian should be 1.0, AR should be 1.0
            assert res["passed"] is True
            np.testing.assert_almost_equal(res["min_jacobian"], 1.0)
            np.testing.assert_almost_equal(res["max_aspect_ratio"], 1.0)
            assert res["degenerate_pct"] == 0.0


def test_check_mesh_quality_degenerate_and_skewed(tmp_path):
    """Test evaluation on bad elements to ensure detection works."""
    mock_meshio = MagicMock()
    
    class MockBadMesh:
        def __init__(self):
            # Points for a flat tet (z=0 for all) -> degenerate
            self.points = np.array([
                [0, 0, 0],
                [1, 0, 0],
                [0, 1, 0],
                [1, 1, 0] # Coplanar!
            ])
            
            class MockCellBlock:
                type = "tetra"
                data = np.array([[0, 1, 2, 3]])
            self.cells = [MockCellBlock()]
            
    mock_meshio.read.return_value = MockBadMesh()
    
    mesh_path = tmp_path / "model.inp"
    mesh_path.touch()
    
    with patch.dict('sys.modules', {'meshio': mock_meshio}):
        with patch('checkers.jacobian.MESHIO_AVAILABLE', True):
            import checkers.jacobian as jac
            jac.meshio = mock_meshio
            
            res = jac.check_mesh_quality(mesh_path)
            
            assert res["passed"] is False
            np.testing.assert_almost_equal(res["min_jacobian"], 0.0)
            assert len(res["findings"]) > 0
