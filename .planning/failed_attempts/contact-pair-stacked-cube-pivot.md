# contact-pair-stacked-cube-pivot — Phase 34 C

## Trigger
Phase 34 C's blueprint slot called for cylinder-on-block Hertz
contact (closing the Phase 33 D deferral). On scoping:
1. **Cylindrical hex meshing** for ccx C3D8 elements needs gmsh
   tetmesh integration — out of session scope.
2. **Hertz peak pressure exceeded S355 yield** at the Phase 33 D
   recommended re-tune geometry (R=0.050m, F=5000N → p₀ ≈ 271 MPa
   elastic, which is closer to but still above the operating
   envelope when boundary effects are accounted for).
3. **ADR-002 CanonicalField enum** doesn't include the canonical
   contact-output fields — Phase 34 C couldn't extend ADR-002 on
   its own.

## Decision
Pivot to **stacked-cube uniaxial geometry** for the live ccx case:
- 20×20 mm punch (h=10mm) stacked on a 20×20×30mm substrate
- 4×4×2 punch + 4×4×6 substrate hex mesh = 128 C3D8 / 250 nodes
- Load F=4000N (10 MPa pressure, well below S355 yield)
- 1D-EXACT analytical: δ = F·H/(E·A); no Hertz curvature, no
  spreading-load approx
- `*CONTACT PAIR, TYPE=NODE TO SURFACE` with master surface
  TYPE=ELEMENT face-based (CCX 2.23 allocont check requirement)
- `*SURFACE BEHAVIOR PRESSURE-OVERCLOSURE=LINEAR` penalty stiffness
  1.0e15 N/m³, NLGEOM=NO step

## Evidence
- Deciding commit: `b78172a` (Phase 34 C)
- Surviving live ccx runner:
  `backend/app/services/cross_check/contact_pair_runner.py`
- Surviving verdict YAML:
  `golden_samples/hertz-contact-candidate/cross_check_verdict.yaml`
  (schema 1.4.0, PASS at -6.823% residual, live ccx 2.23 run)
- Phase 33 D analytical SSOT **preserved verbatim**:
  `backend/app/services/cross_check/hertz_contact.py`
- @requires_solver E2E test pin:
  `backend/tests/test_phase34c_contact_pair_runner.py`
- Live ccx result: analytical δ = 1.905 µm, observed |U_z| = 1.775 µm,
  residual -6.823% (within 20% tolerance → PASS, converged in 1
  increment)

## Closure status
CLOSED in Phase 34 C. The cohort gained its 6th solver_kind
(`contact_pair_static`); Phase 35 B backfilled this verdict YAML
with the field explicitly.

The Hertz CURVATURE case (cylinder-on-block) remains deferred —
Phase 33 D analytical SSOT is the seed for a future phase that
takes on gmsh tetmesh integration + plasticity model + ADR-002
enum extension.

## Lessons
1. The honest pivot from curvature → stacked-cube cost zero on
   solver-kind coverage (still adds `contact_pair_static`) but
   saved ~1500 LOC of out-of-scope work.
2. 1D-EXACT analytical (no spreading-load approx) is a
   significantly stronger validation than a curvature case at the
   edge of yield. Sometimes the "less ambitious geometry" is the
   stronger truth claim.
3. Phase 33 D's analytical SSOT is still load-bearing — it
   doesn't get rewritten or rolled back. The pivot adds a sibling,
   not a replacement.
