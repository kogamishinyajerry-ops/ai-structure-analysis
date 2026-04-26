"""CalculiX Layer-1 adapter — RFC-001 §4.5 W2 contract tests.

Covers the ``ReaderHandle`` Protocol surface end-to-end against the
existing GS-001 ``.frd`` artifact. The σ_max-vs-analytical gate from
RFC §6.4 W2 is documented but skipped — GS-001 is currently flagged
``insufficient_evidence`` per FP-001, so a 5% tolerance check against
the README's analytical solution would fail for fixture reasons, not
adapter reasons.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from app.adapters.calculix import CalculiXReader
from app.core.types import (
    CanonicalField,
    ComponentType,
    CoordinateSystemKind,
    FieldData,
    FieldLocation,
    Mesh,
    ReaderHandle,
    UnitSystem,
)


GS001_FRD = (
    Path(__file__).resolve().parents[2] / "golden_samples" / "GS-001" / "gs001_result.frd"
)


@pytest.fixture(scope="module")
def reader() -> CalculiXReader:
    if not GS001_FRD.exists():
        pytest.skip(f"GS-001 .frd missing at {GS001_FRD}")
    return CalculiXReader(GS001_FRD, unit_system=UnitSystem.SI_MM)


# --- Protocol conformance + lifecycle --------------------------------------


def test_reader_implements_reader_handle_protocol(reader: CalculiXReader) -> None:
    assert isinstance(reader, ReaderHandle)


def test_mesh_implements_mesh_protocol(reader: CalculiXReader) -> None:
    assert isinstance(reader.mesh, Mesh)


def test_close_blocks_subsequent_access(tmp_path: Path) -> None:
    if not GS001_FRD.exists():
        pytest.skip("GS-001 missing")
    r = CalculiXReader(GS001_FRD, unit_system=UnitSystem.SI_MM)
    r.close()
    with pytest.raises(RuntimeError):
        _ = r.mesh
    with pytest.raises(RuntimeError):
        _ = r.solution_states


def test_failed_parse_raises_value_error(tmp_path: Path) -> None:
    junk = tmp_path / "garbage.frd"
    junk.write_text("not a frd file")
    with pytest.raises(ValueError):
        CalculiXReader(junk, unit_system=UnitSystem.SI_MM)


# --- Mesh contract ---------------------------------------------------------


def test_mesh_node_id_array_is_int64_dense(reader: CalculiXReader) -> None:
    arr = reader.mesh.node_id_array
    assert arr.dtype == np.int64
    assert arr.ndim == 1
    assert arr.size == 44  # GS-001 cantilever has 44 nodes


def test_mesh_node_index_maps_id_to_dense_index(reader: CalculiXReader) -> None:
    idx = reader.mesh.node_index
    ids = reader.mesh.node_id_array.tolist()
    assert set(idx.keys()) == set(ids)
    assert sorted(idx.values()) == list(range(len(ids)))


def test_mesh_coordinates_shape(reader: CalculiXReader) -> None:
    coords = reader.mesh.coordinates
    assert coords.shape == (44, 3)
    assert coords.dtype == np.float64


def test_mesh_unit_system_round_trips(reader: CalculiXReader) -> None:
    assert reader.mesh.unit_system is UnitSystem.SI_MM


# --- Layer-2 emptiness honoured (ADR-003) ----------------------------------


def test_materials_empty_for_frd_only(reader: CalculiXReader) -> None:
    # .frd carries no material card; the adapter MUST NOT fabricate.
    assert reader.materials == {}


def test_boundary_conditions_empty_for_frd_only(reader: CalculiXReader) -> None:
    assert reader.boundary_conditions == []


# --- Solution states + field merge -----------------------------------------


def test_solution_states_merge_disp_and_stress_into_one_step(
    reader: CalculiXReader,
) -> None:
    states = reader.solution_states
    assert len(states) == 1
    s = states[0]
    assert s.step_name == "static"
    assert CanonicalField.DISPLACEMENT in s.available_fields
    assert CanonicalField.STRESS_TENSOR in s.available_fields


def test_get_field_displacement(reader: CalculiXReader) -> None:
    step = reader.solution_states[0]
    fd = reader.get_field(CanonicalField.DISPLACEMENT, step.step_id)
    assert isinstance(fd, FieldData)
    assert fd.metadata.name is CanonicalField.DISPLACEMENT
    assert fd.metadata.location is FieldLocation.NODE
    assert fd.metadata.component_type is ComponentType.VECTOR_3D
    assert fd.metadata.source_solver == "calculix"
    assert fd.metadata.source_field_name == "DISP"
    assert fd.metadata.source_file == GS001_FRD
    assert fd.metadata.unit_system is UnitSystem.SI_MM
    assert fd.metadata.coordinate_system == CoordinateSystemKind.GLOBAL.value
    assert fd.metadata.was_averaged == "unknown"
    arr = fd.values()
    assert arr.shape == (44, 3)
    assert arr.dtype == np.float64


def test_get_field_stress_tensor(reader: CalculiXReader) -> None:
    step = reader.solution_states[0]
    fd = reader.get_field(CanonicalField.STRESS_TENSOR, step.step_id)
    assert isinstance(fd, FieldData)
    assert fd.metadata.name is CanonicalField.STRESS_TENSOR
    assert fd.metadata.location is FieldLocation.NODE
    assert fd.metadata.component_type is ComponentType.TENSOR_SYM_3D
    assert fd.metadata.source_field_name == "STRESS"
    arr = fd.values()
    assert arr.shape == (44, 6), "TENSOR_SYM_3D = 6 components per node"
    # ADR-001: adapter does NOT compute von Mises. The 7th column does
    # not exist; if it ever does, derived-quantity contamination crept
    # back into Layer 1.


def test_get_field_at_nodes_matches_values(reader: CalculiXReader) -> None:
    step = reader.solution_states[0]
    fd = reader.get_field(CanonicalField.STRESS_TENSOR, step.step_id)
    assert np.array_equal(fd.values(), fd.at_nodes())


def test_get_field_returns_none_for_missing_field(reader: CalculiXReader) -> None:
    step = reader.solution_states[0]
    # GS-001 .frd carries DISP + STRESS only — STRAIN / REACTION / etc. absent.
    assert reader.get_field(CanonicalField.STRAIN_TENSOR, step.step_id) is None
    assert reader.get_field(CanonicalField.REACTION_FORCE, step.step_id) is None
    assert reader.get_field(CanonicalField.NODAL_COORDINATES, step.step_id) is None


def test_get_field_returns_none_for_unknown_step(reader: CalculiXReader) -> None:
    assert reader.get_field(CanonicalField.DISPLACEMENT, step_id=999) is None


# --- ADR-003 unit-system honesty ------------------------------------------


def test_unit_system_default_is_unknown(tmp_path: Path) -> None:
    if not GS001_FRD.exists():
        pytest.skip("GS-001 missing")
    r = CalculiXReader(GS001_FRD)  # no unit_system kwarg
    try:
        assert r.mesh.unit_system is UnitSystem.UNKNOWN
        fd = r.get_field(
            CanonicalField.DISPLACEMENT, r.solution_states[0].step_id
        )
        assert fd is not None
        assert fd.metadata.unit_system is UnitSystem.UNKNOWN
    finally:
        r.close()


# --- W2 RFC §6.4 σ_max done-gate (BLOCKED on FP-001 GS-001 regeneration) ---


@pytest.mark.skip(
    reason="GS-001 fixture flagged insufficient_evidence per FP-001 — analytical "
    "comparison waits on regeneration; adapter structural contract is verified "
    "by the rest of this module."
)
def test_gs001_sigma_max_within_5pct_of_analytical(reader: CalculiXReader) -> None:
    """RFC §6.4 W2: GS-001 σ_max within 5% of the analytical 7.5 MPa.

    Gated on FP-001 resolution (GS-001 README + .inp + expected_results
    are mutually inconsistent). When the regenerated GS-001 lands, drop
    the skip marker.
    """
    step = reader.solution_states[0]
    fd = reader.get_field(CanonicalField.STRESS_TENSOR, step.step_id)
    assert fd is not None
    arr = fd.values()  # (N, 6): S11, S22, S33, S12, S23, S13
    s11, s22, s33, s12, s23, s13 = (arr[:, i] for i in range(6))
    sigma_vm = np.sqrt(
        0.5 * ((s11 - s22) ** 2 + (s22 - s33) ** 2 + (s33 - s11) ** 2)
        + 3 * (s12**2 + s23**2 + s13**2)
    )
    assert abs(float(sigma_vm.max()) - 7.5) / 7.5 < 0.05
