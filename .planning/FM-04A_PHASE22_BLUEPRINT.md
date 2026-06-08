# FM-04a Phase 22 — Element fidelity + viewport depth + LOC discipline · Blueprint

**Stamp:** drafted 2026-05-17 (Phase 21 closed at composite 73.7/100 ·
`b6ecbe0`). Authorization: user direct, identical Chinese directive as
Phase 18/19/20/21.

**Honest contract (carried verbatim from Phase 18+19+20+21):**
* No rubric reshaping.
* No score gaming.
* If the composite lands at 79/100, the artifact says 79, not 99.
* Iteration capped at v2.3 round-cap = 3.

## 1. Thesis

Phase 18 built the Tier 2 parts bin. Phase 19 ran the first car off
the assembly line. Phase 20 ended the single-element-coupon regime.
Phase 21 added the gauges (analytical cross-checks + plasticity NLGEOM
+ 3D viewport). **Phase 22 polishes:**

1. **Element fidelity** — wire C3D10 quadratic tetrahedra into the
   gmsh + adapter path. Cuts Phase 21 A residuals roughly in half
   (cantilever 7% → ~3%, Kirsch 11% → ~5%) because shear locking on
   bending halves with quadratic elements.
2. **A second solver kind** — ship buckling Tier 2 E2E with the
   `*BUCKLE` CalculiX step + Euler critical-load analytical
   cross-check (P_cr = π²EI/L_eff²).
3. **Viewport depth** — frame-to-frame animation in the WebGL
   viewport (Phase 21 C was single-frame static); a section-cut
   clipping plane; deformation magnification slider.
4. **LOC discipline finally biting** — Narrative + Exploration tab
   body extractions land the App.tsx ≤ 1500 target Phase 21 D
   honestly missed.
5. **Material picker prominence** — Cmd-K palette entry +
   Topbar quick-swap so the picker isn't scroll-buried in the
   Visual tab.

## 2. Honest score projection vs Phase 21 baseline

| Dimension | Phase 21 R1 | Phase 22 projection | Lift mechanism |
|---|---|---|---|
| UX | 76/100 | 82-86 | T4 +2 (palette entry) + T5 +2-3 (animation + Mises selector) + T2 +1 (palette signoff entry) |
| FEA | 68/100 | 74-78 | Dim 2 +2 (buckling E2E) + Dim 3 +2-3 (C3D10 quad tets) + Dim 5 +2 (C3D10 production-grade) |
| UI | 77/100 | 83-87 | Dim 1 +2-3 (App.tsx ≤1500) + Dim 2 +2 (animation/section) + Dim 5 +2-4 (richer viewport interactions) |
| **Composite** | **73.7** | **80-84** | Still NOT 99. 99 needs contact + signed validation + multi-material plasticity sweep + transient dynamics — months. |

The projection assumes:
- C3D10 wiring lands cleanly (gmsh element type 11 parser + adapter
  output + ccx accepts).
- WebGL animation doesn't introduce regressions in the single-frame
  path.
- Tab extractions don't break any of the 250 frontend tests.

If any of these hit a wall, the FINAL.md records actuals verbatim.

## 3. Slice breakdown

### Slice A — Element fidelity: C3D10 + buckling

**Goal:** lift FEA dimensions through better elements + a second
real-solver E2E path.

**A1 — C3D10 quadratic tet adapter:**
* `backend/app/adapters/calculix/mesh_to_inp.py`:
  - Extend `_GMSH_TYPE_TO_CCX` with `11: ("C3D10", 10)` (gmsh type 11
    = 10-node quadratic tet).
  - `parse_gmsh_msh22` already iterates all element types via the
    table; one-line registry addition makes it parse C3D10 too.
  - `write_meshed_static_inp` already emits `*ELEMENT, TYPE=<ccx_type>`
    by lookup; C3D10 rows render via the same path.
* `backend/app/services/meshing/gmsh_runner.py`:
  - The `element_order` parameter is already there (Phase 18 C);
    `element_order=2` makes gmsh emit C3D10 instead of C3D4.
* `backend/app/services/tier2_pipeline.py:run_tier2_meshed_pipeline`:
  - Add an `element_order: int = 1` parameter so callers can opt
    into quadratic elements without breaking back-compat.
* `backend/app/services/cross_check/cantilever_runner.py` +
  `plate_kirsch_runner.py`: accept the `element_order` parameter,
  forward to the pipeline.

**A2 — Buckling Tier 2 E2E:**
* `backend/app/services/cross_check/buckling_euler.py` (NEW):
  pure-function `compute_euler_critical_load(*, length_m,
  youngs_modulus_pa, second_moment_m4, end_condition: Literal["pinned-
  pinned", "fixed-free", "fixed-pinned", "fixed-fixed"]) -> float`
  returning P_cr = π²·E·I·k² / L² where k is the effective-length
  factor (1.0 pinned-pinned, 0.5 fixed-fixed, etc.).
* `backend/app/services/cross_check/buckling_runner.py` (NEW): writes
  a static-prestress + `*BUCKLE` step INP, runs ccx, parses the
  lowest eigenvalue from the `.dat` file (or `.frd`), computes
  residual vs Euler analytical.
* The `*BUCKLE` step requires a unit-load prestress; the eigenvalue
  is the load multiplier. The runner applies F=1000 N axial, reads
  the lowest eigenvalue λ; P_cr_observed = λ · 1000 N.
* `golden_samples/euler-column-candidate/` (NEW): canonical slender
  column geometry, registered as `tier_1_candidate` in
  `_claim_tier.py`. The runner persists `cross_check_verdict.yaml`
  on PASS → promotion to tier_2_validated. **Validated count 3 → 4.**

**Tests (~25 total):**
* Euler formula pin at 4 end-conditions (closed-form values).
* C3D10 element-table registry pin.
* Gmsh element_order=2 forwards through pipeline (compose-only,
  doesn't require gmsh subprocess at unit-test time).
* `requires_solver` E2E pin: cantilever with element_order=2 →
  residual <5% (vs 6.88% on C3D4) — the load-bearing demonstration
  that quadratic tets cut shear locking.
* `requires_solver` E2E pin: buckling runner produces P_cr within
  10% of Euler analytical for a slender steel column.
* Post-promotion registry pin: validated count becomes 4 after
  euler-column-candidate's verdict YAML is on disk.

**Anti-gaming guards:**
* **A:-3** the buckling verdict YAML uses the same SSOT schema as
  Phase 19 B / 21 A; no parallel schema.
* **T:-3** the C3D10 cantilever runs sit at the EXACT same geometry
  as Phase 21 A (cl=0.015m); ONLY the element type changes. So the
  residual improvement is directly attributable to element order,
  not to a different mesh.

**Honest budget:** ~450 LOC backend + ~400 LOC tests; ~3 hr. If C3D10
runs into ccx parsing trouble or buckling eigenvalue convergence
issues, that slice is honestly scope-reduced in FINAL.md.

---

### Slice B — Viewport depth: animation + section + magnification

**Goal:** lift UI dimensions through richer viewport interactions
without a full ParaView rewrite.

**B1 — Frame animation:**
* `frontend/src/components/ResultMeshWebGLViewport.tsx`: add a
  `playing` prop + internal animation loop that interpolates node
  positions between adjacent frames at 60 fps via
  `requestAnimationFrame`. When `playing` is false, the geometry
  rebuilds on `selectedFrame` change as today.
* The Phase 21 C single-frame contract is preserved (`playing=false`
  default); the panel's existing Play/Pause button now also drives
  the WebGL viewport.

**B2 — Section cut clipping plane:**
* The viewport gains a section-cut control overlay (axis selector +
  position slider) that drives a `THREE.Plane` clipping plane.
* `renderer.localClippingEnabled = true` + the mesh material's
  `clippingPlanes` array gets the section plane.
* Section-cut state lifts to a `viewportSection: SectionCutState |
  null` prop so the parent panel can sync between SVG / WebGL modes.

**B3 — Deformation magnification slider:**
* When `summary.maxDisplacement` is small (typical), the deformed
  shape is visually indistinguishable from the undeformed mesh.
* Add a `deformationScale: number` prop; the viewport scales node
  displacements before building the geometry: `position = node.
  coordinates + (node.deformed - node.coordinates) · scale`.
* Default `scale=1` (no magnification); slider in the panel goes
  1×–500× with a log scale.

**Tests (~10 in Phase22B_*):**
* Animation: with two frames + `playing=true`, the rendered geometry
  reflects an interpolated state at t=0.5.
* Section-cut: a clipping plane at the centre of the bbox removes
  ~half of the rendered triangles.
* Magnification: at scale=100, the deformed mesh occupies a larger
  bounding-box than at scale=1.

**Anti-gaming guards:**
* **A:-2** the magnification slider's value is surfaced in the
  legend overlay ("Deformation: 100×") so reviewers don't mistake
  amplified deformation for real.
* **T:-3** the SVG-mode fallback path still renders the un-amplified
  un-clipped un-animated mesh — section-cut + magnification are
  WebGL-only by design.

**Honest budget:** ~350 LOC frontend + ~250 LOC tests; ~3 hr. If
clipping planes break the existing color-attribute binding, B2 is
honestly scope-reduced.

---

### Slice C — Tab extractions: App.tsx ≤ 1500

**Goal:** finish the App.tsx composition-root LOC discipline started
Phase 19 D + 20 D + 21 D.

**Deliverables:**
* `frontend/src/components/NarrativeTabPanel.tsx` (NEW, ~180 LOC):
  extracts the `activeTab === 'report'` block. Houses the
  ReportSurface + audit narrative components.
* `frontend/src/components/ExplorationTabPanel.tsx` (NEW, ~150 LOC):
  extracts the `activeTab === 'explore'` block — SensitivityForm,
  experiment runner, comparison overlays.
* App.tsx mounts both via typed prop interfaces (same pattern as
  Phase 21 D's VisualTabPanel).
* Target: **App.tsx ≤ 1500 LOC.** Current 1898. The two extractions
  should remove ~400+ LOC (the activeTab blocks + their inline
  callbacks); back-import trimming buys another ~30.

**Tests (~6 in Phase22C_*):**
* NarrativeTabPanel + ExplorationTabPanel each mount with their
  expected child testids.
* App.tsx mounts via existing shells; no functional regression
  (Phase 20 D Topbar tests + Phase 21 D VisualTabPanel tests stay
  green).

**Anti-gaming guards:**
* **C:-2** the extractions are rendering-equivalent. A diff at
  build-output level should be ≤10 lines of changes (just the
  import-deduplication adjustments).
* **T:-3** the post-extraction App.tsx LOC count is pinned with a
  `wc -l` check in the commit message + the FINAL.md recording.

**Honest budget:** ~330 LOC frontend (new components) + ~150 LOC
tests; ~2 hr. If a circular-dependency emerges from the export
graph, narrower extractions ship instead and the LOC target is
honestly documented as missed.

---

### Slice D — Material picker prominence + WebGL legend units

**Goal:** close two Phase 21 UX carry-forward items.

**D1 — Material picker promotion:**
* New Cmd-K palette entries: `cmd-material-pick-steel-s355`,
  `cmd-material-pick-aluminium-6061-t6`, `cmd-material-pick-titanium-
  ti-6al-4v`, and a generic `cmd-material-picker-open` that scrolls
  the MaterialPickerPanel into view.
* Topbar gains a compact material-select dropdown adjacent to the
  Analysis-type dropdown, so the swap path is 1 click from the top
  rail. Mirrors the analysis-type pattern (same select styling +
  test-id structure).

**D2 — WebGL legend units + Mises selector:**
* The legend's min/max numbers gain a unit suffix (default "Pa";
  exposed via a `units: string` prop). The runtime sets `'Pa'` from
  `summary.fieldRanges`.
* New "Field component" selector in the legend chrome (Von Mises
  default; σ_xx / σ_yy / σ_zz / max-principal selectable). Each
  selection rebuilds the WebGL geometry with the corresponding
  per-vertex color from the same gradient.

**Tests (~8 in Phase22D_*):**
* Cmd-K palette: each new material command fires
  `setSelectedMaterial`.
* Topbar material select: changing it fires `onChangeMaterialId`.
* Legend units suffix renders.
* Field-component selector default = "Von Mises"; switching to σ_xx
  rebuilds the geometry with x-component values.

**Anti-gaming guards:**
* **A:-2** material-pick palette entries fire ONLY
  `setSelectedMaterial` — they do NOT auto-trigger Run Solver
  (would breach reviewer-agency principle).
* **T:-3** the Von Mises computation is the only new derived field;
  pinned with σ_vm = √((σ_xx-σ_yy)² + (σ_yy-σ_zz)² + (σ_zz-σ_xx)² +
  6(σ_xy² + σ_yz² + σ_xz²)) / √2.

**Honest budget:** ~250 LOC frontend + ~200 LOC tests; ~2 hr.

---

### Slice E — 3 testing agents + honest scoring + closure

**Goal:** same framework. Honest projection 80-84. APPROVE iff
composite ≥ 99 AND each ≥ 99 AND no axis < 95%.

**Deliverables:**
* `.planning/phase22_audit_reports/{UX,FEA,UI,FINAL}.md`.
* `.planning/retrospectives/fm04a_phase22_element_fidelity_viewport_depth.md`.
* `.planning/STATE.md` refresh.

## 4. Hard constraints (preserved verbatim from Phase 18-21)

* HF1.7a signed-registry hard-stop
* HF1.7b `*-candidate` carve-out
* HF1.8 path-guard self-protection
* tmp_path-only test snapshot writes
* No push, no PR, no Linear / Notion writes
* Phase 1-21 chain preserved (additive only)

## 5. Acceptance criteria

* [ ] Slice A: 1 new tier_2_validated flip (euler-column) → 4 total;
      C3D10 cantilever residual <5%.
* [ ] Slice B: animation + section + magnification all live in WebGL
      mode; SVG fallback unchanged.
* [ ] Slice C: App.tsx LOC ≤ 1500 (hard); ≤ 1700 (honest stretch
      already met by Phase 21 D).
* [ ] Slice D: material palette entries + Topbar dropdown live;
      legend units render.
* [ ] Slice E: 3-axis honest composite documented; if < 99 the gap
      is named verbatim.
* [ ] All hard constraints PASS.

## 6. Phase 22 thesis

Phase 21 ended with the right floor (3D viewport unblocks Industrial-
CAE; 3 validated cases unblock cross-check rigor; plasticity NLGEOM
unblocks production-gap). **Phase 22 is the polish pass on the same
shape:** quadratic elements where they matter, a second solver kind,
viewport interactions that real reviewers actually use, the LOC
discipline finally biting on Narrative + Exploration. 99 is still
the destination; Phase 22 closes more honest distance.
