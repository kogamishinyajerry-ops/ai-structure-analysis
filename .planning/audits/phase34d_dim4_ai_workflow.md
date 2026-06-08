# Phase 34 D · Dim 4 — AI workflow integration (synthesis)

> Scored by main session per anti-gaming guard B:-1 (sub-agents score
> Dim 1/2/3/5 directly; main session synthesizes Dim 4/6 from clear
> codebase inventory + file:line evidence per D:-1). Future phases
> may introduce a dedicated `advisor_audit` sub-agent if inventory
> complexity warrants.

## Inventory (codebase as of `b78172a`)

### Advisor surfaces (verifiable count via grep)

| # | Surface | File:line | Mount point | Workflow stage |
|---|---|---|---|---|
| 1 | `AdvisorPanel` (Phase 11 E, 370 LOC) | `frontend/src/components/AdvisorPanel.tsx:67` | `frontend/src/components/VisualTabPanel.tsx:185` | **Review** (post-solve, visual tab) |
| 2 | `CaseOpenAdvisorCard` (Phase 34 B, 180 LOC) | `frontend/src/components/CaseOpenAdvisorCard.tsx:48` | `frontend/src/App.tsx:1318-1324` | **Case-open** (immediately after candidate case selection; visible regardless of which tab the user lands on) |

**Surface count: 2** (was 1 in Phase 33).
**Workflow stages covered: 2** (case-open + review).

### Advisor backend infrastructure (unchanged from Phase 33)

`backend/app/services/reporting/advisor_critique.py` (1214 LOC):
- `AdvisorContext` / `AdvisorRawCritique` / `AdvisorCritique` (schema 1.0.0)
- `AdvisorProvider` Protocol
- `StubAdvisor` rule-based offline fallback
- `LLMAdvisor` env-var-gated (1 LLM-backend code path)

HTTP route: `backend/app/api/routes/advisor_critique.py` (140 LOC):
- `GET /api/v1/advisor-critique/<case_id>?snapshot=<label>`
- 6-step gate composition (422/422/422/404/422/200)

### 4-Q-gate at each surface

| Surface | 4-Q-gate rendering | Source |
|---|---|---|
| AdvisorPanel | **DYNAMIC** — gate state from `critique.fourQuestionGate[key]` | `AdvisorPanel.tsx:184-190` |
| CaseOpenAdvisorCard | **STATIC** — all 4 ticks render unconditionally | `CaseOpenAdvisorCard.tsx:67-80` |

Both surfaces visibly enumerate the 4 SSOT keys from
`FOUR_QUESTION_GATE_KEYS` (`advisorCritiqueClient.ts:24`).
**4-Q-gate vocabulary present at BOTH surfaces** — anchor 80
sub-bullet partially satisfied.

**Honest semantic tension** (Phase 34 D novice_simulator finding #2):
the static-✓ rendering in CaseOpenAdvisorCard could mislead a
reviewer who is used to AdvisorPanel's dynamic rendering. This is
a known sub-bullet cost; counted as honest -1 in the score
interpolation below.

### LLM backend count (unchanged from Phase 33)

- StubAdvisor: concrete rule-based, always-available offline. **Real.**
- LLMAdvisor: env-var-gated; injectable `llm_call` callable; no
  concrete provider classes (OpenAI / Anthropic / Gemini / Ollama)
  shipping in-tree.

**Concrete LLM backends shipped: 1** (StubAdvisor only; LLMAdvisor
is a generic seam awaiting providers).

## Anchor matching

| Anchor | Sub-bullet | Status |
|---|---|---|
| 60 | 1 advisor surface | ✓ |
| 70 | 2 surfaces (critique panel + 1 contextual nudge) | ✓ (Phase 34 B closes this gap) |
| 80 | Advisor at 3 workflow stages (case-open + setup + review) | partial — 2/3 stages (case-open ✓ + review ✓; setup ✗) |
| 80 | 4-Q-gate audited inline at each | partial — present at both but static-vs-dynamic semantic tension |
| 90 | 5 workflow stages | ✗ |
| 90 | Calibration markers ("confidence: high/med/low") on every output | partial — `AdvisorCritique.confidence` exists; `CaseOpenAdvisorCard` doesn't render confidence |
| 95 | Uncertainty narration + file citations + failed-LLM fallback proven | partial — StubAdvisor fallback ✓; uncertainty + citation ✗ |
| 99 | 6 stages + 3 LLM backends + advisor → action wiring | ✗ |

## Score

Interpolation:
- 60-anchor fully met → 60 base
- 70-anchor fully met (2 surfaces, both with critique-style content) → +10 → 70
- 80-anchor partial:
  - 2 of 3 workflow stages → +67% × 5 weighting = +3.3
  - 4-Q-gate inline at both surfaces, with honest semantic tension noted → +50% × 5 weighting = +2.5
  - Net 80-anchor contribution: ~+5.8
- Higher anchors: a small partial credit for StubAdvisor fallback (95-anchor sub-bullet) — say +0.7

Total: 60 + 10 + 5.8 + 0.7 = **76.5**

Rounding to integer score with the honest static-gate-vs-dynamic-
gate tension applied (-1): **Dim 4 score: 72/100**

Confidence: high. The score reflects:
- Real lift from 1 surface → 2 surfaces (anchor 70 closed)
- Real lift from 4-Q-gate vocabulary appearing at both surfaces
- Real partial-credit for 2-of-3 workflow stages (anchor 80 sub-bullet)
- Real cost from static-vs-dynamic 4-Q-gate semantic ambiguity
- Real continuation cost: setup stage still missing, only 1 concrete
  LLM backend, no advisor → action wiring

## Phase 35+ priorities derived from this score

| Priority | Item | Anchor closed | Composite lift |
|---|---|---|---|
| 1 | Wire advisor at BC-setup stage | 80 (3 stages) | +2-3 |
| 2 | Make CaseOpenAdvisorCard 4-Q-gate DYNAMIC (read real `four_question_gate` from a lightweight `/api/v1/case-open-brief/<case_id>` endpoint OR derive from `case_completeness` data already shipped) | resolves honest tension | +1-2 |
| 3 | Wire advisor at solve-monitor stage | 90 (5 stages) | +2 |
| 4 | Add ≥1 concrete LLM provider class (OpenAIAdvisor or similar) | 90 | +2 |

## File:line evidence summary

| Claim | Evidence |
|---|---|
| 2 advisor surfaces | grep `<AdvisorPanel\|<CaseOpenAdvisorCard` returns exactly 2 mount sites: `VisualTabPanel.tsx:185` + `App.tsx:1318-1324` |
| CaseOpenAdvisorCard exists | `frontend/src/components/CaseOpenAdvisorCard.tsx:48` |
| 4-Q-gate static at case-open | `CaseOpenAdvisorCard.tsx:67-80` — 4 hardcoded `✓` icons across `FOUR_QUESTION_GATE_KEYS.map(...)` |
| 4-Q-gate dynamic at AdvisorPanel | `AdvisorPanel.tsx:184-190` — gate state from `critique.fourQuestionGate[key]` |
| Setup stage absent | grep for "setup advisor" / "bc setup advisor" returns 0 matches |
| Solve-monitor stage absent | grep for "solve advisor" / "solve monitor advisor" returns 0 matches |
| StubAdvisor fallback | `backend/app/services/reporting/advisor_critique.py:220` |
| 1 LLM backend code path | `backend/app/services/reporting/advisor_critique.py:799` (LLMAdvisor env-var-gated; no concrete provider) |
| Advisor→action wiring absent | grep for `applyAdvisorRecommendation` / `AdvisorAction` returns 0 matches |
