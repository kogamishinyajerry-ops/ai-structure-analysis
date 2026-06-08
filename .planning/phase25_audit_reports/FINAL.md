# Phase 25 — 5th validated case + App.tsx LOC + modes + polish · FINAL audit report

## Composite (round 1; no R2 spawned — see rationale below)

| Dimension | Round 1 | Phase 24 R1 | Blueprint projection | Delta vs P24 | Delta vs projection |
|---|---|---|---|---|---|
| UX | 84.0/100 | 82.6/100 | 84-85 | **+1.4** | inside band, low end |
| FEA | 76.0/100 | 74.8/100 | 76-77 | **+1.2** | inside band, low end |
| UI | 86.4/100 | 85.2/100 | 86-87 | **+1.2** | inside band, mid-low |
| **Composite** | **82.1** | **80.9** | **81.5-83.0** | **+1.2** | **inside band, +0.6** |

**Verdict:** CHANGES_REQUIRED. APPROVE requires composite ≥ 99 AND
each ≥ 99 AND no axis < 95%. Round 1 fails all three. The composite
lifted +1.2 over Phase 24 — sixth single-phase lift in the Tier 2 era
(after P21 +9.4 / P20 +7.3 / P22 +4.0 / P23 +2.3 / P24 +1.5).
**Landed INSIDE the blueprint's projection band (81.5-83.0) at the
low-mid end (82.1)** — **first inside-band landing since Phase 22**
(which closed at 77.1 inside its 75-80 band). Phase 23 was -1.6
below; Phase 24 was -0.1 below; Phase 25 is +0.6 above the lower
bound. Documented verbatim per the absolute-honesty contract.

## What landed inside / below band

- **UX 84.0 vs 84-85 projection**: inside band at low end (just at
  lower bound). Honest cause: Phase 25 C gated only the probe-list
  panel, not the threshold filter / section cut / per-component
  switcher inside ViewportDepthControls; full ViewportDepthControls
  gating would have pushed UX to ~84.8.
- **FEA 76.0 vs 76-77 projection**: inside band at low end. Honest
  cause: the 5th case promotion drove the validated-cases Dim 2
  needle (+4) but other FEA dims held flat (no new element type, no
  new solver kind). Total +1.2 lift matches projection.
- **UI 86.4 vs 86-87 projection**: inside band at mid-low end.
  Honest cause: industrial-CAE Dim 2 (+2) and visual-polish Dim 3
  (+2) carried the lift; LOC discipline Dim 1 only +1 because Phase
  25 B was a proof-of-concept extraction (App.tsx 1498 → 1446 vs
  blueprint target <1300).

## v2.3 round-cap=3 disposition: NO Round 2 spawned

Round 1 surfaced no Phase 20-style "real defects unit tests missed"
findings. Phase 25's load-bearing claims are independently
verifiable:

- **Phase 25 A** — live ccx run on 2026-05-17 produced 5.79%
  residual, well inside 15% tolerance with 9.21% margin. 14 tests
  including the A:-1 anti-gaming guard (center-node selection
  inside characteristic-disk) + strict registry pin
  `test_phase25a_validated_count_is_five`. Phase 23 A's strict pin
  loosened to subset-of via the same additive-promotion pattern;
  Phase 23 A intent (4 cases REQUIRED validated) preserved.
- **Phase 25 B** — 10 tests pin the builder contract. App.tsx LOC
  measurement is concrete: `wc -l frontend/src/App.tsx` → 1446.
- **Phase 25 C** — 15 tests including C:-1 anti-gaming guard
  (toggleMode purity, state preservation). Storage round-trip pin
  + corrupted-key fallback pin + SSR no-op pin.
- **Phase 25 D** — 12 tests including D:-1 anti-gaming guard (CSV
  preserves PIN ORDER, NOT sorted). Empty list / null fieldValue /
  NaN+Infinity / RFC-4180 quoting all pinned.

The 16.9-point gap to 99 is structural:
- CalculiX static viewer σ-tensor path (Phase 24 carry-forward).
- Real WebGL E2E via puppeteer/playwright (5 phases open
  carry-forward).
- Full App.tsx decomposition (Phase 25 B partial; trustStrip /
  trustSections / candidate-spine view-model still inline).
- Full ViewportDepthControls gating (Phase 25 C partial).
- Apple-tier polish (probe-list row easing, custom slider tracks,
  hover preview, viewport-mode transitions).
- New solver kinds (transient, Riks, contact, thermal coupling).
- Iso-surfaces / streamlines / multi-pick search / annotation —
  multi-phase scope.
- 6th-9th validated cross-check cases.

Round 2 here would polish 1-2 sub-dimensions but cannot move the
composite to 99 or even meaningfully toward the next 5-point step.
Round 2 = score-padding; that violates the absolute-honesty
contract carried verbatim from Phase 18-24.

## What Phase 25 actually delivered (honest accounting)

* **Slice A (commit `8a532c9`):** Simply-supported plate cross-check
  runner. Closed-form Timoshenko α=0.00406 in
  `plate_simply_supported.py`; self-contained `plate_ss_runner.py`
  (~390 LOC) hand-rolls a 4-edge clamp + 3-corner RBM pin + pressure-
  equivalent nodal-load INP. Real ccx 2026-05-17 run: 4420 nodes /
  2125 C3D10 tets / analytical -0.264 mm vs observed -0.249 mm /
  residual **-5.79%**. **Validated count 4 → 5.** 14 tests
  including A:-1 anti-gaming guard + E2E pin.

* **Slice B (commit `2850f3c`):** Cmd-K palette command builder +
  topbar material-options mapper extracted to
  `frontend/src/state/paletteCommands.ts`. **App.tsx 1498 → 1446
  LOC (-52).** ZERO behavior change. HONEST SCOPE: blueprint target
  was <1300 LOC; full decomposition deferred to Phase 26. 10 new
  tests.

* **Slice C (commit `dad0771`):** Basic / Advanced UI mode toggle.
  Pure-function state machine in `uiMode.ts`; UiModeToggle
  segmented-control component; mounted in ResultMeshPlaybackPanel
  header. localStorage persistence with corrupted-key fallback.
  ProbeListPanel rendering gated on `shouldShowFeature(uiMode,
  'probe-list-panel')`. **HONEST SCOPE:** Phase 25 C gates ONLY
  probe-list panel; ViewportDepthControls (threshold filter /
  section cut / per-component switcher) NOT gated — Phase 26
  follow-up. 15 new tests including C:-1 anti-gaming guard.

* **Slice D (commit `a315297`):** OnboardingTour fade+slide-in
  animation (200ms ease-out, prefers-reduced-motion respected) +
  ProbeListPanel "Export CSV" button + pure-function
  `serializeProbeListAsCsv` (RFC-4180 quoted, PIN ORDER preserved,
  NaN/Infinity/null → empty cell). **HONEST SCOPE:** Apple-tier
  polish (probe-list row animations, custom slider tracks, hover
  preview) NOT shipped — Phase 26 punchlist. 12 new tests
  including D:-1 anti-gaming guard.

**51 new tests total** (14 backend Phase 25 A + 10 frontend Phase 25 B
+ 15 frontend Phase 25 C + 12 frontend Phase 25 D). **All 403
frontend tests** + **all backend Phase 18-25 regression** (excl.
requires_solver) pass. Live solver pin times: B31 buckling ~1s,
cantilever C3D10 ~3s, plasticity ~1s, plate Kirsch ~1s, plate-SS ~6s.

## What Phase 25 did NOT deliver vs blueprint

* **App.tsx LOC reduction:** target <1300, delivered 1446 (-52).
  Full reducer / view-model extraction is a multi-slice refactor;
  Slice B shipped the wedge.
* **Full ViewportDepthControls gating** in Basic mode — Phase 25
  C gates only the probe-list panel.
* **Apple-tier polish breadth** — only the tour fade-slide and the
  CSV export shipped; row-easing / slider tracks / hover preview
  deferred.
* **Real WebGL E2E** (Phase 21 C carry-forward) — still mock-only,
  5 phases open.

## Phase 26 opening punchlist (filed from Phase 25 R1)

1. **CalculiX static viewer σ-tensor path** (Phase 24 carry-
   forward) — or honest deprecation if no consumer exists.
2. **Real WebGL E2E via puppeteer/playwright** — Phase 21 C
   carry-forward; 5 phases open.
3. **6th validated case** — pick a contact-mechanics or transient
   case to lift FEA Dim 4 (solver kind coverage still 68).
4. **Full App.tsx decomposition** — extract trustStrip /
   trustSections / candidate-spine view-model; target <1200 LOC.
5. **Full Basic-mode gating** — thread uiMode through
   ViewportDepthControls so threshold filter / section cut /
   per-component switcher hide in Basic mode.
6. **Apple-tier polish breadth pass** — probe-list row add/remove
   easing, custom threshold-filter slider tracks with gradient
   matching the legend, hover preview on section-cut position.
7. **Iso-surface rendering** (Phase 24 carry-forward).
8. **Probe-list diff column** (node A − node B inline).
9. **Probe-list save/restore across sessions** (extend Phase 25 D
   CSV path with import).
10. **Tour auto-promotes to Advanced after dismissal** (deeper
    novice-to-advanced sequencing).

## Decision

Phase 25 closes at composite **82.1/100, CHANGES_REQUIRED**. +1.2
over Phase 24. The 99/100 target remains a multi-phase commitment.

Phase 25 was the depth phase the blueprint promised: 5th validated
case promotion drives FEA Dim 2; App.tsx LOC reversal continues
(modestly); Basic-mode toggle gives returning reviewers a non-modal
cognitive-load escape; tour fade-slide + CSV export are the first
two concrete polish items. **First inside-band landing since Phase
22** — the per-phase trajectory still trends down (9.4 → 4.0 → 4.0
→ 2.3 → 1.5 → 1.2) but the band-landing signal is positive.

Round 1 reports archived alongside this FINAL:
* `UX.md` — 84.0/100, cognitive-load +3 (Basic mode) + novice
  +2 + reviewer-flow +1 (CSV).
* `FEA.md` — 76.0/100, validated cases +4 (4 → 5 promotion),
  Dim 1/3/4 held flat.
* `UI.md` — 86.4/100, industrial-CAE +2 (Basic + CSV) + polish
  +2 (tour motion), LOC discipline +1 (modest).

Not signed validation; not benchmark agreement.
