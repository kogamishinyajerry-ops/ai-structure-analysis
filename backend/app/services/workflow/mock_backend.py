"""MockFEABackend — a synthetic-data implementation of the AERON FEABackend.

Implements the `aeron.protocols.fea_backend.FEABackend` Protocol with NO real
solver: `solve()` returns a plausible `SolveOutcome` without invoking `ccx`, and
`parse_results()` returns synthetic scalars (peak von Mises, displacement, safety
factor). This is the M1 stand-in that the Mock pipeline drives; at M4 the same
pipeline swaps this for `CalculiXFEABackend` with zero contract change.

`force_fault` lets the pipeline demo a solver-stage failure (e.g. non-convergence)
through the real status vocabulary instead of a special-cased error.
"""

from __future__ import annotations

from pathlib import Path

from aeron.protocols.fea_backend import (
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
from schemas.sim_plan import SimPlan
from schemas.sim_state import FaultClass

# Synthetic result scalars the mock "solve" reports — a bracket near yield.
_MOCK_MAX_VON_MISES_PA = 2.18e8
_MOCK_MAX_DISPLACEMENT_M = 3.4e-4
_MOCK_YIELD_PA = 2.5e8
_MOCK_WALL_CLOCK_S = 13.8


class MockFEABackend:
    """A FEABackend that fabricates outputs deterministically (no ccx).

    Conforms structurally to :class:`aeron.protocols.fea_backend.FEABackend`
    (verified by ``isinstance(MockFEABackend(), FEABackend)``).
    """

    solver_name = "mock-fea"
    solver_version = "0.1.0"

    def __init__(self, force_fault: FaultClass | None = None) -> None:
        # When set, solve() reports a failure with this fault class (demo path).
        self.force_fault = force_fault

    def prepare_case(self, plan: SimPlan) -> CasePackage:
        case_dir = Path("/tmp/mock-fea") / plan.case_id
        return CasePackage(
            case_id=plan.case_id,
            case_dir=case_dir,
            primary_input=case_dir / "solve.inp",
            metadata={"mock": True},
        )

    def solve(self, case: CasePackage, opts: SolveOptions) -> SolveOutcome:
        if self.force_fault is not None:
            return SolveOutcome(
                case_id=case.case_id,
                status=SolveStatus(
                    code=SolveStatusCode.DIVERGED,
                    fault_class=self.force_fault,
                    message="mock solver injected non-convergence",
                    returncode=1,
                ),
                wall_clock_s=_MOCK_WALL_CLOCK_S,
                metadata={"mock": True},
            )
        return SolveOutcome(
            case_id=case.case_id,
            status=SolveStatus(code=SolveStatusCode.OK, message="mock solve ok", returncode=0),
            wall_clock_s=_MOCK_WALL_CLOCK_S,
            raw_outputs={"frd": case.case_dir / "solve.frd"},
            metadata={"mock": True},
        )

    def parse_results(self, outcome: SolveOutcome) -> ResultBundle:
        return ResultBundle(
            case_id=outcome.case_id,
            scalars={
                "max_von_mises_pa": _MOCK_MAX_VON_MISES_PA,
                "max_displacement_m": _MOCK_MAX_DISPLACEMENT_M,
                "yield_pa": _MOCK_YIELD_PA,
                "safety_factor": _MOCK_YIELD_PA / _MOCK_MAX_VON_MISES_PA,
            },
            extras={"mock": True},
        )

    def health_check(self) -> HealthReport:
        return HealthReport(
            status=HealthStatus(
                healthy=True,
                solver_name=self.solver_name,
                solver_version=self.solver_version,
                detail="mock backend always healthy",
            ),
            checks={"binary_present": True},
        )


def _assert_protocol() -> None:
    """Import-time guard: MockFEABackend must satisfy the FEABackend Protocol."""
    assert isinstance(MockFEABackend(), FEABackend)


_assert_protocol()
