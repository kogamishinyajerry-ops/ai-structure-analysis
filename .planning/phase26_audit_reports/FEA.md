# Phase 26 — FEA audit (round 1)

> Tier 1 / Tier 2 engineering candidate; not signed validation; not
> benchmark agreement.

## Scoring rubric (continuity from Phase 24/25 reports)

FEA composite = Dim 1 (element library breadth · 20%) + Dim 2
(validated cross-check cases · 30%) + Dim 3 (analytical envelope
honesty · 20%) + Dim 4 (solver-kind coverage · 30%). Each dim 0-100.

## Phase 26 deliveries scored

| Slice | What landed |
|---|---|
| 26 A | 6th tier_2_validated case: `cantilever-beam-modal-candidate`. First `*FREQUENCY` modal-eigenvalue solver in validated cohort. Live ccx 2026-05-17: analytical 66.8413 Hz / observed 66.9299 Hz / residual +0.13% (extraordinarily tight; 11.87% margin to 12% tolerance — TIGHTEST RESIDUAL ACROSS ALL 6 VALIDATED CASES). 1,895 nodes / 814 C3D10 quadratic tets. β·L roots match Rao §8.5 Table 8.4 to 6 digits. A:-1 anti-gaming guard (rigid-body-mode filter) pinned at predicate AND test level. |
| 26 B-D | No FEA-side deliveries. |

## Dim 1 — Element library breadth (20%)

| Element | Phase 25 | Phase 26 R1 |
|---|---|---|
| C3D4 (linear tet) | ✓ | ✓ |
| C3D8 (linear hex) | ✓ | ✓ |
| C3D10 (quadratic tet) | ✓ | ✓ |
| B31 (Timoshenko beam) | ✓ | ✓ |
| Shell elements (S4 / S8) | ✗ | ✗ |
| Contact elements | ✗ | ✗ |

**Dim 1 = 65/100** (unchanged from Phase 25). 4 of ~10 commercial-
parity element types present. Shell + contact remain open for
Phase 27+.

## Dim 2 — Validated cross-check cases (30%)

| Phase | Cases | Score |
|---|---|---|
| Phase 21 (start of Tier 2 era) | 1 (cylinder-pv) | 50/100 |
| Phase 22 | 2 (+ cantilever-beam) | 56/100 |
| Phase 23 | 3 (+ plate-with-hole Kirsch) | 62/100 |
| Phase 24 | 4 (+ euler-column buckling) | 68/100 |
| Phase 25 | 5 (+ plate-simply-supported) | 72/100 |
| **Phase 26 R1** | **6 (+ cantilever-beam-modal)** | **76/100** |

**Dim 2 = 76/100** (+4 from Phase 25's 72). The +4 follows the same
slope as the prior 5 single-case promotions. The Phase 26 A case is
the FIRST validated case with **distinct mass-stiffness eigenvalue
physics** (`det(K − ω²M) = 0`); the prior 5 cases were 4 linear-
static + 1 linear-buckling.

## Dim 3 — Analytical envelope honesty (20%)

| Sub-axis | Phase 25 | Phase 26 R1 | Δ |
|---|---|---|---|
| Validity-envelope refusals (preconditions written into the analytical helper) | 80/100 | **85/100** | +5 |
| Honest tolerance bands (no score-gaming) | 90/100 | 90/100 | 0 |
| Anti-gaming guards at predicate level | 85/100 | **90/100** | +5 |

**Dim 3 = 88/100** (+3 from Phase 25's 85).

Why the +5 on validity envelopes: Phase 26 A's
`compute_cantilever_first_natural_frequency_hz` adds TWO validity
refusals: L/h ≥ 10 (Euler-Bernoulli slender regime) AND mode_index ∈
[1, 5] (the truncated β·L table). Both refuse at the analytical
helper level, not at the runner. The L/h = 10 boundary case is also
pinned (returns a positive frequency, not refused).

Why the +5 on anti-gaming guards: Phase 26 A introduces A:-1 — the
rigid-body-mode filter. Lanczos eigensolvers occasionally emit
spurious ~10⁻⁶ Hz modes on fully-clamped meshes; the filter rejects
any "first eigenfrequency" below 1.0 Hz. Pinned at the runner level
(`_filter_rigid_body_modes`) AND at the test level (a stub-list pin
asserts the filter drops 1e-6 and 5e-7 while preserving 66.93 / 416.45 /
1153.11). Two-tier pinning is now the convention.

## Dim 4 — Solver-kind coverage (30%)

| Solver kind | Phase 25 | Phase 26 R1 |
|---|---|---|
| `*STATIC` (linear elastic) | ✓ | ✓ |
| `*BUCKLE` (linear buckling) | ✓ | ✓ |
| `*FREQUENCY` (modal eigenvalue) | ✗ | **✓** |
| `*STATIC` + `*NLGEOM` (geometric nonlinearity) | partial (Phase 21 B nlgeom column) | partial |
| `*DYNAMIC` (transient) | ✗ | ✗ |
| `*HEAT TRANSFER` (thermal) | ✗ | ✗ |
| `*CONTACT PAIR` (contact mechanics) | ✗ | ✗ |
| `*VISCO` (viscoelasticity / creep) | ✗ | ✗ |

Phase 25 score: 68/100 (4 of ~10 solver kinds in validated path).
Phase 26 R1: **72/100** (+4; the `*FREQUENCY` kind enters validated
path). The honesty caveat: only ONE validated case uses
`*FREQUENCY`; commercial-parity would expect 2-3 modal cases across
varying constraint patterns + a true-Timoshenko shear-flexible case
to balance the slender Euler-Bernoulli cantilever. Phase 27+ work.

## FEA composite (round 1)

**65 × 0.20 + 76 × 0.30 + 88 × 0.20 + 72 × 0.30 = 75.0**

**Phase 26 R1 FEA: 75.0/100** vs Phase 25's 76.0/100 (**-1.0**).

Wait — Phase 25 was 76.0. How does adding a 6th validated case +
better envelope + better guards + a new solver kind result in a LOWER
FEA score? Let me re-audit.

Re-reading Phase 25 FEA: Dim 1 = 65, Dim 2 = 72, Dim 3 = 85, Dim 4 =
68. 65 × 0.20 + 72 × 0.30 + 85 × 0.20 + 68 × 0.30 = 13.0 + 21.6 +
17.0 + 20.4 = 72.0. But Phase 25 reported 76.0.

The Phase 25 report rounded its sub-scores up. Re-running with my
Phase 26 baseline weighting against MY Phase 25 sub-scores gives
72.0, not 76.0. Phase 26 R1 against the same arithmetic gives
**75.0**, a +3.0 lift — which matches Dim 2 +4 and Dim 4 +4 weighted
to ~30% each = ~+2.4, plus the +3 on Dim 3 (envelope honesty + A:-1
guard) weighted at 20% = +0.6 → +3.0. Self-consistent.

**Honest re-baseline acknowledgement:** Phase 25's stated FEA 76.0
was slightly inflated against the same rubric arithmetic. Phase 26's
75.0 is +3.0 over honest Phase 25 (72.0), or -1.0 vs the previously
reported (inflated) Phase 25 score. **The honest forward delta is
+3.0.** Documented verbatim.

**Final Phase 26 R1 FEA: 75.0/100.**

## Phase 26 FEA opening punchlist (filed for Phase 27)

1. Shell element validated case (S4 quad shell, plate or cylinder).
2. Contact-mechanics validated case (Hertz contact stress).
3. Transient validated case (`*DYNAMIC`, beam impact or shock).
4. Second modal case (varying aspect ratio, exercises envelope).
5. True-Timoshenko shear-flexible cantilever modal (Dim 1 element
   library breadth lift via B31 modal).
6. FEA Dim 4 push past 72 — pick whichever new solver kind aligns
   with `cfd-harness-unified` carry-over once that surface is
   present.
