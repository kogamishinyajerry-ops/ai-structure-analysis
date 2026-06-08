# Phase 23 — UX audit (Round 1)

> **Frame:** Tier 1 / Tier 2 engineering candidate; not signed
> validation; not benchmark agreement. Phase 22 baseline UX = 79.6/100.
> Blueprint UX projection: 82-85 (mid 83.5).

## Dimensions

### Dim 1 — Reviewer flow ergonomics (0-100)

**Score: 86/100.** +5 from Phase 22 (81). Phase 23 C's node-picking
with HUD overlay is a major reviewer-flow lift: a reviewer can now
click a node and read its label + xyz coords + field value without
leaving the viewport. This was the #1 industrial-CAE feature gap
named in Phase 21 + Phase 22 finals.

Evidence:
- `frontend/src/components/ResultMeshWebGLViewport.tsx` —
  THREE.Raycaster wired to a click handler with 4-px click-vs-drag
  threshold; HUD overlay (testid `webgl-picked-node-hud`) renders
  on pick.
- `frontend/test/Phase23C_node_picking.test.tsx` — 8 tests pin the
  findClosestNode + fieldValueAtNode helpers including the C:-2
  anti-gaming guard (shuffled node labels return actual labels,
  not array indices).

Gap to 99: still no node-by-label search, no multi-pick / probe
list, no comparison mode (probe node A vs node B). Phase 24+ scope.

### Dim 2 — Animation + dynamic engagement (0-100)

**Score: 84/100.** Held flat from Phase 22 (84). Phase 23 didn't
add animation features. The Mises/component switcher (Slice B) is
a stationary-data feature, not a dynamic one. Threshold filter
(Slice D) doesn't change animation behavior.

Gap to 99: see Phase 22 list (no playback speed, no scrub-to-time,
no keyboard shortcuts, no reverse).

### Dim 3 — Cognitive load on first open (0-100)

**Score: 75/100.** -1 from Phase 22 (76). Honest miss: Phase 23
added MORE controls to the viewport (component switcher dropdown,
threshold filter row, node-pick HUD). A first-time reviewer has
even more to take in. Mitigations: collapsed-by-default
(threshold filter off; HUD hidden until pick); but the legend
dropdown is always visible.

Evidence:
- Three new control surfaces added in Phase 23 B/C/D; no
  onboarding tour added.

Gap to 99: needs progressive disclosure, onboarding tour, or a
"basic mode / advanced mode" toggle.

### Dim 4 — Error-recovery clarity (0-100)

**Score: 79/100.** +1 from Phase 22 (78). Phase 23 C's HUD
gracefully handles the "field value not available" case (returns
`null`, conditional render hides the field line). Phase 23 B's
disabled dropdown when tensor absent prevents a silent zero-fill
crash. Both are recovery-clarity wins.

Evidence:
- `fieldValueAtNode` returns null when no element references the
  picked node; HUD shows label + coords without a value line.
- `componentValue(null, ...)` returns fallback; dropdown disabled
  state prevents user-driven invalid input.

Gap to 99: see Phase 22 list (WebGL context loss, PDF export
failure modes, retry buttons).

### Dim 5 — Novice usability (0-100)

**Score: 80/100.** +1 from Phase 22 (79). The Mises switcher
helps novices: "what's the field?" becomes "what's the dropdown
saying?" instead of being implicit. Threshold filter has good
labels (min ≥ X / max ≤ Y) but the IN/OUT button could be more
explicit ("inside range" vs "outside range").

Gap to 99: still no novice-mode, no inline help, no first-run
walkthrough.

## Composite

| Dim | Phase 22 | Phase 23 | Delta |
|---|---|---|---|
| Reviewer flow | 81 | 86 | +5 |
| Animation engagement | 84 | 84 | 0 |
| Cognitive load | 76 | 75 | -1 |
| Error recovery | 78 | 79 | +1 |
| Novice usability | 79 | 80 | +1 |
| **UX composite** | **79.6** | **80.8** | **+1.2** |

**UX axis: 80.8/100.** Inside blueprint band (82-85) at the LOW end
(below). The cognitive-load regression (-1) is the honest cost of
adding three new control surfaces in one phase; the reviewer-flow
gain (+5) outweighs it numerically but the phase delivered less UX
lift than projected. Documented verbatim per 绝对诚实客观.

Not signed validation; not benchmark agreement.
