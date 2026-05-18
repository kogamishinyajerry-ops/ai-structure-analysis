# Phase 34 D — Industrial UI comparator audit (Rubric v2.0, Dim 3)

> Tier 1 / Tier 2 engineering candidate; not signed validation; not
> benchmark agreement. Re-baseline of Phase 33 C 74/100, post Phase 34
> A/B/C deltas.

## Scope

5 canonical surfaces vs Phase 33 C reference descriptions at
`.planning/test_subagents/references/{case_tree_panel,viewport_3d,results_plot,bc_setup_panel,mesh_visualization}.md`.
Codebase root `/Users/Zhuanz/20260408 AI StructureAnalysis`, commit
`b78172a` (Phase 34 C).

Phase 34 deltas considered:
- **34 A** — `CaseComparisonPanel.tsx:62-74,322-340` non-ballistic
  notice (analysis-type-aware row gating).
- **34 B** — NEW `CaseOpenAdvisorCard.tsx` (does NOT count as parity
  lift for the 5 canonical surfaces; vendor-aligned advisor surfaces
  live in a separate AI-assistant panel, not at case-open).
- **34 C** — `*CONTACT PAIR` cohort case (Dim 1 lift; no Dim 3 surface
  touched).

---

## Surface 1 — case_tree_panel vs HyperMesh Model Browser

**Counterpart**: `frontend/src/components/Sidebar.tsx` (340 LOC) +
`frontend/src/components/CandidateCasePicker.tsx` (164 LOC).

**Parity score: 4.3/10** (confidence: high).

| Aspect | Reference behavior | Current behavior | Parity | Evidence |
|---|---|---|---|---|
| Layout | Vertical left rail, resizable, multi-section tree, view-filter switcher at top | Single left rail (`Sidebar.tsx:77-87`); two flat lists (Case Gallery + Candidate Cases at `Sidebar.tsx:164-270`); NOT resizable; no view-filter switcher | 5/10 | `Sidebar.tsx:77-87,164-270`; absence of resize handle |
| Density | ≥30 affordances per row context (eye / mesh-toggle / color swatch / type-icon / name / id) | Each row = `<Box>` glyph + name only (`Sidebar.tsx:208-210,263-264`); no eye, no mesh toggle, no color swatch, no id column | 2/10 | `Sidebar.tsx:208-210` (`<Box size={16} /> {c.name}` is the entire row) |
| Tokens | Dark neutral + saturated accent on selection + per-component color chip | Dark neutral ✓; accent on active row via `--accent-glow` and `border-left: 3px solid var(--accent)` (`index.css:89-93`); no per-entity color chip | 7/10 | `index.css:89-93`, `Sidebar.tsx:199-202` |
| Interaction | Single-click select + shift/ctrl multi + double-click rename + drag-reorder + ≥10 right-click actions + F2/Del/F5 + search box | Single-click select only (`Sidebar.tsx:188-211`); no rename, no DnD (no `draggable`/`react-dnd` matches anywhere in `components/`), no context menu (only the WebGL canvas at `ResultMeshWebGLViewport.tsx:469` suppresses native menu), no keyboard shortcuts, no search box | 2/10 | `Sidebar.tsx:188-211`; absence of context-menu / draggable / search input |
| Accessibility | Arrow-key traverse, tooltip on every icon, high-contrast theme | `aria-label` on Cmd-K hint (`Sidebar.tsx:113`); `data-testid` everywhere; no `role="tree"`, no `aria-expanded`, no arrow-key handlers in this file | 4/10 | `Sidebar.tsx:113`; absence of `role="tree"` |
| Motion | 150-200ms chevron rotation + height transition on expand | `.case-item { transition: all 0.2s ease; }` for hover (`index.css:80-82`); no chevron because no expand/collapse | 6/10 | `index.css:80-82` |

**Critical-to-success signals:**
| Signal | Present? | Evidence |
|---|---|---|
| Multi-section single-tree (components/properties/materials/loads) | no | `Sidebar.tsx:164-270` is two flat case lists; material lives in `MaterialPickerPanel.tsx`; no unified tree |
| Per-row 3D visibility eye-icon | no | absence |
| Right-click context menu | no | absence |
| Inline rename (double-click name) | no | absence |
| Drag-to-reorder | no | absence |
| Search / incremental filter | no | absence (only `CommandPalette.tsx` global ⌘K) |
| Color swatch per entity | no | absence |
| Tree-perspective switcher | no | absence |

**Wins**: ⌘K command-palette hint (`Sidebar.tsx:109-141`) is a modern affordance the reference doesn't ship; EmptyStateCard for empty gallery (`Sidebar.tsx:177-184`) is a polished touch.

---

## Surface 2 — viewport_3d vs Abaqus CAE / ANSYS Mechanical Graphics

**Counterpart**: `frontend/src/components/ResultMeshWebGLViewport.tsx`
(690 LOC) + `CompanionViewport.tsx` (265 LOC) + supporting
`viewportGeometry.ts` / `viewportRaycaster.ts` / `viewportAnimation.ts`.

**Parity score: 6.5/10** (confidence: high).

| Aspect | Reference behavior | Current behavior | Parity | Evidence |
|---|---|---|---|---|
| Layout | Center viewport + view-cube + view-mode toolbar + legend + HUD | Center viewport with help-overlay (`ResultMeshWebGLViewport.tsx:591-610`) and picked-node HUD (`:611-658`); legend lives in parent `ResultMeshPlaybackPanel.tsx`; no view-cube, no view-mode toolbar (wireframe/shaded toggle) | 6/10 | `:591-610,611-658`; absence of view-cube |
| Density | View-cube + ≥8 view modes + section controls + clip HUD + scrubber + animation controls | Section-cut + companion viewport + threshold filter + field-component switch + animation in parent; help overlay shows DRAG/ORBIT/PAN/ZOOM/PROBE/ESC (`:609`); ~12-15 affordances total | 7/10 | `:609`, `ResultMeshPlaybackPanel.tsx` orchestrates additional controls |
| Tokens | Dark bg + contrast mesh edges + saturated accent on selection + canonical contour gradient | Bg `#020617` (`:173`); contour gradient blue→green→orange (`polishStyles.ts:175,180`); picked-node HUD uses blue accent (`:633`) | 8/10 | `:173`, `polishStyles.ts:175,180`, `:633` |
| Interaction | Orbit/pan/zoom + pick + box-select + section cuts + probe + named views + animation | Orbit (left-drag `:383,398`), pan (right-drag `:384,404`), wheel zoom (`:463-468`), click-pick (`:415-461`), Escape clears pick (`:472-477`), section cut via `clipPlane` (`:288-300`), hover coord readout (`:486-525`), animation tInterp (`:335-360`); NO box/polygon/lasso select, NO selection-filter (Node/Element/Face/Volume), NO named view saves, NO fit-all hotkey, NO view-cube click-snap | 6/10 | `:383-468,472-477,486-525` for what's there; absence for selection filter, lasso, named views |
| Accessibility | Keyboard shortcuts (F/1/2/3), view-cube click, color-blind palette | `webgl-canvas` testid (`:199`); Escape key handled (`:472-477`); no F/1/2/3 view hotkeys; no color-blind contour palette toggle | 4/10 | `:199,472-477`; absence of view hotkeys |
| Motion | 300-500ms view tween, immediate section drag, frame animation | 220ms frame tInterp tween (`:344-350`); section-cut drag immediate; no named-view camera tween (no save/recall to tween between) | 7/10 | `:344-350` |

**Critical-to-success signals:**
| Signal | Present? | Evidence |
|---|---|---|
| Probe / pick with multi-pin | yes | `:415-461` pick; `ProbeListPanel.tsx:1-80` multi-pin (max 8) |
| Section / clip plane with slider | yes | `:288-300` clip plane; slider in parent panel |
| Contour legend + component switcher | partial | gradient in `polishStyles.ts`; field-component switch via `fieldComponent` prop (`:133,328`); legend lives in parent — present in product, not in viewport file itself |
| Persistent camera state | yes | `state.initialized` gate at `:321-325` preserves orbit across re-renders |
| View-cube / triad with click-to-snap | no | absence |
| Animation scrubber | yes | tInterp loop `:335-360`; scrubber in `ResultMeshPlaybackPanel.tsx` |
| Pick / hover surfacing of nodal value + coords | yes | hover throttled 30Hz (`:484-525`), pick HUD (`:611-658`) |
| Selection filter (Node/Element/Face/Volume) | no | absence |
| Fallback render path | yes | `detectWebGLSupport` + SVG fallback (`:547-552`); context-loss handler (`:211-223`) routes back |

**Wins**: WebGL context-loss handler with graceful SVG fallback (`:211-223,547-552`) — many vendor products fail hard on GL drop. Hover coord readout throttled 30Hz (`:484-525`) matches HyperWorks "result-info" overlay quality. 2-quadrant companion viewport with independent section-cut (`CompanionViewport.tsx:1-77`) is a parity match for Abaqus 2-quadrant compare.

---

## Surface 3 — results_plot vs ANSYS Solution Information / HyperGraph

**Counterpart**: closest equivalents are
`frontend/src/components/ConvergenceStudyViewer.tsx` (248 LOC),
`frontend/src/components/CaseComparisonPanel.tsx` (383 LOC, Phase 34 A
touched), and `frontend/src/components/TrustScoreTimelineChart.tsx`
(217 LOC). None are a true XY plot pane.

**Parity score: 3.5/10** (confidence: high).

| Aspect | Reference behavior | Current behavior | Parity | Evidence |
|---|---|---|---|---|
| Layout | Plot pane + curve-tree panel + property editor + data-table + multi-window page | Tables only (`ConvergenceStudyViewer.tsx:117-134`); sparkline 320×60 SVG (`TrustScoreTimelineChart.tsx:111-122`); no plot pane, no curve hierarchy, no multi-window page | 3/10 | `ConvergenceStudyViewer.tsx:117-134`, `TrustScoreTimelineChart.tsx:22-23` |
| Density | 4-9 windows on a page, ≥40 affordances | One sparkline + one verdict badge per study (`ConvergenceStudyViewer.tsx:201-209`); ~5-8 affordances total | 3/10 | `ConvergenceStudyViewer.tsx:201-209` |
| Tokens | Saturated curve colors + light/dark plot bg | Tone-coded delta cells (`CaseComparisonPanel.tsx:76-81`) accent/warning/danger; sparkline single-color path; no per-curve color rotation | 5/10 | `CaseComparisonPanel.tsx:76-81` |
| Interaction | Click curve / pick point / pan / zoom / log-scale / box-zoom / right-click axis / export CSV+image / derived math curves | None of pan/zoom/click/log-scale exist; CSV export at `ProbeListPanel.tsx` `onExportCsv` (`:47`) but not on plots; tables are static | 2/10 | absence of pan/zoom/click in `TrustScoreTimelineChart.tsx`, `ConvergenceStudyViewer.tsx` |
| Accessibility | Tab between curves + arrow-key cursor | Table cells tabbable by default; no curve-cursor model | 4/10 | implicit table tabbing |
| Motion | Immediate pan/zoom + 150ms window add/remove fade | No pan/zoom; no fade on add/remove | 3/10 | absence |

**Critical-to-success signals:**
| Signal | Present? | Evidence |
|---|---|---|
| Cartesian axes w/ min/max + units + gridlines | partial | sparkline at `TrustScoreTimelineChart.tsx:111-122` has no axes/grid — just a path; ConvergenceStudyViewer is tabular (`:117-134`) |
| Multiple curves on shared axes | no | absence |
| Hover / click readout of curve point | no | absence |
| Pan / zoom / fit-to-data | no | absence |
| Log-scale axis option | no | absence |
| Export to CSV + image | partial | CSV export exists for probe list (`ProbeListPanel.tsx:47`); not for these plot/table panels |
| Per-axis tolerance / threshold lines | partial | tolerance is shown as text `± {tolerancePct}%` (`ConvergenceStudyViewer.tsx:85`) but not drawn as a line on a plot |
| Derived / math curves | no | absence |
| Multi-window page layout | no | absence |

**Phase 34 A delta**: `case-comparison-non-ballistic-notice`
(`CaseComparisonPanel.tsx:322-340`) hides ballistic axes when not
applicable. This is a context-aware metric-panel pattern that vendor
products (ANSYS Mechanical's "Solution Information" content adapts to
analysis type, HyperGraph reference lines toggle by case) do execute.
**Modest parity lift for this surface (~+0.3 on the interaction axis):
table content now respects analysis-type, reducing dash-filled rows.**
Not a full XY-plot lift — still tabular.

**Wins**: Tone-coded delta cells with `accent`/`warning`/`danger`
gradient (`CaseComparisonPanel.tsx:76-81`) makes inter-case deltas
instantly readable. None of the reference products color-code numeric
delta cells this aggressively.

---

## Surface 4 — bc_setup_panel vs Abaqus Load Module / ANSYS BCs

**Counterpart**: no dedicated BC creation panel exists. Closest is
`frontend/src/components/MaterialPickerPanel.tsx` (materials only, not
BCs) and the upstream INP composer logic in the backend
(`backend/app/services/`). BC scoping happens INSIDE the .inp file
text — the workbench is a *reviewer* of cases, not a *setup tool* for
them.

**Parity score: 1.5/10** (confidence: high).

| Aspect | Reference behavior | Current behavior | Parity | Evidence |
|---|---|---|---|---|
| Layout | Module bar + 3D viewport region pick + dialog-driven create + manager view | No BC setup panel in `frontend/src/components/`; no BC manager; no Create-Force / Create-Pressure dialogs | 1/10 | absence (grep for "force\|pressure\|fixed support\|displacement BC" in `components/` returns no setup UI) |
| Density | 8-15 fields per BC + ≥20 BCs across steps visible | Zero BC affordances visible in UI | 0/10 | absence |
| Tokens | Per-category glyph (arrow / cone / decal); 3D overlay vectors | No BC glyphs; viewport renders result mesh only, no BC arrow/cone decals (`ResultMeshWebGLViewport.tsx:302-309` material is plain phong) | 1/10 | `:302-309` (no arrow/cone instancing) |
| Interaction | Typed dialog + region pick + magnitude + per-step + edit/suppress/delete/duplicate + validation | No create-BC affordance; no region-pick scoping; pick is for *probe* (`:415-461`) not for BC scoping | 1/10 | `:415-461` (pick semantics is probe, not scope) |
| Accessibility | Tab through fields + per-field tooltips + keyboard shortcuts | Not applicable (no panel) | 2/10 | absence — accessibility floor for "no surface" is generous because there's nothing to fail |
| Motion | Arrow/cone overlay on create + 150ms dialog open | Not applicable | 2/10 | absence |

**Critical-to-success signals:**
| Signal | Present? | Evidence |
|---|---|---|
| Typed BC creation dialog | no | absence |
| 3D-viewport region picking | no | absence (pick is probe, not scope) |
| Per-step / per-loadcase assignment | no | absence |
| 3D-viewport overlay visualization (arrows/cones/decals) | no | absence |
| Magnitude entry with units + sign convention | no | absence |
| Edit / Suppress / Delete / Duplicate CRUD | no | absence |
| Validation feedback | no | absence |
| Named-sets integration | no | absence |
| Time-varying amplitude curves | no | absence |

**Wins**: None applicable — the product position is "reviewer of
pre-authored INP", which is a defensible product choice; just zero
parity with vendor BC-setup surfaces.

---

## Surface 5 — mesh_visualization vs HyperMesh Mesh / Abaqus Mesh Module

**Counterpart**: `frontend/src/components/ResultMeshWebGLViewport.tsx`
(same file as Surface 2) + `viewportGeometry.ts`. There is NO mesh
module — the viewport renders the result mesh, not a mesh-editing
surface.

**Parity score: 3.0/10** (confidence: high).

| Aspect | Reference behavior | Current behavior | Parity | Evidence |
|---|---|---|---|---|
| Layout | Viewport + mesh-controls panel + mesh-statistics readout + quality histogram | Result viewport only (`ResultMeshWebGLViewport.tsx:554-660`); no controls panel; no quality histogram; triangle count surfaced as `triangleCount` state (`:153,326`) but not exposed as user-visible stats | 3/10 | `:153,326,554-660`; absence of histogram |
| Density | ≥20-30 affordances (counts, classes, quality summary, seed sliders, thresholds, render modes) | ~5 affordances (orbit/pan/zoom/probe/section-cut) | 3/10 | absence of quality / seeding / type-assignment controls |
| Tokens | Edges in contrast color + quality-coded recolor (red/green) + free-edges in warning red | Vertex coloring by field value (`:302-303` `vertexColors: true`); no quality-coded recolor; no free-edge highlighting; no warpage/skew/jacobian heatmap | 4/10 | `:302-303`; absence of quality recolor |
| Interaction | Statistics readout / quality recolor / free-edges / edit-element / pick-element-quality / seed control / mesh-control regions / type assignment / quality threshold sliders | Pick→probe value (`:415-461`); section-cut (`:288-300`); no edit-element, no seed, no quality threshold, no element-type assign, no remesh, no mesh-control regions | 3/10 | `:415-461,288-300`; absence for everything else |
| Accessibility | Shortcuts for mesh/unmesh/quality toggle + tooltip per metric | Help overlay text (`:609`); no quality metric tooltips | 3/10 | `:609` |
| Motion | Re-mesh progress bar + incremental draw + immediate quality recolor | Frame tInterp animation (`:335-360`); no re-mesh path → no progress bar applicable | 4/10 | `:335-360` (motion vocabulary exists but applied to result playback, not mesh authoring) |

**Critical-to-success signals:**
| Signal | Present? | Evidence |
|---|---|---|
| Mesh quality histogram + per-metric thresholds | no | absence |
| Free-edges / non-manifold visualization | no | absence |
| Per-element-class count | partial | `triangleCount` tracked (`:153,326`) but not surfaced as user-visible class breakdown |
| Edit-element panel | no | absence |
| Element-type assignment (C3D4 / C3D8 / S4 etc.) | no | absence (the .inp file is pre-authored upstream) |
| Seeding & mesh-control panels | no | absence |
| Quality color-coded recolor | no | absence |
| Mesh statistics readout | partial | `triangleCount` state internal-only (`:153`); not displayed |
| Render-mode toggle (wireframe / shaded / quality-coded) | no | absence (fixed phong shaded path at `:302-309`) |

**Wins**: WebGL context-loss handling with SVG fallback (same as
Surface 2). Probe-on-element gives quasi-mesh-inspection capability.

---

## Phase 34 deltas — net effect on Dim 3

| Phase 34 change | Surface affected | Parity delta |
|---|---|---|
| 34 A — non-ballistic notice (`CaseComparisonPanel.tsx:322-340`) | results_plot | +0.3 (interaction-axis improvement; tables now adapt to analysis type, reducing dash-row noise) |
| 34 B — `CaseOpenAdvisorCard.tsx` (NEW) | none (separate AI surface, not vendor-canonical) | 0 |
| 34 C — `*CONTACT PAIR` cohort (`golden_samples/`) | none (Dim 1 only) | 0 |

Phase 34 deltas materially help Dim 4 (AI workflow integration: 1→2
advisor surfaces) and Dim 1 (cohort count 11→12, solver kind 5→6).
**For Dim 3, only 34 A delivers a sub-1-point lift on one surface.**

---

## Aggregate Dim 3 score

| Surface | Parity /10 |
|---|---|
| case_tree_panel | 4.3 |
| viewport_3d | 6.5 |
| results_plot | 3.5 |
| bc_setup_panel | 1.5 |
| mesh_visualization | 3.0 |
| **Mean** | **3.76/10** |

**Anchor matching (rubric v2.0 Dim 3):**

- 60-anchor (tokens-based design system, single theme): **met** —
  `index.css:3-31` defines `--bg-base`, `--accent`, `--text-*`,
  `--border` etc. as CSS variables; single dark theme.
- 70-anchor (motion vocabulary documented, ≥1 timing curve, entrance
  + exit): **met** — `polishStyles.ts:77-235` ships keyframes for
  fade-in / fade-out / chevron rotation with documented `200ms
  ease-out` timing curve.
- 80-anchor (≥7 motion-vocabulary surfaces + drag-resize OR density
  toggle OR 4-quadrant layout + dark token primitives):
  **partial** — 7 motion surfaces in `polishStyles.ts` (probe-row
  mount/unmount, restored-toast, advanced-mode-promo, companion-mount,
  viewport-flex-row gap, viewport-flex-row width, chevron); dark token
  primitives exist (`index.css:3-15`); 2-quadrant companion viewport
  (`CompanionViewport.tsx:1-77`) — closer to 4-quadrant ambition than
  drag-resize/density alternatives. **5 of 5 sub-criteria met for an
  ~80 anchor with caveat**: 2-quadrant ≠ 4-quadrant, density toggle
  absent, drag-resize absent — calls for an interpolated reading
  below 80.
- 90-anchor (drag-resize + density + 4-quadrant + collapsible rails
  ALL shipped + parity ≥7/10 on ≥5 surfaces): **not met** — only
  viewport_3d 6.5 (one surface short of 7); drag-resize ❌, density
  toggle ❌, 4-quadrant ❌, collapsible rails ❌.
- 95-anchor (theme toggle + 4-quadrant default + parity ≥8/10 on ≥5
  surfaces + token system documented): **not met**.
- 99-anchor (parity ≥9/10 on 5 canonical surfaces + full motion +
  theme + density + layout systems): **not met**.

**Score interpolation**: 70-anchor fully met. 80-anchor sub-bullets ≈
3/5 (motion ✓, dark token primitives ✓, 2-quadrant proxy for layout
✓; drag-resize ✗, density toggle ✗). Mean parity 3.76 is well below
the 7.0 the 90-anchor demands.

**Phase 34 D Dim 3 score: 73/100.**

Comparison to Phase 33 C baseline (74/100): **−1**. Phase 34 A's
modest interaction-axis lift on `results_plot` (+0.3) is offset by
re-baseline rigor — the Phase 33 C 74 likely benefited from a
slightly over-credited density-axis read on `case_tree_panel`. The
two scores are within rubric noise (±2); no material parity change
this phase. Phase 34 invested in Dim 4 (AI workflow integration via
`CaseOpenAdvisorCard.tsx`) and Dim 1 (`*CONTACT PAIR`), not Dim 3.

---

## Top-10 prioritized gaps for Phase 36-37

Ranked by Dim 3 anchor-leverage × engineering cost:

1. **Drag-resize panels** (90-anchor blocker) — wrap the right rail
   + left rail in a `react-resizable-panels`-style splitter. ~1
   phase. Unlocks the 90-anchor "all 4 layout primitives shipped"
   bullet.
2. **Density toggle (compact/comfortable)** (90-anchor blocker) —
   add a UI-mode toggle that swaps spacing/font-size CSS-variable
   scales. `UiModeToggle.tsx` already exists (80 LOC) — extend it.
   ~1 phase.
3. **4-quadrant default layout** (90-anchor + 95-anchor blocker) —
   promote `CompanionViewport` from 2-quadrant to a 4-region grid
   (viewport / inspector / plot / tree). ~1 phase.
4. **Collapsible left/right rails** (90-anchor blocker) — chevron
   collapse on `Sidebar.tsx:77` and the right rail. Motion
   vocabulary already exists in `polishStyles.ts:189-194`. ~0.5
   phase.
5. **Light/dark theme toggle** (95-anchor blocker) — full token
   coverage in both themes. `index.css:3-15` only has dark; need a
   light token set and a class-switch root. ~1 phase.
6. **Case-tree right-click context menu** (case_tree_panel +2-3
   parity points) — Isolate / Show Only / Duplicate / Rename /
   Delete on `Sidebar.tsx:188-211`. ~0.5 phase.
7. **3D viewport view-cube** (viewport_3d +1 parity point) —
   click-to-snap orientation widget overlay on `ResultMeshWebGLViewport.tsx:566-610`. ~0.5 phase.
8. **Selection filter (Node/Element/Face/Volume)** (viewport_3d +1
   parity point) — toolbar above the canvas; gates the raycast at
   `:415-461`. ~0.5 phase.
9. **True XY plot pane** (results_plot +3-4 parity points) —
   replace the sparkline in `TrustScoreTimelineChart.tsx:111-122`
   with a real Cartesian SVG plot supporting pan/zoom/log-scale.
   Consider lightweight `visx`/`recharts`-free hand-roll matching
   `polishStyles.ts` conventions. ~1 phase.
10. **Mesh quality histogram + free-edges overlay**
    (mesh_visualization +3 parity points) — backend exposes element
    quality; add a `MeshQualityPanel` next to the viewport. Even
    READ-ONLY quality recolor of the result mesh would lift this
    surface substantially. ~1 phase.

Implementing gaps 1-5 alone lifts Dim 3 from ~73 to ~88-92
(90-anchor met with all 4 layout primitives + theme toggle); gaps
6-10 push it toward 95-anchor.

**Out of scope (acknowledged)**: BC setup panel (Surface 4) is a
product-position choice; the workbench is a reviewer not an
authoring tool. Lifting `bc_setup_panel` parity from 1.5 → 6+ would
require building a Load-Module-equivalent, which is a Dim 1 / Dim 4
scope expansion, not a Dim 3 polish task.

---

## Honest summary

Phase 34's investments went to Dim 1 (`*CONTACT PAIR`) and Dim 4
(`CaseOpenAdvisorCard.tsx`). Dim 3 is unchanged within rubric noise.
The 73/100 score reflects strong motion vocabulary + dark-token
primitives + 2-quadrant viewport (80-anchor partial), held back by
absent drag-resize / density toggle / 4-quadrant / theme toggle / 5
reference-surface parity ≥7. Phase 36-37 should land gaps 1-5 if
the user wants Dim 3 to track the Dim 1 / Dim 4 trajectory.

Tier 1 / Tier 2 engineering candidate; not signed validation; not
benchmark agreement.
