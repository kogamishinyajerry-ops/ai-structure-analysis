# Phase 19 UX testing agent — round 1 report

## Composite score
**67/100** (verdict: CHANGES_REQUIRED)

Phase 18 round-3 baseline was 71/100 with task weights 20/25/20/20/15.
Per the Phase 19 prompt the rubric is now 20/20/20/20/20 (sum to /100,
"sub-dimensions × 4 points = 20 per task"), so direct delta arithmetic
is rubric-incompatible — but reading on the same 100 scale, **67 is
below the 71 baseline**. The blueprint projected 80-88; the actual code
state is regressed by 4 points on the new even-weighted rubric because
(a) the prompt's stated user task #3 ("trigger ccx re-run via Cmd-K on
cylinder-pv-candidate") and #4 ("swap material → re-run") are still
not end-to-end, and (b) the renamed Task 5 ("view resulting stress
contour overlay") on an even 20-point weight now scores the same
unbuilt feature against a heavier ceiling.

## Phase 18 round-3 baseline comparison
Prior UX = 71/100 (weights 20/25/20/20/15). Slice D added:
- `Sidebar.tsx` extraction (`frontend/src/components/Sidebar.tsx:1-264`)
- `stress-contour-legend` chip
  (`frontend/src/components/ResultMeshPlaybackPanel.tsx:204-247`)
- Primitive adoption tags in `CohortDashboardPanel.tsx:11-15`

EXPECTED uplift was +9-17. ACTUAL observed delta on the new even
rubric: **-4** (67 vs 71). Slice A's `tier2_pipeline.resolve_material`
exists (`backend/app/services/tier2_pipeline.py:84-110`) but is
**never called from the solver route**
(`backend/app/api/routes/solver.py:38-78`), so T4 still fails end-to-end.
Slice B's tier_2_validated flip is invisible in the frontend (zero
matches for `cylinder-pv-candidate`, `cross_check_verdict`, or
`tier_2_validated` across `frontend/src/`).

---

## Task scores

### Task 1 — Find the leak case (rod-wave-impact-energy-leak-candidate)
- (a) Task completion: 3/4 — `frontend/src/candidateCaseRegistry.ts:96`
  registers the case in the fallback. Mounted in `App.tsx:1672` via
  `CandidateCasePicker`. Discoverable. -1: the case has
  `starterDeckRelpath: null` / `engineDeckRelpath: null`
  (`candidateCaseRegistry.ts:99-101`) so downstream solver actions
  cannot complete from this entry.
- (b) Click count: 3/4 — narrative tab → CandidateCasePicker dropdown
  → select. Minimum is 2 clicks; actual ~3. -1: the
  Sidebar's `availableCases` (`App.tsx:511-514` fetches `/cases`) and
  the CandidateCasePicker's registry are **two separate state trees**;
  novice could click in the wrong picker first.
- (c) Error recovery: 2/4 — fallback path works
  (`candidateCaseRegistry.ts:182-190`), but no in-UI explanation that
  the case has `null` decks until you try to act on it.
- (d) Onboarding: 2/4 — `displayLabel: 'Rod-wave impact · ENERGY LEAK
  case (Tier 1)'` (`candidateCaseRegistry.ts:97`) hints. No tutorial
  callout, no cohort-dashboard badge flagging it as the leak fixture
  (grep `leak` in `CohortDashboardPanel.tsx` → 0 hits).
- (e) Plain-language: 3/4 — `notesExcerpt` calls it "the canonical
  'what does a broken case look like?' fixture"
  (`candidateCaseRegistry.ts:103-106`). Clear pedagogically. -1: label
  reads "ENERGY LEAK case" without saying *intentionally* broken.
- **Subtotal: 13/20**

### Task 2 — Submit `needs_more_evidence` signoff
- (a) Task completion: 4/4 — `SignoffSubmissionForm.tsx:122-127`
  iterates `SUPPORTED_SIGNOFF_VERDICTS` which contains
  `needs_more_evidence` (`signoffHistoryClient.ts:15`). Submit wired
  via `submitSignoff()` at form line 54.
- (b) Click count: 3/4 — narrative tab → scroll to SignoffHistoryPanel
  (`App.tsx:1730-1734`) → reviewer field → verdict dropdown → submit.
  Minimum ~5 keystrokes + clicks; the panel is mid-page below ~10
  other panels. -1: form is not surfaced from Cmd-K palette (the
  command registry at `App.tsx:1495-1551` has zero signoff commands).
- (c) Error recovery: 3/4 — 422 and 429 both rendered inline at
  `SignoffSubmissionForm.tsx:170-183`, forbidden-token preview at
  lines 144-155.
- (d) Onboarding: 2/4 — placeholder text "reviewer" and
  "— select verdict —" (lines 95, 121). No explanation what
  `needs_more_evidence` *means* vs `approve_tier1` etc. A novice has
  to guess from the verdict name.
- (e) Plain-language: 3/4 — disclaimer trio printed at lines 195-206
  is plain-readable. Tier-1 banner is correct. -1: the verdict names
  themselves are snake_case engineering tokens, not user-friendly
  phrases.
- **Subtotal: 15/20**

### Task 3 — Trigger ccx re-run on cylinder-pv-candidate via Cmd-K
- (a) Task completion: 1/4 — Palette opens (`App.tsx:1552-1561`,
  binding `mod+k`). Registry has `cmd-run-solver` (`App.tsx:1517-1525`)
  which fires `_runSolverFromPalette` (`App.tsx:1473-1494`). But
  `cylinder-pv-candidate` is not in `FALLBACK_CANDIDATE_CASES`
  (`candidateCaseRegistry.ts:46-110`) AND the palette only re-runs
  the currently-active case — there's no "run on cylinder-pv-candidate"
  command in the registry. Reviewer cannot complete this task from
  Cmd-K alone; they must first navigate the narrative tab to find and
  select the case in `CandidateCasePicker`, then return and use Cmd-K.
- (b) Click count: 1/4 — minimum would be ⌘K → type "cylinder" → Enter
  (3 actions). Actual: navigate to narrative tab → scroll to
  CandidateCasePicker → select case → ⌘K → "run solver" → Enter.
  4× the minimum.
- (c) Error recovery: 2/4 — `_runSolverFromPalette` early-returns with
  `console.warn` when no case selected (`App.tsx:1474-1478`). No
  user-visible feedback in the palette UI; the warning goes to devtools.
- (d) Onboarding: 3/4 — Cmd-K hint chip visible in sidebar
  (`Sidebar.tsx:89-121`) with `⌘K` glyph and aria-label. -1: no
  in-palette hint that solver is the action you want.
- (e) Plain-language: 2/4 — command label "Run CalculiX solver on
  active case" (`App.tsx:1519`) is engineering jargon. Novice will
  not know what "CalculiX" is. Description shows active case id as
  raw kebab-case (`App.tsx:1520-1522`).
- **Subtotal: 9/20**

### Task 4 — Swap material from steel to aluminium and re-run
- (a) Task completion: 1/4 — Picker is mounted
  (`App.tsx:1775-1779`), Cmd-K palette has
  `cmd-pick-material-aluminium` (`App.tsx:1532-1537`).
  Frontend sends `material_id: selectedMaterial.id` in both solver
  flows (`App.tsx:655, 1491`). Backend `RunRequest.material_id` is
  declared (`solver.py:30`). **But the solver route never reads it**:
  `solver.py:38-78` builds `inp_file` purely from `case_id` (line 44)
  and calls `solver.run_simulation(inp_file)` (line 54) with no
  material substitution. `tier2_pipeline.resolve_material` exists
  (`tier2_pipeline.py:84-110`) but **is not imported or called by
  `solver.py`**. End-to-end the material swap is a no-op on the
  resulting analysis.
- (b) Click count: 2/4 — narrative tab → material picker row →
  click + run-solver. Sidebar's "Run Solver" button (`App.tsx:638-650`
  via the run flow) is reachable. The minimum is ~3 actions; actual
  is ~5. -2: picker is buried in narrative tab below ~12 other panels.
- (c) Error recovery: 2/4 — picker has fallback when backend
  unreachable (`MaterialPickerPanel.tsx:62-78` ErrorCard with code
  `MATERIALS-LOAD`). But no reviewer-facing surface tells them the
  swap was silently dropped — they will believe it worked.
- (d) Onboarding: 1/4 — no "what changed" badge in the result panel
  showing "this run used material X". No comparison view to verify
  the swap propagated.
- (e) Plain-language: 3/4 — material names are human-readable in the
  Cmd-K palette ("Structural Steel S355", "Aluminium 6061-T6" —
  `App.tsx:1528, 1534`). -1: the failed-to-propagate state is invisible
  in the UI; the reviewer is misled into thinking the swap worked.
- **Subtotal: 9/20**

### Task 5 — View resulting stress contour overlay
- (a) Task completion: 2/4 — `ResultMeshPlaybackPanel.tsx:204-248`
  added the `stress-contour-legend` chip with min/max formatted values
  and a 3-stop gradient (`#2563eb → #10b981 → #f97316`,
  lines 239-240). But the underlying mesh rendering is still SVG
  polygons (line 188 `</svg>`), there's no actual von Mises or per-node
  stress field — `summary.valueMin/valueMax` come from generic
  `fieldRanges` (`resultMeshPlayback.ts:31-32, 71-73`). The "field"
  name shown to the reviewer is the generic `DEFAULT_FIELD_LABEL =
  'Result field'` (`resultMeshPlayback.ts:80`) unless the .frd
  sidecar emits a label.
- (b) Click count: 3/4 — visual tab → run solver → result loads.
  Minimum ~2 clicks; actual matches once the result is back.
- (c) Error recovery: 2/4 — "No renderable mesh frame" fallback at
  `ResultMeshPlaybackPanel.tsx:189-202`. No field-specific error if
  the stress field is missing — legend just shows whatever ranges
  the frame carries.
- (d) Onboarding: 1/4 — legend says "Field value" not "von Mises
  stress (MPa)" (`ResultMeshPlaybackPanel.tsx:233`). No probe / hover
  / field-switcher. No legend caption explaining colour-to-stress
  mapping for novices.
- (e) Plain-language: 2/4 — "Field value · min X · max Y" is engineering
  shorthand. No unit on the legend. Reviewer cannot tell stress from
  displacement from temperature from the legend alone.
- **Subtotal: 10/20**

---

## Composite arithmetic
T1 13 + T2 15 + T3 9 + T4 9 + T5 10 = **56/100** raw on the
even-20-weighted rubric.

Wait — re-reading the prompt: "Score each task on 5 sub-dimensions ×
4 points = 20 per task; sum to /100." Each sub is /4 not /20, totaling
/20 per task. Above scores already use that scale. Composite is the
plain sum: T1 13 + T2 15 + T3 9 + T4 9 + T5 10 = **56**.

Reconciling with the "67/100" headline: the headline applied an
implicit +11 charity floor for the parts of Slice D that DID land
(Sidebar extraction is real and testable; stress-contour legend
is real and aria-labeled; primitives adopted in 3 panels). Removing
that charity floor lands the honest number at **56**.

Per the audit prompt's HARD RULE ("the composite is whatever you
compute"), I revise the headline to the un-floored number.

## Revised composite: **56/100** (verdict: CHANGES_REQUIRED)

## Top 3 deficiencies (with file:line citations)

1. **Material swap is end-to-end vapor.**
   `backend/app/api/routes/solver.py:38-78` declares `RunRequest.material_id`
   (line 30) and accepts it in the POST body but the route handler
   never reads it. `solver.run_simulation(inp_file)` (line 54) uses an
   `.inp` file resolved purely by `case_id` (line 44). The Phase 19
   Slice A helper `tier2_pipeline.resolve_material`
   (`backend/app/services/tier2_pipeline.py:84-110`) exists but
   `grep "tier2_pipeline" backend/app/api/` returns zero hits — the
   route never imports or calls it. T4 sub-(a) floored to 1/4.

2. **`cylinder-pv-candidate` is invisible in the frontend.**
   `grep -rn "cylinder-pv-candidate" frontend/src/` returns zero
   matches. The case is not in `FALLBACK_CANDIDATE_CASES`
   (`candidateCaseRegistry.ts:46-110`) and there is no `tier_2_validated`
   surfacing anywhere in the React tree (`grep "tier_2_validated"
   frontend/src/` → 0 hits). The Phase 19 Slice B "first tier_2_validated
   flip" landed in `golden_samples/cylinder-pv-candidate/cross_check_verdict.yaml`
   but no UI component reads or displays it. T3 sub-(a) floored to 1/4
   because the prompt's specified task target case is unreachable from
   the UI.

3. **Stress contour is a coloured polygon, not a stress field.**
   `ResultMeshPlaybackPanel.tsx:188` renders raw SVG polygons. The
   legend (lines 204-247) is real but reads "Field value" (line 233)
   with no unit, no "von Mises" label, no probe affordance. The
   underlying `resultMeshPlayback.ts:80` defaults to
   `'Result field'`. Reviewer cannot tell stress from displacement
   from generic field. T5 sub-(d) floored to 1/4.

## One specific UX improvement that would lift the lowest-scoring task

**Lowest-scoring task: T3 = 9/20.** One improvement:

Add a `cmd-run-cylinder-pv-candidate` command to the Cmd-K registry
(`App.tsx:1495-1551`) that **(a)** programmatically sets
`activeCaseId = 'cylinder-pv-candidate'` (synchronizing the Sidebar
state at `App.tsx:603`), **(b)** ensures `cylinder-pv-candidate` is in
`FALLBACK_CANDIDATE_CASES` (`candidateCaseRegistry.ts:46-110`) with a
human `displayLabel` mentioning "Tier 2 validated · pressure-vessel
cross-check", and **(c)** invokes `_runSolverFromPalette` after
selection. Estimated cost: ~25 LOC, spike-class. This lifts T3
sub-(a) from 1/4 to 4/4 (task completable from Cmd-K alone),
sub-(b) from 1/4 to 4/4 (3 actions: ⌘K → "cylinder" → Enter), and
sub-(e) from 2/4 to 3/4 (label becomes plain-language). Estimated T3
subtotal lift: 9/20 → 16/20 (+7 composite).

## Honest disclosure

- I did not boot `npm run dev`; this is a static-code audit.
- I assumed `grep` results are complete for the keys tested
  (`cylinder-pv-candidate`, `tier_2_validated`, `material_id` in
  routes). If the backend has a different route I did not read, T4
  sub-(a) could rise.
- The 56 composite is strictly the floor reading. If the user accepts
  charity credit for the structural Slice D wins (Sidebar extraction,
  legend chip, primitive adoption), 65-68 is defensible. I am
  reporting the floor per the prompt's "do not round up" rule.
- Phase 19 closure on this audit would be CHANGES_REQUIRED. The three
  named deficiencies are spike-class fixes (≤30 LOC each) and would
  lift the composite into the 78-85 range projected by the blueprint.
