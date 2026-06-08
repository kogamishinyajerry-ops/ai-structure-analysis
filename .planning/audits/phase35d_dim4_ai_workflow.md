# Phase 35 D · Dim 4 — AI workflow integration (synthesis)

> Scored by main session per anti-gaming guard B:-1 (sub-agents score
> Dim 1/2/3/5 directly; main session synthesizes Dim 4/6 from
> codebase inventory + file:line evidence per D:-1).

## Inventory delta (codebase as of `31856d1` vs Phase 34 `b78172a`)

### Advisor surfaces (verifiable count via grep)

| # | Surface | File:line | Mount point | Workflow stage |
|---|---|---|---|---|
| 1 | `AdvisorPanel` (Phase 11 E) | `frontend/src/components/AdvisorPanel.tsx:67` | `frontend/src/components/VisualTabPanel.tsx:185` | **Review** (post-solve, visual tab) |
| 2 | `CaseOpenAdvisorCard` (Phase 34 B + 35 A) | `frontend/src/components/CaseOpenAdvisorCard.tsx:49` | `frontend/src/App.tsx:1361-1368` | **Case-open** (immediately after candidate case selection) |

**Surface count: 2** (unchanged from Phase 34).
**Workflow stages covered: 2** (case-open + review, unchanged).

### What Phase 35 changed at the AI-workflow surface

Phase 35 A refines the case-open surface in two ways that affect
Dim 4 anchor matching:

1. **Brief content is now curated, not raw notesExcerpt passthrough**
   (`CaseOpenAdvisorCard.tsx:121-216` — `composeBrief` +
   `orientationForCaseKind`). The brief reads as engineering
   orientation copy keyed on `caseId` prefix, not internal phase
   vocabulary. This raises the quality of the "contextual nudge"
   sub-bullet that the 70-anchor recognises.

2. **4-Q gate at the case-open surface is now SEMANTICALLY
   DISTINGUISHED** from the AdvisorPanel's dynamic gate
   (`CaseOpenAdvisorCard.tsx:68-82`):
   - Italic subtitle `client-side stub status; the Visual tab
     renders a backend-validated gate` (test-id
     `case-open-advisor-gate-hint`)
   - Gate container tagged with `data-gate-kind="static"`
   - Muted-color ticks (vs the accent-color dynamic ticks at the
     AdvisorPanel)

This **partially resolves** the Phase 34 D honest tension that
flagged static-vs-dynamic ambiguity as a -1 cost on the 80-anchor
sub-bullet "4-Q-gate audited inline at each". Phase 35 A does not
make the gate dynamic — that would require a backend route — but
it makes the static status a deliberate, declared state instead of
an undocumented quirk. Honest cost reduced from ~ -1 to ~ -0.

### Advisor backend infrastructure (unchanged from Phase 34)

`backend/app/services/reporting/advisor_critique.py`:
- `AdvisorContext` / `AdvisorRawCritique` / `AdvisorCritique` (schema 1.0.0)
- `AdvisorProvider` Protocol
- `StubAdvisor` rule-based offline fallback
- `LLMAdvisor` env-var-gated (1 LLM-backend code path; no concrete
  providers shipping in-tree)

## Anchor matching (Phase 35 state)

| Anchor | Sub-bullet | Status | Δ from Phase 34 |
|---|---|---|---|
| 60 | 1 advisor surface | ✓ | unchanged |
| 70 | 2 surfaces (critique panel + contextual nudge) | ✓ | nudge content quality lifted (curated copy vs raw passthrough) |
| 80 | Advisor at 3 workflow stages | partial — 2/3 stages | unchanged (no setup-stage surface) |
| 80 | 4-Q-gate audited inline at each | partial → **more partial**: gate hint subtitle + data-gate-kind tag declares the static status; AdvisorPanel dynamic gate unchanged | resolves Phase 34 #28 tension |
| 90 | 5 workflow stages | ✗ | unchanged |
| 90 | Calibration markers ("confidence: high/med/low") on every output | partial | unchanged |
| 95 | Uncertainty narration + file citations + failed-LLM fallback proven | partial — StubAdvisor fallback ✓ | unchanged |
| 99 | 6 stages + 3 LLM backends + advisor → action wiring | ✗ | unchanged |

## Score

Phase 34 D Dim 4 interpolation: 60 + 10 + 5.8 + 0.7 = 76.5, rounded
to 72/100 after applying honest -1 cost for static-gate tension.

Phase 35 changes:
- The honest -1 cost on the 80-anchor 4-Q-gate sub-bullet is now
  reduced to ~ -0 because the static status is declared explicitly
  with a subtitle + data attribute (the reviewer no longer has to
  infer it). Lift: ~+1.
- The 70-anchor "contextual nudge" sub-bullet gains quality lift
  from curated copy (vs raw passthrough). Lift: ~+0.3 (small, since
  the surface count is unchanged).

Total Dim 4 delta: +1.3, rounded to **+1** for the integer score.

**Dim 4 score: 73/100** (Phase 34 D was 72/100).

Confidence: high. The score honestly reflects that Phase 35 did
NOT add a new advisor surface or workflow stage — the lift is
quality refinement at the existing surfaces. Phase 36+ priorities
for Dim 4 are the same as Phase 35 (BC-setup advisor surface,
dynamic gate at case-open, solve-monitor surface, ≥1 concrete LLM
provider class).

## Phase 36+ priorities derived from this score

| Priority | Item | Anchor closed | Composite lift |
|---|---|---|---|
| 1 | Wire advisor at BC-setup stage | 80 (3 stages) | +2-3 |
| 2 | Make CaseOpenAdvisorCard 4-Q-gate DYNAMIC (read real `four_question_gate` from a lightweight `/api/v1/case-open-brief/<case_id>` endpoint OR derive from `case_completeness` data already shipped) | resolves remaining static-gate ambiguity | +1-2 |
| 3 | Wire advisor at solve-monitor stage | 90 (5 stages) | +2 |
| 4 | Add ≥1 concrete LLM provider class (OpenAIAdvisor or similar) | 90 | +2 |

## File:line evidence summary

| Claim | Evidence |
|---|---|
| 2 advisor surfaces (unchanged) | grep `<AdvisorPanel\|<CaseOpenAdvisorCard` returns exactly 2 mount sites: `VisualTabPanel.tsx:185` + `App.tsx:1361-1368` |
| Curated case-kind orientation copy | `frontend/src/components/CaseOpenAdvisorCard.tsx:121-216` (composeBrief + orientationForCaseKind) — 13 case-kind prefixes mapped to engineering copy |
| 4-Q gate hint subtitle | `frontend/src/components/CaseOpenAdvisorCard.tsx:68-74` — `data-testid="case-open-advisor-gate-hint"` with copy "client-side stub status; the Visual tab renders a backend-validated gate" |
| 4-Q gate data attribute | `frontend/src/components/CaseOpenAdvisorCard.tsx:78` — `data-gate-kind="static"` |
| AdvisorPanel dynamic gate (unchanged) | `frontend/src/components/AdvisorPanel.tsx:184-190` — gate state from `critique.fourQuestionGate[key]` |
| Phase 35 A test pins (jargon absence + curated copy + static-gate hint) | `frontend/test/Phase34B_case_open_advisor_card.test.tsx:81-167` |
| Setup / solve-monitor stages still absent | grep for "setup advisor" / "solve monitor advisor" returns 0 matches |
| 1 LLM backend code path (unchanged) | `backend/app/services/reporting/advisor_critique.py` (LLMAdvisor env-var-gated; no concrete provider) |
