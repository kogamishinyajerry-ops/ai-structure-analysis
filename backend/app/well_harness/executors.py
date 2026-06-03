"""Executor implementations for the well-harness orchestration layer."""

from __future__ import annotations

import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Protocol

from ..models.task_spec import TaskSpec
from .knowledge_store import GoldenSampleKnowledgeStore
from .schemas import ExecutorRunResult

# ADR-011 §HF1.7a signed-registry guard. CalculiXRunner + the solver route
# already hard-stop signed cases; CalculixExecutor was the missing path (M2
# threat model P2). Pattern mirrors backend/app/adapters/calculix/runner.py.
_SIGNED_REGISTRY_PATTERN = re.compile(r"^GS-\d{3}$")


class StructuralExecutor(Protocol):
    """Protocol shared by replay and live executors."""

    def execute(
        self,
        case_id: str,
        task_spec: TaskSpec,
        store: GoldenSampleKnowledgeStore,
    ) -> ExecutorRunResult:
        ...


class ReplayExecutor:
    """Use an existing FRD file as the executor surface."""

    def execute(
        self,
        case_id: str,
        task_spec: TaskSpec,
        store: GoldenSampleKnowledgeStore,
    ) -> ExecutorRunResult:
        frd_path = store.find_result_file(case_id)
        return ExecutorRunResult(
            success=True,
            executor_name="replay_executor",
            frd_path=str(frd_path),
            output_dir=str(frd_path.parent),
            is_replay=True,
        )


class CalculixExecutor:
    """Launch CalculiX directly when a local runtime is available."""

    def __init__(self, ccx_path: str = "ccx") -> None:
        self.ccx_path = ccx_path

    def execute(
        self,
        case_id: str,
        task_spec: TaskSpec,
        store: GoldenSampleKnowledgeStore,
    ) -> ExecutorRunResult:
        # HF1.7a hard-stop: never launch ccx inside a signed golden_samples dir
        # (would overwrite the sealed .frd/.dat/.cvg/.sta reproducibility
        # evidence). Enforced here so CLI/test paths respect it independent of
        # the API-boundary check.
        if _SIGNED_REGISTRY_PATTERN.fullmatch(case_id):
            raise ValueError(
                f"refused to run CalculiX on signed-registry case {case_id!r} "
                f"(ADR-011 §HF1.7a hard-stop)"
            )
        inp_path = store.find_input_file(case_id)
        if inp_path is None:
            return ExecutorRunResult(
                success=False,
                executor_name="calculix_executor",
                frd_path="",
                output_dir=str(store.case_dir(case_id)),
                error_message=f"No .inp file found for {case_id}",
            )

        resolved_ccx = shutil.which(self.ccx_path) or self.ccx_path
        if not Path(resolved_ccx).exists() and shutil.which(self.ccx_path) is None:
            return ExecutorRunResult(
                success=False,
                executor_name="calculix_executor",
                frd_path="",
                output_dir=str(inp_path.parent),
                error_message=f"CalculiX executable not found: {self.ccx_path}",
            )

        started = time.perf_counter()
        completed = subprocess.run(
            [resolved_ccx, inp_path.stem],
            cwd=inp_path.parent,
            capture_output=True,
            text=True,
        )
        duration = time.perf_counter() - started

        frd_candidates = sorted(inp_path.parent.glob("*.frd"), key=lambda path: path.stat().st_mtime)
        frd_path = frd_candidates[-1] if frd_candidates else None
        logs = [line for line in (completed.stdout + "\n" + completed.stderr).splitlines() if line.strip()]

        return ExecutorRunResult(
            success=completed.returncode == 0 and frd_path is not None,
            executor_name="calculix_executor",
            frd_path="" if frd_path is None else str(frd_path),
            output_dir=str(inp_path.parent),
            execution_time_s=duration,
            logs=logs[-50:],
            error_message=None
            if completed.returncode == 0 and frd_path is not None
            else f"CalculiX run failed with code {completed.returncode}",
        )
