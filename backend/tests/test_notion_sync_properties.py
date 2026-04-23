from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest
from app.well_harness.notion_sync import NotionRunRegistrar, NotionSyncConfig, NotionDataSources
from app.well_harness.schemas import HarnessRunRecord, HarnessRunStatus, VerificationReport, ExecutorRunResult, TaskSpec

@pytest.fixture
def mock_config():
    return NotionSyncConfig(
        enabled=True,
        token_env="DUMMY_TOKEN_ENV",
        notion_version="2026-03-11",
        root_page_id="dummy_root",
        data_sources=NotionDataSources(tasks="db_tasks", sessions="db_sessions", decisions="db_decisions")
    )

@pytest.fixture
def run_record():
    return HarnessRunRecord(
        run_id="run-123",
        case_id="case-1",
        status=HarnessRunStatus.COMPLETED,
        started_at="2026-04-23T01:00:00Z",
        completed_at="2026-04-23T01:10:00Z",
        task_spec=TaskSpec(task_id="t1", name="t1", task_type="static_analysis", geometry_file="t1", analysis_type="static", constraints=[], inputs={}, outputs=[]),
        executor=ExecutorRunResult(success=True, executor_name="test", frd_path="out.frd", output_dir="out"),
        report_summary="Success",
        report_metrics={},
        validation={},
        verification=VerificationReport(passed=True, summary="Passed"),
        sprint="S2.1",
        model="Gemini 3.1 Pro",
        tokens_used=1234,
        tokens_budget=5000,
        branch="main",
        adr_link="https://docs/adr",
        start_sha="abcdef1"
    )

def test_properties_payload(mock_config, run_record):
    registrar = NotionRunRegistrar(config=mock_config)
    registrar._github_metadata = MagicMock(return_value={"commit_url": "url", "commit_short": "abc"})
    
    session_req = registrar.build_session_request("batch_1", [run_record], "test", "test")
    props = session_req["properties"]
    
    assert props["Sprint"]["select"]["name"] == "S2.1"
    assert props["Model"]["select"]["name"] == "Gemini 3.1 Pro"
    assert props["Tokens Used"]["number"] == 1234
    assert props["Tokens Budget"]["number"] == 5000
    assert props["Branch"]["rich_text"][0]["text"]["content"] == "main"
    assert props["ADR Link"]["url"] == "https://docs/adr"
    assert props["Start SHA"]["rich_text"][0]["text"]["content"] == "abcdef1"
    
    task_req = registrar.build_task_request(run_record, "batch_1", "test", "session title")
    props = task_req["properties"]
    
    assert props["Sprint"]["select"]["name"] == "S2.1"
    assert props["Model"]["select"]["name"] == "Gemini 3.1 Pro"
    assert props["Tokens Used"]["number"] == 1234
    assert props["Tokens Budget"]["number"] == 5000
    assert props["Branch"]["rich_text"][0]["text"]["content"] == "main"
    assert props["ADR Link"]["url"] == "https://docs/adr"
    assert props["Start SHA"]["rich_text"][0]["text"]["content"] == "abcdef1"
