# Onboarding — AI-Structure-FEA (Claude Code edition)

> **Audience:** A new contributor (human or AI agent) joining the project at Phase 1.5+ (post-2026-04-25 governance pivot).
> **Read-time:** 15 minutes.
> **Prerequisites:** Familiarity with Python 3.11+, git, GitHub PR workflow.

---

## 1 — What this project is

AI-Structure-FEA is an **AI-driven Finite Element Analysis engine** with multi-agent orchestration. It uses CalculiX as the only numerical truth source (per ADR-002), LangGraph for agent pipelines (ADR-001), and a four-layer architecture (Control / Execution / Knowledge / Evaluation, per Golden Rule #9).

The PRD lives in Notion: [AI-FEA Engine PRD](https://www.notion.so/AI-Structure-FEA-Control-Plane-345c68942bed80f6a092c9c2b3d3f5b9).

## 2 — Read these in order

Read these documents **before** opening your first PR. They are short.

1. [`README.md`](../../README.md) — quick-reference dev rules + naming conventions
2. [`docs/adr/ADR-011-pivot-claude-code-takeover.md`](../adr/ADR-011-pivot-claude-code-takeover.md) — governance baseline. Pay special attention to:
   - §Decision (T0/T1/T2 routing)
   - §Hard-Floor Rules (HF1-HF5)
   - §9 Golden Rules
   - §Commit Trailer Convention
3. [`docs/adr/ADR-012-calibration-cap-for-t1-self-pass-rate.md`](../adr/ADR-012-calibration-cap-for-t1-self-pass-rate.md) (in-flight on PR #24) — mechanical self-pass-rate
4. [`docs/adr/ADR-013-branch-protection-enforcement.md`](../adr/ADR-013-branch-protection-enforcement.md) (in-flight on PR #25) — enforcement layers
5. [`docs/governance/routing.md`](routing.md) — T0/T1/T2 routing thin pointer
6. [`docs/failure_patterns/`](../failure_patterns/) — empirical failure patterns (FP-001/002/003 currently document GS-001/002/003 issues)
7. [`.planning/STATE.md`](../../.planning/STATE.md) — current execution snapshot (FF-task ledger, open PRs, carry-overs)

## 3 — Minimum local setup

```bash
# Repo
git clone https://github.com/kogamishinyajerry-ops/ai-structure-analysis.git
cd ai-structure-analysis

# Python env (3.11 required by pyproject.toml)
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,agents]"

# Pre-commit hooks (FF-06 HF1 path-guard)
pre-commit install

# Smoke check
pytest tests/ -q
ruff check .
ruff format --check .
```

If `pre-commit install` fails, see `.pre-commit-config.yaml` for the expected hooks (`scripts/hf1_path_guard.py` is the load-bearing one).

## 4 — Calibration ceiling — read this BEFORE you open a PR

Per ADR-012, **T1 cannot self-rate the PR's pass-rate**. Instead:

```bash
python3 scripts/compute_calibration_cap.py --human
```

This prints the current ceiling. As of 2026-04-25 bootstrap, the ceiling is **30% / BLOCKING** (5 of last 5 R1 = CHANGES_REQUIRED). That means:

- Pre-merge Codex review is **mandatory** (`/codex-gpt54 review PR <N>`)
- Codex must reach R1=APPROVE before merge
- Discipline binding: T1 must NOT merge under BLOCKING without R1=APPROVE or T0 explicit override

To exit BLOCKING, your PR must reach R1=APPROVE on first round. Three consecutive APPROVEs reset the ceiling to 95% (honor-system). Each R1=CHANGES_REQUIRED keeps the ceiling at 30 BLOCKING.

The PR template (`.github/PULL_REQUEST_TEMPLATE.md`) prefills the Self-pass-rate field. Do not edit it to a number above the ceiling — CI's `calibration-cap-check` will fail.

## 5 — Where things live (file map)

```
agents/                         # LangGraph agent nodes (HF1.1-HF1.4)
backend/app/well_harness/       # Notion sync + run orchestration
schemas/                        # Pydantic v2 strict schemas (HF1.4)
tools/                          # External-tool drivers (calculix, freecad, gmsh — HF1.1)
checkers/                       # Validators (FRD parsers, GS comparators)
reporters/                      # Output renderers
tests/                          # pytest suite — must stay green on CI
scripts/                        # Governance + utility scripts (FF-06 path-guard, ADR-012 calibration cap, etc.)
golden_samples/GS-001..003/     # Reference benchmarks (HF1.7 — read-only)
docs/adr/                       # Architecture Decision Records (PR-protected zone)
docs/governance/                # This dir; routing + onboarding
docs/failure_patterns/          # FP-* empirical failure documentation
.planning/STATE.md              # Repo-side execution snapshot
.github/workflows/              # CI workflows (HF1.9 — governance surface)
reports/calibration_state.json  # ADR-012 append-only state file
reports/codex_tool_reports/     # Archived Codex review reports
```

## 6 — Workflow for a typical change

1. **Pick a task.** From [Notion 任务库](https://www.notion.so/AI-StructureAnalysis-345c68942bed80f6a092c9c2b3d3f5b9) or `.planning/STATE.md` Phase 1.5 task table.
2. **Branch.** Naming: `feature/AI-FEA-{phase}-{nn}-{slug}` or `feature/AI-FEA-{FF}-{nn}-{slug}` for Foundation-Freeze items.
3. **Code with HF1 in mind.** If your diff touches `agents/solver.py`, `Dockerfile`, `golden_samples/**`, etc., the pre-commit hook will block — open an ADR or set `HF1_GUARD_OVERRIDE='<reason>'` for emergency.
4. **Commit with trailers.** Every commit has `Execution-by:` (you or your agent ID); add `Codex-verified:` once Codex returns APPROVE.
5. **Open PR via the template.** Fill the `Self-pass-rate` section from `compute_calibration_cap.py` output, tick applicable M1-M5 triggers honestly, write a real `## Test plan`.
6. **Codex review.** If ceiling is BLOCKING/MANDATORY or any M-trigger fires, run `/codex-gpt54 review PR <N>`. Iterate fix→push→re-review until APPROVE.
7. **Merge.** Squash-merge once both required CI checks are green AND Codex R1=APPROVE.
8. **Post-merge.** STATE.md update should be in the same PR per FF-05's R1 lesson; if you forgot, do a follow-up housekeeping PR.

## 7 — Things you'll be tempted to do that you should not

- **Push directly to `main`.** ADR-013's branch protection prevents it once active; before then, it's an honor-system rule (Golden Rule #1) and a P0 procedural failure if violated.
- **Self-rate self-pass-rate at 95% by intuition.** ADR-012 forbids this. Read the script's output.
- **Skip Codex because "the change is small."** ADR-011 §T2 anti-shenanigans note: M1-M5 trigger list governs this, not gut feeling. The 0/5 stylistic-vs-5/5 factual distribution from session 2026-04-25 is the empirical anchor.
- **Modify governance text in passing.** `docs/adr/`, `docs/governance/`, `docs/failure_patterns/` are PR-protected zone — every change needs Codex M1.
- **Use `Agent` tool to launch Codex.** Codex must be invoked via `/codex-gpt54` slash command. The Agent-launched path doesn't authenticate properly with the Codex CLI quota system.
- **Bypass the pre-commit hook with `git commit --no-verify`.** That ignores HF1 hard-stop. If the hook is wrong, fix the hook (in a separate PR with Codex review); don't skip it.
- **Commit absolute paths to `/Users/...`.** FF-06's path-guard catches this. The override is for emergencies only and audited at PR review.

## 8 — Where to ask questions

- **In-session:** `/help` for Claude Code, or read the relevant ADR.
- **Async:** Notion control-plane page comments → tagged at T0 (CFDJerry / Kogami) or in Decisions DB.
- **Bug reports / process gaps:** open a `docs/failure_patterns/FP-{NNN}-{slug}.md` proposing the pattern, and a corresponding GitHub Issue.

---

## Self-test — you've onboarded if you can answer these

1. What does T1 stand for, and what's it allowed to do without T0?
2. What's the difference between HF1 hard-stop zone and PR-protected zone?
3. What command tells you the current calibration ceiling?
4. What's the M1 mandatory trigger?
5. Where do new ADRs go, and what should mirror them in Notion?
6. What's the difference between the README's quick-rules and ADR-011 §9 Golden Rules?

Answers: T1 = Claude Code CLI (Opus 4.7), executes code via PRs, can't self-merge under BLOCKING. HF1 hard-stop = pre-commit blocks staged diffs to enumerated paths; PR-protected = regular PR + mandatory Codex M1. `python3 scripts/compute_calibration_cap.py --human`. M1 = PRs touching governance text. ADRs live in `docs/adr/ADR-{nnn}-{slug}.md`, mirrored as Notion 决策库 entries. README is a quick-reference summary; ADR-011 is canonical.
