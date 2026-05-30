# FM-04a Phase 43 — industrial-ui-comparator (Dim 3 Industrial UI parity)

> Registered evaluation fleet (`subagent_type=industrial-ui-comparator`). Tier 1
> engineering candidate; not signed validation. 绝对诚实客观. Code @ `c3422b4`.
> Anti-gaming: scored by the sub-agent (B:-1), file:line evidence or explicit absence
> (D:-1), NOT given any prior audit/retro/blueprint (F:-1), scores what the markup IS
> not what it CLAIMS (G:-1). Parity vs Hyperworks / Abaqus / ANSYS / Simcenter.

## Dim 3 — Industrial UI parity: **78 / 100**

**80-anchor fully met** + several 90 sub-bullets land, but 90 is NOT fully met → upper
band, interpolated **78**.

- **80 met:** motion vocabulary across 8 surfaces (`index.css:99-101` timing tokens →
  `case-item`, `surface-card`, `cb-case-card`, `tab-pill`, `run-solver-btn`,
  `skeleton-line`, `mode-pulse-dot`, `solve-sweep`); compare-cuts split
  (`CompanionViewport.tsx:1-6`); dark token primitives (`ViewportNavGizmo.tsx:69-73`,
  `ScaleBar.tsx:122`).
- **90 partial (the cap):** the 90-anchor needs **all four** of {drag-resize panels,
  density toggle, 4-quadrant, collapsible rails}. **Drag-resize: ABSENT** (fixed
  `gridTemplateColumns:'210px 300px 1fr'` `App.tsx:1226`; no splitter/`col-resize`
  anywhere). **Density toggle: ABSENT.** **Collapsible rails: ABSENT.** **Theme toggle:
  ABSENT** (95-anchor; single `:root` `index.css:20`). These four missing layout systems
  are the specific gap.

## Per-pillar parity (mean of 6 aspects)

| Aspect | /10 | Evidence |
|---|---|---|
| Layout | 7 | 3-column shell `App.tsx:1226` + bottom status strip `StatusBar.tsx:56-75`/`App.tsx:1485` + compare-cuts split. GAP: columns not drag-resizable, rails not collapsible. |
| Density | 7 | Viewport HUD dense: orientation triad + 5 presets (`ViewportNavGizmo.tsx:39-45,100-103`), legend w/ 5 ticks+units (`ScaleBar.tsx:48,97-103,174-178`), colormap selector (`ResultMeshPlaybackPanel.tsx:822-829`), status bar (`StatusBar.tsx:141-224`), hero readout (`HeroPeakReadout.tsx:88-96`). ~15-18 affordances vs reference 25-40 (`viewport_3d.md:18-22`). GAP: no view-mode toggle column, no selection-filter, no anim speed/loop. |
| Tokens | 9 | Full variable system: neutral ramp `index.css:22-34`, accent `:37-41`, status hues w/ documented WCAG ratios `:46-54`, elevation `:78-82`, spacing/radius/type/motion `:85-101`; consumed consistently (`ScaleBar.tsx:122-127`, `StatusBar.tsx:67-69`). GAP: single theme. |
| Interaction | 8 | Hand-rolled orbit/pan/zoom (`ResultMeshWebGLViewport.tsx:538-560`), raycast pick w/ click-vs-drag threshold (`:593-608`), 5 named presets (`ViewportNavGizmo.tsx:51,117`), Cmd-K palette w/ arrow+Enter+Esc (`CommandPalette.tsx:111-126`), section cuts + companion. GAP: no box/lasso, no selection-filter, no named-view save, no camera tween, no drag-resize. |
| Accessibility | 8 | Real `<button>` + `aria-label`/`title` (`ViewportNavGizmo.tsx:111-117`); `role="dialog"`+`aria-modal`+focus-trap (`CommandPalette.tsx:88-90`, `ShortcutsOverlay.tsx:61,108-110`); `role=listbox/option` (`CommandPalette.tsx:132,143-144`); `role=status` (`StatusBar.tsx:227`); `:focus-visible` outline (`index.css:156-159`); `prefers-reduced-motion` (`:463-478`); `?` cheat-sheet (`ShortcutsOverlay.tsx:74-100`). GAP: no committed WCAG audit; gizmo triad `0.6rem` (`:96`) small; `aria-live="off"` status bar (`:227`) → coord/run-state not announced. |
| Motion | 9 | Timing tokens `index.css:99-101`; entrance `:248-252`, hover lift `:261-266,398`, solve-pulse `:401-405`, indeterminate sweep `:446-450`, mode-pulse `:435-439`, skeleton `:420-430`; all suppressed under reduced-motion `:463-478`. GAP: no camera-tween on preset switch (`viewport_3d.md:52` wants ~300-500ms); gizmo button hardcodes `'130ms ease'` (`ViewportNavGizmo.tsx:142`) vs token. |

**Aspect mean: (7+7+9+8+8+9)/6 = 8.0/10** → 80 base, cannot reach 90 (4 layout
systems absent), exceeds 80 on every per-surface metric → **78**. Confidence: high.

## Highest-leverage missing capabilities

1. **Drag-resizable / collapsible panel docks** — ABSENT (`App.tsx:1226` hard-pinned
   grid). Single gap blocking the 90-anchor. → splitter handle + drag state in `App.tsx`.
2. **Density toggle + dark/light theme toggle** — ABSENT. → token-set swap on `:root`
   + header control.
3. **View-mode column + selection filter** (wireframe/shaded/edges; Node/Element/Face)
   — ABSENT (`viewport_3d.md:14-16,73-74`). → left-edge tool column beside the gizmo.
4. **Named-view save + camera tween on preset switch** — ABSENT
   (`ViewportNavGizmo.tsx:117` snaps instantly). → `setView` seam.
5. **Live status-bar announcements + WCAG audit artifact** — `aria-live="off"`
   (`StatusBar.tsx:227`) + no committed report. → `aria-live="polite"` + a WCAG audit.

**Wins over reference:** the ScaleBar legend gradient is sampled from the *same*
`colorForValueFraction` ramp the mesh uses (`ScaleBar.tsx:58-67`) → the legend
provably cannot misrepresent on-screen colors; honest degenerate-field handling (solid
band, no fabricated spread, `ScaleBar.tsx:74-77,107`) and never-fabricated solver-%
(`SolverProgressPanel.tsx:16-22`) exceed reference tools.
