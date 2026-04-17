from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

try:
    import gmsh  # type: ignore
    GMSH_AVAILABLE = True
except ImportError:
    GMSH_AVAILABLE = False


def generate_mesh(geometry_path: Path, params: dict[str, Any], output_dir: Path) -> Path:
    """Generate a finite-element mesh from a STEP geometry file.

    Parameters
    ----------
    geometry_path : Path
        Path to the input STEP/BREP file.
    params : dict
        Meshing parameters (element size, refinement fields, element order).
    output_dir : Path
        Directory to write the mesh file into.

    Returns
    -------
    Path
        Path to the generated mesh file (.inp).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "model.inp"

    if not GMSH_AVAILABLE:
        logger.warning("Gmsh is not available natively. Returning a dummy mesh.")
        out_path.write_text("*NODE\n1, 0, 0, 0\n*ELEMENT, TYPE=C3D10\n1, 1\n")
        return out_path

    # Extract refinement params
    base_size = params.get("global_size", 1.0)
    refinement_multiplier = params.get("refinement_multiplier", 1.0)
    target_size = base_size * refinement_multiplier
    element_order = 2 if params.get("element_order", "quadratic") == "quadratic" else 1

    try:
        gmsh.initialize()
        gmsh.option.setNumber("General.Terminal", 0)
        
        # Load geometry
        gmsh.merge(str(geometry_path))
        
        # Determine global sizes
        gmsh.option.setNumber("Mesh.MeshSizeMin", target_size * 0.5)
        gmsh.option.setNumber("Mesh.MeshSizeMax", target_size)
        
        # If quadratic elements are requested
        gmsh.option.setNumber("Mesh.ElementOrder", element_order)
        # Abaqus/CalculiX format specific configurations
        gmsh.option.setNumber("Mesh.Format", 39) # 39 often corresponds to INP format, gmsh.write handles this natively via extension

        # We assume 3D geometry meshing
        gmsh.model.mesh.generate(3)
        
        if element_order == 2:
            gmsh.model.mesh.setOrder(2)
            
        gmsh.write(str(out_path))

    except Exception as e:
        logger.error(f"Gmsh meshing failed: {e}")
        raise
    finally:
        if GMSH_AVAILABLE:
            gmsh.finalize()

    return out_path
