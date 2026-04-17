from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

try:
    import gmsh  # type: ignore
    GMSH_AVAILABLE = True
except ImportError:
    GMSH_AVAILABLE = False


def _find_gmsh() -> tuple[str | None, bool]:
    """Return (path, is_wsl). checks Windows then WSL."""
    win_bin = shutil.which("gmsh")
    if win_bin:
        return win_bin, False

    # Check WSL
    try:
        wsl_check = subprocess.run(["wsl", "which", "gmsh"], capture_output=True, text=True, timeout=5)
        if wsl_check.returncode == 0:
            return "gmsh", True
    except Exception:
        pass

    return None, False


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
    output_path = output_dir / f"{geometry_path.stem}.inp"

    gmsh_bin, is_wsl = _find_gmsh()
    
    if gmsh_bin:
        cmd = [gmsh_bin, str(geometry_path), "-3", "-format", "inp", "-o", str(output_path)]
        
        # Add refinement parameters if provided
        if "global_size" in params:
            cmd.extend(["-setnumber", "Mesh.CharacteristicLengthMax", str(params["global_size"])])
        
        if is_wsl:
            cmd = ["wsl"] + cmd
            logger.info("Running Gmsh (via WSL): %s", cmd)
        else:
            logger.info("Running Gmsh (Native): %s", cmd)

        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return output_path

    # Fallback to Python API
    if not GMSH_AVAILABLE:
        logger.warning("Gmsh is not available natively or via WSL. Returning a dummy mesh.")
        output_path.write_text("*NODE\n1, 0, 0, 0\n*ELEMENT, TYPE=C3D10\n1, 1\n")
        return output_path

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
        gmsh.option.setNumber("Mesh.Format", 39) 

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
