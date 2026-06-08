# Phase 36 D · Dim 4 — AI workflow integration (synthesis)

> Scored by main session per anti-gaming guard B:-1 (sub-agents
> score Dim 1/2/3/5 directly; main session synthesizes Dim 4/6
> from clear codebase inventory + file:line evidence per D:-1).

## Inventory delta (codebase as of `4188dc5` vs Phase 35 `5d8f368`)

### Advisor surfaces (verifiable count via grep)

Unchanged from Phase 35:

| # | Surface | File | Workflow stage |
|---|---|---|---|
| 1 | `AdvisorPanel` (Phase 11 E) | `frontend/src/components/AdvisorPanel.tsx` | Review |
| 2 | `CaseOpenAdvisorCard` (Phase 34 B + 35 A + 36 C) | `frontend/src/components/CaseOpenAdvisorCard.tsx` | Case-open |

**Surface count: 2** (unchanged).
**Workflow stages covered: 2** (case-open + review, unchanged).

### What Phase 36 changed at the AI-workflow surface

Phase 36 C added a small additive feature at the case-open
advisor: a `runner_available` badge that surfaces when a candidate
case has no live ccx runner (demo-only). This is a content refinement
at an existing surface, NOT a new surface or stage.

Phase 36 A + B did not touch any advisor surface; their work was
on the orthogonal ErrorCard surface (which is NOT classified as an
advisor surface — it surfaces failure modes, not advisory critique).

### Advisor backend infrastructure (unchanged from Phase 34)

- `backend/app/services/reporting/advisor_critique.py` — StubAdvisor + LLMAdvisor seam
- HTTP route `backend/app/api/routes/advisor_critique.py`
- 4-Q-gate at AdvisorPanel: DYNAMIC; at CaseOpenAdvisorCard: STATIC (Phase 35 A made this explicit via subtitle + data-gate-kind)

## Anchor matching (Phase 36 state)

| Anchor | Sub-bullet | Status | Δ from Phase 35 |
|---|---|---|---|
| 60 | 1 advisor surface | ✓ | unchanged |
| 70 | 2 surfaces (critique panel + contextual nudge) | ✓ | unchanged |
| 80 | Advisor at 3 workflow stages | partial — 2/3 stages | unchanged |
| 80 | 4-Q-gate audited inline at each | partial → mostly resolved (Phase 35 A subtitle + data-gate-kind tag) | unchanged from Phase 35 |
| 90 | 5 workflow stages | ✗ | unchanged |
| 90 | Calibration markers ("confidence: high/med/low") on every output | partial | unchanged |
| 95 | Uncertainty narration + file citations + failed-LLM fallback | partial — StubAdvisor fallback ✓ | unchanged |
| 99 | 6 stages + 3 LLM backends + advisor → action wiring | ✗ | unchanged |

## Score

Phase 35 D Dim 4 score: 73/100.

Phase 36 changes: none that move Dim 4 anchor matching. The
runner_available badge is a small additive UX refinement on the
existing case-open advisor surface — too narrow to count as a
separate sub-bullet.

**Dim 4 score: 73/100** (unchanged from Phase 35).

Confidence: high. The score honestly reflects that Phase 36 was
explicitly scoped for Dim 2 + Dim 6, not Dim 4.

## Phase 37+ priorities (carried verbatim from Phase 35)

| Priority | Item | Anchor closed | Composite lift |
|---|---|---|---|
| 1 | Wire advisor at BC-setup stage | 80 (3 stages) | +2-3 |
| 2 | Make CaseOpenAdvisorCard 4-Q-gate DYNAMIC | resolves remaining static ambiguity | +1-2 |
| 3 | Wire advisor at solve-monitor stage | 90 (5 stages) | +2 |
| 4 | Add ≥1 concrete LLM provider class | 90 | +2 |

## File:line evidence summary

| Claim | Evidence |
|---|---|
| 2 advisor surfaces (unchanged) | grep `<AdvisorPanel\|<CaseOpenAdvisorCard` returns exactly 2 mount sites |
| runner_available badge added (Phase 36 C refinement) | `frontend/src/components/CaseOpenAdvisorCard.tsx:61-69` — `case-open-advisor-runner-badge` test-id; renders only when `caseRecord.runnerAvailable === false` |
| Setup / solve-monitor stages still absent | grep for "setup advisor" / "solve monitor advisor" returns 0 matches |
| 1 LLM backend code path (unchanged) | `backend/app/services/reporting/advisor_critique.py` |
