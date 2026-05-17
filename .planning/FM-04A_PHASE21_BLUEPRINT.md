# FM-04a Phase 21 — Validation depth + WebGL viewport · Blueprint

**Stamp:** drafted 2026-05-17 (Phase 20 closed at composite 64.3/100 ·
`cfcc73b`). Authorization: user direct, identical Chinese directive as
Phase 18/19/20.

**Honest contract (carried verbatim from Phase 18+19+20):**
* No rubric reshaping.
* No score gaming.
* If the composite lands at 72/100, the artifact says 72, not 99.
* Iteration is capped at v2.3 round-cap = 3.

## 1. Thesis

Phase 18 built the Tier 2 parts bin. Phase 19 ran the first car off
the assembly line. Phase 20 ended the single-element-coupon regime
and proved the meshed pipeline runs end-to-end. **Phase 21 closes
two open promises:**

1. The two new candidate cases registered in Phase 20 (`plate-with-
   hole-candidate` + `cantilever-beam-candidate`) graduate from
   `tier_1_candidate` to `tier_2_validated` via analytical
   cross-check runners — bringing the validated count from 1 to 3.
2. The frontend stops being a "dashboard with no 3D viewport"
   limitation that has held UI Dim 5 at the 4/20 floor since Phase 18
   audit started. A minimal WebGL viewport ships, reading the same
   `result_mesh.json` payload the SVG panel already consumes, and
   rendering with orbit/pan/zoom + stress-colored faces.

## 2. Honest score projection vs Phase 20 baseline

| Dimension | Phase 20 R2 | Phase 21 projection | Lift mechanism |
|---|---|---|---|
| UX | 70/100 | 76-82 | T4 material_reference surfacing + T5 stress contour via WebGL viewport (3D becomes "actually clickable + readable" not "SVG with a legend") |
| FEA | 57/100 | 65-72 | 2 new tier_2_validated promotions (Cross-check rigor 11→14-15) + plasticity NLGEOM E2E pin (Solver coverage 12→14; Production-gap +1 for honest nonlinear capability) |
| UI | 66/100 | 74-82 | WebGL viewport lifts Industrial-CAE 4→10-12 + Data viz 13→17-18; tab-body extractions trim App.tsx by ~250 LOC |
| **Composite** | **64.3** | **72-78** | Still NOT 99. 99 needs contact + full plasticity sweep + multi-material library + advanced viz (animation, BC arrows). Months. |

The projection assumes WebGL ships cleanly. If three.js integration
hits a wall I haven't anticipated, the UI lift falls to +2-4 instead
of +8-12 and composite lands ~68 instead of 72-78. The FINAL.md will
record actuals verbatim either way.

## 3. Slice breakdown

### Slice A — Cantilever + Kirsch runners → 2 tier_2_validated flips

**Goal:** Use Phase 20 C's `run_tier2_meshed_pipeline` to land
analytical cross-check runners for both candidate cases registered
in Phase 20 B + C, then verify-write the verdicts.

**Deliverables:**

**A1 — cantilever_runner.py:**
* `backend/app/services/cross_check/cantilever_runner.py` (NEW):
  composes a multi-element cantilever via a `.geo` file (rectangular
  prism, slender L/h ≥ 10) → real gmsh → C3D4 tets → ccx → reads tip
  z-displacement → compares to PL³/(3EI) analytical from Phase 20 B.
* Honest tolerance: 10-15% (multi-element C3D4 vs Euler-Bernoulli;
  C3D4 has shear locking, ~10-15% under-prediction is typical).
  Document this in the module docstring. Tightening below 10% needs
  C3D10 (quadratic tets) or C3D8I (incompatible-mode hexes) — both
  Phase 22+ scope.
* `golden_samples/cantilever-beam-candidate/data/cantilever.geo`
  (NEW): the .geo source for the canonical L=1 m, h=b=0.1 m cantilever.
* Writes `cross_check_verdict.yaml` on PASS; `_claim_tier.py` overlay
  auto-promotes.

**A2 — plate_kirsch_runner.py:**
* `backend/app/services/cross_check/plate_kirsch.py` (NEW): pure
  function `compute_kirsch_peak_stress(*, far_field_pa, hole_radius_m,
  plate_half_width_m) -> float` returning `K · σ_∞` where K is the
  stress concentration factor. For an infinite plate K=3.0 (the
  classical Kirsch result). For finite plates with hole-to-width
  ratio r/W, K rises slightly; tabulated correction from Roark's
  eq. 17.1-1.
* `backend/app/services/cross_check/plate_kirsch_runner.py` (NEW):
  composes the plate-with-hole INP from Phase 20 C → real gmsh +
  real ccx → reads max σ_xx along the hole edge → compares to
  K · σ_∞.
* Honest tolerance: 15-20% for a single linear-tet mesh at the hole
  edge (high-gradient region needs refinement; even Abaqus with C3D8
  needs 4× refinement at the hole to recover K=3 to within 5%).
  Document this. Phase 22+ scope = adaptive refinement.

**Tests (≥18 total):**
* (T:-3) Kirsch formula pin on K=3 known input.
* (T:-3) Finite-plate K correction tabulated values pinned.
* (Cantilever) Tolerance band documented + verdict YAML round-trip.
* (Kirsch) Tolerance band documented + verdict YAML round-trip.
* (B) BOTH cases have `cross_check_verdict.yaml` after Phase 21 A
  ships; `CLAIM_TIER_REGISTRY` overlay promotes them to
  `tier_2_validated`.
* (`requires_solver`) Real gmsh + real ccx + verdict PASS pins for
  both — the load-bearing E2E.

**Anti-gaming guards:**
* **A:-3** the verdict YAML schema is the same SSOT used by Phase 19
  B + the promotion overlay; no parallel schema.
* **T:-3** if either runner's residual is OUTSIDE its honestly-
  documented tolerance, the verdict is FAIL (not silently widened
  to PASS).

**Honest budget:** ~350 LOC backend + ~400 LOC tests + 1 new .geo;
~2-2.5 hr.

---

### Slice B — Plasticity NLGEOM `requires_solver` E2E pin

**Goal:** Close the Phase 20 retro #3 item — Slice B shipped the
`*PLASTIC` keyword but no E2E test verifies ccx actually solves the
nonlinear problem under yielding load.

**Deliverables:**
* `backend/tests/test_phase21b_plasticity_nlgeom.py` (NEW, ≥4 tests):
  * `@pytest.mark.requires_solver` — load a single C3D8 hex of
    steel-S355 (with the EN 1993-1-5 bilinear curve) to a tip load
    ABOVE yield (≥ σ_y · A = 355 MPa · 0.01 m² = 3.55 MN). Verify
    ccx returncode 0. Read `.frd` → assert max σ_xx > σ_yield (so we
    know we're in the plastic region) AND the stress is bounded by
    the curve's ultimate stress + a tolerance (so we know ccx is
    actually using the hardening table, not still on the elastic
    branch).
  * Sanity: same geometry + steel WITHOUT the hardening curve →
    elastic-only run produces σ_xx that would be ABOVE yield (the
    linear-elastic solution overshoots; this proves the plastic run
    actually capped the stress).
* (M:-1) The test imports `app.services.materials.get_material(
  "steel-s355")` — does NOT inline the curve.

**Anti-gaming guards:**
* **T:-3** assert observed σ ≥ σ_y AND ≤ σ_u + 10% — verifies the
  plastic branch fired AND didn't blow past the hardening curve.

**Honest budget:** ~150 LOC tests; ~1 hr.

---

### Slice C — WebGL 3D viewport (three.js minimal)

**Goal:** The biggest single UI lever per the Phase 20 audit. The UI
agent's R1 report scored Dim 5 (Industrial-CAE comparison) at 4/20
floor because `grep -rn 'three|webgl|<canvas' frontend/src/` returned
zero hits. Lift it.

**Honest scope reduction up-front:** this is NOT "build an Abaqus
viewport in a session". The deliverable is a MINIMAL three.js view
that:
* Reads the same `result_mesh.json` payload the SVG panel consumes.
* Renders the static mesh (no animation in Phase 21) as a Three.js
  Mesh with deformed-node positions.
* Colors faces by stress field magnitude using the existing
  blue→green→orange gradient from the SVG legend (Phase 19 D).
* Supports orbit (mouse drag), pan (right-click drag), zoom (wheel).
* Sits alongside the SVG panel as a SECOND visualization, not a
  replacement (so the SVG fallback stays when WebGL fails).

**Deliverables:**
* `frontend/package.json`: add `three` + `@types/three` dependencies
  (peer-deps already cover React 19; three.js 0.160+ is the target
  release — small bundle, well-tested with OrbitControls).
* `frontend/src/components/ResultMeshWebGLViewport.tsx` (NEW, ~250
  LOC): the minimal viewport. Props: `payload`, `summary` (same
  shape the SVG panel consumes), `selectedFrame`. Internals:
  - `useEffect` initializes a Three.js Scene + PerspectiveCamera +
    WebGLRenderer + OrbitControls on the mounted `<canvas>`.
  - Builds a `BufferGeometry` from `payload.dynamicFrames[i].nodes`
    + `elements`. Volume elements (C3D8 hex / C3D4 tet) are exploded
    into their face triangles; the BufferGeometry's `color` attribute
    is set per-vertex using the same `valueMin / valueMax` gradient
    as the SVG path.
  - Re-builds the geometry when `selectedFrame` changes.
  - Disposes the renderer on unmount.
* `frontend/src/components/ResultMeshPlaybackPanel.tsx`: when WebGL
  is available (`window.WebGLRenderingContext` exists), mount the
  WebGL viewport above the existing SVG body; the SVG stays as the
  fallback. Add a small "WebGL / SVG" toggle so reviewers can compare.
* `frontend/test/Phase21C_webgl.test.tsx` (NEW, ≥8 tests):
  - Headless: mock the WebGL context (`HTMLCanvasElement.prototype
    .getContext('webgl')` returns a stub) and assert the viewport
    renders without throwing.
  - Color-gradient pin: at min/max stress, the per-vertex color
    matches the legend stops.
  - Fallback pin: with no WebGL context, the SVG body still mounts.

**Anti-gaming guards:**
* **A:-2** if Three.js or any dependency fails to import, the panel
  catches and falls back to SVG; never blank.
* **T:-3** the headless test pins the color-gradient SSOT match
  with the SVG legend so a future drive-by gradient change trips
  both surfaces in lockstep.

**Honest budget:** ~300 LOC frontend + ~200 LOC tests + 1 package add;
~3 hr. If three.js integration hits a wall, deliver the package +
component skeleton + tests as stubs, and downgrade the UI lift in
FINAL.md from +8 to +3.

---

### Slice D — Frontend polish: material_reference surfacing + tab extractions

**Goal:** Two independent UX/UI improvements that together should
deliver +2-4 on UX (material visibility) and +2-3 on UI (App.tsx LOC
reduction).

**Deliverables:**

**D1 — material_reference surfacing:**
* `frontend/src/App.tsx`: parse `data.material_reference` from the
  /solver/run response (route returns it now per Phase 20 A); append
  to the log surface OR display in a new compact panel below the
  "Run Solver" status. Goal: reviewer can SEE which material was
  actually used in the solver run, with the cited reference string.

**D2 — Tab body extractions:**
* `frontend/src/components/VisualTabPanel.tsx` (NEW): extract the
  `activeTab === 'visual'` block (currently lines ~1645-1810 of
  App.tsx). The block mounts CohortDashboardPanel + CohortSubstantiationPanel
  + CaseCompletenessCard + CandidateCasePicker + AcceptancePacketPanel
  + ConvergenceStudyViewer + CaseComparisonPanel + … (heavy panel
  cascade).
* `frontend/src/components/NarrativeTabPanel.tsx` (NEW): extract the
  `activeTab === 'report'` block.
* `frontend/src/components/ExplorationTabPanel.tsx` (NEW): extract
  the `activeTab === 'explore'` block.
* Target App.tsx ≤1500 LOC (currently 2006). Honest stretch: ≤1700.

**Tests:**
* `frontend/test/Phase21D_polish.test.tsx` (≥6 tests):
  - material_reference surfaces in the rendered DOM after a fake
    Run Solver response.
  - VisualTabPanel mounts its expected child panel testids.
  - NarrativeTabPanel + ExplorationTabPanel same.

**Honest budget:** ~400 LOC frontend + ~250 LOC tests; ~2 hr.

---

### Slice E — 3 testing agents + honest scoring + closure

**Goal:** Same framework. Honest projection 72-78. APPROVE iff
composite ≥ 99 AND each ≥ 99 AND no axis < 95%.

**Deliverables:**
* `.planning/phase21_audit_reports/{UX,FEA,UI,FINAL}.md` (R1
  baseline; R2 / R3 only if a single spike-class fix could
  meaningfully lift the lowest axis).
* `.planning/retrospectives/fm04a_phase21_validation_depth_webgl.md`.
* `.planning/STATE.md` refresh.

## 4. Hard constraints (preserved verbatim from Phase 18-20)

* HF1.7a signed-registry hard-stop
* HF1.7b `*-candidate` carve-out
* HF1.8 path-guard self-protection
* tmp_path-only test snapshot writes (the new `cantilever.geo` goes
  inside the EXISTING `cantilever-beam-candidate/data/` dir; no new
  registry entries).
* No push, no PR, no Linear / Notion writes
* Phase 1-20 chain preserved (additive only)

## 5. Acceptance criteria

* [ ] Slice A: 2 new `tier_2_validated` flips, both verdict-file-
      driven; total tier_2_validated count = 3.
* [ ] Slice B: ccx NLGEOM run verified with σ in the plastic regime.
* [ ] Slice C: WebGL viewport mounts, orbits, colors by stress. SVG
      fallback intact.
* [ ] Slice D: App.tsx ≤ 1700 LOC; material_reference visible in UI.
* [ ] Slice E: 3-axis honest composite documented; if < 99 the gap
      is named verbatim.
* [ ] All hard constraints PASS.

## 6. Phase 21 thesis

Phase 18 was about parts. Phase 19 was about the first car. Phase 20
was about the assembly line scaling up. **Phase 21 is about the
gauges:** the analytical-vs-numerical cross-check turns Phase 20's
two new candidates into actual validated results (gauge reads
"green"), and the WebGL viewport gives the reviewer eyes on the
solve they just ran.

99 is the destination. Phase 21 puts us within striking distance
without faking the speedometer.
