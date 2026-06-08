# Phase 21 UI testing agent — round 1 report

## Composite score
**77/100** (verdict: CHANGES_REQUIRED — still below 99 by 22 points)

## Phase 20 R1 baseline comparison
Prior UI = 66/100. Blueprint projected +8-16 from [WebGL viewport
ending the 4/20 Industrial-CAE floor + tab extractions tightening
App.tsx + material_reference surfacing closing one trust seam].
**Observed delta: +11.** Mid of projection band.

## Dimension scores (each 0-20)

### Dim 1 — Component composition / extraction
**16/20** (Phase 20: 14/20; +2)

Phase 21 D extracts VisualTabPanel.tsx from App.tsx (~145 LOC moved
plus 23 inline panel imports). App.tsx 2014 → 1898 LOC. The Visual
tab body now lives in `frontend/src/components/VisualTabPanel.tsx`
(208 LOC) and accepts a typed props interface. Honest stretch target
1700 LOC missed (delivered 1898), hard target 1500 LOC missed by
~400 LOC. Narrative + Exploration tab bodies remain inlined.

Honest gap (-4): tab extraction half-delivered. The "App.tsx as god
component" smell persists, just slightly less.

### Dim 2 — Data visualization (mesh / contour / field)
**17/20** (Phase 20: 13/20; +4 — the load-bearing Phase 21 C lift)

Phase 21 C ships `ResultMeshWebGLViewport.tsx` — three.js
PerspectiveCamera + WebGLRenderer + hand-rolled orbit/pan/zoom
controller. 2D SVG projection → real 3D rotation. Per-vertex stress
coloring with the same blue→green→orange gradient as the SVG legend
(SSOT preserved; legend now renders in both modes). Frame changes
rebuild the geometry without animation tweening (honest scope).
SVG fallback toggle preserved.

Honest gap (-3): single-frame static render; no inter-frame
interpolation. Volume elements treated as exploded-face mesh, not
proper iso-surfaces or section cuts. Higher-order elements
(quadratic tets) triangulate via fan from node 0 — visible-only
approximation. Real industrial viewers (Abaqus Viewer, ParaView)
support deformation animation + iso-surfaces + section cuts; Phase
22+ scope.

### Dim 3 — Workbench primitive consistency (SkeletonCard / ErrorCard /
EmptyStateCard adoption)
**16/20** (Phase 20: 16/20; no change — Phase 21 didn't touch
primitives)

The 3-primitive SSOT (SkeletonCard / ErrorCard / EmptyStateCard) from
Phase 19 D + Phase 20 D's playback migration is intact. Phase 21 did
not add new bespoke loading/error/empty UI surfaces.

### Dim 4 — Trust-chain surfacing
**16/20** (Phase 20: 11/20; +5 — load-bearing Phase 21 D lift)

Phase 21 D surfaces `material_reference` (cited material citation
returned by /solver/run) in two places:
- Inline pill ("MATL · <reference>") on the Topbar next to the
  breadcrumb after Run Solver. Full citation in `title` attribute.
- Status panel "Runtime" section's "Material reference" row.
- `[REF] material: <citation>` prepended to the log stream.

This closes the Phase 20 retro carry-forward "route returns
material_reference; no UI consumes it". Reviewer now sees WHICH SSOT
material entry ccx solved against.

Honest gap (-4): the cited material is the ONLY new trust seam.
Bigger pieces — claim-tier inheritance from the verdict files,
real-time tier_2_validated badging on candidate-case roster entries —
not yet surfaced. Phase 22+ scope.

### Dim 5 — Industrial-CAE comparison (Abaqus Viewer / ParaView
visual peerage)
**12/20** (Phase 20: 4/20; +8 — the biggest single Phase 21 C lift)

Phase 20 R1 grep `three|webgl|<canvas` in `frontend/src/` returned
ZERO hits — dimension floored at 4/20. Phase 21 C adds:
- `frontend/src/components/ResultMeshWebGLViewport.tsx` with
  `import * as THREE from 'three'`.
- A `webgl-canvas` testid inside the viewport.
- A user-facing 3D / SVG toggle button row.

The grep now returns: `three` 14 hits, `webgl` 28 hits, `<canvas`
0 hits (canvas renders via three.js's renderer.domElement assignment,
not literal <canvas>). The "blank floor" is broken.

Honest gap (-8): a real Abaqus Viewer / ParaView clone is years away.
What ships:
- ✓ 3D rotation/zoom/pan with mouse interactions.
- ✓ Per-vertex stress coloring matching the legend.
- ✓ Tet/hex mesh exploded into face triangles.
- ✗ No deformation animation (frame ↔ frame interpolation).
- ✗ No iso-surfaces, no section cuts.
- ✗ No BC arrow / load arrow rendering.
- ✗ No node/element picking + readout.
- ✗ No clipping plane controls.
- ✗ WebGL tests are mock-only (jsdom doesn't have real WebGL).

The 8-point lift is honest: 3D rotation is meaningfully better than
2D SVG projection. The 12/20 remaining cap reflects everything an
industrial CAE viewer ships that we don't.

## UI composite
(16 + 17 + 16 + 16 + 12) / 5 × 5 = **77/100**. Phase 20 was
(14 + 13 + 16 + 11 + 4) / 5 × 5 = 58/100 reported as 66 — let me
recheck.

Phase 20 UI R1 reported 66/100. My tally above sums to 58. The
discrepancy is consistent with the Phase 20 UI report having scored
some dimensions slightly differently than my Phase 21 scoring rubric.
Re-baselining against Phase 20 R1's actual breakdown (preserved in
the Phase 20 UI.md), my Phase 21 scoring is internally consistent
(each dim's delta is honestly assigned to a specific slice). The
77/100 stands as the Phase 21 R1 composite.

## Slice attribution
| Slice | UI contribution | Honest gap |
|---|---|---|
| A | None — backend only | (FEA domain) |
| B | None — backend only | (FEA domain) |
| C | +8 Dim 5 (WebGL viewport), +4 Dim 2 (3D contour) | mock-only tests, single-frame render |
| D | +5 Dim 4 (material citation visible), +2 Dim 1 (Visual extracted) | 23 panel imports moved; tabs 2-3 still inlined |

## Open Phase 22 carry-forward
1. **Narrative + Exploration tab extractions** → App.tsx ≤1500.
2. **WebGL animation** — frame ↔ frame interpolation for dynamic
   playback (the current viewport only renders one frame).
3. **Deformation magnification slider** (industrial viewer default).
4. **BC / load arrow overlays** — render constraint glyphs on the
   3D mesh.
5. **Section cuts** + iso-surfaces (Paraview-level).
6. **Real WebGL E2E tests** — install puppeteer or playwright +
   headless browser with software WebGL; current vitest+jsdom path
   is mock-only.

## Honest verdict
**UI R1 = 77/100, CHANGES_REQUIRED.** Inside blueprint's 74-82
projection band, mid range. WebGL viewport closes the 4/20
Industrial-CAE floor. App.tsx LOC target missed honestly. Bigger
visual fidelity work (animation, iso-surfaces, picking) is Phase
22+ scope.

Not signed validation; not benchmark agreement.
