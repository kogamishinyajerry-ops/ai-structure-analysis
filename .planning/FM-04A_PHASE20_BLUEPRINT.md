# FM-04a Phase 20 — Tier 2 production-grade extension · Blueprint

**Stamp:** drafted 2026-05-17 (Phase 19 closed at composite 57.0/100 ·
`3388f76`). Authorization: user direct, identical Chinese directive as
Phase 18 / 19 ("批准授权你全权开发 … 一直迭代开发下去，直至达到你眼里的优秀水准 99 分以上 … 绝对诚实客观").

**Honest contract (carried verbatim from Phase 18 + 19):**
* No rubric reshaping.
* No score gaming.
* If the composite lands at 70/100, the artifact says 70/100, not 99.
* Iteration is capped at v2.3 round-cap = 3; stop early when iteration
  becomes score-padding.

## 1. Thesis

Phase 18 built the Tier 2 parts bin. Phase 19 ran the first car off the
assembly line (cylinder-pv-candidate flipped to `tier_2_validated` via
verdict-file-driven promotion + real ccx + analytical cross-check).
**Phase 20 makes the car drivable end-to-end through the UI** by closing
the four route-vs-service / commit-vs-claim gaps the Phase 19 E agents
surfaced, AND pushes one production-scale lever (Gmsh + STEP → real
mesh → ccx) into the Tier 2 pipeline so the workbench stops being
single-element-coupon-bound.

## 2. Honest score projection vs Phase 19 baseline

| Dimension | Phase 19 actual | Phase 20 projection | Lift mechanism |
|---|---|---|---|
| UX | 67/100 | 78-85 | T1 (cylinder-pv in Sidebar) + T3/T4 (material flow end-to-end) + T5 (legend + finished migration) |
| FEA | 46/100 | 58-66 | Slice C Gmsh-meshed pipeline (Mesh-fidelity 6→12-14) + Slice B plasticity + second cross-check (Cross-check 11→13-14) + materials with hardening curves |
| UI | 58/100 | 68-74 | Topbar + RightRail extractions targeting App.tsx <1500 LOC (Layout-discipline 12→16) + finished primitive migration (Onboarding 15→17) |
| **Composite** | **57.0** | **68-75** | Still NOT 99. 99 needs WebGL viewport + contact + full materials catalogue + months of Tier 3 work. |

The projection is what I honestly believe the agents will score IF I
execute the 5 slices cleanly. If actual lands lower, the FINAL.md will
say so verbatim.

## 3. Slice breakdown

### Slice A — `RunRequest.material_id` wired route → service

**Goal:** Close the Phase 19 E load-bearing finding (FEA + UX both flagged
independently). The HTTP route declares `material_id` but never reads it
into the service call.

**Deliverables:**
* `backend/app/api/routes/solver.py`: read `request.material_id` and pass
  it to the service entrypoint. If present, route through
  `app.services.tier2_pipeline.run_tier2_minimal_hex(case_dir, ...,
  material_id=request.material_id)`. If absent, preserve the existing
  Phase 1-17 envelope path (back-compat).
* `backend/tests/test_phase20a_material_route_integration.py` (NEW, ≥6
  tests):
  * (T:-3) Route → service handoff: POST with `material_id="aluminium-6061-T6"`
    → assert served INP contains the aluminium `*ELASTIC` block
    (E=68.9e9, ν=0.33) byte-identical to `library.json`. Use
    `TestClient` so the route → service hop is exercised.
  * (A:-2) `material_id="nonexistent"` → 422 (NOT 500) with citation
    pointing at the library path.
  * (A:-2) Missing `material_id` → service falls back to `DEFAULT_STEEL`
    (back-compat with all pre-Phase-20 callers).
  * (C:-1) Response envelope carries the chosen material's `reference`
    citation (so the audit trail surfaces what was actually used).

**Anti-gaming guards:**
* **A:-3** end-to-end via `TestClient` so a handler-direct call cannot
  hide a missing route → service connection.
* **M:-1** material lookup goes through the same SSOT helper Slice A19A
  uses; no inline duplication.

**Honest budget:** ~50 LOC backend + ~120 LOC tests; <1 hr.

---

### Slice B — Plasticity `*PLASTIC` keyword + second analytical cross-check

**Goal:** Two independent FEA capability adds. Both lift the Cross-check
+ Materials sub-scores.

**Deliverables:**

**B1 — plasticity:**
* `backend/app/services/materials/api.py`: extend `Material` dataclass
  with optional `plastic_hardening_curve: list[tuple[float, float]] | None`
  where each tuple is `(plastic_strain, true_stress_pa)`. Loader rejects
  curves that violate monotonicity or include negative values.
* `backend/app/services/materials/library.json`: add bilinear hardening
  to steel-S355 (CEN EN 1993-1-5 bilinear: σ_y=355 MPa → ε_p=0, σ_u=510
  MPa → ε_p=0.20) and aluminium-6061-T6 (MMPDS 6061-T6 effective
  bilinear: σ_y=276 MPa → ε_p=0, σ_u=310 MPa → ε_p=0.12).
* `backend/app/adapters/calculix/inp_writer.py`: when material carries a
  hardening curve, emit a `*PLASTIC` block after `*ELASTIC` with the
  curve points.
* No solver invocation change required — ccx auto-promotes to nonlinear
  if `*PLASTIC` is present.

**B2 — cantilever cross-check:**
* `backend/app/services/cross_check/cantilever_beam.py` (NEW): pure
  function `compute_analytical_tip_deflection(*, length_m,
  youngs_modulus_pa, second_moment_m4, tip_load_n) -> float` returning
  δ = PL³/(3EI).
* `backend/app/services/cross_check/cantilever_runner.py` (NEW): composes
  a single-hex cantilever INP (one end clamped, tip load) + ccx + reads
  tip displacement → compares to analytical.
* `golden_samples/cantilever-beam-candidate/` (NEW *-candidate dir):
  `notes.md`, `cross_check_verdict.yaml` placeholder; promotion is
  verdict-driven (NOT pre-baked).
* `scripts/cross_check_cantilever.py` (NEW): CLI runner identical
  pattern to Phase 19 B's `cross_check_cylinder_pv.py`.
* Registry add: append `cantilever-beam-candidate` to
  `CLAIM_TIER_REGISTRY` as `tier_1_candidate`; `_apply_verdict_overlay()`
  promotes to `tier_2_validated` when the verdict file says PASS.

**Tests** (≥12 total):
* (B1) `test_phase20b_plasticity_keyword.py`: pin that steel-S355 INP
  has `*PLASTIC` followed by 2 rows; aluminium-6061-T6 same; titanium
  (no curve) has NO `*PLASTIC`; non-monotonic curve raises ValueError.
* (B2) `test_phase20b_cantilever_cross_check.py`: pin analytical
  formula on known inputs (L=1m, E=210e9, I=8.33e-9 m⁴, P=1000 N →
  δ = (1000·1³)/(3·210e9·8.33e-9) = 0.0001904 m); pin verdict-file
  round-trip; pin registry promotion seam.
* (B2 + requires_solver) `test_phase20b_real_ccx_cantilever.py`: real
  ccx + cantilever_runner → verdict PASS at ≤5% residual.

**Anti-gaming guards:**
* **M:-1** hardening curves cite EN 1993-1-5 / MMPDS-2023 with section
  numbers in the library `reference` field.
* **T:-3** analytical formula pinned per-input; not just "non-zero".

**Honest budget:** ~200 LOC backend + ~250 LOC tests; ~2 hr.

---

### Slice C — Gmsh + STEP → Tier 2 pipeline

**Goal:** Biggest single FEA lever. Currently `gmsh_runner.py` exists
but is **orphaned** from `tier2_pipeline.run_tier2_minimal_hex` (FEA
agent finding). Wire Gmsh STEP/STL/.geo → C3D4 tet mesh → ccx static
run as the FIRST production-scale (not single-element) Tier 2 path.

**Deliverables:**
* `backend/app/services/tier2_pipeline.py`: add new entrypoint
  `run_tier2_meshed_pipeline(case_dir, *, geometry_spec, material_id,
  bc_spec, load_spec, ccx_binary="ccx", timeout_sec=120.0) ->
  Tier2RunResult`. `geometry_spec` is a typed input — for Phase 20 we
  support `GmshGeoSpec(geo_path)` and `GmshStepSpec(step_path)`.
* `backend/app/adapters/calculix/mesh_to_inp.py` (NEW): converts a
  Gmsh `.msh` file (ASCII v2 or v4) → CalculiX INP body (nodes block
  + elements block as `*ELEMENT, TYPE=C3D4` for tets; *NSET groups
  for named BC surfaces). Re-uses existing `inp_writer` for the step
  + material + load wrappers.
* `golden_samples/plate-with-hole-candidate/` (NEW): canonical
  rectangular plate w/ circular hole .geo file, NOTES.md, expected
  ranges. The case is `tier_1_candidate` baseline; Phase 21+ can add a
  Kirsch analytical cross-check to promote.
* `scripts/run_tier2_meshed.py` (NEW): CLI runner.
* Tests (≥8 total):
  * Mesh-to-INP round-trip: a 1-cube .geo → known node + element count
    → INP byte-pin on first 3 element rows.
  * (requires_solver) plate-with-hole: real Gmsh + real ccx → non-zero
    displacement field + non-singular stress field.
  * Defensive: malformed .msh raises ValueError; missing STEP → 422.

**Anti-gaming guards:**
* **T:-3** mesh-to-INP byte pins; a future regression that reorders
  nodes / changes element type trips the test.
* **C:-1** new candidate case has full NOTES.md with citation to where
  the .geo came from (not a one-off scratch file).

**Honest budget:** ~250 LOC backend + ~300 LOC tests; ~2-3 hr. The
risk is mesh-to-INP edge cases (Gmsh format variance across v2/v4); I
will pin to v2 ASCII and reject v4 with a clear error.

---

### Slice D — Frontend: Topbar + RightRail + ResultMesh finish + Sidebar gallery

**Goal:** Close the three Phase 19 E UI findings (App.tsx still
god-component, ResultMesh partial migration, cylinder-pv invisible in
Sidebar) in one Slice.

**Deliverables:**
* `frontend/src/components/Topbar.tsx` (NEW, ~120 LOC): extracted from
  `App.tsx` lines 1631-1668 (analysis-type select + Run Solver +
  Copilot toggle + Stop button). Props: `analysisType`, `setAnalysisType`,
  `solving`, `onRunSolver`, `onStopSolver`, `showChat`, `onToggleChat`,
  `activeCaseId`. Preserve every data-testid.
* `frontend/src/components/RightRail.tsx` (NEW, ~80 LOC): extracted
  chat panel mount + advisor panel mount block. Props: `showChat`,
  `onSendMessage`, `chatMessages`, `caseId`, `snapshotLabel`.
* `frontend/src/components/ResultMeshPlaybackPanel.tsx`: migrate the
  bespoke loading / error / "no renderable frame" / pending divs to
  SkeletonCard / ErrorCard / EmptyStateCard with wrapper test-ids
  `result-mesh-loading` / `result-mesh-error` / `result-mesh-empty`.
* `frontend/src/components/Sidebar.tsx`: extend `availableCases` to
  also surface `*-candidate` entries from the candidate-case registry
  so cylinder-pv-candidate shows up in the left-rail. Selecting one
  fires the same `onSelectCase` path used by DB cases (no special-case
  branching in App.tsx).
* `frontend/src/App.tsx`: replace the 80-line Topbar JSX + 60-line
  RightRail JSX with `<Topbar ... />` and `<RightRail ... />`. Target
  App.tsx <1500 LOC (current 2019). Honest stretch: <1700 LOC is good,
  <1500 is great, <500 is Phase 21+.
* `frontend/src/App.tsx`: wire `selectedMaterial.id` into the
  `/solver/run` POST body so the Slice A end-to-end flow lights up in
  the UI.
* `frontend/test/Phase20D.test.tsx` (NEW, ≥22 tests): Topbar + RightRail
  + ResultMesh primitive migration + Sidebar cylinder-pv surfacing +
  material body wiring. Same OUTER-wrapper-testid + INNER-primitive-
  testid pin pattern as Phase 19 D.

**Anti-gaming guards:**
* App.tsx LOC: `wc -l frontend/src/App.tsx` must report ≤1750 (honest
  not-quite-target ceiling so the slice doesn't get gamed by inlining
  a "shrink" via deleted comments).
* (T:-3) The Sidebar test asserts cylinder-pv-candidate is selectable
  AND firing onSelectCase delivers a case object with the right id.

**Honest budget:** ~400 LOC frontend + ~450 LOC tests; ~3 hr.

---

### Slice E — 3 testing agents + honest scoring + closure

**Goal:** Same v2.3 round-cap=3 framework as Phase 18 E + 19 E. Agents
return honest composite. APPROVE iff composite ≥99 AND each ≥99 AND no
axis < 95%. Otherwise CHANGES_REQUIRED with honest gap report.

**Honest projection (restated):** 68-75. Not 99.

**Deliverables:**
* `.planning/phase20_audit_reports/UX.md`, `FEA.md`, `UI.md`, `FINAL.md`
  (round-1 baseline). Add `_round2.md` / `_round3.md` only if I judge a
  spike-class fix would meaningfully move the lowest axis.
* `.planning/retrospectives/fm04a_phase20_production_grade_extension.md`
  with honest composite + Phase 21+ carry-forward.
* `.planning/STATE.md` refresh.

**Iteration discipline:**
* Round 1: spawn UX/FEA/UI agents → composite delta vs Phase 19.
* Round 2: ONLY if a single concrete fix could lift the lowest axis by
  ≥5 points without being cosmetic. If the gaps are structural
  (WebGL, contact, etc.), skip round 2.
* Round 3: same gate.

## 4. Hard constraints (preserved verbatim from Phase 18/19)

* HF1.7a signed-registry hard-stop
* HF1.7b `*-candidate` carve-out
* HF1.8 path-guard self-protection
* tmp_path-only test snapshot writes (no live writes to
  `reports/snapshots/` or `golden_samples/` outside the new candidate
  dirs Slice B + C explicitly create)
* No push, no PR, no Linear / Notion writes
* No new GS-registry entries (only `*-candidate` dirs)
* Phase 1-19 chain preserved (additive only)

## 5. Acceptance criteria

* [ ] Slice A: route-level integration test green; material_id flows
      end-to-end (UI POST → service → INP body) and back-compat path
      preserved.
* [ ] Slice B: 2 new analytical surfaces (plasticity keyword +
      cantilever cross-check); cantilever case promotes to
      tier_2_validated when verdict PASS (NOT hand-edited).
* [ ] Slice C: Gmsh-meshed plate-with-hole runs through real ccx with
      non-zero displacement field.
* [ ] Slice D: App.tsx ≤ 1750 LOC; ResultMeshPlaybackPanel primitives
      fully migrated; cylinder-pv-candidate selectable from Sidebar.
* [ ] Slice E: 3-axis honest composite documented; if <99, the gap is
      named verbatim in the retro.
* [ ] All hard constraints PASS.

## 6. Phase 20 thesis

Phase 19 honestly admitted the 57.0/100 floor and surfaced three real
wiring gaps. Phase 20 closes those three gaps AND adds one
production-scale pipeline path so the workbench can mesh a real STEP
and solve it. If the composite lands at 70, that's a +13 honest lift.
If it lands at 80, even better. If it lands at 60, the retro names why.

99 remains months of Tier 3 work that this session does not pretend to
deliver. The discipline is: every score is real, every gap is named.
