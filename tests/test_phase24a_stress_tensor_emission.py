"""Phase 24 A — σ-tensor backend exporter end-to-end contract pin.

Phase 23 B shipped the frontend stress-tensor switcher + math
(`stressDerivatives.ts`) but no backend emitter wrote `stressTensor`
into `result_mesh.json`. Phase 24 A closes that gap in the
OpenRadioss dynamic exporter.

These tests pin the emission contract:

1. when ``frame.stress`` has 6 columns → every element gets
   ``stressTensor: {sxx, syy, szz, sxy, syz, sxz}`` with values
   exactly matching the input columns (no reordering, scaling,
   or unit fold).
2. when ``frame.stress`` is None → no element has a
   ``stressTensor`` key (NOT ``None``, NOT ``{}`` — absent).
3. when ``frame.stress.shape[1] < 6`` → no element has a
   ``stressTensor`` key.
4. anti-gaming guard A:-2 — confirms key-absence (not falsy
   presence) when no tensor input.

Tier 1 engineering candidate; not signed validation; not benchmark
agreement.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.viz.openradioss_dynamic_result_exporter import (  # noqa: E402
    DynamicFrameData,
    export_dynamic_result_mesh_from_frames,
)


def _base_two_hex_geometry() -> tuple[np.ndarray, np.ndarray]:
    """Two hexes — projectile (part 1) + plate (part 2), 8 nodes each."""
    coords = np.asarray(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [1.0, 0.0, 1.0],
            [1.0, 1.0, 1.0],
            [0.0, 1.0, 1.0],
            [3.0, 0.0, 0.0],
            [4.0, 0.0, 0.0],
            [4.0, 1.0, 0.0],
            [3.0, 1.0, 0.0],
            [3.0, 0.0, 0.4],
            [4.0, 0.0, 0.4],
            [4.0, 1.0, 0.4],
            [3.0, 1.0, 0.4],
        ],
        dtype=float,
    )
    connect = np.asarray(
        [
            [0, 1, 2, 3, 4, 5, 6, 7],
            [8, 9, 10, 11, 12, 13, 14, 15],
        ],
        dtype=int,
    )
    return coords, connect


def _make_frame(
    *,
    coords: np.ndarray,
    connect: np.ndarray,
    stress: np.ndarray | None,
    source: str = "model_00A001",
    timestep: float = 0.0,
) -> DynamicFrameData:
    return DynamicFrameData(
        source=source,
        timestep=timestep,
        coords=coords,
        element_node_indexes=connect,
        element_ids=np.asarray([101, 201], dtype=int),
        part_ids=np.asarray([1, 2], dtype=int),
        alive=np.asarray([True, True], dtype=bool),
        stress=stress,
        plastic_strain=np.asarray([0.0, 0.0], dtype=float),
    )


def test_phase24a_stress_tensor_emitted_when_6_columns_present(
    tmp_path: Path,
) -> None:
    """6-column stress → stressTensor on every element."""
    coords, connect = _base_two_hex_geometry()
    # element 0: σ_xx=100, σ_yy=20, σ_zz=10, σ_xy=5, σ_yz=2, σ_xz=1
    # element 1: σ_xx=50,  σ_yy=-30, σ_zz=5, σ_xy=-3, σ_yz=2, σ_xz=0
    stress = np.asarray(
        [
            [100.0, 20.0, 10.0, 5.0, 2.0, 1.0],
            [50.0, -30.0, 5.0, -3.0, 2.0, 0.0],
        ],
        dtype=float,
    )
    frame = _make_frame(coords=coords, connect=connect, stress=stress)

    result = export_dynamic_result_mesh_from_frames(
        [frame],
        output_dir=tmp_path,
        case_id="PHASE24A-EMIT",
        field="von_mises",
        source_root="test_stress_tensor",
    )
    payload = json.loads(result.result_mesh_path.read_text(encoding="utf-8"))
    frame_payload = payload["dynamicFrames"][0]
    assert len(frame_payload["elements"]) > 0

    # Map each rendered face element back to the source element index
    # so we can pin tensor values against the input stress rows.
    for element in frame_payload["elements"]:
        assert "stressTensor" in element, (
            "Phase 24 A contract: 6-col stress input MUST emit stressTensor"
        )
        tensor = element["stressTensor"]
        # Pin the six keys explicitly (no extras, no missing).
        assert set(tensor.keys()) == {"sxx", "syy", "szz", "sxy", "syz", "sxz"}
        source_index = element["sourceElementIndex"]
        expected = stress[source_index]
        assert tensor["sxx"] == expected[0]
        assert tensor["syy"] == expected[1]
        assert tensor["szz"] == expected[2]
        assert tensor["sxy"] == expected[3]
        assert tensor["syz"] == expected[4]
        assert tensor["sxz"] == expected[5]


def test_phase24a_stress_tensor_absent_when_stress_is_none(
    tmp_path: Path,
) -> None:
    """No stress input → NO stressTensor key on any element (A:-2 guard)."""
    coords, connect = _base_two_hex_geometry()
    frame = _make_frame(coords=coords, connect=connect, stress=None)

    result = export_dynamic_result_mesh_from_frames(
        [frame],
        output_dir=tmp_path,
        case_id="PHASE24A-NONE",
        field="von_mises",
        source_root="test_no_stress",
    )
    payload = json.loads(result.result_mesh_path.read_text(encoding="utf-8"))
    frame_payload = payload["dynamicFrames"][0]
    assert len(frame_payload["elements"]) > 0
    for element in frame_payload["elements"]:
        # A:-2 anti-gaming guard: absence, not falsy presence.
        assert "stressTensor" not in element, (
            "A:-2 guard: when frame.stress is None, stressTensor key "
            "must be ABSENT (not None, not {}). element="
            f"{element.get('label')}"
        )


def test_phase24a_stress_tensor_absent_when_fewer_than_6_columns(
    tmp_path: Path,
) -> None:
    """3-col stress (insufficient for full tensor) → no stressTensor key."""
    coords, connect = _base_two_hex_geometry()
    # Only 3 normal-stress columns; cannot reconstruct shear.
    stress_3col = np.asarray(
        [
            [100.0, 20.0, 10.0],
            [50.0, -30.0, 5.0],
        ],
        dtype=float,
    )
    frame = _make_frame(coords=coords, connect=connect, stress=stress_3col)

    result = export_dynamic_result_mesh_from_frames(
        [frame],
        output_dir=tmp_path,
        case_id="PHASE24A-3COL",
        field="von_mises",
        source_root="test_partial_stress",
    )
    payload = json.loads(result.result_mesh_path.read_text(encoding="utf-8"))
    frame_payload = payload["dynamicFrames"][0]
    for element in frame_payload["elements"]:
        assert "stressTensor" not in element, (
            "Partial stress (< 6 cols) must NOT emit stressTensor — "
            "frontend would consume garbage shear values"
        )


def test_phase24a_stress_tensor_preserves_column_order_no_unit_fold(
    tmp_path: Path,
) -> None:
    """Verify exact column→key mapping (no reordering, no scaling)."""
    coords, connect = _base_two_hex_geometry()
    # Use prime-like numbers to detect any silent reordering.
    stress = np.asarray(
        [
            [101.0, 103.0, 107.0, 109.0, 113.0, 127.0],
            [-131.0, 137.0, -139.0, 149.0, -151.0, 157.0],
        ],
        dtype=float,
    )
    frame = _make_frame(coords=coords, connect=connect, stress=stress)

    result = export_dynamic_result_mesh_from_frames(
        [frame],
        output_dir=tmp_path,
        case_id="PHASE24A-ORDER",
        field="von_mises",
        source_root="test_column_order",
    )
    payload = json.loads(result.result_mesh_path.read_text(encoding="utf-8"))
    frame_payload = payload["dynamicFrames"][0]
    # Pick first element from each source element; assert exact match.
    seen_indices: set[int] = set()
    for element in frame_payload["elements"]:
        idx = element["sourceElementIndex"]
        if idx in seen_indices:
            continue
        seen_indices.add(idx)
        t = element["stressTensor"]
        row = stress[idx]
        assert (t["sxx"], t["syy"], t["szz"], t["sxy"], t["syz"], t["sxz"]) == (
            row[0],
            row[1],
            row[2],
            row[3],
            row[4],
            row[5],
        ), f"column order mismatch on source element {idx}: tensor={t} row={row}"
    assert seen_indices == {0, 1}


def test_phase24a_stress_tensor_per_frame_independence(
    tmp_path: Path,
) -> None:
    """Two-frame run: tensor on frame 0 vs frame 1 must differ when input differs."""
    coords, connect = _base_two_hex_geometry()
    stress_a = np.asarray(
        [
            [10.0, 20.0, 30.0, 1.0, 2.0, 3.0],
            [40.0, 50.0, 60.0, 4.0, 5.0, 6.0],
        ],
        dtype=float,
    )
    stress_b = np.asarray(
        [
            [70.0, 80.0, 90.0, 7.0, 8.0, 9.0],
            [100.0, 110.0, 120.0, 10.0, 11.0, 12.0],
        ],
        dtype=float,
    )
    shifted = coords.copy()
    shifted[:8, 0] += 0.5
    frames = [
        _make_frame(
            coords=coords,
            connect=connect,
            stress=stress_a,
            source="model_00A001",
            timestep=0.0,
        ),
        _make_frame(
            coords=shifted,
            connect=connect,
            stress=stress_b,
            source="model_00A002",
            timestep=0.02,
        ),
    ]

    result = export_dynamic_result_mesh_from_frames(
        frames,
        output_dir=tmp_path,
        case_id="PHASE24A-FRAMES",
        field="von_mises",
        source_root="test_two_frames",
    )
    payload = json.loads(result.result_mesh_path.read_text(encoding="utf-8"))
    frame_0, frame_1 = payload["dynamicFrames"]

    # Source element 0 has different stress between frames; tensor must differ.
    tensor_0_frame0 = next(
        e["stressTensor"] for e in frame_0["elements"] if e["sourceElementIndex"] == 0
    )
    tensor_0_frame1 = next(
        e["stressTensor"] for e in frame_1["elements"] if e["sourceElementIndex"] == 0
    )
    assert tensor_0_frame0["sxx"] == 10.0
    assert tensor_0_frame1["sxx"] == 70.0
    assert tensor_0_frame0 != tensor_0_frame1


def test_phase24a_schema_version_unchanged_additive_field(
    tmp_path: Path,
) -> None:
    """schemaVersion stays 1 — stressTensor is optional, additive."""
    coords, connect = _base_two_hex_geometry()
    stress = np.asarray(
        [
            [1.0, 2.0, 3.0, 0.5, 0.25, 0.125],
            [4.0, 5.0, 6.0, 0.75, 0.5, 0.375],
        ],
        dtype=float,
    )
    frame = _make_frame(coords=coords, connect=connect, stress=stress)

    result = export_dynamic_result_mesh_from_frames(
        [frame],
        output_dir=tmp_path,
        case_id="PHASE24A-SCHEMA",
        field="von_mises",
        source_root="test_schema_additive",
    )
    payload = json.loads(result.result_mesh_path.read_text(encoding="utf-8"))
    # Schema stays at v1 — stressTensor is additive optional, no break.
    assert payload["schemaVersion"] == 1


def test_phase24a_no_tensor_in_top_level_elements_when_stress_none(
    tmp_path: Path,
) -> None:
    """Top-level payload.elements (frame 0 snapshot) also must omit stressTensor."""
    coords, connect = _base_two_hex_geometry()
    frame = _make_frame(coords=coords, connect=connect, stress=None)
    result = export_dynamic_result_mesh_from_frames(
        [frame],
        output_dir=tmp_path,
        case_id="PHASE24A-TOPLEVEL-NONE",
        field="von_mises",
        source_root="test_top_level_none",
    )
    payload = json.loads(result.result_mesh_path.read_text(encoding="utf-8"))
    assert "elements" in payload
    for element in payload["elements"]:
        assert "stressTensor" not in element


def test_phase24a_tensor_present_on_top_level_elements_when_stress_provided(
    tmp_path: Path,
) -> None:
    """Top-level payload.elements (frame 0 snapshot) must carry tensor too."""
    coords, connect = _base_two_hex_geometry()
    stress = np.asarray(
        [
            [11.0, 22.0, 33.0, 4.0, 5.0, 6.0],
            [44.0, 55.0, 66.0, 7.0, 8.0, 9.0],
        ],
        dtype=float,
    )
    frame = _make_frame(coords=coords, connect=connect, stress=stress)
    result = export_dynamic_result_mesh_from_frames(
        [frame],
        output_dir=tmp_path,
        case_id="PHASE24A-TOPLEVEL-PRESENT",
        field="von_mises",
        source_root="test_top_level_present",
    )
    payload = json.loads(result.result_mesh_path.read_text(encoding="utf-8"))
    assert "elements" in payload
    seen_count = 0
    for element in payload["elements"]:
        assert "stressTensor" in element
        assert set(element["stressTensor"].keys()) == {
            "sxx",
            "syy",
            "szz",
            "sxy",
            "syz",
            "sxz",
        }
        seen_count += 1
    assert seen_count > 0
