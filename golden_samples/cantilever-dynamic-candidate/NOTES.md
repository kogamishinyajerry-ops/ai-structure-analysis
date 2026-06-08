# cantilever-dynamic-candidate — FM-04a Phase 30 A

> Tier 1 / Tier 2 engineering candidate; not signed validation; not
> benchmark agreement.

## What this case validates

**The first `*DYNAMIC` (transient implicit time integration)
validated case in the cohort.** Closes the FEA Dim 6 ballistic-
readiness floor that has been anchored at 50/100 for 11 phases
(Phase 18-29). Prior 9 cases used `*STATIC` / `*BUCKLE` /
`*FREQUENCY` only.

## Cross-validation logic

This case tests the SAME PHYSICAL SYSTEM as Phase 26 A's
`cantilever-beam-modal-candidate` (slender steel cantilever beam,
L=0.5m × h=w=0.020m, fixed at x=0) but VALIDATES IT VIA A
DIFFERENT SOLVER PATH:

- **Phase 26 A**: solve eigenvalue problem `det(K - ω²M) = 0` via
  CalculiX `*FREQUENCY` step → first natural frequency
  f_1 = 66.93 Hz observed (residual +0.13% vs analytical 66.84 Hz).
- **Phase 30 A**: integrate transient response numerically via
  `*DYNAMIC` step (Hilber-Hughes-Taylor with α=0 = Newmark
  trapezoidal, no numerical damping) → observed period 14.78 ms
  vs analytical T_1 = 1/f_1 = 14.96 ms, residual -1.19%.

The match across BOTH solver paths is independent corroboration of
the Euler-Bernoulli analytical envelope. If one path agreed and the
other didn't, the bug would be in the agreeing-path's solver
implementation, not the analytical theory.

## Configuration

- **Geometry**: 0.500 m × 0.020 m × 0.020 m steel cantilever
  (REUSE of Phase 26 A geometry, no new .geo file needed)
- **Material**: steel-s355 from SSOT library (E=210 GPa, ν=0.30,
  ρ=7850 kg/m³)
- **Mesh**: gmsh C3D10 quadratic tets, characteristic length
  0.012 m → 1,895 nodes / 814 elements (same as Phase 26 A)
- **BC**: u_x = u_y = u_z = 0 on all nodes at x=0 (clamped face)
- **Load**: half-sine impulse 200 N peak, 1 ms duration applied
  to all tip-face nodes (y-direction) via `*CLOAD, AMPLITUDE=IMPULSE`
- **Solver**: CalculiX `*DYNAMIC, ALPHA=0, DIRECT` with
  dt = 1.0e-4 s, t_total = 0.060 s (≈ 4 natural periods)
- **Output**: `*NODE FILE, NSET=NTIP, FREQUENCY=1` U at every step

## Result (live ccx 2026-05-18)

| Quantity | Value |
|---|---|
| analytical f_1 (Phase 26 A helper) | 66.84 Hz |
| analytical period T_1 = 1/f_1 | 14.9608 ms |
| observed period (zero-crossing analysis) | 14.7824 ms |
| residual |observed - analytical| / |analytical| | **-1.1928%** |
| verdict | **PASS** (envelope ±8%) |
| n_zero_crossings | 8 (over 4 periods + initial transient) |
| n_increments | 600 (fixed dt = 0.1 ms over 60 ms) |

## Why the residual sign is NEGATIVE

The observed period is SLIGHTLY SHORTER than analytical. Honest
attribution:

1. **Tip force vs distributed mass**: the impulse force shape (half-
   sine pulse on tip-face nodes) excites mainly mode 1 but also a
   small admixture of mode 3 (whose frequency is ~6.27× higher per
   Euler-Bernoulli (β₃/β₁)²). Mode 3 contamination shortens the
   apparent zero-crossing spacing slightly.

2. **C3D10 cross-section stiffening**: 3D solid tets carry through-
   thickness shear stiffness that pure-1D Euler-Bernoulli analytical
   ignores. This adds a small amount of effective bending stiffness
   → shorter period. Phase 26 A's eigenvalue solve saw +0.13%
   (period 0.13% TOO LONG; frequency 0.13% TOO HIGH = stiffer). Phase
   30 A sees -1.19% (period 1.19% TOO SHORT) — same direction
   (stiffness > analytical) but larger magnitude due to mode-mixing.

3. **HHT-α implicit integration with α=0**: Newmark trapezoidal is
   second-order accurate but introduces a small period error
   proportional to (dt/T)². With dt = 0.1 ms and T = 14.96 ms,
   (dt/T)² ≈ 4.5×10⁻⁵. Negligible vs 1.19%.

The cross-correlation with Phase 26 A's +0.13% confirms the
analytical envelope. The 1.19% magnitude is well within the ±8%
tolerance envelope (tighter than the ±15% Tier-2 grade).

## What this case does NOT validate

- Damped vibration (α=0 means structurally undamped; real beams
  have ζ ~ 0.001-0.01)
- Large deformation (linear *STEP, NLGEOM=NO; tip displacement
  remains in the small-deflection regime)
- Higher modes (only mode-1 dominated by the impulse shape)
- Explicit time integration (this is HHT-α implicit; explicit
  `*DYNAMIC, EXPLICIT` is reserved for ballistic-scale physics
  in a future phase)
- Variable time-step adaptivity (DIRECT forces fixed dt)
- Output frequency artifacts (FREQUENCY=1 outputs every step;
  high-frequency aliasing is not present)

These are deferred to future phases. The validated claim is narrow:
**clamped-free cantilever, isotropic linear-elastic, single-mode-
dominant impulse excitation, Newmark-trapezoidal implicit
integration, undamped free vibration** — reproduces the
Euler-Bernoulli natural-period analytical to within 1.2%.

## Anti-gaming guards

- **A:-1**: observed period derived from ZERO-CROSSING SPACING,
  NOT max-amplitude tracking (which could pad the verdict via
  numerical-noise bias near the peaks).
- **E:-1**: Courant time-step pin — dt < T_analytical / 20
  (default dt = 0.1 ms ≪ 14.96/20 = 0.75 ms; 7.5× safety).
- **E:-2**: damping pin — ALPHA=0 in the *DYNAMIC card (no
  numerical damping).
- **D:-3**: analytical helper reused VERBATIM from Phase 26 A's
  `cantilever_modal.py`; no parallel β₁L = 1.875104 definition.

## Files

- Runner: `backend/app/services/cross_check/cantilever_dynamic_runner.py`
- Tests: `backend/tests/test_phase30a_cantilever_dynamic.py`
- Verdict: `golden_samples/cantilever-dynamic-candidate/cross_check_verdict.yaml` (schema 1.2.0)
- Geometry: `golden_samples/cantilever-dynamic-candidate/data/cantilever_dynamic.geo` (copy of Phase 26 A's)

Tier 1 / Tier 2 engineering candidate; not signed validation; not
benchmark agreement.
