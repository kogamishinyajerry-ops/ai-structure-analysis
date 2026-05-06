# Codex-Primary Routing

> **Status:** Active project routing for AI-Structure-FEA.
> **Canonical source:** ADR-011 and ADR-023. This page is a thin operational pointer.

## Truth Surfaces

| Surface | Role |
|---|---|
| GitHub / repo | Code truth. Branches, PRs, commits, CI, and merge history are authoritative for code and governance files. |
| Linear `Engineering` | Work-control truth. Issues define scope, acceptance, blockers, evidence, proof comments, and state. |
| CI artifacts and `runs/` | Runtime proof. CI is the canonical shared archive for checks. |
| Notion | Architecture/control mirror after repo and Linear truth settle. Notion is not the first write target for code truth. |

## Execution Roles

| Role | Responsibility | Boundary |
|---|---|---|
| Codex | Primary implementation agent. Edits repo files, runs tests, prepares review/proof artifacts, opens PRs, and writes approved proof comments. | Does not self-approve, auto-merge, or claim completion beyond evidence. |
| Local Claude Opus 4.7 | Reviewer/auditor. Reviews prepared packets, diffs, and high-risk decisions; returns `APPROVE`, `CHANGES_REQUIRED`, or `BLOCKER`. Invoked automatically by Codex when review is required and the local CLI is available. | Read-only by default; not the executor, repo owner, or Notion/code truth source. |
| Human owner | Final authority for explicit gates, emergency overrides, and external write approvals. | Must approve PR merges, Linear state transitions, Notion mutations, and other gated writes when policy requires it. |

## Lean Validation Lanes

| Lane | Use for | Gate level | Exit claim |
|---|---|---|---|
| Tier 0 — Sandbox / Demo | fast path discovery, adapter smoke, UI/workbench demo, report wiring | ordinary local verification and honest labeling | software-path evidence only |
| Tier 1 — Engineering Candidate | reproducible candidate deck/run/report | manifest, solver logs, units/material/BC/contact trace, hashes, limitations, Opus review when triggered | candidate result, not signed |
| Tier 2 — Signed Validation | physical-validation claims | benchmark source, metrics, tolerance comparison, convergence, artifact hashes, reviewer/signoff | signed validation / benchmark agreement |

Do not build Tier 2 packets for every Tier 0/Tier 1 change. Do build Tier 2
evidence before saying validated physics, signed GS evidence, benchmark
agreement, or completed bullet-through-steel behavior.

## Banned Default Routes

- Antigravity or Apex as repo owner/default executor.
- Claude Opus direct development by default.
- MiniMax, DeepSeek, or other models as code executors unless explicitly promoted for a bounded task.
- Notion-first truth changes.
- Direct pushes to `main`.

## Milestone-To-Goal Flow

Functional development is organized by `.planning/ROADMAP.md`. Each feature
milestone must be decomposed into one or more Linear issues before execution.
Codex may only start a long-running `/goal` run when one issue has outcome,
repository route, acceptance, boundaries, evidence requirements, claim tier, and
stop conditions.

OpenAI Symphony-style automation is the run pattern: discover one eligible
Linear issue, convert it into a 5-section `/goal`, execute on a Codex-owned
branch, verify locally, invoke Claude Opus read-only review when required, open
a PR, then publish proof after repo evidence exists.

## Issue-To-PR Flow

1. Start from a Linear issue or explicit user scope.
2. Confirm repository route, acceptance, boundaries, and evidence requirements.
3. Create a Codex-owned branch from current `main`.
4. Implement the smallest reversible diff.
5. Run local verification and mandatory reviewer/auditor checks. If review is
   required, call local Claude Opus automatically in read-only mode.
6. Open a PR with mechanical self-pass-rate, M-trigger checkboxes, test results,
   claim tier, and merge trailers.
7. Wait for required checks and review findings; fix before merge.
8. Show dry-run payloads before external proof comments, PR close/merge actions, branch-protection changes, or state transitions.
9. Merge only after explicit confirmation.
10. Update Linear proof/state after repo truth lands.

## Mandatory Review Triggers

The ADR-011 M1-M5 triggers remain binding:

| Trigger | Fires when |
|---|---|
| M1 | Governance text changes: `AGENTS.md`, `docs/adr/**`, `docs/governance/**`, `docs/failure_patterns/**`, ADR amendments. |
| M2 | Non-trivial executable assertions, CI claims, sign/direction math, or factual numerical computations. |
| M3 | HF zone compliance claims. |
| M4 | Governance text becomes enforcement code: hooks, CI, validators, lints, schemas. |
| M5 | A PR is opened while calibration ceiling is at or below 50%. |

When any trigger fires, attach independent review evidence before merge. Codex
should invoke local Claude Opus automatically for these triggers when the local
CLI is available; do not pause only to ask whether reviewer invocation is
allowed.

## Required Main Checks

`main` branch protection currently requires:

- `lint-and-test (3.11)`
- `calibration-cap-check`
- `trailer-check`
- `golden-samples-validation`

`scripts/apply_branch_protection.sh` is the idempotent source for the required
check list and protection settings.
