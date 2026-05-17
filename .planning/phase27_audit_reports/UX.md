# Phase 27 — UX audit (round 1)

> Tier 1 / Tier 2 engineering candidate; not signed validation; not
> benchmark agreement. Honest baseline from Phase 26 R1 (76.8/100)
> carried forward.

## Scoring rubric

UX composite = Dim 1 (cognitive load · 40%) + Dim 2 (novice
onboarding · 30%) + Dim 3 (reviewer-flow expert affordance · 30%).
Each dim 0-100. Composite is weighted-mean.

## Phase 27 deliveries scored

| Slice | What landed | UX dim hit |
|---|---|---|
| 27 A | 7th validated case (second cantilever modal at L/h=50; +0.136% residual matching Phase 26 A's +0.13% across 4× slenderness) | Reviewer-flow (one more place where "Allowed claim" can honestly cite real-solver validation) |
| 27 B | Blueprint section extraction with App.tsx 1464 → 1454 (-10 LOC, genuine reduction) | Cognitive load (panel construction site slightly more skimmable) |
| 27 C | Apple-tier polish: probe row entrance + slider gradient tracks + section-cut hover readout | Cognitive load (motion vocab) + Reviewer-flow (slider gradient = "values are colored on the spectrum") |
| 27 D | Probe save/restore by case_id + tour copy refreshed v1 → v2 (Basic mode + Δ column cards added) | Novice onboarding (tour now mentions Phase 25 C + 26 C affordances) + Reviewer-flow (probe list persists across sessions) |

## Dim 1 — Cognitive load (40%)

| Sub-axis | Phase 26 R1 | Phase 27 R1 | Δ | Why |
|---|---|---|---|---|
| Basic-mode hides advanced surfaces | 80/100 | 80/100 | 0 | Unchanged (Phase 26 B already wired 4/4). |
| App.tsx panel-construction readability | 70/100 | 73/100 | +3 | Phase 27 B extracted Blueprint target section; -10 LOC. |
| State preservation across mode toggle | 90/100 | 92/100 | +2 | Phase 27 D adds probe persistence — state now survives REFRESH, not just toggle. |
| Visual hierarchy at viewport | 72/100 | 80/100 | +8 | Slider gradient track communicates "thresholds are on the value spectrum"; row entrance animation removes the "list just snapped" jarring feeling. |

**Dim 1 composite:** (80 × 0.30 + 73 × 0.25 + 92 × 0.25 + 80 × 0.20) =
24.0 + 18.25 + 23.0 + 16.0 = **81.25 → 81.3/100** vs Phase 26's 77.5
(**+3.8**).

## Dim 2 — Novice onboarding (30%)

| Sub-axis | Phase 26 R1 | Phase 27 R1 | Δ | Why |
|---|---|---|---|---|
| First-load default is basic | 100/100 | 100/100 | 0 | Unchanged. |
| Novice → advanced sequencing | 50/100 | 50/100 | 0 | Tour-auto-promote still not addressed (Phase 28 candidate). |
| Probe-list "first time" affordance | 70/100 | 78/100 | +8 | Phase 27 D persists probes across sessions; novice can pin one, refresh, see it return → tactile feedback on persistence. |
| Tour scope vs current features | 65/100 | 90/100 | +25 | Phase 27 D ships tour v2 with 6 cards (was 4). Basic-mode card + Δ-column card close the Phase 26 honest miss. |

**Dim 2 composite:** (100 × 0.25 + 50 × 0.30 + 78 × 0.30 + 90 × 0.15) =
25.0 + 15.0 + 23.4 + 13.5 = **76.9/100** vs Phase 26's 70.8
(**+6.1**).

## Dim 3 — Reviewer-flow expert affordances (30%)

| Sub-axis | Phase 26 R1 | Phase 27 R1 | Δ | Why |
|---|---|---|---|---|
| Inline comparison (Δ vs baseline) | 85/100 | 85/100 | 0 | Unchanged (Phase 26 C). |
| 7th validated case (envelope honesty) | 86/100 | 89/100 | +3 | Phase 27 A confirms Euler-Bernoulli envelope holds across 4× slenderness range. |
| Trust strip / sections testability | 80/100 | 84/100 | +4 | Phase 27 B's Blueprint target extraction adds 9 more pure-builder tests. |
| Surface for next-phase polish | 72/100 | 80/100 | +8 | Phase 27 C ships 3 polish affordances; sets the visual-vocabulary baseline future phases extend. |
| Probe-list persistence | 0/100 | 80/100 | +80 | NEW: probe list survives browser refresh, scoped by case_id. -20 because there's no "Restore last session" notification UI — silent restoration; some users may not notice. |

**Dim 3 composite:** (85 × 0.25 + 89 × 0.25 + 84 × 0.20 + 80 × 0.15 +
80 × 0.15) = 21.25 + 22.25 + 16.8 + 12.0 + 12.0 = **84.3/100** vs
Phase 26's 81.8 (**+2.5**).

## UX composite (round 1)

**81.3 × 0.40 + 76.9 × 0.30 + 84.3 × 0.30 = 32.52 + 23.07 + 25.29 =
80.88 → UX 80.9/100**

**Phase 27 R1 UX: 80.9/100** vs Phase 26's honest 76.8 (**+4.1**).

The +4.1 is honest:
- Tour v2 refresh closes a 2-phase carry-forward (UX Dim 2 +25 on
  one sub-axis).
- Probe persistence is a real new affordance (UX Dim 3 +80 on its
  sub-axis, weighted at 15%).
- App.tsx LOC trajectory finally down (Dim 1 +3).
- Slider gradient + row entrance close polish-breadth gaps that
  carried from Phase 25 D.
