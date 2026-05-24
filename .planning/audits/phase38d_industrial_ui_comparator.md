# Industrial UI Comparator — Phase 38 D · Dim 3 Calibrated Re-score (R6)

> Tier 1 / Tier 2 engineering candidate; not signed validation; not benchmark agreement.
> Anti-gaming guards in force: D:-1 (every claim cites file:line or "absence"),
> F:-1 (no prior audit / retro / blueprint files read), G:-1 (measures codebase IS, not claims).

---

## Scoring protocol summary

Per RUBRIC_v2.md Dim 3: score = highest anchor (60/70/80/90/95/99) whose ALL sub-bullets
are met. Interpolate between anchors. This is a feature-checklist-driven scale, NOT
raw aesthetic parity × 10 from zero. A 76 means "all 80-anchor items met plus partial
90-anchor items," not "76% visual match to HyperWorks."

---

## Surface 1 — case_tree_panel
**Reference**: Altair HyperWorks (HyperMesh) Model Browser
**Codebase counterpart**: `frontend/src/components/CaseBrowser.tsx` (501 LOC) +
`frontend/src/components/Sidebar.tsx` (partial, left rail)

### Aspect breakdown

| Aspect | Reference behavior | Current behavior | Parity 0-10 | Evidence |
|---|---|---|---|---|
| Layout | Left-hand vertical rail; multi-section tree covering components / properties / materials / loads / constraints / solver decks | 2-pane layout: grouped list on left, preview pane on right. Left rail (`Sidebar.tsx`) holds navigation buttons and case list. No single tree covering all entity classes. | 5/10 | `CaseBrowser.tsx:100-222` (2-pane section); `Sidebar.tsx:76-87` (left rail); multi-section tree = absent |
| Density | ≥30 affordances visible per row (chevron, eye-icon, color swatch, type-icon, name, ID) without scrolling | ~8 affordances visible without scrolling: group header, filter chips, case row buttons, preview pane text. No per-row icons, swatches, or eye toggles. | 3/10 | `CaseBrowser.tsx:150-225` (case row renders text label only, no icon column) |
| Token use | Dark neutral palette; accent highlight on selection; muted greys for inactive | Dark token system: `--bg-surface`, `--border`, `--text-secondary` (muted). Active row uses `--accent` background per `caseRowActiveStyle`. Inactive items use muted. | 7/10 | `CaseBrowser.tsx:313-400` (inline style objects use CSS vars); `index.css:4-17` (token definitions) |
| Interaction | Drag-to-reorder, double-click rename, right-click ≥10 actions, Ctrl-F search, F2 rename, shift/ctrl multi-select | Search input present (`CaseBrowser.tsx:116-123`); filter chips for solver-kind (`CaseBrowser.tsx:125-147`); hover preview (`CaseBrowser.tsx:163-164`); single-click select. NO drag-to-reorder, NO rename, NO right-click menu, NO multi-select. | 4/10 | `CaseBrowser.tsx:160-168` (click+hover only); absence of context menu, dnd, rename |
| Accessibility | Keyboard navigation, tooltip on icons, ARIA roles | `role="region"`, `aria-label` on section, `aria-pressed` on filter chips, `data-testid` IDs. No keyboard tree navigation (arrow keys). No tooltips on row items. | 5/10 | `CaseBrowser.tsx:101-105` (section role+aria-label); `CaseBrowser.tsx:127-132` (aria-pressed chips) |
| Motion | 150ms chevron rotation + 150-200ms height transition on expand/collapse | No expand/collapse animation on groups. Case item hover transitions via `index.css:81` (`transition: all 0.2s ease`). No chevron on groups. | 2/10 | `index.css:81` (case-item hover transition only); absence of expand/collapse animation |

**Aspect mean: (5+3+7+4+5+2)/6 = 4.3/10**

### Critical-to-success signals

| Signal | Present? | Evidence | Gap detail |
|---|---|---|---|
| Multi-section single-tree (components/materials/loads/constraints/sets) | partial | `CaseBrowser.tsx:76-87` (solver-kind grouping only, not entity classes) | Groups by solver-kind, not by entity-type (property / material / loadcollector) |
| Per-row 3D visibility toggle (eye-icon) | no | absence | No per-row visibility toggle; no viewport wiring |
| Right-click context menu (≥6 actions) | no | absence | No ContextMenu component |
| Inline rename (double-click name) | no | absence | No inline-edit affordance |
| Drag-to-reorder/reparent | no | absence | No react-dnd or equivalent |
| Search / incremental filter | yes | `CaseBrowser.tsx:116-123` (`<input type="search">`) | Filters by label+caseId; no fuzzy match |
| Color swatch per component | no | absence | No per-case color swatch |
| Tree-view perspectives switcher | partial | `CaseBrowser.tsx:65-69` (solver-kind filter chips only) | Chips are solver-kind only; no Component/Material/Property root-switch |

**Wins (codebase does better):**
1. Preview pane with solver-kind + claim-tier metadata on hover — not a standard HyperWorks Model Browser affordance (`CaseBrowser.tsx:188-222`).
2. Tier 2 validated filter chip as first-class browsing affordance (`CaseBrowser.tsx:125-133`).

---

## Surface 2 — viewport_3d
**Reference**: Abaqus/CAE Viewport + ANSYS Mechanical Graphics window
**Codebase counterpart**: `frontend/src/components/ResultMeshWebGLViewport.tsx` (690 LOC) +
`frontend/src/components/ResultMeshPlaybackPanel.tsx` (1476 LOC)

### Aspect breakdown

| Aspect | Reference behavior | Current behavior | Parity 0-10 | Evidence |
|---|---|---|---|---|
| Layout | Center stage; top-edge view-cube/triad; left-edge view-mode buttons; right/bottom legend + min/max + units + component selector; HUD | Center stage WebGL canvas. Bottom-right contour legend with min/max + units + field component selector. Floating hover coord readout in advanced mode. No view-cube/triad. No left-edge view-mode column. | 5/10 | `ResultMeshPlaybackPanel.tsx:676-780` (legend + component switcher); `ResultMeshPlaybackPanel.tsx:794-797` (CoordReadoutTooltip); absence of view-cube |
| Density | 25-40 affordances: view-cube + triad + ≥8 view-mode toggles + contour switcher + min/max + section cuts + clip-plane HUD + animation controls | ~15 affordances: 3D/SVG toggle, Compare-cuts toggle, play/pause, frame scrubber, section-cut axis+position, deformation scale, threshold filter, field component select, legend min/max. | 5/10 | `ResultMeshPlaybackPanel.tsx:500-580` (control row); absence of view-cube, triad, isolation toggles |
| Token use | Dark/light background (toggleable); mesh edges in contrast color; selected entity highlighted; contour legend canonical rainbow/blue-to-red | Single dark theme (`--bg-base: #020617`). Contour: blue→green→orange gradient (not rainbow but deliberate). Mesh: PhongMaterial with vertex colors. No per-entity highlight on selection (only probe HUD). | 6/10 | `ResultMeshWebGLViewport.tsx:173` (`renderer.setClearColor(0x020617)`); `polishStyles.ts:173-176` (gradient: `#2563eb → #10b981 → #f97316`) |
| Interaction | Orbit/pan/zoom/fit; left-click pick (node/element/face); box/lasso selection; section cuts with slider; probe with pin; animation scrubber; view saves | Orbit (left drag), pan (right drag), zoom (wheel), node pick (`onNodePicked`), hover coord readout, section cut (axis+position slider), deformation scale, animation play/pause/scrub, 2-quadrant companion viewport, field component switcher, threshold filter. No fit-all, no box selection, no view saves, no polygon/lasso. | 7/10 | `ResultMeshWebGLViewport.tsx:362-414` (orbit+pan); `ResultMeshWebGLViewport.tsx:427-450` (node pick); `ResultMeshPlaybackPanel.tsx:570-583` (section cut); `ResultMeshPlaybackPanel.tsx:870-898` (play+scrub) |
| Accessibility | Keyboard shortcuts for views; view-cube clickable; color-blind options | Tab navigation; aria-label on section and canvas; SVG fallback path for non-WebGL. No keyboard orbit shortcuts. No color-blind contour palette. | 4/10 | `ResultMeshPlaybackPanel.tsx:332-334` (`aria-label="OpenRadioss dynamic playback"`); `ResultMeshWebGLViewport.tsx:199` (`data-testid='webgl-canvas'`); absence of keyboard view shortcuts |
| Motion | Camera tween 300-500ms for named views; section cut immediate; animation at user FPS | Viewport-flex-row layout transition 200ms (`polishStyles.ts:154-159`); companion-mount fade-in 200ms (`polishStyles.ts:94-97`); WebGL context lost → SVG transition. No camera tween (camera transitions are immediate). | 5/10 | `polishStyles.ts:154-168` (viewport-flex-row + companion-mount); `ResultMeshWebGLViewport.tsx:362-414` (no camera tween) |

**Aspect mean: (5+5+6+7+4+5)/6 = 5.3/10**

### Critical-to-success signals

| Signal | Present? | Evidence | Gap detail |
|---|---|---|---|
| Probe / pick affordance (click → coords + value + element ID) | yes | `ResultMeshWebGLViewport.tsx:427-450` (raycast pick); `ResultMeshPlaybackPanel.tsx:829-860` (ProbeListPanel, max 8 pins) | Pick wired, persistent probe list, hover coord readout |
| Section / clip plane with positional slider | yes | `ResultMeshPlaybackPanel.tsx:570-583` (ViewportDepthControls with sectionCut); `ResultMeshWebGLViewport.tsx:285-300` (THREE.Plane clip) | Single-axis clip; no cylindrical/spherical |
| Contour legend + component switcher | yes | `ResultMeshPlaybackPanel.tsx:676-780` (legend + field-component select) | min/max + units + 9-option dropdown |
| Persistent camera state across field switches | partial | `ResultMeshWebGLViewport.tsx:226-236` (stateRef persists azimuth/elevation/radius) | Persistent within session; cleared on case switch |
| View-cube or triad with click-to-snap | no | absence | No orientation indicator |
| Animation scrubber | yes | `ResultMeshPlaybackPanel.tsx:892-898` (`<input type="range">` + play/pause) | Frame scrubber + play/pause/loop |
| Pick/hover surfacing of nodal value + coordinates | yes | `ResultMeshPlaybackPanel.tsx:794-797` (CoordReadoutTooltip in advanced mode); probe list shows per-node value | Hover coord in advanced mode; probe shows value |
| Selection filter (Node/Element/Face/Volume) | no | absence | No selection filter; pick always finds nearest node |
| Fallback render path | yes | `ResultMeshWebGLViewport.tsx:152` (`useState(detectWebGLSupport)`); `ResultMeshPlaybackPanel.tsx:638-667` (SVG fallback) | SVG fallback ships and auto-activates on context loss |

**Wins:**
1. 2-quadrant compare-cuts companion viewport — a comparative visualization affordance not standard in the reference (`ResultMeshPlaybackPanel.tsx:807-821`).
2. WebGL context-loss graceful degradation to SVG with toast notification (`ResultMeshPlaybackPanel.tsx:408-429`).

---

## Surface 3 — results_plot
**Reference**: ANSYS Mechanical "Solution Information" + Altair HyperGraph
**Codebase counterpart**: `frontend/src/components/TrustScoreTimelineChart.tsx` +
`frontend/src/components/ConvergenceStudyViewer.tsx`

### Aspect breakdown

| Aspect | Reference behavior | Current behavior | Parity 0-10 | Evidence |
|---|---|---|---|---|
| Layout | Dedicated plot pane: top toolbar + left curve tree + center 2D plot canvas (Cartesian axes + gridlines + legend) + right property editor + bottom data table | `TrustScoreTimelineChart.tsx`: SVG sparkline (320×60px) with 2 threshold gridlines. No toolbar, no curve tree, no property editor, no data table. `ConvergenceStudyViewer.tsx`: grid-based table display, no 2D plot canvas. | 2/10 | `TrustScoreTimelineChart.tsx:112-153` (SVG sparkline); `ConvergenceStudyViewer.tsx:76-120` (table layout) |
| Density | ≥40 affordances on screen (multi-window, curves with axes, legend, annotations) | ~8: sparkline SVG + 2 gridlines + timeline table + convergence table badges. No interactive affordances on the plot. | 1/10 | `TrustScoreTimelineChart.tsx:111-153`; `ConvergenceStudyViewer.tsx:60-130` |
| Token use | Light background + saturated curve colors; different line styles per curve | Dark background, single accent-colored SVG path. Threshold lines at 0.2 and 0.5 of height in accent/warning. No multi-curve differentiation. | 5/10 | `TrustScoreTimelineChart.tsx:131-152` (accent + warning threshold lines); `index.css:4-17` (token system) |
| Interaction | Click curve → properties; pick point → coords+value readout; pan/zoom; right-click axis; drag curves; synchronized x-axes; math curves | All plots are read-only SVG/DOM tables. No interactivity: no pick, no pan, no zoom, no axis controls, no curve math. | 1/10 | absence of event handlers on `TrustScoreTimelineChart.tsx` SVG elements |
| Accessibility | Keyboard curve navigation; tooltip on toolbar; color-blind palette | `role="img"` with `aria-label` on sparkline SVG. No keyboard navigation, no tooltips. | 3/10 | `TrustScoreTimelineChart.tsx:114-117` (`role="img"`) |
| Motion | Pan/zoom immediate; window add/remove 150ms fade | No transitions on chart content. Table rows static. | 1/10 | absence |

**Aspect mean: (2+1+5+1+3+1)/6 = 2.2/10**

### Critical-to-success signals

| Signal | Present? | Evidence | Gap detail |
|---|---|---|---|
| Cartesian axes with min/max + units + gridlines | partial | `TrustScoreTimelineChart.tsx:126-144` (2 horizontal threshold gridlines only; no tick labels or axis titles) | Threshold lines but no full Cartesian axes |
| Multiple curves on shared axes | no | absence | Only one curve per sparkline |
| Hover/click readout of curve point | no | absence | No interactive hover on SVG |
| Pan / zoom / fit-to-data | no | absence | Static SVG |
| Log-scale axis option | no | absence | |
| Export to CSV + image | no | absence | |
| Per-axis tolerance / threshold lines | partial | `TrustScoreTimelineChart.tsx:126-144` (2 static threshold lines at hardcoded 80 / 50 trust-score levels) | Lines present but not configurable |
| Derived / math curves | no | absence | |
| Multi-window page layout | no | absence | One sparkline at a time |

---

## Surface 4 — bc_setup_panel
**Reference**: Abaqus/CAE Load Module + ANSYS Mechanical Boundary Conditions
**Codebase counterpart**: `frontend/src/components/BCSetupPillList.tsx` (117 LOC) +
`frontend/src/components/BCSetupAdvisorCard.tsx`

### Aspect breakdown

| Aspect | Reference behavior | Current behavior | Parity 0-10 | Evidence |
|---|---|---|---|---|
| Layout | Left module-bar (Step/Type/Region/Geometry) + center 3D viewport for region pick + bottom prompt + dialog-driven BC creation. ANSYS: tree branch + Details panel (~8-15 fields per BC). | Read-only pill list (`BCSetupPillList.tsx:67-117`) showing BC names as styled pills. BC-setup advisor card (read-only orientation text + 4-Q gate). No authoring UI, no 3D region pick, no dialog. | 2/10 | `BCSetupPillList.tsx:67-117` (pill list section); `BCSetupAdvisorCard.tsx:57-80` (advisor card); absence of authoring dialog |
| Density | ~8-15 field entries per BC detail panel; ≥20 BCs visible in manager | ~3 pills visible per case type (no per-BC detail fields). 1 paragraph of orientation text. | 2/10 | `BCSetupPillList.tsx:89-117` (pill list renders 2-3 items per case) |
| Token use | BC category glyphs (arrow=force, flag=fixed, distributed=pressure); 3D viewport overlay arrows/cones/decals | Pills use `--text-secondary` / `--accent` color + `--accent-glow` background for assigned state. No BC-type glyphs. | 4/10 | `BCSetupPillList.tsx:102-114` (pill color tokens: `var(--accent)` / `var(--text-secondary)`) |
| Interaction | Create BC dialog (typed: Force/Pressure/Moment/Fixed/Displacement/Temperature); 3D region pick; magnitude entry with units; per-step assignment; Edit/Suppress/Delete/Duplicate; validation | Read-only. No BC authoring. No 3D pick. No CRUD. | 1/10 | `BCSetupPillList.tsx:2-15` (explicitly "read-only by design"); absence of authoring UI |
| Accessibility | All entry fields tabbable; per-field tooltip with units; keyboard shortcuts | `role="region"`, `aria-label`, `data-testid` on pill list section. Pill items are `<li>` (non-interactive). | 4/10 | `BCSetupPillList.tsx:71-79` (section role+aria-label+data-testid) |
| Motion | BC overlay appears immediately on creation; dialog open ≈150-200ms | No dynamic BC creation or overlay; static render. | 1/10 | absence |

**Aspect mean: (2+2+4+1+4+1)/6 = 2.3/10**

### Critical-to-success signals

| Signal | Present? | Evidence | Gap detail |
|---|---|---|---|
| Typed BC creation dialog (Force/Pressure/Fixed/Displacement/etc.) | no | absence | No authoring dialog |
| 3D-viewport region picking | no | absence | No mesh pick integration in BC panel |
| Per-step / per-loadcase assignment | no | absence | |
| 3D-viewport overlay visualization (arrows/cones/decals) | no | absence | |
| Magnitude entry with units + sign convention | no | absence | |
| Edit / Suppress / Delete / Duplicate | no | absence | Pills are read-only |
| Validation feedback (warnings for incomplete/conflicting BCs) | partial | `BCSetupAdvisorCard.tsx` (static orientation text suggesting validation approach); no live warning | Static advisory only, no live validation |
| Named-sets integration | no | absence | |
| Time-varying / amplitude curves | no | absence | |

**Wins:**
1. 4-question gate (LLM-offline / artifacts / TrustGate / advisory-only) surfaced inline at BC-setup stage — not a standard Abaqus affordance, but serves workbench transparency goals (`BCSetupAdvisorCard.tsx:76-77`).
2. `shouldShowBCSetupAdvisor` predicate correctly hides the card once BCs are assigned (`BCSetupPillList.tsx:57-61`).

---

## Surface 5 — mesh_visualization
**Reference**: Altair HyperMesh "Mesh" panels + Abaqus/CAE Mesh Module
**Codebase counterpart**: No dedicated mesh visualization component found.
The closest is `ResultMeshWebGLViewport.tsx` which renders result mesh (post-solve)
but there is no pre-solve mesh quality panel.

### Aspect breakdown

| Aspect | Reference behavior | Current behavior | Parity 0-10 | Evidence |
|---|---|---|---|---|
| Layout | 3D viewport + right-side mesh controls (seed density, element type, quality thresholds) + left/bottom mesh statistics | No pre-solve mesh visualization surface exists. ResultMeshWebGLViewport renders post-solve element mesh without quality statistics. | 1/10 | absence of mesh quality panel; `ResultMeshWebGLViewport.tsx:1` (renders result-mesh frames, not pre-solve mesh) |
| Density | ≥20-30 affordances: element count, node count, per-class counts, quality metrics (Jacobian/Warpage/Aspect/Skew), seed controls, element-type chooser | No mesh statistics, no quality metrics, no seed controls visible. Triangle count displayed in WebGL viewport but no quality histogram. | 2/10 | `ResultMeshWebGLViewport.tsx:153` (`triangleCount` state) but count not surfaced in UI; absence of quality panel |
| Token use | Contrast edge color over surface; quality recolor (red=bad / green=good); free-edge warning in saturated red/magenta | Contour color legend (blue→green→orange) for result values. No quality-specific recolor. Mesh edges rendered with ambient+directional lighting only. | 3/10 | `ResultMeshWebGLViewport.tsx:302-309` (PhongMaterial, vertex colors only) |
| Interaction | Mesh stats readout; quality color-coded recolor; free-edge visualization; edit element (split/merge/delete); probe element; seeding controls; element-type assignment; quality criterion sliders | No mesh quality interaction. WebGL viewport provides orbit/pan/zoom + node pick. No element edit, no seed controls, no quality sliders. | 2/10 | absence; `ResultMeshWebGLViewport.tsx:362-414` (orbit/pan/zoom only) |
| Accessibility | Keyboard shortcuts for mesh/unmesh/quality toggle; tooltip on metrics | No mesh-specific keyboard shortcuts. | 2/10 | absence |
| Motion | Re-meshing progress bar; quality-color recolor immediate; element highlight on hover | No re-meshing surface. WebGL hover fires `onHoverCoords` for coord readout but no element highlight. | 2/10 | `ResultMeshWebGLViewport.tsx:100-112` (onHoverCoords for coord tooltip only) |

**Aspect mean: (1+2+3+2+2+2)/6 = 2.0/10**

### Critical-to-success signals

| Signal | Present? | Evidence | Gap detail |
|---|---|---|---|
| Mesh quality histogram + per-metric thresholds (Jacobian/Aspect/Warpage/Skew) | no | absence | No quality panel |
| Free-edges / non-manifold visualization | no | absence | |
| Per-element-class element count (tet/hex/wedge/pyramid) | no | absence | Only total triangle count (`ResultMeshWebGLViewport.tsx:153`) |
| Edit-element panel (node drag, split, merge) | no | absence | |
| Element-type assignment (C3D4/C3D8/C3D10/S4) | no | absence | |
| Seeding & mesh-control panels | no | absence | |
| Quality color-coded recolor | no | absence | Contour is result-value only |
| Mesh statistics readout | no | absence | Triangle count tracked but not displayed |
| Render-mode toggle (wireframe/shaded/shaded-with-edges) | partial | `ResultMeshPlaybackPanel.tsx:533-569` (WebGL / SVG toggle, not wireframe/shaded/edges) | Mode toggle exists but is WebGL vs SVG fallback, not rendering-style selector |

---

## Per-surface parity summary

| Surface | Aspect mean | Confidence |
|---|---|---|
| case_tree_panel | 4.3/10 | high |
| viewport_3d | 5.3/10 | high |
| results_plot | 2.2/10 | high |
| bc_setup_panel | 2.3/10 | high |
| mesh_visualization | 2.0/10 | high |

**Overall mean parity: 3.2/10**

---

## Dim 3 Anchor Determination

### Anchor 60 check: "Tokens-based design system (colors/spacing/typography as variables, not magic numbers). Single-theme."

- `index.css:4-17` defines CSS custom properties: `--bg-base`, `--bg-sidebar`, `--bg-surface`, `--accent`, `--accent-glow`, `--text-primary`, `--text-secondary`, `--text-muted`, `--border`, `--border-focus`, `--glass-blur`, `--shadow-lg`. Font: `Plus Jakarta Sans`.
- All component inline styles and class styles consume these variables (e.g., `CaseBrowser.tsx:313-400`, `BCSetupPillList.tsx:102-114`, `ResultMeshPlaybackPanel.tsx:441-444`).
- Single dark theme (slate-950 base). **No light theme.**
- **ANCHOR 60: ALL sub-bullets met.** Evidence: `index.css:1-32`.

### Anchor 70 check: "+ Motion vocabulary documented (≥1 timing curve, ≥1 entrance + exit pattern)"

- Timing curve documented: `200ms ease-out` (dominant) + `150ms ease-in` (exit). `180ms ease-out` for chevron rotation.
  Evidence: `polishStyles.ts:100`, `104`, `122`, `125`, `155`, `167`, `193`.
- Entrance pattern: probe-row-fade-in (`200ms ease-out + 6px lift`), restored-toast-fade-in, advanced-mode-promo-fade-slide-in, companion-mount-fade-in.
- Exit pattern: probe-row-fade-out (`150ms ease-in`).
- Motion vocabulary is in-code (not in a separate `tokens.md`), but the polishStyles.ts file IS the documentation artifact for the motion patterns.
- Single theme polished: consistent dark glassmorphism throughout.
- **ANCHOR 70: ALL sub-bullets met.** Evidence: `polishStyles.ts:1-239`.

### Anchor 80 check: "+ ≥7 motion-vocabulary surfaces + (drag-resize panels OR density toggle OR 4-quadrant layout — ANY 1 of 3) + dark token system primitives"

**≥7 motion-vocabulary surfaces:**
1. Probe-row entrance fade (`polishStyles.ts:99-101`, `fm04a-probe-row-fade-in`)
2. Probe-row exit fade (`polishStyles.ts:103-105`, `fm04a-probe-row-fade-out`)
3. Restored-toast entrance (`polishStyles.ts:107-123`, `fm04a-restored-toast-fade-in`)
4. Advanced-mode promo slide-in (`polishStyles.ts:124-126`, `fm04a-advanced-mode-promo-fade-slide-in`)
5. Companion-viewport mount fade (`polishStyles.ts:166-168`, `fm04a-companion-mount-fade-in`)
6. Viewport-flex-row layout-swap transition (`polishStyles.ts:154-159`, gap/flex-basis 200ms ease-out)
7. SectionFrame chevron rotation (`polishStyles.ts:192-194`, `180ms ease-out`)
(Additionally: case-item hover in `index.css:81`, `transition: all 0.2s ease`)
→ **≥7 motion surfaces: MET (exactly 7 from polishStyles.ts alone).**

**Drag-resize OR density toggle OR 4-quadrant layout:**
- Drag-resize: `grep -rn "dragResize\|drag.*resize\|resize.*handle" ...` returns zero results. **ABSENT.**
- Density toggle: No density toggle found anywhere in codebase. **ABSENT.**
- 4-quadrant layout: App-root is `gridTemplateColumns: '240px 300px 1fr'` — 3 columns, not 4. The companion viewport creates a 2-quadrant viewport split inside the main content area (`ResultMeshPlaybackPanel.tsx:585-821`), but the outer app shell is 3-column. The rubric anchor says "4-quadrant layout." The companion creates a 2-quadrant sub-layout, not a full 4-quadrant app layout. **ABSENT as a whole-app 4-quadrant layout.**

However — re-reading the anchor: "4-quadrant layout" is listed as ONE of THREE alternatives where ANY 1 suffices. The companion viewport does create a meaningful 2-viewport split (2-quadrant). Does this count as the "4-quadrant layout" intent? The rubric anchor at 90 lists "4-quadrant layout" alongside "drag-resize + density toggle + collapsible rails — ALL 4 shipped." The 80-anchor phrasing "4-quadrant layout (any 1 of 3)" likely refers to a full 4-panel workbench layout (viewport top-left / viewport top-right / tree panel / results panel), not a sub-panel 2-way split. The main app is definitively 3-column, not 4-quadrant.

**Conclusion: None of the 3 alternatives (drag-resize / density / 4-quadrant) are shipped at the app-layout level.**

→ **ANCHOR 80: NOT fully met.** The ≥7 motion surfaces sub-bullet IS met. The "any 1 of 3" sub-bullet is NOT met (no drag-resize, no density toggle, no 4-quadrant app layout). The dark token system primitives sub-bullet IS met (dark-only token vars in `index.css:4-17` — "NOT yet a toggle" is the 80-anchor expectation, which matches the codebase: dark-only, no toggle).

**Score: between 70 and 80.**

### Interpolation between 70 and 80

- Anchor 70 is fully met.
- Anchor 80 requires 3 sub-bullets: ≥7 motion surfaces (MET) + any-1-of-3-layout-feature (NOT met) + dark token primitives (MET).
- 2 of 3 sub-bullets for anchor 80 are met. 0 of the layout alternatives are met.
- The missing sub-bullet (layout feature) is a material UI capability gap that results in the 90-anchor being very far.
- Interpolation: 70 fully met + 2/3 of 80's sub-bullets → score ≈ **76**.

---

## Dim 3 Score: **76 / 100**

**Anchor landed on: 70 (fully met), interpolated to 76 due to 2/3 of anchor-80 sub-bullets met.**

**Reasoning:**
- Token-based design system with 11 CSS variables: **anchor 60 met** (`index.css:4-17`).
- Motion vocabulary with ≥2 timing curves (200ms ease-out, 150ms ease-in, 180ms ease-out) + entrance AND exit patterns: **anchor 70 met** (`polishStyles.ts:1-239`).
- ≥7 distinct motion surfaces: **80-sub-bullet met** (7 confirmed from `polishStyles.ts`).
- Dark token system primitives (dark-only, no toggle): **80-sub-bullet met** (`index.css:4-17`).
- No drag-resize panels, no density toggle, no 4-quadrant app layout: **80-sub-bullet NOT met** — the app is a 3-column `240px 300px 1fr` grid (`App.tsx:1215`), and there is no resizable panel handle anywhere in the codebase.

The 76 score reflects meaningful polish infrastructure (strong token system, documented motion vocabulary, 7 surfaces with consistent 200ms ease-out) but the absence of any major layout adaptation feature (drag-resize / density / 4-quadrant) keeps the score below 80. The very low per-surface parity scores on results_plot (2.2/10), bc_setup_panel (2.3/10), and mesh_visualization (2.0/10) corroborate that the UI-parity gap remains large on those surfaces, but per the calibrated rubric procedure, the anchor method governs the Dim 3 score — not a raw parity × 10 computation.

**Reference descriptions:** All 5 reference descriptions are present at `.planning/test_subagents/references/` (bc_setup_panel.md, case_tree_panel.md, mesh_visualization.md, results_plot.md, viewport_3d.md) — this satisfies the 90-anchor's "reference descriptions documented" sub-bullet, but the 90-anchor has 4 sub-bullets ALL of which must be met (drag-resize + density + 4-quadrant + collapsible rails all 4, plus parity ≥7/10 on ≥5 surfaces). Per-surface parity averaging 3.2/10 fails the "parity ≥7/10 on ≥5 surfaces" sub-bullet, which definitively keeps the score below 90.

---

## Feature-checklist gap summary (80/90 anchors)

### At 80-anchor — what is missing:
- **ANY ONE of**: drag-resize panels / density toggle / 4-quadrant layout. None exist. Adding any one would lift to 80.

### At 90-anchor — what is missing (all required):
1. Drag-resize panels — **ABSENT**
2. Density toggle — **ABSENT**
3. 4-quadrant layout — **ABSENT** (3-column app shell; companion is a 2-way sub-split)
4. Collapsible left/right rails — **ABSENT** (rails have no collapse button; SectionFrame collapse is inside the content area, not the rails)
5. Comparator parity ≥7/10 on ≥5 surfaces — **ABSENT** (current: 4.3, 5.3, 2.2, 2.3, 2.0 → zero surfaces ≥7/10)
6. Reference descriptions documented — **PRESENT** (all 5 at `.planning/test_subagents/references/`)

---

## Report written to
`.planning/audits/phase38d_industrial_ui_comparator.md`

Tier 1 / Tier 2 engineering candidate; not signed validation; not benchmark agreement.
绝对诚实客观 contract in force.
