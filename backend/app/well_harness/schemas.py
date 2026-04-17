"""Shared schemas for the well-harness automation layer."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from ..models.task_spec import TaskSpec


def _jsonable_model(model: Any) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    if hasattr(model, "dict"):
        return model.dict()
    raise TypeError(f"Unsupported model type: {type(model)!r}")


def _json_default(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")


class HarnessRunStatus(str, Enum):
    """Stable run lifecycle states for automation control planes."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PENDING_REVIEW = "pending_review"


@dataclass(frozen=True)
class ArtifactRecord:
    """A persisted artifact produced or referenced by the harness."""

    kind: str
    path: str
    description: str


@dataclass(frozen=True)
class VerificationFinding:
    """A single automated verification observation."""

    title: str
    expected: Any
    actual: Any
    severity: str = "info"
    relative_error: Optional[float] = None
    tolerance: Optional[float] = None


@dataclass
class VerificationReport:
    """Automation-level verification summary."""

    passed: bool
    summary: str
    findings: List[VerificationFinding] = field(default_factory=list)
    reference_source: Optional[str] = None
    correction_policy: str = "suggest-only, not auto-applied"


@dataclass
class ExecutorRunResult:
    """Result returned by a structural executor implementation."""

    success: bool
    executor_name: str
    frd_path: str
    output_dir: str
    is_replay: bool = False
    execution_time_s: float = 0.0
    logs: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


@dataclass
class HandoffPacket:
    """Mandatory handoff payload for cross-executor consistency."""

    did_what: str
    did_not_do: str
    risks: List[str]
    next_steps: List[str]
    artifact_paths: List[str]

    def to_markdown(self) -> str:
        risk_lines = "\n".join(f"- {item}" for item in self.risks) or "- 无"
        next_step_lines = "\n".join(f"- {item}" for item in self.next_steps) or "- 无"
        artifact_lines = "\n".join(f"- {item}" for item in self.artifact_paths) or "- 无"
        return (
            "# Handoff\n\n"
            "## 做了什么\n"
            f"{self.did_what}\n\n"
            "## 没做什么\n"
            f"{self.did_not_do}\n\n"
            "## 风险点\n"
            f"{risk_lines}\n\n"
            "## 下一步建议\n"
            f"{next_step_lines}\n\n"
            "## 产物路径\n"
            f"{artifact_lines}\n"
        )


@dataclass
class HarnessRunRecord:
    """Full orchestration record for a single case execution."""

    run_id: str
    case_id: str
    status: HarnessRunStatus
    started_at: str
    completed_at: str
    task_spec: TaskSpec
    executor: ExecutorRunResult
    report_summary: str
    report_metrics: Dict[str, Any]
    validation: Dict[str, Any]
    verification: VerificationReport
    artifacts: List[ArtifactRecord] = field(default_factory=list)
    handoff: Optional[HandoffPacket] = None
    project_state_dir: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "case_id": self.case_id,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "task_spec": _jsonable_model(self.task_spec),
            "executor": asdict(self.executor),
            "report_summary": self.report_summary,
            "report_metrics": self.report_metrics,
            "validation": self.validation,
            "verification": {
                "passed": self.verification.passed,
                "summary": self.verification.summary,
                "reference_source": self.verification.reference_source,
                "correction_policy": self.verification.correction_policy,
                "findings": [asdict(item) for item in self.verification.findings],
            },
            "artifacts": [asdict(item) for item in self.artifacts],
            "handoff": None if self.handoff is None else asdict(self.handoff),
            "project_state_dir": self.project_state_dir,
        }
