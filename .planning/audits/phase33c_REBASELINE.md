# FM-04a Phase 33 C — Honest re-baseline under rubric v2.0

> Tier 1 / Tier 2 engineering candidate; not signed validation; not
> benchmark agreement. 绝对诚实客观 contract carried verbatim from
> Phase 18-32. **17 consecutive Tier-2 phases**.

## Headline

**Phase 33 C honest re-baseline composite: 69.33 / 100 (rubric v2.0)**

**Comparison with prior v1.0 trajectory: NOT VALID** (rubric v2.0 is
a different measurement system; per anti-gaming guard C:-1, v1.0
and v2.0 scores cannot be compared). The v1.0 Phase 32 score of
89.68 remains a true measurement of v1.0's 3 dimensions.

The 69.33 lands at the upper edge of the blueprint's projected
band **~64-68**. Slightly above projection because:
- Dim 3 (Industrial UI) sub-agent rewarded the reference docs being
  shipped during the audit (90-anchor pre-req bullet)
- Dim 4 (AI workflow) synthesis credited the strong infrastructure
  (4-Q-gate, StubAdvisor) above the 60-anchor floor

## Per-dimension scoreboard

| Dim | Name | Score | Anchor matched | Auditor |
|---|---|---|---|---|
| 1 | FEA simulation capability | **78** | 80 fully + 5/6 of 90 sub-bullets; blocked at cohort 11 vs ≥12 | `functional_tester` sub-agent |
| 2 | Novice user experience | **58** | 70 fully + 75% of 80; ballistic-vocab leak; 5 missing recovery paths; 1/4 completion | `novice_simulator` sub-agent |
| 3 | Industrial UI parity | **74** | 70 fully + 80 partial + 90 ref-docs sub-bullet; mean parity 3.1/10 across 5 surfaces | `industrial_ui_comparator` sub-agent |
| 4 | AI workflow integration | **62** | 60 fully + sub-bullets from higher anchors (4-Q-gate, StubAdvisor); blocked at 70-anchor "2 surfaces" | Main session synthesis |
| 5 | Visualization & tracking | **72** | 80 fully + CSV ✓; iso-surface absent; no playwright E2E | `functional_tester` sub-agent |
| 6 | Trust & reproducibility | **72** | 70 fully + 80 partial; ADR ≥10 ✓; failed-attempt corpus absent; no audit-log/reproduce-CLI | Main session synthesis |
| **Composite** | (mean) | **69.33** | — | — |

## Confidence + agreement

- **Sub-agent confidence per dim**: functional_tester high (Dim 1, 5);
  novice_simulator high (Dim 2); industrial_ui_comparator high (Dim 3,
  with note that anchor-matching ≠ linear parity scaling)
- **Synthesis confidence**: high for Dim 4 (clear inventory) and Dim 6
  (clear inventory)
- **Anti-gaming guard F:-1 honored**: all 3 sub-agents explicitly
  forbidden from reading prior FINAL / retro / blueprint files. Each
  confirmed in their report
- **Anti-gaming guard D:-1 honored**: every dim score has file:line
  evidence in the per-dim audit files

## Disagreement / honest tension worth flagging

**Dim 3 (Industrial UI) at 74**: mean parity is 3.1/10 across 5
surfaces, which in raw linear terms would suggest a 31/100 score.
The 74 emerges from anchor-bullet matching: 70-anchor fully met
(motion vocabulary + theme tokens) + 80-anchor partial (7 motion
surfaces ≥7 ✓) + 90-anchor reference-docs sub-bullet shipped during
the audit.

Honest interpretation: the codebase has **strong infrastructure-side
UI craft** (motion vocabulary, token system) but **weak vendor-parity
on canonical surfaces** (case-tree is flat list not tree; results
plot is sparkline not real widget; BC panel doesn't exist as a
setup surface). The 74 reflects this asymmetry — infrastructure is
above mid-range, surface-level parity is well below.

**Lesson for rubric v2.1+**: consider splitting Dim 3 into 3a
(design system depth) and 3b (vendor-surface parity), since
infrastructure quality and surface-level parity diverge so widely.
Note for future rubric-version event. NOT changing v2.0 mid-phase.

## Phase 32 89.68/v1.0 vs Phase 33 C 69.33/v2.0

Per anti-gaming guard C:-1: **DO NOT compare these scores directly.**
They are different measurement systems. The 20.35-point "drop" is not
regression; it is what happens when a 3-dimension rubric is replaced
with a 6-dimension rubric that includes 3 dimensions (Dim 2 novice
UX as a separate axis vs UX overall, Dim 4 AI workflow as separate,
Dim 6 trust as separate) where the codebase has underdeveloped
coverage.

The v1.0 score of 89.68 remains a true measurement of v1.0's 3 axes
(UX 92.7 / FEA 86.33 / UI 90.0). It is not retroactively wrong.

The v2.0 score of 69.33 is the starting point for the multi-phase
journey to 99+.

## Highest-leverage gaps (sub-agent consensus)

### Cross-dimension findings
1. **Ballistic vocabulary leak** in `CaseComparisonPanel.tsx:227-253`
   surfaces "residual velocity / perforation marker / energy audit"
   even for static-structural cases. Novice simulator flagged this
   triple (P1 + P2 + P5). Affects Dim 2 (-1 to -2) AND Dim 3
   (-0.5 to -1). Phase 33 D / 34 should prioritize.
2. **No real BC setup panel** exists; only read-only text summary.
   Industrial UI comparator scored bc_setup_panel at 0.8/10 (severe
   parity gap). Affects Dim 3 (-2 to -3) AND Dim 4 (a future advisor-
   at-BC-setup-stage has no UI to attach to).
3. **Error-recovery infrastructure mismatch**: `ErrorCard.tsx`
   primitive is excellent but `App.tsx` solver / upload / WS paths
   never use it (console.error / alert / silent). 5 paths flagged.
   Affects Dim 2 (-2 to -3) AND Dim 6 (-1, audit-trail gap).

### Dim-specific Tier-1 gaps
- **Dim 1**: 1 more validated case to reach 12-case 90-anchor floor
  (Phase 33 D delivers this via `*CONTACT PAIR` Hertz)
- **Dim 2**: in-context bubbles on ≥5 surfaces; role-branching
  onboarding (Phase 35 target)
- **Dim 3**: real BC setup panel + tree case panel + real plot widget
  (Phase 36 target)
- **Dim 4**: wire advisor at case-open + setup + solve-monitor stages
  (Phase 34 target)
- **Dim 5**: iso-surface rendering + playwright E2E (Phase 39 target)
- **Dim 6**: failed-attempt corpus + audit-trail log (Phase 40 target)

## Phase 33 D forward look

`*CONTACT PAIR` Hertz case will lift Dim 1: 78 → ~82 (12th validated
case + 6th solver kind = `contact_pair_static`; Richardson coverage
likely 5/12 unless Hertz is non-refinable). Other dims unchanged
(33 D is FEA-only work).

**Phase 33 final projection: ~70-71/100 v2.0** after 33 D ships
(composite Δ +0.6-0.7 from 33 C → 33 E).

## Multi-phase roadmap toward 99+ (refined from blueprint)

| Phase | Focus | Projected Dim impact | Composite Δ |
|---|---|---|---|
| 33 | Foundation + 1 FEA lift | Dim 1 +4 | +0.67 |
| 34 | AI workflow wiring (case-open + setup + solve-monitor) | Dim 4 62 → 82 (+20) | +3.3 |
| 35 | Novice UX (role-branching + in-context bubbles + error recovery) | Dim 2 58 → 82 (+24) | +4.0 |
| 36 | Industrial UI #1 (real BC panel + tree case + real plot) | Dim 3 74 → 86 (+12) | +2.0 |
| 37 | Industrial UI #2 (theme + density + 4-quadrant + drag-resize) | Dim 3 86 → 94 (+8) | +1.3 |
| 38 | FEA cohort 13-15 (coupled-temp + modal-intermediate + dynamic) | Dim 1 82 → 90 (+8) | +1.3 |
| 39 | Viz (iso-surface + playwright E2E + 60fps perf) | Dim 5 72 → 92 (+20) | +3.3 |
| 40 | Trust (failed-attempt corpus + audit-log + reproduce CLI) | Dim 6 72 → 92 (+20) | +3.3 |
| 41-43 | NAFEMS benchmark + FEA cases 16-18 | Dim 1 90 → 99 | +1.5 |
| 44 | Dim 2/3/4 final polish | Dim 2/3/4 → 99 | +5-6 |
| 45 | Dim 5/6 final polish + first 99+ audit cycle | Dim 5/6 → 99 | +2-3 |

**Projected reach of 99+: Phase ~45.** ~12 phases, each adding
3-30 points to 1-2 dimensions. The path is honest, not aggressive;
each phase remains scope-disciplined.

## Hard-constraint compliance

- HF1.7a / 7b / 8: PASS (Phase 33 C only added markdown files)
- v2.3 governance round-cap = 3: not triggered (3 sub-agents R1 only)
- confidence: high stamped on every commit
- 绝对诚实客观: PASS — sub-agents reported what they observed; no
  rubric reshaping mid-phase; honest tension on Dim 3 anchor-matching
  flagged transparently
- Anti-gaming guards:
  - A:-1 (no rubric anchor change): PASS — anchors verbatim from v2.0
  - B:-1 (sub-agents score, main session synthesizes): PASS — 3
    sub-agents independently scored Dim 1/2/3/5; main session
    synthesized Dim 4/6 from clear inventory
  - C:-1 (no v1.0 vs v2.0 comparison): PASS — flagged explicitly
  - D:-1 (file:line evidence): PASS — every dim score has it
  - E:-1 (99 evidence): N/A (no 99 claims this phase)
  - F:-1 (anti-priming): PASS — 3 sub-agents confirmed they did not
    read prior FINAL/retro/blueprint
  - G:-1 (codebase IS not CLAIMS): PASS — sub-agents read code, not
    README

## Trajectory under rubric v2.0

| Phase | Composite v2.0 | Per-phase Δ |
|---|---|---|
| **33 C re-baseline** | **69.33** | baseline (no prior v2.0 score) |
| 33 D projected | ~70 | +0.6-0.8 (cohort 11→12 + contact solver kind) |
| 34 projected | ~73-74 | +3.3 (AI workflow wiring) |
| ... | ... | ... |
| 45 projected | ≥99 | composite 99+ |

The 99+ target is reachable but distant. Phase 33 C establishes
the honest starting point.

Tier 1 / Tier 2 engineering candidate; not signed validation; not
benchmark agreement. 绝对诚实客观 across 17 consecutive Tier-2
phases.
