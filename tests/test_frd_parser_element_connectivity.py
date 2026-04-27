"""Regression tests for FRDParser element-connectivity parsing.

The off-by-one bug in `_parse_element_block` (parts[2:] instead of
parts[1:]) silently dropped the first node of every element. The
existing L4 templates only consume point-data (DISP / STRESS), so the
bug surfaced only when W5f's viz module tried to render the mesh and
HEX8 cells came back with 7 nodes instead of 8.

These tests pin the connectivity contract so future refactors can't
silently regress.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from app.parsers.frd_parser import FRDParser

REPO_ROOT = Path(__file__).resolve().parents[1]
GS001_FRD = REPO_ROOT / "golden_samples" / "GS-001" / "gs001_result.frd"


@pytest.fixture()
def gs001_parsed() -> object:
    if not GS001_FRD.is_file():
        pytest.skip(f"GS-001 fixture missing at {GS001_FRD}")
    parsed = FRDParser().parse(GS001_FRD)
    assert parsed.success, parsed.error_message
    return parsed


def test_hex8_elements_have_eight_nodes(gs001_parsed: object) -> None:
    """GS-001 is meshed with linear hex (CalculiX type code "1" =
    HEX8 / C3D8). Every element must have exactly 8 nodes in its
    connectivity list. The bug was that parts[2:] skipped one,
    producing 7-node "HEX8" cells that broke downstream viz."""
    assert len(gs001_parsed.elements) == 10
    for eid, elem in gs001_parsed.elements.items():
        assert elem.element_type == "1", f"element {eid} type changed to {elem.element_type!r}"
        assert len(elem.nodes) == 8, (
            f"element {eid}: expected 8 nodes for HEX8, got {len(elem.nodes)}: {elem.nodes}"
        )


def test_first_element_connectivity_matches_frd_file(
    gs001_parsed: object,
) -> None:
    """Anchor test against the literal .frd file contents. Element 1
    in golden_samples/GS-001/gs001_result.frd is:

        -1         1    1    0    1
        -2         1         2        13        12        23        24        35        34

    so its connectivity is [1, 2, 13, 12, 23, 24, 35, 34]. The
    pre-fix parser would have returned [2, 13, 12, 23, 24, 35, 34]."""
    elem1 = gs001_parsed.elements[1]
    assert elem1.nodes == [1, 2, 13, 12, 23, 24, 35, 34]


def test_all_element_nodes_resolve_in_node_dict(
    gs001_parsed: object,
) -> None:
    """Every node ID in every element's connectivity must exist in
    parsed.nodes. A connectivity bug that produced a missing first
    node would manifest as orphan node references; this test catches
    that class."""
    node_ids = set(gs001_parsed.nodes.keys())
    for eid, elem in gs001_parsed.elements.items():
        for nid in elem.nodes:
            assert nid in node_ids, (
                f"element {eid} references node {nid} which is not "
                f"in parsed.nodes ({len(node_ids)} nodes)"
            )
