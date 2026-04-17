"""Geometry validity checker.

Pre-mesh validation of CAD geometry:
  - Watertight / manifold check.
  - Minimum feature size detection.
  - Bounding-box sanity (units consistency).

This module is a stub (AI-FEA-P0-01).  Logic will be filled in P0-05.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def check_geometry(step_path: Path) -> dict[str, Any]:
    """Validate a STEP geometry file for FEA readiness.

    Parameters
    ----------
    step_path : Path
        Path to the STEP/BREP file.

    Returns
    -------
    dict
        Keys: ``valid`` (bool), ``watertight``, ``manifold``,
        ``min_feature_size_m``, ``bounding_box_mm``, ``findings``.
    """
    raise NotImplementedError("Geometry checker not yet implemented — see AI-FEA-P0-05")
