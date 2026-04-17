from pathlib import Path

from app.well_harness.control_plane import ControlPlaneSyncBuilder
from app.well_harness.knowledge_store import GoldenSampleKnowledgeStore
from app.well_harness.project_state import ProjectStateStore
from app.well_harness.schemas import HarnessRunStatus
from app.well_harness.task_runner import WellHarnessRunner


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


def test_control_plane_payload_is_stable(tmp_path):
    state_store = ProjectStateStore(tmp_path)
    runner = WellHarnessRunner(state_store=state_store)
    run = runner.run_case("GS-001")

    builder = ControlPlaneSyncBuilder()
    sync_plan = builder.build(run)
    stable = sync_plan.stable_repr()

    assert "GS-001" in stable
    assert run.status.value in stable
