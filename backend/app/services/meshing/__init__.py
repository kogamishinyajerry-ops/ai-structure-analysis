"""Meshing service — FM-04a Phase 18 C.

Minimal subprocess wrapper over the ``gmsh`` CLI. Phase 18 C target:
generate a linear-tet mesh from a STEP/STL/BREP input within a case
workspace, producing a CalculiX-compatible mesh on disk.

The runner refuses paths outside the case workspace (path-guard
defense in depth) and enforces a bounded timeout (so a runaway gmsh
invocation cannot wedge the calling process).

The runner does NOT compose with the materials library — that
composition happens at the INP-writer layer in Phase 18 C+ (planned
extension of :func:`app.adapters.calculix.inp_writer.write_minimal_hex_inp`
to consume a mesh + material spec).
"""

from .gmsh_runner import (
    DEFAULT_GMSH_BINARY,
    DEFAULT_TIMEOUT_SEC,
    DEFAULT_CHARACTERISTIC_LENGTH_M,
    GmshRunner,
    GmshRunError,
    GmshRunResult,
    MeshQualityHistogram,
)

__all__ = [
    "DEFAULT_GMSH_BINARY",
    "DEFAULT_TIMEOUT_SEC",
    "DEFAULT_CHARACTERISTIC_LENGTH_M",
    "GmshRunner",
    "GmshRunError",
    "GmshRunResult",
    "MeshQualityHistogram",
]
