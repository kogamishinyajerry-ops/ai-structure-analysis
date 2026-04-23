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
    )

@patch("app.well_harness.notion_sync.os.environ.get", return_value="dummy_token")
@patch("app.well_harness.notion_sync.httpx.Client")
def test_idempotent_register_batch(mock_client_cls, mock_env_get, mock_config, run_record):
    registrar = NotionRunRegistrar(config=mock_config)
    mock_client = MagicMock()
    mock_client_cls.return_value.__enter__.return_value = mock_client
    
    # Mock for first run: no existing session/tasks
    mock_query_response_empty = MagicMock()
    mock_query_response_empty.json.return_value = {"results": [], "has_more": False}
    mock_client.request.return_value = mock_query_response_empty
    
    # Override for POST
    mock_post_response = MagicMock()
    mock_post_response.json.return_value = {"id": "new_id"}
    def side_effect(method, url, json=None, **kwargs):
        if method == "POST" and "query" in url:
            return mock_query_response_empty
        if method == "POST":
            return mock_post_response
        return MagicMock()
    mock_client.request.side_effect = side_effect

    registrar.register_batch([run_record], "test cmd", "test exec")
    
    post_calls = [c for c in mock_client.request.call_args_list if c[0][0] == "POST" and "pages" in c[0][1]]
    assert len(post_calls) == 2  # 1 session, 1 task

    # Mock for second run: existing session and task
    mock_query_session = MagicMock()
    mock_query_session.json.return_value = {"results": [{"id": "existing_session_id", "properties": {"Run Batch": {"type": "rich_text", "rich_text": [{"text": {"content": "run-123"}}]}}}], "has_more": False}
    
    mock_query_task = MagicMock()
    mock_query_task.json.return_value = {"results": [{"id": "existing_task_id", "properties": {"Session Batch": {"type": "rich_text", "rich_text": [{"text": {"content": "run-123"}}]}, "Run ID": {"type": "rich_text", "rich_text": [{"text": {"content": "run-123"}}]}}}], "has_more": False}
    
    def side_effect_2(method, url, json=None, **kwargs):
        if method == "POST" and "query" in url:
            if "db_sessions" in url: return mock_query_session
            if "db_tasks" in url: return mock_query_task
            return mock_query_response_empty
        if method == "PATCH":
            mock_patch_resp = MagicMock()
            mock_patch_resp.json.return_value = {"id": "updated_id"}
            return mock_patch_resp
        if method == "POST":
            return mock_post_response
        return MagicMock()
    
    mock_client.request.reset_mock()
    mock_client.request.side_effect = side_effect_2
    
    registrar.register_batch([run_record], "test cmd", "test exec")
    
    post_calls_2 = [c for c in mock_client.request.call_args_list if c[0][0] == "POST" and "pages" in c[0][1] and "query" not in c[0][1]]
    patch_calls_2 = [c for c in mock_client.request.call_args_list if c[0][0] == "PATCH"]
    
    assert len(post_calls_2) == 0
    assert len(patch_calls_2) == 2  # 1 session update, 1 task update
