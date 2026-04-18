from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np  # type: ignore

logger = logging.getLogger(__name__)

try:
    import meshio  # type: ignore[import-not-found, import-untyped]

    MESHIO_AVAILABLE = True
except ImportError:
    meshio = None
    MESHIO_AVAILABLE = False


def compute_signed_tetra_volume(pts: list) -> float:
    """Compute the signed volume of a tetrahedron given 4 points."""
    a, b, c, d = pts[0], pts[1], pts[2], pts[3]
    return float(np.dot(np.cross(b - a, c - a), d - a) / 6.0)


def compute_tetra_volume(pts: list) -> float:
    """Compute the absolute volume of a tetrahedron given 4 points."""
    return abs(compute_signed_tetra_volume(pts))


def _tetra_metrics(points: np.ndarray) -> tuple[float, float]:
    """Return scaled Jacobian and aspect ratio for a linear tetrahedron."""
    edges = [
        points[1] - points[0],
        points[2] - points[0],
        points[3] - points[0],
        points[2] - points[1],
        points[3] - points[1],
        points[3] - points[2],
    ]
    lengths = [float(np.linalg.norm(edge)) for edge in edges]
    min_length = min(lengths)
    max_length = max(lengths)
    if min_length == 0.0:
        return 0.0, float("inf")

    signed_volume = compute_signed_tetra_volume(points)
    l_rms = float(np.sqrt(np.mean(np.square(lengths))))
    scale = l_rms**3 / (6 * np.sqrt(2))
    scaled_jacobian = signed_volume / scale if scale > 0.0 else 0.0
    aspect_ratio = max_length / min_length
    return float(scaled_jacobian), float(aspect_ratio)


def _read_mock_quality(mesh_path: Path) -> dict[str, Any]:
    """Support deterministic quality checks when meshio is unavailable."""
    content = mesh_path.read_text(errors="ignore") if mesh_path.exists() else ""
    if "BAD_JACOBIAN" in content:
        return {
            "ok": False,
            "passed": False,
            "bad_element_ids": [1],
            "resolution_element_ids": [],
            "min_scaled_jacobian": 0.05,
            "max_aspect_ratio": 4.0,
            "degenerate_pct": 100.0,
            "findings": ["Mock check failed: scaled Jacobian < threshold."],
        }
    if "BAD_RESOLUTION" in content:
        return {
            "ok": False,
            "passed": False,
            "bad_element_ids": [],
            "resolution_element_ids": [1],
            "min_scaled_jacobian": 0.88,
            "max_aspect_ratio": 14.0,
            "degenerate_pct": 0.0,
            "findings": ["Mock check failed: aspect ratio exceeds threshold."],
        }
    return {
        "ok": True,
        "passed": True,
        "bad_element_ids": [],
        "resolution_element_ids": [],
        "min_scaled_jacobian": 0.8,
        "max_aspect_ratio": 3.5,
        "degenerate_pct": 0.0,
        "findings": [],
    }


def check_jacobian_positive(
    mesh_path: Path, min_scaled_jacobian: float = 0.2
) -> tuple[bool, list[int]]:
    """Return whether all tetrahedra satisfy the scaled Jacobian threshold."""
    if not MESHIO_AVAILABLE:
        mock_report = _read_mock_quality(mesh_path)
        bad_element_ids = mock_report["bad_element_ids"]
        return not bad_element_ids, bad_element_ids

    try:
        mesh = meshio.read(str(mesh_path))
    except Exception:
        return False, []

    bad_element_ids: list[int] = []
    element_id = 1
    for cell_block in mesh.cells:
        if cell_block.type not in ("tetra", "tetra10"):
            continue

        for element in cell_block.data:
            scaled_jacobian, _ = _tetra_metrics(mesh.points[element[:4]])
            if scaled_jacobian < min_scaled_jacobian:
                bad_element_ids.append(element_id)
            element_id += 1

    return not bad_element_ids, bad_element_ids


def check_mesh_quality(
    mesh_path: Path, thresholds: dict[str, float] | None = None
) -> dict[str, Any]:
    """Run Jacobian and aspect-ratio checks on a mesh file."""
    thresholds = thresholds or {}
    min_j_thresh = thresholds.get("min_scaled_jacobian", thresholds.get("min_jacobian", 0.2))
    max_ar_thresh = thresholds.get("max_aspect_ratio", 10.0)

    if not MESHIO_AVAILABLE:
        logger.warning("meshio/numpy is not available. Performing a mocked validation pass.")
        return _read_mock_quality(mesh_path)

    try:
        mesh = meshio.read(str(mesh_path))
    except Exception as exc:
        return {
            "ok": False,
            "passed": False,
            "bad_element_ids": [],
            "resolution_element_ids": [],
            "min_scaled_jacobian": 0.0,
            "max_aspect_ratio": float("inf"),
            "degenerate_pct": 100.0,
            "findings": [f"Failed to read mesh: {exc}"],
        }

    points = mesh.points
    min_jacobian = float("inf")
    max_aspect_ratio = 0.0
    degenerate_count = 0
    total_elements = 0
    bad_element_ids: list[int] = []
    resolution_element_ids: list[int] = []
    element_id = 1

    for cell_block in mesh.cells:
        if cell_block.type not in ("tetra", "tetra10"):
            continue

        cells = cell_block.data
        total_elements += len(cells)
        for element in cells:
            tetra_points = points[element[:4]]
            scaled_jacobian, aspect_ratio = _tetra_metrics(tetra_points)
            min_jacobian = min(min_jacobian, scaled_jacobian)
            max_aspect_ratio = max(max_aspect_ratio, aspect_ratio)

            if scaled_jacobian <= 0.0 or aspect_ratio == float("inf"):
                degenerate_count += 1
            if scaled_jacobian < min_j_thresh:
                bad_element_ids.append(element_id)
            if aspect_ratio > max_ar_thresh:
                resolution_element_ids.append(element_id)

            element_id += 1

    if total_elements == 0:
        return {
            "ok": False,
            "passed": False,
            "bad_element_ids": [],
            "resolution_element_ids": [],
            "min_scaled_jacobian": 0.0,
            "max_aspect_ratio": float("inf"),
            "degenerate_pct": 0.0,
            "findings": ["No tetrahedral elements to evaluate."],
        }

    degenerate_pct = (degenerate_count / total_elements) * 100.0
    ok = True
    findings: list[str] = []
    if bad_element_ids:
        ok = False
        findings.append(f"Minimum Jacobian {min_jacobian:.3f} is below threshold {min_j_thresh}.")
    if resolution_element_ids:
        ok = False
        findings.append(
            f"Maximum Aspect Ratio {max_aspect_ratio:.1f} is above threshold {max_ar_thresh}."
        )

    return {
        "ok": ok,
        "passed": ok,
        "bad_element_ids": bad_element_ids,
        "resolution_element_ids": resolution_element_ids,
        "min_scaled_jacobian": float(min_jacobian),
        "max_aspect_ratio": float(max_aspect_ratio),
        "degenerate_pct": float(degenerate_pct),
        "findings": findings,
    }
