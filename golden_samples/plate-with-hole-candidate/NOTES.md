# plate-with-hole-candidate — Phase 20 C

**Tier:** `tier_1_candidate`. Phase 20 C's canonical demonstration of
the meshed Tier 2 pipeline (gmsh + ccx). The Kirsch analytical
cross-check (σ_max = 3·σ_∞ at hole edge under uniaxial tension) would
promote this case to `tier_2_validated`; that runner is Phase 21+
scope.

## Geometry

100 mm × 50 mm × 5 mm plate with a 10 mm-radius circular hole in the
centre. Defined in `data/plate_with_hole.geo` (gmsh OpenCASCADE
geometry kernel).

| parameter | symbol | value | unit |
|---|---|---|---|
| plate length | L | 0.100 | m |
| plate width | W | 0.050 | m |
| plate thickness | T | 0.005 | m |
| hole radius | R | 0.010 | m |

Coordinate frame: x = long axis (0..L), y = short axis (0..W), z =
thickness (0..T). Origin at one corner.

## Canonical BC + load (Phase 20 C runner default)

* clamp: `PlanarSelection(axis="x", value_m=0.0, tol_m=1e-6)` —
  all nodes on the x=0 face fully restrained (DOF 1-3).
* load: `PlanarSelection(axis="x", value_m=L, tol_m=1e-6)`, DOF=1,
  total_force_n = +1000 N — tensile uniaxial pull along x.

Under this loading the far-field stress σ_∞ = F/(W·T) = 1000/(0.05·
0.005) = 4.0e6 Pa. Kirsch peak stress at the hole edge ≈ 3·σ_∞ =
1.2e7 Pa.

## Phase 20 C scope honesty

* Meshed pipeline ships (gmsh + parser + INP composer + ccx).
* The Kirsch analytical comparison is NOT implemented. Promotion to
  `tier_2_validated` waits for Phase 21's `plate_kirsch_runner.py`.
* Linear tetrahedra only (C3D4); quadratic tets (C3D10) would give
  significantly better hole-edge stress accuracy (~3-5× error
  reduction). C3D10 wiring is also Phase 21+ scope.

## Claim envelope

* claim_tier: tier_1_engineering_candidate
* claim_boundary: not signed validation; not benchmark agreement
* claim_impact: Phase 20 C meshed-pipeline demonstration case; first
  Tier 2 path that escapes the single-element-coupon regime.
