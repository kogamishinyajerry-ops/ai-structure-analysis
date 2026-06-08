# Codex Review — ADR-028 P2 aeron `get_backend()` factory + solver de-hardcode (R0)

**Scope (solver-truth + HF1 path):** route `agents/solver.py` solver-backend selection
through a new `aeron.drivers.get_backend()` factory and remove the in-node non-CalculiX
hard-reject. Reverses the ADR-027-era assumption that the solver node owns the CalculiX
literal; dispatch now keys on `plan.solver.name` (ADR-028 D4/D5, CalculiX-first).

## Files

- `aeron/drivers/__init__.py` — **new** `get_backend(name, **kwargs) -> FEABackend`:
  `SolverBackend(name)` normalizes (ValueError on unknown); CALCULIX → `CalculiXFEABackend(**kwargs)`;
  any other known backend → `NotImplementedError` (CalculiX-first; OpenRadioss deferred to P5).
- `agents/solver.py` — `_build_calculix_backend` → `_build_backend(*, plan, work_root, mesh_input)`
  delegating to the factory on `plan.solver.name`; deleted the 3-line hard-reject; wrapped the
  callsite in `try/except NotImplementedError → _unsupported_backend_failure(plan)`; dropped the
  now-unused `from schemas.sim_plan import SolverBackend` import. `CalculiXFEABackend.prepare_case`
  keeps its own `ValueError` guard as defense-in-depth.
- `tests/test_solver_agent.py` — patch target `_build_calculix_backend` → `_build_backend`.
- `tests/test_aeron_get_backend_factory.py` — **new**, 5 tests (calculix enum + string → FEABackend
  instance; fenics + openradioss → NotImplementedError; unknown → ValueError).

## Review tooling note (honest)

`codex-review-relay --uncommitted` (the auto-repo-context wrapper) **ran away** for the third time
in this milestone — ~6000 lines of whole-repo exploration with no emitted verdict (same signature as
the P1 R1 runaway). It was stopped (`TaskStop`). The review was then re-run **contained**: the exact
staged 4-file unified diff was fed directly to the same xhigh model
(`codex-relay-with gpt-5.5`, 86gs) with an explicit "review ONLY this diff, do not explore" directive
and a solver-truth checklist. This is the same governance model, with the runaway-prone repo-walk
removed — a more controlled review, not a weaker one.

## R0 verdict — **APPROVE** (no solver-truth findings)

Codex gpt-5.5 (xhigh, ~9.3k tok) confirmed, reasoning from the diff:

1. CalculiX happy-path construction kwargs are byte-for-byte preserved.
2. Dispatch keys on the **actual** `plan.solver.name` — the `NotImplementedError` branch is reachable
   (not dead code behind a hard-coded `SolverBackend.CALCULIX`).
3. A non-CalculiX plan fails **before** `prepare_case`, via factory `NotImplementedError` →
   `_unsupported_backend_failure` → `UNKNOWN` + non-retriable (no `retry_budgets`, no `verdict`).
   **No silent wrong-physics-as-CalculiX fallback path.**
4. No stale `SolverBackend` reference remains in `agents/solver.py` (no NameError risk).
5. No circular import from the diff + supplied context (factory imported lazily inside `_build_backend`).
6. `try/except NotImplementedError` is scoped to backend construction only — a deeper genuine
   `NotImplementedError` from `solve()` is not swallowed.

Verbatim: *"No solver-truth findings. … I do not see a silent fallback path, stale `SolverBackend`
reference in `agents/solver.py`, or an obvious circular import from the diff and supplied context.
VERDICT: APPROVE."*

## Gates

- `tests/test_solver_agent.py` + `tests/test_aeron_get_backend_factory.py` → **14 passed**
  (9 existing solver + 5 new factory).
- Full root suite `pytest tests/` → **2680 passed, 6 skipped**.
- `ruff check agents aeron schemas tests` (CI-linted, non-excluded trees) → clean.
  `ruff format --check` the 4 files → already formatted.

**Closure:** R0 APPROVE, no fix round needed. P2 cleared for commit under the HF1.1 override.
