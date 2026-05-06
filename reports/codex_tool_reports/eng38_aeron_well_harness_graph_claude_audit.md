# ENG-38 AERON Well-Harness Graph Claude Audit

**Issue:** ENG-38 · AERON-04 · Expose AERON-backed graph path through well-harness CLI
**Branch:** `codex/ENG-38-aeron-well-harness-graph`
**Command:** `claude -p <packet+diff> --model opus --no-session-persistence --tools "" --max-budget-usd 0.80`
**Tool access:** Disabled
**Date:** 2026-05-06

APPROVE

## Rationale

ENG-38 acceptance criteria are met with appropriately scoped, additive changes:

1. CLI surface is additive. `--executor graph` is added alongside `replay` and `calculix` without altering defaults; `_build_executor` dispatch is clean and tested by `test_cli_accepts_graph_executor_mode`.
2. `GraphExecutor.execute()` invokes `agents.graph.compile_graph()` and asserts `solve_metadata.backend == "calculix"`, returning failure when the assertion is not satisfied. Failure-mode tests make the assertion load-bearing rather than aspirational.
3. Replay/dummy truthfulness is preserved: `is_replay=True`, handoff risk text names `graph_executor replay/dummy mode`, README and architecture docs disclaim GS101/signed validation, and CLI smoke logs `execution_mode=replay,dummy-geometry`.
4. Boundary discipline is clean: diff stays inside well-harness, CLI, tests, docs, STATE, and proof reports. No schema, AERON protocol, golden-sample, GS101, signed-validation, API, frontend, Notion contract, CI, or dependency changes.
5. Evidence is sufficient for the slice: well-harness tests passed, cold smoke passed, ruff check and format are clean, `git diff --check` is clean, CLI smoke produced run `gs_001_20260506T125627000031Z`, and the 50% calibration cap was honored.
6. State plumbing is correct: `work_dir=state_dir / "executor"` is wired through `StructuralExecutor.execute()` with a backward-compatible default, and `CapturingExecutor` test confirms the runner passes the expected path.

## Non-Blocking Notes

- `backend/app/well_harness/task_runner.py` includes cosmetic typing and formatting cleanup bundled with the functional `work_dir` change. This is consistent with ruff but should be called out in the PR to avoid reviewer confusion.
- `GraphExecutor` intentionally patches the LLM, geometry, mesh, quality, and solve subprocess surfaces. The smoke exercises the orchestration spine and solver-dispatch boundary, not the full agent internals.
- `GS-001` remains `pending_review` because replayed golden-sample values drift against current reference tolerance. This is expected and is documented as not signed validation.
- Full `pytest backend/tests` remains blocked by existing dependency drift: OpenAI 1.6.1 / httpx 0.28.1 and FastAPI-Starlette / httpx 0.28.1 incompatibilities. This should be tracked separately.

No CHANGES_REQUIRED items. Safe to merge after Codex pre-merge gate handling and CI.
