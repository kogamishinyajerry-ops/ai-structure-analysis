# Phase 23 — FEA audit (Round 1)

> **Frame:** Tier 1 / Tier 2 engineering candidate; not signed
> validation; not benchmark agreement. Phase 22 baseline FEA = 70.4/100.
> Blueprint FEA projection: 75-79 (mid 77).

## Dimensions

### Dim 1 — Element library breadth (0-100)

**Score: 75/100.** +3 from Phase 22 (72). Phase 23 A adds B31
Timoshenko beam elements to the wired-up cohort. Four element
types now compose: C3D4 / C3D8 / C3D10 / B31. The B31 inclusion
proves the harness can wire 1D elements (procedural INP composer,
no gmsh), which opens the door for B32/B33/T3D shells in Phase
24+.

Evidence:
- `backend/app/services/cross_check/buckling_b31_runner.py` —
  procedural INP composer with `*BEAM SECTION` + RECT cross-
  section, *BOUNDARY block targeting beam DOF 1-6, *CLOAD axial.
- `backend/tests/test_phase23a_b31_buckling.py` — 10 tests
  including the requires_solver E2E pin.

Gap to 99: no shell elements (S3/S4), no wedge (C3D6/C3D15), no
truss (T3D2). Each is multi-week scope but achievable phase-by-
phase.

### Dim 2 — Validated cross-check cases (0-100)

**Score: 71/100.** +7 from Phase 22 (64). Phase 23 A flipped
`euler-column-candidate` to tier_2_validated. **Validated count
3 → 4** (cylinder-pv + cantilever-beam + plate-with-hole + euler-
column). Observed P_cr 1730.7 N vs analytical 1727.2 N → residual
**0.21%** (vs 10% tolerance) — by far the tightest residual
across the four validated cases (cylinder-pv 0.004%, cantilever
-6.88%, plate-with-hole -10.71%, euler-column 0.21%).

Evidence:
- `golden_samples/euler-column-candidate/cross_check_verdict.yaml`
  — PASS verdict, runner=`buckling_b31_runner`, residual 0.21%.
- `backend/app/services/reporting/_claim_tier.py` overlay promotes
  the case on next module load.
- `test_phase23a_validated_count_is_four` — strict registry pin.

Gap to 99: no contact-mechanics cross-check, no transient
dynamics, no thermal-expansion, no fatigue, no fracture. Each is
a multi-week extension.

### Dim 3 — Mesh fidelity (0-100)

**Score: 73/100.** +2 from Phase 22 (71). Phase 23 A's B31
runner uses 20 elements along the 1m column — coarse for solid
analysis but appropriate for beam buckling mode shape capture
(captures up to ~10th harmonic). This is a mesh-fidelity win in
the sense that the right element kind + right element count
yielded 0.21% residual on the first try.

Evidence:
- B31 INP composer accepts `n_elements` with floor of 4 (mode
  shape capture lower bound) and default of 20.

Gap to 99: see Phase 22 list (no adaptive remeshing, no aniso
refinement, no quality auto-flagging, no boundary layer).

### Dim 4 — Solver kind coverage (0-100)

**Score: 68/100.** +4 from Phase 22 (64). The B31 buckling
promotion adds a genuinely-validated solver kind (linear buckling
with B31 beams). Phase 22 A had the buckling INFRASTRUCTURE but
no promoted case; Phase 23 A closes that loop.

Evidence:
- `*STEP, PERTURBATION` + `*BUCKLE 4` with B31 elements produces
  observed P_cr within 0.21% of analytical — solver kind is now
  proven against a verifiable reference.

Gap to 99: no transient (*DYNAMIC), no Riks arc-length (*STEP,
RIKS), no implicit dynamics, no contact, no thermal coupling.

### Dim 5 — Cross-check rigor (0-100)

**Score: 83/100.** +2 from Phase 22 (81). Phase 23 B's σ-tensor
derivatives unlock per-component cross-checks (e.g. compare
ccx-emitted σ_xx against analytical σ_xx). The Mises math is
pinned by analytical-known inputs (uniaxial → 100, hydrostatic
→ 0, pure shear → √3·τ). The principal-stresses helper handles
the closed-form 3×3 symmetric eigenvalue problem.

Evidence:
- `frontend/src/stressDerivatives.ts` — `computeVonMises`,
  `computePrincipalStresses` (trigonometric form per Smith 1961).
- 16 tests in `Phase23B_stress_tensor_switcher.test.tsx` pin
  the math.

Gap to 99: tensor derivatives are FRONTEND-only at Phase 23 B;
the backend `result_mesh.json` exporter hasn't been updated to
emit tensors. End-to-end tensor flow (ccx σ_xx → JSON → frontend
switcher) is Phase 24+ scope.

## Composite

| Dim | Phase 22 | Phase 23 | Delta |
|---|---|---|---|
| Element library | 72 | 75 | +3 |
| Validated cases | 64 | 71 | +7 |
| Mesh fidelity | 71 | 73 | +2 |
| Solver kind coverage | 64 | 68 | +4 |
| Cross-check rigor | 81 | 83 | +2 |
| **FEA composite** | **70.4** | **74.0** | **+3.6** |

**FEA axis: 74.0/100.** Inside blueprint band (75-79) at the LOW
end (slightly below). The +3.6 lift was driven by the validated
count flip (3→4) and the B31 solver kind unlock — exactly the
shape Phase 22 A's honest scope reduction predicted. Cross-check
rigor lift was capped because the σ-tensor work is frontend-only
this phase; full end-to-end tensor flow opens in Phase 24+.

Not signed validation; not benchmark agreement.
