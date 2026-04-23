from unittest.mock import MagicMock, patch

import pytest
from app.well_harness.notion_sync import NotionRunRegistrar, NotionSyncConfig, NotionDataSources

@pytest.fixture
def mock_config():
    return NotionSyncConfig(
        enabled=True,
        token_env="DUMMY_TOKEN_ENV",
        notion_version="2026-03-11",
        root_page_id="dummy_root",
        data_sources=NotionDataSources(tasks="db_tasks", sessions="db_sessions", decisions="db_decisions")
    )

def test_register_decision_none(mock_config):
    registrar = NotionRunRegistrar(config=mock_config)
    result = registrar.register_decision(decisions=None)
    assert not result.attempted
    assert result.success
    assert result.skipped_reason == "No decisions provided."
    
@patch("app.well_harness.notion_sync.os.environ.get", return_value="dummy_token")
@patch("app.well_harness.notion_sync.httpx.Client")
def test_register_decision_success(mock_client_cls, mock_env_get, mock_config):
    registrar = NotionRunRegistrar(config=mock_config)
    mock_client = MagicMock()
    mock_client_cls.return_value.__enter__.return_value = mock_client
    
    mock_post_response = MagicMock()
    mock_post_response.json.return_value = {"id": "decision_id_1"}
    mock_client.request.return_value = mock_post_response
    
    decisions = [
        {"title": "Test Decision", "status": "Proposed", "context": "Ctx", "consequences": "Cons"}
    ]
    
    result = registrar.register_decision(decisions=decisions)
    assert result.attempted
    assert result.success
    assert len(result.task_page_ids) == 1
    assert result.task_page_ids[0] == "decision_id_1"
    
    post_calls = [c for c in mock_client.request.call_args_list if c[0][0] == "POST" and "pages" in c[0][1]]
    assert len(post_calls) == 1
    
    json_body = post_calls[0].kwargs.get("json")
    assert json_body["properties"]["Decision"]["title"][0]["text"]["content"] == "Test Decision"
    assert json_body["properties"]["Status"]["select"]["name"] == "Proposed"
