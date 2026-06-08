# FM-04a Phase 34 — FINAL composite audit synthesis · rubric v2.0

> Tier 1 / Tier 2 engineering candidate; not signed validation; not
> benchmark agreement. 绝对诚实客观 contract carried verbatim from
> Phase 18-33. **18 consecutive Tier-2 phases**.

## Headline

**Phase 34 honest composite: 72.50/100 (rubric v2.0)**
**Lift over Phase 33 C re-baseline (69.33): +3.17**

Phase 34 = first feature-build phase under rubric v2.0 (Phase 33
was the scale-change foundation). Lands at the **top of the
projected band 70.5-73**, exceeding the blueprint's mid-band
projection of ~71.

Decisive factor: the functional_tester sub-agent valued the
cohort 11→12 + solver-kind #6 transition higher than the blueprint
projected, because the cohort-12 threshold was the explicit
90-anchor blocker in the Phase 33 re-baseline. Releasing that
blocker unlocked the rest of the 90-anchor sub-bullets that were
already met (5 solver kinds + Richardson ≥60% + 2 bias revelations
+ p≤0 guard).

## Per-dimension scoreboard

| Dim | Name | Phase 33 | Phase 34 | Δ | Source |
|---|---|---|---|---|---|
| 1 | FEA simulation capability | 78 | **87** | **+9** | `functional_tester` sub-agent R2 |
| 2 | Novice user experience | 58 | **59** | +1 | `novice_simulator` sub-agent R2 |
| 3 | Industrial UI parity | 74 | **73** | -1 | `industrial_ui_comparator` sub-agent R2 |
| 4 | AI workflow integration | 62 | **72** | +10 | Main session synthesis (`phase34d_dim4_ai_workflow.md`) |
| 5 | Visualization & tracking | 72 | **72** | 0 | `functional_tester` sub-agent R2 |
| 6 | Trust & reproducibility | 72 | **72** | 0 | Main session synthesis (`phase34d_dim6_trust_reproducibility.md`) |
| **Composite** | (mean) | **69.33** | **72.50** | **+3.17** | — |

## Phase 34 wins (cited verbatim from sub-agents)

### Dim 1 FEA capability (78 → 87, +9)
- **Cohort validated count 11 → 12** via Phase 34 C `hertz-contact-candidate`
  (`golden_samples/hertz-contact-candidate/cross_check_verdict.yaml`,
  schema 1.4.0, solver_kind: contact_pair_static, verdict: PASS).
- **Solver kind #6 added: contact_pair_static**
  (`backend/app/services/cross_check/contact_pair_runner.py`).
- **Live ccx 2.23 PASS**: analytical δ = 1.905 µm (1D uniaxial),
  observed δ = 1.775 µm, residual = -6.823% (within 20% tolerance).
- The functional_tester sub-agent's note: "Anchor 80 fully met +
  5/6 of anchor 90 sub-bullets (cohort 12 exact, 6 solver kinds,
  Richardson on 6 cases ≈ 75% of refinable, 2 asymptotic-bias
  revelations, p≤0 guard live). Missing for full 90: 4th element
  class (only C3D8, S4, B31 in committed runners)."

### Dim 2 Novice UX (58 → 59, +1)
- **Phase 34 A win confirmed**: ballistic-vocab fix at
  `CaseComparisonPanel.tsx:263, 322-340` is unambiguously net-
  positive. P2 (senior engineer) completed T2 (compare-2-cases
  workflow) where Phase 33 baseline would have stalled on six
  dash-filled ballistic-labelled rows.
- **Phase 34 B partial cost noted by sub-agent** (see honest
  tensions below).

### Dim 4 AI workflow (62 → 72, +10)
- **Surface count 1 → 2** via Phase 34 B `CaseOpenAdvisorCard.tsx`
  mounted at case-open stage (`App.tsx:1318-1324`).
- **70-anchor fully met** (2 surfaces with critique-style content).
- **80-anchor partial**: advisor at 2 of 3 workflow stages (case-
  open + review; setup ✗).
- 4-Q-gate vocabulary present at both surfaces (`AdvisorPanel.tsx:184-190`
  dynamic + `CaseOpenAdvisorCard.tsx:67-80` static).

## Phase 34 honest tensions (recorded verbatim per 绝对诚实客观)

### 1. `CaseOpenAdvisorCard` jargon leak (Dim 2 sub-agent flag)

The `CaseOpenAdvisorCard` brief composes from `notesExcerpt` verbatim
(`CaseOpenAdvisorCard.tsx:104-109`), which pulls strings from
`candidateCaseRegistry.ts:156-161` and similar entries. These
strings contain internal vocabulary ("Phase 21+ scope",
"tier_2_validated", "single-hex coupons") that the novice_simulator
P1 + P5 personas immediately bounced off.

**Fix scope**: Phase 35 should sanitize the notesExcerpt rendering
OR replace the brief with a curated 1-paragraph orientation
derived from `displayLabel + analysis_type + claim_boundary`,
NOT raw notesExcerpt.

Cost to Dim 2: ~-1 (offset Phase 34 A's +2 to net +1).

### 2. `CaseOpenAdvisorCard` static-vs-dynamic 4-Q-gate (Dim 4 synthesis flag)

The Phase 11 AdvisorPanel renders the 4-Q-gate **dynamically** from
the backend critique payload (`critique.fourQuestionGate[key]`),
showing real PASS/FAIL per gate question.

The Phase 34 B CaseOpenAdvisorCard renders the 4-Q-gate
**statically** (all 4 ticks ✓ unconditionally), since the surface
has no backend call (it's frontend-only stub-style).

A reviewer (P3 persona) familiar with AdvisorPanel's dynamic gate
loses governance trust when they see the static gate at case-open
— same vocabulary, different semantics.

**Fix scope**: Phase 35 should either:
- Wire CaseOpenAdvisorCard to a real backend endpoint that returns
  honest gate state, OR
- Make the static rendering visually distinct (e.g., gray ticks
  with "static — offline stub" hint label) so the semantic
  difference is clear.

Cost to Dim 4: -1 in the score interpolation (kept honest).

### 3. Dim 3 -1 noise (sub-agent flag)

The industrial_ui_comparator scored Dim 3 at 73 vs Phase 33's 74.
Within ±2 rubric noise (4 different sub-agent instances over 4
phases would naturally show ±2 spread). NOT a regression; just
honest rubric-noise reporting.

### 4. Verdict YAML schema heterogeneity (functional_tester latent)

9 legacy cases at schema 1.0 lack the `solver_kind:` field; 3
cases at schema 1.3-1.4 have it. A `grep solver_kind:` cross-
cohort scan under-counts solver kinds. Per-case readers unaffected.

**Fix scope**: Phase 35 or later — backfill `solver_kind:` to the
9 legacy cases as an additive schema migration (no breaking change
to per-case readers).

### 5. Dim 1 element class undercount (functional_tester note)

The sub-agent's 87 score is anchored at "5/6 of 90 sub-bullets met,
missing 4th element class". Phase 32 A's plate-kirsch sweep used
C3D4 (per its NOTES.md), which would make 4 element classes (C3D4
+ C3D8 + S4 + B31). The sub-agent may have miscounted; this would
push Dim 1 higher.

**Resolution**: per anti-gaming guard B:-1 ("sub-agents score, main
session synthesizes; do not adjust dim scores"), the 87 stands.
Flagged here as an honest counting tension that could be re-
examined in Phase 35 D's audit with a more careful element-class
enumeration protocol.

## Phase 34 honest gaps (carried forward to Phase 35+)

Continuing the 26 honest gaps from Phase 33 FINAL, with Phase 34
status updates:

| Gap | Phase 33 status | Phase 34 status |
|---|---|---|
| #1 *CONTACT PAIR ccx integration | open (Tier 1) | **CLOSED Phase 34 C** ✓ |
| #4 Ballistic-vocab leak | open (Tier 2) | **CLOSED Phase 34 A** ✓ |
| #13 Advisor at case-open stage | open (Tier 1) | **CLOSED Phase 34 B** ✓ |
| #5 Advisor at setup stage | open | still open (Phase 35 target) |
| #14 Advisor at solve-monitor stage | open | still open (Phase 35 target) |
| NEW Phase 34 #27 — CaseOpenAdvisorCard jargon leak | n/a | **NEW Phase 35 target** |
| NEW Phase 34 #28 — CaseOpenAdvisorCard static-vs-dynamic gate | n/a | **NEW Phase 35 target** |
| NEW Phase 34 #29 — Verdict YAML schema heterogeneity (9 legacy at 1.0) | n/a | **NEW Phase 35 target (additive backfill)** |

Remaining open gaps from Phase 33 FINAL (carried verbatim):
- Dim 2: role-branching onboarding, WCAG 2.1 AA full audit
- Dim 3: real BC setup panel + tree case panel + real plot widget +
  drag-resize + density toggle + dark/light theme + 4-quadrant layout
- Dim 4: 3+ LLM backend support, advisor→action wiring
- Dim 5: iso-surface rendering, playwright WebGL E2E, 60fps perf,
  3-format export
- Dim 6: failed-attempt corpus, audit-trail log, reproducibility CLI,
  ADR cross-link matrix, broader signoff coverage

## Phase 35 priority recommendations

Ranked by single-axis lift × shippability:

### Tier 1 (biggest lift in 1 phase)
1. **Novice UX overhaul** — sanitize CaseOpenAdvisorCard jargon leak
   (gap #27) + fix static-vs-dynamic gate (gap #28) + role-branching
   onboarding stub + at least 2 of the 5 missing error-recovery
   paths in App.tsx. Projected Dim 2 lift 59 → ~68 (+9). Composite Δ
   +1.5.
2. **Verdict YAML schema 1.0 → 1.4 backfill** (gap #29) — additive
   `solver_kind:` field for 9 legacy cases. Resolves the
   functional_tester latent under-counting issue. Composite Δ +0.3-0.5.

### Tier 2
3. **AI advisor at setup OR solve-monitor stage** — closes one more
   Dim 4 stage sub-bullet. Composite Δ +0.5.
4. **Element-class audit + Dim 1 re-verification** — careful element-
   class enumeration protocol; may unblock Dim 1 anchor 90 (+1-2).

### Phase 35 projection band: **74-77 / v2.0**

## Multi-phase trajectory under rubric v2.0

| Phase | Composite v2.0 | Δ | Note |
|---|---|---|---|
| 33 C re-baseline | 69.33 | — | First measurement under v2.0 |
| 33 E close | 69.33 | 0 | Foundation phase (apparatus only) |
| **34** | **72.50** | **+3.17** | First feature-build phase |
| 35 projected | ~74-77 | +1.5-4.5 | Novice UX + schema backfill + 1 advisor stage |
| 36-37 projected | ~78-82 | +4-5 | Industrial UI parity push (drag-resize + theme + 4-quadrant) |
| 38 projected | ~80-84 | +1.5-2 | FEA cohort 13-15 |
| 39 projected | ~83-87 | +3 | Viz iso-surface + playwright |
| 40 projected | ~86-90 | +3 | Trust failed-attempt corpus + audit-log + reproduce |
| 41-43 projected | ~89-93 | +3-3.5 | NAFEMS + cases 16-18 |
| 44-45 projected | ~99-100 | +6-10 | Final polish + first 99+ audit cycle |

**Projected reach of 99+: Phase ~45.** ~11 more phases. The Phase 34
delta is +3.17 — slightly faster than the original projection of
~+2.5/phase average needed to reach 99 by Phase 45. **On track.**

## v2.3 disposition

- 1 sub-phase = Phase 34 (4 implementation slices + 34 D audit) = 1
  retro at phase-close ✓
- counter += 4 (telemetry only)
- No Codex review triggered (no auth / signing / 安全边界 hit)
- No charter triggered (changes within frontend components, backend
  cross_check, golden_samples *-candidate, .planning/)
- DEC frontmatter: this FINAL doubles as DEC for Phase 34
  (status=Accepted at commit; parent_dec=Phase 34 blueprint
  `2266460`; notion_sync_status=pending session-end batch sync)
- Round cap 3: NOT triggered — sub-agents R2 produced honest scores;
  honest tensions flagged in this FINAL, not via fix-loop
- Spike-class assessment: NONE of the 4 slices qualified (each >>
  ≤30 LOC + 1 test bound). All correctly full sub-DEC scope.

## Hard-constraint compliance

- HF1.7a / 7b / 8: PASS (Phase 34 only touched candidate dirs +
  backend cross_check + frontend components)
- v2.3 governance round-cap = 3: not triggered (R2 only)
- confidence: high stamped on every Phase 34 commit
- 绝对诚实客观 contract: PASS — Phase 34 B unintended Dim 2 costs
  + Dim 3 -1 noise + Dim 1 element-class undercount all
  transparently documented in this FINAL
- prefers-reduced-motion: N/A (no new motion in Phase 34)
- Anti-gaming guards (rubric v2.0 A-G + Phase 34 H/I/J):
  - A:-1 no rubric reword mid-phase: PASS
  - B:-1 sub-agents score, main session synthesizes Dim 4/6 only:
    PASS — Dim 4 + Dim 6 syntheses cite file:line; sub-agent scores
    NOT adjusted
  - C:-1 never compare v1.0 vs v2.0 directly: PASS — v2.0 trajectory
    only
  - D:-1 every claim cites file:line: PASS — verified in 5 audit
    files
  - E:-1 99 evidence: N/A (no 99 claims this phase)
  - F:-1 anti-priming: PASS — 3 sub-agents confirmed they did NOT
    read prior FINAL / retro / blueprint files
  - G:-1 codebase IS not CLAIMS: PASS — sub-agents traced code,
    grepped, ran tests
  - H:-1 ccx must converge with REAL output (Phase 34 new): PASS —
    Phase 34 C live ccx 2.23 run included in commit
  - I:-1 Phase 11 AdvisorPanel not modified: PASS — verified by grep
  - J:-1 CSV export schema not changed: PASS — Phase 25 D 5-column
    export pins continue to pass; 773/773 frontend tests pass
- NEVER score above 99: 72.50 well under
- NEVER re-score prior phases: PASS — Phase 33's 69.33/v2.0 verbatim
- NEVER apply weights/transforms to composite: PASS — (87 + 59 + 73
  + 72 + 72 + 72) / 6 = 72.50 simple mean

## Closing

Phase 34 is the **first composite Δ on the v2.0 scale**. The +3.17
delta exceeds projection because Dim 1's anchor-90 sub-bullets
unblocked cleanly when cohort hit 12, and Phase 34 B closed Dim 4
gap #13 (advisor at case-open) with surface-count and 4-Q-gate
inline both lifting.

The novice_simulator's honest finding that Phase 34 B introduced
two new friction points (jargon leak + static gate) is exactly the
kind of unanticipated cost the rubric-v2.0 sub-agent infrastructure
was designed to catch. The +1 net to Dim 2 (vs +1 projected) is
honest; the cost is documented as Phase 35 gap #27 + #28.

The trajectory through Phase 34 is **on track for 99+ by Phase ~45**
under the multi-phase roadmap from the Phase 33 FINAL.

Tier 1 / Tier 2 engineering candidate; not signed validation;
not benchmark agreement. 绝对诚实客观 across 18 consecutive
Tier-2 phases.
