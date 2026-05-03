"""AERON L0 · FEABackend protocol contract.

Per §05 four-field discipline:

目的 (Purpose)
    Define a single, solver-agnostic contract that any finite-element backend
    (CalculiX, FEniCS, future drivers) must satisfy to plug into AERON's
    higher layers (orchestrators, agents, dashboards). The contract is
    deliberately minimal: prepare → solve → parse → health.

接口 (Interface)
    A `typing.Protocol` named ``FEABackend`` with four methods. All inputs
    and outputs are plain Pydantic v2 models defined in this module so the
    contract is stable, importable, and serialisable across processes.

不该做 (Out of scope)
    - This file does not implement any solver. Implementations live under
      ``aeron/drivers/<name>/adapter.py``.
    - It does not import LangGraph, agents, the well_harness, or any
      runtime concern. Drivers wire those in.
    - It does not own filesystem layout decisions; ``case_dir`` and
      ``artifact_dir`` are advisory and resolved by the driver.
    - It does not dictate logging, telemetry, or Notion sync — those are
      orchestration concerns at L2+.

反例 (Anti-patterns)
    - ❌ Re-defining ``SimPlan`` here. Reuse ``schemas.sim_plan.SimPlan``;
      the protocol is downstream of the canonical contract.
    - ❌ Passing raw filesystem paths between methods. Use ``CasePackage``
      and ``SolveOutcome`` so the data flow is typed and inspectable.
    - ❌ Subclassing this Protocol. Use structural typing — drivers just
      need to implement the methods with matching signatures.
    - ❌ Adding solver-specific knobs (e.g. CalculiX increment count) to
      ``SolveOptions``. Solver-specific configuration belongs in the
      driver's own constructor.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from schemas.sim_plan import SimPlan
from schemas.sim_state import FaultClass

# All carriers reject unknown keys. This makes adapter-boundary version
# skew loud (ValidationError) instead of silently dropping fields — e.g.
# forwarding ``tools.calculix_driver.run_solve()``'s legacy dict shape
# directly into ``SolveStatus`` will fail fast on stale keys, forcing
# the driver to do the explicit mapping.
_STRICT = ConfigDict(extra="forbid")

# ---------------------------------------------------------------------------
# Status enums (string-valued; serialise cleanly)
# ---------------------------------------------------------------------------


class SolveStatusCode(StrEnum):
    """Closed vocabulary for ``SolveStatus.code``.

    Higher layers branch on this finite set; an unconstrained string would
    let driver typos (e.g. ``"timeot"``) cross process boundaries silently.
    """

    OK = "ok"
    DIVERGED = "diverged"
    TIMEOUT = "timeout"
    PREFLIGHT_FAILED = "preflight_failed"
    SOLVER_ERROR = "solver_error"
    ABORTED = "aborted"


class SolveStatus(BaseModel):
    """Outcome status of a single solve invocation.

    ``code`` is the solver-agnostic high-level outcome (six-value closed
    enum). ``fault_class`` carries the project's ADR-004 fault taxonomy
    (``FaultClass``) so downstream consumers like
    ``backend/app/rag/reviewer_advisor.py`` keep their existing
    fine-grained branching (``solver_syntax`` vs ``solver_timestep`` vs
    ``solver_convergence``) without the L0 protocol enum being polluted
    by solver-specific concerns. Drivers map their native classifications
    onto ``FaultClass`` at the adapter boundary.
    """

    model_config = _STRICT

    code: SolveStatusCode = Field(..., description="High-level, solver-agnostic outcome.")
    fault_class: FaultClass | None = Field(
        default=None,
        description=(
            "Project ADR-004 fault taxonomy. ``None`` when ``code == OK`` or "
            "when the driver cannot classify the failure."
        ),
    )
    message: str = Field(default="", description="Human-readable detail.")
    returncode: int | None = Field(
        default=None,
        description=(
            "Underlying solver process return code, if applicable. Matches "
            "Python ``subprocess.CompletedProcess.returncode`` and the "
            "existing ``tools.calculix_driver.run_solve()`` payload key."
        ),
    )


class HealthStatus(BaseModel):
    """Outcome of a backend self-test."""

    model_config = _STRICT

    healthy: bool
    solver_name: str
    solver_version: str | None = None
    detail: str = ""


# ---------------------------------------------------------------------------
# Data carriers between protocol methods
# ---------------------------------------------------------------------------


class CasePackage(BaseModel):
    """A prepared, solver-ready bundle.

    The driver decides what files exist on disk; this carrier just records
    where they live and any metadata the orchestrator needs without reading
    them.
    """

    model_config = _STRICT

    case_id: str = Field(..., description="Mirrors ``SimPlan.case_id``.")
    case_dir: Path = Field(..., description="Root directory containing all prepared inputs.")
    primary_input: Path = Field(
        ..., description="The single file the solver is invoked against (e.g. .inp)."
    )
    artifacts: dict[str, Path] = Field(
        default_factory=dict,
        description="Named auxiliary files the driver may want to surface (mesh, summary, etc.).",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Driver-defined context (mesh stats, element count, etc.). Opaque to AERON.",
    )


class SolveOptions(BaseModel):
    """Runtime knobs that are universal across solvers.

    Solver-specific knobs (e.g. CalculiX increment count, FEniCS quadrature
    degree) belong in the driver's constructor, not here.
    """

    model_config = _STRICT

    timeout_s: float | None = Field(default=None, ge=0.0, description="Hard wall-clock cap.")
    num_threads: int | None = Field(default=None, ge=1, description="Solver thread hint.")
    dry_run: bool = Field(
        default=False,
        description="If True, the driver should validate inputs but not execute the solver.",
    )
    artifact_dir: Path | None = Field(
        default=None,
        description="Where the driver should write logs and intermediate output. None = case_dir.",
    )


class SolveOutcome(BaseModel):
    """What ``solve`` returns. Raw artefacts only — parsing is a separate step."""

    model_config = _STRICT

    case_id: str
    status: SolveStatus
    wall_clock_s: float = Field(ge=0.0)
    raw_outputs: dict[str, Path] = Field(
        default_factory=dict,
        description="Named raw files produced by the solver (e.g. .frd, .dat, .log).",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResultBundle(BaseModel):
    """Structured results extracted from raw solver output.

    The shape is intentionally permissive: AERON's reviewer/reporter layers
    consume ``fields`` and ``scalars``; drivers may add solver-specific keys
    under ``extras`` without breaking the contract. Note ``extras`` is
    ``dict[str, Any]`` by design — extra **keys at the model level** are
    forbidden, but the ``extras`` dict itself is the explicit escape hatch.
    """

    model_config = _STRICT

    case_id: str
    fields: dict[str, Path] = Field(
        default_factory=dict,
        description="Named field exports (e.g. 'displacement' → Path to VTP/VTU).",
    )
    scalars: dict[str, float] = Field(
        default_factory=dict,
        description="Named scalar metrics (e.g. 'max_displacement_m', 'max_von_mises_pa').",
    )
    extras: dict[str, Any] = Field(default_factory=dict)


class HealthReport(BaseModel):
    """Result of ``health_check``."""

    model_config = _STRICT

    status: HealthStatus
    checks: dict[str, bool] = Field(
        default_factory=dict,
        description="Named sub-check results (e.g. 'binary_present', 'license_ok').",
    )


# ---------------------------------------------------------------------------
# The protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class FEABackend(Protocol):
    """AERON L0 contract for a finite-element backend.

    Drivers do not need to inherit from this class — structural conformance
    is sufficient. Use ``isinstance(driver, FEABackend)`` for runtime checks
    thanks to ``@runtime_checkable``.
    """

    def prepare_case(self, plan: SimPlan) -> CasePackage:
        """Translate a ``SimPlan`` into a solver-ready bundle on disk.

        Must be deterministic given identical inputs (modulo timestamps and
        absolute paths). Must not invoke the solver.
        """
        ...

    def solve(self, case: CasePackage, opts: SolveOptions) -> SolveOutcome:
        """Run the solver against a prepared case.

        Must respect ``opts.timeout_s`` and ``opts.dry_run``. Failures are
        reported via ``SolveOutcome.status``, not by raising — exceptions
        are reserved for programmer errors (bad input shape, missing files
        the driver itself was supposed to create).
        """
        ...

    def parse_results(self, outcome: SolveOutcome) -> ResultBundle:
        """Extract structured results from raw solver output.

        Must be a pure function of the outcome's ``raw_outputs``; no extra
        solver invocation is allowed here.
        """
        ...

    def health_check(self) -> HealthReport:
        """Self-test: verify the solver is reachable and licensed.

        Cheap (sub-second). Safe to call repeatedly. Must not produce
        side-effect files outside a tempdir.
        """
        ...
