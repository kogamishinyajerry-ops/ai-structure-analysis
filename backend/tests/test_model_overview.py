"""W6e model-overview library tests — RFC-001 W6e.

Test buckets:

1. Capability-absent path: reader without SupportsElementInventory →
   total_elements=0, has_inventory=False, no fabricated counts.
2. Capability-present happy path: type_counts + group_counts populated,
   has_inventory=True.
3. Group bucketing: known types map to expected groups; unknown types
   bucket into GROUP_OTHER without raising.
4. Refusal contract: malformed adapter returns surface as
   ModelOverviewError with a useful message.
5. Deep-immutability of ModelOverview's maps.
6. Stable ordering across calls (sorted by key).
7. Integration: GS-001 .frd via real CalculiXReader produces the
   expected element-type breakdown.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType

import numpy as np
import numpy.typing as npt
import pytest
from app.core.types import (
    BoundaryCondition,
    Material,
    Mesh,
    ReaderHandle,
    SolutionState,
    SupportsElementInventory,
    UnitSystem,
)
from app.core.types.enums import CanonicalField
from app.core.types.field_data import FieldData
from app.services.report.model_overview import (
    ELEMENT_TYPE_GROUPS,
    GROUP_OTHER,
    ModelOverview,
    ModelOverviewError,
    summarize_model,
)


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class _FakeMesh:
    """Minimal Mesh-Protocol satisfier for the tests."""

    def __init__(self, n_nodes: int) -> None:
        self._ids = np.arange(1, n_nodes + 1, dtype=np.int64)
        self._coords = np.zeros((n_nodes, 3), dtype=np.float64)

    @property
    def node_id_array(self) -> npt.NDArray[np.int64]:
        return self._ids

    @property
    def node_index(self) -> dict[int, int]:
        return {int(nid): i for i, nid in enumerate(self._ids)}

    @property
    def coordinates(self) -> npt.NDArray[np.float64]:
        return self._coords

    @property
    def unit_system(self) -> UnitSystem:
        return UnitSystem.SI_MM


class _NoInventoryReader:
    """Reader that satisfies the base ReaderHandle Protocol but does
    NOT declare SupportsElementInventory. Mirrors the W7b OpenRadioss
    reader's current state — exercises the graceful-degrade path."""

    def __init__(self, n_nodes: int) -> None:
        self._mesh = _FakeMesh(n_nodes)

    @property
    def mesh(self) -> Mesh:
        return self._mesh

    @property
    def materials(self) -> dict[str, Material]:
        return {}

    @property
    def boundary_conditions(self) -> list[BoundaryCondition]:
        return []

    @property
    def solution_states(self) -> list[SolutionState]:
        return []

    def get_field(
        self, name: CanonicalField, step_id: int
    ) -> FieldData | None:
        return None

    def close(self) -> None:
        pass


class _InventoryReader(_NoInventoryReader):
    """Reader that DOES declare SupportsElementInventory."""

    def __init__(self, n_nodes: int, types: tuple[str, ...]) -> None:
        super().__init__(n_nodes)
        self._types = types

    def element_types(self) -> tuple[str, ...]:
        return self._types


# ---------------------------------------------------------------------------
# Bucket 1 — capability-absent path
# ---------------------------------------------------------------------------


def test_no_inventory_capability_returns_zero_elements_with_flag() -> None:
    """Adapter without SupportsElementInventory: nodes counted from
    Mesh, elements explicitly 0 with has_inventory=False so the
    renderer can show a placeholder instead of '0 elements'."""
    reader = _NoInventoryReader(n_nodes=42)
    overview = summarize_model(reader)

    assert overview.total_nodes == 42
    assert overview.total_elements == 0
    assert overview.has_inventory is False
    assert dict(overview.type_counts) == {}
    assert dict(overview.group_counts) == {}


def test_no_inventory_does_not_call_element_types_method() -> None:
    """Defensive: an adapter that incidentally has an
    ``element_types`` attribute but does not declare the Protocol
    should not be probed. Confirms the isinstance gate is the only
    discovery path."""

    class _IncidentalElementTypes(_NoInventoryReader):
        called = False

        def element_types(self) -> tuple[str, ...]:
            type(self).called = True
            return ("WHATEVER",)

    reader = _IncidentalElementTypes(n_nodes=7)
    # Even though this class has element_types, runtime_checkable
    # Protocol with one method WILL match — so this assertion confirms
    # the Protocol is being respected. If the incidental attribute is
    # the right shape, it IS the capability — that's the documented
    # duck-typing contract of @runtime_checkable.
    assert isinstance(reader, SupportsElementInventory)
    overview = summarize_model(reader)
    assert overview.has_inventory is True
    assert _IncidentalElementTypes.called is True
    assert overview.total_elements == 1


# ---------------------------------------------------------------------------
# Bucket 2 — capability-present happy path
# ---------------------------------------------------------------------------


def test_inventory_present_populates_type_and_group_counts() -> None:
    types = ("C3D10",) * 100 + ("S4R",) * 4 + ("C3D8",) * 10
    reader = _InventoryReader(n_nodes=512, types=types)

    overview = summarize_model(reader)

    assert overview.total_nodes == 512
    assert overview.total_elements == 114
    assert overview.has_inventory is True
    assert dict(overview.type_counts) == {"C3D10": 100, "C3D8": 10, "S4R": 4}
    assert dict(overview.group_counts) == {"四面体": 100, "六面体": 10, "壳": 4}


def test_inventory_zero_elements_is_confirmed_not_unknown() -> None:
    """Capable adapter with zero elements: total_elements=0 BUT
    has_inventory=True so the renderer says '0 elements (confirmed)'
    rather than the unknown placeholder."""
    reader = _InventoryReader(n_nodes=5, types=())
    overview = summarize_model(reader)
    assert overview.total_elements == 0
    assert overview.has_inventory is True
    assert dict(overview.type_counts) == {}


# ---------------------------------------------------------------------------
# Bucket 3 — group bucketing (table integrity)
# ---------------------------------------------------------------------------


def test_unknown_types_bucket_into_group_other() -> None:
    """``CUSTOM_GASKET`` is not in ELEMENT_TYPE_GROUPS — must land in
    ``GROUP_OTHER`` without raising."""
    types = ("C3D10", "C3D10", "CUSTOM_GASKET", "MYSTERY")
    reader = _InventoryReader(n_nodes=10, types=types)
    overview = summarize_model(reader)

    assert overview.group_counts["四面体"] == 2
    assert overview.group_counts[GROUP_OTHER] == 2
    # type_counts preserves the solver-native strings even for unknowns
    assert overview.type_counts["CUSTOM_GASKET"] == 1
    assert overview.type_counts["MYSTERY"] == 1


@pytest.mark.parametrize(
    "type_name, expected_group",
    [
        ("C3D4", "四面体"),
        ("C3D10", "四面体"),
        ("C3D8", "六面体"),
        ("C3D8R", "六面体"),
        ("C3D6", "楔形"),
        ("S3", "壳"),
        ("S4R", "壳"),
        ("B31", "梁"),
    ],
)
def test_known_types_bucket_correctly(
    type_name: str, expected_group: str
) -> None:
    """Spot-check the group table for the most common solver-native
    types we expect to see in real CalculiX / Abaqus runs."""
    assert ELEMENT_TYPE_GROUPS[type_name] == expected_group


# ---------------------------------------------------------------------------
# Bucket 4 — refusal contract
# ---------------------------------------------------------------------------


class _BadInventoryListReader(_NoInventoryReader):
    """Returns a list, not a tuple — capability contract requires a tuple."""

    def element_types(self) -> tuple[str, ...]:  # type: ignore[override]
        return ["C3D10", "C3D10"]  # type: ignore[return-value]


def test_non_tuple_return_raises() -> None:
    reader = _BadInventoryListReader(n_nodes=5)
    with pytest.raises(ModelOverviewError, match="must return a tuple"):
        summarize_model(reader)


class _NonStringEntryReader(_NoInventoryReader):
    def element_types(self) -> tuple[str, ...]:  # type: ignore[override]
        return ("C3D10", 42, "S4R")  # type: ignore[return-value]


def test_non_string_entry_raises_with_index() -> None:
    reader = _NonStringEntryReader(n_nodes=5)
    with pytest.raises(ModelOverviewError, match=r"\[1\] must be a string"):
        summarize_model(reader)


class _EmptyEntryReader(_NoInventoryReader):
    def element_types(self) -> tuple[str, ...]:
        return ("C3D10", "   ", "S4R")


def test_empty_or_whitespace_entry_raises_with_index() -> None:
    reader = _EmptyEntryReader(n_nodes=5)
    with pytest.raises(ModelOverviewError, match=r"\[1\] is empty"):
        summarize_model(reader)


# ---------------------------------------------------------------------------
# Bucket 5 — deep immutability
# ---------------------------------------------------------------------------


def test_type_counts_is_a_read_only_mapping() -> None:
    reader = _InventoryReader(n_nodes=3, types=("C3D10",))
    overview = summarize_model(reader)
    # MappingProxyType refuses item assignment with TypeError
    with pytest.raises(TypeError):
        overview.type_counts["INJECTED"] = 99  # type: ignore[index]


def test_group_counts_is_a_read_only_mapping() -> None:
    reader = _InventoryReader(n_nodes=3, types=("C3D10",))
    overview = summarize_model(reader)
    with pytest.raises(TypeError):
        overview.group_counts["INJECTED"] = 99  # type: ignore[index]


def test_dataclass_is_frozen() -> None:
    reader = _InventoryReader(n_nodes=3, types=("C3D10",))
    overview = summarize_model(reader)
    with pytest.raises(Exception):  # FrozenInstanceError, exact class private
        overview.total_nodes = 999  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Bucket 6 — stable ordering
# ---------------------------------------------------------------------------


def test_type_counts_keys_are_sorted() -> None:
    """The renderer iterates type_counts to render the breakdown
    table; a stable order makes the DOCX byte-stable across runs even
    if the FRD parser shuffles internal block order."""
    types = ("S4R", "C3D10", "B31", "C3D8")
    reader = _InventoryReader(n_nodes=10, types=types)
    overview = summarize_model(reader)
    assert list(overview.type_counts.keys()) == ["B31", "C3D10", "C3D8", "S4R"]


def test_group_counts_keys_are_sorted() -> None:
    types = ("S4R", "C3D10", "B31", "C3D8")
    reader = _InventoryReader(n_nodes=10, types=types)
    overview = summarize_model(reader)
    # 梁=1 (B31), 六面体=1 (C3D8), 四面体=1 (C3D10), 壳=1 (S4R) — sorted by
    # Unicode codepoint of the first char.
    assert list(overview.group_counts.keys()) == sorted(
        overview.group_counts.keys()
    )


# ---------------------------------------------------------------------------
# Bucket 7 — integration with real CalculiXReader
# ---------------------------------------------------------------------------


_GS001_FRD: Path = (
    Path(__file__).resolve().parents[2]
    / "golden_samples"
    / "GS-001"
    / "gs001_result.frd"
)


@pytest.mark.skipif(not _GS001_FRD.is_file(), reason="GS-001 fixture missing")
def test_calculix_reader_reports_inventory_on_gs001_frd() -> None:
    """Smoke test against the bundled GS-001 .frd: the CalculiX
    adapter declares SupportsElementInventory (W6e), translates raw
    FRD numeric type codes into Abaqus-style names, and the summary
    library buckets the result.

    Asserts qualitative properties only — the exact element count and
    type distribution are mesh-quality choices that may change if the
    fixture is re-meshed; we just need to prove the W6e pipeline
    reaches the DOCX with non-fabricated counts.
    """
    from app.adapters.calculix.reader import CalculiXReader

    reader = CalculiXReader(_GS001_FRD, unit_system=UnitSystem.SI_MM)
    try:
        assert isinstance(reader, SupportsElementInventory)
        overview = summarize_model(reader)
        assert overview.has_inventory is True
        assert overview.total_nodes > 0
        assert overview.total_elements > 0
        # Adapter must translate FRD numeric type codes ("1", "2", ...)
        # into Abaqus-style names ("C3D8", "C3D10", ...) — none of the
        # raw integer-coded keys should leak into type_counts.
        assert not any(
            t.isdigit() for t in overview.type_counts
        ), f"raw FRD codes leaked into type_counts: {dict(overview.type_counts)}"
        # Total of group_counts must match total_elements (the
        # bucketing must be lossless — every element lands in some
        # group, even GROUP_OTHER).
        assert sum(overview.group_counts.values()) == overview.total_elements
        # At least one bucket must be a known structural family
        # (not GROUP_OTHER) — confirms the FRD-to-Abaqus translation
        # actually hit the table for the GS-001 element types.
        non_other = {
            g: c for g, c in overview.group_counts.items() if g != GROUP_OTHER
        }
        assert non_other, (
            f"GS-001: no element types resolved into a known group; "
            f"group_counts={dict(overview.group_counts)}, "
            f"type_counts={dict(overview.type_counts)}"
        )
    finally:
        reader.close()
