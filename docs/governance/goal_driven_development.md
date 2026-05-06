# Goal-Driven Development Workflow

This repository uses Codex + Linear + OpenAI Symphony-style automation as a
bounded execution loop. The loop is feature-milestone driven and review-gated;
it is not an open-ended agent swarm.

## Control Surfaces

| Surface | Responsibility |
|---|---|
| `.planning/ROADMAP.md` | Feature milestone map and reusable `/goal` template. |
| `.planning/STATE.md` | Current repo-side execution snapshot and PR/carry-over ledger. |
| Linear `Engineering` | Work-control truth for issue scope, acceptance, blockers, evidence, and proof. |
| GitHub / repo | Code truth for branches, commits, PRs, CI, and merge history. |
| Claude Opus 4.7 | Read-only reviewer/auditor and delegated issue-level owner gate. |
| Notion | Architecture/control mirror after repo and Linear truth settle. |

## Issue Eligibility

Codex may start an autonomous `/goal` run only when one Linear issue provides:

- outcome;
- repository route;
- acceptance criteria;
- file or subsystem boundaries;
- evidence requirements;
- claim tier: Tier 0, Tier 1, or Tier 2 per ADR-023;
- reviewer trigger status;
- stop conditions.

If any field is missing, the issue is not executable. The next action is to
refresh the Linear contract, not to infer scope from stale PRs or chat history.

## Symphony-Style Run Shape

OpenAI Symphony-style orchestration is used as a bounded run pattern:

1. discover eligible Linear work;
2. select one issue;
3. convert it into a 5-section `/goal`;
4. execute with Codex on a branch;
5. verify locally;
6. invoke Claude Opus read-only review when required;
7. open a PR;
8. wait for required GitHub checks and merge-state proof;
9. invoke Claude Opus owner gate for the issue-level merge decision;
10. if Claude returns `APPROVE_TO_MERGE`, merge the PR, mark the Linear issue
   Done, and publish proof to Linear.

The default remains single-agent Codex execution. Additional agents or reviewers
are used only when the issue or user explicitly asks for them.

## `/goal` Contract

Every long-running run must use these sections in order:

1. `Objective`
2. `Scope`
3. `Constraints`
4. `Done when`
5. `Stop if`

Every `Done when` item must be mechanically verifiable by a file, command,
test, PR, or Linear artifact. Every `Stop if` item must be detectable during the
run.

## Review Gates

Claude Opus review is required when ADR-011 M-triggers fire, calibration gates
require review, governance text changes, signed-validation work begins, or the
user explicitly requests review.

Claude review remains read-only with respect to code execution: Claude reviews
packets, diffs, PR bodies, checks, and proof, but does not edit files or run
repo mutations.

For one bounded Linear issue, Claude Opus 4.7 is the delegated owner gate for
the merge decision when all of these are true:

- the issue has an executable Linear contract;
- the PR targets `main`, is not a draft, and has clean merge state;
- all required GitHub checks pass;
- required trailers and proof artifacts exist;
- the diff under review was authored by Codex or another authorized executor,
  not by the Claude reviewer making the owner-gate decision;
- claim-tier wording is honest and no signed physical claim is promoted;
- Claude returns `APPROVE` and an explicit `APPROVE_TO_MERGE` line.

When that gate passes, Codex may merge the issue-level PR and mark the Linear
issue Done without waiting for the human user. The human user returns for
feature-milestone acceptance and experience checks, not every issue-level
merge.

Claude owner-gate approval does not authorize self-approval, Notion mutation,
branch-protection changes, signed-validation promotion, broad role-authority
changes, or milestone-level completion claims.

## Proof Standard

Linear proof comments should summarize value and evidence, not raw logs:

- issue and milestone;
- branch and PR URL;
- claim tier;
- verification commands and results;
- Claude verdict and report path when applicable;
- delegated Claude owner-gate decision when merge is performed;
- blockers or milestone-level decisions needed.

Notion mirror updates happen after repo and Linear truth settle, and must not
be presented as the source of code truth.
