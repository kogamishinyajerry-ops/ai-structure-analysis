# AGENTS.md

> **Realigned by ADR-026** (2026-05-24, Accepted): the development-team
> architecture is now **dual-engine** (Opus 4.7 主驱动 + Codex 代码审查),
> amending the AR-2026-05-06-001 Codex-primary role assignment. **`CLAUDE.md` is
> the team-architecture SSOT**; this file defines Codex-facing operating rules
> within that architecture. If the two drift, ADR-026 is the reconciliation anchor.

## Implementation Roles (dual-engine · ADR-026)

- **Opus 4.7 is the primary driver** for direct-execution work (FM-04a-class:
  blueprint → slice → composite synthesis → final audit; local-commit, no-push,
  under standing user authorization). This amends the AR-2026-05-06-001
  "Codex-primary / Opus-reviewer-not-executor" assignment.
- **Codex is the independent code reviewer + optional delegated codegen.** On
  risk-tier changes (schema / CalculiX adapter / solver-truth / `golden_samples`
  boundary / cross-≥3-file refactor / `confidence: low`), Codex reviews the diff
  before local commit (round cap = 3). Codex may also author delegated codegen
  when Opus defines the contract.
- **The Linear/Symphony Codex-primary path remains available** for bounded-issue
  PR work the user explicitly routes through Linear — no longer the default, but
  not removed.
- Linear is the work-control truth for Linear-routed work: explicit issues for
  scope, status proof, blockers, acceptance.
- GitHub/repo is the code truth. Linear-routed code lands by branch + PR only,
  never direct-push to `main`. FM-04a direct-execution = local-commit / no-push.
- Notion is an architecture/control mirror. Patch only after repo + Linear truth
  settle, and only with explicit confirmation for external writes.
- When Opus drives, Codex review is invoked by the main session via
  `codex-review-relay` (see `CLAUDE.md` Layer 1) — Claude Code's responsibility,
  not pushed to the user. When Codex drives a Linear issue, it may invoke local
  Opus as read-only reviewer without stopping to ask.
- For one bounded Linear issue, Codex may merge the PR and mark it Done when all
  required GitHub checks are green, merge state is clean, required proof/trailers
  exist, and the Opus owner gate returns `APPROVE` + `APPROVE_TO_MERGE`. Human
  acceptance is reserved for feature-milestone checkpoints.

## Operating Rules

- Start from repo truth: read this file, `.planning/STATE.md`, relevant ADRs, Linear issue contracts, and explicit user instructions before changing files.
- Default to Opus 主驱动 + Codex risk-tier review (dual-engine, ADR-026). Prefer single-agent execution over ad-hoc multi-agent orchestration; the evaluation fleet (3 `.claude/agents/` sub-agents) and Codex relay review are the sanctioned multi-agent surfaces.
- For Linear/Symphony work, one eligible Linear issue maps to one bounded run. Do not infer missing outcome, repository, acceptance, boundaries, or evidence requirements.
- External writes are gated. Show dry-run payloads before Notion updates, branch-protection changes, signed-validation claim promotion, or milestone completion announcements. Linear proof comments are allowed inside an explicit Linear issue run when they report verified repo evidence. GitHub merge actions and issue-level Done transitions are allowed only after the Claude owner gate approves the issue-level merge.
- Do not self-approve, auto-merge without the Claude owner gate, or claim completion beyond verified evidence.
- Current calibration gates still apply. If `scripts/compute_calibration_cap.py` reports a mandatory or blocking review gate, attach independent review evidence before merge.
- Lean validation workflow applies per ADR-023: sandbox/demo and engineering-candidate work may move quickly with explicit no-overclaim wording; strict validation packets are required only at signed physical-claim boundaries.

## Code Boundaries

- Prefer small, surgical, reversible diffs.
- Do not perform drive-by refactors, broad reformatting, framework swaps, or dependency additions.
- Do not change public interfaces, schemas, state machines, CLI contracts, persistent data formats, solver truth, golden samples, CI, or workflow policy unless the Linear/user scope explicitly calls for it.
- `golden_samples/` access (HF1.7a/b · ADR-011 AR-2026-05-16): signed-registry dirs (`^GS-\d{3}$`) are hard-stop read-only; `golden_samples/*-candidate/` is **writable** per the HF1.7b carve-out (pinned by `tests/test_hf1_path_guard_candidate_carveout.py`); any other `golden_samples/**` change needs an explicit signed validation/golden-sample issue.
- Keep solver/runtime claims honest: smoke tests, synthetic fixtures, and demo-unsigned paths are not signed validation.
- Name the claim tier when summarizing simulation work: Tier 0 sandbox/demo, Tier 1 engineering candidate, or Tier 2 signed validation. Never let Tier 0 or Tier 1 evidence imply Tier 2 validation.

## Review Roles (dual-engine · ADR-026)

- **Opus 主驱动** authors blueprints, slice implementations, tests, and composite
  synthesis for direct-execution work; **Codex** authors delegated codegen and
  reviews diffs. Either may author; the driver depends on the collaboration path.
- **Codex code review** returns `APPROVE`, `CHANGES_REQUIRED`, or `BLOCKER` with
  evidence-focused findings on the diff (round cap = 3).
- **Opus review** (when Codex drives a Linear issue) returns the same verdicts;
  for ordinary issue-level PRs Opus may act as delegated owner gate and authorize
  merge only with `APPROVE` + `APPROVE_TO_MERGE` after mechanical gates are green.
- Neither engine authorizes self-approval, Notion mutation, branch-protection
  changes, signed-validation (Tier 2) promotion, or milestone-level user
  acceptance by drift.
- A green CI run is not sufficient for governance or role-authority changes.
  **Repo-level policy changes (incl. this architecture realignment) need explicit
  review evidence** — ADR-026 itself is dogfood-reviewed via Codex relay before
  ratification — and must preserve the milestone-level human acceptance gate.

## Completion Format

For meaningful tasks, report:

- Changed files
- Implementation summary
- Verification command
- Test result
- Risks / unresolved issues
- Next recommended step
