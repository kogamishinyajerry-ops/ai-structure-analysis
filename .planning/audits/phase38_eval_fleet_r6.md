# FM-04a Phase 38 — Eval fleet R6 (ADR-026 evaluation layer)

> Tier 1 / Tier 2 engineering candidate; not signed validation; not benchmark
> agreement. 绝对诚实客观.

**Run context (methodology caveat — READ FIRST):** the 3 evaluation sub-agents
(`functional-tester` / `novice-simulator` / `industrial-ui-comparator`) are
defined in `.claude/agents/` but are **NOT registered as invokable
`subagent_type`s in this Claude Code session** (they need a session restart to
load). This R6 was therefore run via **`general-purpose` proxies with embedded
protocol briefings** — the established workaround, but NOT identical to the
calibrated custom agents. The novice + industrial prompts used harsh absolute
framing ("compare to HyperWorks/Abaqus/ANSYS", severity-deduction formula),
which likely scored **harsher than the project's calibrated rubric scale**.
Anti-gaming guards B/D/F/G:-1 were enforced in the prompts (subagents scored,
file:line evidence, no prior-audit access, test-what-IS).

## Scores (this run) vs Phase 37 baseline

| Dim | Phase 37 | R6 (this run) | Δ | Note |
|---|---|---|---|---|
| 1 FEA | 87 | 82–86 | ≈flat | functional-tester; FEA capability strong, surfacing gap penalized |
| 2 Novice UX | 77 | **58** | −19 | novice-simulator; severity-deduction formula + real 38D friction |
| 3 Industrial UI | 76 | **45** | −31 | industrial-ui-comparator; commercial-CAE-parity bar (harsh) |
| 4 AI workflow | 76 | (not scored) | — | no dedicated sub-agent |
| 5 Visualization | 72 | 62–68 | −5 to −10 | functional-tester; render_all HTTP-unreachable |
| 6 Trust | 77 | (not scored) | — | no dedicated sub-agent |

**The Dim 2/3 crash is mostly scale mismatch, not proven prior inflation:**
Dim 1/5 (functional-tester, scenario-based) track the baseline within noise,
while Dim 2/3 (harsh absolute formulas) diverge hugely. Composite NOT finalized
from this run pending a calibrated re-score (see recommendation).

## Real findings (valid regardless of calibration — act on these)

### NEW friction introduced by Phase 38 (my changes)
- **38D BCSetupPillList dead-end** (novice F2, HIGH): `BCSetupPillList.tsx:82-87`
  shows "Boundary conditions this case kind expects — not yet assigned" with NO
  affordance to assign them, and no BC editor exists. `BCSetupAdvisorCard.tsx:113`
  says "set the BCs before running" → instruction with nowhere to go. My 38D
  "concrete affordance" created a UX dead-end for novices.
- **38D advisor row no hierarchy** (novice F3, MED): `App.tsx:1333-1337` mounts 3
  glass cards in a flat `flexDirection:'row'` wrap with no heading/sequence — the
  novice can't tell which is the entry point.

### Pre-existing issues the fleet surfaced (NOT Phase 38 regressions)
- **Tier-2 promotion invisible at the API boundary** (functional, HIGH):
  `candidate_cases.py:39` + `cohort_overview.py:36` hard-code "Tier 1 engineering
  candidate" and never import `_claim_tier.get_claim_tier`. Every tier_2_validated
  case (incl. the new wedge-c3d6) surfaces as Tier 1 to the API/frontend. The
  promotion system works in isolation but is a dead letter to users.
- **18 of 24 cohort cases absent from frontend `FALLBACK_CANDIDATE_CASES`**
  (functional, HIGH): `candidateCaseRegistry.ts` has 6-7 hardcoded entries; the
  modal/buckling/dynamic/heat-transfer/shell/wedge/nafems cases are invisible in
  the picker unless the live API is reachable. (Same root as Codex 38A R1-P2.)
- **`render_all` (viz) is HTTP-unreachable** (functional, MED): `render.py:313`
  PNG render pipeline is CLI-only (`cli.py:840`); no REST route. Dim 5 drag.
- **CaseBrowser amber runner-badge contrast ≈3.3:1** (novice F5): `CaseBrowser.tsx:494`
  text-secondary on faint amber FAILS AA — this is exactly the pair Phase 38 C
  honestly left as a remaining GAP. The fleet independently confirmed it.
- **Silent sensitivity-study error** (novice F6): `App.tsx:484-486` catch →
  `console.error` only, no ErrorCard. Missing recovery path.
- **CaseBrowser "Tier 2 validated" filter always empty** (novice F7): no Tier 2
  cases in the fallback registry → empty list with no explanation.

## Recommendation

1. **Calibrated re-score before finalizing the composite:** restart the session
   so the real `.claude/agents/` eval fleet is invokable via `subagent_type=`,
   then re-run R6 with the calibrated protocol (not harsh general-purpose proxies).
   Only then average into the composite.
2. **Act on the real findings** (independent of calibration): the tier-promotion
   API-boundary wiring + the 38D BC dead-end are the highest-value fixes; both are
   legitimate Phase 39 (or a 38 follow-up) work items.
3. **Do NOT** mechanically crash the composite to ~68 from this caveated run —
   that would implicitly retroactively re-score prior phases on an uncalibrated
   scale, violating the additive-only + no-retroactive-rescore guards.
