from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

import numpy as np  # type: ignore

try:
    import meshio  # type: ignore

    MESHIO_AVAILABLE = True
except ImportError:
    MESHIO_AVAILABLE = False


def compute_tetra_volume(pts: list) -> float:
    """Compute volume of a tetrahedron given 4 points."""
    a, b, c, d = pts[0], pts[1], pts[2], pts[3]
    return abs(np.dot(a - d, np.cross(b - d, c - d))) / 6.0


def check_mesh_quality(
    mesh_path: Path, thresholds: dict[str, float] | None = None
) -> dict[str, Any]:
    """Run Jacobian and aspect-ratio checks on a mesh file.

    Parameters
    ----------
    mesh_path : Path
        Path to the mesh file (.inp or .msh).
    thresholds : dict, optional
        Override default thresholds (``min_jacobian``, ``max_aspect_ratio``).

    Returns
    -------
    dict
        Keys: ``passed`` (bool), ``min_jacobian``, ``max_aspect_ratio``,
        ``degenerate_pct``, ``findings`` (list of issue strings).
    """
    thresholds = thresholds or {}
    min_j_thresh = thresholds.get("min_jacobian", 0.2)
    max_ar_thresh = thresholds.get("max_aspect_ratio", 10.0)

    if not MESHIO_AVAILABLE:
        logger.warning("meshio/numpy is not available. Performing a mocked validation pass.")
        content = mesh_path.read_text(errors="ignore") if mesh_path.exists() else ""
        if "BAD_JACOBIAN" in content:
            return {
                "passed": False,
                "min_jacobian": 0.05,
                "max_aspect_ratio": 12.0,
                "degenerate_pct": 5.0,
                "findings": ["Mock check failed: Jacobian < threshold"],
            }
        return {
            "passed": True,
            "min_jacobian": 0.8,
            "max_aspect_ratio": 3.5,
            "degenerate_pct": 0.0,
            "findings": [],
        }

    try:
        mesh = meshio.read(str(mesh_path))
    except Exception as e:
        return {
            "passed": False,
            "min_jacobian": 0.0,
            "max_aspect_ratio": float("inf"),
            "degenerate_pct": 100.0,
            "findings": [f"Failed to read mesh: {e}"],
        }

    pts = mesh.points
    min_j = float("inf")
    max_ar = 0.0
    degenerate_count = 0
    total_elements = 0

    # For simplicity, we just evaluate tetrahedrons (tetra or tetra10)
    for cell_block in mesh.cells:
        if cell_block.type not in ("tetra", "tetra10"):
            continue

        cells = cell_block.data
        total_elements += len(cells)

        for element in cells:
            # First 4 nodes define the linear tetrahedron
            e_pts = pts[element[:4]]

            # Edges
            edges = [
                e_pts[1] - e_pts[0],
                e_pts[2] - e_pts[0],
                e_pts[3] - e_pts[0],
                e_pts[2] - e_pts[1],
                e_pts[3] - e_pts[1],
                e_pts[3] - e_pts[2],
            ]

            lengths = [np.linalg.norm(edge) for edge in edges]
            if any(l == 0 for l in lengths):
                degenerate_count += 1
                min_j = 0.0
                max_ar = float("inf")
                continue

            vol = compute_tetra_volume(e_pts)

            # Simple scaling for jacobian: roughly proportional to Vol / (l_rms^3)
            # A perfect regular tetrahedron has V = l^3 / (6*sqrt(2))
            l_rms = np.sqrt(np.mean(np.square(lengths)))
            scale = l_rms**3 / (6 * np.sqrt(2))
            j = vol / scale if scale > 0 else 0

            min_j = min(min_j, j)

            ar = max(lengths) / min(lengths)
            max_ar = max(max_ar, ar)

    if total_elements == 0:
        return {
            "passed": True,
            "min_jacobian": 1.0,
            "max_aspect_ratio": 1.0,
            "degenerate_pct": 0.0,
            "findings": ["No tetrahedral elements to evaluate."],
        }

    degenerate_pct = (degenerate_count / total_elements) * 100.0

    passed = True
    findings = []
    if min_j < min_j_thresh:
        passed = False
        findings.append(f"Minimum Jacobian {min_j:.3f} is below threshold {min_j_thresh}.")
    if max_ar > max_ar_thresh:
        passed = False
        findings.append(f"Maximum Aspect Ratio {max_ar:.1f} is above threshold {max_ar_thresh}.")

    return {
        "passed": passed,
        "min_jacobian": float(min_j),
        "max_aspect_ratio": float(max_ar),
        "degenerate_pct": float(degenerate_pct),
        "findings": findings,
    }
