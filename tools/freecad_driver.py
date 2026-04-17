from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any

# We will handle FreeCAD import softly to allow local testing
try:
    import FreeCAD  # type: ignore
    import Part  # type: ignore

    FREECAD_AVAILABLE = True
except ImportError:
    FREECAD_AVAILABLE = False

logger = logging.getLogger(__name__)


def parse_naca_4digit(profile: str) -> tuple[float, float, float]:
    """Parse a string like 'NACA0012' into (m, p, t) parameters."""
    profile = profile.strip().upper()
    if not profile.startswith("NACA") or len(profile) != 8:
        raise ValueError(f"Invalid NACA 4-digit profile: {profile}")

    digits = profile[4:]
    if not digits.isdigit():
        raise ValueError(f"NACA profile must contain 4 digits, got: {profile}")

    m = int(digits[0]) / 100.0
    p = int(digits[1]) / 10.0
    t = int(digits[2:4]) / 100.0

    return m, p, t


def generate_naca_points(
    m: float, p: float, t: float, chord: float, num_points: int = 100
) -> list[tuple[float, float, float]]:
    """Generate ordered 3D points (Z=0) for a NACA 4-digit airfoil profile.

    Points start from trailing edge, go along upper surface to leading edge,
    then back along lower surface to trailing edge.
    """
    beta = [i * math.pi / num_points for i in range(num_points + 1)]
    # Use cosine spacing to put more points near leading and trailing edges
    x_c = [(1 - math.cos(b)) / 2.0 for b in beta]

    upper_points = []
    lower_points = []

    for x in x_c:
        # Thickness distribution (standard equation, exact TE closure optionally adjusted, here standard)
        yt = (
            5
            * t
            * (0.2969 * math.sqrt(x) - 0.1260 * x - 0.3516 * x**2 + 0.2843 * x**3 - 0.1036 * x**4)
        )
        # Note: 0.1015 gives exact TE=0, 0.1036 gives open TE which is more standard physically.
        # We will use 0.1036 for standard NACA. We ensure it's closed manually later.

        # Camber line
        if x < p:
            if p > 0:
                yc = (m / p**2) * (2 * p * x - x**2)
                dyc_dx = (2 * m / p**2) * (p - x)
            else:
                yc = 0.0
                dyc_dx = 0.0
        else:
            if 1 - p > 0:
                yc = (m / (1 - p) ** 2) * ((1 - 2 * p) + 2 * p * x - x**2)
                dyc_dx = (2 * m / (1 - p) ** 2) * (p - x)
            else:
                yc = 0.0
                dyc_dx = 0.0

        theta = math.atan(dyc_dx)

        xu = (x - yt * math.sin(theta)) * chord
        yu = (yc + yt * math.cos(theta)) * chord
        xl = (x + yt * math.sin(theta)) * chord
        yl = (yc - yt * math.cos(theta)) * chord

        upper_points.append(FreeCAD.Vector(xu, yu, 0.0) if FREECAD_AVAILABLE else (xu, yu, 0.0))
        lower_points.append(FreeCAD.Vector(xl, yl, 0.0) if FREECAD_AVAILABLE else (xl, yl, 0.0))

    # Combine: trailing edge to leading edge (upper)
    upper_points.reverse()
    pts = upper_points + lower_points[1:]  # avoid duplicating leading edge (x=0)

    # Close trailing edge
    if FREECAD_AVAILABLE:
        pts[-1] = pts[0]
    else:
        pts[-1] = pts[0]

    return pts


def create_topology_mapping(solid: Any) -> list[dict]:
    """Extract face identifiers and map to semantics based on geometric bounds.

    Assumes extrude performed along Z axis.
    Root: Face with min Z center
    Tip: Face with max Z center
    Skin: All other faces
    """
    if not hasattr(solid, "Faces"):
        return []

    topo_map = {}
    z_centers = []

    for idx, face in enumerate(solid.Faces):
        # Calculate bounding box center
        bb = face.BoundBox
        z_c = (bb.ZMin + bb.ZMax) / 2.0
        z_centers.append((idx + 1, z_c, face))

    if not z_centers:
        return []

    # Sort by Z
    z_centers.sort(key=lambda item: item[1])

    # Lowest Z is fixed root
    root_idx = z_centers[0][0]
    # Highest Z is tip
    tip_idx = z_centers[-1][0]

    topo_map["fixed_root"] = [f"Face{root_idx}"]
    topo_map["tip"] = [f"Face{tip_idx}"]
    topo_map["skin"] = [
        f"Face{item[0]}" for item in z_centers if item[0] not in (root_idx, tip_idx)
    ]

    return [topo_map]


def generate_geometry(spec: dict[str, Any], output_dir: Path) -> Path:
    """Generate CAD geometry from a specification dict.

    Parameters
    ----------
    spec : dict
        Geometry specification from SimPlan (requires 'profile', 'chord_length', 'span').
    output_dir : Path
        Directory to write the STEP file into.

    Returns
    -------
    Path
        Path to the generated STEP file.
    """
    if not FREECAD_AVAILABLE:
        logger.warning(
            "FreeCAD is not available in the environment. Mocks must be used or it will fail."
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    profile = spec.get("profile", "NACA0012")
    chord_length = float(spec.get("chord_length", 1.0))
    span = float(spec.get("span", 1.0))

    m, p, t = parse_naca_4digit(profile)
    points = generate_naca_points(m, p, t, chord_length)

    fcstd_path = output_dir / "model.FCStd"
    step_path = output_dir / "model.step"
    topo_path = output_dir / "topo_map.json"

    if FREECAD_AVAILABLE:
        # Create a new document in memory
        doc = FreeCAD.newDocument("NacaProfile")

        # Build 3D Shape
        polygon = Part.makePolygon(points)
        face = Part.Face(polygon)

        # Extrude along Z
        solid = face.extrude(FreeCAD.Vector(0, 0, span))

        # Bind solid to document feature
        part_feature = doc.addObject("Part::Feature", "Wing")
        part_feature.Shape = solid

        # Export logic
        Part.export([part_feature], str(step_path))
        doc.saveAs(str(fcstd_path))

        topo_data = create_topology_mapping(solid)

        # Cleanup
        FreeCAD.closeDocument("NacaProfile")
    else:
        # In a test environment without FreeCAD we write dummy files
        fcstd_path.write_text("Dummy FCStd")
        step_path.write_text("Dummy STEP")
        topo_data = [{"fixed_root": ["Face1"], "tip": ["Face3"], "skin": ["Face2", "Face4"]}]

    # Write topology map
    with open(topo_path, "w", encoding="utf-8") as f:
        json.dump(topo_data, f, indent=2)

    return step_path
