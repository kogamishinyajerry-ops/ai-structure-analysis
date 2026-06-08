# `hertz-contact-candidate` · scope notes (Phase 33 D infra → Phase 34 C validated)

> Tier 2 real-solver validated (Phase 34 C); not signed validation; not
> benchmark agreement. The *CONTACT PAIR solver machinery is ccx-validated via
> a stacked-cube uniaxial proxy — NOT Hertz curvature contact (future work).

## Status

**Phase 34 C outcome: tier_2_validated** (supersedes the Phase 33 D
INFRASTRUCTURE_ONLY status below). Live ccx 2.23 *CONTACT PAIR cross-check
PASS — 1D-exact δ=F·H/(E·A), residual −6.82% within the 20% envelope; cohort
11 → 12. Honest scope: validates the contact-pair SOLVER mechanism, NOT Hertz
curvature contact. Evidence: `cross_check_verdict.yaml`.

### Historical — Phase 33 D (superseded by Phase 34 C above)

**Phase 33 D outcome: INFRASTRUCTURE_ONLY** — analytical SSOT only; not yet a
tier_2_validated case at that time. The live ccx validation landed in Phase
34 C, which is the current status above.

## What Phase 33 D shipped

| Component | Path | LOC | Status |
|---|---|---|---|
| Hertz line-contact analytical helper | `backend/app/services/cross_check/hertz_contact.py` | 161 | Live |
| Analytical pin tests (17 tests, Johnson textbook values) | `backend/tests/test_phase33d_hertz_contact_analytical.py` | 232 | All passing |
| Scaffolded candidate directory | `golden_samples/hertz-contact-candidate/` | (this NOTES + expected_results.json) | Ready |
| Honest deferral documentation | (this file) | — | Documented |

## What Phase 33 D did NOT ship (deferred to Phase 34)

- `hertz_contact_runner.py` (the runner that composes the CCX INP,
  invokes ccx, parses .frd, computes residual)
- `data/hertz_contact.geo` (gmsh script for cylinder + block)
- `cross_check_verdict.yaml` (validated-case verdict; requires a
  live ccx run + residual computation)
- Live ccx execution + residual measurement
- Integration with `convergence_study.py` (if applicable)

## Why the pivot

### Honest reason 1: session budget

Full *CONTACT PAIR runner implementation following the Phase 31 A
heat_transfer_runner template (~510 LOC) + geometry generation +
ccx convergence iteration was estimated at 3-5 hours. Phase 33 D's
session budget was ~45 minutes after Phase 33 A/B/C. Splitting the
work into Phase 33 D (analytical) + Phase 34 (runner + ccx) is
scope-disciplined per v2.3 sub-DEC pattern.

### Honest reason 2: geometry-load regime issue

The canonical analytical example used for the tests
(R=0.010 m, F=1000 N, S355 steel) yields a peak Hertzian pressure
p_0 = 428.5 MPa, which **exceeds S355 yield stress (355 MPa) by
~21%**. This means the pure-elastic Hertz assumption is marginal
for this specific input pair; a live ccx run with elastic-plastic
material model would diverge from analytical at the contact zone.

Phase 34 must re-tune the geometry: either enlarge R (so contact
strip widens at constant load, reducing p_0) or reduce F. Per the
expected_results.json deferral block, the proposed Phase 34
geometry is R=0.050 m + F=5000 N → p_0 ≈ 271 MPa (well within
S355 yield), δ ≈ 4 µm (small but measurable with refined mesh).

### Honest reason 3: ADR-002 CanonicalField enum

`CDIS` (contact displacement) and `CSTR` (contact stress) are the
CCX outputs that natively capture contact-pair results. Neither is
in the canonical_field enum in `reader.py` (ADR-002 lock). The
Phase 31 A NOTES.md flagged this explicitly. Phase 34 will measure
**vertical displacement (DISP) at the top of the cylinder** vs
analytical δ — this uses the canonical DISP field already in the
enum, avoiding an enum extension RFC.

## Phase 34 plan (committed scope)

1. Write `cylinder_on_block.geo` gmsh script:
   - Two solid bodies (cylinder + block)
   - Cylinder centered on block top with line contact at z=H_block
   - Mesh refinement near contact zone (cl ≈ b/4 ≈ 0.5 mm at contact;
     cl ≈ 5 mm at far field)
2. Write `hertz_contact_runner.py`:
   - Compose CCX INP with `*CONTACT PAIR, TYPE=NODE TO SURFACE`,
     `*SURFACE INTERACTION` with `LINEAR` pressure-overclosure
   - Apply vertical force on cylinder top via `*CLOAD` distributed
     load
   - Fix block bottom via `*BOUNDARY 1, 3, 0` on all bottom nodes
   - Output: `*NODE PRINT, NSET=CYLINDER_TOP, U` to read δ
3. Invoke `CalculiXRunner` with NLGEOM=NO step
4. Parse .dat for U_z at the cylinder top center node
5. Compute residual_pct(observed_delta, analytical_delta)
6. Write `cross_check_verdict.yaml` with `solver_kind:
   contact_pair_static` + `schema_version: 1.4.0`
7. Pin 6+ new tests on the verdict YAML

## Phase 34 entry criteria

This case is ready to enter Phase 34 when:
- Phase 33 closes locally (E1 audit + FINAL + retro + STATE
  refresh + commit)
- A Phase 34 blueprint is written committing to the contact-pair
  runner + ccx integration as Phase 34 A or B slice scope

## Related work elsewhere in tree

- `backend/app/services/cross_check/hertz_contact.py` — analytical
  SSOT (lives here, not in this directory; module-level reuse)
- `backend/app/services/cross_check/heat_transfer_runner.py` —
  Phase 31 A precedent for "new solver-kind runner" pattern
- `.planning/audits/phase33c_REBASELINE.md` — re-baseline that
  flagged Dim 1 as 78 (12th case is the natural lift)
- `.planning/FM-04A_PHASE33_TOP_TIER_FULL_FLOW_AI_FEA_BLUEPRINT.md` —
  the Phase 33 blueprint that originally scoped this slice as
  "33 D *CONTACT PAIR Hertz Tier-1 lift"

## Anti-gaming guards

- A:-1 — analytical pin tests use independent textbook values, NOT
  regression-against-self
- B:-1 — verdict YAML reserves `verdict: INFRASTRUCTURE_ONLY` to
  prevent counting this case as validated
- C:-1 — Phase 33 D commit message + Phase 33 D contribution to
  FINAL audit explicitly notes Dim 1 stays at 78 (no cohort lift)
- D:-3 — Hertz formulas live in ONE module; runner (Phase 34) will
  import them, not duplicate
- E:-1 — no fabricated δ values in expected_results.json (only
  analytical computed from helper)

Tier 1 / Tier 2 engineering candidate; not signed validation;
not benchmark agreement.
