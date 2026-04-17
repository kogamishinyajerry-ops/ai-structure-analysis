"""Deterministic Notion/GitHub payload builders for well-harness runs."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Tuple

from .schemas import HarnessRunRecord


@dataclass(frozen=True)
class NotionUpdatePayload:
    title: str
    status: str
    summary: str
    verification: str
    artifact_paths: Tuple[str, ...]
    next_step: str


@dataclass(frozen=True)
class GitHubIssuePayload:
    title: str
    body: str
    labels: Tuple[str, ...]


@dataclass(frozen=True)
class ControlPlaneSyncPlan:
    notion: NotionUpdatePayload
    github: GitHubIssuePayload

    def stable_repr(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True)


class ControlPlaneSyncBuilder:
    """Build connector-ready payloads without requiring live auth."""

    STATUS_MAP = {
        "completed": "Done",
        "pending_review": "Pending Review",
        "failed": "Blocked",
        "running": "In Progress",
    }

    def build(self, run_record: HarnessRunRecord) -> ControlPlaneSyncPlan:
        next_step = (
            "Review the generated handoff and decide whether to accept the run as-is."
            if run_record.status.value == "pending_review"
            else "Attach the run artifacts to the current execution thread."
        )
        notion = NotionUpdatePayload(
            title=f"{run_record.case_id} well-harness",
            status=self.STATUS_MAP[run_record.status.value],
            summary=run_record.report_summary,
            verification=run_record.verification.summary,
            artifact_paths=tuple(item.path for item in run_record.artifacts),
            next_step=next_step,
        )

        body_lines = [
            f"Case: {run_record.case_id}",
            f"Status: {run_record.status.value}",
            f"Summary: {run_record.report_summary}",
            f"Verification: {run_record.verification.summary}",
            "",
            "Artifacts:",
            *(f"- {item.path}" for item in run_record.artifacts),
        ]
        github = GitHubIssuePayload(
            title=f"[well-harness] {run_record.case_id} {run_record.status.value}",
            body="\n".join(body_lines),
            labels=("well-harness", run_record.status.value),
        )
        return ControlPlaneSyncPlan(notion=notion, github=github)
