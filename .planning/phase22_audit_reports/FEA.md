# Phase 22 — FEA audit (Round 1)

> **Frame:** Tier 1 / Tier 2 engineering candidate; not signed
> validation; not benchmark agreement. Phase 21 baseline FEA = 68/100.
> Blueprint FEA projection: 70-75 (mid 72.5). Honest scope reduction
> on buckling Tier 2 promotion noted verbatim below.

## Dimensions

### Dim 1 — Element library breadth (0-100)

**Score: 72/100.** +6 from Phase 21 (66). Phase 22 A added C3D10
quadratic tetrahedral elements with verified gmsh → ccx node-order
permutation `(0,1,2,3,4,5,6,7,9,8)`. C3D10 cantilever residual at
cl=0.025m fell below 5% (vs C3D4 at -6.88% at cl=0.015m and -16.4%
at cl=0.025m). Three element kinds now wired (C3D4 / C3D8 / C3D10).

Evidence:
- `backend/app/adapters/calculix/mesh_to_inp.py` — `_GMSH_TYPE_TO_CCX`
  map + `_C3D10_GMSH_TO_CCX_PERM` + applied in `parse_gmsh_msh22`.
- `backend/tests/test_phase22a_quad_tets_buckling.py` — C3D10
  wiring pins + cantilever C3D10 residual < 5% E2E pin.

Gap to 99: no C3D6 wedge, no C3D15 wedge, no S3/S4 shells, no
B31 beams. Each is multi-week scope.

### Dim 2 — Validated cross-check cases (0-100)

**Score: 64/100.** Held flat from Phase 21 (64). The blueprint
projected `validated count 3 → 4` via the euler-column buckling
case. Phase 22 A built the runner infrastructure (`buckling_euler.py`
+ `buckling_runner.py`, 490 LOC, 20 tests) but the solid-element
buckling eigenvalue landed ~10× the analytical Euler load on the
canonical 1m × 10×10mm steel column (37,360 N observed vs 1,727 N
analytical). **Honest scope reduction:** Phase 22 A ships the
buckling RUNNER as INFRASTRUCTURE verification only; verdict on
`euler-column-candidate` is FAIL; the case stays at
`tier_1_candidate`; validated count stays at 3.

Evidence:
- `golden_samples/euler-column-candidate/NOTES.md` — canonical
  geometry doc, no verdict file at tier_2_validated.
- `backend/tests/test_phase22a_quad_tets_buckling.py` — buckling
  runner pin honestly expects `verdict == 'FAIL'` (the runner ran;
  the solid-vs-Euler idealization mismatch produced the failure;
  test pins that the failure was DETECTED correctly).
- `backend/app/services/cross_check/buckling_runner.py` — clear
  comment block in front of the runner documenting the solid-vs-
  Euler-vs-beam-element scope gap.

Gap to 99: the proper Phase 23+ path is a Timoshenko beam-element
(B31) runner that matches the 1D Euler-Bernoulli idealization,
plus revisiting solid C3D8 buckling with refined cross-section
mesh (the 1×1 hex per cross-section is too coarse for buckling
mode shape capture).

### Dim 3 — Mesh fidelity (0-100)

**Score: 71/100.** +5 from Phase 21 (66). C3D10 promotes the
cantilever residual from 6.88% (linear tets) to <5% (quadratic
tets) at the same characteristic length. The mesh-refinement
study infrastructure (Phase 20) now has a denser element type
in its convergence-knob toolbox.

Evidence:
- `backend/tests/test_phase22a_quad_tets_buckling.py` —
  `test_phase22a_cantilever_c3d10_residual_below_5pct`
  requires_solver E2E pin.

Gap to 99: no adaptive remeshing, no anisotropic refinement, no
mesh-quality auto-flagging on aspect ratio / skewness, no
boundary-layer prismatic mesh option for contact / friction
problems.

### Dim 4 — Solver kind coverage (0-100)

**Score: 64/100.** +2 from Phase 21 (62). The buckling runner
EXISTS and CAN call `*STEP, PERTURBATION` + `*BUCKLE 4` and parse
the eigenvalues from ccx's .dat output. The runner produces a real
verdict (FAIL on the current solid-element idealization). This
adds genuine new SOLVER KIND coverage to the harness, even though
no case promoted.

Evidence:
- `backend/app/services/cross_check/buckling_runner.py` — handles
  ccx 2.21+ "BUCKLING FACTOR OUTPUT" header and legacy
  "EIGENVALUE OUTPUT" header.
- `backend/app/services/cross_check/__init__.py` — exports buckling
  symbols.

Gap to 99: no transient dynamics (`*DYNAMIC`), no Riks arc-length
(`*STEP, RIKS`), no implicit dynamics, no contact + friction. Each
is multi-phase scope.

### Dim 5 — Cross-check rigor (0-100)

**Score: 81/100.** Held flat from Phase 21 (81). The Phase 21 A
cantilever + Kirsch verdict YAMLs are byte-stable; the Phase 22 A
buckling runner adds one more verdict YAML (with FAIL verdict) to
the SSOT schema. The `_claim_tier.py` overlay logic correctly
keeps `euler-column-candidate` at tier_1 because the FAIL verdict
disqualifies it from promotion.

Evidence:
- All 3 existing verdict YAMLs (cantilever, plate, cylinder)
  continue to drive Phase 22 promotion via Phase 21 A overlay
  mechanism.
- `backend/app/services/reporting/_claim_tier.py` — registry
  includes `"euler-column-candidate": "tier_1_candidate"`.

Gap to 99: no automated daily promotion run, no CI cross-check
that re-runs all runners and stamps verdict timestamps, no
distributed cross-check across N reviewer copies for
reproducibility audit.

## Composite

| Dim | Phase 21 | Phase 22 | Delta |
|---|---|---|---|
| Element library | 66 | 72 | +6 |
| Validated cases | 64 | 64 | 0 (honest miss) |
| Mesh fidelity | 66 | 71 | +5 |
| Solver kind coverage | 62 | 64 | +2 |
| Cross-check rigor | 81 | 81 | 0 |
| **FEA composite** | **67.8** | **70.4** | **+2.6** |

**FEA axis: 70.4/100.** Inside blueprint band (70-75) at the low
end. The honest gap to the projection band's midpoint (72.5) is
the buckling promotion miss — Phase 22 A built the infrastructure
but the case didn't promote. Documented verbatim; no score reshape.

Not signed validation; not benchmark agreement.
