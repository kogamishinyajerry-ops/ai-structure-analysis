"""Executor implementations for the well-harness orchestration layer."""

from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path
from typing import Protocol

from ..models.task_spec import TaskSpec
from .knowledge_store import GoldenSampleKnowledgeStore
from .schemas import ExecutorRunResult


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
        from tools.calculix_driver import run_solve

        inp_path = store.find_input_file(case_id)
        if inp_path is None:
            return ExecutorRunResult(
                success=False,
                executor_name="calculix_executor",
                frd_path="",
                output_dir=str(store.case_dir(case_id)),
                error_message=f"No .inp file found for {case_id}",
            )

        try:
            # Use the core driver which handles WSL detection and pathing
            solve_result = run_solve(inp_path=inp_path, work_dir=inp_path.parent)
            
            return ExecutorRunResult(
                success=solve_result["converged"],
                executor_name="calculix_executor",
                frd_path=solve_result["frd_path"] or "",
                output_dir=str(inp_path.parent),
                execution_time_s=solve_result["wall_time_s"],
                logs=[],  # logs are captured in driver now
                error_message=None if solve_result["converged"] else f"CalculiX error (code {solve_result['returncode']})",
            )
        except Exception as e:
            return ExecutorRunResult(
                success=False,
                executor_name="calculix_executor",
                frd_path="",
                output_dir=str(inp_path.parent),
                error_message=str(e),
            )
