"""Geometry validity checker.

Pre-mesh validation of CAD geometry:
  - Watertight / manifold check.
  - Minimum feature size detection.
  - Bounding-box sanity (units consistency).

This module is a stub (AI-FEA-P0-01).  Logic will be filled in P0-05.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REQUIRED_TOPOLOGY_KEYS = {"fixed_base", "tip_load", "skin"}


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
    findings: list[str] = []
    watertight = False
    manifold = False
    min_feature_size_m: float | None = None
    bounding_box_mm: list[float] | None = None

    if not step_path.exists():
        return {
            "valid": False,
            "watertight": False,
            "manifold": False,
            "min_feature_size_m": None,
            "bounding_box_mm": None,
            "findings": ["missing_step_file"],
        }

    if step_path.stat().st_size <= 0:
        findings.append("empty_step_file")

    topo_map_path = step_path.with_name("topo_map.json")
    geometry_meta_path = step_path.with_name("geometry_meta.json")

    topo_data: list[dict[str, Any]] = []
    if topo_map_path.exists():
        topo_data = json.loads(topo_map_path.read_text(encoding="utf-8"))
    else:
        findings.append("missing_topology_map")

    if not topo_data:
        findings.append("empty_topology_map")
    else:
        topology_keys = set(topo_data[0].keys())
        missing_keys = REQUIRED_TOPOLOGY_KEYS - topology_keys
        if missing_keys:
            findings.append("missing_topology_keys:" + ",".join(sorted(missing_keys)))

    volume_m3 = 0.0
    if geometry_meta_path.exists():
        geometry_meta = json.loads(geometry_meta_path.read_text(encoding="utf-8"))
        watertight = bool(geometry_meta.get("watertight", False))
        manifold = bool(geometry_meta.get("manifold", False))
        volume_m3 = float(geometry_meta.get("volume_m3", 0.0) or 0.0)
        min_feature_size_m = geometry_meta.get("min_feature_size_m")
        bounding_box_mm = geometry_meta.get("bounding_box_mm")
    else:
        findings.append("missing_geometry_meta")

    if not watertight:
        findings.append("non_watertight_geometry")
    if not manifold:
        findings.append("non_manifold_geometry")
    if volume_m3 <= 0.0:
        findings.append("zero_volume_geometry")

    return {
        "valid": not findings,
        "watertight": watertight,
        "manifold": manifold,
        "min_feature_size_m": min_feature_size_m,
        "bounding_box_mm": bounding_box_mm,
        "findings": findings,
    }
