# AGENTS.md

## Codex-Primary Workflow

- Codex is the primary implementation agent for this repository.
- Linear is the work-control truth: use explicit Linear issues for scoped work, status proof, blockers, and acceptance.
- GitHub and this repository are the code truth. Code changes land by branch and PR only; never direct-push to `main`.
- Notion is an architecture/control mirror. Patch Notion only after repo and Linear truth are settled, and only with explicit confirmation for external writes.
- Local Claude Opus 4.7 is reviewer/auditor and the delegated issue-level owner gate. It may review prepared packets or diffs, but it is not the default executor and must not become the repo owner for milestone strategy, signed validation, or policy authority by drift.
- When a reviewer is required and the local `claude` CLI is available, Codex may invoke local Claude Opus 4.7 automatically as a read-only reviewer. Do not stop solely to ask whether reviewer invocation is allowed.
- For one bounded Linear issue, Codex may merge the PR and mark that issue Done when all required GitHub checks are green, merge state is clean, required proof/trailers exist, and local Claude Opus 4.7 returns `APPROVE` with an explicit `APPROVE_TO_MERGE` owner-gate decision. Human user acceptance is reserved for feature-milestone experience checkpoints, not routine issue-level merge approval.

## Operating Rules

- Start from repo truth: read this file, `.planning/STATE.md`, relevant ADRs, Linear issue contracts, and explicit user instructions before changing files.
- Prefer single-agent Codex execution unless the user explicitly asks for multi-agent orchestration.
- For Linear/Symphony work, one eligible Linear issue maps to one bounded run. Do not infer missing outcome, repository, acceptance, boundaries, or evidence requirements.
- External writes are gated. Show dry-run payloads before Notion updates, branch-protection changes, signed-validation claim promotion, or milestone completion announcements. Linear proof comments are allowed inside an explicit Linear issue run when they report verified repo evidence. GitHub merge actions and issue-level Done transitions are allowed only after the Claude owner gate approves the issue-level merge.
- Do not self-approve, auto-merge without the Claude owner gate, or claim completion beyond verified evidence.
- Current calibration gates still apply. If `scripts/compute_calibration_cap.py` reports a mandatory or blocking review gate, attach independent review evidence before merge.
- Lean validation workflow applies per ADR-023: sandbox/demo and engineering-candidate work may move quickly with explicit no-overclaim wording; strict validation packets are required only at signed physical-claim boundaries.

## Code Boundaries

- Prefer small, surgical, reversible diffs.
- Do not perform drive-by refactors, broad reformatting, framework swaps, or dependency additions.
- Do not change public interfaces, schemas, state machines, CLI contracts, persistent data formats, solver truth, golden samples, CI, or workflow policy unless the Linear/user scope explicitly calls for it.
- Treat `golden_samples/**` as read-only unless a signed validation/golden-sample issue explicitly authorizes a change.
- Keep solver/runtime claims honest: smoke tests, synthetic fixtures, and demo-unsigned paths are not signed validation.
- Name the claim tier when summarizing simulation work: Tier 0 sandbox/demo, Tier 1 engineering candidate, or Tier 2 signed validation. Never let Tier 0 or Tier 1 evidence imply Tier 2 validation.

## Review Roles

- Codex may author code, tests, docs, proof packets, and PRs.
- Claude Opus review should return a clear `APPROVE`, `CHANGES_REQUIRED`, or `BLOCKER` verdict with evidence-focused findings.
- Claude Opus review is automatic for mandatory reviewer gates. For ordinary issue-level PRs, Claude may also act as the delegated owner gate and authorize merge only with `APPROVE` plus `APPROVE_TO_MERGE` after mechanical gates are green.
- Claude does not authorize code execution, self-approval, Notion mutation, branch-protection changes, signed-validation promotion, or milestone-level user acceptance.
- A green CI run is not sufficient for governance or role-authority changes. Repo-level policy changes need explicit review evidence and must preserve the milestone-level human acceptance gate.

## Completion Format

For meaningful tasks, report:

- Changed files
- Implementation summary
- Verification command
- Test result
- Risks / unresolved issues
- Next recommended step
