# Functional tester report — phase 38 D (R6 calibrated re-score)

## Scenario

Full codebase audit for Rubric v2.0 Dim 1 (FEA simulation capability) and
Dim 5 (Visualization & tracking). Executed as a calibrated R6 re-score:
score anchors strictly against the RUBRIC_v2.md "What you observe" sub-bullets;
file:line evidence required for every claim.

## Verdict

- result: **partial** (strong FEA capability, visualization gap at iso-surface and E2E playwright)
- confidence: **high**
- estimated time to first-friction (engineer hours): 0.5h (GS-001 test failure is immediately visible)

---

## Dim 1 — FEA Simulation Capability

### Evidence trace

**Cohort count (13 PASS verdicts)**

All 24 `*-candidate/` directories were scanned. 13 have a `cross_check_verdict`
artifact with `verdict: PASS`:

- 12 JSON-format `cross_check_verdict.yaml` (e.g. `cantilever-beam-candidate/cross_check_verdict.yaml:14` → `"solver_kind": "linear_static"`)
- 1 real-YAML file: `hertz-contact-candidate/cross_check_verdict.yaml` line 78 → `verdict: "PASS"`, `solver_kind: "contact_pair_static"`

Remaining 11 candidates: 3 × GS-102 variants, 3 × rod-wave variants, 2 × modal-cantilever variants, 2 × cylinder-pv variants (no `cross_check_verdict.yaml`), 1 NAFEMS (`published_reference.yaml` with `verdict: "REFERENCE_ONLY"`).

**Solver kinds (6 distinct, all with PASS verdicts)**

| solver_kind | Representative case |
|---|---|
| `linear_static` | `cantilever-beam-candidate/cross_check_verdict.yaml` |
| `modal` | `cantilever-beam-modal-candidate/cross_check_verdict.yaml` |
| `buckling` | `cantilever-buckle-candidate/cross_check_verdict.yaml` |
| `dynamic` | `cantilever-dynamic-candidate/cross_check_verdict.yaml` |
| `heat_transfer_steady_state` | `heat-transfer-1d-candidate/cross_check_verdict.yaml` |
| `contact_pair_static` | `hertz-contact-candidate/cross_check_verdict.yaml:78` |

**Element classes (6 distinct, all with code evidence)**

| Element | Codebase evidence |
|---|---|
| C3D4 | `backend/app/adapters/calculix/mesh_to_inp.py:39` |
| C3D8 | `backend/app/adapters/calculix/inp_writer.py:136` |
| C3D10 | `backend/app/adapters/calculix/mesh_to_inp.py:40` |
| C3D6 | `backend/app/adapters/calculix/inp_writer.py:383` (Phase 38 B — "6th element class") |
| S4 | `backend/app/services/cross_check/plate_ss_shell_runner.py:237` |
| B31 | `backend/app/services/cross_check/buckling_b31_runner.py:150` |

**Richardson extrapolation**

`backend/app/services/cross_check/convergence_study.py:218` implements
`richardson_extrapolate()`. Of the 13 convergence study files:

- 5 have the Richardson field populated:
  - `cantilever-beam-candidate/convergence_study.json` → p=1.483, valid
  - `cantilever-beam-modal-candidate/convergence_study.json` → p=0.688, valid
  - `plate-with-hole-candidate/convergence_study.json` → p=3.871, valid
  - `plate-ss-shell-candidate/convergence_study.json` → p=2.480, valid
  - `plate-simply-supported-candidate/convergence_study.json` → p=−0.293 (anomalous; extrapolated_value=None)

- 8 remaining convergence studies are time-step sweeps (`dt_sweep`), single-mesh
  engineering notes, or explicit-dynamics sequences — not h-refinement sweeps
  and therefore not "refinable" in the Richardson sense.

**Richardson coverage = 4 valid / 5 refinable = 80%** (≥60% threshold of anchor 90 met;
approaches anchor 95's ≥80% criterion).

**p ≤ 0 guard**: `backend/app/services/cross_check/convergence_study.py:326` —
`if p <= 0.0: raise ValueError(...)` with diagnostic message. Guard is committed
and exercised by `plate-simply-supported-candidate` result. Meets anchor 90 sub-bullet.

**Asymptotic-bias revelations (2 strongly documented)**

1. `golden_samples/plate-with-hole-candidate/NOTES.md:49` — C3D4 tets under-predict
   hole-edge peak stress by 15-25% per Pilkey commentary; tolerance set to 20%.
2. `golden_samples/plate-ss-shell-candidate/convergence_study.json:47` —
   "~+1.2% ASYMPTOTIC bias … the bias persists as h→0" (S4 + Mindlin thick-shell).

A third candidate exists (`cantilever-dynamic-candidate/NOTES.md:113`
"numerical-noise bias near the peaks") but is weaker — not a clean mesh-convergence
asymptotic statement.

**NAFEMS evidence**: `golden_samples/nafems-le10-thick-plate-candidate/published_reference.yaml`
records the LE10 target stress (−5.38 MPa) with ISBN citation but sets
`verdict: "REFERENCE_ONLY"` and `analytical_only: true`. No CalculiX solve has been
run against the benchmark. The file is deliberately **not** named
`cross_check_verdict.yaml` (NOTES.md §"Honest correction of the Phase 38 blueprint").
→ NAFEMS agreement evidence is **absent** per rubric definition (no `residual_pct`
vs. published target from a real solve).

**Failed-attempt corpus**: `.planning/failed_attempts/INDEX.md` — 7 indexed entries
(plate-ss-shell-pivot, heat-transfer-pivot-from-contact, richardson-p-le-0-guard,
hertz-contact-analytical-only-deferral, contact-pair-stacked-cube-pivot,
phase35b-strict-additive-schema, phase33d-errorcard-rollback).

### Anchor determination — Dim 1

**Anchor 90 checklist** (all sub-bullets verified):

| Sub-bullet | Status | Evidence |
|---|---|---|
| ≥12 validated cases | ✓ (13) | 12 JSON + 1 YAML PASS verdicts |
| ≥5 solver kinds + contact OR heat | ✓ (6 kinds, contact + heat both present) | solver_kind values above |
| Richardson ≥60% refinable | ✓ (4/5 = 80%) | convergence_study.py:218 + 5 studies |
| ≥2 bias revelations | ✓ | plate-with-hole NOTES.md:49, plate-ss-shell CS:47 |
| ≥4 element classes (C3D4/8/10 + S3/4 OR B31) | ✓ (6 classes) | table above |
| p ≤ 0 guard implemented | ✓ | convergence_study.py:326 |

→ **All of anchor 90 met.**

**Anchor 95 blockers**:

| Sub-bullet | Status | Gap |
|---|---|---|
| ≥15 validated cases | ✗ | 13 present, 2 short |
| Richardson ≥80% refinable | ✓ (80%) | Met |
| ≥3 bias revelations | borderline | 2 strong, 1 weak |
| ≥1 NAFEMS test problem agreement evidence | ✗ | REFERENCE_ONLY, no residual |
| ≥6 element classes | ✓ | 6 classes present |
| Failed-attempt corpus indexed | ✓ (7 entries) | Meets "indexed" |

→ Anchor 95 blocked by cohort count (13 < 15) and NAFEMS REFERENCE_ONLY.

**Interpolation**: anchor 90 fully met + 3/6 sub-bullets of anchor 95 met
(Richardson ≥80%, 6 element classes, failed-attempt indexed) + 2 partial (3rd bias revelation borderline,
NAFEMS present as reference but not as solve) = ~1/2 of anchor 95 delta completed.

**Dim 1 score: 91** (all of 90 met + ~1/5 of the 90→95 gap cleared)

---

## Dim 5 — Visualization & Tracking

### Evidence trace

**3D viewport + static contour** (`ResultMeshWebGLViewport.tsx:125`)
Three.js WebGL renderer for displacement/vM contour with color gradient. Present
since Phase 22.

**Probe list** (`ProbeListPanel.tsx:78`) — click node, capture (x,y,z,value).
Probe persistence via `probeListStorage.ts:63` — `localStorage` keyed by `case_id`;
loaded on mount at `ProbeListPanel.tsx:98` → `loadProbeList`.

**Section cuts** (`ResultMeshPlaybackPanel.tsx:131` →`useState<SectionCutState>`)
Passed as prop to `ResultMeshWebGLViewport.tsx:132` → `sectionCut` → `clippingPlane`
at `ResultMeshWebGLViewport.tsx:288`. Axes x/y/z all supported via
`axisIdx = { x:0, y:1, z:2 }[sectionCut.axis]`.

**Companion viewport** (`CompanionViewport.tsx:6`)
"Renders a SECOND ResultMeshWebGLViewport … Hyperworks/Abaqus-CAE-style
compare-cuts 2-quadrant layout." Independent section-cut state; shared
field/component/threshold/playback. Wired in `ResultMeshPlaybackPanel.tsx:163-252`.
This satisfies anchor 90 sub-bullet "comparison cuts (overlay two results)".

**Time-series scrubber** (`ResultMeshPlaybackPanel.tsx:333` aria-label="OpenRadioss dynamic
playback") — frame scrubber for explicit-dynamics/modal step animation. Wired to
`ResultMeshWebGLViewport.tsx` via `selectedFrame` / `nextFrame`.

**WebGL + SVG dual-render fallback** (`ResultMeshWebGLViewport.tsx:114-220`)
`webglcontextlost` listener at line 220; emits event to parent which
"fall[s] back to the SVG render path" (comment at line 117). SVG fallback at
`ResultMeshPlaybackPanel.tsx:404`.

→ **All of anchor 80 met.**

**Anchor 90 sub-bullet checks**:

| Sub-bullet | Status | Evidence |
|---|---|---|
| Iso-surface rendering | ✗ ABSENT | grep for `iso.surface\|isoSurface\|isosurface\|isovalue\|marchingCube` returns no results in `frontend/src/` |
| CSV export | ✓ PRESENT | `ProbeListPanel.tsx:277` — `a.download = 'probe-list-${stamp}.csv'` |
| Real WebGL E2E playwright (not jsdom) | ✗ ABSENT | `find frontend/e2e/` returns no directory or spec files |
| Comparison cuts (overlay two results) | ✓ PRESENT | `CompanionViewport.tsx:6` — Hyperworks-style compare-cuts 2-quadrant |

2/4 anchor-90 sub-bullets met; 2 absent (iso-surface, playwright E2E).

**VTU export**: `backend/app/viz/vtu_exporter.py:1` generates `.vtu` frame files;
served at `backend/app/api/routes/visualization.py:123`
(`GET /result-mesh/{case_id}/{artifact_path:path}`). However, no frontend UI
button to trigger VTU download was found — the VTU path is a backend artifact
accessible via direct API call but not surfaced as a one-click export in the UI.

**Performance**: `ResultMeshWebGLViewport.tsx:69` targets 60fps via
`requestAnimationFrame`. No committed performance benchmark artifact (no
`.planning/perf/viz_benchmark.md`). Anchor 95 ("≥30fps for ≥100k nodes")
cannot be verified without the benchmark artifact.

**Provenance overlays**: `ProvenancePanel.tsx` is a side panel that displays
trust-score provenance for `(caseId, snapshotLabel)` — mounted in
`VisualTabPanel.tsx:176-188`. This is a side panel, NOT an overlay on the viewport
frame itself. Anchor 95 requires "every viz frame links back to its case-id /
snapshot-id / signoff-id" as an overlay; this implementation is a companion panel,
not an in-frame overlay.

### Anchor determination — Dim 5

**Anchor 80 met** (all 4 sub-bullets confirmed with evidence).

**Anchor 90**: 2/4 sub-bullets met (CSV export + comparison cuts). Iso-surface
and playwright E2E absent.

**Interpolation**: 80 + 2/4 × (90−80) = 85. Giving slight credit for VTU
being available at the API layer (even without UI button), round to 84.

**Dim 5 score: 84**

---

## Stage trace

| Stage | Codepath | Test pinned | Status | Evidence |
|---|---|---|---|---|
| INP write (linear static C3D8) | `backend/app/adapters/calculix/inp_writer.py:67-170` | `test_phase18a_calculix_runner.py` | ✓ | `TYPE=C3D8` at line 136 |
| INP write (C3D6 wedge) | `inp_writer.py:280-400` | `test_phase38b_wedge_c3d6.py` | ✓ | `TYPE=C3D6` at line 383; 15 passed 0 failed |
| Mesh→INP (C3D4/C3D10) | `mesh_to_inp.py:39-232` | `test_phase20c_meshed_pipeline.py` | ✓ | gmsh type 4→C3D4, type 11→C3D10 |
| Cross-check verdict (JSON) | `golden_samples/*-candidate/cross_check_verdict.yaml` | `test_phase35b_verdict_yaml_solver_kind_backfill.py` | ✓ | 41 passed |
| Cross-check verdict (YAML, hertz) | `golden_samples/hertz-contact-candidate/cross_check_verdict.yaml` | `test_phase38f_tier_surface_at_api.py` | ⚠ partial | 15 passed; 5 errors (fastapi import missing in env) |
| Richardson extrapolation | `convergence_study.py:218` | `test_convergence_writers.py` | ✓ | 192 passed (modern tests) |
| NAFEMS reference | `nafems-le10-thick-plate-candidate/published_reference.yaml` | `test_phase38a_nafems_le10_verdict.py` | ✓ | All 15 passed; guards tautological-PASS correctly |
| WebGL viewport | `ResultMeshWebGLViewport.tsx:125-690` | `frontend/test/Phase30B_companion_viewport.test.tsx` | ✓ | Component exists, tests present |
| Probe persistence | `probeListStorage.ts:63` + `ProbeListPanel.tsx:98` | `frontend/test/Phase27D_probe_persist_tour_refresh.test.tsx` | ✓ | localStorage key per caseId |
| Section cut | `ResultMeshWebGLViewport.tsx:288-296` | `frontend/test/Phase29B_section_frame_collapse.test.tsx` | ✓ | clipping plane per x/y/z axis |
| Companion viewport | `CompanionViewport.tsx:6-250` | `frontend/test/Phase30B_companion_viewport.test.tsx` | ✓ | compare-cuts 2-quadrant |
| CSV export (probe) | `ProbeListPanel.tsx:269-283` | `frontend/test/Phase26C_probe_diff_column.test.tsx` | ✓ | Blob URL `probe-list-*.csv` |
| Iso-surface | — | — | ✗ ABSENT | No code or test found anywhere |
| WebGL E2E playwright | — | — | ✗ ABSENT | No `frontend/e2e/` directory |

---

## Broken handoffs

None in the primary production flow (candidate path → INP → verdict → API → frontend).

The `test_phase38f_tier_surface_at_api.py` has 5 errors on collection due to `ModuleNotFoundError: No module named 'fastapi'` in the test environment. This is an environment issue (missing dependency), NOT a code handoff break. The tests themselves are correctly wired.

---

## Silent failures

None detected in the candidate production pipeline.

---

## Dead-code suspects

None found.

---

## Test suite run

**Command**: `python3 -m pytest tests/test_phase35b_verdict_yaml_solver_kind_backfill.py tests/test_phase38a_nafems_le10_verdict.py tests/test_phase38b_wedge_c3d6.py tests/test_calculix_adapter.py tests/test_convergence_writers.py tests/test_ballistic_metric_extraction.py tests/test_ballistics.py tests/test_boundary_summary.py tests/test_animation_manifest.py tests/test_allowable_stress.py -q --override-ini="addopts="`

**Result: 192 passed, 9 skipped, 0 failed**

**Separate run — legacy test failure**:
`python3 -m pytest tests/test_golden_samples.py -q --override-ini="addopts="`
→ **1 FAILED, 26 passed**

Failure: `TestGS001Cantilever::test_gs001_displacement_uy`
- Expected: `-493.56` (mm-scale, from `GS-001/expected_results.json`)
- Observed: `-0.493560` (m-scale, from FRD reader)
- Root cause: GS-001 INP was written in mm (`gs001.inp:7` — node coords 0.0, 10.0, 20.0 … 100.0 for a 100 mm beam), but the FRD reader returns displacement in SI meters. The expected_results.json stores the expected value in mm (-493.56) but the reader returns -0.4936 m.
- Scope: This is the **pre-Phase-20 legacy GS-001 fixture**. The production `*-candidate/` cohort (Phase 20+) uses SI units throughout and does NOT have this defect. The failing test has no `@pytest.mark.legacy` decoration and thus runs in the default sweep. It would fail in any CI run with proper dependencies.

This is a **medium-severity finding**: a live test failure in `test_golden_samples.py` with no legacy marker. However it does not affect the production FEA pipeline.

---

## Rubric v2.0 dim contribution

**Dim 1 (FEA simulation capability): 91 / 100**

- Anchor 90 fully met: cohort 13 (≥12 ✓), 6 solver kinds (≥5 + contact + heat ✓), Richardson 80% of refinable (≥60% ✓), 2 bias revelations (≥2 ✓), 6 element classes (≥4 ✓), p≤0 guard ✓.
- Anchor 95 blocked: cohort 13 < 15 required; NAFEMS evidence is REFERENCE_ONLY (no ccx solve, no residual).
- ~1/5 of 90→95 delta cleared (Richardson 80% ✓, 6 element classes ✓, failed-attempt corpus ✓).
- Score: **91**

**Dim 5 (Visualization & tracking): 84 / 100**

- Anchor 80 fully met: 3D WebGL viewport, probe list + persistence, section cuts (x/y/z), companion viewport (compare-cuts), time-series scrubber, WebGL+SVG fallback.
- Anchor 90 partial (2/4): CSV probe export ✓, comparison cuts (CompanionViewport) ✓; iso-surface ABSENT, playwright WebGL E2E ABSENT.
- Score: **84**

---

## HIGH-SEVERITY functional findings

1. **`test_golden_samples.py::TestGS001Cantilever::test_gs001_displacement_uy` — LIVE TEST FAILURE**
   - File: `backend/tests/test_golden_samples.py:79`
   - Expected: `−493.56` (mm), Observed: `−0.493560` (m); 99.9% relative error
   - No `@pytest.mark.legacy` marker → runs in default sweep → CI failure
   - Recommended fix: either add `@pytest.mark.legacy` to the class, or correct the expected value to match SI (−0.49356), or update `GS-001/expected_results.json` to SI.

2. **Iso-surface rendering: completely absent**
   - No code for iso-surface, marching cubes, or isovalue threshold in `frontend/src/`
   - Blocks anchor 90 sub-bullet; required before Dim 5 can clear 90.

3. **No Playwright E2E WebGL test suite**
   - `frontend/e2e/` directory does not exist
   - Blocks anchor 90 sub-bullet; required before Dim 5 can clear 90.
   - The existing frontend tests use jsdom (vitest), which cannot exercise WebGL.

---

*Report generated by functional-tester sub-agent (R6 calibrated re-score). Phase 38 D.*
*Codebase root: `/Users/Zhuanz/20260408 AI StructureAnalysis`*
*Anti-gaming guards honoured: D:-1 (file:line evidence), F:-1 (no prior audit files read), G:-1 (no README/comment trust).*
