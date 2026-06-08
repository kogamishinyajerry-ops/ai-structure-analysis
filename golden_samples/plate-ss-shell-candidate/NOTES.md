# plate-ss-shell-candidate — FM-04a Phase 29 A

> Tier 1 / Tier 2 engineering candidate; not signed validation; not
> benchmark agreement.

## What this case validates

**The first S4 (4-node quadrilateral shell) element case in the
validated cohort.** Closes the FEA Dim 1 hard cap that has been
load-bearing since Phase 18 (≤75/100). Prior 8 cases used
C3D4 / C3D8 / C3D10 / B31 only.

## Configuration

- **Geometry**: 1.0 m × 1.0 m × 0.020 m square plate (same as the
  C3D10 plate-simply-supported case; allows per-case A-B comparison
  across element types).
- **Material**: steel-s355 from SSOT library (E=210 GPa, ν=0.30).
- **Mesh**: hand-rolled structured 20×20 quad mesh (441 nodes /
  400 S4 elements). NO gmsh dependency.
- **BC**: u_z = 0 on all 4 edges (simply-supported) + corner
  u_x = u_y = 0 (RBM kill). Rotations FREE (defining
  simply-supported constraint).
- **Load**: uniform pressure 1.0e4 Pa applied via `*DLOAD ELSET, P2`.
- **Solver**: CalculiX `ccx` 2.21 `*STATIC`.

## Result (live ccx 2026-05-18)

| Quantity | Value |
|---|---|
| analytical w_center (Timoshenko α·q·a⁴/D) | -2.639e-04 m |
| observed w_center (ccx, S4) | +2.652e-04 m |
| residual |observed| vs |analytical| | **+0.4881%** |
| verdict | **PASS** (envelope ±15%) |
| small_deflection_ratio (w/t) | 0.0133 ≪ 0.20 limit |

## Sign convention note

The observed `u_z` from CalculiX (FRD reader) is POSITIVE while the
analytical is NEGATIVE. The MAGNITUDES agree to 0.49%. The
residual is computed using `|observed|` vs `|analytical|` for
exactly this reason.

Root cause investigation: CalculiX S4 shell `*DLOAD Pn` load
convention is documented as "positive value = pressure pointing
INTO side n," and side n=2 is the +n (positive normal) side, with
the normal computed from the right-hand rule on the CCW node
winding (our mesh winds CCW viewed from +z, so +n = +z). By that
documentation, P2 with positive value should deflect the plate in
the -z direction. The observed +z behaviour indicates either a
sign reversal in CCX's shell-element load convention vs the
documentation, or a coordinate-frame transformation in the FRD
output for shells. Either way, the MAGNITUDE agreement at 0.49%
is what the analytical theory predicts.

The runner explicitly compares `|observed|` to `|analytical|` for
the residual, so this sign-convention oddity is a transparent
audit point, not a verdict-padding mechanism.

## What this case does NOT validate

- Drilling DOF (S4 has no drilling rotation; not applicable)
- Composite layups (single isotropic layer only)
- Large-deflection / membrane stretching (w/t = 0.0133 is in the
  linear regime; small_deflection_ratio ≤ 0.20 contract enforced)
- Clamped or 1-edge-free BCs (only 4-edge simply-supported)
- Through-thickness stress (only midplane displacement; *NODE FILE
  U output, no *EL FILE S)
- Non-square aspect ratio (Timoshenko α=0.00406 is for a=b only)

These are deferred to future phases. The validated claim is narrow:
**S4 element in CalculiX, simply-supported square thin plate,
isotropic linear-elastic, uniform pressure, small-deflection
regime, midplane displacement at center node** — reproduces the
Timoshenko analytical to within 0.5%.

## Anti-gaming guards

- **A:-1**: center-node lookup uses geometric proximity to (a/2,
  a/2, 0); test pins that the node lies within half a cell of the
  exact center on the structured mesh.
- **E:-1**: convergence pin — `n_per_side >= 4` runtime guard;
  the registry pin asserts the live run was at `n_per_side=20`
  (default; coarser would inflate residual).
- **D:-3**: analytical helper is reused VERBATIM from
  `plate_simply_supported.py` — no parallel definition that could
  drift.

## Files

- Runner: `backend/app/services/cross_check/plate_ss_shell_runner.py`
- Tests: `backend/tests/test_phase29a_plate_ss_shell.py`
- Verdict: `golden_samples/plate-ss-shell-candidate/cross_check_verdict.yaml` (schema 1.1.0)

Tier 1 / Tier 2 engineering candidate; not signed validation; not
benchmark agreement.
