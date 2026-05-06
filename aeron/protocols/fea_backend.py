"""AERON L0 FEABackend protocol contract.

The contract is intentionally narrow: prepare a canonical ``SimPlan`` into a
solver-ready case, run a solver, parse raw outputs, and report backend health.
Concrete adapters live outside this module.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from schemas.sim_plan import SimPlan
from schemas.sim_state import FaultClass

_STRICT = ConfigDict(extra="forbid")


class SolveStatusCode(StrEnum):
    """Closed vocabulary for solver-agnostic solve outcomes."""

    OK = "ok"
    DIVERGED = "diverged"
    TIMEOUT = "timeout"
    PREFLIGHT_FAILED = "preflight_failed"
    SOLVER_ERROR = "solver_error"
    ABORTED = "aborted"


class SolveStatus(BaseModel):
    """Status summary for a single solve invocation."""

    model_config = _STRICT

    code: SolveStatusCode = Field(..., description="High-level, solver-agnostic outcome.")
    fault_class: FaultClass | None = Field(
        default=None,
        description="ADR-004 fault class when the driver can classify the failure.",
    )
    message: str = Field(default="", description="Human-readable detail.")
    returncode: int | None = Field(
        default=None,
        description=(
            "Underlying solver process return code, matching "
            "subprocess.CompletedProcess.returncode and the existing "
            "tools.calculix_driver.run_solve() payload key."
        ),
    )


class HealthStatus(BaseModel):
    """Outcome of a backend self-test."""

    model_config = _STRICT

    healthy: bool
    solver_name: str
    solver_version: str | None = None
    detail: str = ""


class CasePackage(BaseModel):
    """A prepared, solver-ready input bundle."""

    model_config = _STRICT

    case_id: str = Field(..., description="Mirrors SimPlan.case_id.")
    case_dir: Path = Field(..., description="Root directory containing prepared inputs.")
    primary_input: Path = Field(..., description="File the solver is invoked against.")
    artifacts: dict[str, Path] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SolveOptions(BaseModel):
    """Universal runtime knobs shared across solver families."""

    model_config = _STRICT

    timeout_s: float | None = Field(default=None, ge=0.0)
    num_threads: int | None = Field(default=None, ge=1)
    dry_run: bool = False
    artifact_dir: Path | None = None


class SolveOutcome(BaseModel):
    """Raw solve outcome before result parsing."""

    model_config = _STRICT

    case_id: str
    status: SolveStatus
    wall_clock_s: float = Field(ge=0.0)
    raw_outputs: dict[str, Path] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResultBundle(BaseModel):
    """Structured fields and scalars parsed from raw solver outputs."""

    model_config = _STRICT

    case_id: str
    fields: dict[str, Path] = Field(default_factory=dict)
    scalars: dict[str, float] = Field(default_factory=dict)
    extras: dict[str, Any] = Field(default_factory=dict)


class HealthReport(BaseModel):
    """Result of ``health_check``."""

    model_config = _STRICT

    status: HealthStatus
    checks: dict[str, bool] = Field(default_factory=dict)


@runtime_checkable
class FEABackend(Protocol):
    """Structural protocol for finite-element backends."""

    def prepare_case(self, plan: SimPlan) -> CasePackage:
        """Translate a SimPlan into a solver-ready bundle without solving."""
        ...

    def solve(self, case: CasePackage, opts: SolveOptions) -> SolveOutcome:
        """Run the solver and return raw outputs plus status."""
        ...

    def parse_results(self, outcome: SolveOutcome) -> ResultBundle:
        """Extract structured result fields and scalars from raw outputs."""
        ...

    def health_check(self) -> HealthReport:
        """Verify the backend is reachable and healthy."""
        ...
