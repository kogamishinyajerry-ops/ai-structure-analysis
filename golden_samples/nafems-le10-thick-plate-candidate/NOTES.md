# NAFEMS LE10 — Thick Plate Pressure (published reference)

> **Tier 1 engineering candidate · analytical-only PUBLISHED-REFERENCE record.**
> NOT signed validation, NOT benchmark agreement, NOT a solved cross-check.

## What this case is (and is NOT)

Phase 38 A adds the **first NAFEMS-tagged entry** to the FM-04a cohort by
recording the *published* NAFEMS LE10 target stress as a reference value. **No
CalculiX solve is performed at this phase** (analytical-only, following the
Phase 33 D Hertz precedent). A real meshed `ccx` solve + signed residual
comparison against the −5.38 MPa target is deferred to the **Phase 41-43 NAFEMS
suite**.

The artifact is **`published_reference.yaml`**, deliberately **not**
`cross_check_verdict.yaml`. It records a *reference*, not a *verdict* — there is
no observed value, no residual, no cross-check. This naming keeps the case out
of the verdict cohort (the Phase 35 B `solver_kind` distribution pin globs
`*-candidate/cross_check_verdict.yaml`) and is honest: a published reference is
not a verdict.

### Honest correction of the Phase 38 blueprint

The blueprint specified `verdict: PASS` with `observed_value = analytical_value
= -5.38e6`. That would be a **tautological self-reference** — claiming a PASS by
copying the published number into both the "observed" and "analytical" slots,
with no real solve behind it. That is exactly the `cylinder-pv-candidate` defect
fixed on 2026-05-24 (Codex review R0 finding 1).

This case therefore records `verdict: "REFERENCE_ONLY"` + `analytical_only:
true`, lives in `published_reference.yaml` (not a verdict file), and is
**deliberately NOT registered** in
`backend/app/services/reporting/_claim_tier.py::CLAIM_TIER_REGISTRY`.
Analytical-only reference cases stay at the default `tier_1_candidate`; the
overlay only promotes registry members on a JSON `verdict == "PASS"`. Three
independent guards keep this case Tier 1: not-in-registry, overlay-only-visits-
registry-members, and verdict≠PASS.

## Benchmark definition (NAFEMS LE10)

| Property | Value | Provenance |
|---|---|---|
| Target | σ_yy = **−5.38 MPa** (compressive) at point D | magnitude confirmed across 4 CAE docs; sign per blueprint convention* |
| Point D | lower surface, inner-edge point on the minor axis | secondary CAE docs |
| Material | E = 210 GPa, ν = 0.3, ρ = 7800 kg/m³ | confirmed |
| Load | uniform normal pressure 1.0 MPa on upper surface | confirmed |
| BC | uy=0 (DCD'C'), ux=0 (ABA'B'), ux=uy=0 (BCB'C'), uz=0 (line EE') | confirmed |
| Geometry | outer ellipse 3.25×2.75 m, inner ellipse 2.0×1.0 m, t=0.6 m | standard parametrization** |

\* **Sign caveat** (Codex R0 finding 2). The published σ_yy at point D is
recorded as a **signed** value (−5.38e6 Pa, compressive) rather than a magnitude,
so the deferred Phase 41-43 signed residual check compares against the correct
sign. The **magnitude** 5.38 MPa is cross-confirmed across four CAE sources; the
**sign** follows the Phase 38 blueprint convention and must be re-confirmed
against the primary NAFEMS publication before any benchmark-agreement claim.

\*\* **Geometry caveat.** The dimensions above are the widely-cited NAFEMS LE10
parametrization used across the CAE community. The **primary source** (NAFEMS
TNSB Rev.3, 1990) was **not directly fetched** in this phase — every secondary
document consulted references the original NAFEMS publication for the geometry.
Material, loading, boundary conditions, and the 5.38 MPa target magnitude *were*
cross-confirmed via secondary CAE benchmark documentation (Bibliography below).
**Before any benchmark-agreement claim in the Phase 41-43 real solve, the
geometry and the stress sign must be verified against the primary NAFEMS
publication.**

## Bibliography

- **NAFEMS Publication TNSB Rev.3**, "The Standard NAFEMS Benchmarks",
  October 1990, ISBN 1-874376-04-0 — primary source; target σ_yy = 5.38 MPa at
  point D. (Cited, not directly fetched this phase.)
- Abaqus Benchmarks Guide — LE10 Thick Plate Pressure (material, load, BC, target).
- Altair OptiStruct Verification — OS-V: 0060 (LE10 model definition).
- University of Colorado CEAE §4.2.10 — LE10 (target confirmation).
