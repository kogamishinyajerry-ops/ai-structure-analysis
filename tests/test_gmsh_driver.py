from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from tools.gmsh_driver import generate_mesh


@patch("tools.gmsh_driver.GMSH_AVAILABLE", False)
def test_generate_mesh_fallback(tmp_path):
    """Test standard graceful degradation when Gmsh is not in environment."""
    geom_path = tmp_path / "model.step"
    geom_path.write_text("Dummy STEP")
    
    params = {"global_size": 1.0}
    
    out_path = generate_mesh(geom_path, params, tmp_path)
    
    assert out_path.exists()
    assert out_path.name == "model.inp"
    # Fallback mesh should be a dummy string
    assert "C3D10" in out_path.read_text()


def test_generate_mesh_with_gmsh_mocks(tmp_path):
    """Test full Gmsh invocation via mocks."""
    
    mock_gmsh = MagicMock()
    
    # Let's mock gmsh structure
    mock_option = MagicMock()
    mock_model = MagicMock()
    mock_mesh = MagicMock()
    
    mock_gmsh.option = mock_option
    mock_gmsh.model = mock_model
    mock_model.mesh = mock_mesh
    
    geom_path = tmp_path / "model.step"
    geom_path.write_text("Dummy STEP")
    
    with patch.dict('sys.modules', {'gmsh': mock_gmsh}):
        with patch('tools.gmsh_driver.GMSH_AVAILABLE', True):
            # Patch module-level gmsh reference
            import tools.gmsh_driver as drv
            drv.gmsh = mock_gmsh
            
            params = {
                "global_size": 2.0,
                "refinement_multiplier": 0.5,
                "element_order": "linear"
            }
            
            # The target_size will be 2.0 * 0.5 = 1.0
            
            out_path = drv.generate_mesh(geom_path, params, tmp_path)
            
            assert out_path.name == "model.inp"
            
            mock_gmsh.initialize.assert_called_once()
            mock_gmsh.merge.assert_called_with(str(geom_path))
            
            # Verify options set
            mock_option.setNumber.assert_any_call("Mesh.MeshSizeMin", 0.5)
            mock_option.setNumber.assert_any_call("Mesh.MeshSizeMax", 1.0)
            mock_option.setNumber.assert_any_call("Mesh.ElementOrder", 1)
            mock_option.setNumber.assert_any_call("Mesh.Format", 39)
            
            mock_mesh.generate.assert_called_with(3)
            
            # Expected write
            mock_gmsh.write.assert_called_with(str(out_path))
            mock_gmsh.finalize.assert_called_once()
