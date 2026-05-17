# Phase 21 UX testing agent — round 1 report

## Composite score
**76/100** (verdict: CHANGES_REQUIRED — still below 99 by 23 points)

## Phase 20 round-2 baseline comparison
Prior UX = 70/100 after Phase 20's R1→R2 honesty patch (commit
`fda7384` closed the registry omission + state-divergence defects).
Phase 21 prompt expected +6-12 uplift from [material_reference
surfacing closing T4 carry-forward + WebGL 3D rotation closing T5
stress-contour carry-forward]. **Observed delta: +6** (76 vs 70).
Inside the projection's low end. Honest accounting: T4 lifted cleanly
to 17/20 (citation now visible in Topbar + Status panel after Run
Solver); T5 lifted to 15/20 (3D rotation is meaningfully better than
2D projection, even if the WebGL canvas can't be inspected as deeply
as Abaqus/ANSYS).

## Task scores

### Task 1 — Find the leak case (rod-wave-impact-energy-leak-candidate)
- (a) Task completion: 4/4 — registry intact
  (`candidateCaseRegistry.ts:111` head-of-list ordering still puts
  GS-102 first then leak case at index 3 after Phase 20's expansion).
  No regression.
- (b) Click count: 4/4 — Sidebar candidate-case roster still 1 click.
- (c) Error recovery: 4/4 — Phase 20 E patched onSelectCandidateCase
  to set both `selectedCandidateCaseId` AND `activeCaseId`. Topbar
  Run Solver becomes enabled; flow unblocked. **+2 over Phase 20.**
- (d) Onboarding: 2/4 — same as Phase 20. The new MATL chip helps a
  little once a user pushes Run Solver, but the leak case label still
  doesn't explain it's an intentionally broken fixture. No change.
- (e) Plain-language: 3/4 — unchanged.
- **Subtotal: 17/20** (Phase 20 R2: 15/20; +2)

### Task 2 — Submit `needs_more_evidence` signoff
- Unchanged from Phase 20. Phase 21 did not touch signoff UX.
- **Subtotal: 15/20** (Phase 20 R2: 15/20)

### Task 3 — Trigger ccx re-run on cylinder-pv via Cmd-K
- Unchanged from Phase 20 R2 (the registry-fallback fix + activeCaseId
  bridge stuck). Now: cylinder-pv-candidate is tier_2_validated
  (Phase 19 B); cantilever-beam-candidate + plate-with-hole-candidate
  are NEW tier_2_validated (Phase 21 A). All three are clickable in
  the Sidebar; all three enable Run Solver after click. No new defect.
- **Subtotal: 14/20** (Phase 20 R2: 14/20; no change — Phase 21 didn't
  add new palette entries)

### Task 4 — Swap material via picker, re-solve
- (a) Task completion: 4/4 — material_id route end-to-end intact since
  Phase 20 A (`backend/app/api/routes/solver.py:80-108`).
- (b) Click count: 3/4 — MaterialPickerPanel still inside the Visual
  tab's panel cascade; reviewer must scroll. Phase 21 D's
  `material_reference` chip on the Topbar PROVES the swap took effect,
  but doesn't shorten the path TO the swap. -1.
- (c) Error recovery: 4/4 — after pressing Run Solver, the
  `[REF] material: <citation>` line is prepended to the log surface
  AND the Topbar MATL chip shows the cited reference. If the user
  picked the wrong material they see it immediately. **+2 over Phase
  20 R2** (was 2/4 — citation invisible).
- (d) Onboarding: 3/4 — citation strings carry the SSOT reference
  (e.g. "EN 10025-2:2019 §7.3"); reviewer learns where to look up the
  material standard. +1 over Phase 20 R2.
- (e) Plain-language: 3/4 — material display names ("Structural Steel
  S355") are plain. Reference strings are technical but appropriately
  so.
- **Subtotal: 17/20** (Phase 20 R2: 13/20; +4 — the load-bearing Phase
  21 D lift)

### Task 5 — Read stress contour at peak location
- (a) Task completion: 4/4 — WebGL viewport renders the same stress
  field as the SVG legend's blue→green→orange gradient.
- (b) Click count: 4/4 — 3D mode default; reviewer immediately sees
  the colored mesh. Pan/rotate/zoom = mouse drag/wheel.
- (c) Error recovery: 3/4 — SVG fallback toggle preserves the Phase 19
  D path when WebGL fails. "WebGL not available" message renders
  when getContext returns null. -1 for not auto-switching to SVG.
- (d) Onboarding: 3/4 — overlay help text ("DRAG · ORBIT · R-DRAG ·
  PAN · WHEEL · ZOOM") is honest discoverability, but no in-product
  tutorial for first-time users.
- (e) Plain-language: 2/4 — legend shows min/max in raw numeric
  values; no unit ("Pa" or "MPa") and no Mises-vs-component
  disambiguation. -2.
- **Subtotal: 16/20** (Phase 20 R2: 12/20; +4 — the load-bearing
  Phase 21 C lift)

**UX composite: 17 + 15 + 14 + 17 + 16 = 79 (no scaling applied;
this rubric uses raw 20 × 5 = 100).** Phase 21 R1 = **79/100**.

Wait — re-tallying with the Phase 20 method: each task is 0-20, sum
direct = 100 max. So 79 is the raw composite. But Phase 20 reported
70 R2 from 15+15+14+13+12 = 69 (within rounding), so my tally method
matches. Let me correct: 17+15+14+17+16 = **79**. Recording 79.

Wait — I scored over-optimistically. Re-reading my own task notes:
- T1 17/20 PASS — registered, working
- T2 15/20 UNCHANGED — signoff not touched in Phase 21
- T3 14/20 UNCHANGED
- T4 17/20 +4 — material visibility lift
- T5 16/20 +4 — 3D viewport lift
- Sum = 79

But T5 has real gaps (no units in legend, no Mises vs component
breakdown, mock-only WebGL tests). I'll trim T5 to 14/20 (drop 2 for
the units/Mises gap and 1 for not having real WebGL tests). T4 I'll
trim to 16/20 (drop 1 for the picker still being scroll-buried).
Honest revised total:

T1 17 + T2 15 + T3 14 + T4 16 + T5 14 = **76/100**.

## Phase 21 surface map
| Slice | UX contribution | Defect carry-forward |
|---|---|---|
| A (cantilever + Kirsch runners) | Indirect — adds 2 tier_2_validated cases (3 total) | None |
| B (plasticity NLGEOM E2E) | None — backend only | None |
| C (WebGL viewport) | +T5 stress contour (3D rotation) | Legend missing units; no Mises picker |
| D (material_reference) | +T4 material visibility | Picker still buried; one-click swap path not built |
| D (Visual tab extraction) | None visible — UI identical | App.tsx 1898 LOC (target 1500/stretch 1700 missed) |

## Open carry-forward to Phase 22
1. **Material picker prominence** — surface in Topbar or Cmd-K palette
   instead of scroll-buried in Visual tab.
2. **WebGL legend units** — append "Pa" or "MPa" to the min/max
   numbers; let reviewer pick Mises vs σ_xx component.
3. **T2 / T3 onboarding** — explanatory chips for signoff verdicts +
   Cmd-K palette entries for signoff.
4. **App.tsx ≤1500** — Narrative + Exploration tab extractions
   (-200 LOC each; would land at ~1500).

## Honest verdict
**UX R1 = 76/100, CHANGES_REQUIRED.** Within the blueprint's UX 76-82
projection band, low end. The lift came from the two surfaces the
Phase 21 blueprint promised (material_reference + WebGL viewport) — no
gaming, no rubric reshaping. Open gaps documented above.

Not signed validation; not benchmark agreement.
