# heat-transfer-pivot-from-contact — Phase 31 A

## Trigger
Phase 31 A's original blueprint slot was a 2D contact-mechanics
case (Hertz line-contact OR a simple punch-on-block). Two
constraints emerged during scoping:
1. Live ccx `*CONTACT PAIR` requires `*SURFACE INTERACTION` +
   `*SURFACE BEHAVIOR PRESSURE-OVERCLOSURE=LINEAR` with master
   surface composition (TYPE=ELEMENT face-based) — a non-trivial
   INP authoring task that the Phase 31 A session budget could not
   absorb alongside the analytical SSOT.
2. At session-budget geometry (small radius + moderate load), the
   Hertzian peak pressure exceeded the S355 yield stress — the
   case would have shipped as "tier_1_candidate, plasticity NOT
   modelled, residual undefined" which isn't useful as a tier_2
   target.

## Decision
Pivot the Phase 31 A slot from contact to 1D steady-state heat
transfer (`heat-transfer-1d-candidate`). Heat transfer has:
- Trivial analytical solution (linear Fourier profile T(x) =
  T_left + (T_right - T_left) · x/L for steady-state conduction)
- Trivial mesh authoring (any C3D8 hex with two opposite-face
  fixed-temperature BCs)
- Solver kind diversity benefit — heat_transfer_steady_state is
  the 5th distinct kind in the cohort, closing a Dim 1 90-anchor
  sub-bullet (5 kinds)

The contact-mechanics slot was re-scoped to Phase 33 D analytical
SSOT + Phase 34 C live ccx (stacked-cube uniaxial).

## Evidence
- Deciding commit: see git log Phase 31 A commits shipping
  `backend/app/services/cross_check/heat_transfer_runner.py`
- Surviving verdict YAML:
  `golden_samples/heat-transfer-1d-candidate/cross_check_verdict.yaml`
  (schema 1.3.0, PASS at near-zero residual)
- Phase 33 D analytical SSOT (the deferred contact piece):
  `backend/app/services/cross_check/hertz_contact.py`
- Phase 34 C live ccx runner (contact closure):
  `backend/app/services/cross_check/contact_pair_runner.py`

## Closure status
CLOSED. The contact-mechanics slot was honoured by Phase 33 D
(analytical SSOT) + Phase 34 C (live ccx PASS at -6.823%
residual). Phase 35 B backfilled solver_kind for both.

## Lessons
1. Solver-kind diversity is a coarse but real Dim 1 90-anchor
   driver. Sometimes the right Phase X pivot is "ship a different
   kind", not "force this kind through under budget".
2. Phase 31 A's "what got skipped" is not "what gets dropped" —
   it became Phase 33 D + Phase 34 C. The journey is additive.
