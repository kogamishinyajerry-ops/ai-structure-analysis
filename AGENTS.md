# AGENTS.md — Codex Briefing for `ai-structure-analysis`

> **Audience:** Codex (and any non-Apex AI worker).
> **Owner:** Apex AI (Claude Code). Edits to this file go through `main` only.
> **Protocol:** AERON OS §18 v0.1 — three iron rules apply.
>   1. Calls are one-way: Apex → Codex. Codex never calls Apex.
>   2. PR review and merge: Apex only.
>   3. Writes to `main` and to the Notion dashboard: Apex only. Codex works on `codex/<task_id>` branches and submits PRs.

---

## 1. Mission

Wrap the existing CalculiX-centric stack as an AERON L0 driver that satisfies
`aeron.protocols.fea_backend.FEABackend`. **No replacement of the LangGraph topology, no swap of solver, no new framework.** This is interface adaptation, not a rewrite.

If a task description seems to require any of the above, stop and report — do not improvise.

---

## 2. Project layout (read-only context)

```
agents/             # LangGraph nodes (architect → geometry → mesh → solver → reviewer → viz). DO NOT modify topology.
tools/              # External tool drivers: calculix_driver.py, freecad_driver.py, gmsh_driver.py, frd_parser.py.
schemas/            # Pydantic v2: SimPlan, SimState, viz_manifest, ws_events. Canonical contracts.
templates/          # CalculiX .inp Jinja2 templates.
checkers/           # Pre-solve quality gates (Jacobian, geometry).
reporters/          # Markdown + VTP output generators.
backend/            # Legacy well_harness, Notion sync, control plane. Off-limits unless task explicitly names it.
golden_samples/     # GS-001..GS-003 reference cases for benchmarks. Treat inputs as immutable.
tests/              # pytest suite (Python 3.11+).
aeron/              # NEW under §18 — protocol + driver adapter layer. Apex curates.
```

---

## 3. Immutable invariants (NEVER violate)

1. **Python 3.11+, Pydantic v2.** Use `from __future__ import annotations`. No Pydantic v1 syntax.
2. **CalculiX is the only solver right now.** `SolverBackend.FENICS` exists in the enum as a forward-declared placeholder; do not implement it.
3. **Do not modify** `agents/`, `schemas/`, `tools/`, `templates/`, `checkers/`, `reporters/`, `backend/` unless your task’s `scope` field explicitly lists the path. The default assumption is read-only.
4. **Do not introduce new frameworks** (no FastAPI swap, no Celery, no new ORM, no alternate orchestrator).
5. **Do not touch CI config, pre-commit, pyproject dependencies, or Dockerfile** unless your task is specifically to do so.
6. **Do not write to Notion.** Only Apex writes Notion. Your output is the PR.
7. **Do not merge your own PR.** Apex reviews and merges.

---

## 4. Branch & write rules

| Branch pattern   | Owner   | Allowed writes                                  |
|------------------|---------|-------------------------------------------------|
| `main`           | Apex    | All — but only after PR review                  |
| `claude/<id>`    | Apex    | Anything in scope                               |
| `codex/<id>`     | Codex   | **Only paths listed in task `scope`**           |
| `jerry/<desc>`   | 总师    | Anything                                        |

Codex must:
- Branch from current `main`.
- Push to `codex/<task_id>` only.
- Open a PR targeting `main`. Title: `[<task_id>] <one-line summary>`.
- Never force-push, never rewrite history, never `git merge` into `main`.

---

## 5. Codex task contract

Every task Apex hands you will include these fields. If any are missing, **stop and ask** — do not infer.

```yaml
task_id:        # e.g. L0-cx-tests
type:           # parallel_exec | review | benchmark | independent_rewrite
branch:         # codex/L0-cx-tests
scope:          # explicit list of paths you may create or modify
read_only:      # paths you may read but not modify
forbidden:      # paths you must not even read (used for independent_rewrite)
constraints:    # short bullets, derived from this AGENTS.md
acceptance:     # concrete checks (commands, file existence, test pass)
deliverable:    # PR URL — that is your output
```

**Constraint for `independent_rewrite` tasks:** the `forbidden` list will include the existing implementation of the same module. You must produce your version without reading it. Apex diffs the two and writes an ADR.

---

## 6. Acceptance checklist (apply to every PR)

Before opening the PR, confirm and tick in the PR body:

- [ ] All changes are within `scope`. No file outside it was created or modified.
- [ ] No file in `forbidden` was read (for independent_rewrite tasks).
- [ ] `ruff check .` passes on changed files.
- [ ] `pytest -q` passes locally for changed paths (or new tests added).
- [ ] No new top-level dependency added to `pyproject.toml` unless task says so.
- [ ] PR body cites `task_id` and lists exact files touched.
- [ ] No write to Notion attempted.

---

## 7. Off-limits paths (default)

These directories are off-limits unless explicitly named in `scope`:

- `agents/` — LangGraph topology
- `backend/well_harness/` — Notion sync, control plane
- `golden_samples/` — benchmark inputs
- `.github/workflows/` — CI
- `pyproject.toml`, `uv.lock`, `Dockerfile`, `Makefile`, `.pre-commit-config.yaml`
- `runs/`, `htmlcov/`, `reports/`, `scratch/` — runtime artifacts
- `aeron/protocols/` — protocol contracts (Apex-curated)

If your task needs to touch any of these, the task brief must say so explicitly.

---

## 8. Communication

- You report only via the PR. No Notion writes, no Slack-style updates, no DM to Apex.
- If you find a contradiction between this file and your task brief, **trust this file** and flag the conflict in the PR body.
- If you find a bug outside your `scope`, write it in the PR body under `## Out-of-scope findings`. Do not fix it.

---

*Version: §18 v0.1 · Last revised by Apex AI on integration kickoff.*
