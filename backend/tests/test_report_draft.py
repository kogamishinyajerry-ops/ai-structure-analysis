"""Layer-4 draft generator tests — RFC-001 §3 + ADR-012.

End-to-end stack exercise: CalculiXReader (Layer 1) → von_mises +
displacement-magnitude (Layer 3) → SimulationEvidence + ReportSpec
(Layer 4 schemas from W1's Bucket A).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pytest

from app.adapters.calculix import CalculiXReader
from app.core.types import (
    CanonicalField,
    ComponentType,
    CoordinateSystemKind,
    FieldData,
    FieldLocation,
    FieldMetadata,
    UnitSystem,
)
from app.models import EvidenceType
from app.services.report.draft import generate_static_strength_summary


GS001_FRD = (
    Path(__file__).resolve().parents[2] / "golden_samples" / "GS-001" / "gs001_result.frd"
)


# --- end-to-end with CalculiX adapter --------------------------------------


@pytest.fixture
def gs001_reader() -> CalculiXReader:
    if not GS001_FRD.exists():
        pytest.skip(f"GS-001 .frd missing at {GS001_FRD}")
    return CalculiXReader(GS001_FRD, unit_system=UnitSystem.SI_MM)


def test_summary_returns_report_and_bundle_pair(
    gs001_reader: CalculiXReader,
) -> None:
    report, bundle = generate_static_strength_summary(
        gs001_reader,
        project_id="P-001",
        task_id="GS-001",
        report_id="R-001",
        bundle_id="B-001",
    )
    assert report.report_id == "R-001"
    assert report.project_id == "P-001"
    assert report.evidence_bundle_id == "B-001"
    assert bundle.bundle_id == "B-001"
    assert bundle.task_id == "GS-001"


def test_summary_evidence_bundle_has_disp_and_stress(
    gs001_reader: CalculiXReader,
) -> None:
    _, bundle = generate_static_strength_summary(
        gs001_reader,
        project_id="P", task_id="T", report_id="R", bundle_id="B",
    )
    ids = {item.evidence_id for item in bundle.evidence_items}
    assert "EV-DISP-MAX" in ids
    assert "EV-VM-MAX" in ids
    # Type / data.kind must be consistent (W1 R2 invariant).
    for item in bundle.evidence_items:
        assert item.evidence_type is EvidenceType.SIMULATION
        assert item.data.kind == "simulation"


def test_summary_evidence_unit_pin_matches_reader_unit_system(
    gs001_reader: CalculiXReader,
) -> None:
    """ADR-003: unit-system flows from reader into evidence; never guessed."""
    _, bundle = generate_static_strength_summary(
        gs001_reader,
        project_id="P", task_id="T", report_id="R", bundle_id="B",
    )
    by_id = {item.evidence_id: item for item in bundle.evidence_items}
    # GS-001 was opened with UnitSystem.SI_MM → length=mm, stress=MPa.
    assert by_id["EV-DISP-MAX"].data.unit == "mm"
    assert by_id["EV-VM-MAX"].data.unit == "MPa"


def test_summary_section_references_evidence_ids(
    gs001_reader: CalculiXReader,
) -> None:
    """ADR-012: every claim in the report content references an
    evidence_id that resolves inside the linked bundle."""
    report, bundle = generate_static_strength_summary(
        gs001_reader,
        project_id="P", task_id="T", report_id="R", bundle_id="B",
    )
    assert len(report.sections) == 1
    content = report.sections[0].content or ""
    bundle_ids = {item.evidence_id for item in bundle.evidence_items}
    for ev_id in bundle_ids:
        assert ev_id in content, f"section content must cite {ev_id}"


def test_summary_max_vm_matches_inline_computation(
    gs001_reader: CalculiXReader,
) -> None:
    """Layer-4 derivation must match a fresh inline Layer-3 call —
    proves the stack is consistent (no hidden derivations elsewhere)."""
    from app.domain.stress_derivatives import von_mises

    _, bundle = generate_static_strength_summary(
        gs001_reader,
        project_id="P", task_id="T", report_id="R", bundle_id="B",
    )
    by_id = {item.evidence_id: item for item in bundle.evidence_items}
    reported = by_id["EV-VM-MAX"].data.value

    fd = gs001_reader.get_field(
        CanonicalField.STRESS_TENSOR,
        gs001_reader.solution_states[0].step_id,
    )
    assert fd is not None
    vm = von_mises(fd.values())
    assert reported == pytest.approx(float(vm.max()))


# --- ADR-001 isolation -----------------------------------------------------


def test_draft_module_does_not_import_layer1_adapter_directly() -> None:
    """ADR-001: Layer-4 must not depend on a concrete adapter — only
    on the ReaderHandle Protocol (Layer 2). The CalculiXReader import
    in this test is fine; the production module must NOT import any
    backend.app.adapters.* package.
    """
    import app.services.report.draft as draft_mod
    src = (Path(draft_mod.__file__)).read_text(encoding="utf-8")
    # No literal mention of adapter packages in the production module.
    assert "app.adapters" not in src
    assert "calculix" not in src.lower()


# --- empty / partial reader --------------------------------------------


class _SyntheticEmptyReader:
    """A ReaderHandle whose solution state advertises NO fields."""

    SOLVER_NAME = "synthetic"

    def __init__(self) -> None:
        from app.core.types import SolutionState

        class _M:
            @property
            def node_id_array(self) -> np.ndarray:  # type: ignore[type-arg]
                return np.asarray([], dtype=np.int64)

            @property
            def node_index(self) -> dict[int, int]:
                return {}

            @property
            def coordinates(self) -> np.ndarray:  # type: ignore[type-arg]
                return np.zeros((0, 3))

            @property
            def unit_system(self) -> UnitSystem:
                return UnitSystem.SI_MM

        self._mesh = _M()
        self._states = [
            SolutionState(
                step_id=1, step_name="static",
                time=None, load_factor=None,
                available_fields=(),
            )
        ]

    @property
    def mesh(self) -> object:
        return self._mesh

    @property
    def materials(self) -> dict:  # type: ignore[type-arg]
        return {}

    @property
    def boundary_conditions(self) -> list:  # type: ignore[type-arg]
        return []

    @property
    def solution_states(self) -> list:  # type: ignore[type-arg]
        return self._states

    def get_field(self, name: CanonicalField, step_id: int) -> Optional[FieldData]:
        return None

    def close(self) -> None:
        pass


def test_summary_empty_reader_yields_placeholder_section() -> None:
    """ADR-003: when neither displacement nor stress is available, we
    don't fabricate values — we say so plainly in the section content
    and leave the bundle empty.
    """
    rdr = _SyntheticEmptyReader()
    report, bundle = generate_static_strength_summary(
        rdr,  # type: ignore[arg-type]
        project_id="P", task_id="T", report_id="R", bundle_id="B",
    )
    assert len(bundle.evidence_items) == 0
    assert len(report.sections) == 1
    assert "nothing to summarise" in (report.sections[0].content or "")


def test_summary_no_solution_states_raises() -> None:
    class _NoStepsReader(_SyntheticEmptyReader):
        @property
        def solution_states(self) -> list:  # type: ignore[type-arg, override]
            return []

    with pytest.raises(ValueError, match="no solution states"):
        generate_static_strength_summary(
            _NoStepsReader(),  # type: ignore[arg-type]
            project_id="P", task_id="T", report_id="R", bundle_id="B",
        )


# --- unit-system label policy ---------------------------------------------


def test_unit_label_for_unknown_emits_unknown_literal() -> None:
    """When the wizard hasn't pinned a unit system, the draft surfaces
    'unknown' as the unit string rather than guessing 'MPa' or 'mm'."""
    from app.services.report.draft import _unit_label_for_system

    assert _unit_label_for_system(UnitSystem.UNKNOWN, "stress") == "unknown"
    assert _unit_label_for_system(UnitSystem.UNKNOWN, "length") == "unknown"


def test_unit_label_known_systems() -> None:
    from app.services.report.draft import _unit_label_for_system

    assert _unit_label_for_system(UnitSystem.SI, "length") == "m"
    assert _unit_label_for_system(UnitSystem.SI, "stress") == "Pa"
    assert _unit_label_for_system(UnitSystem.SI_MM, "length") == "mm"
    assert _unit_label_for_system(UnitSystem.SI_MM, "stress") == "MPa"
    assert _unit_label_for_system(UnitSystem.ENGLISH, "length") == "in"
    assert _unit_label_for_system(UnitSystem.ENGLISH, "stress") == "psi"
