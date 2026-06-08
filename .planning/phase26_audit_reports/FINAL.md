# Phase 26 — 6th validated case + Basic-mode gating + probe diff + view-model · FINAL audit report

> Tier 1 / Tier 2 engineering candidate; not signed validation; not
> benchmark agreement.

## Composite (round 1; no R2 spawned — see rationale below)

| Dimension | Round 1 | Honest Phase 25 baseline | Reported Phase 25 (inflated) | Δ vs honest | Δ vs reported |
|---|---|---|---|---|---|
| UX | **76.8/100** | ~76 | 84.0 | **+0.8** | -7.2 |
| FEA | **75.0/100** | 72.0 | 76.0 | **+3.0** | -1.0 |
| UI | **72.3/100** | ~68.7 | 86.4 | **+3.6** | -14.1 |
| **Composite** | **74.7** | **~72.2** | **82.1** | **+2.5** | **-7.4** |

**Verdict:** CHANGES_REQUIRED. APPROVE requires composite ≥ 99 AND
each axis ≥ 99 AND no axis < 95%. Round 1 fails all three.

**Honest re-baseline event (绝对诚实客观 contract):** Phase 26
recalibrates against the rubric. Prior phases (21-25) drifted into
flattering App.tsx LOC discipline and FEA arithmetic. Phase 26's
honest 74.7 represents a **+2.5 lift over honest-Phase-25 (~72.2)**;
the -7.4 swing against the previously-reported 82.1 is the
recalibration cost, paid in this phase rather than carried as silent
debt into Phase 27. Documented verbatim.

## What honest re-baseline names verbatim

1. **App.tsx LOC discipline** — Phase 21-25 UI Dim 1 scores treated
   "App.tsx is being decomposed" as worth 70-80 points even while
   the absolute LOC grew from ~1100 to ~1450. Phase 26 D's
   extraction GREW the file (1446 → 1464) and exposed that LOC
   absolute-target accountability was missing. Honest re-baseline:
   LOC discipline sub-axis maps to (target_LOC / actual_LOC) × 100
   with a 1300 target → 1464 actual → 88.8% → 55/100 with rubric
   discount for "missed by ≥150".
2. **FEA arithmetic** — Phase 25's stated FEA 76.0 against the
   stated rubric weights (20/30/20/30) and sub-scores (65/72/85/68)
   actually computes to 72.0, not 76.0. Phase 26 R1 (65/76/88/72)
   computes to 75.0, a +3.0 honest lift over honest-Phase-25.
3. **UX App.tsx readability sub-axis** — over-credited in Phase 25
   at 75/100 when the trust-section literals were still inline.
   Phase 26 R1 honestly scores this 70/100; the apparent regression
   on Dim 1 is the catch-up.

The trajectory of per-phase lifts becomes:
- Phase 21 → 22: ~+4-5 (honest)
- Phase 22 → 23: ~+2-3 (honest)
- Phase 23 → 24: ~+1-2 (honest)
- Phase 24 → 25: ~+1-2 (honest, less than reported)
- Phase 25 → 26: **+2.5 (honest)** — a small but real second wind

The reported trajectory (9.4 → 4.0 → 4.0 → 2.3 → 1.5 → 1.2) was
sliding toward 0; the honest trajectory has been ~+2 per phase
since Phase 22 with Phase 26 at +2.5.

## What Phase 26 actually delivered

* **Slice A (commit `10f4168`):** 6th tier_2_validated case —
  cantilever-beam-modal-candidate. First `*FREQUENCY` modal-
  eigenvalue solver kind in the validated cohort (prior 5 cases: 4
  linear-static + 1 linear-buckling). Closed-form Euler-Bernoulli
  `f_1 = (β·L)²·√(EI/ρA)/(2π·L²)` with β·L = 1.875104 (Rao §8.5).
  Real ccx 2026-05-17 run: 1,895 nodes / 814 C3D10 quad tets /
  analytical 66.8413 Hz / observed 66.9299 Hz / residual **+0.13%**
  (**TIGHTEST RESIDUAL ACROSS ALL 6 VALIDATED CASES**; 11.87%
  margin to 12% tolerance). Doublet structure at modes 1+2 and 3+4
  confirms square cross-section's identical bending stiffness about
  y and z. **15 unit tests** + **@requires_solver E2E pin**.
  A:-1 anti-gaming guard (rigid-body-mode filter rejecting <1.0 Hz)
  pinned at predicate AND test level.

* **Slice B (commit `ac87e41`):** Full Basic-mode gating threaded
  through ViewportDepthControls and the field-component switcher.
  Closes the Phase 25 C honest-scope gap where 3 of 4 show flags
  were computed but unused. **7 new component-level tests** + 11
  existing tests updated to pre-set localStorage = 'advanced'.
  State-preservation C:-1 contract now load-bearing across ALL 4
  features in ADVANCED_FEATURE_IDS.

* **Slice C (commit `4a1d87b`):** Probe-list A-vs-baseline Δ column.
  Pure helper `buildDiffPairs(state) → ProbeDiffPair[]` follows D:-2
  PIN-ORDER (baseline = first-pinned, NOT smallest/largest/selected).
  E:-1 null propagation, E:-2 column hidden when count < 2.
  Unicode-minus (U+2212) for negative Δ, not hyphen-minus. **18 new
  tests** + 2 Phase 24 D tests loosened (now `.toContain(label)`
  for baseline tag).

* **Slice D (commit `05e0f21`):** Trust Center view-model
  extraction. trustStrip + 5 of 7 sections + statusTone helper
  moved to `src/state/trustCenterViewModel.ts` (284 LOC pure
  module). **24 new tests** pin each builder's items count,
  individual tone derivations, and D:-3 no-mutation guard.
  **Honest scope:** Blueprint target + Ballistic candidate sections
  stay inline (large derived-locals closure); App.tsx grew +18 LOC
  (1446 → 1464) — the LOC target <1300 missed by 164. Honest debt.

**64 new tests total** (15 backend Phase 26 A + 7 frontend Phase 26 B
+ 18 frontend Phase 26 C + 24 frontend Phase 26 D). **All 452 frontend
tests** + **all backend Phase 18-26 regression** (292 tests, excl
requires_solver) pass. Live solver pin: cantilever modal C3D10 ~3s.

## What Phase 26 did NOT deliver vs blueprint

* **App.tsx <1300 LOC** — delivered 1464, missed by 164. Phase 26 D's
  extraction actually GREW the file. Honest scope debt.
* **Real WebGL E2E via puppeteer/playwright** — 6 phases open
  carry-forward.
* **Apple-tier polish BREADTH pass** — no new motion in Phase 26
  (Phase 25 D shipped tour + CSV; Phase 26 added baseline tag +
  Unicode minus but no row-easing / slider tracks / hover preview).
* **Shell elements / contact mechanics validated case** — Dim 1
  element library and Dim 4 solver kind both stuck below 80.
* **Tour copy refresh** — tour was written for Phase 24 B; doesn't
  mention Phase 25 C Basic mode or Phase 26 C Δ column.

## v2.3 round-cap=3 disposition: NO Round 2 spawned

Round 1 surfaced no Phase 20-style "real defects unit tests missed"
findings. Phase 26's load-bearing claims are independently
verifiable:

- **Phase 26 A** — live ccx residual +0.13% with 11.87% margin to
  12% tolerance. 15 unit tests including A:-1 anti-gaming guard
  (stub-list pin asserting filter rejects 1e-6 / 5e-7 while
  preserving 66.93 / 416.45 / 1153.11). Doublet structure verified
  in NOTES.md against the analytical β·L table.
- **Phase 26 B** — 7 component-level tests pin C:-1 state
  preservation across basic → advanced round-trip; existing 11
  tests still pass with explicit localStorage setup.
- **Phase 26 C** — 18 tests pin D:-2 (PIN ORDER), E:-1 (null
  propagation), E:-2 (column hidden when count<2); +/− Unicode glyph
  pinned at component test level.
- **Phase 26 D** — 24 tests pin each builder's items count, tone
  derivations under varying ctx values; D:-3 no-mutation guard.

The 24.3-point gap to 99 is structural:
- App.tsx full decomposition (Phase 26 D extracted 5/7 sections;
  Blueprint + Ballistic remain inline).
- Real WebGL E2E (carry-forward from Phase 21 C).
- Apple-tier motion breadth (carry-forward from Phase 25 D).
- New element types (S4 shell, contact pairs).
- New solver kinds (`*DYNAMIC`, `*HEAT TRANSFER`, `*CONTACT PAIR`).
- 7th-10th validated cross-check cases.
- Tour copy refresh + auto-promote sequencing.

Round 2 would polish 1-2 sub-dimensions but cannot move the
composite to 99 or even meaningfully toward the next 5-point step.
Round 2 = score-padding; violates the absolute-honesty contract.

## Phase 27 opening punchlist (filed from Phase 26 R1)

1. **App.tsx LOC reduction PROPER** — pick one of: (a) Blueprint
   target section to view-model extraction (would shrink ~40 lines);
   (b) ballisticEnergyTone / ballisticPerforationTone /
   ballisticTimeStepStudyTone derivations to view-model (~30 lines);
   (c) candidateAssumptions / candidateMeshEvidence summary builders
   to view-model (~30 lines). Pick whichever a/b/c is most testable
   independent.
2. **7th validated case** — shell-element candidate (S4 quad shell;
   simply-supported circular plate, axisymmetric bending) to lift
   FEA Dim 1 (element library) for the first time since Phase 18.
3. **Apple-tier polish breadth** — probe-list row easing on
   add/remove, custom threshold-filter slider tracks with gradient
   matching the legend, hover preview on section-cut position.
4. **Tour copy refresh** — mention Basic-mode toggle (Phase 25 C),
   Δ column (Phase 26 C), and the trust-strip rationale.
5. **Real WebGL E2E** — Phase 21 C carry-forward; pick puppeteer
   or playwright; one smoke test per major viewport feature.
6. **Trust-strip / trust-section memoization** — `useMemo` the
   trust-center view-model context bundles so the panel re-renders
   only when its inputs actually change. Pure builders make this
   trivial.
7. **Iso-surface rendering** (Phase 24 carry-forward).
8. **Probe-list save/restore across sessions** (extend Phase 25 D
   CSV path with import; localStorage + corrupted-key fallback).
9. **Second modal case** — different aspect ratio (e.g., L/h = 50
   stub or L/h = 6 stub) to exercise the Euler-Bernoulli envelope.
10. **Phase 24 carry-forward: CalculiX static viewer σ-tensor path**
    — still unaddressed.

## Decision

Phase 26 closes at composite **74.7/100, CHANGES_REQUIRED**. +2.5
over honest Phase 25 baseline. The 99/100 target remains a multi-
phase commitment.

Phase 26 was the depth phase the blueprint promised: 6th validated
case ships the first `*FREQUENCY` solver kind in the validated
cohort with the tightest residual (+0.13%) across all 6 cases.
Basic-mode gating now load-bearing across all 4 advanced features
(closes Phase 25 C honest-scope gap). Probe-list Δ column is the
first inline-comparison affordance and follows the same predicate-
level anti-gaming discipline as the 5 prior validated cases. Trust
Center view-model extraction lands the test-isolation surface for
future Phase 27 decompositions — even though it MISSED the App.tsx
LOC target by 164 lines and that miss is named verbatim.

The composite drop from reported 82.1 → 74.7 is the **honest re-
baseline event**: this phase, not later, pays the recalibration
debt that Phase 21-25 accumulated. The +2.5 lift over honest Phase
25 (~72.2) is the real signal; the -7.4 vs reported is the
calibration cost.

Round 1 reports archived alongside this FINAL:
* `UX.md` — 76.8/100, Dim 3 reviewer-flow +15.8 carries the lift
  (Δ column + 6th case + view-model testability).
* `FEA.md` — 75.0/100, Dim 2 +4 (5th → 6th case) + Dim 3 +3 (A:-1
  guard + envelope refusals) + Dim 4 +4 (*FREQUENCY entry).
* `UI.md` — 72.3/100, Dim 2 +7.9 (Basic mode 4/4 + Δ column) +
  Dim 1 -5 on absolute LOC (honest) + view-model extraction +30.

Not signed validation; not benchmark agreement.
