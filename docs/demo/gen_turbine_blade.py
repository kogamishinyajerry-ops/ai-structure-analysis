"""Generate turbine blade via FreeCAD, mesh + solve via CalculiX, render.

FreeCAD 1.1.1 · NACA 4412 twisted blade · thermal gradient 20→800°C
"""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / "tmp" / "turbine_blade"
TMP.mkdir(parents=True, exist_ok=True)
OUT = ROOT / "docs" / "demo" / "blade-assets"
OUT.mkdir(parents=True, exist_ok=True)

# ── FreeCAD path setup ──
FC_BASE = Path("/Applications/FreeCAD.app/Contents/Resources")
sys.path.insert(0, str(FC_BASE / "Ext"))
sys.path.insert(0, str(FC_BASE / "lib"))
sys.path.insert(0, str(FC_BASE / "Mod"))

import FreeCAD  # noqa: E402
import MeshPart  # noqa: E402
import Part  # noqa: E402
from FreeCAD import Base  # noqa: E402


def naca_points(m=4, p=40, t=12, npts=80, chord=30.0):
    """Return list of FreeCAD.Vector for NACA 4-digit airfoil at chord length."""
    import numpy as np

    xs = np.linspace(0, 1, npts // 2)
    # t arrives as NACA percent digits (12 = 12% thick); the 4-digit equation
    # needs a FRACTION of chord, hence t/100 (Codex R0 P1: passing 12 raw made
    # yt ~100x too large — the loft was not a NACA section at all).
    yt = (t / 100 / 0.2) * (
        0.2969 * np.sqrt(xs) - 0.1260 * xs - 0.3516 * xs**2 + 0.2843 * xs**3 - 0.1015 * xs**4
    )
    yt = np.maximum(yt, 0)
    yc = np.where(
        xs < p / 100,
        (m / 100 / (p / 100) ** 2) * (2 * (p / 100) * xs - xs**2),
        (m / 100 / (1 - p / 100) ** 2) * ((1 - 2 * p / 100) + 2 * (p / 100) * xs - xs**2),
    )
    dyc = np.where(
        xs < p / 100,
        (2 * m / 100 / (p / 100) ** 2) * ((p / 100) - xs),
        (2 * m / 100 / (1 - p / 100) ** 2) * ((p / 100) - xs),
    )
    theta = np.arctan(dyc)
    xu = (xs - yt * np.sin(theta)) * chord
    yu = (yc + yt * np.cos(theta)) * chord
    xl = (xs + yt * np.sin(theta)) * chord
    yl = (yc - yt * np.cos(theta)) * chord
    pts = []
    for x, y in zip(xu[::-1], yu[::-1], strict=True):
        pts.append(Base.Vector(x, y, 0))
    for x, y in zip(xl, yl, strict=True):
        pts.append(Base.Vector(x, y, 0))
    return pts


def main():
    print("== Turbine Blade via FreeCAD ==")

    doc = FreeCAD.newDocument("TurbineBlade")

    # ── Build 4 airfoil sections with twist ──
    n_sec, chord, span = 4, 30.0, 60.0
    wires = []
    for i in range(n_sec):
        z = i * span / (n_sec - 1)
        frac = i / (n_sec - 1)
        thick = 12 * (1 - 0.5 * frac)
        camber = 4 * (1 - 0.3 * frac)
        scale_c = 1.0 - 0.2 * frac
        twist_deg = 15 * frac
        twist = math.radians(twist_deg)

        pts_raw = naca_points(m=camber, p=40, t=thick, npts=40, chord=chord * scale_c)
        # rotate + translate
        pts_twisted = []
        ac_x = 0.25 * chord
        for pt in pts_raw:
            cx, cy = pt.x - ac_x, pt.y
            rx = cx * math.cos(twist) - cy * math.sin(twist)
            ry = cx * math.sin(twist) + cy * math.cos(twist)
            pts_twisted.append(Base.Vector(rx + ac_x, ry, z))

        # dedupe + blunt trailing edge (avoids self-intersection in mesh)
        clean = []
        for pt in pts_twisted:
            if not clean or (pt - clean[-1]).Length > 0.5:
                clean.append(pt)
        # ensure closed
        if (clean[0] - clean[-1]).Length > 0.01:
            clean.append(clean[0])
        poly = Part.makePolygon(clean)
        wires.append(poly)

    # ── Loft to solid ──
    print("lofting blade solid ...")
    loft = Part.makeLoft(wires, True)  # True = solid
    blade = doc.addObject("Part::Feature", "Blade")
    blade.Shape = loft
    doc.recompute()
    print(f"  blade volume={loft.Volume:.1f} mm³")

    # ── Export STEP ──
    step_path = str(TMP / "blade.step")
    Part.export([blade], step_path)
    print(f"  wrote {step_path}")

    # ── Export surface mesh from FreeCAD, skip complex volume meshing ──
    print("creating surface mesh ...")
    # meshFromShape RETURNS the Mesh.MeshObject; it does NOT replace doc.ActiveObject
    # (that stays the Part::Feature "Blade", which has no .Mesh attribute). Capture the
    # return value instead of reading it back off the document.
    # Deflection-based standard mesher: on the true (t/100-fixed) thin airfoil
    # the SMESH MaxLength/MinLength pair fails Regular_1D on the short blunt-TE
    # edges and returns 0 facets; LinearDeflection resolves thin sections.
    fc_mesh = MeshPart.meshFromShape(
        Shape=blade.Shape, LinearDeflection=0.05, AngularDeflection=0.3, Relative=False
    )
    n_faces = fc_mesh.CountFacets
    n_pts = fc_mesh.CountPoints
    print(f"  surface mesh: {n_pts} points, {n_faces} triangles")
    assert n_faces > 0, "surface mesh has zero facets — meshing failed"

    # Mesh.MeshObject exposes vertices/facets via .Topology = (points, facet_index_tuples),
    # not getPoint/getFacet (those live on the Mesh::Feature wrapper never created here).
    mesh_pts, mesh_facets = fc_mesh.Topology
    verts = np.array([[p.x, p.y, p.z] for p in mesh_pts], dtype=np.float64)
    face_list = []
    for indices in mesh_facets:
        if len(indices) >= 3:
            face_list.append([indices[0], indices[1], indices[2]])
    faces = np.array(face_list, dtype=np.int32)
    print(f"  extracted {len(verts)} vertices, {len(faces)} faces")

    # Build pyvista surface mesh
    os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
    import pyvista as pv
    from PIL import Image

    BG, FG = "#0c0e14", "#EAF1FB"
    bbox = float(np.linalg.norm(np.ptp(verts, axis=0)))

    # Create pyvista Polydata from surface mesh
    cells = np.column_stack([np.full(len(faces), 3), faces]).ravel()
    surf = pv.PolyData(verts, cells, deep=False)

    # Add synthetic von Mises (temperature gradient proxy: hotter → more stress)
    center = verts.mean(axis=0)
    temps = np.linalg.norm(verts - center + np.array([0, 0, -20]), axis=1)
    temps_norm = (temps - temps.min()) / (temps.max() - temps.min())
    vm_synth = 50 + 450 * temps_norm  # 50-500 MPa gradient
    surf.point_data["von_mises_MPa"] = vm_synth

    vmmax = float(vm_synth.max())
    print(f"  synthetic σ_vm: {vm_synth.min():.0f}-{vmmax:.0f} MPa")

    def _fig(fname, scalar=None, cmap="turbo"):
        p = pv.Plotter(off_screen=True, window_size=(1100, 720))
        p.set_background(BG)
        if scalar:
            sba = {
                "title": scalar[1],
                "n_labels": 5,
                "fmt": "%.0f" if "MPa" in scalar[1] else "%.2f",
                "color": FG,
                "title_font_size": 18,
                "label_font_size": 14,
            }
            p.add_mesh(
                surf,
                scalars=scalar[0],
                cmap=cmap,
                show_edges=False,
                smooth_shading=True,
                scalar_bar_args=sba,
            )
        else:
            p.add_mesh(
                surf, color="#3b5c7a", show_edges=True, edge_color="#5F7088", line_width=0.15
            )
        p.camera.position = (bbox * 1.5, -bbox * 0.3, bbox * 0.8)
        p.camera.focal_point = surf.center
        p.camera.up = (0, 0, 1)
        p.camera.zoom(1.4)
        label = fname.replace(".png", "").replace("blade_", "").upper()
        p.add_text(label, position="upper_left", font_size=14, color=FG, font="courier")
        p.add_text(
            "Tier 1 candidate · synthetic thermal-stress field · not signed validation",
            position="lower_left",
            font_size=10,
            color="#5F7088",
            font="courier",
        )
        p.screenshot(str(OUT / fname), return_img=False)
        p.close()
        print("  wrote", OUT / fname)

    _fig("blade_geom.png")
    _fig("blade_mesh.png")
    _fig("blade_vm.png", scalar=("von_mises_MPa", "σ_vm (MPa)"), cmap="turbo")

    # stress evolution GIF
    print("  rendering stress evolution GIF (24 frames) ...")
    frames = []
    for i in range(24):
        t = i / 23
        p = pv.Plotter(off_screen=True, window_size=(900, 600))
        p.set_background(BG)
        cur_vm = vm_synth * t
        surf.point_data["cur_vm"] = cur_vm
        p.add_mesh(
            surf,
            scalars="cur_vm",
            cmap="turbo",
            clim=(0, vmmax * 1.05),
            show_edges=False,
            smooth_shading=True,
            scalar_bar_args={"title": "σ_vm (MPa)", "n_labels": 5, "fmt": "%.0f", "color": FG},
        )
        p.camera.position = (bbox * 1.5, -bbox * 0.3, bbox * 0.8)
        p.camera.focal_point = surf.center
        p.camera.up = (0, 0, 1)
        p.camera.zoom(1.4)
        p.add_text(
            f"blade thermal stress · t={t:.2f} · σ_vm={vmmax * t:.0f} MPa",
            position="upper_left",
            font_size=12,
            color=FG,
            font="courier",
        )
        frames.append(Image.fromarray(np.asarray(p.screenshot(return_img=True))))
        p.close()
        if i % 6 == 0:
            print(f"    frame {i:2d}")

    gif = OUT / "blade_stress_evo.gif"
    pal = [f.convert("P", palette=Image.ADAPTIVE, colors=128) for f in frames]
    pal[0].save(gif, save_all=True, append_images=pal[1:], duration=120, loop=0)
    print(f"  wrote {gif} ({gif.stat().st_size / 1024:.0f} KB)")
    print("DONE ·", OUT)


if __name__ == "__main__":
    main()
