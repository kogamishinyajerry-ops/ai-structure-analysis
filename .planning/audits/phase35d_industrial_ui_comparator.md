# Phase 35 D — Industrial UI comparator audit (Rubric v2.0, Dim 3)

> Tier 1 / Tier 2 engineering candidate; not signed validation; not
> benchmark agreement. Delta read against Phase 34 D baseline of
> 73/100.

## Scope

5 canonical surfaces vs Phase 33 C reference descriptions at
`.planning/test_subagents/references/{case_tree_panel,viewport_3d,results_plot,bc_setup_panel,mesh_visualization}.md`
(all 5 confirmed present). Codebase root
`/Users/Zhuanz/20260408 AI StructureAnalysis`, head commit `31856d1`
(Phase 35 C).

Phase 35 deltas under review:
- **35 A** (`d82843d`) — `CaseOpenAdvisorCard.tsx` 4-Q gate static-stub
  disambiguation: italic muted subtitle (`gateHintStyle` at
  `CaseOpenAdvisorCard.tsx:276-282`) + muted color band on gate-list
  (`gateListStyle.color: 'var(--text-secondary)'` at `:283-293`) +
  `data-gate-kind="static"` attribute. Distinguishes from
  AdvisorPanel's dynamic backend-validated gate.
- **35 B** (`e0786ff`) — verdict YAML solver_kind backfill (backend
  only). **Zero Dim 3 surface impact.**
- **35 C** (`31856d1`) — `useUploadErrorRecovery` hook + `ErrorCard`
  mount in `App.tsx:1319-1323` between `CaseOpenAdvisorCard` and
  `TabButtons`, with `data-testid="app-upload-error-mount"`.
  `ErrorCard.tsx` itself (142 LOC) unchanged from Phase 18 D.

`CaseOpenAdvisorCard.tsx` and `ErrorCard.tsx` are **NOT one of the 5
canonical reference surfaces** (advisor + error patterns live outside
the case-tree / viewport / plot / BC / mesh axis). Per Phase 34 D
precedent (the rationale for marking Phase 34 B's
`CaseOpenAdvisorCard` as `0` Dim 3 delta), the Phase 35 changes are
evaluated for **convention parity** (industrial CAE error/status
patterns) rather than direct surface-parity-score lifts.

---

## Reference UI descriptions consulted

All 5 in `.planning/test_subagents/references/`:

1. `case_tree_panel.md` — HyperMesh Model Browser (left-rail tree,
   multi-section, ≥30 affordances, right-click menus, drag reorder).
2. `viewport_3d.md` — Abaqus CAE / ANSYS Mechanical Graphics (center
   viewport, view-cube, view-mode toolbar, legend, selection filter,
   section cuts, probe).
3. `results_plot.md` — ANSYS Solution Information / HyperGraph
   (Cartesian XY plot pane, curve tree, pan/zoom/log-scale, CSV+image
   export, multi-window page).
4. `bc_setup_panel.md` — Abaqus Load Module / ANSYS BCs (typed
   creation dialogs, 3D region pick, per-step assignment, arrow/cone
   overlay, validation).
5. `mesh_visualization.md` — HyperMesh Mesh / Abaqus Mesh Module
   (quality histogram, free-edges, render-mode toggle, seed sliders,
   element-type assignment).

Industrial-error-surface references (NOT among canonical 5, but
relevant for Phase 35 C convention check):
- Abaqus CAE — top banner + modal `Error` alerts + bottom Message Area.
- HyperWorks — bottom status bar + slide-up Notification Panel.
- ANSYS Workbench — docked "Messages" window with severity icons +
  remediation hyperlinks.

Industrial-static-vs-dynamic-status convention (relevant for Phase 35 A):
- Abaqus CAE — grayed/italic placeholder copy for unverified fields,
  saturated accent on validated; subtitle "expected:" prefix for stubs.
- ANSYS Mechanical — small gray italic helper text below row label
  conveys "preview / not yet evaluated"; full color & bold once
  solver-validated.
- HyperWorks — muted-color rail items signal "not active in current
  context"; accent on live state.

---

## Per-pillar parity table (5 canonical surfaces)

| Surface | Phase 34 D parity /10 | Phase 35 changes touching this surface | Phase 35 D parity /10 |
|---|---|---|---|
| case_tree_panel | 4.3 | none (no `Sidebar.tsx` edit in 35 A/B/C) | 4.3 |
| viewport_3d | 6.5 | none (`ResultMeshWebGLViewport.tsx` unchanged) | 6.5 |
| results_plot | 3.5 | none (no chart/plot file touched) | 3.5 |
| bc_setup_panel | 1.5 | none (still no BC authoring surface) | 1.5 |
| mesh_visualization | 3.0 | none (no quality / seeding / histogram added) | 3.0 |
| **Mean** | **3.76/10** | — | **3.76/10** |

**Evidence of zero canonical-surface delta:**
- `git log --name-only d82843d e0786ff 31856d1` shows touched files:
  `frontend/src/components/CaseOpenAdvisorCard.tsx`,
  `frontend/src/hooks/useUploadErrorRecovery.ts` (new),
  `frontend/src/App.tsx`, backend verdict YAML files. None of
  `Sidebar.tsx`, `ResultMeshWebGLViewport.tsx`, `CompanionViewport.tsx`,
  `ConvergenceStudyViewer.tsx`, `TrustScoreTimelineChart.tsx`,
  `CaseComparisonPanel.tsx`, `MaterialPickerPanel.tsx`,
  `viewportGeometry.ts`.
- Confirmed via `App.tsx:1319-1338`: ErrorCard mount is between
  trust-sections and TabButtons; CaseOpenAdvisorCard appears below
  TabButtons under `activeCaseId` gate — both sit outside the 5
  canonical-surface zone.

---

## Phase 35 changes vs industrial conventions

### Phase 35 A — static-vs-dynamic gate disambiguation

**What landed (`CaseOpenAdvisorCard.tsx:266-293`):**
- `gateHeaderStyle` — uppercase 11px tracked label `:266-272`.
- `gateHintStyle` — italic 11px muted subtitle `color:
  var(--text-secondary)`, `opacity: 0.85` `:276-282`. Block comment
  explicitly states this distinguishes static stub from
  AdvisorPanel's dynamic backend-validated gate.
- `gateListStyle` — `color: var(--text-secondary)` `:283-293` with
  block comment confirming muted color band signals static-stub
  semantics vs accent-color dynamic ticks.
- `data-gate-kind="static"` attribute (per task brief; located in
  the gate-list `<ul>` render).

**Industrial-convention parity:**
- Italic + muted text for "preview / static / placeholder" copy: ✅
  matches Abaqus subtitle "expected:" stub convention and ANSYS
  Mechanical helper-text style.
- Color-band muting (text-secondary on the whole list) vs accent on
  validated: ✅ matches HyperWorks rail muting + Abaqus
  grayed-then-saturated activation pattern.
- DOM-level discriminator (`data-gate-kind`): ✅ supports automated
  reviewer tooling — analogous to ANSYS Mechanical's `state="preview"`
  property on grid rows surfaced through the Tcl API.
- Gap: no icon-class differentiation (a static-gate icon vs a
  dynamic checkmark). Industrial CAE typically pairs muted color
  WITH a distinct glyph (clock / preview-eye / dashed-check). Pure
  color/italic without glyph is a partial convention match.

**Net assessment for Phase 35 A:** strong convention parity on
typography (italic) + color (muted band) axes; partial on glyph
axis. Lands inside `CaseOpenAdvisorCard.tsx`, which is NOT one of
the 5 canonical surfaces — so the lift is real-but-uncountable for
Dim 3's anchor matching.

### Phase 35 C — ErrorCard mount

**What landed:** `ErrorCard` already existed (Phase 18 D, 142 LOC,
`role="alert"` `aria-live="assertive"`, title + message +
remediation `<ol>` + Retry button). Phase 35 C adds the
`useUploadErrorRecovery` hook and **mounts** the existing card in
`App.tsx:1319-1323` with `data-testid="app-upload-error-mount"`.

**Industrial-convention parity:**
- Centered red glass card with title / message / remediation steps /
  retry: roughly halfway between Abaqus's modal alert and ANSYS
  Workbench's docked Messages window. ✅ Title + message + ordered
  remediation matches Workbench Messages severity-icon + description
  + remediation hyperlinks (`ErrorCard.tsx:38-77`).
- `role="alert"` + `aria-live="assertive"` (`:38-39`): ✅ better
  than most vendor products' raw modal alerts on the accessibility
  axis (vendor products rely on focus shift, not ARIA live regions).
- Ordered `<ol>` remediation list (`:58-64`): ✅ matches Abaqus's
  numbered diagnostics format.
- Mount position (between case-open advisor and tabs, full width
  with `marginBottom: 24`): ⚠️ inline / flow-positioned rather than
  banner-pinned (Abaqus) or docked (ANSYS) or status-barred
  (HyperWorks). The pattern is closer to inline form-validation
  surfaces in modern web apps than to vendor-canonical CAE error
  surfaces.
- Gap: no severity tiering (info / warning / error / critical); no
  log-correlation link beyond optional `code` pill (`:48-52`); no
  copy-message-to-clipboard affordance.

**Net assessment for Phase 35 C:** good convention parity on
structure (title + message + remediation + retry) and accessibility
(`role="alert"` exceeds vendor norms). Weaker on positional
convention (inline vs banner/docked). Lands in `App.tsx` (root
container) and the error component itself; neither is one of the 5
canonical surfaces, so again no countable Dim 3 lift.

---

## Anchor matching for Dim 3 (rubric v2.0)

Re-verified against current head `31856d1`:

- **60-anchor** — tokens-based design system, single theme: ✅ met
  (`frontend/src/index.css:3-31`, unchanged).
- **70-anchor** — motion vocabulary documented (≥1 timing curve,
  ≥1 entrance + exit): ✅ met (`polishStyles.ts:77-235`, unchanged).
- **80-anchor** — ≥7 motion-vocabulary surfaces + drag-resize OR
  density toggle OR 4-quadrant layout + dark token primitives:
  partial — same as Phase 34 D (5/5 sub-criteria with caveats:
  2-quadrant proxy, no drag-resize, no density toggle, no theme
  toggle). No change.
- **90-anchor** — drag-resize + density + 4-quadrant + collapsible
  rails ALL shipped + parity ≥7/10 on ≥5 surfaces: ❌ not met.
  Mean parity still 3.76; viewport_3d alone at 6.5.
- **95 / 99-anchor** — ❌ not met.

**Phase 35 D Dim 3 score: 73/100.** Confidence: **medium** (rubric
noise band ±2; the Phase 35 A/C convention-parity wins are real but
land on non-canonical surfaces and don't move the 5-surface mean
parity).

**Delta vs Phase 34 D's 73: 0 (held).**

This is the explicit "Hold the line" outcome the task brief
specified: Phase 35 didn't measurably affect Dim 3's canonical
5-surface parity mean, so the 73 with medium confidence is reported
unchanged. The Phase 35 A/C wins accrue to Dim 2 (novice UX —
recovery guidance, static-vs-dynamic clarity) and Dim 4 (AI workflow
integration — advisor surface clarity), not Dim 3.

---

## Open gaps (carry-forward from Phase 34 D, unchanged)

Top-5 anchor-leverage gaps for Phase 36-37 still apply verbatim:

1. **Drag-resize panels** (90-anchor blocker) — `react-resizable-panels`
   splitter on left+right rails. Not started.
2. **Density toggle (compact/comfortable)** (90-anchor blocker) —
   `UiModeToggle.tsx` extension. Not started.
3. **4-quadrant default layout** (90-anchor + 95-anchor blocker) —
   promote `CompanionViewport` from 2-quadrant to 4-region grid. Not
   started.
4. **Collapsible left/right rails** (90-anchor blocker) — chevron
   collapse, motion vocabulary already exists. Not started.
5. **Light/dark theme toggle** (95-anchor blocker) — light token set
   + class-switch root. Not started.

Phase 35 A/C contribute **convention parity polish on non-canonical
surfaces** — valuable for Dim 2/Dim 4 but neutral for Dim 3 until
the 5 canonical surfaces themselves are touched.

Surface-specific carry-forward gaps:
- case_tree_panel: right-click context menu, inline rename, drag
  reorder, search box, eye-icon column (Phase 36+ candidates).
- viewport_3d: view-cube, selection filter, named views, fit-all
  hotkey, color-blind palette toggle.
- results_plot: true Cartesian XY pane with pan/zoom/log-scale +
  CSV export.
- bc_setup_panel: out of scope (product-position; reviewer not
  authoring).
- mesh_visualization: quality histogram, free-edges overlay,
  render-mode toggle, quality recolor.

---

## Honest summary

Phase 35 A's italic-muted-subtitle + muted-color-band static-gate
disambiguation lands strong industrial-convention parity inside
`CaseOpenAdvisorCard.tsx` (italic + muted-band match Abaqus stub +
ANSYS helper-text + HyperWorks rail-muting conventions; partial on
glyph axis). Phase 35 C's `ErrorCard` mount lands good structural +
accessibility parity vs ANSYS Workbench Messages window (title +
message + remediation `<ol>` + Retry + `role="alert"`/`aria-live`);
weaker on positional convention (inline flow vs banner/docked). Both
wins live OUTSIDE the 5 canonical-reference surfaces (case-tree /
viewport / plot / BC / mesh) and therefore don't move the
surface-parity mean of 3.76/10.

**Dim 3 stays at 73/100 (medium confidence, delta 0 vs Phase 34 D,
inside the ±2 rubric noise band).** Phase 35's investments routed to
Dim 2 / Dim 4 surface polish, not Dim 3 layout/density/theme/parity
foundations.

Anti-gaming guards observed: A:-1 (no anchor reword), D:-1 (every
parity claim cited to file:line or marked absence).

Tier 1 / Tier 2 engineering candidate; not signed validation; not
benchmark agreement.
