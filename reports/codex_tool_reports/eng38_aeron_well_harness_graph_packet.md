# ENG-38 AERON Well-Harness Graph Packet

**Issue:** ENG-38 · AERON-04 · Expose AERON-backed graph path through well-harness CLI
**Branch:** `codex/ENG-38-aeron-well-harness-graph`
**Prepared by:** Codex primary executor
**Prepared at:** 2026-05-06
**External writes:** dry-run only; no Linear, GitHub, or Notion mutation performed by this packet.

## Outcome

Expose one user-runnable AERON adoption point through the existing well-harness CLI:

```bash
python run_well_harness.py GS-001 --executor graph --no-notion-sync
```

The command runs a bounded graph-backed path, proves the graph result has
`solve_metadata.backend == "calculix"`, and persists the normal well-harness
`project_state` bundle. It remains replay/dummy execution and is not signed
validation, GS101, or a fresh real-solver run.

## Scope Mapping

| ENG-38 acceptance | Evidence |
|---|---|
| CLI accepts `--executor graph` while preserving `replay` and `calculix` | `backend/app/well_harness/cli.py`; `test_cli_accepts_graph_executor_mode` |
| `GraphExecutor` invokes `agents.graph.compile_graph()` and proves AERON-backed solver metadata | `backend/app/well_harness/executors.py`; `test_graph_executor_runs_graph_path_and_persists_project_state`; CLI smoke logs `solve_metadata.backend=calculix` |
| Graph mode persists normal well-harness run record and `project_state` bundle for `GS-001` without Notion sync | `backend/app/well_harness/task_runner.py`; `test_graph_executor_runs_graph_path_and_persists_project_state`; CLI smoke run `gs_001_20260506T125627000031Z` |
| Graph mode is honest about replay/dummy execution | `GraphExecutor.is_replay=True`; handoff risk says `graph_executor replay/dummy mode`; README and `docs/well_harness_architecture.md` disclaim no signed validation |
| Focused tests cover graph executor and CLI parser/runner behavior | `backend/tests/test_well_harness.py` adds graph mode, failure handling, backend metadata, and work-dir coverage |

## Changed Files

- `.planning/STATE.md`
- `README.md`
- `backend/app/well_harness/__init__.py`
- `backend/app/well_harness/cli.py`
- `backend/app/well_harness/executors.py`
- `backend/app/well_harness/task_runner.py`
- `backend/tests/test_well_harness.py`
- `docs/well_harness_architecture.md`

## Boundary Check

No tracked changes to:

- `schemas/*`
- `aeron/protocols/*`
- `golden_samples/**`
- GS101 or signed-validation artifacts
- API routes
- frontend
- Notion sync contracts
- CI/governance policy
- dependency declarations

Existing untracked files outside the ENG-38 slice were left untouched.

Claude Opus audit returned `APPROVE` in
`reports/codex_tool_reports/eng38_aeron_well_harness_graph_claude_audit.md`.

## Verification

```text
.venv/bin/python scripts/compute_calibration_cap.py --human
T1 calibration ceiling : 50%
Codex pre-merge gate   : MANDATORY
Basis                  : 4 of last 5 = CHANGES_REQUIRED -> ceiling 50%
State entries          : 19 (last 5 used)
```

```text
.venv/bin/ruff check backend/app/well_harness/__init__.py backend/app/well_harness/cli.py backend/app/well_harness/executors.py backend/app/well_harness/task_runner.py backend/tests/test_well_harness.py
All checks passed!
```

```text
.venv/bin/ruff format --check backend/app/well_harness/__init__.py backend/app/well_harness/cli.py backend/app/well_harness/executors.py backend/app/well_harness/task_runner.py backend/tests/test_well_harness.py
5 files already formatted
```

```text
.venv/bin/python -m pytest backend/tests/test_well_harness.py -q -o addopts=''
10 passed
```

```text
.venv/bin/python -m pytest tests/test_cold_smoke_e2e.py -q -o addopts=''
1 passed
```

```text
git diff --check
passed
```

```text
.venv/bin/python run_well_harness.py GS-001 --executor graph --no-notion-sync
executor_name=graph_executor
solve_metadata.backend=calculix
execution_mode=replay,dummy-geometry
status=pending_review
project_state_dir=project_state/runs/GS-001/gs_001_20260506T125627000031Z
```

## Known Risks And Limits

- The graph executor uses replay/dummy external surfaces. It does not require or launch real `ccx`, FreeCAD, Gmsh, OpenAI API, or Notion credentials.
- The CLI smoke prints an existing knowledge-store warning from NumPy 2.0 drift: ``np.float_`` was removed. The well-harness command continues successfully.
- Full `pytest backend/tests` is blocked before ENG-38 code runs by existing dependency drift:
  - OpenAI 1.6.1 with httpx 0.28.1 rejects `proxies`.
  - With `OPENAI_API_KEY=`, FastAPI/Starlette `TestClient` then fails because httpx 0.28.1 rejects `app`.
- The GS-001 result remains `pending_review` because the replayed golden-sample value is outside the current stress tolerance. That is expected for this integration smoke and is not represented as signed validation.

## GitHub PR Dry-Run Body

````markdown
## Summary

- Add an additive `--executor graph` well-harness mode for ENG-38 / AERON-04.
- Route graph mode through `agents.graph.compile_graph()` with replay/dummy external surfaces while proving `solve_metadata.backend == "calculix"`.
- Persist the normal well-harness `project_state` bundle and document that this is not GS101, signed validation, or a fresh real-solver run.

## Self-pass-rate (mechanically derived)

**50%** · derived from `reports/calibration_state.json` last-5 R1 outcomes.

Codex pre-merge gate (per ADR-012):

- [ ] BLOCKING (ceiling 30) — must reach Codex R1=APPROVE before merge
- [x] MANDATORY non-blocking (ceiling 50) — Codex R1 required, can iterate
- [ ] RECOMMENDED (ceiling 80) — Codex review strongly suggested
- [ ] OPTIONAL (ceiling 95) — honor system, Codex at author discretion

ADR-011 §T2 mandatory triggers:

- [ ] M1: governance text added/changed
- [ ] M2: sign-or-direction math
- [ ] M3: HF compliance claim
- [ ] M4: governance→enforcement translation
- [x] M5: PR opened while ceiling <= 50%

## Test plan

- [x] `.venv/bin/ruff check backend/app/well_harness/__init__.py backend/app/well_harness/cli.py backend/app/well_harness/executors.py backend/app/well_harness/task_runner.py backend/tests/test_well_harness.py`
- [x] `.venv/bin/ruff format --check backend/app/well_harness/__init__.py backend/app/well_harness/cli.py backend/app/well_harness/executors.py backend/app/well_harness/task_runner.py backend/tests/test_well_harness.py`
- [x] `.venv/bin/python -m pytest backend/tests/test_well_harness.py -q -o addopts=''`
- [x] `.venv/bin/python -m pytest tests/test_cold_smoke_e2e.py -q -o addopts=''`
- [x] `.venv/bin/python run_well_harness.py GS-001 --executor graph --no-notion-sync`
- [x] Claude Opus audit verdict: `APPROVE` in `reports/codex_tool_reports/eng38_aeron_well_harness_graph_claude_audit.md`
- [ ] GitHub CI

## Merge trailers

```text
Execution-by: codex-primary
Codex-verified: eng38-local-proof@8a38b20
Reviewed-by: claude-opus47 APPROVE reports/codex_tool_reports/eng38_aeron_well_harness_graph_claude_audit.md
Linear-Issue: ENG-38
```

## Out of scope

- No schema, AERON protocol, golden-sample, GS101, signed-validation, API, frontend, Notion, CI/governance, dependency, or default-executor changes.
- No claim that replay/dummy graph mode is a fresh CalculiX solve or signed validation.
- Note: `backend/app/well_harness/task_runner.py` includes ruff-compatible typing/line-wrap cleanup bundled with the functional `work_dir` change.

## Related

- Linear ENG-38
- ADR-011, ADR-012, ADR-013
- Prior AERON chain: ENG-35, ENG-36, ENG-37
````

## Linear Proof Comment Dry-Run

```markdown
ENG-38 local proof is ready for review.

Delivered:
- `run_well_harness.py GS-001 --executor graph --no-notion-sync` now runs graph mode.
- Graph mode invokes `agents.graph.compile_graph()` and logs `solve_metadata.backend=calculix`.
- Normal well-harness `project_state` bundle is persisted.
- Replay/dummy limits are documented and surfaced in handoff risks.

Verification:
- Calibration cap: 50%, mandatory review.
- Ruff check: passed on touched well-harness files.
- Ruff format check: passed on touched well-harness files.
- Focused pytest: `backend/tests/test_well_harness.py` -> 10 passed.
- Cold smoke: `tests/test_cold_smoke_e2e.py` -> 1 passed.
- CLI smoke: passed, latest run `gs_001_20260506T125627000031Z`.

Known limits:
- No GS101 or signed-validation claim.
- Full backend suite is blocked by existing OpenAI/httpx and FastAPI-Starlette/httpx dependency drift before ENG-38 code runs.

Pending before state transition:
- GitHub PR and CI links.
```
