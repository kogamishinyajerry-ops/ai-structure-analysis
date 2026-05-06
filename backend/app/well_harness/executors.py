"""Executor implementations for the well-harness orchestration layer."""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Protocol
from unittest.mock import patch

from schemas.sim_plan import (
    BCSpec,
    GeometrySpec,
    LoadSpec,
    MaterialSpec,
    ObjectiveSpec,
    SimPlan,
)
from schemas.sim_state import FaultClass

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
        work_dir: Path | None = None,
    ) -> ExecutorRunResult: ...


class ReplayExecutor:
    """Use an existing FRD file as the executor surface."""

    def execute(
        self,
        case_id: str,
        task_spec: TaskSpec,
        store: GoldenSampleKnowledgeStore,
        work_dir: Path | None = None,
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
        work_dir: Path | None = None,
    ) -> ExecutorRunResult:
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

        frd_candidates = sorted(
            inp_path.parent.glob("*.frd"),
            key=lambda path: path.stat().st_mtime,
        )
        frd_path = frd_candidates[-1] if frd_candidates else None
        logs = [
            line
            for line in (completed.stdout + "\n" + completed.stderr).splitlines()
            if line.strip()
        ]

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


class GraphExecutor:
    """Run the existing LangGraph pipeline with replayed external tool surfaces.

    This executor is intentionally a cold-smoke adoption point. It exercises the
    graph and AERON-backed solver boundary without requiring FreeCAD, Gmsh,
    ccx, Notion, or signed-validation fixtures.
    """

    def execute(
        self,
        case_id: str,
        task_spec: TaskSpec,
        store: GoldenSampleKnowledgeStore,
        work_dir: Path | None = None,
    ) -> ExecutorRunResult:
        output_dir = work_dir or (Path.cwd() / "project_state" / "graph_executor" / case_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        run_id = _run_id_from_output_dir(output_dir, case_id)

        try:
            source_frd = store.find_result_file(case_id)
        except FileNotFoundError as exc:
            return ExecutorRunResult(
                success=False,
                executor_name="graph_executor",
                frd_path="",
                output_dir=str(output_dir),
                is_replay=True,
                error_message=str(exc),
            )

        started = time.perf_counter()
        plan = _graph_smoke_plan(case_id, task_spec)

        try:
            with (
                patch("agents.architect._extract_structured_data", return_value=plan),
                patch("agents.geometry.generate_geometry", side_effect=_fake_generate_geometry),
                patch("agents.geometry.check_geometry", return_value=_valid_geometry_report()),
                patch("agents.mesh.generate_mesh", side_effect=_fake_generate_mesh),
                patch("agents.mesh.check_mesh_quality", return_value=_valid_mesh_report()),
                patch(
                    "agents.solver.run_solve",
                    side_effect=lambda inp_path, run_dir, **kwargs: _fake_run_solve(
                        inp_path=inp_path,
                        work_dir=run_dir,
                        source_frd=source_frd,
                    ),
                ),
            ):
                from agents.graph import compile_graph

                result = compile_graph().invoke(
                    {
                        "user_request": f"{case_id} well-harness graph smoke: {task_spec.name}",
                        "case_id": plan.case_id,
                        "run_id": run_id,
                        "project_state_dir": str(output_dir),
                        "artifacts": [],
                        "history": [],
                        "retry_budgets": {},
                        "fault_class": FaultClass.NONE,
                        "execution_mode": {
                            "replay": True,
                            "geometry_source": "dummy",
                            "executor": "graph_executor",
                        },
                    }
                )
        except Exception as exc:
            return _graph_failure_result(
                output_dir=output_dir,
                started=started,
                message=f"Graph executor failed while invoking compile_graph: {exc}",
            )
        if not isinstance(result, dict):
            return _graph_failure_result(
                output_dir=output_dir,
                started=started,
                message=f"Graph executor returned non-mapping result: {type(result).__name__}",
            )

        duration = time.perf_counter() - started
        frd_path = _resolve_graph_frd(result)
        backend_name = (result.get("solve_metadata") or {}).get("backend")
        fault_class = result.get("fault_class")
        success = (
            fault_class in {FaultClass.NONE, FaultClass.NONE.value}
            and backend_name == "calculix"
            and frd_path is not None
            and frd_path.exists()
        )
        error_message = _graph_error_message(
            success=success,
            fault_class=fault_class,
            backend_name=backend_name,
            frd_path=frd_path,
        )

        return ExecutorRunResult(
            success=success,
            executor_name="graph_executor",
            frd_path="" if frd_path is None else str(frd_path),
            output_dir=str(output_dir),
            is_replay=True,
            execution_time_s=duration,
            logs=[
                "invoked agents.graph.compile_graph()",
                f"solve_metadata.backend={backend_name or 'missing'}",
                f"verdict={result.get('verdict') or 'missing'}",
                "execution_mode=replay,dummy-geometry",
            ],
            error_message=error_message,
        )


def _graph_smoke_plan(case_id: str, task_spec: TaskSpec) -> SimPlan:
    digits = "".join(ch for ch in case_id if ch.isdigit())
    suffix = int(digits[-2:]) if digits else 4
    return SimPlan(
        case_id=f"AI-FEA-P2-{suffix:02d}",
        description=f"Well-harness graph executor smoke for {case_id}: {task_spec.name}",
        geometry=GeometrySpec(
            kind="naca",
            parameters={"profile": "NACA0012", "chord_length": 1.0, "span": 1.0},
        ),
        material=MaterialSpec(
            name="Aluminum 7075",
            youngs_modulus_pa=71.7e9,
            poissons_ratio=0.33,
        ),
        loads=[
            LoadSpec(
                kind="concentrated_force",
                parameters={"magnitude": -500.0, "node_set": "Ntip"},
            )
        ],
        boundary_conditions=[BCSpec(kind="fixed", parameters={"node_set": "Nroot"})],
        objectives=ObjectiveSpec(export_vtp=True, narrative_report=True),
    )


def _fake_generate_geometry(
    spec: dict,
    output_dir: Path,
    *,
    allow_dummy: bool | None = None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    step_path = output_dir / "model.step"
    step_path.write_text("ISO-10303-21;\nEND-ISO-10303-21;\n", encoding="utf-8")
    (output_dir / "topo_map.json").write_text(
        json.dumps([{"fixed_base": ["Face1"], "tip_load": ["Face2"], "skin": ["Face3"]}]),
        encoding="utf-8",
    )
    (output_dir / "geometry_meta.json").write_text(
        json.dumps(
            {
                "watertight": True,
                "manifold": True,
                "volume_m3": 0.01,
                "min_feature_size_m": 0.12,
                "bounding_box_mm": [1000.0, 120.0, 1000.0],
            }
        ),
        encoding="utf-8",
    )
    return step_path


def _fake_generate_mesh(step_path: Path, params: dict, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    mesh_path = output_dir / "model.inp"
    mesh_path.write_text(
        "*NODE\n"
        "1, 0.0, 0.0, 0.0\n"
        "2, 1.0, 0.0, 0.0\n"
        "3, 0.0, 1.0, 0.0\n"
        "4, 0.0, 0.0, 1.0\n"
        "*ELEMENT, TYPE=C3D4, ELSET=Eall\n"
        "1, 1, 2, 3, 4\n"
        "*NSET, NSET=Nroot\n"
        "1\n"
        "*NSET, NSET=Ntip\n"
        "2\n",
        encoding="utf-8",
    )
    (output_dir / "mesh_meta.json").write_text(
        json.dumps({"field_config": {"thin_wall_detected": False}}),
        encoding="utf-8",
    )
    return mesh_path


def _fake_run_solve(*, inp_path: Path, work_dir: Path, source_frd: Path) -> dict:
    frd_path = work_dir / "solve.frd"
    dat_path = work_dir / "solve.dat"
    sta_path = work_dir / "solve.sta"
    shutil.copy2(source_frd, frd_path)
    dat_path.write_text("graph executor replay result\n", encoding="utf-8")
    sta_path.write_text("STEP 1 converged\n", encoding="utf-8")
    return {
        "frd_path": str(frd_path),
        "dat_path": str(dat_path),
        "sta_path": str(sta_path),
        "converged": True,
        "wall_time_s": 0.0,
        "returncode": 0,
        "ccx_version": "graph-replay",
        "fault_class": FaultClass.NONE,
        "failure_reason": None,
    }


def _resolve_graph_frd(result: dict) -> Path | None:
    frd_path = result.get("frd_path")
    if frd_path:
        return Path(frd_path)
    for artifact in result.get("artifacts") or []:
        path = Path(str(artifact))
        if path.suffix.lower() == ".frd":
            return path
    return None


def _graph_failure_result(*, output_dir: Path, started: float, message: str) -> ExecutorRunResult:
    return ExecutorRunResult(
        success=False,
        executor_name="graph_executor",
        frd_path="",
        output_dir=str(output_dir),
        is_replay=True,
        execution_time_s=time.perf_counter() - started,
        logs=["invoked agents.graph.compile_graph()", message],
        error_message=message,
    )


def _graph_error_message(
    *,
    success: bool,
    fault_class: Any,
    backend_name: str | None,
    frd_path: Path | None,
) -> str | None:
    if success:
        return None
    if backend_name != "calculix":
        return f"Graph executor expected solve_metadata.backend='calculix', got {backend_name!r}."
    if frd_path is None:
        return "Graph executor did not return an FRD artifact."
    if not frd_path.exists():
        return f"Graph executor returned missing FRD artifact: {frd_path}"
    return f"Graph executor completed with fault_class={fault_class!r}."


def _run_id_from_output_dir(output_dir: Path, case_id: str) -> str:
    parent = output_dir.parent
    if parent.name:
        return parent.name
    return f"{case_id.lower().replace('-', '_')}_graph_executor"


def _valid_geometry_report() -> dict:
    return {
        "valid": True,
        "watertight": True,
        "manifold": True,
        "min_feature_size_m": 0.12,
        "bounding_box_mm": [1000.0, 120.0, 1000.0],
        "findings": [],
    }


def _valid_mesh_report() -> dict:
    return {
        "ok": True,
        "passed": True,
        "bad_element_ids": [],
        "resolution_element_ids": [],
        "findings": [],
    }
