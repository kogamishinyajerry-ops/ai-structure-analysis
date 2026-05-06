# PR #126 Codex Disposition — WF-00

**Pilot issue:** ENG-32 · WF-00 Codex-primary / Claude-audited workflow pilot
**Target PR:** #126 · `feat(aeron): S0+S1 — AGENTS.md + L0 FEABackend protocol`
**Repo:** `kogamishinyajerry-ops/ai-structure-analysis`
**Reviewer role:** Codex primary executor, producing the disposition packet for local Claude Opus audit.
**Date:** 2026-05-06

## Verdict

**BLOCKER — do not merge PR #126 as-is.**

The AERON protocol code in #126 may be salvageable later, but the PR's root
`AGENTS.md` cannot become repo policy in its current form because it assigns
project ownership and merge authority to an Apex/Claude-controlled workflow.
That conflicts with the user-approved workflow for this repo:

- Codex is the primary implementation agent.
- Linear is the work-control truth.
- GitHub/repo is the code truth.
- Local Claude Opus 4.7 is reviewer/auditor, not the owner/executor.
- Notion is an architecture/control mirror after repo/Linear truth is settled.

## Blocking Finding

### P1 · Root `AGENTS.md` reverses the approved execution model

**File:** `AGENTS.md` in PR #126
**Severity:** BLOCKER

PR #126 introduces a root `AGENTS.md` that says Apex/Claude owns `main`,
reviews/merges PRs, writes Notion, and that Codex works only on delegated
`codex/<task_id>` branches. This directly conflicts with the user-approved
Codex-primary Linear/Symphony workflow, where Codex is the primary executor
and Claude Opus is reviewer/auditor.

If merged unchanged, future agents would read the repo-level `AGENTS.md` as
higher-priority local policy and route authority back to Apex/Claude, undoing
the intended Codex-primary workflow.

**Required fix:**

1. Rewrite the proposed root `AGENTS.md` so it encodes Codex-primary execution,
   Linear work-control, GitHub code truth, Claude Opus reviewer/auditor, and
   Notion mirror-only behavior.
2. Remove or reword Apex-only ownership, Apex-only merge authority, and
   "Codex as delegated PR worker only" language.
3. Add a final post-fix reviewer acceptance from local Claude Opus after the
   rewritten policy is visible in the PR diff.

## Non-Blocking Notes

- `aeron/protocols/fea_backend.py` has already received two rounds of Codex
  technical review on packaging, strict status vocabulary, fault taxonomy, and
  strict Pydantic carriers.
- CI is green on #126, but CI does not validate role-authority policy. Green
  checks are not sufficient to merge a repo-level governance change.
- A later Codex-owned PR may salvage the AERON L0 protocol files after the
  workflow policy is aligned.

## Evidence

- `python3 scripts/compute_calibration_cap.py --human`:
  - T1 calibration ceiling: 50%
  - Codex pre-merge gate: MANDATORY
  - Basis: 4 of last 5 = CHANGES_REQUIRED -> ceiling 50%
- `gh pr view 126 --repo kogamishinyajerry-ops/ai-structure-analysis --json ...`:
  - Head branch: `claude/L0-protocol`
  - Status: not draft, merge state `CLEAN`
  - Checks: `lint-and-test (3.11)`, `calibration-cap-check`, and
    `build-and-push` are successful
  - Existing comments include owner self-review, Codex Round 1, and Codex
    Round 2, but no final post-fix independent reviewer acceptance

## Decision Needed

Route #126 through a governance rewrite before merge, or close it and reopen a
Codex-owned PR that separates the workflow policy update from salvageable AERON
protocol code.
