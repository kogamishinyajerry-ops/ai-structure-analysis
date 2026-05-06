# ENG-33 AERON L0 Protocol Salvage Claude Audit

**Issue:** ENG-33 · AERON L0 protocol salvage from blocked PR #126
**Branch:** `codex/aeron-l0-protocol-salvage`
**Command:** `claude -p <packet> --model opus --no-session-persistence --tools "" --max-budget-usd 0.80`
**Tool access:** Disabled

APPROVE

## Findings

**Scope compliance — clean**

- Diff touches only: `aeron/` package, `pyproject.toml`, focused tests, and `.planning/STATE.md` status text.
- No root `AGENTS.md`, Apex/Claude ownership artifacts, driver adapters, solver code, golden-sample, orchestration/LangGraph, or Notion sync.
- The salvage stays inside the contract surface.

**#126 review issues — addressed**

1. Package inclusion: `pyproject.toml` adds `aeron*` to `setuptools.packages.find.include`; `tests/test_packaging.py` pins it as a regression test.
2. Closed SolveStatus code vocabulary: `SolveStatusCode(StrEnum)` defines exactly `{ok, diverged, timeout, preflight_failed, solver_error, aborted}`. `test_solve_status_rejects_unknown_status_code` pins closure.
3. `fault_class` preserves CalculiX taxonomy: `SolveStatus.fault_class: FaultClass | None` imports the existing `schemas.sim_state.FaultClass`; `test_solve_status_preserves_fault_class_and_returncode` exercises `FaultClass.SOLVER_SYNTAX`.
4. Strict extra-field rejection: all seven carrier models share `ConfigDict(extra="forbid")`; the parametrized protocol-carrier test covers every carrier.
5. `returncode` matches the existing `tools.calculix_driver.run_solve()` payload. `test_solve_status_rejects_legacy_return_code_key` rejects divergent `return_code`.

**Protocol shape — sound**

- `FEABackend` is a `@runtime_checkable Protocol` with the four-method contract: `prepare_case`, `solve`, `parse_results`, and `health_check`.
- `test_driver_structurally_satisfies_protocol` validates structural conformance via `isinstance`.
- Note: `runtime_checkable` only checks method presence, not signatures; adapters should still pass static type checks later. Not a blocker.

**Minor non-blocking observations**

- `StrEnum` requires Python >=3.11; the project already declares `requires-python = ">=3.11"`.
- `HealthReport.status: HealthStatus` plus `checks: dict[str, bool]` is reasonable.
- `STATE.md` update is consistent with the salvage-only constraint and no-#126-AGENTS inheritance.

**Verdict rationale**

Diff is on-charter, surgical, and each #126 review issue has both a contract-level fix and a test that pins the fix. Safe to merge as the AERON L0 protocol salvage.
