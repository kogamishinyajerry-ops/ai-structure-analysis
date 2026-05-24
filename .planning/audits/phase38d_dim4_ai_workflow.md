# Phase 38 D — Dim 4 (AI workflow integration) · main-session synthesis

> Tier 1 / Tier 2 engineering candidate; not signed validation; not benchmark
> agreement. 绝对诚实客观. Rubric v2.0 Dim 4. No dedicated sub-agent exists for
> Dim 4 (the fleet covers Dim 1/5 functional, Dim 2 novice, Dim 3 industrial);
> the main session synthesizes Dim 4 + Dim 6 — the documented Phase 37 D
> precedent (`phase37d_dim4_ai_workflow.md`).

## Verdict: **Dim 4 = 76 (HELD from Phase 37)**

**Phase 38 made NO code change to the advisor wiring.** `git diff f56f6ce..HEAD`
(Phase 37 C → Phase 38 J) shows the three advisor surfaces are byte-unchanged:
`CaseOpenAdvisorCard.tsx`, `BCSetupAdvisorCard.tsx`, `AdvisorPanel.tsx` are absent
from the diff. Phase 38 D added `BCSetupPillList.tsx` (a **read-only BC pill list**,
NOT an advisor surface) and touched its copy — neither adds nor removes an advisor
stage. Per the no-retroactive-rescore guard, a byte-unchanged dimension retains its
last calibrated value.

## Current-state evidence (for the record — anchor 80 sub-bullets present)
- **3 advisor workflow stages** wired:
  - case-open: `CaseOpenAdvisorCard.tsx` (mounted `App.tsx:1331`)
  - BC-setup: `BCSetupAdvisorCard.tsx` (mounted `App.tsx:1332`, gated by `shouldShowBCSetupAdvisor`)
  - review: `AdvisorPanel.tsx` (critique panel)
- **4-Q gate at each stage**: `FOUR_QUESTION_GATE_KEYS` rendered in all three
  (`CaseOpenAdvisorCard.tsx:40,49`; `BCSetupAdvisorCard.tsx:39,48,51`;
  `AdvisorPanel.tsx:30,180-187` — "Four-question gate" checklist mapping all 4 keys).

## Why HELD at 76, not fresh-read to ≥80
Phase 37 D made a **deliberate interpolation** (Dim 4 73→76: "closes 80-anchor
3-stage sub-bullet; surface count 2→3") — it did NOT place the just-closed 3-stage
milestone at the full 80 floor. On byte-identical advisor code, the main session
does **not** override that calibrated interpolation with a fresh "force to 80"
reading; that would be a retroactive re-score of unchanged code. Value holds at **76**.

## Anchor-90+ gaps (unchanged; Phase 39+ targets)
- **90**: advisor at only 3 stages, not 5 (no mesh-setup / solve-monitor advisor);
  no calibration-marker prose (`confidence: h/m/l`) on advisor **output** (grep:
  absent on all 3 cards).
- **99**: <3 LLM providers gated (`backend/app/core/config.py:15` = OpenAI key only,
  + StubAdvisor fallback = 2 of the {Stub, OpenAI, Anthropic, Gemini, Ollama}
  required ≥3); advisor→action wiring **absent** (grep: no apply-suggestion /
  refine-mesh route back into the pipeline); no `.planning/audits/ai_advisor_coverage.md`.
