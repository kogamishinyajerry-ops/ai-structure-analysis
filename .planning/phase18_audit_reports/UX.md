# Phase 18 UX testing agent — report

## Composite score
**38/100** (verdict: CHANGES_REQUIRED)
APPROVE only if composite ≥ 99 AND every task ≥ 19. Phase 18 is far below that floor: 3 of the 5 user tasks cannot be completed at all through the current UI because the components Slice D shipped (`CommandPalette`, `useKeyboardShortcuts`, `DriftBadge`, `SkeletonCard`, `ErrorCard`, `EmptyStateCard`) are orphaned — present as files, never imported by `frontend/src/App.tsx`. No `WorkbenchShell.tsx` exists. No `MaterialPickerPanel.tsx` / `MeshControlPanel.tsx` exists. No `/api/v1/materials` route exists. `ResultMeshPlaybackPanel` shows wireframe geometry only — zero `.frd`-driven stress contour rendering.

A novice opening the workbench cannot, by clicking around in good faith, discover Cmd-K (there is none), swap materials (no UI flow), or see stress contours (no overlay code). The Phase 18 D blueprint is, from a user-visible UX standpoint, **delivered as dead code**.

## Task scores

### Task 1 — Find the leak case
- (a) Task completion: **2/4** — The leak case directory is `golden_samples/rod-wave-impact-energy-leak-candidate/`. It is NOT in the `FALLBACK_CANDIDATE_CASES` array (`frontend/src/candidateCaseRegistry.ts:39-78` — only 3 GS-102 entries). It surfaces only via the live `/api/v1/candidate-cases` endpoint (`backend/app/api/routes/candidate_cases.py:53-66` scans the dir) AND only inside the **Visual tab body** in either `CohortDashboardPanel` or `CandidateCasePicker` (rendered at `frontend/src/App.tsx:1557-1599`). A novice would first see the left-rail "Case Gallery" (`App.tsx:1474-1479`) which lists DB-registered cases from `/cases` — a different list — and may not see the leak case there at all if the DB wasn't seeded. With backend up + DB happens-to-contain-it, partial credit; otherwise the case is invisible.
- (b) Click count: **2/4** — Minimum with knowledge: 1 click on the sidebar row. Actual novice path: scan 13 unlabeled `case_id` strings in a `<select>` dropdown (`CandidateCasePicker.tsx:89-93` renders raw `c.caseId` as `<option>` text — no human label, no description), pick `rod-wave-impact-energy-leak-candidate`, then read the NOTES.md excerpt (`CandidateCasePicker.tsx:126`). 1-3 extra clicks if novice picks the wrong tab first (`activeTab` defaults to 'visual', which is correct, but the picker is below `CohortDashboardPanel` + `CohortSubstantiationPanel` + `CaseCompletenessCard` — scroll required, ~6 panels deep).
- (c) Error recovery: **1/4** — If `/api/v1/candidate-cases` is down, the picker silently falls back to the 3-entry GS-102 list (`CandidateCasePicker.tsx:104` shows "source: static fallback list" in 0.7rem warning color — easy to miss). No remediation guidance ("backend offline? start `make backend`"). No `ErrorCard` is rendered for this failure — and `ErrorCard.tsx` exists but is never imported by App.tsx.
- (d) Onboarding: **1/4** — No tooltip explaining "candidate case". No glossary. The tier banner reads "Tier 1 engineering candidate · not signed validation · not benchmark agreement" (`CandidateCasePicker.tsx:123`) — defensible disclaimer phrasing for compliance, but actively confusing to a first-time structural engineer who came to find a "leak". The word "leak" appears nowhere in the UI; the user must infer from the case_id substring `energy-leak`.
- (e) Plain-language: **1/4** — Acronyms (FRD, INP, GS, Tier 1, Tier 2, BC, signoff verdict) appear everywhere with zero expansion. NOTES.md excerpt is raw markdown reflow (case-author-controlled), not a curated "what's wrong with this case" sentence. No `?` cheatsheet (no `useKeyboardShortcuts` hook is wired in `App.tsx`, confirmed via `grep -n cheatsheet App.tsx` returning empty).
- **Subtotal: 7/20**

### Task 2 — Submit needs_more_evidence signoff
- (a) Task completion: **3/4** — `SignoffSubmissionForm` is rendered through `SignoffHistoryPanel` (`App.tsx:1646-1650` → `SignoffHistoryPanel.tsx:122` → `SignoffSubmissionForm.tsx:108`). `needs_more_evidence` is in `SUPPORTED_SIGNOFF_VERDICTS` (`signoffHistoryClient.ts:15`). A novice CAN complete the task. Deducted 1 for: the form is buried after ~7 large panels in the Visual tab; novice must scroll a long way and notice the inline "Record a signoff" form (`SignoffSubmissionForm.tsx:91` — 0.78rem label, not a section header).
- (b) Click count: **3/4** — Minimum: type reviewer, pick verdict, click submit (3 interactions). Actual: identical 3 interactions. -1 because the verdict dropdown shows raw enum values (`SignoffSubmissionForm.tsx:122-126` maps `SUPPORTED_SIGNOFF_VERDICTS` as `<option value={v}>{v}</option>` — `needs_more_evidence` is rendered as literal snake_case, no human label like "Needs more evidence").
- (c) Error recovery: **3/4** — 422 / 429 paths show inline error with retry-after (`SignoffSubmissionForm.tsx:170-183`). Client-side forbidden-claim preview surfaces before POST (`SignoffSubmissionForm.tsx:144-155`). One deduct: no remediation tip on what `needs_more_evidence` means to a novice — if they pick the wrong verdict by mistake they get no inline hint.
- (d) Onboarding: **2/4** — Form has a 0.66rem footer disclaimer (`SignoffSubmissionForm.tsx:196-206`) but no explanation of what each verdict implies. The form is unmarked as a section — easily mistaken for ambient panel text. No "?" cheatsheet (Phase 18 D scope).
- (e) Plain-language: **2/4** — Verdict enum values are snake_case English; "candidate_ready_for_review", "needs_more_evidence", "rejected_blocking_finding" etc. are technically self-documenting but not glossarized. Reviewer column accepts free text — no example.
- **Subtotal: 13/20**

### Task 3 — Trigger ccx re-run on cylinder-pv-candidate via Cmd-K
- (a) Task completion: **0/4** — **Cmd-K is not wired**. `grep -n "metaKey\|ctrlKey\|mod+k\|CommandPalette\|useKeyboardShortcuts" frontend/src/App.tsx` returns ZERO matches. The `CommandPalette.tsx` component (210 LOC) is present but never imported by App.tsx (verified: `grep -rn "CommandPalette" frontend/src/ | grep -v test | grep -v "components/CommandPalette"` returns nothing in the main bundle). The `useKeyboardShortcuts.ts` hook is similarly orphaned. Per hard rule "if completing a task requires reading source code → MAX 2 on this sub-score" — and here, Cmd-K cannot be invoked AT ALL, not even by reading source. Floor: **0**.
  - The Run Solver button exists (`App.tsx:1528-1531`) and POSTs to `/solver/run` (`solver.py:30` → `services/solver.py:35-50` actually spawns `ccx` via `asyncio.create_subprocess_exec`), so the re-run IS possible — just not via Cmd-K. If the task were "trigger a re-run" without the Cmd-K constraint, it would score 4/4. As written, the Cmd-K requirement makes it unreachable.
- (b) Click count: **0/4** — Cmd-K = 0 keystrokes possible. Infinite extra interactions vs the "minimum" (1 keypress + 1 Enter).
- (c) Error recovery: **0/4** — Pressing Cmd-K does nothing. The browser default behavior (focus URL bar in some browsers) takes over silently. No "did you mean to use the Run Solver button instead?" affordance.
- (d) Onboarding: **0/4** — No cheatsheet (no `?` binding exists). No "Press Cmd-K to open commands" hint anywhere in the chrome.
- (e) Plain-language: **0/4** — Not applicable; the feature doesn't exist in the running UI.
- **Subtotal: 0/20** (per the hard rule for tasks that are unimplemented in the current UI: floor each sub-dimension at 0-4; here genuinely 0 because Cmd-K is the load-bearing requirement and it's silently absent.)

### Task 4 — Swap material from steel to aluminium and re-run
- (a) Task completion: **0/4** — **No material swap UI exists.** `find frontend/src/components -name "MaterialPicker*" -o -name "MeshControl*"` returns empty. The Slice C blueprint deliverables `MaterialPickerPanel.tsx` and `MeshControlPanel.tsx` were never created. Backend has `services/materials/api.py` (`Material` dataclass + `list_materials` / `get_material`) but **no HTTP route** exposes it — `find backend/app/api/routes -name "materials*"` returns empty. The `/solver/run` request schema (`solver.py:17-21` — `RunRequest` = `case_id, inp_path, analysis_type, num_modes`) has NO material parameter. The `inp_writer.write_smoke_static_inp` (`backend/app/adapters/calculix/inp_writer.py:57`) takes a `MinimalHexMaterial` but is wired only into the smoke INP, not into the live solver pipeline.
- (b) Click count: **0/4** — Not achievable; clicks irrelevant.
- (c) Error recovery: **0/4** — N/A; nothing to err on.
- (d) Onboarding: **0/4** — No material-related UI text at all in App.tsx beyond `materialSummary` which is read-only metadata display (`App.tsx:892-894, 1159`).
- (e) Plain-language: **0/4** — N/A.
- **Subtotal: 0/20** (hard rule: feature not implemented in current UI → ≤ 5/20.)

### Task 5 — View resulting stress contour overlay
- (a) Task completion: **1/4** — `ResultMeshPlaybackPanel.tsx` renders SVG wireframe geometry over frames (`ResultMeshPlaybackPanel.tsx:18-26` defines `ProjectedPolygon` with `fill` + `stroke` + `opacity`). `grep -n "vonMises\|stress\|contour\|colorScale" frontend/src/components/ResultMeshPlaybackPanel.tsx frontend/src/resultMeshPlayback.ts` returns ZERO matches — there is no stress-field-driven coloring. The panel renders shape evolution, not a contour. The blueprint explicitly says "ResultMeshPlaybackPanel extended: accepts new CalculiX .frd payload schema; renders stress contour overlay" (`.planning/FM-04A_PHASE18_BLUEPRINT.md:113`) — this extension is NOT in the code.
- (b) Click count: **1/4** — Even if the contour existed, novice would have to navigate to Visual tab (default — 0 clicks) then scroll past ~10 panels to find ResultMeshPlaybackPanel. No legend / colorbar / field-selector control would exist either.
- (c) Error recovery: **1/4** — Panel shows "result_mesh.json unavailable" on 404 (`ResultMeshPlaybackPanel.tsx:55-58`) but provides no remediation (e.g., "run the solver first via `/solver/run`").
- (d) Onboarding: **1/4** — Panel label is "Result mesh playback" — does NOT mention stress. A user looking for stress contour would not associate this panel with their goal.
- (e) Plain-language: **1/4** — No legend, no σ_VM symbol explanation, no SI-unit annotation. The panel is technically present but communicates nothing about stress to a novice.
- **Subtotal: 5/20** (hard rule: stress contour overlay is unimplemented; floor 5/20 — granted the partial credit because the playback panel itself exists.)

## Top 3 deficiencies (with file:line citations)

1. **Phase 18 D components are orphaned dead code.** `frontend/src/components/CommandPalette.tsx`, `DriftBadge.tsx`, `SkeletonCard.tsx`, `ErrorCard.tsx`, `EmptyStateCard.tsx`, and `frontend/src/hooks/useKeyboardShortcuts.ts` are NEVER imported by `frontend/src/App.tsx` (1926 LOC monolith, verified with `grep -rn "CommandPalette\|useKeyboardShortcuts\|DriftBadge\|SkeletonCard\|EmptyStateCard" frontend/src/ | grep -v test`). No `WorkbenchShell.tsx` exists. The blueprint promised "App.tsx shrinks to <500 LOC composition root" (`.planning/FM-04A_PHASE18_BLUEPRINT.md:102`) — App.tsx is still 1926 lines. **The components ship as test-only artifacts**; their unit tests in `frontend/test/Phase18D.test.tsx` pass without proving any UX value.

2. **Material swap (Task 4) is end-to-end missing**: no `MaterialPickerPanel.tsx` (Slice C deliverable, `.planning/FM-04A_PHASE18_BLUEPRINT.md:84`), no `backend/app/api/routes/materials.py` (Slice C deliverable, `.planning/FM-04A_PHASE18_BLUEPRINT.md:83`), and `RunRequest` (`backend/app/api/routes/solver.py:17-21`) has no material override field. The backend material library `backend/app/services/materials/api.py:38-65` exists with `Material` dataclass + `library.json`, but is unreachable from the UI.

3. **Stress contour overlay (Task 5) is end-to-end missing.** `ResultMeshPlaybackPanel.tsx` renders only wireframe geometry — `grep -nE "vonMises|stress|contour|colorScale|color_scale" frontend/src/components/ResultMeshPlaybackPanel.tsx frontend/src/resultMeshPlayback.ts` returns zero matches. The blueprint deliverable "ResultMeshPlaybackPanel extended: accepts new CalculiX .frd payload schema; renders stress contour overlay" (`.planning/FM-04A_PHASE18_BLUEPRINT.md:113`) is not delivered.

## One specific UX improvement that would lift the lowest-scoring task

**Wire Cmd-K into App.tsx**, lifting Task 3 from 0/20 to ~12-15/20 in a single afternoon. The components are ready and tested. Concrete steps:

1. In `App.tsx` top imports add:
   ```ts
   import { useState as useStateAlias } from 'react';  // already imported
   import { CommandPalette } from './components/CommandPalette';
   import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts';
   import type { Command } from './commands/registry';
   ```
2. Inside the App component, add `const [paletteOpen, setPaletteOpen] = useState(false);`.
3. Define a command list at component scope referencing existing handlers, e.g.:
   ```ts
   const commands: Command[] = useMemo(() => [
     { id: 'run-solver', label: 'Run solver on current case', category: 'solver',
       hotkey: 'mod+enter', handler: runSolver },
     { id: 'select-leak-case', label: 'Select rod-wave-impact-energy-leak-candidate',
       category: 'navigation',
       handler: () => setSelectedCandidateCaseId('rod-wave-impact-energy-leak-candidate') },
     { id: 'switch-tab-visual', label: 'Switch to 3D Scene tab', category: 'view',
       hotkey: 'g 1', handler: () => setActiveTab('visual') },
     // ... one entry per major action
   ], [runSolver]);
   ```
4. Add the shortcut binding:
   ```ts
   useKeyboardShortcuts([
     { hotkey: 'mod+k', handler: (e) => { e.preventDefault(); setPaletteOpen(true); },
       fireInTextInput: true },
   ]);
   ```
5. Render `<CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} commands={commands} />` near the top of the JSX (sibling to `<aside>`).

That single wiring unlocks Task 3 (`Cmd-K → "run solver" → Enter`) and gives partial credit to Tasks 1 & 4 once the corresponding commands are added — assuming Task 4's underlying material-swap pipeline is also built, which it currently isn't.

## Honest disclosure

- I did NOT spin up the actual frontend dev server. Findings are based on static analysis of `frontend/src/App.tsx` (1926 LOC), `frontend/src/components/*.tsx`, and `backend/app/api/routes/*.py`. If a `git pull` since my analysis introduced the missing wiring, my scores are stale for that delta.
- The Run Solver button (`App.tsx:1528-1531`) was confirmed to POST to `/solver/run` and the backend route (`backend/app/api/routes/solver.py:30-50` + `backend/app/services/solver.py:35-50`) does spawn `ccx` via `asyncio.create_subprocess_exec`. I did NOT verify by actually running ccx; that's a Slice A integration concern, not a UX-agent concern.
- I assumed a novice would NOT read source code or invoke `curl` directly. The "AI as co-pilot" via `ChatPanel` (imported at `App.tsx:24`) might be a back-door for advanced users to complete Tasks 3/4/5 by asking the AI — that would be a different evaluation (AI-driver capability, not UX clarity).
- The `frontend/test/Phase18D.test.tsx` test file exercises `CommandPalette`, `DriftBadge`, `EmptyStateCard`, `ErrorCard`, `SkeletonCard`, `useKeyboardShortcuts` in isolation (`test:14-40` imports). These tests passing tells us the components *work in isolation* — not that the UX exists for a real user. This is a common blueprint-vs-delivery gap; I'm flagging it honestly rather than rewarding the green-checkmark-without-integration pattern.
- I evaluated against the user task wording verbatim ("via Cmd-K", "swap the material", "stress contour overlay"). Re-scoping any of these tasks would change scores; e.g., "trigger a re-run by any means" → Task 3 becomes ~14/20 (the Run Solver button works, modulo the candidate-case list issue from Task 1).
- The blueprint's own "honest pre-warning" projects UX 60-85 at single-session Phase 18 (`.planning/FM-04A_PHASE18_BLUEPRINT.md:201`). My 38/100 is below that projection band, primarily because the 5 specified user tasks were chosen to stress Slice D + Slice C deliverables and those slices were not integrated into the live UI. If the test agent had been given a different 5-task set focused on Slice A/B (real solver + tier discriminator), the score would likely land in the projected 60-85 band.
