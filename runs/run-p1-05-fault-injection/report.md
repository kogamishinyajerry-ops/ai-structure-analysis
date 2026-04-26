# P1-05 — Reviewer Fault Injection Baseline

> Generated: 2026-04-18T15:44:26+00:00
> Covers every ADR-004 fault_class across three canonical injection scenarios (fresh, mid-retry, budget-exhausted) — 24 total.

## 1. Headline

- Scenarios executed: **24**
- Passed: **24**
- Failed: **0**
- Pass rate: **100.0%**

## 2. Recovery contract (ADR-004 mirror)

| FaultClass | Target node | Verdict | Budget key |
|---|---|---|---|
| `geometry_invalid` | `geometry` | Re-run | `geometry` |
| `mesh_jacobian` | `mesh` | Re-run | `mesh` |
| `mesh_resolution` | `mesh` | Re-run | `mesh` |
| `solver_convergence` | `solver` | Re-run | `solver` |
| `solver_timestep` | `solver` | Re-run | `solver` |
| `solver_syntax` | `solver` | Re-run | `solver` |
| `reference_mismatch` | `human_fallback` | Needs Review | `human_fallback` |
| `unknown` | `human_fallback` | Needs Review | `human_fallback` |

## 3. Per-scenario verdicts

| Scenario | FaultClass | Verdict | Route | Pass |
|---|---|---|---|---|
| `geometry_invalid-fresh` | `geometry_invalid` | Re-run | `geometry` | ✅ |
| `geometry_invalid-mid-retry` | `geometry_invalid` | Re-run | `geometry` | ✅ |
| `geometry_invalid-budget-exhausted` | `geometry_invalid` | Re-run | `human_fallback` | ✅ |
| `mesh_jacobian-fresh` | `mesh_jacobian` | Re-run | `mesh` | ✅ |
| `mesh_jacobian-mid-retry` | `mesh_jacobian` | Re-run | `mesh` | ✅ |
| `mesh_jacobian-budget-exhausted` | `mesh_jacobian` | Re-run | `human_fallback` | ✅ |
| `mesh_resolution-fresh` | `mesh_resolution` | Re-run | `mesh` | ✅ |
| `mesh_resolution-mid-retry` | `mesh_resolution` | Re-run | `mesh` | ✅ |
| `mesh_resolution-budget-exhausted` | `mesh_resolution` | Re-run | `human_fallback` | ✅ |
| `solver_convergence-fresh` | `solver_convergence` | Re-run | `solver` | ✅ |
| `solver_convergence-mid-retry` | `solver_convergence` | Re-run | `solver` | ✅ |
| `solver_convergence-budget-exhausted` | `solver_convergence` | Re-run | `human_fallback` | ✅ |
| `solver_timestep-fresh` | `solver_timestep` | Re-run | `solver` | ✅ |
| `solver_timestep-mid-retry` | `solver_timestep` | Re-run | `solver` | ✅ |
| `solver_timestep-budget-exhausted` | `solver_timestep` | Re-run | `human_fallback` | ✅ |
| `solver_syntax-fresh` | `solver_syntax` | Re-run | `solver` | ✅ |
| `solver_syntax-mid-retry` | `solver_syntax` | Re-run | `solver` | ✅ |
| `solver_syntax-budget-exhausted` | `solver_syntax` | Re-run | `human_fallback` | ✅ |
| `reference_mismatch-fresh` | `reference_mismatch` | Needs Review | `human_fallback` | ✅ |
| `reference_mismatch-mid-retry` | `reference_mismatch` | Needs Review | `human_fallback` | ✅ |
| `reference_mismatch-budget-exhausted` | `reference_mismatch` | Needs Review | `human_fallback` | ✅ |
| `unknown-fresh` | `unknown` | Needs Review | `human_fallback` | ✅ |
| `unknown-mid-retry` | `unknown` | Needs Review | `human_fallback` | ✅ |
| `unknown-budget-exhausted` | `unknown` | Needs Review | `human_fallback` | ✅ |

## 4. Architectural findings surfaced by this baseline

- **REFERENCE_MISMATCH architect-loop is unreachable via the Reviewer path.** `agents.router.FAULT_TO_NODE` wires it to `architect`, but the Reviewer emits `verdict="Needs Review"` for REFERENCE_MISMATCH, and the Router only consults `FAULT_TO_NODE` when `verdict="Re-run"`. Observed routing lands on `human_fallback`. Flagged for ADR-004 follow-up; the fault_injection recovery table and router_mapping guards in the test suite now document this gap explicitly.

## 5. Traceability

- Source of truth: `schemas/fault_injection.py::FAULT_RECOVERY_TABLE`
- Battery generator: `tests/test_fault_injection.py::collect_injection_report`
- Drift guards: `TestAdr004Mirror`
- Per-scenario assertions: `TestInjectionBattery`
- Cross-cutting budget guards: `TestBudgetKeyingIsPerNode`
