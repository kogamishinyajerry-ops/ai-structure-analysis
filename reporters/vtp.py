"""VTP (VTK PolyData) exporter for ParaView visualization.

Converts parsed FRD nodal/elemental data into VTP files
that can be opened in ParaView for interactive 3-D exploration.

This module is a stub (AI-FEA-P0-01).  Logic will be filled in P0-09.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def export_vtp(results: dict[str, Any], output_dir: Path) -> Path:
    """Export FEA results as a VTP file.

    Parameters
    ----------
    results : dict
        Parsed FRD data (nodes, elements, fields).
    output_dir : Path
        Directory to write the VTP file into.

    Returns
    -------
    Path
        Path to the generated ``.vtp`` file.
    """
    raise NotImplementedError("VTP exporter not yet implemented — see AI-FEA-P0-09")
