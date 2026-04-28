"""W6e model-overview library tests — RFC-001 W6e.

Test buckets:

1. Happy path: synthetic reader with elements + GS-001 round-trip
2. Refusal contract: empty mesh, malformed coordinates
3. Capability detection: reader without SupportsElementInventory
4. Characteristic-length math (boundary + golden value)
5. Deep immutability
6. Unit-system label resolution
"""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType
from typing import Optional

import numpy as np
import pytest
from app.core.types import (
    BoundaryCondition,
    CanonicalField,
    FieldData,
    Material,
    Mesh,
    SolutionState,
    SupportsElementInventory,
    UnitSystem,
)
from app.services.report.model_overview import (
    ModelOverview,
    ModelOverviewError,
    summarize_model_overview,
)


# ---------------------------------------------------------------------------
# Synthetic readers — exercise the model_overview library without
# depending on a CalculiX .frd file. The CalculiX integration is
# pinned by a separate test that reads GS-001.
# ---------------------------------------------------------------------------


class _SyntheticMesh:
    def __init__(
        self,
        node_ids: list[int],
        coords: np.ndarray,
        unit_system: UnitSystem,
    ) -> None:
        self._node_ids = np.asarray(node_ids, dtype=np.int64)
        self._coords = coords
        self._unit_system = unit_system

    @property
    def node_id_array(self) -> np.ndarray:
        return self._node_ids

    @property
    def node_index(self) -> dict[int, int]:
        return {int(nid): i for i, nid in enumerate(self._node_ids)}

    @property
    def coordinates(self) -> np.ndarray:
        return self._coords

    @property
    def unit_system(self) -> UnitSystem:
        return self._unit_system


class _SyntheticReader:
    """Reader without ``SupportsElementInventory`` — element data
    unknown. The renderer should flag with [需工程师确认]."""

    SOLVER_NAME = "synthetic"

    def __init__(
        self,
        node_ids: list[int],
        coords: np.ndarray,
        unit_system: UnitSystem = UnitSystem.SI_MM,
    ) -> None:
        self._mesh = _SyntheticMesh(node_ids, coords, unit_system)

    @property
    def mesh(self) -> Mesh:
        return self._mesh  # type: ignore[return-value]

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
    ) -> Optional[FieldData]:
        return None

    def close(self) -> None:
        pass


class _SyntheticReaderWithElements(_SyntheticReader):
    """Reader that DOES implement ``SupportsElementInventory``."""

    def __init__(
        self,
        node_ids: list[int],
        coords: np.ndarray,
        elements_by_type: dict[str, int],
        unit_system: UnitSystem = UnitSystem.SI_MM,
    ) -> None:
        super().__init__(node_ids, coords, unit_system)
        self._elements_by_type = dict(elements_by_type)

    def element_inventory(self) -> dict[str, int]:
        # Return a fresh dict per call (capability contract).
        return dict(self._elements_by_type)


# ---------------------------------------------------------------------------
# Bucket 1 — happy path
# ---------------------------------------------------------------------------


def test_summary_returns_model_overview_with_inventory() -> None:
    """Reader with HEX8/TET4 mix → ModelOverview reports both counts
    and a non-null element_count."""
    coords = np.array(
        [
            [0.0, 0.0, 0.0],
            [10.0, 0.0, 0.0],
            [10.0, 5.0, 0.0],
            [0.0, 5.0, 0.0],
            [0.0, 0.0, 2.0],
            [10.0, 0.0, 2.0],
            [10.0, 5.0, 2.0],
            [0.0, 5.0, 2.0],
        ],
        dtype=np.float64,
    )
    rdr = _SyntheticReaderWithElements(
        node_ids=[1, 2, 3, 4, 5, 6, 7, 8],
        coords=coords,
        elements_by_type={"HEX8": 1, "TET4": 0},
    )
    mo = summarize_model_overview(rdr)  # type: ignore[arg-type]

    assert isinstance(mo, ModelOverview)
    assert mo.node_count == 8
    assert mo.element_inventory is not None
    assert dict(mo.element_inventory) == {"HEX8": 1, "TET4": 0}
    assert mo.element_count == 1
    # bbox_diag = sqrt(10^2 + 5^2 + 2^2) ≈ 11.358
    assert mo.bbox_diag == pytest.approx(np.sqrt(100 + 25 + 4))
    # characteristic_length = bbox / 8^(1/3) = bbox / 2
    assert mo.characteristic_length == pytest.approx(mo.bbox_diag / 2.0)
    assert mo.length_unit == "mm"
    assert mo.unit_system is UnitSystem.SI_MM
    assert mo.is_estimated is True


def test_summary_omits_inventory_when_capability_absent() -> None:
    """Reader without ``SupportsElementInventory`` produces
    ``element_inventory=None`` rather than fabricating zeros."""
    coords = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]], dtype=np.float64)
    rdr = _SyntheticReader(node_ids=[1, 2], coords=coords)

    mo = summarize_model_overview(rdr)  # type: ignore[arg-type]
    assert mo.element_inventory is None
    assert mo.element_count is None
    assert mo.node_count == 2


def test_isinstance_runtime_check_works_for_both_readers() -> None:
    """Sanity: the runtime_checkable protocol does not falsely match
    the no-inventory reader. (Without runtime_checkable on the
    protocol, isinstance returns False even for valid implementations.)"""
    rdr_no = _SyntheticReader(
        node_ids=[1], coords=np.array([[0.0, 0.0, 0.0]])
    )
    rdr_yes = _SyntheticReaderWithElements(
        node_ids=[1],
        coords=np.array([[0.0, 0.0, 0.0]]),
        elements_by_type={"HEX8": 1},
    )
    assert not isinstance(rdr_no, SupportsElementInventory)
    assert isinstance(rdr_yes, SupportsElementInventory)


# ---------------------------------------------------------------------------
# Bucket 2 — refusal contract
# ---------------------------------------------------------------------------


def test_summary_refuses_empty_mesh() -> None:
    """An empty mesh is not a structural-analysis report — refuse
    rather than emit an uncited placeholder section."""
    rdr = _SyntheticReader(
        node_ids=[], coords=np.zeros((0, 3), dtype=np.float64)
    )
    with pytest.raises(ModelOverviewError, match="zero nodes"):
        summarize_model_overview(rdr)  # type: ignore[arg-type]


def test_summary_refuses_misshaped_coordinate_array() -> None:
    """Coordinate array shape ≠ (N, 3) is a Layer-1 adapter bug —
    refuse rather than work around it."""
    rdr = _SyntheticReader(
        node_ids=[1, 2],
        coords=np.zeros((2, 2), dtype=np.float64),  # missing z column
    )
    with pytest.raises(ModelOverviewError, match=r"shape.*\(2, 2\).*expected \(2, 3\)"):
        summarize_model_overview(rdr)  # type: ignore[arg-type]


def test_summary_refuses_node_count_coord_count_mismatch() -> None:
    rdr = _SyntheticReader(
        node_ids=[1, 2, 3],
        coords=np.zeros((2, 3), dtype=np.float64),  # 3 IDs but only 2 rows
    )
    with pytest.raises(ModelOverviewError, match="expected.*3, 3"):
        summarize_model_overview(rdr)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Bucket 3b — Codex R1 (PR #103) protocol-spoof refusals
# ---------------------------------------------------------------------------


def test_summary_handles_capability_present_empty_inventory() -> None:
    """Codex R1 MEDIUM: capability-present-empty ``{}`` is documented
    but was never tested. Distinguishes from ``None`` (capability
    absent) — the renderer must show "0 elements" rather than
    [需工程师确认]."""
    rdr = _SyntheticReaderWithElements(
        node_ids=[1, 2],
        coords=np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]),
        elements_by_type={},
    )
    mo = summarize_model_overview(rdr)  # type: ignore[arg-type]
    assert mo.element_inventory is not None
    assert dict(mo.element_inventory) == {}
    assert mo.element_count == 0


class _BadAritySpoofReader(_SyntheticReader):
    """Codex R1 HIGH-a: ``element_inventory(required_arg)`` passes
    ``isinstance(SupportsElementInventory)`` (only checks presence)
    but raises TypeError at call time. The validator must surface
    a clean ModelOverviewError with the adapter class name."""

    def element_inventory(self, required_bucket: str) -> dict[str, int]:  # type: ignore[override]
        return {required_bucket: 1}


def test_summary_refuses_protocol_spoof_with_required_arg() -> None:
    rdr = _BadAritySpoofReader(
        node_ids=[1, 2], coords=np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    )
    assert isinstance(rdr, SupportsElementInventory)  # protocol passes ✗
    with pytest.raises(ModelOverviewError, match="zero-arg method"):
        summarize_model_overview(rdr)  # type: ignore[arg-type]


class _BadKeyTypeSpoofReader(_SyntheticReader):
    """Codex R1 HIGH-b1: keys must be canonical element-type strings."""

    def element_inventory(self) -> dict:  # type: ignore[override]
        return {1: 5}  # int key


def test_summary_refuses_protocol_spoof_with_int_key() -> None:
    rdr = _BadKeyTypeSpoofReader(
        node_ids=[1, 2], coords=np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    )
    with pytest.raises(ModelOverviewError, match="keys must be strings"):
        summarize_model_overview(rdr)  # type: ignore[arg-type]


class _FloatCountSpoofReader(_SyntheticReader):
    """Codex R1 HIGH-b2: counts must be int. Float would corrupt
    ``element_count = 2.5`` in the audit trail."""

    def element_inventory(self) -> dict:  # type: ignore[override]
        return {"HEX8": 2.5}


def test_summary_refuses_protocol_spoof_with_float_count() -> None:
    rdr = _FloatCountSpoofReader(
        node_ids=[1, 2], coords=np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    )
    with pytest.raises(ModelOverviewError, match="must be a real int"):
        summarize_model_overview(rdr)  # type: ignore[arg-type]


class _BoolCountSpoofReader(_SyntheticReader):
    """``bool`` ⊂ ``int`` would silently coerce ``True``/``False`` to
    1/0 — explicit guard required."""

    def element_inventory(self) -> dict:  # type: ignore[override]
        return {"HEX8": True}


def test_summary_refuses_protocol_spoof_with_bool_count() -> None:
    rdr = _BoolCountSpoofReader(
        node_ids=[1, 2], coords=np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    )
    with pytest.raises(ModelOverviewError, match="must be a real int"):
        summarize_model_overview(rdr)  # type: ignore[arg-type]


class _NegativeCountSpoofReader(_SyntheticReader):
    def element_inventory(self) -> dict[str, int]:
        return {"HEX8": -3}


def test_summary_refuses_negative_count() -> None:
    rdr = _NegativeCountSpoofReader(
        node_ids=[1, 2], coords=np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    )
    with pytest.raises(ModelOverviewError, match="non-negative"):
        summarize_model_overview(rdr)  # type: ignore[arg-type]


class _NonMappingSpoofReader(_SyntheticReader):
    """Returning a list instead of Mapping passes the runtime_checkable
    method-presence check but breaks the contract."""

    def element_inventory(self) -> list:  # type: ignore[override]
        return [("HEX8", 5)]


def test_summary_refuses_non_mapping_return() -> None:
    rdr = _NonMappingSpoofReader(
        node_ids=[1, 2], coords=np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    )
    with pytest.raises(ModelOverviewError, match="must return a Mapping"):
        summarize_model_overview(rdr)  # type: ignore[arg-type]


class _MutableCount:
    """Stand-in for an adapter that wraps counts in a mutable
    object. Validates that the normaliser refuses non-int-typed
    values rather than letting the wrapper survive the snapshot
    and corrupt it later (Codex R1 HIGH-c POC)."""

    def __init__(self, n: int) -> None:
        self.n = n

    def __index__(self) -> int:
        return self.n


class _MutableCountSpoofReader(_SyntheticReader):
    def element_inventory(self) -> dict:  # type: ignore[override]
        return {"HEX8": _MutableCount(5)}


def test_summary_refuses_mutable_count_wrapper() -> None:
    """Even ``__index__``-supporting wrappers are rejected — the
    contract is ``int`` exactly. A mutable wrapper that survived
    would let an adversary mutate the published snapshot via the
    wrapper reference."""
    rdr = _MutableCountSpoofReader(
        node_ids=[1, 2], coords=np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    )
    with pytest.raises(ModelOverviewError, match="must be a real int"):
        summarize_model_overview(rdr)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Bucket 4 — characteristic-length math
# ---------------------------------------------------------------------------


def test_characteristic_length_at_single_node_falls_back_to_diag() -> None:
    """N=1 → ``N^(1/3)=1``, characteristic_length == bbox_diag.
    Single-node bbox_diag is 0 so this also tests the zero case."""
    rdr = _SyntheticReader(
        node_ids=[1], coords=np.zeros((1, 3), dtype=np.float64)
    )
    mo = summarize_model_overview(rdr)  # type: ignore[arg-type]
    assert mo.bbox_diag == 0.0
    assert mo.characteristic_length == 0.0


def test_characteristic_length_matches_roadmap_example() -> None:
    """Roadmap end-state quotes ``"36 节点 / ... / 特征尺寸约 25 mm"``.
    With 36 nodes evenly distributed on a 100 mm cube edge, bbox_diag
    is ``100 * sqrt(3) ≈ 173.2`` and ``N^(1/3) ≈ 3.302``, so
    characteristic_length ≈ ``173.2 / 3.302 ≈ 52.5 mm`` — pin the math
    here so a future change can't silently drift it."""
    # Build a 36-node placeholder cube. Coord values picked just to
    # make bbox = (0..100, 0..100, 0..100); the actual node distribution
    # is irrelevant to the formula.
    coords = np.zeros((36, 3), dtype=np.float64)
    coords[0] = [0.0, 0.0, 0.0]
    coords[-1] = [100.0, 100.0, 100.0]
    rdr = _SyntheticReader(node_ids=list(range(1, 37)), coords=coords)
    mo = summarize_model_overview(rdr)  # type: ignore[arg-type]

    expected_diag = float(np.linalg.norm([100.0, 100.0, 100.0]))
    expected_charlen = expected_diag / (36.0 ** (1.0 / 3.0))
    assert mo.bbox_diag == pytest.approx(expected_diag, rel=1e-9)
    assert mo.characteristic_length == pytest.approx(expected_charlen, rel=1e-9)


def test_characteristic_length_unit_follows_mesh_unit_system() -> None:
    """SI_mm → 'mm', SI → 'm', English → 'in', UNKNOWN → 'unknown'."""
    coords = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]], dtype=np.float64)
    for system, expected in [
        (UnitSystem.SI_MM, "mm"),
        (UnitSystem.SI, "m"),
        (UnitSystem.ENGLISH, "in"),
        (UnitSystem.UNKNOWN, "unknown"),
    ]:
        rdr = _SyntheticReader(
            node_ids=[1, 2], coords=coords, unit_system=system,
        )
        mo = summarize_model_overview(rdr)  # type: ignore[arg-type]
        assert mo.length_unit == expected
        assert mo.unit_system is system


# ---------------------------------------------------------------------------
# Bucket 5 — deep immutability
# ---------------------------------------------------------------------------


def test_model_overview_is_frozen() -> None:
    from dataclasses import FrozenInstanceError

    rdr = _SyntheticReader(
        node_ids=[1], coords=np.zeros((1, 3), dtype=np.float64)
    )
    mo = summarize_model_overview(rdr)  # type: ignore[arg-type]
    with pytest.raises(FrozenInstanceError):
        mo.node_count = 999  # type: ignore[misc]


def test_element_inventory_is_immutable_when_present() -> None:
    """The DOCX renderer must not be able to mutate the inventory
    between extraction and template substitution."""
    rdr = _SyntheticReaderWithElements(
        node_ids=[1, 2],
        coords=np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]),
        elements_by_type={"HEX8": 5, "TET4": 3},
    )
    mo = summarize_model_overview(rdr)  # type: ignore[arg-type]

    assert isinstance(mo.element_inventory, MappingProxyType)
    with pytest.raises(TypeError):
        mo.element_inventory["TAMPER"] = 99  # type: ignore[index]


def test_element_inventory_isolated_from_subsequent_adapter_mutation() -> None:
    """If the adapter later returns a different dict (or mutates its
    internal copy), the previously-returned ModelOverview must NOT
    change. Defensive-copy contract."""
    rdr = _SyntheticReaderWithElements(
        node_ids=[1, 2],
        coords=np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]),
        elements_by_type={"HEX8": 5},
    )
    mo = summarize_model_overview(rdr)  # type: ignore[arg-type]
    snapshot = dict(mo.element_inventory or {})

    # Mutate the adapter's internal counts after the snapshot.
    rdr._elements_by_type["HEX8"] = 999
    rdr._elements_by_type["NEW_TYPE"] = 42

    assert dict(mo.element_inventory or {}) == snapshot
    assert dict(mo.element_inventory or {}) == {"HEX8": 5}


# ---------------------------------------------------------------------------
# Integration with CalculiX adapter (skipped if GS-001 absent)
# ---------------------------------------------------------------------------


_GS001_FRD = (
    Path(__file__).resolve().parents[2]
    / "golden_samples"
    / "GS-001"
    / "gs001_result.frd"
)


def test_summary_round_trips_calculix_reader() -> None:
    """End-to-end: CalculiX adapter implements ``SupportsElementInventory``,
    so the model overview surfaces both the node count and the
    element-type breakdown for GS-001."""
    if not _GS001_FRD.exists():
        pytest.skip(f"GS-001 .frd missing at {_GS001_FRD}")

    from app.adapters.calculix import CalculiXReader

    rdr = CalculiXReader(_GS001_FRD, unit_system=UnitSystem.SI_MM)
    mo = summarize_model_overview(rdr)

    assert isinstance(mo, ModelOverview)
    assert mo.node_count > 0
    assert mo.element_inventory is not None
    # Exact GS-001 counts are pinned in test_calculix_adapter; here we
    # just confirm the protocol round-trip and that some elements exist.
    assert mo.element_count is not None and mo.element_count > 0
    assert mo.length_unit == "mm"
    rdr.close()


def test_calculix_reader_implements_element_inventory_protocol() -> None:
    """Discipline: CalculiX adapter must implement
    ``SupportsElementInventory`` so the W6e service can detect it via
    ``isinstance``. Pinning this ensures a future refactor doesn't
    accidentally drop the capability."""
    if not _GS001_FRD.exists():
        pytest.skip(f"GS-001 .frd missing at {_GS001_FRD}")

    from app.adapters.calculix import CalculiXReader

    rdr = CalculiXReader(_GS001_FRD, unit_system=UnitSystem.SI_MM)
    assert isinstance(rdr, SupportsElementInventory)
    inventory = rdr.element_inventory()
    # Each call returns a fresh mapping (mutable copy is OK as long as
    # mutating it doesn't poison subsequent calls).
    inventory["TAMPER"] = 999
    fresh = rdr.element_inventory()
    assert "TAMPER" not in fresh
    rdr.close()
