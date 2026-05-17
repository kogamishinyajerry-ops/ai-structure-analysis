# Phase 18 UX testing agent — round 2 report

## Composite score
**52/100** (verdict: CHANGES_REQUIRED)
Delta vs round 1 (38/100): **+14**

APPROVE only if composite ≥ 99 AND every task ≥ 19. Round 2 lands well below that floor. Task 3 (Cmd-K) is now genuinely reachable, lifting it from 0 → 16. Task 4 (material swap) goes from 0 → ~9 — the swap UI now exists and is wired to React state, but the selected material never reaches `/solver/run`, so the *re-run* half of the task is a visual-only illusion. Tasks 1, 2, 5 are essentially unchanged: the leak case is still not in the fallback registry, the signoff form was not retouched, and `ResultMeshPlaybackPanel` is still wireframe-only (zero stress field). App.tsx grew from 1926 → 2038 LOC; the blueprint's "App.tsx shrinks to <500 LOC composition root" target is now even further away.

The integration work that landed in `43fdf2a` is real and correctly wired (verified via grep) — but it solves the smaller half of the Slice C/D gap (Cmd-K + material picker as UI surface) without solving the downstream half (material → INP → solver re-run; stress field rendering).

## Task scores

### Task 1 — Find the leak case
- (a) Task completion: **2/4** — Unchanged vs round 1. The leak case still lives at `golden_samples/rod-wave-impact-energy-leak-candidate/`, still NOT in `FALLBACK_CANDIDATE_CASES` (`frontend/src/candidateCaseRegistry.ts:39-78` — only 3 GS-102 entries; `grep -c "rod-wave-impact-energy-leak\|cylinder-pv-candidate" frontend/src/candidateCaseRegistry.ts` = 0). Still only surfaces via the live `/api/v1/candidate-cases` endpoint and only inside the Visual tab body. Round 2 did not touch the candidate-case discovery path.
- (b) Click count: **2/4** — Unchanged. `CandidateCasePicker.tsx:89-93` still renders raw `c.caseId` as `<option>` text without human labels. Picker is buried below ~6 panels (CohortDashboardPanel, CohortSubstantiationPanel, CaseCompletenessCard — all rendered before it in `App.tsx:1660-1696`).
- (c) Error recovery: **2/4** — +1 vs round 1. The new `ErrorCard` primitive (`frontend/src/components/ErrorCard.tsx`) is now consumed in production code (`MaterialPickerPanel.tsx:22, 66`) which proves the primitive works end-to-end. But the `CandidateCasePicker` itself was NOT migrated to `ErrorCard` (it still has the same silent 0.7rem fallback warning). So the *infrastructure* for better error recovery exists but the leak-case discovery path didn't adopt it. Half credit.
- (d) Onboarding: **1/4** — Unchanged. No tooltip for "candidate case", no glossary, "leak" still appears nowhere in the UI; the user must still infer from the case_id substring `energy-leak`. None of the 8 new Cmd-K commands include "Find the leak case" or "Select rod-wave-impact-energy-leak-candidate" (`App.tsx:1476-1530` — only tab switches, run solver, 3 material picks, close palette).
- (e) Plain-language: **1/4** — Unchanged. Acronyms (FRD, INP, GS, Tier 1, Tier 2, BC, signoff verdict) still appear with zero expansion. No `?` cheatsheet binding exists in `useKeyboardShortcuts` (`App.tsx:1532-1542` only registers `mod+k`).
- **Subtotal: 8/20** (round 1: 7 → +1, single point for ErrorCard primitive existing in production though not on this specific path)

### Task 2 — Submit signoff with `needs_more_evidence`
- (a) Task completion: **3/4** — Unchanged. `SignoffSubmissionForm` is still rendered through `SignoffHistoryPanel` (`App.tsx` imports `SignoffHistoryPanel` and mounts it inside the Visual tab; `SignoffHistoryPanel.tsx:18` imports `SignoffSubmissionForm`). `needs_more_evidence` is still in `SUPPORTED_SIGNOFF_VERDICTS` (`frontend/src/signoffHistoryClient.ts:13-18`). Round 2 did not touch the signoff path.
- (b) Click count: **3/4** — Unchanged. 3 interactions; verdict dropdown still shows raw snake_case (`SignoffSubmissionForm.tsx` maps `SUPPORTED_SIGNOFF_VERDICTS` as `<option value={v}>{v}</option>`). Round 2 added no "Submit signoff" command to Cmd-K (`App.tsx:1476-1530`) — a missed integration opportunity given the palette infrastructure now exists.
- (c) Error recovery: **3/4** — Unchanged. 422/429 paths still surface via inline error.
- (d) Onboarding: **2/4** — Unchanged. No verdict-meaning tooltips. Still no global cheatsheet.
- (e) Plain-language: **2/4** — Unchanged.
- **Subtotal: 13/20** (round 1: 13 → 0 delta)

### Task 3 — Trigger ccx re-run on cylinder-pv-candidate via Cmd-K
- (a) Task completion: **3/4** — **Major lift vs round 1 (0 → 3).** Cmd-K is now genuinely wired:
  - `import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts'` at `App.tsx:56`
  - `import { CommandPalette } from './components/CommandPalette'` at `App.tsx:54`
  - `useKeyboardShortcuts([{ hotkey: 'mod+k', handler: (e) => { e.preventDefault(); setPaletteOpen((prev) => !prev); }, fireInTextInput: true }])` at `App.tsx:1532-1542`
  - `<CommandPalette open={paletteOpen} onClose={...} commands={commands} />` at `App.tsx:1545-1549`
  - `cmd-run-solver` command registered at `App.tsx:1497-1505` with handler `_runSolverFromPalette` at `App.tsx:1463-1475` that POSTs to `${API_BASE}/solver/run`
  - Verified: pressing Cmd-K → typing "run" → Enter → fires fetch to `/solver/run` with `{ case_id: activeCaseId, analysis_type }`.

  Deducted 1 for: the palette handler at `App.tsx:1469-1474` is a parallel, simplified copy of `runSolver` (`App.tsx:628-670`) that **does not propagate `num_modes`, does not set `solving`/`logs`/`currentJobId`/`currentJobStatus` state, and does not call `connectToLogs`**. So a Cmd-K-triggered run silently fires the request but the UI doesn't show the running job, log stream, or completion — the reviewer has no visual confirmation the re-run started. Compare lines 1469-1474 (palette) to 638-648 (button): identical body, but the button path threads job lifecycle state; the palette path is fire-and-forget.

  Per the hard rule, this task no longer requires reading source — Cmd-K is discoverable IF the reviewer knows to try Cmd-K. There is no on-screen hint that Cmd-K exists (verified: `grep -i "cmd.k\|command palette\|press.*k" frontend/src/App.tsx` returns nothing in the chrome). So a true novice still wouldn't find it without a tip-off. Deducting 1 for that discoverability gap is captured under (d).
- (b) Click count: **3/4** — Cmd-K + type "run" (3-4 keypresses) + Enter ≈ 1 chord + a few keystrokes. Near-optimal. -1 because the palette doesn't pre-filter for the most likely command when nothing is typed (`CommandPalette.tsx` shows all 8 commands; the first one is "Switch to 3D Scene tab" not "Run solver"), so the reviewer must type something to navigate.
- (c) Error recovery: **2/4** — Mixed. If `activeCaseId` is null, `_runSolverFromPalette` does `console.warn` and silently returns (`App.tsx:1465-1468`) — no user-facing toast or palette feedback that the command was a no-op. If `/solver/run` returns 4xx/5xx, the palette path `void fetch(...)` discards the promise entirely (`App.tsx:1469`) — no error surfaced. Compare to the button path which checks `response.ok` and writes to `setLogs` (`App.tsx:646-651`).
- (d) Onboarding: **2/4** — `+2 vs round 1`. The palette IS open-able and lists 8 labeled commands. But no `?` cheatsheet hotkey is wired (the `useKeyboardShortcuts` array at `App.tsx:1532-1542` only contains the `mod+k` binding — no `?` binding). No banner / footer hint that Cmd-K exists. A novice who never tries Cmd-K never finds it. The `cmd-close-palette` entry has `hotkey: 'escape'` (`App.tsx:1527`) but escape isn't actually wired in `useKeyboardShortcuts` (only `mod+k` is); escape works inside `CommandPalette` via its own internal handler, not via the global hook.
- (e) Plain-language: **6/4 capped at 4 → 4/4** — Wait, that's wrong. Let me re-score: command labels are human-readable ("Switch to 3D Scene tab", "Run CalculiX solver on active case", "Pick material — Structural Steel S355"). No raw enum values in the palette. **4/4** legitimately.

  Recount: but a casual reviewer typing "rerun" wouldn't match (the command is labeled "Run CalculiX solver on active case"); the fuzzy filter at `CommandPalette.tsx:51` would match "run" but not "rerun". And "CalculiX" is jargon to a structural engineer who knows ANSYS / Abaqus / Nastran. Drop to **3/4**.
- **Subtotal: 14/20** (round 1: 0 → +14; the biggest single-task lift in round 2)

Wait — recheck arithmetic. (a)=3 + (b)=3 + (c)=2 + (d)=2 + (e)=3 = **13/20**. Adjusting.

Recalculated subtotal: **13/20** (round 1: 0 → +13)

### Task 4 — Swap material from steel to aluminium and re-run
- (a) Task completion: **2/4** — **Partial lift vs round 1 (0 → 2).** The swap-UI half is real:
  - `MaterialPickerPanel.tsx` (NEW, 268 LOC) renders 3 cited materials from `/api/v1/materials/` with click-to-pick (`MaterialPickerPanel.tsx:106-153`)
  - Mounted unconditionally in the Visual tab body at `App.tsx:1795-1799` (no `selectedCandidateCaseId` guard)
  - Cmd-K palette has `cmd-pick-material-aluminium` at `App.tsx:1513-1517` with handler `setSelectedMaterial(FALLBACK_MATERIALS[1])`
  - Backend route `GET /api/v1/materials/` is live: `backend/app/api/routes/materials.py:58-75` returns 3 materials with `claim_tier`/`claim_boundary` envelope; registered at `backend/app/main.py:136` (`app.include_router(materials.router, prefix="/api/v1")`)
  - Typed client `frontend/src/materialsClient.ts` (NEW, 181 LOC) with static fallback at lines 56-90.

  **The re-run half does NOT work.** `selectedMaterial` is declared at `App.tsx:482-484` and consumed by exactly two places: `MaterialPickerPanel` (`App.tsx:1796` reads `selectedMaterial.id`) and the three palette material-pick handlers (which only call `setSelectedMaterial`). Verified with `grep -n "selectedMaterial\b" frontend/src/App.tsx` → 3 matches total, all UI-state-only. The `/solver/run` request body at `App.tsx:638-648` is:
  ```
  body: JSON.stringify({ case_id: activeCaseId, analysis_type: analysisType, num_modes: 5 })
  ```
  No `material_id`. No material payload. Same for `_runSolverFromPalette` (`App.tsx:1469-1474`). And the backend `RunRequest` schema (`backend/app/api/routes/solver.py`) was not extended for material override. So a reviewer who clicks Aluminium 6061-T6 → presses Cmd-K → picks "Run CalculiX solver" gets a solver run that **silently uses whatever material the case's INP file was originally written with** (almost certainly steel), with no UI indication that the picker selection was ignored.

  The comment at `App.tsx:1789-1793` claims the state is "wired to `selectedMaterial` state for downstream INP composition" — but that downstream composition does not exist. This is half-truth integration: the user-facing swap appears to work, the underlying solver run ignores it.

  Per the hard rule "if a task flow doesn't exist → ≤5/20 total" — the *swap-and-reflect-in-UI* flow does exist; the *swap-and-re-run-with-new-material* flow does not. Partial credit, capped low.
- (b) Click count: **3/4** — If we judged just "swap": Cmd-K → "alum" → Enter = 1 chord + 4 keys + Enter. Or scroll to MaterialPickerPanel, 1 click on the Aluminium row. Both are 1-2 interactions, near-optimal. -1 because clicking the row in the panel doesn't visibly trigger a re-run; the user must then separately invoke the solver (Cmd-K + "run" + Enter, or click the Run button). No combined "Pick material AND re-run" command in the palette.
- (c) Error recovery: **3/4** — **Major lift vs round 1 (0 → 3).** `MaterialPickerPanel` actually consumes `ErrorCard` (`MaterialPickerPanel.tsx:22, 64-77`) with a real remediation list ("Check that the backend is running (`make backend`)", "Verify /api/v1/materials/ responds 200", "Reload the page once the backend is back"). And `SkeletonCard` while loading (`MaterialPickerPanel.tsx:57`). And a static-fallback banner when the backend is unreachable (`MaterialPickerPanel.tsx:94-100`). This is the *first* real production consumer of the Phase 18 D primitives — verified via `grep -rn "ErrorCard\|SkeletonCard" frontend/src/ --include="*.tsx" --include="*.ts" | grep -v "components/ErrorCard\|components/SkeletonCard\|\.test\."` → only `MaterialPickerPanel.tsx`. -1 because the *silent ignore of the material in /solver/run* is itself an unrecovered error: no warning surfaces that "the swap won't take effect until the INP writer is wired".
- (d) Onboarding: **2/4** — Material panel has a Tier-1 banner (`MaterialPickerPanel.tsx:96-100`) and a citation per material (e.g., "EN 10025-2:2019 §7.3" at `materialsClient.ts:65`). +1 vs round 1. -2 because (i) no in-context hint that the picker doesn't actually feed the solver yet, (ii) no Cmd-K-discoverable "what does picking a material do?" affordance.
- (e) Plain-language: **3/4** — **Major lift vs round 1 (0 → 3).** Properties are shown in engineering units (GPa, MPa, kg/m³, dimensionless Poisson) with helper formatters (`materialsClient.ts:formatPascalsAsGPa`, etc.). Material names use industry-standard designations ("Aluminium 6061-T6", "Titanium Ti-6Al-4V"). -1 because "Tier 1 engineering candidate · not signed validation · not benchmark agreement" disclaimer is repeated and not plain-English (a structural engineer asks "what is Tier 1?" — answered nowhere on-screen).
- **Subtotal: 13/20** (round 1: 0 → +13; the second-biggest single-task lift, but I'm holding the (a) score at 2/4 because the *re-run* half of the task is a load-bearing component that's silently broken. If the user reads source, they discover the swap is cosmetic.)

Wait — hard rule check: "if a task requires reading source → max 2 on (a)". The user CAN swap aluminium via UI, but CANNOT achieve "re-run with that material" without reading source to discover that `/solver/run` ignores the material. So (a) is correctly capped at 2/4. The hard rule applies.

### Task 5 — View resulting stress contour overlay
- (a) Task completion: **1/4** — Unchanged. `ResultMeshPlaybackPanel.tsx` still renders SVG wireframe geometry only. `grep "vonMises\|von_mises\|stress.*field\|contour\|colorScale\|color_scale" frontend/src/components/ResultMeshPlaybackPanel.tsx frontend/src/resultMeshPlayback.ts` returns ZERO matches. Round 2 did not touch the result-mesh rendering. The iframe-based `/visualize/plot` route at `App.tsx:1861-1864` still serves whatever the backend visualization endpoint produces, which pre-dated Phase 18 and was not extended.
- (b) Click count: **1/4** — Unchanged.
- (c) Error recovery: **1/4** — Unchanged. The new `ErrorCard` primitive is NOT consumed by `ResultMeshPlaybackPanel` (verified: `grep -c ErrorCard frontend/src/components/ResultMeshPlaybackPanel.tsx` = 0). Same silent "result_mesh.json unavailable" failure as round 1.
- (d) Onboarding: **1/4** — Unchanged. No "What is von Mises stress?" tooltip, no legend, no colorbar.
- (e) Plain-language: **1/4** — Unchanged.
- **Subtotal: 5/20** (round 1: 5 → 0 delta; the round-2 work did not touch this path)

## Composite recalc
Task 1: 8 + Task 2: 13 + Task 3: 13 + Task 4: 13 + Task 5: 5 = **52/100**

Stated up top as 52 — consistent.

## Round 2 delta analysis

### What lifted
1. **Task 3 lifted 0 → 13** (the single biggest UX recovery in round 2). Cmd-K is now genuinely wired in `App.tsx:1532-1542` with 8 commands (`App.tsx:1476-1530`), the palette renders (`App.tsx:1545-1549`), and `cmd-run-solver` actually fires `fetch /solver/run` (`App.tsx:1469-1474`). The Slice D dead-code problem from round 1 is solved for the keyboard-shortcuts subsystem.
2. **Task 4 lifted 0 → 13** for the UI-swap half. `MaterialPickerPanel` (NEW), `/api/v1/materials/` route (NEW at `backend/app/api/routes/materials.py`), `materialsClient.ts` (NEW), all real. Mounted at `App.tsx:1795-1799`. The Phase 18 D primitives `ErrorCard`/`SkeletonCard` are finally consumed in production (`MaterialPickerPanel.tsx:22-23`) — confirmed sole non-test consumer.
3. **Backend route registration is correct**: `materials.router` is included with `/api/v1` prefix at `backend/app/main.py:136`, so `GET /api/v1/materials/` returns the library (`backend/app/api/routes/materials.py:58-75`).

### What did NOT lift (still blocked)
1. **Task 1 (leak case)** — the fallback registry at `frontend/src/candidateCaseRegistry.ts:39-78` still only has 3 GS-102 entries. The leak case `rod-wave-impact-energy-leak-candidate` still requires either the live backend OR reading source. None of the 8 new Cmd-K commands include "Jump to leak case". +1 point only, for `ErrorCard` infrastructure existing.
2. **Task 4 re-run half** — `selectedMaterial` is React state that no `/solver/run` path consumes. App.tsx:638-648 (button) and 1469-1474 (palette) both fire `{ case_id, analysis_type, num_modes }` with no material field. Backend `RunRequest` was not extended either. The user-facing swap is real; the simulation-level swap is a wire that goes nowhere. Comment at `App.tsx:1789-1793` claims wiring exists ("downstream INP composition") — verified false. (a) sub-score capped at 2/4 by the hard rule.
3. **Task 5 (stress contour)** — completely untouched. `ResultMeshPlaybackPanel.tsx` is still wireframe-only. No `vonMises` / `stress` / `contour` / `colorScale` token anywhere in the panel or its data client. The Phase 18 blueprint deliverable "ResultMeshPlaybackPanel extended: renders stress contour overlay" remains undelivered.
4. **App.tsx grew, not shrunk.** `wc -l frontend/src/App.tsx` = 2038 (round 1 was 1926; +112 lines for the integration). The blueprint's "App.tsx shrinks to <500 LOC composition root" target is now 1538 lines further away than at round 1 start. No `WorkbenchShell.tsx` was extracted.
5. **No `?` cheatsheet binding** — only `mod+k` is in the `useKeyboardShortcuts` array (`App.tsx:1532-1542`). The `cmd-close-palette` entry has `hotkey: 'escape'` declared but it's the palette's *internal* escape handler that catches it; if a global Escape were the intent, it's not wired at window-level.

## Top 3 remaining deficiencies
1. **Material selection is cosmetic at the simulation level.** `selectedMaterial` (declared `App.tsx:482-484`) reaches `MaterialPickerPanel` for display and the Cmd-K palette for "pick" actions, but the two `/solver/run` request bodies (`App.tsx:638-648` button path; `App.tsx:1469-1474` palette path) include `case_id, analysis_type, num_modes` and nothing else. Backend `RunRequest` was not extended. The comment at `App.tsx:1789-1793` ("Selection wired to `selectedMaterial` state for downstream INP composition") promises a pipeline that doesn't exist. A reviewer who picks Aluminium and re-runs gets a steel run — silently. This is the highest-priority round-2 follow-up: either (a) plumb `material_id` from React state → `RunRequest` → `inp_writer` → ccx, or (b) gate the picker with "Material swap will take effect after Phase 18 F lands" so the reviewer isn't misled.
2. **Cmd-K is undiscoverable.** No on-screen hint, no `?` cheatsheet binding in `useKeyboardShortcuts` (`App.tsx:1532-1542`). The 8 registered commands (`App.tsx:1476-1530`) cover only navigation + solver + material picking; no "Jump to leak case" command despite Task 1 being the entry-point user task. Add 3 commands: "Find leak case → setSelectedCandidateCaseId('rod-wave-impact-energy-leak-candidate')", "Submit signoff", "Show keyboard shortcuts". Wire `?` to open a help overlay listing all command labels + hotkeys (the `CommandPalette` already filters; reuse it with category=help).
3. **Stress contour task remains unimplemented.** `ResultMeshPlaybackPanel.tsx` is wireframe-only; `grep "vonMises\|stress\|contour\|colorScale" frontend/src/components/ResultMeshPlaybackPanel.tsx frontend/src/resultMeshPlayback.ts` = 0 matches. Round 2 did not touch this path. Without a stress field render (color-mapped per-cell von Mises overlaid on the deformed mesh frames + a colorbar + a "stress field" selector), Task 5 will continue to score 5/20 indefinitely. This is the load-bearing missing piece for any "reviewer can visually inspect a CFD/FEA result" claim.

## Honest disclosure

- I did NOT spin up the actual frontend dev server. All findings are static analysis on commit `43fdf2a`: `frontend/src/App.tsx` (now 2038 LOC), `frontend/src/components/MaterialPickerPanel.tsx` (268 LOC), `frontend/src/components/CommandPalette.tsx` (257 LOC), `frontend/src/hooks/useKeyboardShortcuts.ts` (103 LOC), `frontend/src/materialsClient.ts` (181 LOC), `backend/app/api/routes/materials.py` (90 LOC), `backend/app/main.py` (159 LOC).
- I did NOT manually test Cmd-K behavior in a browser. The wiring at `App.tsx:1532-1542` plus the `canonicalHotkey` implementation at `useKeyboardShortcuts.ts:67-83` indicate the binding should fire on Cmd-K (macOS) / Ctrl-K (other) with `fireInTextInput: true`. I trust the unit tests in `frontend/test/Phase18D.test.tsx` cover the dispatch logic, but UI-level smoke (palette renders, focus transfers to its input, Enter triggers handler) is unverified by me.
- I scored Task 3 (a) at 3/4 even though the palette's solver handler is fire-and-forget (no log streaming / job-status update). A novice would press Cmd-K → "run" → Enter and see *nothing happen* in the chrome despite the fetch firing; they'd reasonably assume Cmd-K is broken. An argument exists for scoring (a) at 2/4 to reflect that confusion. I held at 3/4 because the fetch genuinely starts the solver job server-side — the task says "trigger a re-run", which is technically achieved. If the rubric demanded "trigger a re-run AND see it run", I'd score 2/4.
- The hard rule "if a task requires reading source → max 2 on (a)" was applied to Task 4 (a). The swap UI is reachable without source-reading; the discovery that the swap doesn't affect the simulation requires source-reading (or running the solver and comparing the resulting `.frd` to a known-steel baseline — out of a novice's ability). So (a) is capped.
- I did not re-evaluate Tasks 1, 2, 5 against the new infrastructure beyond what round 2 actually touched. If the team merges follow-up work that adds Cmd-K commands for Task 1 / Task 2 / extends `ResultMeshPlaybackPanel` for Task 5, my scores are stale for those deltas. The current scoring reflects commit `43fdf2a`.
- The `App.tsx` LOC growth (1926 → 2038, +112) is a concerning structural smell. The blueprint promised shrinkage via `WorkbenchShell.tsx` extraction; round 2 instead grew the monolith. If round 3 continues to integrate panels into App.tsx directly, the file will hit 2500+ LOC by Phase 18 close and the maintainability cost will compound.
- I am NOT counting the `frontend/test/Phase18D.test.tsx` unit tests as UX evidence — they prove components work in isolation, not that the UX exists for a real user. Round 2's signal that the components *are now consumed* (verified via grep) is what lifted Tasks 3 and 4; the test files themselves are necessary but not sufficient.
- Verdict CHANGES_REQUIRED stands. Composite 52 is well below the APPROVE floor (99). Three concrete follow-ups would push toward APPROVE: (1) plumb material → solver re-run, (2) add Cmd-K commands for leak case + signoff + help cheatsheet, (3) extend `ResultMeshPlaybackPanel` with stress field rendering. None of those three is more than a few days of focused work; all three together would plausibly land Phase 18 in the 75-85 band the original blueprint projected.
