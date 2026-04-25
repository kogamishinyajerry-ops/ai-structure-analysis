"""Schema-shape assertions for `schemas.viz_manifest` (ADR-016).

This guards the contract every Phase 2.2 viewer-track PR will be measured
against. The actual `.frd → .vtu` writer (`backend.app.viz.frd_to_vtu`)
lands in a follow-up; round-trip tests live in `test_frd_to_vtu_writer.py`.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from schemas.viz_manifest import (
    VIZ_MANIFEST_SCHEMA_VERSION,
    BBox,
    DisplacementField,
    IncrementEntry,
    MeshSection,
    ScalarStressField,
    Units,
    VizManifest,
    WriterInfo,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _bbox() -> BBox:
    return BBox(min=(0.0, 0.0, 0.0), max=(1.0, 1.0, 1.0))


def _units() -> Units:
    return Units(length="m", stress="Pa")


def _mesh() -> MeshSection:
    return MeshSection(
        uri="mesh.vtu",
        n_nodes=10,
        n_elements=4,
        element_types=("C3D10",),
        bbox=_bbox(),
        units=_units(),
    )


def _disp_field() -> DisplacementField:
    return DisplacementField(
        uri="field_0_displacement.vtu",
        units="m",
        max_magnitude=0.0023,
    )


def _vm_field() -> ScalarStressField:
    return ScalarStressField(
        kind="von_mises",
        uri="field_0_von_mises.vtu",
        units="Pa",
        min=0.0,
        max=1.4e8,
    )


def _increment() -> IncrementEntry:
    return IncrementEntry(
        index=0,
        step=1,
        type="static",
        value=1.0,
        fields={"displacement": _disp_field(), "von_mises": _vm_field()},
    )


def _writer() -> WriterInfo:
    return WriterInfo(
        version="0.1.0",
        frd_parser_version="2.1.0",
        wrote_at="2026-04-27T12:34:56Z",
    )


def _manifest() -> VizManifest:
    return VizManifest(
        run_id="RUN-2026-04-27-abc123",
        mesh=_mesh(),
        increments=(_increment(),),
        writer=_writer(),
    )


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


def test_schema_version_constant_pinned():
    assert VIZ_MANIFEST_SCHEMA_VERSION == "v1"


def test_default_schema_version_matches_constant():
    m = _manifest()
    assert m.schema_version == VIZ_MANIFEST_SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Frozen + extra=forbid invariants
# ---------------------------------------------------------------------------


def test_manifest_is_frozen():
    m = _manifest()
    with pytest.raises(ValidationError):
        m.run_id = "RUN-other"  # type: ignore[misc]


def test_manifest_rejects_unknown_top_level_keys():
    payload = json.loads(_manifest().model_dump_json())
    payload["mystery_field"] = "should_not_be_allowed"
    with pytest.raises(ValidationError):
        VizManifest.model_validate(payload)


def test_increment_rejects_unknown_keys():
    base = _increment().model_dump()
    base["bonus"] = "nope"
    with pytest.raises(ValidationError):
        IncrementEntry.model_validate(base)


def test_mesh_rejects_unknown_keys():
    base = _mesh().model_dump()
    base["bonus"] = "nope"
    with pytest.raises(ValidationError):
        MeshSection.model_validate(base)


# ---------------------------------------------------------------------------
# Required-field validation
# ---------------------------------------------------------------------------


def test_run_id_must_be_non_empty():
    with pytest.raises(ValidationError):
        VizManifest(
            run_id="",
            mesh=_mesh(),
            increments=(_increment(),),
            writer=_writer(),
        )


def test_increments_must_be_non_empty():
    with pytest.raises(ValidationError):
        VizManifest(
            run_id="RUN-x",
            mesh=_mesh(),
            increments=(),
            writer=_writer(),
        )


def test_mesh_n_nodes_must_be_positive():
    with pytest.raises(ValidationError):
        MeshSection(
            uri="mesh.vtu",
            n_nodes=0,
            n_elements=1,
            element_types=("C3D10",),
            bbox=_bbox(),
            units=_units(),
        )


def test_mesh_n_elements_must_be_positive():
    with pytest.raises(ValidationError):
        MeshSection(
            uri="mesh.vtu",
            n_nodes=10,
            n_elements=0,
            element_types=("C3D10",),
            bbox=_bbox(),
            units=_units(),
        )


def test_skipped_cells_cannot_be_negative():
    with pytest.raises(ValidationError):
        VizManifest(
            run_id="RUN-x",
            mesh=_mesh(),
            increments=(_increment(),),
            skipped_cells=-1,
            writer=_writer(),
        )


def test_displacement_max_magnitude_cannot_be_negative():
    with pytest.raises(ValidationError):
        DisplacementField(uri="f.vtu", units="m", max_magnitude=-0.001)


# ---------------------------------------------------------------------------
# Cell-type discipline
# ---------------------------------------------------------------------------


def test_unsupported_cell_type_rejected():
    """An element type the writer doesn't yet emit must NOT silently slip in."""
    with pytest.raises(ValidationError):
        MeshSection(
            uri="mesh.vtu",
            n_nodes=10,
            n_elements=4,
            element_types=("C3D27",),  # not in SupportedCellType literal
            bbox=_bbox(),
            units=_units(),
        )


def test_supported_cell_types_accepted():
    for ct in ("C3D4", "C3D10", "C3D8", "C3D20", "S3", "S4"):
        m = MeshSection(
            uri="mesh.vtu",
            n_nodes=10,
            n_elements=4,
            element_types=(ct,),  # type: ignore[arg-type]
            bbox=_bbox(),
            units=_units(),
        )
        assert ct in m.element_types


# ---------------------------------------------------------------------------
# Increment type discipline
# ---------------------------------------------------------------------------


def test_unknown_increment_type_rejected():
    with pytest.raises(ValidationError):
        IncrementEntry(
            index=0,
            step=1,
            type="harmonic",  # type: ignore[arg-type]
            value=1.0,
            fields={"displacement": _disp_field()},
        )


def test_static_vibration_buckling_accepted():
    for t in ("static", "vibration", "buckling"):
        IncrementEntry(
            index=0,
            step=1,
            type=t,  # type: ignore[arg-type]
            value=1.0,
            fields={"displacement": _disp_field()},
        )


# ---------------------------------------------------------------------------
# Discriminated union: field kind
# ---------------------------------------------------------------------------


def test_field_kind_discriminator_displacement():
    payload = {
        "kind": "displacement",
        "uri": "f.vtu",
        "units": "m",
        "max_magnitude": 0.001,
    }
    inc = IncrementEntry(
        index=0,
        step=1,
        type="static",
        value=1.0,
        fields={"displacement": payload},  # type: ignore[arg-type]
    )
    assert isinstance(inc.fields["displacement"], DisplacementField)


def test_field_kind_discriminator_von_mises():
    payload = {
        "kind": "von_mises",
        "uri": "f.vtu",
        "units": "Pa",
        "min": 0.0,
        "max": 1.0e8,
    }
    inc = IncrementEntry(
        index=0,
        step=1,
        type="static",
        value=1.0,
        fields={"von_mises": payload},  # type: ignore[arg-type]
    )
    assert isinstance(inc.fields["von_mises"], ScalarStressField)


def test_unknown_field_kind_rejected():
    payload = {
        "kind": "strain_xx",  # not in the union
        "uri": "f.vtu",
        "units": "Pa",
        "min": 0.0,
        "max": 1.0e8,
    }
    with pytest.raises(ValidationError):
        IncrementEntry(
            index=0,
            step=1,
            type="static",
            value=1.0,
            fields={"strain_xx": payload},  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# Units discipline
# ---------------------------------------------------------------------------


def test_unknown_length_unit_rejected():
    with pytest.raises(ValidationError):
        Units(length="cm")  # type: ignore[arg-type]


def test_unknown_stress_unit_rejected():
    with pytest.raises(ValidationError):
        Units(length="m", stress="kPa")  # type: ignore[arg-type]


def test_stress_unit_optional():
    u = Units(length="m")
    assert u.stress is None


# ---------------------------------------------------------------------------
# JSON round-trip
# ---------------------------------------------------------------------------


def test_manifest_json_round_trip():
    original = _manifest()
    blob = original.model_dump_json()
    parsed = json.loads(blob)
    rebuilt = VizManifest.model_validate(parsed)
    assert rebuilt == original


def test_manifest_json_dump_is_indexable_by_viewer():
    """Viewer SPA uses these specific keys; pin the surface."""
    blob = json.loads(_manifest().model_dump_json())
    assert blob["schema_version"] == "v1"
    assert blob["mesh"]["uri"] == "mesh.vtu"
    assert blob["mesh"]["bbox"]["min"] == [0.0, 0.0, 0.0]
    assert blob["increments"][0]["fields"]["displacement"]["kind"] == "displacement"
    assert blob["increments"][0]["fields"]["von_mises"]["kind"] == "von_mises"


# ---------------------------------------------------------------------------
# Writer info discipline
# ---------------------------------------------------------------------------


def test_writer_tool_pinned():
    """Only this one writer may produce manifests."""
    with pytest.raises(ValidationError):
        WriterInfo(
            tool="some.other.writer",  # type: ignore[arg-type]
            version="0.1.0",
            frd_parser_version="2.1.0",
            wrote_at="2026-04-27T00:00:00Z",
        )


def test_writer_default_tool():
    w = WriterInfo(version="0.1.0", frd_parser_version="2.1.0", wrote_at="2026-04-27T00:00:00Z")
    assert w.tool == "backend.app.viz.frd_to_vtu"
