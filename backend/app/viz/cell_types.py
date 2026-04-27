"""CalculiX → VTK cell-type map for the viz pipeline.

CalculiX writes element types as short codes (``C3D4``, ``C3D8R``, ``S4``, ...)
in the `.frd` 4E header. VTK / pyvista need an integer cell-type code per
cell. This map covers the element types that appear in the W5 wedge's
golden samples plus a small fringe (shells, beams) for forward-compat.

Element-type codes documented at
https://abaqus-docs.mit.edu/2017/English/SIMACAEELMRefMap/simaelm-r-elementlibrary.htm
and CalculiX manual §6 (compatibility-with-Abaqus subset).

Anything not in this table renders as a missing cell — the viz module
logs a one-line warning to stderr and skips it. We deliberately do NOT
silently degrade an unknown element to a crude approximation; that
would mask a parser bug and produce a misleading colormap.
"""

from __future__ import annotations

# VTK cell type integers (vtkCellType.h). Hardcoded to avoid pulling
# the vtk module into this file's import surface — the renderer
# imports vtk lazily.
_VTK_LINE = 3
_VTK_TRIANGLE = 5
_VTK_QUAD = 9
_VTK_TETRA = 10
_VTK_HEXAHEDRON = 12
_VTK_WEDGE = 13
_VTK_PYRAMID = 14
_VTK_QUADRATIC_EDGE = 21
_VTK_QUADRATIC_TRIANGLE = 22
_VTK_QUADRATIC_QUAD = 23
_VTK_QUADRATIC_TETRA = 24
_VTK_QUADRATIC_HEXAHEDRON = 25
_VTK_QUADRATIC_WEDGE = 26


# (vtk_type, n_nodes_in_connectivity)
#
# CalculiX `.frd` files use TWO conventions for element type, depending
# on the writer:
#   * Numeric codes 1..12 (the raw integer that goes in the 4E header
#     of binary frd; GS-001 fixture uses these). The parser surfaces
#     them as decimal strings.
#   * Abaqus-style stems ("C3D8R", "S4", "B31"). Newer text-mode .frd
#     files emit these.
# We map both.
CALCULIX_TO_VTK: dict[str, tuple[int, int]] = {
    # Numeric .frd codes (CalculiX manual §6.6 / Abaqus 1971-1981 ref)
    "1": (_VTK_HEXAHEDRON, 8),  # 8-node hex (HEX8 / C3D8)
    "2": (_VTK_QUADRATIC_HEXAHEDRON, 20),  # 20-node hex (C3D20)
    "3": (_VTK_TETRA, 4),  # 4-node tet (C3D4)
    "4": (_VTK_QUADRATIC_TETRA, 10),  # 10-node tet (C3D10)
    "5": (_VTK_WEDGE, 6),  # 6-node wedge (C3D6)
    "6": (_VTK_QUADRATIC_WEDGE, 15),  # 15-node wedge (C3D15)
    "7": (_VTK_TRIANGLE, 3),  # 3-node tri shell (S3 / CPS3)
    "8": (_VTK_QUADRATIC_TRIANGLE, 6),  # 6-node tri shell (S6)
    "9": (_VTK_QUAD, 4),  # 4-node quad shell (S4 / CPS4)
    "10": (_VTK_QUADRATIC_QUAD, 8),  # 8-node quad shell (S8)
    "11": (_VTK_LINE, 2),  # 2-node beam (B31)
    "12": (_VTK_QUADRATIC_EDGE, 3),  # 3-node beam (B32)

    # Abaqus-style stems
    # Solid 3D — linear
    "C3D4": (_VTK_TETRA, 4),
    "C3D8": (_VTK_HEXAHEDRON, 8),
    "C3D8R": (_VTK_HEXAHEDRON, 8),  # reduced integration; same connectivity
    "C3D8I": (_VTK_HEXAHEDRON, 8),
    "C3D6": (_VTK_WEDGE, 6),
    "C3D5": (_VTK_PYRAMID, 5),
    # Solid 3D — quadratic
    "C3D10": (_VTK_QUADRATIC_TETRA, 10),
    "C3D10T": (_VTK_QUADRATIC_TETRA, 10),
    "C3D20": (_VTK_QUADRATIC_HEXAHEDRON, 20),
    "C3D20R": (_VTK_QUADRATIC_HEXAHEDRON, 20),
    "C3D15": (_VTK_QUADRATIC_WEDGE, 15),
    # Shell — linear
    "S3": (_VTK_TRIANGLE, 3),
    "S3R": (_VTK_TRIANGLE, 3),
    "S4": (_VTK_QUAD, 4),
    "S4R": (_VTK_QUAD, 4),
    # Shell — quadratic
    "S6": (_VTK_QUADRATIC_TRIANGLE, 6),
    "S8": (_VTK_QUADRATIC_QUAD, 8),
    "S8R": (_VTK_QUADRATIC_QUAD, 8),
    # Beam
    "B31": (_VTK_LINE, 2),
    "B32": (_VTK_QUADRATIC_EDGE, 3),
    # Truss / spring (degenerate but valid as line)
    "T3D2": (_VTK_LINE, 2),
}


def vtk_type_for(calculix_type: str) -> tuple[int, int] | None:
    """Return ``(vtk_type, n_nodes)`` or ``None`` if the element is
    unsupported. Uses the bare type stem (e.g. ``C3D8R`` matches
    directly; an unknown ``C3D17`` returns ``None``)."""
    return CALCULIX_TO_VTK.get(calculix_type)
