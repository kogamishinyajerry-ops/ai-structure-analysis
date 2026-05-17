# cantilever-beam-candidate — Phase 20 B

**Tier:** `tier_1_candidate` (baseline). The analytical cross-check
companion to the Phase 19 B cylinder-pv flip; promotion to
`tier_2_validated` requires a verdict-file PASS from `cantilever_runner`
which Phase 20 B did NOT ship (see scope honesty below).

## Geometry

A slender steel cantilever fixed at one end, transverse point load at
the free tip.

| parameter | value | unit |
|---|---|---|
| length L | 1.0 | m |
| cross-section depth h | 0.1 | m |
| cross-section width b | 0.1 | m |
| aspect ratio L/h | 10.0 | — |
| second moment I = b·h³ / 12 | 8.3333…e-6 | m⁴ |
| tip load P | -1000.0 | N (downward) |
| Young's modulus (steel-s355) | 210e9 | Pa |

## Expected analytical (Euler-Bernoulli)

δ_tip = P · L³ / (3 · E · I)
     = -1000 · 1.0³ / (3 · 210e9 · 8.3333e-6)
     = -1.9048e-4 m  (−0.19 mm)

Sign convention: negative δ_tip ↔ downward, matching the load
direction.

## Phase 20 B scope honesty (carry-forward to Phase 21)

The Phase 20 B blueprint promised a real-ccx cantilever runner that
would auto-promote this case to `tier_2_validated`. The runner is NOT
delivered in Phase 20 B because a single-C3D8-hex coupon cannot
capture bending response (the formula needs multi-element refinement
through the length AND a meshing path that Slice C delivers). The
analytical half (`compute_analytical_tip_deflection` in
`backend/app/services/cross_check/cantilever_beam.py`) and this
candidate directory + the registry entry are shipped; the
`cantilever_runner.py` + ccx integration + verdict PASS path lands in
Phase 21 once Slice C's Gmsh-meshed pipeline is the canonical
multi-element route.

## References

* Roark's Formulas for Stress and Strain, 8th ed., Table 8.1 Case 1a.
* Timoshenko & Gere, Mechanics of Materials, 4th ed., §5.4 eq. 5-15.

## Claim envelope

* claim_tier: tier_1_engineering_candidate
* claim_boundary: not signed validation; not benchmark agreement
* claim_impact: Phase 20 B analytical-only landing pad; cross-check
  + ccx-driven promotion is Phase 21+ scope.
