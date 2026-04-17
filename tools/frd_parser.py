"""CalculiX .frd result file parser.

Parses the ASCII .frd format produced by CalculiX and exposes
nodal/elemental field data as NumPy arrays for downstream analysis
and visualization.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


def _parse_nodes(lines: list[str], start: int) -> tuple[dict[int, np.ndarray], int]:
    """Parse a node block starting after the ``2C`` header line.

    Returns a dict mapping node-id → [x, y, z] and the line index
    after the block-end marker (``-3``).
    """
    nodes: dict[int, np.ndarray] = {}
    i = start
    while i < len(lines):
        line = lines[i]
        if line.startswith(" -3"):
            return nodes, i + 1
        if line.startswith(" -1"):
            # FRD node format: " -1" + node_id(10) + x(12) + y(12) + z(12)
            try:
                nid = int(line[3:13])
                x = float(line[13:25])
                y = float(line[25:37])
                z = float(line[37:49])
                nodes[nid] = np.array([x, y, z])
            except (ValueError, IndexError):
                pass
        i += 1
    return nodes, i


def _parse_field_block(lines: list[str], start: int) -> tuple[dict[str, Any] | None, int]:
    """Parse a single results field block (displacement, stress, …).

    A field block begins with a ``100C`` header (field name / components),
    followed by ``-4`` component-name lines and ``-1`` data lines,
    ending with ``-3``.

    Returns (field_dict, next_line_index).  field_dict has keys
    ``name``, ``component_names``, ``values`` (dict[node_id → ndarray]).
    """
    # The 100C line carries the field name.
    header = lines[start] if start < len(lines) else ""
    # Typical: " 100CL 101         1           1PSTEP               1  1"
    # Field name starts at column 5, length ~6, but easier to regex.
    m = re.search(r"100C[A-Z]*\s+\d+", header)
    if not m:
        return None, start + 1

    # Read component names from "-4" lines that follow.
    comp_names: list[str] = []
    i = start + 1
    while i < len(lines) and lines[i].startswith(" -4"):
        name_part = lines[i][5:17].strip()
        if name_part:
            comp_names.append(name_part)
        i += 1

    # Read data lines ("-1" prefix) until "-3".
    values: dict[int, np.ndarray] = {}
    while i < len(lines):
        line = lines[i]
        if line.startswith(" -3"):
            i += 1
            break
        if line.startswith(" -1"):
            try:
                nid = int(line[3:13])
                # Each value occupies 12 chars after the node id.
                vals = []
                pos = 13
                while pos + 12 <= len(line):
                    vals.append(float(line[pos : pos + 12]))
                    pos += 12
                values[nid] = np.array(vals)
            except (ValueError, IndexError):
                pass
        i += 1

    field_name = "UNKNOWN"
    if "DISP" in header.upper():
        field_name = "displacement"
    elif "STRESS" in header.upper():
        field_name = "stress"
    elif "NDTEMP" in header.upper() or "TEMP" in header.upper():
        field_name = "temperature"
    elif "FORC" in header.upper():
        field_name = "force"
    else:
        # Use first component name or fallback.
        field_name = comp_names[0].lower() if comp_names else "field"

    return {
        "name": field_name,
        "component_names": comp_names,
        "values": values,
    }, i


def parse_frd(frd_path: Path) -> dict[str, Any]:
    """Parse a CalculiX .frd result file.

    Parameters
    ----------
    frd_path : Path
        Path to the .frd file.

    Returns
    -------
    dict
        Keys: ``nodes``, ``fields`` (list of field dicts each with
        ``name``, ``component_names``, ``values``).
    """
    if not frd_path.exists():
        raise FileNotFoundError(f"FRD file not found: {frd_path}")

    text = frd_path.read_text(errors="replace")
    lines = text.splitlines()

    nodes: dict[int, np.ndarray] = {}
    fields: list[dict[str, Any]] = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # Node block header: starts with "    2C"
        if line.strip().startswith("2C"):
            parsed_nodes, i = _parse_nodes(lines, i + 1)
            nodes.update(parsed_nodes)
            continue

        # Field block header: starts with " 100C"
        if " 100C" in line:
            field, i = _parse_field_block(lines, i)
            if field:
                fields.append(field)
            continue

        i += 1

    logger.info("Parsed FRD: %d nodes, %d field blocks", len(nodes), len(fields))

    return {"nodes": nodes, "fields": fields}


def extract_field_extremes(parsed: dict[str, Any], field_name: str) -> dict[str, Any]:
    """Extract min/max values and locations for a named field.

    Parameters
    ----------
    parsed : dict
        Output of ``parse_frd``.
    field_name : str
        Field to query (e.g. ``"displacement"``, ``"stress"``).

    Returns
    -------
    dict
        Keys: ``field``, ``max_magnitude``, ``max_node``,
        ``min_magnitude``, ``min_node``.
    """
    nodes = parsed.get("nodes", {})
    for field in parsed.get("fields", []):
        if field["name"] != field_name:
            continue

        values = field["values"]
        if not values:
            return {
                "field": field_name,
                "max_magnitude": 0.0,
                "max_node": None,
                "min_magnitude": 0.0,
                "min_node": None,
            }

        max_mag = -float("inf")
        min_mag = float("inf")
        max_node = None
        min_node = None

        for nid, arr in values.items():
            mag = float(np.linalg.norm(arr))
            if mag > max_mag:
                max_mag = mag
                max_node = nid
            if mag < min_mag:
                min_mag = mag
                min_node = nid

        return {
            "field": field_name,
            "max_magnitude": max_mag,
            "max_node": max_node,
            "min_magnitude": min_mag,
            "min_node": min_node,
        }

    return {
        "field": field_name,
        "max_magnitude": None,
        "max_node": None,
        "min_magnitude": None,
        "min_node": None,
    }
