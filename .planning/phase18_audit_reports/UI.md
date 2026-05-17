# Phase 18 UI tier testing agent — report

> Benchmarks for scoring: ANSYS Workbench (Mechanical), SimScale (web-tier),
> Abaqus CAE. No live dev server was run; scoring is purely from static reading
> of `frontend/src/`. See **Honest disclosure** at the bottom.

## Composite score
**41 / 100** (verdict: **CHANGES_REQUIRED**)

APPROVE requires composite ≥ 99 AND every axis ≥ 9.5. This build does not come
close, primarily because **the Phase 18 D primitives that were built (palette,
skeleton, error card, empty state, drift badge, shortcuts hook) are not wired
into `App.tsx` or any of the 28 panels**. They exist as orphan files plus tests.

Verified by `grep` for every primitive name across `frontend/src/` (excluding
the primitive source files and the dedicated `test/Phase18D.test.tsx`): zero
imports outside of the primitives themselves. The only hit was a doc-comment
inside `frontend/src/commands/registry.ts:6`. Translation: Phase 18 D shipped
building blocks but not the wiring.

## Per-axis scores (with file:line citations)

### 1. Information density vs whitespace balance — **4 / 10**

- The main "visual" tab is a single vertical column that renders 18+ panels
  back to back: `CohortDashboardPanel`, `CohortSubstantiationPanel`,
  `CaseCompletenessCard`, `CandidateCasePicker`, `AcceptancePacketPanel`,
  `ConvergenceStudyViewer`, `CaseComparisonPanel`, `ReviewerBundlePanel`,
  `ArchivedPacketDiffPanel`, `ReproducibilityManifestCard`,
  `CohortExecutiveSummaryPanel`, `CohortAnomaliesPanel`,
  `CohortTrendAnomaliesPanel`, `TrustScoreGauge`, `SignoffHistoryPanel`,
  `TrustScoreTimelineChart`, `CohortSnapshotPanel`, `ProvenancePanel`,
  `AdvisorPanel`, `DriftNarrativePanel`, `BulletPlateBlueprintPanel`
  (`frontend/src/App.tsx:1555-1688`). ANSYS Workbench uses a tree + tabbed
  property inspector to keep this kind of evidence load navigable; this app
  has none of that.
- Top-level grid is hard-coded 3 columns `240px 300px 1fr` with no collapse
  or resize affordance (`frontend/src/App.tsx:1446`).
- `OperatorStatusPanel` inside the same scroll column further stacks a
  strip, a sections grid, and a golden-sample queue grid
  (`frontend/src/App.tsx:1854-1913`) — burying the rest of the workbench
  600+ px down before the user ever sees the 3D scene.

### 2. Command accessibility — **2 / 10**

- `CommandPalette.tsx` exists (`frontend/src/components/CommandPalette.tsx:37`)
  and `useKeyboardShortcuts` exists
  (`frontend/src/hooks/useKeyboardShortcuts.ts:88`), but **neither is imported
  by `App.tsx`** (verified by grep).
- `frontend/src/commands/registry.ts` defines the type system + filter
  helpers but **no command list is exported**, no command set is ever passed
  to the palette, and no `mod+k` binding is registered anywhere.
- Only available "shortcut" today is the `Run Solver` button
  (`frontend/src/App.tsx:1528`) — no Cmd-K, no `?` cheatsheet, no `g <n>`
  navigation. SimScale's web UI ships a working palette; ANSYS Workbench
  ships ribbon hotkeys + customizable shortcuts. This app ships neither.
- Points for the primitive being well-built (palette has Escape, arrow nav,
  duplicate-id assertion at `CommandPalette.tsx:42`, click-outside dismiss at
  `:92`). That's why this isn't a `0/10` — but if it isn't wired, the user
  can't reach it.

### 3. Visual hierarchy and typography — **5 / 10**

- `index.css:1` imports Plus Jakarta Sans, a respectable display face. Color
  tokens are coherent: `--bg-base #020617`, `--accent #10b981`,
  `--text-primary/-secondary/-muted` (`frontend/src/index.css:3-16`). That's
  a real design language, not vibes-CSS.
- But typography is inconsistently applied via **inline `style={{}}`** on
  almost every element in `App.tsx` (e.g., `fontSize: '0.75rem'`,
  `'0.875rem'`, `'0.78rem'`, `'1.1rem'`, `'1.25rem'`, `'0.66rem'`,
  `'0.68rem'`, `'0.72rem'`, `'0.82rem'`, `'0.86rem'`, `'0.88rem'`, `'1rem'`,
  `'16px'`, `'14px'`, `'13px'` — found across `App.tsx:1457`,
  `:1461`, `:1472`, `:1857`, `:1858`, `:1860`, `:1867-1908`,
  `CommandPalette.tsx:200/231/240/249`). Eyeballed: at least **15 distinct
  font sizes** in the visible UI. A graded type scale (ANSYS / SimScale use
  ≤ 6 steps) would let the eye anchor.
- Heading levels: `App.tsx:1461` uses `<h2>` for "StructureAI" brand title,
  `:1772` uses `<h2>` for "Design Auditor Insight", `:1858` uses `<h2>` for
  "Evidence-first workbench state". No `<h1>` anywhere — DOM heading
  hierarchy is broken for assistive tech and for outline mode.

### 4. Error/warning surface design — **3 / 10**

- `ErrorCard.tsx` exists with role="alert", title, message, remediation list,
  retry button, error code pill (`frontend/src/components/ErrorCard.tsx:34-79`).
  Quality is fine.
- **It is imported by zero panels.** Instead every panel rolls its own
  inline error string:
  - `CohortAnomaliesPanel.tsx:64` — `<div style={{ fontSize: '0.78rem',
    color: 'var(--danger, #c0392b)' }}>{error}</div>` (raw error string, no
    remediation, no retry)
  - `AdvisorPanel.tsx:124-131` — similar bespoke inline error
  - `ProvenancePanel.tsx:91-93` — same pattern, bespoke
  - `CohortDashboardPanel.tsx:174-176` — error/empty state merged into one
    grey `<div>` ("No Tier 1 candidate cases found...")
  - `ResultMeshPlaybackPanel.tsx:154` — error shown via local
    `PanelState` helper, not `ErrorCard`
- `App.tsx` itself silently swallows fetch errors to `console.error`
  (`:498, :517, :577, :607, :650, :672, :699, :756`) — none of these
  surface a user-visible error component. A reviewer hitting a 500 from the
  backend sees the workbench just sit there with no feedback.

### 5. Empty state and onboarding affordances — **3 / 10**

- `EmptyStateCard.tsx` exists with glyph, headline, body, action button
  (`frontend/src/components/EmptyStateCard.tsx:35-58`). Quality is fine.
- **It is imported by zero callers.** Empty states across the workbench
  use grey strings instead:
  - `App.tsx:1786-1790` — the main empty state ("Select a structural case
    from the gallery to begin analysis") is a hand-rolled column of
    `<LayoutDashboard>` + plain text, no primary action button to guide
    the user
  - `App.tsx:807-936` — 25+ "No X surfaced" string fallbacks
    (`'No active case'`, `'No solver job started'`, `'No golden-sample
    reference selected'`, `'No FailurePattern reference surfaced'`, `'No
    report validation yet'`, ...) all rendered as plain text into
    `OperatorStatusPanel`. The user is told things are missing without
    being told what action to take.
  - `CohortDashboardPanel.tsx:174-176` — empty cohort is rendered as a
    grey paragraph, no action.
  - `ResultMeshPlaybackPanel.tsx:201` — "No renderable mesh frame" is a
    grey overlay, no remediation.

### 6. Accessibility — **5 / 10**

- The primitives ship a11y correctly: `CommandPalette.tsx:88-90`
  (`role="dialog" aria-modal aria-label`), `SkeletonCard.tsx:36-38`
  (`role="status" aria-busy aria-live`), `ErrorCard.tsx:39-41`
  (`role="alert" aria-live="assertive"`), `EmptyStateCard.tsx:39-40`
  (`role="status"`), `DriftBadge.tsx:74-79` (`aria-label` computed).
- But `App.tsx` itself has **one** `aria-label` in 1926 LOC
  (`:1854` on the trust-center `<section>`). Buttons in the case gallery,
  tab bar, nav, and run-solver row have no `aria-label`, no
  `aria-current`, no `aria-pressed`.
- Tab order: the nav button at `:1465` is announced as `nav-item active`
  but has no `aria-current="page"`. The Compass tab at `:1552` toggles
  visual state via inline style only — no `role="tab"` /
  `aria-selected`.
- Color contrast: `--text-muted: #64748b` on `--bg-base: #020617` is
  ≈ 4.6:1 — borderline AA, fails AAA for body. `DriftBadge` warn-state
  uses `#ffe3b3` on `#5c4416` ≈ 6.5:1 — passes AA. Mixed.
- iframe at `App.tsx:1747` has `title="FEA Visualization"` ✓.

### 7. Loading state design — **3 / 10**

- `SkeletonCard.tsx` exists with shimmer animation
  (`frontend/src/components/SkeletonCard.tsx:19-46`). Quality is fine.
- **It is imported by zero panels.** Every panel rolls its own loading state:
  - `App.tsx:1715-1716` — `<div className="shimmer-active"
    style={{ height: '400px', ... }}></div>` uses the inline CSS shimmer
    keyframe, not the new component
  - `CohortAnomaliesPanel.tsx:61` — `<div>loading…</div>` literal lowercase text
  - `CohortDashboardPanel.tsx:170` — `loading cohort overview…` literal
  - `ProvenancePanel.tsx:88` — `loading…` literal
  - `AdvisorPanel.tsx:118-121` — bespoke loading div with `data-testid`
  - `ResultMeshPlaybackPanel.tsx:151-152` — `<PanelState>` helper with a
    spinning Loader2, bespoke to that file
- The result is six different "loading" affordances for the same conceptual
  state. ANSYS Workbench uses one consistent progress monitor; SimScale uses
  one consistent skeleton. This codebase has none of that.

### 8. Responsiveness / feel — **3 / 10**

- `App.tsx` is **1926 lines in a single React function**. All panels are
  re-rendered together on any state change because the App component owns
  ~40+ `useState` hooks (a 30-second grep counted at least
  `loading`, `solving`, `activeCaseId`, `activeExperiment`,
  `comparedIndices`, `selectedModeIndex`, `selectedCandidateCaseId`,
  `comparisonCaseA`, `comparisonCaseB`, `snapshotLabelA`, `snapshotLabelB`,
  `caeReviewCards`, `latestSignoff`, `showChat`, `showConsole`,
  `analysisType`, `report`, `file`, `selectedProjectId`, ...). No
  `React.memo`, no `useMemo` on the heavy panels seen.
- Fetches in `App.tsx` are uncoordinated: 6+ separate `setLoading(true)`
  / `setLoading(false)` blocks at `:557`, `:585`, `:660`, `:744`, `:760`
  with no cancellation tokens — switching cases mid-load can race.
- The visual tab renders 18+ panels at once (`App.tsx:1555-1688`), each
  of which fires its own `useEffect` fetch. Browser will see a 15-20
  concurrent fetch burst on every case change.
- No virtualization on the case gallery (`App.tsx:1474`) — would be fine
  for the FALLBACK_CANDIDATE_CASES set, less fine if a real cohort grows.

### 9. Industrial aesthetic — **6 / 10**

- The visual language is **actually decent**: deep navy `#020617`,
  emerald-green accent `#10b981`, glass-blur panels
  (`index.css:5-19, 65-77`), shimmer animation (`:135-160`). It reads as
  "modern engineering tool" — closer to SimScale's web UI than to
  ANSYS Workbench (the latter is dated). It is recognizably "industrial,"
  but it veers toward web-startup chic, not CAE-platform gravitas.
- Brand is consistent: "Structure**AI**" wordmark
  (`App.tsx:1461`), "not signed validation" red pill repeated as a
  honesty marker (`App.tsx:1860-1863`, `ResultMeshPlaybackPanel.tsx:138-148`).
  The honesty marker is genuinely nice and unusual.
- But the **inline-style sprawl** in `App.tsx` is the antithesis of
  industrial polish: spacings, paddings, radii, font weights, font sizes
  are all inline literals with no token discipline. Inline styles also
  short-circuit `App.css` (which is literally 1 byte —
  `frontend/src/App.css` has length 1, i.e., blank). For a 1926-LOC
  monolith, having zero CSS in the App stylesheet is a real signal that
  the design-system pass never landed.
- Phase 18 D primitives commit the same sin: every styling value is an
  inline `CSSProperties` literal (`CommandPalette.tsx:174-257`,
  `ErrorCard.tsx:81-142`, `EmptyStateCard.tsx:62-100`,
  `SkeletonCard.tsx:48-65`, `DriftBadge.tsx:86-102`). The components'
  own header comments say "no CSS-Modules / Tailwind step in Phase 18 D.
  The full design-system pass is Slice E+ territory."
  (`CommandPalette.tsx:172-173`). That's honest scope-disclosure but it
  caps polish.

### 10. 3D viewport + result visualization clarity — **3 / 10**

- The headline "3D Scene" tab (`App.tsx:1550`) does **not contain a real
  3D viewport**. It contains:
  1. `ResultMeshPlaybackPanel` (`App.tsx:1730-1735`), which renders the
     mesh as an **SVG `<polygon>` projection inside a static
     `<svg viewBox="0 0 1000 440">`** (`ResultMeshPlaybackPanel.tsx:176-188`).
     No camera, no orbit, no shading, no depth cue, no element picking.
     It is a 2D shadow of a 3D mesh.
  2. An `<iframe src={API_BASE + '/visualize/plot?...'}>`
     (`App.tsx:1747-1753`) pointed at a backend HTML endpoint. Whatever
     that endpoint produces is the visualization; the UI tier has no
     view of it and no controls over it.
- ANSYS Workbench's Mechanical viewport gives orbit, pan, zoom, section
  views, contour scales, element picking, named selections, and probe
  points. SimScale gives WebGL + ParaView-tier post-processing in the
  browser. This UI offers neither.
- Playback timeline controls are decent: a play/pause button
  (`ResultMeshPlaybackPanel.tsx:214-234`) with `aria-label`, a range slider
  (`:235-244`), and a `Frame N/M` readout (`:245-248`). Reasonable
  scrubbing UX, but the canvas it scrubs is the 2D SVG.
- No contour legend, no color-bar scale, no probe annotation, no measure
  tool. The `ModeSelector` (`App.tsx:1757-1762`) gives mode-shape switching
  for modal analysis but lives in an absolute-positioned overlay
  (`right: 24px, top: 24px`) on top of the iframe — fragile layout.

## Top 3 UI deficiencies (with file:line citations)

1. **Phase 18 D primitives are not integrated.** `CommandPalette`,
   `SkeletonCard`, `ErrorCard`, `EmptyStateCard`, `DriftBadge`, and
   `useKeyboardShortcuts` are imported by exactly zero callers outside their
   own files and the dedicated test
   (`frontend/test/Phase18D.test.tsx`). Verified by
   `grep -rn '<primitive>' frontend/src/`. The visible UI uses six
   different bespoke loading indicators, four bespoke error renders, a
   dozen bespoke "No X" empty states, and zero Cmd-K. The Phase 18 D
   work shipped a parts bin but no car — `App.tsx:1-1926` has no awareness
   of it. This is the single biggest scope-honesty gap of Phase 18.

2. **`App.tsx` is a 1926-line single-component monolith with ~20+
   `useState`s, ~40 inline-style blocks, and ~20 panels rendered into one
   scrolling column** (`frontend/src/App.tsx:468, :585, :660, :744`, plus
   the entire `:1555-1688` panel stack). The 18+ panels in the visual tab
   share a single render scope, so every fetch in any panel re-renders
   the entire workbench. There is no panel grouping, no collapsible
   sections, no tabbed sub-navigation, no priority/triage of what the
   reviewer should see first. ANSYS Workbench's project tree solves
   exactly this problem; this code re-derives it as a 1.5k-line `<main>`.

3. **The "3D Scene" tab does not contain a real 3D viewport.**
   `ResultMeshPlaybackPanel.tsx:176-188` is a static SVG projection; the
   neighboring `<iframe>` at `App.tsx:1747-1753` defers all rendering to a
   server-side HTML endpoint that the UI tier has no control over. No
   WebGL, no camera, no contour legend, no picking. For a structural-FEA
   workbench benchmarked against ANSYS / SimScale, this is the lowest-
   leverage axis to leave behind — the 3D scene IS the product to a CAE
   engineer.

## Phase 19+ specific UI improvements to lift the lowest-scoring axes

- **Wire the Phase 18 D primitives (lift axes 2, 4, 5, 7).** Concretely,
  in `App.tsx`:
  1. Build a real `commands` array (start with: focus case gallery, run
     solver, stop solver, toggle copilot, toggle console, jump to each
     tab, export PDF, open sign-off form) and pass it to a single
     `<CommandPalette open={paletteOpen} onClose={...} commands={...}/>`
     mounted at the root.
  2. Call `useKeyboardShortcuts([{ hotkey: 'mod+k', handler: openPalette,
     fireInTextInput: true }, { hotkey: '?', handler: openCheatsheet }])`
     once at the top of the App component.
  3. Replace the 6 bespoke loading divs at `App.tsx:1715-1716`,
     `CohortAnomaliesPanel.tsx:61`, `CohortDashboardPanel.tsx:170`,
     `ProvenancePanel.tsx:88`, `AdvisorPanel.tsx:118-121`, and the
     `<PanelState>` helper in `ResultMeshPlaybackPanel.tsx:151-152` with
     `<SkeletonCard label="..." lines={4}/>`.
  4. Replace every inline error render (4 panel files cited above) with
     `<ErrorCard title=... message=... remediation=... onRetry=... />`.
     Add `<ErrorCard>` fallbacks for the 8 `console.error` swallows in
     `App.tsx:498, :517, :577, :607, :650, :672, :699, :756`.
  5. Replace the bare empty-state column at `App.tsx:1786-1790` and the
     grey paragraph at `CohortDashboardPanel.tsx:174-176` with
     `<EmptyStateCard headline=... body=... action={...}/>`.

- **Refactor `App.tsx` (lift axes 1, 8, 9).** Extract panel groupings
  ("evidence", "trust", "drift", "sign-off") into separate components,
  each owning its own state and useEffects. Introduce a left-side
  workbench tree (case → analysis → results → drift → sign-off) so the
  scrolling vertical wall in `App.tsx:1555-1688` becomes a navigable
  tree. Move font-size literals into 5-step type scale tokens in
  `index.css` (`--fs-xs/-sm/-base/-lg/-xl`) and **delete** the inline
  `fontSize` overrides.

- **Replace the SVG mesh + iframe with a real 3D viewport (lift axis 10).**
  Add `react-three-fiber` (or `three.js` direct) for the result mesh.
  Render OpenRadioss frames with proper camera (orbit/pan/zoom), a
  contour scalar field (von Mises / displacement) with a legend, element
  picking with hover tooltip, and a section plane. Keep the existing
  scrub timeline (`ResultMeshPlaybackPanel.tsx:214-244`) — it's already
  good — and wire it to the new viewport instead of the SVG canvas.

- **Type scale + `App.css` (lift axes 3, 9).** `App.css` is currently
  1 byte. Migrate the inline styles in `App.tsx` and in the Phase 18 D
  primitives to CSS variables / utility classes so the design system
  has somewhere to live. The component comments in the primitives
  already flag this as Slice E+ scope (e.g.,
  `CommandPalette.tsx:172-173`); just doing it would close axes 3 and 9
  by 2-3 points each.

- **A11y pass (lift axis 6).** Add `aria-current="page"` to the
  nav-item active state (`App.tsx:1465`), `role="tab" aria-selected={...}`
  to TabButton (`:1918-1924`), `aria-label` to every icon-only button
  (the run/stop/copilot/console buttons at `:1514, :1528, :1533`).
  Run an axe-core pass.

## Honest disclosure

- **No dev server was run.** Scoring is purely from static reading of
  `frontend/src/`. Things I could not verify:
  - actual paint latency on a real backend response
  - actual focus-trap behavior in the palette dialog under a screen reader
  - actual contrast under different OS dark-mode themes (only contrast of
    the literal hex values was estimated)
  - actual smoothness of the SVG playback at 30+ fps
  - actual responsive behavior at the `@media (max-width: 1024px / 768px /
    480px)` breakpoints in `index.css:101-133`
- **`App.tsx` is 1926 LOC**; I read lines 1-200 and 1380-1660 and
  1660-1926 in detail, and grep-scanned the rest. There may be additional
  uses of the Phase 18 D primitives buried in lines 200-1380 that grep
  would have missed if they were renamed on import — but a string search
  for the *exported names* across the entire `src/` tree returned zero
  external hits, so I'm confident the integration gap is real.
- I did not have access to a designer's spec sheet, so the "industrial
  aesthetic" score is calibrated against ANSYS Workbench / SimScale from
  memory, not against an internal style guide.
- The Phase 18 D primitives are individually well-built (assertion at
  `CommandPalette.tsx:42`, signed-percent formatter at `DriftBadge.tsx:41`,
  shouldFire policy at `useKeyboardShortcuts.ts:37`). The deduction is
  entirely about integration, not about primitive quality. If the user
  reads this report and thinks "Phase 18 D was wasted work," that is
  wrong — the parts are good, they just aren't bolted on yet.
- I am the UI tier agent, not the backend or evidence-spine agent. Some
  of the panel sprawl in `App.tsx:1555-1688` may be intentional Tier 1
  evidence stacking (every panel = one Tier 1 evidence card). If that's
  the product-honest framing, then "axis 1: information density" should
  be re-read as "the reviewer is supposed to scroll through every piece
  of evidence by design." That still doesn't fix axes 2/4/5/7/10, and it
  doesn't justify 18+ panels sharing one `useState` graph.
