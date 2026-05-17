"""Gmsh `.msh v2.2 ASCII` → CalculiX INP adapter — Phase 20 C.

Parses a gmsh-produced ASCII mesh file (the canonical Phase 18 C
GmshRunner output) into nodes + C3D4 (linear-tet) elements, then
composes a CalculiX-friendly INP body with material, boundary
conditions (clamp-by-plane), and load (force-on-plane) specifications.

This adapter is what bridges the Phase 18 C orphaned `GmshRunner` into
the Phase 19 A `tier2_pipeline` — until Phase 20 C, the Tier 2 pipeline
was single-element-coupon bound. With this module, real CAD geometry
can be meshed by Gmsh and solved by ccx end-to-end.

**Scope honesty (Phase 20 C):**
* Linear tetrahedra (gmsh type 4 / CalculiX C3D4) only. Quadratic tets
  (gmsh type 11 / C3D10) would give much better stress accuracy but
  add parsing complexity; deferred to Phase 21.
* BC + load specs use planar selection by coordinate threshold
  (``"all nodes with x < ε" → clamped``). This avoids depending on
  gmsh Physical Groups, which would couple the adapter to .geo-file
  conventions that vary across CAD authors.
* The INP step is linear static only. Modal / buckling on meshed
  geometry is Phase 21+ scope.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .inp_writer import MinimalHexMaterial

# Gmsh element type → number of nodes per element + CalculiX type label.
# Phase 20 C wires C3D4 only; the table is here so a future Phase
# extending to C3D10 / C3D8 / S4 just edits one place.
_GMSH_TYPE_TO_CCX: dict[int, tuple[str, int]] = {
    4: ("C3D4", 4),  # 4-node linear tetrahedron
}

Axis = Literal["x", "y", "z"]


@dataclass(frozen=True)
class PlanarSelection:
    """Select nodes near a coordinate plane (``axis = value ± tol``).

    Attributes:
        axis: which axis ("x", "y", or "z") the selection plane is
            perpendicular to.
        value_m: coordinate value of the selection plane in meters.
        tol_m: half-width of the selection band in meters. Nodes with
            ``abs(coord[axis] - value_m) <= tol_m`` are included.
    """

    axis: Axis
    value_m: float
    tol_m: float = 1e-6


@dataclass(frozen=True)
class BoundaryConditionSpec:
    """Clamp-by-plane boundary condition.

    All nodes selected by ``plane`` are fixed in the specified DOFs
    (default: all three translational DOFs, i.e. full clamp).
    """

    plane: PlanarSelection
    dof_low: int = 1
    dof_high: int = 3


@dataclass(frozen=True)
class LoadSpec:
    """Force-on-plane load specification.

    The ``total_force_n`` is split equally across the nodes selected by
    ``plane`` and applied as a nodal load in DOF ``dof`` (1=x, 2=y,
    3=z).
    """

    plane: PlanarSelection
    dof: int
    total_force_n: float


@dataclass(frozen=True)
class ParsedMesh:
    """Outcome of parsing a gmsh ASCII .msh v2.2 file.

    Attributes:
        nodes: ordered dict-like mapping node_id → (x, y, z). The keys
            are 1-based as gmsh emits them; preserved verbatim so the
            INP element rows can reference them without renumbering.
        elements: list of ``(elem_id, ccx_type, [node_ids...])`` rows
            for every supported volume element type.
    """

    nodes: dict[int, tuple[float, float, float]]
    elements: list[tuple[int, str, list[int]]]


class MeshParseError(ValueError):
    """Raised when the `.msh` file cannot be parsed (malformed header,
    unsupported version, no volume elements found)."""


def parse_gmsh_msh22(msh_path: Path) -> ParsedMesh:
    """Parse a gmsh ASCII `.msh` file (version 2.2).

    Args:
        msh_path: absolute path to the `.msh` file.

    Returns:
        :class:`ParsedMesh` with nodes + volume elements.

    Raises:
        FileNotFoundError: if the file does not exist.
        MeshParseError: on malformed header, wrong version, or zero
            volume elements (gmsh produced surface mesh only).
    """
    if not msh_path.is_file():
        raise FileNotFoundError(f"mesh file {msh_path!s} not found")
    text = msh_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    # Header parse: $MeshFormat → version + file_type + data_size
    if not lines or lines[0].strip() != "$MeshFormat":
        first_line = lines[0] if lines else "<empty>"
        raise MeshParseError(
            f"{msh_path}: missing $MeshFormat header (got "
            f"{first_line!r}); Phase 20 C expects gmsh ASCII v2.2"
        )
    fmt_parts = lines[1].split()
    if not fmt_parts or not fmt_parts[0].startswith("2.2"):
        raise MeshParseError(
            f"{msh_path}: unsupported mesh version {lines[1]!r}; "
            f"Phase 20 C requires version 2.2 ASCII (pass `-format "
            f"msh22` to gmsh)"
        )
    if len(fmt_parts) > 1 and fmt_parts[1] != "0":
        raise MeshParseError(
            f"{msh_path}: binary .msh refused; need ASCII (-format "
            f"msh22)"
        )

    # Section index — find $Nodes / $EndNodes / $Elements / $EndElements.
    def _find(tag: str, start: int = 0) -> int:
        for i in range(start, len(lines)):
            if lines[i].strip() == tag:
                return i
        raise MeshParseError(f"{msh_path}: missing section {tag!r}")

    nodes_start = _find("$Nodes")
    nodes_end = _find("$EndNodes", nodes_start + 1)
    elements_start = _find("$Elements", nodes_end + 1)
    elements_end = _find("$EndElements", elements_start + 1)

    # $Nodes block: <count> then <id> <x> <y> <z> rows.
    n_nodes = int(lines[nodes_start + 1].strip())
    nodes: dict[int, tuple[float, float, float]] = {}
    for i in range(nodes_start + 2, nodes_end):
        parts = lines[i].split()
        if len(parts) < 4:
            continue
        nid = int(parts[0])
        x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
        nodes[nid] = (x, y, z)
    if len(nodes) != n_nodes:
        raise MeshParseError(
            f"{msh_path}: node count mismatch (header says {n_nodes}, "
            f"parsed {len(nodes)})"
        )

    # $Elements block: <count> then <id> <type> <n_tags> <tags...>
    # <node_ids...> rows. We filter to supported volume types only;
    # surface elements (gmsh type 2 = 3-node triangle) come along for
    # the ride in 3D meshes but aren't part of the INP body.
    elements: list[tuple[int, str, list[int]]] = []
    for i in range(elements_start + 2, elements_end):
        parts = lines[i].split()
        if len(parts) < 4:
            continue
        elem_id = int(parts[0])
        gmsh_type = int(parts[1])
        n_tags = int(parts[2])
        if gmsh_type not in _GMSH_TYPE_TO_CCX:
            continue  # skip unsupported (surface tris, points, …)
        ccx_type, node_count = _GMSH_TYPE_TO_CCX[gmsh_type]
        node_ids_start = 3 + n_tags
        node_ids = [
            int(parts[node_ids_start + k])
            for k in range(node_count)
        ]
        elements.append((elem_id, ccx_type, node_ids))

    if not elements:
        raise MeshParseError(
            f"{msh_path}: no supported volume elements (C3D4) found; "
            f"check that gmsh ran with `-3` (3D meshing) and the "
            f"geometry has a closed volume"
        )

    return ParsedMesh(nodes=nodes, elements=elements)


def _select_nodes_in_plane(
    nodes: dict[int, tuple[float, float, float]],
    plane: PlanarSelection,
) -> list[int]:
    """Return the list of node ids whose coordinate on ``plane.axis``
    is within ``plane.tol_m`` of ``plane.value_m``."""
    axis_idx = {"x": 0, "y": 1, "z": 2}[plane.axis]
    selected: list[int] = []
    for nid, coords in nodes.items():
        if abs(coords[axis_idx] - plane.value_m) <= plane.tol_m:
            selected.append(nid)
    return sorted(selected)


def write_meshed_static_inp(
    case_dir: Path,
    *,
    jobname: str,
    mesh: ParsedMesh,
    material: MinimalHexMaterial,
    bc: BoundaryConditionSpec,
    load: LoadSpec,
) -> Path:
    """Compose a CalculiX linear-static INP from a parsed mesh.

    Args:
        case_dir: workspace directory (must exist).
        jobname: INP filename stem; written as ``<case_dir>/<jobname>.inp``.
        mesh: result of :func:`parse_gmsh_msh22`.
        material: linear elastic (optionally with plastic hardening curve).
        bc: clamp specification by coordinate plane.
        load: force-on-plane specification.

    Returns:
        Absolute path to the written INP.

    Raises:
        ValueError: if BC or load plane selects zero nodes.
    """
    if not case_dir.is_dir():
        raise FileNotFoundError(
            f"case_dir {case_dir!s} must exist before writing INP"
        )

    clamped_nodes = _select_nodes_in_plane(mesh.nodes, bc.plane)
    loaded_nodes = _select_nodes_in_plane(mesh.nodes, load.plane)
    if not clamped_nodes:
        raise ValueError(
            f"BC plane (axis={bc.plane.axis}, value={bc.plane.value_m}, "
            f"tol={bc.plane.tol_m}) selected zero nodes; geometry / "
            f"plane parameters mismatch"
        )
    if not loaded_nodes:
        raise ValueError(
            f"Load plane (axis={load.plane.axis}, "
            f"value={load.plane.value_m}, tol={load.plane.tol_m}) "
            f"selected zero nodes; geometry / plane parameters mismatch"
        )
    load_per_node = load.total_force_n / float(len(loaded_nodes))

    lines: list[str] = []
    lines.append("*HEADING")
    lines.append(f"Phase 20 C meshed static run ({jobname})")
    lines.append("*NODE")
    for nid, (x, y, z) in mesh.nodes.items():
        lines.append(f"{nid}, {x:.6f}, {y:.6f}, {z:.6f}")
    # Group elements by ccx_type so the *ELEMENT block stays clean.
    # Phase 20 C only emits C3D4; the loop is future-proof for C3D10.
    by_type: dict[str, list[tuple[int, list[int]]]] = {}
    for elem_id, ccx_type, node_ids in mesh.elements:
        by_type.setdefault(ccx_type, []).append((elem_id, node_ids))
    for ccx_type, rows in by_type.items():
        lines.append(f"*ELEMENT, TYPE={ccx_type}, ELSET=EALL_{ccx_type}")
        for elem_id, node_ids in rows:
            lines.append(
                f"{elem_id}, " + ", ".join(str(n) for n in node_ids)
            )
    # Material + section.
    lines.append(f"*MATERIAL, NAME={material.name}")
    lines.append("*ELASTIC")
    lines.append(
        f"{material.youngs_modulus_pa:.6e}, "
        f"{material.poisson_ratio:.6f}"
    )
    if material.plastic_hardening_curve is not None:
        lines.append("*PLASTIC")
        for plastic_strain, stress_pa in material.plastic_hardening_curve:
            lines.append(f"{stress_pa:.6e}, {plastic_strain:.6f}")
    for ccx_type in by_type:
        lines.append(
            f"*SOLID SECTION, ELSET=EALL_{ccx_type}, "
            f"MATERIAL={material.name}"
        )
    # BC: clamp all selected nodes across the requested DOF range.
    # CalculiX caps *NSET rows at 16 entries; longer sets must wrap
    # across continuation rows under the same *NSET header.
    lines.append("*NSET, NSET=NCLAMP")
    _NSET_ROW_MAX = 16
    for chunk_start in range(0, len(clamped_nodes), _NSET_ROW_MAX):
        chunk = clamped_nodes[chunk_start : chunk_start + _NSET_ROW_MAX]
        lines.append(", ".join(str(n) for n in chunk))
    lines.append("*BOUNDARY")
    lines.append(f"NCLAMP, {bc.dof_low}, {bc.dof_high}, 0.0")
    # Step: linear static; nodal load applied to each loaded node.
    lines.append("*STEP")
    lines.append("*STATIC")
    lines.append("*CLOAD")
    for nid in loaded_nodes:
        lines.append(f"{nid}, {load.dof}, {load_per_node:.6f}")
    lines.append("*NODE FILE")
    lines.append("U")
    lines.append("*EL FILE")
    lines.append("S")
    lines.append("*END STEP")
    lines.append("")

    inp_path = case_dir / f"{jobname}.inp"
    inp_path.write_text("\n".join(lines), encoding="utf-8")
    return inp_path


__all__ = [
    "Axis",
    "PlanarSelection",
    "BoundaryConditionSpec",
    "LoadSpec",
    "ParsedMesh",
    "MeshParseError",
    "parse_gmsh_msh22",
    "write_meshed_static_inp",
]
