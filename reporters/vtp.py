"""Minimal VTP exporter for ParaView-compatible point-cloud inspection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np


def _format_array(values: list[float] | list[int]) -> str:
    return " ".join(f"{float(value):.12g}" for value in values)


def export_vtp(results: dict[str, Any], output_dir: Path) -> Path:
    """Export parsed FRD nodes and point-data arrays as an ASCII `.vtp` file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    vtp_path = output_dir / "results.vtp"

    nodes: dict[int, np.ndarray] = results.get("nodes", {})
    fields: dict[str, dict[str, Any]] = results.get("fields", {})
    node_ids = sorted(nodes)

    points: list[float] = []
    connectivity: list[int] = []
    offsets: list[int] = []
    point_data_blocks: list[str] = []

    for index, node_id in enumerate(node_ids):
        coords = np.asarray(nodes[node_id], dtype=float)
        padded = list(coords[:3]) + [0.0] * max(0, 3 - len(coords))
        points.extend(padded[:3])
        connectivity.append(index)
        offsets.append(index + 1)

    for field_name, payload in fields.items():
        values = payload.get("values", {})
        component_names = payload.get("component_names", [])
        component_count = max(
            (len(np.atleast_1d(values[node_id])) for node_id in node_ids),
            default=1,
        )
        flattened: list[float] = []
        for node_id in node_ids:
            raw_value = values.get(node_id, np.zeros(component_count))
            vector = np.atleast_1d(np.asarray(raw_value, dtype=float))
            padded = list(vector[:component_count]) + [0.0] * max(0, component_count - len(vector))
            flattened.extend(padded[:component_count])
        names_attr = f' Name="{field_name}"'
        comps_attr = f' NumberOfComponents="{component_count}"' if component_count > 1 else ""
        point_data_blocks.append(
            "        "
            f'<DataArray type="Float64"{names_attr}{comps_attr} format="ascii">'
            f"{_format_array(flattened)}</DataArray>"
        )
        if field_name == "stress" and component_names:
            point_data_blocks.append(f"        <!-- components: {', '.join(component_names)} -->")

    connectivity_text = " ".join(str(value) for value in connectivity)
    offsets_text = " ".join(str(value) for value in offsets)
    points_text = _format_array(points)
    xml_lines = [
        '<?xml version="1.0"?>',
        '<VTKFile type="PolyData" version="0.1" byte_order="LittleEndian">',
        "  <PolyData>",
        (
            f'    <Piece NumberOfPoints="{len(node_ids)}" NumberOfVerts="{len(node_ids)}" '
            'NumberOfLines="0" NumberOfStrips="0" NumberOfPolys="0">'
        ),
        "      <Points>",
        (
            '        <DataArray type="Float64" NumberOfComponents="3" format="ascii">'
            f"{points_text}</DataArray>"
        ),
        "      </Points>",
        "      <Verts>",
        (
            '        <DataArray type="Int32" Name="connectivity" format="ascii">'
            f"{connectivity_text}</DataArray>"
        ),
        (
            '        <DataArray type="Int32" Name="offsets" format="ascii">'
            f"{offsets_text}</DataArray>"
        ),
        "      </Verts>",
        "      <PointData>",
        *point_data_blocks,
        "      </PointData>",
        "    </Piece>",
        "  </PolyData>",
        "</VTKFile>",
        "",
    ]
    vtp_path.write_text("\n".join(xml_lines), encoding="utf-8")
    return vtp_path
