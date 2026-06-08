# Phase 20 UI testing agent — round 1 report

## Composite score
**66/100** (verdict: CHANGES_REQUIRED)

Brutally honest read: Phase 20 D delivered the three promised extractions (Topbar 177 LOC, RightRail 62 LOC, Sidebar 340 LOC) and migrated ResultMeshPlaybackPanel to the three primitives. Those are real, verifiable structural wins. But the headline metric — App.tsx LOC — moved from 2019 to **2006** (a 13-line delta, ~0.6%). That is not "composition root" progress; it is cosmetic shaving while the 1500+ LOC of inline Trust Center, Cohort, signoff, and validation panels still live in App.tsx. And Dim 5 is hard-floored because **the frontend still renders zero 3D** — `grep -rEn 'three|webgl|<canvas' frontend/src/` returns only comment strings. Phase 20 C's meshed-pipeline backend is invisible to the user.

## Phase 19 round-1 baseline comparison
Prior UI = 58/100. Slice D shipped [Topbar+RightRail extractions, Sidebar candidate roster, ResultMesh primitive migration]. EXPECTED uplift +10–16. **ACTUAL observed delta = +8** (58 → 66). Below the floor of expectation because (a) App.tsx LOC barely budged (2019 → 2006, the extractions deleted JSX but the same business logic stayed inline as new panels), and (b) Dim 5 cannot move without WebGL.

## Dimension scores

### 1. Visual identity & polish: 13/20
Glass-panel system, consistent spacing, ComplianceBadge / DriftBadge tone vocabulary, three-card Trust Center industrial aesthetic — all intact. The Sidebar candidate roster (340 LOC) is genuinely well-designed: discoverable Cmd-K hint chip at line 112-139, aria-labeled, integrated with active-case state. Topbar extraction is clean. What still drags this dim below 15: no design-token file visible, color/spacing values still ad-hoc-inlined in App.tsx style props (`style={{ padding: '18px 20px', marginBottom: '24px' }}` at line 1934 is one of dozens), no motion/transition system, no dark-mode hook. Polish is "competent enterprise" not "Apple-tier industrial."

### 2. Layout discipline: 11/20
Verified: `wc -l frontend/src/App.tsx` = **2006**. Target was <500 composition-root. We are 4× over budget. Three components extracted (Topbar/RightRail/Sidebar = 579 LOC moved out) but App.tsx only shrank 13 LOC — meaning the extractions mostly replaced existing JSX with `<Component ... />` calls and left the rest of the god-component intact. Still inline in App.tsx (grep evidence at lines 1631, 1713, 1725, 1934): CohortDashboardPanel wrapper section, TrustScoreGauge mount, TrustScoreTimelineChart mount, full Trust Center 3-card section (~250 LOC), signoff submission flow, validation banner. App.tsx is a composition root in *aspiration* only. +3 over Phase 19 for the directionally-correct extractions, but the score reflects 4×-over-budget reality, not intent.

### 3. Onboarding & affordance: 15/20
Primitive adoption: 29 call sites across components/ (grep verified). Top adopters: SignoffHistoryPanel/ResultMeshPlaybackPanel/CohortDashboardPanel each at 6 references; MaterialPickerPanel/AdvisorPanel at 4; Sidebar at 3. ResultMeshPlaybackPanel migration confirmed: SkeletonCard at line 160, ErrorCard at line 164, EmptyStateCard at line 371 — bespoke loading/error/empty fully retired. Cmd-K hint chip preserved through extraction in Sidebar.tsx line 107-139 with `data-testid="cmd-k-hint"` and `aria-label`. This is the strongest dimension and the cleanest closure of a Phase 19 finding. Held below 18 because there's no first-run tour, no contextual tooltips on the Trust Center cards, no keyboard-shortcut overlay panel beyond the single Cmd-K chip.

### 4. Data viz quality: 13/20
Stress-contour-legend confirmed present in ResultMeshPlaybackPanel.tsx line 231 (`data-testid="stress-contour-legend"`) — the Phase 19 finding stays closed. TrustScoreGauge mounted at App.tsx:1713, TrustScoreTimelineChart at App.tsx:1725, CohortDashboardPanel at App.tsx:1631. The data-viz inventory is broad (gauge + timeline + cohort dashboard + convergence study viewer + stress legend) and quality is decent for SVG/CSS-rendered charts. What keeps this at 13: the "stress contour legend" is a *legend without a contour* — without a 3D mesh viewport, the legend is a color bar pointing at nothing. CFD/FEA industrial users expect the legend to coexist with a live colored mesh. Charts are static (no brushing, no linked highlighting, no slice scrubbing).

### 5. Compared to top-tier industrial CAE: 4/20
Hard floor enforced per audit rules. Verified: `grep -rEn 'three|webgl|<canvas' frontend/src/` returns **only comment-string matches** (App.tsx:1243 "three industrial Trust Center cards" / trustCenterSummary.ts:5 etc.). No three.js, no react-three-fiber, no `<canvas>`, no WebGL context anywhere in `frontend/src/`. Phase 20 C shipped a meshed pipeline backend — but the frontend viewport renders zero geometry. ANSYS Mechanical, Abaqus/CAE, SimScale, Onshape Simulation, COMSOL all have rotatable 3D mesh viewports with picking, sectioning, deformation animation. We have placeholder panels. No backend gain compensates here; the audit explicitly scores the *frontend* experience and the floor is 4.

## Top 3 deficiencies (file:line)

1. **frontend/src/App.tsx:444–2006** — App.tsx is still a 2006-LOC god component. Phase 20 D extracted ~579 LOC of UI shell (Topbar/RightRail/Sidebar) but the Trust Center 3-card section (1631–1855), TrustScoreGauge mount (1713), TrustScoreTimelineChart mount (1725), validation banner (1934), and signoff flow remain inline. The "<500 LOC composition root" target is not credibly approachable without extracting these business sections next.

2. **frontend/src/** (no file) — Zero WebGL/three.js/canvas-based 3D rendering. Phase 20 C built a meshed pipeline server-side and the user sees no benefit. Until a three.js or react-three-fiber viewport ships, Dim 5 stays at 4/20 and any FEA reviewer would correctly call this "a dashboard, not a CAE tool."

3. **frontend/src/App.tsx:1934** — Inline `style={{ padding: '18px 20px', marginBottom: '24px' }}` (one of dozens). No design-token layer means visual identity drifts every time a panel ships; this is the root cause of Dim 1 staying at 13 despite competent individual components.

## One specific UI improvement that would lift the lowest-scoring dimension

Ship a minimal **react-three-fiber mesh viewport** (`<Canvas>` rendering the meshed-pipeline output from Phase 20 C as an OrbitControls-rotatable surface mesh colored by the stress field that the existing `stress-contour-legend` already documents). Even a v0 that only shows static geometry with no picking would lift Dim 5 from 4/20 to ~10/20 (the WebGL floor is removed, basic viewport exists) and would simultaneously upgrade Dim 4 because the legend would finally point at a real colored mesh. Suggested entry point: a new `frontend/src/components/MeshViewport.tsx` consuming the Phase 20 C `/api/v1/mesh/<case_id>` (or equivalent) endpoint and mounted inside ResultMeshPlaybackPanel where the bespoke loading state used to live. This is the single highest-leverage change available; it's also the one Phase 20 D explicitly did not attempt, which is why this audit is CHANGES_REQUIRED rather than APPROVE.
