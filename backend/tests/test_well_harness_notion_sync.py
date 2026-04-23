import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
from app.well_harness.notion_sync import NotionRunRegistrar
from app.well_harness.project_state import ProjectStateStore
from app.well_harness.task_runner import WellHarnessRunner


def _write_config(path: Path, enabled: bool = True) -> None:
    path.write_text(
        f"""
notion:
  enabled: {"true" if enabled else "false"}
  token_env: TEST_NOTION_TOKEN
  notion_version: "2026-03-11"
  root_page_id: "345c68942bed80f6a092c9c2b3d3f5b9"
  data_source_ids:
    tasks: "f17ba02b-d6d7-4aa7-b375-bd705038f47d"
    sessions: "6644423a-671b-4def-8e42-7414ba0d8d4a"
    decisions: "2b99ac18-0ba5-4b0a-9f38-18075b3bd6b6"
github:
  repository: "kogamishinyajerry-ops/ai-structure-analysis"
""".strip(),
        encoding="utf-8",
    )


def _title_property(value: str) -> dict:
    return {"id": "title", "type": "title", "title": [{"type": "text", "text": {"content": value}}]}


def _rich_text_property(value: str) -> dict:
    return {
        "id": "rich_text",
        "type": "rich_text",
        "rich_text": [{"type": "text", "text": {"content": value}}],
    }


def _select_property(value: str) -> dict:
    return {"id": "select", "type": "select", "select": {"name": value}}


def _session_page(page_id: str, batch_id: str, status: str, outcome: str, summary: str) -> dict:
    return {
        "object": "page",
        "id": page_id,
        "properties": {
            "Session": _title_property(f"well_harness batch {batch_id}"),
            "Run Batch": _rich_text_property(batch_id),
            "Status": _select_property(status),
            "Outcome": _select_property(outcome),
            "Summary": _rich_text_property(summary),
        },
    }


def _task_page(
    page_id: str,
    batch_id: str,
    approval_status: str,
    verdict: str,
) -> dict:
    return {
        "object": "page",
        "id": page_id,
        "properties": {
            "Task": _title_property(f"task-{page_id}"),
            "Session Batch": _rich_text_property(batch_id),
            "Approval Status": _select_property(approval_status),
            "Verdict": _select_property(verdict),
        },
    }


def test_notion_sync_request_shapes(tmp_path, monkeypatch):
    config_path = tmp_path / "well_harness_control_plane.yaml"
    _write_config(config_path, enabled=True)
    monkeypatch.setenv("TEST_NOTION_TOKEN", "secret-token")

    runner = WellHarnessRunner(state_store=ProjectStateStore(tmp_path / "state"))
    run = runner.run_case("GS-001")
    registrar = NotionRunRegistrar.from_default_path(config_path)
    monkeypatch.setattr(
        registrar,
        "_github_metadata",
        lambda: {
            "repository": "kogamishinyajerry-ops/ai-structure-analysis",
            "repo_url": "https://github.com/kogamishinyajerry-ops/ai-structure-analysis",
            "branch": "main",
            "commit_sha": "ef5e9db47a70c9eb9a647f3f75e92df062082ead",
            "commit_short": "ef5e9db",
            "commit_url": "https://github.com/kogamishinyajerry-ops/ai-structure-analysis/commit/ef5e9db47a70c9eb9a647f3f75e92df062082ead",
        },
    )

    session_request = registrar.build_session_request(
        batch_id="batch-001",
        run_records=[run],
        invoked_command="python3 run_well_harness.py GS-001",
        executor_mode="replay",
    )
    task_request = registrar.build_task_request(
        run_record=run,
        batch_id="batch-001",
        invoked_command="python3 run_well_harness.py GS-001",
        session_title="well_harness batch batch-001",
    )

    assert session_request["parent"]["type"] == "data_source_id"
    assert session_request["properties"]["Outcome"]["select"]["name"] == "Pending Review"
    assert session_request["properties"]["GitHub Commit Link"]["url"].endswith(
        "ef5e9db47a70c9eb9a647f3f75e92df062082ead"
    )
    assert "Artifacts" not in session_request["properties"]
    assert "Project State Root" not in session_request["properties"]
    assert task_request["parent"]["type"] == "data_source_id"
    assert task_request["properties"]["Approval Status"]["select"]["name"] == "Awaiting Approval"
    assert task_request["properties"]["GitHub Commit Link"]["url"].endswith(
        "ef5e9db47a70c9eb9a647f3f75e92df062082ead"
    )
    assert task_request["properties"]["GitHub PR Link"]["url"] is None
    assert task_request["properties"]["GitHub Issue Link"]["url"] is None
    assert "Artifact Path" not in task_request["properties"]
    assert "Handoff Path" not in task_request["properties"]
    assert (
        task_request["properties"]["Session Batch"]["rich_text"][0]["text"]["content"]
        == "batch-001"
    )


def test_notion_sync_skips_when_not_configured(tmp_path):
    config_path = tmp_path / "well_harness_control_plane.yaml"
    _write_config(config_path, enabled=False)
    runner = WellHarnessRunner(state_store=ProjectStateStore(tmp_path / "state"))
    run = runner.run_case("GS-001")
    registrar = NotionRunRegistrar.from_default_path(config_path)

    result = registrar.register_batch(
        run_records=[run],
        invoked_command="python3 run_well_harness.py GS-001",
        executor_mode="replay",
    )

    assert result.attempted is False
    assert result.success is False
    assert "disabled" in (result.skipped_reason or "")


def test_build_graph_run_id_uses_case_and_commit_short(tmp_path, monkeypatch):
    config_path = tmp_path / "well_harness_control_plane.yaml"
    _write_config(config_path, enabled=True)
    monkeypatch.setenv("TEST_NOTION_TOKEN", "secret-token")

    registrar = NotionRunRegistrar.from_default_path(config_path)
    monkeypatch.setattr(
        registrar,
        "_github_metadata",
        lambda: {
            "repository": "kogamishinyajerry-ops/ai-structure-analysis",
            "repo_url": "https://github.com/kogamishinyajerry-ops/ai-structure-analysis",
            "branch": "feature/AI-FEA-P0-03-notion-sync",
            "commit_sha": "ebf5f9a0e1b785487a5cdc30f91b42a55fe93cb7",
            "commit_short": "ebf5f9a",
            "commit_url": "https://github.com/kogamishinyajerry-ops/ai-structure-analysis/commit/ebf5f9a0e1b785487a5cdc30f91b42a55fe93cb7",
        },
    )

    run_id = registrar.build_graph_run_id(
        "AI-FEA-P0-03",
        now=datetime(2026, 4, 18, 9, 30, tzinfo=UTC),
    )

    assert run_id == "run-20260418-AI-FEA-P0-03-ebf5f9a"


def test_create_standalone_task_request_shape(tmp_path, monkeypatch):
    config_path = tmp_path / "well_harness_control_plane.yaml"
    _write_config(config_path, enabled=True)
    monkeypatch.setenv("TEST_NOTION_TOKEN", "secret-token")

    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "POST" and request.url.path == "/v1/pages":
            return httpx.Response(200, json={"id": "task-page-1"})
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    client = httpx.Client(
        base_url="https://api.notion.com/v1",
        transport=httpx.MockTransport(handler),
    )
    registrar = NotionRunRegistrar.from_default_path(config_path, client=client)
    monkeypatch.setattr(
        registrar,
        "_github_metadata",
        lambda: {
            "repository": "kogamishinyajerry-ops/ai-structure-analysis",
            "repo_url": "https://github.com/kogamishinyajerry-ops/ai-structure-analysis",
            "branch": "feature/AI-FEA-P0-03-notion-sync",
            "commit_sha": "ebf5f9a0e1b785487a5cdc30f91b42a55fe93cb7",
            "commit_short": "ebf5f9a",
            "commit_url": "https://github.com/kogamishinyajerry-ops/ai-structure-analysis/commit/ebf5f9a0e1b785487a5cdc30f91b42a55fe93cb7",
        },
    )

    result = registrar.create_standalone_task(
        case_id="AI-FEA-P0-03",
        run_id="run-20260418-AI-FEA-P0-03-ebf5f9a",
        summary=(
            "Graph execution paused by human_fallback interrupt due to limit "
            "or unknown fault. fault_class=unknown."
        ),
        invoked_command="langgraph human_fallback",
    )

    assert result.attempted is True
    assert result.success is True
    assert result.task_page_ids == ["task-page-1"]

    request_body = json.loads(requests[0].content.decode("utf-8"))
    assert (
        request_body["properties"]["Case ID"]["rich_text"][0]["text"]["content"] == "AI-FEA-P0-03"
    )
    assert (
        request_body["properties"]["Run ID"]["rich_text"][0]["text"]["content"]
        == "run-20260418-AI-FEA-P0-03-ebf5f9a"
    )
    assert (
        request_body["properties"]["Session Batch"]["rich_text"][0]["text"]["content"]
        == "run-20260418-AI-FEA-P0-03-ebf5f9a"
    )
    assert (
        request_body["properties"]["Command"]["rich_text"][0]["text"]["content"]
        == "langgraph human_fallback"
    )
    assert request_body["properties"]["GitHub Commit Link"]["url"].endswith(
        "ebf5f9a0e1b785487a5cdc30f91b42a55fe93cb7"
    )


def test_notion_reconcile_updates_session_summary_from_task_approvals(tmp_path, monkeypatch):
    config_path = tmp_path / "well_harness_control_plane.yaml"
    _write_config(config_path, enabled=True)
    monkeypatch.setenv("TEST_NOTION_TOKEN", "secret-token")

    batch_id = "20260417T105706.960169+0000"
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if (
            request.method == "POST"
            and request.url.path == "/v1/data_sources/6644423a-671b-4def-8e42-7414ba0d8d4a/query"
        ):
            return httpx.Response(
                200,
                json={
                    "results": [
                        _session_page(
                            "session-page-1",
                            batch_id=batch_id,
                            status="Open",
                            outcome="Pending Review",
                            summary=(
                                "Batch completed via replay. "
                                "GS-001:pending_review; GS-002:pending_review"
                            ),
                        )
                    ],
                    "has_more": False,
                    "next_cursor": None,
                },
            )
        if (
            request.method == "POST"
            and request.url.path == "/v1/data_sources/f17ba02b-d6d7-4aa7-b375-bd705038f47d/query"
        ):
            return httpx.Response(
                200,
                json={
                    "results": [
                        _task_page("task-1", batch_id, "Approved", "Accept"),
                        _task_page("task-2", batch_id, "Approved", "Accept with Note"),
                    ],
                    "has_more": False,
                    "next_cursor": None,
                },
            )
        if request.method == "PATCH" and request.url.path == "/v1/pages/session-page-1":
            return httpx.Response(200, json={"id": "session-page-1"})
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    client = httpx.Client(
        base_url="https://api.notion.com/v1",
        transport=httpx.MockTransport(handler),
    )
    registrar = NotionRunRegistrar.from_default_path(config_path, client=client)

    result = registrar.reconcile_session_approval_status()

    assert result.attempted is True
    assert result.success is True
    assert result.processed_sessions == 1
    assert result.updated_session_ids == ["session-page-1"]

    patch_request = next(request for request in requests if request.method == "PATCH")
    patch_body = json.loads(patch_request.content.decode("utf-8"))
    assert patch_body["properties"]["Status"]["select"]["name"] == "Closed"
    assert patch_body["properties"]["Outcome"]["select"]["name"] == "Mixed"
    assert "approved=2" in patch_body["properties"]["Summary"]["rich_text"][0]["text"]["content"]
    assert (
        "accept_with_note=1"
        in patch_body["properties"]["Summary"]["rich_text"][0]["text"]["content"]
    )


def test_notion_reconcile_skips_when_not_configured(tmp_path):
    config_path = tmp_path / "well_harness_control_plane.yaml"
    _write_config(config_path, enabled=False)
    registrar = NotionRunRegistrar.from_default_path(config_path)

    result = registrar.reconcile_session_approval_status()

    assert result.attempted is False
    assert result.success is False
    assert "disabled" in (result.skipped_reason or "")


# ---------------------------------------------------------------------------
# AI-FEA-S2.1-02 Gate-fix coverage: create_standalone_task ADR-010 defaults
# ---------------------------------------------------------------------------

def test_create_standalone_task_adr010_field_defaults(tmp_path, monkeypatch):
    """create_standalone_task must emit ADR-010 sprint/model/tokens/branch/sha
    fields with safe defaults — no NameError and no run_record reference.
    (Gate check S2.1-02 identified this gap.)
    """
    config_path = tmp_path / "well_harness_control_plane.yaml"
    _write_config(config_path, enabled=True)
    monkeypatch.setenv("TEST_NOTION_TOKEN", "secret-token")

    requests_seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests_seen.append(request)
        if request.method == "POST" and "/pages" in request.url.path:
            return httpx.Response(200, json={"id": "standalone-page-1"})
        raise AssertionError(f"Unexpected: {request.method} {request.url}")

    client = httpx.Client(
        base_url="https://api.notion.com/v1",
        transport=httpx.MockTransport(handler),
    )
    registrar = NotionRunRegistrar.from_default_path(config_path, client=client)
    monkeypatch.setattr(
        registrar,
        "_github_metadata",
        lambda: {
            "repository": "kogamishinyajerry-ops/ai-structure-analysis",
            "repo_url": "https://github.com/kogamishinyajerry-ops/ai-structure-analysis",
            "branch": "main",
            "commit_sha": "aabbccdd1234",
            "commit_short": "aabbccd",
            "commit_url": "https://github.com/kogamishinyajerry-ops/ai-structure-analysis/commit/aabbccdd1234",
        },
    )

    # Should NOT raise NameError — that was the gate-fix bug
    result = registrar.create_standalone_task(
        case_id="AI-FEA-S2.1-XX",
        run_id="run-20260423-AI-FEA-S2.1-XX-aabbccd",
    )

    assert result.attempted is True
    assert result.success is True
    assert requests_seen, "Expected at least one HTTP request"

    body = json.loads(requests_seen[0].content.decode("utf-8"))
    props = body["properties"]

    # ADR-010 field defaults ---------------------------------------------------
    # Sprint must default to "S2.1" (not a NameError crash)
    assert props["Sprint"]["select"]["name"] == "S2.1", \
        "Sprint default should be S2.1"

    # Model, Branch, Start SHA must be present but None (omitted from Notion)
    assert props["Model"] is None, "Model should default to None"
    assert props["Branch"] is None, "Branch should default to None"
    assert props["Start SHA"] is None, "Start SHA should default to None"

    # Tokens Used / Tokens Budget must emit number=null (not crash)
    assert props["Tokens Used"]["number"] is None, "Tokens Used should be null"
    assert props["Tokens Budget"]["number"] is None, "Tokens Budget should be null"

    # ADR Link must be a url prop with empty/None value (not crash)
    assert "url" in props["ADR Link"], "ADR Link should be a url prop"
