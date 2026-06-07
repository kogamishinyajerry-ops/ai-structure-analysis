# Rotating annular disk, centrifugal load — CalculiX public-benchmark agreement

> **Tier-2 real-solver validated public-benchmark agreement** (NOT signed validation).
> The project's **third** public-benchmark agreement and its **first centrifugal /
> rotational-body-force** load. ccx 2.23 reproduces the classical Timoshenko plane-stress
> rotating-disk hoop stress at the bore: **observed 65.353 MPa vs analytic 65.312 MPa,
> +0.063%** (canonical mesh), with the σ_θ(r)/σ_r(r) profile **along the +x radial line**
> matching to ±0.1%.

## What this case is

A thin steel annular disk (inner radius a = 0.2 m, outer radius b = 1.0 m) spinning at
ω = 100 rad/s about its axis. The centrifugal body force ρω²r is reacted by an in-plane
stress field with closed-form plane-stress solution (Timoshenko & Goodier, *Theory of
Elasticity*, Art. 32):

```
σ_r(r)     = (3+ν)/8 · ρω² · [ b² + a² − a²b²/r² − r² ]
σ_θ(r)     = (3+ν)/8 · ρω² · [ b² + a² + a²b²/r² − (1+3ν)/(3+ν)·r² ]
σ_θ(a)     = ρω²/4 · [ (3+ν)b² + (1−ν)a² ]   = 65.312 MPa   ← headline target
```

## Why this is a CLEAN ccx agreement (the lesson from LE3 / FV52)

This benchmark was chosen *specifically* because its reference is a **continuum
(plane-stress) elasticity** quantity (an exact stress field), not a reduced-kinematic
plate/shell/beam theory. The two preceding 3rd-benchmark attempts failed for the
opposite reason:

| case | reference theory | ccx solver (3-D elasticity FE) | residual | clean? |
|---|---|---|---|---|
| LE3 (hemisphere shell) | thin-shell displacement | solid-shell C3D20R | **+8.3%** | ✗ formulation gap |
| FV52 (thick plate modal) | Mindlin-plate frequency | C3D20 / C3D8I | **−6%** | ✗ formulation gap |
| **rotating disk** | **plane-stress elasticity stress** | **C3D20** | **+0.06%** | ✓ **clean** |

The generalisation, now confirmed on five benchmarks: **ccx (full 3-D elasticity FE)
cleanly reproduces CONTINUUM-ELASTICITY references** — closed-form stress fields,
whether 3-D (LE10 +1.08%, LE11 +0.38%) or plane-stress (rotating disk +0.06%) — and
**systematically disagrees with reduced-KINEMATIC plate/shell/beam-theory references**
(LE3, FV52) by several percent that refinement does not close. Plane stress is a
continuum-elasticity reduction (exact in the thin limit), NOT an assumed displacement
kinematics like Kirchhoff/Mindlin — so a thin 3-D solid converges to it. The rotating
disk therefore has no reduced-kinematic gap; refinement drives the residual to zero.

## Convergence (residual CLOSES — contrast LE3/FV52 which grow)

| nr/edge | nodes | σ_θ(a) (MPa) | residual |
|--------:|------:|-------------:|---------:|
|      20 |  4725 |       65.591 |   +0.43% |
|      32 | 11781 |       65.428 |   +0.18% |
|  **48** | **26117** | **65.353** | **+0.063%** |
|      64 | 46085 |       65.323 |   +0.02% |
|      80 | 71685 |       65.308 |   −0.01% |

Monotone convergence to the analytic 65.312 MPa. Canonical = nr=48 (+0.063%, tol 1.0%).

The radial-line profile check (`generator.py --profile`) confirms σ_θ(r) and σ_r(r)
**along the +x radial line** match the closed form to within ±0.1% (one radial line at
the top surface — not a circumferential or through-thickness sweep), and σ_r(a) ≈ 0.11
MPa ≈ 0 verifies the free inner-bore boundary.

## Model

- **3-D quarter annulus** (double symmetry), C3D20 hexahedra — the proven LE10/LE11 element.
- **Half thickness** modelled with z=0 **mid-plane symmetry** (uz=0); free top surface →
  plane-stress state (σ_z ≈ 0) for the thin disk. Full disk thickness 0.10 m.
- Radial-edge symmetry: uy=0 on the y=0 edge, ux=0 on the x=0 edge.
- **Centrifugal load** via ccx `*DLOAD ... CENTRIF`, magnitude = **ω² = 10000** (ccx CENTRIF
  takes the *square* of the rotational speed), axis = global z through the origin.
- Hoop stress read as **SYY** at the bore node on the +x axis (there θ ‖ global y).
- ccx renumbers/extrapolates nodal stress to the `.frd` STRESS block; the reader stops at
  the `-3` block terminator so the trailing `-4 ERROR` estimate block is never misparsed.

## Provenance / honesty

- **Tier:** tier_2_validated (real ccx 2.23) / public-benchmark agreement. **NOT signed
  validation** (no independent reviewer signoff per ADR-023 / ADR-027 G-2).
- **Reference:** closed-form Timoshenko & Goodier plane-stress rotating-disk solution,
  reproduced across standard elasticity texts and FE verification manuals (ANSYS APDL VM,
  code_aster). Timoshenko & Goodier is itself a textbook; the point is the canonical
  formula is not gated by any single paywalled benchmark document (unlike the NAFEMS
  LE-series). Honest limitation: exact ANSYS-VM / code_aster case IDs are not pinned.
- **Cohort:** registered in `CLAIM_TIER_REGISTRY` (tier_1 baseline → overlay-promoted to
  tier_2 on this PASS verdict) + `CANONICAL_TOLERANCES` (1.0%). Admitted to the V2-0
  residual-floor cohort via `cross_check_verdict.yaml`.
- **Reproduce:** `python golden_samples/rotating-disk-centrifugal-candidate/data/generator.py [--ladder] [--profile]`
