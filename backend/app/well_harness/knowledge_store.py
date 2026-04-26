"""Golden-sample backed knowledge store for well-harness runs.

RFC-001 §6.2 update: ``TaskSpec`` was slimmed to (task_id, name,
result_file, unit_system, citations). The Sprint-2 builder used to pass
description / task_type / priority / material_properties /
acceptance_criteria / tags — those fields no longer exist on TaskSpec
and are dropped here. The well-harness consumer of TaskSpec is itself
Sprint-2 infrastructure; cross-checking will be reworked in W2 once
the CalculiX adapter lands on the Layer-2 ReaderHandle contract.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..models.task_spec import TaskSpec


class GoldenSampleKnowledgeStore:
    """Resolve case metadata, expected values, and input/output paths."""

    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = root or Path(__file__).resolve().parents[3] / "golden_samples"

    def list_case_ids(self) -> List[str]:
        return sorted(
            path.name
            for path in self.root.iterdir()
            if path.is_dir() and path.name.startswith("GS-")
        )

    def case_dir(self, case_id: str) -> Path:
        return self.root / case_id

    def load_expected_results(self, case_id: str) -> Dict[str, Any]:
        path = self.case_dir(case_id) / "expected_results.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def find_input_file(self, case_id: str) -> Optional[Path]:
        matches = sorted(self.case_dir(case_id).glob("*.inp"))
        return matches[0] if matches else None

    def find_result_file(self, case_id: str) -> Path:
        case_dir = self.case_dir(case_id)
        preferred = sorted(case_dir.glob("*_result.frd"))
        if preferred:
            return preferred[0]
        matches = sorted(case_dir.glob("*.frd"))
        if not matches:
            raise FileNotFoundError(f"No FRD result file found for {case_id} in {case_dir}")
        return matches[0]

    def build_task_spec(self, case_id: str) -> TaskSpec:
        expected = self.load_expected_results(case_id)
        try:
            result_file = self.find_result_file(case_id)
        except FileNotFoundError:
            result_file = self.case_dir(case_id)

        citations_raw = expected.get("citations") or expected.get("standards") or []
        if isinstance(citations_raw, dict):
            citations = [str(v) for v in citations_raw.values()]
        elif isinstance(citations_raw, list):
            citations = [str(c) for c in citations_raw]
        else:
            citations = [str(citations_raw)]

        return TaskSpec(
            task_id=case_id,
            name=expected.get("case_name", case_id),
            result_file=str(result_file),
            citations=citations,
        )

    def resolve_reference_stress(self, case_id: str) -> Tuple[Optional[float], Optional[str]]:
        expected = self.load_expected_results(case_id)
        candidates = (
            (
                expected.get("correct_theoretical_calculation", {})
                .get("stress", {})
                .get("result_MPa"),
                "correct_theoretical_calculation.stress.result_MPa",
            ),
            (
                expected.get("theoretical_solutions", {})
                .get("stresses", {})
                .get("all_members", {})
                .get("value"),
                "theoretical_solutions.stresses.all_members.value",
            ),
            (
                expected.get("theoretical_solutions", {})
                .get("max_stress", {})
                .get("value"),
                "theoretical_solutions.max_stress.value",
            ),
        )

        for value, source in candidates:
            if value is None:
                continue
            if isinstance(value, (int, float)):
                return abs(float(value)), source
        return None, None
