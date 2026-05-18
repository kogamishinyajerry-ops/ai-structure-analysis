# Phase 33 C · Dim 4 — AI workflow integration (synthesis)

> Scored by main session (not a dedicated sub-agent) because Dim 4 is
> best measured by structural inventory: presence/absence of advisor
> wiring at named workflow stages, 4-Q-gate audit, LLM backend count.
> Future phases may introduce an `advisor_audit` sub-agent if the
> inventory complexity warrants it.
>
> File:line evidence required per RUBRIC v2.0 D:-1.

## Inventory (codebase as of `c581746`)

### Advisor surfaces (where the user sees / interacts with the advisor)

| # | Surface | File | Mount point | Stage in workflow |
|---|---|---|---|---|
| 1 | `AdvisorPanel.tsx` (370 LOC) | `frontend/src/components/AdvisorPanel.tsx:67` | `frontend/src/components/VisualTabPanel.tsx:185` | **Review** (post-solve, visual tab) |

**Surface count: 1.**

### Advisor backend infrastructure

| Component | File:line | Purpose |
|---|---|---|
| `AdvisorContext` dataclass | `backend/app/services/reporting/advisor_critique.py:130` | Input context for advisor call |
| `AdvisorRawCritique` | `:152` | Pre-shape-audit raw LLM response |
| `AdvisorCritique` (1.0.0) | `:167` | Validated critique schema |
| `AdvisorProvider` Protocol | `:205` | Pluggable advisor backend |
| `StubAdvisor` rule-based | `:220` | Always-available offline fallback |
| `LLMAdvisor` env-var-gated | `:799` | Real-LLM provider (env-var `LLM_PROVIDER`) |
| `AdvisorSnapshotNotFound` | `:1073` | Distinguishes 404 vs 422 |
| HTTP route | `backend/app/api/routes/advisor_critique.py` (140 LOC) | `GET /api/v1/advisor-critique/<case_id>?snapshot=<label>` |

Total advisor module surface: 1724 LOC (1214 + 140 + 370).

### 4-Q-gate audit

`AdvisorCritique` schema and the route handler enforce the 4-question
gate (LLM offline? artifacts? TrustGate? advisory-only?). The
critique payload includes `four_q_gate_audit: dict[str, bool]` fields
that the `AdvisorPanel.tsx` renders as a checklist.

### LLM backend count

- **StubAdvisor**: rule-based, always-available offline. Real.
- **LLMAdvisor**: env-var-gated; injectable `llm_call` callable
  with defensive parse + stub-fallback on every shape-drift branch.
  Code path exists; no provider concrete classes (OpenAI/Anthropic
  /Gemini/Ollama) ship in-tree.

**Concrete LLM backends shipped: 1** (StubAdvisor only counts as
concrete; LLMAdvisor is a generic seam awaiting a provider).

## Anchor matching

### Anchor 60: "1 advisor surface" — ✓ (AdvisorPanel)
### Anchor 70: "2 surfaces" — ✗ (only 1 surface)
### Anchor 80: "advisor at 3 workflow stages + 4-Q-gate at each" — ✗
- Stages met: **1** (review). Required: 3 (case-open + setup + review).
- 4-Q-gate ✓ (the single stage has it).
- Net: 1/3 stages × bonus + 4-Q-gate sub-bullet met = partial.

### Anchor 90: "5 stages + 4-Q-gate inline + calibration markers"
- 1 stage / 5 → 20% of stages bullet
- 4-Q-gate ✓ (at the 1 stage)
- Calibration markers ("confidence: high/med/low" on advisor
  output): partial — the `AdvisorCritique` schema has a
  `confidence` field but the panel rendering's coverage isn't
  100%

### Anchor 95: "uncertainty + file citations + failed-LLM fallback proven"
- Failed-LLM fallback ✓ (StubAdvisor + defensive parse)
- Uncertainty narration in advisor output: partial
- File citations: not implemented

### Anchor 99: "6 stages + 3 LLM backends + advisor→action wiring"
- Stages: 1/6 ≈ 17%
- LLM backends: 1/3 ≈ 33%
- Advisor→action wiring: 0 (read-only critique)

## Score

Anchor 60 fully met. Anchor 70 not met (1 surface only).
Sub-bullets from anchors 80/90/95 partially scattered (4-Q-gate at
the 1 stage, StubAdvisor fallback). Honest interpolation:

- 60 (anchor floor) + ~2 points credit for the strong backend
  infrastructure (4-Q-gate, StubAdvisor, schema rigor) that's
  above the 60-anchor bar but doesn't reach 70-anchor's "2 surfaces"
  hard requirement.

**Dim 4 score: 62/100**

Confidence: high. The score reflects that the *infrastructure* for
AI workflow is mature (1700+ LOC, schema rigor, 4-Q-gate, fallback),
but the *wiring into actual workflow stages* is limited to a single
review-time panel. Phase 34 is targeted at lifting this to 80+ via
case-open + mesh-setup + BC-setup + solve-monitor stages.

## File:line evidence summary

| Claim | Evidence |
|---|---|
| 1 advisor surface | `frontend/src/components/VisualTabPanel.tsx:185` (sole AdvisorPanel mount) |
| AdvisorPanel exists | `frontend/src/components/AdvisorPanel.tsx:67` |
| StubAdvisor offline-capable | `backend/app/services/reporting/advisor_critique.py:220` |
| LLMAdvisor env-var-gated | `backend/app/services/reporting/advisor_critique.py:799` |
| 4-Q-gate in payload | `backend/app/services/reporting/advisor_critique.py:167` (AdvisorCritique dataclass) |
| Route handler | `backend/app/api/routes/advisor_critique.py:1-140` |
| Calibration field exists | `AdvisorCritique.confidence` (see schema) |
| No advisor → action wiring | absence: no `AdvisorAction` / `apply_advisor_recommendation` module exists |

## Phase 34+ priorities derived from this score

1. Wire advisor at case-open stage (`App.tsx` first-load) — +1 stage
2. Wire advisor at mesh-setup stage (when mesh refinement is offered)
3. Wire advisor at BC-setup stage (sanity check)
4. Wire advisor at solve-monitor stage (narrate ccx progress)
5. Add at least 2 concrete LLM provider classes (e.g., `OpenAIAdvisor`,
   `AnthropicAdvisor`, `OllamaAdvisor`)
6. Add advisor→action seam: e.g., "refine mesh at region X" suggestion
   routes back to a button on the workbench
