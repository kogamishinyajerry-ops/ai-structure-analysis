"""AERON FEABackend adapter for the OpenRadioss explicit-dynamics path.

Tier 1 engineering candidate. Not signed validation. Not benchmark agreement.

This adapter supports the FM-04a ballistic candidate workflow end-to-end:

    SimPlan(solver=openradioss) -> prepare_case() -> solve() -> parse_results()

The adapter is intentionally narrow:

* It owns deck *placement* (copy starter + engine decks into the case dir),
  but it does **not** render Jinja templates. Authoring deck content with
  Johnson-Cook plasticity / JC damage / element-deletion configuration is
  the responsibility of the deck author (FM-04a P3 + later authoring rounds
  under ADR-024 lite).
* It propagates a Tier 1 candidate claim-tier marker through metadata so
  downstream consumers (candidate report spine, Trust Center) cannot lose
  the ADR-023 wording boundary by accident.
* It does **not** parse residual velocity, perforation marker, or any
  ballistic engineering quantity from raw outputs. That is the job of
  FM-04a P6 metric extraction; this adapter only exposes raw output paths
  the way ``CalculiXFEABackend.parse_results`` does.

Forbidden wording reaffirmed (per ADR-023 + ADR-024 lite):

* not signed validation
* not benchmark agreement
* not "bullet-through-steel complete"
* not "steel perforation completed"
* not "validated physics"
* not "signed GS-102" / not "signed GS101"
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
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
from schemas.sim_plan import SimPlan, SolverBackend
from schemas.sim_state import FaultClass

BALLISTIC_CANDIDATE_TIER = "tier-1-engineering-candidate"
BALLISTIC_CANDIDATE_CLAIM_BOUNDARY = (
    "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"
)
BALLISTIC_CANDIDATE_DECK_DISCIPLINE = (
    "deck content must cite Johnson-Cook plasticity / damage parameters from "
    "Børvik 2002 Part II per ADR-024 (lite); no benchmark agreement is implied"
)
DEFAULT_TIMEOUT_S = 7200
RADIOSS_STARTER_CANDIDATES: tuple[str, ...] = (
    "starter_linux64_gf",
    "openradioss_starter",
    "starter",
    "radioss_starter",
)
RADIOSS_ENGINE_CANDIDATES: tuple[str, ...] = (
    "engine_linux64_gf",
    "openradioss_engine",
    "engine",
    "radioss_engine",
)
RADIOSS_OUTPUT_SUFFIXES: tuple[str, ...] = (".h3d", ".anim", ".out", ".rst", ".rad", ".A001")


RunSolve = Callable[..., dict[str, Any]]


class OpenRadiossFEABackend:
    """Narrow AERON wrapper around an OpenRadioss starter+engine invocation.

    The adapter takes explicit deck dependencies (starter + engine) at
    construction time. It does not author or template these decks; it only
    moves them into the case directory and shells out to the OpenRadioss
    binaries. Real solver invocation requires the binaries on PATH; tests
    drive ``opts.dry_run = True`` or supply an injected ``run_solve`` callable.
    """

    solver_name = "openradioss"

    def __init__(
        self,
        *,
        work_root: Path | str,
        starter_deck: Path | str,
        engine_deck: Path | str,
        run_solve: RunSolve | None = None,
        case_dir_name: str | None = None,
        starter_binary: str | None = None,
        engine_binary: str | None = None,
    ) -> None:
        self.work_root = Path(work_root)
        self.starter_deck = Path(starter_deck)
        self.engine_deck = Path(engine_deck)
        self._run_solve = run_solve
        self._case_dir_name = case_dir_name
        self._starter_binary = starter_binary
        self._engine_binary = engine_binary

    # -----------------------------------------------------------------
    # FEABackend protocol surface
    # -----------------------------------------------------------------

    def prepare_case(self, plan: SimPlan) -> CasePackage:
        """Place the starter + engine decks under ``work_root/case_dir``."""
        if plan.solver.name is not SolverBackend.OPENRADIOSS:
            raise ValueError(
                "OpenRadiossFEABackend requires plan.solver.name='openradioss', "
                f"got {plan.solver.name!r}."
            )
        if not self.starter_deck.exists():
            raise FileNotFoundError(f"starter_deck does not exist: {self.starter_deck}")
        if not self.engine_deck.exists():
            raise FileNotFoundError(f"engine_deck does not exist: {self.engine_deck}")

        case_dir = self.work_root / (self._case_dir_name or plan.case_id)
        case_dir.mkdir(parents=True, exist_ok=True)

        starter_dst = case_dir / self.starter_deck.name
        engine_dst = case_dir / self.engine_deck.name
        if self.starter_deck.resolve() != starter_dst.resolve():
            shutil.copy2(self.starter_deck, starter_dst)
        if self.engine_deck.resolve() != engine_dst.resolve():
            shutil.copy2(self.engine_deck, engine_dst)

        return CasePackage(
            case_id=plan.case_id,
            case_dir=case_dir,
            primary_input=starter_dst,
            artifacts={
                "starter_deck": starter_dst,
                "engine_deck": engine_dst,
            },
            metadata={
                "backend": self.solver_name,
                "claim_tier": BALLISTIC_CANDIDATE_TIER,
                "claim_boundary": BALLISTIC_CANDIDATE_CLAIM_BOUNDARY,
                "deck_discipline": BALLISTIC_CANDIDATE_DECK_DISCIPLINE,
                "starter_deck_source": str(self.starter_deck),
                "engine_deck_source": str(self.engine_deck),
            },
        )

    def solve(self, case: CasePackage, opts: SolveOptions) -> SolveOutcome:
        """Run OpenRadioss starter + engine, or preflight only."""
        if opts.dry_run:
            return SolveOutcome(
                case_id=case.case_id,
                status=SolveStatus(
                    code=SolveStatusCode.OK,
                    message="Dry run: OpenRadioss starter and engine were not invoked.",
                    returncode=0,
                ),
                wall_clock_s=0.0,
                metadata={
                    "dry_run": True,
                    "backend": self.solver_name,
                    "claim_tier": BALLISTIC_CANDIDATE_TIER,
                    "claim_boundary": BALLISTIC_CANDIDATE_CLAIM_BOUNDARY,
                    "primary_input": str(case.primary_input),
                },
            )

        if self._run_solve is not None:
            try:
                result = self._run_solve(
                    starter_deck=case.artifacts["starter_deck"],
                    engine_deck=case.artifacts["engine_deck"],
                    case_dir=case.case_dir,
                    timeout_s=int(opts.timeout_s) if opts.timeout_s else DEFAULT_TIMEOUT_S,
                )
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
                    metadata={"backend": self.solver_name, "claim_tier": BALLISTIC_CANDIDATE_TIER},
                )
            return self._outcome_from_driver_result(case, result)

        starter_bin = self._resolve_binary(
            self._starter_binary, RADIOSS_STARTER_CANDIDATES, "OpenRadioss starter"
        )
        engine_bin = self._resolve_binary(
            self._engine_binary, RADIOSS_ENGINE_CANDIDATES, "OpenRadioss engine"
        )

        if starter_bin is None or engine_bin is None:
            missing = [
                name
                for name, value in (("starter", starter_bin), ("engine", engine_bin))
                if value is None
            ]
            return SolveOutcome(
                case_id=case.case_id,
                status=SolveStatus(
                    code=SolveStatusCode.PREFLIGHT_FAILED,
                    fault_class=FaultClass.UNKNOWN,
                    message=(
                        f"OpenRadioss binaries missing on PATH: {', '.join(missing)}. "
                        "FM-04a Tier 1 candidate workflow requires OpenRadioss starter and engine "
                        "binaries; this is preflight only and not a benchmark agreement claim."
                    ),
                    returncode=None,
                ),
                wall_clock_s=0.0,
                metadata={
                    "backend": self.solver_name,
                    "claim_tier": BALLISTIC_CANDIDATE_TIER,
                    "preflight_missing": missing,
                },
            )

        return self._invoke_starter_engine(case, opts, starter_bin, engine_bin)

    def parse_results(self, outcome: SolveOutcome) -> ResultBundle:
        """Expose raw OpenRadioss output paths without deriving ballistic quantities."""
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
                "claim_tier": BALLISTIC_CANDIDATE_TIER,
                "claim_boundary": BALLISTIC_CANDIDATE_CLAIM_BOUNDARY,
                "extraction_note": (
                    "raw OpenRadioss outputs only; residual velocity, perforation marker, "
                    "and energy balance are extracted in FM-04a P6, not here"
                ),
            },
        )

    def health_check(self) -> HealthReport:
        """Probe whether OpenRadioss starter + engine are on PATH."""
        starter_bin = self._resolve_binary(
            self._starter_binary, RADIOSS_STARTER_CANDIDATES, "OpenRadioss starter"
        )
        engine_bin = self._resolve_binary(
            self._engine_binary, RADIOSS_ENGINE_CANDIDATES, "OpenRadioss engine"
        )
        starter_ok = starter_bin is not None
        engine_ok = engine_bin is not None
        if starter_ok and engine_ok:
            return HealthReport(
                status=HealthStatus(
                    healthy=True,
                    solver_name=self.solver_name,
                    detail=(
                        f"OpenRadioss starter='{starter_bin}', engine='{engine_bin}'. "
                        "Tier 1 candidate path; not signed validation."
                    ),
                ),
                checks={
                    "starter_on_path": True,
                    "engine_on_path": True,
                },
            )
        missing = [name for name, ok in (("starter", starter_ok), ("engine", engine_ok)) if not ok]
        return HealthReport(
            status=HealthStatus(
                healthy=False,
                solver_name=self.solver_name,
                detail=(
                    f"OpenRadioss binaries missing on PATH: {', '.join(missing)}. "
                    "FM-04a Tier 1 candidate workflow cannot run a real solve."
                ),
            ),
            checks={
                "starter_on_path": starter_ok,
                "engine_on_path": engine_ok,
            },
        )

    # -----------------------------------------------------------------
    # Internals
    # -----------------------------------------------------------------

    @staticmethod
    def _resolve_binary(
        explicit: str | None, candidates: tuple[str, ...], _label: str
    ) -> str | None:
        if explicit:
            located = shutil.which(explicit)
            return located if located else None
        for candidate in candidates:
            located = shutil.which(candidate)
            if located:
                return located
        return None

    def _invoke_starter_engine(
        self,
        case: CasePackage,
        opts: SolveOptions,
        starter_bin: str,
        engine_bin: str,
    ) -> SolveOutcome:
        timeout_s = int(opts.timeout_s) if opts.timeout_s else DEFAULT_TIMEOUT_S
        env = os.environ.copy()
        if opts.num_threads:
            env.setdefault("OMP_NUM_THREADS", str(opts.num_threads))
        started = time.time()
        try:
            starter_proc = subprocess.run(
                [starter_bin, "-i", str(case.artifacts["starter_deck"].name)],
                cwd=case.case_dir,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                check=False,
            )
            if starter_proc.returncode != 0:
                return self._failure_outcome(
                    case,
                    starter_proc.returncode,
                    f"OpenRadioss starter failed: {starter_proc.stderr.strip()}",
                    started,
                )
            engine_proc = subprocess.run(
                [engine_bin, "-i", str(case.artifacts["engine_deck"].name)],
                cwd=case.case_dir,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return self._failure_outcome(case, -1, f"OpenRadioss timed out: {exc}", started)
        except FileNotFoundError as exc:
            return self._failure_outcome(
                case, None, f"OpenRadioss binary disappeared mid-solve: {exc}", started
            )

        wall = time.time() - started
        raw_outputs = self._discover_outputs(case.case_dir)

        if engine_proc.returncode != 0:
            return SolveOutcome(
                case_id=case.case_id,
                status=SolveStatus(
                    code=SolveStatusCode.SOLVER_ERROR,
                    fault_class=FaultClass.UNKNOWN,
                    message=f"OpenRadioss engine failed: {engine_proc.stderr.strip()}",
                    returncode=engine_proc.returncode,
                ),
                wall_clock_s=wall,
                raw_outputs=raw_outputs,
                metadata={
                    "backend": self.solver_name,
                    "claim_tier": BALLISTIC_CANDIDATE_TIER,
                    "claim_boundary": BALLISTIC_CANDIDATE_CLAIM_BOUNDARY,
                    "starter_returncode": starter_proc.returncode,
                    "engine_returncode": engine_proc.returncode,
                },
            )

        return SolveOutcome(
            case_id=case.case_id,
            status=SolveStatus(
                code=SolveStatusCode.OK,
                message="OpenRadioss starter+engine completed (Tier 1 candidate).",
                returncode=engine_proc.returncode,
            ),
            wall_clock_s=wall,
            raw_outputs=raw_outputs,
            metadata={
                "backend": self.solver_name,
                "claim_tier": BALLISTIC_CANDIDATE_TIER,
                "claim_boundary": BALLISTIC_CANDIDATE_CLAIM_BOUNDARY,
                "starter_returncode": starter_proc.returncode,
                "engine_returncode": engine_proc.returncode,
            },
        )

    def _failure_outcome(
        self,
        case: CasePackage,
        returncode: int | None,
        message: str,
        started_at: float,
    ) -> SolveOutcome:
        return SolveOutcome(
            case_id=case.case_id,
            status=SolveStatus(
                code=SolveStatusCode.SOLVER_ERROR,
                fault_class=FaultClass.UNKNOWN,
                message=message,
                returncode=returncode,
            ),
            wall_clock_s=time.time() - started_at,
            raw_outputs=self._discover_outputs(case.case_dir),
            metadata={
                "backend": self.solver_name,
                "claim_tier": BALLISTIC_CANDIDATE_TIER,
                "claim_boundary": BALLISTIC_CANDIDATE_CLAIM_BOUNDARY,
            },
        )

    def _outcome_from_driver_result(
        self, case: CasePackage, result: dict[str, Any]
    ) -> SolveOutcome:
        raw_outputs = {
            key.removesuffix("_path"): Path(path)
            for key, path in result.items()
            if key.endswith("_path") and path
        }
        if not raw_outputs:
            raw_outputs = self._discover_outputs(case.case_dir)
        converged = bool(result.get("converged", True))
        status_code = SolveStatusCode.OK if converged else SolveStatusCode.SOLVER_ERROR
        message = (
            "" if converged else str(result.get("failure_reason") or "OpenRadioss solve failed.")
        )
        return SolveOutcome(
            case_id=case.case_id,
            status=SolveStatus(
                code=status_code,
                fault_class=None if converged else FaultClass.UNKNOWN,
                message=message,
                returncode=result.get("returncode"),
            ),
            wall_clock_s=float(result.get("wall_time_s") or 0.0),
            raw_outputs=raw_outputs,
            metadata={
                "backend": self.solver_name,
                "claim_tier": BALLISTIC_CANDIDATE_TIER,
                "claim_boundary": BALLISTIC_CANDIDATE_CLAIM_BOUNDARY,
                "openradioss_version": result.get("openradioss_version"),
                "converged": converged,
            },
        )

    @staticmethod
    def _discover_outputs(case_dir: Path) -> dict[str, Path]:
        outputs: dict[str, Path] = {}
        if not case_dir.exists():
            return outputs
        for path in sorted(case_dir.iterdir()):
            if not path.is_file():
                continue
            suffix = path.suffix.lower()
            if suffix in RADIOSS_OUTPUT_SUFFIXES:
                key = suffix.lstrip(".")
                outputs.setdefault(key, path)
        return outputs
