"""Tests for the well_harness GitHub Actions workflow contract.

Validates that .github/workflows/well_harness.yml:
- Contains all three required triggers (pull_request, repository_dispatch, push)
- References all required Notion secrets
- Contains the Case ID extraction regex step
- Contains the correct CLI invocation pattern
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

# Anchor: find repo root via the pyproject.toml sentinel file, walking upward
def _repo_root() -> Path:
    p = Path(__file__).resolve()
    for parent in [p, *p.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    raise FileNotFoundError("Could not locate repo root (pyproject.toml not found)")

WORKFLOW_PATH = _repo_root() / ".github" / "workflows" / "well_harness.yml"

REQUIRED_SECRETS = [
    "NOTION_TOKEN",
    "NOTION_TASK_DB",
    "NOTION_DECISION_DB",
    "NOTION_SESSION_DB",
]

REQUIRED_DISPATCH_TYPES = ["notion_approval"]

CASE_ID_REGEX = r"\[([A-Z0-9a-z_\-\.]+)\]"


@pytest.fixture(scope="module")
def workflow() -> dict:
    assert WORKFLOW_PATH.exists(), f"Workflow file not found: {WORKFLOW_PATH}"
    with WORKFLOW_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def workflow_raw() -> str:
    assert WORKFLOW_PATH.exists()
    return WORKFLOW_PATH.read_text(encoding="utf-8")


class TestTriggers:
    def test_pull_request_trigger_exists(self, workflow: dict) -> None:
        # PyYAML 1.1 parses bare `on:` as True (boolean), not "on" string
        on_key = workflow.get("on") or workflow.get(True, {})
        assert "pull_request" in on_key, "Missing pull_request trigger"

    def test_pull_request_types(self, workflow: dict) -> None:
        on_key = workflow.get("on") or workflow.get(True, {})
        pr_trigger = on_key.get("pull_request", {})
        types = pr_trigger.get("types", [])
        assert "opened" in types, "pull_request.types missing 'opened'"
        assert "synchronize" in types, "pull_request.types missing 'synchronize'"
        assert "ready_for_review" in types, "pull_request.types missing 'ready_for_review'"

    def test_repository_dispatch_trigger(self, workflow: dict) -> None:
        on_key = workflow.get("on") or workflow.get(True, {})
        assert "repository_dispatch" in on_key, "Missing repository_dispatch trigger"
        types = on_key["repository_dispatch"].get("types", [])
        for t in REQUIRED_DISPATCH_TYPES:
            assert t in types, f"repository_dispatch missing type '{t}'"

    def test_push_to_main_trigger(self, workflow: dict) -> None:
        on_key = workflow.get("on") or workflow.get(True, {})
        assert "push" in on_key, "Missing push trigger"
        branches = on_key["push"].get("branches", [])
        assert "main" in branches, "push trigger missing 'main' branch"



class TestJobs:
    def test_three_jobs_exist(self, workflow: dict) -> None:
        jobs = workflow.get("jobs", {})
        assert "well-harness-run" in jobs
        assert "notion-approval-dispatch" in jobs
        assert "post-merge-sync" in jobs

    def test_well_harness_run_triggers_on_pr(self, workflow: dict) -> None:
        condition = workflow["jobs"]["well-harness-run"].get("if", "")
        assert "pull_request" in condition, "well-harness-run should guard on pull_request event"

    def test_notion_approval_dispatch_triggers_on_dispatch(self, workflow: dict) -> None:
        condition = workflow["jobs"]["notion-approval-dispatch"].get("if", "")
        assert "repository_dispatch" in condition
        assert "notion_approval" in condition

    def test_post_merge_sync_triggers_on_main_push(self, workflow: dict) -> None:
        condition = workflow["jobs"]["post-merge-sync"].get("if", "")
        assert "push" in condition
        assert "main" in condition


class TestSecrets:
    def test_required_secrets_referenced(self, workflow_raw: str) -> None:
        for secret in REQUIRED_SECRETS:
            assert f"secrets.{secret}" in workflow_raw, \
                f"Secret '{secret}' not referenced in workflow"


class TestCliContract:
    def test_case_id_regex_present(self, workflow_raw: str) -> None:
        # The regex pattern should appear in the workflow for Case ID extraction
        assert r"\[" in workflow_raw, "Case ID extraction regex not found in workflow"

    def test_cli_run_subcommand_invoked(self, workflow_raw: str) -> None:
        assert "well_harness.cli run" in workflow_raw, \
            "Notion §3.5 CLI contract 'well_harness.cli run' not found in workflow"

    def test_pr_url_argument_present(self, workflow_raw: str) -> None:
        assert "--pr-url" in workflow_raw or "--github-pr-link" in workflow_raw, \
            "PR URL argument not passed to CLI in workflow"

    def test_notion_approval_verdict_handled(self, workflow_raw: str) -> None:
        assert "verdict" in workflow_raw.lower(), \
            "Notion approval verdict not handled in workflow"

    def test_adr_sync_step_exists(self, workflow_raw: str) -> None:
        assert "migrate_notion_schema" in workflow_raw, \
            "ADR sync step (migrate_notion_schema) not found in post-merge-sync job"
