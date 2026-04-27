"""Layer-4 pressure_vessel_local_stress producer tests — RFC-001 §3
+ ASME VIII Div 2 §5.5.

Exercises the third L1→L4 producer end-to-end: a synthetic ReaderHandle
exposes a STRESS_TENSOR field at known SCL nodes, the producer
linearizes the through-thickness field, and we verify P_m / P_m+P_b /
P+Q correspond to the documented categorised stresses.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import numpy as np
import pytest

from app.core.types import (
    CanonicalField,
    ComponentType,
    CoordinateSystemKind,
    FieldData,
    FieldLocation,
    FieldMetadata,
    SolutionState,
    UnitSystem,
)
from app.models import EvidenceBundle, EvidenceType, ReportSpec
from app.services.report.draft import (
    generate_pressure_vessel_local_stress_summary,
)
from app.services.report.templates import (
    PRESSURE_VESSEL_LOCAL_STRESS,
    validate_report,
)


# --- synthetic reader scaffolding ----------------------------------------


class _SCLReader:
    """A ReaderHandle that exposes a configurable per-node stress
    tensor field. Built so each test can plant the exact tensors at
    chosen node IDs and assert the produced categorised stresses.
    """

    SOLVER_NAME = "synthetic"

    def __init__(
        self,
        *,
        node_ids: "np.ndarray[Any, Any]",
        tensors: "np.ndarray[Any, Any]",
    ) -> None:
        assert tensors.shape == (node_ids.size, 6)
        self._node_ids = node_ids
        self._tensors = tensors

        node_ids_local = node_ids
        tensors_local = tensors

        class _M:
            @property
            def node_id_array(self) -> np.ndarray:  # type: ignore[type-arg]
                return node_ids_local

            @property
            def node_index(self) -> dict[int, int]:
                return {int(nid): i for i, nid in enumerate(node_ids_local)}

            @property
            def coordinates(self) -> np.ndarray:  # type: ignore[type-arg]
                return np.zeros((node_ids_local.size, 3))

            @property
            def unit_system(self) -> UnitSystem:
                return UnitSystem.SI_MM

        self._mesh = _M()
        self._states = [
            SolutionState(
                step_id=1, step_name="static",
                time=None, load_factor=None,
                available_fields=(CanonicalField.STRESS_TENSOR,),
            )
        ]

        meta = FieldMetadata(
            name=CanonicalField.STRESS_TENSOR,
            location=FieldLocation.NODE,
            component_type=ComponentType.TENSOR_SYM_3D,
            unit_system=UnitSystem.SI_MM,
            source_solver="synthetic",
            source_field_name="STRESS",
            source_file=Path("/dev/null"),
            coordinate_system=CoordinateSystemKind.GLOBAL.value,
            was_averaged=False,
        )
        meta_local = meta
        tensors_for_fd = tensors_local

        class _FD:
            metadata = meta_local

            def values(self) -> np.ndarray:  # type: ignore[type-arg]
                return tensors_for_fd

            def at_nodes(self) -> np.ndarray:  # type: ignore[type-arg]
                return tensors_for_fd

        self._fd = _FD()

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
        if name is CanonicalField.STRESS_TENSOR and step_id == 1:
            return self._fd
        return None

    def close(self) -> None:
        pass


def _make_reader_with_uniaxial_membrane(value: float = 100.0) -> _SCLReader:
    """5-node SCL where σ_xx = const along the wall — pure membrane."""
    node_ids = np.array([10, 20, 30, 40, 50], dtype=np.int64)
    tensors = np.zeros((5, 6), dtype=np.float64)
    tensors[:, 0] = value
    return _SCLReader(node_ids=node_ids, tensors=tensors)


def _make_reader_with_uniaxial_bending(slope: float = 50.0) -> _SCLReader:
    """5-node SCL where σ_xx is linear from -slope at inner to +slope
    at outer (pure bending, midplane-antisymmetric)."""
    node_ids = np.array([10, 20, 30, 40, 50], dtype=np.int64)
    tensors = np.zeros((5, 6), dtype=np.float64)
    # 5 nodes uniformly spaced: indices 0..4, midplane at 2.
    tensors[:, 0] = np.array(
        [-slope, -slope / 2, 0.0, slope / 2, slope], dtype=np.float64
    )
    return _SCLReader(node_ids=node_ids, tensors=tensors)


# --- output structure ------------------------------------------------------


def test_returns_report_and_bundle_with_correct_template() -> None:
    rdr = _make_reader_with_uniaxial_membrane()
    report, bundle = generate_pressure_vessel_local_stress_summary(
        rdr,  # type: ignore[arg-type]
        project_id="P", task_id="T", report_id="R", bundle_id="B",
        scl_node_ids=[10, 20, 30, 40, 50],
        scl_distances=[0.0, 0.5, 1.0, 1.5, 2.0],
    )
    assert isinstance(report, ReportSpec)
    assert isinstance(bundle, EvidenceBundle)
    assert report.template_id == "pressure_vessel_local_stress"
    assert report.evidence_bundle_id == "B"


def test_bundle_has_three_distinct_evidence_ids() -> None:
    rdr = _make_reader_with_uniaxial_membrane()
    _, bundle = generate_pressure_vessel_local_stress_summary(
        rdr,  # type: ignore[arg-type]
        project_id="P", task_id="T", report_id="R", bundle_id="B",
        scl_node_ids=[10, 20, 30, 40, 50],
        scl_distances=[0.0, 0.5, 1.0, 1.5, 2.0],
    )
    ids = {item.evidence_id for item in bundle.evidence_items}
    assert ids == {"EV-PM", "EV-PM-PB", "EV-MAX-VM-SCL"}
    for item in bundle.evidence_items:
        assert item.evidence_type is EvidenceType.SIMULATION


def test_evidence_dag_links_pmpb_to_pm_and_pq_to_pmpb() -> None:
    """ADR-012 derivation chain: EV-PM-PB derives from EV-PM,
    EV-MAX-VM-SCL derives from EV-PM-PB."""
    rdr = _make_reader_with_uniaxial_membrane()
    _, bundle = generate_pressure_vessel_local_stress_summary(
        rdr,  # type: ignore[arg-type]
        project_id="P", task_id="T", report_id="R", bundle_id="B",
        scl_node_ids=[10, 20, 30, 40, 50],
        scl_distances=[0.0, 0.5, 1.0, 1.5, 2.0],
    )
    by_id = {item.evidence_id: item for item in bundle.evidence_items}
    assert by_id["EV-PM"].derivation is None
    assert by_id["EV-PM-PB"].derivation == ["EV-PM"]
    assert by_id["EV-MAX-VM-SCL"].derivation == ["EV-PM-PB"]


# --- numerical correctness -------------------------------------------------


def test_pure_membrane_p_m_equals_input_pm_pb_pq_equal_pm() -> None:
    """For uniaxial σ_xx = 100 (pure membrane):
      P_m = von_mises(uniaxial 100) = 100
      P_m + P_b = same (bending = 0)
      P + Q = same (peak = 0)
    """
    rdr = _make_reader_with_uniaxial_membrane(value=100.0)
    _, bundle = generate_pressure_vessel_local_stress_summary(
        rdr,  # type: ignore[arg-type]
        project_id="P", task_id="T", report_id="R", bundle_id="B",
        scl_node_ids=[10, 20, 30, 40, 50],
        scl_distances=[0.0, 0.5, 1.0, 1.5, 2.0],
    )
    by_id = {item.evidence_id: item for item in bundle.evidence_items}
    assert by_id["EV-PM"].data.value == pytest.approx(100.0)
    assert by_id["EV-PM-PB"].data.value == pytest.approx(100.0)
    assert by_id["EV-MAX-VM-SCL"].data.value == pytest.approx(100.0)


def test_pure_bending_p_m_zero_pb_equal_slope_pq_equal_slope() -> None:
    """For uniaxial σ_xx = slope * (s_norm - 0.5) * 2 (pure bending,
    -slope at inner to +slope at outer):
      P_m = 0
      P_m + P_b = von_mises(uniaxial ±slope) = slope (max over surfaces)
      P + Q = same as P_m + P_b (the peak component is zero — pure
              linear bending lives entirely in the bending term)
    """
    slope = 80.0
    rdr = _make_reader_with_uniaxial_bending(slope=slope)
    _, bundle = generate_pressure_vessel_local_stress_summary(
        rdr,  # type: ignore[arg-type]
        project_id="P", task_id="T", report_id="R", bundle_id="B",
        scl_node_ids=[10, 20, 30, 40, 50],
        scl_distances=[0.0, 0.5, 1.0, 1.5, 2.0],
    )
    by_id = {item.evidence_id: item for item in bundle.evidence_items}
    assert by_id["EV-PM"].data.value == pytest.approx(0.0, abs=1e-10)
    assert by_id["EV-PM-PB"].data.value == pytest.approx(slope, rel=1e-9)
    assert by_id["EV-MAX-VM-SCL"].data.value == pytest.approx(slope, rel=1e-9)


def test_membrane_plus_bending_separates_correctly() -> None:
    """Combined uniaxial membrane=50 + bending=±30:
      σ_xx at inner = 20, at outer = 80
      P_m = 50, P_m + P_b = 80 (max of |20|, |80|), P+Q = 80.
    """
    node_ids = np.array([10, 20, 30, 40, 50], dtype=np.int64)
    tensors = np.zeros((5, 6), dtype=np.float64)
    tensors[:, 0] = np.array([20, 35, 50, 65, 80], dtype=np.float64)
    rdr = _SCLReader(node_ids=node_ids, tensors=tensors)
    _, bundle = generate_pressure_vessel_local_stress_summary(
        rdr,  # type: ignore[arg-type]
        project_id="P", task_id="T", report_id="R", bundle_id="B",
        scl_node_ids=[10, 20, 30, 40, 50],
        scl_distances=[0.0, 0.5, 1.0, 1.5, 2.0],
    )
    by_id = {item.evidence_id: item for item in bundle.evidence_items}
    assert by_id["EV-PM"].data.value == pytest.approx(50.0)
    assert by_id["EV-PM-PB"].data.value == pytest.approx(80.0, rel=1e-9)
    assert by_id["EV-MAX-VM-SCL"].data.value == pytest.approx(80.0, rel=1e-9)


def test_pq_picks_max_along_scl_when_field_has_quadratic_residual() -> None:
    """Construct σ_xx(s) = 50 + 30*(s-s_mid) + parabola(peak=100 at mid).
    At s_mid: σ = 50 + 0 + 100 = 150 (the SCL maximum).
    At surfaces: σ = 50 ± 30 + 0 = 20 or 80.

    Important: P_m is the through-thickness AVERAGE of σ, which
    includes the DC component of the parabola. The parabola
    100*(1 - 4(s-s_mid)²/t²) has analytical mean 100*(2/3) ≈ 66.67,
    so P_m_continuous = 50 + 66.67 ≈ 116.67. With 5 trapz points
    P_m ≈ 112.5 (O(h²) error — trapezoidal underestimates the
    parabola integral). P_b is the LS linear coefficient = 30
    (exact). So P_m + P_b ≈ 142.5; P + Q is the SCL max = 150.

    This test pins the producer's behaviour against ASME §5.5.3
    semantics: the parabola's DC content lives in P_m, NOT in P_b
    or peak — the bending/peak split is linear-vs-residual, not
    surface-value-vs-midplane-value.
    """
    s = np.linspace(0.0, 2.0, 5)
    s_mid = 1.0
    t = 2.0
    parabola_peak = 100.0 * (1.0 - 4.0 * (s - s_mid) ** 2 / t**2)
    sigma_xx = 50.0 + 30.0 * (s - s_mid) + parabola_peak
    # σ_xx at the 5 sample points = [20, 110, 150, 140, 80]

    tensors = np.zeros((5, 6), dtype=np.float64)
    tensors[:, 0] = sigma_xx
    node_ids = np.array([10, 20, 30, 40, 50], dtype=np.int64)
    rdr = _SCLReader(node_ids=node_ids, tensors=tensors)
    _, bundle = generate_pressure_vessel_local_stress_summary(
        rdr,  # type: ignore[arg-type]
        project_id="P", task_id="T", report_id="R", bundle_id="B",
        scl_node_ids=[10, 20, 30, 40, 50],
        scl_distances=s.tolist(),
    )
    by_id = {item.evidence_id: item for item in bundle.evidence_items}
    # P+Q at midplane = 150 (sample at index 2, which is node 30)
    assert by_id["EV-MAX-VM-SCL"].data.value == pytest.approx(150.0, rel=1e-9)
    # P_m via 5-point trapz: weight-sum-mean of [20,110,150,140,80]
    # with weights [0.25,0.5,0.5,0.5,0.25] / 2 = 112.5.
    assert by_id["EV-PM"].data.value == pytest.approx(112.5, rel=1e-9)
    # P_m + P_b at outer: 112.5 + 30 = 142.5; at inner: 112.5 - 30 = 82.5.
    # max = 142.5.
    assert by_id["EV-PM-PB"].data.value == pytest.approx(142.5, rel=1e-9)


# --- ADR / template integration --------------------------------------------


def test_section_content_cites_all_three_evidence_ids() -> None:
    rdr = _make_reader_with_uniaxial_membrane()
    report, _ = generate_pressure_vessel_local_stress_summary(
        rdr,  # type: ignore[arg-type]
        project_id="P", task_id="T", report_id="R", bundle_id="B",
        scl_node_ids=[10, 20, 30, 40, 50],
        scl_distances=[0.0, 0.5, 1.0, 1.5, 2.0],
    )
    content = report.sections[0].content or ""
    assert "EV-PM" in content
    assert "EV-PM-PB" in content
    assert "EV-MAX-VM-SCL" in content


def test_output_validates_against_pressure_vessel_template() -> None:
    """The producer's output must satisfy PRESSURE_VESSEL_LOCAL_STRESS
    by construction (3 distinct citations, correct title)."""
    rdr = _make_reader_with_uniaxial_membrane()
    report, bundle = generate_pressure_vessel_local_stress_summary(
        rdr,  # type: ignore[arg-type]
        project_id="P", task_id="T", report_id="R", bundle_id="B",
        scl_node_ids=[10, 20, 30, 40, 50],
        scl_distances=[0.0, 0.5, 1.0, 1.5, 2.0],
    )
    validate_report(report, bundle, template=PRESSURE_VESSEL_LOCAL_STRESS)


def test_unit_pinned_to_field_metadata_unit_system() -> None:
    """ADR-003: stress unit comes from FieldMetadata.unit_system, not
    a guess. Reader is SI_MM → 'MPa'."""
    rdr = _make_reader_with_uniaxial_membrane()
    _, bundle = generate_pressure_vessel_local_stress_summary(
        rdr,  # type: ignore[arg-type]
        project_id="P", task_id="T", report_id="R", bundle_id="B",
        scl_node_ids=[10, 20, 30, 40, 50],
        scl_distances=[0.0, 0.5, 1.0, 1.5, 2.0],
    )
    for item in bundle.evidence_items:
        assert item.data.unit == "MPa"


def test_accepts_numpy_arrays_for_scl_inputs() -> None:
    """Codex R1 PR #77 MEDIUM regression: the public type hints
    accept numpy integer / float arrays, not just plain Sequence
    types. Engineers extracting SCL data via numpy slicing should be
    able to pass the result directly without a cast."""
    rdr = _make_reader_with_uniaxial_membrane()
    node_ids_np = np.array([10, 20, 30, 40, 50], dtype=np.int64)
    distances_np = np.linspace(0.0, 2.0, 5, dtype=np.float64)
    report, bundle = generate_pressure_vessel_local_stress_summary(
        rdr,  # type: ignore[arg-type]
        project_id="P", task_id="T", report_id="R", bundle_id="B",
        scl_node_ids=node_ids_np,
        scl_distances=distances_np,
    )
    assert report.template_id == "pressure_vessel_local_stress"
    assert len(bundle.evidence_items) == 3


# --- preconditions / refusal -----------------------------------------------


def test_refuses_length_mismatch_node_ids_distances() -> None:
    rdr = _make_reader_with_uniaxial_membrane()
    with pytest.raises(ValueError, match="length"):
        generate_pressure_vessel_local_stress_summary(
            rdr,  # type: ignore[arg-type]
            project_id="P", task_id="T", report_id="R", bundle_id="B",
            scl_node_ids=[10, 20, 30],
            scl_distances=[0.0, 0.5],  # len=2, mismatched
        )


def test_refuses_fewer_than_two_scl_nodes() -> None:
    rdr = _make_reader_with_uniaxial_membrane()
    with pytest.raises(ValueError, match="at least 2 nodes"):
        generate_pressure_vessel_local_stress_summary(
            rdr,  # type: ignore[arg-type]
            project_id="P", task_id="T", report_id="R", bundle_id="B",
            scl_node_ids=[10],
            scl_distances=[0.0],
        )


def test_refuses_unknown_node_id() -> None:
    rdr = _make_reader_with_uniaxial_membrane()
    with pytest.raises(ValueError, match="not present in reader's mesh"):
        generate_pressure_vessel_local_stress_summary(
            rdr,  # type: ignore[arg-type]
            project_id="P", task_id="T", report_id="R", bundle_id="B",
            scl_node_ids=[10, 20, 999],  # 999 not in mesh
            scl_distances=[0.0, 0.5, 1.0],
        )


def test_refuses_when_stress_field_missing() -> None:
    """Reader exists but its (only) state has no STRESS_TENSOR."""
    class _NoStressReader(_SCLReader):
        def get_field(
            self, name: CanonicalField, step_id: int
        ) -> Optional[FieldData]:
            return None

    rdr = _NoStressReader(
        node_ids=np.array([10, 20], dtype=np.int64),
        tensors=np.zeros((2, 6), dtype=np.float64),
    )
    with pytest.raises(ValueError, match="STRESS_TENSOR"):
        generate_pressure_vessel_local_stress_summary(
            rdr,  # type: ignore[arg-type]
            project_id="P", task_id="T", report_id="R", bundle_id="B",
            scl_node_ids=[10, 20],
            scl_distances=[0.0, 1.0],
        )


def test_refuses_non_uniform_scl_spacing_propagates_from_layer3() -> None:
    """Codex R1 W3c HIGH guard from Layer 3 must surface here as a
    ValueError to the engineer (not silently bias P_b)."""
    node_ids = np.array([10, 20, 30, 40, 50], dtype=np.int64)
    tensors = np.zeros((5, 6), dtype=np.float64)
    tensors[:, 0] = 50.0  # uniform doesn't matter for the spacing check
    rdr = _SCLReader(node_ids=node_ids, tensors=tensors)
    with pytest.raises(ValueError, match="uniformly-spaced"):
        generate_pressure_vessel_local_stress_summary(
            rdr,  # type: ignore[arg-type]
            project_id="P", task_id="T", report_id="R", bundle_id="B",
            scl_node_ids=[10, 20, 30, 40, 50],
            scl_distances=[0.0, 0.1, 0.4, 1.0, 2.0],  # non-uniform
        )


def test_template_id_and_title_overrides() -> None:
    """Backwards-compat parity with the other two producers."""
    rdr = _make_reader_with_uniaxial_membrane()
    report, _ = generate_pressure_vessel_local_stress_summary(
        rdr,  # type: ignore[arg-type]
        project_id="P", task_id="T", report_id="R", bundle_id="B",
        scl_node_ids=[10, 20, 30, 40, 50],
        scl_distances=[0.0, 0.5, 1.0, 1.5, 2.0],
        template_id="custom_pv_v2",
        title="Custom PV title",
    )
    assert report.template_id == "custom_pv_v2"
    assert report.title == "Custom PV title"


# --- resample integration (RFC-002-prep) ---------------------------------


def test_resample_n_points_accepts_non_uniform_input() -> None:
    """The headline use case: an engineer with non-uniform CalculiX
    nodes hands the producer a non-uniform --scl-distances series and
    sets resample_n_points. The producer must NOT raise the
    'uniformly-spaced' error from the linearizer; the report comes
    out clean."""
    node_ids = np.array([10, 20, 30, 40, 50], dtype=np.int64)
    tensors = np.zeros((5, 6), dtype=np.float64)
    tensors[:, 0] = 100.0  # pure membrane, value-invariant under resample
    rdr = _SCLReader(node_ids=node_ids, tensors=tensors)
    report, bundle = generate_pressure_vessel_local_stress_summary(
        rdr,  # type: ignore[arg-type]
        project_id="P", task_id="T", report_id="R", bundle_id="B",
        scl_node_ids=[10, 20, 30, 40, 50],
        scl_distances=[0.0, 0.1, 0.4, 1.0, 2.0],  # non-uniform
        resample_n_points=21,
    )
    assert isinstance(report, ReportSpec)
    ids = {item.evidence_id for item in bundle.evidence_items}
    assert ids == {"EV-PM", "EV-PM-PB", "EV-MAX-VM-SCL"}


def test_resample_pure_membrane_value_unchanged() -> None:
    """Pure-membrane input has no through-thickness variation, so
    resampling onto any uniform grid recovers the same membrane —
    P_m must equal the input membrane stress."""
    node_ids = np.array([10, 20, 30, 40, 50], dtype=np.int64)
    tensors = np.zeros((5, 6), dtype=np.float64)
    tensors[:, 0] = 80.0
    rdr = _SCLReader(node_ids=node_ids, tensors=tensors)
    _, bundle = generate_pressure_vessel_local_stress_summary(
        rdr,  # type: ignore[arg-type]
        project_id="P", task_id="T", report_id="R", bundle_id="B",
        scl_node_ids=[10, 20, 30, 40, 50],
        scl_distances=[0.0, 0.1, 0.4, 1.0, 2.0],  # non-uniform
        resample_n_points=21,
    )
    pm_item = next(it for it in bundle.evidence_items if it.evidence_id == "EV-PM")
    assert pm_item.data.value == pytest.approx(80.0, rel=1e-9)


def test_resample_max_vm_keeps_raw_node_label() -> None:
    """Even with resampling on, EV-MAX-VM-SCL must report a real
    physical node id (from scl_node_ids), not an interpolated grid
    index — the location label is the engineer's audit anchor."""
    # Construct a field where the maximum von Mises sits at a known
    # raw node so we can assert the label points at it.
    node_ids = np.array([10, 20, 30, 40, 50], dtype=np.int64)
    tensors = np.zeros((5, 6), dtype=np.float64)
    # σ_xx values: max at index 3 (node 40) — peak-near-outer.
    tensors[:, 0] = np.array([10.0, 20.0, 50.0, 200.0, 30.0], dtype=np.float64)
    rdr = _SCLReader(node_ids=node_ids, tensors=tensors)
    _, bundle = generate_pressure_vessel_local_stress_summary(
        rdr,  # type: ignore[arg-type]
        project_id="P", task_id="T", report_id="R", bundle_id="B",
        scl_node_ids=[10, 20, 30, 40, 50],
        scl_distances=[0.0, 0.1, 0.4, 1.0, 2.0],  # non-uniform
        resample_n_points=21,
    )
    max_vm_item = next(
        it for it in bundle.evidence_items if it.evidence_id == "EV-MAX-VM-SCL"
    )
    # The location label includes the physical node id — must be 40.
    assert "node 40" in max_vm_item.data.location


def test_resample_none_still_rejects_non_uniform() -> None:
    """Default behavior (resample_n_points=None) must remain
    fail-fast on non-uniform spacing — the contract change is
    opt-in only."""
    node_ids = np.array([10, 20, 30, 40, 50], dtype=np.int64)
    tensors = np.zeros((5, 6), dtype=np.float64)
    tensors[:, 0] = 50.0
    rdr = _SCLReader(node_ids=node_ids, tensors=tensors)
    with pytest.raises(ValueError, match="uniformly-spaced"):
        generate_pressure_vessel_local_stress_summary(
            rdr,  # type: ignore[arg-type]
            project_id="P", task_id="T", report_id="R", bundle_id="B",
            scl_node_ids=[10, 20, 30, 40, 50],
            scl_distances=[0.0, 0.1, 0.4, 1.0, 2.0],  # non-uniform
            resample_n_points=None,  # explicit
        )
