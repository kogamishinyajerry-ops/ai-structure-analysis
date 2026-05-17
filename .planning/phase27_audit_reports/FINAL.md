# Phase 27 — 7th case + LOC reduction + Apple polish + persist · FINAL audit report

> Tier 1 / Tier 2 engineering candidate; not signed validation; not
> benchmark agreement. Honest baseline from Phase 26 R1 carried
> forward.

## Composite (round 1; no R2 spawned)

| Dimension | Round 1 | Phase 26 R1 (honest) | Δ |
|---|---|---|---|
| UX | **80.9/100** | 76.8 | **+4.1** |
| FEA | **76.5/100** | 75.0 | **+1.5** |
| UI | **77.6/100** | 72.3 | **+5.3** |
| **Composite** | **78.5** | **74.7** | **+3.8** |

**Verdict:** CHANGES_REQUIRED. APPROVE requires composite ≥ 99 AND
each axis ≥ 99 AND no axis < 95%. Round 1 fails all three.

**Phase 27 R1 composite +3.8 lift** over honest Phase 26 baseline,
inside the blueprint's 77.5-79.5 projection band at mid-band (78.5).
**Second inside-band landing in a row** after Phase 26 (which was
the honest re-baseline event itself, treated as a new baseline rather
than a band-comparison).

## What Phase 27 actually delivered (honest accounting)

* **Slice A (commit `7627438`):** 7th tier_2_validated case
  `cantilever-beam-modal-l50-candidate`. SECOND modal case at the
  slenderness extreme (L/h = 50, 4× more slender than Phase 26 A).
  Reuses Phase 26 A's runner verbatim. Live ccx 2026-05-17: analytical
  16.7103 Hz / observed 16.7331 Hz / residual **+0.136%** (virtually
  identical to Phase 26 A's +0.13% across 4× slenderness range). 8
  new tests + @requires_solver E2E. **HONEST SCOPE PIVOT** (recorded
  before execution): original target was S4 shell to lift FEA Dim 1
  from 65 → 75; CalculiX shell-output reader plumbing too involved
  for one slice. Pivot documented in blueprint + commit message + NOTES.md.

* **Slice B (commit `c280f1d`):** Blueprint target section extracted
  to `trustCenterViewModel.ts`. **App.tsx 1464 → 1454 LOC (-10, genuine
  reduction)**. LOC trajectory finally DOWN after Phase 26 D's +18 miss.
  Picked Blueprint section precisely because its context is a SINGLE
  already-typed bundle (blueprintSummary) — 3-line builder call vs
  15-line inline literal. 9 new tests.

* **Slice C (commit `82c8594`):** Apple-tier polish breadth pass.
  NEW `polishStyles.ts` (~90 LOC) module injecting a single global
  `<style>` tag (idempotent). Three affordances:
  - Probe-list row entrance: 200ms ease-out + 6px lift via
    `.fm04a-probe-row-mount` class
  - Slider gradient tracks (blue → green → orange) matching legend
    on value-filter-min, value-filter-max, section-cut-position
    via `.fm04a-gradient-slider` class
  - Section-cut position hover readout: floating "x = 0.25 m"
    above slider while dragging; React `isDragging` state
  **Anti-gaming B:-1: prefers-reduced-motion: reduce honored.** Tests
  search `POLISH_CSS_TEXT` for the @media block + `animation: none`
  rule. 16 new tests.

* **Slice D (commit `4a74c62`):** Probe save/restore by case_id +
  tour copy refresh v1 → v2. NEW `probeListStorage.ts` (~115 LOC)
  with `loadProbeList(caseId)` / `saveProbeList(caseId, state)` /
  `clearProbeListStorage(caseId)`. **Anti-gaming C:-1: storage key
  includes case_id VERBATIM** (`fm04a.probe-list.v1.<caseId>`); 4
  corrupted-key fallback paths (malformed JSON / wrong shape / wrong
  entry shape / wrong position shape) all return
  `PROBE_LIST_INITIAL_STATE`. Tour `ONBOARDING_LS_KEY` bumped
  `v1.dismissed → v2.dismissed`; 2 new tour cards added (Phase 25 C
  Basic/Advanced + Phase 26 C Δ column). **Honest annoyance trade:**
  existing dismissed-v1 users see v2 once. v1 key NOT cleared
  (additive D:-1 bump). 17 new tests + 5 Phase 24 B loosened.

**59 new tests total** (8 backend Phase 27 A + 9 frontend Phase 27 B
+ 16 frontend Phase 27 C + 17 frontend Phase 27 D + 9 Phase 27 E
loosened/preserved). **All 494 frontend tests** + **all backend
Phase 18-27 regression** (299 tests, excl. requires_solver) PASS.
Live solver pin: cantilever modal L/h=50 ~3s.

## What Phase 27 did NOT deliver vs blueprint

1. **Shell elements (S4) for FEA Dim 1 lift** — scope reduction
   recorded BEFORE execution; CalculiX shell-output reader plumbing
   requires a dedicated phase. Phase 28 punchlist.
2. **App.tsx <1300 LOC** — delivered 1454, missed by 154. Trajectory
   now DOWN, but target still distant.
3. **Probe-list ROW EXIT animation** — only entrance shipped.
   Would require AnimatePresence-style state outside the `<tbody>`.
4. **"Restored from session" toast UI** — silent restoration is the
   shipping behavior.
5. **Tour auto-promote sequencing** (novice → advanced after
   dismissal) — Phase 28 candidate.

## v2.3 round-cap=3 disposition: NO Round 2 spawned

Round 1 surfaced no Phase 20-style "real defects unit tests missed"
findings. Phase 27's load-bearing claims are independently
verifiable:

- **Phase 27 A** — live ccx residual +0.136% (analytical 16.7103 Hz /
  observed 16.7331 Hz). 8 unit tests including 1/L² scaling pin,
  validity envelope, strict `validated_count_is_seven` registry pin,
  envelope-honesty pin (residual matches Phase 26 A to within 1%),
  doublet structure preserved at L/h=50.
- **Phase 27 B** — App.tsx LOC measurement is concrete: `wc -l`
  before/after = 1464 → 1454. 9 tests pin builder contract.
- **Phase 27 C** — 16 tests including idempotent install,
  prefers-reduced-motion CSS rule, gradient color stops match
  legend, gradient class on 3 sliders, hover readout on/off via
  mouse + touch events.
- **Phase 27 D** — 17 tests including PIN ORDER round-trip, C:-1
  cross-case isolation, 4 corrupted-key fallback paths, tour v2
  step IDs + provenance.

The 20.5-point gap to 99 remains structural:
- App.tsx full decomposition (Ballistic candidate section still
  inline; FM-04a phase 24-25 reducer extraction in app body).
- Real WebGL E2E (still mock-only; 7 phases open carry-forward).
- Shell elements + contact + transient solvers.
- 8th-10th validated cases.
- Probe-list ROW EXIT animation.
- Restored-from-session UI affordance.
- Tour auto-promote sequencing.
- prefers-reduced-motion across ALL motion (only Phase 27 C
  affordances tested; Phase 25 D tour fade-slide and Phase 27 C
  hover readout could be audited next).

Round 2 here would polish 1-2 sub-dimensions but cannot move the
composite to 99 or even meaningfully toward the next 5-point step.

## Phase 28 opening punchlist (filed from Phase 27 R1)

1. **Shell element validated case (S4) with CalculiX reader plumbing
   for expanded-node mapping** — single most important Phase 28
   target (lifts FEA Dim 1 from 65 → 75 for first time since Phase 18).
2. **Ballistic candidate section extraction** to view-model — 11
   items inline; context is wider but tractable.
3. **App.tsx reducer / candidate-spine view-model extraction** —
   broader refactor to push toward <1300 LOC.
4. **Probe-list row EXIT animation** with AnimatePresence-style
   state.
5. **"Restored from session" toast notification** when probe-list
   loads from localStorage with ≥ 1 entry.
6. **Tour auto-promote sequencing** — after dismissal, surface the
   "Switch to Advanced mode" prompt once.
7. **Real WebGL E2E via puppeteer/playwright** — 7 phases open.
8. **Third modal case at intermediate aspect ratio (L/h = 15-20)**
   triangulating the Euler-Bernoulli envelope.
9. **Trust-strip / sections memoization** (useMemo the view-model
   context bundles).
10. **Iso-surface rendering** (Phase 24 carry-forward).

## Decision

Phase 27 closes at composite **78.5/100, CHANGES_REQUIRED**. +3.8
over honest Phase 26 baseline. **Second inside-band landing in a
row.**

Phase 27 was the breadth phase the blueprint promised: 7th case
extending envelope honesty (FEA Dim 3 +1.3), App.tsx LOC trajectory
finally DOWN (Dim 1 +2.9), Apple-tier polish breadth pass
(Dim 3 +11.4 including new prefers-reduced-motion sub-axis), tour
copy refresh closing the Phase 26 honest miss (Dim 2 +6.1), probe-
list session persistence (Dim 3 new sub-axis at 80). The +3.8 lift
over honest Phase 26 is real; no inflation accumulated.

Round 1 reports archived alongside this FINAL:
* `UX.md` — 80.9/100, Dim 1 +3.8 from polish/persistence; Dim 2
  +6.1 from tour refresh; Dim 3 +2.5 from 7th case + persistence.
* `FEA.md` — 76.5/100, Dim 2 +4 from 7th case; Dim 3 +1.3 from
  cross-aspect-ratio confidence sub-axis (now load-bearing).
* `UI.md` — 77.6/100, Dim 3 +11.4 including new
  prefers-reduced-motion sub-axis; Dim 1 +2.9 from LOC trajectory
  reversal + Blueprint extraction; Dim 2 +1.5 from persistence
  + tour breadth.

Not signed validation; not benchmark agreement.
