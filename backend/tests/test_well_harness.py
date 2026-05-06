from pathlib import Path
from unittest.mock import patch

from app.well_harness.cli import _build_executor, build_parser
from app.well_harness.control_plane import ControlPlaneSyncBuilder
from app.well_harness.executors import GraphExecutor
from app.well_harness.knowledge_store import GoldenSampleKnowledgeStore
from app.well_harness.project_state import ProjectStateStore
from app.well_harness.schemas import HarnessRunStatus
from app.well_harness.task_runner import WellHarnessRunner


class CapturingExecutor:
    def __init__(self):
        self.work_dir = None

    def execute(self, case_id, task_spec, store, work_dir=None):
        self.work_dir = work_dir
        return GraphExecutor().execute(case_id, task_spec, store, work_dir=work_dir)


def test_knowledge_store_lists_expected_cases():
    store = GoldenSampleKnowledgeStore()
    case_ids = store.list_case_ids()
    assert {"GS-001", "GS-002", "GS-003"}.issubset(set(case_ids))


def test_well_harness_persists_project_state(tmp_path):
    state_store = ProjectStateStore(tmp_path)
    runner = WellHarnessRunner(state_store=state_store)

    run = runner.run_case("GS-001")
    run_dir = Path(run.project_state_dir)

    assert run.status in {HarnessRunStatus.COMPLETED, HarnessRunStatus.PENDING_REVIEW}
    assert run_dir.exists()
    assert (run_dir / "input_summary.json").exists()
    assert (run_dir / "output_summary.json").exists()
    assert (run_dir / "artifacts.json").exists()
    assert (run_dir / "control_plane_sync.json").exists()
    assert (run_dir / "handoff.md").exists()


def test_well_harness_runs_multiple_cases_without_hard_failure(tmp_path):
    state_store = ProjectStateStore(tmp_path)
    runner = WellHarnessRunner(state_store=state_store)

    runs = runner.run_cases(["GS-001", "GS-002", "GS-003"])

    assert len(runs) == 3
    assert all(run.status != HarnessRunStatus.FAILED for run in runs)


def test_cli_accepts_graph_executor_mode():
    args = build_parser().parse_args(["GS-001", "--executor", "graph", "--no-notion-sync"])

    assert args.executor == "graph"
    assert args.no_notion_sync is True
    assert isinstance(_build_executor("graph"), GraphExecutor)


def test_graph_executor_runs_graph_path_and_persists_project_state(tmp_path):
    state_store = ProjectStateStore(tmp_path)
    runner = WellHarnessRunner(executor=GraphExecutor(), state_store=state_store)

    run = runner.run_case("GS-001")
    run_dir = Path(run.project_state_dir)

    assert run.status != HarnessRunStatus.FAILED
    assert run.executor.executor_name == "graph_executor"
    assert run.executor.is_replay is True
    assert "solve_metadata.backend=calculix" in run.executor.logs
    assert Path(run.executor.frd_path).exists()
    assert run_dir.exists()
    assert (run_dir / "input_summary.json").exists()
    assert (run_dir / "output_summary.json").exists()
    assert (run_dir / "artifacts.json").exists()
    assert (run_dir / "control_plane_sync.json").exists()
    assert (run_dir / "handoff.md").exists()
    assert any("graph_executor replay/dummy mode" in risk for risk in run.handoff.risks)


def test_graph_executor_marks_failed_on_compile_graph_exception(tmp_path):
    store = GoldenSampleKnowledgeStore()
    task_spec = store.build_task_spec("GS-001")

    with patch("agents.graph.compile_graph", side_effect=RuntimeError("graph unavailable")):
        result = GraphExecutor().execute(
            "GS-001",
            task_spec,
            store,
            work_dir=tmp_path / "executor",
        )

    assert result.success is False
    assert result.executor_name == "graph_executor"
    assert result.is_replay is True
    assert "graph unavailable" in result.error_message


def test_graph_executor_marks_failed_on_non_mapping_graph_result(tmp_path):
    class FakeGraph:
        def invoke(self, state):
            return None

    store = GoldenSampleKnowledgeStore()
    task_spec = store.build_task_spec("GS-001")

    with patch("agents.graph.compile_graph", return_value=FakeGraph()):
        result = GraphExecutor().execute(
            "GS-001",
            task_spec,
            store,
            work_dir=tmp_path / "executor",
        )

    assert result.success is False
    assert "non-mapping result" in result.error_message


def test_graph_executor_requires_calculix_backend(tmp_path):
    class FakeGraph:
        def invoke(self, state):
            frd_path = Path(state["project_state_dir"]) / "solve.frd"
            frd_path.write_text("synthetic", encoding="utf-8")
            return {
                "fault_class": "none",
                "frd_path": str(frd_path),
                "solve_metadata": {"backend": "fenics"},
            }

    store = GoldenSampleKnowledgeStore()
    task_spec = store.build_task_spec("GS-001")

    with patch("agents.graph.compile_graph", return_value=FakeGraph()):
        result = GraphExecutor().execute(
            "GS-001",
            task_spec,
            store,
            work_dir=tmp_path / "executor",
        )

    assert result.success is False
    assert "solve_metadata.backend='calculix'" in result.error_message


def test_task_runner_passes_executor_work_dir(tmp_path):
    state_store = ProjectStateStore(tmp_path)
    executor = CapturingExecutor()
    runner = WellHarnessRunner(executor=executor, state_store=state_store)

    run = runner.run_case("GS-001")

    assert run.status != HarnessRunStatus.FAILED
    assert executor.work_dir == Path(run.project_state_dir) / "executor"


def test_control_plane_payload_is_stable(tmp_path):
    state_store = ProjectStateStore(tmp_path)
    runner = WellHarnessRunner(state_store=state_store)
    run = runner.run_case("GS-001")

    builder = ControlPlaneSyncBuilder()
    sync_plan = builder.build(run)
    stable = sync_plan.stable_repr()

    assert "GS-001" in stable
    assert run.status.value in stable
