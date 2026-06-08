# Phase 20 UX testing agent — round 2 report

## Composite score
**70/100** (verdict: CHANGES_REQUIRED — improved but not yet APPROVE)
Round 1: 62/100. Round 2 honest delta: **+8**.

The patch is real, not cosmetic. Both R1 defects are closed and the
lift is concentrated where R1 said it should be (T3). The remaining
gap to a high-70s/80s score is the carry-forward backlog (material
swap onboarding, stress-legend wording, signoff Cmd-K command) that
Phase 20 D's patch was never scoped to address.

## Patch verification

R1 defect 1 (registry missing 3 cases) — **fixed**.
`frontend/src/candidateCaseRegistry.ts:46-165` now contains 7 entries:
the original 4 plus `cylinder-pv-candidate` (line 118, Tier 2
validated displayLabel line 119), `plate-with-hole-candidate`
(line 134), and `cantilever-beam-candidate` (line 150). Each has
displayLabel + claimTier + notesExcerpt + claimBoundary per the
prompt.

R1 defect 2 (two-state-tree wiring) — **fixed**.
`frontend/src/App.tsx:1585-1600` `onSelectCandidateCase` now calls
both `setSelectedCandidateCaseId(id)` (line 1586) AND
`setActiveCaseId(id)` (line 1594) with explicit comment citing the
UX round-1 finding (lines 1587-1593). Topbar gate
`showRunControls={Boolean(activeCaseId)}` (line 1614) and Cmd-K
`cmd-run-solver` early-return on `!activeCaseId` (line 1474) both
now evaluate true after a candidate click. End-to-end flow:
Sidebar candidate click → Topbar Run Solver button appears →
button click OR ⌘K → "Run CalculiX..." → /solver/run fires with
candidate id + material_id. Verified by static read; no live boot.

Test update — **landed**.
`frontend/test/Phase18E_round3.test.tsx:39` switched to
`toBeGreaterThanOrEqual(4)` plus a head-of-list invariant on line 40
(`FALLBACK_CANDIDATE_CASES[0].caseId).toBe('GS-102-candidate')`).

Minor honesty note: when `activeCaseId` is set to a candidate id like
`cylinder-pv-candidate`, `availableCases.find(c => c.id === activeCaseId)`
at `App.tsx:826` returns undefined, so `activeCase` is null and the
breadcrumb at `App.tsx:1612` falls back to the literal id string. This
is acceptable UX (breadcrumb reads "cylinder-pv-candidate") and doesn't
break the Run path, but it does mean the `caseLabel` formatting
("id / name") degrades to the raw id. Not enough to floor a sub-dim
but worth flagging.

## Task scores (delta from R1)

### Task 1 — Find the leak case (R1: 15/20 → R2: 17/20, Δ=+2)
- (a) Task completion: 4/4 — unchanged; leak entry was already in
  fallback at R1 (`candidateCaseRegistry.ts:96-109`).
- (b) Click count: 4/4 — unchanged; 1 click in Sidebar.
- (c) Error recovery: **2/4 → 4/4 (+2)** — The R1 two-state-tree
  hazard is closed. Clicking the leak entry now sets both
  `selectedCandidateCaseId` and `activeCaseId` (`App.tsx:1585-1600`),
  so the Topbar Run Solver button appears (`Topbar.tsx:103`,
  `App.tsx:1614` `showRunControls={Boolean(activeCaseId)}` is true)
  and Cmd-K `cmd-run-solver` (`App.tsx:1474`) is reachable. Recovery
  path is now visible-and-actionable, not silent failure.
- (d) Onboarding: 2/4 — unchanged. No tutorial callout, no cohort
  badge calling out the leak. Label still says "ENERGY LEAK case"
  without "intentionally broken fixture" framing.
- (e) Plain-language: 3/4 — unchanged. `notesExcerpt` still says
  "the canonical 'what does a broken case look like?' fixture"
  (`candidateCaseRegistry.ts:103-106`).
- **Subtotal: 17/20**

### Task 2 — Submit `needs_more_evidence` signoff (R1: 15/20 → R2: 15/20, Δ=0)
- (a) Task completion: 4/4 — `SUPPORTED_SIGNOFF_VERDICTS` still
  includes `needs_more_evidence`; form unchanged.
- (b) Click count: 3/4 — unchanged. No `cmd-submit-signoff` entry
  in the Cmd-K registry (`App.tsx:1495-1551` still has zero signoff
  commands).
- (c) Error recovery: 3/4 — unchanged.
- (d) Onboarding: 2/4 — unchanged.
- (e) Plain-language: 3/4 — unchanged.
- **Subtotal: 15/20** (Phase 20 patch did not touch signoff path)

### Task 3 — Cmd-K ccx re-run on cylinder-pv (R1: 9/20 → R2: 14/20, Δ=+5)
- (a) Task completion: **1/4 → 4/4 (+3)** — cylinder-pv-candidate
  is now in `FALLBACK_CANDIDATE_CASES` at `candidateCaseRegistry.ts:118`
  with displayLabel `'Cylinder pressure vessel · Tier 2 validated
  (Phase 19 B)'`. Sidebar renders it (`Sidebar.tsx:237-267`, fed by
  `App.tsx:1580-1583`). Click sets both `selectedCandidateCaseId`
  and `activeCaseId` (`App.tsx:1594`). ⌘K → "Run CalculiX" handler
  passes the gate (`App.tsx:1474`) and POSTs to `/solver/run` with
  `case_id: 'cylinder-pv-candidate'`, `material_id: ...`
  (`App.tsx:1483-1492`). End-to-end task is completable from the UI.
- (b) Click count: **1/4 → 3/4 (+2)** — Path is: Sidebar click
  cylinder-pv → ⌘K → "Run CalculiX..." → Enter. That's ~3 actions.
  Not 4/4 because there is no `cmd-select-cylinder-pv-candidate`
  alias in the Cmd-K registry (`App.tsx:1495-1551`), so a pure-Cmd-K
  flow ("⌘K → 'cylinder' → Enter → ⌘K → 'Run' → Enter") still
  requires the Sidebar click for case selection. A `cmd-select-*`
  family would push this to 4/4.
- (c) Error recovery: 2/4 — unchanged. `_runSolverFromPalette` still
  `console.warn`s on missing case (`App.tsx:1476`); no visible
  palette feedback. Now far less likely to fire because the gate
  closes around an actually-selected case, but the no-feedback
  path is unchanged.
- (d) Onboarding: 3/4 — unchanged. Cmd-K hint chip in Sidebar
  (`Sidebar.tsx:108-141`).
- (e) Plain-language: 2/4 — unchanged. Label "Run CalculiX solver
  on active case" (`App.tsx:1519`) remains engineering jargon.
- **Subtotal: 14/20** (R1's lowest-scoring task lifts the most,
  exactly per R1's predicted spike)

### Task 4 — Swap material to aluminium (R1: 13/20 → R2: 13/20, Δ=0)
- (a) Task completion: 3/4 — unchanged. Backend wiring at
  `backend/app/api/routes/solver.py:66-95` still real;
  `material_reference` still ignored by frontend (grep
  `material_reference frontend/src/` → 0 hits). The Phase 20 D
  patch did not surface the material echo.
- (b) Click count: 2/4 — unchanged. Patch didn't add a material
  picker to the Sidebar or to the visual tab; still buried in
  narrative tab.
- (c) Error recovery: 3/4 — unchanged. 422 detail logged to
  console only (`App.tsx:659-664`); no banner.
- (d) Onboarding: 2/4 — unchanged. No "this run used material X"
  badge in result panel.
- (e) Plain-language: 3/4 — unchanged.
- **Subtotal: 13/20** — Note: the *availability* of T4 on a
  Tier-2-validated case (cylinder-pv) is new, but the rubric
  scores T4-on-its-own-merits and the picker/echo gaps weren't
  touched. Honest reading: this is reachability lift for T4 hidden
  inside T3, not a T4 sub-dim improvement.

### Task 5 — Stress contour overlay (R1: 11/20 → R2: 11/20, Δ=0)
- (a) Task completion: 2/4 — unchanged.
- (b) Click count: 3/4 — unchanged.
- (c) Error recovery: 3/4 — unchanged (Phase 20 D primitive
  migration already counted at R1).
- (d) Onboarding: 1/4 — unchanged. Legend still reads "Field value".
- (e) Plain-language: 2/4 — unchanged.
- **Subtotal: 11/20**

---

## Composite arithmetic
T1 17 + T2 15 + T3 14 + T4 13 + T5 11 = **70/100**.

No charity adjustments. Math is the math.

## Honest verdict

The R2 patch landed real, user-visible UX value. cylinder-pv-candidate
is now selectable from the left rail, Run Solver lights up on click,
and Cmd-K can fire a ccx re-run against it — exactly the spike-class
fix R1 prescribed at ~25 LOC + 1 test. The +8 composite delta matches
R1's predicted lift band ("69-73 still below blueprint projection")
landing at the bottom of that band; T3 itself lifted +5 of the +8,
again per R1's call. Verdict remains CHANGES_REQUIRED because three
carry-forward gaps still floor scores: (1) no signoff Cmd-K command
keeps T2(b) at 3/4, (2) material_reference still invisible keeps
T4(a)/(d) at 3/4 + 2/4, and (3) stress legend wording / unit / von
Mises label keep T5(d)/(e) at 1/4 + 2/4. None of these regressed —
they were just not in scope for this patch. Nothing regressed
elsewhere; T3(b) is honestly 3/4 not 4/4 because pure-Cmd-K
case-selection requires a `cmd-select-cylinder-pv-candidate` alias
that doesn't exist yet. The patch is correctly scoped, cleanly
landed, and the score reflects it.
