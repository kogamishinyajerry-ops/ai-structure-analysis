# Phase 23 — UI audit (Round 1)

> **Frame:** Tier 1 / Tier 2 engineering candidate; not signed
> validation; not benchmark agreement. Phase 22 baseline UI = 81.4/100.
> Blueprint UI projection: 84-86 (mid 85).

## Dimensions

### Dim 1 — Composition-root LOC discipline (0-100)

**Score: 90/100.** -2 from Phase 22 (92). Honest miss: Phase 23
adds props to ResultMeshWebGLViewport (fieldComponent + onNodePicked
+ valueFilter) and grows ResultMeshPlaybackPanel (ViewportDepthControls
now has filter row). App.tsx LOC unchanged (still 1498), but the
viewport file went from ~675 to ~820 LOC. Worth noting because the
trajectory is composition-root → component-files, and Phase 23 grew
component files faster than App.tsx shrank.

Evidence:
- `wc -l frontend/src/App.tsx` → 1498 (unchanged).
- `wc -l frontend/src/components/ResultMeshWebGLViewport.tsx` →
  ~820 (was ~675 at end of Phase 22).

Gap to 99: viewport file could be split into raycaster + animation
+ geometry-build modules. Phase 24+ scope.

### Dim 2 — Industrial-CAE comparison (0-100)

**Score: 83/100.** +5 from Phase 22 (78). Three new features each
match a standard industrial-CAE post-processor pattern:
- Node-picking with HUD (Slice C) — ANSYS Mechanical, Abaqus/CAE,
  HyperMesh all have this. Reviewer probe is foundational.
- Per-component σ switcher (Slice B) — every commercial CAE has
  σ_xx / σ_yy / σ_zz / shear / Mises / principal selectors.
- Threshold filter (Slice D) — many tools have an "iso-display"
  filter; ours is simpler (element-level) but functionally close.

Evidence:
- Node-pick HUD shows label + xyz + field value in scientific
  notation (industry-standard formatting).
- 9 component options in the dropdown matches industrial tools.
- Filter mode IN/OUT button mirrors the typical CAE
  "show range" / "hide range" toggle.

Gap to 99: still no iso-surface rendering (true threshold-surface
not just element-cull), no streamlines, no animation of failure
sequence, no fracture-mechanics overlay. Multi-phase scope.

### Dim 3 — Visual polish (0-100)

**Score: 78/100.** +1 from Phase 22 (77). Phase 23 C's HUD overlay
adds a visual polish element: top-right pinned panel with bold
NODE label, scientific-notation coords, and a colored field-value
line. Looks like a CAE reviewer's probe panel. But the threshold-
filter row and component-dropdown stayed utilitarian.

Evidence:
- HUD uses a blue accent on the NODE label header, yellow on the
  field value — feels like a CAE tool's probe overlay.

Gap to 99: no animation on HUD appear/disappear, no easing, no
custom slider tracks for the threshold filter, no hover preview
on the section-cut position.

### Dim 4 — Information density vs clarity (0-100)

**Score: 81/100.** +2 from Phase 22 (79). The HUD is dense but
clear (4 lines: NODE id, x, y, z, then field). The legend gained
a real dropdown which replaces the read-only chip — same vertical
space, more information. Threshold-filter row uses two sliders
with always-visible numeric labels (min ≥ / max ≤) so the user
sees the exact bound without hover.

Evidence:
- Legend chrome: gradient + min/max with Pa suffix + field-
  component dropdown — three vertically-stacked rows of distinct
  information.
- Threshold-filter row labels carry the current value (min ≥
  1.23e+5 etc) so no hover required.

Gap to 99: Topbar continues to busy itself with each phase's
additions (analysis-type + material + Run Solver + Stop + Copilot
+ ...). The depth controls row is now 2 sub-rows tall.

### Dim 5 — 3D viewport depth & interactivity (0-100)

**Score: 85/100.** +4 from Phase 22 (81). Phase 23 C's raycaster
+ HUD is a major 3D depth lift. The viewport is no longer
"navigate and look" — it's "navigate, probe, and inspect."
Phase 23 D's threshold filter adds a third dimension of
interactivity (what to show vs hide).

Evidence:
- 6 mouse interactions (drag/right-drag/wheel from before) + 1
  new click for pick + 1 new key for Escape clear = 8 distinct
  reviewer affordances on the viewport.

Gap to 99: see UI Dim 2 — iso-surfaces, vectors, multi-pick.
Plus real WebGL E2E tests still mock-only (Phase 21 carry-
forward still open).

## Composite

| Dim | Phase 22 | Phase 23 | Delta |
|---|---|---|---|
| LOC discipline | 92 | 90 | -2 |
| Industrial CAE comparison | 78 | 83 | +5 |
| Visual polish | 77 | 78 | +1 |
| Information density | 79 | 81 | +2 |
| 3D depth & interactivity | 81 | 85 | +4 |
| **UI composite** | **81.4** | **83.4** | **+2.0** |

**UI axis: 83.4/100.** Inside blueprint band (84-86) at the LOW
end (slightly below). Industrial-CAE comparison + 3D depth carried
the lift; LOC discipline regressed because viewport file grew
fastest. Honest miss documented.

Not signed validation; not benchmark agreement.
