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
| Claude Opus 4.7 | Read-only reviewer/auditor for mandatory review gates and high-risk decisions. |
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
8. publish proof to Linear after repo evidence exists.

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

Claude review is read-only by default. It does not authorize merge,
self-approval, Linear state transitions, Notion mutation, branch-protection
changes, or signed-claim promotion.

## Proof Standard

Linear proof comments should summarize value and evidence, not raw logs:

- issue and milestone;
- branch and PR URL;
- claim tier;
- verification commands and results;
- Claude verdict and report path when applicable;
- blockers or owner decisions needed.

Notion mirror updates happen after repo and Linear truth settle, and must not
be presented as the source of code truth.
