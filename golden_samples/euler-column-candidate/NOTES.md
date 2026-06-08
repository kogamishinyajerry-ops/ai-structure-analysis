# euler-column-candidate — Phase 22 A (infrastructure) + Phase 23 A (promotion)

**Tier:** `tier_2_validated` (promoted Phase 23 A · 2026-05-17). Verdict
file `cross_check_verdict.yaml` carries a PASS verdict from
`run_buckling_b31_cross_check` (B31 Timoshenko beam-element runner).

**Promotion path:**
* Phase 22 A: built `run_buckling_cross_check` (C3D8 solid-element)
  + analytical helper. Solid-element verdict landed ~10× off Euler
  analytical (37,360 N vs 1,727 N) — honest scope reduction recorded
  FAIL verdict, case stayed tier_1_candidate.
* Phase 23 A: shipped `run_buckling_b31_cross_check` using ccx B31
  Timoshenko beam elements. Procedural INP composer (no gmsh). 20
  B31 elements along the column length. Observed P_cr 1730.7 N vs
  analytical 1727.2 N → **residual 0.21%** (vs 10% tolerance).
  Verdict PASS; case promoted to tier_2_validated.

## Geometry

A slender pinned-pinned steel column under axial compression. The
canonical setup:

| parameter | symbol | value | unit |
|---|---|---|---|
| length | L | 1.000 | m |
| section depth | h | 0.010 | m |
| section width | b | 0.010 | m |
| slenderness L/h | — | 100.0 | — |
| I_min (b·h³/12) | I | 8.333e-10 | m⁴ |
| Young's modulus (steel-s355) | E | 210e9 | Pa |
| end condition | — | pinned-pinned | — |

## Expected analytical (Euler)

P_cr = π²·E·I / (k·L)²
     = π² · 210e9 · 8.333e-10 / (1.0 · 1.0)²
     = 9.871 · 210e9 · 8.333e-10
     ≈ 1727 N

## Phase 22 A runner

`backend/app/services/cross_check/buckling_runner.py`:
* Composes a 20-element hex column INP (4 hexes through the column
  length per the n_elements_along=20 default; 1 hex through-section).
* Applies P_ref = 1000 N axial compression at the x=L face.
* `*STEP, PERTURBATION` + `*BUCKLE 4` requests the lowest 4
  eigenvalues.
* Reads λ from the `.dat` file; observed P_cr = λ · 1000 N.
* Tolerance 10% — comfortable for a 20-hex column with C3D8 elements
  on a half-sine mode shape.

## References

* Roark's Formulas for Stress and Strain, 8th ed., Table 12.1.
* Timoshenko & Gere, Theory of Elastic Stability, 2nd ed., §2.2.

## Claim envelope (Phase 22 A · post-promotion)

* claim_tier: tier_2_validated
* claim_boundary: tier2_real_solver_validated; not_signed_validation;
  cross_check_against_analytical
* claim_impact: Phase 22 A buckling cross-check delivered the
  promotion; second SOLVER KIND validated (Phase 18-21 was static +
  modal + plastic; Phase 22 A adds linear buckling).
