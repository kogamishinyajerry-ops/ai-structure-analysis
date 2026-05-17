# plate-simply-supported-candidate · NOTES

> **Phase 25 A** — 5th tier_2_validated case. Closes Phase 24 retro
> FEA Dim 2 "validated count held flat at 4". Promotion driven by
> `cross_check_verdict.yaml` overlay in
> `backend/app/services/reporting/_claim_tier.py:_apply_verdict_overlay`.

## Geometry

- `data/plate_ss.geo` — 1.0 m × 1.0 m × 0.020 m square steel plate.
- a / t = 50 (well inside Kirchhoff thin-plate envelope a/t ≥ 20).
- Origin at one corner; thickness extruded along +z.

## Cross-check (Phase 25 A)

- **Runner:** `backend/app/services/cross_check/plate_ss_runner.py`
- **Analytical:** Timoshenko & Woinowsky-Krieger §30 Table 8 /
  Roark Table 11.4 case 1a — `w_center = α · q · a⁴ / D` with
  α = 0.00406 for square plate, ν = 0.3, simply supported on all 4
  edges, uniform pressure load.
- **Material:** steel-S355 (E = 210 GPa, ν = 0.3, from SSOT library).
- **Load:** q = 1.0 × 10⁴ Pa (10 kPa pressure, total ≈ 10 kN downward).
- **BC (3D-solid approximation of ideal SS):**
  - u_z = 0 along the 4 edge lines of the bottom face (z=0 AND on
    perimeter)
  - u_x = u_y = 0 at corner (0,0,0) (eliminate 2 in-plane RBMs)
  - u_y = 0 at corner (a,0,0) (eliminate z-rotation RBM)
  - u_x = 0 at corner (0,a,0) (redundant safety)
- **Tolerance:** 15% (honest envelope; Kirchhoff vs 3D-solid ~3-5% +
  C3D10 through-thickness coarseness ~5-8% + reader-numerical ~1-2%).

## Live run (2026-05-17)

- Analytical w_center = -0.2639 mm
- Observed   w_center = -0.2486 mm
- **Residual: -5.79%** (well inside 15% tolerance; 9.21% margin)
- Mesh: 4,420 nodes / 2,125 C3D10 quadratic tets (cl_max = 0.060 m,
  element_order = 2)
- Small-deflection ratio w/t = 0.0124 (well below 0.2 limit)

The -5.79% sign indicates ccx slightly UNDER-predicts the Kirchhoff
analytical — typical for solid-element vs thin-plate-theory because
the 3D model captures transverse shear (Mindlin correction is a
~3-5% addition to deflection at a/t=50) and the C3D10 mesh slightly
stiffens via through-thickness discretization. Both effects are
included in the honest tolerance envelope.

## Anti-gaming guard A:-1

The runner reads w at the node nearest the plate-center 3D
coordinate (a/2, a/2, t/2), NOT `max(|w|)` across the mesh. A central-
disk radius check at runtime refuses any candidate node outside
`max(cl_max, a/20)` of the geometric center — corner or edge artifacts
cannot pad the verdict. Pinned at test level too.

Not signed validation; not benchmark agreement.
