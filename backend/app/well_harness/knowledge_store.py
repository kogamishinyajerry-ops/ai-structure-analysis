"""Golden-sample backed knowledge store for well-harness runs."""

from __future__ import annotations

import json
from json import dumps
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..models.task_spec import Priority, TaskSpec, TaskType


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
        geometry_file = self.find_input_file(case_id)
        analysis_type = str(expected.get("analysis_type", "")).lower()
        description = expected.get("case_description")
        if not isinstance(description, str):
            description = dumps(description, ensure_ascii=False)

        material_properties = (
            expected.get("material_params")
            or expected.get("structure_params")
            or expected.get("metadata")
            or {}
        )
        acceptance = expected.get("acceptance_criteria", [])
        if isinstance(acceptance, dict):
            acceptance = [
                f"{key}: {value.get('criteria', value)}"
                if isinstance(value, dict)
                else f"{key}: {value}"
                for key, value in acceptance.items()
            ]
        elif not isinstance(acceptance, list):
            acceptance = [str(acceptance)]

        return TaskSpec(
            task_id=case_id,
            name=expected.get("case_name", case_id),
            description=description,
            task_type=self._map_task_type(analysis_type),
            priority=Priority.HIGH,
            geometry_file=str(geometry_file) if geometry_file else str(self.case_dir(case_id)),
            material_properties=material_properties,
            acceptance_criteria=acceptance,
            tags=[case_id, "well-harness", "golden-sample"],
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

    @staticmethod
    def _map_task_type(analysis_type: str) -> TaskType:
        if "modal" in analysis_type or "frequency" in analysis_type:
            return TaskType.MODAL_ANALYSIS
        if "thermal" in analysis_type:
            return TaskType.THERMAL_ANALYSIS
        if "buckling" in analysis_type:
            return TaskType.BUCKLING_ANALYSIS
        if "dynamic" in analysis_type:
            return TaskType.DYNAMIC_ANALYSIS
        return TaskType.STATIC_ANALYSIS
