# Phase 25 — UI audit (Round 1)

> **Frame:** Tier 1 / Tier 2 engineering candidate; not signed
> validation; not benchmark agreement. Phase 24 baseline UI = 85.2/100.
> Blueprint UI projection: 86-87 (mid 86.5).

## Dimensions

### Dim 1 — Composition-root LOC discipline (0-100)

**Score: 94/100.** +1 from Phase 24 (93). Phase 25 B extracted the
Cmd-K palette command builder + topbar material-options mapper from
App.tsx into `frontend/src/state/paletteCommands.ts`. App.tsx
shrank from **1498 → 1446 LOC (-52, -3.5%)**.

**Honest miss:** Blueprint target was <1300 LOC (-198 from baseline);
delivered -52. Full reducer / view-model extraction (the candidate-
spine derived strings at lines 527-720, the trustStrip and
trustSections at lines 829-940) is a multi-slice refactor recorded
as a Phase 26 honest gap. Slice B shipped the palette wedge as a
proof-of-concept; the bigger wedges deferred.

Evidence:
- `wc -l frontend/src/App.tsx` → 1446 (post-Phase-25-B).
- `wc -l frontend/src/state/paletteCommands.ts` → 109.
- `Phase25B_palette_extraction.test.tsx` — 10 tests pin the
  builder contract: command-id order, handler wiring, purity,
  extension via materials list growth.

Gap to 99: full App.tsx decomposition (trustStrip/trustSections
builder, candidate-spine view-model, useReducer for scenario
state).

### Dim 2 — Industrial-CAE comparison (0-100)

**Score: 87/100.** +2 from Phase 24 (85). Two industrial-CAE
pattern matches landed in Phase 25:
1. **Basic / Advanced mode toggle** — every commercial CAE has
   this affordance (ANSYS Workbench "Simplified" / Abaqus/CAE
   "Basic interface" / SOLIDWORKS Simulation "Easy" mode).
2. **Probe-list CSV export** — standard reviewer-flow handoff
   from CAE to spreadsheet (Excel / numerical post-processor).
   Industry default is csv with header row + per-entry rows.

Evidence:
- `UiModeToggle.tsx` segmented control with aria-radiogroup
  semantics.
- `ProbeListPanel` "Export CSV" button visible whenever count
  > 0; `serializeProbeListAsCsv` RFC-4180 quoted output.

Gap to 99: still no iso-surface rendering, no streamlines, no
animation of failure sequence, no fracture-mechanics overlay.

### Dim 3 — Visual polish (0-100)

**Score: 82/100.** +2 from Phase 24 (80). Phase 25 D ships the
first motion polish: OnboardingTour fades + slides in (200ms
ease-out) on first render, respecting `prefers-reduced-motion`.
The UiModeToggle segmented control has measured polish (blue-on-
dark active state, monospace-feel letter-spacing).

**Honest scope reduction within this dim:** Apple-tier polish
items from the blueprint (probe-list row add/remove animations,
custom threshold-filter slider tracks with gradient matching the
legend, hover preview on section-cut position slider) are NOT
shipped. Phase 26 punchlist.

Evidence:
- `@keyframes fm04a-onboarding-fade-slide-in` + the
  `prefers-reduced-motion: reduce` media query.
- `Phase25D_polish_csv_export.test.tsx` pins the keyframes
  injection + animation class on the card.

Gap to 99: probe-list row easing, custom slider tracks,
hover-preview, viewport-mode transitions.

### Dim 4 — Information density vs clarity (0-100)

**Score: 83/100.** +1 from Phase 24 (82). UiModeToggle is a
compact 2-segment control (~80 px wide); Basic mode in turn
reduces the probe-list panel from the layout when not pinned.
Net: more affordances available without crowding the default view.

Evidence:
- UiModeToggle mounted next to the panel title chip; no new
  vertical space consumed.
- Basic mode default hides the probe-list (cleanest first-load
  visual; matches the novice path described in UX Dim 5).

Gap to 99: topbar still busy (multiple Phase 22-23-24 additions);
threshold filter row still in both modes; section-cut row still
in both modes.

### Dim 5 — 3D viewport depth & interactivity (0-100)

**Score: 86/100.** Held flat from Phase 24 (86). No new viewport
interactivity in Phase 25 (Slice C gates panel visibility; Slice
D adds CSV export at the panel chrome; neither touches the WebGL
viewport itself).

Gap to 99: see Phase 22/23/24 list — iso-surfaces, vectors, real
WebGL E2E tests (still mock-only since Phase 21 C, 5 phases open),
animation-of-failure overlay.

## Composite

| Dim | Phase 24 | Phase 25 | Delta |
|---|---|---|---|
| LOC discipline | 93 | 94 | +1 |
| Industrial CAE comparison | 85 | 87 | +2 |
| Visual polish | 80 | 82 | +2 |
| Information density | 82 | 83 | +1 |
| 3D depth & interactivity | 86 | 86 | 0 |
| **UI composite** | **85.2** | **86.4** | **+1.2** |

**UI axis: 86.4/100.** Inside blueprint band (86-87) at the MID-LOW
end. The +1.2 lift is driven by industrial-CAE pattern parity
(Basic mode + CSV) and the first tour motion polish; LOC discipline
moved only modestly because Phase 25 B was a proof-of-concept
extraction (full decomposition deferred).

Not signed validation; not benchmark agreement.
