# hertz-contact-analytical-only-deferral — Phase 33 D

## Trigger
Phase 33 D's blueprint slot called for a complete Hertz line-contact
case: analytical SSOT + live ccx integration + verdict file. Three
constraints emerged during scoping:
1. **Session budget**: a complete `*CONTACT PAIR` runner (~600+ LOC)
   alongside the ccx authoring iteration would not fit in the
   Phase 33 D session.
2. **Geometry/load regime**: the canonical input inputs (F=1000N,
   R=0.010m) yield a Hertzian peak pressure
   p₀ = 428.5 MPa — exceeding the S355 yield (355 MPa) by ~21%.
   Without a plasticity model, the case can't honestly claim
   tier_2_validated.
3. **ADR-002 CanonicalField enum**: the canonical field set
   excludes CDIS/CSTR contact-output fields. Phase 33 D couldn't
   extend the enum on its own — that's a downstream ADR review.

## Decision
Ship the **analytical SSOT only** at Phase 33 D
(`backend/app/services/cross_check/hertz_contact.py`, ~161 LOC),
pinned to Johnson "Contact Mechanics" (Cambridge, 1985) §4.2 with
every formula bracket-cited. Scaffold the directory
(`golden_samples/hertz-contact-candidate/`) with `expected_results.json
+ NOTES.md` documenting the deferral honestly. Defer live ccx to
Phase 34. Document the geometry/load re-tune (R=0.050m, F=5000N →
p₀ ≈ 271 MPa elastic) for Phase 34 to consume.

## Evidence
- Deciding commit: see git log Phase 33 D
- Surviving analytical SSOT:
  `backend/app/services/cross_check/hertz_contact.py`
  (every formula cites Johnson §4.2 brackets)
- Phase 33 D scaffold directory:
  `golden_samples/hertz-contact-candidate/`
- Phase 33 D NOTES.md documents the geometry/load re-tune target

## Closure status
CLOSED via Phase 34 C **with an honest pivot** — instead of doing
the Hertz curvature live ccx, Phase 34 C shipped stacked-cube
uniaxial geometry (1D-EXACT analytical, no Hertz curvature),
preserving the Phase 33 D analytical SSOT verbatim for a future
phase that does take on cylinder-meshing + plasticity.

See companion entry [contact-pair-stacked-cube-pivot](./contact-pair-stacked-cube-pivot.md).

## Lessons
1. Analytical SSOT + scaffolded directory + honest deferral notes
   ≫ "skip the slot entirely". The analytical SSOT becomes
   load-bearing for the future closure, even when the closure
   takes a different geometric form.
2. Geometry/load regime matters: pencil-and-paper Hertz can claim
   beautiful elastic contact while real session-budget meshes hit
   yield. Plan the geometry around the operating envelope.
