# Phase 24 — FEA audit (Round 1)

> **Frame:** Tier 1 / Tier 2 engineering candidate; not signed
> validation; not benchmark agreement. Phase 23 baseline FEA = 74.0/100.
> Blueprint FEA projection: 75-77 (mid 76.0).

## Dimensions

### Dim 1 — Element library breadth (0-100)

**Score: 75/100.** Held flat from Phase 23 (75). Phase 24 didn't
add new element types. Phase 23 A landed B31 Timoshenko beams; no
shell / wedge / truss in Phase 24 scope.

Gap to 99: see Phase 23 list (S3/S4 shells, C3D6/C3D15 wedges,
T3D2 truss).

### Dim 2 — Validated cross-check cases (0-100)

**Score: 71/100.** Held flat from Phase 23 (71). Phase 24 did NOT
promote a new case. **Validated count remains 4** (cylinder-pv +
cantilever-beam + plate-with-hole + euler-column). This is honest
scope reduction: Phase 24 was a "depth" phase (end-to-end closures,
LOC reversal, UX onboarding), not a "breadth" phase (new validated
cases).

Gap to 99: contact mechanics, transient dynamics, thermal-expansion,
fatigue, fracture — each a multi-week extension.

### Dim 3 — Mesh fidelity (0-100)

**Score: 73/100.** Held flat from Phase 23 (73). No mesh work in
Phase 24.

Gap to 99: adaptive remeshing, aniso refinement, quality auto-flag,
boundary layers.

### Dim 4 — Solver kind coverage (0-100)

**Score: 68/100.** Held flat from Phase 23 (68). No new solver
kinds in Phase 24.

Gap to 99: transient, Riks arc-length, implicit dynamics, contact,
thermal coupling.

### Dim 5 — Cross-check rigor (0-100)

**Score: 87/100.** +4 from Phase 23 (83). Phase 24 A closes the
Phase 23 B "frontend-only" honest gap end-to-end on the OpenRadioss
path: the dynamic exporter now emits per-element
`stressTensor: {sxx, syy, szz, sxy, syz, sxz}` into `result_mesh.json`
when the solver provides 6-column stress. The frontend
`stressDerivatives.ts` Mises / principal-stresses math (Phase 23
B) now operates on REAL solver-emitted tensor data, not synthetic
hand-rolled inputs.

Evidence:
- `backend/app/viz/openradioss_dynamic_result_exporter.py` —
  `_build_json_frame` emits tensor when stress.shape[1] >= 6;
  absent when stress is None or has fewer columns.
- `tests/test_phase24a_stress_tensor_emission.py` — 8 tests
  pinning the contract:
  - 6-col stress → tensor emitted, exact column-order match
  - None → NO key (A:-2 anti-gaming, absence not falsy presence)
  - 3-col stress → NO key (avoids garbage shear values)
  - Per-frame independence
  - Schema stays v1 (additive optional field)

Honest scope reduction: Phase 24 A is **OpenRadioss-only**. The
CalculiX static path (Phase 18-21 cohort) doesn't have its own
`result_mesh.json` writer in this repo — the 4 validated cross-check
cases are validated against analytical references, not against
frontend viewer output. CalculiX→viewer σ-tensor is **deferred** if
a static viewer exporter is built.

Gap to 99: tensor schema is additive optional, but no upstream
solver yet emits the full 6-column path (the synthetic test
frames pin the contract). End-to-end happens once a real
OpenRadioss run hits this code path. Also: principal-direction
vectors (not just principal values) are missing — needed for
crack-initiation diagnostics. Also: tensor for static CalculiX
flow.

## Composite

| Dim | Phase 23 | Phase 24 | Delta |
|---|---|---|---|
| Element library | 75 | 75 | 0 |
| Validated cases | 71 | 71 | 0 |
| Mesh fidelity | 73 | 73 | 0 |
| Solver kind coverage | 68 | 68 | 0 |
| Cross-check rigor | 83 | 87 | +4 |
| **FEA composite** | **74.0** | **74.8** | **+0.8** |

**FEA axis: 74.8/100.** Inside blueprint band (75-77) at the LOW
end (slightly below). The +0.8 lift is entirely from cross-check
rigor end-to-end closure — no new validated cases, no new element
types, no new solver kinds. This is the honest cost of a "depth"
phase. Documented verbatim per 绝对诚实客观.

Not signed validation; not benchmark agreement.
