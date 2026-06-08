# cantilever-beam-modal-candidate · NOTES

> **Phase 26 A** — 6th tier_2_validated case. Closes Phase 25 retro
> punchlist item #3 (FEA Dim 4 solver-kind coverage held flat at 68
> since Phase 23 A). Introduces the `*FREQUENCY` modal-eigenvalue
> solver kind to the validated cohort.

## Geometry

- `data/cantilever_modal.geo` — 0.500 m × 0.020 m × 0.020 m steel beam.
- L / max(h, w) = 25 (well inside Euler-Bernoulli slender-beam
  envelope ≥ 10).
- Origin at the clamped end (x=0 face fully fixed). Free end at x=L.
- Vibration direction is +y (height); the rectangular cross-section
  has identical bending stiffness about y and z, so modes 1 and 2
  are a degenerate doublet (verified in the live run, see below).

## Cross-check (Phase 26 A)

- **Runner:** `backend/app/services/cross_check/cantilever_modal_runner.py`
- **Analytical:** Euler-Bernoulli clamped-free cantilever first
  natural frequency
  `f_1 = (β_1·L)² · √(EI / (ρA)) / (2π · L²)` with β_1·L = 1.875104
  (Rao §8.5 Table 8.4 / Inman §6.4 Table 6.1 / Blevins Table 4-1).
- **Material:** steel-S355 (E = 210 GPa, ν = 0.3, ρ = 7850 kg/m³,
  from SSOT library).
- **BC:** all 3 DOFs clamped on the x=0 face (cantilever).
- **Solver:** `*FREQUENCY 5` Lanczos eigenvalue extraction.
- **Tolerance:** 12% (honest envelope; Euler-Bernoulli vs 3D-solid
  ~3-5% + C3D10 mesh discretization ~3-6% + reader-numerical ~1-2%).

## Live run (2026-05-17)

- Analytical f_1 = 66.8413 Hz
- Observed   f_1 = 66.9299 Hz
- **Residual: +0.13%** (extraordinarily tight; 11.87% margin to
  12% tolerance — easily the tightest residual across all 6
  validated cases)
- Mesh: 1,895 nodes / 814 C3D10 quadratic tets (cl_max = 0.012 m,
  element_order = 2)
- Slender ratio L/h = 25 (3D solid captures only minimal Timoshenko
  shear correction at this aspect ratio)

Full 5-mode eigenfrequency list (ascending):
1. 66.92993 Hz (bending mode 1, y-direction)
2. 66.93393 Hz (bending mode 1, z-direction — degenerate doublet)
3. 416.4527 Hz (bending mode 2, y-direction)
4. 416.5019 Hz (bending mode 2, z-direction)
5. 1153.113 Hz (bending mode 3 OR first torsional)

The doublet structure at modes 1+2 (66.93 / 66.93) and modes 3+4
(416.45 / 416.50) confirms the square cross-section's identical
bending stiffness about y and z; the analytical only computes
ONE of the doublet (both have identical β_1·L). Ratio
mode-3 / mode-1 ≈ 6.22 matches the Euler-Bernoulli prediction
(β_2/β_1)² = (4.694/1.875)² ≈ 6.27 to within 1%.

## Anti-gaming guard A:-1

The runner refuses any "first eigenfrequency" below 1.0 Hz as a
likely numerical rigid-body artifact. CalculiX's Lanczos solver
occasionally emits ~10⁻⁶ Hz spurious modes on fully-clamped
meshes due to constraint-equation rounding; structural mode 1 for
this canonical geometry is ~67 Hz (two orders of magnitude above
the reject threshold). Pinned at the runner level by
`_filter_rigid_body_modes` AND at the test level by a stub-list
pin.

## What this 6th case adds

Until Phase 26 A, all 5 tier_2_validated cases used:
- cylinder-pv: linear static (analytical hoop stress)
- cantilever-beam: linear static (analytical tip deflection)
- plate-with-hole: linear static (Kirsch stress concentration)
- euler-column: linear buckling (Euler critical load)
- plate-simply-supported: linear static (Timoshenko α)

Cantilever-beam-modal-candidate is the **first validated case with
the `*FREQUENCY` modal-eigenvalue solver kind** — distinct physics
regime (mass-stiffness matrix eigenvalue problem `det(K − ω²M) = 0`,
not just `K·u = F`). FEA Dim 4 (solver kind coverage) lifts from
68 to ~72.

Not signed validation; not benchmark agreement.
