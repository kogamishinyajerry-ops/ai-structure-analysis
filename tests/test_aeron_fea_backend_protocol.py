"""Tests for the AERON L0 FEABackend protocol contract.

This salvages the protocol portion of blocked PR #126 without inheriting its
governance changes. The tests pin the driver boundary behavior needed before
any concrete AERON adapter lands.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from schemas.sim_plan import SimPlan
from schemas.sim_state import FaultClass


def test_protocol_exports_public_contract() -> None:
    from aeron.protocols import (
        CasePackage,
        FEABackend,
        HealthReport,
        HealthStatus,
        ResultBundle,
        SolveOptions,
        SolveOutcome,
        SolveStatus,
        SolveStatusCode,
    )

    assert FEABackend.__name__ == "FEABackend"
    assert SolveStatusCode.OK == "ok"
    assert CasePackage.__name__ == "CasePackage"
    assert SolveOptions.__name__ == "SolveOptions"
    assert SolveOutcome.__name__ == "SolveOutcome"
    assert ResultBundle.__name__ == "ResultBundle"
    assert HealthStatus.__name__ == "HealthStatus"
    assert HealthReport.__name__ == "HealthReport"
    assert SolveStatus.__name__ == "SolveStatus"


def test_driver_structurally_satisfies_protocol(tmp_path: Path) -> None:
    from aeron.protocols import (
        CasePackage,
        FEABackend,
        HealthReport,
        HealthStatus,
        ResultBundle,
        SolveOptions,
        SolveOutcome,
        SolveStatus,
        SolveStatusCode,
    )

    class DummyBackend:
        def prepare_case(self, plan: SimPlan) -> CasePackage:
            case_dir = tmp_path / plan.case_id
            case_dir.mkdir()
            primary = case_dir / "case.inp"
            primary.write_text("*HEADING\n", encoding="utf-8")
            return CasePackage(case_id=plan.case_id, case_dir=case_dir, primary_input=primary)

        def solve(self, case: CasePackage, opts: SolveOptions) -> SolveOutcome:
            assert opts.dry_run is True
            return SolveOutcome(
                case_id=case.case_id,
                status=SolveStatus(code=SolveStatusCode.OK, returncode=0),
                wall_clock_s=0.0,
            )

        def parse_results(self, outcome: SolveOutcome) -> ResultBundle:
            return ResultBundle(case_id=outcome.case_id, scalars={"max_von_mises_pa": 1.0})

        def health_check(self) -> HealthReport:
            return HealthReport(status=HealthStatus(healthy=True, solver_name="dummy"))

    driver = DummyBackend()
    assert isinstance(driver, FEABackend)


def test_solve_status_rejects_unknown_status_code() -> None:
    from aeron.protocols import SolveStatus

    with pytest.raises(ValidationError):
        SolveStatus(code="timeot")


def test_solve_status_preserves_fault_class_and_returncode() -> None:
    from aeron.protocols import SolveStatus, SolveStatusCode

    status = SolveStatus(
        code=SolveStatusCode.SOLVER_ERROR,
        fault_class=FaultClass.SOLVER_SYNTAX,
        message="bad keyword",
        returncode=1,
    )

    assert status.fault_class is FaultClass.SOLVER_SYNTAX
    assert status.returncode == 1


@pytest.mark.parametrize(
    "model,payload",
    [
        ("SolveStatus", {"code": "ok", "stale": "nope"}),
        (
            "CasePackage",
            {
                "case_id": "case-1",
                "case_dir": Path("."),
                "primary_input": Path("case.inp"),
                "stale": "nope",
            },
        ),
        ("SolveOptions", {"dry_run": True, "stale": "nope"}),
        (
            "SolveOutcome",
            {
                "case_id": "case-1",
                "status": {"code": "ok"},
                "wall_clock_s": 0.0,
                "stale": "nope",
            },
        ),
        ("ResultBundle", {"case_id": "case-1", "stale": "nope"}),
        (
            "HealthStatus",
            {"healthy": True, "solver_name": "dummy", "stale": "nope"},
        ),
        (
            "HealthReport",
            {"status": {"healthy": True, "solver_name": "dummy"}, "stale": "nope"},
        ),
    ],
)
def test_protocol_carriers_reject_unknown_top_level_keys(
    model: str, payload: dict[str, object]
) -> None:
    import aeron.protocols as protocols

    cls = getattr(protocols, model)
    with pytest.raises(ValidationError):
        cls.model_validate(payload)


def test_solve_status_rejects_legacy_return_code_key() -> None:
    from aeron.protocols import SolveStatus

    with pytest.raises(ValidationError):
        SolveStatus.model_validate({"code": "ok", "return_code": 0})
