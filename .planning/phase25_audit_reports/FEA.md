# Phase 25 — FEA audit (Round 1)

> **Frame:** Tier 1 / Tier 2 engineering candidate; not signed
> validation; not benchmark agreement. Phase 24 baseline FEA = 74.8/100.
> Blueprint FEA projection: 76-77 (mid 76.5).

## Dimensions

### Dim 1 — Element library breadth (0-100)

**Score: 75/100.** Held flat from Phase 24 (75). Phase 25 A reuses
the existing C3D10 quadratic-tet path (Phase 22 A's element library
addition). No new element types in Phase 25.

Gap to 99: see Phase 23/24 list (S3/S4 shells, C3D6/C3D15 wedges,
T3D2 truss).

### Dim 2 — Validated cross-check cases (0-100)

**Score: 75/100.** +4 from Phase 24 (71). Phase 25 A promotes
`plate-simply-supported-candidate` to tier_2_validated. **Validated
count 4 → 5** (cylinder-pv + cantilever-beam + plate-with-hole +
euler-column + plate-simply-supported).

Live ccx run (2026-05-17): analytical w_center = -0.2639 mm vs
observed -0.2486 mm → residual **-5.79%** (well inside 15% tolerance,
9.21% margin). The plate-SS case adds GENUINELY NEW physics regime —
distributed-load plate bending under Kirchhoff thin-plate theory,
distinct from the 4 prior regimes (thin-walled hoop / Euler-
Bernoulli cantilever / Kirsch stress concentration / Euler buckling).

Evidence:
- `golden_samples/plate-simply-supported-candidate/cross_check_verdict.yaml`
  — PASS verdict, runner=`plate_ss_runner`, residual -5.79%.
- `backend/app/services/cross_check/plate_simply_supported.py` —
  Timoshenko α=0.00406 analytical with Roark / Timoshenko
  citations + validity-envelope refusals (a/t ≥ 20, w/t ≤ 0.2).
- `backend/app/services/cross_check/plate_ss_runner.py` (~390 LOC)
  — self-contained runner: gmsh + parse_msh + hand-rolled INP
  (4-edge u_z=0 clamp + 3-corner RBM pin + pressure-equivalent
  nodal load) + ccx + .frd center-node read.
- `backend/tests/test_phase25a_plate_ss_runner.py` — 14 tests
  including A:-1 anti-gaming guard (center-node-selection lands
  at geometric center, NOT corner/edge).
- `test_phase25a_validated_count_is_five` strict registry pin.

Gap to 99: no contact mechanics, no transient dynamics, no
thermal-expansion, no fatigue, no fracture — each is a multi-week
extension.

### Dim 3 — Mesh fidelity (0-100)

**Score: 74/100.** +1 from Phase 24 (73). The plate-SS runner
defaults to C3D10 quadratic tets with cl_max=0.060 m, yielding
~4,420 nodes / 2,125 elements on a 1m × 1m × 20mm plate (a/t=50).
This is roughly 2 elements through thickness — appropriate for the
thin-plate envelope but not deeply refined.

Evidence:
- Live run mesh: 4420 nodes / 2125 C3D10 tets.
- 5.79% residual demonstrates the mesh resolves the bending
  field adequately within the 15% honest envelope.

Gap to 99: see Phase 22/23/24 list (adaptive remeshing, aniso
refinement, quality auto-flagging, boundary layer).

### Dim 4 — Solver kind coverage (0-100)

**Score: 68/100.** Held flat from Phase 24 (68). The plate-SS
cross-check uses linear-static (same solver kind as Phase 20 B/C
+ Phase 21 A's cantilever and Kirsch). No new solver kind
introduced.

Gap to 99: transient (*DYNAMIC), Riks arc-length (*STEP, RIKS),
implicit dynamics, contact, thermal coupling.

### Dim 5 — Cross-check rigor (0-100)

**Score: 88/100.** +1 from Phase 24 (87). The plate-SS analytical
reference is a new analytical TYPE — closed-form coefficient from
Timoshenko / Roark tables, distinct from the closed-form formulas
of Phase 19-23 (σ=pr/t / PL³/3EI / K=3.74·σ_∞ / P_cr=π²EI/L²).
Validity envelope is enforced at the analytical helper level
(refuses a/t < 20 and surfaces w/t to the verdict for audit).

Evidence:
- PlateSimplySupportedValidityError refuses thick plates with
  citation hint to Timoshenko §61 (Mindlin-Reissner regime).
- Verdict YAML carries `small_deflection_ratio` for the audit
  trail.

Gap to 99: see Phase 24 list — tensor schema is additive optional
on OpenRadioss path only; CalculiX static path has no result_mesh
writer (deferred); plate principal-direction vectors not surfaced.

## Composite

| Dim | Phase 24 | Phase 25 | Delta |
|---|---|---|---|
| Element library | 75 | 75 | 0 |
| Validated cases | 71 | 75 | +4 |
| Mesh fidelity | 73 | 74 | +1 |
| Solver kind coverage | 68 | 68 | 0 |
| Cross-check rigor | 87 | 88 | +1 |
| **FEA composite** | **74.8** | **76.0** | **+1.2** |

**FEA axis: 76.0/100.** Inside blueprint band (76-77) at the LOW
end (just at lower bound). The +1.2 lift is driven by the 5th
validated case promotion — exactly the Phase 24 retro punchlist
item #3. Validated count moved 4 → 5 with -5.79% residual; honest
scope (linear-static reuse, no new solver kind, no new element
type) is named verbatim.

Not signed validation; not benchmark agreement.
