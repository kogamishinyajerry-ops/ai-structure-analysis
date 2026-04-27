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


def test_summary_evidence_carries_field_metadata(
    gs001_reader: CalculiXReader,
) -> None:
    """Codex R1 MEDIUM: per-field provenance (FieldMetadata) must reach
    the evidence item — not be reconstructed from reader-level facts."""
    _, bundle = generate_static_strength_summary(
        gs001_reader,
        project_id="P", task_id="T", report_id="R", bundle_id="B",
    )
    by_id = {item.evidence_id: item for item in bundle.evidence_items}
    disp_meta = by_id["EV-DISP-MAX"].field_metadata
    stress_meta = by_id["EV-VM-MAX"].field_metadata
    assert disp_meta is not None
    assert stress_meta is not None
    assert disp_meta.name is CanonicalField.DISPLACEMENT
    assert stress_meta.name is CanonicalField.STRESS_TENSOR
    # source label is now solver name from FieldMetadata, not class name.
    assert by_id["EV-DISP-MAX"].source == disp_meta.source_solver == "calculix"
    assert by_id["EV-VM-MAX"].source == stress_meta.source_solver == "calculix"


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


def test_summary_empty_reader_raises() -> None:
    """ADR-012: a section with no cited evidence_ids cannot ship. When
    neither DISPLACEMENT nor STRESS_TENSOR is available we refuse the
    draft rather than emit an uncited placeholder bullet.
    """
    rdr = _SyntheticEmptyReader()
    with pytest.raises(ValueError, match="zero evidence"):
        generate_static_strength_summary(
            rdr,  # type: ignore[arg-type]
            project_id="P", task_id="T", report_id="R", bundle_id="B",
        )


# --- step_id selection ----------------------------------------------------


class _SyntheticFieldData:
    """Minimal in-memory FieldData (protocol-conformant)."""

    def __init__(
        self, metadata: FieldMetadata, arr: "np.ndarray"  # type: ignore[type-arg]
    ) -> None:
        self.metadata = metadata
        self._arr = arr

    def values(self) -> "np.ndarray":  # type: ignore[type-arg]
        return self._arr

    def at_nodes(self) -> "np.ndarray":  # type: ignore[type-arg]
        return self._arr


class _MultiStateReader:
    """A ReaderHandle with two distinct steps, only one of which has fields.

    Locks down the API: ``step_id=None`` summarises the FINAL state
    (``solution_states[-1]``), and an explicit ``step_id`` selects.
    """

    SOLVER_NAME = "synthetic"

    def __init__(self) -> None:
        from app.core.types import SolutionState

        class _M:
            @property
            def node_id_array(self) -> np.ndarray:  # type: ignore[type-arg]
                return np.asarray([1, 2], dtype=np.int64)

            @property
            def node_index(self) -> dict[int, int]:
                return {1: 0, 2: 1}

            @property
            def coordinates(self) -> np.ndarray:  # type: ignore[type-arg]
                return np.zeros((2, 3))

            @property
            def unit_system(self) -> UnitSystem:
                return UnitSystem.SI_MM

        self._mesh = _M()
        self._states = [
            SolutionState(
                step_id=1, step_name="early",
                time=None, load_factor=None,
                available_fields=(),
            ),
            SolutionState(
                step_id=2, step_name="late",
                time=None, load_factor=None,
                available_fields=(CanonicalField.DISPLACEMENT,),
            ),
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

    def get_field(
        self, name: CanonicalField, step_id: int
    ) -> Optional[FieldData]:
        if step_id == 2 and name is CanonicalField.DISPLACEMENT:
            arr = np.array([[0.1, 0.0, 0.0], [0.5, 0.0, 0.0]], dtype=np.float64)
            meta = FieldMetadata(
                name=CanonicalField.DISPLACEMENT,
                location=FieldLocation.NODE,
                component_type=ComponentType.VECTOR_3D,
                unit_system=UnitSystem.SI_MM,
                source_solver="synthetic",
                source_field_name="DISP",
                source_file=Path("/dev/null"),
                coordinate_system=CoordinateSystemKind.GLOBAL.value,
                was_averaged="unknown",
            )
            return _SyntheticFieldData(meta, arr)
        return None

    def close(self) -> None:
        pass


def test_summary_default_step_is_final_state() -> None:
    """API contract: step_id=None summarises solution_states[-1].
    The early step has no fields; the late step has DISPLACEMENT.
    Default-call must succeed (using the late step), not fail.
    """
    rdr = _MultiStateReader()
    _, bundle = generate_static_strength_summary(
        rdr,  # type: ignore[arg-type]
        project_id="P", task_id="T", report_id="R", bundle_id="B",
    )
    assert {item.evidence_id for item in bundle.evidence_items} == {"EV-DISP-MAX"}


def test_summary_explicit_step_id_selects_state() -> None:
    """Passing step_id=1 (early, empty) must raise; step_id=2 must succeed."""
    rdr = _MultiStateReader()
    with pytest.raises(ValueError, match="zero evidence"):
        generate_static_strength_summary(
            rdr,  # type: ignore[arg-type]
            project_id="P", task_id="T", report_id="R", bundle_id="B",
            step_id=1,
        )
    _, bundle = generate_static_strength_summary(
        rdr,  # type: ignore[arg-type]
        project_id="P", task_id="T", report_id="R", bundle_id="B",
        step_id=2,
    )
    assert len(bundle.evidence_items) == 1


def test_summary_unknown_step_id_raises() -> None:
    rdr = _MultiStateReader()
    with pytest.raises(ValueError, match="not present in reader"):
        generate_static_strength_summary(
            rdr,  # type: ignore[arg-type]
            project_id="P", task_id="T", report_id="R", bundle_id="B",
            step_id=999,
        )


# --- NODE-location guard --------------------------------------------------


class _IPLocationReader(_MultiStateReader):
    """Reader that returns a STRESS_TENSOR field at integration points
    rather than nodes — exercises the Codex R1 MEDIUM guard."""

    def get_field(
        self, name: CanonicalField, step_id: int
    ) -> Optional[FieldData]:
        if step_id == 2 and name is CanonicalField.STRESS_TENSOR:
            arr = np.zeros((4, 6), dtype=np.float64)
            arr[0, 0] = 100.0
            meta = FieldMetadata(
                name=CanonicalField.STRESS_TENSOR,
                location=FieldLocation.INTEGRATION_POINT,
                component_type=ComponentType.TENSOR_SYM_3D,
                unit_system=UnitSystem.SI_MM,
                source_solver="synthetic",
                source_field_name="S_IP",
                source_file=Path("/dev/null"),
                coordinate_system=CoordinateSystemKind.GLOBAL.value,
                was_averaged=False,
            )
            return _SyntheticFieldData(meta, arr)
        return None


def test_summary_refuses_non_node_field() -> None:
    """Layer-2 contract permits IP/centroid fields; the W4-prep draft
    must refuse to mislabel them as node values."""
    rdr = _IPLocationReader()
    with pytest.raises(ValueError, match="NODE-located"):
        generate_static_strength_summary(
            rdr,  # type: ignore[arg-type]
            project_id="P", task_id="T", report_id="R", bundle_id="B",
            step_id=2,
        )


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
