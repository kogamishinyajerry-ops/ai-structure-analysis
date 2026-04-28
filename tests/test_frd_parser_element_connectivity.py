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


def test_multi_continuation_he20_and_tet10_connectivity_with_vtk_lookup() -> None:
    """Codex R1 (PR #90) HIGH regression — pin two things that the
    GS-001-only fixture does not exercise:

    1. Higher-order elements that span MULTIPLE ``-2`` continuation
       lines must accumulate connectivity correctly across all
       continuations (not just the first one).
    2. The numeric FRD type code → VTK cell-type lookup must match
       the CalculiX manual: ``4`` is ``he20`` (20-node hex), ``6``
       is ``tet10`` (10-node tet). The earlier table had ``4 → TET10``
       and ``6 → WEDGE15``, which would have produced wrong topology
       (or silent skip on width mismatch) for any non-HEX8 .frd.

    The synthetic ``-2`` records below match the FRD writer's
    "12-per-line wrap with the marker on every line" convention.
    """
    from app.parsers.frd_parser import FRDParser
    from app.viz.cell_types import vtk_type_for

    # he20 element id=1, type code "4", 20 connectivity nodes split
    # across two -2 continuation lines (12 + 8).
    # tet10 element id=2, type code "6", 10 nodes on a single -2 line
    # (still verifies the type-lookup path even without continuation).
    lines = [
        "3C",
        "-1         1    4    0    1",
        "-2  1  2  3  4  5  6  7  8  9 10 11 12",
        "-2 13 14 15 16 17 18 19 20",
        "-1         2    6    0    1",
        "-2 21 22 23 24 25 26 27 28 29 30",
        "-3",
    ]
    parser = FRDParser()
    parser._parse_element_block(lines, 0)

    # 1) connectivity length pinned (proves multi-continuation accumulation
    # for he20, and single-line decode for tet10)
    elem_he20 = parser.elements[1]
    assert elem_he20.element_type == "4"
    assert len(elem_he20.nodes) == 20, (
        f"he20 multi-continuation lost nodes: got {len(elem_he20.nodes)} ({elem_he20.nodes})"
    )
    assert elem_he20.nodes == list(range(1, 21))

    elem_tet10 = parser.elements[2]
    assert elem_tet10.element_type == "6"
    assert len(elem_tet10.nodes) == 10
    assert elem_tet10.nodes == list(range(21, 31))

    # 2) numeric type-code lookup pinned (would have failed before the
    # cell_types.py R1 fix: "4" was mapped to QUADRATIC_TETRA n=10,
    # which would have given a width mismatch against this 20-node he20)
    he20_vtk = vtk_type_for("4")
    assert he20_vtk == (25, 20), (
        f"FRD numeric code '4' (he20) must map to (VTK_QUADRATIC_HEXAHEDRON=25, 20); got {he20_vtk}"
    )
    tet10_vtk = vtk_type_for("6")
    assert tet10_vtk == (24, 10), (
        f"FRD numeric code '6' (tet10) must map to (VTK_QUADRATIC_TETRA=24, 10); got {tet10_vtk}"
    )
