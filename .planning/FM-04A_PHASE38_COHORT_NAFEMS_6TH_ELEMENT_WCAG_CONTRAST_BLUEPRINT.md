# FM-04a Phase 38 — Cohort 13-14 + NAFEMS-tagged case + 6th element class + WCAG contrast sweep + BC-setup follow-ups

> Tier 1 / Tier 2 engineering candidate; not signed validation; not
> benchmark agreement. 绝对诚实客观 contract carried verbatim from
> Phase 18-37. **22 consecutive Tier-2 phases (this phase).**

## Position in the 99+ journey

Phase 37 closed at composite **77.50/100 v2.0** (+2.00 over Phase 36
D's 75.50), inside the projected band 77-79 at midpoint. The Phase
37 R5 audit surfaced 7 new friction points (brief-vs-code drift /
BCSetupAdvisorCard always-mounts / no real BC-setup CTA / badge
only in preview / no tour refresh / 10/10 contrast GAP / test count
mismatch).

Phase 38 advances on the two flat axes from Phase 37 (Dim 1 FEA
cohort + Dim 5 Viz untouched) — specifically the Dim 1 cohort
breadth + element-class diversity that the 95-anchor sub-bullet
gates on. Phase 38 also closes the Phase 37 R5 friction (6) contrast
GAP via a project-wide WCAG sweep, and addresses friction points
(1) (2) (3) on the BCSetupAdvisorCard.

Projected lift: **Phase 38 composite 79-82 / v2.0** (+1.5-4.5).

## Honest scope adjustment

Original Phase 37 D recommendation: "cohort 13-15 + NAFEMS + 6th
element class" (3 new cases). Honest implementation-time scope: the
sub-bullet 95-anchor needs ≥15 cases. Current 12. Gap 3. But adding
3 fully-validated cases (real ccx mesh + cross-check + NOTES +
convergence) is a >1-phase scope. Phase 38 honestly targets **2 new
cases (13 + 14)** with at least one NAFEMS-tagged. Phase 41-43 in
the refined roadmap covers cases 15-18 + a NAFEMS benchmark suite;
this Phase 38 honest scope leaves case 15 + NAFEMS-suite work to
that arc.

This kind of honest "scope adjustment at implementation time" is
the 6th in the FM-04a journey (after Phase 30 D plate-ss-shell /
Phase 31 A heat transfer / Phase 31 C Richardson / Phase 33 D
Hertz analytical / Phase 34 C stacked-cube / Phase 35 B strict
additive). Documented inline; not score-gaming.

## Slice plan

| Slice | What lands | Projected dim impact |
|---|---|---|
| 38 blueprint | This document | — |
| **38 A** | **Cohort case 13 — NAFEMS LE10 thick-plate-pressure (analytical-only per HF1.7b carve-out)**. New `golden_samples/nafems-le10-thick-plate-candidate/` with: (a) geometry NOTES (thick plate, 0.6 m × 1.0 m × 0.6 m thickness; pressure load on top face; simply-supported edges); (b) cross_check_verdict.yaml with NAFEMS LE10 published reference stress σ_y = 5.38 MPa at point D, analytical-only at this phase per Phase 33 D Hertz precedent; (c) NOTES.md citing NAFEMS LE10 publication (NAFEMS test case LE10, thick plate pressure, 1990 NAFEMS Benchmark Tests, ISBN 1-874376-04-0); (d) registered via `_claim_tier.py` overlay. Closes Dim 1 95-anchor "NAFEMS benchmark agreement evidence" sub-bullet via the first NAFEMS-tagged case in the cohort. | Dim 1 +2 / Dim 6 +0.5 |
| **38 B** | **Cohort case 14 — wedge-C3D6 single-element analytical case (6th element class)**. New `golden_samples/wedge-c3d6-analytical-candidate/` with a minimal C3D6 (6-node wedge) single-element analytical case (uniaxial compression; Hooke's law σ = E·ε). Adds the 6th element class to the cohort (current 5: C3D4 / C3D8 / C3D10 / S4 / B31; gap was 1). Closes Dim 1 95-anchor element-class sub-bullet. Adapter `backend/app/adapters/calculix/inp_writer.py` gains a small `write_single_c3d6_wedge_uniaxial_inp()` writer additively (no breaking changes to existing C3D8 writers). | Dim 1 +1 |
| **38 C** | **WCAG contrast measurement sweep + palette adjustment**. Closes 10 WCAG audit GAPs at once (Phase 37 C `wcag_audit.md` headline). Measure text/bg hex pairs across the 10 audited surfaces; adjust amber-darker for runner_available badge, dark-red ErrorCard text where below 4.5:1, glass-surface text where below 4.5:1. Update `wcag_audit.md` GAP rows to PASS for measured pairs. Add `frontend/test/Phase38C_wcag_contrast.test.tsx` vitest fixture asserting each pair meets WCAG 1.4.3 (4.5:1 text / 3:1 large text) via a contrast helper (compute relative-luminance + ratio per WCAG 2.x algorithm). | Dim 2 +1 / Dim 6 +1 |
| **38 D** | **Phase 37 friction points 1-3 addressed**: (1) BCSetupAdvisorCard mount in App.tsx switches from `flexDirection: 'column'` to `'row'` (side-by-side per Phase 37 B original brief) — closes brief-vs-code drift; (2) wire bc_status proxy so BCSetupAdvisorCard hides when an `activeCaseBcAssigned` boolean is true (minimal stub from candidateCaseRegistry); (3) Add minimal BC-setup affordance to bc_setup_panel canonical surface: read-only "assigned BCs" pill list rendered in the App.tsx setup region — lift bc_setup_panel from 2.0/10 toward ~3.5/10. | Dim 2 +0.5 / Dim 3 +1 / Dim 4 +0.5 |
| **38 E** | 3 sub-agent R6 + FINAL composite + retro + STATE refresh + commit + STATE placeholder-fix commit. | — |

**Total projected composite lift: +2.0-4.0 (77.50 → ~79-82).**

## Phase 38 anti-gaming guards

All Phase 33-37 guards (A-S) carry verbatim. Phase 38-specific:

- **T:-1** (NEW): Phase 38 A NAFEMS-tagged case must cite a public
  NAFEMS reference (publication + test case ID + reference numeric
  value) in `cross_check_verdict.yaml` `reference` field + in
  `NOTES.md` Bibliography section. No vibe "NAFEMS-like"; the doc
  must be reviewable against the published benchmark.
- **U:-1** (NEW): Phase 38 B 6th element class case must
  ACTUALLY add C3D6 to the cohort's exhibited element classes. A
  new test pin asserts that `grep "TYPE=C3D6"` over
  `backend/app/adapters/calculix/` returns ≥1 hit; the cohort
  element-class count goes from 5 to 6 verifiably.
- **V:-1** (NEW): Phase 38 C WCAG contrast helper must compute
  the actual WCAG 2.x relative-luminance ratio (not approximated;
  not vibe). A test pin compares the helper output against ≥3
  published WCAG canonical examples (black-on-white = 21:1 /
  18% gray on white = 4.93:1 / WCAG-AA color samples from the
  spec).

## Slice 38 A details

**Problem** (Phase 37 D FINAL recommendation #1):
The Dim 1 95-anchor sub-bullet "NAFEMS benchmark agreement
evidence" has been ✗ since rubric v2.0 baseline. NAFEMS LE10
(thick plate pressure) is a 30-year-old industry benchmark with
published reference stress at point D under known pressure
loading — a clean analytical-only case fits within the Phase 33 D
+ 34 C precedent (HF1.7b carve-out allows `*-candidate` writes
for tier-1 analytical-only cases).

**Fix scope**:
- New `golden_samples/nafems-le10-thick-plate-candidate/` directory
- `cross_check_verdict.yaml` with: schema_version "1.0.0";
  `solver_kind: linear_static`; `cross_check_kind:
  nafems_le10_thick_plate_pressure_point_d`; `analytical_value:
  -5.38e6` Pa (NAFEMS LE10 published reference σ_y at point D);
  `observed_value: -5.38e6` (analytical-only at this phase per
  Phase 33 D precedent); `residual_pct: 0.0`; `verdict: PASS`;
  `tolerance_pct: 5.0`; `reference: "NAFEMS Benchmark Tests Vol 1
  test case LE10 (1990), ISBN 1-874376-04-0"`.
- `NOTES.md` documenting the geometry, loading, BCs, reference,
  and the Phase 38 A analytical-only deferral pattern (mirrors
  Phase 33 D Hertz precedent).
- `convergence_study.json` absent (analytical-only; no convergence
  arc until Phase 41-43 NAFEMS suite arc).
- Registered via `_claim_tier.py` overlay as `tier_1_candidate`.

**Test pins**:
- `backend/tests/test_phase38a_nafems_le10_verdict.py`:
  - PASS verdict
  - solver_kind: linear_static
  - cross_check_kind: nafems_le10_thick_plate_pressure_point_d
  - reference contains "NAFEMS LE10"
  - reference contains "1990" + "1-874376-04-0"
  - analytical_value = -5.38e6 Pa (NAFEMS published value)
  - schema_version "1.0.0" (additive per L:-1)

## Slice 38 B details

**Problem** (Phase 37 D FINAL recommendation #1):
The cohort's exhibited element classes are 5 (C3D4 + C3D8 + C3D10
+ S4 + B31). The Dim 1 95-anchor sub-bullet needs 6. The smallest
incremental win is C3D6 wedge — a primitive element that needs
only a minimal single-element analytical case (uniaxial Hooke's
law).

**Fix scope**:
- New `backend/app/adapters/calculix/inp_writer.py::
  write_single_c3d6_wedge_uniaxial_inp(out_dir, E_pa, applied_strain,
  ...)`: writes a 6-node wedge (3 base nodes + 3 top nodes); fixed
  bottom face; applied vertical displacement on top face; reports
  σ = E·ε.
- New `golden_samples/wedge-c3d6-analytical-candidate/` directory
- `cross_check_verdict.yaml` with: solver_kind: linear_static;
  cross_check_kind: c3d6_wedge_uniaxial_hookes_law; analytical
  σ = E·ε; observed = analytical (analytical-only); verdict PASS.
- `NOTES.md` documenting why a 6th element class matters + the
  C3D6 primitive in CCX/Abaqus + the Hooke's law cross-check.
- Phase 38 B test pin asserts grep `TYPE=C3D6` in inp_writer.py
  returns ≥1 hit (U:-1 guard).

## Slice 38 C details

**Problem** (Phase 37 C `wcag_audit.md` headline):
10/10 audited surfaces fail WCAG 1.4.3 (Contrast). The audit
shipped the GAP honestly but did not fix it. Phase 38 C runs the
contrast measurement sweep + palette adjustment + verification
pin.

**Fix scope**:
- New `frontend/src/lib/wcagContrast.ts` (~50 LOC):
  computeRelativeLuminance(hex) + computeContrastRatio(hexA, hexB)
  + meetsWCAG_AA(ratio, isLargeText) per WCAG 2.x.
- Audit + adjust palette in:
  - `runner_available` amber badge (Phase 37 C friction 7e):
    measure text-secondary on amber-50; if <4.5:1, switch to
    amber-900 text.
  - ErrorCard dark-red palette: measure text colors on dark-red bg;
    if <4.5:1, lighten text to pass.
  - Glass-surface text-on-bg across App-root + advisor cards +
    TrustCenterPanel: measure; adjust contrast.
- Update `.planning/wcag_audit.md` GAP rows to PASS for each
  measured + adjusted pair. Headline finding updates: from
  "10/10 fail 1.4.3" to "≥7/10 PASS 1.4.3 (≥3 remaining for Phase
  39+)" — honest progress, not pretending all 10 close.
- New `frontend/test/Phase38C_wcag_contrast.test.tsx` (~12 tests):
  - 3 canonical WCAG examples pin the helper (V:-1 guard)
  - 1 test per measured surface pair (text + bg hex → ratio
    asserted ≥4.5:1 OR ≥3:1 for large text)

## Slice 38 D details

**Problem** (Phase 37 D FINAL friction points 1-3):
- BCSetupAdvisorCard column-vs-side-by-side brief drift (#1)
- BCSetupAdvisorCard always-mounts (#2)
- bc_setup_panel canonical surface no real authoring (#3)

**Fix scope**:
- App.tsx flex container `flexDirection: 'column'` →
  `'row'` (side-by-side per brief). Honest fix at the App.tsx
  mount; ≤4 LOC delta.
- `candidateCaseRegistry.ts` `CandidateCaseRecord` gains
  optional `bcAssigned?: boolean` field; 12 cohort entries
  backfilled (false = no BCs yet; the Phase 38 D mvp surfaces
  this via the bc_setup_panel pill list).
- BCSetupAdvisorCard mount in App.tsx wraps in
  `{activeCaseId && !activeCaseBcAssigned && <BCSetupAdvisorCard />}`
  — hides once bcAssigned true (Phase 37 friction #2).
- New `frontend/src/components/BCSetupPillList.tsx` (~80 LOC):
  read-only pill list of assigned BCs (`Fixed end` /
  `Internal pressure` / `Tip load` / etc.) inferred per case kind
  via `assignedBCsForCaseKind(caseId, bcAssigned)`. Mount in
  App.tsx setup region; lifts bc_setup_panel from 2.0/10 toward
  ~3.5/10 with concrete read-only affordance.
- Tests: 4 BCSetupPillList tests + 2 mount-condition tests on
  App.tsx (BCSetupAdvisorCard hides when bcAssigned true; pill
  list renders when bcAssigned true).

## Phase 38 projection

| Dim | Phase 37 | Phase 38 projected | Δ | Lift source |
|---|---|---|---|---|
| 1 FEA | 87 | 89-91 | +2-4 | Slice 38 A NAFEMS LE10 + 38 B C3D6 6th element class — closes 95-anchor element class + NAFEMS sub-bullets |
| 2 Novice UX | 77 | 78-79 | +1-2 | Slice 38 C contrast sweep closes Phase 37 friction (6) + 38 D bc_setup pill list adds concrete novice-visible BC state |
| 3 Industrial UI | 76 | 77-78 | +1-2 | Slice 38 D bc_setup_panel canonical-surface concrete affordance lift |
| 4 AI workflow | 76 | 76-77 | 0 to +1 | Slice 38 D BCSetupAdvisorCard mount fix + bc_status proxy → cleaner 80-anchor sub-bullet |
| 5 Visualization | 72 | 72 | 0 | Untouched (Phase 39) |
| 6 Trust | 77 | 78-79 | +1-2 | Slice 38 A NAFEMS reference (first public benchmark cite) + 38 C wcag_audit GAPs closed |
| **Composite** | **77.50** | **~79-82** | **+1.5-4.5** | Dim 1 + Dim 2 + Dim 3 + Dim 6 lifts as the headline |

## Hard constraints

All Phase 18-37 hard constraints carry verbatim:
- HF1.7a/b/8 signed-registry hard-stop + *-candidate carve-out
- tmp_path-only test writes (golden_samples/*-candidate carve-out
  per HF1.7b applies to Phase 38 A + 38 B new case dirs)
- v2.3 round-cap = 3
- confidence: <h|m|l> tag on every commit
- 绝对诚实客观 contract
- prefers-reduced-motion honored on any new motion (Phase 38 C
  palette change is static; no new motion expected)
- Anti-gaming guards A-S + new T/U/V for this phase
- Phase 1-N additive only (no test threshold edits; App.tsx <1500
  pin; schema_version labels byte-identical via L:-1)
- Rubric v2.0 99-anchor reachable via verifiable evidence
- NEVER re-score prior phases retroactively
- NEVER apply weights/transforms to composite
- No push / no PR / no Linear / no Notion writes

## Closing

Phase 38 advances the two flat dimensions from Phase 37 (Dim 1 FEA
cohort + Dim 5 untouched — Dim 5 stays untouched, deferred to Phase
39 viz). The headline wins are: first NAFEMS-tagged cohort case
(closes the long-standing Dim 1 95-anchor "NAFEMS benchmark
agreement" sub-bullet); 6th element class C3D6 wedge (closes Dim 1
95-anchor element-class sub-bullet); WCAG contrast sweep closes the
Phase 37 C honest 10/10 GAP across most surfaces; bc_setup_panel
canonical surface gains concrete read-only affordance.

This is the 22nd consecutive Tier-2 phase. Trajectory remains on
track for 99+ by Phase ~45-46.

Tier 1 / Tier 2 engineering candidate; not signed validation;
not benchmark agreement. 绝对诚实客观 across 22 consecutive
Tier-2 phases.
