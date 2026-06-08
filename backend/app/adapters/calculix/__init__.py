"""CalculiX (.frd) Layer-1 adapter.

* ``CalculiXReader`` — RFC-001 §4.5 W2 ``ReaderHandle`` over ``.frd``
  result files. ADR-001/003/004 enforced: no derived quantities, no
  UNIT inference, no IO caching at this layer.
* ``CalculiXRunner`` — FM-04a Phase 18 A subprocess runner that
  invokes the real ``ccx`` binary on a ``case_dir/<jobname>.inp``
  and returns paths to the produced ``.frd`` + ``.dat`` artifacts.
  The runner is paired with ``CalculiXReader`` (runner produces the
  ``.frd``; reader parses it).
* ``inp_writer`` — Phase 18 A minimal-hex INP writer for smoke runs.
"""

from .inp_writer import (
    DEFAULT_STEEL,
    MinimalHexMaterial,
    write_minimal_hex_inp,
    write_modal_hex_inp,
)
# FM-04a Phase 20 C — Gmsh .msh → CalculiX INP adapter; bridges the
# orphaned Phase 18 C GmshRunner into the Tier 2 pipeline so meshed
# CAD geometries become solvable end-to-end.
from .mesh_to_inp import (
    BoundaryConditionSpec,
    LoadSpec,
    MeshParseError,
    ParsedMesh,
    PlanarSelection,
    parse_gmsh_msh22,
    write_meshed_static_inp,
)
from .reader import CalculiXReader
from .runner import (
    DEFAULT_CCX_BINARY,
    DEFAULT_TIMEOUT_SEC,
    CalculiXRunError,
    CalculiXRunner,
    CalculiXRunResult,
)

__all__ = [
    "CalculiXReader",
    "CalculiXRunner",
    "CalculiXRunResult",
    "CalculiXRunError",
    "DEFAULT_CCX_BINARY",
    "DEFAULT_TIMEOUT_SEC",
    "DEFAULT_STEEL",
    "MinimalHexMaterial",
    "write_minimal_hex_inp",
    "write_modal_hex_inp",
    "BoundaryConditionSpec",
    "LoadSpec",
    "MeshParseError",
    "ParsedMesh",
    "PlanarSelection",
    "parse_gmsh_msh22",
    "write_meshed_static_inp",
]
