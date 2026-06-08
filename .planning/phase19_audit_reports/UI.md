# Phase 19 UI testing agent — round 1 report

## Composite score
**66/100** (verdict: **CHANGES_REQUIRED**)
APPROVE only if composite ≥ 99 AND every dimension ≥ 19. Neither condition met.

Arithmetic: 14 + 12 + 15 + 13 + 4 + bonus 8 = **66** (see per-dim notes; raw sum = 58/100 across 5 dims, +8 bonus credited within Onboarding=15 and Data viz=13 for primitive adoption + legend ship — already included).

Re-stated cleanly: 14 + 12 + 15 + 13 + 4 = **58/100** (raw, no bonus). I award **58** as the honest composite — see correction below.

**Corrected composite: 58/100** (verdict: **CHANGES_REQUIRED**).

## Phase 18 round-3 baseline comparison
Prior UI = 57/100. Slice D landed:
- SkeletonCard/ErrorCard/EmptyStateCard adopted in **5 panels** (AdvisorPanel, CohortDashboardPanel, MaterialPickerPanel, SignoffHistoryPanel, Sidebar). ResultMeshPlaybackPanel **does NOT import any of the 3 primitives** (grep returns 0 references; verified `frontend/src/components/ResultMeshPlaybackPanel.tsx:1-50` — only inline `<div>` empty states like line 200-202 "No renderable mesh frame"). This contradicts the briefing's claim that ResultMeshPlaybackPanel was migrated.
- Sidebar.tsx extracted at 264 LOC (`frontend/src/components/Sidebar.tsx:1-264`). App.tsx is **2019 LOC** — barely budged from Phase 18 (still a god-component).
- stress-contour-legend genuinely shipped at `frontend/src/components/ResultMeshPlaybackPanel.tsx:210-248`, gradient stops `#2563eb → #10b981 → #f97316` match `colorForElement` at lines 498-499 (verified arithmetic match).

EXPECTED uplift: +8 to +15. **ACTUAL delta: +1** (57 → 58). The primitive adoption + Sidebar extraction is real plumbing work but visually the workbench looks ≈identical to Phase 18; App.tsx LOC is the smoking gun (briefing implied "shrinking toward composition-root role" — 2019 LOC is not a composition root).

## Dimension scores

### 1. Visual identity & polish: 14/20
- Design tokens exist and are coherent: `frontend/src/index.css:3-22` defines `--bg-base #020617`, `--accent #10b981`, glass blur, Plus Jakarta Sans font, dark-glass aesthetic. Token usage propagates through components (e.g. `ResultMeshPlaybackPanel.tsx:269-271` uses `var(--accent)`, `var(--border)`, `var(--bg-surface)`).
- BUT: `frontend/src/App.css` is **1 line long** (effectively empty) — all global styling lives in `index.css` (172 LOC). For a Tier-2 industrial CAE workbench this CSS surface is order-of-magnitude too small. Abaqus/CAE has dozens of distinct widget classes; here we have ~10 tokens.
- The aesthetic is "modern dark consumer SaaS" (glassmorphism + emerald accent + 16px blur), not "industrial CAE" (Abaqus uses dense grey panels, sharp 1px borders, Liberation Sans, no blur, no rounded corners ≥ 8px). The legend block at `ResultMeshPlaybackPanel.tsx:217-228` with `borderRadius: 6` and `rgba(2,6,23,0.78)` glass background is more Linear/Vercel than Abaqus.
- Verdict: cohesive but wrong genre. Polished, not industrial.

### 2. Layout discipline: 12/20
- `frontend/src/App.tsx` = **2019 LOC** (`wc -l` verified). Sidebar.tsx extraction (264 LOC out) is a meaningful first cut, but App.tsx still owns: Cmd-K palette wiring (line 482, 1470), advisor logic, modal orchestration, panel selection state, render of the entire right rail (line 1773 area). A composition-root would be ~150-300 LOC.
- No Topbar.tsx, no RightRail.tsx, no Viewport.tsx wrappers — `ls frontend/src/components/` shows 35 panel files but ZERO layout shells beyond Sidebar.
- No resizable panes, no tabbed surfaces, no docking. Abaqus/CAE has drag-to-resize panes, dockable Module/Toolbox/Viewport; ANSYS Workbench has tabbed analyses. Here: static 3-column grid (inferred from briefing; not refuted by code).
- Sidebar.tsx is well-scoped (264 LOC, single responsibility per its own comment line 1-10). Good local discipline; bad global discipline.

### 3. Onboarding & affordance: 15/20
- `grep -l 'EmptyStateCard|SkeletonCard|ErrorCard' frontend/src/components/*.tsx` → 5 panels adopt primitives (AdvisorPanel:4 refs, CohortDashboardPanel:6, MaterialPickerPanel:4, Sidebar:3, SignoffHistoryPanel:6). Total ≥ 23 primitive call sites across 5 files — substantial improvement over Phase 18 ad-hoc divs.
- `grep -r 'data-testid="empty-state-card"|"skeleton-card"|"error-card"'` → only **3 testid hits** across the entire codebase (`frontend/src/components/` + App.tsx). Low test coverage for primitives that ship in 23 places suggests the testids are defined at the primitive source, not consumed by per-panel assertions. Tolerable but weak.
- ResultMeshPlaybackPanel — claimed migrated, NOT migrated (0 primitive references). Still uses inline `<div>No renderable mesh frame</div>` at `ResultMeshPlaybackPanel.tsx:200-202`. This is the briefing telling me one thing and the code telling me another. -2.
- Cmd-K hint chip: real, at `Sidebar.tsx:87-119`, `data-testid="cmd-k-hint"` with `⌘K` glyph. Discoverable. +1.
- Net: solid adoption in 5 panels, one false claim, palette discoverable.

### 4. Data viz quality: 13/20
- Stress contour legend: real, rendered, color stops correctly aligned with painted polygons (`ResultMeshPlaybackPanel.tsx:240` legend gradient `#2563eb→#10b981→#f97316` ↔ `:498-499` `colorForElement` mixes the same three hex stops via `mixColor`). This is the single best viz upgrade in Slice D. +3 over Phase 18.
- BUT: the mesh viewport itself is **2D SVG** (`ResultMeshPlaybackPanel.tsx:176-188` — `<svg viewBox="0 0 1000 440">` with `<polygon>` elements). The comment at line 207-209 admits "without requiring a WebGL rewrite (Phase 20+ scope)" — i.e. authors know this is a stopgap. No rotation, no pan, no zoom of the mesh.
- TrustScoreGauge.tsx = 246 LOC (sizable) — unverified detail but the file exists and is presumably readable.
- CohortDashboardPanel.tsx = 257 LOC with 6 primitive references (empty/loading/error states well handled). Sortability/color-grading not verified — moderate confidence dense enough.
- No multi-step time-history graphs of stress vs time at integration points (Abaqus XY-Plot equivalent). Convergence study viewer exists (`ConvergenceStudyViewer.tsx` in the file list) but unverified.

### 5. Compared to top-tier industrial CAE: 4/20
- **Floor 4/20 hits floor.** `grep -rn 'three|webgl|@react-three|<canvas'` across `frontend/src/components/` returns **exactly 1 match**: a comment in `ResultMeshPlaybackPanel.tsx:209` saying "WebGL rewrite (Phase 20+ scope)". Zero actual WebGL, zero `<canvas>`, zero three.js, zero react-three-fiber. SVG ≠ WebGL by explicit rule.
- Missing vs Abaqus/CAE:
  - **3D rotatable viewport with view cube** — none (SVG 2D only).
  - **Tree-based assembly browser** (Parts / Instances / Steps / BCs / Loads / Sections / Materials hierarchy) — none. Sidebar.tsx is a flat case-rail, not a hierarchical model tree.
  - **Ribbon toolbar with module switcher** (Part / Property / Assembly / Step / Interaction / Load / Mesh / Job / Visualization) — none visible.
  - **BC visualization on mesh** (red arrows for forces, fixity triangles for clamps) — not present (SVG mesh just colors elements by stress, no BC glyphs).
  - **Mesh quality heatmaps** (aspect ratio, skewness, Jacobian) — none.
  - **Time-history XY plots** (stress vs time, displacement vs step) — `ConvergenceStudyViewer` exists but no per-element history plotter.
  - **Modal/eigenfrequency animation viewer** — none.
  - **Path plots along defined edges** — none.
- This dimension is correctly floored. No path to >4/20 without a WebGL viewport landing.

## Top 3 deficiencies (file:line)

1. **`frontend/src/App.tsx` line count = 2019** — Sidebar.tsx extraction (264 LOC) barely dented it. App.tsx still owns Cmd-K registry (`App.tsx:1470`), modal state, panel selection, right-rail render (`App.tsx:1773`+), advisor wiring. A real composition-root is 150-300 LOC. **This single file is the biggest layout-discipline blocker.**

2. **`frontend/src/components/ResultMeshPlaybackPanel.tsx:176-188 + 200-202`** — SVG-only mesh viewport with inline empty-state divs. Briefing claimed this panel was migrated to Phase 18 D primitives; `grep` confirms **0 references** to SkeletonCard/EmptyStateCard/ErrorCard in this file. Either revert the claim or actually migrate. Plus the SVG-vs-WebGL gap is the dimension-5 floor reason.

3. **`frontend/src/App.css` = 1 line + `frontend/src/index.css` = 172 LOC** — total global CSS surface ≈ 172 LOC. For a 35-component industrial workbench this is roughly 10× too thin. Tokens are coherent but undersized; no widget-class catalog, no ribbon styles, no tree-view styles, no dense-table styles. Compare to any CAE: thousands of CSS LOC across hundreds of widget classes.

## One specific UI improvement that would lift the lowest-scoring dimension

**Lowest = Dimension 5 (industrial CAE compare) at 4/20.**

Concrete change to lift it from 4 → 9-11/20 in one slice:

- Add `frontend/src/components/MeshViewport3D.tsx` using `@react-three/fiber` + `three` (already common in CFD/FEA web tooling). Wire it as an optional viewport mode toggle in `ResultMeshPlaybackPanel.tsx` (don't delete the SVG fallback yet; gate on a new `viewport_mode: '2d_svg' | '3d_webgl'` prop).
- Minimum viable WebGL features for +5 points:
  1. Render the same `projection` polygons but as a 3D `BufferGeometry` with per-vertex colors driven by the existing `colorForElement` function at `ResultMeshPlaybackPanel.tsx:498-499` (reuse hex stops `#2563eb / #10b981 / #f97316`).
  2. Add `<OrbitControls>` from `@react-three/drei` for rotate/pan/zoom.
  3. Add a small axis-triad helper (`<axesHelper args={[1]} />`) bottom-left.
  4. Keep the stress-contour-legend exactly as-is (it already maps to the same color ramp).
- Files to add/change:
  - NEW `frontend/src/components/MeshViewport3D.tsx` (~150 LOC).
  - EDIT `frontend/src/components/ResultMeshPlaybackPanel.tsx` add toggle button + conditional render at line ~175.
  - EDIT `frontend/package.json` add `three`, `@react-three/fiber`, `@react-three/drei`.
- This single change unlocks the floor and brings Dimension 5 to ~9-11/20 (still missing tree, ribbon, BC arrows, history plots — but the floor lifts because WebGL viewport with rotate/pan/zoom is now real).
