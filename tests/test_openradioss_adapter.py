"""Tests for the OpenRadioss Layer-1 adapter — RFC-001 W7b.

Tests that drive a real animation frame are skipped if
``vortex_radioss`` / ``lasso-python`` aren't importable (declared
optional under ``[project.optional-dependencies] openradioss``). Static
helpers (e.g. ``_resolve_node_ids``) are exercised unconditionally —
the adapter package imports the parser lazily inside ``_read_frame``,
so the class itself is importable without the extra installed.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest
from app.adapters.openradioss import OpenRadiossReader
from app.core.types import (
    CanonicalField,
    ComponentType,
    FieldLocation,
    UnitSystem,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
GS100_DIR = REPO_ROOT / "golden_samples" / "GS-100-radioss-smoke"

_HAS_PARSER = (
    importlib.util.find_spec("vortex_radioss") is not None
    and importlib.util.find_spec("lasso") is not None
)
needs_parser = pytest.mark.skipif(
    not _HAS_PARSER,
    reason="vortex_radioss / lasso-python not installed (optional 'openradioss' extra)",
)


@pytest.fixture()
def gs100_reader() -> OpenRadiossReader:
    """Open the GS-100 smoke fixture in si-mm and yield the reader."""
    if not _HAS_PARSER:
        pytest.skip("vortex_radioss / lasso-python not installed (optional extra)")
    if not (GS100_DIR / "BOULE1V5A001.gz").is_file():
        pytest.skip(f"GS-100 fixture missing at {GS100_DIR}")
    rdr = OpenRadiossReader(
        root_dir=GS100_DIR,
        rootname="BOULE1V5",
        unit_system=UnitSystem.SI_MM,
    )
    try:
        yield rdr
    finally:
        rdr.close()


# ---------------------------------------------------------------------------
# Layer-2 protocol shape
# ---------------------------------------------------------------------------


def test_reader_implements_reader_handle_protocol(
    gs100_reader: OpenRadiossReader,
) -> None:
    """Runtime-check that the adapter satisfies the Protocol surface."""
    from app.core.types import ReaderHandle

    assert isinstance(gs100_reader, ReaderHandle), (
        "OpenRadiossReader must satisfy the ReaderHandle Protocol — "
        "missing one of: mesh / materials / boundary_conditions / "
        "solution_states / get_field / close."
    )


def test_mesh_node_count_matches_first_frame_header(
    gs100_reader: OpenRadiossReader,
) -> None:
    """GS-100 BOULE1V5 has 114 nodes; the mesh must surface the same
    node ID array regardless of how many frames the case has."""
    mesh = gs100_reader.mesh
    assert mesh.node_id_array.shape == (114,)
    assert mesh.coordinates.shape == (114, 3)
    assert mesh.unit_system == UnitSystem.SI_MM


def test_node_index_is_consistent_with_id_array(
    gs100_reader: OpenRadiossReader,
) -> None:
    mesh = gs100_reader.mesh
    ids = mesh.node_id_array
    idx = mesh.node_index
    assert len(idx) == len(ids)
    for i, nid in enumerate(ids):
        assert idx[int(nid)] == i


# ---------------------------------------------------------------------------
# Time history
# ---------------------------------------------------------------------------


def test_solution_states_present_and_time_monotonic(
    gs100_reader: OpenRadiossReader,
) -> None:
    """GS-100 fixture ships frames A001 / A011 / A021. The reader must
    discover all three and report monotonically increasing time."""
    states = gs100_reader.solution_states
    assert len(states) == 3, f"expected 3 frames in GS-100; got {[s.step_id for s in states]}"
    step_ids = [s.step_id for s in states]
    assert step_ids == sorted(step_ids), "states must be sorted by step_id"
    times = [s.time for s in states]
    assert all(t is not None for t in times)
    assert times == sorted(times), "time must be monotonically non-decreasing"
    # Final time per the W7a engine deck (run-time 0.5 ms, dump dt 0.025).
    assert states[-1].time == pytest.approx(0.5, rel=0.05), (
        f"final state time should be ~0.5 ms; got {states[-1].time}"
    )


def test_displacement_field_available_for_all_states(
    gs100_reader: OpenRadiossReader,
) -> None:
    """Displacement is reconstructed from coorA(step) - coorA(0); it
    must be reported as available for every state. Stress/strain are
    NOT available in this contact-only fixture (no /ANIM/ELEM/STRESS
    in the legacy deck)."""
    for state in gs100_reader.solution_states:
        assert CanonicalField.DISPLACEMENT in state.available_fields, (
            f"state {state.step_id} missing DISPLACEMENT"
        )
        assert CanonicalField.STRESS_TENSOR not in state.available_fields, (
            f"state {state.step_id} should NOT advertise STRESS_TENSOR — "
            "GS-100 has no field output. (GS-101 W7e will exercise that path.)"
        )


# ---------------------------------------------------------------------------
# Field reconstruction
# ---------------------------------------------------------------------------


def test_displacement_at_first_state_is_zero(
    gs100_reader: OpenRadiossReader,
) -> None:
    """Reference frame: displacement = current - reference = 0 by
    construction. Pin this so a future change that breaks the
    reference-frame anchor doesn't silently slip through."""
    states = gs100_reader.solution_states
    first = states[0]
    field = gs100_reader.get_field(CanonicalField.DISPLACEMENT, first.step_id)
    assert field is not None
    vals = field.values()
    assert vals.shape == (114, 3)
    assert np.allclose(vals, 0.0), (
        f"reference frame displacement must be zero; got max={np.max(np.abs(vals))}"
    )


def test_displacement_grows_with_time(
    gs100_reader: OpenRadiossReader,
) -> None:
    """For BOULE1V5 (ball impacting a fixed surface) the maximum
    nodal displacement magnitude must be monotonically non-decreasing
    across the 3 ship frames. If a future change accidentally swaps
    the reference frame this test fires."""
    states = gs100_reader.solution_states
    max_disp = []
    for s in states:
        f = gs100_reader.get_field(CanonicalField.DISPLACEMENT, s.step_id)
        assert f is not None
        v = f.values()
        max_disp.append(float(np.max(np.linalg.norm(v, axis=1))))
    assert max_disp[0] == pytest.approx(0.0, abs=1e-12)
    assert max_disp[1] > 0.0, f"mid-run displacement should be > 0; got {max_disp}"
    assert max_disp[2] >= max_disp[1], (
        f"final-frame displacement should be >= mid-frame; got {max_disp}"
    )


def test_displacement_metadata_pinned(
    gs100_reader: OpenRadiossReader,
) -> None:
    states = gs100_reader.solution_states
    f = gs100_reader.get_field(CanonicalField.DISPLACEMENT, states[1].step_id)
    assert f is not None
    m = f.metadata
    assert m.name == CanonicalField.DISPLACEMENT
    assert m.location == FieldLocation.NODE
    assert m.component_type == ComponentType.VECTOR_3D
    assert m.unit_system == UnitSystem.SI_MM
    assert m.source_solver == "OpenRadioss"
    assert m.was_averaged is False
    # Reconstruction citation, not a literal solver field name.
    assert "coorA" in m.source_field_name


# ---------------------------------------------------------------------------
# ADR-003: don't fabricate
# ---------------------------------------------------------------------------


def test_get_field_returns_none_for_missing(
    gs100_reader: OpenRadiossReader,
) -> None:
    """ADR-003: no STRESS_TENSOR in this fixture → get_field MUST
    return None, not a zero tensor."""
    states = gs100_reader.solution_states
    out = gs100_reader.get_field(CanonicalField.STRESS_TENSOR, states[0].step_id)
    assert out is None


def test_get_field_returns_none_for_unknown_step(
    gs100_reader: OpenRadiossReader,
) -> None:
    out = gs100_reader.get_field(CanonicalField.DISPLACEMENT, step_id=99999)
    assert out is None


def test_materials_and_bcs_are_empty(
    gs100_reader: OpenRadiossReader,
) -> None:
    """ADR-003: animation file carries material *codes* but not full
    Material cards; the adapter must NOT fabricate. BCs come from the
    starter `.rad` deck which this adapter does not parse."""
    assert gs100_reader.materials == {}
    assert gs100_reader.boundary_conditions == []


# ---------------------------------------------------------------------------
# Adapter-specific surface (W7d will consume)
# ---------------------------------------------------------------------------


def test_deleted_facets_array_shape_and_alive_state(
    gs100_reader: OpenRadiossReader,
) -> None:
    """delEltA contract: shape (n_facets,), int8, 1=alive 0=deleted.
    GS-100 has 74 facets, all alive (it's a contact test, no erosion)."""
    states = gs100_reader.solution_states
    for s in states:
        flags = gs100_reader.deleted_facets_for(s.step_id)
        assert flags.shape == (74,), (
            f"state {s.step_id}: expected 74 facets in delEltA; got {flags.shape}"
        )
        assert flags.dtype == np.int8
        # Contact-only test, no erosion.
        assert int(flags.sum()) == 74, (
            f"state {s.step_id}: GS-100 should have all 74 facets alive; got {int(flags.sum())}"
        )


def test_deleted_facets_unknown_step_raises(
    gs100_reader: OpenRadiossReader,
) -> None:
    with pytest.raises(KeyError):
        gs100_reader.deleted_facets_for(99999)


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


@needs_parser
def test_close_releases_decompressed_tmpdir(tmp_path: Path) -> None:
    """The adapter decompresses .gz frames into a /tmp scratch dir.
    close() must remove it. We verify by sniffing the private state —
    not strictly clean, but the alternative is a fragile fs walk."""
    if not (GS100_DIR / "BOULE1V5A001.gz").is_file():
        pytest.skip(f"GS-100 fixture missing at {GS100_DIR}")
    rdr = OpenRadiossReader(
        root_dir=GS100_DIR,
        rootname="BOULE1V5",
        unit_system=UnitSystem.SI_MM,
    )
    tmpdir = rdr._tmpdir  # type: ignore[attr-defined]
    assert tmpdir is not None and tmpdir.is_dir()
    rdr.close()
    assert not tmpdir.exists()
    # Idempotent close.
    rdr.close()


def test_close_then_read_raises(gs100_reader: OpenRadiossReader) -> None:
    gs100_reader.close()
    with pytest.raises(RuntimeError, match="close"):
        _ = gs100_reader.mesh


@needs_parser
def test_context_manager_closes_on_exit() -> None:
    if not (GS100_DIR / "BOULE1V5A001.gz").is_file():
        pytest.skip(f"GS-100 fixture missing at {GS100_DIR}")
    with OpenRadiossReader(
        root_dir=GS100_DIR,
        rootname="BOULE1V5",
        unit_system=UnitSystem.SI_MM,
    ) as rdr:
        assert len(rdr.solution_states) == 3
    with pytest.raises(RuntimeError):
        _ = rdr.mesh


# ---------------------------------------------------------------------------
# Bad input
# ---------------------------------------------------------------------------


def test_unknown_rootname_raises(tmp_path: Path) -> None:
    """No frames in tmp_path → fail fast with FileNotFoundError, not a
    silent empty reader."""
    with pytest.raises(FileNotFoundError, match="no OpenRadioss animation"):
        OpenRadiossReader(
            root_dir=tmp_path,
            rootname="NOPE",
            unit_system=UnitSystem.SI_MM,
        )


# ---------------------------------------------------------------------------
# Codex R1 follow-ups: reopen, decompressed-sibling, partial-invalid IDs,
# gap indices, SupportsElementDeletion Protocol
# ---------------------------------------------------------------------------


@needs_parser
def test_reopen_yields_equivalent_mesh_and_states() -> None:
    """ADR-004 forbids hidden caches: closing + reopening the same
    fixture must produce equivalent mesh + states. Catches stateful
    bugs (e.g. tmpdir name leaking into metadata, frame iteration
    order drifting) without needing a second fixture."""
    if not (GS100_DIR / "BOULE1V5A001.gz").is_file():
        pytest.skip(f"GS-100 fixture missing at {GS100_DIR}")
    rdr_a = OpenRadiossReader(root_dir=GS100_DIR, rootname="BOULE1V5", unit_system=UnitSystem.SI_MM)
    try:
        ids_a = rdr_a.mesh.node_id_array.copy()
        coords_a = rdr_a.mesh.coordinates.copy()
        steps_a = [s.step_id for s in rdr_a.solution_states]
        times_a = [s.time for s in rdr_a.solution_states]
    finally:
        rdr_a.close()
    rdr_b = OpenRadiossReader(root_dir=GS100_DIR, rootname="BOULE1V5", unit_system=UnitSystem.SI_MM)
    try:
        np.testing.assert_array_equal(rdr_b.mesh.node_id_array, ids_a)
        np.testing.assert_allclose(rdr_b.mesh.coordinates, coords_a)
        assert [s.step_id for s in rdr_b.solution_states] == steps_a
        assert [s.time for s in rdr_b.solution_states] == times_a
    finally:
        rdr_b.close()


@needs_parser
def test_decompressed_sibling_preferred_over_gz(tmp_path: Path) -> None:
    """Both BOULE1V5A001 and BOULE1V5A001.gz on disk → reader keeps
    the decompressed one (avoids re-decompressing on every restart in
    the dev loop)."""
    if not (GS100_DIR / "BOULE1V5A001.gz").is_file():
        pytest.skip(f"GS-100 fixture missing at {GS100_DIR}")
    import gzip
    import shutil as _sh

    # Copy the fixture into tmp + materialise decompressed siblings
    # alongside the .gz files for exactly one frame.
    for src in GS100_DIR.iterdir():
        _sh.copy(src, tmp_path / src.name)
    decomp = tmp_path / "BOULE1V5A001"
    with gzip.open(tmp_path / "BOULE1V5A001.gz", "rb") as fin, open(decomp, "wb") as fout:
        _sh.copyfileobj(fin, fout)
    assert decomp.is_file() and (tmp_path / "BOULE1V5A001.gz").is_file()

    rdr = OpenRadiossReader(root_dir=tmp_path, rootname="BOULE1V5", unit_system=UnitSystem.SI_MM)
    try:
        # The frame_paths dict must reference the decompressed file
        # for index 1 — sibling-preference rule.
        first_idx = sorted(rdr._frame_paths)[0]  # type: ignore[attr-defined]
        chosen = rdr._frame_paths[first_idx]  # type: ignore[attr-defined]
        assert chosen.suffix != ".gz", f"expected decompressed sibling preference, got {chosen}"
    finally:
        rdr.close()


def test_resolve_node_ids_partial_invalid() -> None:
    """Codex R1 HIGH: partial-invalid nodNumA must preserve valid IDs
    and synthesize *only* the bad slots above max(valid). The earlier
    implementation clobbered the whole array."""
    # Bad slots: index 2 (zero), index 4 (duplicate of 1).
    raw = np.array([10, 11, 0, 12, 11, 13], dtype=np.int64)
    ids, n_synth = OpenRadiossReader._resolve_node_ids(raw, 6)
    assert n_synth == 2
    # Valid IDs preserved in their slots.
    assert int(ids[0]) == 10
    assert int(ids[1]) == 11
    assert int(ids[3]) == 12
    assert int(ids[5]) == 13
    # Bad slots got fresh IDs strictly greater than max(valid)=13.
    assert int(ids[2]) > 13
    assert int(ids[4]) > 13
    # No collisions, no duplicates anywhere.
    assert len(set(ids.tolist())) == 6


def test_resolve_node_ids_all_valid_passthrough() -> None:
    raw = np.array([7, 9, 11, 13], dtype=np.int64)
    ids, n_synth = OpenRadiossReader._resolve_node_ids(raw, 4)
    assert n_synth == 0
    np.testing.assert_array_equal(ids, raw)


def test_resolve_node_ids_absent_falls_back_to_arange() -> None:
    ids, n_synth = OpenRadiossReader._resolve_node_ids(None, 5)
    assert n_synth == 5
    np.testing.assert_array_equal(ids, np.array([1, 2, 3, 4, 5]))


def test_displacement_metadata_records_id_synthesis(
    gs100_reader: OpenRadiossReader,
) -> None:
    """If the GS-100 nodNumA had any zeros/dups, the field metadata's
    source_field_name must say so. If it didn't, plain string. Either
    way the metadata is consistent with reader state."""
    states = gs100_reader.solution_states
    f = gs100_reader.get_field(CanonicalField.DISPLACEMENT, states[1].step_id)
    assert f is not None
    name = f.metadata.source_field_name
    n_synth = gs100_reader._n_synthesized_ids  # type: ignore[attr-defined]
    if n_synth:
        assert "adapter-synthesised" in name and str(n_synth) in name
    else:
        assert name == "coorA(step)-coorA(0)"


@needs_parser
def test_gap_indices_supported() -> None:
    """Frames at non-contiguous indices (e.g. A001, A011, A021 — what
    GS-100 actually ships) must surface as 3 states with the original
    step_ids preserved, not renumbered to 1/2/3."""
    if not (GS100_DIR / "BOULE1V5A001.gz").is_file():
        pytest.skip(f"GS-100 fixture missing at {GS100_DIR}")
    with OpenRadiossReader(
        root_dir=GS100_DIR,
        rootname="BOULE1V5",
        unit_system=UnitSystem.SI_MM,
    ) as rdr:
        step_ids = [s.step_id for s in rdr.solution_states]
        assert step_ids == [1, 11, 21], f"step_ids must equal frame index suffix; got {step_ids}"


def test_supports_element_deletion_protocol(
    gs100_reader: OpenRadiossReader,
) -> None:
    """Layer 3 feature-detects element-erosion via the runtime-checked
    sub-Protocol. Concrete adapter must satisfy it."""
    from app.core.types import SupportsElementDeletion

    assert isinstance(gs100_reader, SupportsElementDeletion), (
        "OpenRadiossReader must satisfy the SupportsElementDeletion "
        "sub-Protocol (deleted_facets_for(step_id) -> int8 array)."
    )
