"""Demo-asset renderer — provenance for docs/demo/assets/*.png.

Renders the REAL CalculiX plate-with-hole result into the one-take demo's
contour assets using the PROJECT'S OWN grid builder (app.viz.render.build_grid)
+ pyvista, with demo-quality camera/edges/sizing. Same real data + same render
stack as backend/app/viz/render.py — only the framing (dark deck bg, MPa
colorbar, zoom) differs.

Run from repo root with the project venv:
    PYVISTA_OFF_SCREEN=true .venv/bin/python docs/demo/render_assets.py

Input .frd is a real ccx static solve (S355 steel plate, central hole, clamped
+ tension): peak von Mises 3.17 MPa, max displacement 0.627 um. Tier-1
engineering candidate — NOT signed validation, NOT benchmark agreement.

Provenance / what is committed:
    This script CONSUMES a local solver output (the .frd below) that is
    NOT checked into git (`*.frd` is gitignored — see .gitignore line 48).
    Only the rendered GIF/PNG products under docs/demo/assets/ are committed.
    A fresh clone will therefore NOT have the .frd; run the regeneration
    command printed by the preflight check below (the real gmsh→ccx Kirsch
    cross-check) before running this renderer.
"""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")

import sys  # noqa: E402

import numpy as np  # noqa: E402
import pyvista as pv  # noqa: E402

sys.path.insert(0, "backend")
from app.parsers.frd_parser import parse_frd  # noqa: E402
from app.viz.render import (  # noqa: E402
    _build_displacement_array,
    _build_von_mises_array,
    build_grid,
)

FRD = "tmp/workspace_plate-with-hole-candidate/cl_0p0020/plate_kirsch_xcheck.frd"
OUT = Path("docs/demo/assets")
OUT.mkdir(parents=True, exist_ok=True)
WIN = (1680, 1050)
BG = "#0c0e14"  # deck background — assets composite seamlessly onto the dark slide
FG = "#EAF1FB"  # deck primary text
ZOOM = 1.5


def _preflight() -> None:
    """Verify every solver input this renderer consumes exists.

    The .frd is a local solver output (gitignored); a fresh clone won't
    have it. On a miss, print an honest, actionable message — what is
    missing and the exact real command that regenerates it — then exit
    non-zero instead of crashing deep inside parse_frd().
    """
    if Path(FRD).is_file():
        return
    print(
        "\n".join(
            [
                "ERROR: missing solver input — cannot render demo assets.",
                f"  missing: {FRD}",
                "",
                "  This .frd is a local ccx output and is gitignored "
                "(.gitignore line 48: `*.frd`),",
                "  so a fresh clone does not contain it. Regenerate the real gmsh -> ccx Kirsch",
                "  cross-check into a PERSISTENT workspace (default is a TemporaryDirectory",
                "  that is deleted on exit), then copy the artifact and re-run this renderer:",
                "",
                "    .venv/bin/python scripts/cross_check_phase21a.py \\",
                "        --skip cantilever --workdir tmp/phase21a",
                f"    mkdir -p {Path(FRD).parent}",
                f"    cp tmp/phase21a/plate-with-hole-candidate/plate_kirsch_xcheck.frd {FRD}",
                "",
                "  (The regenerated run uses cl=0.003 m; the historical dir name says",
                "  cl_0p0020 — this renderer reads whatever real .frd sits at FRD.)",
            ]
        ),
        file=sys.stderr,
    )
    raise SystemExit(1)


_preflight()

parsed = parse_frd(FRD)
sorted_ids = sorted(parsed.nodes.keys())
grid = build_grid(parsed)
disp = _build_displacement_array(parsed, sorted_ids)
vm_pa = _build_von_mises_array(parsed, sorted_ids)
vm_mpa = vm_pa / 1.0e6  # SI Pa → MPa for a clean colorbar
mag_um = np.linalg.norm(disp, axis=1) * 1.0e6  # m → micrometre

grid.point_data["von_mises_MPa"] = vm_mpa
grid.point_data["disp_um"] = mag_um
grid.point_data["displacement"] = disp

peak = float(np.nanmax(vm_mpa))
print(f"peak von Mises = {peak:.3f} MPa   max |u| = {float(np.nanmax(mag_um)):.4f} um")


def _vm_plot(view: str, fname: str, *, deformed: bool, edges: bool) -> None:
    mesh = grid
    scale = 0.0
    if deformed:
        bbox = float(np.linalg.norm(np.ptp(grid.points, axis=0)))
        mx = float(np.linalg.norm(disp, axis=1).max()) or 1.0
        scale = 0.06 * bbox / mx
        mesh = grid.warp_by_vector("displacement", factor=scale)
    p = pv.Plotter(off_screen=True, window_size=WIN)
    p.set_background(BG)
    p.add_mesh(
        mesh,
        scalars="von_mises_MPa",
        cmap="turbo",
        show_edges=edges,
        edge_color="#5F7088",
        line_width=0.15,
        nan_color="#2a2f3a",
        scalar_bar_args={
            "title": "von Mises  (MPa)",
            "n_labels": 6,
            "fmt": "%.2f",
            "color": FG,
            "title_font_size": 26,
            "label_font_size": 22,
        },
    )
    if view == "top":
        p.view_xy()
    else:
        p.view_isometric()
    p.camera.zoom(ZOOM)
    p.screenshot(str(OUT / fname), return_img=False)
    p.close()
    print("wrote", OUT / fname)


def _disp_plot(fname: str) -> None:
    bbox = float(np.linalg.norm(np.ptp(grid.points, axis=0)))
    mx = float(np.linalg.norm(disp, axis=1).max()) or 1.0
    scale = 0.06 * bbox / mx
    warped = grid.warp_by_vector("displacement", factor=scale)
    p = pv.Plotter(off_screen=True, window_size=WIN)
    p.set_background(BG)
    p.add_mesh(
        warped,
        scalars="disp_um",
        cmap="viridis",
        show_edges=True,
        edge_color="#5F7088",
        line_width=0.15,
        scalar_bar_args={
            "title": f"|u|  (um)   deformed x{scale:.0f}",
            "n_labels": 6,
            "fmt": "%.3f",
            "color": FG,
            "title_font_size": 24,
            "label_font_size": 22,
        },
    )
    p.view_isometric()
    p.camera.zoom(ZOOM)
    p.screenshot(str(OUT / fname), return_img=False)
    p.close()
    print("wrote", OUT / fname)


def _geom_plot(fname: str) -> None:
    surf = grid.extract_surface()
    p = pv.Plotter(off_screen=True, window_size=WIN)
    p.set_background(BG)
    p.add_mesh(
        surf,
        color="#2b4f6a",
        show_edges=False,
        smooth_shading=True,
        specular=0.3,
    )
    p.add_mesh(surf.extract_feature_edges(), color="#62C4FF", line_width=2.0)
    p.view_isometric()
    p.camera.zoom(ZOOM)
    p.screenshot(str(OUT / fname), return_img=False)
    p.close()
    print("wrote", OUT / fname)


def _mesh_plot(fname: str) -> None:
    p = pv.Plotter(off_screen=True, window_size=WIN)
    p.set_background(BG)
    p.add_mesh(
        grid,
        show_edges=True,
        edge_color="#3BA8FF",
        line_width=0.25,
        color="#1b2b45",
        opacity=0.85,
    )
    p.view_isometric()
    p.camera.zoom(ZOOM)
    p.screenshot(str(OUT / fname), return_img=False)
    p.close()
    print("wrote", OUT / fname)


_vm_plot("top", "vm_top.png", deformed=False, edges=False)
_vm_plot("top", "vm_top_edges.png", deformed=False, edges=True)
_vm_plot("iso", "vm_iso.png", deformed=False, edges=False)
_disp_plot("disp_iso.png")
_mesh_plot("mesh_iso.png")
_geom_plot("geom_iso.png")
print("DONE")
