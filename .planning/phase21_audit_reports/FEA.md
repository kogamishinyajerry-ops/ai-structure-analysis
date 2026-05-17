# Phase 21 FEA testing agent — round 1 report

## Composite score
**68/100** (verdict: CHANGES_REQUIRED — still below 99 by 31 points)

## Phase 20 R1 baseline comparison
Prior FEA = 57/100 (Phase 20 R1, unchanged in R2). Blueprint projected
+8-15 from [2 new tier_2_validated flips + plasticity NLGEOM E2E pin].
**Observed delta: +11.** Mid of projection band.

## Dimension scores (each 0-20; sum / 5 = composite scaled to 100)

### Dim 1 — Cross-check rigor (analytical vs numerical)
**15/20** (Phase 20: 11/20; +4 — the load-bearing Phase 21 A lift)

Phase 20 closed with 1 tier_2_validated case (cylinder-pv). Phase 21 A
adds two more via real-ccx runners:
- `cantilever-beam-candidate`: residual -6.88% vs Euler-Bernoulli
  PL³/(3EI) at cl=0.015m (3611 nodes / 14787 C3D4 tets). Tolerance
  15%. Verdict PASS persisted at
  `golden_samples/cantilever-beam-candidate/cross_check_verdict.yaml`.
- `plate-with-hole-candidate`: residual -10.71% vs Howland K(2a/W=0.4)
  · σ_∞ at cl=0.003m (1841 nodes / 5745 C3D4 tets). Tolerance 20%.
  Verdict PASS persisted at
  `golden_samples/plate-with-hole-candidate/cross_check_verdict.yaml`.

Both runners use the same Phase 20 C `run_tier2_meshed_pipeline`
(gmsh → C3D4 → ccx). Both verdict files use the SAME schema as Phase
19 B (no parallel schema). The `_claim_tier.py` overlay promotes both
on next module load.

Honest gap (-5): residuals are 7-11%, not <5%. C3D4 linear tets are
shear-locking-prone on bending and high-gradient stress fields.
Tightening below 5% requires:
- C3D10 (quadratic tets) — adapter + gmsh both need C3D10 support.
- Adaptive mesh refinement at hole edges.
- C3D8I (incompatible-mode hexes) — needs structured hex meshing.

All Phase 22+ scope.

### Dim 2 — Solver coverage (analysis types validated)
**15/20** (Phase 20: 12/20; +3 — Phase 21 B plasticity NLGEOM)

Static + modal still work (Phase 18-19). Phase 21 B adds the
load-bearing E2E pin for plasticity:
`test_real_ccx_engages_bilinear_plasticity_above_yield` runs real ccx
on a 100mm steel-S355 cube with 4 MN tensile load
(σ_applied = 400 MPa, between σ_y=355 and σ_u=510). NLGEOM step with
INC=20 sub-increments. Observed: σ_zz_max = 450 MPa (uniform), ε_p ≈
12.4% — exactly what the bilinear curve [(0, 355MPa), (0.20, 510MPa)]
predicts. Cross-validated against an elastic-only baseline run with
the SAME geometry + load: plastic displacement is 66× the elastic
baseline (≥3× threshold).

Honest gap (-5): only one plastic case (uniaxial tension). No
buckling (Phase 21 P5 deferred), no contact, no transient dynamics,
no thermal coupling, no large-rotation NLGEOM beyond the small ε
regime. The bilinear curve is two-point — multi-point hardening
curves (e.g. Johnson-Cook) aren't exercised. Phase 22+ scope.

### Dim 3 — Mesh fidelity (real meshes vs single-element coupons)
**14/20** (Phase 20: 12/20; +2 — Phase 21 A two more meshed E2E runs)

Phase 20 C ended the single-element-coupon regime; Phase 21 A
exercises the meshed pipeline on two additional real-CAD geometries
(.geo → C3D4 → ccx). Combined Phase 21 A meshes produce 5452 nodes /
20532 elements across the two new cross-checks — non-trivial workouts
of the meshed pipeline at honest residual levels.

Honest gap (-6): still ONLY C3D4 linear tets. C3D8 hex meshing
(structured) gives ~2× better bending accuracy for the same node
count. C3D10 quadratic tets cut shear locking in half. Phase 21 A
runners stayed on C3D4 because the adapter only supports it.

### Dim 4 — Material library breadth
**14/20** (Phase 20: 14/20; no change — Phase 21 didn't add materials)

8 materials shipped Phase 19 C; nothing new in Phase 21. Plasticity
curves still exist only on steel-S355 + aluminium-6061-t6.

### Dim 5 — Production-gap (signed validation distance)
**10/20** (Phase 20: 8/20; +2 — honest nonlinear capability)

Phase 21 B's plasticity NLGEOM pin moves the harness materially
closer to "real engineering" capability — the difference between
linear-elastic-only and verified-nonlinear is large for industrial
acceptance. But still: no contact, no transient dynamics, no thermal,
no fracture, no fatigue, no signed validation packets, no commercial-
solver-equivalent benchmark. Tier 3 work multi-week.

## FEA composite
(15 + 15 + 14 + 14 + 10) / 5 × 5 = (68/100). Phase 20 was
(11+12+12+14+8)/5×5 = (57/100). +11 delta.

## Slice attribution
| Slice | FEA contribution | Honest gap |
|---|---|---|
| A | +4 Dim 1 (2 validated flips) +2 Dim 3 (more meshed runs) | residuals 7-11%, C3D4-bound |
| B | +3 Dim 2 (NLGEOM E2E) +2 Dim 5 (real nonlinear) | single plastic case, no buckling/contact/transient |
| C | None — frontend only | (UI domain) |
| D | None — frontend only | (UI domain) |

## Open Phase 22 carry-forward
1. **C3D10 quadratic tet adapter + gmsh wiring** — cut Phase 21 A
   residuals roughly in half.
2. **Buckling E2E pin** — the Phase 21 P5 blueprint promise that
   slipped.
3. **Contact prototype** — bullet-plate cohort (currently Tier 1
   declared) needs real ccx contact runner.
4. **Multi-material hardening curves** — extend `*PLASTIC` library
   from 2 to 5+ materials.
5. **Signed validation harness scaffold** — formal V&V documentation
   path; Tier 3 territory.

## Honest verdict
**FEA R1 = 68/100, CHANGES_REQUIRED.** Inside blueprint's 65-72
projection band, mid range. The Tier 2 validated count went 1 → 3
(promised lift delivered). Plasticity NLGEOM E2E pin closes Phase 20
retro #3. No game-changer toward 99 — the next 30 points require
contact, buckling, transient, signed validation, all multi-week.

Not signed validation; not benchmark agreement.
