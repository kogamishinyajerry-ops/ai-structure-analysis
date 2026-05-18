# Phase 37 D · Dim 4 — AI workflow integration (synthesis)

> Scored by main session per anti-gaming guard B:-1 (sub-agents
> score Dim 1/2/3/5 directly; main session synthesizes Dim 4/6
> from clear codebase inventory + file:line evidence per D:-1).

## Inventory delta (codebase as of `f56f6ce` vs Phase 36 `de294c1`)

### Advisor surfaces (verifiable count via grep)

| # | Surface | File:line | Workflow stage |
|---|---|---|---|
| 1 | `AdvisorPanel` (Phase 11 E) | `frontend/src/components/AdvisorPanel.tsx:67` | Review |
| 2 | `CaseOpenAdvisorCard` (Phase 34 B + 35 A + 36 C) | `frontend/src/components/CaseOpenAdvisorCard.tsx:49` | Case-open |
| 3 | **`BCSetupAdvisorCard` (Phase 37 B, NEW)** | `frontend/src/components/BCSetupAdvisorCard.tsx:52` | **BC-setup** |

**Surface count: 2 → 3** (+1, Phase 37 B).
**Workflow stages covered: 2 → 3** (case-open + setup + review).

### Phase 37 changes at the AI-workflow surface

Phase 37 B added the **3rd advisor surface** — the long-pending
Dim 4 80-anchor sub-bullet "advisor at 3 workflow stages
(case-open + setup + review)" is now CLOSED.

BCSetupAdvisorCard envelope matches Phase 34 B + 35 A verbatim:
- Offline-first stub status badge
- Curated BC-orientation copy derived from `caseId` prefix via
  `bcOrientationForCaseKind()` — 13 case-kind branches mapping to
  expected BC conventions (cantilever → fixed end + point load;
  cylinder-pv → internal-pressure + axial constraint;
  hertz-contact → top-face load + bottom fixed + contact-pair;
  etc.)
- 4-Q gate inline with the same static-gate-hint subtitle pattern
- data-gate-kind="static" attribute matches CaseOpenAdvisorCard

Phase 37 A CaseBrowser is NOT an advisor surface (it's a case
picker); does not contribute to Dim 4 count.

Phase 37 C WCAG audit doc + solver-start error path are NOT advisor
surfaces; do not contribute to Dim 4 count.

### Advisor backend infrastructure (unchanged from Phase 34)

- `backend/app/services/reporting/advisor_critique.py` — StubAdvisor
  + LLMAdvisor seam
- HTTP route `backend/app/api/routes/advisor_critique.py`
- 4-Q-gate at AdvisorPanel: DYNAMIC; at CaseOpenAdvisorCard +
  BCSetupAdvisorCard: STATIC (both surfaces use the same gate-hint
  subtitle for visual consistency)

## Anchor matching (Phase 37 state)

| Anchor | Sub-bullet | Status | Δ from Phase 36 |
|---|---|---|---|
| 60 | 1 advisor surface | ✓ | unchanged |
| 70 | 2 surfaces (critique panel + contextual nudge) | ✓ | unchanged |
| 80 | **Advisor at 3 workflow stages** | **✓ FULLY MET** (case-open + BC-setup + review) | **3/3 stages closed by Phase 37 B** |
| 80 | 4-Q-gate audited inline at each | ✓ at all 3 surfaces (AdvisorPanel dynamic; CaseOpenAdvisorCard + BCSetupAdvisorCard static with gate-hint) | strengthened (3 surfaces, 3 explicit gate renders) |
| 90 | 5 workflow stages | ✗ | unchanged |
| 90 | Calibration markers ("confidence: high/med/low") on every output | partial | unchanged |
| 95 | Uncertainty narration + file citations + failed-LLM fallback | partial — StubAdvisor fallback ✓ | unchanged |
| 99 | 6 stages + 3 LLM backends + advisor → action wiring | ✗ | unchanged |

## Score

Phase 36 D Dim 4 score: 73/100.

Phase 37 changes:
- **3rd workflow stage closed** (case-open + BC-setup + review).
  This is the headline Phase 37 lift. The 80-anchor sub-bullet
  "advisor at 3 workflow stages" goes from partial 2/3 to
  FULLY MET. Per Phase 34 D's interpolation, this sub-bullet
  carries ~5 points weight; the partial → full transition
  contributes ~+1.7.
- **4-Q-gate audited inline at each surface** sub-bullet
  strengthens because we now have 3 surfaces with explicit
  gate renders (was 2). All 3 use the consistent static-gate-hint
  pattern (the 2 stub surfaces) or dynamic from backend (the
  review surface). Contribution: ~+0.6.
- **Curated case-kind BC orientation** at the new surface adds
  quality on the 70-anchor "contextual nudge" sub-bullet (now 2
  curated nudges instead of 1). Contribution: ~+0.4.

Total Dim 4 delta: +2.7, rounded to **+3** for the integer score.

**Dim 4 score: 76/100** (Phase 36 D was 73/100).

> Note: I considered +5 (to 78) because the 80-anchor 3-stage
> sub-bullet is the biggest Dim 4 anchor sub-bullet in the rubric.
> The honest cap is +3 because:
> 1. Surface count went 2 → 3 (+1); 80-anchor closure is real
> 2. BUT the 80-anchor "audited inline at each" sub-bullet was
>    already partially counted in Phase 36 D (static gate hint
>    landed in Phase 35 A); incremental contribution at Phase 37 is
>    smaller than first impression
> 3. The 90-anchor (5 stages) and 99-anchor (6 stages + 3 LLM
>    backends) are still ✗; +3 keeps appropriate distance from
>    those higher anchors
> 4. Anti-gaming guard E:-1 spirit ("99 evidence required"): we
>    don't have 90-anchor evidence, so we shouldn't approach 90 yet

Confidence: high. The score honestly reflects the closure of the
80-anchor 3-stage sub-bullet while keeping appropriate distance
from the 90+ anchors that require concrete LLM provider work.

## Phase 38+ priorities for Dim 4

| Priority | Item | Anchor closed | Composite lift |
|---|---|---|---|
| 1 | Solve-monitor advisor surface (4th stage) | 90 (5 stages) | +2 |
| 2 | Pre-run advisor surface (5th stage, full 90-anchor close) | 90 | +2 |
| 3 | Make CaseOpenAdvisorCard 4-Q-gate DYNAMIC (real `four_question_gate` from a lightweight endpoint) | resolves remaining static ambiguity at 2 of 3 surfaces | +1-2 |
| 4 | Add ≥1 concrete LLM provider class (OpenAIAdvisor) | 90 | +2 |
| 5 | Advisor → action wiring (advisor recommendations applied to next solver run) | 99 | +3 |

## File:line evidence summary

| Claim | Evidence |
|---|---|
| 3 advisor surfaces (Phase 37 B added one) | grep `<AdvisorPanel\|<CaseOpenAdvisorCard\|<BCSetupAdvisorCard` returns 3 mount sites: `VisualTabPanel.tsx:185` + `App.tsx:1334` + `App.tsx:1335` (paired with CaseOpenAdvisorCard) |
| BCSetupAdvisorCard 3rd surface | `frontend/src/components/BCSetupAdvisorCard.tsx:52` (`role="region"` + `aria-label="BC-setup AI advisor"`) |
| Curated BC orientation per case kind | `frontend/src/components/BCSetupAdvisorCard.tsx:120-216` — 13 case-kind branches in `bcOrientationForCaseKind` |
| Consistent static-gate-hint pattern | grep `data-gate-kind="static"` returns 2 sites (CaseOpenAdvisorCard + BCSetupAdvisorCard); AdvisorPanel uses backend-validated DYNAMIC gate at `AdvisorPanel.tsx:184-190` |
| Solve-monitor stage absent | grep for "solve monitor advisor" returns 0 matches |
| 1 LLM backend code path (unchanged) | `backend/app/services/reporting/advisor_critique.py` |
| Phase 37 B test pins | `frontend/test/Phase37B_bc_setup_advisor_card.test.tsx` — 28 it() blocks across 6 describe groups |
