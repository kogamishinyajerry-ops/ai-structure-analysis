# Phase 19 FEA testing agent — round 1 report

## Composite score
**46/100** (verdict: CHANGES_REQUIRED)
APPROVE only if composite ≥ 99 AND every dimension ≥ 19. Floor not met.

## Phase 18 round-3 baseline comparison
Prior FEA = 34/100 (Phase 18 round 3 final). Phase 19 Slices added:
- Slice A: material_id plumbed end-to-end (`backend/app/services/tier2_pipeline.py:84-114, 156-225`)
- Slice B: Lame thin-walled hoop cross-check + first verdict-driven tier flip (`backend/app/services/cross_check/cylinder_hoop.py:56-104`, `backend/app/services/cross_check/cylinder_pv_runner.py:212-273`, `backend/app/services/reporting/_claim_tier.py:89-122`)
- Slice C: materials 3→8 (`backend/app/services/materials/library.json`), modal step writer + eigenvalue parser (`backend/app/adapters/calculix/inp_writer.py:160-261`, `backend/app/services/modal_frequencies.py:21-83`)

EXPECTED uplift was +8-16. ACTUAL observed delta = +12 (34 → 46). Honest landing inside the projected band.

## Dimension scores

### 1. Solver coverage: 10/20
- Real CalculiX subprocess wired and load-bearing: YES — `backend/app/adapters/calculix/runner.py:138-240` runs `ccx -i <jobname>` via `subprocess.run` with bounded timeout.
- Static (linear): YES — `write_minimal_hex_inp` emits `*STATIC` (`inp_writer.py:142`).
- Modal (`*FREQUENCY`): YES — `write_modal_hex_inp` emits `*FREQUENCY` + density (`inp_writer.py:252`). NEW in Phase 19 C.
- Buckling (`*BUCKLE`): EXISTS in `services/analysis_service.py:80-86` but it's a string-rewrite hack on an existing static INP, NOT plumbed into the Tier 2 pipeline, no `requires_solver` E2E test, no cross-check.
- Dynamic / Explicit / Contact: NO. Reader handle mentions `C3D10` + contact-pair as known *types* (`core/types/reader_handle.py:11, 100`) but no INP composer, no test, no pipeline.
- `@pytest.mark.requires_solver` E2E pins that actually invoke ccx: 3 pins total — `test_phase19a_material_plumbing.py:258` (aluminium-vs-steel ratio), `test_phase19a_material_plumbing.py:329` (audit citation), `test_phase19b_cross_check.py:308, 336` (cross-check + tier flip), `test_phase19c_materials_breadth_modal.py:253` (5-mode modal). 5 real-ccx pins; load-bearing.
- Honest gap: static + modal only. Buckling exists in legacy path, untested at Tier 2; dynamic + contact = absent.

### 2. Materials catalogue: 11/20
- Material count: **8** (verified by `python3 -c "import json; print(len(json.load(open('backend/app/services/materials/library.json'))['materials']))"` → 8). `library.json:5-83` lists steel-s355, aluminium-6061-t6, titanium-ti-6al-4v, steel-s275, stainless-304, cast-iron-grade-250, bronze-c93200, inconel-718.
- Standards citations: YES — each entry carries `reference` (EN 10025-2:2019, MMPDS-2023 §3.6.1.0 / §5.4.1.0, ASM Specialty Handbook, ASTM A48/A48M-22, SAE J462 + ASTM B505, AMS 5662). `library.json:12, 22, 32, 42, 52, 62, 72, 82`.
- Property completeness: E, ν, ρ, σ_y, σ_u present for all 8 (`library.json` fields `youngs_modulus_pa`, `poisson_ratio`, `density_kg_m3`, `yield_stress_pa`, `ultimate_stress_pa`).
- Value sanity check: steel-s355 E=210 GPa, σ_y=355 MPa (EN 10025 nominal — correct); inconel-718 E=200 GPa, σ_y=1034 MPa (AMS 5662 age-hardened — correct); aluminium-6061-t6 E=68.9 GPa (MMPDS 6061-T6 — correct).
- SSOT discipline: YES — single `library.json`, `app.services.materials.get_material` is the only access path, exercised end-to-end in tests (`test_phase19a_material_plumbing.py:75-81`). No inline duplication detected.
- Honest gap: 8 materials is the floor for a credible workbench. No composites, no temperature curves, no anisotropic / orthotropic entries, no plasticity hardening curves, no fatigue S-N data. Production catalogues (Abaqus, Nastran) carry thousands and include temperature dependence + plasticity tables. Score reflects "credible starter set" not "production parity."

### 3. Mesh / element fidelity: 6/20
- Element types wired into INP composer: **C3D8 only** (linear hex, 1 element). `inp_writer.py:130, 237` both write `*ELEMENT, TYPE=C3D8` with a single element comprising 8 corner nodes.
- Second-order (C3D10 tet, C3D20 hex): NOT WIRED. `viz/cell_types.py:76` knows how to visualize C3D10 if read, and `core/types/enums.py:71-72` enumerates TET4/TET10, but no INP writer emits them.
- Cross-check geometry: SINGLE C3D8 wall coupon, NOT a meshed cylinder. `cylinder_pv_runner.py:93-186` writes one hex with 8 nodes and applies the analytical traction. The runner's own docstring (lines 10-21) admits this is a "scalar wall coupon, not a full cylinder mesh."
- Gmsh integration: `services/meshing/gmsh_runner.py:40-260` exists with STEP/STL/BREP/GEO support, but it is **NOT WIRED** into `tier2_pipeline.run_tier2_minimal_hex` — that function only calls `write_minimal_hex_inp` (`tier2_pipeline.py:194-202`). Gmsh runner has its own `requires_solver` tests but no composition into the Tier 2 pipeline.
- Refinement / convergence study: NONE for Phase 19. There is a generic `test_convergence_writers.py` for output formatting but no actual h-refinement or p-refinement study against an analytical baseline. `cylinder_hoop.py:36-43` explicitly admits "single-wedge wall-coupon model with one element through thickness has an inherent ~3-5% discretisation error" — i.e., the tolerance was *relaxed* to 5% precisely to avoid doing a refinement study.
- Floor: A workbench that writes single-hex INPs and has no path from CAD geometry → mesh → INP is sub-industrial.

### 4. Cross-check / validation rigor: 11/20
- Analytical solutions implemented: ONE — thin-walled cylinder hoop stress σ = p·r/t (`cylinder_hoop.py:56-104`), with validity envelope `t/r ≤ 0.1` enforced (lines 97-102).
- Tolerance band: 5% (`cylinder_hoop.py:35`), enforced in `cylinder_pv_runner.py:257-259`. Honest disclosure of why not 2% on lines 38-43 (single-element discretisation error).
- Cases actually reaching `tier_2_validated`: **1 of 5** (verified by `find golden_samples -name cross_check_verdict.yaml` → only `cylinder-pv-candidate/cross_check_verdict.yaml`; registry has 5 cases at `_claim_tier.py:80-86`).
- Verdict file existence + content match claim: VERIFIED. `golden_samples/cylinder-pv-candidate/cross_check_verdict.yaml:4-6` shows `"verdict": "PASS"`, `"residual_pct": -0.003902...` (matches the -0.004% repo-state claim to within rounding), `"claim_tier": "tier_2_validated"`.
- Promotion mechanism: VERDICT-FILE DRIVEN, not hand-edited registry. `_claim_tier.py:89-122` runs `_apply_verdict_overlay()` at module load, reads each case's `cross_check_verdict.yaml`, and promotes when `verdict == "PASS"`. The static dict at lines 80-86 is the *baseline*; the verdict file is the *promoter*. Clean SSOT.
- The wall-coupon "cross-check" is honest about what it tests (Saint-Venant traction recovery), not what it doesn't (cylinder bending, end-cap effects, multi-element through-thickness): `cylinder_pv_runner.py:10-21`. Engineering honesty bonus.
- Honest gap: 1 analytical case (Lame thin-walled) + 1 promoted case is a starter substrate. Production validation suites have dozens (NAFEMS benchmarks, ASME pressure-vessel cases, V&V 10-2006). No buckling Euler-column cross-check, no modal closed-form (cantilever beam f₁ = (1.875²/2π)·√(EI/ρAL⁴)), no Roark plate-bending case.

### 5. Production-grade gap honesty: 4/20
Floor said max 8/20 unless ALL boxes are checked. Checking:
- Geometry import (STEP/IGES): PARTIAL — `gmsh_runner.py:57-59` accepts `.step/.stp/.stl/.brep/.geo` but the gmsh-produced mesh is NOT composed into the Tier 2 INP writer. Functionally absent end-to-end.
- Auto-meshing (Gmsh integrated for arbitrary CAD): PARTIAL — runner exists, no composition into the static/modal pipeline.
- Material plasticity / hyperelastic / damage: NO. `library.json` carries σ_y as a number but `inp_writer.py:133-134` only emits `*ELASTIC` (linear elastic); no `*PLASTIC`, no Mises/Hill, no Neo-Hookean, no damage card.
- Contact / nonlinear: NO. Grep across `backend/app/` finds zero `*CONTACT` emissions. `core/types/reader_handle.py:11` mentions contact-pair as a known *future* capability.
- Postprocessing 3D contour over arbitrary meshes: PARTIAL — `viz/cell_types.py:69-77` maps Abaqus types to VTK cells (read path), but the contour rendering presumes meshes produced by the single-hex composer. No arbitrary-CAD path through the full pipeline.

Vs. MSC Nastran / Abaqus / ANSYS: those carry SOL 101/103/105/106/107/108/109/111/112/200 (linear static / modal / buckling / nonlinear static / direct freq / direct transient / modal complex eigen / modal freq / modal transient / design opt), Abaqus has 50+ material models with plasticity (J2, Drucker-Prager, Mohr-Coulomb, Hill, Hosford, Johnson-Cook), hyperelastic (Mooney-Rivlin, Ogden, Yeoh, Arruda-Boyce), damage (Lemaitre, Gurson), full contact (penalty, augmented Lagrangian, frictional/frictionless), and read arbitrary STEP/IGES/CATIA/Parasolid. THIS workbench has: linear elastic + modal Lanczos + single C3D8 hex.

Score 4/20 reflects: linear-static + modal extraction works on a single hex; nothing else in the production checklist is wired end-to-end. Score is NOT 8/20 because partial gmsh wiring without composition is closer to "absent" than "halfway done."

## Top 3 deficiencies (file:line)

1. **`backend/app/services/tier2_pipeline.py:194-202`** — `run_tier2_minimal_hex` is hard-coded to `write_minimal_hex_inp` (single C3D8). There is no `run_tier2_meshed` function that consumes a gmsh-produced mesh + writes a multi-element INP. The gmsh runner at `backend/app/services/meshing/gmsh_runner.py` is functionally orphaned from the Tier 2 path.

2. **`backend/app/adapters/calculix/inp_writer.py:133-134`** — `*MATERIAL` block emits only `*ELASTIC`. `library.json` carries `yield_stress_pa` and `ultimate_stress_pa` per material, but the INP composer never emits `*PLASTIC`, so the workbench cannot run any nonlinear analysis even though the data is in the library. Wasted SSOT.

3. **`backend/app/services/cross_check/` directory** — only `cylinder_hoop.py` + `cylinder_pv_runner.py`. No `beam_cantilever_modal.py` (analytical f₁ for the modal step that Phase 19 C added), no `euler_buckling.py`, no `roark_plate_bending.py`. The cross-check substrate is one case; 4 of 5 cases in `_claim_tier.py:80-86` are still tier_1_candidate.

## One specific FEA improvement that would lift the lowest-scoring dimension

**Lowest = dimension 5 (production-grade gap) at 4/20.** The single highest-leverage move is to compose the existing `gmsh_runner` with `tier2_pipeline` and the INP writer:

Files to add / change:
- New `backend/app/adapters/calculix/inp_writer_meshed.py` — accepts a list of nodes + a list of elements (C3D4 / C3D10 / C3D8 / C3D20 by element-type discriminator) + material + BC set + load set, emits a multi-element INP. Reuse the material block from current `inp_writer.py`.
- New `backend/app/services/tier2_pipeline.py::run_tier2_meshed(case_dir, *, geometry_path, material_id, ...)` — calls `GmshRunner` on the geometry, parses the resulting mesh (Abaqus-format `.inp` mesh fragment that gmsh can emit directly via `-o mesh.inp -format inp`), composes via `inp_writer_meshed`, runs ccx.
- New `backend/app/services/cross_check/cantilever_modal.py` — analytical f₁ = (1.875²/(2π)) · √(EI / (ρAL⁴)) for a clamped-free beam. Cross-check the multi-element modal run against it; promotes a second case to `tier_2_validated`.
- New `backend/tests/test_phase20a_meshed_pipeline.py` with `@pytest.mark.requires_solver` — STEP-import → gmsh-mesh → ccx-static → reader check; STEP-import → gmsh-mesh → ccx-modal → cross-check.

This single composition lifts dimensions 1 (solver coverage on meshed geometry), 3 (mesh fidelity: multi-element + C3D10 path), 4 (second cross-check case + modal closed-form), and 5 (production-grade: end-to-end STEP-to-results) simultaneously. Expected uplift: +3-5 in dim 5 alone, +2 each in dims 1/3/4, total composite +9-12 toward the high 50s.
