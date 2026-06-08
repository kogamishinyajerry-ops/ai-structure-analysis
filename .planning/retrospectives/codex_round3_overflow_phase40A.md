# Codex round-3 overflow — FM-04a Phase 40 A step 2 (iso-surface wiring)

> Round-cap-3 governance (ADR-026 / `~/CLAUDE.md` v2.3): the Codex review
> loop converged after R2 (the 3rd round) with **0 P1** remaining. Per the
> rule, round-3 residual **P2/P3 → retro queue; the sub-DEC does NOT iterate
> further**. No user ratification needed (that is reserved for round-3 **P1**).
> This file records the two deferred P2 findings so they are tracked, not lost.

## Review arc summary

| Round | Base | Verdict | Findings | Disposition |
|---|---|---|---|---|
| R0 | `de493d3` (commit) | CHANGES_REQUIRED | P1 deformed-coords · P2 value-filter · P2 companion | all fixed → `c5c7b87` |
| R1 | `bc62f11` (full range) | CHANGES_REQUIRED | P1 filtered-tet-marches · P2 camera-snap · P3 skip-mislabel | all fixed → `f2070a9` |
| R2 | `bc62f11` (full range) | CHANGES_REQUIRED | **0 P1**, 2× P2 | **deferred (this file)** — round cap reached |

Both correctness-class blockers (the two P1s) were caught and fixed before the
cap. The residuals are quality/edge-case P2s.

## Deferred finding 1 — iso threshold range ignores the active tensor component (P2)

- **Where:** `ResultMeshPlaybackPanel.tsx` (iso `valueRange` / `isoThresholdEffective`)
  + `ResultMeshWebGLViewport.tsx` iso memo default `(valueMin + valueMax) / 2`.
- **Issue:** when the frame carries `stressTensor` data and the reviewer switches
  to a tensor-derived component (σ_xx / σ_yy / σ_zz / shear / principal), the iso
  slider min/max and the default midpoint are still driven by `summary.valueMin/
  valueMax` (the `value` / payload `fieldRanges` domain), not the selected
  component's range. The slider can be clamped to the wrong domain (e.g. negative
  principal-stress thresholds unreachable) and the default can sit outside the
  real range → the badge reads `no crossing` when one exists.
- **Why deferred (not a round-cap-3 violation):**
  1. Codex rated it **P2**, not P1 — the primary `value`/mises path (the default)
     is correct; this is a secondary component × iso combination.
  2. The **existing value-filter slider shares the identical limitation** (same
     `valueRange` source), so iso is *consistent with the established pattern*,
     not a new regression.
  3. A correct fix derives per-component min/max (max/min of `componentValue`
     over the frame's elements for the active component) and threads it to BOTH
     the iso slider AND the value-filter slider for consistency — a broader change
     than step 2's additive scope.
- **Honesty:** documented inline at the `isoThresholdEffective` site so it is a
  *known* limitation, not a hidden defect (绝对诚实客观).
- **Recommended follow-up:** a dedicated "per-component field range" increment
  (compute component range once per frame; feed iso + value-filter sliders;
  default threshold = component midpoint). Pairs naturally with any future
  Dim 5 work on the field-component switcher.

## Deferred finding 2 — iso mesh not in hover/probe raycasts (P2)

- **Where:** `ResultMeshWebGLViewport.tsx` pick/hover handlers raycast `state.mesh`
  only, not `state.isoMesh`.
- **Issue:** with the overlay on (especially behind a section cut), clicking/
  hovering the magenta iso surface reports coordinates from the base mesh behind
  it, not the iso surface.
- **Why deferred — and arguably correct-by-design:** the node-pick probe reports a
  **frame node** (label + coords + field value). Iso-surface vertices are
  *interpolated edge-crossing points*, not nodes — they have no node label and no
  solved field value of their own. Probing the truth mesh for the nearest real
  node is the honest behavior; "picking" a smoothed iso vertex would invent a node
  identity that does not exist. The only mild inaccuracy is the hover **coord
  readout** (XYZ), which would read the base-mesh hit point rather than the iso
  surface point.
- **Recommended follow-up (if pursued):** add the iso mesh to the *hover coord*
  raycast set (report iso-surface XYZ when it is the front hit) while keeping the
  *node-pick* raycast on the truth mesh only (no fabricated node identity). Low
  priority; the iso surface is explicitly a viz approximation, not a probe target.

## Net state at cap

- Both P1 correctness blockers fixed + regression-guarded (4 new step-2 tests
  across R0/R1: deformed-coord follow, filter-exclusion, filtered-tet-no-march,
  incomplete-vs-non-tet labeling).
- Gates green: tsc -b 16 / eslint 72 (0 net new) · vitest 951 / 65 files · step-1
  node --test 12/12 · App.tsx untouched.
- Feature ships for its documented scope (tet-only, smoothed Tier-0 viz, default
  OFF, per-element coloring is the truth view) with the two P2 limitations
  recorded here.
