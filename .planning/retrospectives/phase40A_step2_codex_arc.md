# Retro — FM-04a Phase 40 A step 2 (iso-surface viewport wiring + Codex arc)

> Date: 2026-05-25 · code @ `774ab69`. Light retro (not a phase-close — Phase 40
> is mid-flight). Focus: the dev-team-architecture (ADR-026) layer-1 Codex-review
> arc, because it produced the FM-04a Codex relay's most substantive catch to date.

## What shipped

Phase 40 A step 2: wired the step-1 iso-surface extraction core into the result-mesh
3D viewport (opt-in, default OFF) + honesty-label UX (smoothed Tier-0 viz; per-element
coloring stays the truth view) + panel control (advanced-gated) + companion forwarding.
Registered `functional-tester` re-score: **Dim 5 = 84** (was 82). Composite **81.00**
(was 80.67) — prospective, driven by new code (not a byte-unchanged truth correction);
Phase 37/38/39 records unchanged.

## Codex review arc (the notable part)

| Round | Verdict | P1 | P2/P3 | Outcome |
|---|---|---|---|---|
| R0 (de493d3) | CHANGES_REQUIRED | 1 (undeformed coords) | 2 | fixed → c5c7b87 |
| R1 (full range) | CHANGES_REQUIRED | 1 (filtered tets march via shared nodes) | 2 | fixed → f2070a9 |
| R2 (full range) | CHANGES_REQUIRED | **0** | 2 | round cap → retro queue (774ab69) |

### Insight 1 — Codex caught two GENUINE P1 correctness bugs my self-review missed
Both were real, not style:
- **R0 P1:** the iso-surface was extracted in undeformed coords while the base mesh
  rebuilds from deformed/interpolated coords → the overlay visibly peels away the
  moment a reviewer magnifies deformation or plays the animation.
- **R1 P1:** my R0 value-filter fix only gated the cell→point *averaging*; the
  marching loop still marched filtered-out tets whose corners were averaged by kept
  neighbors → overlay geometry in the filtered region, disagreeing with the truth mesh.

Neither would have been caught by tsc/eslint/the vitest suite as I'd written them
(the tests asserted the happy path; these are interaction-with-existing-features
bugs). This is exactly the "module-level review misses cross-feature semantics"
blind spot the risk-tier Codex gate exists for. **The relay earned its keep here.**

### Insight 2 — the round cap converged correctly
R2 (3rd round) found 0 P1 and 2 P2. Per round-cap-3, the P2s went to the retro queue
(`codex_round3_overflow_phase40A.md`) without further iteration and WITHOUT user
ratification (reserved for round-3 P1). No premature stop, no infinite polishing —
the cap did its job. The remaining P2s are genuine edge-case/quality items
(tensor-component threshold range; iso in hover raycast), one of which is consistent
with a pre-existing pattern (value-filter slider) and the other arguably correct-by-design.

### Insight 3 — confidence self-tag calibrated correctly
The step-2 commit was tagged `confidence: med` (not high) because it touched the
691-LOC regression-sensitive viewport + load-bearing honesty framing. That med was
*right*: Codex found P1s. The honest self-tag correctly signaled "worth a review
round" rather than over-claiming high. The R2-closure commit went `confidence: high`
once correctness had converged. Calibration working as intended — no penalty needed.

## Methodology notes (for the dev-architecture record)

- This is the FM-04a Codex relay's most valuable activation since ADR-026 ratified it
  (the ratifying dogfood found only 2 P2s; this arc found 2 P1s). Evidence the layer-1
  review is value-creation, not process-completion.
- No post-R3 defect to log (R2 found no P1; the functional-tester independently
  confirmed the deformed-coord + value-filter fixes hold at `ResultMeshWebGLViewport.tsx:195-217`).
- Pattern worth keeping: for honesty-critical viz/UX touching existing multi-feature
  viewports, run Codex even when no hard risk-tier trigger fires — the cross-feature
  integration blind spot is real and static review surfaces it cheaply.

## Next increments (Dim 5 → 90+, from the fresh audit's gap list)

1. Two-results overlay in the viewport (closes the 4th 90-sub-bullet → ~88).
2. Real-WebGL Playwright E2E in CI (90 + 99 evidence; current tests are all jsdom).
3. Provenance overlay on viz frames + measured-fps artifact + VTU/PNG export (95→99).
