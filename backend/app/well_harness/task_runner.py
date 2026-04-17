"""Main orchestration loop for the structure-analysis well-harness."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from ..parsers.frd_parser import FRDParser
from ..services.report_generator import ReportGenerator
from .control_plane import ControlPlaneSyncBuilder, ControlPlaneSyncPlan
from .executors import ReplayExecutor, StructuralExecutor
from .knowledge_store import GoldenSampleKnowledgeStore
from .project_state import ProjectStateStore
from .schemas import (
    ArtifactRecord,
    HarnessRunRecord,
    HarnessRunStatus,
    HandoffPacket,
    VerificationFinding,
    VerificationReport,
)


class WellHarnessRunner:
    """Structural-analysis analogue of the cfd-harness-unified runner."""

    def __init__(
        self,
        executor: Optional[StructuralExecutor] = None,
        store: Optional[GoldenSampleKnowledgeStore] = None,
        report_generator: Optional[ReportGenerator] = None,
        state_store: Optional[ProjectStateStore] = None,
        sync_builder: Optional[ControlPlaneSyncBuilder] = None,
        stress_tolerance: float = 0.35,
    ) -> None:
        self._executor = executor or ReplayExecutor()
        self._store = store or GoldenSampleKnowledgeStore()
        self._report_generator = report_generator or ReportGenerator(self._store.root)
        self._state_store = state_store or ProjectStateStore()
        self._sync_builder = sync_builder or ControlPlaneSyncBuilder()
        self._stress_tolerance = stress_tolerance

    def run_cases(self, case_ids: List[str]) -> List[HarnessRunRecord]:
        return [self.run_case(case_id) for case_id in case_ids]

    def run_case(self, case_id: str) -> HarnessRunRecord:
        started_at = self._iso_now()
        run_id = self._make_run_id(case_id)
        state_dir = self._state_store.run_dir(case_id, run_id)
        task_spec = self._store.build_task_spec(case_id)

        execution = self._executor.execute(case_id, task_spec, self._store)
        if not execution.success:
            run_record = HarnessRunRecord(
                run_id=run_id,
                case_id=case_id,
                status=HarnessRunStatus.FAILED,
                started_at=started_at,
                completed_at=self._iso_now(),
                task_spec=task_spec,
                executor=execution,
                report_summary=execution.error_message or "Execution failed before parsing",
                report_metrics={},
                validation={"status": "FAILED"},
                verification=VerificationReport(
                    passed=False,
                    summary=execution.error_message or "Execution failed before parsing",
                    findings=[
                        VerificationFinding(
                            title="executor_failure",
                            expected="successful execution",
                            actual=execution.error_message or "unknown error",
                            severity="critical",
                        )
                    ],
                ),
            )
            run_record.project_state_dir = str(state_dir)
            run_record.artifacts = [ArtifactRecord("project_state", str(state_dir), "Persisted run state directory")]
            run_record.handoff = self._build_handoff(run_record)
            self._persist(run_record)
            return run_record

        parser = FRDParser()
        parsed = parser.parse(execution.frd_path)
        report = self._report_generator.generate(parsed, case_id=case_id)
        verification = self._verify_case(case_id, parsed.max_von_mises, report.validation)
        status = self._resolve_status(execution.success, parsed.success, verification, report.validation)

        artifacts = self._build_artifacts(case_id, execution.frd_path, state_dir)
        run_record = HarnessRunRecord(
            run_id=run_id,
            case_id=case_id,
            status=status,
            started_at=started_at,
            completed_at=self._iso_now(),
            task_spec=task_spec,
            executor=execution,
            report_summary=report.summary,
            report_metrics=report.metrics,
            validation=report.validation,
            verification=verification,
            artifacts=artifacts,
            project_state_dir=str(state_dir),
        )
        run_record.handoff = self._build_handoff(run_record)
        self._persist(run_record)
        return run_record

    def build_sync_plan(self, run_record: HarnessRunRecord) -> ControlPlaneSyncPlan:
        return self._sync_builder.build(run_record)

    def _persist(self, run_record: HarnessRunRecord) -> None:
        sync_plan = self._sync_builder.build(run_record)
        self._state_store.persist(run_record, sync_plan)

    def _build_artifacts(self, case_id: str, frd_path: str, state_dir: Path) -> List[ArtifactRecord]:
        expected_path = self._store.case_dir(case_id) / "expected_results.json"
        artifacts = [
            ArtifactRecord("result_frd", frd_path, "Primary FRD result consumed by the harness"),
            ArtifactRecord("expected_results", str(expected_path), "Golden sample reference payload"),
            ArtifactRecord("project_state", str(state_dir), "Persisted run state directory"),
        ]
        input_file = self._store.find_input_file(case_id)
        if input_file is not None:
            artifacts.append(
                ArtifactRecord("input_inp", str(input_file), "CalculiX input deck for the case"),
            )
        return artifacts

    def _verify_case(
        self,
        case_id: str,
        actual_stress: Optional[float],
        validation: dict,
    ) -> VerificationReport:
        findings: List[VerificationFinding] = []
        reference_stress, source = self._store.resolve_reference_stress(case_id)

        if actual_stress is None:
            findings.append(
                VerificationFinding(
                    title="missing_stress_metric",
                    expected="resolved stress metric",
                    actual=None,
                    severity="critical",
                )
            )

        if reference_stress is not None and actual_stress is not None:
            relative_error = abs(actual_stress - reference_stress) / reference_stress if reference_stress else 0.0
            severity = "warning" if relative_error > self._stress_tolerance else "info"
            findings.append(
                VerificationFinding(
                    title="reference_stress_comparison",
                    expected=round(reference_stress, 4),
                    actual=round(actual_stress, 4),
                    severity=severity,
                    relative_error=round(relative_error, 4),
                    tolerance=self._stress_tolerance,
                )
            )

        if validation.get("status") == "FAIL":
            findings.append(
                VerificationFinding(
                    title="report_validation_failed",
                    expected="PASS",
                    actual=validation,
                    severity="warning",
                )
            )

        blocking = any(item.severity in {"warning", "critical"} for item in findings)
        if not findings:
            summary = "Automation completed without reference-side findings."
        elif blocking:
            summary = "Automation completed, but the case requires human review before control-plane closure."
        else:
            summary = "Automation completed and reference checks stayed within tolerance."

        return VerificationReport(
            passed=not blocking,
            summary=summary,
            findings=findings,
            reference_source=source,
        )

    @staticmethod
    def _resolve_status(
        execution_ok: bool,
        parse_ok: bool,
        verification: VerificationReport,
        validation: dict,
    ) -> HarnessRunStatus:
        if not execution_ok or not parse_ok:
            return HarnessRunStatus.FAILED
        if not verification.passed or validation.get("status") == "FAIL":
            return HarnessRunStatus.PENDING_REVIEW
        return HarnessRunStatus.COMPLETED

    def _build_handoff(self, run_record: HarnessRunRecord) -> HandoffPacket:
        risks = [
            item.title for item in run_record.verification.findings if item.severity in {"warning", "critical"}
        ]
        if run_record.executor.is_replay:
            risks.append("run used replay_executor and did not launch a fresh CalculiX solve")
        if not risks:
            risks = ["no blocking risk detected by automation"]

        next_steps = []
        if run_record.status == HarnessRunStatus.PENDING_REVIEW:
            next_steps.append("Review project_state artifacts and decide whether to accept the current benchmark drift.")
        if run_record.status == HarnessRunStatus.FAILED:
            next_steps.append("Inspect executor logs and rerun the case after fixing the blocking issue.")
        if run_record.status == HarnessRunStatus.COMPLETED:
            next_steps.append("Attach the run bundle to the active Notion/GitHub control-plane record.")
        next_steps.append("Use control_plane_sync.json as the deterministic payload for external connectors.")

        return HandoffPacket(
            did_what=(
                f"Ran well-harness for {run_record.case_id}, parsed the FRD result, generated a report, "
                "evaluated it against golden-sample references, and persisted a project_state bundle."
            ),
            did_not_do=(
                "Did not auto-write back to Notion or GitHub because this repository currently generates "
                "connector-ready payloads rather than issuing live API mutations."
            ),
            risks=risks,
            next_steps=next_steps,
            artifact_paths=[item.path for item in run_record.artifacts],
        )

    @staticmethod
    def _iso_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _make_run_id(case_id: str) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        return f"{case_id.lower().replace('-', '_')}_{timestamp}"
