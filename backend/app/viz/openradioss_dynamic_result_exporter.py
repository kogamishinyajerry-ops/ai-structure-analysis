"""OpenRadioss dynamic result exporter for Text-to-CAE-style viewers.

Tier 1 engineering-candidate infrastructure only. This module turns
solver-emitted OpenRadioss animation frames into:

* ``result_mesh.json`` with ``dynamicFrames`` for browser playback.
* optional per-frame ASCII ``.vtu`` files plus a compact VTU manifest.

The exporter uses real OpenRadioss part geometry when it is present. It does
not synthesize a projectile mesh, does not hide deleted elements, and does not
promote the output to signed validation.
"""

from __future__ import annotations

import gzip
import json
import math
import re
import shutil
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final, Literal
from xml.sax.saxutils import escape

import numpy as np

CLAIM_TIER: Final[str] = "Tier 1 engineering candidate"
CLAIM_BOUNDARY: Final[str] = (
    "Tier 1 engineering candidate; not signed validation; not benchmark agreement"
)
RESULT_SCHEMA_VERSION: Final[int] = 1
VTU_MANIFEST_SCHEMA_VERSION: Final[str] = "openradioss-dynamic-vtu-manifest.v1"

DynamicField = Literal["pressure_proxy", "pressure_delta", "von_mises", "plastic_strain"]

_ANIM_RE = re.compile(r"A\d{3,4}(?:\.gz)?$")
_VTK_TRIANGLE: Final[int] = 5
_VTK_QUAD: Final[int] = 9
_VTK_TETRA: Final[int] = 10
_VTK_HEXAHEDRON: Final[int] = 12

_HEX_FACE_NODE_INDICES: Final[tuple[tuple[int, ...], ...]] = (
    (0, 1, 2, 3),
    (4, 7, 6, 5),
    (0, 4, 5, 1),
    (1, 5, 6, 2),
    (2, 6, 7, 3),
    (3, 7, 4, 0),
)
_TET_FACE_NODE_INDICES: Final[tuple[tuple[int, ...], ...]] = (
    (0, 2, 1),
    (0, 1, 3),
    (1, 2, 3),
    (2, 0, 3),
)


class DynamicResultExportError(RuntimeError):
    """Raised when frames cannot be exported to browser-ready artifacts."""


@dataclass(frozen=True)
class DynamicFrameData:
    """One OpenRadioss animation frame after Vortex-Radioss extraction."""

    source: str
    timestep: float
    coords: np.ndarray
    element_node_indexes: np.ndarray
    element_ids: np.ndarray
    part_ids: np.ndarray
    alive: np.ndarray
    stress: np.ndarray | None = None
    plastic_strain: np.ndarray | None = None


@dataclass(frozen=True)
class DynamicExportResult:
    result_mesh_path: Path
    vtu_manifest_path: Path
    frame_count: int


def discover_animation_files(
    run_data_dir: Path,
    *,
    rootname: str | None = None,
) -> tuple[Path, ...]:
    """Return OpenRadioss ``A###`` animation files in deterministic order."""

    if not run_data_dir.is_dir():
        raise DynamicResultExportError(f"run data dir is not a directory: {run_data_dir}")

    files: list[Path] = []
    prefix = f"{rootname}A" if rootname else None
    for path in run_data_dir.iterdir():
        if not path.is_file() or not _ANIM_RE.search(path.name):
            continue
        if prefix and not path.name.startswith(prefix):
            continue
        files.append(path)
    return tuple(sorted(files, key=_animation_sort_key))


def read_openradioss_dynamic_frames(anim_files: Sequence[Path]) -> list[DynamicFrameData]:
    """Read OpenRadioss animation files via Vortex-Radioss."""

    if not anim_files:
        raise DynamicResultExportError("anim_files must not be empty")

    from vortex_radioss.animtod3plot.RadiossReader import RadiossReader

    frames: list[DynamicFrameData] = []
    for src in anim_files:
        path = _ungzip_if_needed(src)
        try:
            frames.append(_extract_frame(RadiossReader(str(path)), source=str(src)))
        finally:
            if path != src:
                path.unlink(missing_ok=True)
    return frames


def export_dynamic_result_mesh(
    *,
    run_data_dir: Path,
    output_dir: Path,
    case_id: str,
    field: DynamicField = "von_mises",
    rootname: str | None = "model_00",
    source_root: str | None = None,
    write_vtu: bool = True,
    model_metadata: Mapping[str, Any] | None = None,
) -> DynamicExportResult:
    """Read OpenRadioss A-frames and write dynamic viewer artifacts."""

    anim_files = discover_animation_files(run_data_dir, rootname=rootname)
    if not anim_files:
        suffix = f" for rootname {rootname!r}" if rootname else ""
        raise DynamicResultExportError(f"no OpenRadioss A-files found under {run_data_dir}{suffix}")
    return export_dynamic_result_mesh_from_frames(
        read_openradioss_dynamic_frames(anim_files),
        output_dir=output_dir,
        case_id=case_id,
        field=field,
        source_root=source_root or str(run_data_dir),
        write_vtu=write_vtu,
        model_metadata=model_metadata,
    )


def export_dynamic_result_mesh_from_frames(
    frames: Sequence[DynamicFrameData],
    *,
    output_dir: Path,
    case_id: str,
    field: DynamicField = "von_mises",
    source_root: str | None = None,
    write_vtu: bool = True,
    model_metadata: Mapping[str, Any] | None = None,
) -> DynamicExportResult:
    """Write ``result_mesh.json`` and optional VTU sidecars from frame data."""

    if field not in {"pressure_proxy", "pressure_delta", "von_mises", "plastic_strain"}:
        raise DynamicResultExportError(f"unsupported dynamic field: {field}")
    if not frames:
        raise DynamicResultExportError("frames must not be empty")

    normalised = [_normalise_frame(frame) for frame in frames]
    _assert_frame_topology_stable(normalised)

    output_dir.mkdir(parents=True, exist_ok=True)
    reference_coords = normalised[0].coords
    model_tree = _build_model_tree(case_id, normalised[0], model_metadata or {})
    dynamic_frames = [
        _build_json_frame(
            frame,
            frame_index=index,
            reference_coords=reference_coords,
            field=field,
        )
        for index, frame in enumerate(normalised)
    ]
    overall_ranges = _merge_field_ranges(frame["fieldRanges"] for frame in dynamic_frames)

    vtu_manifest_path = output_dir / "vtu_manifest.json"
    vtu_status: dict[str, Any] = {"status": "unavailable"}
    if write_vtu:
        vtu_manifest_path = _write_vtu_sidecars(
            normalised,
            output_dir=output_dir,
            case_id=case_id,
            field=field,
            reference_coords=reference_coords,
        )
        vtu_status = {
            "status": "available",
            "path": vtu_manifest_path.name,
            "schema_version": VTU_MANIFEST_SCHEMA_VERSION,
        }
    else:
        vtu_manifest_path.write_text(
            json.dumps(
                {
                    "schema_version": VTU_MANIFEST_SCHEMA_VERSION,
                    "case_id": case_id,
                    "field": field,
                    "frames": [],
                    "status": "disabled",
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        vtu_status = {"status": "disabled", "path": vtu_manifest_path.name}

    payload = {
        "schemaVersion": RESULT_SCHEMA_VERSION,
        "source": {
            "solver": "OpenRadioss",
            "reader": "vortex-radioss",
            "root": source_root or "",
            "frameCount": len(normalised),
        },
        "analysisType": "dynamic",
        "claimTier": CLAIM_TIER,
        "claimBoundary": CLAIM_BOUNDARY,
        "caseId": case_id,
        "generatedAtUtc": datetime.now(UTC).isoformat(),
        "field": field,
        "fieldLabel": _field_label(field),
        "fieldSource": _field_source(field),
        "fieldRanges": overall_ranges,
        "modelTree": model_tree,
        "nodes": dynamic_frames[0]["nodes"],
        "elements": dynamic_frames[0]["elements"],
        "frame": dynamic_frames[0]["frame"],
        "timeMs": dynamic_frames[0]["timeMs"],
        "deformationScale": 1.0,
        "elementType": "solver_surface",
        "dynamicFrames": dynamic_frames,
        "artifacts": {
            "vtuManifest": vtu_status,
        },
        "limitations": [
            "Tier 1 engineering candidate only",
            "not signed validation",
            "not benchmark agreement",
            "pressure fields, when selected, are stress-derived visual proxies",
        ],
    }

    result_mesh_path = output_dir / "result_mesh.json"
    result_mesh_path.write_text(
        json.dumps(payload, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    return DynamicExportResult(
        result_mesh_path=result_mesh_path,
        vtu_manifest_path=vtu_manifest_path,
        frame_count=len(normalised),
    )


def _normalise_frame(frame: DynamicFrameData) -> DynamicFrameData:
    coords = np.asarray(frame.coords, dtype=float)
    if coords.ndim != 2 or coords.shape[1] != 3:
        raise DynamicResultExportError(f"{frame.source}: coords must have shape (n, 3)")

    element_node_indexes = np.asarray(frame.element_node_indexes, dtype=int)
    if element_node_indexes.ndim != 2:
        raise DynamicResultExportError(
            f"{frame.source}: element_node_indexes must be a 2D array"
        )
    element_count = int(element_node_indexes.shape[0])
    element_ids = _coerce_1d_int(frame.element_ids, element_count, "element_ids", frame.source)
    part_ids = _coerce_1d_int(frame.part_ids, element_count, "part_ids", frame.source)
    alive = np.asarray(frame.alive, dtype=bool).reshape(-1)
    if alive.size != element_count:
        raise DynamicResultExportError(
            f"{frame.source}: alive length {alive.size} does not match "
            f"element count {element_count}"
        )
    stress = None if frame.stress is None else np.asarray(frame.stress, dtype=float)
    if stress is not None and stress.shape[0] != element_count:
        raise DynamicResultExportError(
            f"{frame.source}: stress rows {stress.shape[0]} do not match "
            f"element count {element_count}"
        )
    plastic_strain = None
    if frame.plastic_strain is not None:
        plastic_strain = np.asarray(frame.plastic_strain, dtype=float).reshape(-1)
        if plastic_strain.size != element_count:
            raise DynamicResultExportError(
                f"{frame.source}: plastic_strain length {plastic_strain.size} "
                f"does not match element count {element_count}"
            )

    return DynamicFrameData(
        source=frame.source,
        timestep=float(frame.timestep),
        coords=coords,
        element_node_indexes=element_node_indexes,
        element_ids=element_ids,
        part_ids=part_ids,
        alive=alive,
        stress=stress,
        plastic_strain=plastic_strain,
    )


def _coerce_1d_int(raw: np.ndarray, expected: int, name: str, source: str) -> np.ndarray:
    arr = np.asarray(raw, dtype=int).reshape(-1)
    if arr.size != expected:
        raise DynamicResultExportError(
            f"{source}: {name} length {arr.size} does not match element count {expected}"
        )
    return arr


def _assert_frame_topology_stable(frames: Sequence[DynamicFrameData]) -> None:
    ref = frames[0]
    ref_shape = ref.coords.shape
    ref_connect = ref.element_node_indexes
    ref_elements = ref.element_ids
    for frame in frames[1:]:
        if frame.coords.shape != ref_shape:
            raise DynamicResultExportError(
                f"{frame.source}: node count changed from {ref_shape[0]} to {frame.coords.shape[0]}"
            )
        if frame.element_node_indexes.shape != ref_connect.shape:
            raise DynamicResultExportError(
                f"{frame.source}: element topology shape changed from "
                f"{ref_connect.shape} to {frame.element_node_indexes.shape}"
            )
        if not np.array_equal(frame.element_node_indexes, ref_connect):
            raise DynamicResultExportError(f"{frame.source}: element connectivity changed mid-run")
        if not np.array_equal(frame.element_ids, ref_elements):
            raise DynamicResultExportError(f"{frame.source}: element IDs changed mid-run")


def _extract_frame(reader: Any, *, source: str) -> DynamicFrameData:
    arrays = reader.arrays
    coords = np.asarray(arrays["node_coordinates"], dtype=float)
    node_indexes = np.asarray(arrays["element_solid_node_indexes"], dtype=int)
    element_count = int(node_indexes.shape[0])
    return DynamicFrameData(
        source=source,
        timestep=_first_float(arrays.get("timesteps")),
        coords=coords,
        element_node_indexes=node_indexes,
        element_ids=np.asarray(
            arrays.get("element_solid_ids", np.arange(1, element_count + 1)),
            dtype=int,
        ),
        part_ids=np.asarray(
            arrays.get("element_solid_part_ids", np.zeros(element_count)),
            dtype=int,
        ),
        alive=np.asarray(arrays.get("element_solid_is_alive", np.ones(element_count)), dtype=bool),
        stress=(
            None
            if arrays.get("element_solid_stress") is None
            else np.asarray(arrays.get("element_solid_stress"), dtype=float)
        ),
        plastic_strain=(
            None
            if arrays.get("element_solid_plastic_strain") is None
            else np.asarray(arrays.get("element_solid_plastic_strain"), dtype=float)
        ),
    )


def _build_model_tree(
    case_id: str,
    frame: DynamicFrameData,
    model_metadata: Mapping[str, Any],
) -> dict[str, Any]:
    children: list[dict[str, Any]] = []
    for part_id in _ordered_part_ids(frame.part_ids):
        mask = frame.part_ids == part_id
        role = _part_role(int(part_id))
        children.append(
            {
                "id": f"part-{int(part_id)}",
                "label": _part_label(int(part_id), model_metadata),
                "kind": "part",
                "partId": int(part_id),
                "partRole": role,
                "elementCount": int(mask.sum()),
                "aliveElementCount": int(np.logical_and(mask, frame.alive).sum()),
                "fieldRole": "projectile_geometry" if role == "projectile" else "contour_cloud",
            }
        )
    return {
        "id": "assembly",
        "label": case_id,
        "kind": "assembly",
        "children": children,
    }


def _build_json_frame(
    frame: DynamicFrameData,
    *,
    frame_index: int,
    reference_coords: np.ndarray,
    field: DynamicField,
) -> dict[str, Any]:
    displacement = frame.coords - reference_coords
    disp_mag = np.linalg.norm(displacement, axis=1)
    node_part_roles = _node_part_roles(frame)
    values = _element_field_values(frame, field)
    faces = _surface_faces(frame)

    nodes = [
        {
            "label": index + 1,
            "coordinates": _float_list(reference_coords[index]),
            "displacement": _float_list(displacement[index]),
            "deformed": _float_list(frame.coords[index]),
            "partRoles": sorted(node_part_roles.get(index, {"unknown"})),
        }
        for index in range(frame.coords.shape[0])
    ]

    elements: list[dict[str, Any]] = []
    for label, face in enumerate(faces, start=1):
        element_index = face["element_index"]
        value = _safe_float(values[element_index])
        part_id = int(frame.part_ids[element_index])
        role = _part_role(part_id)
        element = {
            "label": label,
            "type": "S4R" if len(face["nodes"]) == 4 else "S3R",
            "connectivity": [int(node_index) + 1 for node_index in face["nodes"]],
            "sourceElement": int(frame.element_ids[element_index]),
            "sourceElementIndex": int(element_index),
            "partId": part_id,
            "partRole": role,
            "alive": bool(frame.alive[element_index]),
            "field": field,
            "value": value,
            "visualOnly": False,
        }
        if field == "von_mises":
            element["mises"] = value
        elements.append(element)

    ranges = _field_ranges(values, alive=frame.alive, max_displacement=float(disp_mag.max()))
    return {
        "frame": frame_index,
        "sourceFrame": frame_index,
        "source": frame.source,
        "timeMs": _safe_float(frame.timestep),
        "deformationScale": 1.0,
        "field": field,
        "fieldLabel": _field_label(field),
        "elementType": "solver_surface",
        "nodes": nodes,
        "elements": elements,
        "fieldRanges": ranges,
        "elementStatus": [
            {
                "sourceElement": int(element_id),
                "partId": int(part_id),
                "partRole": _part_role(int(part_id)),
                "alive": bool(alive),
            }
            for element_id, part_id, alive in zip(
                frame.element_ids, frame.part_ids, frame.alive, strict=True
            )
        ],
    }


def _surface_faces(frame: DynamicFrameData) -> list[dict[str, Any]]:
    faces: dict[tuple[int, tuple[int, ...]], dict[str, Any]] = {}
    internal: set[tuple[int, tuple[int, ...]]] = set()
    for element_index, row in enumerate(frame.element_node_indexes.tolist()):
        part_id = int(frame.part_ids[element_index])
        for local_face in _face_indices_for_row(row):
            nodes = tuple(int(row[index]) for index in local_face)
            key = (part_id, tuple(sorted(nodes)))
            if key in faces:
                internal.add(key)
                faces.pop(key, None)
            elif key not in internal:
                faces[key] = {"element_index": element_index, "nodes": nodes}
    return list(faces.values())


def _face_indices_for_row(row: Sequence[int]) -> tuple[tuple[int, ...], ...]:
    if len(row) == 8:
        return _HEX_FACE_NODE_INDICES
    if len(row) == 4:
        return _TET_FACE_NODE_INDICES
    if len(row) == 3:
        return ((0, 1, 2),)
    raise DynamicResultExportError(
        f"unsupported element connectivity length {len(row)} for Text-to-CAE surface export"
    )


def _node_part_roles(frame: DynamicFrameData) -> dict[int, set[str]]:
    out: dict[int, set[str]] = {}
    for row, part_id in zip(frame.element_node_indexes, frame.part_ids, strict=True):
        role = _part_role(int(part_id))
        for node_index in row:
            out.setdefault(int(node_index), set()).add(role)
    return out


def _write_vtu_sidecars(
    frames: Sequence[DynamicFrameData],
    *,
    output_dir: Path,
    case_id: str,
    field: DynamicField,
    reference_coords: np.ndarray,
) -> Path:
    vtu_dir = output_dir / "vtu"
    vtu_dir.mkdir(parents=True, exist_ok=True)
    frame_records: list[dict[str, Any]] = []
    for index, frame in enumerate(frames):
        relpath = Path("vtu") / f"{case_id}_frame_{index:04d}.vtu"
        path = output_dir / relpath
        _write_ascii_vtu(
            frame,
            path,
            field=field,
            reference_coords=reference_coords,
        )
        frame_records.append(
            {
                "frame": index,
                "source": frame.source,
                "time_ms": _safe_float(frame.timestep),
                "vtu_relpath": str(relpath),
                "n_points": int(frame.coords.shape[0]),
                "n_cells": int(frame.element_node_indexes.shape[0]),
            }
        )

    manifest = {
        "schema_version": VTU_MANIFEST_SCHEMA_VERSION,
        "case_id": case_id,
        "claim_boundary": CLAIM_BOUNDARY,
        "field": field,
        "field_label": _field_label(field),
        "frames": frame_records,
    }
    manifest_path = output_dir / "vtu_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


def _write_ascii_vtu(
    frame: DynamicFrameData,
    path: Path,
    *,
    field: DynamicField,
    reference_coords: np.ndarray,
) -> None:
    values = _element_field_values(frame, field)
    displacement = frame.coords - reference_coords
    connectivity: list[int] = []
    offsets: list[int] = []
    types: list[int] = []
    offset = 0
    for row in frame.element_node_indexes.tolist():
        vtk_type = _vtk_type_for_connectivity_len(len(row))
        connectivity.extend(int(value) for value in row)
        offset += len(row)
        offsets.append(offset)
        types.append(vtk_type)

    text = "\n".join(
        [
            '<?xml version="1.0"?>',
            '<VTKFile type="UnstructuredGrid" version="0.1" byte_order="LittleEndian">',
            "  <UnstructuredGrid>",
            (
                f'    <Piece NumberOfPoints="{frame.coords.shape[0]}" '
                f'NumberOfCells="{frame.element_node_indexes.shape[0]}">'
            ),
            '      <PointData Vectors="displacement">',
            (
                '        <DataArray type="Float32" Name="displacement" '
                f'NumberOfComponents="3" format="ascii">{_format_floats(displacement)}</DataArray>'
            ),
            "      </PointData>",
            f'      <CellData Scalars="{escape(field)}">',
            (
                '        <DataArray type="Int32" Name="element_id" format="ascii">'
                f"{_format_ints(frame.element_ids)}</DataArray>"
            ),
            (
                '        <DataArray type="Int32" Name="part_id" format="ascii">'
                f"{_format_ints(frame.part_ids)}</DataArray>"
            ),
            (
                '        <DataArray type="UInt8" Name="alive" format="ascii">'
                f"{_format_ints(frame.alive.astype(np.uint8))}</DataArray>"
            ),
            (
                f'        <DataArray type="Float32" Name="{escape(field)}" format="ascii">'
                f"{_format_floats(values)}</DataArray>"
            ),
            "      </CellData>",
            "      <Points>",
            (
                '        <DataArray type="Float32" NumberOfComponents="3" format="ascii">'
                f"{_format_floats(frame.coords)}</DataArray>"
            ),
            "      </Points>",
            "      <Cells>",
            (
                '        <DataArray type="Int32" Name="connectivity" format="ascii">'
                f"{_format_ints(connectivity)}</DataArray>"
            ),
            (
                '        <DataArray type="Int32" Name="offsets" format="ascii">'
                f"{_format_ints(offsets)}</DataArray>"
            ),
            (
                '        <DataArray type="UInt8" Name="types" format="ascii">'
                f"{_format_ints(types)}</DataArray>"
            ),
            "      </Cells>",
            "    </Piece>",
            "  </UnstructuredGrid>",
            "</VTKFile>",
            "",
        ]
    )
    path.write_text(text, encoding="utf-8")


def _element_field_values(frame: DynamicFrameData, field: DynamicField) -> np.ndarray:
    if field in {"pressure_proxy", "pressure_delta"}:
        if frame.stress is None or frame.stress.shape[1] < 3:
            return np.zeros(frame.element_node_indexes.shape[0], dtype=float)
        pressure = np.abs((frame.stress[:, 0] + frame.stress[:, 1] + frame.stress[:, 2]) / 3.0)
        if field == "pressure_delta":
            plate_alive = np.logical_and(frame.part_ids == 2, frame.alive)
            baseline = float(np.median(pressure[plate_alive])) if bool(np.any(plate_alive)) else 0.0
            return np.abs(pressure - baseline)
        return np.asarray(pressure, dtype=float)
    if field == "von_mises":
        if frame.stress is None or frame.stress.shape[1] < 6:
            return np.zeros(frame.element_node_indexes.shape[0], dtype=float)
        sxx, syy, szz, sxy, syz, sxz = [frame.stress[:, i] for i in range(6)]
        return np.sqrt(
            0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
            + 3.0 * (sxy**2 + syz**2 + sxz**2)
        )
    if field == "plastic_strain":
        if frame.plastic_strain is None:
            return np.zeros(frame.element_node_indexes.shape[0], dtype=float)
        return np.asarray(frame.plastic_strain, dtype=float).reshape(-1)
    raise DynamicResultExportError(f"unsupported field {field}")


def _field_ranges(
    values: np.ndarray,
    *,
    alive: np.ndarray,
    max_displacement: float,
) -> dict[str, float]:
    finite = np.asarray([_safe_float(value) for value in values], dtype=float)
    live = finite[np.asarray(alive, dtype=bool)] if finite.size else finite
    basis = live if live.size else finite
    if basis.size == 0:
        value_min = 0.0
        value_max = 1.0
    else:
        value_min = float(np.min(basis))
        value_max = float(np.max(basis))
        if value_max <= value_min:
            value_max = value_min + 1.0
    return {
        "valueMin": _safe_float(value_min),
        "valueMax": _safe_float(value_max),
        "misesMin": _safe_float(value_min),
        "misesMax": _safe_float(value_max),
        "maxDisplacement": _safe_float(max_displacement),
    }


def _merge_field_ranges(ranges: Sequence[Mapping[str, float]]) -> dict[str, float]:
    range_items = list(ranges)
    value_min = min(float(item["valueMin"]) for item in range_items)
    value_max = max(float(item["valueMax"]) for item in range_items)
    max_displacement = max(float(item["maxDisplacement"]) for item in range_items)
    return {
        "valueMin": _safe_float(value_min),
        "valueMax": _safe_float(value_max),
        "misesMin": _safe_float(value_min),
        "misesMax": _safe_float(value_max),
        "maxDisplacement": _safe_float(max_displacement),
    }


def _ordered_part_ids(part_ids: np.ndarray) -> list[int]:
    ids = {int(value) for value in part_ids.tolist()}
    return sorted(ids, key=lambda part_id: (_part_order(part_id), part_id))


def _part_order(part_id: int) -> int:
    if _part_role(part_id) == "projectile":
        return 0
    if _part_role(part_id) == "plate":
        return 1
    return 2


def _part_role(part_id: int) -> str:
    if part_id == 1:
        return "projectile"
    if part_id == 2:
        return "plate"
    return f"part_{part_id}"


def _part_label(part_id: int, model_metadata: Mapping[str, Any]) -> str:
    parts = model_metadata.get("parts")
    if isinstance(parts, Mapping):
        match = parts.get(str(part_id)) or parts.get(part_id)
        if isinstance(match, Mapping) and match.get("label"):
            return str(match["label"])
        if isinstance(match, str):
            return match
    if part_id == 1:
        return "Projectile"
    if part_id == 2:
        return "Plate"
    return f"Part {part_id}"


def _field_label(field: DynamicField) -> str:
    if field == "pressure_proxy":
        return "pressure proxy: |mean normal stress|"
    if field == "pressure_delta":
        return "pressure proxy delta from alive plate median"
    if field == "von_mises":
        return "von Mises stress"
    if field == "plastic_strain":
        return "plastic strain"
    return str(field)


def _field_source(field: DynamicField) -> str:
    if field == "plastic_strain":
        return "element_solid_plastic_strain"
    if field.startswith("pressure"):
        return "element_solid_stress hydrostatic proxy"
    return "element_solid_stress"


def _vtk_type_for_connectivity_len(length: int) -> int:
    if length == 8:
        return _VTK_HEXAHEDRON
    if length == 4:
        return _VTK_TETRA
    if length == 3:
        return _VTK_TRIANGLE
    raise DynamicResultExportError(f"unsupported VTU connectivity length: {length}")


def _first_float(raw: Any) -> float:
    arr = np.asarray(raw, dtype=float).reshape(-1)
    if arr.size == 0:
        return 0.0
    return _safe_float(arr[0])


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    if math.isnan(number) or math.isinf(number):
        return fallback
    return number


def _float_list(values: Sequence[float] | np.ndarray) -> list[float]:
    return [_safe_float(value) for value in np.asarray(values, dtype=float).reshape(-1).tolist()]


def _format_floats(values: Sequence[float] | np.ndarray) -> str:
    flat = np.asarray(values, dtype=float).reshape(-1)
    return " ".join(f"{_safe_float(value):.9g}" for value in flat)


def _format_ints(values: Sequence[int] | np.ndarray) -> str:
    flat = np.asarray(values, dtype=int).reshape(-1)
    return " ".join(str(int(value)) for value in flat)


def _animation_sort_key(path: Path) -> tuple[str, int, str]:
    name = path.name
    ungz = name[:-3] if name.endswith(".gz") else name
    marker = ungz.rfind("A")
    prefix = ungz[:marker] if marker >= 0 else ungz
    suffix = ungz[marker + 1 :] if marker >= 0 else "0"
    step = int(suffix) if suffix.isdigit() else 0
    return (prefix, step, name)


def _ungzip_if_needed(src: Path) -> Path:
    if src.suffix != ".gz":
        return src
    with tempfile.NamedTemporaryFile(suffix=".A001", delete=False) as tmp_file:
        tmp = Path(tmp_file.name)
    with gzip.open(src, "rb") as fin, tmp.open("wb") as fout:
        shutil.copyfileobj(fin, fout)
    return tmp


__all__ = [
    "CLAIM_BOUNDARY",
    "CLAIM_TIER",
    "DynamicExportResult",
    "DynamicFrameData",
    "DynamicResultExportError",
    "export_dynamic_result_mesh",
    "export_dynamic_result_mesh_from_frames",
    "discover_animation_files",
    "read_openradioss_dynamic_frames",
]
