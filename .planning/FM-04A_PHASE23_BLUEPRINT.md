# FM-04a Phase 23 blueprint — Solver depth + viewport fidelity + reviewer-driven inspection

> **Tier banner:** Tier 1 / Tier 2 engineering candidate; not signed
> validation; not benchmark agreement.
>
> **Authorization:** user directive (verbatim): "批准授权你全权开发，构建
> 下一个阶段的蓝图（致力于顶级的全流程AI FEA demo展示），瞄准蓝图进行开发，
> 要有一套专门的测试子agent，真实测评项目的功能、使用手感、可视化追踪……有
> 明确的完成度评分机制（要绝对诚实客观，且维度充足，包括FEA仿真全维度能力，
> 包括新手人类用户的使用难度、交互模式，包括UI设计是否能对标顶级工业软件），
> 一直迭代开发下去，直至达到你眼里的优秀水准（99分以上）"
>
> **Composite trajectory:** Phase 18 R1 47.7 → P20 R2 64.3 → P21 R1
> 73.1 → P22 R1 77.1. Phase 23 projection band: **81-85**, mid 83.
> Honest expected lift: +4 to +8.

## 1. Thesis

Phase 22 was the polish pass: C3D10 quadratic elements lifted mesh
fidelity, WebGL viewport gained depth controls (animation + section
+ magnification), App.tsx LOC discipline finally bit, material
picker promoted to top rail. The honest misses:
- **Buckling promotion failed** because the C3D8 solid-element
  idealization can't match Euler-Bernoulli 1D-beam analytical.
- **σ-tensor switcher deferred** because result_mesh.json carries
  only scalar `value` per element.
- **Real WebGL E2E still mock-only** (jsdom getContext stub).
- **No industrial-CAE feature parity for node-picking** — reviewers
  can't probe a field value at a point.

Phase 23 attacks these structural misses directly. The unifying
shape is **reviewer-driven inspection**: a reviewer should be able
to (1) trust the buckling case because B31 beam-element gives the
right answer, (2) see σ_xx vs Mises vs max-principal at will, (3)
click any node to read its field value, (4) hide elements above /
below a threshold to focus on hot spots.

## 2. Slices

### Slice A — B31 Timoshenko beam-element buckling runner

**Goal:** flip `euler-column-candidate` from tier_1_candidate to
tier_2_validated. Validated count 3 → 4.

**Deliverables:**
* `backend/app/services/cross_check/buckling_b31_runner.py` — composes
  a procedural ccx INP with B31 beam elements, `*BEAM SECTION`
  carrying I_min + A + cross-section orientation, `*BOUNDARY` pinning
  the two end nodes for DOF 2/3 (translation, NOT rotation), axial
  compressive force at one end, `*STEP, PERTURBATION` + `*BUCKLE 4`
  for the first 4 eigenvalues.
* The composer does NOT use gmsh — B31 is a 1D line element with
  inline node generation (N points along the column length).
* Reuses Phase 22 A's eigenvalue parser from `buckling_runner.py`
  via shared module `_buckle_dat_parser.py` (refactor to lift it
  out so both runners share the same parser).
* Verdict YAML `golden_samples/euler-column-candidate/cross_check_
  verdict.yaml` written on successful run; `_claim_tier.py` overlay
  flips the case to tier_2_validated.

**Tests (~8 in Phase23A_*):**
* B31 INP composer pins: header, *NODE block, *ELEMENT TYPE=B31,
  *BEAM SECTION block with computed Ixx/Iyy/Area, *BOUNDARY block.
* `@pytest.mark.requires_solver` E2E pin: ccx run produces 4
  eigenvalues, lowest within 10% tolerance of analytical 1727 N.
* Verdict YAML round-trip via existing SSOT schema.
* Post-promotion registry pin: `test_phase23a_validated_count_is_four`
  trips if the verdict file is removed.

**Anti-gaming guards:**
* **A:-1** the runner MUST honestly fail at the existing 10%
  tolerance if the cross-section properties are wrong. Test pins
  this with a deliberately wrong I_min and asserts FAIL verdict.
* **T:-2** test runs real ccx subprocess and parses real .dat output
  — no mocking of solver output.

**Honest budget:** ~250 LOC backend (runner + composer + parser
extraction) + ~200 LOC tests; ~2-3 hr.

---

### Slice B — σ-tensor schema upgrade + Mises/component switcher

**Goal:** unlock the per-component σ switcher that Phase 22 D
documented as deferred. Honest scope: frontend-only delivery —
schema extension is on the frontend side; backend exporter
updates are stretch.

**Deliverables:**
* `frontend/src/resultMeshPlayback.ts` — `ResultMeshElement` gains
  optional `stressTensor: {sxx: number, syy: number, szz: number,
  sxy: number, syz: number, sxz: number} | null`.
* `frontend/src/stressDerivatives.ts` (NEW, ~80 LOC) — pure-function
  `computeVonMises(t)`, `computeMaxPrincipal(t)`, `componentValue
  (t, axis)`. Von Mises formula:
  ```
  σ_vm = √((σ_xx-σ_yy)² + (σ_yy-σ_zz)² + (σ_zz-σ_xx)²
          + 6(σ_xy² + σ_yz² + σ_xz²)) / √2
  ```
  Max principal via 3×3 eigenvalue (closed-form characteristic
  polynomial for symmetric matrix).
* `ResultMeshWebGLViewport.tsx` — accepts new `fieldComponent: 'mises'
  | 'sxx' | 'syy' | 'szz' | 'max_principal'` prop. When a tensor
  is present per element, the displayed value rebuilds via the
  selected derivative; falls back to scalar `value` when tensor is
  absent (backwards compatible).
* `ResultMeshPlaybackPanel.tsx` — legend gains a real dropdown
  `<select data-testid="legend-field-component-select">` for
  switching components. Disabled with tooltip when no tensor data
  present.

**Tests (~10 in Phase23B_*):**
* `computeVonMises` pins for canonical inputs (uniaxial,
  hydrostatic, pure shear).
* `computeMaxPrincipal` eigenvalue closed-form pin.
* `componentValue` axis switch pin.
* Legend selector renders, changes prop, rebuild fires.
* Backwards compat: element with no tensor still renders via scalar
  value path.

**Anti-gaming guards:**
* **B:-1** Von Mises pin uses analytical-known input: σ_xx=100 MPa
  uniaxial → σ_vm = 100 MPa. Hydrostatic (100,100,100) → σ_vm=0.
* **B:-2** the switcher MUST NOT silently coerce a missing tensor
  to zero. When `stressTensor=null`, the selector is disabled, NOT
  computing Mises from zero-fill.

**Honest budget:** ~150 LOC frontend (math + UI) + ~180 LOC tests;
~2 hr.

---

### Slice C — Node-picking with field probe overlay

**Goal:** industrial-CAE feature parity. Reviewers click a node and
read its (x,y,z, value) at the cursor.

**Deliverables:**
* `ResultMeshWebGLViewport.tsx` — adds `THREE.Raycaster` mouse
  handler. On left-click (no drag), casts a ray and finds the
  closest face's vertex within hit tolerance. Highlights the picked
  node with a small `THREE.Sphere` mesh overlay (R=0.5% bbox span).
* Picked-node HUD overlay: top-left fixed-position div showing
  `node_label`, `x/y/z`, current field value + units.
* New prop `onNodePicked?: (info: PickedNodeInfo | null) => void`
  forwards the event to the parent so the panel can surface it in
  its info pane.
* Escape clears the pick.

**Tests (~6 in Phase23C_*):**
* `findClosestVertex(ray, geometry)` pure-function pin with
  canonical inputs.
* Pick clears on Escape.
* HUD overlay renders after a synthetic click event.
* `onNodePicked` callback fires with node label.

**Anti-gaming guards:**
* **C:-1** the picker must use SCREEN-SPACE hit tolerance, not
  world-space, so the picker stays usable at zoomed-out views.
* **C:-2** picked node label MUST come from the frame's node list,
  NOT a synthetic index — pinned via test with shuffled node
  labels.

**Honest budget:** ~180 LOC frontend (raycast + HUD) + ~150 LOC
tests; ~2 hr.

---

### Slice D — Element-threshold filter

**Goal:** alternative-to-iso-surfaces for hot-spot focus. Reviewers
hide elements below or above a threshold value (e.g. "show only
elements above 200 MPa"), letting them concentrate on yielded /
critical zones.

**Deliverables:**
* `ResultMeshWebGLViewport.tsx` — accepts `valueFilter?:
  {minValue?: number; maxValue?: number; mode: 'inside' | 'outside'}`
  prop. When set, elements outside (or inside, inverted) the range
  drop out of the BufferGeometry build.
* `ResultMeshPlaybackPanel.tsx` — depth controls row gains a
  threshold sub-control (min slider + max slider + inside/outside
  toggle).
* The legend's gradient stays anchored to the full value range; the
  filter only changes which elements render.

**Tests (~6 in Phase23D_*):**
* `applyValueFilter(elements, filter)` pure-function pin.
* UI: setting the min filter excludes low-value elements; max
  filter excludes high; inside/outside inverts.
* Backwards compat: undefined filter → all elements render.

**Anti-gaming guards:**
* **D:-1** elements without a `value` field MUST be retained
  regardless of filter (no silent drop of e.g. projectile-class
  elements that never carry a stress value).

**Honest budget:** ~120 LOC frontend + ~120 LOC tests; ~1.5 hr.

---

### Slice E — 3 testing agents + honest scoring + closure

**Goal:** same framework. Honest projection 81-85. APPROVE iff
composite ≥ 99 AND each ≥ 99 AND no axis < 95%.

**Deliverables:**
* `.planning/phase23_audit_reports/{UX,FEA,UI,FINAL}.md`.
* `.planning/retrospectives/fm04a_phase23_solver_depth_viewport_fidelity.md`.
* `.planning/STATE.md` refresh.

## 3. Hard constraints (preserved verbatim from Phase 18-22)

* HF1.7a signed-registry hard-stop
* HF1.7b `*-candidate` carve-out
* HF1.8 path-guard self-protection
* tmp_path-only test snapshot writes
* No push, no PR, no Linear / Notion writes
* Phase 1-22 chain preserved (additive only)
* v2.3 round-cap=3

## 4. Acceptance criteria

* [ ] Slice A: 1 new tier_2_validated flip (euler-column) → 4 total;
      B31 buckling residual <10% vs Euler analytical.
* [ ] Slice B: σ-tensor schema + Mises/component switcher live in
      WebGL viewport; backwards compatible.
* [ ] Slice C: node-pick + HUD overlay live; Escape clears pick.
* [ ] Slice D: element-threshold filter live; legend stable.
* [ ] Slice E: 3-axis honest composite documented; if < 99 the gap
      is named verbatim.
* [ ] All hard constraints PASS.

## 5. Phase 23 thesis

Phase 22 ended with the right shape (polish pass on viewport +
elements + LOC) but two honest misses (buckling promotion, σ-tensor
switcher). Phase 23 closes both directly + adds two reviewer-
driven inspection features (node-picking, threshold filter) that
close real industrial-CAE feature-parity gaps. 99 is still the
destination; Phase 23 closes more honest distance.

## 6. Projection breakdown

| Axis | Phase 22 | Phase 23 projection | Honest delta | Driver |
|---|---|---|---|---|
| UX | 79.6 | 82-85 | +2.4 to +5.4 | node-pick reviewer ergonomics, threshold filter cognitive load, Mises switcher value |
| FEA | 70.4 | 75-79 | +4.6 to +8.6 | B31 promotion (Dim 2 +5-7), B31 element kind (Dim 1 +2), Mises switcher derived field (Dim 5 +1) |
| UI | 81.4 | 84-86 | +2.6 to +4.6 | node-pick industrial parity (Dim 2 +3-5), threshold filter information density (Dim 4 +1-2) |
| **Composite** | **77.1** | **81-85** | **+3.9 to +7.9** | mid projection **83** |

Honest if 81 lands: documented; honest if 85 lands: documented;
no rubric reshape regardless.

Not signed validation; not benchmark agreement.
