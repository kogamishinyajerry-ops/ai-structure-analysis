# Phase 23 — Solver depth + viewport fidelity + reviewer-driven inspection · FINAL audit report

## Composite (round 1; no R2 spawned — see rationale below)

| Dimension | Round 1 | Phase 22 R1 | Blueprint projection | Delta vs P22 | Delta vs projection |
|---|---|---|---|---|---|
| UX | 80.8/100 | 79.6/100 | 82-85 | **+1.2** | below band, mid -2.2 |
| FEA | 74.0/100 | 70.4/100 | 75-79 | **+3.6** | inside band, low -1.0 |
| UI | 83.4/100 | 81.4/100 | 84-86 | **+2.0** | inside band, low -0.6 |
| **Composite** | **79.4** | **77.1** | **81-85** | **+2.3** | **below band, -1.6** |

**Verdict:** CHANGES_REQUIRED. APPROVE requires composite ≥ 99 AND
each ≥ 99 AND no axis < 95%. Round 1 fails all three. The composite
lifted +2.3 over Phase 22 — fourth-largest single-phase lift since
Tier 2 launched (after P21 +9.4 / P20 +7.3 / P22 +4.0). **Landed
BELOW the blueprint's projection band (81-85) by 1.6 points** — the
first sub-band landing since Phase 18 R1. Documented verbatim per
the absolute-honesty contract.

## What landed inside / below band

- **UX 80.8 vs 82-85 projection**: below band by 2.2. Honest cause:
  the cognitive-load axis regressed -1 because Phase 23 added three
  control surfaces (component switcher, threshold filter,
  node-pick HUD) without onboarding to absorb the new complexity.
  Reviewer-flow win (+5) outpaced the regression numerically but
  the net delta was smaller than projected (+1.2 vs +3-5 projected).
- **FEA 74.0 vs 75-79 projection**: inside band at low end, -1.0
  vs mid. Honest cause: Cross-check rigor lift (+2) was capped
  because the σ-tensor work is frontend-only this phase; the
  backend exporter update is Phase 24+ scope. Validated count
  flip (3→4) landed as projected.
- **UI 83.4 vs 84-86 projection**: inside band at low end, -0.6
  vs mid. Honest cause: LOC discipline regressed -2 because the
  viewport file grew 145 LOC (raycaster + HUD + filter add up
  fast). Industrial-CAE comparison lift (+5) outweighed but the
  net was less than projected.

## v2.3 round-cap=3 disposition: NO Round 2 spawned

Round 1 surfaced no Phase 20-style "real defects unit tests
missed" findings. Phase 23's load-bearing claims are independently
verifiable:
- **Phase 23 A** — `test_phase23a_validated_count_is_four` pin
  trips if `euler-column-candidate` verdict file is removed; the
  E2E pin runs real ccx + parses real .dat output; observed
  residual 0.21% is well inside tolerance (margin of 9.79%).
- **Phase 23 B** — Mises math pinned by analytical-known inputs;
  principal-stress pin pins plane stress to [150, 50, 0]; B:-2
  anti-gaming guard pinned (dropdown disabled without tensor).
- **Phase 23 C** — findClosestNode pin uses shuffled node labels
  (7, 42, 99, 11) to verify the picker returns ACTUAL labels not
  array indices (C:-2 anti-gaming guard).
- **Phase 23 D** — D:-1 guard pinned by three tests
  (alive=false, projectile, no-value all force retain).

The 19.6-point gap to 99 is structural:
- σ-tensor schema upgrade is frontend-only at Phase 23 B; backend
  exporter end-to-end flow is Phase 24+.
- Real WebGL E2E via puppeteer/playwright — still mock-only since
  Phase 21 C.
- Iso-surfaces / streamlines / multi-pick / annotation tools —
  multi-phase scope.
- Contact + friction + transient dynamics — each multi-week.
- Apple-tier visual polish — Phase 24+.
- Cognitive-load mitigations (onboarding tour, basic-vs-advanced
  modes) — Phase 24+.
- LOC discipline rebound — viewport file split into raycaster +
  animation + geometry modules; Phase 24+.

Round 2 here would polish 1-2 sub-dimensions but cannot move the
composite to 99 or even meaningfully toward the next 5-point step.
Round 2 = score-padding; that violates the absolute-honesty
contract carried verbatim from Phase 18/19/20/21/22.

## What Phase 23 actually delivered (honest accounting)

* **Slice A (commit `6107ae4`):** B31 Timoshenko beam-element
  buckling runner. Procedural ccx INP composer (no gmsh — B31 is
  1D). Shared eigenvalue parser refactored out of Phase 22 A.
  `euler-column-candidate` promoted to tier_2_validated; observed
  P_cr 1730.7 N vs analytical 1727.2 N → **residual 0.21%**.
  Validated count **3 → 4**. 10 new backend tests including
  `@pytest.mark.requires_solver` E2E pin and strict registry
  count pin.

* **Slice B (commit `caf7a34`):** σ-tensor schema upgrade
  (frontend) + Mises/component switcher. NEW
  `stressDerivatives.ts` with `computeVonMises` (analytical
  formula), `computePrincipalStresses` (closed-form 3×3 symmetric
  eigenvalue via Smith 1961 trigonometric method),
  `componentValue` switcher. `ResultMeshElement` gains optional
  `stressTensor`; readElement parses it from JSON. Legend
  chrome's read-only chip promoted to a real `<select>` with 9
  options. Backwards compatible (Phase 22 D scalar path retained).
  16 new frontend tests.

* **Slice C (commit `25ddc64`):** Node-picking with field probe
  overlay. THREE.Raycaster wired to click handler with 4-px
  click-vs-drag threshold. HUD overlay surfaces node label + xyz
  coords (scientific notation) + field value. Escape clears the
  pick. `onNodePicked` callback forwards to parent. New pure-
  function helpers (`findClosestNode`, `fieldValueAtNode`) pinned
  by 8 tests including C:-2 anti-gaming guard (shuffled node
  labels → returns actual labels).

* **Slice D (commit `e9b495b`):** Element-value threshold filter.
  Alternative to iso-surfaces (simpler & achievable in one slice).
  `ValueFilterState` interface + `applyValueFilter` predicate
  honors the Phase 23 B component switcher (filter compares
  against SAME scalar viewer sees on gradient). D:-1 anti-gaming
  guard: elements with alive=false / projectile / no-derivable-
  value ALWAYS render regardless of filter. UI: checkbox toggle
  + min/max sliders + IN/OUT mode button. 12 new frontend tests.

**46 new tests total** (10 backend Phase 23 A + 16 frontend
Phase 23 B + 8 frontend Phase 23 C + 12 frontend Phase 23 D).
**All 316 frontend tests** + **all backend Phase 18-23 regression**
(excl. requires_solver, which the B31 E2E pin runs and PASSes)
pass. Real-solver pin times: B31 buckling ~1s, cantilever C3D10
~3s, plasticity ~1s, plate Kirsch ~1s.

## What Phase 23 did NOT deliver vs blueprint

* **UX composite landed below the 82-85 projection band** (80.8).
  Honest cause: cognitive-load regression from three new control
  surfaces.
* **σ-tensor backend exporter NOT updated** — Phase 23 B is
  frontend-only. End-to-end tensor flow (ccx σ_xx → JSON →
  switcher) is Phase 24+.
* **Real WebGL E2E** (Phase 21 carry-forward) — still mock-only.
* **LOC discipline regressed** — viewport file grew 145 LOC.
* **No iso-surface rendering** — Phase 23 D shipped element-cull
  as a deliberately-simpler alternative; true iso-surfaces deferred.

## Phase 24 opening punchlist (filed from Phase 23 R1)

1. **σ-tensor backend exporter** — update result_mesh.json writer
  to emit per-element/per-node tensor when ccx provides it. Closes
  Phase 23 B's frontend-only gap.
2. **Real WebGL E2E via puppeteer/playwright** — Phase 21 carry-
  forward; address with headless-software WebGL.
3. **Iso-surface rendering in WebGL** — Phase 23 D's element-cull
  alternative falls short of true iso-surfaces.
4. **Onboarding tour / progressive disclosure** — close the Phase
  23 cognitive-load regression.
5. **Apple-tier visual polish pass** — animations, custom slider
  tracks, motion easing, hover previews, viewport-mode transitions.
6. **Contact + friction Tier 2 cross-check** — open the contact-
  mechanics solver kind.
7. **App.tsx + viewport reducer/state-slice refactor** — reverse
  the Phase 23 LOC-discipline regression.
8. **Multi-node pick (probe list)** — Phase 23 C's single-pick is
  the minimum; reviewers want to compare nodes.

## Decision

Phase 23 closes at composite **79.4/100, CHANGES_REQUIRED**.
+2.3 over Phase 22. The 99/100 target remains a multi-phase
commitment.

Phase 23 was the solver-depth + reviewer-driven-inspection phase
the blueprint promised: B31 promotion closed Phase 22 A's honest
miss; σ-tensor math + switcher closed Phase 22 D's honest miss;
node-picking closed the industrial-CAE feature parity gap; the
threshold filter shipped a useful alternative to iso-surfaces.
The composite landed below band by 1.6 — honestly recorded.

Round 1 reports archived alongside this FINAL:
* `UX.md` — 80.8/100, reviewer-flow +5 driven by node-picking;
  cognitive-load -1 honest miss.
* `FEA.md` — 74.0/100, validated count 3→4 (+7 Dim 2), B31
  solver kind unlock (+4 Dim 4).
* `UI.md` — 83.4/100, industrial-CAE +5 (Dim 2), 3D depth +4
  (Dim 5); LOC discipline -2 honest miss.

Not signed validation; not benchmark agreement.
