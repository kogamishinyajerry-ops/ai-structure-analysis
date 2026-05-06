# ENG-39 Lean Validation Workflow Claude Audit

- **Reviewer:** local Claude Opus 4.7
- **Mode:** read-only reviewer/auditor, tools disabled
- **Command:** `claude -p <packet> --model opus --no-session-persistence --tools "" --max-budget-usd 2.00`
- **Branch:** `codex/ENG-39-lean-validation-workflow`
- **Linear:** ENG-39
- **R1 Verdict:** `CHANGES_REQUIRED`
- **R2 Verdict:** `APPROVE`
- **Follow-up Verdict:** `APPROVE`

## R1 Reviewer Result

Claude Opus returned `CHANGES_REQUIRED`, not `BLOCKER`.

The reviewer found the ENG-39 direction acceptable but required cleanup before PR:

1. Keep unrelated untracked files out of the ENG-39 branch/PR, especially
   `golden_samples/GS-001/**`, `hello.py`, status artifacts, helper scripts, and
   `uv.lock`.
2. Confirm ADR-023 forbids demo/candidate outputs from being called validated
   physics, benchmark agreement, signed GS evidence, steel perforation complete,
   or bullet-through-steel complete.
3. Confirm Tier 2 keeps all strict physical-claim requirements: public benchmark
   source, material/failure traceability, deck provenance, solver logs,
   residual/perforation metrics with tolerance comparison, convergence evidence,
   artifact hashes, independent reviewer/signoff, and Linear/GitHub proof
   linkage.
4. Confirm automatic Claude invocation remains read-only and does not authorize
   merge, self-approval, Linear state transitions, Notion mutations, branch
   protection changes, or signed-claim promotion.
5. Confirm the sync report marks Notion mirror content as proposed only, not
   written.

## R1 Follow-up Plan

- Restrict the PR diff to the ENG-39 governance/docs/report files only.
- Tighten ADR-023 forbidden-claim and Tier 2 required-evidence wording.
- Make the sync report explicitly say the Notion payload is proposed, not
  written.
- Re-run local validation and a scoped Claude review before PR handoff.

## R2 Reviewer Result

Claude Opus returned `APPROVE`.

The reviewer confirmed that R1 was sufficiently addressed for ENG-39 to
continue toward PR:

1. The staged PR diff is restricted to the eight in-scope ENG-39 files:
   `.planning/STATE.md`, `AGENTS.md`, `README.md`,
   `docs/adr/ADR-023-lean-validation-workflow.md`,
   `docs/governance/onboarding.md`, `docs/governance/routing.md`,
   `reports/codex_tool_reports/eng39_lean_validation_workflow_claude_audit.md`,
   and `reports/codex_tool_reports/eng39_lean_validation_workflow_sync.md`.
2. ADR-023 explicitly lists the forbidden Tier 0/Tier 1 claim phrases.
3. ADR-023 states that all Tier 2 physical-claim evidence items are required.
4. Reviewer automation remains read-only and does not authorize merge,
   self-approval, Linear state transitions, Notion mutations, branch protection
   changes, or signed-claim promotion.
5. The sync report marks Notion as pending and the mirror payload as proposed,
   not written.
6. The R1 audit is archived in this file.

Non-blocking reviewer advisories:

- The 50% calibration ceiling still makes the Codex pre-merge gate mandatory.
- Unrelated untracked files remain in the local worktree; they are excluded from
  the staged diff but must not be added to the ENG-39 PR.

## R2 Verification Evidence

- `git diff --cached --check` passed.
- `python3 scripts/compute_calibration_cap.py --human` returned a 50% T1
  calibration ceiling and mandatory Codex pre-merge gate.
- `.venv/bin/python scripts/check_commit_trailers.py --from-ref origin/main --require-codex-verified --require-reviewed-by`
  returned `HF5 commit-trailer check passed`.
- `rg` sweep confirmed forbidden-claim phrases and Notion proposed/not-written
  wording in the scoped docs.

## Follow-up Reviewer Result

After PR #143 opened, the user requested a clearer feature-milestone workflow
using Codex + Linear + OpenAI Symphony-style `/goal` runs with Claude Opus 4.7
review. A follow-up docs/planning diff added `.planning/ROADMAP.md`,
`docs/governance/goal_driven_development.md`, and routing/onboarding/STATE
updates.

Claude Opus returned `APPROVE`.

The reviewer confirmed:

1. The follow-up diff is docs/planning only and does not touch solver code,
   schemas, public APIs, CI, dependencies, `golden_samples/**`, or runtime truth
   mechanisms.
2. Linear remains work-control truth, GitHub/repo remains code truth, and Notion
   remains a downstream mirror.
3. Claude remains read-only reviewer/auditor and cannot authorize merge,
   self-approval, Linear transitions, Notion mutation, branch-protection change,
   or signed-claim promotion.
4. The milestone ordering is coherent: FM-01 operator shell, FM-02 AERON path,
   FM-03 candidate report spine, FM-04 signed validation gate, and FM-05
   nonlinear/adaptive activation.
5. The reusable `/goal` template has explicit `Objective`, `Scope`,
   `Constraints`, `Done when`, and `Stop if` sections.

Non-blocking reviewer nit addressed in `.planning/ROADMAP.md`: milestone exit
evidence is satisfied by repo artifacts, CI/runtime proof, Linear/GitHub
linkage, and owner-approved gates where required; Claude may review evidence but
cannot mark a milestone complete by itself.
