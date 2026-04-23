"""Optional Notion runtime sync for well_harness batches.

This module uses the official Notion public API to register each CLI batch
into the project-specific task/session data sources configured for this repo.
"""

from __future__ import annotations

import os
import subprocess
from collections import Counter, defaultdict
from contextlib import nullcontext
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import yaml

from .schemas import HarnessRunRecord, HarnessRunStatus

NOTION_API_BASE_URL = "https://api.notion.com/v1"
DEFAULT_NOTION_VERSION = "2026-03-11"


@dataclass(frozen=True)
class NotionDataSources:
    """Project-scoped Notion destinations."""

    tasks: str
    sessions: str
    decisions: Optional[str] = None


@dataclass(frozen=True)
class NotionSyncConfig:
    """Runtime config for Notion registration."""

    enabled: bool
    token_env: str
    notion_version: str
    root_page_id: str
    data_sources: NotionDataSources
    github_repository: Optional[str] = None

    @property
    def token(self) -> Optional[str]:
        return os.environ.get(self.token_env)

    @property
    def is_configured(self) -> bool:
        return (
            self.enabled
            and bool(self.token)
            and bool(self.data_sources.tasks)
            and bool(self.data_sources.sessions)
        )

    @classmethod
    def from_file(cls, path: Path) -> "NotionSyncConfig":
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        notion = raw.get("notion", {})
        data_source_ids = notion.get("data_source_ids", {})
        return cls(
            enabled=bool(notion.get("enabled", False)),
            token_env=notion.get("token_env", "NOTION_API_KEY"),
            notion_version=notion.get("notion_version", DEFAULT_NOTION_VERSION),
            root_page_id=str(notion.get("root_page_id", "")),
            data_sources=NotionDataSources(
                tasks=str(data_source_ids.get("tasks", "")),
                sessions=str(data_source_ids.get("sessions", "")),
                decisions=str(data_source_ids.get("decisions", "")) or None,
            ),
            github_repository=str((raw.get("github", {}) or {}).get("repository", "")) or None,
        )


@dataclass(frozen=True)
class NotionSyncResult:
    """High-level result of a Notion registration attempt."""

    attempted: bool
    success: bool
    skipped_reason: Optional[str] = None
    batch_id: Optional[str] = None
    session_page_id: Optional[str] = None
    task_page_ids: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


@dataclass(frozen=True)
class NotionApprovalSyncResult:
    """High-level result of reconciling approval state back into sessions."""

    attempted: bool
    success: bool
    processed_sessions: int = 0
    updated_session_ids: List[str] = field(default_factory=list)
    skipped_reason: Optional[str] = None
    error_message: Optional[str] = None


class NotionRunRegistrar:
    """Create project-scoped task/session records for each harness batch."""

    def __init__(
        self,
        config: NotionSyncConfig,
        client: Optional[httpx.Client] = None,
    ) -> None:
        self._config = config
        self._client = client
        self._github_metadata_cache: Optional[Dict[str, str]] = None

    @classmethod
    def from_default_path(
        cls,
        path: Optional[Path] = None,
        client: Optional[httpx.Client] = None,
    ) -> "NotionRunRegistrar":
        config_path = (
            path
            or Path(__file__).resolve().parents[3] / "config" / "well_harness_control_plane.yaml"
        )
        return cls(config=NotionSyncConfig.from_file(config_path), client=client)

    def register_batch(
        self,
        run_records: List[HarnessRunRecord],
        invoked_command: str,
        executor_mode: str,
        github_pr_link: Optional[str] = None,
        github_issue_link: Optional[str] = None,
    ) -> NotionSyncResult:
        if not run_records:
            return NotionSyncResult(
                attempted=False, success=False, skipped_reason="No run records were produced."
            )

        if not self._config.is_configured:
            return NotionSyncResult(
                attempted=False,
                success=False,
                skipped_reason=(
                    f"Notion sync is disabled or missing {self._config.token_env}. "
                    "The run still completed locally."
                ),
            )

        batch_id = self._build_batch_id(run_records)
        session_body = self.build_session_request(
            batch_id=batch_id,
            run_records=run_records,
            invoked_command=invoked_command,
            executor_mode=executor_mode,
            github_pr_link=github_pr_link,
            github_issue_link=github_issue_link,
        )
        task_bodies = [
            self.build_task_request(
                run_record=record,
                batch_id=batch_id,
                invoked_command=invoked_command,
                session_title=session_body["properties"]["Session"]["title"][0]["text"]["content"],
                github_pr_link=github_pr_link,
                github_issue_link=github_issue_link,
            )
            for record in run_records
        ]

        session_page_id = None
        task_page_ids: List[str] = []

        try:
            with self._http_client() as client:
                # Find existing session by Run Batch
                existing_session_id = None
                session_pages = self._query_data_source_pages(
                    client, 
                    self._config.data_sources.sessions,
                    filter_prop={"property": "Run Batch", "rich_text": {"equals": batch_id}}
                )
                if session_pages:
                    existing_session_id = session_pages[0]["id"]
                
                # Find existing tasks
                existing_tasks_by_run_id = {}
                task_pages = self._query_data_source_pages(
                    client,
                    self._config.data_sources.tasks,
                    filter_prop={"property": "Session Batch", "rich_text": {"equals": batch_id}}
                )
                for page in task_pages:
                    run_id = self._page_property_text(page, "Run ID")
                    if run_id:
                        existing_tasks_by_run_id[run_id] = page["id"]

                if existing_session_id:
                    session_response = self._update_page_properties(client, existing_session_id, session_body["properties"])
                    session_page_id = existing_session_id
                else:
                    session_response = self._request(client, "POST", "/pages", json_body=session_body)
                    session_page_id = session_response["id"]
                
                for task_body, run_record in zip(task_bodies, run_records):
                    existing_task_id = existing_tasks_by_run_id.get(run_record.run_id)
                    if existing_task_id:
                        task_response = self._update_page_properties(client, existing_task_id, task_body["properties"])
                        task_page_ids.append(existing_task_id)
                    else:
                        task_response = self._request(client, "POST", "/pages", json_body=task_body)
                        task_page_ids.append(task_response["id"])
        except Exception as exc:
            return NotionSyncResult(
                attempted=True,
                success=False,
                batch_id=batch_id,
                session_page_id=session_page_id,
                task_page_ids=task_page_ids,
                error_message=str(exc),
            )

        return NotionSyncResult(
            attempted=True,
            success=True,
            batch_id=batch_id,
            session_page_id=session_page_id,
            task_page_ids=task_page_ids,
        )

    def create_standalone_task(
        self,
        case_id: str,
        run_id: str,
        status: str = "Pending Review",
        summary: str = "Execution paused for human fallback.",
        invoked_command: str = "langgraph fallback",
        verdict: str = "Needs Review",
        github_pr_link: str = "",
        github_issue_link: str = "",
    ) -> NotionSyncResult:
        """Create a single task record without a full batch session (for mid-run interrupts)."""
        if not self._config.is_configured:
            return NotionSyncResult(
                attempted=False, success=False, skipped_reason="Notion sync disabled"
            )

        github = self._github_metadata()
        batch_id = run_id
        task_title = f"{case_id} run review {run_id}"

        task_body = {
            "parent": {
                "type": "data_source_id",
                "data_source_id": self._config.data_sources.tasks,
            },
            "properties": {
                "Task": self._title_prop(task_title),
                "Status": self._select_prop(status),
                "Priority": self._select_prop("P0" if status == "Pending Review" else "P2"),
                "Type": self._select_prop("Review"),
                "Case ID": self._rich_text_prop(case_id),
                "Run ID": self._rich_text_prop(run_id),
                "Summary": self._rich_text_prop(summary),
                "Command": self._rich_text_prop(invoked_command),
                "GitHub Commit Link": self._url_prop(github["commit_url"]),
                "Approval Status": self._select_prop("Awaiting Approval"),
                "Verdict": self._select_prop(verdict),
                "Review Summary": self._rich_text_prop(
                    "Waiting for human review due to graph interrupt."
                ),
                "Next Action": self._rich_text_prop(
                    "Review project_state artifacts and determine next steps."
                ),
                "GitHub PR Link": self._url_prop(github_pr_link),
                "GitHub Issue Link": self._url_prop(github_issue_link),
                                "Session Batch": self._rich_text_prop(batch_id),
                "Sprint": self._select_prop("S2.1"),
                "Model": None,
                "Tokens Used": self._number_prop(None),
                "Tokens Budget": self._number_prop(None),
                "Branch": None,
                "ADR Link": self._url_prop(""),
                "Start SHA": None,
            },
        }

        try:
            with self._http_client() as client:
                task_response = self._request(client, "POST", "/pages", json_body=task_body)
                return NotionSyncResult(
                    attempted=True,
                    success=True,
                    batch_id=batch_id,
                    task_page_ids=[task_response["id"]],
                )
        except Exception as exc:
            return NotionSyncResult(
                attempted=True,
                success=False,
                error_message=str(exc),
            )

    def register_decision(
        self,
        decisions: Optional[List[Dict[str, Any]]] = None,
    ) -> NotionSyncResult:
        if not decisions:
            return NotionSyncResult(
                attempted=False, success=True, skipped_reason="No decisions provided."
            )
            
        if not self._config.is_configured or not self._config.data_sources.decisions:
            return NotionSyncResult(
                attempted=False,
                success=False,
                skipped_reason=(
                    f"Notion sync is disabled or missing decisions data source. "
                    "The run still completed locally."
                ),
            )

        task_page_ids = []
        try:
            with self._http_client() as client:
                for decision in decisions:
                    decision_body = self.build_decision_request(decision)
                    task_response = self._request(client, "POST", "/pages", json_body=decision_body)
                    task_page_ids.append(task_response["id"])
        except Exception as exc:
            return NotionSyncResult(
                attempted=True,
                success=False,
                task_page_ids=task_page_ids,
                error_message=str(exc),
            )

        return NotionSyncResult(
            attempted=True,
            success=True,
            task_page_ids=task_page_ids,
        )

    def build_decision_request(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "parent": {
                "type": "data_source_id",
                "data_source_id": self._config.data_sources.decisions,
            },
            "properties": {
                "Decision": self._title_prop(decision.get("title", "Untitled Decision")),
                "Status": self._select_prop(decision.get("status", "Proposed")),
                "Context": self._rich_text_prop(decision.get("context", "")),
                "Consequences": self._rich_text_prop(decision.get("consequences", "")),
            },
            "children": [
                self._paragraph_block(decision.get("details", ""))
            ]
        }

    def build_graph_run_id(
        self,
        case_id: str,
        now: Optional[datetime] = None,
    ) -> str:
        """Build a repo-scoped run id for graph interrupts and standalone tasks."""
        github = self._github_metadata()
        shortsha = github.get("commit_short") or "nogit"
        stamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%d")
        return f"run-{stamp}-{case_id}-{shortsha}"

    def reconcile_session_approval_status(
        self,
        batch_id: Optional[str] = None,
    ) -> NotionApprovalSyncResult:
        if not self._config.is_configured:
            return NotionApprovalSyncResult(
                attempted=False,
                success=False,
                skipped_reason=(
                    f"Notion sync is disabled or missing {self._config.token_env}. "
                    "No approval reconciliation was attempted."
                ),
            )

        processed_sessions = 0
        updated_session_ids: List[str] = []

        try:
            with self._http_client() as client:
                session_pages = self._query_data_source_pages(
                    client, self._config.data_sources.sessions
                )
                task_pages = self._query_data_source_pages(client, self._config.data_sources.tasks)

                tasks_by_batch: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
                for task_page in task_pages:
                    task_batch = self._page_property_text(task_page, "Session Batch")
                    if task_batch:
                        tasks_by_batch[task_batch].append(task_page)

                for session_page in session_pages:
                    session_batch = self._page_property_text(session_page, "Run Batch")
                    if not session_batch:
                        continue
                    if batch_id and session_batch != batch_id:
                        continue
                    if (
                        not batch_id
                        and self._page_property_text(session_page, "Status") == "Closed"
                    ):
                        continue

                    related_tasks = tasks_by_batch.get(session_batch, [])
                    if not related_tasks:
                        continue

                    processed_sessions += 1
                    next_status = self._session_status_from_approvals(related_tasks)
                    next_outcome = self._session_outcome_from_approvals(related_tasks)
                    next_summary = self._approval_summary_text(
                        base_summary=self._page_property_text(session_page, "Summary"),
                        related_tasks=related_tasks,
                    )

                    current_status = self._page_property_text(session_page, "Status")
                    current_outcome = self._page_property_text(session_page, "Outcome")
                    current_summary = self._page_property_text(session_page, "Summary")
                    if (
                        current_status == next_status
                        and current_outcome == next_outcome
                        and current_summary == next_summary
                    ):
                        continue

                    self._update_page_properties(
                        client,
                        page_id=session_page["id"],
                        properties={
                            "Status": self._select_prop(next_status),
                            "Outcome": self._select_prop(next_outcome),
                            "Summary": self._rich_text_prop(next_summary),
                        },
                    )
                    updated_session_ids.append(session_page["id"])

        except Exception as exc:
            return NotionApprovalSyncResult(
                attempted=True,
                success=False,
                processed_sessions=processed_sessions,
                updated_session_ids=updated_session_ids,
                error_message=str(exc),
            )

        return NotionApprovalSyncResult(
            attempted=True,
            success=True,
            processed_sessions=processed_sessions,
            updated_session_ids=updated_session_ids,
        )

    def build_session_request(
        self,
        batch_id: str,
        run_records: List[HarnessRunRecord],
        invoked_command: str,
        executor_mode: str,
        github_pr_link: Optional[str] = None,
        github_issue_link: Optional[str] = None,
    ) -> Dict[str, Any]:
        github = self._github_metadata()
        title = f"well_harness batch {batch_id}"
        session_status = self._session_status(run_records)
        session_kind = (
            "Review"
            if any(record.status != HarnessRunStatus.COMPLETED for record in run_records)
            else "Execution"
        )
        summary = self._session_summary(run_records, executor_mode, github)
        outcome = self._session_outcome(run_records)
        cases = ", ".join(record.case_id for record in run_records)

        execution_notes = []
        for r in run_records:
            if r.handoff:
                execution_notes.append(f"[{r.case_id}] {r.handoff.did_what}")
        note_text = (
            "\n".join(execution_notes)
            if execution_notes
            else "GitHub is the source of truth; local execution artifacts stay out of Notion."
        )

        return {
            "parent": {
                "type": "data_source_id",
                "data_source_id": self._config.data_sources.sessions,
            },
            "properties": {
                "Session": self._title_prop(title),
                "Status": self._select_prop(session_status),
                "Kind": self._select_prop(session_kind),
                "Outcome": self._select_prop(outcome),
                "Run Batch": self._rich_text_prop(batch_id),
                "Cases": self._rich_text_prop(cases),
                "Summary": self._rich_text_prop(summary),
                "GitHub Commit Link": self._url_prop(github["commit_url"]),
                "GitHub PR Link": self._url_prop(github_pr_link or ""),
                "GitHub Issue Link": self._url_prop(github_issue_link or ""),
                "Command": self._rich_text_prop(invoked_command),
                                "Execution Note": self._rich_text_prop(note_text),
                "Sprint": self._select_prop(run_records[0].sprint) if run_records[0].sprint else self._select_prop("S2.1"),
                "Model": self._select_prop(run_records[0].model) if run_records[0].model else None,
                "Tokens Used": self._number_prop(run_records[0].tokens_used),
                "Tokens Budget": self._number_prop(run_records[0].tokens_budget),
                "Branch": self._rich_text_prop(run_records[0].branch) if run_records[0].branch else None,
                "ADR Link": self._url_prop(run_records[0].adr_link),
                "Start SHA": self._rich_text_prop(run_records[0].start_sha) if run_records[0].start_sha else None,
            },
            "children": self._session_children(
                batch_id, run_records, invoked_command, executor_mode, github
            ),
        }

    def build_task_request(
        self,
        run_record: HarnessRunRecord,
        batch_id: str,
        invoked_command: str,
        session_title: str,
        github_pr_link: Optional[str] = None,
        github_issue_link: Optional[str] = None,
    ) -> Dict[str, Any]:
        github = self._github_metadata()
        task_title = f"{run_record.case_id} run review {run_record.run_id}"
        return {
            "parent": {
                "type": "data_source_id",
                "data_source_id": self._config.data_sources.tasks,
            },
            "properties": {
                "Task": self._title_prop(task_title),
                "Status": self._select_prop(self._task_status(run_record)),
                "Priority": self._select_prop(self._task_priority(run_record)),
                "Type": self._select_prop(self._task_type(run_record)),
                "Case ID": self._rich_text_prop(run_record.case_id),
                "Run ID": self._rich_text_prop(run_record.run_id),
                "Summary": self._rich_text_prop(run_record.report_summary),
                "Command": self._rich_text_prop(invoked_command),
                "GitHub Commit Link": self._url_prop(github["commit_url"]),
                "Approval Status": self._select_prop(self._approval_status(run_record)),
                "Verdict": self._select_prop(self._verdict(run_record)),
                
                "Review Summary": self._rich_text_prop(run_record.verification.summary),
                "Next Action": self._rich_text_prop(self._next_action(run_record)),
                "GitHub PR Link": self._url_prop(github_pr_link or ""),
                "GitHub Issue Link": self._url_prop(github_issue_link or ""),
                                "Session Batch": self._rich_text_prop(batch_id),
                "Sprint": self._select_prop(run_record.sprint) if run_record.sprint else self._select_prop("S2.1"),
                "Model": self._select_prop(run_record.model) if run_record.model else None,
                "Tokens Used": self._number_prop(run_record.tokens_used),
                "Tokens Budget": self._number_prop(run_record.tokens_budget),
                "Branch": self._rich_text_prop(run_record.branch) if run_record.branch else None,
                "ADR Link": self._url_prop(run_record.adr_link),
                "Start SHA": self._rich_text_prop(run_record.start_sha) if run_record.start_sha else None,
            },
            "children": self._task_children(run_record, batch_id, session_title, github),
        }

    def _http_client(self) -> httpx.Client:
        if self._client is not None:
            return nullcontext(self._client)
        return httpx.Client(
            base_url=NOTION_API_BASE_URL,
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {self._config.token}",
                "Notion-Version": self._config.notion_version,
                "Content-Type": "application/json",
            },
        )

    @staticmethod
    def _request(
        client: httpx.Client,
        method: str,
        path: str,
        json_body: Dict[str, Any],
    ) -> Dict[str, Any]:
        response = client.request(method, path, json=json_body)
        response.raise_for_status()
        return response.json()

    def _query_data_source_pages(
        self,
        client: httpx.Client,
        data_source_id: str,
        filter_prop: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        next_cursor: Optional[str] = None

        while True:
            payload: Dict[str, Any] = {"page_size": 100}
            if next_cursor:
                payload["start_cursor"] = next_cursor
            if filter_prop:
                payload["filter"] = filter_prop
            response = self._request(
                client,
                "POST",
                f"/data_sources/{data_source_id}/query",
                json_body=payload,
            )
            results.extend(response.get("results", []))
            if not response.get("has_more"):
                return results
            next_cursor = response.get("next_cursor")

    @staticmethod
    def _update_page_properties(
        client: httpx.Client,
        page_id: str,
        properties: Dict[str, Any],
    ) -> Dict[str, Any]:
        response = client.request("PATCH", f"/pages/{page_id}", json={"properties": properties})
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _build_batch_id(run_records: List[HarnessRunRecord]) -> str:
        anchor = min(run_records, key=lambda record: record.started_at)
        return anchor.run_id.replace("-", "").replace("+00:00", "Z")

    @staticmethod
    def _task_status(run_record: HarnessRunRecord) -> str:
        if run_record.status == HarnessRunStatus.FAILED:
            return "Blocked"
        if run_record.status == HarnessRunStatus.PENDING_REVIEW:
            return "Pending Review"
        if run_record.status == HarnessRunStatus.COMPLETED:
            return "Done"
        return "Running"

    @staticmethod
    def _approval_status(run_record: HarnessRunRecord) -> str:
        if run_record.status == HarnessRunStatus.COMPLETED:
            return "Approved"
        if run_record.status == HarnessRunStatus.FAILED:
            return "Re-run Required"
        return "Awaiting Approval"

    @staticmethod
    def _verdict(run_record: HarnessRunRecord) -> str:
        if run_record.status == HarnessRunStatus.COMPLETED:
            return "Accept"
        if run_record.status == HarnessRunStatus.FAILED:
            return "Re-run"
        return "Needs Review"

    @staticmethod
    def _task_type(run_record: HarnessRunRecord) -> str:
        return "Review" if run_record.status != HarnessRunStatus.COMPLETED else "Execution"

    @staticmethod
    def _task_priority(run_record: HarnessRunRecord) -> str:
        if run_record.status == HarnessRunStatus.FAILED:
            return "P0"
        if any(item.severity == "critical" for item in run_record.verification.findings):
            return "P0"
        if any(item.severity == "warning" for item in run_record.verification.findings):
            return "P1"
        return "P3"

    @staticmethod
    def _next_action(run_record: HarnessRunRecord) -> str:
        if run_record.handoff and run_record.handoff.next_steps:
            return run_record.handoff.next_steps[0]
        if run_record.status == HarnessRunStatus.COMPLETED:
            return "No manual action required."
        if run_record.status == HarnessRunStatus.FAILED:
            return "Inspect the failed run and decide whether to re-run."
        return "Review the current run and record the approval decision."

    @staticmethod
    def _session_status(run_records: List[HarnessRunRecord]) -> str:
        if any(record.status != HarnessRunStatus.COMPLETED for record in run_records):
            return "Open"
        return "Captured"

    @staticmethod
    def _session_outcome(run_records: List[HarnessRunRecord]) -> str:
        statuses = {record.status for record in run_records}
        if statuses == {HarnessRunStatus.COMPLETED}:
            return "Clean Pass"
        if statuses == {HarnessRunStatus.FAILED}:
            return "Failed"
        if HarnessRunStatus.PENDING_REVIEW in statuses and len(statuses) == 1:
            return "Pending Review"
        return "Mixed"

    @staticmethod
    def _session_summary(
        run_records: List[HarnessRunRecord],
        executor_mode: str,
        github: Dict[str, str],
    ) -> str:
        parts = [f"{record.case_id}:{record.status.value}" for record in run_records]
        baseline = NotionRunRegistrar._github_baseline_text(github)
        return f"{baseline}. Batch completed via {executor_mode}. " + "; ".join(parts)

    @staticmethod
    def _session_status_from_approvals(task_pages: List[Dict[str, Any]]) -> str:
        approval_statuses = [
            NotionRunRegistrar._page_property_text(task_page, "Approval Status")
            for task_page in task_pages
        ]
        if any(status == "Awaiting Approval" for status in approval_statuses):
            return "Open"
        return "Closed"

    @staticmethod
    def _session_outcome_from_approvals(task_pages: List[Dict[str, Any]]) -> str:
        approval_statuses = [
            NotionRunRegistrar._page_property_text(task_page, "Approval Status")
            for task_page in task_pages
        ]
        verdicts = [
            NotionRunRegistrar._page_property_text(task_page, "Verdict") for task_page in task_pages
        ]
        if any(status == "Awaiting Approval" for status in approval_statuses):
            return "Pending Review"
        if any(status in {"Rejected", "Re-run Required"} for status in approval_statuses):
            return "Failed"
        if any(verdict in {"Reject", "Re-run"} for verdict in verdicts):
            return "Failed"
        if any(verdict == "Accept with Note" for verdict in verdicts):
            return "Mixed"
        return "Clean Pass"

    @staticmethod
    def _approval_summary_text(
        base_summary: str,
        related_tasks: List[Dict[str, Any]],
    ) -> str:
        stable_summary = base_summary.split(" | Approval:", 1)[0]
        verdict_counts = Counter(
            NotionRunRegistrar._page_property_text(task_page, "Verdict")
            for task_page in related_tasks
        )
        approval_counts = Counter(
            NotionRunRegistrar._page_property_text(task_page, "Approval Status")
            for task_page in related_tasks
        )
        approval_summary = (
            "Approval: "
            f"approved={approval_counts.get('Approved', 0)}, "
            f"pending={approval_counts.get('Awaiting Approval', 0)}, "
            f"rejected={approval_counts.get('Rejected', 0)}, "
            f"rerun={approval_counts.get('Re-run Required', 0)}, "
            f"accept_with_note={verdict_counts.get('Accept with Note', 0)}"
        )
        return f"{stable_summary} | {approval_summary}" if stable_summary else approval_summary

    def _github_metadata(self) -> Dict[str, str]:
        if self._github_metadata_cache is not None:
            return self._github_metadata_cache

        repository = self._config.github_repository or ""
        repo_url = f"https://github.com/{repository}" if repository else ""
        branch = self._git_output("git", "rev-parse", "--abbrev-ref", "HEAD") or "main"
        commit_sha = self._git_output("git", "rev-parse", "HEAD")
        commit_short = commit_sha[:7] if commit_sha else ""
        commit_url = f"{repo_url}/commit/{commit_sha}" if repo_url and commit_sha else ""
        self._github_metadata_cache = {
            "repository": repository,
            "repo_url": repo_url,
            "branch": branch,
            "commit_sha": commit_sha,
            "commit_short": commit_short,
            "commit_url": commit_url,
        }
        return self._github_metadata_cache

    @staticmethod
    def _github_baseline_text(github: Dict[str, str]) -> str:
        if github.get("commit_short"):
            return f"GitHub baseline {github.get('branch', 'main')}@{github['commit_short']}"
        if github.get("repo_url"):
            return f"GitHub repo {github['repo_url']}"
        return "GitHub baseline pending"

    @staticmethod
    def _git_output(*args: str) -> str:
        try:
            return subprocess.check_output(
                list(args),
                cwd=Path(__file__).resolve().parents[3],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
        except Exception:
            return ""

    @staticmethod
    def _page_property_text(page: Dict[str, Any], property_name: str) -> str:
        property_value = page.get("properties", {}).get(property_name, {})
        property_type = property_value.get("type")
        if property_type == "title":
            return "".join(
                item.get("plain_text") or item.get("text", {}).get("content", "")
                for item in property_value.get("title", [])
            )
        if property_type == "rich_text":
            return "".join(
                item.get("plain_text") or item.get("text", {}).get("content", "")
                for item in property_value.get("rich_text", [])
            )
        if property_type in {"select", "status"}:
            return (property_value.get(property_type) or {}).get("name", "")
        if property_type == "number":
            number_value = property_value.get("number")
            return "" if number_value is None else str(number_value)
        if property_type == "url":
            return property_value.get("url", "") or ""
        return ""

    def _session_children(
        self,
        batch_id: str,
        run_records: List[HarnessRunRecord],
        invoked_command: str,
        executor_mode: str,
        github: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        blocks: List[Dict[str, Any]] = [
            self._heading_block("运行批次"),
            self._paragraph_block(f"Batch ID: {batch_id}"),
            self._paragraph_block(f"Command: {invoked_command}"),
            self._paragraph_block(f"Executor: {executor_mode}"),
            self._paragraph_block(f"GitHub Baseline: {self._github_baseline_text(github)}"),
            self._paragraph_block(f"GitHub Commit: {github.get('commit_url') or '待补充'}"),
            self._heading_block("案例结果"),
        ]
        for record in run_records:
            blocks.append(
                self._bullet_block(
                    f"{record.case_id} | status={record.status.value} | summary={record.report_summary}"
                )
            )
        blocks.extend(
            [
                self._heading_block("后续动作"),
                self._numbered_block("若存在 pending_review，请在任务库的审批流中完成审批结论。"),
                self._numbered_block("若存在 failed，请评估是否需要 fresh CalculiX run。"),
                self._numbered_block("代码实现与模块事实以 GitHub 仓库为准。"),
            ]
        )
        return blocks

    def _task_children(
        self,
        run_record: HarnessRunRecord,
        batch_id: str,
        session_title: str,
        github: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        return [
            self._heading_block("审批流"),
            self._paragraph_block(f"当前阶段：{self._approval_status(run_record)}"),
            self._bullet_block(f"Batch: {batch_id}"),
            self._bullet_block(f"Session: {session_title}"),
            self._bullet_block(f"Run ID: {run_record.run_id}"),
            self._bullet_block(f"GitHub Baseline: {self._github_baseline_text(github)}"),
            self._bullet_block(f"GitHub Commit: {github.get('commit_url') or '待补充'}"),
            self._bullet_block("GitHub PR: 待创建或待绑定"),
            self._bullet_block("GitHub Issue: 待创建或待绑定"),
            self._heading_block("结论模板"),
            self._paragraph_block(
                "1. GitHub 证据摘要：补充本次 run 关联的 commit、PR、issue 和关键结果摘要。"
            ),
            self._paragraph_block("2. 风险判断：判断当前结果是否可接受，以及风险级别和说明。"),
            self._paragraph_block("3. 审批决定：填写 Verdict、Approval Status 和审批说明。"),
            self._paragraph_block("4. 下一步：填写是否需要新建 issue、补 PR、还是继续重跑。"),
        ]

    @staticmethod
    def _title_prop(value: str) -> Dict[str, Any]:
        return {"title": [{"type": "text", "text": {"content": value[:2000]}}]}

    @staticmethod
    def _rich_text_prop(value: str) -> Dict[str, Any]:
        return {"rich_text": [{"type": "text", "text": {"content": value[:2000]}}]}

    @staticmethod
    def _select_prop(value: str) -> Dict[str, Any]:
        return {"select": {"name": value}}

    @staticmethod
    def _number_prop(value: Optional[int]) -> Dict[str, Any]:
        if value is None:
            return {'number': None}
        return {'number': value}

    @staticmethod
    def _url_prop(value: str) -> Dict[str, Any]:
        return {"url": value or None}

    @staticmethod
    def _text(value: str) -> List[Dict[str, Any]]:
        return [{"type": "text", "text": {"content": value[:2000]}}]

    @classmethod
    def _heading_block(cls, value: str) -> Dict[str, Any]:
        return {
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": cls._text(value)},
        }

    @classmethod
    def _paragraph_block(cls, value: str) -> Dict[str, Any]:
        return {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": cls._text(value)},
        }

    @classmethod
    def _bullet_block(cls, value: str) -> Dict[str, Any]:
        return {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": cls._text(value)},
        }

    @classmethod
    def _numbered_block(cls, value: str) -> Dict[str, Any]:
        return {
            "object": "block",
            "type": "numbered_list_item",
            "numbered_list_item": {"rich_text": cls._text(value)},
        }
