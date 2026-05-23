# C3D6 wedge — uniaxial Hooke's law (6th element class)

> **Tier 2 real-solver validated** · genuine cross-check (real ccx + analytical).
> Not signed validation; not benchmark agreement.

## What this case is

Phase 38 B adds the **6th element class** to the FM-04a validated cohort.
Prior 5: C3D4 / C3D8 / C3D10 / S4 / B31. This case exhibits **C3D6** — the
6-node linear pentahedral wedge — via a real ccx solve of a single wedge held
in pure uniaxial stress, cross-checked against the closed-form Hooke's law.

Unlike the analytical-only Phase 38 A NAFEMS reference, this is a **genuine
cross-check**: real ccx produces the observed stress; the analytical is the
independent Hooke's law σ = E·ε. They agree exactly (constant-strain element →
0.00% residual), so the case is promoted to `tier_2_validated`.

## Model

- **Geometry:** one right triangular prism (C3D6); base = 0.1 m legs; height
  = 0.1 m.
- **Material:** S355 steel, E = 210 GPa, ν = 0.3.
- **BC:** bottom triangle z-clamped + statically-determinate in-plane pins
  (node 1 ux=uy=0, node 2 uy=0, node 3 ux=0) so the lateral faces stay
  traction-free → **pure uniaxial stress**, Poisson contraction unconstrained.
  Top triangle prescribed `uz = −ε·height` (ε = 1e-3).
- **Analytical:** σ_zz = −E·ε = −210 MPa (compressive). A positive applied
  strain produces a compressive axial stress.

## Live ccx result

| quantity | value |
|---|---|
| analytical σ_zz | −2.10e8 Pa |
| observed σ_zz (ccx) | −2.10e8 Pa |
| residual | −0.00 % (exact; constant-strain element) |
| verdict | PASS → tier_2_validated |
| tolerance | 1.0 % |

## Reproduce

`app.services.cross_check.wedge_c3d6_runner.run_wedge_c3d6_cross_check(...)`
writes the INP (`app.adapters.calculix.inp_writer.write_single_c3d6_wedge_
uniaxial_inp`), runs ccx, reads σ_zz, and computes the residual. Re-running is
a deliberate offline action; the committed `cross_check_verdict.yaml` is the
persisted result the `_claim_tier` overlay reads to promote the case.

Tier 2 real-solver validated; not signed validation; not benchmark agreement.
