"""Render thick-walled cylinder (Lame problem) → engine casing thermal-stress.

287 nodes / 32 C3D20 quadratic hex elements.
Real CalculiX *STATIC result (internal pressure on a thick cylinder).

Framed as: "航空发动机燃烧室外壳" — the Lame stress gradient
(inner wall high → outer wall low) is exactly the engineering
concern in engine casing design.

Outputs → docs/demo/engine-assets/
"""

from __future__ import annotations

import os

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
import sys

sys.path.insert(0, "backend")
from pathlib import Path

import numpy as np
import pyvista as pv
from app.parsers.frd_parser import parse_frd
from app.viz.render import _build_displacement_array, _build_von_mises_array, build_grid
from PIL import Image

FRD = "demo_cylinder_pv/solve.frd"
OUT = Path("docs/demo/engine-assets")
OUT.mkdir(parents=True, exist_ok=True)
WIN = (1100, 720)
BG = "#0c0e14"
FG = "#EAF1FB"
DIM = "#5F7088"
CLAIM = "Tier 1 candidate · real CalculiX Lame cylinder · not signed validation"

print("loading", FRD)
parsed = parse_frd(FRD)
grid = build_grid(parsed)
sorted_ids = sorted(parsed.nodes.keys())
disp = _build_displacement_array(parsed, sorted_ids)
vm = _build_von_mises_array(parsed, sorted_ids)
mag = np.linalg.norm(disp, axis=1)
bbox = float(np.linalg.norm(np.ptp(grid.points, axis=0)))
mx = float(mag.max()) or 1e-9
scale = 0.06 * bbox / mx
grid.point_data["displacement"] = disp
# Deck is the mm/MPa unit system (Ri=100mm, E=2.0e5 MPa, p=10 MPa), so the FRD
# fields are ALREADY mm and MPa — no conversion (Codex R0 P2: the old *1000 /
# "Pa" label overstated |u| by 1000x and mislabelled stress by 1e6). Verified
# against the Lame closed form: sigma_vm inner = sqrt(972) = 31.18 MPa vs
# parsed 31.16; u_r inner ~0.014mm vs parsed 0.0134.
grid.point_data["von_mises_MPa"] = vm
grid.point_data["|u|_mm"] = mag

vmmax = float(np.nanmax(vm))
print(
    f"  nodes={len(parsed.nodes)} cells={grid.n_cells} |u|max={mx:.4f}mm "
    f"σ_vm max={vmmax:.1f}MPa scale=×{scale:.0f}"
)


def _fig(fname: str, scalar=None, cmap="turbo") -> None:
    p = pv.Plotter(off_screen=True, window_size=WIN)
    p.set_background(BG)
    deformed = scalar is not None
    mesh = grid.warp_by_vector("displacement", factor=scale) if deformed else grid
    if scalar:
        sba = {
            "title": scalar[1],
            "n_labels": 5,
            "fmt": "%.2f" if "mm" in scalar[1] else "%.1f",
            "color": FG,
            "title_font_size": 20,
            "label_font_size": 16,
        }
        p.add_mesh(
            mesh,
            scalars=scalar[0],
            cmap=cmap,
            show_edges=False,
            smooth_shading=True,
            scalar_bar_args=sba,
        )
    else:
        p.add_mesh(mesh, color="#3b5c7a", show_edges=True, edge_color=DIM, line_width=0.2)
    p.view_isometric()
    p.camera.zoom(1.4)
    label = fname.replace(".png", "").replace("engine_", "").replace("_", " ").upper()
    if deformed:
        label += f"  (deform ×{scale:.0f})"
    p.add_text(label, position="upper_left", font_size=15, color=FG, font="courier")
    p.add_text(CLAIM, position="lower_left", font_size=10, color=DIM, font="courier")
    p.screenshot(str(OUT / fname), return_img=False)
    p.close()
    print("  wrote", OUT / fname)


_fig("engine_geom.png")
_fig("engine_mesh.png")
_fig("engine_disp.png", scalar=("|u|_mm", "|u| (mm)"), cmap="viridis")
_fig("engine_vm.png", scalar=("von_mises_MPa", "σ_vm (MPa)"), cmap="turbo")

# stress evolution GIF (24 frames pseudo-time)
print("rendering stress evolution GIF (24 frames) ...")
frames = []
for i in range(24):
    t = i / 23
    warped = grid.warp_by_vector("displacement", factor=scale * t)
    # Ramp the SCALAR field with t too, not just the warp. clim stays pinned
    # to the full range (0, vmmax) so the colorbar is honest while the
    # picture builds up — frame 0 reads ≈0 MPa (matching the title) instead
    # of showing the full stress field under a "σ_vm max≈0" caption.
    warped["von_mises_MPa_t"] = warped["von_mises_MPa"] * t
    p = pv.Plotter(off_screen=True, window_size=(900, 600))
    p.set_background(BG)
    p.add_mesh(
        warped,
        scalars="von_mises_MPa_t",
        cmap="turbo",
        clim=(0, vmmax),
        show_edges=False,
        smooth_shading=True,
        scalar_bar_args={
            "title": "σ_vm (MPa)",
            "n_labels": 5,
            "fmt": "%.1f",
            "color": FG,
            "title_font_size": 14,
            "label_font_size": 10,
        },
    )
    p.view_isometric()
    p.camera.zoom(1.3)
    # vmmax is already MPa (deck-native) — no /1e6 (was double-converting).
    p.add_text(
        f"engine casing stress · t={t:.2f} · σ_vm max={vmmax * t:.1f} MPa",
        position="upper_left",
        font_size=13,
        color=FG,
        font="courier",
    )
    frames.append(Image.fromarray(np.asarray(p.screenshot(return_img=True))))
    p.close()
    if i % 5 == 0:
        print(f"  frame {i:2d}")

gif = OUT / "engine_stress_evo.gif"
pal = [f.convert("P", palette=Image.ADAPTIVE, colors=128) for f in frames]
pal[0].save(gif, save_all=True, append_images=pal[1:], duration=120, loop=0)
print(f"  wrote {gif} ({gif.stat().st_size / 1024:.0f} KB)")
print("DONE ·", OUT)
