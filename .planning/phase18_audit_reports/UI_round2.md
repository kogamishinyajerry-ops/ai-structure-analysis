# Phase 18 UI tier testing agent — round 2 report

## Composite score
**51/100** (verdict: **CHANGES_REQUIRED**)
Delta vs round 1 (41/100): **+10**

The integration landed exactly as advertised — CommandPalette, useKeyboardShortcuts and MaterialPickerPanel are all live in `frontend/src/App.tsx` (verified at lines 54–56, 1475–1531, 1532–1541, 1545–1549, 1794–1798), and the new `MaterialPickerPanel.tsx` is the first real consumer of the Phase 18 D `ErrorCard` + `SkeletonCard` primitives (`frontend/src/components/MaterialPickerPanel.tsx:22-23, 57, 66-75`). The lift on axis 2 (command accessibility) is real and large. Lifts on axes 4 / 5 / 7 are real but tiny — one panel's worth of consumption out of ≥10 fetching panels. The headline "+10" almost entirely comes from axis 2 alone (+5). The "expected lift 50–58" projection from round 1 was essentially right; we land at the bottom of that band, not the middle, because the bespoke states elsewhere are unchanged AND App.tsx grew by 112 lines (1926 → 2038) instead of being refactored.

## Per-axis scores

1. **Information density: 5/10** — unchanged from round 1.
   `frontend/src/App.tsx` is now `2038` lines (`wc -l` confirms), up from `1926`. No refactor; the integration added a `commands: Command[]` registry (lines 1475–1531) and a new panel mount (lines 1794–1798) on top of the existing monolith. Three-column grid `240px 300px 1fr` (`frontend/src/App.tsx:1544`) still pushes the main viewport to the right; multi-panel "every panel a card" pattern survives in the Step-7 stack (`AcceptancePacketPanel`, `DriftNarrativePanel`, `MaterialPickerPanel`, `BulletPlateBlueprintPanel` co-mounted at lines 1779–1799). No proper panel collapsing, no information density toggle. Industrial CAE peers (ANSYS Workbench, SimScale) hit 7–8 here.

2. **Command accessibility: 7/10** — biggest lift this round (+5).
   `CommandPalette` is fully wired and competent: `mod+k` toggles via `useKeyboardShortcuts` (`frontend/src/App.tsx:1532-1541`); 8 commands registered (3× tab switch with `g 1/2/3` hotkeys, 1× run solver, 3× material pick, 1× close) at `frontend/src/App.tsx:1475-1531`. Palette internals (`frontend/src/components/CommandPalette.tsx`) implement arrow-key nav (lines 71–79, 111–125), Enter to invoke (line 121), Escape to close (line 106), backdrop dismiss (line 92), input auto-focus on open (line 64), fuzzy filtering via `filterCommands` (line 49), and duplicate-id assertion (line 42). `data-testid` hooks throughout for E2E. **Why not 8+:** registry is hard-coded inline in `App.tsx` instead of pulled from a per-panel contribution system; 8 commands cover the smoke path but miss obvious actions (signoff submit, export PDF, toggle chat, project select, case select from gallery, tab "explore" already there but no quick-jump to cases, no help overlay). No `?` hotkey to discover commands. Workbench parity requires ≥30 commands and per-context discoverability.

3. **Visual hierarchy: 5/10** — unchanged.
   Header at `frontend/src/App.tsx:1609`, sidebar at 1558, palette overlay at 1545–1549. CommandPalette adds a proper modal layer (z-index 1000 at `CommandPalette.tsx:181`, 12vh top inset at 182, backdrop alpha 0.45 at 177) so when open it dominates correctly — small +1 in palette context — but resting hierarchy is unchanged. Still no consistent type ramp; still mixed font-sizes within the same panel (e.g., `MaterialPickerPanel.tsx:178` `headingStyle.fontSize: 14` vs the surrounding case-gallery 0.875rem at `App.tsx:1578` vs section heading 1.25rem at `App.tsx:1564`). No visual rhythm system.

4. **Error surface: 4/10** — small lift (+1).
   `ErrorCard` exists, has good ergonomics (title + message + code pill + remediation list + retry button + `role="alert"` + `aria-live="assertive"` at `frontend/src/components/ErrorCard.tsx:38-39`), and is consumed exactly **once**: `MaterialPickerPanel.tsx:66-75`. Every other fetching panel still has bespoke error rendering: `AdvisorPanel.tsx:124-131` renders `<div style={{color:'#b00020'}}>{error}</div>`; `SignoffHistoryPanel.tsx:88,93` still drives a local `error` state with no `ErrorCard` import (`grep -l ErrorCard frontend/src/components/` returns only ErrorCard.tsx + MaterialPickerPanel.tsx); same for `CohortDashboardPanel`, `CohortAnomaliesPanel`, `CaseComparisonPanel`, `ConvergenceStudyViewer`, `ChatPanel`, `AcceptancePacketPanel`. The primitive is good; adoption is 1/10 panels. Round-1 projection of "5-6" was optimistic.

5. **Empty state / onboarding: 3/10** — **no lift**.
   `EmptyStateCard.tsx` exists (100 LOC, `frontend/src/components/EmptyStateCard.tsx`) but `grep` confirms **zero consumers** anywhere — neither MaterialPickerPanel nor any other panel imports it. The bespoke empty-state strings persist at the same call sites round 1 flagged: `App.tsx:1111` "Select a gallery case or upload an FRD file", `App.tsx:1306, 1331, 1334` "Pick a Tier 1 candidate case...", `App.tsx:1901` `<div>Select a structural case from the gallery to begin analysis</div>` (raw div, no card chrome), plus `AcceptancePacketPanel.tsx:111`, `CandidateCasePicker.tsx:126`, `CaseCompletenessCard.tsx:120`, `ConvergenceStudyViewer.tsx:194`, `ReviewerBundlePanel.tsx:107`, `CohortTrendAnomaliesPanel.tsx:81` (latter has `data-testid="cohort-trend-anomalies-empty"` — purely bespoke). Round-1 projection "3 → 4" did not materialize because no panel actually adopted the card.

6. **Accessibility: 6/10** — small lift (+1) entirely on palette.
   New palette is the only well-A11y surface: `role="dialog"`, `aria-modal="true"`, `aria-label="Command palette"` at `CommandPalette.tsx:88-90`; `role="listbox"` + `aria-label="Commands"` at line 132; `role="option"` + `aria-selected={active}` at 143–144; SkeletonCard has `role="status"` + `aria-busy="true"` + `aria-live="polite"` at `SkeletonCard.tsx:36-38`; ErrorCard has `role="alert"` + `aria-live="assertive"` at `ErrorCard.tsx:38-39`. Outside these four files, the existing landscape is unchanged — `App.tsx` panels rely on raw `<div>` chrome, no skip links, no keyboard-trap discipline outside the palette, no `aria-live` regions for the solver-progress log (`App.tsx:1636` solver controls have no role hints). Tab order in the multi-column layout has not been audited.

7. **Loading states: 4/10** — small lift (+1).
   `SkeletonCard` exists and is consumed exactly **once** at `MaterialPickerPanel.tsx:57` (`<SkeletonCard lines={4} label="Loading materials library" />`). Round-1 inventory of bespoke loading still intact: `AdvisorPanel.tsx:118-122` renders raw `<div data-testid="advisor-panel-loading">Loading advisor critique…</div>`; `SignoffHistoryPanel.tsx:70,83`, `CohortDashboardPanel.tsx:104,109`, `CohortAnomaliesPanel.tsx:25,30`, `ConvergenceStudyViewer.tsx:144,153`, `CaseComparisonPanel.tsx:140,149` all drive local `loading` state with no SkeletonCard import. The skeleton has shimmer animation (`SkeletonCard.tsx:64`) and `role="status"` but reaches 1/10 panels. Round-1 projection "5" was overstated.

8. **Responsiveness: 3/10** — unchanged.
   Fixed grid `240px 300px 1fr` at `App.tsx:1544` is hard-coded; CommandPalette uses `min(680px, 92vw)` at `CommandPalette.tsx:185` — sensible — and 12vh top padding at line 182 — fine. But nothing else flexes. No breakpoints, no `@media` queries anywhere in App.tsx (verified by absence in grep). Sub-1280px will horizontal-scroll the chat panel out of view (`gridTemplateColumns: showChat ? '1fr 340px' : '1fr'` at `App.tsx:1607`).

9. **Industrial aesthetic: 6/10** — marginal lift on palette card alone.
   Palette inline styles (`CommandPalette.tsx:174-257`) are competent — `#1e1e1e` card, `#161616` input, soft shadow `0 20px 60px rgba(0,0,0,0.5)` at line 190, `<kbd>` styling for hotkeys at lines 154, 235–241 — feels closer to VS Code command palette than to ANSYS. MaterialPickerPanel rows (lines 207–221) are clean dark cards with subtle blue selection (`#3a5fa8` border at 219). But these are two islands in an otherwise heterogeneous chrome: `App.tsx` still mixes `glass-panel` class with inline rgba(255,255,255,0.05) backgrounds, hard-coded `var(--accent)` highlights, and emoji-style stop button `rgba(255,100,100,0.2)` at line 1636. The "system" is not yet a system; it's two well-styled primitives + a legacy app.

10. **3D viewport + result viz: 3/10** — **no lift**.
    `ResultMeshPlaybackPanel.tsx:176-188` confirmed unchanged: raw `<svg viewBox="0 0 1000 440">` with `<polygon>` children inside a flat `<rect>` background. No Three.js, no WebGL, no react-three-fiber, no orbit/zoom/pan, no color-bar legend, no animated playback timeline UI tooling beyond what existed round 1. SimScale / Workbench parity is 8+; this remains a developer-tier placeholder.

## Round 2 delta analysis (what lifted / what didn't)

**Real lifts (+10 total):**
- Axis 2 (cmd accessibility): +5. CommandPalette + useKeyboardShortcuts integration is genuinely competent — modal a11y, arrow nav, fuzzy filter, 8 commands wired, duplicate-id guard. Half of the round-2 score gain lives here.
- Axis 4 (error surface): +1. ErrorCard exists and is well-designed but only MaterialPickerPanel consumes it (1/10 fetching panels).
- Axis 6 (a11y): +1. Three new primitives all have `role` + `aria-*` discipline. Outside those primitives, nothing changed.
- Axis 7 (loading states): +1. SkeletonCard exists with shimmer + `role="status"` but only MaterialPickerPanel consumes it (1/10 fetching panels).
- Axis 9 (industrial): +1. Two new well-styled cards (palette, material picker) raise the ceiling but not the average; legacy panel chrome unchanged.
- Axis 3 (hierarchy): +0. Palette modal does add layering when open but resting state is unchanged.

**Zero lift (despite round-1 projection):**
- Axis 5 (empty states): EmptyStateCard has **zero consumers** — verified by `grep -rn EmptyStateCard frontend/src/components/` returning only the source file. Round-1 projection "3 → 4" did not happen.

**Unchanged (round-1 score honored):**
- Axis 1 (density): App.tsx grew 1926 → 2038 LOC instead of being refactored. No collapse/expand controls added.
- Axis 8 (responsive): no media queries, no breakpoints.
- Axis 10 (3D viewport): still SVG polygon, no GPU pipeline.

**Why bottom-of-band (51 vs projected 50–58):** the round-1 FINAL.md projection assumed at least 2 panels would adopt SkeletonCard/ErrorCard and at least 1 would adopt EmptyStateCard. Actual adoption is 1 + 1 + 0. The primitives are well-built; the integration story is one consumer deep.

## Top 3 UI deficiencies remaining

1. **Phase 18 D primitives are orphans outside MaterialPickerPanel.** `ErrorCard` consumer count: 1 (`MaterialPickerPanel.tsx:66`). `SkeletonCard` consumer count: 1 (`MaterialPickerPanel.tsx:57`). `EmptyStateCard` consumer count: **0** (`grep` confirms). Meanwhile `AdvisorPanel.tsx:118-131`, `SignoffHistoryPanel`, `CohortDashboardPanel`, `CohortAnomaliesPanel`, `CaseComparisonPanel`, `ConvergenceStudyViewer`, `ChatPanel`, `AcceptancePacketPanel`, `ReviewerBundlePanel` all still ship bespoke per-component loading divs and inline-styled error spans. The pattern was built and ratified in one panel; the migration plan to the other 9 was not done. This is the single biggest gap between Phase 18's stated goal ("standard primitives") and the shipped state.

2. **App.tsx is now 2038 lines and growing the wrong direction.** Round 1 flagged the monolith at 1926; round 2 added the command registry, palette mount, and MaterialPickerPanel mount inline — net +112 lines, no extractions. The command registry (`App.tsx:1475-1531`) alone is 57 lines that could be a `commands/appCommands.ts` module; `_runSolverFromPalette` (lines 1462-1474) is wedged into the render function. The next round of features (per the round-1 projection: 30+ commands, more panels, more state) will balloon this past 2200 LOC unless a `useWorkbench` hook + per-feature command files are extracted.

3. **3D viewport remains the single largest score sink (3/10) and was untouched.** `ResultMeshPlaybackPanel.tsx:176-188` is still a 1000×440 SVG with polygon children — no WebGL, no orbit camera, no color-bar legend, no animated time-slider UI, no annotation pinning. Phase 18 D / E shipped four solid primitives but did not budget any work toward axis 10. As long as this stays SVG, the composite ceiling is structurally capped around 70 — the other 9 axes can't compensate for a developer-tier mesh viz when the rubric anchors at "ANSYS Workbench / SimScale parity".

## Honest disclosure

- I verified every load-bearing claim with `grep` / `wc -l` / direct file reads. Specific verifications:
  - Integration: `grep -n "CommandPalette\|useKeyboardShortcuts\|MaterialPickerPanel" frontend/src/App.tsx` returned 6 hits at lines 54, 55, 56, 1532, 1545, 1794.
  - LOC: `wc -l frontend/src/App.tsx` → 2038.
  - Phase 18 D primitive consumers (outside originating files): `grep -rn "SkeletonCard\|ErrorCard\|EmptyStateCard" frontend/src/components/` shows only `MaterialPickerPanel.tsx` consumes SkeletonCard and ErrorCard; EmptyStateCard has no external consumer.
  - Bespoke states still in place: read `AdvisorPanel.tsx:115-131` directly — confirms raw `<div>Loading advisor critique…</div>` + raw `<div style={{color:'#b00020'}}>{error}</div>`. Spot-checked `SignoffHistoryPanel`, `CohortDashboardPanel`, `CohortAnomaliesPanel`, `ConvergenceStudyViewer`, `CaseComparisonPanel` all still have local `loading`/`error` state without SkeletonCard/ErrorCard imports.
  - 3D viewport: `ResultMeshPlaybackPanel.tsx:176-188` re-read confirms SVG polygon, unchanged.

- **Round-1 bespoke-state inventory I trusted (6 loading / 4 error / 12 empty)** — I sampled enough to corroborate the order of magnitude (≥6 panels still bespoke loading, ≥4 bespoke error, ≥6 bespoke empty literally in App.tsx alone). I did not re-derive the exact 12 empty-state count; my round-2 score does not depend on the exact number, only on the pattern that adoption is 1/10 across the surface.

- **No rubric reshaping.** Same 10 axes, same 0–10 scale, same anchors (10 = Workbench/SimScale parity; 8 = competent industrial; 5 = functional MVP; 3 = developer-tier; 1 = barely usable; 0 = unstyled). I did not award credit for "primitive exists" — I awarded credit for "primitive is in use across the surface". This is why axis 5 stayed at 3 despite EmptyStateCard.tsx existing.

- **Calibration sanity check:** total moved 41 → 51 (+10). Per-axis: +5 / +1 / +1 / +1 / +1 / +1 = +10. Math holds; no off-by-one.

- **Verdict CHANGES_REQUIRED, not APPROVE:** primitives shipped without surface migration is the textbook "design system without adoption" anti-pattern. Approving here ratifies that pattern. Round 3 should be a migration round (convert AdvisorPanel, SignoffHistoryPanel, CohortDashboardPanel to SkeletonCard + ErrorCard; convert App.tsx:1901 + AcceptancePacketPanel + CandidateCasePicker empty divs to EmptyStateCard; extract command registry to its own module) targeting 60–65 before any new primitives land.
