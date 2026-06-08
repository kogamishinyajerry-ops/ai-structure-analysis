"""Generate turbine blade surface mesh using FreeCAD, save as .npz.
Run: /Applications/FreeCAD.app/Contents/Resources/bin/python docs/demo/gen_blade_mesh.py
"""

import sys

sys.path.insert(0, "/Applications/FreeCAD.app/Contents/Resources/Ext")
sys.path.insert(0, "/Applications/FreeCAD.app/Contents/Resources/lib")
sys.path.insert(0, "/Applications/FreeCAD.app/Contents/Resources/Mod")

import math
import os
from pathlib import Path

import FreeCAD
import MeshPart
import numpy as np
import Part
from FreeCAD import Base

ROOT = Path(__file__).resolve().parents[2]
OUT_NPZ = ROOT / "docs" / "demo" / "blade-assets" / "blade_surface.npz"
OUT_NPZ.parent.mkdir(parents=True, exist_ok=True)


def naca_points(m=4, p=40, t=12, npts=40, chord=30.0):
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


print("== Building turbine blade ==")
doc = FreeCAD.newDocument("Blade")

n_sec, chord, span = 5, 30.0, 60.0
wires = []
for i in range(n_sec):
    z = i * span / (n_sec - 1)
    frac = i / (n_sec - 1)
    thick = 12 * (1 - 0.5 * frac)
    camber = 4 * (1 - 0.3 * frac)
    scale_c = 1.0 - 0.2 * frac
    twist = math.radians(15 * frac)
    pts_raw = naca_points(m=camber, p=40, t=thick, npts=40, chord=chord * scale_c)
    clean = []
    for pt in pts_raw:
        cx, cy = pt.x - 0.25 * chord, pt.y
        rx = cx * math.cos(twist) - cy * math.sin(twist)
        ry = cx * math.sin(twist) + cy * math.cos(twist)
        v = Base.Vector(rx + 0.25 * chord, ry, z)
        if not clean or (v - clean[-1]).Length > 0.5:
            clean.append(v)
    if (clean[0] - clean[-1]).Length > 0.01:
        clean.append(clean[0])
    wires.append(Part.makePolygon(clean))

print("lofting...")
loft = Part.makeLoft(wires, True)
blade = doc.addObject("Part::Feature", "Blade")
blade.Shape = loft
doc.recompute()
print(f"  volume={loft.Volume:.0f} mm³")

print("meshing...")
# meshFromShape RETURNS the Mesh.MeshObject; it does NOT replace doc.ActiveObject
# (that stays the Part::Feature, which has no .Mesh attribute). Capture the return value.
# Deflection-based standard mesher: on the true (t/100-fixed) thin airfoil the
# SMESH MaxLength/MinLength pair fails Regular_1D on the short blunt-TE edges
# (~1.3mm < MaxLength) and returns 0 facets; LinearDeflection has no such
# constraint and resolves the thin sections cleanly.
fc_mesh = MeshPart.meshFromShape(
    Shape=blade.Shape, LinearDeflection=0.05, AngularDeflection=0.3, Relative=False
)
n_pts = fc_mesh.CountPoints
n_faces = fc_mesh.CountFacets
print(f"  points={n_pts} faces={n_faces}")
assert n_faces > 0, "surface mesh has zero facets — meshing failed, refusing to write npz"

# Mesh.MeshObject exposes vertices/facets via .Topology = (points, facet_index_tuples),
# not getPoint/getFacet (those live on the Mesh::Feature wrapper that is never created here).
mesh_pts, mesh_facets = fc_mesh.Topology
verts = np.array([[p.x, p.y, p.z] for p in mesh_pts], dtype=np.float64)
faces = np.array([[f[0], f[1], f[2]] for f in mesh_facets], dtype=np.int32)

np.savez_compressed(OUT_NPZ, verts=verts, faces=faces)
print(f"  saved {OUT_NPZ} ({os.path.getsize(OUT_NPZ) / 1024:.0f} KB)")
print("DONE")
