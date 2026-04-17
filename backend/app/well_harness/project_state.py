"""Persistence helpers for project_state audit retention."""

from __future__ import annotations

import json
from pathlib import Path

from .control_plane import ControlPlaneSyncPlan
from .schemas import HarnessRunRecord


class ProjectStateStore:
    """Persist run inputs, outputs, and decisions under project_state/."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path(__file__).resolve().parents[3] / "project_state"

    def run_dir(self, case_id: str, run_id: str) -> Path:
        return self.root / "runs" / case_id / run_id

    def persist(self, run_record: HarnessRunRecord, sync_plan: ControlPlaneSyncPlan) -> Path:
        target = self.run_dir(run_record.case_id, run_record.run_id)
        target.mkdir(parents=True, exist_ok=True)

        if hasattr(run_record.task_spec, "model_dump"):
            task_spec_payload = run_record.task_spec.model_dump(mode="json")
        else:
            task_spec_payload = run_record.task_spec.dict()

        self._write_json(target / "input_summary.json", {"task_spec": task_spec_payload})
        self._write_json(
            target / "output_summary.json",
            {
                "status": run_record.status.value,
                "report_summary": run_record.report_summary,
                "report_metrics": run_record.report_metrics,
                "validation": run_record.validation,
                "verification": {
                    "passed": run_record.verification.passed,
                    "summary": run_record.verification.summary,
                    "reference_source": run_record.verification.reference_source,
                    "correction_policy": run_record.verification.correction_policy,
                    "findings": [item.__dict__ for item in run_record.verification.findings],
                },
            },
        )
        self._write_json(target / "artifacts.json", {"artifacts": [item.__dict__ for item in run_record.artifacts]})
        self._write_json(target / "control_plane_sync.json", json.loads(sync_plan.stable_repr()))
        if run_record.handoff is not None:
            (target / "handoff.md").write_text(run_record.handoff.to_markdown(), encoding="utf-8")
        return target

    @staticmethod
    def _write_json(path: Path, payload: dict) -> None:
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
