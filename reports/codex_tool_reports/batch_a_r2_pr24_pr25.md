2026-04-25T18:53:10.235585Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-research-deerflow/SKILL.md: missing YAML frontmatter delimited by ---
2026-04-25T18:53:10.235609Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-report-pretext/SKILL.md: missing YAML frontmatter delimited by ---
OpenAI Codex v0.118.0 (research preview)
--------
workdir: /Users/Zhuanz/20260408 AI StructureAnalysis
model: gpt-5.4
provider: openai
approval: never
sandbox: danger-full-access
reasoning effort: xhigh
reasoning summaries: none
session id: 019dc5fd-1713-7013-a657-45951a8498b1
--------
user
You are reviewing two stacked R2 PRs that previously got CHANGES_REQUIRED on R1. Verify the fixes resolve every R1 HIGH and surface any HIGH/MEDIUM the R2 introduced. Output a concrete verdict per PR (APPROVE / APPROVE_WITH_NITS / CHANGES_REQUIRED) with line references.

Repo: github.com/kogamishinyajerry-ops/ai-structure-analysis (public). Use `gh pr diff <num>`, `gh pr view <num>`, and direct file reads to inspect.

--- PR #24 [ADR-012 calibration cap, R2] ---
URL: https://github.com/kogamishinyajerry-ops/ai-structure-analysis/pull/24
R1 verdict: CHANGES_REQUIRED, 2 HIGH.
R2 fixes claimed:
1. HIGH#1 (PR-number sort vs merge-order): scripts/compute_calibration_cap.py now sorts entries by `merged_at` (ISO 8601 lexicographic) at load time. Adversarial test test_load_state_sorts_by_merged_at_not_pr_counterexample encodes the exact repro (PR #20 merged before #18/#19 on 2026-04-25).
2. HIGH#2 (silent fallback on bad state): _validate_state_dict() now hard-fails on missing file, schema_version mismatch, duplicate `pr`, missing `merged_at`, unknown `r1_outcome`, non-int/zero/negative pr; main() catches CalibrationStateError → exit 1 with stderr.
3. reports/calibration_state.json doc field updated.
Tests: 60 (was 42); +18 adversarial state-validation + main() fail-closed cases.

--- PR #25 [ADR-013 branch protection, R2 stacked on #24] ---
URL: https://github.com/kogamishinyajerry-ops/ai-structure-analysis/pull/25
R1 verdict: CHANGES_REQUIRED, 3 HIGH.
R2 fixes claimed:
1. HIGH#1 (HTML-comment / fenced-code bypass): scripts/extract_pr_self_pass_rate.py now strips HTML comments, triple-backtick / triple-tilde fenced blocks, and inline code BEFORE heading match. test_r2_html_comment_bypass_codex_repro encodes Codex's exact repro (hidden 30%, visible 95% → 95).
2. HIGH#2 (untrusted PR validators): .github/workflows/calibration-cap-check.yml now uses actions/checkout@v4 ref=main path=trusted; runs scripts/compute_calibration_cap.py from trusted/; PR's own checkout intentionally absent; PR body comes from event payload.
3. HIGH#3 inherited from #24 fail-closed (resolved by #24 R2).
Tests: 27 (was 16); +11 adversarial bypass cases.

For each PR, output sections:
- VERDICT: APPROVE / APPROVE_WITH_NITS / CHANGES_REQUIRED
- HIGH findings: enumerate with file:line references
- MEDIUM findings: enumerate with file:line references
- LOW/NITS: brief
- Notes on any new regressions introduced by the R2 diff itself
- Self-pass-rate calibration check: both PRs claim 30%, deliberately at the BLOCKING ceiling; flag if the actual pass rate diverges meaningfully

Self-pass-rate claim on both PRs is 30%. Be terse but concrete. Cite exact file paths and line numbers.

codex
Reviewing PRs `#24` and `#25` as stacked R2 follow-ups, with a code-review-only scope. I’m loading the review workflow guidance, then I’ll inspect each PR’s metadata, diff, and touched files to verify the claimed HIGH fixes and check for new HIGH/MEDIUM regressions.
exec
/bin/zsh -lc "sed -n '1,220p' /Users/Zhuanz/.codex/plugins/cache/openai-curated/superpowers/421657af0e7e94573f3a5f2c51091df43668da94/skills/using-superpowers/SKILL.md" in /Users/Zhuanz/20260408 AI StructureAnalysis
exec
/bin/zsh -lc "sed -n '1,220p' /Users/Zhuanz/.agents/skills/gsd-code-review/SKILL.md" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
---
name: gsd-code-review
description: "Review source files changed during a phase for bugs, security issues, and code quality problems"
argument-hint: "<phase-number> [--depth=quick|standard|deep] [--files file1,file2,...]"
allowed-tools:
  - Read
  - Bash
  - Glob
  - Grep
  - Write
  - Task
---

<objective>
Review source files changed during a phase for bugs, security vulnerabilities, and code quality problems.

Spawns the gsd-code-reviewer agent to analyze code at the specified depth level. Produces REVIEW.md artifact in the phase directory with severity-classified findings.

Arguments:
- Phase number (required) — which phase's changes to review (e.g., "2" or "02")
- `--depth=quick|standard|deep` (optional) — review depth level, overrides workflow.code_review_depth config
  - quick: Pattern-matching only (~2 min)
  - standard: Per-file analysis with language-specific checks (~5-15 min, default)
  - deep: Cross-file analysis including import graphs and call chains (~15-30 min)
- `--files file1,file2,...` (optional) — explicit comma-separated file list, skips SUMMARY/git scoping (highest precedence for scoping)

Output: {padded_phase}-REVIEW.md in phase directory + inline summary of findings
</objective>

<execution_context>
@$HOME/.Codex/get-shit-done/workflows/code-review.md
</execution_context>

<context>
Phase: $ARGUMENTS (first positional argument is phase number)

Optional flags parsed from $ARGUMENTS:
- `--depth=VALUE` — Depth override (quick|standard|deep). If provided, overrides workflow.code_review_depth config.
- `--files=file1,file2,...` — Explicit file list override. Has highest precedence for file scoping per D-08. When provided, workflow skips SUMMARY.md extraction and git diff fallback entirely.

Context files (AGENTS.md, SUMMARY.md, phase state) are resolved inside the workflow via `gsd-tools init phase-op` and delegated to agent via `<files_to_read>` blocks.
</context>

<process>
This command is a thin dispatch layer. It parses arguments and delegates to the workflow.

Execute the code-review workflow from @$HOME/.Codex/get-shit-done/workflows/code-review.md end-to-end.

The workflow (not this command) enforces these gates:
- Phase validation (before config gate)
- Config gate check (workflow.code_review)
- File scoping (--files override > SUMMARY.md > git diff fallback)
- Empty scope check (skip if no files)
- Agent spawning (gsd-code-reviewer)
- Result presentation (inline summary + next steps)
</process>

 succeeded in 0ms:
---
name: using-superpowers
description: Use when starting any conversation - establishes how to find and use skills, requiring Skill tool invocation before ANY response including clarifying questions
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, skip this skill.
</SUBAGENT-STOP>

<EXTREMELY-IMPORTANT>
If you think there is even a 1% chance a skill might apply to what you are doing, you ABSOLUTELY MUST invoke the skill.

IF A SKILL APPLIES TO YOUR TASK, YOU DO NOT HAVE A CHOICE. YOU MUST USE IT.

This is not negotiable. This is not optional. You cannot rationalize your way out of this.
</EXTREMELY-IMPORTANT>

## Instruction Priority

Superpowers skills override default system prompt behavior, but **user instructions always take precedence**:

1. **User's explicit instructions** (CLAUDE.md, GEMINI.md, AGENTS.md, direct requests) — highest priority
2. **Superpowers skills** — override default system behavior where they conflict
3. **Default system prompt** — lowest priority

If CLAUDE.md, GEMINI.md, or AGENTS.md says "don't use TDD" and a skill says "always use TDD," follow the user's instructions. The user is in control.

## How to Access Skills

**In Claude Code:** Use the `Skill` tool. When you invoke a skill, its content is loaded and presented to you—follow it directly. Never use the Read tool on skill files.

**In Copilot CLI:** Use the `skill` tool. Skills are auto-discovered from installed plugins. The `skill` tool works the same as Claude Code's `Skill` tool.

**In Gemini CLI:** Skills activate via the `activate_skill` tool. Gemini loads skill metadata at session start and activates the full content on demand.

**In other environments:** Check your platform's documentation for how skills are loaded.

## Platform Adaptation

Skills use Claude Code tool names. Non-CC platforms: see `references/copilot-tools.md` (Copilot CLI), `references/codex-tools.md` (Codex) for tool equivalents. Gemini CLI users get the tool mapping loaded automatically via GEMINI.md.

# Using Skills

## The Rule

**Invoke relevant or requested skills BEFORE any response or action.** Even a 1% chance a skill might apply means that you should invoke the skill to check. If an invoked skill turns out to be wrong for the situation, you don't need to use it.

```dot
digraph skill_flow {
    "User message received" [shape=doublecircle];
    "About to EnterPlanMode?" [shape=doublecircle];
    "Already brainstormed?" [shape=diamond];
    "Invoke brainstorming skill" [shape=box];
    "Might any skill apply?" [shape=diamond];
    "Invoke Skill tool" [shape=box];
    "Announce: 'Using [skill] to [purpose]'" [shape=box];
    "Has checklist?" [shape=diamond];
    "Create TodoWrite todo per item" [shape=box];
    "Follow skill exactly" [shape=box];
    "Respond (including clarifications)" [shape=doublecircle];

    "About to EnterPlanMode?" -> "Already brainstormed?";
    "Already brainstormed?" -> "Invoke brainstorming skill" [label="no"];
    "Already brainstormed?" -> "Might any skill apply?" [label="yes"];
    "Invoke brainstorming skill" -> "Might any skill apply?";

    "User message received" -> "Might any skill apply?";
    "Might any skill apply?" -> "Invoke Skill tool" [label="yes, even 1%"];
    "Might any skill apply?" -> "Respond (including clarifications)" [label="definitely not"];
    "Invoke Skill tool" -> "Announce: 'Using [skill] to [purpose]'";
    "Announce: 'Using [skill] to [purpose]'" -> "Has checklist?";
    "Has checklist?" -> "Create TodoWrite todo per item" [label="yes"];
    "Has checklist?" -> "Follow skill exactly" [label="no"];
    "Create TodoWrite todo per item" -> "Follow skill exactly";
}
```

## Red Flags

These thoughts mean STOP—you're rationalizing:

| Thought | Reality |
|---------|---------|
| "This is just a simple question" | Questions are tasks. Check for skills. |
| "I need more context first" | Skill check comes BEFORE clarifying questions. |
| "Let me explore the codebase first" | Skills tell you HOW to explore. Check first. |
| "I can check git/files quickly" | Files lack conversation context. Check for skills. |
| "Let me gather information first" | Skills tell you HOW to gather information. |
| "This doesn't need a formal skill" | If a skill exists, use it. |
| "I remember this skill" | Skills evolve. Read current version. |
| "This doesn't count as a task" | Action = task. Check for skills. |
| "The skill is overkill" | Simple things become complex. Use it. |
| "I'll just do this one thing first" | Check BEFORE doing anything. |
| "This feels productive" | Undisciplined action wastes time. Skills prevent this. |
| "I know what that means" | Knowing the concept ≠ using the skill. Invoke it. |

## Skill Priority

When multiple skills could apply, use this order:

1. **Process skills first** (brainstorming, debugging) - these determine HOW to approach the task
2. **Implementation skills second** (frontend-design, mcp-builder) - these guide execution

"Let's build X" → brainstorming first, then implementation skills.
"Fix this bug" → debugging first, then domain-specific skills.

## Skill Types

**Rigid** (TDD, debugging): Follow exactly. Don't adapt away discipline.

**Flexible** (patterns): Adapt principles to context.

The skill itself tells you which.

## User Instructions

Instructions say WHAT, not HOW. "Add X" or "Fix Y" doesn't mean skip workflows.

exec
/bin/zsh -lc 'pwd && git status --short && git remote -v' in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
/Users/Zhuanz/20260408 AI StructureAnalysis
?? reports/codex_tool_reports/batch_a_r2_pr24_pr25.md
origin	https://github.com/kogamishinyajerry-ops/ai-structure-analysis.git (fetch)
origin	https://github.com/kogamishinyajerry-ops/ai-structure-analysis.git (push)

codex
Using `gsd-code-review` for correctness-focused review discipline. The repo is clean apart from an unrelated untracked report file, so I’ll inspect `#24` first, then `#25`, and check whether the claimed R2 fixes actually close the prior HIGHs without opening new issues.
  → Inspect PR #24 metadata, diff, and touched files; verify the two R1 HIGH fixes and look for new HIGH/MEDIUM issues
  • Inspect PR #25 metadata, diff, and touched files; verify the three R1 HIGH fixes and look for new HIGH/MEDIUM issues
  • Compare both PRs’ self-pass-rate claims against actual extraction/calibration behavior and produce verdicts with line-cited findings
exec
/bin/zsh -lc 'gh pr view 25 --json number,title,state,isDraft,baseRefName,headRefName,mergeStateStatus,body,files,commits' in /Users/Zhuanz/20260408 AI StructureAnalysis
exec
/bin/zsh -lc 'gh pr view 24 --json number,title,state,isDraft,baseRefName,headRefName,mergeStateStatus,body,files,commits' in /Users/Zhuanz/20260408 AI StructureAnalysis
exec
/bin/zsh -lc 'gh pr diff 24' in /Users/Zhuanz/20260408 AI StructureAnalysis
exec
/bin/zsh -lc 'gh pr diff 25' in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 768ms:
diff --git a/docs/adr/ADR-012-calibration-cap-for-t1-self-pass-rate.md b/docs/adr/ADR-012-calibration-cap-for-t1-self-pass-rate.md
new file mode 100644
index 0000000..c5fd350
--- /dev/null
+++ b/docs/adr/ADR-012-calibration-cap-for-t1-self-pass-rate.md
@@ -0,0 +1,132 @@
+# ADR-012: Calibration Cap for T1 Self-Pass-Rate
+
+- **Status:** Accepted
+- **Decider:** T0 / Opus 4.7 Architecture Gate (CFDJerry) per AR-2026-04-25-001
+- **Date:** 2026-04-25
+- **Supersedes:** RETRO-V61-001 §`external_gate_self_estimated_pass_rate` honor-system discipline (replaced for AI-Structure-FEA; other projects still under V61 may retain the honor-system version)
+- **Related:** ADR-011 (parent), ADR-013 (branch protection — sibling, lands separately), DEC-T0-2026-04-25-001 (Notion record)
+- **Branch:** `feature/AI-FEA-ADR-012-calibration-cap`
+
+---
+
+## Context
+
+ADR-011 ratified RETRO-V61-001's honor-system: T1 writes a self-pass-rate per PR; ≤70% triggers pre-merge Codex; high estimates that fail are retro-debited next cycle. Session 2026-04-25 produced empirical evidence that this honor-system fails:
+
+| PR | T1 self-estimate | Codex R1 actual outcome |
+|---|---|---|
+| #20 revert | 95% | CHANGES_REQUIRED · 1 BLOCKER (direction inversion) |
+| #18 FF-02 | 95% | CHANGES_REQUIRED · 1 HIGH (over-claim + unflagged prescription) |
+| #19 FF-05 | 95% | CHANGES_REQUIRED · 1 HIGH (stale post-merge state) |
+| #21 chore | 90% | CHANGES_REQUIRED · 1 HIGH (open-PRs underreport) |
+| #22 FF-06 | 80% | CHANGES_REQUIRED · 1 BLOCKER (rename/delete bypass) |
+
+Empirical R1-pass-rate: **0/5 = 0%**. T1 self-estimates were systematically wrong by 80-95 percentage points each, *across the same session*. T0's diagnostic in AR-2026-04-25-001 §1: "this is not noise; it is the predictable failure mode of any honor-system metric where the rater and the rated party are the same agent in the same context window." The discipline cannot self-correct mid-session — T1 wrote "95%" five times in a row while Codex was actively contradicting it.
+
+The retro-debit lag (next-cycle correction) is also too slow: by the time the retro lands, multiple PRs have already shipped with mis-calibrated confidence, and T1's session-end summary inherits the over-confidence as part of its training signal.
+
+## Decision
+
+Self-pass-rate becomes a **mechanically-derived ceiling** based on a rolling window of the last 5 PRs' Codex Round 1 outcomes. T1 cannot type a number; T1 reads a number computed by `scripts/compute_calibration_cap.py` from the append-only state file `reports/calibration_state.json`.
+
+### Formula (canonical, ratified in AR-2026-04-25-001 §1)
+
+```
+Rolling window:  last 5 PRs to main (≥ ADR-011 baseline; pre-ADR PRs excluded)
+Outcome canon:   APPROVE | APPROVE_WITH_NITS | CHANGES_REQUIRED | BLOCKER
+                 (NITS counts as APPROVE; CR/BLOCKER count as CHANGES_REQUIRED)
+
+Base ceiling (per next PR):
+  0 of last 5 = CR  → 95%  · honor system   · pre-merge Codex OPTIONAL
+  1-2 of last 5     → 80%  · pre-merge Codex RECOMMENDED
+  3-4 of last 5     → 50%  · pre-merge Codex MANDATORY
+  5 of last 5       → 30%  · pre-merge Codex MANDATORY · BLOCKING
+
+Recovery (override on top of base):
+  2 consecutive R1=APPROVE  → ceiling steps up one rung from base
+  3 consecutive R1=APPROVE  → ceiling returns to 95%
+```
+
+Rung ladder is `30 → 50 → 80 → 95` (`step_up` saturates at 95).
+
+### Codex gate derivation from final ceiling
+
+| Ceiling | Mandatory Codex pre-merge | Blocking |
+|---|---|---|
+| 30 | yes | **yes** (no T1 self-merge; needs t0-approved or external review) |
+| 50 | yes | no |
+| 80 | no (recommended) | no |
+| 95 | no (optional) | no |
+
+Independently of the ceiling, ADR-011 §T2 amendments (M1-M5 triggers — governance text, sign/direction math, HF compliance claims, governance→enforcement translations, and any PR opened while ceiling ≤ 50%) may still mandate Codex review.
+
+## Implementation contract
+
+**Sources of truth:**
+
+- `reports/calibration_state.json` — append-only state file, schema v1. Each entry: `{pr, sha, title, merged_at, r1_outcome, r1_severity, r1_review_report, notes}`. Authoritative for the formula's input. **Entries are sorted by `merged_at` (ISO 8601) at read time** — PR-number is NOT a reliable proxy for merge order (the bootstrap state already contains a counterexample: PR #20 merged before #18 and #19 on 2026-04-25).
+- `scripts/compute_calibration_cap.py` — pure function over the state file. Outputs `{ceiling, mandatory_codex, blocking, basis, entry_count, gate_label}` JSON. Has `--human` and `--check <claimed-ceiling>` modes. **Fails closed**: missing state file, schema-version mismatch, duplicate `pr`, missing `merged_at`, or unknown `r1_outcome` all produce a hard `CalibrationStateError` and exit 1 — never a silent fail-open.
+- `tests/test_compute_calibration_cap.py` — unit tests covering each rung, recovery transitions, BLOCKER/NITS canon, the merged_at-vs-PR-number counterexample regression, and every adversarial state-validation path.
+
+**T1 invocation surface:**
+
+- At session-start, T1 runs `python3 scripts/compute_calibration_cap.py --human` and renders the result in the `MODEL COMPLIANCE CHECK` block of every reply that initiates work.
+- The PR template (in `.github/PULL_REQUEST_TEMPLATE.md` once branch protection lands per ADR-013) prefills the `Self-pass-rate` field by calling the script. The field is **read-only** to T1.
+- A CI check (in ADR-013's workflow batch) calls `--check <claimed>` to fail PRs whose body claims a higher ceiling than computed.
+
+**State maintenance:**
+
+After each PR merges, the maintainer (T1 or T0) appends a new entry to `reports/calibration_state.json` with the actual R1 outcome. Entry SHOULD be added in the same PR as housekeeping or in the next PR's first commit. State updates do NOT themselves count as PRs in the formula — the formula counts PRs that touched code/governance content.
+
+## Bootstrap state (initial 5 entries)
+
+Per AR-2026-04-25-001 §1, initialize from PRs #18-#22 (PR #17 excluded as the ADR-011 baseline establishment). All 5 are `CHANGES_REQUIRED` per session 2026-04-25 record:
+
+| PR | SHA | R1 outcome | R1 severity |
+|---|---|---|---|
+| #18 | `77e6813` | CHANGES_REQUIRED | 1 HIGH + 3 MEDIUM |
+| #19 | `4a64cfd` | CHANGES_REQUIRED | 1 HIGH + 1 MEDIUM |
+| #20 | `9362f6d` | CHANGES_REQUIRED | 1 BLOCKER + 2 SHOULD_FIX |
+| #21 | `2bbf0f1` | CHANGES_REQUIRED | 1 HIGH |
+| #22 | `ac98fc3` | CHANGES_REQUIRED | 1 BLOCKER + 2 SHOULD_FIX |
+
+Resulting ceiling at ADR-012 land: **30%, MANDATORY pre-merge Codex, BLOCKING**.
+
+This means ADR-012 itself (this PR), ADR-013, and ADR-011 amendments all open under the 30% blocking regime. That is exactly correct given the empirical record.
+
+## Recovery path
+
+To return to the 95% honor-system regime from the bootstrap 30%, T1 needs:
+
+- **One** R1=APPROVE PR after this one → state `4 of last 5 = CR` → ceiling 50, MANDATORY but not blocking
+- **Two consecutive** R1=APPROVE → recovery clause overrides base → ceiling steps from `4 of 5 → base 50` to step-up `80`, RECOMMENDED only
+- **Three consecutive** R1=APPROVE → recovery clause resets ceiling to 95, OPTIONAL
+
+In other words: three clean PRs in a row, no R1 BLOCKER/HIGH, restores honor-system. The formula is forgiving but evidence-grounded.
+
+## Consequences
+
+**Intended:**
+
+- T1's self-rated confidence becomes irrelevant to ceiling derivation. Calibration error cannot affect the gate.
+- Ceiling = leading indicator (predicts likely R1 outcome) rather than RETRO-V61-001's lagging indicator (corrects after the fact).
+- Recovery is mechanical and fast (3 clean PRs ≈ 1-2 sessions of clean work), so T1 isn't permanently penalized for one bad session.
+- Bootstrap 30%/BLOCKING for the immediate next 3 PRs (ADR-012, ADR-013, ADR-011 amendment) is exactly what the empirical record warrants.
+
+**Acknowledged:**
+
+- The recovery thresholds (2 → step up, 3 → reset) are reasonable but not empirically grounded yet (T0 self-rated 88% on this clause). Revisit after 10 more PRs of post-ADR-012 data; either ratify or tighten via ADR-012 amendment.
+- The formula assumes Codex R1 quality is stable. If Codex itself becomes lenient over time (NITS-with-ulterior-motive or APPROVE-without-checking), the formula's signal degrades. This is a Codex-quality concern, not an ADR-012 concern, but should be tracked.
+- "Last 5" is small enough that one anomalous session can flip the ceiling. A larger window (10 or 20) is statistically more robust but slower to respond. T0's choice of 5 prioritizes responsiveness; revisit if ceiling thrashes after the bootstrap recovery completes.
+- Cross-project portability: the formula assumes Codex is the de facto reviewer (per ADR-011 §T2). Projects without Codex must adapt the canon (e.g., human review verdict).
+
+**Out of scope:**
+
+- ADR-013 (branch protection) is the surface that *enforces* the gate (a 30%-blocking ceiling means nothing if T1 can self-merge anyway). ADR-012 is the calibration math; ADR-013 is the access-control wrapper. They are sibling ADRs landed in the same session under the same T0 verdict.
+- Codex role rewording (anti-shenanigans backstop, M1-M5 triggers) is part of the ADR-011 amendment PR, not ADR-012.
+
+## Open follow-ups
+
+- Add CI step calling `compute_calibration_cap.py --check` against PR body's claim, after `.github/PULL_REQUEST_TEMPLATE.md` lands (in ADR-013's batch).
+- After 10 post-ADR-012 PRs, write a calibration-stability retro: confirm or amend recovery thresholds based on empirical thrashing rate.
+- Notion control plane: DEC-T0-2026-04-25-001 captures this ADR; future ADR-012 amendments must update the same DEC entry.
diff --git a/reports/calibration_state.json b/reports/calibration_state.json
new file mode 100644
index 0000000..edcb47a
--- /dev/null
+++ b/reports/calibration_state.json
@@ -0,0 +1,80 @@
+{
+  "schema_version": 1,
+  "established_by": "ADR-012 / AR-2026-04-25-001 / DEC-T0-2026-04-25-001",
+  "doc": "Append-only state for T1 calibration cap. Entries are ordered by `merged_at` (ISO 8601) at read time — PR-number is NOT a reliable proxy for merge order (PR #20 merged before #18 and #19 on 2026-04-25). Last 5 entries determine the ceiling per AR-2026-04-25-001 §1 formula. Pre-ADR-011-baseline PRs excluded; PR #17 (the ADR-011 establishment) is also excluded as bootstrap baseline per T0 verdict. R2 contract (post Codex R1, 2026-04-26): the load path FAILS CLOSED on missing file, schema_version mismatch, duplicate `pr`, missing `merged_at`, or unknown `r1_outcome`.",
+  "outcome_canon": "APPROVE | APPROVE_WITH_NITS | CHANGES_REQUIRED | BLOCKER (NITS counts as APPROVE; CR/BLOCKER count as CHANGES_REQUIRED)",
+  "entries": [
+    {
+      "pr": 18,
+      "sha": "77e6813",
+      "title": "[FF-02] FailurePattern attribution for GS-001/002/003",
+      "merged_at": "2026-04-25T08:53:09Z",
+      "r1_outcome": "CHANGES_REQUIRED",
+      "r1_severity": "1 HIGH + 3 MEDIUM",
+      "r1_review_report": "reports/codex_tool_reports/ff02_r1_review.md",
+      "notes": "Over-claim/prescription, gs_artifact_pin placeholder, HF3 cite inconsistency, README severity scope"
+    },
+    {
+      "pr": 19,
+      "sha": "4a64cfd",
+      "title": "[FF-05] Seed .planning/STATE.md as repo-side execution snapshot",
+      "merged_at": "2026-04-25T08:56:46Z",
+      "r1_outcome": "CHANGES_REQUIRED",
+      "r1_severity": "1 HIGH + 1 MEDIUM",
+      "r1_review_report": "reports/codex_tool_reports/ff05_r1_review.md",
+      "notes": "STATE.md still pre-push state (FF-01/FF-02 listed as pending); invented ADR-012/013 references"
+    },
+    {
+      "pr": 20,
+      "sha": "9362f6d",
+      "title": "Revert direct-push 815945c, preserve portable-path fixes",
+      "merged_at": "2026-04-25T08:33:51Z",
+      "r1_outcome": "CHANGES_REQUIRED",
+      "r1_severity": "1 BLOCKER + 2 SHOULD_FIX",
+      "r1_review_report": "reports/codex_tool_reports/revert_815945c_r1_review.md",
+      "notes": "Revert direction inversion (re-introduced /Users/Zhuanz/ paths); commit message factual error; CI claim overstated"
+    },
+    {
+      "pr": 21,
+      "sha": "2bbf0f1",
+      "title": "chore: post-merge cleanup — STATE.md + Codex review archive",
+      "merged_at": "2026-04-25T10:30:14Z",
+      "r1_outcome": "CHANGES_REQUIRED",
+      "r1_severity": "1 HIGH",
+      "r1_review_report": null,
+      "r1_review_report_pending_archive": true,
+      "notes": "STATE.md Active branches/Open PRs sections underreported (P1-* PRs #11-#16 missing); R1 review still in /tmp/, awaits next housekeeping cycle"
+    },
+    {
+      "pr": 22,
+      "sha": "ac98fc3",
+      "title": "[FF-06] pre-commit path-guard for HF1 forbidden zone",
+      "merged_at": "2026-04-25T10:43:55Z",
+      "r1_outcome": "CHANGES_REQUIRED",
+      "r1_severity": "1 BLOCKER + 2 SHOULD_FIX",
+      "r1_review_report": null,
+      "r1_review_report_pending_archive": true,
+      "notes": "pre-commit pass_filenames misses rename old-paths and deletes (silent HF1 bypass); HF1.6 over-blocks Makefile other targets; override audit trail unenforceable"
+    },
+    {
+      "pr": 23,
+      "sha": "e53b0f7",
+      "title": "[ADR-011] T0 amendments AR-2026-04-25-001 (T2 + HF1 + HF2 + numbering)",
+      "merged_at": "2026-04-25T12:06:52Z",
+      "r1_outcome": "CHANGES_REQUIRED",
+      "r1_severity": "3 BLOCKER + 1 SHOULD_FIX",
+      "r1_review_report": null,
+      "r1_review_report_pending_archive": true,
+      "notes": "ADR-011 amendments PR — Codex R1 returned 3 BLOCKER + 1 SHOULD_FIX, fixed in commit e96904d, then merged after CI green. R1 review report still pending archive into reports/codex_tool_reports/."
+    }
+  ],
+  "computed_at_bootstrap": {
+    "last_5_cr_count": 5,
+    "trailing_approve_count": 0,
+    "base_ceiling": 30,
+    "final_ceiling": 30,
+    "mandatory_codex": true,
+    "blocking": true,
+    "basis": "5 of last 5 = CHANGES_REQUIRED → ceiling 30%"
+  }
+}
diff --git a/scripts/compute_calibration_cap.py b/scripts/compute_calibration_cap.py
new file mode 100644
index 0000000..e77f5df
--- /dev/null
+++ b/scripts/compute_calibration_cap.py
@@ -0,0 +1,322 @@
+#!/usr/bin/env python3
+"""Calibration cap computation for T1 self-pass-rate (ADR-012 · AR-2026-04-25-001).
+
+Replaces RETRO-V61-001's per-PR honesty discipline with a mechanical formula
+derived from the rolling window of the last 5 PRs' Codex Round 1 outcomes.
+T1 cannot self-rate; T1 reads the ceiling. PR template prefills the
+self-pass field by calling this script; the field is read-only to T1.
+
+Formula (canonical, ratified in AR-2026-04-25-001 §1):
+
+    Rolling window:  last 5 PRs to main, ordered by `merged_at` (ISO 8601).
+                     ≥ ADR-011 baseline; pre-ADR excluded.
+    Outcome canon:   APPROVE | APPROVE_WITH_NITS | CHANGES_REQUIRED | BLOCKER
+                     (NITS counts as APPROVE; CR/BLOCKER count as CHANGES_REQUIRED)
+
+    Base ceiling (per next PR):
+      0 of last 5 = CR  → 95%  · honor system   · pre-merge Codex OPTIONAL
+      1-2 of last 5     → 80%  · pre-merge Codex RECOMMENDED
+      3-4 of last 5     → 50%  · pre-merge Codex MANDATORY
+      5 of last 5       → 30%  · pre-merge Codex MANDATORY · BLOCKING
+
+    Recovery (override):
+      2 consecutive R1=APPROVE  → ceiling steps up one rung from base
+      3 consecutive R1=APPROVE  → ceiling returns to 95%
+
+Invocations:
+    python3 scripts/compute_calibration_cap.py
+        emits JSON to stdout (ceiling, mandatory_codex, blocking, basis, entry_count)
+    python3 scripts/compute_calibration_cap.py --human
+        emits human-readable summary to stdout
+    python3 scripts/compute_calibration_cap.py --check <CEILING>
+        exits 1 if claimed CEILING > computed ceiling (PR-template / CI use)
+
+State source: reports/calibration_state.json (append-only, hard-validated).
+The script is a pure function over its contents and FAILS CLOSED on any
+shape violation: missing file, schema mismatch, duplicate PR, missing
+merged_at, unknown outcome — all exit non-zero with a clear stderr message.
+
+Honesty caveat (T0 self-rated 88% on ratification): the recovery thresholds
+(2 → step up, 3 → reset) are reasonable but not empirically grounded yet;
+revisit after 10 more PRs of post-ADR-012 data.
+
+R2 changes (post Codex R1 CHANGES_REQUIRED, 2026-04-26):
+  * load_state() now sorts by merged_at, not PR number — the repo already
+    has a counterexample (PR #20 merged before #18 and #19).
+  * Missing/malformed state file is now a hard error (was: returned [] →
+    fail-open at 95%/OPTIONAL).
+  * schema_version, duplicate PRs, missing merged_at, and unknown outcomes
+    are all hard-validated.
+"""
+
+from __future__ import annotations
+
+import argparse
+import json
+import sys
+from dataclasses import dataclass
+from pathlib import Path
+
+# Canonical: NITS counts as APPROVE; everything else (CR, BLOCKER) counts as CR.
+APPROVE_OUTCOMES = frozenset({"APPROVE", "APPROVE_WITH_NITS"})
+CANONICAL_OUTCOMES = frozenset({"APPROVE", "APPROVE_WITH_NITS", "CHANGES_REQUIRED", "BLOCKER"})
+
+# Rung ladder, low → high. Recovery moves one index up.
+RUNGS: tuple[int, ...] = (30, 50, 80, 95)
+
+# Schema version this script supports. Bump only with a corresponding ADR.
+SUPPORTED_SCHEMA_VERSION = 1
+
+
+class CalibrationStateError(Exception):
+    """Hard error reading or validating the calibration state file."""
+
+
+@dataclass(frozen=True)
+class CalibrationResult:
+    ceiling: int
+    mandatory_codex: bool
+    blocking: bool
+    basis: str
+    entry_count: int
+
+
+def step_up(ceiling: int) -> int:
+    """Move ceiling one rung up (saturate at 95)."""
+    if ceiling not in RUNGS:
+        raise ValueError(f"unknown ceiling rung: {ceiling}")
+    idx = RUNGS.index(ceiling)
+    return RUNGS[min(idx + 1, len(RUNGS) - 1)]
+
+
+def base_ceiling_from_cr_count(cr_count: int) -> int:
+    """Map count of CHANGES_REQUIRED in last 5 entries to base ceiling.
+
+    Per AR-2026-04-25-001 §1.
+    """
+    if cr_count < 0:
+        raise ValueError(f"cr_count must be >= 0, got {cr_count}")
+    if cr_count == 0:
+        return 95
+    if cr_count <= 2:
+        return 80
+    if cr_count <= 4:
+        return 50
+    return 30
+
+
+def trailing_approve_count(outcomes: list[str]) -> int:
+    """Count consecutive APPROVE/NITS at the END of the list (most recent first)."""
+    n = 0
+    for o in reversed(outcomes):
+        if o in APPROVE_OUTCOMES:
+            n += 1
+        else:
+            break
+    return n
+
+
+def compute_calibration(outcomes: list[str]) -> CalibrationResult:
+    """Compute calibration ceiling from a chronologically-ordered list of R1 outcomes."""
+    last5 = outcomes[-5:]
+    cr_count = sum(1 for o in last5 if o not in APPROVE_OUTCOMES)
+    base = base_ceiling_from_cr_count(cr_count)
+    trailing = trailing_approve_count(outcomes)
+
+    if trailing >= 3:
+        ceiling = 95
+        basis = "3+ trailing APPROVE → ceiling reset to 95% (recovery)"
+    elif trailing >= 2:
+        stepped = step_up(base)
+        ceiling = stepped
+        basis = (
+            f"{cr_count} of last 5 = CHANGES_REQUIRED (base {base}%) + "
+            f"2 trailing APPROVE → step up to {ceiling}%"
+        )
+    else:
+        ceiling = base
+        basis = f"{cr_count} of last 5 = CHANGES_REQUIRED → ceiling {ceiling}%"
+
+    # Codex gate derivation from final ceiling
+    if ceiling <= 30:
+        mandatory_codex = True
+        blocking = True
+    elif ceiling <= 50:
+        mandatory_codex = True
+        blocking = False
+    else:
+        # 80 = recommended; 95 = optional. Both are "not mandatory" for the
+        # ceiling itself; M1-M5 triggers in ADR-011 §T2 may still mandate
+        # Codex independently of the ceiling.
+        mandatory_codex = False
+        blocking = False
+
+    return CalibrationResult(
+        ceiling=ceiling,
+        mandatory_codex=mandatory_codex,
+        blocking=blocking,
+        basis=basis,
+        entry_count=len(outcomes),
+    )
+
+
+def _validate_state_dict(data: object) -> list[dict]:
+    """Hard-validate a parsed calibration_state.json document.
+
+    Raises CalibrationStateError on any shape violation. Returns the
+    validated entries list (each entry guaranteed to have pr/merged_at/
+    r1_outcome of the right type).
+    """
+    if not isinstance(data, dict):
+        raise CalibrationStateError("state file root must be a JSON object")
+
+    schema_version = data.get("schema_version")
+    if schema_version != SUPPORTED_SCHEMA_VERSION:
+        raise CalibrationStateError(
+            f"schema_version must be {SUPPORTED_SCHEMA_VERSION}, got {schema_version!r}"
+        )
+
+    entries = data.get("entries")
+    if not isinstance(entries, list):
+        raise CalibrationStateError("'entries' must be a list")
+
+    seen_prs: set[int] = set()
+    for i, e in enumerate(entries):
+        if not isinstance(e, dict):
+            raise CalibrationStateError(f"entries[{i}] must be a JSON object")
+
+        pr = e.get("pr")
+        if not isinstance(pr, int) or pr <= 0:
+            raise CalibrationStateError(
+                f"entries[{i}].pr must be a positive int, got {pr!r}"
+            )
+        if pr in seen_prs:
+            raise CalibrationStateError(
+                f"entries[{i}].pr={pr} is a duplicate of an earlier entry"
+            )
+        seen_prs.add(pr)
+
+        merged_at = e.get("merged_at")
+        if not isinstance(merged_at, str) or not merged_at:
+            raise CalibrationStateError(
+                f"entries[{i}].merged_at (ISO 8601 string) is required"
+            )
+
+        outcome = e.get("r1_outcome")
+        if outcome not in CANONICAL_OUTCOMES:
+            raise CalibrationStateError(
+                f"entries[{i}].r1_outcome must be one of "
+                f"{sorted(CANONICAL_OUTCOMES)}, got {outcome!r}"
+            )
+
+    return entries
+
+
+def load_state(state_path: Path) -> list[str]:
+    """Read calibration_state.json and return chronologically-ordered R1 outcomes.
+
+    Raises CalibrationStateError on missing file, invalid JSON, schema-version
+    mismatch, duplicate PR rows, missing merged_at, or unknown outcomes.
+
+    Sorting is by `merged_at` ISO 8601 timestamp (lexicographic == chronological
+    for ISO 8601). This is the fix for Codex R1 HIGH #1: the previous
+    implementation sorted by PR number, but the repo already contains a
+    counterexample (PR #20 merged_at 2026-04-25T08:33:51Z is BEFORE
+    PR #18 at 08:53:09Z).
+    """
+    if not state_path.exists():
+        raise CalibrationStateError(
+            f"calibration state file not found: {state_path}. "
+            "This file is required; it must be initialised by the ADR-012 "
+            "establishing PR and append-only thereafter."
+        )
+
+    try:
+        with state_path.open() as f:
+            data = json.load(f)
+    except json.JSONDecodeError as e:
+        raise CalibrationStateError(
+            f"calibration state file is not valid JSON: {state_path}: {e}"
+        ) from e
+
+    entries = _validate_state_dict(data)
+
+    # Sort by merged_at (ISO 8601 lexicographic == chronological).
+    entries_sorted = sorted(entries, key=lambda e: e["merged_at"])
+    return [e["r1_outcome"] for e in entries_sorted]
+
+
+def gate_label(result: CalibrationResult) -> str:
+    if result.blocking:
+        return "BLOCKING"
+    if result.mandatory_codex:
+        return "MANDATORY"
+    if result.ceiling <= 80:
+        return "RECOMMENDED"
+    return "OPTIONAL"
+
+
+def main(argv: list[str]) -> int:
+    default_state = Path(__file__).resolve().parent.parent / "reports" / "calibration_state.json"
+    parser = argparse.ArgumentParser(
+        description="Compute T1 calibration ceiling per ADR-012 / AR-2026-04-25-001."
+    )
+    parser.add_argument(
+        "--human",
+        action="store_true",
+        help="emit human-readable summary instead of JSON",
+    )
+    parser.add_argument(
+        "--check",
+        type=int,
+        metavar="CEILING",
+        help="exit 1 if claimed CEILING exceeds the computed ceiling",
+    )
+    parser.add_argument(
+        "--state",
+        type=Path,
+        default=default_state,
+        help=f"path to calibration_state.json (default: {default_state})",
+    )
+    args = parser.parse_args(argv[1:])
+
+    try:
+        outcomes = load_state(args.state)
+    except CalibrationStateError as e:
+        sys.stderr.write(f"calibration state error: {e}\n")
+        return 1
+
+    result = compute_calibration(outcomes)
+
+    if args.check is not None:
+        if args.check > result.ceiling:
+            sys.stderr.write(
+                f"calibration check FAILED: claimed {args.check}% exceeds "
+                f"computed ceiling {result.ceiling}%\n"
+                f"  basis: {result.basis}\n"
+                f"  Codex gate: {gate_label(result)}\n"
+            )
+            return 1
+        return 0
+
+    if args.human:
+        print(f"T1 calibration ceiling : {result.ceiling}%")
+        print(f"Codex pre-merge gate   : {gate_label(result)}")
+        print(f"Basis                  : {result.basis}")
+        print(f"State entries          : {result.entry_count} (last 5 used)")
+    else:
+        out = {
+            "ceiling": result.ceiling,
+            "mandatory_codex": result.mandatory_codex,
+            "blocking": result.blocking,
+            "basis": result.basis,
+            "entry_count": result.entry_count,
+            "gate_label": gate_label(result),
+        }
+        print(json.dumps(out, ensure_ascii=False))
+
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main(sys.argv))
diff --git a/tests/test_compute_calibration_cap.py b/tests/test_compute_calibration_cap.py
new file mode 100644
index 0000000..a3d995e
--- /dev/null
+++ b/tests/test_compute_calibration_cap.py
@@ -0,0 +1,530 @@
+"""Tests for scripts/compute_calibration_cap.py (ADR-012).
+
+R2 update (2026-04-26, post Codex R1 CHANGES_REQUIRED):
+  * load_state now sorts by merged_at, not PR number — see
+    `test_load_state_sorts_by_merged_at_not_pr_counterexample` for the
+    Codex-cited regression case.
+  * Missing/malformed state is now a hard CalibrationStateError; see
+    the "adversarial state validation" block below.
+"""
+
+from __future__ import annotations
+
+import json
+import sys
+from pathlib import Path
+
+import pytest
+
+_REPO_ROOT = Path(__file__).resolve().parent.parent
+_SCRIPTS_DIR = _REPO_ROOT / "scripts"
+if str(_SCRIPTS_DIR) not in sys.path:
+    sys.path.insert(0, str(_SCRIPTS_DIR))
+
+
+def _load_calc():
+    import compute_calibration_cap  # type: ignore[import-not-found]
+
+    return compute_calibration_cap
+
+
+@pytest.fixture(scope="module")
+def calc():
+    return _load_calc()
+
+
+def _entry(pr: int, merged_at: str, outcome: str = "CHANGES_REQUIRED") -> dict:
+    """Build a valid entry dict for tests."""
+    return {"pr": pr, "merged_at": merged_at, "r1_outcome": outcome}
+
+
+def _write_state(tmp_path: Path, entries: list[dict], schema_version: int = 1) -> Path:
+    state_path = tmp_path / "calibration_state.json"
+    state_path.write_text(json.dumps({"schema_version": schema_version, "entries": entries}))
+    return state_path
+
+
+# ---------------------------------------------------------------------------
+# step_up
+# ---------------------------------------------------------------------------
+
+
+@pytest.mark.parametrize(
+    "input_ceiling,expected",
+    [(30, 50), (50, 80), (80, 95), (95, 95)],
+)
+def test_step_up_each_rung(calc, input_ceiling, expected):
+    assert calc.step_up(input_ceiling) == expected
+
+
+def test_step_up_rejects_unknown_ceiling(calc):
+    with pytest.raises(ValueError, match="unknown ceiling rung"):
+        calc.step_up(42)
+
+
+# ---------------------------------------------------------------------------
+# base_ceiling_from_cr_count
+# ---------------------------------------------------------------------------
+
+
+@pytest.mark.parametrize(
+    "cr_count,expected",
+    [
+        (0, 95),
+        (1, 80),
+        (2, 80),
+        (3, 50),
+        (4, 50),
+        (5, 30),
+    ],
+)
+def test_base_ceiling_each_count(calc, cr_count, expected):
+    assert calc.base_ceiling_from_cr_count(cr_count) == expected
+
+
+def test_base_ceiling_rejects_negative(calc):
+    with pytest.raises(ValueError, match="cr_count must be >= 0"):
+        calc.base_ceiling_from_cr_count(-1)
+
+
+# ---------------------------------------------------------------------------
+# trailing_approve_count
+# ---------------------------------------------------------------------------
+
+
+def test_trailing_approve_empty(calc):
+    assert calc.trailing_approve_count([]) == 0
+
+
+def test_trailing_approve_no_trailing(calc):
+    assert calc.trailing_approve_count(["APPROVE", "CHANGES_REQUIRED"]) == 0
+
+
+def test_trailing_approve_single(calc):
+    assert calc.trailing_approve_count(["CHANGES_REQUIRED", "APPROVE"]) == 1
+
+
+def test_trailing_approve_two(calc):
+    assert calc.trailing_approve_count(["CHANGES_REQUIRED", "APPROVE", "APPROVE"]) == 2
+
+
+def test_trailing_approve_three(calc):
+    assert calc.trailing_approve_count(["CHANGES_REQUIRED", "APPROVE", "APPROVE", "APPROVE"]) == 3
+
+
+def test_trailing_approve_all_approve(calc):
+    assert calc.trailing_approve_count(["APPROVE"] * 5) == 5
+
+
+def test_trailing_approve_nits_counts_as_approve(calc):
+    assert calc.trailing_approve_count(["CHANGES_REQUIRED", "APPROVE_WITH_NITS", "APPROVE"]) == 2
+
+
+def test_trailing_approve_blocker_breaks(calc):
+    assert calc.trailing_approve_count(["APPROVE", "BLOCKER", "APPROVE"]) == 1
+
+
+# ---------------------------------------------------------------------------
+# compute_calibration — bootstrap and steady-state scenarios
+# ---------------------------------------------------------------------------
+
+
+def test_compute_bootstrap_5_cr_yields_30_blocking(calc):
+    """Session 2026-04-25 bootstrap: 5/5 CHANGES_REQUIRED → ceiling 30, blocking."""
+    r = calc.compute_calibration(["CHANGES_REQUIRED"] * 5)
+    assert r.ceiling == 30
+    assert r.mandatory_codex is True
+    assert r.blocking is True
+    assert "5 of last 5" in r.basis
+
+
+def test_compute_ideal_5_approve_yields_95_optional(calc):
+    r = calc.compute_calibration(["APPROVE"] * 5)
+    assert r.ceiling == 95
+    assert r.mandatory_codex is False
+    assert r.blocking is False
+
+
+def test_compute_two_cr_three_approve_recovery_step_up(calc):
+    """3-trailing-APPROVE recovery overrides base ceiling to 95."""
+    outcomes = ["CHANGES_REQUIRED", "CHANGES_REQUIRED", "APPROVE", "APPROVE", "APPROVE"]
+    r = calc.compute_calibration(outcomes)
+    assert r.ceiling == 95
+    assert "recovery" in r.basis
+
+
+def test_compute_three_cr_two_approve_step_up_one_rung(calc):
+    """2-trailing-APPROVE recovery moves base 50 → 80."""
+    outcomes = ["CHANGES_REQUIRED", "CHANGES_REQUIRED", "CHANGES_REQUIRED", "APPROVE", "APPROVE"]
+    r = calc.compute_calibration(outcomes)
+    assert r.ceiling == 80
+    assert r.mandatory_codex is False
+
+
+def test_compute_four_cr_one_approve_no_recovery(calc):
+    """1-trailing-APPROVE is below 2 threshold; ceiling stays at base."""
+    outcomes = ["CHANGES_REQUIRED"] * 4 + ["APPROVE"]
+    r = calc.compute_calibration(outcomes)
+    assert r.ceiling == 50
+    assert r.mandatory_codex is True
+    assert r.blocking is False
+
+
+def test_compute_more_than_5_uses_only_last_5(calc):
+    """Window is last 5 entries; older entries do not affect base count."""
+    outcomes = ["APPROVE", "APPROVE"] + ["CHANGES_REQUIRED"] * 5
+    r = calc.compute_calibration(outcomes)
+    assert r.ceiling == 30
+
+
+def test_compute_trailing_approve_uses_full_history(calc):
+    """Trailing-APPROVE count uses the entire history, not just last 5."""
+    outcomes = ["APPROVE", "APPROVE", "APPROVE"] + ["CHANGES_REQUIRED"] * 5
+    r = calc.compute_calibration(outcomes)
+    assert r.ceiling == 30
+
+
+def test_compute_empty_history_yields_95(calc):
+    """No PRs yet → 0 of last 5 = CR → ceiling 95.
+
+    Note: this only tests the pure-function compute_calibration; the load_state
+    side now hard-errors on a MISSING file, so the empty-history branch is
+    only reachable via an explicitly-empty entries list, which the establishing
+    PR must seed deliberately.
+    """
+    r = calc.compute_calibration([])
+    assert r.ceiling == 95
+    assert r.mandatory_codex is False
+    assert r.blocking is False
+
+
+def test_compute_blocker_counts_as_changes_required(calc):
+    r = calc.compute_calibration(["BLOCKER"] * 5)
+    assert r.ceiling == 30
+    assert r.blocking is True
+
+
+def test_compute_nits_counts_as_approve(calc):
+    r = calc.compute_calibration(["APPROVE_WITH_NITS"] * 5)
+    assert r.ceiling == 95
+
+
+# ---------------------------------------------------------------------------
+# load_state — happy path + chronological sort by merged_at (R2 fix HIGH 1)
+# ---------------------------------------------------------------------------
+
+
+def test_load_state_sorts_by_merged_at(calc, tmp_path):
+    """Entries must be ordered by merged_at, not file order."""
+    state_path = _write_state(
+        tmp_path,
+        [
+            _entry(22, "2026-04-25T10:43:55Z", "BLOCKER"),
+            _entry(18, "2026-04-25T08:53:09Z", "APPROVE"),
+            _entry(20, "2026-04-25T08:33:51Z", "CHANGES_REQUIRED"),
+        ],
+    )
+    outcomes = calc.load_state(state_path)
+    # merged_at order: 20 (08:33), 18 (08:53), 22 (10:43)
+    assert outcomes == ["CHANGES_REQUIRED", "APPROVE", "BLOCKER"]
+
+
+def test_load_state_sorts_by_merged_at_not_pr_counterexample(calc, tmp_path):
+    """Codex R1 HIGH #1 regression: PR #20 merged BEFORE PR #18 and #19.
+
+    With the old PR-number sort, the recovery calculation diverges. Verify
+    that sorting by merged_at gives the truly chronological sequence.
+    """
+    state_path = _write_state(
+        tmp_path,
+        [
+            _entry(18, "2026-04-25T08:53:09Z", "CHANGES_REQUIRED"),
+            _entry(19, "2026-04-25T08:56:46Z", "APPROVE"),
+            _entry(20, "2026-04-25T08:33:51Z", "APPROVE"),
+        ],
+    )
+    outcomes = calc.load_state(state_path)
+    # merged_at order: 20, 18, 19 — so sequence is APPROVE, CR, APPROVE
+    # Trailing approve = 1 (from #19), no recovery
+    assert outcomes == ["APPROVE", "CHANGES_REQUIRED", "APPROVE"]
+    r = calc.compute_calibration(outcomes)
+    # Compare with the WRONG (PR-sorted) order: would be CR, APPROVE, APPROVE
+    # which has 2 trailing APPROVE → recovery step up. The chronologically
+    # correct answer has only 1 trailing APPROVE → no recovery.
+    assert "trailing APPROVE" not in r.basis
+    assert r.ceiling == 80  # 1 of last 5 = CR → base 80, no recovery
+
+
+def test_load_state_real_file_yields_30_while_last_5_are_cr(calc):
+    """The real reports/calibration_state.json must yield 30/BLOCKING
+    as long as the last 5 R1 outcomes are CHANGES_REQUIRED."""
+    state_path = _REPO_ROOT / "reports" / "calibration_state.json"
+    outcomes = calc.load_state(state_path)
+    assert len(outcomes) >= 5
+    last_5 = outcomes[-5:]
+    if all(o in ("CHANGES_REQUIRED", "BLOCKER") for o in last_5):
+        r = calc.compute_calibration(outcomes)
+        assert r.ceiling == 30
+        assert r.blocking is True
+
+
+# ---------------------------------------------------------------------------
+# load_state — adversarial state validation (R2 fix HIGH 2)
+# ---------------------------------------------------------------------------
+
+
+def test_load_state_missing_file_is_hard_error(calc, tmp_path):
+    """R2 fix: missing state file used to fail-open at 95%/OPTIONAL."""
+    with pytest.raises(calc.CalibrationStateError, match="not found"):
+        calc.load_state(tmp_path / "definitely-missing.json")
+
+
+def test_load_state_invalid_json_is_hard_error(calc, tmp_path):
+    bad = tmp_path / "bad.json"
+    bad.write_text("{not-valid-json")
+    with pytest.raises(calc.CalibrationStateError, match="not valid JSON"):
+        calc.load_state(bad)
+
+
+def test_load_state_non_dict_root_is_hard_error(calc, tmp_path):
+    bad = tmp_path / "list_root.json"
+    bad.write_text("[1, 2, 3]")
+    with pytest.raises(calc.CalibrationStateError, match="JSON object"):
+        calc.load_state(bad)
+
+
+def test_load_state_wrong_schema_version_is_hard_error(calc, tmp_path):
+    state_path = _write_state(tmp_path, [], schema_version=999)
+    with pytest.raises(calc.CalibrationStateError, match="schema_version"):
+        calc.load_state(state_path)
+
+
+def test_load_state_missing_schema_version_is_hard_error(calc, tmp_path):
+    bad = tmp_path / "no_schema.json"
+    bad.write_text(json.dumps({"entries": []}))
+    with pytest.raises(calc.CalibrationStateError, match="schema_version"):
+        calc.load_state(bad)
+
+
+def test_load_state_entries_not_list_is_hard_error(calc, tmp_path):
+    bad = tmp_path / "bad_entries.json"
+    bad.write_text(json.dumps({"schema_version": 1, "entries": "not-a-list"}))
+    with pytest.raises(calc.CalibrationStateError, match="entries"):
+        calc.load_state(bad)
+
+
+def test_load_state_duplicate_pr_is_hard_error(calc, tmp_path):
+    state_path = _write_state(
+        tmp_path,
+        [
+            _entry(18, "2026-04-25T08:53:09Z"),
+            _entry(18, "2026-04-25T09:00:00Z"),  # same PR number twice
+        ],
+    )
+    with pytest.raises(calc.CalibrationStateError, match="duplicate"):
+        calc.load_state(state_path)
+
+
+def test_load_state_missing_merged_at_is_hard_error(calc, tmp_path):
+    bad = tmp_path / "no_merged_at.json"
+    bad.write_text(
+        json.dumps(
+            {
+                "schema_version": 1,
+                "entries": [{"pr": 18, "r1_outcome": "APPROVE"}],
+            }
+        )
+    )
+    with pytest.raises(calc.CalibrationStateError, match="merged_at"):
+        calc.load_state(bad)
+
+
+def test_load_state_unknown_outcome_is_hard_error(calc, tmp_path):
+    state_path = _write_state(
+        tmp_path,
+        [{"pr": 18, "merged_at": "2026-04-25T08:53:09Z", "r1_outcome": "MAYBE"}],
+    )
+    with pytest.raises(calc.CalibrationStateError, match="r1_outcome"):
+        calc.load_state(state_path)
+
+
+def test_load_state_non_int_pr_is_hard_error(calc, tmp_path):
+    state_path = _write_state(
+        tmp_path,
+        [{"pr": "eighteen", "merged_at": "2026-04-25T08:53:09Z", "r1_outcome": "APPROVE"}],
+    )
+    with pytest.raises(calc.CalibrationStateError, match="pr"):
+        calc.load_state(state_path)
+
+
+def test_load_state_zero_pr_is_hard_error(calc, tmp_path):
+    state_path = _write_state(tmp_path, [_entry(0, "2026-04-25T08:53:09Z")])
+    with pytest.raises(calc.CalibrationStateError, match="positive int"):
+        calc.load_state(state_path)
+
+
+def test_load_state_negative_pr_is_hard_error(calc, tmp_path):
+    state_path = _write_state(tmp_path, [_entry(-1, "2026-04-25T08:53:09Z")])
+    with pytest.raises(calc.CalibrationStateError, match="positive int"):
+        calc.load_state(state_path)
+
+
+def test_load_state_non_dict_entry_is_hard_error(calc, tmp_path):
+    bad = tmp_path / "bad_entry.json"
+    bad.write_text(json.dumps({"schema_version": 1, "entries": ["not-a-dict"]}))
+    with pytest.raises(calc.CalibrationStateError, match="JSON object"):
+        calc.load_state(bad)
+
+
+def test_load_state_empty_entries_list_is_valid(calc, tmp_path):
+    """An empty list of entries is valid (only the establishing PR uses this)."""
+    state_path = _write_state(tmp_path, [])
+    assert calc.load_state(state_path) == []
+
+
+# ---------------------------------------------------------------------------
+# gate_label
+# ---------------------------------------------------------------------------
+
+
+def test_gate_label_blocking(calc):
+    r = calc.CalibrationResult(
+        ceiling=30, mandatory_codex=True, blocking=True, basis="b", entry_count=5
+    )
+    assert calc.gate_label(r) == "BLOCKING"
+
+
+def test_gate_label_mandatory(calc):
+    r = calc.CalibrationResult(
+        ceiling=50, mandatory_codex=True, blocking=False, basis="b", entry_count=5
+    )
+    assert calc.gate_label(r) == "MANDATORY"
+
+
+def test_gate_label_recommended(calc):
+    r = calc.CalibrationResult(
+        ceiling=80, mandatory_codex=False, blocking=False, basis="b", entry_count=5
+    )
+    assert calc.gate_label(r) == "RECOMMENDED"
+
+
+def test_gate_label_optional(calc):
+    r = calc.CalibrationResult(
+        ceiling=95, mandatory_codex=False, blocking=False, basis="b", entry_count=5
+    )
+    assert calc.gate_label(r) == "OPTIONAL"
+
+
+# ---------------------------------------------------------------------------
+# main() — JSON / human / --check + R2 fail-closed paths
+# ---------------------------------------------------------------------------
+
+
+def test_main_json_output(calc, tmp_path, capsys):
+    state_path = _write_state(
+        tmp_path,
+        [_entry(i, f"2026-04-25T08:0{i}:00Z") for i in range(1, 6)],
+    )
+    rc = calc.main(["compute_calibration_cap.py", "--state", str(state_path)])
+    assert rc == 0
+    out = json.loads(capsys.readouterr().out)
+    assert out["ceiling"] == 30
+    assert out["mandatory_codex"] is True
+    assert out["blocking"] is True
+    assert out["entry_count"] == 5
+    assert out["gate_label"] == "BLOCKING"
+
+
+def test_main_human_output(calc, tmp_path, capsys):
+    state_path = _write_state(tmp_path, [])
+    rc = calc.main(["compute_calibration_cap.py", "--human", "--state", str(state_path)])
+    assert rc == 0
+    captured = capsys.readouterr().out
+    assert "T1 calibration ceiling : 95%" in captured
+    assert "OPTIONAL" in captured
+
+
+def test_main_check_passes_when_claim_below_ceiling(calc, tmp_path):
+    state_path = _write_state(tmp_path, [])  # ceiling 95
+    rc = calc.main(["compute_calibration_cap.py", "--check", "30", "--state", str(state_path)])
+    assert rc == 0
+
+
+def test_main_check_fails_when_claim_above_ceiling(calc, tmp_path, capsys):
+    state_path = _write_state(
+        tmp_path,
+        [_entry(i, f"2026-04-25T08:0{i}:00Z") for i in range(1, 6)],
+    )  # ceiling 30
+    rc = calc.main(["compute_calibration_cap.py", "--check", "95", "--state", str(state_path)])
+    assert rc == 1
+    err = capsys.readouterr().err
+    assert "calibration check FAILED" in err
+    assert "claimed 95%" in err
+    assert "computed ceiling 30%" in err
+
+
+def test_main_check_at_exact_ceiling_passes(calc, tmp_path):
+    """Claim == ceiling must pass (not strictly greater)."""
+    state_path = _write_state(
+        tmp_path,
+        [_entry(i, f"2026-04-25T08:0{i}:00Z") for i in range(1, 6)],
+    )
+    rc = calc.main(["compute_calibration_cap.py", "--check", "30", "--state", str(state_path)])
+    assert rc == 0
+
+
+# ---------------------------------------------------------------------------
+# main() — R2 fail-closed enforcement
+# ---------------------------------------------------------------------------
+
+
+def test_main_missing_state_file_returns_1(calc, tmp_path, capsys):
+    """R2 fix: --check used to silently pass when state file was missing.
+
+    Codex R1 reproduction: `--check 95 --state /tmp/does-not-exist.json` → 0.
+    Now: hard error, exit 1, no fail-open.
+    """
+    rc = calc.main(
+        [
+            "compute_calibration_cap.py",
+            "--check",
+            "95",
+            "--state",
+            str(tmp_path / "missing.json"),
+        ]
+    )
+    assert rc == 1
+    err = capsys.readouterr().err
+    assert "calibration state error" in err
+    assert "not found" in err
+
+
+def test_main_invalid_json_returns_1(calc, tmp_path, capsys):
+    bad = tmp_path / "bad.json"
+    bad.write_text("not-valid-json")
+    rc = calc.main(["compute_calibration_cap.py", "--state", str(bad)])
+    assert rc == 1
+    err = capsys.readouterr().err
+    assert "calibration state error" in err
+
+
+def test_main_wrong_schema_version_returns_1(calc, tmp_path, capsys):
+    state_path = _write_state(tmp_path, [], schema_version=999)
+    rc = calc.main(["compute_calibration_cap.py", "--state", str(state_path)])
+    assert rc == 1
+    err = capsys.readouterr().err
+    assert "schema_version" in err
+
+
+def test_main_duplicate_pr_returns_1(calc, tmp_path, capsys):
+    state_path = _write_state(
+        tmp_path,
+        [
+            _entry(18, "2026-04-25T08:53:09Z"),
+            _entry(18, "2026-04-25T09:00:00Z"),
+        ],
+    )
+    rc = calc.main(["compute_calibration_cap.py", "--state", str(state_path)])
+    assert rc == 1
+    err = capsys.readouterr().err
+    assert "duplicate" in err

 succeeded in 784ms:
{"baseRefName":"main","body":"## Summary\n\nReplaces RETRO-V61-001's honor-system self-pass-rate with a mechanically-derived ceiling computed from a rolling 5-PR window of Codex Round 1 outcomes. T1 cannot type a number; T1 reads one.\n\nPer **AR-2026-04-25-001 §1** / **DEC-T0-2026-04-25-001** / sibling ADR-013 (branch protection, lands separately).\n\n### Formula (canonical)\n\n```\nBase ceiling (per next PR), CR-of-last-5:\n  0 → 95% optional · 1-2 → 80% recommended · 3-4 → 50% mandatory · 5 → 30% mandatory BLOCKING\n\nRecovery (overrides base):\n  2 trailing R1=APPROVE → step up one rung    (30→50, 50→80, 80→95)\n  3 trailing R1=APPROVE → reset to 95\n```\n\nOutcome canon: `APPROVE | APPROVE_WITH_NITS | CHANGES_REQUIRED | BLOCKER` (NITS = APPROVE; BLOCKER = CHANGES_REQUIRED).\n\n### Why this exists\n\nSession 2026-04-25 produced empirical evidence that the honor-system fails:\n\n| PR | T1 self-estimate | Codex R1 actual |\n|---|---|---|\n| #20 | 95% | CHANGES_REQUIRED (1 BLOCKER) |\n| #18 | 95% | CHANGES_REQUIRED (1 HIGH) |\n| #19 | 95% | CHANGES_REQUIRED (1 HIGH) |\n| #21 | 90% | CHANGES_REQUIRED (1 HIGH) |\n| #22 | 80% | CHANGES_REQUIRED (1 BLOCKER) |\n| #23 | (n/a) | CHANGES_REQUIRED (3 BLOCKER + 1 SHOULD_FIX) |\n\nT1 self-estimates were systematically wrong by 80-95 pp each across the same session. The retro-debit lag (next-cycle correction) is too slow.\n\n## Files\n\n- `docs/adr/ADR-012-calibration-cap-for-t1-self-pass-rate.md` (132 lines)\n- `scripts/compute_calibration_cap.py` (229 lines · pure function + CLI: `--human`, `--check <claimed>`, JSON default)\n- `tests/test_compute_calibration_cap.py` (42 unit tests · all rungs, recovery, BLOCKER/NITS canon, JSON output, edge cases)\n- `reports/calibration_state.json` (append-only schema v1 · 6 entries: PR #18-#23)\n\n## Bootstrap state at this PR's open\n\nLast 5 = #19, #20, #21, #22, #23 — all `CHANGES_REQUIRED`.\n\n```\nT1 calibration ceiling : 30%\nCodex pre-merge gate   : BLOCKING\nBasis                  : 5 of last 5 = CHANGES_REQUIRED → ceiling 30%\nState entries          : 6 (last 5 used)\n```\n\n**This PR therefore opens UNDER the 30%/BLOCKING regime that ADR-012 itself defines.** Pre-merge Codex review is **mandatory** per the ADR's own gate rules — not optional.\n\n## Self-pass-rate (mechanically derived)\n\n**30%** · BLOCKING · pre-merge Codex MANDATORY · derivation in `reports/calibration_state.json` last-5 window.\n\nADR-011 §T2 mandatory triggers (audited per AR-2026-04-25-001 §4):\n\n- [x] **M1** — governance text added (`docs/adr/ADR-012-*.md` + supersedes-clause for RETRO-V61-001)\n- [x] **M2** — non-trivial numerical computation (the rung-ladder formula, recovery thresholds, and the `--check` boundary semantics are factual numerical assertions)\n- [x] **M4** — governance→enforcement translation (`compute_calibration_cap.py` is the validator implementing the rule; `calibration_state.json` is the schema-typed source of truth)\n- [x] **M5** — PR opened while ceiling ≤ 50% (ceiling is 30; this PR opens under its own BLOCKING regime)\n- [ ] M3 — no HF zone compliance claim made by this PR\n\nCodex pre-merge is therefore mandatory on **two independent grounds**: ceiling-derived BLOCKING gate AND M1+M2+M4+M5 triggers. Either alone would suffice.\n\n## Recovery path\n\nTo return to honor-system 95%:\n\n- 1 R1=APPROVE → 4-of-5-CR → ceiling 50, MANDATORY non-blocking\n- 2 trailing APPROVE → step-up to 80, RECOMMENDED\n- 3 trailing APPROVE → reset to 95, OPTIONAL\n\nThree clean PRs in a row restore honor-system. Mechanical, fast, evidence-grounded.\n\n## Test plan\n\n- [ ] **Pre-merge Codex review** (`/codex-gpt54`) — required by the ADR's own gate; review must reach R1=APPROVE before merge per the BLOCKING ceiling\n- [x] `tests/test_compute_calibration_cap.py` — 42/42 passing locally (Python 3.9 + 3.11)\n- [x] `tests/test_hf1_path_guard.py` — 30/30 passing locally\n- [x] `python3 scripts/compute_calibration_cap.py --human` produces ceiling=30 BLOCKING\n- [x] `python3 scripts/compute_calibration_cap.py --check 80` exits non-zero (claim above ceiling)\n- [x] `python3 scripts/compute_calibration_cap.py --check 30` exits zero\n- [ ] CI green on 3.11\n\n## Out of scope\n\n- ADR-013 (branch protection — the *enforcement* surface for this gate; sibling PR, lands separately)\n- ADR-011 amendment for Codex M1-M5 reword: already shipped via PR #23 (e53b0f7)\n- PR template integration (waits for ADR-013)\n- CI hook calling `--check` against PR body claims (waits for ADR-013)\n\n## Related\n\n- Parent: ADR-011 (claude-code-takeover, ratified PR #17, amended PR #23)\n- Sibling: ADR-013 (branch protection)\n- T0 Decision: AR-2026-04-25-001 / DEC-T0-2026-04-25-001\n- Supersedes (for AI-Structure-FEA only): RETRO-V61-001 §`external_gate_self_estimated_pass_rate` honor-system\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)\n","commits":[{"authoredDate":"2026-04-25T11:24:25Z","authors":[{"email":"kogamishinyajerry-ops@users.noreply.github.com","id":"U_kgDODjMbqg","login":"kogamishinyajerry-ops","name":"kogamishinyajerry-ops"},{"email":"noreply@anthropic.com","id":"MDQ6VXNlcjgxODQ3","login":"claude","name":"Claude Opus 4.7 (1M context)"}],"committedDate":"2026-04-25T12:08:03Z","messageBody":"Replaces RETRO-V61-001's honor-system self-pass-rate with a\nmechanically-derived ceiling computed from a rolling 5-PR window of\nCodex Round 1 outcomes. T1 cannot type a number; T1 reads one.\n\nPer AR-2026-04-25-001 §1 / DEC-T0-2026-04-25-001:\n\n- Base ceiling table (CR-of-last-5):\n    0 → 95% optional · 1-2 → 80% recommended · 3-4 → 50% mandatory ·\n    5 → 30% mandatory BLOCKING.\n- Recovery: 2 trailing R1=APPROVE step up one rung; 3 trailing reset to 95.\n- Outcome canon: APPROVE | APPROVE_WITH_NITS | CHANGES_REQUIRED | BLOCKER\n  (NITS = APPROVE; BLOCKER = CHANGES_REQUIRED).\n\nBootstrap state (PRs #18-#22, all R1=CHANGES_REQUIRED) yields\nceiling=30, BLOCKING — exactly correct given session 2026-04-25's\nempirical 0/5 R1-pass-rate while T1 self-rated 80-95% on each.\n\nFiles:\n  docs/adr/ADR-012-calibration-cap-for-t1-self-pass-rate.md\n  scripts/compute_calibration_cap.py            (pure function + CLI)\n  tests/test_compute_calibration_cap.py         (42 unit tests)\n  reports/calibration_state.json                (append-only schema v1)\n\nLand sequence: this PR opens UNDER the bootstrap 30%/BLOCKING regime\nthat ADR-012 itself defines. Pre-merge Codex review is mandatory per\nthe ADR's own gate rules.\n\nCo-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>","messageHeadline":"[ADR-012] Calibration cap for T1 self-pass-rate","oid":"971616cc6165137506fcee77c644a1928849cd94"},{"authoredDate":"2026-04-25T12:09:11Z","authors":[{"email":"kogamishinyajerry-ops@users.noreply.github.com","id":"U_kgDODjMbqg","login":"kogamishinyajerry-ops","name":"kogamishinyajerry-ops"},{"email":"noreply@anthropic.com","id":"MDQ6VXNlcjgxODQ3","login":"claude","name":"Claude Opus 4.7 (1M context)"}],"committedDate":"2026-04-25T12:09:11Z","messageBody":"ADR-012's own protocol: \"After each PR merges, the maintainer\nappends a new entry to reports/calibration_state.json\".\nPR #23 (ADR-011 amendments) merged at 2026-04-25T12:06:52Z with R1\noutcome CHANGES_REQUIRED (3 BLOCKER + 1 SHOULD_FIX, fixed in e96904d).\n\nAlso harden test_load_state_real_bootstrap_yields_30 → renamed to\ntest_load_state_real_file_yields_30_while_last_5_are_cr. The original\nasserted entry_count == 5, which would break every time a new PR\nappended to the file. The invariant is the ceiling under \"last-5-CR\",\nnot the absolute row count. New assertion: when last 5 are all\nCR/BLOCKER, ceiling must be 30 BLOCKING; otherwise the test no-ops\ngracefully (recovery path covered by other tests).\n\nWindow-of-last-5 = #19, #20, #21, #22, #23 — still 5/5 CR, ceiling\nremains 30 BLOCKING.\n\nCo-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>","messageHeadline":"[ADR-012] housekeeping: append PR #23 entry, harden bootstrap test","oid":"5c21247cb4ca93ba65dff75c3a1e26ecbdb8e661"},{"authoredDate":"2026-04-25T18:03:00Z","authors":[{"email":"kogamishinyajerry-ops@users.noreply.github.com","id":"U_kgDODjMbqg","login":"kogamishinyajerry-ops","name":"kogamishinyajerry-ops"},{"email":"noreply@anthropic.com","id":"MDQ6VXNlcjgxODQ3","login":"claude","name":"Claude Opus 4.7 (1M context)"}],"committedDate":"2026-04-25T18:03:00Z","messageBody":"Addresses Codex R1 CHANGES_REQUIRED on PR #24 (2026-04-26).\n\nHIGH #1 — load_state sorted by PR number, not merge order. Repo's\nown bootstrap data has PR #20 merged at 2026-04-25T08:33:51Z\nBEFORE PR #18 at 08:53:09Z. PR-number sort silently produced wrong\noutcome ordering.\n\nFix: load_state sorts by `merged_at` (ISO 8601). New regression test\ntest_load_state_sorts_by_merged_at_not_pr_counterexample encodes the\nexact scenario Codex cited: PR-sort vs merged_at-sort produce\ndifferent ceilings (80 with recovery vs 80 without recovery) for\nthe same data.\n\nHIGH #2 — fail-open on missing/malformed state. Codex reproduced\n`--check 95 --state /tmp/nonexistent.json` exiting 0; schema\nversion 999 silently accepted; duplicate `pr` rows silently used.\n\nFix: introduced CalibrationStateError. load_state hard-errors on\nmissing file, JSON parse failure, non-dict root, schema_version != 1\n(or missing), entries not a list, non-dict entry, non-int / zero /\nnegative pr, duplicate pr, missing/empty merged_at, r1_outcome\nnot in canonical set. main() catches the error and exits 1.\n\nEmpty entries list remains valid (the legitimate \"0 of last 5\"\nbranch — only the establishing PR uses this).\n\nManual verification against Codex's repro commands:\n  $ python3 scripts/compute_calibration_cap.py --check 95 --state /tmp/nonexistent.json\n  → calibration state error: ... not found ... ; EXIT=1\n  $ python3 scripts/compute_calibration_cap.py --state /tmp/bad_schema.json (schema 999)\n  → calibration state error: schema_version must be 1, got 999 ; EXIT=1\n  $ python3 scripts/compute_calibration_cap.py --state /tmp/dup_pr.json\n  → calibration state error: entries[1].pr=23 is a duplicate ... ; EXIT=1\n\nDoc updates:\n  - reports/calibration_state.json `doc` field: merged_at is the\n    sort key; lists fail-closed contract\n  - docs/adr/ADR-012: implementation contract reflects merged_at\n    sort + fail-closed semantics\n\nTests: 42 → 60 (+18). Includes counterexample regression and 12\nadversarial state-validation cases.\n\nSelf-pass-rate: 30% (under the BLOCKING cap this PR establishes).\n\nM-triggers: M1 (ADR + state doc), M2 (18 new assertions), M4\n(governance→enforcement: this is the enforcement path that ADR-013\nwill gate-check), M5 (ceiling 30% ≤ 50%).\n\nR1 review archived as PR #49 (pr24_adr012_r1_review.md).\nR2 expects re-review under same M1+M2+M4+M5 trigger set.\n\nCo-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>","messageHeadline":"[ADR-012] R2: sort by merged_at + fail-closed state validation","oid":"3d97d30732df51b0430110afb7d7828f4716b66c"}],"files":[{"path":"docs/adr/ADR-012-calibration-cap-for-t1-self-pass-rate.md","additions":132,"deletions":0,"changeType":"ADDED"},{"path":"reports/calibration_state.json","additions":80,"deletions":0,"changeType":"ADDED"},{"path":"scripts/compute_calibration_cap.py","additions":322,"deletions":0,"changeType":"ADDED"},{"path":"tests/test_compute_calibration_cap.py","additions":530,"deletions":0,"changeType":"ADDED"}],"headRefName":"feature/AI-FEA-ADR-012-calibration-cap","isDraft":false,"mergeStateStatus":"CLEAN","number":24,"state":"OPEN","title":"[ADR-012] Calibration cap for T1 self-pass-rate (mechanical ceiling, BLOCKING bootstrap)"}

 succeeded in 809ms:
{"baseRefName":"feature/AI-FEA-ADR-012-calibration-cap","body":"## Summary\n\nThree-layer enforcement wrapper around ADR-012 (PR #24, parent in stack). ADR-012 defines a calibration ceiling but has no surface that prevents T1 self-merge under BLOCKING — this PR adds it.\n\n**Stacked on PR #24.** Base = `feature/AI-FEA-ADR-012-calibration-cap`. Diff narrows to ADR-013-only after PR #24 merges and GitHub auto-rebases the base to `main`.\n\n## Three layers\n\n**L1 — PR template** (`.github/PULL_REQUEST_TEMPLATE.md`)\nReserves a `## Self-pass-rate (mechanically derived)` section and forces a Codex gate level pick + ADR-011 §T2 M1-M5 ticks. Surfaces the gate before review.\n\n**L2 — CI workflow** (`.github/workflows/calibration-cap-check.yml`)\nOn every `pull_request` event, parses the PR body, runs `compute_calibration_cap.py --check <claim>`. CI red on overclaim. 16 unit tests for the extractor.\n\n**L3 — Branch protection** (`scripts/apply_branch_protection.sh`)\nIdempotent `gh api PUT` enabling required status checks (`lint-and-test (3.11)` + `calibration-cap-check`), linear history, no force-push, no deletions, conversation resolution. `enforce_admins: false` so T0 retains emergency override; `required_pull_request_reviews: null` because solo-dev (Codex is de facto reviewer).\n\n## Discipline binding\n\nLayer 3's `enforce_admins: false` is a deliberate residual loophole. Closed by explicit T1 contract in ADR-013:\n\n> T1 must NOT merge a PR while its ceiling-derived gate is BLOCKING (30%) unless either:\n> (a) Codex R1=APPROVE on latest commit, OR\n> (b) T0 explicit in-conversation authorization.\n\nViolation = P0 procedural failure → retro entry.\n\n## Repo-tier prerequisite\n\nBoth classic branch protection and rulesets are paywalled on free private repos. Repo flipped **private → public** on 2026-04-25 to satisfy this. ADR-013 §\"Repo-tier prerequisite\" documents the alternatives if the project ever needs to go private again.\n\n## Files\n\n**Commit 1 — ADR-013 enforcement (`b6b722d`):**\n\n- `docs/adr/ADR-013-branch-protection-enforcement.md` (~110 lines)\n- `.github/PULL_REQUEST_TEMPLATE.md` (~50 lines)\n- `.github/workflows/calibration-cap-check.yml` (~55 lines)\n- `scripts/extract_pr_self_pass_rate.py` (~50 lines, pure stdlib)\n- `tests/test_extract_pr_self_pass_rate.py` (16 unit tests)\n- `scripts/apply_branch_protection.sh` (~35 lines, idempotent)\n\n**Commit 2 — STATE.md sync (`7542b05`):**\n\nPer FF-05 R1 lesson (\"update STATE.md in the same PR as the change it reflects\"), this PR also resyncs `.planning/STATE.md` to current main + ADR-012/013 in-flight. Before this commit, STATE.md was 4 PRs stale (#20/#21/#22/#23 missing) — Codex would have flagged this on R1 as the same stale-state pattern that produced FF-05's R1 CHANGES_REQUIRED.\n\n- `.planning/STATE.md` (44 insertions, 23 deletions)\n- New row FF-01a for ADR-011 amendments (PR #23)\n- FF-06 row flipped Pending → Merged (PR #22)\n- New \"Governance ADRs in flight\" sub-table for PR #24/25\n- 2026-04-25 merge timeline (UTC) added\n- Carry-over item #1 + #2 updated to reflect FF-06 merge + ADR-013 in flight\n- Carry-over item #6 added: T1 still operates under falsified honor-system until #24 merges (epistemically honest disclosure)\n\n## Self-pass-rate (mechanically derived)\n\n**30%** · BLOCKING · pre-merge Codex MANDATORY · derived from `reports/calibration_state.json` last-5 R1 outcomes (PRs #19-#23, all CR).\n\nADR-011 §T2 mandatory triggers:\n- [x] M1: governance text added (ADR-013)\n- [x] M4: governance→enforcement translation (the entire purpose of this PR)\n- [x] M5: PR opened while ceiling ≤ 50%\n\nThis PR is doubly Codex-mandatory: ceiling regime + M1+M4+M5 triggers.\n\n## Activation sequence (post-merge of this PR)\n\n1. Layers 1 + 2 take effect automatically on subsequent PRs.\n2. T0 runs `bash scripts/apply_branch_protection.sh` once → Layer 3 active.\n3. From that point: no main-bound PR can merge without both required checks green.\n\n## Why stacked, not standalone\n\n`scripts/compute_calibration_cap.py` lives on PR #24's branch and isn't on `main` yet. The CI workflow (`calibration-cap-check.yml`) shipped in this PR invokes that script. Stacking on PR #24 means the head ref has both files together, so CI on this PR can run end-to-end. After PR #24 merges, this PR's base auto-rebases to `main` and the diff cleanly narrows.\n\n## Test plan\n\n- [ ] **Pre-merge Codex review** (`/codex-gpt54`) — mandatory under both ceiling + M1+M4+M5\n- [x] `tests/test_extract_pr_self_pass_rate.py` — 16/16 passing\n- [x] Combined targeted suite (extractor + calibration_cap + hf1_path_guard) — 94/94 passing\n- [x] Manual: empty body → extractor exits 2; `--check 80` against ceiling 30 → exits 1; `--check 30` → exits 0\n- [ ] CI green on this PR (workflow file is new on this PR; runs against PR head — should validate cleanly since the body has the 30% claim)\n\n## Out of scope\n\n- Multi-reviewer / CODEOWNERS (single-author repo, no value yet)\n- Signed-commit requirements (would require GPG keypair setup for T1)\n- Direct-push restrictions on feature branches (force-push protection on main is enough)\n- Auto-revert workflow for merge-bypasses (could land in a follow-up retro after observing actual bypass attempts)\n\n## Related\n\n- Parent: ADR-012 (PR #24, calibration math) — stacked beneath this PR\n- Grandparent: ADR-011 (claude-code-takeover, ratified PR #17, amended PR #23)\n- T0 Decision: AR-2026-04-25-001 / DEC-T0-2026-04-25-001\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)\n","commits":[{"authoredDate":"2026-04-25T12:22:05Z","authors":[{"email":"kogamishinyajerry-ops@users.noreply.github.com","id":"U_kgDODjMbqg","login":"kogamishinyajerry-ops","name":"kogamishinyajerry-ops"},{"email":"noreply@anthropic.com","id":"MDQ6VXNlcjgxODQ3","login":"claude","name":"Claude Opus 4.7 (1M context)"}],"committedDate":"2026-04-25T12:22:05Z","messageBody":"ADR-012 defines a calibration ceiling but has zero enforcement surface.\nThis PR adds three concentric layers so the gate cannot be silently\nbypassed by T1 acting alone.\n\nLayer 1 — PR template (.github/PULL_REQUEST_TEMPLATE.md):\n  Reserves a \"Self-pass-rate (mechanically derived)\" section, instructs\n  authors to fill it from compute_calibration_cap.py output (not\n  intuition), forces a Codex gate level pick (BLOCKING/MANDATORY/\n  RECOMMENDED/OPTIONAL), and tickbox for ADR-011 §T2 M1-M5 triggers.\n\nLayer 2 — CI workflow (.github/workflows/calibration-cap-check.yml):\n  On every pull_request event, computes the current ceiling, extracts\n  the claimed ceiling from PR body via scripts/extract_pr_self_pass_rate.py,\n  runs --check; non-zero exit → CI red → merge blocked once Layer 3\n  is on. 16 unit tests for the extractor (h2/h3 headings, percent\n  bounds, window-size, h1-rejection, inline-mention rejection, CLI).\n\nLayer 3 — branch protection (scripts/apply_branch_protection.sh):\n  Idempotent gh api script applying:\n    - required_status_checks: lint-and-test (3.11) + calibration-cap-check\n    - required_linear_history: true\n    - allow_force_pushes/deletions: false\n    - required_conversation_resolution: true\n    - enforce_admins: false (T0 emergency override retained)\n    - required_pull_request_reviews: null (solo-dev; Codex is de facto reviewer)\n\nDiscipline binding: the residual admin-bypass loophole is closed by an\nexplicit T1 contract — no merge under BLOCKING ceiling unless either\nCodex R1=APPROVE or T0 explicit in-conversation authorization.\n\nRepo-tier prerequisite: protection + rulesets API requires public OR\nGitHub Pro. Repo flipped private→public on 2026-04-25 to satisfy this.\n\nActivation sequence (post-merge):\n  1. Layers 1+2 take effect on subsequent PRs automatically.\n  2. T0 runs `bash scripts/apply_branch_protection.sh` once to enable Layer 3.\n  3. From that point, no main-bound PR can land without both checks green.\n\nThis PR + ADR-012 PR (#24) ride on Layer 0 (no enforcement) since their\nworkflow files don't yet exist on main. ADR-012 §discipline applies\nretroactively: both must reach Codex R1=APPROVE before merge.\n\nCo-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>","messageHeadline":"[ADR-013] Branch protection enforcement (3-layer wrapper around ADR-012)","oid":"b6b722d6cfed686e316916ee0228ed9f3e2dfeed"},{"authoredDate":"2026-04-25T13:02:29Z","authors":[{"email":"kogamishinyajerry-ops@users.noreply.github.com","id":"U_kgDODjMbqg","login":"kogamishinyajerry-ops","name":"kogamishinyajerry-ops"},{"email":"noreply@anthropic.com","id":"MDQ6VXNlcjgxODQ3","login":"claude","name":"Claude Opus 4.7 (1M context)"}],"committedDate":"2026-04-25T13:02:29Z","messageBody":"Per FF-05 R1 lesson (\"update STATE.md in the same PR as the change it\nreflects\"), bundling the STATE.md drift fix onto ADR-013's branch.\n\nResync covers PRs #20, #21, #22, #23 (all merged 2026-04-25) plus\nADR-012 (#24) and ADR-013 (#25, this PR) listed under in-flight.\n\nChanges:\n- Stamp: post-#17/18/19 → post-#17/18/19/20/21/22/23 ·\n  ADR-012/013-in-flight; main hash 4a64cfd → e53b0f7\n- FF-06 row flipped Pending → Merged (PR #22 ac98fc3); R1/R2 history\n  recorded\n- New row FF-01a for ADR-011 amendments AR-2026-04-25-001 (PR #23 e53b0f7)\n- New table \"Governance ADRs in flight\" listing PR #24 (ADR-012) and\n  PR #25 (ADR-013) with their queue status\n- \"Repo state\" merge-timeline added with UTC timestamps for each\n  2026-04-25 merge (#17 → #23)\n- Phase 1.5 status block updated: governance baseline merged, ADR-012/013\n  in queue, FF-07/08/09 still pending (FF-06 removed from pending list)\n- Phase 2 gating: FF-06 dropped from gate list (now merged)\n- Active ADRs table: ADR-011 marked amended, ADR-012/013 added with\n  drafted/awaiting status; ADR-014+ follow-ups renumbered\n- Carry-overs section item #1 updated for FF-06 merge, item #2 updated\n  for ADR-013 in flight, new item #6 acknowledging the\n  T1-still-under-falsified-honor-system reality until PR #24 merges\n- \"How to update\" section reinforces FF-05 R1 lesson (same-PR rule)\n\nThis update is itself an ADR-011 §T2 M1 trigger (governance text added),\nso Codex review on this PR was already mandatory; no new gate trigger.\n\nCo-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>","messageHeadline":"[FF-05-discipline] STATE.md sync to current main + ADR-012/013 in-flight","oid":"7542b05ba98269dcbc06a06c8f26dde9059413d7"},{"authoredDate":"2026-04-25T18:13:21Z","authors":[{"email":"kogamishinyajerry-ops@users.noreply.github.com","id":"U_kgDODjMbqg","login":"kogamishinyajerry-ops","name":"kogamishinyajerry-ops"},{"email":"noreply@anthropic.com","id":"MDQ6VXNlcjgxODQ3","login":"claude","name":"Claude Opus 4.7 (1M context)"}],"committedDate":"2026-04-25T18:13:21Z","messageBody":"Addresses Codex R1 CHANGES_REQUIRED on PR #25 (2026-04-26).\n\nHIGH #1 — workflow self-bypass.\n  Codex finding: the workflow checked out the PR's tree and ran\n  scripts/compute_calibration_cap.py + scripts/extract_pr_self_pass_rate.py\n  + reports/calibration_state.json from there. A bad-faith PR could edit\n  any of those three to make the gate go green.\n\n  Fix: .github/workflows/calibration-cap-check.yml now does\n  `actions/checkout@v4 with: ref: main, path: trusted` and runs every\n  validator from `trusted/...`. The PR's own tree is not checked out.\n  The PR body still comes from the GitHub event payload (legitimately\n  untrusted; that's the input the gate validates). State file also\n  comes from `trusted/reports/calibration_state.json`, so PR-level\n  edits to state are silently ignored by CI.\n\nHIGH #2 — extractor hidden-marker bypass.\n  Codex reproduction: `## Self-pass-rate\\n\\n<!-- 30% -->\\n\\n95%`\n  returned 30 because the regex matched the first `N%` within 600\n  chars of the heading without distinguishing visible markdown from\n  hidden constructs.\n\n  Fix: scripts/extract_pr_self_pass_rate.py now strips\n    - HTML comments (<!-- ... -->), incl. multi-line, BEFORE matching\n    - fenced code blocks (```...``` and ~~~...~~~), all flavors\n    - inline code spans (`...`)\n  via _strip_hidden_constructs(). After stripping, the same heading +\n  600-char tail + `\\b(\\d{1,3})\\s*%` regex applies.\n\nHIGH #3 — fail-open inheritance from #24.\n  Auto-resolved: PR #24 R2 makes load_state hard-error on missing\n  state, schema mismatch, duplicate pr, etc. With #24 R2 merged, this\n  workflow's `compute_calibration_cap.py --check` exits 1 on any\n  state file problem instead of silently returning 95%/OPTIONAL.\n\nTests: tests/test_extract_pr_self_pass_rate.py 16 → 27 (+11). The\nnew adversarial cases pin every Codex-cited bypass: the exact repro\n(hidden HTML comment, visible 95%), HTML-only (no visible → None),\nmulti-line HTML, triple-backtick + triple-tilde code blocks, fenced\nwith language tag, inline code, combined bypass attempts, all-hidden\nreturns None, HTML comment outside section, duplicate sections\n(first visible wins).\n\nHF1.9 override:\n  HF1_GUARD_OVERRIDE='ADR-013 R2 cycle: this branch is the introducing\n  PR for .github/workflows/calibration-cap-check.yml; the workflow\n  file is the artifact under review and Codex R1 HIGH #1 explicitly\n  mandates this exact change (PR-checkout → trusted main checkout)'\n\nSelf-pass-rate: 30% (under the BLOCKING ceiling that PR #24 R2\nestablishes).\n\nM-triggers: M1 (ADR text touched indirectly via workflow comment\nheader + extractor docstring), M3 (HF1.9 zone touched, with override),\nM4 (governance→enforcement: this is the gate), M5 (ceiling 30%).\n\nR1 review archived as PR #49 (pr25_adr013_r1_review.md). R2 expects\nre-review under same M1+M4+M5 trigger set + the new M3 (override).\n\nCo-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>","messageHeadline":"[ADR-013] R2: trusted main checkout + extractor hidden-marker stripping","oid":"20b8c003c284c72282175b34f9d5b096a851437c"}],"files":[{"path":".github/PULL_REQUEST_TEMPLATE.md","additions":61,"deletions":0,"changeType":"ADDED"},{"path":".github/workflows/calibration-cap-check.yml","additions":87,"deletions":0,"changeType":"ADDED"},{"path":".planning/STATE.md","additions":44,"deletions":23,"changeType":"MODIFIED"},{"path":"docs/adr/ADR-013-branch-protection-enforcement.md","additions":109,"deletions":0,"changeType":"ADDED"},{"path":"scripts/apply_branch_protection.sh","additions":46,"deletions":0,"changeType":"ADDED"},{"path":"scripts/extract_pr_self_pass_rate.py","additions":103,"deletions":0,"changeType":"ADDED"},{"path":"tests/test_extract_pr_self_pass_rate.py","additions":279,"deletions":0,"changeType":"ADDED"}],"headRefName":"feature/AI-FEA-ADR-013-branch-protection","isDraft":false,"mergeStateStatus":"CLEAN","number":25,"state":"OPEN","title":"[ADR-013] Branch protection enforcement (stacked on PR #24)"}

 succeeded in 905ms:
diff --git a/.github/PULL_REQUEST_TEMPLATE.md b/.github/PULL_REQUEST_TEMPLATE.md
new file mode 100644
index 0000000..667bf1c
--- /dev/null
+++ b/.github/PULL_REQUEST_TEMPLATE.md
@@ -0,0 +1,61 @@
+<!--
+ADR-013 PR template. Sections marked REQUIRED are validated by CI.
+The "Self-pass-rate" section is mechanically checked against the formula
+in scripts/compute_calibration_cap.py — claims above the current ceiling
+fail CI. Fill it by running:
+
+    python3 scripts/compute_calibration_cap.py --human
+
+and copying the ceiling integer (no `%`) into the section below.
+-->
+
+## Summary
+
+<!-- 1-3 bullets: what changes, why now. -->
+
+-
+-
+
+## Self-pass-rate (mechanically derived) <!-- REQUIRED — ADR-013 -->
+
+<!--
+Replace `<N>` with the integer printed by:
+    python3 scripts/compute_calibration_cap.py
+The CI calibration-cap-check job will fail if your claim exceeds the
+current ceiling. Do not type a number from intuition; ADR-012 forbids it.
+-->
+
+**<N>%** · derived from `reports/calibration_state.json` last-5 R1 outcomes.
+
+Codex pre-merge gate (per ADR-012):
+
+- [ ] BLOCKING (ceiling 30) — must reach Codex R1=APPROVE before merge
+- [ ] MANDATORY non-blocking (ceiling 50) — Codex R1 required, can iterate
+- [ ] RECOMMENDED (ceiling 80) — Codex review strongly suggested
+- [ ] OPTIONAL (ceiling 95) — honor system, Codex at author discretion
+
+ADR-011 §T2 mandatory triggers (M1-M5) override the ceiling-derived gate
+when applicable. Tick any that fire:
+
+- [ ] M1: governance text added/changed (ADRs, FailurePatterns, RETROs)
+- [ ] M2: sign-or-direction math (revert direction, BC orientation, etc.)
+- [ ] M3: HF compliance claim (HF1-HF6 path/zone/process assertions)
+- [ ] M4: governance→enforcement translation (script/CI/hook implementing a rule)
+- [ ] M5: PR opened while ceiling ≤ 50%
+
+## Test plan <!-- REQUIRED -->
+
+- [ ] `pytest tests/`
+- [ ] `ruff check .` and `ruff format --check .`
+- [ ] *(if applicable)* hot-smoke / hand-tested in a real workflow
+- [ ] Codex pre-merge review *(if BLOCKING/MANDATORY or any M1-M5 triggered)*
+
+## Out of scope
+
+<!-- What this PR explicitly does NOT do, to prevent scope creep reviews. -->
+
+-
+
+## Related
+
+- ADR-XXX, FP-XXX, DEC-XXX, AR-XXX as relevant
diff --git a/.github/workflows/calibration-cap-check.yml b/.github/workflows/calibration-cap-check.yml
new file mode 100644
index 0000000..9689b4b
--- /dev/null
+++ b/.github/workflows/calibration-cap-check.yml
@@ -0,0 +1,87 @@
+name: Calibration Cap Check
+
+# ADR-013 enforcement workflow. Validates that every PR's
+# "Self-pass-rate" claim does not exceed the mechanical ceiling
+# computed by scripts/compute_calibration_cap.py from
+# reports/calibration_state.json.
+#
+# Runs only on pull_request events (no value on push to main).
+#
+# R2 hardening (post Codex R1, 2026-04-26):
+#   * The validator scripts AND the calibration_state.json are loaded
+#     from a separate `actions/checkout` of `main`, NOT from the PR's
+#     own checkout. This closes the self-bypass hole Codex reproduced
+#     where a PR could modify scripts/compute_calibration_cap.py,
+#     scripts/extract_pr_self_pass_rate.py, or
+#     reports/calibration_state.json to make the check pass.
+#   * The PR body itself comes from the GitHub API event payload, not
+#     from any file in the PR's checkout, so it remains the legitimate
+#     untrusted input.
+
+on:
+  pull_request:
+    branches: [main]
+    types: [opened, edited, synchronize, reopened]
+
+permissions:
+  contents: read
+  pull-requests: read
+
+jobs:
+  calibration-cap-check:
+    runs-on: ubuntu-latest
+    steps:
+      - name: Checkout main (trusted validators + state)
+        # The PR is intentionally NOT checked out for the validator
+        # scripts. Only main's view of compute_calibration_cap.py,
+        # extract_pr_self_pass_rate.py, and reports/calibration_state.json
+        # is trusted. A PR can change those files in its own working
+        # tree but the check here ignores those changes.
+        uses: actions/checkout@v4
+        with:
+          ref: main
+          path: trusted
+
+      - name: Set up Python 3.11
+        uses: actions/setup-python@v5
+        with:
+          python-version: "3.11"
+
+      - name: Compute current ceiling (from trusted main)
+        id: ceiling
+        working-directory: trusted
+        run: |
+          set -euo pipefail
+          OUTPUT=$(python3 scripts/compute_calibration_cap.py)
+          CEILING=$(echo "$OUTPUT" | python3 -c "import json,sys;print(json.load(sys.stdin)['ceiling'])")
+          GATE=$(echo "$OUTPUT" | python3 -c "import json,sys;print(json.load(sys.stdin)['gate_label'])")
+          BLOCKING=$(echo "$OUTPUT" | python3 -c "import json,sys;print(json.load(sys.stdin)['blocking'])")
+          echo "ceiling=$CEILING" >> "$GITHUB_OUTPUT"
+          echo "gate=$GATE" >> "$GITHUB_OUTPUT"
+          echo "blocking=$BLOCKING" >> "$GITHUB_OUTPUT"
+          echo "Current ceiling: ${CEILING}%, gate: ${GATE}, blocking: ${BLOCKING} (computed from trusted/main)"
+
+      - name: Extract Self-pass-rate claim from PR body (trusted extractor)
+        id: claim
+        working-directory: trusted
+        env:
+          PR_BODY: ${{ github.event.pull_request.body }}
+        run: |
+          set -euo pipefail
+          if [[ -z "${PR_BODY:-}" ]]; then
+            echo "::error::PR body is empty. ADR-013 requires a 'Self-pass-rate' section."
+            exit 1
+          fi
+          # Use main's extractor — not the PR's. PR body comes from the
+          # event payload (already untrusted; that's the point — its claim
+          # must be checked against the trusted ceiling).
+          CLAIM=$(printf '%s' "$PR_BODY" | python3 scripts/extract_pr_self_pass_rate.py)
+          echo "claim=$CLAIM" >> "$GITHUB_OUTPUT"
+          echo "Claim parsed from PR body: ${CLAIM}% (extractor from trusted/main)"
+
+      - name: Validate claim does not exceed ceiling (from trusted main)
+        working-directory: trusted
+        run: |
+          set -euo pipefail
+          python3 scripts/compute_calibration_cap.py --check "${{ steps.claim.outputs.claim }}"
+          echo "::notice::Claim ${{ steps.claim.outputs.claim }}% does not exceed ceiling ${{ steps.ceiling.outputs.ceiling }}% (gate: ${{ steps.ceiling.outputs.gate }})"
diff --git a/.planning/STATE.md b/.planning/STATE.md
index 151a120..712384a 100644
--- a/.planning/STATE.md
+++ b/.planning/STATE.md
@@ -1,7 +1,7 @@
 # AI-Structure-FEA · STATE
 
-> **Stamp:** `post-pivot-foundation-freeze-2026-04-25 · post-#17/#18/#19-merge · pre-FF-06`
-> **Last updated:** 2026-04-25 (after PR #17 → #18 → #19 merge chain; main = `4a64cfd`; Codex review reports archived at `reports/codex_tool_reports/`)
+> **Stamp:** `post-pivot-foundation-freeze-2026-04-25 · post-#17/18/19/20/21/22/23-merge · ADR-012/013-in-flight`
+> **Last updated:** 2026-04-25 (after PR #23 ADR-011 amendments merge; main = `e53b0f7`; PR #24 ADR-012 + PR #25 ADR-013 in flight, both pending Codex R1)
 > **Maintained by:** T1 (Claude Code CLI · Opus 4.7) per ADR-011 §6 Sessions fully traced.
 
 This file is the **repo-side execution status snapshot**. Notion 项目控制塔 (root_page_id `345c68942bed80f6a092c9c2b3d3f5b9`) is the human-facing process SSOT. When they conflict, **git is authoritative**; STATE.md is updated to match git, and Notion is patched from STATE.md.
@@ -13,8 +13,8 @@ This file is the **repo-side execution status snapshot**. Notion 项目控制塔
 | Phase | Status | Notes |
 |-------|--------|-------|
 | Phase 1 — Foundation | ✅ Done (Sprint 2) | See `docs/PHASE1_SPRINT2_COMPLETION.md` and `PHASE1_SPRINT1_COMPLETION.md`. |
-| Phase 1.5 — Foundation-Freeze (post-pivot) | 🟡 Active (governance baseline merged 2026-04-25; FF-06/07/08 enforcement open through 2026-05-23) | FF-01 (ADR-011), FF-02 (FailurePatterns), and FF-05 (STATE.md) all merged. FF-06/07/08 (path-guard, trailer-check, GS registry) are the remaining gate before Phase 2. |
-| Phase 2 — Web Console | ⏳ Planned (next active) | Gated by FF-06/07/08 (HF1 path-guard, HF5 trailer check, HF3 GS registry) per ADR-011 §Enforcement Maturity. |
+| Phase 1.5 — Foundation-Freeze (post-pivot) | 🟡 Active (governance baseline merged 2026-04-25; FF-07/08/09 + ADR-012/013 still open) | FF-01 (ADR-011 + amendments), FF-02 (FailurePatterns), FF-05 (STATE.md), FF-06 (HF1 path-guard) all merged. ADR-012 (PR #24) + ADR-013 (PR #25) in Codex-review queue. FF-07/08/09 remain pending. |
+| Phase 2 — Web Console | ⏳ Planned (next active) | Gated by FF-07/08/09 (HF5 trailer check, HF3 GS registry, README↔ADR-011 sync) per ADR-011 §Enforcement Maturity. |
 | Phase 3 — Nonlinear & adaptive mesh | ⚪ Planned | No dates committed. |
 
 ---
@@ -24,36 +24,52 @@ This file is the **repo-side execution status snapshot**. Notion 项目控制塔
 | Task | Status | Branch | Commit | Notes |
 |------|--------|--------|--------|-------|
 | FF-01 — ADR-011 Pivot baseline | ✅ Merged (PR #17 · 2026-04-25) · **R5 APPROVE** | (deleted post-merge) | `34722ea` (squash) | 5-round Codex arc; reports landed at `reports/codex_tool_reports/adr_011_r{1..5}_review.md`. |
+| FF-01a — ADR-011 amendments AR-2026-04-25-001 | ✅ Merged (PR #23 · 2026-04-25 12:06Z) · **R1 CR → R2 APPROVE** | (deleted post-merge) | `e53b0f7` (squash) | T2 rewording (Codex anti-shenanigans backstop + M1-M5 trigger taxonomy), §HF2 subagent split, §HF1 zone narrowing, §Enforcement Maturity post-FF-06 update, §Known Gaps ADR-012/013 number reassignment. R1 returned 3 BLOCKER + 1 SHOULD_FIX, fixed in commit `e96904d`. |
 | FF-01b — Notion Decisions DS sync | ✅ Done | (no branch — Notion API write) | n/a | Page id `34dc6894-2bed-81f0-bf9a-edceb840945d`. Discovered DS schema gap (missing `Branch`/`Session Batch`/`ADR Link`); see ADR-011 Risk #3. |
-| FF-02 — GS deviation attribution → FailurePatterns | ✅ Merged (PR #18 · 2026-04-25) | (deleted post-merge) | `77e6813` (squash) | 3 FPs (FP-001/002/003); recommends GS-001/002/003 → `insufficient_evidence`. Codex R1 (CHANGES_REQUIRED, 1 HIGH + 3 MEDIUM) → R2 APPROVE. |
+| FF-02 — GS deviation attribution → FailurePatterns | ✅ Merged (PR #18 · 2026-04-25) | (deleted post-merge) | `77e6813` (squash) | 3 FPs (FP-001/002/003); recommends GS-001/002/003 → `insufficient_evidence`. R1 (CR, 1 HIGH + 3 MEDIUM) → R2 APPROVE. |
 | FF-03 — Routing v6.2 doc (supersede Antigravity) | ⚪ Pending | — | — | Lower priority: ADR-011 already encodes the routing; this would be a thin pointer doc. |
 | FF-04 — Onboarding manual (Claude Code edition) | ⚪ Pending | — | — | New-contributor entry doc. |
-| FF-05 — STATE.md | ✅ Merged (PR #19 · 2026-04-25) | (deleted post-merge) | `4a64cfd` (squash) | Adopts `.planning/` directory convention from cfd-harness-unified. Codex R1 (CHANGES_REQUIRED, 1 HIGH stale-state + 1 MEDIUM ADR-012/013 inventions) → R2 APPROVE. |
-| FF-06 — pre-commit path-guard for HF1 forbidden zone | ⚪ Pending | — | — | Per ADR-011 §Enforcement Maturity. Hard deadline 2026-05-23. |
-| FF-07 — CI commit-trailer presence + claim-id format check (HF5) | ⚪ Pending | — | — | Same hard deadline. |
+| FF-05 — STATE.md | ✅ Merged (PR #19 · 2026-04-25) | (deleted post-merge) | `4a64cfd` (squash) | Adopts `.planning/` directory convention from cfd-harness-unified. R1 (CR, 1 HIGH stale-state + 1 MEDIUM ADR-012/013 inventions) → R2 APPROVE. |
+| FF-06 — pre-commit path-guard for HF1 forbidden zone | ✅ Merged (PR #22 · 2026-04-25 10:43Z) · **R1 CR → R2 APPROVE** | (deleted post-merge) | `ac98fc3` (squash) | `scripts/hf1_path_guard.py` + `tests/test_hf1_path_guard.py` (30 tests). R1 returned 1 BLOCKER (rename/delete bypass via `pass_filenames` default) + 2 SHOULD_FIX (HF1.6 over-block, override audit). Fixed via `--all-files` flag and HF1.6 scoping. |
+| FF-07 — CI commit-trailer presence + claim-id format check (HF5) | ⚪ Pending | — | — | Per ADR-011 §Enforcement Maturity. Hard deadline 2026-05-23. |
 | FF-08 — `golden_samples/<id>` registry schema validation (HF3) | ⚪ Pending | — | — | Same hard deadline. |
 | FF-09 — README ↔ ADR-011 sync (Golden Rules vs 5 dev rules) | ⚪ Pending | — | — | Reconcile partial overlap noted in ADR-011 §Cross-References. |
 
+### Governance ADRs in flight
+
+| ADR | Status | PR | Branch | Notes |
+|-----|--------|----|--------|-------|
+| **ADR-012 — Calibration cap for T1 self-pass-rate** | 🟡 OPEN, CI green, awaiting Codex R1 | **#24** | `feature/AI-FEA-ADR-012-calibration-cap` | Replaces RETRO-V61-001's honor-system with a mechanical 5-PR rolling-window ceiling. Bootstrap: 5/5 CR → ceiling 30%, BLOCKING. 42 unit tests passing. Self-applies its own gate — must reach R1=APPROVE before merge. |
+| **ADR-013 — Branch protection enforcement** | 🟡 OPEN, stacked on PR #24, awaiting Codex R1 | **#25** | `feature/AI-FEA-ADR-013-branch-protection` | 3-layer wrapper around ADR-012: PR template + CI `--check` workflow + `gh api` protection script. M1+M4+M5 triggers fire. Repo flipped private→public on 2026-04-25 to access protection API. CI doesn't run on this PR until #24 merges and base auto-rebases. |
+
 ---
 
-## Governance-chain branches (post-#17/#18/#19 merge · 2026-04-25)
+## Repo state
+
+`main == origin/main == e53b0f7` (post #17 + #18 + #19 + #20 + #21 + #22 + #23).
+
+Merge timeline 2026-04-25 (UTC):
 
 ```
-chore/post-merge-cleanup-state-and-codex-archive   (this PR — STATE.md self-update lag fix + Codex log archive)
-feature/AI-FEA-S2.1-02-notion-sync-contract-align  (origin tracked; WIP stashed in stash@{0} as of 2026-04-25 pivot session, not touched by FF-* work)
+07:56  #17  ADR-011 baseline                               (FF-01)
+07:56  #18  FailurePattern attribution                     (FF-02)
+07:56  #19  STATE.md seed                                  (FF-05)
+08:33  #20  Revert direct-push 815945c                     (governance hygiene)
+10:26  #21  Post-merge cleanup — STATE.md + Codex archive  (chore)
+10:43  #22  HF1 path-guard pre-commit                      (FF-06)
+12:06  #23  ADR-011 amendments AR-2026-04-25-001           (FF-01a)
 ```
 
-`main == origin/main == 4a64cfd` (after PR #20 revert + PR #17 ADR-011 + PR #18 FF-02 + PR #19 FF-05 merges).
-
 ## Open PRs (governance-chain · this session)
 
 | PR | Branch | Status |
 |----|--------|--------|
-| (this) | `chore/post-merge-cleanup-state-and-codex-archive` | OPEN · post-merge housekeeping; PR self-references STATE.md update — see commit message for the self-update-lag pattern |
+| #24 | `feature/AI-FEA-ADR-012-calibration-cap` | OPEN · CI green · CLEAN/MERGEABLE · awaiting Codex R1 (BLOCKING gate self-applied) |
+| #25 | `feature/AI-FEA-ADR-013-branch-protection` | OPEN · stacked on #24 (base will auto-rebase to main on #24 merge) · awaiting Codex R1 |
 
 ## Open PRs (Phase 1 sprint work · pre-pivot, not in governance chain)
 
-The following PRs were opened on 2026-04-18 and remain OPEN as of 2026-04-25. They are orthogonal to the Phase 1.5 governance pivot (PRs #17-#21) and are owned by their original sprint authors. STATE.md tracks them here for repo-wide situational awareness; **disposition (rebase / close / merge under ADR-006) is not in scope for the FF-* work** and will be handled separately.
+The following PRs were opened on 2026-04-18 and remain OPEN as of 2026-04-25. They are orthogonal to the Phase 1.5 governance pivot and are owned by their original sprint authors. STATE.md tracks them here for repo-wide situational awareness; **disposition (rebase / close / merge under ADR-006) is not in scope for the FF-* work** and will be handled separately.
 
 | PR | Branch | Title |
 |----|--------|-------|
@@ -64,7 +80,7 @@ The following PRs were opened on 2026-04-18 and remain OPEN as of 2026-04-25. Th
 | #15 | `feature/AI-FEA-P1-06b-wire-linter-solver` | AI-FEA-P1-06b: wire Gate-Solve linter into Solver node (stacked on #14) |
 | #16 | `feature/AI-FEA-P1-05-reviewer-fault-injection` | AI-FEA-P1-05: Reviewer fault-injection baseline + ADR-004 mirror |
 
-**Carry-over flag:** these PRs predate ADR-011 and therefore predate the T0/T1/T2 routing contract. Any rebase onto current main must (a) inherit ADR-011 § HF1-HF5 zoning, (b) decide whether their original review trail is sufficient or whether re-review under v6.2 is required. This is a separate decision from FF-06/07/08.
+**Carry-over flag:** these PRs predate ADR-011 and therefore predate the T0/T1/T2 routing contract. Any rebase onto current main must (a) inherit ADR-011 §HF1-HF5 zoning, (b) decide whether their original review trail is sufficient or whether re-review under v6.2 is required. This is a separate decision from FF-07/08/09 + ADR-012/013.
 
 ---
 
@@ -77,9 +93,12 @@ The following PRs were opened on 2026-04-18 and remain OPEN as of 2026-04-25. Th
 | ADR-005 | Live | (well_harness Notion writeback) |
 | ADR-008 | Live | (FreeCAD N-3 dummy guard, see `tools/freecad_driver.py`) |
 | ADR-010 | Live | (notion_sync contract — being aligned in S2.1-02) |
-| **ADR-011** | **Accepted (R5 APPROVE) · merged in main** | `docs/adr/ADR-011-pivot-claude-code-takeover.md` |
+| **ADR-011** | **Accepted (R5 APPROVE) · merged + amended (R1 CR → R2 APPROVE) on main** | `docs/adr/ADR-011-pivot-claude-code-takeover.md` (with AR-2026-04-25-001 amendments) |
+| **ADR-012** | **Drafted; awaiting Codex R1 on PR #24** | `docs/adr/ADR-012-calibration-cap-for-t1-self-pass-rate.md` (in `feature/AI-FEA-ADR-012-calibration-cap`) |
+| **ADR-013** | **Drafted; awaiting Codex R1 on PR #25** | `docs/adr/ADR-013-branch-protection-enforcement.md` (in `feature/AI-FEA-ADR-013-branch-protection`) |
+
+Two **further follow-up ADRs (numbers ADR-014 and beyond, not yet drafted)** are proposed in FP-001/002/003 cross-cutting findings + ADR-011 §Known Gaps:
 
-Two **follow-up ADRs (numbers TBD; not yet drafted)** are proposed in FP-001/002/003 cross-cutting findings + ADR-011 §Known Gaps:
 - "Golden-sample triplet contract" (README + `expected_results.json` + theory script as one calculator)
 - "Comparison-validity precondition for `REFERENCE_MISMATCH` retry routing"
 
@@ -89,10 +108,12 @@ These will be assigned numbers when drafted; do not pre-reserve ADR IDs.
 
 ## Carry-overs that ADR-011 R5 APPROVE does **not** make go away
 
-1. HF1 / HF5 enforcement is honor-system today (only `ruff` pre-commit + lint+pytest CI exist). Auto-detection is FF-06/07/08, deadline **2026-05-23**.
-2. `main` branch protection rules, PR review state machine, subagent failure SOP — all deferred to follow-up ADR candidates (numbers TBD; per ADR-011 §Known Gaps).
-3. Notion Decisions DS schema gap (`Branch` / `Session Batch` / `ADR Link` properties missing, `notion_sync.register_decision()` would fail against the live schema). S2.1-02's `Sprint` add does not address it. Needs separate ADR.
-4. GS-001/002/003 status flip pending_review → `insufficient_evidence` is **proposed in FP-001/002/003 only**; the Notion control-plane status field has not yet been changed. Action item attached to FF-02 PR merge.
+1. HF1 hard-stop is now enforced via FF-06 pre-commit (PR #22 ✅); the **PR-protected zone** (`docs/adr/`, `docs/governance/`, `.github/workflows/**`) relies on Codex M1 + branch protection (ADR-013 in flight, PR #25). HF5 (commit-trailer) auto-detection remains FF-07. Hard deadline **2026-05-23**.
+2. Branch protection rules + PR review state machine — proposed in ADR-013 (PR #25). Layer 3 activation (`bash scripts/apply_branch_protection.sh`) is a one-shot T0 action post-#25-merge.
+3. Subagent failure SOP — still deferred to a future ADR (number TBD).
+4. Notion Decisions DS schema gap (`Branch` / `Session Batch` / `ADR Link` properties missing, `notion_sync.register_decision()` would fail against the live schema). S2.1-02's `Sprint` add does not address it. Needs separate ADR.
+5. GS-001/002/003 status flip pending_review → `insufficient_evidence` is **proposed in FP-001/002/003 only**; the Notion control-plane status field has not yet been changed. Action item attached to FF-02 PR merge.
+6. Self-pass-rate honor-system (RETRO-V61-001) is empirically falsified by session 2026-04-25 (T1 estimated 80-95% on 5 PRs that all returned R1=CR). ADR-012 (PR #24) replaces it with a mechanical ceiling. Until #24 merges, T1 still operates under the falsified honor-system — i.e., this PR (#25) and the next few must explicitly cite the empirical 0/5 R1-pass-rate when self-rating.
 
 ---
 
@@ -106,4 +127,4 @@ Update STATE.md whenever:
 - A carry-over is closed (delete the line, don't strike-through — git history holds the trail).
 - The `Last updated` stamp must change in the same commit.
 
-Do **not** update STATE.md to reflect things that have not yet landed in the repo. Forward-looking commitments belong in the relevant ADR / task tracker, not here.
+**STATE.md must be updated in the SAME PR as the change it reflects** (FF-05 R1 lesson). Do **not** update STATE.md to reflect things that have not yet landed in the repo. Forward-looking commitments belong in the relevant ADR / task tracker, not here. PRs in flight may be listed under "Open PRs" but their status must reflect actual git state, not aspirations.
diff --git a/docs/adr/ADR-013-branch-protection-enforcement.md b/docs/adr/ADR-013-branch-protection-enforcement.md
new file mode 100644
index 0000000..ed6c9a6
--- /dev/null
+++ b/docs/adr/ADR-013-branch-protection-enforcement.md
@@ -0,0 +1,109 @@
+# ADR-013: Branch protection enforcement for the calibration cap
+
+- **Status:** Accepted
+- **Decider:** T0 / Opus 4.7 Architecture Gate (CFDJerry) per AR-2026-04-25-001
+- **Date:** 2026-04-25
+- **Related:** ADR-011 (parent), ADR-012 (calibration math — sibling), DEC-T0-2026-04-25-001 (Notion record)
+- **Branch:** `feature/AI-FEA-ADR-013-branch-protection`
+- **Repo-tier prerequisite:** repo must be **public** OR on **GitHub Pro** (required for branch protection + rulesets API). Repo was flipped from private→public on 2026-04-25 to satisfy this.
+
+---
+
+## Context
+
+ADR-012 defines a *calibration ceiling* (mechanical, derived from rolling 5-PR Codex R1 outcomes). That math is meaningless if T1 can self-merge under any ceiling — including 30%/BLOCKING. Session 2026-04-25 demonstrated empirically that T1 wrote `95%` self-estimates five times in a row while Codex was actively returning CHANGES_REQUIRED on each PR. The honor-system has zero enforcement surface; the calibration cap needs a wrapper that physically prevents T1 from merging when the gate is BLOCKING and that surfaces the gate's claim-vs-ceiling check on every PR.
+
+ADR-013 is that wrapper.
+
+## Decision
+
+Enforce ADR-012's gate via three concentric layers:
+
+### Layer 1 — PR template (`.github/PULL_REQUEST_TEMPLATE.md`)
+
+Every PR is opened from a template that:
+
+- Reserves a section labeled `## Self-pass-rate (mechanically derived)`.
+- Instructs the author to fill it from `python3 scripts/compute_calibration_cap.py`'s output, **never from intuition**.
+- Forces the author to tick exactly one Codex pre-merge gate level (BLOCKING / MANDATORY / RECOMMENDED / OPTIONAL).
+- Forces the author to tick any ADR-011 §T2 M1-M5 mandatory triggers that fire (independent override).
+- Includes a `## Test plan` section validated by reviewers.
+
+The template is only a *prompt*; the actual enforcement is in Layer 2.
+
+### Layer 2 — CI workflow (`.github/workflows/calibration-cap-check.yml`)
+
+Triggered on every `pull_request` event (`opened` / `edited` / `synchronize` / `reopened`):
+
+1. Computes the current ceiling via `compute_calibration_cap.py`.
+2. Extracts the claimed ceiling from the PR body via `scripts/extract_pr_self_pass_rate.py`.
+3. Runs `compute_calibration_cap.py --check <claim>` — exits non-zero if the claim exceeds the ceiling.
+
+Result: a PR whose body claims 80% while the formula says 30% fails CI. The author cannot fix this by editing the body to a higher number — only by either correcting downward to ≤ ceiling or by adding R1=APPROVE entries to `calibration_state.json` (which requires merging clean PRs first, which require Codex review, which is the whole point).
+
+### Layer 3 — GitHub branch protection (`scripts/apply_branch_protection.sh`)
+
+A protection ruleset on `main` requires:
+
+- **`required_status_checks`** = `["lint-and-test (3.11)", "calibration-cap-check"]` with `strict: true` (PR must be up-to-date with main before merge).
+- **`required_linear_history`** = `true` — squash-only style, no merge commits.
+- **`allow_force_pushes`** = `false`, **`allow_deletions`** = `false` — protect against accidental destruction of main.
+- **`required_conversation_resolution`** = `true` — Codex review threads must be resolved.
+- **`enforce_admins`** = `false` — T0 (the human admin) retains emergency override. Justification: solo-developer setup; without admin override, any CI infrastructure breakage would brick the repo. ADR-013's discipline is procedural, not coercive at the admin level.
+- **`required_pull_request_reviews`** = `null` — solo-dev; Codex (via the M1-M5 + ceiling gate) is the de facto reviewer rather than a human approver. Adding a human-required-review on a single-author repo would just stamp the author's own approvals.
+
+### Discipline binding (T1 contract)
+
+The gate cannot mechanically prevent admin-bypass merges by T1 acting through the user's authenticated `gh` CLI. This residual loophole is closed by **discipline**:
+
+> **T1 must NOT merge a PR while its ceiling-derived gate is BLOCKING (30%) unless either:**
+> **(a) Codex Round 1 returned `APPROVE` (or `APPROVE_WITH_NITS` with all nits resolved) on the latest commit, OR**
+> **(b) T0 (the human) explicitly authorizes the merge in writing in the conversation, citing the BLOCKING state.**
+
+Any T1 merge that violates this contract is a P0 procedural failure and triggers a retro entry per RETRO cadence rules. Layer 1 + 2 surface the BLOCKING state in CI and PR template so T1 cannot plausibly miss it; Layer 3 makes the merge *physically possible* only via deliberate admin-bypass *that T1 has no business invoking*.
+
+## Implementation contract
+
+| File | Purpose |
+|---|---|
+| `.github/PULL_REQUEST_TEMPLATE.md` | Layer 1 — PR template |
+| `.github/workflows/calibration-cap-check.yml` | Layer 2 — CI claim-vs-ceiling check |
+| `scripts/extract_pr_self_pass_rate.py` | Layer 2 — PR body parser (16 unit tests) |
+| `scripts/apply_branch_protection.sh` | Layer 3 — idempotent protection setup |
+| `docs/adr/ADR-013-branch-protection-enforcement.md` | This doc |
+
+## Activation sequence
+
+1. **Land this PR via Codex R1=APPROVE.** Layers 1 and 2 take effect on merge (template applies to subsequent PRs; CI workflow runs on subsequent PRs).
+2. **T0 runs** `bash scripts/apply_branch_protection.sh` once after merge. Layer 3 takes effect immediately; from this moment forward, no merge to main can land without `lint-and-test (3.11)` + `calibration-cap-check` both green.
+3. **Subsequent PRs** open from the new template; the calibration-cap-check workflow validates each automatically.
+
+The bootstrap PR for ADR-013 itself (this PR) is NOT subject to Layer 2 yet because the workflow file lands as part of this PR — GitHub doesn't run workflow files that don't exist on the base branch yet. ADR-012's PR (#24) is also NOT subject to Layer 2 for the same reason. **Both PRs land under Layer 0 (no enforcement) but are required by ADR-012/AR-2026-04-25-001 §1 to reach Codex R1=APPROVE before merge** — the discipline binding above applies retroactively to the same session that authored these ADRs.
+
+## Consequences
+
+**Intended:**
+
+- T1's mechanical ceiling becomes physically enforced at PR-merge time once Layer 3 is on. CI red blocks merge.
+- Layer 1 + 2 produce a clear paper trail: every PR body declares a ceiling; CI validates it; the validation result is part of the PR's check history.
+- Layer 3 prevents accidental force-push or deletion of main (defense against the same class of error that produced PR #20's revert).
+- The discipline binding turns the residual admin-bypass into a documented retro-eligible event rather than a silent loophole.
+
+**Acknowledged:**
+
+- `enforce_admins: false` means a determined or careless admin can bypass everything. This is a deliberate trade-off for solo-dev recoverability; revisit if/when the project grows to multi-author.
+- Layer 3 doesn't run until after this PR merges (chicken-and-egg). The first two ADR PRs (#24 and this one) ride on Layer 0 = nothing. ADR-012/013 is therefore a *prospective* gate, not retroactive.
+- The CI check uses GitHub's `pull_request.body` field, which can be edited freely. An author could in principle merge a PR, then edit the body to game future tooling. The state file (Layer 0 of ADR-012) is the actual source of truth, not the body claim. The body claim is just a checksum.
+- Repo had to be made public to access protection APIs on the free tier. Future-proof: if the project ever needs to go private again, options are (a) GitHub Pro, (b) move to GitLab (free private branch protection), (c) drop Layer 3 and rely on Layer 1 + 2 + discipline alone.
+
+**Out of scope:**
+
+- Multi-reviewer / CODEOWNERS enforcement (single-author repo, no value yet).
+- Signed-commit requirements (would block T1's automated commits without GPG keypair setup).
+- Blocking direct push to feature branches (low value; force-push protection on main is enough).
+
+## Open follow-ups
+
+- After 10 post-ADR-013 PRs, audit: did the `calibration-cap-check` job ever fail? Did it ever falsely pass? Sample 3 PR bodies to confirm the template was followed.
+- Consider extending the workflow to also scrape ADR-011 §T2 M1-M5 checkboxes; if any is ticked, require a `Codex-Approved-By:` trailer in the merge commit.
+- If a future PR rewords the `Self-pass-rate` heading, add a heading-rename safety check to `extract_pr_self_pass_rate.py` (currently tolerates `Self-pass-rate` and `Self pass rate` only).
diff --git a/scripts/apply_branch_protection.sh b/scripts/apply_branch_protection.sh
new file mode 100755
index 0000000..fddb340
--- /dev/null
+++ b/scripts/apply_branch_protection.sh
@@ -0,0 +1,46 @@
+#!/usr/bin/env bash
+# ADR-013: applies the protection ruleset to main.
+#
+# Idempotent — re-running with the same settings is a no-op.
+# Requires: `gh` authenticated as a user with admin permission on the repo.
+#
+# Settings rationale (see ADR-013 §"Protection ruleset"):
+# - required_status_checks: lint-and-test (3.11) + calibration-cap-check
+# - enforce_admins: false        (T0 retains emergency override)
+# - required_pull_request_reviews: null  (solo-dev — Codex is the de facto reviewer)
+# - allow_force_pushes: false
+# - allow_deletions: false
+# - required_linear_history: true        (squash-only style)
+# - lock_branch: false
+# - required_conversation_resolution: true
+
+set -euo pipefail
+
+REPO="${1:-kogamishinyajerry-ops/ai-structure-analysis}"
+BRANCH="${2:-main}"
+
+echo "Applying branch protection to $REPO:$BRANCH ..."
+
+gh api -X PUT "repos/$REPO/branches/$BRANCH/protection" \
+  --input - <<'JSON'
+{
+  "required_status_checks": {
+    "strict": true,
+    "contexts": ["lint-and-test (3.11)", "calibration-cap-check"]
+  },
+  "enforce_admins": false,
+  "required_pull_request_reviews": null,
+  "restrictions": null,
+  "required_linear_history": true,
+  "allow_force_pushes": false,
+  "allow_deletions": false,
+  "required_conversation_resolution": true,
+  "lock_branch": false,
+  "allow_fork_syncing": true
+}
+JSON
+
+echo
+echo "Protection applied. Verifying..."
+gh api "repos/$REPO/branches/$BRANCH/protection" \
+  --jq '{checks: .required_status_checks.contexts, enforce_admins: .enforce_admins.enabled, linear: .required_linear_history.enabled, force_push: .allow_force_pushes.enabled, deletions: .allow_deletions.enabled}'
diff --git a/scripts/extract_pr_self_pass_rate.py b/scripts/extract_pr_self_pass_rate.py
new file mode 100644
index 0000000..227ff83
--- /dev/null
+++ b/scripts/extract_pr_self_pass_rate.py
@@ -0,0 +1,103 @@
+"""Extract the claimed Self-pass-rate from a PR body.
+
+The PR template (per ADR-013) reserves a section labeled
+"Self-pass-rate (mechanically derived)" whose first line contains the
+claimed ceiling as `**N%**` (or just `N%`). This helper extracts that
+integer so CI can pass it to compute_calibration_cap.py --check.
+
+R2 hardening (post Codex R1, 2026-04-26): hidden-marker bypass closed.
+The previous regex matched the FIRST `N%` within 600 chars of the
+heading without distinguishing visible markdown from hidden constructs.
+A PR body like:
+
+    ## Self-pass-rate
+
+    <!-- 30% -->
+
+    **95%**
+
+would parse as `30` while a human reviewer sees `95`. Codex reproduced
+this exact case. Fix: strip HTML comments AND fenced code blocks
+(triple-backtick OR triple-tilde) BEFORE searching, so only visible
+markdown contributes a candidate.
+
+Usage:
+    python3 scripts/extract_pr_self_pass_rate.py < pr_body.txt
+    cat pr_body.txt | python3 scripts/extract_pr_self_pass_rate.py
+    echo "$PR_BODY" | python3 scripts/extract_pr_self_pass_rate.py
+
+Prints the integer claim on stdout (one line, no `%`). Exits non-zero if
+no claim found in the body.
+"""
+
+from __future__ import annotations
+
+import re
+import sys
+
+# R2 hidden-content strippers — order matters (HTML comments may
+# legitimately appear inside fenced code, and we want both gone).
+# All use re.DOTALL so multi-line constructs are scrubbed.
+_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
+_FENCED_BACKTICK_RE = re.compile(r"```.*?```", re.DOTALL)
+_FENCED_TILDE_RE = re.compile(r"~~~.*?~~~", re.DOTALL)
+_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
+
+# Match the Self-pass-rate section heading then the first \d+% within
+# the next ~600 chars (one paragraph block). Tolerates `## Self-pass-rate`,
+# `### Self-pass-rate`, with-or-without trailing parenthetical.
+_HEADING_RE = re.compile(
+    r"(?im)^\s{0,3}#{2,4}\s*Self[- ]pass[- ]rate\b[^\n]*\n",
+)
+_PERCENT_RE = re.compile(r"\b(\d{1,3})\s*%")
+
+
+def _strip_hidden_constructs(body: str) -> str:
+    """Remove HTML comments + fenced code blocks + inline-code spans.
+
+    Pinned by adversarial tests in tests/test_extract_pr_self_pass_rate.py.
+    """
+    body = _HTML_COMMENT_RE.sub("", body)
+    body = _FENCED_BACKTICK_RE.sub("", body)
+    body = _FENCED_TILDE_RE.sub("", body)
+    body = _INLINE_CODE_RE.sub("", body)
+    return body
+
+
+def extract_claim(body: str) -> int | None:
+    """Return the integer claim (0-100) or None if not found.
+
+    Strips hidden markdown constructs (HTML comments, fenced and inline
+    code) before matching, so the parsed claim must equal what a human
+    reviewer sees.
+    """
+    body = _strip_hidden_constructs(body)
+    heading = _HEADING_RE.search(body)
+    if not heading:
+        return None
+    tail = body[heading.end() : heading.end() + 600]
+    m = _PERCENT_RE.search(tail)
+    if not m:
+        return None
+    val = int(m.group(1))
+    if not 0 <= val <= 100:
+        return None
+    return val
+
+
+def main(argv: list[str]) -> int:
+    body = sys.stdin.read()
+    claim = extract_claim(body)
+    if claim is None:
+        print(
+            "ERROR: PR body does not contain a 'Self-pass-rate' section "
+            "with a `N%` claim. ADR-013 requires this section in every PR.",
+            file=sys.stderr,
+        )
+        return 2
+    print(claim)
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main(sys.argv))
diff --git a/tests/test_extract_pr_self_pass_rate.py b/tests/test_extract_pr_self_pass_rate.py
new file mode 100644
index 0000000..5d4e4fa
--- /dev/null
+++ b/tests/test_extract_pr_self_pass_rate.py
@@ -0,0 +1,279 @@
+"""Tests for scripts/extract_pr_self_pass_rate.py (ADR-013)."""
+
+from __future__ import annotations
+
+import sys
+from pathlib import Path
+
+import pytest
+
+_REPO_ROOT = Path(__file__).resolve().parent.parent
+_SCRIPTS_DIR = _REPO_ROOT / "scripts"
+if str(_SCRIPTS_DIR) not in sys.path:
+    sys.path.insert(0, str(_SCRIPTS_DIR))
+
+
+def _load():
+    import extract_pr_self_pass_rate  # type: ignore[import-not-found]
+
+    return extract_pr_self_pass_rate
+
+
+@pytest.fixture(scope="module")
+def mod():
+    return _load()
+
+
+# ---------------------------------------------------------------------------
+# Happy paths
+# ---------------------------------------------------------------------------
+
+
+def test_h2_with_parenthetical_bold_percent(mod):
+    body = """## Summary
+Stuff.
+
+## Self-pass-rate (mechanically derived)
+
+**30%** · BLOCKING · pre-merge Codex MANDATORY · derivation in state file.
+
+## Test plan
+- [x] tests
+"""
+    assert mod.extract_claim(body) == 30
+
+
+def test_h2_plain_percent(mod):
+    body = "## Self-pass-rate\n\n80%\n"
+    assert mod.extract_claim(body) == 80
+
+
+def test_h3_heading(mod):
+    body = "### Self-pass-rate\n95%\n"
+    assert mod.extract_claim(body) == 95
+
+
+def test_heading_with_space(mod):
+    """Tolerate 'Self pass rate' with spaces."""
+    body = "## Self pass rate\n\n50%\n"
+    assert mod.extract_claim(body) == 50
+
+
+def test_picks_first_percent_after_heading(mod):
+    body = "## Self-pass-rate\n\n**80%** baseline (raised from 50% earlier).\n"
+    assert mod.extract_claim(body) == 80
+
+
+def test_zero_percent_is_valid(mod):
+    body = "## Self-pass-rate\n\n0%\n"
+    assert mod.extract_claim(body) == 0
+
+
+def test_one_hundred_percent_is_valid(mod):
+    body = "## Self-pass-rate\n\n100%\n"
+    assert mod.extract_claim(body) == 100
+
+
+# ---------------------------------------------------------------------------
+# Unhappy paths
+# ---------------------------------------------------------------------------
+
+
+def test_no_heading_returns_none(mod):
+    body = "## Summary\n\nWe have 95% confidence here.\n"
+    assert mod.extract_claim(body) is None
+
+
+def test_heading_without_percent_returns_none(mod):
+    body = "## Self-pass-rate\n\nTBD — script will fill in.\n"
+    assert mod.extract_claim(body) is None
+
+
+def test_above_100_rejected(mod):
+    body = "## Self-pass-rate\n\n150%\n"
+    assert mod.extract_claim(body) is None
+
+
+def test_h1_heading_rejected(mod):
+    """Single-# heading must NOT match (PR body sections are h2+)."""
+    body = "# Self-pass-rate\n\n95%\n"
+    assert mod.extract_claim(body) is None
+
+
+def test_inline_mention_rejected(mod):
+    """Mentioning self-pass-rate in prose must not match."""
+    body = "## Summary\n\nThe self-pass-rate is 95% trust me bro.\n"
+    assert mod.extract_claim(body) is None
+
+
+def test_empty_body_returns_none(mod):
+    assert mod.extract_claim("") is None
+
+
+def test_percent_too_far_after_heading_ignored(mod):
+    """Search window is bounded so a wandering paragraph doesn't pollute."""
+    body = "## Self-pass-rate\n\n" + ("filler. " * 200) + "95%\n"
+    assert mod.extract_claim(body) is None
+
+
+# ---------------------------------------------------------------------------
+# CLI
+# ---------------------------------------------------------------------------
+
+
+def test_cli_prints_claim(mod, capsys, monkeypatch):
+    monkeypatch.setattr("sys.stdin", _StdinShim("## Self-pass-rate\n\n30%\n"))
+    rc = mod.main([])
+    captured = capsys.readouterr()
+    assert rc == 0
+    assert captured.out.strip() == "30"
+
+
+def test_cli_exits_2_when_no_claim(mod, capsys, monkeypatch):
+    monkeypatch.setattr("sys.stdin", _StdinShim("## Summary\n\nNo claim here.\n"))
+    rc = mod.main([])
+    captured = capsys.readouterr()
+    assert rc == 2
+    assert "Self-pass-rate" in captured.err
+
+
+class _StdinShim:
+    def __init__(self, text: str):
+        self._text = text
+
+    def read(self) -> str:
+        return self._text
+
+
+# ---------------------------------------------------------------------------
+# R2 hardening — adversarial hidden-marker bypass cases (Codex R1 HIGH #2)
+# ---------------------------------------------------------------------------
+
+
+def test_r2_html_comment_bypass_codex_repro(mod):
+    """The exact Codex reproduction: hidden 30% via HTML comment, visible 95%.
+
+    Before R2: returned 30 (hidden marker). After R2: returns 95 (visible).
+    """
+    body = "## Self-pass-rate\n\n<!-- 30% -->\n\n**95%**\n"
+    assert mod.extract_claim(body) == 95
+
+
+def test_r2_html_comment_with_only_hidden_returns_none(mod):
+    """If the only `N%` after the heading is inside an HTML comment,
+    the result must be None (no visible claim)."""
+    body = "## Self-pass-rate\n\n<!-- 30% -->\n\nTBD.\n"
+    assert mod.extract_claim(body) is None
+
+
+def test_r2_multiline_html_comment_stripped(mod):
+    body = """## Self-pass-rate
+
+<!--
+This is a multi-line comment
+with a hidden 50% claim.
+-->
+
+80%
+"""
+    assert mod.extract_claim(body) == 80
+
+
+def test_r2_fenced_backtick_code_bypass(mod):
+    """A fenced code block hiding `30%` must not be the parsed claim."""
+    body = """## Self-pass-rate
+
+```
+30%
+```
+
+95%
+"""
+    assert mod.extract_claim(body) == 95
+
+
+def test_r2_fenced_tilde_code_bypass(mod):
+    """Tilde fences (~~~) are also treated as code blocks."""
+    body = """## Self-pass-rate
+
+~~~
+30%
+~~~
+
+95%
+"""
+    assert mod.extract_claim(body) == 95
+
+
+def test_r2_fenced_with_language_tag(mod):
+    """```python ... ``` should also be stripped."""
+    body = """## Self-pass-rate
+
+```python
+SELF_PASS_RATE = "30%"
+```
+
+**80%**
+"""
+    assert mod.extract_claim(body) == 80
+
+
+def test_r2_inline_code_bypass(mod):
+    """Inline code spans like `30%` must not be the parsed claim."""
+    body = "## Self-pass-rate\n\nExample: `30%`. Actual: **75%**\n"
+    assert mod.extract_claim(body) == 75
+
+
+def test_r2_combined_bypass_attempts(mod):
+    """A bad-faith body using multiple hidden constructs at once."""
+    body = """## Self-pass-rate
+
+<!-- 30% -->
+
+```
+50%
+```
+
+`60%`
+
+<!-- 70% -->
+
+**95%**
+"""
+    assert mod.extract_claim(body) == 95
+
+
+def test_r2_only_hidden_constructs_returns_none(mod):
+    """If every `N%` is hidden, no claim is found."""
+    body = """## Self-pass-rate
+
+<!-- 30% -->
+
+```
+80%
+```
+
+`95%`
+"""
+    assert mod.extract_claim(body) is None
+
+
+def test_r2_html_comment_before_heading_does_not_consume_heading(mod):
+    """Make sure stripping an HTML comment doesn't accidentally remove
+    text adjacent to the section heading."""
+    body = "<!-- TODO: revisit -->\n\n## Self-pass-rate\n\n50%\n"
+    assert mod.extract_claim(body) == 50
+
+
+def test_r2_multiple_self_pass_rate_sections(mod):
+    """If a body has two Self-pass-rate sections (template + copy-paste
+    artifact), the FIRST visible claim wins."""
+    body = """## Self-pass-rate
+
+50%
+
+## Self-pass-rate
+
+80%
+"""
+    assert mod.extract_claim(body) == 50

codex
The PR metadata is consistent with the claimed R2 fixes. I’m reading the head revisions line-by-line now so I can verify the specific failure modes and cite exact lines, then I’ll run a few targeted checks around the calibration path and extractor behavior.
exec
/bin/zsh -lc "git show 3d97d30732df51b0430110afb7d7828f4716b66c:reports/calibration_state.json | nl -ba | sed -n '1,140p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
exec
/bin/zsh -lc "git show 3d97d30732df51b0430110afb7d7828f4716b66c:scripts/compute_calibration_cap.py | nl -ba | sed -n '1,260p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
exec
/bin/zsh -lc "git show 20b8c003c284c72282175b34f9d5b096a851437c:scripts/extract_pr_self_pass_rate.py | nl -ba | sed -n '1,220p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
exec
/bin/zsh -lc "git show 20b8c003c284c72282175b34f9d5b096a851437c:.github/workflows/calibration-cap-check.yml | nl -ba | sed -n '1,220p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
     1	{
     2	  "schema_version": 1,
     3	  "established_by": "ADR-012 / AR-2026-04-25-001 / DEC-T0-2026-04-25-001",
     4	  "doc": "Append-only state for T1 calibration cap. Entries are ordered by `merged_at` (ISO 8601) at read time — PR-number is NOT a reliable proxy for merge order (PR #20 merged before #18 and #19 on 2026-04-25). Last 5 entries determine the ceiling per AR-2026-04-25-001 §1 formula. Pre-ADR-011-baseline PRs excluded; PR #17 (the ADR-011 establishment) is also excluded as bootstrap baseline per T0 verdict. R2 contract (post Codex R1, 2026-04-26): the load path FAILS CLOSED on missing file, schema_version mismatch, duplicate `pr`, missing `merged_at`, or unknown `r1_outcome`.",
     5	  "outcome_canon": "APPROVE | APPROVE_WITH_NITS | CHANGES_REQUIRED | BLOCKER (NITS counts as APPROVE; CR/BLOCKER count as CHANGES_REQUIRED)",
     6	  "entries": [
     7	    {
     8	      "pr": 18,
     9	      "sha": "77e6813",
    10	      "title": "[FF-02] FailurePattern attribution for GS-001/002/003",
    11	      "merged_at": "2026-04-25T08:53:09Z",
    12	      "r1_outcome": "CHANGES_REQUIRED",
    13	      "r1_severity": "1 HIGH + 3 MEDIUM",
    14	      "r1_review_report": "reports/codex_tool_reports/ff02_r1_review.md",
    15	      "notes": "Over-claim/prescription, gs_artifact_pin placeholder, HF3 cite inconsistency, README severity scope"
    16	    },
    17	    {
    18	      "pr": 19,
    19	      "sha": "4a64cfd",
    20	      "title": "[FF-05] Seed .planning/STATE.md as repo-side execution snapshot",
    21	      "merged_at": "2026-04-25T08:56:46Z",
    22	      "r1_outcome": "CHANGES_REQUIRED",
    23	      "r1_severity": "1 HIGH + 1 MEDIUM",
    24	      "r1_review_report": "reports/codex_tool_reports/ff05_r1_review.md",
    25	      "notes": "STATE.md still pre-push state (FF-01/FF-02 listed as pending); invented ADR-012/013 references"
    26	    },
    27	    {
    28	      "pr": 20,
    29	      "sha": "9362f6d",
    30	      "title": "Revert direct-push 815945c, preserve portable-path fixes",
    31	      "merged_at": "2026-04-25T08:33:51Z",
    32	      "r1_outcome": "CHANGES_REQUIRED",
    33	      "r1_severity": "1 BLOCKER + 2 SHOULD_FIX",
    34	      "r1_review_report": "reports/codex_tool_reports/revert_815945c_r1_review.md",
    35	      "notes": "Revert direction inversion (re-introduced /Users/Zhuanz/ paths); commit message factual error; CI claim overstated"
    36	    },
    37	    {
    38	      "pr": 21,
    39	      "sha": "2bbf0f1",
    40	      "title": "chore: post-merge cleanup — STATE.md + Codex review archive",
    41	      "merged_at": "2026-04-25T10:30:14Z",
    42	      "r1_outcome": "CHANGES_REQUIRED",
    43	      "r1_severity": "1 HIGH",
    44	      "r1_review_report": null,
    45	      "r1_review_report_pending_archive": true,
    46	      "notes": "STATE.md Active branches/Open PRs sections underreported (P1-* PRs #11-#16 missing); R1 review still in /tmp/, awaits next housekeeping cycle"
    47	    },
    48	    {
    49	      "pr": 22,
    50	      "sha": "ac98fc3",
    51	      "title": "[FF-06] pre-commit path-guard for HF1 forbidden zone",
    52	      "merged_at": "2026-04-25T10:43:55Z",
    53	      "r1_outcome": "CHANGES_REQUIRED",
    54	      "r1_severity": "1 BLOCKER + 2 SHOULD_FIX",
    55	      "r1_review_report": null,
    56	      "r1_review_report_pending_archive": true,
    57	      "notes": "pre-commit pass_filenames misses rename old-paths and deletes (silent HF1 bypass); HF1.6 over-blocks Makefile other targets; override audit trail unenforceable"
    58	    },
    59	    {
    60	      "pr": 23,
    61	      "sha": "e53b0f7",
    62	      "title": "[ADR-011] T0 amendments AR-2026-04-25-001 (T2 + HF1 + HF2 + numbering)",
    63	      "merged_at": "2026-04-25T12:06:52Z",
    64	      "r1_outcome": "CHANGES_REQUIRED",
    65	      "r1_severity": "3 BLOCKER + 1 SHOULD_FIX",
    66	      "r1_review_report": null,
    67	      "r1_review_report_pending_archive": true,
    68	      "notes": "ADR-011 amendments PR — Codex R1 returned 3 BLOCKER + 1 SHOULD_FIX, fixed in commit e96904d, then merged after CI green. R1 review report still pending archive into reports/codex_tool_reports/."
    69	    }
    70	  ],
    71	  "computed_at_bootstrap": {
    72	    "last_5_cr_count": 5,
    73	    "trailing_approve_count": 0,
    74	    "base_ceiling": 30,
    75	    "final_ceiling": 30,
    76	    "mandatory_codex": true,
    77	    "blocking": true,
    78	    "basis": "5 of last 5 = CHANGES_REQUIRED → ceiling 30%"
    79	  }
    80	}

 succeeded in 0ms:
     1	#!/usr/bin/env python3
     2	"""Calibration cap computation for T1 self-pass-rate (ADR-012 · AR-2026-04-25-001).
     3	
     4	Replaces RETRO-V61-001's per-PR honesty discipline with a mechanical formula
     5	derived from the rolling window of the last 5 PRs' Codex Round 1 outcomes.
     6	T1 cannot self-rate; T1 reads the ceiling. PR template prefills the
     7	self-pass field by calling this script; the field is read-only to T1.
     8	
     9	Formula (canonical, ratified in AR-2026-04-25-001 §1):
    10	
    11	    Rolling window:  last 5 PRs to main, ordered by `merged_at` (ISO 8601).
    12	                     ≥ ADR-011 baseline; pre-ADR excluded.
    13	    Outcome canon:   APPROVE | APPROVE_WITH_NITS | CHANGES_REQUIRED | BLOCKER
    14	                     (NITS counts as APPROVE; CR/BLOCKER count as CHANGES_REQUIRED)
    15	
    16	    Base ceiling (per next PR):
    17	      0 of last 5 = CR  → 95%  · honor system   · pre-merge Codex OPTIONAL
    18	      1-2 of last 5     → 80%  · pre-merge Codex RECOMMENDED
    19	      3-4 of last 5     → 50%  · pre-merge Codex MANDATORY
    20	      5 of last 5       → 30%  · pre-merge Codex MANDATORY · BLOCKING
    21	
    22	    Recovery (override):
    23	      2 consecutive R1=APPROVE  → ceiling steps up one rung from base
    24	      3 consecutive R1=APPROVE  → ceiling returns to 95%
    25	
    26	Invocations:
    27	    python3 scripts/compute_calibration_cap.py
    28	        emits JSON to stdout (ceiling, mandatory_codex, blocking, basis, entry_count)
    29	    python3 scripts/compute_calibration_cap.py --human
    30	        emits human-readable summary to stdout
    31	    python3 scripts/compute_calibration_cap.py --check <CEILING>
    32	        exits 1 if claimed CEILING > computed ceiling (PR-template / CI use)
    33	
    34	State source: reports/calibration_state.json (append-only, hard-validated).
    35	The script is a pure function over its contents and FAILS CLOSED on any
    36	shape violation: missing file, schema mismatch, duplicate PR, missing
    37	merged_at, unknown outcome — all exit non-zero with a clear stderr message.
    38	
    39	Honesty caveat (T0 self-rated 88% on ratification): the recovery thresholds
    40	(2 → step up, 3 → reset) are reasonable but not empirically grounded yet;
    41	revisit after 10 more PRs of post-ADR-012 data.
    42	
    43	R2 changes (post Codex R1 CHANGES_REQUIRED, 2026-04-26):
    44	  * load_state() now sorts by merged_at, not PR number — the repo already
    45	    has a counterexample (PR #20 merged before #18 and #19).
    46	  * Missing/malformed state file is now a hard error (was: returned [] →
    47	    fail-open at 95%/OPTIONAL).
    48	  * schema_version, duplicate PRs, missing merged_at, and unknown outcomes
    49	    are all hard-validated.
    50	"""
    51	
    52	from __future__ import annotations
    53	
    54	import argparse
    55	import json
    56	import sys
    57	from dataclasses import dataclass
    58	from pathlib import Path
    59	
    60	# Canonical: NITS counts as APPROVE; everything else (CR, BLOCKER) counts as CR.
    61	APPROVE_OUTCOMES = frozenset({"APPROVE", "APPROVE_WITH_NITS"})
    62	CANONICAL_OUTCOMES = frozenset({"APPROVE", "APPROVE_WITH_NITS", "CHANGES_REQUIRED", "BLOCKER"})
    63	
    64	# Rung ladder, low → high. Recovery moves one index up.
    65	RUNGS: tuple[int, ...] = (30, 50, 80, 95)
    66	
    67	# Schema version this script supports. Bump only with a corresponding ADR.
    68	SUPPORTED_SCHEMA_VERSION = 1
    69	
    70	
    71	class CalibrationStateError(Exception):
    72	    """Hard error reading or validating the calibration state file."""
    73	
    74	
    75	@dataclass(frozen=True)
    76	class CalibrationResult:
    77	    ceiling: int
    78	    mandatory_codex: bool
    79	    blocking: bool
    80	    basis: str
    81	    entry_count: int
    82	
    83	
    84	def step_up(ceiling: int) -> int:
    85	    """Move ceiling one rung up (saturate at 95)."""
    86	    if ceiling not in RUNGS:
    87	        raise ValueError(f"unknown ceiling rung: {ceiling}")
    88	    idx = RUNGS.index(ceiling)
    89	    return RUNGS[min(idx + 1, len(RUNGS) - 1)]
    90	
    91	
    92	def base_ceiling_from_cr_count(cr_count: int) -> int:
    93	    """Map count of CHANGES_REQUIRED in last 5 entries to base ceiling.
    94	
    95	    Per AR-2026-04-25-001 §1.
    96	    """
    97	    if cr_count < 0:
    98	        raise ValueError(f"cr_count must be >= 0, got {cr_count}")
    99	    if cr_count == 0:
   100	        return 95
   101	    if cr_count <= 2:
   102	        return 80
   103	    if cr_count <= 4:
   104	        return 50
   105	    return 30
   106	
   107	
   108	def trailing_approve_count(outcomes: list[str]) -> int:
   109	    """Count consecutive APPROVE/NITS at the END of the list (most recent first)."""
   110	    n = 0
   111	    for o in reversed(outcomes):
   112	        if o in APPROVE_OUTCOMES:
   113	            n += 1
   114	        else:
   115	            break
   116	    return n
   117	
   118	
   119	def compute_calibration(outcomes: list[str]) -> CalibrationResult:
   120	    """Compute calibration ceiling from a chronologically-ordered list of R1 outcomes."""
   121	    last5 = outcomes[-5:]
   122	    cr_count = sum(1 for o in last5 if o not in APPROVE_OUTCOMES)
   123	    base = base_ceiling_from_cr_count(cr_count)
   124	    trailing = trailing_approve_count(outcomes)
   125	
   126	    if trailing >= 3:
   127	        ceiling = 95
   128	        basis = "3+ trailing APPROVE → ceiling reset to 95% (recovery)"
   129	    elif trailing >= 2:
   130	        stepped = step_up(base)
   131	        ceiling = stepped
   132	        basis = (
   133	            f"{cr_count} of last 5 = CHANGES_REQUIRED (base {base}%) + "
   134	            f"2 trailing APPROVE → step up to {ceiling}%"
   135	        )
   136	    else:
   137	        ceiling = base
   138	        basis = f"{cr_count} of last 5 = CHANGES_REQUIRED → ceiling {ceiling}%"
   139	
   140	    # Codex gate derivation from final ceiling
   141	    if ceiling <= 30:
   142	        mandatory_codex = True
   143	        blocking = True
   144	    elif ceiling <= 50:
   145	        mandatory_codex = True
   146	        blocking = False
   147	    else:
   148	        # 80 = recommended; 95 = optional. Both are "not mandatory" for the
   149	        # ceiling itself; M1-M5 triggers in ADR-011 §T2 may still mandate
   150	        # Codex independently of the ceiling.
   151	        mandatory_codex = False
   152	        blocking = False
   153	
   154	    return CalibrationResult(
   155	        ceiling=ceiling,
   156	        mandatory_codex=mandatory_codex,
   157	        blocking=blocking,
   158	        basis=basis,
   159	        entry_count=len(outcomes),
   160	    )
   161	
   162	
   163	def _validate_state_dict(data: object) -> list[dict]:
   164	    """Hard-validate a parsed calibration_state.json document.
   165	
   166	    Raises CalibrationStateError on any shape violation. Returns the
   167	    validated entries list (each entry guaranteed to have pr/merged_at/
   168	    r1_outcome of the right type).
   169	    """
   170	    if not isinstance(data, dict):
   171	        raise CalibrationStateError("state file root must be a JSON object")
   172	
   173	    schema_version = data.get("schema_version")
   174	    if schema_version != SUPPORTED_SCHEMA_VERSION:
   175	        raise CalibrationStateError(
   176	            f"schema_version must be {SUPPORTED_SCHEMA_VERSION}, got {schema_version!r}"
   177	        )
   178	
   179	    entries = data.get("entries")
   180	    if not isinstance(entries, list):
   181	        raise CalibrationStateError("'entries' must be a list")
   182	
   183	    seen_prs: set[int] = set()
   184	    for i, e in enumerate(entries):
   185	        if not isinstance(e, dict):
   186	            raise CalibrationStateError(f"entries[{i}] must be a JSON object")
   187	
   188	        pr = e.get("pr")
   189	        if not isinstance(pr, int) or pr <= 0:
   190	            raise CalibrationStateError(
   191	                f"entries[{i}].pr must be a positive int, got {pr!r}"
   192	            )
   193	        if pr in seen_prs:
   194	            raise CalibrationStateError(
   195	                f"entries[{i}].pr={pr} is a duplicate of an earlier entry"
   196	            )
   197	        seen_prs.add(pr)
   198	
   199	        merged_at = e.get("merged_at")
   200	        if not isinstance(merged_at, str) or not merged_at:
   201	            raise CalibrationStateError(
   202	                f"entries[{i}].merged_at (ISO 8601 string) is required"
   203	            )
   204	
   205	        outcome = e.get("r1_outcome")
   206	        if outcome not in CANONICAL_OUTCOMES:
   207	            raise CalibrationStateError(
   208	                f"entries[{i}].r1_outcome must be one of "
   209	                f"{sorted(CANONICAL_OUTCOMES)}, got {outcome!r}"
   210	            )
   211	
   212	    return entries
   213	
   214	
   215	def load_state(state_path: Path) -> list[str]:
   216	    """Read calibration_state.json and return chronologically-ordered R1 outcomes.
   217	
   218	    Raises CalibrationStateError on missing file, invalid JSON, schema-version
   219	    mismatch, duplicate PR rows, missing merged_at, or unknown outcomes.
   220	
   221	    Sorting is by `merged_at` ISO 8601 timestamp (lexicographic == chronological
   222	    for ISO 8601). This is the fix for Codex R1 HIGH #1: the previous
   223	    implementation sorted by PR number, but the repo already contains a
   224	    counterexample (PR #20 merged_at 2026-04-25T08:33:51Z is BEFORE
   225	    PR #18 at 08:53:09Z).
   226	    """
   227	    if not state_path.exists():
   228	        raise CalibrationStateError(
   229	            f"calibration state file not found: {state_path}. "
   230	            "This file is required; it must be initialised by the ADR-012 "
   231	            "establishing PR and append-only thereafter."
   232	        )
   233	
   234	    try:
   235	        with state_path.open() as f:
   236	            data = json.load(f)
   237	    except json.JSONDecodeError as e:
   238	        raise CalibrationStateError(
   239	            f"calibration state file is not valid JSON: {state_path}: {e}"
   240	        ) from e
   241	
   242	    entries = _validate_state_dict(data)
   243	
   244	    # Sort by merged_at (ISO 8601 lexicographic == chronological).
   245	    entries_sorted = sorted(entries, key=lambda e: e["merged_at"])
   246	    return [e["r1_outcome"] for e in entries_sorted]
   247	
   248	
   249	def gate_label(result: CalibrationResult) -> str:
   250	    if result.blocking:
   251	        return "BLOCKING"
   252	    if result.mandatory_codex:
   253	        return "MANDATORY"
   254	    if result.ceiling <= 80:
   255	        return "RECOMMENDED"
   256	    return "OPTIONAL"
   257	
   258	
   259	def main(argv: list[str]) -> int:
   260	    default_state = Path(__file__).resolve().parent.parent / "reports" / "calibration_state.json"

 succeeded in 0ms:
     1	name: Calibration Cap Check
     2	
     3	# ADR-013 enforcement workflow. Validates that every PR's
     4	# "Self-pass-rate" claim does not exceed the mechanical ceiling
     5	# computed by scripts/compute_calibration_cap.py from
     6	# reports/calibration_state.json.
     7	#
     8	# Runs only on pull_request events (no value on push to main).
     9	#
    10	# R2 hardening (post Codex R1, 2026-04-26):
    11	#   * The validator scripts AND the calibration_state.json are loaded
    12	#     from a separate `actions/checkout` of `main`, NOT from the PR's
    13	#     own checkout. This closes the self-bypass hole Codex reproduced
    14	#     where a PR could modify scripts/compute_calibration_cap.py,
    15	#     scripts/extract_pr_self_pass_rate.py, or
    16	#     reports/calibration_state.json to make the check pass.
    17	#   * The PR body itself comes from the GitHub API event payload, not
    18	#     from any file in the PR's checkout, so it remains the legitimate
    19	#     untrusted input.
    20	
    21	on:
    22	  pull_request:
    23	    branches: [main]
    24	    types: [opened, edited, synchronize, reopened]
    25	
    26	permissions:
    27	  contents: read
    28	  pull-requests: read
    29	
    30	jobs:
    31	  calibration-cap-check:
    32	    runs-on: ubuntu-latest
    33	    steps:
    34	      - name: Checkout main (trusted validators + state)
    35	        # The PR is intentionally NOT checked out for the validator
    36	        # scripts. Only main's view of compute_calibration_cap.py,
    37	        # extract_pr_self_pass_rate.py, and reports/calibration_state.json
    38	        # is trusted. A PR can change those files in its own working
    39	        # tree but the check here ignores those changes.
    40	        uses: actions/checkout@v4
    41	        with:
    42	          ref: main
    43	          path: trusted
    44	
    45	      - name: Set up Python 3.11
    46	        uses: actions/setup-python@v5
    47	        with:
    48	          python-version: "3.11"
    49	
    50	      - name: Compute current ceiling (from trusted main)
    51	        id: ceiling
    52	        working-directory: trusted
    53	        run: |
    54	          set -euo pipefail
    55	          OUTPUT=$(python3 scripts/compute_calibration_cap.py)
    56	          CEILING=$(echo "$OUTPUT" | python3 -c "import json,sys;print(json.load(sys.stdin)['ceiling'])")
    57	          GATE=$(echo "$OUTPUT" | python3 -c "import json,sys;print(json.load(sys.stdin)['gate_label'])")
    58	          BLOCKING=$(echo "$OUTPUT" | python3 -c "import json,sys;print(json.load(sys.stdin)['blocking'])")
    59	          echo "ceiling=$CEILING" >> "$GITHUB_OUTPUT"
    60	          echo "gate=$GATE" >> "$GITHUB_OUTPUT"
    61	          echo "blocking=$BLOCKING" >> "$GITHUB_OUTPUT"
    62	          echo "Current ceiling: ${CEILING}%, gate: ${GATE}, blocking: ${BLOCKING} (computed from trusted/main)"
    63	
    64	      - name: Extract Self-pass-rate claim from PR body (trusted extractor)
    65	        id: claim
    66	        working-directory: trusted
    67	        env:
    68	          PR_BODY: ${{ github.event.pull_request.body }}
    69	        run: |
    70	          set -euo pipefail
    71	          if [[ -z "${PR_BODY:-}" ]]; then
    72	            echo "::error::PR body is empty. ADR-013 requires a 'Self-pass-rate' section."
    73	            exit 1
    74	          fi
    75	          # Use main's extractor — not the PR's. PR body comes from the
    76	          # event payload (already untrusted; that's the point — its claim
    77	          # must be checked against the trusted ceiling).
    78	          CLAIM=$(printf '%s' "$PR_BODY" | python3 scripts/extract_pr_self_pass_rate.py)
    79	          echo "claim=$CLAIM" >> "$GITHUB_OUTPUT"
    80	          echo "Claim parsed from PR body: ${CLAIM}% (extractor from trusted/main)"
    81	
    82	      - name: Validate claim does not exceed ceiling (from trusted main)
    83	        working-directory: trusted
    84	        run: |
    85	          set -euo pipefail
    86	          python3 scripts/compute_calibration_cap.py --check "${{ steps.claim.outputs.claim }}"
    87	          echo "::notice::Claim ${{ steps.claim.outputs.claim }}% does not exceed ceiling ${{ steps.ceiling.outputs.ceiling }}% (gate: ${{ steps.ceiling.outputs.gate }})"

 succeeded in 0ms:
     1	"""Extract the claimed Self-pass-rate from a PR body.
     2	
     3	The PR template (per ADR-013) reserves a section labeled
     4	"Self-pass-rate (mechanically derived)" whose first line contains the
     5	claimed ceiling as `**N%**` (or just `N%`). This helper extracts that
     6	integer so CI can pass it to compute_calibration_cap.py --check.
     7	
     8	R2 hardening (post Codex R1, 2026-04-26): hidden-marker bypass closed.
     9	The previous regex matched the FIRST `N%` within 600 chars of the
    10	heading without distinguishing visible markdown from hidden constructs.
    11	A PR body like:
    12	
    13	    ## Self-pass-rate
    14	
    15	    <!-- 30% -->
    16	
    17	    **95%**
    18	
    19	would parse as `30` while a human reviewer sees `95`. Codex reproduced
    20	this exact case. Fix: strip HTML comments AND fenced code blocks
    21	(triple-backtick OR triple-tilde) BEFORE searching, so only visible
    22	markdown contributes a candidate.
    23	
    24	Usage:
    25	    python3 scripts/extract_pr_self_pass_rate.py < pr_body.txt
    26	    cat pr_body.txt | python3 scripts/extract_pr_self_pass_rate.py
    27	    echo "$PR_BODY" | python3 scripts/extract_pr_self_pass_rate.py
    28	
    29	Prints the integer claim on stdout (one line, no `%`). Exits non-zero if
    30	no claim found in the body.
    31	"""
    32	
    33	from __future__ import annotations
    34	
    35	import re
    36	import sys
    37	
    38	# R2 hidden-content strippers — order matters (HTML comments may
    39	# legitimately appear inside fenced code, and we want both gone).
    40	# All use re.DOTALL so multi-line constructs are scrubbed.
    41	_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
    42	_FENCED_BACKTICK_RE = re.compile(r"```.*?```", re.DOTALL)
    43	_FENCED_TILDE_RE = re.compile(r"~~~.*?~~~", re.DOTALL)
    44	_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
    45	
    46	# Match the Self-pass-rate section heading then the first \d+% within
    47	# the next ~600 chars (one paragraph block). Tolerates `## Self-pass-rate`,
    48	# `### Self-pass-rate`, with-or-without trailing parenthetical.
    49	_HEADING_RE = re.compile(
    50	    r"(?im)^\s{0,3}#{2,4}\s*Self[- ]pass[- ]rate\b[^\n]*\n",
    51	)
    52	_PERCENT_RE = re.compile(r"\b(\d{1,3})\s*%")
    53	
    54	
    55	def _strip_hidden_constructs(body: str) -> str:
    56	    """Remove HTML comments + fenced code blocks + inline-code spans.
    57	
    58	    Pinned by adversarial tests in tests/test_extract_pr_self_pass_rate.py.
    59	    """
    60	    body = _HTML_COMMENT_RE.sub("", body)
    61	    body = _FENCED_BACKTICK_RE.sub("", body)
    62	    body = _FENCED_TILDE_RE.sub("", body)
    63	    body = _INLINE_CODE_RE.sub("", body)
    64	    return body
    65	
    66	
    67	def extract_claim(body: str) -> int | None:
    68	    """Return the integer claim (0-100) or None if not found.
    69	
    70	    Strips hidden markdown constructs (HTML comments, fenced and inline
    71	    code) before matching, so the parsed claim must equal what a human
    72	    reviewer sees.
    73	    """
    74	    body = _strip_hidden_constructs(body)
    75	    heading = _HEADING_RE.search(body)
    76	    if not heading:
    77	        return None
    78	    tail = body[heading.end() : heading.end() + 600]
    79	    m = _PERCENT_RE.search(tail)
    80	    if not m:
    81	        return None
    82	    val = int(m.group(1))
    83	    if not 0 <= val <= 100:
    84	        return None
    85	    return val
    86	
    87	
    88	def main(argv: list[str]) -> int:
    89	    body = sys.stdin.read()
    90	    claim = extract_claim(body)
    91	    if claim is None:
    92	        print(
    93	            "ERROR: PR body does not contain a 'Self-pass-rate' section "
    94	            "with a `N%` claim. ADR-013 requires this section in every PR.",
    95	            file=sys.stderr,
    96	        )
    97	        return 2
    98	    print(claim)
    99	    return 0
   100	
   101	
   102	if __name__ == "__main__":
   103	    sys.exit(main(sys.argv))

exec
/bin/zsh -lc "git show 3d97d30732df51b0430110afb7d7828f4716b66c:scripts/compute_calibration_cap.py | nl -ba | sed -n '260,340p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
   260	    default_state = Path(__file__).resolve().parent.parent / "reports" / "calibration_state.json"
   261	    parser = argparse.ArgumentParser(
   262	        description="Compute T1 calibration ceiling per ADR-012 / AR-2026-04-25-001."
   263	    )
   264	    parser.add_argument(
   265	        "--human",
   266	        action="store_true",
   267	        help="emit human-readable summary instead of JSON",
   268	    )
   269	    parser.add_argument(
   270	        "--check",
   271	        type=int,
   272	        metavar="CEILING",
   273	        help="exit 1 if claimed CEILING exceeds the computed ceiling",
   274	    )
   275	    parser.add_argument(
   276	        "--state",
   277	        type=Path,
   278	        default=default_state,
   279	        help=f"path to calibration_state.json (default: {default_state})",
   280	    )
   281	    args = parser.parse_args(argv[1:])
   282	
   283	    try:
   284	        outcomes = load_state(args.state)
   285	    except CalibrationStateError as e:
   286	        sys.stderr.write(f"calibration state error: {e}\n")
   287	        return 1
   288	
   289	    result = compute_calibration(outcomes)
   290	
   291	    if args.check is not None:
   292	        if args.check > result.ceiling:
   293	            sys.stderr.write(
   294	                f"calibration check FAILED: claimed {args.check}% exceeds "
   295	                f"computed ceiling {result.ceiling}%\n"
   296	                f"  basis: {result.basis}\n"
   297	                f"  Codex gate: {gate_label(result)}\n"
   298	            )
   299	            return 1
   300	        return 0
   301	
   302	    if args.human:
   303	        print(f"T1 calibration ceiling : {result.ceiling}%")
   304	        print(f"Codex pre-merge gate   : {gate_label(result)}")
   305	        print(f"Basis                  : {result.basis}")
   306	        print(f"State entries          : {result.entry_count} (last 5 used)")
   307	    else:
   308	        out = {
   309	            "ceiling": result.ceiling,
   310	            "mandatory_codex": result.mandatory_codex,
   311	            "blocking": result.blocking,
   312	            "basis": result.basis,
   313	            "entry_count": result.entry_count,
   314	            "gate_label": gate_label(result),
   315	        }
   316	        print(json.dumps(out, ensure_ascii=False))
   317	
   318	    return 0
   319	
   320	
   321	if __name__ == "__main__":
   322	    sys.exit(main(sys.argv))

codex
The R1 HIGHs look addressed at the code path level. I’m doing two final passes now: one on edge-case correctness around the new `merged_at` validation/sort contract, and one on whether the claimed 30% ceiling still matches the actual head-state of each PR.
exec
/bin/zsh -lc 'tmpdir=$(mktemp -d); git show 3d97d30732df51b0430110afb7d7828f4716b66c:scripts/compute_calibration_cap.py > "$tmpdir/compute_calibration_cap.py"; git show 3d97d30732df51b0430110afb7d7828f4716b66c:reports/calibration_state.json > "$tmpdir/calibration_state.json"; python3 "$tmpdir/compute_calibration_cap.py" --state "$tmpdir/calibration_state.json"; rm -rf "$tmpdir"' in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
{"ceiling": 30, "mandatory_codex": true, "blocking": true, "basis": "5 of last 5 = CHANGES_REQUIRED → ceiling 30%", "entry_count": 6, "gate_label": "BLOCKING"}

exec
/bin/zsh -lc "python3 - <<'PY'
import subprocess, tempfile, pathlib, sys
script = subprocess.check_output(['git','show','20b8c003c284c72282175b34f9d5b096a851437c:scripts/extract_pr_self_pass_rate.py'], text=True)
with tempfile.TemporaryDirectory() as td:
    td = pathlib.Path(td)
    (td/'extract_pr_self_pass_rate.py').write_text(script)
    sys.path.insert(0, str(td))
    import extract_pr_self_pass_rate as mod
    cases = {
        'html_comment_visible_95': '## Self-pass-rate\\n\\n<"'!-- 30% -->'"\\n\\n95%\\n',
        'indented_code_then_visible': '## Self-pass-rate\\n\\n    30%\\n\\n95%\\n',
        'details_hidden_then_visible': '## Self-pass-rate\\n\\n<details><summary>foo</summary>30%</details>\\n\\n95%\\n',
    }
    for name, body in cases.items():
        print(name, '=>', mod.extract_claim(body))
PY" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
html_comment_visible_95 => 95
indented_code_then_visible => 30
details_hidden_then_visible => 30

exec
/bin/zsh -lc "python3 - <<'PY'
import json, subprocess, tempfile, pathlib, sys
script = subprocess.check_output(['git','show','3d97d30732df51b0430110afb7d7828f4716b66c:scripts/compute_calibration_cap.py'], text=True)
state = subprocess.check_output(['git','show','3d97d30732df51b0430110afb7d7828f4716b66c:reports/calibration_state.json'], text=True)
with tempfile.TemporaryDirectory() as td:
    td = pathlib.Path(td)
    (td/'compute_calibration_cap.py').write_text(script)
    bad = {
        'schema_version': 1,
        'entries': [
            {'pr': 18, 'merged_at': 'zzz', 'r1_outcome': 'APPROVE'},
            {'pr': 19, 'merged_at': '2026-04-25T08:56:46Z', 'r1_outcome': 'CHANGES_REQUIRED'},
        ],
    }
    (td/'bad.json').write_text(json.dumps(bad))
    sys.path.insert(0, str(td))
    import compute_calibration_cap as mod
    try:
        print(mod.load_state(td/'bad.json'))
    except Exception as e:
        print(type(e).__name__, str(e))
PY" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
['CHANGES_REQUIRED', 'APPROVE']

exec
/bin/zsh -lc "gh pr view 24 --json body --jq .body | python3 - <<'PY'
import re,sys
body=sys.stdin.read()
m=re.search(r'## Self-pass-rate \\(mechanically derived\\)\\n\\n\\*\\*(\\d+)%\\*\\*', body)
print(m.group(1) if m else 'NO_MATCH')
PY" in /Users/Zhuanz/20260408 AI StructureAnalysis
exec
/bin/zsh -lc "gh pr view 25 --json body --jq .body | python3 - <<'PY'
import re,sys
body=sys.stdin.read()
m=re.search(r'## Self-pass-rate \\(mechanically derived\\)\\n\\n\\*\\*(\\d+)%\\*\\*', body)
print(m.group(1) if m else 'NO_MATCH')
PY" in /Users/Zhuanz/20260408 AI StructureAnalysis
 exited 1 in 855ms:
  File "<stdin>", line 3
    Three-layer enforcement wrapper around ADR-012 (PR #24, parent in stack). ADR-012 defines a calibration ceiling but has no surface that prevents T1 self-merge under BLOCKING — this PR adds it.
                ^
SyntaxError: invalid syntax

 exited 1 in 896ms:
  File "<stdin>", line 3
    Replaces RETRO-V61-001's honor-system self-pass-rate with a mechanically-derived ceiling computed from a rolling 5-PR window of Codex Round 1 outcomes. T1 cannot type a number; T1 reads one.
             ^
SyntaxError: invalid syntax

exec
/bin/zsh -lc "gh pr view 24 --json body --jq .body | rg -n '\\*\\*[0-9]+%\\*\\*|Self-pass-rate'" in /Users/Zhuanz/20260408 AI StructureAnalysis
exec
/bin/zsh -lc "gh pr view 25 --json body --jq .body | rg -n '\\*\\*[0-9]+%\\*\\*|Self-pass-rate'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 1595ms:
55:## Self-pass-rate (mechanically derived)
57:**30%** · BLOCKING · pre-merge Codex MANDATORY · derivation in `reports/calibration_state.json` last-5 window.

 succeeded in 1594ms:
10:Reserves a `## Self-pass-rate (mechanically derived)` section and forces a Codex gate level pick + ADR-011 §T2 M1-M5 ticks. Surfaces the gate before review.
55:## Self-pass-rate (mechanically derived)
57:**30%** · BLOCKING · pre-merge Codex MANDATORY · derived from `reports/calibration_state.json` last-5 R1 outcomes (PRs #19-#23, all CR).

codex
One gap remains in the extractor hardening pass: the R2 stripping closes the reported HTML-comment and fenced-code bypasses, but I found that indented code blocks and collapsed raw HTML like `<details>...</details>` still parse as the claim. I’m checking whether that rises to a reviewable regression versus a follow-up hardening item.
exec
/bin/zsh -lc "python3 - <<'PY'
import json, subprocess
state = json.loads(subprocess.check_output(['git','show','3d97d30732df51b0430110afb7d7828f4716b66c:reports/calibration_state.json'], text=True))
entries = sorted(state['entries'], key=lambda e: e['merged_at'])
print([(e['pr'], e['merged_at'], e['r1_outcome']) for e in entries])
print('last5=', [e['pr'] for e in entries[-5:]])
PY" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
[(20, '2026-04-25T08:33:51Z', 'CHANGES_REQUIRED'), (18, '2026-04-25T08:53:09Z', 'CHANGES_REQUIRED'), (19, '2026-04-25T08:56:46Z', 'CHANGES_REQUIRED'), (21, '2026-04-25T10:30:14Z', 'CHANGES_REQUIRED'), (22, '2026-04-25T10:43:55Z', 'CHANGES_REQUIRED'), (23, '2026-04-25T12:06:52Z', 'CHANGES_REQUIRED')]
last5= [18, 19, 21, 22, 23]

exec
/bin/zsh -lc "git show 3d97d30732df51b0430110afb7d7828f4716b66c:docs/adr/ADR-012-calibration-cap-for-t1-self-pass-rate.md | nl -ba | sed -n '68,92p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
    68	- `scripts/compute_calibration_cap.py` — pure function over the state file. Outputs `{ceiling, mandatory_codex, blocking, basis, entry_count, gate_label}` JSON. Has `--human` and `--check <claimed-ceiling>` modes. **Fails closed**: missing state file, schema-version mismatch, duplicate `pr`, missing `merged_at`, or unknown `r1_outcome` all produce a hard `CalibrationStateError` and exit 1 — never a silent fail-open.
    69	- `tests/test_compute_calibration_cap.py` — unit tests covering each rung, recovery transitions, BLOCKER/NITS canon, the merged_at-vs-PR-number counterexample regression, and every adversarial state-validation path.
    70	
    71	**T1 invocation surface:**
    72	
    73	- At session-start, T1 runs `python3 scripts/compute_calibration_cap.py --human` and renders the result in the `MODEL COMPLIANCE CHECK` block of every reply that initiates work.
    74	- The PR template (in `.github/PULL_REQUEST_TEMPLATE.md` once branch protection lands per ADR-013) prefills the `Self-pass-rate` field by calling the script. The field is **read-only** to T1.
    75	- A CI check (in ADR-013's workflow batch) calls `--check <claimed>` to fail PRs whose body claims a higher ceiling than computed.
    76	
    77	**State maintenance:**
    78	
    79	After each PR merges, the maintainer (T1 or T0) appends a new entry to `reports/calibration_state.json` with the actual R1 outcome. Entry SHOULD be added in the same PR as housekeeping or in the next PR's first commit. State updates do NOT themselves count as PRs in the formula — the formula counts PRs that touched code/governance content.
    80	
    81	## Bootstrap state (initial 5 entries)
    82	
    83	Per AR-2026-04-25-001 §1, initialize from PRs #18-#22 (PR #17 excluded as the ADR-011 baseline establishment). All 5 are `CHANGES_REQUIRED` per session 2026-04-25 record:
    84	
    85	| PR | SHA | R1 outcome | R1 severity |
    86	|---|---|---|---|
    87	| #18 | `77e6813` | CHANGES_REQUIRED | 1 HIGH + 3 MEDIUM |
    88	| #19 | `4a64cfd` | CHANGES_REQUIRED | 1 HIGH + 1 MEDIUM |
    89	| #20 | `9362f6d` | CHANGES_REQUIRED | 1 BLOCKER + 2 SHOULD_FIX |
    90	| #21 | `2bbf0f1` | CHANGES_REQUIRED | 1 HIGH |
    91	| #22 | `ac98fc3` | CHANGES_REQUIRED | 1 BLOCKER + 2 SHOULD_FIX |
    92	

exec
/bin/zsh -lc 'tmpdir=$(mktemp -d); git show 20b8c003c284c72282175b34f9d5b096a851437c:scripts/compute_calibration_cap.py > "$tmpdir/compute_calibration_cap.py"; git show 20b8c003c284c72282175b34f9d5b096a851437c:reports/calibration_state.json > "$tmpdir/calibration_state.json"; python3 "$tmpdir/compute_calibration_cap.py" --state "$tmpdir/calibration_state.json"; rm -rf "$tmpdir"' in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
{"ceiling": 30, "mandatory_codex": true, "blocking": true, "basis": "5 of last 5 = CHANGES_REQUIRED → ceiling 30%", "entry_count": 6, "gate_label": "BLOCKING"}

  ✓ Inspect PR #24 metadata, diff, and touched files; verify the two R1 HIGH fixes and look for new HIGH/MEDIUM issues
  ✓ Inspect PR #25 metadata, diff, and touched files; verify the three R1 HIGH fixes and look for new HIGH/MEDIUM issues
  ✓ Compare both PRs’ self-pass-rate claims against actual extraction/calibration behavior and produce verdicts with line-cited findings
codex
**PR #24**
`VERDICT: APPROVE_WITH_NITS`

`HIGH findings`
- None. R1 HIGH#1 is closed by the merge-order load path in `scripts/compute_calibration_cap.py:215-246`. R1 HIGH#2 is closed by the fail-closed state validation and `main()` error exit in `scripts/compute_calibration_cap.py:163-212,283-287`.

`MEDIUM findings`
- None.

`LOW/NITS`
- `scripts/compute_calibration_cap.py:199-245` treats `merged_at` as “non-empty string” rather than validating actual ISO-8601 syntax. That does not reopen the reported R1 HIGHs, but it means malformed timestamps would still sort silently instead of fail-closing.

`Notes on new regressions introduced by the R2 diff itself`
- None found.

`Self-pass-rate calibration check`
- The claimed `30%` is correct. Running the head revision over `reports/calibration_state.json:6-69` via `scripts/compute_calibration_cap.py:119-159,215-246` yields `30 / BLOCKING`.
- The prose window in the PR body names `#19-#23`, but after the `merged_at` sort fix the actual merge-ordered last five are `#18,#19,#21,#22,#23`. That does not change the computed ceiling because all five are still `CHANGES_REQUIRED`.

**PR #25**
`VERDICT: CHANGES_REQUIRED`

`HIGH findings`
- `scripts/extract_pr_self_pass_rate.py:41-44,55-64,74-85` still allows claim/parser desync through non-stripped constructs. R2 strips HTML comments, triple-fence blocks, and inline code, but it still takes the first `%` from other non-claim containers such as collapsed raw HTML or indented code blocks. Repro I verified locally against the R2 head: `## Self-pass-rate\n\n<details><summary>x</summary>30%</details>\n\n95%\n` returns `30`, so CI can still pass a visible overclaim. The exact R1 HTML-comment/fenced-code repro is fixed, but the underlying bypass class is not fully closed.

`MEDIUM findings`
- None.

`LOW/NITS`
- Same prose nit as PR #24: the numeric `30%` claim is right, but the body’s named last-5 set is not the actual merge-ordered window after ADR-012’s `merged_at` fix.

`Notes on new regressions introduced by the R2 diff itself`
- R1 HIGH#2 is resolved by the trusted-main execution path in `.github/workflows/calibration-cap-check.yml:34-87`.
- R1 HIGH#3 is resolved by inheriting PR #24’s fail-closed loader in `scripts/compute_calibration_cap.py:163-246,283-287`.
- The remaining blocker is the partial extractor hardening above.

`Self-pass-rate calibration check`
- The claimed `30%` is correct. Running the PR #25 head’s inherited `scripts/compute_calibration_cap.py` against its `reports/calibration_state.json` also yields `30 / BLOCKING`.
tokens used
113,156
**PR #24**
`VERDICT: APPROVE_WITH_NITS`

`HIGH findings`
- None. R1 HIGH#1 is closed by the merge-order load path in `scripts/compute_calibration_cap.py:215-246`. R1 HIGH#2 is closed by the fail-closed state validation and `main()` error exit in `scripts/compute_calibration_cap.py:163-212,283-287`.

`MEDIUM findings`
- None.

`LOW/NITS`
- `scripts/compute_calibration_cap.py:199-245` treats `merged_at` as “non-empty string” rather than validating actual ISO-8601 syntax. That does not reopen the reported R1 HIGHs, but it means malformed timestamps would still sort silently instead of fail-closing.

`Notes on new regressions introduced by the R2 diff itself`
- None found.

`Self-pass-rate calibration check`
- The claimed `30%` is correct. Running the head revision over `reports/calibration_state.json:6-69` via `scripts/compute_calibration_cap.py:119-159,215-246` yields `30 / BLOCKING`.
- The prose window in the PR body names `#19-#23`, but after the `merged_at` sort fix the actual merge-ordered last five are `#18,#19,#21,#22,#23`. That does not change the computed ceiling because all five are still `CHANGES_REQUIRED`.

**PR #25**
`VERDICT: CHANGES_REQUIRED`

`HIGH findings`
- `scripts/extract_pr_self_pass_rate.py:41-44,55-64,74-85` still allows claim/parser desync through non-stripped constructs. R2 strips HTML comments, triple-fence blocks, and inline code, but it still takes the first `%` from other non-claim containers such as collapsed raw HTML or indented code blocks. Repro I verified locally against the R2 head: `## Self-pass-rate\n\n<details><summary>x</summary>30%</details>\n\n95%\n` returns `30`, so CI can still pass a visible overclaim. The exact R1 HTML-comment/fenced-code repro is fixed, but the underlying bypass class is not fully closed.

`MEDIUM findings`
- None.

`LOW/NITS`
- Same prose nit as PR #24: the numeric `30%` claim is right, but the body’s named last-5 set is not the actual merge-ordered window after ADR-012’s `merged_at` fix.

`Notes on new regressions introduced by the R2 diff itself`
- R1 HIGH#2 is resolved by the trusted-main execution path in `.github/workflows/calibration-cap-check.yml:34-87`.
- R1 HIGH#3 is resolved by inheriting PR #24’s fail-closed loader in `scripts/compute_calibration_cap.py:163-246,283-287`.
- The remaining blocker is the partial extractor hardening above.

`Self-pass-rate calibration check`
- The claimed `30%` is correct. Running the PR #25 head’s inherited `scripts/compute_calibration_cap.py` against its `reports/calibration_state.json` also yields `30 / BLOCKING`.
