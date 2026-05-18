# FM-04a Phase 37 — Industrial UI canonical-surface parity + BC-setup advisor + WCAG audit doc

> Tier 1 / Tier 2 engineering candidate; not signed validation; not
> benchmark agreement. 绝对诚实客观 contract carried verbatim from
> Phase 18-36. **21 consecutive Tier-2 phases**.

## Position in the 99+ journey

Phase 36 closed at composite **75.50/100 v2.0** (+1.67 over Phase 35
D's 73.83), inside the projected band 75-78 at the low end. The
Phase 36 R4 audit surfaced 5 new friction points (WS death silent /
no WCAG audit doc / solver-start [ERROR] unstructured / re-announce
edge case / runner badge contrast) and one Dim 1 element-class
undercount finding (cohort has 5 classes not 4; gap to 6 is 1).

Phase 37 advances on the two flat axes from Phase 36 (Dim 3
Industrial UI + Dim 4 AI workflow) while continuing to close
Novice UX + Trust gaps.

Projected lift: **Phase 37 composite 77-80 / v2.0** (+1.5-4.5).

## Slice plan

| Slice | What lands | Projected dim impact |
|---|---|---|
| 37 blueprint | This document | — |
| **37 A** | **Industrial UI canonical-surface parity round 1**: redesign the case picker + Cmd-K palette toward Hyperworks-style case browser parity (tree-style grouping by solver_kind; filter chip row; preview pane). This is the smallest-scope canonical-surface lift — 1 of 5 surfaces, moves the 5-canonical-surface mean from 3.76/10 → ~5/10 if successful. Reuses the runner_available badge from Phase 36 C. | Dim 3 +3-5 |
| **37 B** | **BC-setup advisor surface** — 3rd AI advisor surface at the BC-setup stage. Adds a new lightweight `BCSetupAdvisorCard` component that surfaces when a case has a BC-setup mismatch or when a novice opens a case with no BCs assigned yet. Mounted in App.tsx near the case-setup panel. 4-Q gate inline (same SSOT pattern as case-open). Closes Dim 4 anchor-80 sub-bullet "advisor at 3 workflow stages". | Dim 4 +3-5 |
| **37 C** | Project-wide WCAG audit doc + close solver-start [ERROR] silent path. New `.planning/wcag_audit.md` cataloguing the WCAG status of every user-facing surface (alerts, badges, buttons, focus rings, contrast pairs). Close Phase 36 R4 friction point (c) by surfacing a structured ErrorCard alongside the solver-start [ERROR] log line via the existing `useUploadErrorRecovery` hook + new `solverStartRecoveryOptions()` template. | Dim 2 +1-2 / Dim 6 +0.5 |
| **37 D** | 3 sub-agents R5 + FINAL composite + retro + STATE refresh + commit. | — |

**Total projected composite lift: +1.5-3.5 (75.50 → ~77-79)**

## Phase 37 anti-gaming guards

All Phase 33-36 guards (A-P) carry verbatim. Phase 37-specific:

- **Q:-1** (NEW): Phase 37 A canonical-surface redesign must NOT
  break the existing `availableCases` data contract. Backend
  `/api/v1/candidate-cases` route stays as-is; only the React
  picker surface changes. New test pin asserts the picker still
  renders all 12 cohort cases when the data is unchanged.
- **R:-1** (NEW): Phase 37 B `BCSetupAdvisorCard` follows the
  Phase 34 B + 35 A pattern verbatim — offline-first stub,
  curated copy from caseId pattern, 4-Q gate visible (static
  with the same gate-hint subtitle for visual consistency).
  No new LLM call; no fetch; mount conditionally only when a
  case is open AND the BC state is unset.
- **S:-1** (NEW): Phase 37 C WCAG audit doc must enumerate each
  user-facing surface explicitly (≥10 surfaces) with WCAG criteria
  status (1.3.1 / 1.4.3 / 2.1.1 / 2.4.6 / 3.3.1 / 4.1.2 at
  minimum). No vibe "we audited the UI"; the doc must be reviewable
  surface-by-surface.

## Slice 37 A details

**Problem** (Phase 36 D industrial_ui_comparator R4 + carryover):
The 5 canonical-surface mean parity stays at 3.76/10 because Phase
34-36 lifts landed on non-canonical surfaces (advisor card, error
pattern). The case picker is the easiest canonical-surface win —
Hyperworks's case browser pattern is well-documented (tree-style
grouping by solver kind / filter chip row / preview pane on the
right).

**Fix scope**:
- New `frontend/src/components/CaseBrowser.tsx` (target ~250 LOC)
  with: (a) tree-style grouping by `solver_kind` (or `claimTier`
  when `runner_available === false`); (b) filter chip row
  (`solver_kind` chips + `tier_2_validated` filter chip + 1 search
  input); (c) preview pane showing the selected case's
  displayLabel + claimTier + 4-Q-gate + runner_available badge.
- Mounted in App.tsx as the new case picker; OLD Cmd-K palette
  remains as a quick-jump fallback.
- 12 new tests pin tree grouping by solver_kind, filter chip
  toggling, search filtering, preview pane mount on selection,
  fallback to OLD palette unchanged.

## Slice 37 B details

**Problem** (Phase 35 D + 36 D Dim 4 audits):
The 80-anchor "advisor at 3 workflow stages" sub-bullet is held at
partial 2/3 because the BC-setup stage has no advisor surface. The
solve-monitor stage is the natural next move after BC-setup.

**Fix scope**:
- New `frontend/src/components/BCSetupAdvisorCard.tsx` (target
  ~180 LOC, same envelope as Phase 34 B CaseOpenAdvisorCard).
  composeBrief() infers BC orientation from caseId prefix (e.g.
  cantilever → "expects a tip load + fixed-end constraint";
  cylinder-pv → "expects an internal-pressure BC"; hertz-contact →
  "expects a top-face compression load + bottom-face fixed BC";
  etc.).
- Mounted in App.tsx conditionally when (`activeCaseId && !bcState`)
  — only surfaces when novice hasn't set BCs yet.
- 4-Q gate inline with the same static-gate-hint subtitle pattern
  from Phase 35 A (semantic consistency across advisor surfaces).
- 10 new tests pin: mount + status badge + curated BC orientation
  per case-kind fixture × 5 + 4-Q gate render + gate-hint subtitle.

## Slice 37 C details

**Problem** (Phase 36 D novice_simulator R4 friction points b + c):
- No committed project-wide `wcag_audit.md`
- Solver-start `[ERROR]` log is text-only (no structured ErrorCard)

**Fix scope**:
- Create `.planning/wcag_audit.md` (target ~150 LOC) cataloguing
  ≥10 user-facing surfaces: App-root, OperatorStatusPanel,
  ErrorCard, CaseOpenAdvisorCard, runner_available badge,
  TabButtons, AdvisorPanel, CaseBrowser (new Phase 37 A),
  BCSetupAdvisorCard (new Phase 37 B), TrustCenterPanel. Each with
  status against WCAG criteria 1.3.1 (info-structure), 1.4.3
  (contrast), 2.1.1 (keyboard), 2.4.6 (heading order), 3.3.1
  (error identification), 4.1.2 (name+role+value). PASS / GAP /
  TODO per criterion.
- Close solver-start [ERROR] silent path: in
  `useUploadErrorRecovery.ts` add `solverStartRecoveryOptions(jobId)`
  template; in App.tsx solver-start path wrap the relevant fetch
  in `withUploadRecovery`. App.tsx growth target: ≤6 LOC.
- 4 new tests: 3 option-template (matches the Phase 35 C + 36 A
  pattern) + 1 App.tsx wiring pin.

## Phase 37 projection

| Dim | Phase 36 | Phase 37 projected | Δ | Lift source |
|---|---|---|---|---|
| 1 FEA | 87 | 87 | 0 | Untouched (Phase 38 cohort 13-15 + 6th element class) |
| 2 Novice UX | 72 | 74-75 | +2-3 | Slice 37 A case browser + 37 C close 1 more error path + WCAG audit document |
| 3 Industrial UI | 73 | 76-78 | +3-5 | Slice 37 A canonical-surface (case picker → CaseBrowser) parity lift |
| 4 AI workflow | 73 | 76-78 | +3-5 | Slice 37 B BCSetupAdvisorCard closes 80-anchor 3-stage sub-bullet |
| 5 Visualization | 72 | 72 | 0 | Untouched (Phase 39) |
| 6 Trust | 76 | 76-77 | 0 to +1 | Slice 37 C WCAG audit doc + 1 more provenance touchpoint |
| **Composite** | **75.50** | **~77-79** | **+1.5-3.5** | Dim 3 + Dim 4 lifts as the headline |

## Hard constraints

All Phase 18-36 hard constraints carry verbatim:
- HF1.7a/b/8 signed-registry hard-stop + *-candidate carve-out
- tmp_path-only test writes
- v2.3 round-cap = 3
- confidence: <h|m|l> tag on every commit
- 绝对诚实客观 contract
- prefers-reduced-motion honored
- Anti-gaming guards A-P + new Q/R/S for this phase
- Phase 1-N additive only (no test threshold edits; App.tsx <1500)
- Rubric v2.0 99-anchor reachable via verifiable evidence
- NEVER re-score prior phases retroactively
- NEVER apply weights/transforms to composite
- No push / no PR / no Linear / no Notion writes

## Closing

Phase 37 advances on the two flat axes from Phase 36 (Dim 3 + Dim 4)
while continuing concrete Novice UX + Trust work. The CaseBrowser
canonical-surface lift is the headline; the BCSetupAdvisorCard
closes the 80-anchor 3-stage sub-bullet that has been open since
Phase 33; the WCAG audit doc + 5th error-recovery closure are
small-scope but valuable.

This is the 21st consecutive Tier-2 phase. Trajectory remains on
track for 99+ by Phase ~45.

Tier 1 / Tier 2 engineering candidate; not signed validation;
not benchmark agreement. 绝对诚实客观 across 21 consecutive
Tier-2 phases.
