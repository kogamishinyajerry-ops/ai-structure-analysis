# Phase 20 FEA testing agent — round 1 report

## Composite score
**57/100** (verdict: **CHANGES_REQUIRED** — below 60 informal landing bar; Slice C delivered the headline uplift but the plasticity slice is keyword-only with no NLGEOM E2E pin, and one tier_2_validated case remains the validation floor.)

## Phase 19 round-1 baseline comparison
Prior FEA = 46/100. Phase 20 added [Slice A `material_id` route → `compose_material_id_inp` consumed end-to-end at `backend/app/api/routes/solver.py:76`; Slice B plasticity (S355 EN 1993-1-5 C.6 + 6061-T6 MMPDS §9.2) + `*PLASTIC` keyword writer at `backend/app/adapters/calculix/inp_writer.py:148` + cantilever PL³/(3EI) analytical at `backend/app/services/cross_check/cantilever_beam.py`; Slice C Gmsh STEP/STL/BREP/.geo → C3D4 tet → ccx pipeline at `backend/app/services/tier2_pipeline.py:318` with real-solver E2E pin at `backend/tests/test_phase20c_meshed_pipeline.py:423` PASSED].
**EXPECTED uplift +12 to +20. ACTUAL observed delta = +11** (just below the projected band). The miss is concentrated in the plasticity dimension: `*PLASTIC` is written but no `requires_solver` test promotes the run to NLGEOM and verifies a yielding response, so Slice B reads as scaffolding rather than capability.

## Dimension scores

### 1. Solver coverage: 12/20
Real CalculiX ccx subprocess invocation via `backend/app/adapters/calculix/runner.py`. Analysis types wired: **Static** (`inp_writer.py:67`) + **Modal `*FREQUENCY`** (`inp_writer.py:268`). **No Buckling / Dynamic / Contact.** `@pytest.mark.requires_solver` count = **13** decorators (`grep -c @pytest.mark.requires_solver` on `backend/tests/`):
- `test_phase18a_calculix_runner.py:271,296,328` — coupon ccx subprocess pins
- `test_phase18c_mesh_materials.py:435,457` — gmsh real-subprocess pins
- `test_phase19a_material_plumbing.py:257,328` — aluminium / steel coupons
- `test_phase19b_cross_check.py:308,336` — hoop-stress cross-check + verdict promotion
- `test_phase19c_materials_breadth_modal.py:253,…` — modal eigenvalue pins
- `test_phase20c_meshed_pipeline.py:423` — gmsh+ccx meshed plate E2E (PASSED, verified this session)

Cap at 12/20: two analysis types is half the production matrix; the meshed-pipeline pin is the only new requires_solver of Phase 20.

### 2. Materials catalogue: 14/20
`backend/app/services/materials/library.json` carries **8 materials**, each with full property set and standards citation (verified via `json.load` enumeration):
- steel-S355 (EN 10025-2:2019 §7.3) — **plastic_hardening_curve** per EN 1993-1-5 Annex C §C.6 bilinear (σ_y=355 MPa → σ_u=510 MPa @ 20% εₚ)
- aluminium-6061-T6 (MMPDS-2023 §3.6.1.0) — **plastic_hardening_curve** per MMPDS §9.2 (σ_y=276 → σ_u=310 @ 12% εₚ)
- Ti-6Al-4V, steel-S275, SS-304, cast-iron-grey, bronze-C932, Inconel-718 — elastic only

API surface at `backend/app/services/materials/api.py`. Two of eight with hardening curves is enough to demonstrate plasticity wiring; six are elastic-only. 14/20 reflects strong breadth + complete standards citations but limited plastic coverage.

### 3. Mesh / element fidelity: 13/20
INP composers cover two element families now:
- `backend/app/adapters/calculix/inp_writer.py:136,253` — hand-written **C3D8** linear hex (single-element coupons, static + modal)
- `backend/app/adapters/calculix/mesh_to_inp.py:37` — **C3D4** linear tet from gmsh msh-format; future-proof table comment at `mesh_to_inp.py:34-35` notes C3D10 / S4 extension is a one-line edit

**Gmsh STEP→INP integration verified end-to-end**: `backend/tests/test_phase20c_meshed_pipeline.py::test_real_gmsh_and_ccx_plate_with_hole_yields_displacement` **PASSED** (15/15 in file, requires_solver branch PASS verified this session). Phase 20 C closed the "single-element coupon only" finding from prior rounds. No quadratic (C3D10), no shells (S4), no beams (B31) yet — straight tets only.

### 4. Cross-check / validation rigor: 11/20
**Verdict YAML count under `golden_samples/*/cross_check_verdict.yaml` = 1** (verified via `find golden_samples -name cross_check_verdict.yaml`):
- `golden_samples/cylinder-pv-candidate/cross_check_verdict.yaml:15` → `"claim_tier": "tier_2_validated"`

Plate-with-hole and cantilever were honestly registered as **`tier_1_candidate`** (verified via grep in `golden_samples/cantilever-beam-candidate/NOTES.md:3` and `golden_samples/plate-with-hole-candidate/NOTES.md:3` — both explicitly call out "runner is Phase 21+ scope"). Two analytical solutions now ship: hoop (`backend/app/services/cross_check/cylinder_hoop.py:56`) + cantilever PL³/3EI (`backend/app/services/cross_check/cantilever_beam.py`). Verdict-file-driven promotion loader at `backend/app/services/reporting/_claim_tier.py:38-88` is real and reads `claim_tier` from yaml. 11/20: one tier_2_validated case is still the floor; second analytical formula adds rigor for the future runner but cannot yet promote anything.

### 5. Production-grade gap honesty: 7/20
vs. ANSYS / Abaqus / MSC Nastran:
- **Geometry import (STEP)**: ✓ — wired in `backend/app/services/tier2_pipeline.py:349` (.step/.stp/.stl/.brep/.geo)
- **Auto-mesh**: ✓ — Gmsh subprocess driver, real E2E in test_phase20c
- **Plasticity (full)**: ⚠ partial — `*PLASTIC` keyword emitted (`inp_writer.py:148`, `mesh_to_inp.py:292`); the comment at `inp_writer.py:38-39` claims "ccx promotes to a nonlinear (NLGEOM-capable) run", but `grep -E "NLGEOM=YES|nonlinear" backend/app/adapters/calculix/*.py` returns zero `NLGEOM=YES` and **no requires_solver test in Phase 20 exercises a yielding load and verifies plastic strain ≠ 0**. Plasticity is declared, not demonstrated.
- **Contact**: ✗ — no `*CONTACT PAIR` / `*SURFACE` emission anywhere in INP writers
- **3D contour viz**: ✗ — `frontend/src/components/BulletPlateBlueprintPanel.tsx:263-300` uses SVG `linearGradient` + `ellipse` schematics; `frontend/src/bulletPlateBlueprint.ts:110` explicitly admits "contour is schematic unless backed by result_mesh and metric artifacts". No WebGL / three.js / VTK.js.

Floor rule: "max 8/20 unless ALL boxes checked" — 2 of 5 unchecked, plasticity is half-checked. **7/20**. Phase 20 C credit for closing the coupon-only finding (geometry+mesh boxes now genuinely tick), which is why this is 7 not 5.

## Top 3 deficiencies (file:line)
1. **No NLGEOM/plasticity E2E test** — `backend/app/adapters/calculix/inp_writer.py:142-149` writes `*PLASTIC` but `backend/tests/test_phase20b_plasticity_and_cantilever.py` carries zero `@pytest.mark.requires_solver`; a yielding-load coupon ccx run that asserts `PE` (plastic strain) field > 0 is the missing pin. Without it, Slice B is keyword scaffolding.
2. **Only one tier_2_validated case** — `golden_samples/cylinder-pv-candidate/cross_check_verdict.yaml:15`. Plate-with-hole (`golden_samples/plate-with-hole-candidate/NOTES.md:6`) and cantilever (`NOTES.md:3`) have analytical formulas + .geo on disk but no runner promoting them. Cross-check breadth is bottlenecked on Phase 21+ runners.
3. **No 3D viewport for FEA results** — `frontend/src/bulletPlateBlueprint.ts:110` openly labels contour "schematic"; result mesh artifacts produced by ccx (.frd) have no WebGL renderer wired. Production-grade gap dimension cannot move above 8/20 until this lands.

## One specific FEA improvement that would lift the lowest-scoring dimension
**Add `*STEP, NLGEOM=YES` to `inp_writer.py:153` (just before `*STATIC`) when material carries `plastic_hardening_curve`, then ship one `@pytest.mark.requires_solver` test in `test_phase20b_plasticity_and_cantilever.py` that applies a tensile traction above σ_y on the steel-S355 coupon, runs real ccx, parses the `.frd`, and asserts `PE` (plastic strain) component > 1e-4 at the loaded face.** That single E2E pin promotes the plasticity dimension from "keyword wired" to "ccx truly solved a nonlinear yielding problem", lifting **Production-grade gap honesty 7 → 9** (plasticity box flips from ⚠ to ✓) and giving **Solver coverage** a credible claim to nonlinear-static as a third analysis type (+1, → 13). Net composite uplift ≈ +3. Beyond that, the same fix unlocks a tier_2_validated path for any plasticity-bearing analytical (e.g., a tension coupon with bilinear hardening cross-checked against the curve's own (σ, εₚ) table).
