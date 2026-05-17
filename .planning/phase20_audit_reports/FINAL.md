# Phase 20 — production-grade Tier 2 extension · FINAL audit report

## Composite (round 2, UX re-scored; FEA + UI unchanged from round 1)

| Dimension | Round 1 | Round 2 | Phase 19 R1 | Blueprint projection | Delta vs P19 | Delta vs projection |
|---|---|---|---|---|---|---|
| UX | 62/100 | **70/100** | 67/100 | 78-85 | **+3** | **-8 vs low end** |
| FEA | 57/100 | 57/100 | 46/100 | 58-66 | **+11** | inside band (lower bound -1) |
| UI | 66/100 | 66/100 | 58/100 | 68-74 | **+8** | -2 vs low end |
| **Composite** | **61.7** | **64.3** | **57.0** | **68-75** | **+7.3** | **-3.7 vs low end** |

**Verdict:** CHANGES_REQUIRED. APPROVE requires composite ≥ 99 AND each ≥ 99 AND no axis < 95%. Round 2 fails all three. The composite lifted +7.3 over Phase 19 — real and the biggest single-phase lift since Phase 18 launched the Tier 2 program — and **landed slightly below the blueprint's own honest projection (68-75)**.

## v2.3 round-cap=3 disposition

Round 1 ran all three axes; the UX agent surfaced two real defects in Phase 20 D (registry-fallback omission + selection state-divergence). Round 2 patched both (commit `fda7384`) and re-scored UX only. FEA and UI weren't affected by the patch so their R1 scores stand. **I chose NOT to spawn round 3.**

Rationale:
* The remaining lowest axes (FEA Production-gap = 4/20, UI Industrial-CAE = 4/20 floor) require WebGL viewport + contact + nonlinear-plasticity E2E — multi-week structural work, not spike-class iteration.
* UX T2 (signoff form, R2 14/20) and T5 (stress contour, R2 12/20) carry forward; further form/contour polish would lift sub-scores but not move the composite to 99 or even to the projection band low end (68).
* Round 3 here would be score-padding: rearranging dim weights or cosmetic tightening. That violates the absolute-honesty contract carried verbatim from Phase 18/19.

The v2.3 round-cap discipline is working as designed: cap on iteration, not on candor.

## Round 1 → Round 2 findings (the agents' actual contribution)

### Round 1 — Defects surfaced (agents found what unit tests missed)

1. **Registry fallback omission.** Phase 20 D commit message claimed cylinder-pv / plate-with-hole / cantilever were in the left-rail candidate roster. They weren't — `FALLBACK_CANDIDATE_CASES` at `frontend/src/candidateCaseRegistry.ts` only had the original 4 entries. The Sidebar roster rendered correctly; my new Phase 19 B / Phase 20 B / Phase 20 C candidates were silently invisible.

2. **State-divergence on candidate click.** Selecting a candidate set `selectedCandidateCaseId` but not `activeCaseId`, so Topbar's Run Solver button (gated by `activeCaseId`) stayed hidden. The Phase 20 A material_id route handoff is real but the UI path to reach it was broken.

### Round 2 — Patch verification (commit fda7384)

Both defects closed:
* Registry extended by 3 entries with file:line cites: cylinder-pv (Tier 2 validated), plate-with-hole (Tier 1 + Phase 21 Kirsch scope note), cantilever-beam (Tier 1 + Phase 21 runner scope note).
* `onSelectCandidateCase` now calls both `setSelectedCandidateCaseId` AND `setActiveCaseId`. Test file updated from a `toHaveLength(4)` pin to `toBeGreaterThanOrEqual(4)` + head-of-list invariant so future additions don't re-trip.

UX Round 2 lift:
* Task 3 (Cmd-K re-run on cylinder-pv) 9/20 → 14/20 (+5) — the load-bearing fix.
* Task 1 (find leak case) +2 sub-dims.
* Task 4 (material swap) stayed flat at 13/20 — the patch doesn't surface `material_reference` in the UI or move the buried Material picker. Phase 21 carry-forward.

## What Phase 20 actually delivered (honest accounting)

* **Slice A (commit `af0d52a`):** `RunRequest.material_id` end-to-end. Route → service handoff verified by 9 new tests including a route-handler integration test that pins the aluminium `*ELASTIC` block byte-identically. Closes the Phase 19 E load-bearing finding.
* **Slice B (commit `8447501`):** plasticity `*PLASTIC` keyword + cantilever analytical. 27 new tests. 2 materials gain cited bilinear hardening curves (EN 1993-1-5 + MMPDS). Honest scope reduction documented: cantilever-runner deferred to Phase 21 because single-hex coupons can't capture bending.
* **Slice C (commit `e0eb83b`):** Gmsh + STEP → Tier 2 pipeline. 15 new tests including a real-solver E2E pin (real gmsh meshes a 690-node plate-with-hole, real ccx solves it, non-zero u_x verified, 1.15 s total). **Ends the single-element-coupon regime — the biggest single FEA milestone since Phase 18 A.**
* **Slice D (commit `523723f`):** Topbar + RightRail extractions, Sidebar candidate roster, ResultMeshPlaybackPanel primitive migration. 16 new tests. App.tsx 2019 → 2006 LOC (modest; <1750 blueprint target NOT met).
* **Slice E R1→R2 (commit `fda7384`):** registry + state-divergence defects closed.

**67 new tests total** (51 backend Phase 20 A/B/C + 16 frontend Phase 20 D). **230/230 frontend regression** + **241/241 backend regression** post Slice D. Real-solver pin time **1.15 s** for a 690-node plate.

## What Phase 20 did NOT deliver vs blueprint

* **App.tsx <1750 LOC target missed** (landed at 2006 LOC). Continued shrinkage needs Visual/Narrative/Exploration tab extractions (~80-150 LOC each).
* **Cantilever ccx-running runner deferred** to Phase 21 (single-hex coupons can't capture bending; needs Slice C's multi-element path).
* **No `tier_2_validated` count increase.** Slice B + C added 2 candidate cases as `tier_1` baselines; the analytical cross-check runner that would promote them is Phase 21 scope.
* **No buckling step in Tier 2 pipeline.** Blueprint listed this as Phase 21 P5; deferred.
* **Plasticity is keyword-only.** `*PLASTIC` is written, but no `@pytest.mark.requires_solver` test verifies ccx actually promotes to NLGEOM under yielding loads.
* **No WebGL frontend viewport.** UI Dim 5 stays at 4/20 floor. Multi-week effort; Phase 22+ scope.

## Phase 21 opening punchlist (filed from R2 retros)

1. **Cantilever ccx-running runner** using Slice C's meshed pipeline → flips `cantilever-beam-candidate` to `tier_2_validated`.
2. **Plate-with-hole Kirsch cross-check runner** (σ_max = 3·σ_∞) → flips `plate-with-hole-candidate` to `tier_2_validated`.
3. **Plasticity `requires_solver` E2E pin** — yielding load on bilinear steel-S355 + assert ccx σ at large-strain region matches hardening curve.
4. **App.tsx <1500 LOC** via Visual/Narrative/Exploration tab extractions.
5. **Surface `material_reference` in the UI** (the route now returns it; no frontend consumes it) so reviewers see the citation in the Run Solver result panel.
6. **WebGL viewport prototype** — even a minimal three.js render of `result_mesh.json` would lift UI Dim 5 from 4/20 to ~10/20 and Data Viz from 13/20 to ~16/20.

## Decision

Phase 20 closes at composite **64.3/100, CHANGES_REQUIRED**. +7.3 over Phase 19 is the biggest single-phase lift since Tier 2 launched. The agents earned their keep again — Round 1 surfaced two real defects unit tests missed, Round 2 verified the patch. The 99/100 target remains a multi-phase commitment ("99 is months of Tier 3 work" — blueprint thesis preserved verbatim across Phase 18 / 19 / 20).

Round 1 reports archived alongside this FINAL:
* `UX.md` — 62/100, surfaced registry omission + state-divergence
* `FEA.md` — 57/100, +11 over Phase 19, inside projection band low end -1
* `UI.md` — 66/100, +8 over Phase 19, App.tsx still 2006 LOC
* `UX_round2.md` — 70/100, +8 after R1→R2 honesty patch

Not signed validation; not benchmark agreement.
