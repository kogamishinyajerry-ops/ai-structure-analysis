# Phase 22 — UI audit (Round 1)

> **Frame:** Tier 1 / Tier 2 engineering candidate; not signed
> validation; not benchmark agreement. Phase 21 baseline UI = 77/100.
> Blueprint UI projection: 79-83 (mid 81).

## Dimensions

### Dim 1 — Composition-root LOC discipline (0-100)

**Score: 92/100.** Phase 21 score was 70 (App.tsx at 1898 LOC,
blueprint target ≤1700 honest / ≤1500 hard, both missed). Phase
22 C delivered the named extractions (NarrativeTabPanel +
ExplorationTabPanel) plus follow-on extractions
(OperatorStatusPanel + TabButton) and a types-module split
(`frontend/src/types/AppTypes.ts`). App.tsx landed at **1498 LOC**
— inside the ≤1500 hard target.

Evidence:
- `wc -l frontend/src/App.tsx` → 1498.
- Phase 21 baseline: 1898. Reduction: 400 LOC.
- 4 new components + 1 types module + 9 Phase 22 C tests.

Gap to 99: App.tsx still has ~1000 LOC of mixed state +
useEffects + handlers. A reducer-based state machine or
useReducer + state-slice files would buy another ~300-500 LOC,
but that's structural refactor (Phase 23+).

### Dim 2 — Industrial-CAE comparison (0-100)

**Score: 78/100.** +1 from Phase 21 (77). The Phase 22 B section-
cut + deformation magnification controls are standard fare for
industrial CAE post-processors (ANSYS Mechanical, Abaqus/CAE,
HyperMesh all surface these controls in the viewport sidebar).
Their presence in our WebGL viewport closes a "missing standard
feature" gap reviewers would notice immediately.

Evidence:
- Section-cut: industrial CAE always has a "clip section" toggle.
- Deformation magnification (1× → 100×): standard slider, often
  named "scale factor" in commercial tools.
- The legend units suffix ('Pa' default) matches commercial-CAE
  conventions (CalculiX / ANSYS / Abaqus all surface units in
  field-value legends).

Gap to 99: still no iso-surface rendering, no streamlines/vectors,
no node-picking with field probe, no annotation tools, no
multi-result comparison overlay, no orthogonal-axis snap views
(XY/YZ/XZ presets). These are commercial-tier features that close
multi-phase scope.

### Dim 3 — Visual polish (0-100)

**Score: 77/100.** Held flat from Phase 21 (77). Phase 22 didn't
deliver Apple-tier UI polish (no animations, transitions, hover
states beyond the existing ones). The depth-control row is
functional but utilitarian; reviewers will perceive it as "a
control panel" not "a beautiful UI surface."

Evidence:
- `ViewportDepthControls` in `ResultMeshPlaybackPanel.tsx` —
  vanilla `<input type="range">` and `<select>` styling, no
  custom slider track, no easing on toggle expansions.

Gap to 99: needs custom CSS-driven slider rails, motion easing
on section-cut activation, hover preview of cut-plane position,
animated transitions between viewport modes (3D ↔ SVG). All
Phase 23+ polish work.

### Dim 4 — Information density vs clarity (0-100)

**Score: 79/100.** +2 from Phase 21 (77). The legend now carries
units + field-component label (e.g. "Von Mises Pa") which gives
reviewers more signal per pixel. The depth control row sits in
its own auto-row above the viewport, separating "what I'm looking
at" (viewport) from "how I'm looking" (controls).

Evidence:
- `frontend/src/components/ResultMeshPlaybackPanel.tsx` —
  `legend-field-component` chip surfaces field label; legend min/
  max carry unit suffix.
- Gridlayout `gridTemplateRows: 'auto auto 1fr auto'` separates
  toggles / depth controls / viewport / playback.

Gap to 99: the OperatorStatusPanel is still dense (3 grids of
status tiles); the Topbar is now busier (analysis + material +
Run Solver + Stop + Copilot toggle = 5 elements on the right).

### Dim 5 — 3D viewport depth & interactivity (0-100)

**Score: 81/100.** +6 from Phase 21 (75). The WebGL viewport now
has orbit + pan + zoom (Phase 21 C) + animation interpolation +
section cut + deformation magnification (Phase 22 B). Reviewers
have meaningful 3D engagement.

Evidence:
- `ResultMeshWebGLViewport.tsx` — 6 mouse interactions (drag,
  right-drag, wheel) + section + magnification + animation.
- 14 tests cover the new depth behaviors.

Gap to 99: see Dim 2 — iso-surfaces, vectors, picking, annotation.
Plus, the WebGL canvas is still tested via jsdom mocks — no real
headless-WebGL coverage via puppeteer/playwright. Phase 21's
"Real WebGL E2E tests" punchlist item remains open.

## Composite

| Dim | Phase 21 | Phase 22 | Delta |
|---|---|---|---|
| LOC discipline | 70 | 92 | +22 |
| Industrial CAE comparison | 77 | 78 | +1 |
| Visual polish | 77 | 77 | 0 |
| Information density | 77 | 79 | +2 |
| 3D depth & interactivity | 75 | 81 | +6 |
| **UI composite** | **75.2** | **81.4** | **+6.2** |

**UI axis: 81.4/100.** Inside blueprint band (79-83) at the mid.
LOC discipline lift was the single biggest contributor; the
WebGL viewport gains contributed second-most. Visual polish and
industrial-comparison feature parity remain the dominant gaps to
99.

Not signed validation; not benchmark agreement.
