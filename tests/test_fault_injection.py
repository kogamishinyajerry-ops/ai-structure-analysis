"""P1-05 Reviewer fault-injection baseline.

Feeds the Reviewer synthetic upstream faults covering every ADR-004 fault
class across multiple realistic injection scenarios, then pipes the result
through ``route_reviewer`` to confirm the graph lands on the right recovery
node (or human_fallback when budgets are exhausted).

Design:
  * ``FAULT_RECOVERY_TABLE`` is the single source of truth used by tests —
    drift between Reviewer / Router code and ADR-004 is caught here.
  * Each fault class gets three scenarios (fresh injection, mid-retry,
    budget-exhausted) so the tests exercise the most common state shapes
    the graph will actually see at runtime.
  * A machine-readable summary is emitted via ``collect_injection_report``
    so ``scripts/p1_05_fault_injection_report.py`` can produce an artifact
    without duplicating logic.

This is a *baseline*. Later PRs can add real fault artifacts (malformed
decks, bad meshes, reference drift synthetic FRDs) — at that point the
scenario list here stays the same and just gains ``fixture_path`` fields.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest

from agents.reviewer import (
    RERUN_FAULTS,
    VERDICT_NEEDS_REVIEW,
    VERDICT_RERUN,
    run as reviewer_run,
)
from agents.router import FAULT_TO_NODE, MAX_RETRIES, route_reviewer
from schemas.fault_injection import (
    FAULT_RECOVERY_BY_CLASS,
    FAULT_RECOVERY_TABLE,
    FaultRecoveryContract,
    all_fault_classes_except_none,
)
from schemas.sim_state import FaultClass


@dataclass(frozen=True)
class InjectionScenario:
    """One synthetic state shape + the expected Reviewer+Router outcome."""

    scenario_id: str
    fault_class: FaultClass
    initial_retry_budgets: dict[str, int]
    expected_verdict: str
    expected_route: str
    description: str


def _scenarios_for(contract: FaultRecoveryContract) -> list[InjectionScenario]:
    """Generate the three canonical injection scenarios for a fault class."""
    fc = contract.fault_class
    budget_key = contract.budget_key
    scenarios = [
        InjectionScenario(
            scenario_id=f"{fc.value}-fresh",
            fault_class=fc,
            initial_retry_budgets={},
            expected_verdict=contract.expected_verdict,
            expected_route=contract.target_node,
            description=f"First-time injection of {fc.value}; budget=0; should route to {contract.target_node}.",
        ),
        InjectionScenario(
            scenario_id=f"{fc.value}-mid-retry",
            fault_class=fc,
            initial_retry_budgets={budget_key: MAX_RETRIES - 1},
            expected_verdict=contract.expected_verdict,
            expected_route=contract.target_node if fc in RERUN_FAULTS else contract.target_node,
            description=(
                f"{fc.value} with budget={MAX_RETRIES - 1}; last-chance retry; "
                f"should still route to {contract.target_node}."
            ),
        ),
        InjectionScenario(
            scenario_id=f"{fc.value}-budget-exhausted",
            fault_class=fc,
            initial_retry_budgets={budget_key: MAX_RETRIES},
            expected_verdict=contract.expected_verdict,
            # Exhausted budget: Re-run faults fall to human_fallback. Non-Re-run
            # faults were already heading to human_fallback / architect anyway.
            expected_route=(
                "human_fallback"
                if fc in RERUN_FAULTS
                else contract.target_node
            ),
            description=(
                f"{fc.value} with budget={MAX_RETRIES} (exhausted); "
                "Re-run faults must escape to human_fallback."
            ),
        ),
    ]
    return scenarios


def _all_scenarios() -> list[InjectionScenario]:
    return [s for c in FAULT_RECOVERY_TABLE for s in _scenarios_for(c)]


def _base_state(plan_ref_values: dict[str, float] | None = None) -> dict[str, Any]:
    """Minimal SimState dict sufficient for the Reviewer's upstream-fault branch."""
    plan = MagicMock()
    plan.reference_values = plan_ref_values or {"displacement": 1.0e-3}
    return {
        "plan": plan,
        "frd_path": "/dev/null/fake.frd",
        "artifacts": [],
        "retry_budgets": {},
        "history": [],
        "fault_class": FaultClass.NONE,
    }


# ---------------------------------------------------------------------------
# Drift guards — fail loudly if ADR-004 mirror and code disagree.
# ---------------------------------------------------------------------------


class TestAdr004Mirror:
    """The recovery table must stay in sync with Reviewer + Router code."""

    def test_every_rerun_fault_in_recovery_table(self):
        for fc in RERUN_FAULTS:
            assert fc in FAULT_RECOVERY_BY_CLASS, (
                f"{fc.value} is in agents.reviewer.RERUN_FAULTS but missing "
                "from FAULT_RECOVERY_TABLE — ADR-004 mirror drift."
            )

    def test_router_mapping_matches_recovery_table_for_rerun_faults(self):
        """For every Re-run fault, Router's raw mapping must equal the recovery contract.

        REFERENCE_MISMATCH is excluded: its Router mapping ("architect") is wired
        but unreachable via the Reviewer path today (see NOTE in fault_injection).
        """
        for contract in FAULT_RECOVERY_TABLE:
            if contract.fault_class == FaultClass.REFERENCE_MISMATCH:
                continue
            assert FAULT_TO_NODE.get(contract.fault_class) == contract.target_node, (
                f"{contract.fault_class.value}: router says "
                f"{FAULT_TO_NODE.get(contract.fault_class)!r}, recovery table "
                f"says {contract.target_node!r} — ADR-004 mirror drift."
            )

    def test_reference_mismatch_architect_mapping_is_present_but_unreachable(self):
        """Regression guard: if someone ever wires REFERENCE_MISMATCH → Re-run,
        they must update both the Router mapping AND the recovery table together.
        """
        assert FAULT_TO_NODE.get(FaultClass.REFERENCE_MISMATCH) == "architect", (
            "Router still maps REFERENCE_MISMATCH → architect; keep this "
            "assertion in sync with agents/router.py."
        )
        # Observed behavior via the Reviewer path lands on human_fallback.
        assert (
            FAULT_RECOVERY_BY_CLASS[FaultClass.REFERENCE_MISMATCH].target_node
            == "human_fallback"
        )

    def test_every_rerun_fault_has_rerun_verdict(self):
        for contract in FAULT_RECOVERY_TABLE:
            if contract.fault_class in RERUN_FAULTS:
                assert contract.expected_verdict == VERDICT_RERUN
            else:
                assert contract.expected_verdict == VERDICT_NEEDS_REVIEW

    def test_adr_004_enumerates_eight_fault_classes(self):
        # ADR-004 explicitly names 8 fault_classes; NONE is the "no fault" tag.
        assert len(all_fault_classes_except_none()) == 8


# ---------------------------------------------------------------------------
# Per-scenario injection battery.
# ---------------------------------------------------------------------------


class TestInjectionBattery:
    @pytest.mark.parametrize(
        "scenario",
        _all_scenarios(),
        ids=lambda s: s.scenario_id,
    )
    def test_reviewer_plus_router_produces_expected_route(self, scenario: InjectionScenario):
        state = _base_state()
        state["fault_class"] = scenario.fault_class
        state["retry_budgets"] = dict(scenario.initial_retry_budgets)

        # Reviewer stage — propagates upstream fault.
        review_result = reviewer_run(state)
        assert review_result["verdict"] == scenario.expected_verdict, (
            f"Reviewer verdict wrong for {scenario.scenario_id}: "
            f"got {review_result['verdict']!r}, expected {scenario.expected_verdict!r}"
        )
        assert review_result["fault_class"] == scenario.fault_class

        # Router stage — threads Reviewer output back into state and routes.
        routed_state = dict(state)
        routed_state.update(review_result)
        next_node = route_reviewer(routed_state)
        assert next_node == scenario.expected_route, (
            f"Router landed wrong for {scenario.scenario_id}: "
            f"got {next_node!r}, expected {scenario.expected_route!r}"
        )

    def test_battery_covers_every_fault_class_exactly_three_times(self):
        all_scenarios = _all_scenarios()
        counts: dict[FaultClass, int] = {}
        for s in all_scenarios:
            counts[s.fault_class] = counts.get(s.fault_class, 0) + 1
        for fc in all_fault_classes_except_none():
            assert counts.get(fc) == 3, f"{fc.value} has {counts.get(fc, 0)} scenarios, expected 3."


# ---------------------------------------------------------------------------
# Cross-cutting: budget keying is per-node, not per-fault-class.
# ---------------------------------------------------------------------------


class TestBudgetKeyingIsPerNode:
    def test_mesh_jacobian_and_resolution_share_mesh_budget(self):
        """Both mesh-bucket fault_classes must draw from the same budget key."""
        state = _base_state()
        state["fault_class"] = FaultClass.MESH_JACOBIAN
        state["retry_budgets"] = {"mesh": MAX_RETRIES}

        review_result = reviewer_run(state)
        routed = dict(state)
        routed.update(review_result)
        assert route_reviewer(routed) == "human_fallback"

        # Same exhaustion applies to MESH_RESOLUTION.
        state["fault_class"] = FaultClass.MESH_RESOLUTION
        review_result = reviewer_run(state)
        routed = dict(state)
        routed.update(review_result)
        assert route_reviewer(routed) == "human_fallback"

    def test_solver_family_shares_solver_budget(self):
        """SOLVER_CONVERGENCE / TIMESTEP / SYNTAX all charge the 'solver' budget."""
        for fc in (
            FaultClass.SOLVER_CONVERGENCE,
            FaultClass.SOLVER_TIMESTEP,
            FaultClass.SOLVER_SYNTAX,
        ):
            state = _base_state()
            state["fault_class"] = fc
            state["retry_budgets"] = {"solver": MAX_RETRIES}
            review_result = reviewer_run(state)
            routed = dict(state)
            routed.update(review_result)
            assert route_reviewer(routed) == "human_fallback", (
                f"{fc.value} with exhausted solver budget should escape to human_fallback."
            )

    def test_geometry_budget_independent_of_mesh(self):
        """Exhausted mesh budget must not block a geometry retry."""
        state = _base_state()
        state["fault_class"] = FaultClass.GEOMETRY_INVALID
        state["retry_budgets"] = {"mesh": MAX_RETRIES}

        review_result = reviewer_run(state)
        routed = dict(state)
        routed.update(review_result)
        assert route_reviewer(routed) == "geometry"


# ---------------------------------------------------------------------------
# Public helper consumed by scripts/p1_05_fault_injection_report.py.
# ---------------------------------------------------------------------------


def collect_injection_report() -> dict[str, Any]:
    """Run every scenario once and return a structured summary for the report."""
    rows: list[dict[str, Any]] = []
    for scenario in _all_scenarios():
        state = _base_state()
        state["fault_class"] = scenario.fault_class
        state["retry_budgets"] = dict(scenario.initial_retry_budgets)
        review_result = reviewer_run(state)
        routed = dict(state)
        routed.update(review_result)
        actual_route = route_reviewer(routed)
        rows.append(
            {
                "scenario_id": scenario.scenario_id,
                "fault_class": scenario.fault_class.value,
                "initial_budget": dict(scenario.initial_retry_budgets),
                "verdict": review_result["verdict"],
                "expected_verdict": scenario.expected_verdict,
                "route": actual_route,
                "expected_route": scenario.expected_route,
                "pass": (
                    review_result["verdict"] == scenario.expected_verdict
                    and actual_route == scenario.expected_route
                ),
                "description": scenario.description,
            }
        )
    total = len(rows)
    passed = sum(1 for r in rows if r["pass"])
    return {
        "total_scenarios": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate_pct": round(100 * passed / max(total, 1), 2),
        "rows": rows,
    }


def test_collect_injection_report_all_pass():
    """If the Reviewer+Router chain is correct, every scenario in the battery passes."""
    report = collect_injection_report()
    assert report["failed"] == 0, (
        f"Injection battery regressed: {report['failed']}/{report['total_scenarios']} failed."
    )
    assert report["pass_rate_pct"] == 100.0
