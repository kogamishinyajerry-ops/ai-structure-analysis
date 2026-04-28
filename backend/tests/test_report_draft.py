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
    Material,
    UnitSystem,
)
from app.models import EvidenceType
from app.services.report.draft import (
    generate_lifting_lug_summary,
    generate_static_strength_summary,
)


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
    app.adapters.* package.
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


# --- generate_lifting_lug_summary -----------------------------------------


def test_lifting_lug_summary_returns_lifting_lug_template(
    gs001_reader: CalculiXReader,
) -> None:
    report, bundle = generate_lifting_lug_summary(
        gs001_reader,
        project_id="P", task_id="T", report_id="R", bundle_id="B",
    )
    assert report.template_id == "lifting_lug"
    assert bundle.bundle_id == "B"
    assert report.evidence_bundle_id == "B"


def test_lifting_lug_summary_uses_lug_specific_evidence_ids(
    gs001_reader: CalculiXReader,
) -> None:
    """Lifting-lug evidence IDs must NOT collide with the
    equipment-foundation IDs; both reports may live in the same
    bundle workspace, and ID collision would corrupt provenance."""
    _, bundle = generate_lifting_lug_summary(
        gs001_reader,
        project_id="P", task_id="T", report_id="R", bundle_id="B",
    )
    ids = {item.evidence_id for item in bundle.evidence_items}
    assert ids == {"EV-LUG-DISP-MAX", "EV-LUG-VM-MAX"}
    # Equipment-foundation IDs must not appear.
    assert "EV-DISP-MAX" not in ids
    assert "EV-VM-MAX" not in ids


def test_lifting_lug_summary_section_title_is_bilingual_lug() -> None:
    """The section title must match what the LIFTING_LUG template
    requires verbatim (RFC §2.4 rule 2)."""
    # Build a synthetic reader with at least one field so the function
    # produces a section we can inspect.
    class _OneFieldReader(_SyntheticEmptyReader):
        def __init__(self) -> None:
            super().__init__()
            from app.core.types import SolutionState

            self._states = [
                SolutionState(
                    step_id=1, step_name="static",
                    time=None, load_factor=None,
                    available_fields=(CanonicalField.DISPLACEMENT,),
                ),
            ]

        @property
        def mesh(self) -> object:
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

            return _M()

        def get_field(
            self, name: CanonicalField, step_id: int
        ) -> Optional[FieldData]:
            if name is CanonicalField.DISPLACEMENT:
                arr = np.array(
                    [[0.1, 0.0, 0.0], [0.5, 0.0, 0.0]], dtype=np.float64
                )
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

                class _FD:
                    metadata = meta

                    def values(self) -> np.ndarray:  # type: ignore[type-arg]
                        return arr

                    def at_nodes(self) -> np.ndarray:  # type: ignore[type-arg]
                        return arr

                return _FD()
            return None

    report, _ = generate_lifting_lug_summary(
        _OneFieldReader(),  # type: ignore[arg-type]
        project_id="P", task_id="T", report_id="R", bundle_id="B",
    )
    assert len(report.sections) == 1
    assert (
        report.sections[0].title
        == "吊耳强度评估 (Lifting-lug strength assessment)"
    )
    # The bullet label uses the lug-specific phrasing.
    content = report.sections[0].content or ""
    assert "吊装工况下最大位移" in content


def test_lifting_lug_summary_validates_against_lifting_lug_template(
    gs001_reader: CalculiXReader,
) -> None:
    """The lug generator's output must satisfy LIFTING_LUG by
    construction — same producer/template-validator contract that
    generate_static_strength_summary has with EQUIPMENT_FOUNDATION_STATIC."""
    from app.services.report.templates import LIFTING_LUG, validate_report

    report, bundle = generate_lifting_lug_summary(
        gs001_reader,
        project_id="P", task_id="T", report_id="R", bundle_id="B",
    )
    validate_report(report, bundle, template=LIFTING_LUG)


def test_lifting_lug_summary_empty_reader_raises() -> None:
    rdr = _SyntheticEmptyReader()
    with pytest.raises(ValueError, match="zero evidence"):
        generate_lifting_lug_summary(
            rdr,  # type: ignore[arg-type]
            project_id="P", task_id="T", report_id="R", bundle_id="B",
        )


# --- backwards-compat: template_id + title kwargs ------------------------


def test_static_strength_summary_template_id_kwarg_overrides_default(
    gs001_reader: CalculiXReader,
) -> None:
    """Codex R1 MEDIUM regression: the public template_id kwarg must
    still flow through to ReportSpec (this kwarg existed pre-refactor)."""
    report, _ = generate_static_strength_summary(
        gs001_reader,
        project_id="P", task_id="T", report_id="R", bundle_id="B",
        template_id="custom_static_v2",
    )
    assert report.template_id == "custom_static_v2"


def test_static_strength_summary_title_kwarg_overrides_default(
    gs001_reader: CalculiXReader,
) -> None:
    report, _ = generate_static_strength_summary(
        gs001_reader,
        project_id="P", task_id="T", report_id="R", bundle_id="B",
        title="Project-X equipment foundation report",
    )
    assert report.title == "Project-X equipment foundation report"


def test_static_strength_summary_default_kwargs_unchanged(
    gs001_reader: CalculiXReader,
) -> None:
    """Without overrides, the equipment-foundation defaults still apply."""
    report, _ = generate_static_strength_summary(
        gs001_reader,
        project_id="P", task_id="T", report_id="R", bundle_id="B",
    )
    assert report.template_id == "equipment_foundation_static"
    assert report.title == "Static-strength summary"


def test_lifting_lug_summary_template_id_kwarg_overrides_default(
    gs001_reader: CalculiXReader,
) -> None:
    """Symmetry: the lug producer accepts the same overrides."""
    report, _ = generate_lifting_lug_summary(
        gs001_reader,
        project_id="P", task_id="T", report_id="R", bundle_id="B",
        template_id="custom_lug_v2",
        title="Custom lug title",
    )
    assert report.template_id == "custom_lug_v2"
    assert report.title == "Custom lug title"


# ---------------------------------------------------------------------------
# W6c.2 — § 许用应力 + § 评定结论 wiring
# ---------------------------------------------------------------------------
#
# The W6c.2 contract: when ``material + code`` are both supplied to a
# generator, the resulting draft additionally renders an allowable-stress
# section and a verdict section, backed by ``EV-ALLOWABLE-001`` +
# ``EV-VERDICT-001`` analytical evidence with an honest derivation DAG
# pointing back to the σ_max simulation evidence.
#
# Inputs picked to make the math obvious:
#   Q345B at room T → simplified [σ] = min(345/1.5, 470/3.0)
#                                    = min(230.0, 156.67) = 156.67 MPa
#   σ_max = 50 MPa  → SF = 156.67 / 50 ≈ 3.13  (PASS at threshold=1.0)
#   σ_max = 200 MPa → SF = 156.67 / 200 ≈ 0.78 (FAIL at threshold=1.0)


_Q345B = None  # populated below to avoid hitting the file system at import time


def _make_q345b():
    """Return a fresh Material(Q345B) — same numbers as the built-in JSON."""
    return Material(
        name="Q345B",
        youngs_modulus=206_000.0,
        poissons_ratio=0.30,
        density=7.85e-9,
        yield_strength=345.0,
        ultimate_strength=470.0,
        code_standard="GB",
        code_grade="Q345B",
        source_citation="GB/T 1591-2018 §6.2 Table 7",
        unit_system=UnitSystem.SI_MM,
        is_user_supplied=False,
    )


def _make_synthetic_stress_reader(
    sigma_max_mpa: float,
) -> "_SyntheticStressReader":
    return _SyntheticStressReader(sigma_max_mpa)


class _SyntheticStressReader:
    """ReaderHandle exposing one node + STRESS_TENSOR with peak σ_vm =
    ``sigma_max_mpa`` MPa. Bypasses CalculiX so the wedge tests run
    even when the GS-001 .frd is unavailable."""

    SOLVER_NAME = "synthetic"

    def __init__(self, sigma_max_mpa: float) -> None:
        from app.core.types import SolutionState

        self._sigma_max_mpa = sigma_max_mpa

        class _M:
            @property
            def node_id_array(self_inner) -> np.ndarray:  # type: ignore[type-arg]
                return np.asarray([42], dtype=np.int64)

            @property
            def node_index(self_inner) -> dict[int, int]:
                return {42: 0}

            @property
            def coordinates(self_inner) -> np.ndarray:  # type: ignore[type-arg]
                return np.zeros((1, 3))

            @property
            def unit_system(self_inner) -> UnitSystem:
                return UnitSystem.SI_MM

        self._mesh = _M()
        self._states = [
            SolutionState(
                step_id=1, step_name="static",
                time=None, load_factor=None,
                available_fields=(CanonicalField.STRESS_TENSOR,),
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

    def get_field(
        self, name: CanonicalField, step_id: int
    ) -> Optional[FieldData]:
        if step_id == 1 and name is CanonicalField.STRESS_TENSOR:
            # Uniaxial tension: σ_xx = σ_max → von Mises = σ_max.
            arr = np.zeros((1, 6), dtype=np.float64)
            arr[0, 0] = self._sigma_max_mpa
            meta = FieldMetadata(
                name=CanonicalField.STRESS_TENSOR,
                location=FieldLocation.NODE,
                component_type=ComponentType.TENSOR_SYM_3D,
                unit_system=UnitSystem.SI_MM,
                source_solver="synthetic",
                source_field_name="S",
                source_file=Path("/dev/null"),
                coordinate_system=CoordinateSystemKind.GLOBAL.value,
                was_averaged="unknown",
            )
            return _SyntheticFieldData(meta, arr)
        return None

    def close(self) -> None:
        pass


def test_w6c2_with_material_pass_appends_two_sections() -> None:
    """σ_max=50 MPa, Q345B GB → SF≈3.13 ≥ 1.0 → PASS. Report grows
    from 1 section (max-field summary) to 3 sections (+ § 许用应力 +
    § 评定结论)."""
    rdr = _make_synthetic_stress_reader(50.0)
    report, bundle = generate_static_strength_summary(
        rdr,  # type: ignore[arg-type]
        project_id="P", task_id="T", report_id="R", bundle_id="B",
        material=_make_q345b(),
        code="GB",
    )

    assert len(report.sections) == 3
    titles = [s.title for s in report.sections]
    assert "许用应力 (Allowable stress)" in titles
    assert "评定结论 (Strength verdict)" in titles

    ids = {item.evidence_id for item in bundle.evidence_items}
    assert {"EV-VM-MAX", "EV-ALLOWABLE-001", "EV-VERDICT-001"} <= ids

    by_id = {item.evidence_id: item for item in bundle.evidence_items}
    verdict_ev = by_id["EV-VERDICT-001"]
    assert verdict_ev.evidence_type is EvidenceType.ANALYTICAL
    assert verdict_ev.data.kind == "analytical"
    # SF = 156.67 / 50 ≈ 3.133
    assert verdict_ev.data.value == pytest.approx(156.6667 / 50.0, rel=1e-4)


def test_w6c2_verdict_section_says_pass_when_sf_above_threshold() -> None:
    rdr = _make_synthetic_stress_reader(50.0)
    report, _ = generate_static_strength_summary(
        rdr,  # type: ignore[arg-type]
        project_id="P", task_id="T", report_id="R", bundle_id="B",
        material=_make_q345b(),
        code="GB",
    )
    verdict_section = next(
        s for s in report.sections if s.title.startswith("评定结论")
    )
    assert "PASS" in verdict_section.content
    assert "强度满足要求" in verdict_section.content
    assert "EV-VERDICT-001" in verdict_section.content


def test_w6c2_verdict_section_says_fail_when_sf_below_threshold() -> None:
    """σ_max=200 MPa > [σ]=156.67 MPa → SF≈0.78 < 1.0 → FAIL."""
    rdr = _make_synthetic_stress_reader(200.0)
    report, bundle = generate_static_strength_summary(
        rdr,  # type: ignore[arg-type]
        project_id="P", task_id="T", report_id="R", bundle_id="B",
        material=_make_q345b(),
        code="GB",
    )
    verdict_section = next(
        s for s in report.sections if s.title.startswith("评定结论")
    )
    assert "FAIL" in verdict_section.content
    assert "强度不满足要求" in verdict_section.content
    by_id = {item.evidence_id: item for item in bundle.evidence_items}
    assert by_id["EV-VERDICT-001"].data.value < 1.0


def test_w6c2_threshold_flips_marginal_design_to_fail() -> None:
    """σ_max=120 → SF ≈ 1.305. PASS at threshold=1.0, FAIL at 1.5
    (institute-internal margin). Same FE result, same material — only
    the threshold flips the verdict."""
    rdr = _make_synthetic_stress_reader(120.0)
    _, bundle_default = generate_static_strength_summary(
        rdr,  # type: ignore[arg-type]
        project_id="P", task_id="T", report_id="R1", bundle_id="B1",
        material=_make_q345b(),
        code="GB",
    )
    rdr2 = _make_synthetic_stress_reader(120.0)
    _, bundle_strict = generate_static_strength_summary(
        rdr2,  # type: ignore[arg-type]
        project_id="P", task_id="T", report_id="R2", bundle_id="B2",
        material=_make_q345b(),
        code="GB",
        threshold=1.5,
    )
    by_id_default = {it.evidence_id: it for it in bundle_default.evidence_items}
    by_id_strict = {it.evidence_id: it for it in bundle_strict.evidence_items}
    # Same SF in both bundles — only the threshold (and thus the kind)
    # differs. The kind is in the description string.
    assert by_id_default["EV-VERDICT-001"].data.value == pytest.approx(
        by_id_strict["EV-VERDICT-001"].data.value, rel=1e-9
    )
    assert "PASS" in by_id_default["EV-VERDICT-001"].description
    assert "FAIL" in by_id_strict["EV-VERDICT-001"].description


def test_w6c2_verdict_derivation_lists_sigma_max_and_allowable() -> None:
    """ADR-012 honest DAG: EV-VERDICT-001 must list BOTH the simulation
    σ_max evidence AND EV-ALLOWABLE-001 in its derivation. Without
    this link, an auditor can't trace the SF back to the two numbers
    it came from."""
    rdr = _make_synthetic_stress_reader(50.0)
    _, bundle = generate_static_strength_summary(
        rdr,  # type: ignore[arg-type]
        project_id="P", task_id="T", report_id="R", bundle_id="B",
        material=_make_q345b(),
        code="GB",
    )
    by_id = {item.evidence_id: item for item in bundle.evidence_items}
    derivation = by_id["EV-VERDICT-001"].derivation or []
    assert "EV-VM-MAX" in derivation
    assert "EV-ALLOWABLE-001" in derivation
    # Allowable stands alone (it depends on the Material data, not on
    # any other evidence in this bundle).
    assert by_id["EV-ALLOWABLE-001"].derivation in (None, [])


def test_w6c2_no_material_falls_through_to_old_behavior() -> None:
    """Backwards compat: omitting material+code yields the same
    1-section summary the W4 path always produced — no extra evidence,
    no extra sections."""
    rdr = _make_synthetic_stress_reader(50.0)
    report, bundle = generate_static_strength_summary(
        rdr,  # type: ignore[arg-type]
        project_id="P", task_id="T", report_id="R", bundle_id="B",
    )
    assert len(report.sections) == 1
    ids = {item.evidence_id for item in bundle.evidence_items}
    assert "EV-ALLOWABLE-001" not in ids
    assert "EV-VERDICT-001" not in ids


def test_w6c2_material_without_stress_field_raises() -> None:
    """W6c.2 verdict needs σ_max. If material+code are passed but the
    chosen state has no STRESS_TENSOR, refuse loudly rather than emit
    a verdict section with no σ_max number behind it."""

    class _DispOnlyReader(_SyntheticStressReader):
        def get_field(
            self, name: CanonicalField, step_id: int
        ) -> Optional[FieldData]:
            if step_id == 1 and name is CanonicalField.DISPLACEMENT:
                arr = np.array([[0.5, 0.0, 0.0]], dtype=np.float64)
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

    rdr = _DispOnlyReader(50.0)
    with pytest.raises(ValueError, match="W6c.2 verdict requires"):
        generate_static_strength_summary(
            rdr,  # type: ignore[arg-type]
            project_id="P", task_id="T", report_id="R", bundle_id="B",
            material=_make_q345b(),
            code="GB",
        )


def test_w6c2_cross_standard_request_propagates() -> None:
    """A Q345B (GB) Material against ``code='ASME'`` must surface the
    AllowableStressError from the W6b layer — the draft generator
    does not auto-cross-reference standards (per ADR-020 §1)."""
    from app.services.report.allowable_stress import AllowableStressError

    rdr = _make_synthetic_stress_reader(50.0)
    with pytest.raises(AllowableStressError, match="cross-standard"):
        generate_static_strength_summary(
            rdr,  # type: ignore[arg-type]
            project_id="P", task_id="T", report_id="R", bundle_id="B",
            material=_make_q345b(),
            code="ASME",
        )


def test_w6c2_lifting_lug_accepts_same_kwargs() -> None:
    """Symmetry: the lug producer also accepts material+code+threshold."""
    rdr = _make_synthetic_stress_reader(50.0)
    report, bundle = generate_lifting_lug_summary(
        rdr,  # type: ignore[arg-type]
        project_id="P", task_id="T", report_id="R", bundle_id="B",
        material=_make_q345b(),
        code="GB",
    )
    assert report.template_id == "lifting_lug"
    assert len(report.sections) == 3
    ids = {item.evidence_id for item in bundle.evidence_items}
    # The lug uses LUG-prefixed simulation evidence_ids, but the
    # allowable / verdict IDs are stable across templates.
    assert "EV-LUG-VM-MAX" in ids
    assert "EV-ALLOWABLE-001" in ids
    assert "EV-VERDICT-001" in ids
    by_id = {item.evidence_id: item for item in bundle.evidence_items}
    derivation = by_id["EV-VERDICT-001"].derivation or []
    # Lug verdict derivation must reference the LUG-prefixed σ_max ID.
    assert "EV-LUG-VM-MAX" in derivation


def test_w6c2_material_without_code_raises() -> None:
    """Codex R1 MEDIUM (PR #100): partial-kwargs must hard-fail. A
    caller passing only ``material`` is a configuration bug — silently
    falling through to the legacy 1-section summary would hide it.
    """
    rdr = _make_synthetic_stress_reader(50.0)
    with pytest.raises(ValueError, match="requires BOTH material\\+code"):
        generate_static_strength_summary(
            rdr,  # type: ignore[arg-type]
            project_id="P", task_id="T", report_id="R", bundle_id="B",
            material=_make_q345b(),
            # no code
        )


def test_w6c2_code_without_material_raises() -> None:
    """Codex R1 MEDIUM (PR #100), symmetric: caller passing only
    ``code`` is also a bug; the verdict needs σ_y/σ_u from material."""
    rdr = _make_synthetic_stress_reader(50.0)
    with pytest.raises(ValueError, match="requires BOTH material\\+code"):
        generate_static_strength_summary(
            rdr,  # type: ignore[arg-type]
            project_id="P", task_id="T", report_id="R", bundle_id="B",
            code="GB",
            # no material
        )


def test_w6c2_lifting_lug_partial_kwargs_also_raises() -> None:
    """The XOR guard must apply to both producers — otherwise an
    engineer using the lug template could slip the same bug past it."""
    rdr = _make_synthetic_stress_reader(50.0)
    with pytest.raises(ValueError, match="requires BOTH material\\+code"):
        generate_lifting_lug_summary(
            rdr,  # type: ignore[arg-type]
            project_id="P", task_id="T", report_id="R", bundle_id="B",
            material=_make_q345b(),
        )
    rdr2 = _make_synthetic_stress_reader(50.0)
    with pytest.raises(ValueError, match="requires BOTH material\\+code"):
        generate_lifting_lug_summary(
            rdr2,  # type: ignore[arg-type]
            project_id="P", task_id="T", report_id="R", bundle_id="B",
            code="GB",
        )


def test_w6c2_verdict_relation_truthful_when_threshold_above_floor_and_fail() -> None:
    """With threshold=1.5 and σ_max=140 MPa < [σ]=156.67 MPa, the SF
    is 1.119 — FAIL against the institute-internal margin, but σ_max
    is genuinely BELOW [σ]. Hard-coding ``>`` for the σ-relation on
    FAIL would print the audit-line as ``σ_max > [σ]`` — factually
    wrong and exactly the silent untruth ADR-012 forbids in
    audit-trail content."""
    rdr = _make_synthetic_stress_reader(140.0)
    report, _ = generate_static_strength_summary(
        rdr,  # type: ignore[arg-type]
        project_id="P", task_id="T", report_id="R", bundle_id="B",
        material=_make_q345b(),
        code="GB",
        threshold=1.5,
    )
    verdict_section = next(
        s for s in report.sections if s.title.startswith("评定结论")
    )
    # Verdict is FAIL (SF=1.119 < threshold=1.5)…
    assert "FAIL" in verdict_section.content
    # …but σ_max=140 IS less than [σ]=156.67 — the rendered inequality
    # must be ``<`` (or ``≤`` / ``=`` for boundary), NEVER ``>``.
    assert "140" in verdict_section.content
    # Find the σ_max-vs-[σ] clause and assert its relation is honest.
    # The line shape is "σ_max = 140 ... < [σ] = 156.667 ...".
    assert "σ_max = 140 MPa < [σ]" in verdict_section.content


def test_w6c2_format_inputs_substitution_respects_word_boundaries() -> None:
    """A future YAML formula could reference both ``sigma_y`` and
    ``sigma_yield`` (or ``sigma_u`` and ``sigma_ut``). The naive
    ``str.replace`` strategy would corrupt the longer token by
    consuming the shorter one as a substring; the word-boundary
    regex must isolate each whole-word symbol.

    This is the bug Codex was specifically pointed at on PR #100 R1
    review focus #6 — fixing it pre-emptively here closes the audit
    hole before any future formula trips it.
    """
    from app.services.report.draft import _format_inputs_substitution

    # Today's formulas only have sigma_y / sigma_u — sanity check first.
    assert _format_inputs_substitution(
        "min(sigma_y / 1.5, sigma_u / 3.0)",
        {"sigma_y": 345.0, "sigma_u": 470.0},
    ) == "min(345 / 1.5, 470 / 3.0)"

    # Tomorrow's formula: sigma_y AND sigma_yield in the same expression.
    # If we mis-replaced sigma_y first, sigma_yield would become
    # "345ield" — a clear corruption of the audit line. The regex
    # boundaries must keep them distinct.
    rendered = _format_inputs_substitution(
        "min(sigma_y / 1.5, sigma_yield / 2.0)",
        {"sigma_y": 345.0, "sigma_yield": 400.0},
    )
    assert "345" in rendered
    assert "400" in rendered
    assert "ield" not in rendered  # no truncated token surviving
    assert rendered == "min(345 / 1.5, 400 / 2.0)"

    # Symbol present in the formula but absent from inputs is left alone
    # (a future formula extension might reference a new symbol the data
    # layer hasn't started supplying yet — better to leave it visible
    # than silently disappear it).
    rendered = _format_inputs_substitution(
        "min(sigma_y / 1.5, sigma_u / 3.0, E_j)",
        {"sigma_y": 345.0, "sigma_u": 470.0},
    )
    assert "E_j" in rendered  # untouched
    assert "345" in rendered
    assert "470" in rendered


# ---------------------------------------------------------------------------
# W6d.2 — § 边界条件 wiring
# ---------------------------------------------------------------------------


def _write_bc_yaml(tmp_path: Path, body: str) -> Path:
    from textwrap import dedent

    p = tmp_path / "bc.yaml"
    p.write_text(dedent(body), encoding="utf-8")
    return p


def test_w6d2_bc_yaml_appends_section_and_evidence(
    gs001_reader: CalculiXReader, tmp_path: Path
) -> None:
    """When ``bc_yaml_path`` is provided, the draft grows by one
    level-1 section (§ 边界条件) and the bundle gains exactly one
    new ``EV-BC-001`` ReferenceEvidence pointing at the source file.
    """
    p = _write_bc_yaml(
        tmp_path,
        """
        boundary_conditions:
          - name: fixed_bottom
            kind: fixed
            target: NSET=bottom
            components: {ux: 0.0, uy: 0.0, uz: 0.0}
            unit_system: SI_mm
          - name: top_pressure
            kind: pressure
            target: ELSET=top_face
            components: {pressure: 5.0}
            unit_system: SI_mm
        """,
    )
    report, bundle = generate_static_strength_summary(
        gs001_reader,
        project_id="P", task_id="T", report_id="R", bundle_id="B",
        bc_yaml_path=p,
    )

    titles = [s.title for s in report.sections]
    assert "边界条件 (Boundary conditions)" in titles

    ids = {item.evidence_id for item in bundle.evidence_items}
    assert "EV-BC-001" in ids

    by_id = {item.evidence_id: item for item in bundle.evidence_items}
    bc_ev = by_id["EV-BC-001"]
    assert bc_ev.evidence_type is EvidenceType.REFERENCE
    assert bc_ev.data.kind == "reference"
    # value = number of BCs (2), unit = "conditions"
    assert bc_ev.data.value == 2.0
    assert bc_ev.data.unit == "conditions"
    assert bc_ev.data.source_document == str(p)


def test_w6d2_bc_section_lists_each_bc_in_source_order(
    gs001_reader: CalculiXReader, tmp_path: Path
) -> None:
    """The section content lists each BC in source order — engineers
    cross-reference the rendered DOCX back to their bc.yaml by index."""
    p = _write_bc_yaml(
        tmp_path,
        """
        boundary_conditions:
          - name: alpha
            kind: fixed
            target: NSET=a
            components: {ux: 0.0}
            unit_system: SI_mm
          - name: beta
            kind: force
            target: NSET=b
            components: {fx: 100.0}
            unit_system: SI_mm
          - name: gamma
            kind: pressure
            target: ELSET=g
            components: {pressure: 2.5}
            unit_system: SI_mm
        """,
    )
    report, _ = generate_static_strength_summary(
        gs001_reader,
        project_id="P", task_id="T", report_id="R", bundle_id="B",
        bc_yaml_path=p,
    )
    bc_section = next(
        s for s in report.sections if s.title.startswith("边界条件")
    )
    # Each BC name must appear once and in source order.
    pos_alpha = bc_section.content.find("alpha")
    pos_beta = bc_section.content.find("beta")
    pos_gamma = bc_section.content.find("gamma")
    assert pos_alpha != -1 and pos_beta != -1 and pos_gamma != -1
    assert pos_alpha < pos_beta < pos_gamma
    # The summary line shows total + grouping
    assert "共 **3** 项" in bc_section.content
    # The citation appears inside the section
    assert "EV-BC-001" in bc_section.content


def test_w6d2_no_bc_yaml_leaves_sections_unchanged(
    gs001_reader: CalculiXReader,
) -> None:
    """Backwards-compat: when ``bc_yaml_path`` is not provided, the
    report shape matches the old W4 path exactly. No § 边界条件
    section, no EV-BC-001."""
    report, bundle = generate_static_strength_summary(
        gs001_reader,
        project_id="P", task_id="T", report_id="R", bundle_id="B",
    )
    titles = [s.title for s in report.sections]
    assert not any(t.startswith("边界条件") for t in titles)
    ids = {item.evidence_id for item in bundle.evidence_items}
    assert "EV-BC-001" not in ids


def test_w6d2_empty_bc_yaml_emits_placeholder_with_evidence(
    gs001_reader: CalculiXReader, tmp_path: Path
) -> None:
    """Empty bc.yaml = engineer touched the file but had nothing to
    list. The renderer must emit a [需工程师确认] placeholder section
    *with* citation back to the source — distinguishes "uploaded
    empty" from "did not upload" in the audit trail."""
    p = tmp_path / "bc.yaml"
    p.write_text("", encoding="utf-8")  # empty file → 0 BCs
    report, bundle = generate_static_strength_summary(
        gs001_reader,
        project_id="P", task_id="T", report_id="R", bundle_id="B",
        bc_yaml_path=p,
    )
    bc_section = next(
        s for s in report.sections if s.title.startswith("边界条件")
    )
    assert "需工程师确认" in bc_section.content
    assert "EV-BC-001" in bc_section.content

    by_id = {item.evidence_id: item for item in bundle.evidence_items}
    assert by_id["EV-BC-001"].data.value == 0.0


def test_w6d2_mixed_unit_systems_warns_in_section(
    gs001_reader: CalculiXReader, tmp_path: Path
) -> None:
    """Mixed unit systems is almost always a wizard bug; surfacing
    the warning at sign time is cheaper than catching it at audit."""
    p = _write_bc_yaml(
        tmp_path,
        """
        boundary_conditions:
          - name: a
            kind: fixed
            target: NSET=a
            components: {ux: 0.0}
            unit_system: SI_mm
          - name: b
            kind: pressure
            target: ELSET=b
            components: {pressure: 1.0}
            unit_system: SI
        """,
    )
    report, _ = generate_static_strength_summary(
        gs001_reader,
        project_id="P", task_id="T", report_id="R", bundle_id="B",
        bc_yaml_path=p,
    )
    bc_section = next(
        s for s in report.sections if s.title.startswith("边界条件")
    )
    assert "混合单位系统" in bc_section.content
    assert "SI_mm" in bc_section.content and "SI" in bc_section.content


def test_w6d2_malformed_bc_yaml_propagates(
    gs001_reader: CalculiXReader, tmp_path: Path
) -> None:
    """``BCSummaryError`` from the loader must propagate cleanly so
    the engineer sees the error at draft time, not at DOCX render."""
    from app.services.report.boundary_summary import BCSummaryError

    p = _write_bc_yaml(
        tmp_path,
        """
        boundary_conditions:
          - name: bad
            kind: fixed
            target: NSET=x
            components: {fx: .nan}
            unit_system: SI_mm
        """,
    )
    with pytest.raises(BCSummaryError, match="must be finite"):
        generate_static_strength_summary(
            gs001_reader,
            project_id="P", task_id="T", report_id="R", bundle_id="B",
            bc_yaml_path=p,
        )


def test_w6d2_lifting_lug_accepts_bc_yaml(
    gs001_reader: CalculiXReader, tmp_path: Path
) -> None:
    """Symmetric: the lug producer also forwards ``bc_yaml_path`` so
    a lifting-lug DOCX can carry § 边界条件."""
    p = _write_bc_yaml(
        tmp_path,
        """
        boundary_conditions:
          - name: lug_pin
            kind: fixed
            target: NSET=lug_hole
            components: {ux: 0.0, uy: 0.0, uz: 0.0}
            unit_system: SI_mm
        """,
    )
    report, bundle = generate_lifting_lug_summary(
        gs001_reader,
        project_id="P", task_id="T", report_id="R", bundle_id="B",
        bc_yaml_path=p,
    )
    titles = [s.title for s in report.sections]
    assert "边界条件 (Boundary conditions)" in titles
    ids = {item.evidence_id for item in bundle.evidence_items}
    assert "EV-BC-001" in ids


def test_w6d2_bc_section_coexists_with_w6c2_verdict_sections(
    gs001_reader: CalculiXReader, tmp_path: Path
) -> None:
    """Stacking the two W6 wedges: verdict + BC sections appear
    alongside the max-field summary. Total = 4 sections (max-field +
    许用应力 + 评定结论 + 边界条件)."""
    p = _write_bc_yaml(
        tmp_path,
        """
        boundary_conditions:
          - name: fixed_bottom
            kind: fixed
            target: NSET=bottom
            components: {ux: 0.0}
            unit_system: SI_mm
        """,
    )
    report, bundle = generate_static_strength_summary(
        gs001_reader,
        project_id="P", task_id="T", report_id="R", bundle_id="B",
        material=_make_q345b(),
        code="GB",
        bc_yaml_path=p,
    )
    # Codex R1 PR #102 MEDIUM: pin the exact ordered sequence + level
    # contract, not just membership. Order matters because the DOCX
    # renderer iterates sections sequentially; level matters because
    # 许用应力 / 评定结论 are sub-sections of the max-field summary
    # while 边界条件 is its own top-level chapter.
    sequence = [(s.title, s.level) for s in report.sections]
    assert sequence == [
        ("结构强度摘要 (Static-strength summary)", 1),
        ("许用应力 (Allowable stress)", 2),
        ("评定结论 (Strength verdict)", 2),
        ("边界条件 (Boundary conditions)", 1),
    ]

    ids = {item.evidence_id for item in bundle.evidence_items}
    assert {"EV-VM-MAX", "EV-ALLOWABLE-001", "EV-VERDICT-001", "EV-BC-001"} <= ids


def test_w6c2_allowable_section_shows_substituted_formula() -> None:
    """The substitution line must show the actual σ_y / σ_u numbers,
    not the symbolic placeholders. ADR-020 §5: engineers cross-check
    [σ] back to source by reading the substituted line."""
    rdr = _make_synthetic_stress_reader(50.0)
    report, _ = generate_static_strength_summary(
        rdr,  # type: ignore[arg-type]
        project_id="P", task_id="T", report_id="R", bundle_id="B",
        material=_make_q345b(),
        code="GB",
    )
    allowable_section = next(
        s for s in report.sections if s.title.startswith("许用应力")
    )
    # Q345B σ_y=345, σ_u=470 — both must appear verbatim.
    assert "345" in allowable_section.content
    assert "470" in allowable_section.content
    # And the resolved [σ] (156.67) must appear.
    assert "156.667" in allowable_section.content or "156.67" in allowable_section.content
    # And the clause citation.
    assert "GB 150.3-2011" in allowable_section.content
    assert "EV-ALLOWABLE-001" in allowable_section.content
