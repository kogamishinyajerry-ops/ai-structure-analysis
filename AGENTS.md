# AGENTS.md

## Codex-Primary Workflow

- Codex is the primary implementation agent for this repository.
- Linear is the work-control truth: use explicit Linear issues for scoped work, status proof, blockers, and acceptance.
- GitHub and this repository are the code truth. Code changes land by branch and PR only; never direct-push to `main`.
- Notion is an architecture/control mirror. Patch Notion only after repo and Linear truth are settled, and only with explicit confirmation for external writes.
- Local Claude Opus 4.7 is reviewer/auditor. It may review prepared packets or diffs, but it is not the default executor and must not become the repo owner by policy drift.
- When a reviewer is required and the local `claude` CLI is available, Codex may invoke local Claude Opus 4.7 automatically as a read-only reviewer. Do not stop solely to ask whether reviewer invocation is allowed; still stop for merge, self-approval, Linear state transitions, Notion mutations, branch-protection changes, or signed-validation claim promotion.

## Operating Rules

- Start from repo truth: read this file, `.planning/STATE.md`, relevant ADRs, Linear issue contracts, and explicit user instructions before changing files.
- Prefer single-agent Codex execution unless the user explicitly asks for multi-agent orchestration.
- For Linear/Symphony work, one eligible Linear issue maps to one bounded run. Do not infer missing outcome, repository, acceptance, boundaries, or evidence requirements.
- External writes are gated. Show dry-run payloads before Linear comments, GitHub comments/PR actions, or Notion updates; do not transition states, close/merge PRs, or mutate Notion without explicit confirmation.
- Do not self-approve, auto-merge, or claim completion beyond verified evidence.
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
- Claude Opus review is automatic for mandatory reviewer gates, but it remains read-only audit evidence. It does not authorize code execution, merge, self-approval, Linear/Notion/GitHub writes, or signed-validation promotion.
- A green CI run is not sufficient for governance or role-authority changes. Repo-level policy changes need explicit review evidence.

## Completion Format

For meaningful tasks, report:

- Changed files
- Implementation summary
- Verification command
- Test result
- Risks / unresolved issues
- Next recommended step
