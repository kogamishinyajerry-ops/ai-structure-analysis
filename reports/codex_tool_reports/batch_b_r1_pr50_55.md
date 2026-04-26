2026-04-25T19:05:19.577560Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-research-deerflow/SKILL.md: missing YAML frontmatter delimited by ---
2026-04-25T19:05:19.577580Z ERROR codex_core::codex: failed to load skill /Users/Zhuanz/.agents/skills/cfd-report-pretext/SKILL.md: missing YAML frontmatter delimited by ---
OpenAI Codex v0.118.0 (research preview)
--------
workdir: /Users/Zhuanz/20260408 AI StructureAnalysis
model: gpt-5.4
provider: openai
approval: never
sandbox: danger-full-access
reasoning effort: xhigh
reasoning summaries: none
session id: 019dc608-33da-75a1-a974-971c84199cfa
--------
user
You are reviewing 6 parallel-track PRs at github.com/kogamishinyajerry-ops/ai-structure-analysis (public). Use `gh pr diff <num>`, `gh pr view <num>`, and direct file reads.

Four are ADR Drafts that pin the Phase 2.1 workbench surface. Two are stacked Phase 2.1 skeleton implementations. All claim self-pass-rate 30% (BLOCKING ceiling per ADR-012 R2). All claim M2-only (M1 also for the ADRs); none touch HF1 zones.

For each PR output a section with:
- VERDICT: APPROVE / APPROVE_WITH_NITS / CHANGES_REQUIRED
- HIGH findings (file:line)
- MEDIUM findings (file:line)
- LOW/NITS (brief)
- Notes on any new regressions

--- PR #50 [ADR-014 — WS event bus contract] ---
URL: https://github.com/kogamishinyajerry-ops/ai-structure-analysis/pull/50
Defines: 12 event kinds (run.started, node.entered/progress/exited, artifact.ready, rag.queried, surrogate.hint, reviewer.verdict, handoff.required, bus.dropped, bus.gap, run.finished). Single WS endpoint /ws/runs/{run_id}; append-only typed JSON; schema_version="v1". asyncio.Queue + 256-event ring buffer for resume via ?since_seq. Privacy: digests only, no raw prompts/RAG/CAD.
Tests: 62 in tests/test_ws_events_schema.py — discriminated union (TypeAdapter), frozen, extra=forbid, JSON round-trip across all 12 kinds, privacy-guard sweep (no field name contains secret/internal/raw_query/raw_text/agent_thought/prompt).

--- PR #51 [ADR-015 — workbench → agent RPC boundary] ---
URL: https://github.com/kogamishinyajerry-ops/ai-structure-analysis/pull/51
Defines: in-process facade pattern. backend/app/workbench/agent_facade.py is the SOLE workbench file that imports agents.*. Read-only contract; effects flow through ADR-014's bus. NL → SimPlan → HMAC-SHA256 confirmation_token → submit. Architect runs ONCE per request. Auth: X-Workbench-Token header.
Tests: 14 in tests/test_workbench_facade_discipline.py — 3 file-walk rules + 11 synthetic-fixture predicate tests pinning bare-import / relative-import / lookalike-module (agentsuite) / deep attribute / local-variable cases.

--- PR #52 [ADR-016 — .frd → .vtu + result viz] ---
URL: https://github.com/kogamishinyajerry-ops/ai-structure-analysis/pull/52
Defines: pipeline .frd → FRDParseResult → ASCII .vtu → vtk.js. NO ParaView Web. Storage runs/{id}/viz/. Initial cell coverage C3D4/C3D10/C3D8/C3D20/S3/S4. Initial fields displacement + von_mises + max/mid/min principal. Units carried from SimPlan via run_orchestrator.
Tests: 26 in tests/test_viz_manifest_schema.py — Pydantic v2 frozen + extra=forbid, discriminated FieldEntry union (DisplacementField | ScalarStressField), cell-type / increment-type / units literals, JSON round-trip, WriterInfo.tool literal pin. Union[...] kept for Py 3.9 runtime compat.

--- PR #53 [ADR-017 — RAG facade in-process + CLI/lib parity] ---
URL: https://github.com/kogamishinyajerry-ops/ai-structure-analysis/pull/53
Defines: backend/app/workbench/rag_facade.py wraps backend.app.rag.* library (NOT CLI shells). Workbench-side facade is the privacy-redaction site. CLI must remain thin shell over library — discipline test enforces parity. BGE-M3 startup-singleton in workbench backend; CLI continues per-invocation cold-start.
Tests: 9 in tests/test_rag_facade_parity.py: rule #1 (only facade modules import RAG from workbench), #2 (facade does not import RAG CLI shells), #3 (each CLI imports its library sibling), #4 (no CLI imports another CLI). 5 pass / 4 skip until RAG track (PR #38-#47) lands.

--- PR #54 [P2.1-01 agent_facade + task_spec_builder skeleton, stacked on #51] ---
URL: https://github.com/kogamishinyajerry-ops/ai-structure-analysis/pull/54
Implements:
- backend/app/workbench/agent_facade.py: draft_simplan_from_nl(nl_request, case_id=None) -> ArchitectResult, calls agents.architect.run({...}) with plain dict (NO schemas.sim_state import). Raises ArchitectError on null/exception, ValueError on empty input.
- backend/app/workbench/task_spec_builder.py: draft_from_nl + verify_confirmation. HMAC-SHA256 over `draft_id || NUL || canonical-JSON(SimPlan)`. canonical = sort_keys + ensure_ascii=False + (",", ":"). secrets.compare_digest for constant-time comparison.
Tests: 33 across two test files (10 facade + 18 builder + 5 newly-active discipline). Both new test files use pytest.importorskip("schemas.sim_plan") to gate Py 3.11+ requirements gracefully.

--- PR #55 [P2.1-02 event_bus runtime, stacked on #50] ---
URL: https://github.com/kogamishinyajerry-ops/ai-structure-analysis/pull/55
Implements backend/app/runtime/event_bus.py:
- RunEventBus per-run instance; collections.deque + asyncio.Event for "events available" (NOT asyncio.Queue — would need to poke private internals to selectively drop non-critical).
- 256-event ring buffer for resume via ?since_seq.
- Monotonic per-run seq counter + asyncio.Lock for emit-side atomicity.
- Soft cap QUEUE_CAPACITY=1024; on overflow with non-critical event arrival: drop the arriving event + enqueue synthetic bus.dropped. Critical events (run.started/run.finished/handoff.required) bypass the cap (may push queue temporarily above 1024).
- replay_since(seq) returns events with seq > seq; if seq below ring tail, output starts with synthetic bus.gap.
- close() flips flag, raises on subsequent emit; in-flight drain still works.
Tests: 22 in tests/test_runtime_event_bus.py covering construction, monotonic seq, overflow drop, critical bypass, ring buffer eviction, replay since cases (zero/filtered/empty/below-tail/inside-buffer/negative), close lifecycle, 8-producer × 50-event concurrency, multi-run isolation.

Common patterns to scrutinize:
- AST-predicate edge cases (lookalike modules like agentsuite/ragout, relative vs absolute imports, indirect imports through __all__)
- Pydantic v2 frozen + extra=forbid completeness across nested models
- Discriminated-union exhaustiveness; Literal-pin completeness
- HMAC binding correctness — canonical JSON determinism, constant-time compare actually used
- asyncio race conditions in event_bus (lock coverage, ring buffer concurrent-mutation safety, replay snapshot consistency)
- privacy boundary: no field name in ws_events.py contains secret/internal/raw_*

Be terse but concrete. Cite exact file:line references. Group findings by PR.

codex
Reviewing the six PRs as a correctness-focused pass. I’m pulling each PR’s metadata and diff first, then I’ll read the touched files directly and cite concrete file:line findings only where the code actually justifies them.
exec
/bin/zsh -lc "sed -n '1,220p' /Users/Zhuanz/.agents/skills/gsd-code-review/SKILL.md" in /Users/Zhuanz/20260408 AI StructureAnalysis
exec
/bin/zsh -lc "sed -n '1,220p' /Users/Zhuanz/.codex/plugins/cache/openai-curated/superpowers/421657af0e7e94573f3a5f2c51091df43668da94/skills/using-superpowers/SKILL.md" in /Users/Zhuanz/20260408 AI StructureAnalysis
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
/bin/zsh -lc 'pwd && git remote -v && gh repo view --json nameWithOwner,defaultBranchRef' in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 622ms:
{"defaultBranchRef":{"name":"main"},"nameWithOwner":"kogamishinyajerry-ops/ai-structure-analysis"}

codex
Using `using-superpowers` for skill discipline and `gsd-code-review` as the review workflow baseline. Next I’m fetching the six PR heads and their diffs so I can inspect the actual changed files with stable line references instead of reviewing from summaries.
Code review across six stacked PRs. I need the exact diff scope and head file contents for each before scoring findings.
  → Fetch PR metadata, diffs, and head refs for PRs 50-55
  • Inspect changed files and tests for each PR, focusing on contract holes and regression risks
  • Produce terse per-PR verdicts with severity-ordered findings and exact file:line citations
exec
/bin/zsh -lc 'git status --short --branch' in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
## feature/AI-FEA-ADR-013-branch-protection...origin/feature/AI-FEA-ADR-013-branch-protection
?? reports/codex_tool_reports/batch_b_r1_pr50_55.md

exec
/bin/zsh -lc 'for n in 50 51 52 53 54 55; do echo "===PR$n==="; gh pr view "$n" --json number,title,headRefName,baseRefName,author,mergeStateStatus,isDraft,files; done' in /Users/Zhuanz/20260408 AI StructureAnalysis
exec
/bin/zsh -lc 'for n in 50 51 52 53 54 55; do git fetch origin pull/$n/head:pr-$n; done' in /Users/Zhuanz/20260408 AI StructureAnalysis
exec
/bin/zsh -lc 'mkdir -p /tmp/ai-structure-pr-review && for n in 50 51 52 53 54 55; do gh pr diff "$n" > /tmp/ai-structure-pr-review/pr-$n.diff; done && ls -l /tmp/ai-structure-pr-review' in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 4823ms:
{"author":{"id":"U_kgDODjMbqg","is_bot":false,"login":"kogamishinyajerry-ops","name":""},"baseRefName":"main","files":[{"path":"docs/adr/ADR-014-ws-event-bus-for-workbench.md","additions":173,"deletions":0,"changeType":"ADDED"},{"path":"schemas/ws_events.py","additions":201,"deletions":0,"changeType":"ADDED"},{"path":"tests/test_ws_events_schema.py","additions":499,"deletions":0,"changeType":"ADDED"}],"headRefName":"feature/AI-FEA-ADR-014-ws-event-bus","isDraft":false,"mergeStateStatus":"CLEAN","number":50,"title":"[ADR-014] Draft: WebSocket event bus for the workbench"}
===PR51===
{"author":{"id":"U_kgDODjMbqg","is_bot":false,"login":"kogamishinyajerry-ops","name":""},"baseRefName":"main","files":[{"path":"backend/app/workbench/__init__.py","additions":5,"deletions":0,"changeType":"ADDED"},{"path":"docs/adr/ADR-015-workbench-agent-rpc-boundary.md","additions":164,"deletions":0,"changeType":"ADDED"},{"path":"tests/test_workbench_facade_discipline.py","additions":204,"deletions":0,"changeType":"ADDED"}],"headRefName":"feature/AI-FEA-ADR-015-workbench-agent-rpc","isDraft":false,"mergeStateStatus":"CLEAN","number":51,"title":"[ADR-015] Workbench → Agent RPC boundary (Draft, parallel to ADR-014)"}
===PR52===
{"author":{"id":"U_kgDODjMbqg","is_bot":false,"login":"kogamishinyajerry-ops","name":""},"baseRefName":"main","files":[{"path":"backend/app/viz/__init__.py","additions":6,"deletions":0,"changeType":"ADDED"},{"path":"docs/adr/ADR-016-frd-vtu-result-viz.md","additions":207,"deletions":0,"changeType":"ADDED"},{"path":"schemas/viz_manifest.py","additions":126,"deletions":0,"changeType":"ADDED"},{"path":"tests/test_viz_manifest_schema.py","additions":384,"deletions":0,"changeType":"ADDED"}],"headRefName":"feature/AI-FEA-ADR-016-frd-vtu-result-viz","isDraft":false,"mergeStateStatus":"CLEAN","number":52,"title":"[ADR-016] .frd → .vtu + result visualization (Draft, parallel to ADR-015)"}
===PR53===
{"author":{"id":"U_kgDODjMbqg","is_bot":false,"login":"kogamishinyajerry-ops","name":""},"baseRefName":"main","files":[{"path":"docs/adr/ADR-017-rag-facade-cli-lib-parity.md","additions":194,"deletions":0,"changeType":"ADDED"},{"path":"tests/test_rag_facade_parity.py","additions":262,"deletions":0,"changeType":"ADDED"}],"headRefName":"feature/AI-FEA-ADR-017-rag-facade-cli-lib-parity","isDraft":false,"mergeStateStatus":"UNSTABLE","number":53,"title":"[ADR-017] RAG facade in-process + CLI/lib parity (Draft, parallel to ADR-015)"}
===PR54===
{"author":{"id":"U_kgDODjMbqg","is_bot":false,"login":"kogamishinyajerry-ops","name":""},"baseRefName":"feature/AI-FEA-ADR-015-workbench-agent-rpc","files":[{"path":"backend/app/workbench/agent_facade.py","additions":115,"deletions":0,"changeType":"ADDED"},{"path":"backend/app/workbench/task_spec_builder.py","additions":135,"deletions":0,"changeType":"ADDED"},{"path":"tests/test_workbench_agent_facade.py","additions":159,"deletions":0,"changeType":"ADDED"},{"path":"tests/test_workbench_task_spec_builder.py","additions":249,"deletions":0,"changeType":"ADDED"}],"headRefName":"feature/AI-FEA-P2.1-01-agent-facade-skeleton","isDraft":false,"mergeStateStatus":"CLEAN","number":54,"title":"[P2.1-01] agent_facade + task_spec_builder skeleton (stacked on ADR-015)"}
===PR55===
{"author":{"id":"U_kgDODjMbqg","is_bot":false,"login":"kogamishinyajerry-ops","name":""},"baseRefName":"feature/AI-FEA-ADR-014-ws-event-bus","files":[{"path":"backend/app/runtime/__init__.py","additions":10,"deletions":0,"changeType":"ADDED"},{"path":"backend/app/runtime/event_bus.py","additions":251,"deletions":0,"changeType":"ADDED"},{"path":"tests/test_runtime_event_bus.py","additions":380,"deletions":0,"changeType":"ADDED"}],"headRefName":"feature/AI-FEA-P2.1-02-event-bus-runtime","isDraft":false,"mergeStateStatus":"CLEAN","number":55,"title":"[P2.1-02] event_bus runtime (stacked on ADR-014)"}

 succeeded in 4896ms:
total 312
-rw-r--r--@ 1 Zhuanz  wheel  36761 Apr 26 03:06 pr-50.diff
-rw-r--r--@ 1 Zhuanz  wheel  20170 Apr 26 03:06 pr-51.diff
-rw-r--r--@ 1 Zhuanz  wheel  26893 Apr 26 03:06 pr-52.diff
-rw-r--r--@ 1 Zhuanz  wheel  22672 Apr 26 03:06 pr-53.diff
-rw-r--r--@ 1 Zhuanz  wheel  23119 Apr 26 03:06 pr-54.diff
-rw-r--r--@ 1 Zhuanz  wheel  22855 Apr 26 03:06 pr-55.diff

 succeeded in 5152ms:
From https://github.com/kogamishinyajerry-ops/ai-structure-analysis
 * [new ref]         refs/pull/50/head -> pr-50
From https://github.com/kogamishinyajerry-ops/ai-structure-analysis
 * [new ref]         refs/pull/51/head -> pr-51
From https://github.com/kogamishinyajerry-ops/ai-structure-analysis
 * [new ref]         refs/pull/52/head -> pr-52
From https://github.com/kogamishinyajerry-ops/ai-structure-analysis
 * [new ref]         refs/pull/53/head -> pr-53
From https://github.com/kogamishinyajerry-ops/ai-structure-analysis
 * [new ref]         refs/pull/54/head -> pr-54
From https://github.com/kogamishinyajerry-ops/ai-structure-analysis
 * [new ref]         refs/pull/55/head -> pr-55

codex
The refs are coming down cleanly. I’m letting the long `gh pr view` and `gh pr diff` batches finish, then I’ll pivot into targeted file reads on the fetched PR heads so the line citations match the actual code under review.
codex
I have the exact changed-file scopes now. I’m reviewing the ADR and implementation pairs together where that helps catch contract drift, but I’ll keep the verdicts per-PR and only cite lines that exist on each PR head.
exec
/bin/zsh -lc "git show pr-50:schemas/ws_events.py | nl -ba | sed -n '1,260p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
     1	"""WebSocket event schema v1 for the workbench (ADR-014).
     2	
     3	The contract between LangGraph runtime and the React/TS frontend. Every
     4	event carries `schema_version` (literal "v1"), `seq` (monotonic int per
     5	run), `ts` (ISO-8601 UTC string), and `event` (discriminator).
     6	
     7	Privacy: events MUST NOT carry agent prompt text, raw RAG chunk text,
     8	raw user CAD bytes, or any field with `_secret` / `_internal` in its
     9	name. Large bodies travel as digest references; the frontend pulls the
    10	body via a separate authenticated REST endpoint.
    11	
    12	This module is NOT in HF1.4 (`schemas/sim_state.py`). It is a sibling
    13	file under `schemas/` per ADR-014's explicit non-touch of HF1.
    14	"""
    15	
    16	from __future__ import annotations
    17	
    18	from typing import Annotated, Literal, Union
    19	
    20	from pydantic import BaseModel, ConfigDict, Field
    21	
    22	WS_SCHEMA_VERSION: Literal["v1"] = "v1"
    23	
    24	# Stage names match Phase 1's six-stage LangGraph DAG (router → architect →
    25	# geometry → mesh → solver → reviewer + handoff). These are also the
    26	# `stage` values on `node.entered`.
    27	Stage = Literal["intent", "geometry", "mesh", "solver", "review", "handoff"]
    28	
    29	NodeStatus = Literal["ok", "err", "skipped"]
    30	
    31	# Reviewer verdicts mirror reviewer_advisor.GOVERNANCE_BIASING_VERDICTS plus
    32	# the non-biasing ones; pin here as a literal so a new verdict requires
    33	# a schema bump.
    34	ReviewerVerdict = Literal["Accept", "Accept with Note", "Reject", "Needs Review", "Re-run"]
    35	
    36	TerminalStatus = Literal["success", "error", "cancelled", "handoff"]
    37	
    38	ConfidenceIndicator = Literal["high", "medium", "low", "n/a"]
    39	
    40	# SHA-256 hex digest with `sha256:` prefix (44 chars total: "sha256:" + 64).
    41	DigestStr = Annotated[
    42	    str,
    43	    Field(
    44	        pattern=r"^sha256:[0-9a-f]{64}$",
    45	        description="SHA-256 hex digest with sha256: prefix",
    46	    ),
    47	]
    48	
    49	
    50	class _BaseEvent(BaseModel):
    51	    """All events share this header."""
    52	
    53	    model_config = ConfigDict(extra="forbid", frozen=True)
    54	
    55	    schema_version: Literal["v1"] = WS_SCHEMA_VERSION
    56	    run_id: str = Field(..., min_length=1)
    57	    seq: int = Field(..., ge=0)
    58	    ts: str = Field(..., description="ISO-8601 UTC timestamp")
    59	
    60	
    61	class RunStarted(_BaseEvent):
    62	    event: Literal["run.started"] = "run.started"
    63	    task_spec_digest: DigestStr
    64	    started_at: str | None = None
    65	    submitted_by: str | None = None
    66	
    67	
    68	class NodeEntered(_BaseEvent):
    69	    event: Literal["node.entered"] = "node.entered"
    70	    node_name: str = Field(..., min_length=1)
    71	    stage: Stage
    72	    inputs_digest: DigestStr | None = None
    73	
    74	
    75	class NodeProgress(_BaseEvent):
    76	    event: Literal["node.progress"] = "node.progress"
    77	    node_name: str = Field(..., min_length=1)
    78	    message: str
    79	    percent: int | None = Field(default=None, ge=0, le=100)
    80	
    81	
    82	class NodeExited(_BaseEvent):
    83	    event: Literal["node.exited"] = "node.exited"
    84	    node_name: str = Field(..., min_length=1)
    85	    duration_ms: int = Field(..., ge=0)
    86	    status: NodeStatus
    87	    outputs_digest: DigestStr | None = None
    88	    error_class: str | None = None
    89	
    90	
    91	class ArtifactReady(_BaseEvent):
    92	    event: Literal["artifact.ready"] = "artifact.ready"
    93	    kind: str = Field(..., min_length=1)
    94	    path: str = Field(..., min_length=1)
    95	    bytes: int = Field(..., ge=0)
    96	    digest: DigestStr | None = None
    97	    mime: str | None = None
    98	
    99	
   100	class RagQueried(_BaseEvent):
   101	    event: Literal["rag.queried"] = "rag.queried"
   102	    query_digest: DigestStr
   103	    top_k_titles: tuple[str, ...] = Field(default_factory=tuple)
   104	    scores: tuple[float, ...] = Field(default_factory=tuple)
   105	    source_filter: str | None = None
   106	
   107	
   108	class QuantitySummary(BaseModel):
   109	    """Compact projection of a SurrogateHint quantity. No notes, no extras."""
   110	
   111	    model_config = ConfigDict(extra="forbid", frozen=True)
   112	
   113	    name: str = Field(..., min_length=1)
   114	    value: float
   115	    unit: str = Field(..., min_length=1)
   116	    confidence: ConfidenceIndicator = "low"
   117	
   118	
   119	class SurrogateHintEvent(_BaseEvent):
   120	    event: Literal["surrogate.hint"] = "surrogate.hint"
   121	    provider: str = Field(..., min_length=1)
   122	    case_id: str = Field(..., min_length=1)
   123	    quantities_summary: tuple[QuantitySummary, ...] = Field(default_factory=tuple)
   124	    confidence_indicator: ConfidenceIndicator = "low"
   125	
   126	
   127	class ReviewerVerdictEvent(_BaseEvent):
   128	    event: Literal["reviewer.verdict"] = "reviewer.verdict"
   129	    verdict: ReviewerVerdict
   130	    fault_class: str
   131	    deviation_pct: float | None = None
   132	    notion_task_url: str | None = None
   133	
   134	
   135	class HandoffRequired(_BaseEvent):
   136	    event: Literal["handoff.required"] = "handoff.required"
   137	    reason: str = Field(..., min_length=1)
   138	    notion_task_url: str | None = None
   139	    recommended_action: str | None = None
   140	
   141	
   142	class BusDropped(_BaseEvent):
   143	    event: Literal["bus.dropped"] = "bus.dropped"
   144	    dropped_count: int = Field(..., ge=1)
   145	    dropped_kinds: tuple[str, ...] = Field(default_factory=tuple)
   146	
   147	
   148	class BusGap(_BaseEvent):
   149	    event: Literal["bus.gap"] = "bus.gap"
   150	    requested_since: int = Field(..., ge=0)
   151	    buffer_tail: int = Field(..., ge=0)
   152	
   153	
   154	class RunFinished(_BaseEvent):
   155	    event: Literal["run.finished"] = "run.finished"
   156	    terminal_status: TerminalStatus
   157	    total_duration_ms: int = Field(..., ge=0)
   158	    failure_summary: str | None = None
   159	
   160	
   161	# Discriminated union for parsing a stream of mixed events.
   162	# NOTE: typing.Union here (not X | Y) so this module loads on Python 3.9
   163	# environments. The PEP-604 syntax requires 3.10+ at module-level.
   164	WSEvent = Annotated[  # noqa: UP007
   165	    Union[  # noqa: UP007
   166	        RunStarted,
   167	        NodeEntered,
   168	        NodeProgress,
   169	        NodeExited,
   170	        ArtifactReady,
   171	        RagQueried,
   172	        SurrogateHintEvent,
   173	        ReviewerVerdictEvent,
   174	        HandoffRequired,
   175	        BusDropped,
   176	        BusGap,
   177	        RunFinished,
   178	    ],
   179	    Field(discriminator="event"),
   180	]
   181	
   182	# Critical events that backpressure must NEVER drop. The bus is required
   183	# to enqueue these even if the queue is otherwise full; older non-critical
   184	# events are evicted instead.
   185	CRITICAL_EVENT_KINDS: frozenset[str] = frozenset(
   186	    {
   187	        "run.started",
   188	        "run.finished",
   189	        "handoff.required",
   190	    }
   191	)
   192	
   193	
   194	def is_critical(event_kind: str) -> bool:
   195	    """True if the event kind must survive backpressure eviction.
   196	
   197	    Note: `node.exited` with `status="err"` is also critical at the
   198	    consumer level, but we keep that judgement in the event-bus
   199	    eviction policy (it inspects the payload), not in this set.
   200	    """
   201	    return event_kind in CRITICAL_EVENT_KINDS

exec
/bin/zsh -lc "git show pr-50:tests/test_ws_events_schema.py | nl -ba | sed -n '1,260p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
     1	"""Tests for schemas/ws_events.py — the WebSocket event contract (ADR-014).
     2	
     3	Pins the v1 schema before any runtime code consumes it. Every event kind
     4	must:
     5	  * round-trip through json (model_dump_json → model_validate_json)
     6	  * reject unknown extra fields (extra="forbid")
     7	  * be selected correctly by the discriminated union on the `event` tag
     8	  * be frozen (immutable)
     9	  * fail validation on missing required fields
    10	"""
    11	
    12	from __future__ import annotations
    13	
    14	import json
    15	from typing import Any
    16	
    17	import pytest
    18	
    19	try:
    20	    from pydantic import TypeAdapter, ValidationError
    21	
    22	    from schemas.ws_events import (
    23	        CRITICAL_EVENT_KINDS,
    24	        WS_SCHEMA_VERSION,
    25	        ArtifactReady,
    26	        BusDropped,
    27	        BusGap,
    28	        HandoffRequired,
    29	        NodeEntered,
    30	        NodeExited,
    31	        NodeProgress,
    32	        QuantitySummary,
    33	        RagQueried,
    34	        ReviewerVerdictEvent,
    35	        RunFinished,
    36	        RunStarted,
    37	        SurrogateHintEvent,
    38	        WSEvent,
    39	        is_critical,
    40	    )
    41	except ImportError as e:
    42	    pytest.skip(f"ws_events imports failed: {e}", allow_module_level=True)
    43	
    44	
    45	VALID_DIGEST = "sha256:" + "a" * 64
    46	RUN_ID = "run-12345"
    47	TS = "2026-04-26T12:00:00Z"
    48	
    49	
    50	def _common(seq: int = 0) -> dict[str, Any]:
    51	    """Header fields every event needs."""
    52	    return {"run_id": RUN_ID, "seq": seq, "ts": TS}
    53	
    54	
    55	# ---------------------------------------------------------------------------
    56	# Schema constants
    57	# ---------------------------------------------------------------------------
    58	
    59	
    60	def test_schema_version_is_v1():
    61	    assert WS_SCHEMA_VERSION == "v1"
    62	
    63	
    64	def test_critical_event_kinds_membership():
    65	    assert "run.started" in CRITICAL_EVENT_KINDS
    66	    assert "run.finished" in CRITICAL_EVENT_KINDS
    67	    assert "handoff.required" in CRITICAL_EVENT_KINDS
    68	    # Non-critical examples
    69	    assert "node.progress" not in CRITICAL_EVENT_KINDS
    70	    assert "rag.queried" not in CRITICAL_EVENT_KINDS
    71	
    72	
    73	def test_is_critical_helper():
    74	    assert is_critical("run.started") is True
    75	    assert is_critical("run.finished") is True
    76	    assert is_critical("handoff.required") is True
    77	    assert is_critical("node.progress") is False
    78	    assert is_critical("totally-unknown") is False
    79	
    80	
    81	# ---------------------------------------------------------------------------
    82	# RunStarted
    83	# ---------------------------------------------------------------------------
    84	
    85	
    86	def test_run_started_minimal():
    87	    e = RunStarted(**_common(), task_spec_digest=VALID_DIGEST)
    88	    assert e.event == "run.started"
    89	    assert e.schema_version == "v1"
    90	
    91	
    92	def test_run_started_round_trip():
    93	    e = RunStarted(**_common(), task_spec_digest=VALID_DIGEST, submitted_by="alice")
    94	    j = e.model_dump_json()
    95	    parsed = RunStarted.model_validate_json(j)
    96	    assert parsed == e
    97	
    98	
    99	def test_run_started_rejects_extra_field():
   100	    with pytest.raises(ValidationError):
   101	        RunStarted(**_common(), task_spec_digest=VALID_DIGEST, sneaky="hi")
   102	
   103	
   104	def test_run_started_rejects_bad_digest():
   105	    with pytest.raises(ValidationError):
   106	        RunStarted(**_common(), task_spec_digest="not-a-digest")
   107	
   108	
   109	def test_run_started_rejects_short_run_id():
   110	    with pytest.raises(ValidationError):
   111	        RunStarted(run_id="", seq=0, ts=TS, task_spec_digest=VALID_DIGEST)
   112	
   113	
   114	def test_run_started_rejects_negative_seq():
   115	    with pytest.raises(ValidationError):
   116	        RunStarted(run_id=RUN_ID, seq=-1, ts=TS, task_spec_digest=VALID_DIGEST)
   117	
   118	
   119	# ---------------------------------------------------------------------------
   120	# NodeEntered + stage enum
   121	# ---------------------------------------------------------------------------
   122	
   123	
   124	@pytest.mark.parametrize("stage", ["intent", "geometry", "mesh", "solver", "review", "handoff"])
   125	def test_node_entered_each_stage(stage):
   126	    e = NodeEntered(**_common(), node_name="router", stage=stage)
   127	    assert e.stage == stage
   128	
   129	
   130	def test_node_entered_rejects_unknown_stage():
   131	    with pytest.raises(ValidationError):
   132	        NodeEntered(**_common(), node_name="router", stage="unknown_stage")
   133	
   134	
   135	def test_node_entered_optional_inputs_digest():
   136	    e = NodeEntered(**_common(), node_name="router", stage="intent", inputs_digest=VALID_DIGEST)
   137	    assert e.inputs_digest == VALID_DIGEST
   138	
   139	
   140	def test_node_entered_round_trip():
   141	    e = NodeEntered(**_common(seq=42), node_name="solver", stage="solver")
   142	    parsed = NodeEntered.model_validate_json(e.model_dump_json())
   143	    assert parsed == e
   144	    assert parsed.seq == 42
   145	
   146	
   147	# ---------------------------------------------------------------------------
   148	# NodeProgress
   149	# ---------------------------------------------------------------------------
   150	
   151	
   152	def test_node_progress_with_percent():
   153	    e = NodeProgress(**_common(), node_name="solver", message="iter 50", percent=50)
   154	    assert e.percent == 50
   155	
   156	
   157	def test_node_progress_no_percent():
   158	    e = NodeProgress(**_common(), node_name="solver", message="working")
   159	    assert e.percent is None
   160	
   161	
   162	@pytest.mark.parametrize("bad", [-1, 101, 200])
   163	def test_node_progress_rejects_out_of_range_percent(bad):
   164	    with pytest.raises(ValidationError):
   165	        NodeProgress(**_common(), node_name="solver", message="x", percent=bad)
   166	
   167	
   168	# ---------------------------------------------------------------------------
   169	# NodeExited
   170	# ---------------------------------------------------------------------------
   171	
   172	
   173	@pytest.mark.parametrize("status", ["ok", "err", "skipped"])
   174	def test_node_exited_each_status(status):
   175	    e = NodeExited(**_common(), node_name="solver", duration_ms=1234, status=status)
   176	    assert e.status == status
   177	
   178	
   179	def test_node_exited_rejects_unknown_status():
   180	    with pytest.raises(ValidationError):
   181	        NodeExited(**_common(), node_name="solver", duration_ms=1, status="maybe")
   182	
   183	
   184	def test_node_exited_negative_duration_rejected():
   185	    with pytest.raises(ValidationError):
   186	        NodeExited(**_common(), node_name="solver", duration_ms=-1, status="ok")
   187	
   188	
   189	# ---------------------------------------------------------------------------
   190	# ArtifactReady
   191	# ---------------------------------------------------------------------------
   192	
   193	
   194	def test_artifact_ready_minimal():
   195	    e = ArtifactReady(**_common(), kind="frd", path="runs/r1/result.frd", bytes=1024)
   196	    assert e.kind == "frd"
   197	    assert e.bytes == 1024
   198	
   199	
   200	def test_artifact_ready_with_digest_and_mime():
   201	    e = ArtifactReady(
   202	        **_common(),
   203	        kind="vtu",
   204	        path="runs/r1/result.vtu",
   205	        bytes=2048,
   206	        digest=VALID_DIGEST,
   207	        mime="application/xml",
   208	    )
   209	    assert e.digest == VALID_DIGEST
   210	    assert e.mime == "application/xml"
   211	
   212	
   213	# ---------------------------------------------------------------------------
   214	# RagQueried — privacy: only digest + titles, never raw query
   215	# ---------------------------------------------------------------------------
   216	
   217	
   218	def test_rag_queried_no_raw_query_field():
   219	    """The schema must NOT carry the raw query string. Only a digest."""
   220	    fields = set(RagQueried.model_fields.keys())
   221	    assert "query" not in fields, "raw query must not be a field — privacy boundary"
   222	    assert "query_digest" in fields
   223	
   224	
   225	def test_rag_queried_minimal():
   226	    e = RagQueried(**_common(), query_digest=VALID_DIGEST)
   227	    assert e.top_k_titles == ()
   228	    assert e.scores == ()
   229	
   230	
   231	def test_rag_queried_with_titles_and_scores():
   232	    e = RagQueried(
   233	        **_common(),
   234	        query_digest=VALID_DIGEST,
   235	        top_k_titles=("ADR-011", "FP-002"),
   236	        scores=(0.9, 0.7),
   237	    )
   238	    assert e.top_k_titles == ("ADR-011", "FP-002")
   239	    assert e.scores == (0.9, 0.7)
   240	
   241	
   242	def test_rag_queried_with_source_filter():
   243	    e = RagQueried(**_common(), query_digest=VALID_DIGEST, source_filter="project-adr-fp")
   244	    assert e.source_filter == "project-adr-fp"
   245	
   246	
   247	# ---------------------------------------------------------------------------
   248	# SurrogateHintEvent — privacy: no notes, no extras
   249	# ---------------------------------------------------------------------------
   250	
   251	
   252	def test_surrogate_hint_event_no_notes_field():
   253	    """The schema must NOT carry the surrogate's free-text notes."""
   254	    fields = set(SurrogateHintEvent.model_fields.keys())
   255	    assert "notes" not in fields, "raw notes must not be a field — privacy boundary"
   256	    assert "extra" not in fields, "extra dict must not be a field — privacy boundary"
   257	
   258	
   259	def test_surrogate_hint_event_minimal():
   260	    e = SurrogateHintEvent(**_common(), provider="placeholder@v0", case_id="GS-001")

exec
/bin/zsh -lc "git show pr-50:docs/adr/ADR-014-ws-event-bus-for-workbench.md | nl -ba | sed -n '1,260p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
     1	# ADR-014: WebSocket Event Bus for the Workbench
     2	
     3	- **Status:** Draft (post-R2 of #24/#25, pending Codex R1)
     4	- **Decider:** Claude Code CLI (Opus 4.7, 1M context) — human-confirmed
     5	- **Date:** 2026-04-26
     6	- **Related Phase:** 2.0 — Workbench Skeleton (the first concrete artifact of the engineer-facing visualization workbench pivot)
     7	- **Branch:** `feature/AI-FEA-ADR-014-ws-event-bus`
     8	- **Companion ADRs (Draft, parallel):** ADR-015 (Workbench → Agent RPC boundary), ADR-016 (`.frd → .vtu` + result viz stack), ADR-017 (RAG facade in-process + CLI/lib parity)
     9	
    10	---
    11	
    12	## Context
    13	
    14	Phase 1.5 closes a Foundation-Freeze that culminates in Phase 2: a Web Console that lets engineers run end-to-end FEA simulations through this project. Phase 2's North Star (per the 2026-04-26 architecture review by Opus 4.7 in Notion):
    15	
    16	> "可视化仿真工作台,让任何一个工程师一上手就能用这个系统进行全流程仿真,并且清晰的看到逐步的流程"
    17	
    18	The Phase 2 architecture review settled three questions whose joint answer determines the workbench's runtime shape:
    19	
    20	1. **Backend stack** = FastAPI + Pydantic v2 (already on `main`); the workbench is not a Streamlit demo
    21	2. **Frontend stack** = React/TypeScript over WebSocket
    22	3. **Visibility** = engineers must see every LangGraph node entered/exited, every agent decision, every RAG retrieval, every Reviewer verdict — not a black-box "spinner then result"
    23	
    24	The remaining design question, which **this ADR closes**, is: *what is the on-the-wire contract between the LangGraph runtime and the React frontend*?
    25	
    26	This is the first time agent-internal state will leave the Python process. The contract chosen here will determine:
    27	
    28	- whether agents on `main` need to be modified (HF1 risk)
    29	- what raw text leaks to a browser tab (security/privacy risk per Q7-R3 of the architecture review)
    30	- how the frontend handles disconnect/reconnect during a 30-minute CalculiX run (engineering-trust risk per Q7-R8)
    31	- whether the four already-merged-in-PR-stack RAG CLIs (`#38`–`#48`) can plug into the workbench without re-implementation
    32	
    33	---
    34	
    35	## Decision
    36	
    37	**Wire format**: a single WebSocket endpoint at `/ws/runs/{run_id}` emitting an append-only stream of typed JSON events. Each event carries `schema_version: "v1"`, an integer `seq`, an ISO-8601 `ts`, and a discriminator field `event`.
    38	
    39	**Transport**: native WebSockets via FastAPI's `websockets` integration. **No Redis / Kafka / RabbitMQ.** Phase 2 is single-node; an in-process `asyncio.Queue` is the bus, fed by LangGraph callbacks and drained by the WebSocket endpoint.
    40	
    41	**Schema location**: a new file `schemas/ws_events.py` (Pydantic v2 models, `frozen=True`, `extra="forbid"`). **Not** in `schemas/sim_state.py` (HF1.4); a separate file with no overlap to existing state.
    42	
    43	**LangGraph integration**: a new module `backend/app/runtime/langgraph_callbacks.py` registers a callback handler with `config={"callbacks": [...]}`. **No agent file is modified** — `agents/router.py`, `agents/architect.py`, `agents/geometry.py`, `agents/mesh.py`, `agents/solver.py`, `agents/reviewer.py`, `agents/calculix_driver.py` are all untouched. (Of these, HF1.1, HF1.2, HF1.3, HF1.5 are HF1 — touching them would require an HF1 zone-carve ADR, which we are deliberately avoiding.)
    44	
    45	**Privacy / data-leak boundary**: events MUST NOT carry agent prompt text, raw RAG chunk text, raw user CAD bytes, or any field with `_secret` / `_internal` in its name. Large bodies travel as **digest references** (`inputs_digest: "sha256:..."`); the frontend pulls the body via a separate authenticated REST endpoint `GET /runs/{run_id}/nodes/{node_name}/io` only when a user explicitly clicks "Show details".
    46	
    47	**Backpressure**: the in-process queue is bounded (capacity 1024). On overflow the *oldest non-critical* event is dropped (terminal events `run.started` / `run.finished` / `handoff.required` / `node.exited(status=err)` are never dropped). A `bus.dropped` event records the loss, so the frontend can show a banner.
    48	
    49	**Resume semantics**: the endpoint accepts `?since_seq=N` on connect; the bus retains a per-run ring buffer of the last 256 events. If `N` is older than the buffer's tail, the endpoint emits `bus.gap` and the frontend MUST refetch state via REST (not from the bus alone).
    50	
    51	---
    52	
    53	## Event schema (v1)
    54	
    55	The full Pydantic models will live in `schemas/ws_events.py`. This section is the contract reviewers must approve.
    56	
    57	| event | when emitted | required fields | optional fields |
    58	|-------|--------------|----------------|----------------|
    59	| `run.started` | LangGraph compile + invoke succeeded | `run_id`, `seq`, `ts`, `task_spec_digest` | `started_at`, `submitted_by` |
    60	| `node.entered` | LangGraph node function entered | `run_id`, `seq`, `ts`, `node_name`, `stage` | `inputs_digest` |
    61	| `node.progress` | node-internal explicit emit | `run_id`, `seq`, `ts`, `node_name`, `message` | `percent` (0–100) |
    62	| `node.exited` | node function returned (success or error) | `run_id`, `seq`, `ts`, `node_name`, `duration_ms`, `status` | `outputs_digest`, `error_class` |
    63	| `artifact.ready` | a tracked artifact landed on disk | `run_id`, `seq`, `ts`, `kind`, `path`, `bytes` | `digest`, `mime` |
    64	| `rag.queried` | `reviewer_advisor.advise()` or kb.query was called | `run_id`, `seq`, `ts`, `query_digest`, `top_k_titles[]`, `scores[]` | `source_filter` |
    65	| `surrogate.hint` | a `SurrogateHint` was generated | `run_id`, `seq`, `ts`, `provider`, `case_id`, `quantities_summary[]` | `confidence_indicator` |
    66	| `reviewer.verdict` | the Reviewer node produced a verdict | `run_id`, `seq`, `ts`, `verdict`, `fault_class`, `deviation_pct?` | `notion_task_url` |
    67	| `handoff.required` | a TrustGate verdict requires human review | `run_id`, `seq`, `ts`, `reason`, `notion_task_url` | `recommended_action` |
    68	| `bus.dropped` | bounded queue dropped a non-critical event | `run_id`, `seq`, `ts`, `dropped_count`, `dropped_kinds[]` | — |
    69	| `bus.gap` | resume requested before the ring buffer's tail | `run_id`, `seq`, `ts`, `requested_since`, `buffer_tail` | — |
    70	| `run.finished` | the LangGraph state machine exited | `run_id`, `seq`, `ts`, `terminal_status`, `total_duration_ms` | `failure_summary` |
    71	
    72	Key constraints:
    73	
    74	- `stage` ∈ `{intent, geometry, mesh, solver, review, handoff}` — fixed enum, names match Phase 1's existing six-stage DAG
    75	- `status` (on `node.exited`) ∈ `{ok, err, skipped}`
    76	- `verdict` ∈ `{Accept, Accept with Note, Reject, Needs Review, Re-run}` — matches `reviewer_advisor.GOVERNANCE_BIASING_VERDICTS` plus the non-biasing ones
    77	- `terminal_status` ∈ `{success, error, cancelled, handoff}`
    78	- `quantities_summary[]` is a tuple of `(name, value, unit, confidence)` — **never** the full SurrogateHint (no notes, no provider-specific extras)
    79	- `task_spec_digest`, `inputs_digest`, `outputs_digest`, `query_digest` are SHA-256 hex strings
    80	
    81	---
    82	
    83	## Considered alternatives
    84	
    85	### gRPC streaming
    86	Pros: typed, multiplexed, mature.
    87	Cons: requires `grpc-web` proxy in front of the React app; adds an extra hop and a new mental-model burden. We are running everything in one Python process; multiplexing is overkill. **Rejected.**
    88	
    89	### Server-Sent Events (SSE)
    90	Pros: simpler than WebSocket (one-way HTTP stream, browser-native); no upgrade handshake.
    91	Cons: one-way only — but the workbench will eventually need user → server commands (cancel run, request retry). Re-using WebSocket here saves a future migration. **Rejected for the workbench critical path; SSE retained as a fallback for read-only embedded views in Phase 2.3+.**
    92	
    93	### Polling + REST snapshots
    94	Pros: no long-lived connections; works through any proxy.
    95	Cons: latency floor ≥ poll interval; for engineering trust we need <500 ms node-state latency. **Rejected.**
    96	
    97	### Redis pub/sub now
    98	Pros: future-proof for multi-node.
    99	Cons: adds an operational dependency before any user has logged in. The architecture review explicitly recommends *not* introducing Redis until Phase 3. **Rejected for Phase 2.**
   100	
   101	---
   102	
   103	## Consequences
   104	
   105	**Intended:**
   106	
   107	- Workbench frontend can render every LangGraph stage transition in <100 ms of the agent producing it
   108	- Disconnect/reconnect during a 30-min CalculiX run survives via `?since_seq` resume
   109	- New event kinds add to the schema as `v1` minor extensions; consumers ignore unknown `event` strings
   110	- Agents and HF1 zones stay untouched; the visibility layer is purely additive
   111	- The four RAG CLIs from PR #38–#48 plug into `rag.queried` events via the in-process facade ADR-017 will define
   112	
   113	**Unintended (acknowledged):**
   114	
   115	- One process bug now spans Python + JS — debugging requires both stacks; ADR-014 includes a contract test (described below) to keep regressions on one side
   116	- The 1024-event queue cap means a sufficiently chatty run can drop `node.progress` events; users will see progress jump rather than animate. Acceptable: progress is informational, not authoritative
   117	- The ring-buffer tail of 256 events means a frontend can permanently miss events if it disconnects for more than ~10 minutes during a busy run. The `bus.gap` event tells it to refetch via REST; not silent loss
   118	
   119	**Out of scope:**
   120	
   121	- Multi-tenant isolation: Phase 2 assumes a single trusted operator per server. Multi-user comes in Phase 2.4+
   122	- Authentication on the WS endpoint: deferred to Phase 2.1 (ADR-015 will spec the auth boundary alongside the RPC contract)
   123	- Persisting the event stream to disk for replay/audit: a future ADR (likely ADR-019 or later)
   124	
   125	---
   126	
   127	## Implementation plan
   128	
   129	This ADR alone produces no executable code beyond the schema file; the workbench code is in subsequent PRs (Phase 2.0).
   130	
   131	| File | Status | Owner | Notes |
   132	|------|--------|-------|-------|
   133	| `docs/adr/ADR-014-ws-event-bus-for-workbench.md` | this PR | Claude Code | M1 trigger |
   134	| `schemas/ws_events.py` | this PR | Claude Code | Pydantic v2 models matching the table above |
   135	| `tests/test_ws_events_schema.py` | this PR | Claude Code | unit tests: each event kind round-trips JSON; required-field validation; `extra="forbid"` enforcement; `schema_version` constant |
   136	| `backend/app/runtime/event_bus.py` | Phase 2.0 follow-up | Claude Code | `asyncio.Queue` + ring buffer + bounded backpressure |
   137	| `backend/app/runtime/langgraph_callbacks.py` | Phase 2.0 follow-up | Claude Code | translates LangGraph callback signals → WS events |
   138	| `backend/app/api/ws_runs.py` | Phase 2.0 follow-up | Claude Code | the `/ws/runs/{run_id}` endpoint |
   139	| `frontend/` | Phase 2.0 follow-up | Claude Code | React/TS skeleton consuming the bus |
   140	
   141	The schema PR (this one) and the runtime PRs land sequentially; no PR depends on R2 of PR #24/#25 because no path here changes governance enforcement. **This PR's self-pass-rate is `50%`** — under the BLOCKING ceiling currently in force, deliberately conservative because the schema is the contract the rest of Phase 2 will follow.
   142	
   143	---
   144	
   145	## Codex review expectation
   146	
   147	This PR triggers M1 (governance text in `docs/adr/` and `schemas/`) and M2 (executable assertions in the test file). It does NOT trigger M3 (no HF1 hot-zone touched), M4 (no enforcement coupling — the schema is read-only contract), or M5 (50% claim is below the 50% threshold in the M5 trigger language; but under the current 30% BLOCKING ceiling the cap-check still fires).
   148	
   149	Self-pass-rate: **30%** — match the current BLOCKING ceiling. We are deliberately conservative on the contract PR because every downstream Phase 2 PR will pivot off it; Codex review here saves N future R2 cycles.
   150	
   151	---
   152	
   153	## Cross-references
   154	
   155	- ADR-011 §T2 — M1+M2 trigger compliance basis
   156	- ADR-011 §HF1 — explicit non-touch of HF1.1–HF1.9 (this ADR adds `schemas/ws_events.py` which is a new file alongside HF1.4 `schemas/sim_state.py`, NOT inside HF1.4)
   157	- ADR-012 R2 (PR #24) — the calibration cap whose 30% BLOCKING ceiling this PR honors
   158	- ADR-015 (Draft, parallel) — Workbench → Agent RPC boundary; defines what triggers `node.entered`
   159	- ADR-016 (Draft, parallel) — Result viz stack; `artifact.ready` events feed it
   160	- ADR-017 (Draft, parallel) — RAG facade; `rag.queried` events come from there
   161	- Architecture review by Opus 4.7 (Notion async, 2026-04-26) — Q1, Q2, Q5, Q7 are the inputs to this ADR's specific decisions
   162	
   163	---
   164	
   165	## Status notes
   166	
   167	**Draft → Final criteria:**
   168	
   169	1. Codex R1 returns APPROVE or APPROVE_WITH_NITS
   170	2. The Phase 2.0 follow-up PRs (event bus, callbacks, WS endpoint) implement this schema verbatim
   171	3. After 3 consecutive workbench runs in dev, no event-kind addition is needed (revisit `schema_version` if it does)
   172	
   173	Until all three are met, this ADR remains `Draft`.

exec
/bin/zsh -lc "git show pr-50:tests/test_ws_events_schema.py | nl -ba | sed -n '261,560p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
   261	    assert e.quantities_summary == ()
   262	    assert e.confidence_indicator == "low"
   263	
   264	
   265	def test_surrogate_hint_event_with_quantities():
   266	    q1 = QuantitySummary(name="max_displacement", value=1.234, unit="mm", confidence="low")
   267	    q2 = QuantitySummary(name="sigma_vm_max", value=210.0, unit="MPa", confidence="medium")
   268	    e = SurrogateHintEvent(
   269	        **_common(),
   270	        provider="manual@v0",
   271	        case_id="GS-001",
   272	        quantities_summary=(q1, q2),
   273	        confidence_indicator="medium",
   274	    )
   275	    assert len(e.quantities_summary) == 2
   276	    assert e.confidence_indicator == "medium"
   277	
   278	
   279	def test_quantity_summary_frozen():
   280	    q = QuantitySummary(name="x", value=1.0, unit="mm")
   281	    with pytest.raises((TypeError, ValidationError, AttributeError)):
   282	        q.name = "mutated"  # type: ignore[misc]
   283	
   284	
   285	def test_quantity_summary_rejects_unknown_confidence():
   286	    with pytest.raises(ValidationError):
   287	        QuantitySummary(name="x", value=1.0, unit="mm", confidence="medium-high")
   288	
   289	
   290	# ---------------------------------------------------------------------------
   291	# ReviewerVerdictEvent
   292	# ---------------------------------------------------------------------------
   293	
   294	
   295	@pytest.mark.parametrize(
   296	    "verdict", ["Accept", "Accept with Note", "Reject", "Needs Review", "Re-run"]
   297	)
   298	def test_reviewer_verdict_each_value(verdict):
   299	    e = ReviewerVerdictEvent(**_common(), verdict=verdict, fault_class="solver_convergence")
   300	    assert e.verdict == verdict
   301	
   302	
   303	def test_reviewer_verdict_rejects_unknown():
   304	    with pytest.raises(ValidationError):
   305	        ReviewerVerdictEvent(**_common(), verdict="ApproveWithNits", fault_class="x")
   306	
   307	
   308	def test_reviewer_verdict_optional_deviation():
   309	    e = ReviewerVerdictEvent(
   310	        **_common(),
   311	        verdict="Accept",
   312	        fault_class="none",
   313	        deviation_pct=2.5,
   314	    )
   315	    assert e.deviation_pct == 2.5
   316	
   317	
   318	# ---------------------------------------------------------------------------
   319	# HandoffRequired
   320	# ---------------------------------------------------------------------------
   321	
   322	
   323	def test_handoff_required_minimal():
   324	    e = HandoffRequired(**_common(), reason="deviation > 50%")
   325	    assert e.reason == "deviation > 50%"
   326	    assert e.notion_task_url is None
   327	
   328	
   329	def test_handoff_required_with_notion_link():
   330	    e = HandoffRequired(
   331	        **_common(),
   332	        reason="critical fault",
   333	        notion_task_url="https://notion.so/task/123",
   334	        recommended_action="Re-run with refined mesh",
   335	    )
   336	    assert e.notion_task_url.startswith("https://")
   337	
   338	
   339	# ---------------------------------------------------------------------------
   340	# BusDropped + BusGap
   341	# ---------------------------------------------------------------------------
   342	
   343	
   344	def test_bus_dropped_minimal():
   345	    e = BusDropped(**_common(), dropped_count=3, dropped_kinds=("node.progress",))
   346	    assert e.dropped_count == 3
   347	
   348	
   349	def test_bus_dropped_zero_count_rejected():
   350	    with pytest.raises(ValidationError):
   351	        BusDropped(**_common(), dropped_count=0)
   352	
   353	
   354	def test_bus_gap_minimal():
   355	    e = BusGap(**_common(), requested_since=10, buffer_tail=50)
   356	    assert e.requested_since == 10
   357	    assert e.buffer_tail == 50
   358	
   359	
   360	# ---------------------------------------------------------------------------
   361	# RunFinished
   362	# ---------------------------------------------------------------------------
   363	
   364	
   365	@pytest.mark.parametrize("status", ["success", "error", "cancelled", "handoff"])
   366	def test_run_finished_each_terminal_status(status):
   367	    e = RunFinished(**_common(), terminal_status=status, total_duration_ms=12345)
   368	    assert e.terminal_status == status
   369	
   370	
   371	def test_run_finished_rejects_unknown_status():
   372	    with pytest.raises(ValidationError):
   373	        RunFinished(**_common(), terminal_status="ok", total_duration_ms=1)
   374	
   375	
   376	# ---------------------------------------------------------------------------
   377	# Discriminated union — wire-format parsing
   378	# ---------------------------------------------------------------------------
   379	
   380	
   381	def _ws_event_adapter():
   382	    return TypeAdapter(WSEvent)
   383	
   384	
   385	def test_discriminator_parses_run_started():
   386	    payload = {
   387	        "schema_version": "v1",
   388	        "event": "run.started",
   389	        "run_id": RUN_ID,
   390	        "seq": 0,
   391	        "ts": TS,
   392	        "task_spec_digest": VALID_DIGEST,
   393	    }
   394	    parsed = _ws_event_adapter().validate_python(payload)
   395	    assert isinstance(parsed, RunStarted)
   396	
   397	
   398	def test_discriminator_parses_node_exited():
   399	    payload = {
   400	        "schema_version": "v1",
   401	        "event": "node.exited",
   402	        "run_id": RUN_ID,
   403	        "seq": 7,
   404	        "ts": TS,
   405	        "node_name": "solver",
   406	        "duration_ms": 2000,
   407	        "status": "ok",
   408	    }
   409	    parsed = _ws_event_adapter().validate_python(payload)
   410	    assert isinstance(parsed, NodeExited)
   411	    assert parsed.status == "ok"
   412	
   413	
   414	def test_discriminator_rejects_unknown_event_kind():
   415	    payload = {
   416	        "schema_version": "v1",
   417	        "event": "bogus.event",
   418	        "run_id": RUN_ID,
   419	        "seq": 0,
   420	        "ts": TS,
   421	    }
   422	    with pytest.raises(ValidationError):
   423	        _ws_event_adapter().validate_python(payload)
   424	
   425	
   426	def test_round_trip_via_union_for_every_event_kind():
   427	    """Build one of each, dump, and parse back through the union."""
   428	    samples = [
   429	        RunStarted(**_common(seq=0), task_spec_digest=VALID_DIGEST),
   430	        NodeEntered(**_common(seq=1), node_name="router", stage="intent"),
   431	        NodeProgress(**_common(seq=2), node_name="router", message="ok", percent=10),
   432	        NodeExited(**_common(seq=3), node_name="router", duration_ms=100, status="ok"),
   433	        ArtifactReady(**_common(seq=4), kind="frd", path="x", bytes=1),
   434	        RagQueried(**_common(seq=5), query_digest=VALID_DIGEST),
   435	        SurrogateHintEvent(**_common(seq=6), provider="p", case_id="c"),
   436	        ReviewerVerdictEvent(**_common(seq=7), verdict="Accept", fault_class="none"),
   437	        HandoffRequired(**_common(seq=8), reason="r"),
   438	        BusDropped(**_common(seq=9), dropped_count=1),
   439	        BusGap(**_common(seq=10), requested_since=0, buffer_tail=10),
   440	        RunFinished(**_common(seq=11), terminal_status="success", total_duration_ms=10),
   441	    ]
   442	    adapter = _ws_event_adapter()
   443	    for original in samples:
   444	        payload = json.loads(original.model_dump_json())
   445	        parsed = adapter.validate_python(payload)
   446	        assert parsed == original, f"round-trip failed for {type(original).__name__}"
   447	
   448	
   449	# ---------------------------------------------------------------------------
   450	# Frozen invariant
   451	# ---------------------------------------------------------------------------
   452	
   453	
   454	def test_event_is_frozen():
   455	    e = RunStarted(**_common(), task_spec_digest=VALID_DIGEST)
   456	    with pytest.raises((TypeError, ValidationError, AttributeError)):
   457	        e.run_id = "mutated"  # type: ignore[misc]
   458	
   459	
   460	# ---------------------------------------------------------------------------
   461	# Privacy guard rails (negative tests)
   462	# ---------------------------------------------------------------------------
   463	
   464	
   465	def test_no_event_carries_secret_or_internal_fields():
   466	    """Sweep every WSEvent variant for fields named *_secret / *_internal /
   467	    raw_query / raw_text / agent_thought / prompt — these are the boundary
   468	    classes that ADR-014 forbids."""
   469	    forbidden_substrings = (
   470	        "secret",
   471	        "internal",
   472	        "raw_query",
   473	        "raw_text",
   474	        "agent_thought",
   475	        "prompt",
   476	    )
   477	    classes = [
   478	        RunStarted,
   479	        NodeEntered,
   480	        NodeProgress,
   481	        NodeExited,
   482	        ArtifactReady,
   483	        RagQueried,
   484	        SurrogateHintEvent,
   485	        ReviewerVerdictEvent,
   486	        HandoffRequired,
   487	        BusDropped,
   488	        BusGap,
   489	        RunFinished,
   490	        QuantitySummary,
   491	    ]
   492	    for cls in classes:
   493	        for fname in cls.model_fields:
   494	            lower = fname.lower()
   495	            for forbidden in forbidden_substrings:
   496	                assert forbidden not in lower, (
   497	                    f"{cls.__name__}.{fname} contains forbidden substring "
   498	                    f"{forbidden!r} — ADR-014 privacy boundary violated"
   499	                )

exec
/bin/zsh -lc "git show pr-51:tests/test_workbench_facade_discipline.py | nl -ba | sed -n '1,320p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
     1	"""Facade discipline check for ADR-015.
     2	
     3	Asserts the contract from `docs/adr/ADR-015-workbench-agent-rpc-boundary.md`:
     4	
     5	1. Only `backend/app/workbench/agent_facade.py` may import from `agents.*`.
     6	2. `agent_facade.py` does not assign to attributes of `agents.*` modules
     7	   (read-only contract — agents emit effects, the facade observes them).
     8	3. No file under `backend/app/workbench/` imports from `schemas.sim_state`
     9	   (HF1.4); the workbench surface uses `schemas.sim_plan` only.
    10	
    11	Pure-AST static check — no module-level execution of workbench code.
    12	Skips when `backend/app/workbench/` does not exist (Phase 2.1 follow-up
    13	PRs add the actual modules; this test guards their landing).
    14	"""
    15	
    16	from __future__ import annotations
    17	
    18	import ast
    19	from pathlib import Path
    20	
    21	import pytest
    22	
    23	_REPO_ROOT = Path(__file__).resolve().parent.parent
    24	_WORKBENCH_DIR = _REPO_ROOT / "backend" / "app" / "workbench"
    25	_FACADE_FILENAME = "agent_facade.py"
    26	
    27	
    28	def _workbench_py_files() -> list[Path]:
    29	    if not _WORKBENCH_DIR.is_dir():
    30	        return []
    31	    return sorted(p for p in _WORKBENCH_DIR.rglob("*.py") if p.is_file())
    32	
    33	
    34	def _is_agents_module(module: str | None) -> bool:
    35	    if module is None:
    36	        return False
    37	    return module == "agents" or module.startswith("agents.")
    38	
    39	
    40	def _is_sim_state_module(module: str | None) -> bool:
    41	    if module is None:
    42	        return False
    43	    return module == "schemas.sim_state"
    44	
    45	
    46	def _imports_from(tree: ast.AST, predicate) -> list[ast.AST]:
    47	    hits: list[ast.AST] = []
    48	    for node in ast.walk(tree):
    49	        if isinstance(node, ast.ImportFrom) and predicate(node.module):
    50	            hits.append(node)
    51	        elif isinstance(node, ast.Import):
    52	            for alias in node.names:
    53	                if predicate(alias.name):
    54	                    hits.append(node)
    55	                    break
    56	    return hits
    57	
    58	
    59	def _assigns_to_agents_attribute(tree: ast.AST) -> list[ast.Assign]:
    60	    """Find `agents.X.Y = ...` style mutations of agent module state."""
    61	    hits: list[ast.Assign] = []
    62	    for node in ast.walk(tree):
    63	        if not isinstance(node, ast.Assign):
    64	            continue
    65	        for target in node.targets:
    66	            if not isinstance(target, ast.Attribute):
    67	                continue
    68	            base = target
    69	            while isinstance(base, ast.Attribute):
    70	                base = base.value
    71	            if isinstance(base, ast.Name) and base.id == "agents":
    72	                hits.append(node)
    73	                break
    74	    return hits
    75	
    76	
    77	def test_workbench_dir_exists_or_skip():
    78	    if not _WORKBENCH_DIR.is_dir():
    79	        pytest.skip(
    80	            f"{_WORKBENCH_DIR} does not exist yet — Phase 2.1 follow-up PRs "
    81	            "add workbench modules. Discipline check is a no-op until then."
    82	        )
    83	    assert _WORKBENCH_DIR.is_dir()
    84	
    85	
    86	def test_only_agent_facade_imports_from_agents():
    87	    """ADR-015 discipline rule #1: facade is the choke point for agents.*"""
    88	    violations: list[str] = []
    89	    for path in _workbench_py_files():
    90	        if path.name == _FACADE_FILENAME:
    91	            continue
    92	        try:
    93	            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    94	        except SyntaxError as exc:
    95	            pytest.fail(f"could not parse {path}: {exc}")
    96	        hits = _imports_from(tree, _is_agents_module)
    97	        if hits:
    98	            rel = path.relative_to(_REPO_ROOT)
    99	            for node in hits:
   100	                module = getattr(node, "module", None) or "<bare import>"
   101	                violations.append(f"{rel}:{node.lineno}: imports from `{module}`")
   102	    assert not violations, (
   103	        "ADR-015 violation — only backend/app/workbench/agent_facade.py "
   104	        "may import from `agents.*`:\n  " + "\n  ".join(violations)
   105	    )
   106	
   107	
   108	def test_agent_facade_does_not_mutate_agent_state():
   109	    """ADR-015 discipline rule #2: read-only contract on agent modules."""
   110	    facade = _WORKBENCH_DIR / _FACADE_FILENAME
   111	    if not facade.is_file():
   112	        pytest.skip(f"{facade} not present yet — Phase 2.1 follow-up PR introduces it")
   113	    tree = ast.parse(facade.read_text(encoding="utf-8"), filename=str(facade))
   114	    hits = _assigns_to_agents_attribute(tree)
   115	    rendered = [
   116	        f"{facade.relative_to(_REPO_ROOT)}:{node.lineno}: assigns to agents.* attribute"
   117	        for node in hits
   118	    ]
   119	    assert not hits, (
   120	        "ADR-015 violation — agent_facade.py must not mutate agent module-level "
   121	        "state (read-only contract; effects flow through ADR-014's event bus):\n  "
   122	        + "\n  ".join(rendered)
   123	    )
   124	
   125	
   126	def test_no_workbench_file_imports_sim_state():
   127	    """ADR-015 discipline rule #3: HF1.4 — schemas.sim_state stays internal."""
   128	    violations: list[str] = []
   129	    for path in _workbench_py_files():
   130	        try:
   131	            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
   132	        except SyntaxError as exc:
   133	            pytest.fail(f"could not parse {path}: {exc}")
   134	        hits = _imports_from(tree, _is_sim_state_module)
   135	        if hits:
   136	            rel = path.relative_to(_REPO_ROOT)
   137	            for node in hits:
   138	                violations.append(f"{rel}:{node.lineno}: imports from `schemas.sim_state`")
   139	    assert not violations, (
   140	        "ADR-015 violation — workbench code must not import schemas.sim_state "
   141	        "(HF1.4); use schemas.sim_plan instead:\n  " + "\n  ".join(violations)
   142	    )
   143	
   144	
   145	# ---------------------------------------------------------------------------
   146	# Synthetic-fixture coverage — verify the AST predicates catch what they must.
   147	# These tests parse strings (not on-disk files) so they pass regardless of the
   148	# real workbench/ contents and pin the discipline-check semantics.
   149	# ---------------------------------------------------------------------------
   150	
   151	
   152	def _parse(src: str) -> ast.AST:
   153	    return ast.parse(src, filename="<synthetic>")
   154	
   155	
   156	class TestPredicates:
   157	    def test_from_agents_router_is_caught(self):
   158	        tree = _parse("from agents.router import route_simplan\n")
   159	        hits = _imports_from(tree, _is_agents_module)
   160	        assert len(hits) == 1
   161	
   162	    def test_bare_import_agents_is_caught(self):
   163	        tree = _parse("import agents.solver as solver\n")
   164	        hits = _imports_from(tree, _is_agents_module)
   165	        assert len(hits) == 1
   166	
   167	    def test_unrelated_import_is_ignored(self):
   168	        tree = _parse("from backend.app.api import runs\nimport json\n")
   169	        assert _imports_from(tree, _is_agents_module) == []
   170	
   171	    def test_relative_import_is_ignored(self):
   172	        # `from .agent_facade import X` — module is "agent_facade", NOT "agents.*"
   173	        tree = _parse("from .agent_facade import draft_simplan\n")
   174	        assert _imports_from(tree, _is_agents_module) == []
   175	
   176	    def test_lookalike_module_is_ignored(self):
   177	        # "agentsuite" must not match "agents" — startswith check is "agents."
   178	        tree = _parse("from agentsuite import helpers\n")
   179	        assert _imports_from(tree, _is_agents_module) == []
   180	
   181	    def test_assignment_to_agents_attribute_is_caught(self):
   182	        tree = _parse("import agents\nagents.router.GLOBAL_FLAG = True\n")
   183	        assert len(_assigns_to_agents_attribute(tree)) == 1
   184	
   185	    def test_deep_attribute_assignment_is_caught(self):
   186	        tree = _parse("import agents\nagents.solver.driver.cache = {}\n")
   187	        assert len(_assigns_to_agents_attribute(tree)) == 1
   188	
   189	    def test_assignment_to_local_variable_is_ignored(self):
   190	        tree = _parse("agents = []\nagents_seen = True\n")
   191	        assert _assigns_to_agents_attribute(tree) == []
   192	
   193	    def test_assignment_to_unrelated_module_is_ignored(self):
   194	        tree = _parse("import json\njson.something = 1\n")
   195	        assert _assigns_to_agents_attribute(tree) == []
   196	
   197	    def test_sim_state_import_is_caught(self):
   198	        tree = _parse("from schemas.sim_state import SimState\n")
   199	        hits = _imports_from(tree, _is_sim_state_module)
   200	        assert len(hits) == 1
   201	
   202	    def test_sim_plan_import_is_allowed(self):
   203	        tree = _parse("from schemas.sim_plan import SimPlan\n")
   204	        assert _imports_from(tree, _is_sim_state_module) == []

exec
/bin/zsh -lc "git show pr-51:backend/app/workbench/__init__.py | nl -ba | sed -n '1,200p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
exec
/bin/zsh -lc "git show pr-51:docs/adr/ADR-015-workbench-agent-rpc-boundary.md | nl -ba | sed -n '1,280p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
     1	"""Workbench facade layer (ADR-015).
     2	
     3	This package is the only call site that may import from `agents.*` outside
     4	the agent layer itself. See `docs/adr/ADR-015-workbench-agent-rpc-boundary.md`.
     5	"""

 succeeded in 0ms:
     1	# ADR-015: Workbench → Agent RPC Boundary
     2	
     3	- **Status:** Draft (parallel to ADR-014, ahead of Phase 2.1)
     4	- **Decider:** Claude Code CLI (Opus 4.7, 1M context) — human-confirmed
     5	- **Date:** 2026-04-26
     6	- **Related Phase:** 2.1 — Engineer Entry & Run Submission
     7	- **Branch:** `feature/AI-FEA-ADR-015-workbench-agent-rpc`
     8	- **Companion ADRs (Draft, parallel):** ADR-014 (WS event bus contract), ADR-016 (`.frd → .vtu` + result viz), ADR-017 (RAG facade in-process + CLI/lib parity)
     9	
    10	---
    11	
    12	## Context
    13	
    14	Phase 2.1 brings the engineer's first interaction surface online: a browser dialog where they describe a problem in natural language, see the architect agent translate it into a `SimPlan`, confirm or correct that plan, and submit a run. The frontend then watches the resulting LangGraph execution through ADR-014's WebSocket event bus.
    15	
    16	This ADR closes the **call-direction** question that ADR-014 deliberately punts: *how does the workbench backend invoke the agent layer without modifying it?*
    17	
    18	The constraint is severe. Six agent files (`agents/router.py`, `agents/architect.py`, `agents/geometry.py`, `agents/mesh.py`, `agents/solver.py`, `agents/reviewer.py`, plus `agents/calculix_driver.py`) collectively encode the LangGraph state machine. Three of them (`router`, `geometry`, `solver`, `calculix_driver`) are HF1-protected. None can be modified by a Phase 2 PR without an HF1 zone-carve ADR — which we are deliberately avoiding for the workbench track.
    19	
    20	Additionally, ADR-006's autonomous-merge regime relies on the agent layer being a stable target. Adding "the workbench dialed in here" coupling on the agent side would force every workbench iteration to re-validate ADR-006 invariants. That coupling must point the other direction: the agent layer is the stable surface; the workbench is the consumer.
    21	
    22	---
    23	
    24	## Decision
    25	
    26	**Pattern:** in-process **facade** module(s) under `backend/app/workbench/`. The workbench facade IS the only call site that touches the agent layer; the React frontend never imports agents.
    27	
    28	**Direction:** workbench → agents only. Agents do not know the workbench exists. No agent function gains a `workbench` keyword argument, a callback, a global, or a class-level mixin.
    29	
    30	**Read-only contract:** facade calls into agents are *read-only* with respect to agent state. The agents continue to emit their effects (artifacts on disk, LangGraph state transitions, log lines); the workbench observes those effects through ADR-014's event bus, NOT through return values that the facade then mutates.
    31	
    32	**No HTTP-internal RPC:** we do **not** wrap agents in a separate FastAPI service the workbench calls over the network. The cost would be: serialization, an extra port, and an authentication boundary, all to talk to code in the same process. Phase 3 may revisit if multi-process becomes useful (e.g. running agents in a sandbox), but Phase 2 is single-process.
    33	
    34	**No LangGraph "as a service":** we do **not** put LangGraph behind a gRPC service either. The workbench backend constructs the same LangGraph compiled state machine that the existing CLI does, and invokes it directly.
    35	
    36	---
    37	
    38	## Facade module map
    39	
    40	| Module | New / existing | Purpose |
    41	|--------|----------------|---------|
    42	| `backend/app/workbench/__init__.py` | **new** | package marker |
    43	| `backend/app/workbench/agent_facade.py` | **new** | the only file that imports `agents.*` from workbench code |
    44	| `backend/app/workbench/run_orchestrator.py` | **new** | builds and invokes the LangGraph compiled graph; wires the ADR-014 callback |
    45	| `backend/app/workbench/task_spec_builder.py` | **new** | calls `agents.architect` to translate NL → SimPlan; returns the SimPlan + a "confirmation token" the user signs off on |
    46	| `backend/app/workbench/rag_facade.py` | covered by ADR-017 | imports `backend.app.rag.*` for `advise()` / `combine()`; sibling to `agent_facade` |
    47	| `backend/app/runtime/event_bus.py` | covered by ADR-014 | `asyncio.Queue` + ring buffer |
    48	| `backend/app/runtime/langgraph_callbacks.py` | covered by ADR-014 | translates LangGraph signals → WS events |
    49	
    50	The split between `workbench/` (semantic operations) and `runtime/` (event-bus plumbing) is deliberate: ADR-014 owns the wire format; ADR-015 owns the in-process call sites.
    51	
    52	**`agent_facade.py` is the choke point.** Every import of `agents.*` from outside the agent layer goes through this file. A pre-merge static check (defined below) enforces the rule.
    53	
    54	---
    55	
    56	## Authentication & authorization for `POST /runs`
    57	
    58	The Phase 2.1 first-run scope is **single-trusted-operator-per-server** (per ADR-014). That means:
    59	
    60	- The browser is assumed to be on the same network as the backend (LAN / VPN) and has been pre-authenticated at the session boundary
    61	- `POST /runs` requires an `X-Workbench-Token` header that matches `os.environ["WORKBENCH_TOKEN"]` (a per-deployment secret)
    62	- The same token gates `GET /runs/{id}/nodes/{name}/io` (the digest-fetch endpoint from ADR-014)
    63	- WS handshake is upgraded only when the matching token is present in the `Sec-WebSocket-Protocol` header
    64	
    65	This is intentionally simple. A future ADR will introduce per-user identity once the workbench has more than one operator. **No OAuth / JWT in Phase 2.1.**
    66	
    67	---
    68	
    69	## Confirmation protocol (NL → SimPlan → user-signed run)
    70	
    71	The Phase 2.1 user flow:
    72	
    73	1. Browser sends `POST /runs/draft { "nl_request": "..." }` with the workbench token
    74	2. Backend calls `task_spec_builder.draft_from_nl(nl_request)` → returns `(sim_plan, draft_id, confirmation_token)`
    75	3. Browser displays the rendered SimPlan; user can edit or accept
    76	4. Browser sends `POST /runs/submit { "draft_id": ..., "confirmation_token": ..., "edits": {...} }` with the workbench token
    77	5. Backend rebuilds the SimPlan with edits applied, validates `confirmation_token` ties draft_id ↔ rebuilt SimPlan via HMAC, and only then invokes `run_orchestrator.invoke(sim_plan)`
    78	
    79	The `confirmation_token` is HMAC-SHA256 of the canonical-JSON-serialized SimPlan, keyed by the workbench token. It guarantees:
    80	
    81	- the SimPlan the user confirmed in step 3 is identical to the SimPlan that runs in step 5 (no silent drift)
    82	- a draft cannot be submitted by a third party who didn't see the rendered SimPlan
    83	- replay of the same `confirmation_token` against a different `draft_id` fails
    84	
    85	**No LLM regeneration between draft and submit.** Architect agent runs ONCE per request — at draft time. If user edits, the edits are applied as a structured diff to the draft SimPlan; the agent is not re-invoked.
    86	
    87	---
    88	
    89	## Considered alternatives
    90	
    91	### Direct frontend → agent imports
    92	Pros: zero glue layer.
    93	Cons: every JS bundle change forces a Python rebuild; cross-language type drift; the architect agent's prompt-engineering details would leak to the browser. **Rejected.**
    94	
    95	### HTTP-internal RPC (`POST /internal/agent/architect/draft`)
    96	Pros: language-agnostic; future multi-process viability.
    97	Cons: serialization round-trip per call; auth boundary inside the same process; no Phase 2 use case justifies the cost. **Rejected.**
    98	
    99	### LangGraph behind gRPC streaming
   100	Pros: typed, future-multi-host.
   101	Cons: complexity dwarfs the win; ADR-014 already streams events via WS. **Rejected.**
   102	
   103	### Subprocess invocation (fork/exec the existing CLI)
   104	Pros: maximum process isolation.
   105	Cons: cold-start cost (BGE-M3, LangGraph compile) per call; stdout parsing instead of typed return; cancellation requires SIGTERM dance. **Rejected.**
   106	
   107	---
   108	
   109	## Static check — facade discipline
   110	
   111	A new test, `tests/test_workbench_facade_discipline.py`, walks every `.py` file under `backend/app/workbench/` (when those files land in Phase 2.1) and asserts:
   112	
   113	1. **Only `agent_facade.py` imports from `agents.*`.** Any other workbench file importing `agents.*` is a violation.
   114	2. **`agent_facade.py` does not modify agent module-level state.** It calls functions and reads return values; it never assigns to `agents.X.Y`.
   115	3. **No workbench file imports from `schemas.sim_state`** (HF1.4) directly. They use `schemas.sim_plan` (which is also HF1-adjacent but not in the hard floor — see ADR-011 §HF1).
   116	
   117	The check is pure-AST (no import-time execution); fast (<100ms on the whole repo); and bound to ADR-015 by docstring reference.
   118	
   119	---
   120	
   121	## Implementation plan
   122	
   123	This ADR alone produces no executable code beyond the discipline test stub. The workbench code lands in subsequent PRs (Phase 2.1).
   124	
   125	| File | Status | Owner | Notes |
   126	|------|--------|-------|-------|
   127	| `docs/adr/ADR-015-workbench-agent-rpc-boundary.md` | this PR | Claude Code | M1 trigger |
   128	| `tests/test_workbench_facade_discipline.py` | this PR | Claude Code | static check, runs even before workbench/ exists (skips if dir missing) |
   129	| `backend/app/workbench/__init__.py` | this PR | Claude Code | package marker, single-line docstring referencing ADR-015 |
   130	| `backend/app/workbench/agent_facade.py` | Phase 2.1 follow-up | Claude Code | the only `agents.*` import site |
   131	| `backend/app/workbench/task_spec_builder.py` | Phase 2.1 follow-up | Claude Code | NL → SimPlan + confirmation_token |
   132	| `backend/app/workbench/run_orchestrator.py` | Phase 2.1 follow-up | Claude Code | LangGraph invocation + ADR-014 wiring |
   133	| `backend/app/api/runs.py` | Phase 2.1 follow-up | Claude Code | `POST /runs/draft`, `POST /runs/submit`, `GET /runs/{id}/nodes/{name}/io` |
   134	
   135	---
   136	
   137	## Codex review expectation
   138	
   139	This PR triggers M1 (governance text in `docs/adr/`) and M2 (executable assertion in `test_workbench_facade_discipline.py`). It does **not** touch HF1 zones (only adds new files outside HF1.x). It is **not** an enforcement-coupling PR (the workbench observes effects through ADR-014's bus, not through agent return values that mutate enforcement state).
   140	
   141	Self-pass-rate: **30%** — match the current BLOCKING ceiling. The discipline-check test is the contract every Phase 2.1 PR will be measured against; conservative review here saves N future R2 cycles on workbench code PRs.
   142	
   143	---
   144	
   145	## Cross-references
   146	
   147	- ADR-011 §T2 — M1+M2 trigger compliance basis
   148	- ADR-011 §HF1 — explicit non-touch of HF1.1–HF1.9; the discipline test is the durable enforcement
   149	- ADR-012 R2 (PR #24) — the calibration cap whose 30% BLOCKING ceiling this PR honors
   150	- ADR-014 (Draft, parallel) — WS event bus; this ADR's `run_orchestrator` consumes its event types
   151	- ADR-006 — autonomous-merge regime; this ADR strengthens the "agents are a stable target" pre-condition
   152	- Architecture review by Opus 4.7 (Notion, 2026-04-26) — Q1 (in-process facade), Q5 (Phase 2.1 scope), Q7-R2 (privacy boundary), Q7-R7 (HF1 boundary)
   153	
   154	---
   155	
   156	## Status notes
   157	
   158	**Draft → Final criteria:**
   159	
   160	1. Codex R1 returns APPROVE or APPROVE_WITH_NITS
   161	2. The discipline test passes on `main` and on every workbench-track PR
   162	3. Phase 2.1 follow-up PRs implement `agent_facade` / `task_spec_builder` / `run_orchestrator` without ever importing `agents.*` from outside the facade
   163	
   164	Until all three are met, this ADR remains `Draft`.

exec
/bin/zsh -lc "git show pr-52:schemas/viz_manifest.py | nl -ba | sed -n '1,260p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
     1	"""Result-viewer manifest schema (ADR-016).
     2	
     3	The `manifest.json` written under `runs/{run_id}/viz/` indexes the `.vtu`
     4	artifacts produced by the `.frd → .vtu` writer. The viewer SPA fetches
     5	`manifest.json` first to learn which fields exist, default increment,
     6	color-map ranges, and bbox; then fetches specific `.vtu` URIs on demand.
     7	
     8	See `docs/adr/ADR-016-frd-vtu-result-viz.md`.
     9	"""
    10	
    11	from __future__ import annotations
    12	
    13	from typing import (  # noqa: UP035 — Union kept for runtime PEP-604 portability
    14	    Annotated,
    15	    Literal,
    16	    Union,
    17	)
    18	
    19	from pydantic import BaseModel, ConfigDict, Field
    20	
    21	VIZ_MANIFEST_SCHEMA_VERSION: Literal["v1"] = "v1"
    22	
    23	IncrementType = Literal["static", "vibration", "buckling"]
    24	
    25	# Cell types we currently emit (Phase 2.2 initial coverage).
    26	SupportedCellType = Literal[
    27	    "C3D4",  # tet4
    28	    "C3D10",  # tet10
    29	    "C3D8",  # hex8
    30	    "C3D20",  # hex20
    31	    "S3",  # tri3 shell
    32	    "S4",  # quad4 shell
    33	]
    34	
    35	
    36	class _Frozen(BaseModel):
    37	    model_config = ConfigDict(frozen=True, extra="forbid")
    38	
    39	
    40	class BBox(_Frozen):
    41	    """Axis-aligned bounding box in mesh-coordinate units."""
    42	
    43	    min: tuple[float, float, float]
    44	    max: tuple[float, float, float]
    45	
    46	
    47	class Units(_Frozen):
    48	    """Physical units carried over from the originating SimPlan.
    49	
    50	    Populated by `run_orchestrator` (ADR-015), NOT inferred from `.frd`.
    51	    """
    52	
    53	    length: Literal["m", "mm", "in"]
    54	    stress: Literal["Pa", "MPa", "psi"] | None = None
    55	
    56	
    57	class MeshSection(_Frozen):
    58	    uri: str = Field(..., description="filename relative to manifest.json")
    59	    n_nodes: int = Field(..., ge=1)
    60	    n_elements: int = Field(..., ge=1)
    61	    element_types: tuple[SupportedCellType, ...]
    62	    bbox: BBox
    63	    units: Units
    64	
    65	
    66	class DisplacementField(_Frozen):
    67	    kind: Literal["displacement"] = "displacement"
    68	    uri: str
    69	    units: Literal["m", "mm", "in"]
    70	    max_magnitude: float = Field(..., ge=0.0)
    71	
    72	
    73	class ScalarStressField(_Frozen):
    74	    kind: Literal["von_mises", "max_principal", "min_principal", "mid_principal"]
    75	    uri: str
    76	    units: Literal["Pa", "MPa", "psi"]
    77	    min: float
    78	    max: float
    79	
    80	
    81	FieldEntry = Annotated[
    82	    Union[DisplacementField, ScalarStressField],  # noqa: UP007 — runtime PEP-604 portability (3.9)
    83	    Field(discriminator="kind"),
    84	]
    85	
    86	
    87	class IncrementEntry(_Frozen):
    88	    index: int = Field(..., ge=0)
    89	    step: int = Field(..., ge=1)
    90	    type: IncrementType
    91	    value: float
    92	    fields: dict[str, FieldEntry]
    93	
    94	
    95	class WriterInfo(_Frozen):
    96	    tool: Literal["backend.app.viz.frd_to_vtu"] = "backend.app.viz.frd_to_vtu"
    97	    version: str
    98	    frd_parser_version: str
    99	    wrote_at: str = Field(..., description="ISO 8601 UTC")
   100	
   101	
   102	class VizManifest(_Frozen):
   103	    """Top-level manifest written to `runs/{run_id}/viz/manifest.json`."""
   104	
   105	    schema_version: Literal["v1"] = VIZ_MANIFEST_SCHEMA_VERSION
   106	    run_id: str = Field(..., min_length=1)
   107	    mesh: MeshSection
   108	    increments: tuple[IncrementEntry, ...] = Field(..., min_length=1)
   109	    skipped_cells: int = Field(0, ge=0)
   110	    writer: WriterInfo
   111	
   112	
   113	__all__ = [
   114	    "VIZ_MANIFEST_SCHEMA_VERSION",
   115	    "IncrementType",
   116	    "SupportedCellType",
   117	    "BBox",
   118	    "Units",
   119	    "MeshSection",
   120	    "DisplacementField",
   121	    "ScalarStressField",
   122	    "FieldEntry",
   123	    "IncrementEntry",
   124	    "WriterInfo",
   125	    "VizManifest",
   126	]

exec
/bin/zsh -lc "git show pr-52:docs/adr/ADR-016-frd-vtu-result-viz.md | nl -ba | sed -n '1,320p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
exec
/bin/zsh -lc "git show pr-52:tests/test_viz_manifest_schema.py | nl -ba | sed -n '1,360p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
     1	# ADR-016: `.frd` → `.vtu` Conversion + Result Visualization
     2	
     3	- **Status:** Draft (parallel to ADR-014, ADR-015, ADR-017)
     4	- **Decider:** Claude Code CLI (Opus 4.7, 1M context) — human-confirmed
     5	- **Date:** 2026-04-26
     6	- **Related Phase:** 2.1 — Engineer Entry & Run Submission (viz consumed in 2.2)
     7	- **Branch:** `feature/AI-FEA-ADR-016-frd-vtu-result-viz`
     8	- **Companion ADRs (Draft, parallel):** ADR-014 (WS event bus), ADR-015 (workbench → agent RPC), ADR-017 (RAG facade)
     9	
    10	---
    11	
    12	## Context
    13	
    14	The workbench's last surface to design is **the result-viewer**. The engineer who submitted a SimPlan in Phase 2.1, watched it stream through the agent graph via ADR-014's WS bus, and saw a green `run.finished` now needs to see *what the simulation actually produced* — deformation, stress, mode shapes — without leaving the browser.
    15	
    16	CalculiX writes results to a `.frd` file (mixed ASCII/binary, CalculiX-specific). Three options for getting that on screen:
    17	
    18	1. **PNG snapshots from the backend.** Cheap. Static. Loses interactivity (can't rotate, can't probe, can't switch between fields).
    19	2. **ParaView Web / Trame.** Full ParaView in the browser. Heavy (Python service + WebGL bridge). Already evaluated in `cfd-ai-workbench` and rejected for similar reasons there (see Notion: 2026-04-11 v1.6.0 migration).
    20	3. **Convert `.frd` → `.vtu` (VTK XML UnstructuredGrid) and render with vtk.js in the browser.** vtk.js takes the `.vtu` blob directly; rendering, picking, color-mapping all run client-side. Backend becomes a static-file server for the `.vtu` artifact.
    21	
    22	This ADR commits to **option 3** and pins the contract.
    23	
    24	The corresponding constraint is that we already have a mature `backend/app/parsers/frd_parser.py` (CalculiX `.frd` → typed Python dataclasses, multi-increment aware). We do NOT have a `.vtu` writer. ADR-016 specifies the writer's contract; the implementation lands as a Phase 2.2 PR.
    25	
    26	---
    27	
    28	## Decision
    29	
    30	**Pipeline:** `.frd` (CalculiX) → `FRDParseResult` (existing parser) → `.vtu` (new writer, Phase 2.2) → `vtk.js` in browser (new frontend, Phase 2.2).
    31	
    32	**Storage path:** every run that produces results writes to `runs/{run_id}/viz/`:
    33	- `mesh.vtu` — geometry + topology (one per run, written once)
    34	- `field_{increment_index}_{field_name}.vtu` — per-increment, per-field result (deformation, von Mises, principal stresses, mode shape)
    35	- `manifest.json` — index of which fields exist, increment metadata (step, type, value), units, and BBox for camera framing
    36	
    37	**Format:** ASCII VTK XML (not binary VTU). Reasons:
    38	1. vtk.js's `vtkXMLUnstructuredGridReader` handles ASCII directly; binary requires base64 + zlib, doubles backend complexity.
    39	2. Compressed-on-the-wire by HTTP gzip is ~2× bigger than binary VTU but the browser doesn't care.
    40	3. Diffability: ASCII `.vtu` files diff cleanly in golden-sample regression tests; binary doesn't.
    41	4. The size ceiling that breaks ASCII (>50 MB per increment) corresponds to meshes >500k cells — not Phase 2.x territory. Phase 3 may revisit.
    42	
    43	**No streaming, no chunking, no progressive rendering.** vtk.js loads the full `.vtu` and renders. The backend writes the artifact when CalculiX finishes; the frontend fetches when the user opens the viewer. Simple and matches the synchronous Phase 2.1 flow (results are ready before the viewer opens).
    44	
    45	**No surface extraction in Phase 2.x.** vtk.js renders the volumetric mesh directly. Surface-only rendering (faster for >100k cells) is a Phase 3 optimization driven by measured performance, not assumed.
    46	
    47	**No animations of mode shapes in Phase 2.x.** Mode shapes are scalar magnitude visualizations on a static mesh; the user can scrub through increments via UI, but we do not write per-frame interpolated meshes. Phase 3 add if requested.
    48	
    49	---
    50	
    51	## Field selection
    52	
    53	The `.vtu` files emit a deliberate subset of `FRDParseResult`:
    54	
    55	| Source | `.vtu` representation | Phase | Notes |
    56	|--------|----------------------|-------|-------|
    57	| `nodes[i].coords` | `<Points>` | 2.2 | always present |
    58	| `elements[i]` (C3D4, C3D8, C3D10, C3D20, S3, S4, B31, …) | `<Cells>` | 2.2 | initial coverage: tet4/tet10/hex8/hex20/tri3/quad4 (covers all golden samples) |
    59	| `displacements[i]` | `<PointData Name="displacement" type="Float32" NumberOfComponents="3">` | 2.2 | per-increment field; magnitude derived in vtk.js |
    60	| `stresses[i].von_mises` | `<PointData Name="von_mises" type="Float32">` | 2.2 | per-increment field |
    61	| `stresses[i].max_principal` | `<PointData Name="max_principal" type="Float32">` | 2.2 | per-increment field |
    62	| `stresses[i].S11..S23` | (NOT emitted Phase 2.2) | 3 | tensor components rarely useful at the workbench tier; defer |
    63	| `strains` | (NOT emitted Phase 2.2) | 3 | strain field not in FailurePattern signal set; defer |
    64	
    65	The "(NOT emitted)" rows are deliberate scope bounds. A Phase 3 ADR can add them when a concrete consumer (reviewer agent, advisor) needs them.
    66	
    67	---
    68	
    69	## `manifest.json` schema
    70	
    71	```json
    72	{
    73	  "schema_version": "v1",
    74	  "run_id": "RUN-2026-04-27-abc123",
    75	  "mesh": {
    76	    "uri": "mesh.vtu",
    77	    "n_nodes": 1234,
    78	    "n_elements": 567,
    79	    "element_types": ["C3D10"],
    80	    "bbox": {"min": [0.0, 0.0, 0.0], "max": [10.0, 1.0, 1.0]},
    81	    "units": {"length": "m"}
    82	  },
    83	  "increments": [
    84	    {
    85	      "index": 0,
    86	      "step": 1,
    87	      "type": "static",
    88	      "value": 1.0,
    89	      "fields": {
    90	        "displacement": {"uri": "field_0_displacement.vtu", "units": "m", "max_magnitude": 0.0023},
    91	        "von_mises":   {"uri": "field_0_von_mises.vtu",    "units": "Pa", "max": 1.4e8, "min": 0.0},
    92	        "max_principal": {"uri": "field_0_max_principal.vtu", "units": "Pa", "max": 9.8e7, "min": -1.1e8}
    93	      }
    94	    }
    95	  ],
    96	  "writer": {
    97	    "tool": "backend.app.viz.frd_to_vtu",
    98	    "version": "0.1.0",
    99	    "frd_parser_version": "(from FRDParseResult)",
   100	    "wrote_at": "2026-04-27T12:34:56Z"
   101	  }
   102	}
   103	```
   104	
   105	Pydantic v2 frozen + `extra="forbid"` schema lives in `schemas/viz_manifest.py`. The viewer fetches `manifest.json` first to populate the UI (which fields exist, which increment to default to, what color-map range to use); then fetches the specific `.vtu` URI on demand.
   106	
   107	The `units` field is **populated from the originating SimPlan**, not inferred from `.frd` (the FRD format does not record units). This requires `run_orchestrator` (ADR-015) to pass the SimPlan's units into the writer.
   108	
   109	---
   110	
   111	## Authorization
   112	
   113	`GET /runs/{run_id}/viz/manifest.json` and `GET /runs/{run_id}/viz/{filename}` are gated by the same `X-Workbench-Token` header from ADR-015. The viewer SPA includes the token in its requests (read from a secure HTTP-only cookie set during the operator login flow).
   114	
   115	**No CDN / external storage.** Phase 2.x serves `.vtu` from the workbench backend's local filesystem. Phase 3 may consider object storage if multi-host becomes useful.
   116	
   117	---
   118	
   119	## Static check — viz contract
   120	
   121	A new test, `tests/test_viz_manifest_schema.py`, asserts the `manifest.json` shape. A second test, `tests/test_frd_to_vtu_writer.py` (Phase 2.2 follow-up), asserts:
   122	
   123	1. **Round-trip on golden samples:** `.frd` from `golden_samples/GS-001..003/` parses → writes `.vtu` → vtk Python reader re-parses without error → node count, cell count, displacement magnitude match the original `FRDParseResult`.
   124	2. **No Inf / NaN values.** A `.vtu` with `Inf` in `<PointData>` would crash vtk.js silently. Writer must filter or fail loudly.
   125	3. **Cell-type coverage.** Every CalculiX element type in the golden samples has a documented VTK cell-type mapping. New CalculiX types that the FRD parser handles but the writer doesn't are skipped + logged + counted in `manifest.skipped_cells`.
   126	4. **Manifest validates against `schemas.viz_manifest`** (Pydantic v2 frozen, `extra="forbid"`).
   127	
   128	Phase 2.2 follow-up PRs implement the writer and tests. This ADR PR adds only the schema stub + the manifest-shape test.
   129	
   130	---
   131	
   132	## Frontend rendering choice
   133	
   134	**vtk.js, no ParaView Web.** Reasons:
   135	
   136	1. vtk.js is npm-installable; no Python service required for the viewer.
   137	2. The bundle is large (~5 MB minified) but cached after first load and gzips well.
   138	3. Picking, threshold filtering, and color-map switching all run client-side — no backend round-trip per UI interaction.
   139	4. ParaView Web's Trame stack would force a separate Python service alongside the FastAPI backend, doubling the deploy surface for one feature.
   140	
   141	The frontend code lands in `frontend/src/viz/` (Phase 2.2). Outside this ADR's scope.
   142	
   143	---
   144	
   145	## Considered alternatives
   146	
   147	### PNG snapshots from a backend ParaView/PyVista session
   148	Pros: tiny artifacts; trivial to embed in markdown reports.
   149	Cons: no interactivity. Cannot rotate/probe. Forecloses the use case ADR-014 was designed for ("engineer sees stepwise visibility"). **Rejected.**
   150	
   151	### ParaView Web (Trame)
   152	Pros: full ParaView feature set in the browser.
   153	Cons: separate Python service; WebGL bridge complexity; deploy doubled. Phase 3 may revisit if Phase 2.2 vtk.js performance is insufficient on real meshes. **Rejected for now.**
   154	
   155	### Custom Three.js renderer reading raw `.frd`
   156	Pros: minimal dep set.
   157	Cons: re-implements VTK's 20-year unstructured-grid pipeline. **Rejected.**
   158	
   159	### Binary VTU (base64 + zlib `<DataArray>`)
   160	Pros: ~2× smaller files; faster gzip.
   161	Cons: writer complexity; harder to diff in tests; vtk.js handles ASCII just as well. Phase 3 may revisit if file-size ceilings bite. **Rejected for now.**
   162	
   163	---
   164	
   165	## Implementation plan
   166	
   167	| File | Status | Owner | Notes |
   168	|------|--------|-------|-------|
   169	| `docs/adr/ADR-016-frd-vtu-result-viz.md` | this PR | Claude Code | M1 trigger |
   170	| `schemas/viz_manifest.py` | this PR | Claude Code | Pydantic v2 frozen schema (M2) |
   171	| `tests/test_viz_manifest_schema.py` | this PR | Claude Code | shape assertions on `viz_manifest` (M2) |
   172	| `backend/app/viz/__init__.py` | this PR | Claude Code | package marker referencing ADR-016 |
   173	| `backend/app/viz/frd_to_vtu.py` | Phase 2.2 follow-up | Claude Code | the writer |
   174	| `tests/test_frd_to_vtu_writer.py` | Phase 2.2 follow-up | Claude Code | golden-sample round-trip |
   175	| `backend/app/api/viz.py` | Phase 2.2 follow-up | Claude Code | `GET /runs/{id}/viz/{filename}` |
   176	| `frontend/src/viz/*` | Phase 2.2 follow-up | Claude Code | vtk.js viewer SPA |
   177	
   178	---
   179	
   180	## Codex review expectation
   181	
   182	This PR triggers M1 (governance text) and M2 (executable schema + assertions). It does **not** touch HF1 zones. It is **not** an enforcement-coupling PR (the writer reads `FRDParseResult` and writes artifacts; no governance-state mutation).
   183	
   184	Self-pass-rate: **30%** — match the BLOCKING ceiling. The schema is the contract every viewer-track PR will be measured against.
   185	
   186	---
   187	
   188	## Cross-references
   189	
   190	- ADR-011 §T2 — M1+M2 trigger compliance basis
   191	- ADR-011 §HF1 — explicit non-touch (only adds new files outside HF1.x)
   192	- ADR-012 R2 (PR #24) — 30% BLOCKING ceiling honored
   193	- ADR-014 (Draft, parallel) — the WS bus emits `artifact.ready` events when `mesh.vtu` / `field_*.vtu` finish writing; the viewer subscribes
   194	- ADR-015 (Draft, parallel) — `run_orchestrator` invokes the writer after CalculiX finishes; passes SimPlan units in
   195	- ADR-017 (Draft, parallel) — independent surface (RAG facade), no overlap
   196	
   197	---
   198	
   199	## Status notes
   200	
   201	**Draft → Final criteria:**
   202	
   203	1. Codex R1 returns APPROVE or APPROVE_WITH_NITS
   204	2. The manifest-shape test passes on `main`
   205	3. Phase 2.2 follow-up PR implements `frd_to_vtu` writer + golden-sample round-trip test
   206	
   207	Until all three are met, this ADR remains `Draft`.

 succeeded in 0ms:
     1	"""Schema-shape assertions for `schemas.viz_manifest` (ADR-016).
     2	
     3	This guards the contract every Phase 2.2 viewer-track PR will be measured
     4	against. The actual `.frd → .vtu` writer (`backend.app.viz.frd_to_vtu`)
     5	lands in a follow-up; round-trip tests live in `test_frd_to_vtu_writer.py`.
     6	"""
     7	
     8	from __future__ import annotations
     9	
    10	import json
    11	
    12	import pytest
    13	from pydantic import ValidationError
    14	
    15	from schemas.viz_manifest import (
    16	    VIZ_MANIFEST_SCHEMA_VERSION,
    17	    BBox,
    18	    DisplacementField,
    19	    IncrementEntry,
    20	    MeshSection,
    21	    ScalarStressField,
    22	    Units,
    23	    VizManifest,
    24	    WriterInfo,
    25	)
    26	
    27	# ---------------------------------------------------------------------------
    28	# Fixtures
    29	# ---------------------------------------------------------------------------
    30	
    31	
    32	def _bbox() -> BBox:
    33	    return BBox(min=(0.0, 0.0, 0.0), max=(1.0, 1.0, 1.0))
    34	
    35	
    36	def _units() -> Units:
    37	    return Units(length="m", stress="Pa")
    38	
    39	
    40	def _mesh() -> MeshSection:
    41	    return MeshSection(
    42	        uri="mesh.vtu",
    43	        n_nodes=10,
    44	        n_elements=4,
    45	        element_types=("C3D10",),
    46	        bbox=_bbox(),
    47	        units=_units(),
    48	    )
    49	
    50	
    51	def _disp_field() -> DisplacementField:
    52	    return DisplacementField(
    53	        uri="field_0_displacement.vtu",
    54	        units="m",
    55	        max_magnitude=0.0023,
    56	    )
    57	
    58	
    59	def _vm_field() -> ScalarStressField:
    60	    return ScalarStressField(
    61	        kind="von_mises",
    62	        uri="field_0_von_mises.vtu",
    63	        units="Pa",
    64	        min=0.0,
    65	        max=1.4e8,
    66	    )
    67	
    68	
    69	def _increment() -> IncrementEntry:
    70	    return IncrementEntry(
    71	        index=0,
    72	        step=1,
    73	        type="static",
    74	        value=1.0,
    75	        fields={"displacement": _disp_field(), "von_mises": _vm_field()},
    76	    )
    77	
    78	
    79	def _writer() -> WriterInfo:
    80	    return WriterInfo(
    81	        version="0.1.0",
    82	        frd_parser_version="2.1.0",
    83	        wrote_at="2026-04-27T12:34:56Z",
    84	    )
    85	
    86	
    87	def _manifest() -> VizManifest:
    88	    return VizManifest(
    89	        run_id="RUN-2026-04-27-abc123",
    90	        mesh=_mesh(),
    91	        increments=(_increment(),),
    92	        writer=_writer(),
    93	    )
    94	
    95	
    96	# ---------------------------------------------------------------------------
    97	# Constants
    98	# ---------------------------------------------------------------------------
    99	
   100	
   101	def test_schema_version_constant_pinned():
   102	    assert VIZ_MANIFEST_SCHEMA_VERSION == "v1"
   103	
   104	
   105	def test_default_schema_version_matches_constant():
   106	    m = _manifest()
   107	    assert m.schema_version == VIZ_MANIFEST_SCHEMA_VERSION
   108	
   109	
   110	# ---------------------------------------------------------------------------
   111	# Frozen + extra=forbid invariants
   112	# ---------------------------------------------------------------------------
   113	
   114	
   115	def test_manifest_is_frozen():
   116	    m = _manifest()
   117	    with pytest.raises(ValidationError):
   118	        m.run_id = "RUN-other"  # type: ignore[misc]
   119	
   120	
   121	def test_manifest_rejects_unknown_top_level_keys():
   122	    payload = json.loads(_manifest().model_dump_json())
   123	    payload["mystery_field"] = "should_not_be_allowed"
   124	    with pytest.raises(ValidationError):
   125	        VizManifest.model_validate(payload)
   126	
   127	
   128	def test_increment_rejects_unknown_keys():
   129	    base = _increment().model_dump()
   130	    base["bonus"] = "nope"
   131	    with pytest.raises(ValidationError):
   132	        IncrementEntry.model_validate(base)
   133	
   134	
   135	def test_mesh_rejects_unknown_keys():
   136	    base = _mesh().model_dump()
   137	    base["bonus"] = "nope"
   138	    with pytest.raises(ValidationError):
   139	        MeshSection.model_validate(base)
   140	
   141	
   142	# ---------------------------------------------------------------------------
   143	# Required-field validation
   144	# ---------------------------------------------------------------------------
   145	
   146	
   147	def test_run_id_must_be_non_empty():
   148	    with pytest.raises(ValidationError):
   149	        VizManifest(
   150	            run_id="",
   151	            mesh=_mesh(),
   152	            increments=(_increment(),),
   153	            writer=_writer(),
   154	        )
   155	
   156	
   157	def test_increments_must_be_non_empty():
   158	    with pytest.raises(ValidationError):
   159	        VizManifest(
   160	            run_id="RUN-x",
   161	            mesh=_mesh(),
   162	            increments=(),
   163	            writer=_writer(),
   164	        )
   165	
   166	
   167	def test_mesh_n_nodes_must_be_positive():
   168	    with pytest.raises(ValidationError):
   169	        MeshSection(
   170	            uri="mesh.vtu",
   171	            n_nodes=0,
   172	            n_elements=1,
   173	            element_types=("C3D10",),
   174	            bbox=_bbox(),
   175	            units=_units(),
   176	        )
   177	
   178	
   179	def test_mesh_n_elements_must_be_positive():
   180	    with pytest.raises(ValidationError):
   181	        MeshSection(
   182	            uri="mesh.vtu",
   183	            n_nodes=10,
   184	            n_elements=0,
   185	            element_types=("C3D10",),
   186	            bbox=_bbox(),
   187	            units=_units(),
   188	        )
   189	
   190	
   191	def test_skipped_cells_cannot_be_negative():
   192	    with pytest.raises(ValidationError):
   193	        VizManifest(
   194	            run_id="RUN-x",
   195	            mesh=_mesh(),
   196	            increments=(_increment(),),
   197	            skipped_cells=-1,
   198	            writer=_writer(),
   199	        )
   200	
   201	
   202	def test_displacement_max_magnitude_cannot_be_negative():
   203	    with pytest.raises(ValidationError):
   204	        DisplacementField(uri="f.vtu", units="m", max_magnitude=-0.001)
   205	
   206	
   207	# ---------------------------------------------------------------------------
   208	# Cell-type discipline
   209	# ---------------------------------------------------------------------------
   210	
   211	
   212	def test_unsupported_cell_type_rejected():
   213	    """An element type the writer doesn't yet emit must NOT silently slip in."""
   214	    with pytest.raises(ValidationError):
   215	        MeshSection(
   216	            uri="mesh.vtu",
   217	            n_nodes=10,
   218	            n_elements=4,
   219	            element_types=("C3D27",),  # not in SupportedCellType literal
   220	            bbox=_bbox(),
   221	            units=_units(),
   222	        )
   223	
   224	
   225	def test_supported_cell_types_accepted():
   226	    for ct in ("C3D4", "C3D10", "C3D8", "C3D20", "S3", "S4"):
   227	        m = MeshSection(
   228	            uri="mesh.vtu",
   229	            n_nodes=10,
   230	            n_elements=4,
   231	            element_types=(ct,),  # type: ignore[arg-type]
   232	            bbox=_bbox(),
   233	            units=_units(),
   234	        )
   235	        assert ct in m.element_types
   236	
   237	
   238	# ---------------------------------------------------------------------------
   239	# Increment type discipline
   240	# ---------------------------------------------------------------------------
   241	
   242	
   243	def test_unknown_increment_type_rejected():
   244	    with pytest.raises(ValidationError):
   245	        IncrementEntry(
   246	            index=0,
   247	            step=1,
   248	            type="harmonic",  # type: ignore[arg-type]
   249	            value=1.0,
   250	            fields={"displacement": _disp_field()},
   251	        )
   252	
   253	
   254	def test_static_vibration_buckling_accepted():
   255	    for t in ("static", "vibration", "buckling"):
   256	        IncrementEntry(
   257	            index=0,
   258	            step=1,
   259	            type=t,  # type: ignore[arg-type]
   260	            value=1.0,
   261	            fields={"displacement": _disp_field()},
   262	        )
   263	
   264	
   265	# ---------------------------------------------------------------------------
   266	# Discriminated union: field kind
   267	# ---------------------------------------------------------------------------
   268	
   269	
   270	def test_field_kind_discriminator_displacement():
   271	    payload = {
   272	        "kind": "displacement",
   273	        "uri": "f.vtu",
   274	        "units": "m",
   275	        "max_magnitude": 0.001,
   276	    }
   277	    inc = IncrementEntry(
   278	        index=0,
   279	        step=1,
   280	        type="static",
   281	        value=1.0,
   282	        fields={"displacement": payload},  # type: ignore[arg-type]
   283	    )
   284	    assert isinstance(inc.fields["displacement"], DisplacementField)
   285	
   286	
   287	def test_field_kind_discriminator_von_mises():
   288	    payload = {
   289	        "kind": "von_mises",
   290	        "uri": "f.vtu",
   291	        "units": "Pa",
   292	        "min": 0.0,
   293	        "max": 1.0e8,
   294	    }
   295	    inc = IncrementEntry(
   296	        index=0,
   297	        step=1,
   298	        type="static",
   299	        value=1.0,
   300	        fields={"von_mises": payload},  # type: ignore[arg-type]
   301	    )
   302	    assert isinstance(inc.fields["von_mises"], ScalarStressField)
   303	
   304	
   305	def test_unknown_field_kind_rejected():
   306	    payload = {
   307	        "kind": "strain_xx",  # not in the union
   308	        "uri": "f.vtu",
   309	        "units": "Pa",
   310	        "min": 0.0,
   311	        "max": 1.0e8,
   312	    }
   313	    with pytest.raises(ValidationError):
   314	        IncrementEntry(
   315	            index=0,
   316	            step=1,
   317	            type="static",
   318	            value=1.0,
   319	            fields={"strain_xx": payload},  # type: ignore[arg-type]
   320	        )
   321	
   322	
   323	# ---------------------------------------------------------------------------
   324	# Units discipline
   325	# ---------------------------------------------------------------------------
   326	
   327	
   328	def test_unknown_length_unit_rejected():
   329	    with pytest.raises(ValidationError):
   330	        Units(length="cm")  # type: ignore[arg-type]
   331	
   332	
   333	def test_unknown_stress_unit_rejected():
   334	    with pytest.raises(ValidationError):
   335	        Units(length="m", stress="kPa")  # type: ignore[arg-type]
   336	
   337	
   338	def test_stress_unit_optional():
   339	    u = Units(length="m")
   340	    assert u.stress is None
   341	
   342	
   343	# ---------------------------------------------------------------------------
   344	# JSON round-trip
   345	# ---------------------------------------------------------------------------
   346	
   347	
   348	def test_manifest_json_round_trip():
   349	    original = _manifest()
   350	    blob = original.model_dump_json()
   351	    parsed = json.loads(blob)
   352	    rebuilt = VizManifest.model_validate(parsed)
   353	    assert rebuilt == original
   354	
   355	
   356	def test_manifest_json_dump_is_indexable_by_viewer():
   357	    """Viewer SPA uses these specific keys; pin the surface."""
   358	    blob = json.loads(_manifest().model_dump_json())
   359	    assert blob["schema_version"] == "v1"
   360	    assert blob["mesh"]["uri"] == "mesh.vtu"

exec
/bin/zsh -lc "git show pr-52:tests/test_viz_manifest_schema.py | nl -ba | sed -n '361,460p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
   361	    assert blob["mesh"]["bbox"]["min"] == [0.0, 0.0, 0.0]
   362	    assert blob["increments"][0]["fields"]["displacement"]["kind"] == "displacement"
   363	    assert blob["increments"][0]["fields"]["von_mises"]["kind"] == "von_mises"
   364	
   365	
   366	# ---------------------------------------------------------------------------
   367	# Writer info discipline
   368	# ---------------------------------------------------------------------------
   369	
   370	
   371	def test_writer_tool_pinned():
   372	    """Only this one writer may produce manifests."""
   373	    with pytest.raises(ValidationError):
   374	        WriterInfo(
   375	            tool="some.other.writer",  # type: ignore[arg-type]
   376	            version="0.1.0",
   377	            frd_parser_version="2.1.0",
   378	            wrote_at="2026-04-27T00:00:00Z",
   379	        )
   380	
   381	
   382	def test_writer_default_tool():
   383	    w = WriterInfo(version="0.1.0", frd_parser_version="2.1.0", wrote_at="2026-04-27T00:00:00Z")
   384	    assert w.tool == "backend.app.viz.frd_to_vtu"

exec
/bin/zsh -lc "git show pr-53:tests/test_rag_facade_parity.py | nl -ba | sed -n '1,360p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
     1	"""Discipline + parity checks for ADR-017.
     2	
     3	Asserts the contract from `docs/adr/ADR-017-rag-facade-cli-lib-parity.md`:
     4	
     5	1. Only `rag_facade.py` (and `agent_facade.py`, per ADR-015) under
     6	   `backend/app/workbench/` may import `backend.app.rag.*`.
     7	2. `rag_facade.py` does NOT import `backend.app.rag.*_cli` / `coverage_audit`
     8	   (the facade goes through the library, not the CLI shell).
     9	3. Each CLI module that exists imports its sibling library module (parity:
    10	   CLI is a thin shell over the library, never re-implements logic).
    11	4. No CLI module imports another CLI module's symbols (CLIs compose through
    12	   the library, never through each other's `main()`).
    13	
    14	Pure-AST static checks. Skips gracefully when target modules don't exist
    15	yet — the workbench facade lands in Phase 2.1 follow-up; the RAG track
    16	(PR #38-#47) lands the library + CLI modules.
    17	"""
    18	
    19	from __future__ import annotations
    20	
    21	import ast
    22	from pathlib import Path
    23	
    24	import pytest
    25	
    26	_REPO_ROOT = Path(__file__).resolve().parent.parent
    27	_WORKBENCH_DIR = _REPO_ROOT / "backend" / "app" / "workbench"
    28	_RAG_DIR = _REPO_ROOT / "backend" / "app" / "rag"
    29	_FACADE_NAMES = {"rag_facade.py", "agent_facade.py"}
    30	
    31	# CLI/library pairs as the RAG track defines them. Each tuple is
    32	# (cli_module_filename, library_module_filename). When a CLI exists, it
    33	# must import its library sibling.
    34	_CLI_LIB_PAIRS = [
    35	    ("cli.py", "ingest.py"),  # PR #38: ingest CLI wraps ingest library
    36	    ("query_cli.py", "kb.py"),  # PR #39: query CLI wraps KB
    37	    ("advise_cli.py", "reviewer_advisor.py"),  # PR #41 wraps PR #40
    38	    ("preflight_publish_cli.py", "preflight_publish.py"),  # PR #45 wraps PR #43
    39	]
    40	
    41	# CLI modules that must NEVER appear in rag_facade.py imports.
    42	_FORBIDDEN_FACADE_IMPORTS = {
    43	    "backend.app.rag.cli",
    44	    "backend.app.rag.query_cli",
    45	    "backend.app.rag.advise_cli",
    46	    "backend.app.rag.preflight_publish_cli",
    47	    "backend.app.rag.coverage_audit",  # CLI-shaped audit tool
    48	}
    49	
    50	
    51	# ---------------------------------------------------------------------------
    52	# Helpers
    53	# ---------------------------------------------------------------------------
    54	
    55	
    56	def _module_predicate_from_rag(module: str | None) -> bool:
    57	    if module is None:
    58	        return False
    59	    return module == "backend.app.rag" or module.startswith("backend.app.rag.")
    60	
    61	
    62	def _imports_modules(tree: ast.AST) -> set[str]:
    63	    """Collect every `from X import …` target and `import X` name."""
    64	    seen: set[str] = set()
    65	    for node in ast.walk(tree):
    66	        if isinstance(node, ast.ImportFrom) and node.module:
    67	            seen.add(node.module)
    68	        elif isinstance(node, ast.Import):
    69	            for alias in node.names:
    70	                seen.add(alias.name)
    71	    return seen
    72	
    73	
    74	def _parse_file(path: Path) -> ast.AST | None:
    75	    if not path.is_file():
    76	        return None
    77	    try:
    78	        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    79	    except SyntaxError as exc:  # pragma: no cover — surfaces real bugs
    80	        pytest.fail(f"could not parse {path}: {exc}")
    81	        return None
    82	
    83	
    84	def _workbench_py_files() -> list[Path]:
    85	    if not _WORKBENCH_DIR.is_dir():
    86	        return []
    87	    return sorted(p for p in _WORKBENCH_DIR.rglob("*.py") if p.is_file())
    88	
    89	
    90	# ---------------------------------------------------------------------------
    91	# Rule #1 — only facade modules import backend.app.rag.* from workbench
    92	# ---------------------------------------------------------------------------
    93	
    94	
    95	def test_only_facade_modules_import_rag_from_workbench():
    96	    """ADR-017 rule #1: rag_facade.py is the choke point for RAG library."""
    97	    if not _WORKBENCH_DIR.is_dir():
    98	        pytest.skip(f"{_WORKBENCH_DIR} does not exist yet — Phase 2.1 follow-up")
    99	    violations: list[str] = []
   100	    for path in _workbench_py_files():
   101	        if path.name in _FACADE_NAMES:
   102	            continue
   103	        tree = _parse_file(path)
   104	        if tree is None:
   105	            continue
   106	        for node in ast.walk(tree):
   107	            if isinstance(node, ast.ImportFrom) and _module_predicate_from_rag(node.module):
   108	                violations.append(
   109	                    f"{path.relative_to(_REPO_ROOT)}:{node.lineno}: imports `{node.module}`"
   110	                )
   111	            elif isinstance(node, ast.Import):
   112	                for alias in node.names:
   113	                    if _module_predicate_from_rag(alias.name):
   114	                        violations.append(
   115	                            f"{path.relative_to(_REPO_ROOT)}:{node.lineno}: imports `{alias.name}`"
   116	                        )
   117	    assert not violations, (
   118	        "ADR-017 violation — only rag_facade.py / agent_facade.py may import "
   119	        "backend.app.rag.* from the workbench package:\n  " + "\n  ".join(violations)
   120	    )
   121	
   122	
   123	# ---------------------------------------------------------------------------
   124	# Rule #2 — rag_facade.py does NOT import RAG CLI shells
   125	# ---------------------------------------------------------------------------
   126	
   127	
   128	def test_rag_facade_does_not_import_rag_cli_shells():
   129	    """ADR-017 rule #2: facade goes through library, not CLI."""
   130	    facade = _WORKBENCH_DIR / "rag_facade.py"
   131	    if not facade.is_file():
   132	        pytest.skip(f"{facade} does not exist yet — Phase 2.1 follow-up adds it")
   133	    tree = _parse_file(facade)
   134	    assert tree is not None
   135	    imported = _imports_modules(tree)
   136	    forbidden_hits = imported & _FORBIDDEN_FACADE_IMPORTS
   137	    assert not forbidden_hits, (
   138	        f"ADR-017 violation — rag_facade.py must not import RAG CLI shells; "
   139	        f"found: {sorted(forbidden_hits)}. Use the library API instead."
   140	    )
   141	
   142	
   143	# ---------------------------------------------------------------------------
   144	# Rule #3 — each CLI shell imports its library sibling
   145	# ---------------------------------------------------------------------------
   146	
   147	
   148	def test_each_cli_shell_imports_its_library_sibling():
   149	    """ADR-017 rule #3: CLI modules are thin shells over library modules."""
   150	    if not _RAG_DIR.is_dir():
   151	        pytest.skip(f"{_RAG_DIR} does not exist yet — RAG track (PR #38-#47)")
   152	    skipped = 0
   153	    parity_violations: list[str] = []
   154	    for cli_name, lib_name in _CLI_LIB_PAIRS:
   155	        cli_path = _RAG_DIR / cli_name
   156	        lib_path = _RAG_DIR / lib_name
   157	        if not cli_path.is_file() or not lib_path.is_file():
   158	            skipped += 1
   159	            continue
   160	        tree = _parse_file(cli_path)
   161	        if tree is None:
   162	            continue
   163	        imported = _imports_modules(tree)
   164	        # The CLI may import via `from backend.app.rag.<lib> import …` or
   165	        # `from .<lib> import …` (relative). Accept either.
   166	        lib_stem = lib_name[: -len(".py")]
   167	        absolute = f"backend.app.rag.{lib_stem}"
   168	        relative_targets = {lib_stem}  # `from .<lib_stem> import …`
   169	        ok = absolute in imported or any(t in imported for t in relative_targets)
   170	        # Also accept any module starting with `backend.app.rag.<lib_stem>`
   171	        if not ok:
   172	            ok = any(m == absolute or m.startswith(absolute + ".") for m in imported)
   173	        if not ok:
   174	            parity_violations.append(
   175	                f"{cli_path.relative_to(_REPO_ROOT)}: does not import `{absolute}` "
   176	                f"(or relative `.{lib_stem}`); add a thin-shell import or carve "
   177	                f"the logic out into the library."
   178	            )
   179	    if skipped == len(_CLI_LIB_PAIRS):
   180	        pytest.skip("no CLI/lib pair present yet — RAG track (PR #38-#47) not landed")
   181	    assert not parity_violations, (
   182	        "ADR-017 rule #3 violation — CLI shells must import their library "
   183	        "siblings:\n  " + "\n  ".join(parity_violations)
   184	    )
   185	
   186	
   187	# ---------------------------------------------------------------------------
   188	# Rule #4 — no CLI imports another CLI's symbols
   189	# ---------------------------------------------------------------------------
   190	
   191	
   192	def test_no_cli_imports_another_cli():
   193	    """ADR-017 rule #4: CLIs compose through the library, not each other."""
   194	    if not _RAG_DIR.is_dir():
   195	        pytest.skip(f"{_RAG_DIR} does not exist yet — RAG track (PR #38-#47)")
   196	    cli_filenames = {p[0] for p in _CLI_LIB_PAIRS}
   197	    cli_module_names = {f"backend.app.rag.{name[:-len('.py')]}" for name in cli_filenames}
   198	    cli_relative_names = {name[: -len(".py")] for name in cli_filenames}
   199	    violations: list[str] = []
   200	    for cli_name in cli_filenames:
   201	        cli_path = _RAG_DIR / cli_name
   202	        if not cli_path.is_file():
   203	            continue
   204	        tree = _parse_file(cli_path)
   205	        if tree is None:
   206	            continue
   207	        imported = _imports_modules(tree)
   208	        own_module = f"backend.app.rag.{cli_name[: -len('.py')]}"
   209	        own_relative = cli_name[: -len(".py")]
   210	        for mod in imported:
   211	            if mod in cli_module_names and mod != own_module:
   212	                violations.append(
   213	                    f"{cli_path.relative_to(_REPO_ROOT)}: imports another CLI `{mod}`"
   214	                )
   215	            elif mod in cli_relative_names and mod != own_relative:
   216	                violations.append(
   217	                    f"{cli_path.relative_to(_REPO_ROOT)}: imports another CLI `.{mod}`"
   218	                )
   219	    assert not violations, (
   220	        "ADR-017 rule #4 violation — CLIs must not import each other; route "
   221	        "shared logic through the library:\n  " + "\n  ".join(violations)
   222	    )
   223	
   224	
   225	# ---------------------------------------------------------------------------
   226	# Synthetic-fixture coverage — pin the AST predicates
   227	# ---------------------------------------------------------------------------
   228	
   229	
   230	def _parse(src: str) -> ast.AST:
   231	    return ast.parse(src, filename="<synthetic>")
   232	
   233	
   234	class TestPredicates:
   235	    def test_from_rag_lib_is_caught(self):
   236	        tree = _parse("from backend.app.rag.reviewer_advisor import advise\n")
   237	        assert any(_module_predicate_from_rag(m) for m in _imports_modules(tree))
   238	
   239	    def test_bare_import_rag_subpackage_is_caught(self):
   240	        tree = _parse("import backend.app.rag.kb\n")
   241	        # `_imports_modules` records the bare-import target as the full name
   242	        names = _imports_modules(tree)
   243	        assert any(_module_predicate_from_rag(n) for n in names)
   244	
   245	    def test_unrelated_rag_lookalike_is_ignored(self):
   246	        # `backend.app.ragout` must NOT match `backend.app.rag.*`
   247	        tree = _parse("from backend.app.ragout import helper\n")
   248	        names = _imports_modules(tree)
   249	        assert not any(_module_predicate_from_rag(n) for n in names)
   250	
   251	    def test_relative_import_records_module(self):
   252	        tree = _parse("from .reviewer_advisor import advise\n")
   253	        names = _imports_modules(tree)
   254	        assert "reviewer_advisor" in names
   255	
   256	    def test_forbidden_facade_set_recognizes_cli_modules(self):
   257	        for name in _FORBIDDEN_FACADE_IMPORTS:
   258	            assert name.startswith("backend.app.rag.")
   259	            tail = name.rsplit(".", 1)[1]
   260	            # Each forbidden module is either a CLI shell or the coverage_audit
   261	            # CLI-shaped tool. "cli" alone (PR #38 ingest CLI) counts.
   262	            assert tail.endswith("_cli") or tail == "cli" or tail == "coverage_audit"

exec
/bin/zsh -lc "git show pr-53:docs/adr/ADR-017-rag-facade-cli-lib-parity.md | nl -ba | sed -n '1,320p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
     1	# ADR-017: RAG Facade In-Process + CLI/Library Parity
     2	
     3	- **Status:** Draft (parallel to ADR-014, ADR-015, ADR-016)
     4	- **Decider:** Claude Code CLI (Opus 4.7, 1M context) — human-confirmed
     5	- **Date:** 2026-04-26
     6	- **Related Phase:** 2.1 — Engineer Entry & Run Submission (RAG advisor surfaces in 2.1; preflight publish loops in 2.2)
     7	- **Branch:** `feature/AI-FEA-ADR-017-rag-facade-cli-lib-parity`
     8	- **Companion ADRs (Draft, parallel):** ADR-014 (WS event bus), ADR-015 (workbench → agent RPC), ADR-016 (`.frd → .vtu` + result viz)
     9	
    10	---
    11	
    12	## Context
    13	
    14	The RAG track (PR #38–#47) lands a complete corpus + advisor + preflight publish loop:
    15	
    16	```
    17	SimPlan → predict_for_simplan → SurrogateHint
    18	                                    ↓
    19	KB → advise(verdict, fault) → ReviewerAdvice    [PR #40]
    20	                                    ↓
    21	combine(hint, advice) → PreflightSummary        [PR #42]
    22	                                    ↓
    23	publish_preflight(...) → PublishResult          [PR #43, #44 upsert]
    24	                                    ↓
    25	GitHub PR comment
    26	```
    27	
    28	These modules currently expose **two parallel call paths**:
    29	
    30	1. **CLI path:** `python3 -m backend.app.rag.advise_cli`, `…preflight_publish_cli`, etc. (operator-facing, rich `--json` output)
    31	2. **Library path:** `backend.app.rag.reviewer_advisor.advise(...)`, `backend.app.rag.preflight_summary.combine(...)` (Python-import-facing)
    32	
    33	The **workbench** (Phase 2.1, ADR-015) is a **third** consumer that needs the same surface. The risk is:
    34	
    35	- **Drift between CLI and library** as new flags/output fields are added — the workbench could end up matching neither
    36	- **Three independent integration paths** into the same RAG modules — every RAG change re-validated three times
    37	- **Privacy boundary leaks** if the workbench facade independently re-implements logic that the CLI/library already correctly redact
    38	
    39	This ADR pins the contract:
    40	
    41	- A single in-process **`backend.app.workbench.rag_facade`** module wraps the RAG library API (NOT the CLI)
    42	- The CLI continues to wrap the same library API — both surfaces are thin shells over the lib layer
    43	- A discipline test asserts CLI and lib hit identical core code paths on identical inputs (parity)
    44	
    45	---
    46	
    47	## Decision
    48	
    49	**Pattern:** the workbench imports `backend.app.rag.{reviewer_advisor, preflight_summary, preflight_publish}` through a single facade module, **`backend/app/workbench/rag_facade.py`**, sibling to `agent_facade.py` (ADR-015).
    50	
    51	**The CLI is not a dependency.** The workbench does NOT shell out to `python3 -m backend.app.rag.advise_cli`. Three reasons:
    52	
    53	1. **Process spawning cost.** BGE-M3 model load is ~6 s per CLI invocation; the workbench would wear that on every advisor request.
    54	2. **Type erasure.** CLI returns JSON-on-stdout; the facade would re-parse and re-validate something the library already returns as a typed object.
    55	3. **Cancellation semantics.** The workbench needs `asyncio` cancellation; subprocess cancellation requires a SIGTERM dance.
    56	
    57	**The CLI must remain a thin shell over the library.** The discipline test (below) enforces this.
    58	
    59	**Direction:** workbench → rag library only. RAG library does not know the workbench exists. No RAG function gains a `workbench` keyword argument or callback. Same direction-of-coupling rule as ADR-015.
    60	
    61	**Privacy boundary:** the facade is the choke point for redaction. RAG queries can include user-typed natural language; the facade scrubs sensitive sub-strings (per ADR-014 §Privacy) before passing to `reviewer_advisor.advise(...)`. The library trusts its inputs; the facade is responsible for not passing things it shouldn't.
    62	
    63	---
    64	
    65	## Facade module map
    66	
    67	| Module | New / existing | Purpose |
    68	|--------|----------------|---------|
    69	| `backend/app/workbench/rag_facade.py` | **new (this PR)** | the only file in `backend/app/workbench/` that imports `backend.app.rag.*` |
    70	| `backend/app/workbench/__init__.py` | existing (ADR-015) | package marker |
    71	| `backend/app/rag/reviewer_advisor.py` | covered by PR #40 | `advise(verdict, fault) → ReviewerAdvice` |
    72	| `backend/app/rag/preflight_summary.py` | covered by PR #42 | `combine(hint, advice) → PreflightSummary` |
    73	| `backend/app/rag/preflight_publish.py` | covered by PR #43, #44 | `publish_preflight(...) → PublishResult` |
    74	
    75	The split between `agent_facade.py` (ADR-015) and `rag_facade.py` (this ADR) is deliberate: agents are stateful (LangGraph state machine) and have HF1 zone protection; RAG is stateless query + advisory. They have different lifetimes, different failure modes, and different test surfaces.
    76	
    77	**`rag_facade.py` is the workbench's choke point for `backend.app.rag.*`.** A static check in `tests/test_workbench_facade_discipline.py` (this PR extends the ADR-015 test) enforces the rule.
    78	
    79	---
    80	
    81	## CLI/library parity
    82	
    83	The contract has three rules:
    84	
    85	1. **Every CLI subcommand shells through the library API.** The CLI may add presentation logic (formatting, `--json` mode, exit-code mapping) but MUST NOT re-implement the underlying advise/combine/publish logic.
    86	2. **Every CLI flag corresponds to a library function parameter.** New flags require library-side parameters first. The CLI never reads from globals or env vars that the library cannot.
    87	3. **Every library function has at least one CLI test that round-trips its output.** This guarantees that library-side breaking changes are caught by CLI tests, not just import-only tests.
    88	
    89	Operationally, this means:
    90	
    91	- The **library** is what the workbench facade imports
    92	- The **CLI** is what the operator uses on a terminal
    93	- The **discipline tests** assert the two paths cannot drift
    94	
    95	---
    96	
    97	## Singleton policy for BGE-M3
    98	
    99	The workbench backend loads BGE-M3 **once at startup** as a process-level singleton (`backend.app.rag.kb.get_kb()` cached). All facade calls reuse the same model object.
   100	
   101	This decision was made independently in the architecture review (Notion 2026-04-26, Q3 startup-singleton). It avoids:
   102	
   103	- Per-request model load (~6 s) — would render the workbench unusable
   104	- Per-request memory churn (~2 GB resident) — would OOM on small VMs
   105	
   106	The CLI continues to load BGE-M3 per invocation — that's fine; CLI users absorb the cold-start once per session.
   107	
   108	The discipline test asserts that the workbench does NOT take a per-request `KnowledgeBase` parameter into the facade — only the singleton accessor.
   109	
   110	---
   111	
   112	## Authorization
   113	
   114	`POST /workbench/rag/advise` and `POST /workbench/rag/preflight` (Phase 2.1 follow-up) are gated by the same `X-Workbench-Token` header from ADR-015. The facade does not perform its own auth.
   115	
   116	---
   117	
   118	## Discipline tests
   119	
   120	This PR adds a new test file, **`tests/test_rag_facade_parity.py`**, asserting:
   121	
   122	1. **Only `rag_facade.py` and `agent_facade.py` import from `backend.app.rag.*` outside the rag package itself.** Walks all `backend/app/workbench/*.py` (when present) and asserts.
   123	2. **`rag_facade.py` does not import `backend.app.rag.cli` / `query_cli` / `advise_cli` / `preflight_publish_cli` / `coverage_audit`.** The facade goes through the library, not the CLI shell.
   124	3. **CLI parity surface check.** For each CLI module that exists (skipped if not present yet — RAG track lands in PRs #38–#47), assert the CLI module imports the corresponding library module. Detects when someone adds a new CLI subcommand without backing it with a library function.
   125	4. **No CLI module imports another CLI module's `main`.** CLI modules compose through the library, never through each other's `main()`.
   126	
   127	Pure-AST static checks — no import-time execution; <100ms on the whole repo.
   128	
   129	---
   130	
   131	## Considered alternatives
   132	
   133	### Workbench shells out to `advise_cli` / `preflight_publish_cli`
   134	Pros: maximum reuse of operator-facing surface; no second integration point.
   135	Cons: ~6s BGE-M3 cold start per request; type erasure through JSON-on-stdout; cancellation requires SIGTERM. **Rejected.**
   136	
   137	### Workbench reimplements its own RAG client (parallel to lib + CLI)
   138	Pros: full control over privacy/redaction.
   139	Cons: triple validation surface; redaction logic drifts; bug fixes need three patches. **Rejected.**
   140	
   141	### Library exposes async API; facade is a no-op pass-through
   142	Pros: thinnest possible facade.
   143	Cons: privacy redaction needs a place to live; without a facade, the redaction lives in the library (forces RAG to know about workbench-specific concerns) or in every caller (drifts). The facade is the right home for redaction. **Rejected.**
   144	
   145	### Single package `backend.app.rag.workbench_adapter` instead of `workbench.rag_facade`
   146	Pros: keeps RAG-related code in one tree.
   147	Cons: violates ADR-015's direction-of-coupling (RAG library would gain a workbench-aware module). **Rejected.**
   148	
   149	---
   150	
   151	## Implementation plan
   152	
   153	This ADR alone produces no executable RAG code beyond the discipline test. The actual `rag_facade.py` and the wired endpoints land in Phase 2.1 follow-up PRs **after** the RAG track (PR #38–#47) has merged.
   154	
   155	| File | Status | Owner | Notes |
   156	|------|--------|-------|-------|
   157	| `docs/adr/ADR-017-rag-facade-cli-lib-parity.md` | this PR | Claude Code | M1 trigger |
   158	| `tests/test_rag_facade_parity.py` | this PR | Claude Code | static parity + discipline checks (M2) |
   159	| `backend/app/workbench/rag_facade.py` | Phase 2.1 follow-up | Claude Code | the only `backend.app.rag.*` import site from workbench |
   160	| `backend/app/api/rag.py` | Phase 2.1 follow-up | Claude Code | `POST /workbench/rag/advise`, `POST /workbench/rag/preflight` |
   161	| (CLI modules, RAG library) | already in flight | Claude Code | PR #38–#47 |
   162	
   163	---
   164	
   165	## Codex review expectation
   166	
   167	This PR triggers M1 (governance text) and M2 (executable assertions in `test_rag_facade_parity.py`). It does **not** touch HF1 zones. It is **not** an enforcement-coupling PR.
   168	
   169	Self-pass-rate: **30%** — match the BLOCKING ceiling. The parity tests are the contract every Phase 2.1 RAG-touching PR will be measured against.
   170	
   171	---
   172	
   173	## Cross-references
   174	
   175	- ADR-011 §T2 — M1+M2 trigger compliance basis
   176	- ADR-011 §HF1 — no HF1.x file touched
   177	- ADR-012 R2 (PR #24) — 30% BLOCKING ceiling honored
   178	- ADR-014 (Draft, parallel) — privacy-boundary spec; this ADR's facade is the redaction site
   179	- ADR-015 (Draft, parallel) — sibling facade pattern; same direction-of-coupling rule
   180	- ADR-016 (Draft, parallel) — independent surface (viz), no overlap
   181	- PR #38–#47 — the RAG library + CLI surface this ADR pins
   182	- Architecture review by Opus 4.7 (Notion, 2026-04-26) — Q3 (BGE-M3 startup singleton), Q7-R2 (privacy boundary), CLI/lib parity
   183	
   184	---
   185	
   186	## Status notes
   187	
   188	**Draft → Final criteria:**
   189	
   190	1. Codex R1 returns APPROVE or APPROVE_WITH_NITS
   191	2. The parity tests pass on `main` and on every workbench-track PR
   192	3. Phase 2.1 follow-up PR implements `rag_facade.py` without ever calling the CLI
   193	
   194	Until all three are met, this ADR remains `Draft`.

codex
A few gaps are appearing in the static-discipline tests rather than the ADR prose itself. I’m checking the live repo tree around `backend/app/rag` and the stacked implementation branches now to separate “draft contract gap” from “would immediately miss a real bypass on main.”
exec
/bin/zsh -lc 'rg --files backend/app/rag tests | sort' in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
rg: backend/app/rag: No such file or directory (os error 2)
tests/__init__.py
tests/conftest.py
tests/test_architect.py
tests/test_calculix_driver.py
tests/test_checkpointer.py
tests/test_cold_smoke_e2e.py
tests/test_compute_calibration_cap.py
tests/test_extract_pr_self_pass_rate.py
tests/test_frd_parser.py
tests/test_freecad_driver.py
tests/test_geometry_agent.py
tests/test_geometry_checker.py
tests/test_gmsh_driver.py
tests/test_hf1_path_guard.py
tests/test_human_fallback.py
tests/test_jacobian.py
tests/test_markdown_reporter.py
tests/test_mesh_agent.py
tests/test_reviewer_agent.py
tests/test_router.py
tests/test_schemas.py
tests/test_solver_agent.py
tests/test_stub_imports.py
tests/test_toolchain_probes.py
tests/test_viz_agent.py
tests/test_vtp_reporter.py

exec
/bin/zsh -lc "git show pr-54:backend/app/workbench/agent_facade.py | nl -ba | sed -n '1,260p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
     1	"""Agent facade — the SOLE workbench call site that imports `agents.*`.
     2	
     3	ADR-015 §Decision pins the discipline contract:
     4	
     5	- only this file may import `agents.*` from anywhere in `backend/app/workbench/`
     6	- all calls into agents are read-only with respect to agent state
     7	- agents observe nothing about the workbench (no `workbench` kwarg, no
     8	  callback registration through the facade)
     9	
    10	This module currently exposes the architect-agent surface only. The
    11	geometry / mesh / solver / reviewer agents are reached through the
    12	LangGraph compiled state machine in `run_orchestrator` (Phase 2.1
    13	follow-up); they do not need a dedicated facade entrypoint.
    14	
    15	Design notes:
    16	
    17	- The facade does NOT import `schemas.sim_state` (HF1.4). It builds the
    18	  per-call agent input as a plain dict; the architect's `run()` reads
    19	  via `state.get(key)` and tolerates missing keys.
    20	- The facade does NOT touch agent module-level state — see
    21	  `tests/test_workbench_facade_discipline.py`.
    22	- The facade does NOT cache `SimPlan`s; HMAC binding lives in
    23	  `task_spec_builder` so the draft → submit roundtrip is verifiable.
    24	"""
    25	
    26	from __future__ import annotations
    27	
    28	import logging
    29	from dataclasses import dataclass
    30	
    31	from agents import architect
    32	from schemas.sim_plan import SimPlan
    33	
    34	logger = logging.getLogger(__name__)
    35	
    36	
    37	class ArchitectError(Exception):
    38	    """Raised when the architect agent fails to produce a SimPlan."""
    39	
    40	
    41	@dataclass(frozen=True)
    42	class ArchitectResult:
    43	    """Outcome of a single architect invocation.
    44	
    45	    Attributes
    46	    ----------
    47	    plan:
    48	        The SimPlan the architect produced. Always present when the
    49	        result is returned by `draft_simplan_from_nl` (failures raise
    50	        instead).
    51	    fault_class:
    52	        Stringified `FaultClass` value the architect emitted alongside
    53	        the plan. Stored as a plain string to keep the facade free of
    54	        `schemas.sim_state` imports (ADR-015 rule #3 / HF1.4).
    55	    """
    56	
    57	    plan: SimPlan
    58	    fault_class: str
    59	
    60	
    61	def draft_simplan_from_nl(nl_request: str, *, case_id: str | None = None) -> ArchitectResult:
    62	    """Translate a natural-language request to a `SimPlan` via the architect agent.
    63	
    64	    The architect agent runs ONCE per request (per ADR-015's confirmation
    65	    protocol — there is no LLM regeneration between draft and submit).
    66	    Edits the user makes after seeing the rendered SimPlan are applied
    67	    as a structured diff in `task_spec_builder`, NOT by re-invoking the
    68	    agent.
    69	
    70	    Parameters
    71	    ----------
    72	    nl_request:
    73	        The engineer's free-form problem description from the workbench
    74	        dialog. Must be non-empty.
    75	    case_id:
    76	        Optional pre-assigned case id. When omitted, the architect
    77	        derives one deterministically from the request body.
    78	
    79	    Returns
    80	    -------
    81	    ArchitectResult
    82	        Wraps the produced `SimPlan` and the fault-class signal the
    83	        architect emitted.
    84	
    85	    Raises
    86	    ------
    87	    ValueError
    88	        If `nl_request` is empty.
    89	    ArchitectError
    90	        If the architect failed to produce a `SimPlan` (LLM error,
    91	        validation error, etc.). The error message includes the
    92	        agent's diagnostic history when available.
    93	    """
    94	    if not nl_request or not nl_request.strip():
    95	        raise ValueError("nl_request must be a non-empty string")
    96	
    97	    state: dict[str, object] = {"user_request": nl_request}
    98	    if case_id is not None:
    99	        state["case_id"] = case_id
   100	
   101	    result = architect.run(state)  # type: ignore[arg-type]
   102	
   103	    plan = result.get("plan")
   104	    if not isinstance(plan, SimPlan):
   105	        history = result.get("history", [])
   106	        fault = result.get("fault_class", "unknown")
   107	        raise ArchitectError(
   108	            f"architect failed to produce a SimPlan (fault_class={fault!s}); "
   109	            f"history={history!r}"
   110	        )
   111	
   112	    return ArchitectResult(plan=plan, fault_class=str(result.get("fault_class", "none")))
   113	
   114	
   115	__all__ = ["ArchitectError", "ArchitectResult", "draft_simplan_from_nl"]

exec
/bin/zsh -lc "git show pr-55:backend/app/runtime/event_bus.py | nl -ba | sed -n '1,320p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
     1	"""Per-run in-process event bus (ADR-014 §Backpressure / §Resume semantics).
     2	
     3	A `RunEventBus` owns:
     4	
     5	- a producer-side bounded queue (cap 1024) — LangGraph callbacks enqueue
     6	  events here as the run progresses; the WS endpoint drains it
     7	- a 256-event ring buffer for resume-via-`?since_seq` — the WS endpoint
     8	  uses this when a client reconnects mid-run
     9	- monotonic per-run `seq` counter so consumers can detect gap
    10	
    11	Backpressure rules (per ADR-014 §Backpressure):
    12	
    13	- queue capacity = 1024
    14	- when the queue is full and a non-critical event arrives: drop the
    15	  arriving event and enqueue a synthetic `bus.dropped` so the frontend
    16	  can render a banner
    17	- critical events (`run.started`, `run.finished`, `handoff.required`)
    18	  bypass the cap. They MAY push the queue temporarily above 1024.
    19	  Losing them would leave the frontend hung forever, so the cap is a
    20	  *non-critical-drop trigger*, not a hard size limit
    21	
    22	Ring-buffer (per ADR-014 §Resume semantics):
    23	
    24	- retains the last 256 events emitted on this run
    25	- `replay_since(seq)` returns events with seq > `seq`
    26	- if `seq` is older than the buffer's tail, the result starts with a
    27	  synthetic `bus.gap` describing the requested window vs. what the
    28	  buffer actually holds; the frontend must refetch state via REST
    29	
    30	Implementation note: the queue is a `collections.deque` + an
    31	`asyncio.Event` for "events available", NOT `asyncio.Queue`. The cap
    32	is a soft trigger for the drop-non-critical path; we do not need
    33	`asyncio.Queue`'s internal `put` semaphore + `_unfinished_tasks`
    34	machinery, which is private API.
    35	
    36	This module is pure asyncio + Pydantic; no FastAPI / no LangGraph
    37	imports. The WS endpoint and the LangGraph callbacks are separate
    38	modules that wrap this bus.
    39	"""
    40	
    41	from __future__ import annotations
    42	
    43	import asyncio
    44	import logging
    45	from collections import deque
    46	from collections.abc import Iterable
    47	from dataclasses import dataclass, field
    48	from datetime import datetime, timezone
    49	from schemas.ws_events import (
    50	    CRITICAL_EVENT_KINDS,
    51	    BusDropped,
    52	    BusGap,
    53	    WSEvent,
    54	    is_critical,
    55	)
    56	
    57	logger = logging.getLogger(__name__)
    58	
    59	# Per ADR-014 §Backpressure / §Resume semantics.
    60	QUEUE_CAPACITY = 1024
    61	RING_BUFFER_CAPACITY = 256
    62	
    63	
    64	def _utcnow_iso() -> str:
    65	    """ISO 8601 UTC timestamp with second precision and trailing 'Z'."""
    66	    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    67	
    68	
    69	@dataclass
    70	class RunEventBus:
    71	    """Per-run event bus.
    72	
    73	    Construct one bus per run id. The orchestrator that invokes
    74	    LangGraph holds a reference; the WS endpoint resolves the bus from
    75	    a registry (Phase 2.1 follow-up) when a client connects.
    76	    """
    77	
    78	    run_id: str
    79	    _queue: deque = field(init=False)
    80	    _has_event: asyncio.Event = field(init=False)
    81	    _ring: deque = field(init=False)
    82	    _next_seq: int = field(init=False, default=1)
    83	    _closed: bool = field(init=False, default=False)
    84	    _lock: asyncio.Lock = field(init=False)
    85	
    86	    def __post_init__(self) -> None:
    87	        if not self.run_id:
    88	            raise ValueError("run_id must be a non-empty string")
    89	        self._queue = deque()
    90	        self._has_event = asyncio.Event()
    91	        self._ring = deque(maxlen=RING_BUFFER_CAPACITY)
    92	        self._lock = asyncio.Lock()
    93	
    94	    # ------------------------------------------------------------------
    95	    # Producer side
    96	    # ------------------------------------------------------------------
    97	
    98	    async def emit(self, event: WSEvent) -> None:  # type: ignore[valid-type]
    99	        """Append an event to the bus.
   100	
   101	        Behavior:
   102	
   103	        - assigns the next monotonic seq, records the event in the
   104	          ring buffer, and enqueues for the consumer
   105	        - when the queue is at `QUEUE_CAPACITY` and the new event is
   106	          non-critical, the new event itself is dropped and a synthetic
   107	          `bus.dropped` is enqueued in its place (the queue is sized
   108	          for the worst chatty-progress scenario; under load the most
   109	          recent progress is the most informative one to keep, but we
   110	          deliberately drop *new* non-critical events rather than
   111	          rewriting the queue's middle to keep ordering stable)
   112	        - critical events (`run.started`, `run.finished`,
   113	          `handoff.required`) bypass the cap. They MAY push the queue
   114	          temporarily above `QUEUE_CAPACITY` — losing them would leave
   115	          the frontend hung forever, which is unacceptable.
   116	
   117	        Raises RuntimeError if the bus has been `close()`-d.
   118	        """
   119	        if self._closed:
   120	            raise RuntimeError(f"event bus for run {self.run_id} is closed")
   121	
   122	        async with self._lock:
   123	            sealed = event.model_copy(update={"seq": self._next_seq})
   124	            self._next_seq += 1
   125	            self._ring.append(sealed)
   126	
   127	            if len(self._queue) < QUEUE_CAPACITY:
   128	                self._enqueue(sealed)
   129	                return
   130	
   131	            # Queue at capacity.
   132	            if is_critical(sealed.event):
   133	                # Critical events bypass the cap. Enqueue and let the
   134	                # queue grow; the consumer will drain.
   135	                self._enqueue(sealed)
   136	                logger.info(
   137	                    "run %s emitted critical event %s while queue at capacity %d",
   138	                    self.run_id,
   139	                    sealed.event,
   140	                    QUEUE_CAPACITY,
   141	                )
   142	                return
   143	
   144	            # Non-critical event arriving on a full queue: drop it
   145	            # (most recent non-critical is "newest" and tends to be
   146	            # `node.progress`; its loss is the documented degraded
   147	            # mode in ADR-014 §Consequences) and emit a synthetic
   148	            # `bus.dropped` so the frontend can show a banner.
   149	            self._enqueue_synthetic_drop(sealed.event)
   150	
   151	    def _enqueue(self, event: WSEvent) -> None:  # type: ignore[valid-type]
   152	        self._queue.append(event)
   153	        self._has_event.set()
   154	
   155	    def _enqueue_synthetic_drop(self, dropped_kind: str) -> None:
   156	        """Record (in the ring) and enqueue a synthetic `bus.dropped`.
   157	
   158	        Always called under the bus lock from `emit()`. The synthetic
   159	        event is exempt from the cap on the same grounds as critical
   160	        events: losing the bus.dropped notification would mask the
   161	        original loss from the frontend.
   162	        """
   163	        bus_dropped = BusDropped(
   164	            run_id=self.run_id,
   165	            seq=self._next_seq,
   166	            ts=_utcnow_iso(),
   167	            dropped_count=1,
   168	            dropped_kinds=(dropped_kind,),
   169	        )
   170	        self._next_seq += 1
   171	        self._ring.append(bus_dropped)
   172	        self._enqueue(bus_dropped)
   173	
   174	    # ------------------------------------------------------------------
   175	    # Consumer side
   176	    # ------------------------------------------------------------------
   177	
   178	    async def get(self) -> WSEvent:  # type: ignore[valid-type]
   179	        """Block until an event is available, then return it."""
   180	        while True:
   181	            async with self._lock:
   182	                if self._queue:
   183	                    event = self._queue.popleft()
   184	                    if not self._queue:
   185	                        self._has_event.clear()
   186	                    return event
   187	            await self._has_event.wait()
   188	
   189	    def qsize(self) -> int:
   190	        return len(self._queue)
   191	
   192	    def replay_since(self, since_seq: int) -> Iterable[WSEvent]:  # type: ignore[valid-type]
   193	        """Replay events with seq > since_seq from the ring buffer.
   194	
   195	        If the requested `since_seq` is older than the buffer's tail
   196	        (meaning events have been evicted), the iterable starts with a
   197	        synthetic `bus.gap` describing the requested window. The caller
   198	        must then refetch state via REST per ADR-014 §Resume semantics.
   199	        """
   200	        if since_seq < 0:
   201	            raise ValueError("since_seq must be non-negative")
   202	
   203	        # Materialize a snapshot to avoid concurrent-mutation surprises
   204	        # mid-iteration.
   205	        snapshot = list(self._ring)
   206	        if not snapshot:
   207	            return iter(())
   208	
   209	        oldest_seq = snapshot[0].seq
   210	        if since_seq + 1 < oldest_seq:
   211	            gap = BusGap(
   212	                run_id=self.run_id,
   213	                seq=self._next_seq,
   214	                ts=_utcnow_iso(),
   215	                requested_since=since_seq,
   216	                buffer_tail=oldest_seq,
   217	            )
   218	            tail = [ev for ev in snapshot if ev.seq > since_seq]
   219	            return iter([gap, *tail])
   220	
   221	        return iter(ev for ev in snapshot if ev.seq > since_seq)
   222	
   223	    # ------------------------------------------------------------------
   224	    # Lifecycle
   225	    # ------------------------------------------------------------------
   226	
   227	    @property
   228	    def next_seq(self) -> int:
   229	        return self._next_seq
   230	
   231	    @property
   232	    def is_closed(self) -> bool:
   233	        return self._closed
   234	
   235	    def close(self) -> None:
   236	        """Mark the bus closed.
   237	
   238	        After close(), `emit()` raises. Consumers that are awaiting
   239	        `get()` will continue to drain whatever is in-flight; the WS
   240	        endpoint breaks out of its read loop on receipt of a terminal
   241	        event (`run.finished` / `bus.gap`).
   242	        """
   243	        self._closed = True
   244	
   245	
   246	__all__ = [
   247	    "QUEUE_CAPACITY",
   248	    "RING_BUFFER_CAPACITY",
   249	    "RunEventBus",
   250	    "CRITICAL_EVENT_KINDS",
   251	]

exec
/bin/zsh -lc "git show pr-54:backend/app/workbench/task_spec_builder.py | nl -ba | sed -n '1,260p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
     1	"""NL → SimPlan draft + user-signed submit (ADR-015 §Confirmation protocol).
     2	
     3	The Phase 2.1 user flow:
     4	
     5	1. Browser sends `POST /runs/draft { "nl_request": "..." }`
     6	2. Backend calls `draft_from_nl(nl_request)` → returns
     7	   `(SimPlan, draft_id, confirmation_token)`
     8	3. Browser displays the rendered SimPlan; user can edit or accept
     9	4. Browser sends `POST /runs/submit { "draft_id", "confirmation_token", "edits" }`
    10	5. Backend rebuilds the SimPlan with edits applied, validates the
    11	   confirmation_token ties draft_id ↔ rebuilt SimPlan via HMAC, and
    12	   only then invokes the LangGraph run
    13	
    14	The HMAC is computed over `draft_id || canonical-JSON(SimPlan)` with
    15	the workbench token as the key. It guarantees:
    16	
    17	- the SimPlan the user confirmed in step 3 is identical to the SimPlan
    18	  that runs in step 5 (no silent drift)
    19	- a draft cannot be submitted by a third party who didn't see the
    20	  rendered SimPlan
    21	- replay of the same `confirmation_token` against a different
    22	  `draft_id` fails
    23	
    24	There is no LLM regeneration between draft and submit. If the user
    25	edits the draft, edits are applied via a structured diff to the draft
    26	SimPlan; the architect agent is NOT re-invoked.
    27	"""
    28	
    29	from __future__ import annotations
    30	
    31	import hashlib
    32	import hmac
    33	import json
    34	import secrets
    35	import uuid
    36	
    37	from schemas.sim_plan import SimPlan
    38	
    39	from .agent_facade import ArchitectResult, draft_simplan_from_nl
    40	
    41	
    42	class ConfirmationError(Exception):
    43	    """Raised when a draft → submit confirmation cannot be verified."""
    44	
    45	
    46	def _canonical_json(plan: SimPlan) -> bytes:
    47	    """Serialize a SimPlan to canonical JSON bytes.
    48	
    49	    Pydantic v2's `model_dump_json` is non-canonical (key order tracks
    50	    declaration). We re-serialize with `sort_keys=True` to make the
    51	    HMAC input deterministic regardless of model evolution.
    52	    """
    53	    payload = json.loads(plan.model_dump_json())
    54	    return json.dumps(
    55	        payload,
    56	        sort_keys=True,
    57	        separators=(",", ":"),
    58	        ensure_ascii=False,
    59	    ).encode("utf-8")
    60	
    61	
    62	def _hmac_token(secret: bytes, draft_id: str, plan: SimPlan) -> str:
    63	    """Compute HMAC-SHA256 over draft_id || canonical-JSON(plan)."""
    64	    if not secret:
    65	        raise ValueError("workbench secret must be non-empty bytes")
    66	    body = draft_id.encode("utf-8") + b"\x00" + _canonical_json(plan)
    67	    return hmac.new(secret, body, hashlib.sha256).hexdigest()
    68	
    69	
    70	def _new_draft_id() -> str:
    71	    """Generate a draft id with enough entropy to be unguessable.
    72	
    73	    Format: `draft-<uuid4>` — uuid4 is 122 bits of randomness which is
    74	    sufficient since the HMAC binding is the actual security boundary.
    75	    """
    76	    return f"draft-{uuid.uuid4()}"
    77	
    78	
    79	def draft_from_nl(
    80	    nl_request: str,
    81	    *,
    82	    workbench_secret: bytes,
    83	    case_id: str | None = None,
    84	) -> tuple[SimPlan, str, str]:
    85	    """Architect-translate `nl_request` to a SimPlan and emit a confirmation token.
    86	
    87	    Returns
    88	    -------
    89	    (plan, draft_id, confirmation_token)
    90	        - `plan`: the SimPlan the architect produced
    91	        - `draft_id`: a freshly minted, server-side-only identifier
    92	        - `confirmation_token`: HMAC-SHA256 hex string binding the
    93	          draft_id to the canonical-JSON of the plan
    94	
    95	    Notes
    96	    -----
    97	    The caller (e.g. an `/runs/draft` endpoint) is responsible for
    98	    persisting (draft_id, plan, confirmation_token) so the matching
    99	    `submit_with_confirmation` call can validate against the same plan
   100	    bytes. The token alone is NOT a session — it binds a specific
   101	    plan-instance.
   102	    """
   103	    architect_result: ArchitectResult = draft_simplan_from_nl(
   104	        nl_request, case_id=case_id
   105	    )
   106	    draft_id = _new_draft_id()
   107	    token = _hmac_token(workbench_secret, draft_id, architect_result.plan)
   108	    return architect_result.plan, draft_id, token
   109	
   110	
   111	def verify_confirmation(
   112	    *,
   113	    workbench_secret: bytes,
   114	    draft_id: str,
   115	    plan: SimPlan,
   116	    confirmation_token: str,
   117	) -> None:
   118	    """Raise `ConfirmationError` if the token does not bind draft_id to plan.
   119	
   120	    Uses `hmac.compare_digest` to defeat timing oracle attacks on the
   121	    token comparison.
   122	    """
   123	    expected = _hmac_token(workbench_secret, draft_id, plan)
   124	    if not secrets.compare_digest(expected, confirmation_token):
   125	        raise ConfirmationError(
   126	            f"confirmation_token does not match draft_id={draft_id!r} and the supplied SimPlan; "
   127	            f"either the plan was edited in transit or the token was issued for a different draft"
   128	        )
   129	
   130	
   131	__all__ = [
   132	    "ConfirmationError",
   133	    "draft_from_nl",
   134	    "verify_confirmation",
   135	]

exec
/bin/zsh -lc "git show pr-54:tests/test_workbench_agent_facade.py | nl -ba | sed -n '1,260p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
exec
/bin/zsh -lc "git show pr-54:tests/test_workbench_task_spec_builder.py | nl -ba | sed -n '1,320p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
     1	"""Tests for backend.app.workbench.agent_facade (ADR-015 §Decision)."""
     2	
     3	from __future__ import annotations
     4	
     5	from unittest.mock import patch
     6	
     7	import pytest
     8	
     9	# schemas.sim_plan uses `enum.StrEnum` (Python 3.11+). Skip cleanly on older
    10	# interpreters; CI is 3.11+.
    11	pytest.importorskip("schemas.sim_plan")
    12	
    13	from backend.app.workbench.agent_facade import (  # noqa: E402
    14	    ArchitectError,
    15	    ArchitectResult,
    16	    draft_simplan_from_nl,
    17	)
    18	from schemas.sim_plan import AnalysisType, GeometrySpec, PhysicsSpec, SimPlan  # noqa: E402
    19	
    20	
    21	def _sample_plan(case_id: str = "AI-FEA-P0-11") -> SimPlan:
    22	    return SimPlan(
    23	        case_id=case_id,
    24	        physics=PhysicsSpec(type=AnalysisType.STATIC),
    25	        geometry=GeometrySpec(
    26	            mode="knowledge",
    27	            ref="naca",
    28	            params={"profile": "NACA0012", "span": 1.2, "chord": 0.3},
    29	        ),
    30	    )
    31	
    32	
    33	# ---------------------------------------------------------------------------
    34	# Happy path
    35	# ---------------------------------------------------------------------------
    36	
    37	
    38	def test_draft_returns_architect_result_on_success():
    39	    plan = _sample_plan()
    40	    with patch(
    41	        "agents.architect._extract_structured_data",
    42	        return_value=plan,
    43	    ):
    44	        result = draft_simplan_from_nl(
    45	            "Run a static analysis on a NACA0012 cantilever wing.",
    46	        )
    47	    assert isinstance(result, ArchitectResult)
    48	    assert result.plan.case_id == "AI-FEA-P0-11"
    49	    assert result.fault_class == "none"
    50	
    51	
    52	def test_draft_passes_case_id_through_to_architect():
    53	    plan = _sample_plan(case_id="AI-FEA-P2-99")
    54	    with patch(
    55	        "agents.architect._extract_structured_data",
    56	        return_value=plan,
    57	    ):
    58	        result = draft_simplan_from_nl(
    59	            "static beam analysis",
    60	            case_id="AI-FEA-P2-99",
    61	        )
    62	    assert result.plan.case_id == "AI-FEA-P2-99"
    63	
    64	
    65	# ---------------------------------------------------------------------------
    66	# Input validation
    67	# ---------------------------------------------------------------------------
    68	
    69	
    70	def test_empty_nl_request_rejected():
    71	    with pytest.raises(ValueError, match="non-empty"):
    72	        draft_simplan_from_nl("")
    73	
    74	
    75	def test_whitespace_only_nl_request_rejected():
    76	    with pytest.raises(ValueError, match="non-empty"):
    77	        draft_simplan_from_nl("   \n\t  ")
    78	
    79	
    80	# ---------------------------------------------------------------------------
    81	# Architect failure surfaces
    82	# ---------------------------------------------------------------------------
    83	
    84	
    85	def test_architect_returning_none_plan_raises_architect_error():
    86	    with (
    87	        patch("agents.architect._extract_structured_data", return_value=None),
    88	        pytest.raises(ArchitectError) as exc_info,
    89	    ):
    90	        draft_simplan_from_nl("a request the LLM cannot parse")
    91	    # The error includes the fault_class signal so callers can
    92	    # surface a useful message to the workbench dialog.
    93	    assert "fault_class" in str(exc_info.value)
    94	
    95	
    96	def test_architect_llm_exception_raises_architect_error():
    97	    with (
    98	        patch(
    99	            "agents.architect._extract_structured_data",
   100	            side_effect=RuntimeError("LLM 500"),
   101	        ),
   102	        pytest.raises(ArchitectError),
   103	    ):
   104	        draft_simplan_from_nl("static beam")
   105	
   106	
   107	# ---------------------------------------------------------------------------
   108	# Discipline (ADR-015 read-only contract)
   109	# ---------------------------------------------------------------------------
   110	
   111	
   112	def test_facade_does_not_import_sim_state_at_module_level():
   113	    """ADR-015 rule #3: facade does not import schemas.sim_state.
   114	
   115	    A direct sys.modules check is the simplest assertion: importing the
   116	    facade must not pull in schemas.sim_state under any name.
   117	    """
   118	    # Import inside the test so the import order is deterministic.
   119	    import importlib
   120	    import sys
   121	
   122	    # Clear any previously loaded copy so the assertion reflects this
   123	    # import path specifically.
   124	    for mod in list(sys.modules):
   125	        if mod.startswith("backend.app.workbench.agent_facade"):
   126	            del sys.modules[mod]
   127	
   128	    importlib.import_module("backend.app.workbench.agent_facade")
   129	
   130	    # The facade itself MUST NOT have caused schemas.sim_state to be
   131	    # imported. Other tests in the run may have loaded it; we only
   132	    # check that the facade module's own dependency graph is clean.
   133	    facade_module = sys.modules["backend.app.workbench.agent_facade"]
   134	    facade_globals = vars(facade_module)
   135	    # No direct `FaultClass` / `SimState` symbol in the facade's namespace.
   136	    assert "FaultClass" not in facade_globals
   137	    assert "SimState" not in facade_globals
   138	
   139	
   140	def test_facade_does_not_mutate_architect_module_state():
   141	    """The facade must call architect.run; it must NEVER assign to
   142	    architect attributes."""
   143	    plan = _sample_plan()
   144	    with patch(
   145	        "agents.architect._extract_structured_data",
   146	        return_value=plan,
   147	    ):
   148	        # Snapshot architect's public attribute set, then call the
   149	        # facade, then verify nothing was added.
   150	        from agents import architect as architect_mod
   151	
   152	        before = set(vars(architect_mod).keys())
   153	        draft_simplan_from_nl("static beam")
   154	        after = set(vars(architect_mod).keys())
   155	
   156	    assert before == after, (
   157	        "facade mutated agents.architect module-level state — "
   158	        f"added: {after - before}, removed: {before - after}"
   159	    )

 succeeded in 0ms:
     1	"""Tests for backend.app.workbench.task_spec_builder (ADR-015 §Confirmation protocol)."""
     2	
     3	from __future__ import annotations
     4	
     5	import json
     6	from unittest.mock import patch
     7	
     8	import pytest
     9	
    10	# schemas.sim_plan uses `enum.StrEnum` (Python 3.11+). Skip cleanly on older
    11	# interpreters; CI is 3.11+.
    12	pytest.importorskip("schemas.sim_plan")
    13	
    14	from backend.app.workbench.task_spec_builder import (  # noqa: E402
    15	    ConfirmationError,
    16	    _canonical_json,
    17	    _hmac_token,
    18	    _new_draft_id,
    19	    draft_from_nl,
    20	    verify_confirmation,
    21	)
    22	from schemas.sim_plan import AnalysisType, GeometrySpec, PhysicsSpec, SimPlan  # noqa: E402
    23	
    24	SECRET = b"workbench-token-fixture-32-bytes!"
    25	ALT_SECRET = b"different-workbench-token-32-byts"
    26	
    27	
    28	def _sample_plan(case_id: str = "AI-FEA-P0-11") -> SimPlan:
    29	    return SimPlan(
    30	        case_id=case_id,
    31	        physics=PhysicsSpec(type=AnalysisType.STATIC),
    32	        geometry=GeometrySpec(
    33	            mode="knowledge",
    34	            ref="naca",
    35	            params={"profile": "NACA0012", "span": 1.2, "chord": 0.3},
    36	        ),
    37	    )
    38	
    39	
    40	# ---------------------------------------------------------------------------
    41	# canonical_json determinism
    42	# ---------------------------------------------------------------------------
    43	
    44	
    45	def test_canonical_json_is_sorted_keys():
    46	    plan = _sample_plan()
    47	    blob = _canonical_json(plan)
    48	    parsed = json.loads(blob)
    49	    # Re-serialize the parsed structure with sort_keys=True and verify
    50	    # the string round-trips identically.
    51	    rebuilt = json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
    52	        "utf-8"
    53	    )
    54	    assert blob == rebuilt
    55	
    56	
    57	def test_canonical_json_stable_across_calls():
    58	    plan = _sample_plan()
    59	    a = _canonical_json(plan)
    60	    b = _canonical_json(plan)
    61	    assert a == b
    62	
    63	
    64	def test_canonical_json_differs_between_distinct_plans():
    65	    a = _canonical_json(_sample_plan(case_id="AI-FEA-P0-11"))
    66	    b = _canonical_json(_sample_plan(case_id="AI-FEA-P0-12"))
    67	    assert a != b
    68	
    69	
    70	# ---------------------------------------------------------------------------
    71	# _hmac_token contract
    72	# ---------------------------------------------------------------------------
    73	
    74	
    75	def test_hmac_token_is_hex_string():
    76	    token = _hmac_token(SECRET, "draft-abc", _sample_plan())
    77	    assert len(token) == 64
    78	    int(token, 16)  # must parse as hex
    79	
    80	
    81	def test_hmac_token_changes_when_draft_id_changes():
    82	    plan = _sample_plan()
    83	    a = _hmac_token(SECRET, "draft-aaa", plan)
    84	    b = _hmac_token(SECRET, "draft-bbb", plan)
    85	    assert a != b
    86	
    87	
    88	def test_hmac_token_changes_when_plan_changes():
    89	    a = _hmac_token(SECRET, "draft-x", _sample_plan(case_id="AI-FEA-P0-11"))
    90	    b = _hmac_token(SECRET, "draft-x", _sample_plan(case_id="AI-FEA-P0-12"))
    91	    assert a != b
    92	
    93	
    94	def test_hmac_token_changes_when_secret_changes():
    95	    plan = _sample_plan()
    96	    a = _hmac_token(SECRET, "draft-x", plan)
    97	    b = _hmac_token(ALT_SECRET, "draft-x", plan)
    98	    assert a != b
    99	
   100	
   101	def test_hmac_token_rejects_empty_secret():
   102	    with pytest.raises(ValueError, match="non-empty"):
   103	        _hmac_token(b"", "draft-x", _sample_plan())
   104	
   105	
   106	# ---------------------------------------------------------------------------
   107	# _new_draft_id
   108	# ---------------------------------------------------------------------------
   109	
   110	
   111	def test_draft_id_is_unique():
   112	    seen = {_new_draft_id() for _ in range(100)}
   113	    assert len(seen) == 100
   114	
   115	
   116	def test_draft_id_has_expected_prefix():
   117	    assert _new_draft_id().startswith("draft-")
   118	
   119	
   120	# ---------------------------------------------------------------------------
   121	# draft_from_nl wires architect → token correctly
   122	# ---------------------------------------------------------------------------
   123	
   124	
   125	def test_draft_from_nl_returns_plan_draft_id_token_triple():
   126	    plan = _sample_plan()
   127	    with patch(
   128	        "agents.architect._extract_structured_data",
   129	        return_value=plan,
   130	    ):
   131	        produced_plan, draft_id, token = draft_from_nl("static beam", workbench_secret=SECRET)
   132	    assert produced_plan.case_id == "AI-FEA-P0-11"
   133	    assert draft_id.startswith("draft-")
   134	    assert len(token) == 64
   135	
   136	
   137	def test_draft_from_nl_token_validates_with_returned_plan():
   138	    plan = _sample_plan()
   139	    with patch(
   140	        "agents.architect._extract_structured_data",
   141	        return_value=plan,
   142	    ):
   143	        produced_plan, draft_id, token = draft_from_nl("static beam", workbench_secret=SECRET)
   144	    # Round-trip: the returned token must verify against the returned plan.
   145	    verify_confirmation(
   146	        workbench_secret=SECRET,
   147	        draft_id=draft_id,
   148	        plan=produced_plan,
   149	        confirmation_token=token,
   150	    )
   151	
   152	
   153	# ---------------------------------------------------------------------------
   154	# verify_confirmation contract — drift / replay / cross-secret
   155	# ---------------------------------------------------------------------------
   156	
   157	
   158	def test_verify_confirmation_rejects_token_for_different_plan():
   159	    plan = _sample_plan()
   160	    other_plan = _sample_plan(case_id="AI-FEA-P0-99")
   161	    token = _hmac_token(SECRET, "draft-x", plan)
   162	    with pytest.raises(ConfirmationError):
   163	        verify_confirmation(
   164	            workbench_secret=SECRET,
   165	            draft_id="draft-x",
   166	            plan=other_plan,
   167	            confirmation_token=token,
   168	        )
   169	
   170	
   171	def test_verify_confirmation_rejects_token_for_different_draft_id():
   172	    """Replay attack: same token, different draft_id."""
   173	    plan = _sample_plan()
   174	    token = _hmac_token(SECRET, "draft-original", plan)
   175	    with pytest.raises(ConfirmationError):
   176	        verify_confirmation(
   177	            workbench_secret=SECRET,
   178	            draft_id="draft-replay-target",
   179	            plan=plan,
   180	            confirmation_token=token,
   181	        )
   182	
   183	
   184	def test_verify_confirmation_rejects_token_signed_with_different_secret():
   185	    plan = _sample_plan()
   186	    token = _hmac_token(ALT_SECRET, "draft-x", plan)
   187	    with pytest.raises(ConfirmationError):
   188	        verify_confirmation(
   189	            workbench_secret=SECRET,
   190	            draft_id="draft-x",
   191	            plan=plan,
   192	            confirmation_token=token,
   193	        )
   194	
   195	
   196	def test_verify_confirmation_rejects_truncated_token():
   197	    plan = _sample_plan()
   198	    token = _hmac_token(SECRET, "draft-x", plan)
   199	    with pytest.raises(ConfirmationError):
   200	        verify_confirmation(
   201	            workbench_secret=SECRET,
   202	            draft_id="draft-x",
   203	            plan=plan,
   204	            confirmation_token=token[:-1],  # 63 chars instead of 64
   205	        )
   206	
   207	
   208	def test_verify_confirmation_rejects_empty_token():
   209	    plan = _sample_plan()
   210	    with pytest.raises(ConfirmationError):
   211	        verify_confirmation(
   212	            workbench_secret=SECRET,
   213	            draft_id="draft-x",
   214	            plan=plan,
   215	            confirmation_token="",
   216	        )
   217	
   218	
   219	def test_verify_confirmation_uses_constant_time_compare():
   220	    """Smoke test that the comparison path goes through hmac/secrets,
   221	    not a Python `==` that early-exits on mismatch."""
   222	    import secrets as secrets_mod
   223	
   224	    plan = _sample_plan()
   225	    valid = _hmac_token(SECRET, "draft-x", plan)
   226	
   227	    # Patch compare_digest to a sentinel; if verify_confirmation calls
   228	    # it, our test passes; if it uses `==`, the patch is unused and we
   229	    # detect the regression.
   230	    called = {"hit": False}
   231	
   232	    real = secrets_mod.compare_digest
   233	
   234	    def spy(a, b):
   235	        called["hit"] = True
   236	        return real(a, b)
   237	
   238	    with patch("backend.app.workbench.task_spec_builder.secrets.compare_digest", spy):
   239	        verify_confirmation(
   240	            workbench_secret=SECRET,
   241	            draft_id="draft-x",
   242	            plan=plan,
   243	            confirmation_token=valid,
   244	        )
   245	
   246	    assert called["hit"], (
   247	        "verify_confirmation should compare via secrets.compare_digest "
   248	        "to defeat timing-oracle attacks; saw direct equality instead"
   249	    )

exec
/bin/zsh -lc "git show pr-55:tests/test_runtime_event_bus.py | nl -ba | sed -n '1,420p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
     1	"""Tests for backend.app.runtime.event_bus (ADR-014 §Backpressure / §Resume)."""
     2	
     3	from __future__ import annotations
     4	
     5	import asyncio
     6	
     7	import pytest
     8	
     9	from backend.app.runtime.event_bus import (
    10	    QUEUE_CAPACITY,
    11	    RING_BUFFER_CAPACITY,
    12	    RunEventBus,
    13	)
    14	from schemas.ws_events import (
    15	    NodeEntered,
    16	    NodeProgress,
    17	    RunFinished,
    18	    RunStarted,
    19	)
    20	
    21	# ---------------------------------------------------------------------------
    22	# Fixtures + helpers
    23	# ---------------------------------------------------------------------------
    24	
    25	
    26	def _started(run_id: str = "RUN-1") -> RunStarted:
    27	    return RunStarted(
    28	        run_id=run_id,
    29	        seq=0,  # placeholder; emit() reassigns
    30	        ts="2026-04-26T12:00:00Z",
    31	        task_spec_digest="sha256:" + "a" * 64,
    32	    )
    33	
    34	
    35	def _progress(run_id: str = "RUN-1", message: str = "step") -> NodeProgress:
    36	    return NodeProgress(
    37	        run_id=run_id,
    38	        seq=0,
    39	        ts="2026-04-26T12:00:00Z",
    40	        node_name="geometry",
    41	        message=message,
    42	    )
    43	
    44	
    45	def _node_entered(run_id: str = "RUN-1", node_name: str = "geometry") -> NodeEntered:
    46	    return NodeEntered(
    47	        run_id=run_id,
    48	        seq=0,
    49	        ts="2026-04-26T12:00:00Z",
    50	        node_name=node_name,
    51	        stage="geometry",
    52	    )
    53	
    54	
    55	def _finished(run_id: str = "RUN-1") -> RunFinished:
    56	    return RunFinished(
    57	        run_id=run_id,
    58	        seq=0,
    59	        ts="2026-04-26T12:00:00Z",
    60	        terminal_status="success",
    61	        total_duration_ms=42,
    62	    )
    63	
    64	
    65	# ---------------------------------------------------------------------------
    66	# Construction + invariants
    67	# ---------------------------------------------------------------------------
    68	
    69	
    70	def test_construct_with_empty_run_id_rejected():
    71	    with pytest.raises(ValueError, match="non-empty"):
    72	        RunEventBus(run_id="")
    73	
    74	
    75	def test_capacity_constants_match_adr_014():
    76	    """ADR-014 §Backpressure pins QUEUE=1024 / RING=256."""
    77	    assert QUEUE_CAPACITY == 1024
    78	    assert RING_BUFFER_CAPACITY == 256
    79	
    80	
    81	# ---------------------------------------------------------------------------
    82	# Producer / consumer happy path
    83	# ---------------------------------------------------------------------------
    84	
    85	
    86	@pytest.mark.asyncio
    87	async def test_emit_assigns_monotonic_seq():
    88	    bus = RunEventBus(run_id="RUN-A")
    89	    await bus.emit(_started())
    90	    await bus.emit(_progress())
    91	    await bus.emit(_finished())
    92	
    93	    a = await bus.get()
    94	    b = await bus.get()
    95	    c = await bus.get()
    96	    assert (a.seq, b.seq, c.seq) == (1, 2, 3)
    97	
    98	
    99	@pytest.mark.asyncio
   100	async def test_emit_preserves_event_type():
   101	    bus = RunEventBus(run_id="RUN-A")
   102	    await bus.emit(_started(run_id="RUN-A"))
   103	    out = await bus.get()
   104	    assert isinstance(out, RunStarted)
   105	    assert out.run_id == "RUN-A"
   106	
   107	
   108	@pytest.mark.asyncio
   109	async def test_get_blocks_until_emit():
   110	    bus = RunEventBus(run_id="RUN-A")
   111	    consumer = asyncio.create_task(bus.get())
   112	    await asyncio.sleep(0.01)  # let the consumer start awaiting
   113	    assert not consumer.done()
   114	    await bus.emit(_progress(message="hello"))
   115	    out = await asyncio.wait_for(consumer, timeout=0.5)
   116	    assert out.message == "hello"
   117	
   118	
   119	@pytest.mark.asyncio
   120	async def test_qsize_reflects_queue():
   121	    bus = RunEventBus(run_id="RUN-A")
   122	    assert bus.qsize() == 0
   123	    await bus.emit(_progress())
   124	    await bus.emit(_progress())
   125	    assert bus.qsize() == 2
   126	    await bus.get()
   127	    assert bus.qsize() == 1
   128	
   129	
   130	# ---------------------------------------------------------------------------
   131	# Backpressure: non-critical events drop on overflow
   132	# ---------------------------------------------------------------------------
   133	
   134	
   135	@pytest.mark.asyncio
   136	async def test_overflow_drops_non_critical_and_emits_bus_dropped():
   137	    bus = RunEventBus(run_id="RUN-A")
   138	    # Fill queue to cap with non-critical events.
   139	    for _ in range(QUEUE_CAPACITY):
   140	        await bus.emit(_progress())
   141	    assert bus.qsize() == QUEUE_CAPACITY
   142	
   143	    # One more non-critical event → it gets dropped, bus.dropped enqueued.
   144	    await bus.emit(_progress(message="will be dropped"))
   145	
   146	    # Queue size should be cap+1 now (the synthetic bus.dropped pushed
   147	    # above cap because synthetic events bypass it).
   148	    assert bus.qsize() == QUEUE_CAPACITY + 1
   149	
   150	    # Drain everything; the FIRST cap items are the original progress
   151	    # events; the LAST is bus.dropped — the dropping happened "newest
   152	    # first" per the impl.
   153	    drained = []
   154	    while bus.qsize() > 0:
   155	        drained.append(await bus.get())
   156	    kinds = [ev.event for ev in drained]
   157	    # All but the last should be node.progress; last must be bus.dropped.
   158	    assert kinds[:-1] == ["node.progress"] * QUEUE_CAPACITY
   159	    assert kinds[-1] == "bus.dropped"
   160	
   161	    # The bus.dropped should record the dropped kind.
   162	    assert drained[-1].dropped_kinds == ("node.progress",)
   163	    assert drained[-1].dropped_count == 1
   164	
   165	
   166	@pytest.mark.asyncio
   167	async def test_critical_events_bypass_cap():
   168	    """run.started / run.finished / handoff.required NEVER drop on overflow."""
   169	    bus = RunEventBus(run_id="RUN-A")
   170	    # Fill queue to cap with non-critical.
   171	    for _ in range(QUEUE_CAPACITY):
   172	        await bus.emit(_progress())
   173	    assert bus.qsize() == QUEUE_CAPACITY
   174	
   175	    # Critical event should enqueue and exceed cap (not drop, not block).
   176	    await asyncio.wait_for(bus.emit(_finished()), timeout=0.5)
   177	    assert bus.qsize() == QUEUE_CAPACITY + 1
   178	
   179	
   180	@pytest.mark.asyncio
   181	async def test_critical_event_seq_is_unique_when_bypassing_cap():
   182	    bus = RunEventBus(run_id="RUN-A")
   183	    for _ in range(QUEUE_CAPACITY):
   184	        await bus.emit(_progress())
   185	    await bus.emit(_finished())
   186	    await bus.emit(_started())  # also critical
   187	
   188	    # Drain everything; collect seqs for critical events.
   189	    seqs_by_kind: dict[str, list[int]] = {}
   190	    while bus.qsize() > 0:
   191	        ev = await bus.get()
   192	        seqs_by_kind.setdefault(ev.event, []).append(ev.seq)
   193	    assert len(seqs_by_kind["run.finished"]) == 1
   194	    assert len(seqs_by_kind["run.started"]) == 1
   195	    # Seqs are still strictly monotonic across critical-bypass.
   196	    finished_seq = seqs_by_kind["run.finished"][0]
   197	    started_seq = seqs_by_kind["run.started"][0]
   198	    assert finished_seq < started_seq  # finished was emitted first
   199	
   200	
   201	# ---------------------------------------------------------------------------
   202	# Ring buffer + replay
   203	# ---------------------------------------------------------------------------
   204	
   205	
   206	@pytest.mark.asyncio
   207	async def test_replay_since_zero_returns_all_buffered_events():
   208	    bus = RunEventBus(run_id="RUN-A")
   209	    await bus.emit(_started())
   210	    await bus.emit(_progress())
   211	    await bus.emit(_finished())
   212	
   213	    out = list(bus.replay_since(0))
   214	    assert [ev.event for ev in out] == ["run.started", "node.progress", "run.finished"]
   215	
   216	
   217	@pytest.mark.asyncio
   218	async def test_replay_since_filters_out_consumed_seqs():
   219	    bus = RunEventBus(run_id="RUN-A")
   220	    await bus.emit(_started())  # seq=1
   221	    await bus.emit(_progress())  # seq=2
   222	    await bus.emit(_finished())  # seq=3
   223	
   224	    out = list(bus.replay_since(2))
   225	    assert [ev.seq for ev in out] == [3]
   226	
   227	
   228	@pytest.mark.asyncio
   229	async def test_replay_returns_empty_when_caught_up():
   230	    bus = RunEventBus(run_id="RUN-A")
   231	    await bus.emit(_started())  # seq=1
   232	    out = list(bus.replay_since(1))
   233	    assert out == []
   234	
   235	
   236	@pytest.mark.asyncio
   237	async def test_ring_buffer_evicts_oldest_when_over_capacity():
   238	    bus = RunEventBus(run_id="RUN-A")
   239	    # Emit MORE than ring buffer capacity.
   240	    n = RING_BUFFER_CAPACITY + 50
   241	    for i in range(n):
   242	        await bus.emit(_progress(message=f"msg-{i}"))
   243	
   244	    # Ring should hold only the LAST RING_BUFFER_CAPACITY events.
   245	    out = list(bus.replay_since(0))
   246	    # First entry will be a synthetic bus.gap because seq=0+1=1 is older
   247	    # than the ring's tail (which starts at seq=51).
   248	    assert out[0].event == "bus.gap"
   249	    # The remaining events are the actual progress entries kept.
   250	    actual = [ev for ev in out if ev.event != "bus.gap"]
   251	    assert len(actual) == RING_BUFFER_CAPACITY
   252	    # Oldest kept seq is 51 (since first 50 evicted).
   253	    assert actual[0].seq == n - RING_BUFFER_CAPACITY + 1
   254	
   255	
   256	@pytest.mark.asyncio
   257	async def test_replay_emits_bus_gap_when_since_seq_below_buffer_tail():
   258	    bus = RunEventBus(run_id="RUN-A")
   259	    # Force eviction.
   260	    n = RING_BUFFER_CAPACITY + 100
   261	    for i in range(n):
   262	        await bus.emit(_progress(message=f"m{i}"))
   263	
   264	    out = list(bus.replay_since(0))
   265	    gap = out[0]
   266	    assert gap.event == "bus.gap"
   267	    assert gap.requested_since == 0
   268	    # buffer_tail is the seq of the oldest *retained* event.
   269	    assert gap.buffer_tail == n - RING_BUFFER_CAPACITY + 1
   270	
   271	
   272	@pytest.mark.asyncio
   273	async def test_replay_no_gap_when_since_seq_inside_buffer():
   274	    bus = RunEventBus(run_id="RUN-A")
   275	    for _ in range(RING_BUFFER_CAPACITY + 10):  # cause eviction
   276	        await bus.emit(_progress())
   277	
   278	    # Pick a seq that's still in the buffer.
   279	    in_buffer_seq = RING_BUFFER_CAPACITY  # safely past the eviction edge
   280	    out = list(bus.replay_since(in_buffer_seq))
   281	    kinds = [ev.event for ev in out]
   282	    assert "bus.gap" not in kinds
   283	
   284	
   285	@pytest.mark.asyncio
   286	async def test_replay_negative_since_seq_rejected():
   287	    bus = RunEventBus(run_id="RUN-A")
   288	    await bus.emit(_started())
   289	    with pytest.raises(ValueError, match="non-negative"):
   290	        list(bus.replay_since(-1))
   291	
   292	
   293	@pytest.mark.asyncio
   294	async def test_replay_on_empty_bus_returns_empty_iterable():
   295	    bus = RunEventBus(run_id="RUN-A")
   296	    out = list(bus.replay_since(0))
   297	    assert out == []
   298	
   299	
   300	# ---------------------------------------------------------------------------
   301	# Lifecycle
   302	# ---------------------------------------------------------------------------
   303	
   304	
   305	@pytest.mark.asyncio
   306	async def test_close_blocks_subsequent_emits():
   307	    bus = RunEventBus(run_id="RUN-A")
   308	    await bus.emit(_started())
   309	    bus.close()
   310	    assert bus.is_closed is True
   311	    with pytest.raises(RuntimeError, match="closed"):
   312	        await bus.emit(_progress())
   313	
   314	
   315	@pytest.mark.asyncio
   316	async def test_close_does_not_break_in_flight_drain():
   317	    bus = RunEventBus(run_id="RUN-A")
   318	    await bus.emit(_started())
   319	    await bus.emit(_progress())
   320	    bus.close()
   321	    # Already-enqueued events still drain.
   322	    a = await bus.get()
   323	    b = await bus.get()
   324	    assert {a.event, b.event} == {"run.started", "node.progress"}
   325	
   326	
   327	@pytest.mark.asyncio
   328	async def test_next_seq_property_advances():
   329	    bus = RunEventBus(run_id="RUN-A")
   330	    assert bus.next_seq == 1
   331	    await bus.emit(_started())
   332	    assert bus.next_seq == 2
   333	    await bus.emit(_progress())
   334	    assert bus.next_seq == 3
   335	
   336	
   337	# ---------------------------------------------------------------------------
   338	# Concurrency: many producers, one consumer
   339	# ---------------------------------------------------------------------------
   340	
   341	
   342	@pytest.mark.asyncio
   343	async def test_many_producers_one_consumer_preserves_total_count():
   344	    bus = RunEventBus(run_id="RUN-A")
   345	    n_producers = 8
   346	    per_producer = 50
   347	
   348	    async def produce(idx: int):
   349	        for j in range(per_producer):
   350	            await bus.emit(_progress(message=f"p{idx}-{j}"))
   351	
   352	    consumed: list = []
   353	
   354	    async def consume(target: int):
   355	        for _ in range(target):
   356	            consumed.append(await bus.get())
   357	
   358	    target = n_producers * per_producer
   359	    consumer_task = asyncio.create_task(consume(target))
   360	    await asyncio.gather(*(produce(i) for i in range(n_producers)))
   361	    await asyncio.wait_for(consumer_task, timeout=5.0)
   362	
   363	    assert len(consumed) == target
   364	    # All seqs are unique and form 1..target.
   365	    seqs = sorted(ev.seq for ev in consumed)
   366	    assert seqs == list(range(1, target + 1))
   367	
   368	
   369	@pytest.mark.asyncio
   370	async def test_isolation_between_distinct_runs():
   371	    """Distinct run_ids own distinct seq counters and queues."""
   372	    a = RunEventBus(run_id="RUN-A")
   373	    b = RunEventBus(run_id="RUN-B")
   374	    await a.emit(_started(run_id="RUN-A"))
   375	    await b.emit(_started(run_id="RUN-B"))
   376	    await b.emit(_progress(run_id="RUN-B"))
   377	    assert a.qsize() == 1
   378	    assert b.qsize() == 2
   379	    assert a.next_seq == 2
   380	    assert b.next_seq == 3

exec
/bin/zsh -lc "git show pr-55:tests/test_runtime_event_bus.py | nl -ba | sed -n '420,520p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
exec
/bin/zsh -lc "nl -ba agents/architect.py | sed -n '1,280p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
exec
/bin/zsh -lc "nl -ba schemas/sim_plan.py | sed -n '1,320p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
     1	"""Architect Agent — produces a canonical SimPlan from a natural-language spec."""
     2	
     3	from __future__ import annotations
     4	
     5	import hashlib
     6	import logging
     7	import re
     8	from pathlib import Path
     9	from typing import Any
    10	
    11	from schemas.sim_plan import SimPlan
    12	from schemas.sim_state import FaultClass, SimState
    13	
    14	logger = logging.getLogger(__name__)
    15	
    16	PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "architect_golden_prompt.md"
    17	CASE_ID_PATTERN = re.compile(r"^AI-FEA-P\d+-\d+$")
    18	
    19	
    20	def _load_prompt_template() -> str:
    21	    """Load the golden architect prompt from the repository."""
    22	    return PROMPT_PATH.read_text(encoding="utf-8")
    23	
    24	
    25	def _build_prompt(user_request: str) -> str:
    26	    template = _load_prompt_template()
    27	    return template.replace("{{USER_REQUEST}}", user_request)
    28	
    29	
    30	def _valid_case_id(candidate: str | None) -> bool:
    31	    return bool(candidate and CASE_ID_PATTERN.fullmatch(candidate))
    32	
    33	
    34	def _canonical_case_id(user_request: str, existing_case_id: str | None = None) -> str:
    35	    """Return a deterministic, naming-compliant fallback case id."""
    36	    if _valid_case_id(existing_case_id):
    37	        return str(existing_case_id)
    38	
    39	    digest = hashlib.sha1(user_request.encode("utf-8")).hexdigest()
    40	    suffix = (int(digest[:4], 16) % 90) + 10
    41	    return f"AI-FEA-P0-{suffix:02d}"
    42	
    43	
    44	def _extract_structured_data(**kwargs: Any) -> SimPlan | None:
    45	    """Import the LLM helper lazily so schema tests do not require runtime deps."""
    46	    from agents.llm import extract_structured_data
    47	
    48	    return extract_structured_data(**kwargs)
    49	
    50	
    51	def run(state: SimState) -> dict[str, Any]:
    52	    """Architect agent entrypoint (LangGraph node signature)."""
    53	    logger.info("Architect Agent invoked.")
    54	
    55	    user_request = state.get("user_request")
    56	    if not user_request:
    57	        logger.warning("No user_request found in state.")
    58	        return {"fault_class": FaultClass.UNKNOWN}
    59	
    60	    try:
    61	        plan = _extract_structured_data(
    62	            prompt=_build_prompt(user_request),
    63	            response_model=SimPlan,
    64	            system_message="You are a professional FEA Architect.",
    65	        )
    66	    except Exception as exc:
    67	        logger.error("LLM extraction failed: %s", exc)
    68	        return {
    69	            "fault_class": FaultClass.UNKNOWN,
    70	            "history": [{"node": "architect", "fault": "logic_error", "msg": str(exc)}],
    71	        }
    72	
    73	    if not plan:
    74	        logger.error("Architect failed to produce a valid SimPlan.")
    75	        return {
    76	            "fault_class": FaultClass.UNKNOWN,
    77	            "history": [
    78	                {"node": "architect", "fault": "parsing_failed", "msg": "LLM returned null"}
    79	            ],
    80	        }
    81	
    82	    plan.case_id = _canonical_case_id(
    83	        user_request=user_request,
    84	        existing_case_id=state.get("case_id") or plan.case_id,
    85	    )
    86	
    87	    logger.info("Architect produced SimPlan: %s", plan.case_id)
    88	    return {"plan": plan, "fault_class": FaultClass.NONE}

 succeeded in 0ms:
     1	"""Canonical SimPlan contract with backward-compatible accessors.
     2	
     3	PRD v0.2 names the top-level contract as:
     4	``case_id / physics / geometry / material / bcs / loads / sweep /
     5	objectives / solver / reference``.
     6	
     7	The rest of the stack was initially built against a pre-PRD draft with names
     8	like ``analysis_type`` and ``boundary_conditions``.  To let P0-04 land
     9	cleanly without breaking P0-05..P0-08, this module accepts both shapes and
    10	exposes lightweight compatibility properties for the older call sites.
    11	"""
    12	
    13	from __future__ import annotations
    14	
    15	from enum import StrEnum
    16	from typing import Any
    17	
    18	from pydantic import BaseModel, Field, model_validator
    19	
    20	
    21	class AnalysisType(StrEnum):
    22	    """Supported analysis types (PRD v0.2)."""
    23	
    24	    STATIC = "static"
    25	    MODAL = "modal"
    26	    PRESTRESS_MODAL = "prestress_modal"
    27	    CYCLIC_SYMMETRY = "cyclic_symmetry"
    28	    STEADY_THERMAL = "steady_thermal"
    29	    THERMO_STRUCTURAL = "thermo_structural"
    30	
    31	
    32	class SolverBackend(StrEnum):
    33	    """Available solver backends."""
    34	
    35	    CALCULIX = "calculix"
    36	    FENICS = "fenics"
    37	
    38	
    39	class ElementOrder(StrEnum):
    40	    """Finite-element polynomial order."""
    41	
    42	    LINEAR = "linear"
    43	    QUADRATIC = "quadratic"
    44	
    45	
    46	class MeshLevel(StrEnum):
    47	    """Named mesh density presets for the Mesh Agent."""
    48	
    49	    COARSE = "coarse"
    50	    MEDIUM = "medium"
    51	    FINE = "fine"
    52	    VERY_FINE = "very_fine"
    53	
    54	
    55	def _coerce_model_dict(raw: Any) -> dict[str, Any]:
    56	    if raw is None:
    57	        return {}
    58	    if isinstance(raw, BaseModel):
    59	        return raw.model_dump()
    60	    return dict(raw)
    61	
    62	
    63	def _compat_geometry_kind(ref: str | None, params: dict[str, Any]) -> str:
    64	    ref_value = (ref or "").strip().lower()
    65	    profile = str(params.get("profile", "")).strip().lower()
    66	    if "naca" in ref_value or profile.startswith("naca"):
    67	        return "naca"
    68	    if ref_value:
    69	        return ref_value
    70	    return "custom"
    71	
    72	
    73	class PhysicsSpec(BaseModel):
    74	    """High-level physics requested by the PRD contract."""
    75	
    76	    type: AnalysisType = AnalysisType.STATIC
    77	    nonlinear: bool = False
    78	
    79	
    80	class GeometrySpec(BaseModel):
    81	    """Canonical geometry definition used by the Geometry Agent."""
    82	
    83	    mode: str = Field(
    84	        default="knowledge",
    85	        description="How geometry is resolved, e.g. knowledge / parametric / import.",
    86	    )
    87	    ref: str = Field(
    88	        default="naca",
    89	        description="Canonical geometry family or external reference identifier.",
    90	    )
    91	    params: dict[str, Any] = Field(default_factory=dict, description="Geometry parameters.")
    92	
    93	    @model_validator(mode="before")
    94	    @classmethod
    95	    def _upgrade_legacy_shape(cls, raw: Any) -> Any:
    96	        data = _coerce_model_dict(raw)
    97	        if not data:
    98	            return data
    99	        if "kind" in data and "ref" not in data:
   100	            data["ref"] = data.pop("kind")
   101	        if "parameters" in data and "params" not in data:
   102	            data["params"] = data.pop("parameters")
   103	        data.setdefault("mode", "knowledge")
   104	        return data
   105	
   106	    @property
   107	    def kind(self) -> str:
   108	        """Compatibility alias for pre-PRD call sites."""
   109	        return _compat_geometry_kind(self.ref, self.params)
   110	
   111	    @property
   112	    def parameters(self) -> dict[str, Any]:
   113	        """Compatibility alias for pre-PRD call sites."""
   114	        return self.params
   115	
   116	
   117	class MaterialSpec(BaseModel):
   118	    """Isotropic linear-elastic material."""
   119	
   120	    name: str = "Aluminum 7075"
   121	    youngs_modulus_pa: float = Field(71.7e9, description="Young's modulus [Pa]")
   122	    poissons_ratio: float = Field(0.33, ge=0.0, le=0.5)
   123	    density_kg_m3: float = Field(2810.0, description="Density [kg/m^3]")
   124	    thermal_conductivity: float | None = Field(None, description="[W/m*K]")
   125	    specific_heat: float | None = Field(None, description="[J/kg*K]")
   126	
   127	
   128	class LoadSpec(BaseModel):
   129	    """A single load definition in canonical PRD form."""
   130	
   131	    semantic: str = Field(default="tip_load", description="User-facing load label.")
   132	    kind: str = Field(default="concentrated_force")
   133	    target: str | None = Field(default="Ntip")
   134	    magnitude: float | None = Field(default=None, description="Scalar magnitude of the load.")
   135	    direction: str | None = Field(default=None, description="Direction label such as -Z.")
   136	    unit: str = Field(default="N")
   137	    components: dict[str, float] = Field(default_factory=dict)
   138	    parameters: dict[str, Any] = Field(
   139	        default_factory=dict,
   140	        description="Legacy compatibility map.",
   141	    )
   142	
   143	    @model_validator(mode="before")
   144	    @classmethod
   145	    def _upgrade_legacy_shape(cls, raw: Any) -> Any:
   146	        data = _coerce_model_dict(raw)
   147	        if not data:
   148	            return data
   149	
   150	        params = dict(data.get("parameters") or {})
   151	        if params:
   152	            data.setdefault("target", params.get("node_set") or params.get("target"))
   153	            data.setdefault("magnitude", params.get("magnitude"))
   154	            data.setdefault("direction", params.get("direction"))
   155	            components = dict(data.get("components") or {})
   156	            for axis in ("fx", "fy", "fz"):
   157	                if axis in params and axis not in components:
   158	                    components[axis] = float(params[axis])
   159	            if components:
   160	                data["components"] = components
   161	        return data
   162	
   163	    @model_validator(mode="after")
   164	    def _hydrate_legacy_parameters(self) -> LoadSpec:
   165	        params = dict(self.parameters)
   166	        if self.target is not None:
   167	            params.setdefault("node_set", self.target)
   168	            params.setdefault("target", self.target)
   169	        if self.magnitude is not None:
   170	            params.setdefault("magnitude", self.magnitude)
   171	        if self.direction:
   172	            params.setdefault("direction", self.direction)
   173	        for axis, value in self.components.items():
   174	            params.setdefault(axis, value)
   175	        self.parameters = params
   176	        return self
   177	
   178	
   179	class BCSpec(BaseModel):
   180	    """A single boundary-condition definition in canonical PRD form."""
   181	
   182	    semantic: str = Field(default="fixed_base")
   183	    kind: str = Field(default="fixed")
   184	    target: str | None = Field(default="Nroot")
   185	    constraints: dict[str, Any] = Field(default_factory=dict)
   186	    parameters: dict[str, Any] = Field(
   187	        default_factory=dict,
   188	        description="Legacy compatibility map.",
   189	    )
   190	
   191	    @model_validator(mode="before")
   192	    @classmethod
   193	    def _upgrade_legacy_shape(cls, raw: Any) -> Any:
   194	        data = _coerce_model_dict(raw)
   195	        if not data:
   196	            return data
   197	
   198	        params = dict(data.get("parameters") or {})
   199	        if params:
   200	            data.setdefault("target", params.get("node_set") or params.get("target"))
   201	            if "constraints" not in data and "dofs" in params:
   202	                data["constraints"] = {"dofs": params["dofs"]}
   203	        return data
   204	
   205	    @model_validator(mode="after")
   206	    def _hydrate_legacy_parameters(self) -> BCSpec:
   207	        params = dict(self.parameters)
   208	        if self.target is not None:
   209	            params.setdefault("node_set", self.target)
   210	            params.setdefault("target", self.target)
   211	        if self.constraints:
   212	            params.setdefault("constraints", self.constraints)
   213	        self.parameters = params
   214	        return self
   215	
   216	
   217	class SweepSpec(BaseModel):
   218	    """Optional parameter sweep instructions."""
   219	
   220	    enabled: bool = False
   221	    parameters: list[dict[str, Any]] = Field(default_factory=list)
   222	
   223	
   224	class ObjectiveSpec(BaseModel):
   225	    """Requested result outputs and success metrics."""
   226	
   227	    metrics: list[str] = Field(
   228	        default_factory=lambda: ["max_displacement", "max_von_mises"],
   229	        description="Quantities the report should surface.",
   230	    )
   231	    export_vtp: bool = True
   232	    narrative_report: bool = True
   233	
   234	    @model_validator(mode="before")
   235	    @classmethod
   236	    def _upgrade_legacy_post_spec(cls, raw: Any) -> Any:
   237	        data = _coerce_model_dict(raw)
   238	        if not data:
   239	            return data
   240	        if "fields" in data and "metrics" not in data:
   241	            data["metrics"] = data.pop("fields")
   242	        if "generate_report" in data and "narrative_report" not in data:
   243	            data["narrative_report"] = data.pop("generate_report")
   244	        return data
   245	
   246	
   247	class MeshStrategy(BaseModel):
   248	    """Meshing parameters for the Mesh Agent."""
   249	
   250	    element_order: ElementOrder = ElementOrder.QUADRATIC
   251	    mesh_level: MeshLevel = MeshLevel.MEDIUM
   252	    global_size: float | None = Field(None, description="Global element size [m]")
   253	    refinement_regions: list[dict[str, Any]] = Field(default_factory=list)
   254	    min_scaled_jacobian: float = Field(0.2, gt=0.0, description="Scaled Jacobian threshold")
   255	    max_aspect_ratio: float = Field(10.0, gt=1.0, description="Aspect ratio threshold")
   256	    thin_wall_threshold_m: float = Field(
   257	        5e-4,
   258	        gt=0.0,
   259	        description="Minimum feature size below which thin-wall refinement is forced",
   260	    )
   261	
   262	
   263	class SolverControls(BaseModel):
   264	    """Solver-specific knobs in canonical PRD form."""
   265	
   266	    name: SolverBackend = SolverBackend.CALCULIX
   267	    version: str = "2.21"
   268	    nonlinear: bool = False
   269	    num_modes: int | None = Field(default=None, description="Number of modes for modal analyses.")
   270	    max_increments: int = 100
   271	
   272	    @model_validator(mode="before")
   273	    @classmethod
   274	    def _upgrade_legacy_shape(cls, raw: Any) -> Any:
   275	        data = _coerce_model_dict(raw)
   276	        if not data:
   277	            return data
   278	        if "backend" in data and "name" not in data:
   279	            data["name"] = data.pop("backend")
   280	        return data
   281	
   282	    @property
   283	    def backend(self) -> SolverBackend:
   284	        """Compatibility alias for pre-PRD call sites."""
   285	        return self.name
   286	
   287	
   288	class ReferenceSpec(BaseModel):
   289	    """Reference values used by the reviewer gate."""
   290	
   291	    type: str = Field(default="analytical")
   292	    value: dict[str, float] = Field(default_factory=dict)
   293	    tol_pct: float = Field(default=5.0, ge=0.0, description="Approval tolerance in percent.")
   294	
   295	
   296	class SimPlan(BaseModel):
   297	    """Master simulation plan produced by the Architect Agent."""
   298	
   299	    case_id: str = Field(
   300	        ..., pattern=r"^AI-FEA-P\d+-\d+$", description="Case ID per naming convention."
   301	    )
   302	    physics: PhysicsSpec = Field(default_factory=PhysicsSpec)
   303	    geometry: GeometrySpec
   304	    material: MaterialSpec = Field(default_factory=MaterialSpec)
   305	    bcs: list[BCSpec] = Field(default_factory=list)
   306	    loads: list[LoadSpec] = Field(default_factory=list)
   307	    sweep: SweepSpec = Field(default_factory=SweepSpec)
   308	    objectives: ObjectiveSpec = Field(default_factory=ObjectiveSpec)
   309	    solver: SolverControls = Field(default_factory=SolverControls)
   310	    reference: ReferenceSpec = Field(default_factory=ReferenceSpec)
   311	    mesh: MeshStrategy = Field(default_factory=MeshStrategy)
   312	    description: str = ""
   313	
   314	    @model_validator(mode="before")
   315	    @classmethod
   316	    def _upgrade_legacy_shape(cls, raw: Any) -> Any:
   317	        data = _coerce_model_dict(raw)
   318	        if not data:
   319	            return data
   320	

exec
/bin/zsh -lc "nl -ba agents/router.py | sed -n '1,220p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
     1	from __future__ import annotations
     2	
     3	from schemas.sim_state import FaultClass, SimState
     4	
     5	# ADR-004 Fault to Node Mapping
     6	FAULT_TO_NODE: dict[FaultClass, str] = {
     7	    FaultClass.GEOMETRY_INVALID: "geometry",
     8	    FaultClass.MESH_JACOBIAN: "mesh",
     9	    FaultClass.MESH_RESOLUTION: "mesh",
    10	    FaultClass.SOLVER_CONVERGENCE: "solver",
    11	    FaultClass.SOLVER_TIMESTEP: "solver",
    12	    FaultClass.SOLVER_SYNTAX: "solver",
    13	    FaultClass.REFERENCE_MISMATCH: "architect",
    14	    FaultClass.UNKNOWN: "human_fallback",
    15	    # If re-run is requested without a fault_class, treat it as unknown.
    16	    FaultClass.NONE: "human_fallback",
    17	}
    18	
    19	MAX_RETRIES = 3
    20	
    21	
    22	def _normalize_verdict(verdict: str | None) -> str:
    23	    """Normalize reviewer verdict labels to routing tokens."""
    24	    if not verdict:
    25	        return ""
    26	
    27	    normalized = verdict.strip().lower().replace("_", " ").replace("-", " ")
    28	    normalized = " ".join(normalized.split())
    29	    if normalized in {"accept", "accept with note"}:
    30	        return "accept"
    31	    if normalized == "re run":
    32	        return "re-run"
    33	    if normalized in {"needs review", "reject"}:
    34	        return normalized
    35	    return normalized
    36	
    37	
    38	def route_reviewer(state: SimState) -> str:
    39	    """Determine the next node after reviewer validation."""
    40	    verdict = _normalize_verdict(state.get("verdict"))
    41	    fault_class = state.get("fault_class", FaultClass.NONE)
    42	    budgets = state.get("retry_budgets", {})
    43	
    44	    if verdict == "accept":
    45	        return "viz"
    46	
    47	    if verdict == "re-run":
    48	        target_node = FAULT_TO_NODE.get(fault_class, "human_fallback")
    49	
    50	        # Check if the target node exceeds retry budget
    51	        current_retries = budgets.get(target_node, 0)
    52	
    53	        if current_retries >= MAX_RETRIES:
    54	            return "human_fallback"
    55	
    56	        return target_node
    57	
    58	    return "human_fallback"

exec
/bin/zsh -lc "nl -ba schemas/sim_state.py | sed -n '1,220p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
     1	from __future__ import annotations
     2	
     3	from enum import StrEnum
     4	from typing import Annotated, Any, TypedDict
     5	
     6	from schemas.sim_plan import SimPlan
     7	
     8	
     9	class FaultClass(StrEnum):
    10	    """Fault classifications as defined in ADR-004."""
    11	
    12	    GEOMETRY_INVALID = "geometry_invalid"
    13	    MESH_JACOBIAN = "mesh_jacobian"
    14	    MESH_RESOLUTION = "mesh_resolution"
    15	    SOLVER_CONVERGENCE = "solver_convergence"
    16	    SOLVER_TIMESTEP = "solver_timestep"
    17	    SOLVER_SYNTAX = "solver_syntax"
    18	    REFERENCE_MISMATCH = "reference_mismatch"
    19	    UNKNOWN = "unknown"
    20	    NONE = "none"  # Used when there is no fault
    21	
    22	
    23	def update_retry_budget(current: dict[str, int], update: dict[str, int]) -> dict[str, int]:
    24	    """Reducer for updating independent retry counters per node."""
    25	    res = dict(current)
    26	    for k, v in update.items():
    27	        res[k] = res.get(k, 0) + v
    28	    return res
    29	
    30	
    31	def append_history(
    32	    current: list[dict[str, Any]], update: list[dict[str, Any]]
    33	) -> list[dict[str, Any]]:
    34	    """Reducer for appending to retry history."""
    35	    return current + update
    36	
    37	
    38	class SimState(TypedDict):
    39	    """LangGraph global state for AI-FEA engine."""
    40	
    41	    # 1. Inputs
    42	    user_request: str  # Original natural language request
    43	    case_id: str
    44	    run_id: str
    45	    plan: SimPlan
    46	
    47	    # 2. Intermediate Artifacts
    48	    project_state_dir: str
    49	    artifacts: list[str]
    50	    geometry_path: str | None
    51	    mesh_path: str | None
    52	    frd_path: str | None
    53	    solve_path: str | None
    54	    solve_metadata: dict[str, Any]
    55	
    56	    # 3. Validation and Fault Routing
    57	    verdict: str | None
    58	    fault_class: FaultClass
    59	
    60	    # 4. Independent Retry Budgets (e.g., {"solver": 1}, max 3 per node)
    61	    retry_budgets: Annotated[dict[str, int], update_retry_budget]
    62	
    63	    # 5. Fault History
    64	    history: Annotated[list[dict[str, Any]], append_history]
    65	
    66	    # 6. Outputs
    67	    reports: dict[str, str] | None
    68	
    69	    # 7. Execution provenance (ADR-008 N-3: honest reporting of replay / dummy geometry)
    70	    execution_mode: dict[str, Any]

codex
The stacked implementation branches surfaced two concrete logic bugs already: one in the draft/edit HMAC flow and one in the event-bus drop path. I’m running a couple of tiny AST/python repros now to confirm the review findings around import-rule bypasses before I finalize verdicts.
exec
/bin/zsh -lc "python - <<'PY'
import ast
samples = {
    'from_schemas_import_sim_state': 'from schemas import sim_state\\n',
    'from_dot_import_query_cli': 'from . import query_cli\\n',
    'from_dot_import_kb': 'from . import kb\\n',
}
for name, src in samples.items():
    node = ast.parse(src).body[0]
    print(name, type(node).__name__, 'module=', getattr(node, 'module', None), 'names=', [a.name for a in getattr(node,'names',[])], 'level=', getattr(node,'level',None))
PY" in /Users/Zhuanz/20260408 AI StructureAnalysis
 exited 127 in 0ms:
zsh:1: command not found: python

exec
/bin/zsh -lc "python - <<'PY'
from enum import StrEnum
class X(StrEnum):
    A='a'
print(str(X.A), repr(str(X.A)))
PY" in /Users/Zhuanz/20260408 AI StructureAnalysis
 exited 127 in 0ms:
zsh:1: command not found: python

exec
/bin/zsh -lc "python3 - <<'PY'
from enum import StrEnum
class X(StrEnum):
    A='a'
print(str(X.A), repr(str(X.A)))
PY" in /Users/Zhuanz/20260408 AI StructureAnalysis
 exited 1 in 0ms:
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
ImportError: cannot import name 'StrEnum' from 'enum' (/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/enum.py)

exec
/bin/zsh -lc "python3 - <<'PY'
import ast
samples = {
    'from_schemas_import_sim_state': 'from schemas import sim_state\\n',
    'from_dot_import_query_cli': 'from . import query_cli\\n',
    'from_dot_import_kb': 'from . import kb\\n',
}
for name, src in samples.items():
    node = ast.parse(src).body[0]
    print(name, type(node).__name__, 'module=', getattr(node, 'module', None), 'names=', [a.name for a in getattr(node,'names',[])], 'level=', getattr(node,'level',None))
PY" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
from_schemas_import_sim_state ImportFrom module= schemas names= ['sim_state'] level= 0
from_dot_import_query_cli ImportFrom module= None names= ['query_cli'] level= 1
from_dot_import_kb ImportFrom module= None names= ['kb'] level= 1

exec
/bin/zsh -lc "rg -n \"python.?3\\.(9|10|11)|StrEnum|requires-python|actions/setup-python|matrix:\" -S pyproject.toml requirements* .github/workflows tests | sed -n '1,220p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
zsh:1: no matches found: requirements*

exec
/bin/zsh -lc 'ls -la .github/workflows && for f in .github/workflows/*.yml .github/workflows/*.yaml; do [ -f "$f" ] && echo "=== $f ===" && sed -n '"'1,220p' \""'$f"; done' in /Users/Zhuanz/20260408 AI StructureAnalysis
 exited 1 in 0ms:
total 24
drwxr-xr-x@ 5 Zhuanz  staff   160 Apr 26 03:01 .
drwxr-xr-x@ 4 Zhuanz  staff   128 Apr 26 03:01 ..
-rw-r--r--@ 1 Zhuanz  staff  3789 Apr 26 03:01 calibration-cap-check.yml
-rw-r--r--@ 1 Zhuanz  staff   782 Apr 25 19:45 ci.yml
-rw-r--r--  1 Zhuanz  staff  1621 Apr 18 16:50 docker-base.yml
zsh:1: no matches found: .github/workflows/*.yaml

exec
/bin/zsh -lc 'for f in pyproject.toml .github/workflows/ci.yml .github/workflows/calibration-cap-check.yml; do if [ -f "$f" ]; then echo "=== $f ==="; sed -n '"'1,240p' \""'$f"; fi; done' in /Users/Zhuanz/20260408 AI StructureAnalysis
exec
/bin/zsh -lc "rg -n \"StrEnum|requires-python|python-version|3\\.11|3\\.9\" -S pyproject.toml .github/workflows tests agents backend schemas | sed -n '1,260p'" in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
pyproject.toml:10:requires-python = ">=3.11"
pyproject.toml:21:    "Programming Language :: Python :: 3.11",
pyproject.toml:92:python_version = "3.11"
schemas/sim_state.py:3:from enum import StrEnum
schemas/sim_state.py:9:class FaultClass(StrEnum):
.github/workflows/ci.yml:17:        python-version: ["3.11"]
.github/workflows/ci.yml:22:      - name: Set up Python ${{ matrix.python-version }}
.github/workflows/ci.yml:25:          python-version: ${{ matrix.python-version }}
.github/workflows/calibration-cap-check.yml:45:      - name: Set up Python 3.11
.github/workflows/calibration-cap-check.yml:48:          python-version: "3.11"
schemas/sim_plan.py:15:from enum import StrEnum
schemas/sim_plan.py:21:class AnalysisType(StrEnum):
schemas/sim_plan.py:32:class SolverBackend(StrEnum):
schemas/sim_plan.py:39:class ElementOrder(StrEnum):
schemas/sim_plan.py:46:class MeshLevel(StrEnum):
tests/test_hf1_path_guard.py:19:    # (importlib.util.spec_from_file_location triggers a Python 3.9
tests/test_hf1_path_guard.py:20:    # dataclasses bug otherwise; CI is 3.11 but local dev may be 3.9).

 succeeded in 0ms:
=== pyproject.toml ===
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "ai-structure-fea"
version = "0.2.0"
description = "AI-driven Finite Element Analysis engine with multi-agent orchestration"
readme = "README.md"
requires-python = ">=3.11"
license = {text = "MIT"}
authors = [
    {name = "Structure Analysis Team"}
]
keywords = ["fea", "structural-analysis", "ai", "calculix", "multi-agent", "langgraph"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Scientific/Engineering",
]
dependencies = [
    "pydantic>=2.0",
    "jinja2>=3.1",
    "numpy>=1.24",
    "pyyaml>=6.0",
    "httpx>=0.25",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "ruff>=0.8",
]
agents = [
    "langgraph>=0.2",
    "langgraph-checkpoint-sqlite>=2.0",
]
solvers = [
    "meshio>=5.3",
    "gmsh>=4.11",
]
viz = [
    "pyvista>=0.42",
    "matplotlib>=3.7",
]

[project.urls]
Homepage = "https://github.com/kogamishinyajerry-ops/ai-structure-analysis"
Repository = "https://github.com/kogamishinyajerry-ops/ai-structure-analysis"
"Notion Control Hub" = "https://www.notion.so/AI-StructureAnalysis-345c68942bed80f6a092c9c2b3d3f5b9"

[project.scripts]
run-well-harness = "app.well_harness.cli:main"

[tool.setuptools.packages.find]
where = ["."]
include = [
    "agents*",
    "tools*",
    "schemas*",
    "checkers*",
    "reporters*",
    "backend*",
]

[tool.ruff]
target-version = "py311"
line-length = 100
exclude = [
    "backend/",
    "golden_samples/",
    "calculix_cases/",
    "frontend/",
    "scripts/",
    "run_well_harness.py",
    "sync_well_harness_approvals.py",
    ".venv/",
]

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B", "SIM"]

[tool.ruff.format]
quote-style = "double"

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
=== .github/workflows/ci.yml ===
name: CI

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev,agents]"

      - name: Lint — ruff check
        run: ruff check .

      - name: Lint — ruff format check
        run: ruff format --check .

      - name: Test — pytest
        run: pytest tests/ -v --tb=short
=== .github/workflows/calibration-cap-check.yml ===
name: Calibration Cap Check

# ADR-013 enforcement workflow. Validates that every PR's
# "Self-pass-rate" claim does not exceed the mechanical ceiling
# computed by scripts/compute_calibration_cap.py from
# reports/calibration_state.json.
#
# Runs only on pull_request events (no value on push to main).
#
# R2 hardening (post Codex R1, 2026-04-26):
#   * The validator scripts AND the calibration_state.json are loaded
#     from a separate `actions/checkout` of `main`, NOT from the PR's
#     own checkout. This closes the self-bypass hole Codex reproduced
#     where a PR could modify scripts/compute_calibration_cap.py,
#     scripts/extract_pr_self_pass_rate.py, or
#     reports/calibration_state.json to make the check pass.
#   * The PR body itself comes from the GitHub API event payload, not
#     from any file in the PR's checkout, so it remains the legitimate
#     untrusted input.

on:
  pull_request:
    branches: [main]
    types: [opened, edited, synchronize, reopened]

permissions:
  contents: read
  pull-requests: read

jobs:
  calibration-cap-check:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout main (trusted validators + state)
        # The PR is intentionally NOT checked out for the validator
        # scripts. Only main's view of compute_calibration_cap.py,
        # extract_pr_self_pass_rate.py, and reports/calibration_state.json
        # is trusted. A PR can change those files in its own working
        # tree but the check here ignores those changes.
        uses: actions/checkout@v4
        with:
          ref: main
          path: trusted

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Compute current ceiling (from trusted main)
        id: ceiling
        working-directory: trusted
        run: |
          set -euo pipefail
          OUTPUT=$(python3 scripts/compute_calibration_cap.py)
          CEILING=$(echo "$OUTPUT" | python3 -c "import json,sys;print(json.load(sys.stdin)['ceiling'])")
          GATE=$(echo "$OUTPUT" | python3 -c "import json,sys;print(json.load(sys.stdin)['gate_label'])")
          BLOCKING=$(echo "$OUTPUT" | python3 -c "import json,sys;print(json.load(sys.stdin)['blocking'])")
          echo "ceiling=$CEILING" >> "$GITHUB_OUTPUT"
          echo "gate=$GATE" >> "$GITHUB_OUTPUT"
          echo "blocking=$BLOCKING" >> "$GITHUB_OUTPUT"
          echo "Current ceiling: ${CEILING}%, gate: ${GATE}, blocking: ${BLOCKING} (computed from trusted/main)"

      - name: Extract Self-pass-rate claim from PR body (trusted extractor)
        id: claim
        working-directory: trusted
        env:
          PR_BODY: ${{ github.event.pull_request.body }}
        run: |
          set -euo pipefail
          if [[ -z "${PR_BODY:-}" ]]; then
            echo "::error::PR body is empty. ADR-013 requires a 'Self-pass-rate' section."
            exit 1
          fi
          # Use main's extractor — not the PR's. PR body comes from the
          # event payload (already untrusted; that's the point — its claim
          # must be checked against the trusted ceiling).
          CLAIM=$(printf '%s' "$PR_BODY" | python3 scripts/extract_pr_self_pass_rate.py)
          echo "claim=$CLAIM" >> "$GITHUB_OUTPUT"
          echo "Claim parsed from PR body: ${CLAIM}% (extractor from trusted/main)"

      - name: Validate claim does not exceed ceiling (from trusted main)
        working-directory: trusted
        run: |
          set -euo pipefail
          python3 scripts/compute_calibration_cap.py --check "${{ steps.claim.outputs.claim }}"
          echo "::notice::Claim ${{ steps.claim.outputs.claim }}% does not exceed ceiling ${{ steps.ceiling.outputs.ceiling }}% (gate: ${{ steps.ceiling.outputs.gate }})"

exec
/bin/zsh -lc 'command -v python3.11 || true; command -v python3.12 || true' in /Users/Zhuanz/20260408 AI StructureAnalysis
 succeeded in 0ms:
/Users/Zhuanz/.local/bin/python3.11
/opt/homebrew/bin/python3.12

Fetched all six PRs, inspected the touched files on each PR head, and confirmed the main review findings. I’m consolidating them into per-PR verdicts now.
  ✓ Fetch PR metadata, diffs, and head refs for PRs 50-55
  ✓ Inspect changed files and tests for each PR, focusing on contract holes and regression risks
  → Produce terse per-PR verdicts with severity-ordered findings and exact file:line citations
  ✓ Fetch PR metadata, diffs, and head refs for PRs 50-55
  ✓ Inspect changed files and tests for each PR, focusing on contract holes and regression risks
  ✓ Produce terse per-PR verdicts with severity-ordered findings and exact file:line citations
codex
Reviewed via `gh pr view`, `gh pr diff`, and direct file reads from the fetched PR heads.

**PR #50 [ADR-014 — WS event bus contract]**
- `VERDICT: APPROVE_WITH_NITS`
- `HIGH findings: none`
- `MEDIUM findings: schemas/ws_events.py:58,64 advertise ISO-8601 UTC timestamps but enforce only bare str, so the wire contract is weaker than the ADR says.`
- `MEDIUM findings: schemas/ws_events.py:103-104 let top_k_titles and scores diverge in length, so title<->score pairing is not actually guaranteed by the schema.`
- `LOW/NITS: schemas/ws_events.py:40 misstates the digest length; docs/adr/ADR-014-ws-event-bus-for-workbench.md:141 and :149 contradict each other on 50% vs 30% self-pass-rate.`
- `Notes on any new regressions: none in this PR itself.`

**PR #51 [ADR-015 — workbench → agent RPC boundary]**
- `VERDICT: CHANGES_REQUIRED`
- `HIGH findings: tests/test_workbench_facade_discipline.py:71 only flags assignments whose root name is literally agents. The sanctioned import form from agents import architect would let architect.SOMETHING = ... bypass rule #2 entirely.`
- `HIGH findings: tests/test_workbench_facade_discipline.py:43,49-53 only match module == "schemas.sim_state". from schemas import sim_state is a clean bypass of rule #3, so the HF1 guard is not actually closed.`
- `MEDIUM findings: tests/test_workbench_facade_discipline.py:86-105 only blocks direct agents.* imports; it does not guard against indirect agent-module exposure via facade re-exports.`
- `LOW/NITS: docs/adr/ADR-015-workbench-agent-rpc-boundary.md:63 uses Sec-WebSocket-Protocol as an auth carrier, which is awkward for standard WS subprotocol handling.`
- `Notes on any new regressions: the stacked PR54 implementation already uses from agents import architect at backend/app/workbench/agent_facade.py:31, which means this checker misses the most likely mutation form in practice.`

**PR #52 [ADR-016 — .frd → .vtu + result viz]**
- `VERDICT: APPROVE_WITH_NITS`
- `HIGH findings: none`
- `MEDIUM findings: schemas/viz_manifest.py:92 allows arbitrary dict keys unrelated to FieldEntry.kind, so writer/viewer field-name drift can validate silently.`
- `MEDIUM findings: schemas/viz_manifest.py:43-44 and :77-78 do not enforce ordered bounds (bbox min<=max, stress min<=max), so obviously broken viewer ranges still pass schema validation.`
- `LOW/NITS: docs/adr/ADR-016-frd-vtu-result-viz.md:89-93 omits the required kind discriminator shown by schemas/viz_manifest.py:66-84.`
- `Notes on any new regressions: docs/adr/ADR-016-frd-vtu-result-viz.md:113 says the SPA reads an HTTP-only cookie to set X-Workbench-Token; browser JS cannot do that, and it conflicts with ADR-015’s auth story.`

**PR #53 [ADR-017 — RAG facade in-process + CLI/lib parity]**
- `VERDICT: CHANGES_REQUIRED`
- `HIGH findings: tests/test_rag_facade_parity.py:29 allows both rag_facade.py and agent_facade.py as legal RAG import sites, but docs/adr/ADR-017-rag-facade-cli-lib-parity.md:41-42,49 say rag_facade.py is the single choke point.`
- `MEDIUM findings: tests/test_rag_facade_parity.py:62-71 ignore from . import kb / from . import query_cli because ImportFrom.module is None, so rules #3 and #4 can be bypassed with normal relative-import syntax.`
- `MEDIUM findings: docs/adr/ADR-017-rag-facade-cli-lib-parity.md:108 promises a singleton-policy discipline assertion, but tests/test_rag_facade_parity.py:120-127 only implement the four AST checks and never enforce that rule.`
- `LOW/NITS: the hardcoded CLI/lib tables at tests/test_rag_facade_parity.py:34-48 are brittle and will need manual updates for every new CLI module.`
- `Notes on any new regressions: no runtime regression yet because backend/app/rag is not on main in this workspace; the problem is that the contract test is weaker than the ADR claims.`

**PR #54 [P2.1-01 agent_facade + task_spec_builder skeleton]**
- `VERDICT: CHANGES_REQUIRED`
- `HIGH findings: docs/adr/ADR-015-workbench-agent-rpc-boundary.md:75-77 explicitly allow user edits before submit, but backend/app/workbench/task_spec_builder.py:107 mints the token over the pre-edit plan and :123 rechecks against the submitted plan. Any legitimate edit invalidates the token, so edited submits cannot succeed under this design.`
- `MEDIUM findings: tests/test_workbench_task_spec_builder.py:125-150 and :158-216 only cover accept-without-edit flows; the documented draft->edit->submit path is completely untested.`
- `LOW/NITS: backend/app/workbench/task_spec_builder.py:14 says the HMAC is over draft_id || canonical-JSON(plan), while the implementation at :66 uses an explicit NUL separator.`
- `Notes on any new regressions: backend/app/workbench/agent_facade.py:31 uses the alias-import style that PR51’s discipline test does not police.`

**PR #55 [P2.1-02 event_bus runtime]**
- `VERDICT: CHANGES_REQUIRED`
- `HIGH findings: backend/app/runtime/event_bus.py:125 appends the incoming event to the replay ring before overflow handling. When the queue is full, the later drop path at :149 still leaves the “dropped” event replayable, so reconnecting clients can see events live clients never received.`
- `HIGH findings: backend/app/runtime/event_bus.py:149 and :163-172 enqueue a fresh bus.dropped for every dropped non-critical event without removing anything. Under sustained overload the queue grows past 1024 indefinitely, so the cap does not actually cap memory.`
- `HIGH findings: backend/app/runtime/event_bus.py:213 emits bus.gap with seq=self._next_seq but never reserves that seq. The next real event reuses the same seq, so a client that persists the gap seq can miss the real event on the next since_seq resume.`
- `MEDIUM findings: backend/app/runtime/event_bus.py:119-123 race with :235-243; close() does not take the lock, so a post-close emit can still slip through after the initial closed check.`
- `MEDIUM findings: backend/app/runtime/event_bus.py:78,123 never enforce event.run_id == self.run_id, so a caller bug can contaminate one run’s stream with another run’s event.`
- `LOW/NITS: raw deque annotations could be parameterized for readability/type checking.`
- `Notes on any new regressions: this runtime no longer matches ADR-014’s stated backpressure contract. docs/adr/ADR-014-ws-event-bus-for-workbench.md:47-49 say oldest non-critical events are evicted and node.exited(status=err) must survive drops; backend/app/runtime/event_bus.py:144-149 drops the arriving event and only uses kind-based criticality.`

Static review only; I did not execute the PR branches.
tokens used
180,192
Reviewed via `gh pr view`, `gh pr diff`, and direct file reads from the fetched PR heads.

**PR #50 [ADR-014 — WS event bus contract]**
- `VERDICT: APPROVE_WITH_NITS`
- `HIGH findings: none`
- `MEDIUM findings: schemas/ws_events.py:58,64 advertise ISO-8601 UTC timestamps but enforce only bare str, so the wire contract is weaker than the ADR says.`
- `MEDIUM findings: schemas/ws_events.py:103-104 let top_k_titles and scores diverge in length, so title<->score pairing is not actually guaranteed by the schema.`
- `LOW/NITS: schemas/ws_events.py:40 misstates the digest length; docs/adr/ADR-014-ws-event-bus-for-workbench.md:141 and :149 contradict each other on 50% vs 30% self-pass-rate.`
- `Notes on any new regressions: none in this PR itself.`

**PR #51 [ADR-015 — workbench → agent RPC boundary]**
- `VERDICT: CHANGES_REQUIRED`
- `HIGH findings: tests/test_workbench_facade_discipline.py:71 only flags assignments whose root name is literally agents. The sanctioned import form from agents import architect would let architect.SOMETHING = ... bypass rule #2 entirely.`
- `HIGH findings: tests/test_workbench_facade_discipline.py:43,49-53 only match module == "schemas.sim_state". from schemas import sim_state is a clean bypass of rule #3, so the HF1 guard is not actually closed.`
- `MEDIUM findings: tests/test_workbench_facade_discipline.py:86-105 only blocks direct agents.* imports; it does not guard against indirect agent-module exposure via facade re-exports.`
- `LOW/NITS: docs/adr/ADR-015-workbench-agent-rpc-boundary.md:63 uses Sec-WebSocket-Protocol as an auth carrier, which is awkward for standard WS subprotocol handling.`
- `Notes on any new regressions: the stacked PR54 implementation already uses from agents import architect at backend/app/workbench/agent_facade.py:31, which means this checker misses the most likely mutation form in practice.`

**PR #52 [ADR-016 — .frd → .vtu + result viz]**
- `VERDICT: APPROVE_WITH_NITS`
- `HIGH findings: none`
- `MEDIUM findings: schemas/viz_manifest.py:92 allows arbitrary dict keys unrelated to FieldEntry.kind, so writer/viewer field-name drift can validate silently.`
- `MEDIUM findings: schemas/viz_manifest.py:43-44 and :77-78 do not enforce ordered bounds (bbox min<=max, stress min<=max), so obviously broken viewer ranges still pass schema validation.`
- `LOW/NITS: docs/adr/ADR-016-frd-vtu-result-viz.md:89-93 omits the required kind discriminator shown by schemas/viz_manifest.py:66-84.`
- `Notes on any new regressions: docs/adr/ADR-016-frd-vtu-result-viz.md:113 says the SPA reads an HTTP-only cookie to set X-Workbench-Token; browser JS cannot do that, and it conflicts with ADR-015’s auth story.`

**PR #53 [ADR-017 — RAG facade in-process + CLI/lib parity]**
- `VERDICT: CHANGES_REQUIRED`
- `HIGH findings: tests/test_rag_facade_parity.py:29 allows both rag_facade.py and agent_facade.py as legal RAG import sites, but docs/adr/ADR-017-rag-facade-cli-lib-parity.md:41-42,49 say rag_facade.py is the single choke point.`
- `MEDIUM findings: tests/test_rag_facade_parity.py:62-71 ignore from . import kb / from . import query_cli because ImportFrom.module is None, so rules #3 and #4 can be bypassed with normal relative-import syntax.`
- `MEDIUM findings: docs/adr/ADR-017-rag-facade-cli-lib-parity.md:108 promises a singleton-policy discipline assertion, but tests/test_rag_facade_parity.py:120-127 only implement the four AST checks and never enforce that rule.`
- `LOW/NITS: the hardcoded CLI/lib tables at tests/test_rag_facade_parity.py:34-48 are brittle and will need manual updates for every new CLI module.`
- `Notes on any new regressions: no runtime regression yet because backend/app/rag is not on main in this workspace; the problem is that the contract test is weaker than the ADR claims.`

**PR #54 [P2.1-01 agent_facade + task_spec_builder skeleton]**
- `VERDICT: CHANGES_REQUIRED`
- `HIGH findings: docs/adr/ADR-015-workbench-agent-rpc-boundary.md:75-77 explicitly allow user edits before submit, but backend/app/workbench/task_spec_builder.py:107 mints the token over the pre-edit plan and :123 rechecks against the submitted plan. Any legitimate edit invalidates the token, so edited submits cannot succeed under this design.`
- `MEDIUM findings: tests/test_workbench_task_spec_builder.py:125-150 and :158-216 only cover accept-without-edit flows; the documented draft->edit->submit path is completely untested.`
- `LOW/NITS: backend/app/workbench/task_spec_builder.py:14 says the HMAC is over draft_id || canonical-JSON(plan), while the implementation at :66 uses an explicit NUL separator.`
- `Notes on any new regressions: backend/app/workbench/agent_facade.py:31 uses the alias-import style that PR51’s discipline test does not police.`

**PR #55 [P2.1-02 event_bus runtime]**
- `VERDICT: CHANGES_REQUIRED`
- `HIGH findings: backend/app/runtime/event_bus.py:125 appends the incoming event to the replay ring before overflow handling. When the queue is full, the later drop path at :149 still leaves the “dropped” event replayable, so reconnecting clients can see events live clients never received.`
- `HIGH findings: backend/app/runtime/event_bus.py:149 and :163-172 enqueue a fresh bus.dropped for every dropped non-critical event without removing anything. Under sustained overload the queue grows past 1024 indefinitely, so the cap does not actually cap memory.`
- `HIGH findings: backend/app/runtime/event_bus.py:213 emits bus.gap with seq=self._next_seq but never reserves that seq. The next real event reuses the same seq, so a client that persists the gap seq can miss the real event on the next since_seq resume.`
- `MEDIUM findings: backend/app/runtime/event_bus.py:119-123 race with :235-243; close() does not take the lock, so a post-close emit can still slip through after the initial closed check.`
- `MEDIUM findings: backend/app/runtime/event_bus.py:78,123 never enforce event.run_id == self.run_id, so a caller bug can contaminate one run’s stream with another run’s event.`
- `LOW/NITS: raw deque annotations could be parameterized for readability/type checking.`
- `Notes on any new regressions: this runtime no longer matches ADR-014’s stated backpressure contract. docs/adr/ADR-014-ws-event-bus-for-workbench.md:47-49 say oldest non-critical events are evicted and node.exited(status=err) must survive drops; backend/app/runtime/event_bus.py:144-149 drops the arriving event and only uses kind-based criticality.`

Static review only; I did not execute the PR branches.
