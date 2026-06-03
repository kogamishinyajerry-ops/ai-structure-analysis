# AI-Structure-FEA · Feature Roadmap

> ## ⛔ SUPERSEDED by ADR-027 (2026-06-03, Accepted)
> This FM-01..05 **Linear / Codex-primary** milestone model is **no longer operative**. Its role
> assignment ("Codex as primary executor, Opus read-only reviewer") was reversed by **ADR-026**
> (Opus 主驱动 + Codex review), and the project actually ran the **FM-04a Opus-primary** track.
> The current goal model is **ADR-027**: FM-04a v1.0 = honest engineering-candidate (complete);
> the 6-dim rubric is a health dashboard (not a 99-gate); v2 = FM-05 "Outward-Credible Validation
> & Reproducibility" (NAFEMS real benchmark + reproduce-CLI). The **FM-02 "AERON-Backed Solve
> Path"** milestone below is **dead framing** — the `aeron/` code itself is a live, tested seam
> (see `aeron/README.md`), but it is not pursued as an active milestone. Text below retained for
> historical context only.
>
> **Status:** SUPERSEDED (was: Active planning surface).
> **Last updated:** 2026-05-07 (superseded 2026-06-03).
> **Control truth:** Linear `Engineering` issues own scoped work; this file
> defines the repo-side feature milestone map.

This roadmap translates the project into feature milestones that can be executed
through Codex + Linear + OpenAI Symphony-style `/goal` runs, with local Claude
Opus 4.7 as read-only reviewer/auditor when gates fire.

## Milestone Model

Each milestone is a product capability checkpoint, not a loose theme. A
milestone may contain multiple Linear issues, but every executable issue must
have:

- outcome;
- repository route;
- acceptance;
- boundaries;
- evidence requirements;
- claim tier per ADR-023;
- reviewer trigger status;
- one `/goal` command with `Objective`, `Scope`, `Constraints`, `Done when`,
  and `Stop if`.

Milestone exit evidence is satisfied by repo artifacts, CI/runtime proof,
Linear/GitHub linkage, and owner-approved gates where required. Claude Opus may
review the evidence, but it cannot mark a milestone complete by itself.

## Functional Milestones

| Milestone | Target capability | Claim tier | Entry condition | Exit evidence |
|---|---|---|---|---|
| FM-01 — Web Console Operator Shell | A user can open the Web Console and see current workflow state, backend provenance, and next allowed action without reading repo history. | Tier 0 sandbox/demo | ENG-39 workflow PR merged; one Linear issue has complete autonomous contract. | Browser or HTTP smoke, screenshots or status artifact, PR evidence, no signed-physics claim. |
| FM-02 — AERON-Backed Solve Path | One user-facing path invokes the `CalculiXFEABackend` spine end-to-end while preserving existing `SimState -> dict` compatibility. | Tier 1 engineering candidate | A bounded issue names exactly one caller/UI/API path and excludes protocol/schema changes unless explicitly authorized. | Focused unit/integration tests, backend provenance, reproducibility notes, Claude review if M-trigger fires. |
| FM-03 — Candidate Report Spine | A candidate run can produce a compact reproducibility package: deck/model provenance, solver logs, units/material/BC/contact assumptions, hashes, limitations, and report output. | Tier 1 engineering candidate | FM-02 proof exists; issue specifies fixture/deck and report surface. | Manifest, logs, report artifact, extraction command, hash list, explicit `not signed validation` wording. |
| FM-04 — GS101 Signed Validation Gate | The project can start the strict GS101 signed path only after benchmark/source and evidence requirements are explicit. | Tier 2 signed validation | ENG-24/ENG-25 or successor issues define benchmark source, deck provenance, metrics, tolerances, convergence, and signoff. | Public benchmark linkage, metrics/tolerance table, convergence evidence, artifact hashes, independent reviewer/signoff. |
| FM-05 — Nonlinear / Adaptive Mesh Activation | Phase 3 begins only after the active candidate lane has a stable user-facing solve/report loop. | Tier 1 or Tier 2 depending on claim | FM-02 and FM-03 are merged; signed claims require FM-04 evidence. | ADR or Linear activation packet, scope-limited prototype, tests, claim-tier label. |

## Execution Cadence

1. Select one milestone.
2. Create or refresh one Linear issue with the autonomous issue contract.
3. Convert the issue into one `/goal` command.
4. Execute the goal on a Codex-owned branch.
5. Run local verification and mandatory Claude Opus read-only review.
6. Open PR with claim tier, test evidence, reviewer evidence, and merge
   trailers.
7. After merge, write concise proof back to Linear and mirror Notion only after
   repo and Linear truth settle.

## Current Next Slice

Next executable feature work should start with FM-01 or FM-02, not GS101 signed
validation:

- FM-01 if the priority is a visible, repeatable operator workflow.
- FM-02 if the priority is deeper AERON adoption in one concrete caller path.

Do not infer missing acceptance criteria from stale PRs. If no Linear issue is
eligible, the next slice is a control-plane issue to create the missing issue
contract.

## Reusable `/goal` Template

```text
/goal Execute one AI-Structure-FEA milestone issue from Linear through a reviewable PR.

Objective:
  Deliver exactly one bounded Linear issue for the selected functional milestone.

Scope:
  - Repository: /Users/Zhuanz/20260408 AI StructureAnalysis
  - Milestone: FM-01, FM-02, FM-03, FM-04, or FM-05 from .planning/ROADMAP.md
  - Linear issue: the single eligible ENG issue selected for this run

Constraints:
  - Follow AGENTS.md, ADR-011, ADR-012, ADR-013, and ADR-023.
  - Use Codex as primary executor and local Claude Opus 4.7 as read-only reviewer/auditor when required.
  - Do not change solver protocols, schemas, public APIs, CI policy, dependencies, runtime truth mechanisms, solver decks, or golden_samples/** unless the issue explicitly authorizes it.
  - Name the claim tier in PR, proof artifacts, and handoff text.
  - Do not merge, self-approve, transition Linear state, mutate Notion, or promote signed claims without explicit owner authority.

Done when:
  1. The Linear issue has outcome, repository route, acceptance, boundaries, evidence requirements, and claim tier recorded.
  2. A Codex-owned branch contains the minimal implementation or documentation diff for that issue.
  3. The closest relevant verification commands exit 0 and their command lines/results are recorded in a repo artifact or PR body.
  4. Required Claude Opus review evidence is archived under reports/codex_tool_reports/ and returns APPROVE, or required changes are handled in the same branch.
  5. A GitHub PR exists with claim tier, verification results, M-trigger check, reviewer evidence, and merge trailers.
  6. Linear proof payload is prepared or written only after the PR URL and verification evidence exist.

Stop if:
  - No single eligible Linear issue has a complete autonomous contract.
  - The work would touch a forbidden surface outside the issue boundaries.
  - Tier 0 or Tier 1 evidence would be described as signed validation.
  - Tier 2 work lacks benchmark/source, tolerance, convergence, artifact hash, or signoff requirements.
  - Required local verification cannot run and no manual check path can be stated.
```
