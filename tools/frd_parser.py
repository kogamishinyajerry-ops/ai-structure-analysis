"""CalculiX `.frd` result parser and approval-grade metric helpers."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


def _parse_nodes(lines: list[str], start: int) -> tuple[dict[int, np.ndarray], int]:
    """Parse a node block starting after a ``2C`` header line."""
    nodes: dict[int, np.ndarray] = {}
    i = start
    while i < len(lines):
        line = lines[i]
        if line.startswith(" -3"):
            return nodes, i + 1
        if line.startswith(" -1"):
            try:
                nid = int(line[3:13])
                x = float(line[13:25])
                y = float(line[25:37])
                z = float(line[37:49])
            except (ValueError, IndexError):
                i += 1
                continue
            nodes[nid] = np.array([x, y, z], dtype=float)
        i += 1
    return nodes, i


def _field_name_from_header(header: str, component_names: list[str]) -> str:
    normalized = header.upper()
    if "DISP" in normalized:
        return "displacement"
    if "STRESS" in normalized:
        return "stress"
    if "NDTEMP" in normalized or "TEMP" in normalized:
        return "temperature"
    if "FORC" in normalized:
        return "force"
    return component_names[0].lower() if component_names else "field"


def _parse_field_block(
    lines: list[str],
    start: int,
) -> tuple[tuple[str, dict[str, Any]] | None, int]:
    """Parse a single results field block."""
    header = lines[start] if start < len(lines) else ""
    if not re.search(r"100C[A-Z]*\s+\d+", header):
        return None, start + 1

    component_names: list[str] = []
    i = start + 1
    while i < len(lines) and lines[i].startswith(" -4"):
        name_part = lines[i][5:17].strip()
        if name_part:
            component_names.append(name_part)
        i += 1

    values: dict[int, np.ndarray] = {}
    while i < len(lines):
        line = lines[i]
        if line.startswith(" -3"):
            i += 1
            break
        if line.startswith(" -1"):
            try:
                nid = int(line[3:13])
                components: list[float] = []
                pos = 13
                while pos + 12 <= len(line):
                    components.append(float(line[pos : pos + 12]))
                    pos += 12
            except (ValueError, IndexError):
                i += 1
                continue
            values[nid] = np.array(components, dtype=float)
        i += 1

    field_name = _field_name_from_header(header, component_names)
    return (
        field_name,
        {
            "name": field_name,
            "component_names": component_names,
            "values": values,
        },
    ), i


def parse_frd(frd_path: Path) -> dict[str, Any]:
    """Parse an ASCII CalculiX `.frd` file into node and field dictionaries."""
    if not frd_path.exists():
        raise FileNotFoundError(f"FRD file not found: {frd_path}")

    text = frd_path.read_text(errors="replace")
    lines = text.splitlines()

    nodes: dict[int, np.ndarray] = {}
    fields: dict[str, dict[str, Any]] = {}

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("2C"):
            parsed_nodes, i = _parse_nodes(lines, i + 1)
            nodes.update(parsed_nodes)
            continue
        if " 100C" in line:
            parsed_field, i = _parse_field_block(lines, i)
            if parsed_field:
                field_name, field_payload = parsed_field
                fields[field_name] = field_payload
            continue
        i += 1

    logger.info("Parsed FRD: %d nodes, %d fields", len(nodes), len(fields))
    return {"nodes": nodes, "fields": fields}


def _values_from_field_data(field_data: Any) -> dict[int, np.ndarray]:
    raw_values = field_data.get("values", {}) if isinstance(field_data, dict) else field_data

    if isinstance(raw_values, dict):
        return {
            int(node_id): np.asarray(value, dtype=float) for node_id, value in raw_values.items()
        }
    if isinstance(raw_values, list):
        return {
            index + 1: np.atleast_1d(np.asarray(value, dtype=float))
            for index, value in enumerate(raw_values)
        }
    return {}


def _lookup_field(parsed: dict[str, Any], field_name: str) -> dict[str, Any] | None:
    fields = parsed.get("fields")
    if isinstance(fields, dict):
        value = fields.get(field_name)
        if value is None:
            return None
        return value if isinstance(value, dict) else {"values": value}
    if isinstance(fields, list):
        for item in fields:
            if isinstance(item, dict) and item.get("name") == field_name:
                return item
    return None


def _metric_key(field_name: str, field_data: dict[str, Any], values: dict[int, np.ndarray]) -> str:
    component_count = max((len(arr) for arr in values.values()), default=0)
    component_names = [str(name).upper() for name in field_data.get("component_names", [])]
    if field_name == "stress" and (
        component_count >= 6 or {"SXX", "SYY", "SZZ"} <= set(component_names)
    ):
        return "von_mises"
    return field_name


def _scalar_metric(field_name: str, metric_key: str, vector: np.ndarray) -> float:
    data = np.atleast_1d(vector.astype(float))
    if field_name == "stress" and metric_key == "von_mises" and len(data) >= 6:
        sxx, syy, szz, sxy, syz, szx = data[:6]
        return float(
            np.sqrt(
                0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
                + 3.0 * (sxy**2 + syz**2 + szx**2)
            )
        )
    return float(np.linalg.norm(data))


def extract_field_extremes(parsed: dict[str, Any], field_name: str) -> dict[str, Any]:
    """Extract approval-grade min/max statistics for a named field."""
    field_data = _lookup_field(parsed, field_name)
    if field_data is None:
        return {
            "field": field_name,
            "metric": field_name,
            "max_magnitude": None,
            "max_node": None,
            "min_magnitude": None,
            "min_node": None,
        }

    values = _values_from_field_data(field_data)
    metric_key = _metric_key(field_name, field_data, values)
    if not values:
        return {
            "field": field_name,
            "metric": metric_key,
            "max_magnitude": 0.0,
            "max_node": None,
            "min_magnitude": 0.0,
            "min_node": None,
        }

    max_magnitude = -float("inf")
    min_magnitude = float("inf")
    max_node = None
    min_node = None

    for node_id, vector in values.items():
        magnitude = _scalar_metric(field_name, metric_key, vector)
        if magnitude > max_magnitude:
            max_magnitude = magnitude
            max_node = node_id
        if magnitude < min_magnitude:
            min_magnitude = magnitude
            min_node = node_id

    return {
        "field": field_name,
        "metric": metric_key,
        "max_magnitude": max_magnitude,
        "max_node": max_node,
        "min_magnitude": min_magnitude,
        "min_node": min_node,
    }
