"""Result-figure renderer — RFC-001 W5f viz tracking.

Renders three PNG figures from a CalculiX `.frd` parse result:
  * mesh outline (geometry only, no field) — the "case under construction" view
  * displacement field (deformed mesh, magnitude colormap)
  * von Mises field (deformed mesh, von_mises colormap)

The output is PNG-on-disk, deliberately. The Electron wedge needs raster
images to (a) stream into a renderer-side image gallery as each figure
is produced, and (b) embed in the final DOCX. A vtk.js / interactive
viewer is a separate scope (see ADR-016 — different audience, different
runtime model).

Off-screen rendering uses VTK's headless OS-Mesa path. On the
engineer's macOS dev shell this just works; on Linux CI we set
``PYVISTA_OFF_SCREEN=true`` so plotters don't try to open an X display.
The renderer never imports vtk / pyvista at module load — it imports
inside the public functions so a `--doctor` probe of `app.viz` doesn't
crash the report-cli on a half-installed graphics stack.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from .cell_types import vtk_type_for

if TYPE_CHECKING:  # pragma: no cover — type-only imports
    from ..parsers.frd_parser import FRDParseResult


# Figure shape — kept moderate so DOCX embedding doesn't bloat. 1280×900
# at 100 DPI ≈ 0.5 MB PNG, fits a Word page width comfortably.
_FIG_WINDOW_SIZE = (1280, 900)


def _ensure_off_screen() -> None:
    """Force off-screen mode before pyvista is imported. Setting the env
    var is documented to be the most reliable way; ``Plotter(off_screen=True)``
    is a per-call override that's racy with Plotter defaults on some
    platforms."""
    os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")


def _import_pyvista() -> "object":
    """Lazy-import pyvista. Same broken-submodule-survives-doctor reason
    as ``app.services.report.cli`` (W5c): pyvista pulls in vtk which
    pulls in OS GL libraries, and a half-installed wheel can crash the
    whole process at module load. Importing inside the function gives
    `--doctor` a chance to surface a clean diagnostic."""
    _ensure_off_screen()
    import pyvista as pv

    return pv


def build_grid(parsed: "FRDParseResult") -> "object":
    """Convert FRD parse result to a pyvista UnstructuredGrid.

    Builds a dense point array indexed by sorted node ID (matching the
    CalculiXReader convention — Layer-1 contract), and connectivity
    arrays per VTK conventions: ``cells`` is a flat array
    ``[n_pts_0, *pts_0, n_pts_1, *pts_1, ...]``, ``celltypes`` is one
    int per cell.

    Skips elements whose CalculiX type isn't in the cell-type map (logs
    one stderr warning per unique skipped type, deliberately — silent
    skip would mask a parser bug).
    """
    pv = _import_pyvista()

    sorted_ids = sorted(parsed.nodes.keys())
    node_index = {nid: idx for idx, nid in enumerate(sorted_ids)}
    points = np.zeros((len(sorted_ids), 3), dtype=np.float64)
    for nid, idx in node_index.items():
        points[idx] = parsed.nodes[nid].coords

    cells: list[int] = []
    celltypes: list[int] = []
    skipped_types: dict[str, int] = {}

    for elem in parsed.elements.values():
        mapped = vtk_type_for(elem.element_type)
        if mapped is None:
            skipped_types[elem.element_type] = skipped_types.get(elem.element_type, 0) + 1
            continue
        vtk_type, n_nodes = mapped
        if len(elem.nodes) != n_nodes:
            # Connectivity row is the wrong width for this VTK type.
            # Skip rather than emit a malformed cell that would crash
            # downstream rendering.
            skipped_types[f"{elem.element_type}(width={len(elem.nodes)})"] = (
                skipped_types.get(f"{elem.element_type}(width={len(elem.nodes)})", 0) + 1
            )
            continue
        try:
            indices = [node_index[nid] for nid in elem.nodes]
        except KeyError:
            # Element references a node that isn't in the parse — also
            # a parser bug; surface as skipped rather than guess.
            skipped_types[f"{elem.element_type}(orphan-node)"] = (
                skipped_types.get(f"{elem.element_type}(orphan-node)", 0) + 1
            )
            continue
        cells.append(n_nodes)
        cells.extend(indices)
        celltypes.append(vtk_type)

    if skipped_types:
        import sys

        for typ, count in sorted(skipped_types.items()):
            print(
                f"viz: skipped {count} element(s) of type {typ} (unsupported)",
                file=sys.stderr,
            )

    if not celltypes:
        raise ValueError(
            "no renderable elements after cell-type filtering — "
            f"input has {len(parsed.elements)} elements but none mapped to a "
            "supported VTK cell type. Check the CalculiX element types in "
            "the .frd against backend/app/viz/cell_types.py."
        )

    cells_arr = np.asarray(cells, dtype=np.int64)
    celltypes_arr = np.asarray(celltypes, dtype=np.uint8)
    grid = pv.UnstructuredGrid(cells_arr, celltypes_arr, points)
    return grid


def _build_displacement_array(
    parsed: "FRDParseResult",
    sorted_ids: list[int],
) -> np.ndarray:
    """Return shape-(N,3) displacement vectors per sorted node ID.

    Uses ``parsed.displacements`` (the flat / union dict). The parser
    splits a CalculiX static step's DISP and STRESS into separate
    ``FRDIncrement`` slots — increments[-1] often has zero
    displacements because the *last* slot in the file is the stress
    block, not the displacement block. The flat dict carries the
    union of all per-increment data, which for the wedge's static
    step is what we want. Multi-increment animations (transient /
    modal) are W6+ scope.

    Missing entries fill with zeros (a node with no displacement is
    indistinguishable from a node clamped at the origin in static
    analysis — both render as a lattice point that doesn't move).
    """
    disp_dict = parsed.displacements
    out = np.zeros((len(sorted_ids), 3), dtype=np.float64)
    for idx, nid in enumerate(sorted_ids):
        d = disp_dict.get(nid)
        if d is not None:
            out[idx] = d
    return out


def _build_von_mises_array(
    parsed: "FRDParseResult",
    sorted_ids: list[int],
) -> np.ndarray:
    """Return shape-(N,) von Mises values per sorted node ID. Missing
    entries fill with NaN; pyvista renders NaN as ``nan_color``
    (light gray) rather than 0, which would skew the colorbar."""
    stress_dict = parsed.stresses
    out = np.full(len(sorted_ids), np.nan, dtype=np.float64)
    for idx, nid in enumerate(sorted_ids):
        s = stress_dict.get(nid)
        if s is not None and s.von_mises is not None:
            out[idx] = s.von_mises
    return out


def render_mesh_outline(
    parsed: "FRDParseResult",
    output_path: Path,
    *,
    title: str = "Mesh — geometry only",
) -> Path:
    """Render the mesh as a wireframe + translucent surface, no field.
    This is the 'case under construction' visual — what data the
    pipeline received. Returns the PNG path that was written."""
    pv = _import_pyvista()
    grid = build_grid(parsed)

    plotter = pv.Plotter(off_screen=True, window_size=_FIG_WINDOW_SIZE)
    plotter.add_mesh(
        grid,
        show_edges=True,
        edge_color="black",
        line_width=0.5,
        color="lightsteelblue",
        opacity=0.4,
    )
    plotter.add_text(title, position="upper_edge", font_size=10)
    plotter.show_axes()
    plotter.view_isometric()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plotter.screenshot(str(output_path), return_img=False)
    plotter.close()
    return output_path


def render_displacement(
    parsed: "FRDParseResult",
    output_path: Path,
    *,
    title: str = "Displacement magnitude (deformed)",
    deform_scale: float | None = None,
) -> Path:
    """Render mesh deformed by the displacement field with magnitude
    coloring. ``deform_scale`` exaggerates small displacements; default
    is auto-scaled so max displacement ≈ 5% of the model's bounding-box
    diagonal (industry-standard)."""
    pv = _import_pyvista()
    grid = build_grid(parsed)

    sorted_ids = sorted(parsed.nodes.keys())
    disp = _build_displacement_array(parsed, sorted_ids)
    grid.point_data["displacement"] = disp
    mag = np.linalg.norm(disp, axis=1)
    grid.point_data["displacement_magnitude"] = mag

    bbox_diag = float(np.linalg.norm(np.ptp(grid.points, axis=0)))
    max_disp = float(mag.max()) if mag.size else 0.0
    if deform_scale is None:
        deform_scale = (
            (0.05 * bbox_diag / max_disp) if max_disp > 0 else 1.0
        )

    warped = grid.warp_by_vector("displacement", factor=deform_scale)

    plotter = pv.Plotter(off_screen=True, window_size=_FIG_WINDOW_SIZE)
    plotter.add_mesh(
        warped,
        scalars="displacement_magnitude",
        cmap="viridis",
        show_edges=True,
        edge_color="black",
        line_width=0.3,
        scalar_bar_args={"title": "|u|", "n_labels": 5},
    )
    plotter.add_text(
        f"{title}\nscale=×{deform_scale:.3g}",
        position="upper_edge",
        font_size=10,
    )
    plotter.show_axes()
    plotter.view_isometric()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plotter.screenshot(str(output_path), return_img=False)
    plotter.close()
    return output_path


def render_von_mises(
    parsed: "FRDParseResult",
    output_path: Path,
    *,
    title: str = "von Mises stress (deformed)",
    deform_scale: float | None = None,
) -> Path:
    """Render mesh deformed by displacement, colored by von Mises
    stress. Same deform-scale convention as ``render_displacement``."""
    pv = _import_pyvista()
    grid = build_grid(parsed)

    sorted_ids = sorted(parsed.nodes.keys())
    disp = _build_displacement_array(parsed, sorted_ids)
    vm = _build_von_mises_array(parsed, sorted_ids)
    grid.point_data["displacement"] = disp
    grid.point_data["von_mises"] = vm

    bbox_diag = float(np.linalg.norm(np.ptp(grid.points, axis=0)))
    max_disp = float(np.linalg.norm(disp, axis=1).max()) if disp.size else 0.0
    if deform_scale is None:
        deform_scale = (
            (0.05 * bbox_diag / max_disp) if max_disp > 0 else 1.0
        )

    warped = grid.warp_by_vector("displacement", factor=deform_scale)

    plotter = pv.Plotter(off_screen=True, window_size=_FIG_WINDOW_SIZE)
    plotter.add_mesh(
        warped,
        scalars="von_mises",
        cmap="turbo",  # high-contrast for stress concentration
        show_edges=True,
        edge_color="black",
        line_width=0.3,
        nan_color="lightgray",
        scalar_bar_args={"title": "σ_vm", "n_labels": 5},
    )
    plotter.add_text(
        f"{title}\nscale=×{deform_scale:.3g}",
        position="upper_edge",
        font_size=10,
    )
    plotter.show_axes()
    plotter.view_isometric()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plotter.screenshot(str(output_path), return_img=False)
    plotter.close()
    return output_path


def render_all(
    parsed: "FRDParseResult",
    output_dir: Path,
) -> dict[str, Path]:
    """Convenience: render the three default figures into ``output_dir``.
    Returns a dict mapping figure-name → PNG path. Each call mkdirs
    output_dir; the renderer cleans up its plotter on exit."""
    return {
        "mesh": render_mesh_outline(parsed, output_dir / "mesh.png"),
        "displacement": render_displacement(
            parsed, output_dir / "displacement.png"
        ),
        "von_mises": render_von_mises(parsed, output_dir / "von_mises.png"),
    }


__all__ = [
    "build_grid",
    "render_mesh_outline",
    "render_displacement",
    "render_von_mises",
    "render_all",
]
