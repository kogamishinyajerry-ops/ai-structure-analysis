"""AERON FEABackend adapter for the existing CalculiX path."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

from aeron.protocols import (
    CasePackage,
    HealthReport,
    HealthStatus,
    ResultBundle,
    SolveOptions,
    SolveOutcome,
    SolveStatus,
    SolveStatusCode,
)
from agents.solver import _render_inp_deck
from schemas.sim_plan import SimPlan, SolverBackend
from schemas.sim_state import FaultClass
from tools import calculix_driver

RunSolve = Callable[..., dict[str, Any]]


class CalculiXFEABackend:
    """Narrow AERON wrapper around the existing CalculiX deck/solve path.

    The backend intentionally takes an explicit mesh ``.inp`` dependency at
    construction time. Current ``SimPlan`` objects do not carry a mesh/deck
    artifact path, so this adapter does not pretend to own upstream meshing.
    """

    solver_name = "calculix"

    def __init__(
        self,
        *,
        work_root: Path | str,
        mesh_input: Path | str,
        run_solve: RunSolve = calculix_driver.run_solve,
    ) -> None:
        self.work_root = Path(work_root)
        self.mesh_input = Path(mesh_input)
        self._run_solve = run_solve

    def prepare_case(self, plan: SimPlan) -> CasePackage:
        """Render ``solve.inp`` from ``plan`` and a constructor-provided mesh."""
        if plan.solver.name is not SolverBackend.CALCULIX:
            raise ValueError(
                f"CalculiXFEABackend requires plan.solver.name='calculix', "
                f"got {plan.solver.name!r}."
            )
        if not self.mesh_input.exists():
            raise FileNotFoundError(f"mesh_input does not exist: {self.mesh_input}")
        if self.mesh_input.suffix.lower() != ".inp":
            raise ValueError(f"mesh_input must be a .inp file: {self.mesh_input}")

        case_dir = self.work_root / plan.case_id
        case_dir.mkdir(parents=True, exist_ok=True)

        mesh_dst = case_dir / self.mesh_input.name
        if self.mesh_input.resolve() != mesh_dst.resolve():
            shutil.copy2(self.mesh_input, mesh_dst)

        primary_input = _render_inp_deck(plan, mesh_dst.name, case_dir)
        return CasePackage(
            case_id=plan.case_id,
            case_dir=case_dir,
            primary_input=primary_input,
            artifacts={"mesh_input": mesh_dst},
            metadata={
                "backend": self.solver_name,
                "source_mesh": str(self.mesh_input),
            },
        )

    def solve(self, case: CasePackage, opts: SolveOptions) -> SolveOutcome:
        """Run CalculiX through the existing driver, or preflight only."""
        if opts.dry_run:
            return SolveOutcome(
                case_id=case.case_id,
                status=SolveStatus(
                    code=SolveStatusCode.OK,
                    message="Dry run: CalculiX was not invoked.",
                    returncode=0,
                ),
                wall_clock_s=0.0,
                metadata={
                    "dry_run": True,
                    "backend": self.solver_name,
                    "primary_input": str(case.primary_input),
                },
            )

        timeout_s = (
            int(opts.timeout_s) if opts.timeout_s is not None else calculix_driver.DEFAULT_TIMEOUT_S
        )
        try:
            result = self._run_solve(case.primary_input, case.case_dir, timeout_s=timeout_s)
        except (FileNotFoundError, RuntimeError) as exc:
            return SolveOutcome(
                case_id=case.case_id,
                status=SolveStatus(
                    code=SolveStatusCode.PREFLIGHT_FAILED,
                    fault_class=FaultClass.UNKNOWN,
                    message=str(exc),
                    returncode=None,
                ),
                wall_clock_s=0.0,
                metadata={"backend": self.solver_name},
            )

        return self._outcome_from_driver_result(case, result)

    def parse_results(self, outcome: SolveOutcome) -> ResultBundle:
        """Expose raw output paths without deriving engineering quantities."""
        return ResultBundle(
            case_id=outcome.case_id,
            fields=dict(outcome.raw_outputs),
            scalars={},
            extras={
                "status_code": outcome.status.code.value,
                "fault_class": (
                    outcome.status.fault_class.value if outcome.status.fault_class else None
                ),
                "metadata": dict(outcome.metadata),
            },
        )

    def health_check(self) -> HealthReport:
        """Probe whether ``ccx`` is on PATH and version-readable."""
        ccx_bin = calculix_driver._find_ccx()
        if ccx_bin is None:
            return HealthReport(
                status=HealthStatus(
                    healthy=False,
                    solver_name=self.solver_name,
                    detail="CalculiX executable 'ccx' not found on PATH.",
                ),
                checks={"ccx_on_path": False, "version_readable": False},
            )

        version = calculix_driver._probe_ccx_version(ccx_bin)
        return HealthReport(
            status=HealthStatus(
                healthy=version is not None,
                solver_name=self.solver_name,
                solver_version=version,
                detail="" if version else "Unable to determine CalculiX version.",
            ),
            checks={"ccx_on_path": True, "version_readable": version is not None},
        )

    def _outcome_from_driver_result(
        self, case: CasePackage, result: dict[str, Any]
    ) -> SolveOutcome:
        raw_outputs = {
            key.removesuffix("_path"): Path(path)
            for key, path in result.items()
            if key.endswith("_path") and path
        }
        fault_class = result.get("fault_class")
        if not isinstance(fault_class, FaultClass):
            fault_class = None

        converged = bool(result.get("converged"))
        status_code = SolveStatusCode.OK if converged else self._failure_status_code(result)
        message = "" if converged else str(result.get("failure_reason") or "CalculiX solve failed.")

        return SolveOutcome(
            case_id=case.case_id,
            status=SolveStatus(
                code=status_code,
                fault_class=None if converged else fault_class,
                message=message,
                returncode=result.get("returncode"),
            ),
            wall_clock_s=float(result.get("wall_time_s") or 0.0),
            raw_outputs=raw_outputs,
            metadata={
                "backend": self.solver_name,
                "ccx_version": result.get("ccx_version"),
                "converged": converged,
            },
        )

    @staticmethod
    def _failure_status_code(result: dict[str, Any]) -> SolveStatusCode:
        failure_reason = str(result.get("failure_reason") or "").lower()
        if result.get("returncode") == -1 or "timed out" in failure_reason:
            return SolveStatusCode.TIMEOUT
        if result.get("fault_class") is FaultClass.SOLVER_CONVERGENCE:
            return SolveStatusCode.DIVERGED
        return SolveStatusCode.SOLVER_ERROR
