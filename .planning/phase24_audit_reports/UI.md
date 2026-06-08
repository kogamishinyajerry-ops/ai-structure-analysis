# Phase 24 — UI audit (Round 1)

> **Frame:** Tier 1 / Tier 2 engineering candidate; not signed
> validation; not benchmark agreement. Phase 23 baseline UI = 83.4/100.
> Blueprint UI projection: 84-86 (mid 85.0).

## Dimensions

### Dim 1 — Composition-root LOC discipline (0-100)

**Score: 93/100.** +3 from Phase 23 (90). Phase 24 C extracted
pure-function helpers from `ResultMeshWebGLViewport.tsx` into three
submodules. The orchestrator file shrank from ~930 LOC (start of
Phase 24) to **581 LOC (-349 LOC, -37.5%)**. ZERO behavior change
— all 336 frontend tests pass without modification.

The Phase 22 baseline was 92 (App.tsx 1498 LOC unchanged + viewport
675 LOC); Phase 23 regressed to 90 (viewport grew to ~820); Phase
24 reverses past Phase 22 baseline to **93** because the new
submodules are individually small (264 / 125 / 19 LOC) and
focused (geometry / raycaster / animation).

Evidence:
- `wc -l frontend/src/components/ResultMeshWebGLViewport.tsx` → 581
- `wc -l frontend/src/components/viewportGeometry.ts` → 264
- `wc -l frontend/src/components/viewportRaycaster.ts` → 125
- `wc -l frontend/src/components/viewportAnimation.ts` → 19
- `Phase24C_viewport_split.test.tsx` — 12 tests pin C:-3
  anti-gaming guard: same function reference imported through
  orchestrator + submodule is identity-equal (re-export, not
  duplicate).

Gap to 99: `App.tsx` is still 1498 LOC; further composition-root
work would extract its scenario-state reducer and topbar config
into dedicated modules.

### Dim 2 — Industrial-CAE comparison (0-100)

**Score: 85/100.** +2 from Phase 23 (83). Phase 24 D's multi-node
probe list is a standard industrial-CAE pattern (probe list /
sensor list panel in ANSYS Mechanical, Abaqus/CAE, HyperMesh).
Phase 24 B's onboarding tour is also a standard CAE-tool first-run
walkthrough pattern (matches the "Welcome to ANSYS Workbench" /
"Abaqus first-time tour" affordances).

Evidence:
- ProbeListPanel table with 6 columns (Node / X / Y / Z / Value /
  remove) is the canonical CAE probe-list layout.
- OnboardingTour 4-step overlay with progress dots matches the
  ANSYS Workbench / SolidWorks "Tip of the Day" pattern.

Gap to 99: still no iso-surface rendering, no streamlines, no
animation of failure sequence, no fracture-mechanics overlay.

### Dim 3 — Visual polish (0-100)

**Score: 80/100.** +2 from Phase 23 (78). Phase 24 B's
OnboardingTour overlay has measured polish: blue-accent step
indicator, gray progress dots, scoped color palette
(`#2563eb` accent + `#94a3b8` muted gray), system-font stack.
Phase 24 D's ProbeListPanel uses a darker glass panel
(`rgba(15, 23, 42, 0.88)` + `1px solid rgba(148, 163, 184, 0.25)`)
matching the existing reviewer-overlay aesthetic.

Evidence:
- OnboardingTour: `box-shadow: '0 24px 48px rgba(15, 23, 42, 0.18)'`
  + 12px border-radius card design.
- ProbeListPanel: monospace number columns for value comparison,
  uppercase letter-spaced section labels.

Gap to 99: no animation on tour appear/disappear, no easing on
probe-list row add/remove, no custom slider tracks for threshold
filter, no hover preview on section-cut position, no Apple-tier
polish pass.

### Dim 4 — Information density vs clarity (0-100)

**Score: 82/100.** +1 from Phase 23 (81). Phase 24 D probe-list
table packs 6 columns of comparison data into a tight ~150px row;
header chrome is uppercased + muted; remove button is a tiny "×"
not a full label. Information density rises without crowding the
default no-probe state (the empty-state message is brief).
Phase 24 B onboarding tour is a modal overlay; it doesn't compete
for vertical space at default.

Evidence:
- ProbeListPanel table cells use `padding: '5px 6px'` + 0.72rem
  monospace — visually compact.
- Empty state: 1 short sentence + italic muted text.

Gap to 99: topbar still busy (multiple Phase 22-23 additions);
column count in the probe panel reaches 6 when 4 is the typical
sweet spot; legend-row stacking is now 3+ rows tall.

### Dim 5 — 3D viewport depth & interactivity (0-100)

**Score: 86/100.** +1 from Phase 23 (85). Phase 24 D adds a 9th
distinct reviewer affordance on the viewport: pinning. Phase 24 C's
file split doesn't change the interactivity surface but improves
maintainability — easier to extend the viewport going forward.

Evidence:
- 6 mouse interactions (drag / right-drag / wheel) + 1 click for
  pick + 1 key for Escape + 1 pin button = 9 distinct reviewer
  affordances.

Gap to 99: iso-surfaces, vectors, real WebGL E2E tests (Phase 21
carry-forward still open), animation-of-failure overlay.

## Composite

| Dim | Phase 23 | Phase 24 | Delta |
|---|---|---|---|
| LOC discipline | 90 | 93 | +3 |
| Industrial CAE comparison | 83 | 85 | +2 |
| Visual polish | 78 | 80 | +2 |
| Information density | 81 | 82 | +1 |
| 3D depth & interactivity | 85 | 86 | +1 |
| **UI composite** | **83.4** | **85.2** | **+1.8** |

**UI axis: 85.2/100.** Inside blueprint band (84-86) at the
MID-HIGH end. The +1.8 lift is driven by the viewport-file split
LOC reversal (+3), industrial-CAE pattern parity from multi-probe
+ tour (+2), and visual polish on tour overlay (+2). Documented
verbatim per 绝对诚实客观.

Not signed validation; not benchmark agreement.
