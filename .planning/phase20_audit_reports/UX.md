# Phase 20 UX testing agent — round 1 report

## Composite score
**62/100** (verdict: CHANGES_REQUIRED)

## Phase 19 round-1 baseline comparison
Prior UX = 67/100. Phase 20 prompt expected +11-18 uplift from
[Slice A material_id route wiring + Slice D candidate roster +
ResultMesh primitive migration]. **ACTUAL observed delta: -5**
(62 vs 67). Phase 19 had two killers — (a) material swap was vapor,
(b) cylinder-pv was invisible. Phase 20 fixed (a) cleanly
(`backend/app/api/routes/solver.py:66-95` truly consumes material_id
via `compose_material_id_inp`) but Slice D **did not** fix (b) — the
candidate-case roster in the Sidebar still ships with only the
Phase 19 fallback set (GS-102 ×3 + leak case;
`frontend/src/candidateCaseRegistry.ts:46-110`). Neither
`cylinder-pv-candidate`, `plate-with-hole-candidate`, nor
`cantilever-beam-candidate` appears in `FALLBACK_CANDIDATE_CASES`
(grep across `frontend/src/` returns zero matches for each).
Additionally a new wiring defect was introduced: the Sidebar
candidate roster sets `selectedCandidateCaseId` but **not**
`activeCaseId`, while both `runSolver` (`App.tsx:631`) and the
Cmd-K `cmd-run-solver` handler (`App.tsx:1474`) gate on
`activeCaseId`. Clicking cylinder-pv in the roster (if it existed)
would not enable Run Solver — a novel two-state-tree confusion the
Sidebar roster brought back to the same task that Phase 19 flagged.

## Task scores

### Task 1 — Find the leak case (rod-wave-impact-energy-leak-candidate)
- (a) Task completion: 4/4 — `candidateCaseRegistry.ts:96-109` registers
  the case in the static fallback. Sidebar's new candidate-case roster
  surfaces it directly via test-id `candidate-case-rod-wave-impact-energy-leak-candidate`
  (`Sidebar.tsx:222-269`, fed by `App.tsx:1580-1583`). Novice now has
  a left-rail entry, not just the buried CandidateCasePicker dropdown.
  +1 over Phase 19.
- (b) Click count: 4/4 — left-rail Sidebar → "Rod-wave impact · ENERGY LEAK"
  is now 1 click. Phase 19 required 3.
- (c) Error recovery: 2/4 — fallback works
  (`candidateCaseRegistry.ts:182-190`). But **clicking it only sets
  `selectedCandidateCaseId`** (`App.tsx:1585-1592`); `activeCaseId`
  stays null, so the Topbar breadcrumb still says "Session"
  (`App.tsx:1604`) and Run Solver is disabled (`Topbar.tsx:103`
  `showRunControls={Boolean(activeCaseId)}`). The two-state-tree split
  is a real recovery hazard with no in-UI explanation. -2.
- (d) Onboarding: 2/4 — `displayLabel: 'Rod-wave impact · ENERGY LEAK
  case (Tier 1)'` (`candidateCaseRegistry.ts:97`) hints. No tutorial
  callout. No cohort-dashboard badge flagging it as the leak fixture
  (grep `leak` in `CohortDashboardPanel.tsx` → 0 hits). The label
  still says "ENERGY LEAK case" without saying *intentionally* broken
  fixture. Unchanged from Phase 19.
- (e) Plain-language: 3/4 — `notesExcerpt` calls it "the canonical
  'what does a broken case look like?' fixture"
  (`candidateCaseRegistry.ts:103-106`). Same as Phase 19.
- **Subtotal: 15/20** (Phase 19: 13/20; +2 from roster surfacing)

### Task 2 — Submit `needs_more_evidence` signoff
- (a) Task completion: 4/4 — `SignoffSubmissionForm.tsx` still iterates
  `SUPPORTED_SIGNOFF_VERDICTS` including `needs_more_evidence`. No
  Phase 20 changes; functionality preserved.
- (b) Click count: 3/4 — narrative tab → scroll to
  `SignoffHistoryPanel` (`App.tsx:1720`) → reviewer field → verdict
  dropdown → submit. Form is not surfaced from Cmd-K palette (the
  registry at `App.tsx:1495-1551` has zero signoff commands —
  unchanged). -1.
- (c) Error recovery: 3/4 — 422 and 429 rendered inline. Unchanged.
- (d) Onboarding: 2/4 — no explanation what `needs_more_evidence`
  means vs `approve_tier1`. Unchanged.
- (e) Plain-language: 3/4 — verdict names remain snake_case
  engineering tokens. Unchanged.
- **Subtotal: 15/20** (Phase 19: 15/20; no change — Phase 20 did not
  touch signoff)

### Task 3 — Trigger ccx re-run on cylinder-pv-candidate via Cmd-K
- (a) Task completion: 1/4 — Palette opens (binding `mod+k`,
  `App.tsx:1554`). `cmd-run-solver` exists (`App.tsx:1518-1525`). But
  `cylinder-pv-candidate` is **STILL NOT in `FALLBACK_CANDIDATE_CASES`**
  (`candidateCaseRegistry.ts:46-110` — registry contains only
  `GS-102-candidate`, `GS-102-refined-candidate`, `GS-102-hifi-candidate`,
  and `rod-wave-impact-energy-leak-candidate`; grep
  `cylinder-pv-candidate frontend/src/` → 0 hits). The Phase 20 prompt
  claim that Sidebar surfaces cylinder-pv + plate-with-hole + cantilever
  is **false against current `App.tsx:1580-1583`**, which feeds the
  Sidebar from `FALLBACK_CANDIDATE_CASES` verbatim. Even if it were
  selected, the wiring at `App.tsx:1585-1592` sets only
  `selectedCandidateCaseId`, not `activeCaseId`, and the palette's
  `cmd-run-solver` handler still early-returns when
  `!activeCaseId` (`App.tsx:1474-1478`). End-to-end: same Phase 19
  failure mode, now in a worse two-state-tree shape.
- (b) Click count: 1/4 — minimum stated: ⌘K → "cylinder" → Enter
  (3 actions). Actual: case is unreachable from Cmd-K at all.
- (c) Error recovery: 2/4 — `_runSolverFromPalette` warns to
  devtools when no case selected (`App.tsx:1476`); no user-visible
  feedback in the palette. Unchanged.
- (d) Onboarding: 3/4 — Cmd-K hint chip in Sidebar
  (`Sidebar.tsx:108-141`). Unchanged.
- (e) Plain-language: 2/4 — command label "Run CalculiX solver on
  active case" (`App.tsx:1519`) — engineering jargon. Unchanged.
- **Subtotal: 9/20** (Phase 19: 9/20; no change — Slice D claim
  unmet, prompt's "cylinder-pv + plate-with-hole + cantilever in
  candidate roster" does not match the code)

### Task 4 — Swap material from steel to aluminium and re-run
- (a) Task completion: 3/4 — **Phase 20's real win.** Backend now
  consumes `material_id`: `backend/app/api/routes/solver.py:18-21`
  imports `compose_material_id_inp` + `Tier2PipelineError`; lines
  66-95 branch on `request.material_id` and synthesize a real INP
  via `compose_material_id_inp(case_dir, jobname, material_id)`;
  line 134 returns `material_reference` in the response body. Frontend
  sends `material_id: selectedMaterial.id` in both run flows
  (`App.tsx:655, 1491`). End-to-end the swap now actually changes
  what ccx solves. -1: the frontend does **not** read or display
  `material_reference` from the JSON response (grep
  `material_reference frontend/src/` → 0 hits), so the reviewer has
  no in-UI confirmation that the swap propagated. They still believe
  it worked only on faith.
- (b) Click count: 2/4 — narrative tab → scroll to material picker →
  click + Run Solver. Cmd-K aluminium command exists
  (`App.tsx:1532-1537`) so palette path is faster but still ~3
  actions plus the Run Solver action. Picker buried mid-page
  unchanged.
- (c) Error recovery: 3/4 — backend now returns 422 with citation
  to the library SSOT when material_id is unknown
  (`solver.py:87-94`). Real improvement. -1: the frontend's
  `runSolver` catch block (`App.tsx:659-664`) only logs the detail
  to the in-app console; no banner explaining what to do.
- (d) Onboarding: 2/4 — no "this run used material X" badge in the
  result panel (grep `material_reference` → 0 hits in frontend).
  Picker has material names but the result view does not echo the
  picked material back. +1 over Phase 19 because the swap is now
  real, but onboarding gap unchanged.
- (e) Plain-language: 3/4 — material names human-readable in palette.
  Unchanged.
- **Subtotal: 13/20** (Phase 19: 9/20; +4 from real end-to-end wiring)

### Task 5 — View resulting stress contour overlay
- (a) Task completion: 2/4 — Same SVG polygon rendering as Phase 19
  (`ResultMeshPlaybackPanel.tsx:195-207`). `summary.valueMin/valueMax`
  still come from generic `fieldRanges`
  (`resultMeshPlayback.ts:185-198`). The "field" label shown to the
  reviewer is the generic `DEFAULT_FIELD_LABEL = 'Result field'`
  (`resultMeshPlayback.ts:80`) unless the .frd sidecar emits a label.
  No von Mises tensor computation visible.
- (b) Click count: 3/4 — visual tab → Run Solver → result loads.
  Unchanged.
- (c) Error recovery: 3/4 — **Phase 20's other real win.** Slice D
  migrated bespoke `<div>` to `SkeletonCard` / `ErrorCard` /
  `EmptyStateCard` primitives (`ResultMeshPlaybackPanel.tsx:158-173`).
  Error now has structured `code="RESULT-MESH-LOAD"` plus
  `remediation` bullets — actionable for a novice. +1 over Phase 19.
- (d) Onboarding: 1/4 — legend still reads "Field value"
  (`ResultMeshPlaybackPanel.tsx:252`) not "von Mises stress (MPa)".
  No probe / hover / field-switcher. No legend caption explaining
  colour→stress mapping. Unchanged.
- (e) Plain-language: 2/4 — "Field value · min X · max Y"
  (`ResultMeshPlaybackPanel.tsx:251-264`) is engineering shorthand.
  No unit. Reviewer cannot tell stress from displacement from
  temperature from the legend alone. Unchanged.
- **Subtotal: 11/20** (Phase 19: 10/20; +1 from primitive migration's
  error path improvement)

---

## Composite arithmetic
T1 15 + T2 15 + T3 9 + T4 13 + T5 11 = **63/100** raw.

T4 (a) earns 3/4 not 4/4 because the response.material_reference is
returned by the backend but ignored by the frontend — material swap
visibly works but invisibly so. Honesty rule: feature is real, but
reviewer cannot verify it from the UI alone. Composite revised by
-1 charity floor to reflect this verification gap: **62/100**.

## Top 3 deficiencies (with file:line citations)

1. **Phase 20 Slice D's headline claim is wrong.** The prompt asserts
   "cylinder-pv + plate-with-hole + cantilever now in left-rail
   candidate roster". `frontend/src/candidateCaseRegistry.ts:46-110`
   only contains `GS-102-candidate`, `GS-102-refined-candidate`,
   `GS-102-hifi-candidate`, `rod-wave-impact-energy-leak-candidate`.
   `grep -rn "cylinder-pv-candidate" frontend/src/` → 0 hits;
   `plate-with-hole-candidate` → 0 hits; `cantilever-beam-candidate`
   → 0 hits. `App.tsx:1580-1583` feeds the Sidebar verbatim from
   that fallback. T3 (a) floored to 1/4 because the prompt's target
   case is still unreachable from Cmd-K.

2. **Sidebar candidate roster has a two-state-tree wiring defect.**
   `App.tsx:1585-1592` only mutates `selectedCandidateCaseId`;
   `activeCaseId` (`App.tsx:446`) stays null. Run Solver requires
   `activeCaseId` (`App.tsx:631` early-return; `Topbar.tsx:103`
   `showRunControls={Boolean(activeCaseId)}`). Cmd-K `cmd-run-solver`
   also requires `activeCaseId` (`App.tsx:1474`). So a novice
   clicking a candidate-roster entry sees the Sidebar highlight
   change but no Run Solver button appears in the Topbar — silent
   failure with no surfaced explanation. T1 (c) floored to 2/4 over
   this hazard.

3. **Phase 20 A backend material wiring is real but invisible.**
   `backend/app/api/routes/solver.py:66-95` correctly composes the
   material-aware INP; line 134 returns
   `material_reference: "EN 10025-2:2019 §7.3"` etc. But
   `grep -rn "material_reference" frontend/src/` → 0 hits. The
   frontend ignores the field. Reviewer cannot confirm from the UI
   that the swap propagated; they have to read backend logs. T4 (a)
   capped at 3/4 over this onboarding gap.

## One specific UX improvement that would lift the lowest-scoring task

**Lowest-scoring task: T3 = 9/20.** Two micro-changes, ~30 LOC total
(true spike-class):

1. Add `cylinder-pv-candidate`, `plate-with-hole-candidate`, and
   `cantilever-beam-candidate` entries to `FALLBACK_CANDIDATE_CASES`
   (`candidateCaseRegistry.ts:46-110`) with `displayLabel`s like
   "Cylinder PV · pressure-vessel cross-check (Tier 2 validated)"
   so the roster contains the cases the prompt claimed.
2. Fix the two-state-tree wiring in `App.tsx:1585-1592` to also
   call `setActiveCaseId(id)` (and ideally synthesize an
   `availableCases`-shaped fallback entry so the Topbar breadcrumb
   resolves). This single line lets Run Solver and Cmd-K
   `cmd-run-solver` fire on candidate cases without needing them to
   appear in the DB-backed `/cases` route.

Estimated cost: ~25 LOC + 1 test. Expected lift: T3 sub-(a) from
1/4 to 4/4 (task completable from Cmd-K alone), sub-(b) from 1/4 to
4/4 (3 actions: ⌘K → "cylinder" → Enter), sub-(e) from 2/4 to 3/4
(label becomes plain-language if a `cmd-run-cylinder-pv-candidate`
alias is added). Estimated T3 subtotal lift: 9/20 → 16/20
(**+7 composite**, landing the workbench in the 69-73 band — still
below the 78-85 blueprint projection but the honest delta).

## Honest disclosure
- I did not boot `npm run dev`; this is a static-code audit.
- Phase 20 A (material wiring) is genuinely landed and I did read
  the route handler end-to-end (`solver.py:52-135`); my T4 score
  reflects what is reachable from the *UI surface*, not what the
  backend can do.
- Phase 20 C (gmsh plate-with-hole pipeline) and Phase 20 B
  (plasticity / cantilever runner deferred to Phase 21) do not
  surface in the workbench UX I scored, so they do not move the
  novice-usability needle even though they are real backend wins.
  This is the rubric working correctly: a feature that exists only
  in `tier2_pipeline.run_tier2_meshed_pipeline` but has no
  left-rail entry is invisible to a novice reviewer.
- The composite 62 is strictly the floor reading. If the user
  accepts charity credit for backend Slices A/B/C (real, tested,
  but not surfaced in UI), 70-72 is defensible. I am reporting the
  floor per the prompt's "do not round up" rule.
- Phase 20 closure on this audit would be **CHANGES_REQUIRED**.
  The 2-fix (1) above is spike-class (≤30 LOC + 1 test) and would
  lift the composite into the high-60s; reaching 78-85 requires the
  signoff Cmd-K command (Phase 19 T2 carry-forward), the stress
  legend wording fix (T5 (d)/(e)), and the `material_reference`
  surface (T4 (a)/(d)).
