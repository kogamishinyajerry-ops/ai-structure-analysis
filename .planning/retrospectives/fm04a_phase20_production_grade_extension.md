# FM-04a Phase 20 — Production-grade Tier 2 extension · Retrospective

**Date:** 2026-05-17
**Composite (honest):** 64.3/100 — CHANGES_REQUIRED
**Round count:** 2 (UX re-scored after R1→R2 honesty patch; FEA + UI scored once)
**Phase 19 baseline:** 57.0/100 → **+7.3 lift (biggest single-phase lift since Tier 2 launched)**
**Blueprint projection:** 68-75/100 → **landed BELOW the low end by 3.7 points**

---

## What got built

| Slice | Deliverable | Status | Evidence |
|---|---|---|---|
| A | `RunRequest.material_id` route → service handoff | ✓ closed Phase 19 E load-bearing finding | commit `af0d52a`, 9 tests, route-handler integration pin asserts aluminium `*ELASTIC` block byte-identical |
| B | Plasticity `*PLASTIC` keyword + cantilever analytical | ✓ partial (analytical only; runner deferred) | commit `8447501`, 27 tests, bilinear curves on 2 of 8 materials (EN 1993-1-5 + MMPDS) |
| C | Gmsh + STEP → Tier 2 meshed pipeline | ✓ ENDS single-element-coupon regime | commit `e0eb83b`, 15 tests, real solver E2E pin 690 nodes / 1.15 s |
| D | Topbar + RightRail + Sidebar candidate roster + ResultMesh primitive migration | ✓ shipped, 2 R1 defects | commit `523723f`, 16 tests + R1→R2 patch `fda7384` |
| E | 3 testing agents + honest scoring | ✓ 2 rounds | this retro + 4 audit reports |

**Tests at close:** 230/230 frontend (vitest) + 241/241 backend Phase 18+19+20 (pytest, requires_solver deselected) + 4 `@pytest.mark.requires_solver` pins land real ccx/gmsh subprocesses.

---

## What the 3 testing agents found (load-bearing)

The agents earned their keep AGAIN this phase. The R1 reports surfaced two real defects in Phase 20 D that the unit tests didn't see:

### R1 Finding 1 — Registry-fallback omission

* Phase 20 D commit message: "cylinder-pv-candidate + plate-with-hole-candidate + cantilever-beam-candidate now in left-rail candidate roster".
* Reality: `FALLBACK_CANDIDATE_CASES` at `frontend/src/candidateCaseRegistry.ts:46-110` only had 4 entries (3 GS-102 + leak). My new Phase 19 B / Phase 20 B / Phase 20 C candidates were silently invisible.
* Root cause: I added the Sidebar roster + plumbed `FALLBACK_CANDIDATE_CASES` into it (which worked correctly for the EXISTING entries), but never actually extended the fallback list with the new candidates.
* Why unit tests didn't catch it: the Phase 20 D test fixture supplied its OWN hardcoded `candidateCases` array — it never asserted against `FALLBACK_CANDIDATE_CASES` directly.

### R1 Finding 2 — Selection state-divergence

* `App.tsx` `onSelectCandidateCase` set `selectedCandidateCaseId` but not `activeCaseId`.
* Topbar's `showRunControls = Boolean(activeCaseId)` → Run Solver button stays hidden when a candidate is the only selection.
* The Phase 20 A material_id route is functional, but the UI path to actually push the button to trigger it was broken.
* Why unit tests didn't catch it: the Phase 20 D Topbar tests passed `showRunControls=true` directly as a prop; they never exercised the App.tsx-level state plumbing.

### R2 patch verification (commit `fda7384`)

* Registry extended by 3 entries with file:line cites: cylinder-pv (Tier 2 validated per Phase 19 B verdict), plate-with-hole (Tier 1 + Phase 21 Kirsch scope note), cantilever-beam (Tier 1 + Phase 21 runner scope note).
* `onSelectCandidateCase` now calls both setters.
* Test `Phase18E_round3.test.tsx`'s `toHaveLength(4)` pin softened to `toBeGreaterThanOrEqual(4)` + head-of-list invariant.

UX agent R2 lift: 62 → 70 (+8). T3 (Cmd-K re-run) +5 of the +8; T1 (find leak) +2. T4 (material swap) stayed at 13/20 — the patch doesn't surface `material_reference` in the UI; carry-forward to Phase 21.

---

## What the rubric tells me about the projection gap

Blueprint projected UX 78-85 / FEA 58-66 / UI 68-74 → composite 68-75.
Actual: UX 70 / FEA 57 / UI 66 → composite 64.3.

* **FEA landed effectively inside the band** (57 vs 58-66 low end -1; with Slice B's plasticity counted as "scaffolding without NLGEOM E2E" the agent honestly trimmed credit).
* **UI UNDER-shot by 2 points** vs the low end — App.tsx shrank only 13 LOC despite three extractions. The candidate-roster wiring added 17 LOC; the math doesn't compound. Continued shrinkage requires extracting the Visual/Narrative/Exploration tab bodies (each 80-150 LOC).
* **UX UNDER-shot by 8 points** vs the low end after R2. T4 (material swap) is the unfixed gap: the route accepts material_id end-to-end now, but the UI flow ("see what material was used" + a less-buried picker) wasn't tightened.

**Lesson (Phase 20 version):** my Phase 20 D commit message described features that were ALMOST true. The registry omission was a literal one-line gap between claim and code. The state-divergence was a "two states should be one" design oversight. Both are commit-discipline failures, not engineering failures. Phase 21+ commit-time self-check: when I write "X is now visible/clickable", grep the code path that actually surfaces X before committing.

---

## v2.3 governance signals (telemetry)

* `autonomous_governance_counter_v61`: Phase 20 contributed ~6 DECs (blueprint + 4 slice commits + R1→R2 patch). Cumulative still well below the 30 cadence floor.
* **Kogami:** not invoked. No user request for strategic-layer review; v2.3 opt-in policy honoured. ✓
* **Codex review rounds:** 0. All slices Opus-singled with high-confidence commit messages. None of the risk-tier-1 triggers (auth / signing / safety boundary) fired.
* **DEC scope discipline:** all 5 slices were sub-DEC scope. Slice C was the closest to charter trigger (cross-cutting: meshing + INP composer + pipeline + new candidate dir) but stayed under the ≥3-shared-code-paths threshold. ✓
* **Notion sync:** none from this session per the "Status=Accepted only" policy. ✓

---

## Decision

Phase 20 closes at composite **64.3/100, CHANGES_REQUIRED**, with the Phase 21 punchlist filed in FINAL.md.

**Phase 21 opening punchlist:**
1. Cantilever ccx-running runner (Phase 21's first Slice C beneficiary) → flips `cantilever-beam-candidate` to `tier_2_validated`
2. Plate-with-hole Kirsch cross-check runner → flips `plate-with-hole-candidate` to `tier_2_validated`
3. Plasticity `requires_solver` E2E pin (yielding load on bilinear steel-S355 + ccx NLGEOM verification)
4. App.tsx <1500 LOC via Visual/Narrative/Exploration tab extractions
5. Surface `material_reference` in the UI Run Solver result panel
6. WebGL viewport prototype (three.js minimal render of `result_mesh.json`) — biggest single UI lever; would lift UI Dim 5 from 4/20 floor to ~10/20

99/100 remains a multi-phase commitment. Phase 18 launched Tier 2 at 54.0. Phase 19 lifted +3.0 to 57.0. Phase 20 lifted +7.3 to 64.3. Each phase delivers honest work; the 99 ceiling is the integral of many phases.

Not signed validation; not benchmark agreement.
