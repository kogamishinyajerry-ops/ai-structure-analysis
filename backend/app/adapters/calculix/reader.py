"""CalculiX Layer-1 adapter — implements the ``ReaderHandle`` Protocol
over CalculiX ``.frd`` ASCII result files.

RFC-001 §4.5 W2: rewrap Sprint-2 ``parsers/frd_parser.py`` (the live,
working parser) into the Layer-2 contract from ``app.core.types``.

ADR compliance:
  * ADR-001 — no derived quantities here. The legacy ``frd_parser``
    computed ``von_mises`` and ``max_von_mises`` eagerly; this adapter
    exposes only the raw stress tensor. Layer-3
    ``app.domain.stress_derivatives`` computes von Mises (lands W3).
  * ADR-003 — ``UnitSystem`` is **not inferred** from the file.
    ``.frd`` carries no unit metadata; the constructor's ``unit_system``
    argument MUST be explicit (the wizard pins it). Default is
    ``UnitSystem.UNKNOWN`` and Layer-3 must refuse to convert from it.
  * ADR-004 — no caching, no IO optimisation. Each ``get_field`` /
    ``mesh.coordinates`` access materialises a fresh numpy array from
    the parsed dicts; lazy as in "no work until asked", not as in
    "memoised forever".
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, ClassVar, Optional

import numpy as np
import numpy.typing as npt

from ...core.types import (
    BoundaryCondition,
    CanonicalField,
    ComponentType,
    CoordinateSystemKind,
    FieldData,
    FieldLocation,
    FieldMetadata,
    Material,
    Mesh,
    ReaderHandle,
    SolutionState,
    UnitSystem,
)
from ...parsers.frd_parser import FRDParseResult, FRDParser, FRDStress


class _CalculiXMesh:
    """``Mesh`` Protocol implementation backed by an ``FRDParseResult``."""

    def __init__(self, parsed: FRDParseResult, unit_system: UnitSystem) -> None:
        # Sort node IDs for deterministic dense indexing (RFC §4.6 trap #4).
        self._sorted_ids: tuple[int, ...] = tuple(sorted(parsed.nodes.keys()))
        self._node_index: dict[int, int] = {
            nid: idx for idx, nid in enumerate(self._sorted_ids)
        }
        self._parsed = parsed
        self._unit_system = unit_system

    @property
    def node_id_array(self) -> npt.NDArray[np.int64]:
        return np.asarray(self._sorted_ids, dtype=np.int64)

    @property
    def node_index(self) -> dict[int, int]:
        # Defensive copy: callers must not mutate our internal map.
        return dict(self._node_index)

    @property
    def coordinates(self) -> npt.NDArray[np.float64]:
        coords = np.zeros((len(self._sorted_ids), 3), dtype=np.float64)
        for nid, idx in self._node_index.items():
            coords[idx] = self._parsed.nodes[nid].coords
        return coords

    @property
    def unit_system(self) -> UnitSystem:
        return self._unit_system


class _CalculiXFieldData:
    """``FieldData`` Protocol implementation — values materialised on call."""

    def __init__(
        self,
        metadata: FieldMetadata,
        node_index: dict[int, int],
        n_nodes: int,
        raw: dict[int, Any],
        component_extractor: Callable[[Any], tuple[Optional[float], ...]],
    ) -> None:
        # ``metadata`` is read eagerly per Layer-2 contract; the ``raw``
        # dict + extractor are stored for the lazy values() / at_nodes()
        # path. ``component_extractor`` is a callable that turns one raw
        # entry (e.g. an FRDStress) into a fixed-length tuple of floats
        # — the per-node row in the materialised array.
        self.metadata = metadata
        self._node_index = node_index
        self._n_nodes = n_nodes
        self._raw = raw
        self._extract = component_extractor
        # Inferred row width from the first present sample so an empty
        # field still returns a sane (N,0) array rather than failing.
        sample = next(iter(raw.values()), None)
        self._cols = len(self._extract(sample)) if sample is not None else 0

    def values(self) -> npt.NDArray[np.float64]:
        return self._materialise()

    def at_nodes(self) -> npt.NDArray[np.float64]:
        # FRD already stores stresses *per node, unaveraged*. CalculiX's
        # node-extrapolated values may be averaged or unaveraged depending
        # on solver flags; this adapter does NOT re-average (ADR-001).
        return self._materialise()

    def _materialise(self) -> npt.NDArray[np.float64]:
        # Honour the docstring contract: empty raw → (N, 0). Codex R1
        # observed that ``max(_cols, 1)`` produced (N, 1) instead, an
        # inconsistency with the comment. Fixed here.
        out = np.zeros((self._n_nodes, self._cols), dtype=np.float64)
        if self._cols == 0:
            return out
        for nid, row in self._raw.items():
            idx = self._node_index.get(nid)
            if idx is None:
                continue
            extracted = self._extract(row)
            for j, val in enumerate(extracted):
                out[idx, j] = 0.0 if val is None else float(val)
        return out


def _disp_components(disp: Optional[tuple[float, float, float]]) -> tuple[float, ...]:
    if disp is None:
        return (0.0, 0.0, 0.0)
    return (disp[0], disp[1], disp[2])


def _stress_components(stress: Optional[FRDStress]) -> tuple[Optional[float], ...]:
    if stress is None:
        return (None, None, None, None, None, None)
    return (stress.S11, stress.S22, stress.S33, stress.S12, stress.S23, stress.S13)


class CalculiXReader:
    """``ReaderHandle`` over a CalculiX ``.frd`` result file.

    Wrapper around the live Sprint-2 ``FRDParser`` — no parser logic is
    duplicated here. Full file is parsed eagerly on construction (the
    legacy parser is not streaming-aware); per-field materialisation is
    lazy in ``_CalculiXFieldData``.

    The ``.frd`` format encodes solution results only — material cards
    and boundary conditions live in the matching ``.inp`` (input deck)
    and are not reachable from a ``.frd`` alone. ``materials`` and
    ``boundary_conditions`` therefore return empty containers; once the
    Layer-2 contract grows an ``.inp``-aware companion (post-W2), they
    will hydrate from there.
    """

    SOLVER_NAME = "calculix"

    def __init__(
        self,
        result_file: Path | str,
        *,
        unit_system: UnitSystem = UnitSystem.UNKNOWN,
    ) -> None:
        self._result_file = Path(result_file)
        self._unit_system = unit_system
        # Sprint-2 ``FRDParser`` predates the strict-typed adapter layer
        # and lacks its own annotations; the type: ignore is scoped to
        # this single call site (the legacy parser will be replaced when
        # binary .frd support lands per RFC §4.5).
        parsed = FRDParser().parse(str(self._result_file))  # type: ignore[no-untyped-call]
        if not parsed.success:
            raise ValueError(
                f"CalculiX .frd parse failed for {self._result_file}: "
                f"{parsed.error_message}"
            )
        if not parsed.nodes:
            # Sprint-2 parser is lenient — non-FRD text returns success=True
            # with zero nodes. A reader with no mesh is structurally broken;
            # surface the failure here rather than handing back a useless
            # ReaderHandle.
            raise ValueError(
                f"CalculiX .frd at {self._result_file} produced zero nodes; "
                "file is missing the node block or is not a CalculiX result."
            )
        self._parsed: FRDParseResult = parsed
        self._mesh = _CalculiXMesh(parsed, unit_system)
        self._closed = False

    # --- Layer-2 surface -------------------------------------------------

    @property
    def mesh(self) -> Mesh:
        self._check_open()
        return self._mesh

    @property
    def materials(self) -> dict[str, Material]:
        self._check_open()
        # ADR-003: do not fabricate. .frd has no material data.
        return {}

    @property
    def boundary_conditions(self) -> list[BoundaryCondition]:
        self._check_open()
        # ADR-003: do not fabricate. BCs live in the .inp deck.
        return []

    @property
    def solution_states(self) -> list[SolutionState]:
        self._check_open()
        increments = self._parsed.increments
        # Sprint-2 parser splits DISP and STRESS blocks of a single
        # CalculiX step into separate ``FRDIncrement`` slots when each
        # block is announced with its own header. We collapse adjacent
        # increments that share ``(type, value)`` AND contribute
        # *disjoint* field types — two increments at ('static', 1.0)
        # where one carries only DISP and the other only STRESS are
        # the same logical step. Two increments at ('static', 1.0)
        # where BOTH carry DISP would be real distinct steps (multi-
        # step / restart with the same load factor) and stay separate.
        # This addresses Codex R1 HIGH: bare-(type, value) collapse
        # was lossy on multi-step or restarted analyses.
        if not increments:
            available = self._available_fields_for_dicts(
                self._parsed.displacements, self._parsed.stresses
            )
            return [
                SolutionState(
                    step_id=1,
                    step_name="static",
                    time=None,
                    load_factor=None,
                    available_fields=available,
                )
            ]

        merged: list[dict[str, Any]] = []
        for inc in increments:
            inc_fields = self._fields_in_increment(inc)
            slot = self._find_disjoint_slot(merged, inc, inc_fields)
            if slot is None:
                slot = {
                    "step_id": inc.step,
                    "type": inc.type or "static",
                    "value": float(inc.value),
                    "disp": {},
                    "stress": {},
                    "fields": set(),
                }
                merged.append(slot)
            if inc.displacements:
                slot["disp"] = inc.displacements
            if inc.stresses:
                slot["stress"] = inc.stresses
            slot["fields"] |= inc_fields

        return [self._slot_to_state(slot) for slot in merged]

    @staticmethod
    def _fields_in_increment(inc: Any) -> set[CanonicalField]:
        present: set[CanonicalField] = set()
        if inc.displacements:
            present.add(CanonicalField.DISPLACEMENT)
        if inc.stresses:
            present.add(CanonicalField.STRESS_TENSOR)
        return present

    @staticmethod
    def _find_disjoint_slot(
        merged: list[dict[str, Any]],
        inc: Any,
        inc_fields: set[CanonicalField],
    ) -> Optional[dict[str, Any]]:
        # Match the most recent slot with same (type, value) and disjoint
        # field set. ``reversed`` so multi-step loops at the same load
        # factor don't all coalesce into the first slot.
        for slot in reversed(merged):
            if slot["type"] != (inc.type or "static"):
                continue
            if slot["value"] != float(inc.value):
                continue
            if slot["fields"] & inc_fields:
                return None  # field collision → real distinct step
            return slot
        return None

    @staticmethod
    def _slot_to_state(slot: dict[str, Any]) -> SolutionState:
        # Per Layer-2 contract:
        #   * ``time`` is wall-clock simulation time (transient/dynamic).
        #     CalculiX static `value` is a load-step counter (1.0 = end
        #     of step), NOT physical time → time=None.
        #   * ``load_factor`` is the buckling eigenvalue or modal-frequency
        #     value; for static and unknown types, leave None.
        # This addresses Codex R1 MEDIUM (time leak from value).
        kind = (slot["type"] or "static").lower()
        time_val = slot["value"] if kind in {"transient", "dynamic"} else None
        lf = slot["value"] if kind in {"buckling", "vibration", "modal", "frequency"} else None
        return SolutionState(
            step_id=slot["step_id"],
            step_name=slot["type"] or "static",
            time=time_val,
            load_factor=lf,
            available_fields=CalculiXReader._available_fields_for_dicts(
                slot["disp"], slot["stress"]
            ),
        )

    def get_field(
        self, name: CanonicalField, step_id: int
    ) -> Optional[FieldData]:
        self._check_open()
        disp_dict, stress_dict = self._dicts_for_step(step_id)
        if name is CanonicalField.DISPLACEMENT:
            if not disp_dict:
                return None
            return _CalculiXFieldData(
                metadata=self._metadata(name, FieldLocation.NODE, ComponentType.VECTOR_3D),
                node_index=self._mesh.node_index,
                n_nodes=len(self._mesh.node_id_array),
                raw=disp_dict,
                component_extractor=_disp_components,
            )
        if name is CanonicalField.STRESS_TENSOR:
            if not stress_dict:
                return None
            return _CalculiXFieldData(
                metadata=self._metadata(
                    name, FieldLocation.NODE, ComponentType.TENSOR_SYM_3D
                ),
                node_index=self._mesh.node_index,
                n_nodes=len(self._mesh.node_id_array),
                raw=stress_dict,
                component_extractor=_stress_components,
            )
        # Other CanonicalField members not yet wired (STRAIN_TENSOR /
        # REACTION_FORCE / NODAL_COORDINATES / ELEMENT_VOLUME). Returning
        # None per ADR-003 — adapter does not fabricate when the data is
        # not on disk.
        return None

    def close(self) -> None:
        # No native handle held open; flag for sanity checks.
        self._closed = True

    # --- SupportsElementInventory (RFC-001 W6e) --------------------------

    # FRD ``-3`` block stores the element type as an integer code per
    # the CalculiX FRD spec. The Sprint-2 parser stores the code as a
    # string ("1", "2", ...) verbatim. The W6e ``ELEMENT_TYPE_GROUPS``
    # table is keyed on Abaqus-style names (C3D10, S4R, B31, ...) — the
    # cross-solver standard. Translate the FRD codes here so the
    # model_overview library never sees the raw integers.
    #
    # CalculiX FRD type-code → Abaqus name table (from cgx-2.21
    # "frdtypes.txt" + cross-checked against
    # https://github.com/Dhondtguido/CalculiX/blob/master/CalculiX/ccx_2.21/src/frd.c).
    # The integer-to-string map is intentionally narrow — codes the
    # solver does not emit yet (axisymmetric, gap, contact-pair, ...)
    # are absent and pass through unchanged into ``GROUP_OTHER``.
    _FRD_TYPE_CODE_TO_ABAQUS: ClassVar[Mapping[str, str]] = MappingProxyType(
        {
            "1": "C3D8",   # 8-node linear hex
            "2": "C3D6",   # 6-node linear penta (wedge)
            "3": "C3D4",   # 4-node linear tet
            "4": "C3D20",  # 20-node quadratic hex
            "5": "C3D15",  # 15-node quadratic penta
            "6": "C3D10",  # 10-node quadratic tet
            "7": "S3",     # 3-node tri shell
            "8": "S6",     # 6-node tri shell
            "9": "S4",     # 4-node quad shell
            "10": "S8",    # 8-node quad shell
            "11": "B31",   # 2-node lin beam
            "12": "B32",   # 3-node quad beam
        }
    )

    def element_types(self) -> tuple[str, ...]:
        """Return per-element type strings in element-id order.

        Implements ``SupportsElementInventory`` (W6e) so the Layer-4
        model-overview library can render the § 模型概览 section.
        Translates raw FRD integer-coded type strings ("1", "2", ...)
        from the parser to canonical Abaqus-style names ("C3D8",
        "C3D10", "S4R", ...) via :attr:`_FRD_TYPE_CODE_TO_ABAQUS`,
        which is the vocabulary the W6e grouping table consumes. Codes
        not in the table pass through verbatim — the W6e library
        buckets them into ``GROUP_OTHER`` and the engineer sees the
        raw FRD code so they can extend the table if needed.

        Element ordering: sorted by ``element_id`` so the order is
        stable across calls (FRD's internal block order can change
        between solver runs even on the same input). The W6e summary
        only consumes counts, so order does not affect the rendered
        output, but a deterministic order makes mesh-quality follow-
        ups (median element size by type, etc.) reproducible.
        """
        self._check_open()
        elements = self._parsed.elements
        if not elements:
            return ()
        translate = self._FRD_TYPE_CODE_TO_ABAQUS
        return tuple(
            translate.get(elements[eid].element_type, elements[eid].element_type)
            for eid in sorted(elements)
        )

    # --- helpers ---------------------------------------------------------

    def _check_open(self) -> None:
        if self._closed:
            raise RuntimeError(
                "CalculiXReader is closed; create a fresh instance to read again."
            )

    def _dicts_for_step(
        self, step_id: int
    ) -> tuple[dict[int, Any], dict[int, Any]]:
        # Re-run the same disjoint-slot merge walk used by
        # ``solution_states`` and pick the slot whose ``step_id`` matches.
        # ADR-004: no caching — paying the O(N) walk on every call is
        # the cost of forbidding hidden state. N is "number of FRD blocks
        # in the file", typically <10.
        if not self._parsed.increments:
            if step_id == 1:
                return self._parsed.displacements, self._parsed.stresses
            return {}, {}

        merged: list[dict[str, Any]] = []
        for inc in self._parsed.increments:
            inc_fields = self._fields_in_increment(inc)
            slot = self._find_disjoint_slot(merged, inc, inc_fields)
            if slot is None:
                slot = {
                    "step_id": inc.step,
                    "type": inc.type or "static",
                    "value": float(inc.value),
                    "disp": {},
                    "stress": {},
                    "fields": set(),
                }
                merged.append(slot)
            if inc.displacements:
                slot["disp"] = inc.displacements
            if inc.stresses:
                slot["stress"] = inc.stresses
            slot["fields"] |= inc_fields

        for slot in merged:
            if slot["step_id"] == step_id:
                return slot["disp"], slot["stress"]
        return {}, {}

    @staticmethod
    def _available_fields_for_dicts(
        disp_dict: dict[int, Any], stress_dict: dict[int, Any]
    ) -> tuple[CanonicalField, ...]:
        present: list[CanonicalField] = []
        if disp_dict:
            present.append(CanonicalField.DISPLACEMENT)
        if stress_dict:
            present.append(CanonicalField.STRESS_TENSOR)
        return tuple(present)

    def _metadata(
        self,
        name: CanonicalField,
        location: FieldLocation,
        component_type: ComponentType,
    ) -> FieldMetadata:
        source_field_name = {
            CanonicalField.DISPLACEMENT: "DISP",
            CanonicalField.STRESS_TENSOR: "STRESS",
            CanonicalField.STRAIN_TENSOR: "TOSTRAIN",
            CanonicalField.REACTION_FORCE: "FORC",
        }.get(name, name.value)
        return FieldMetadata(
            name=name,
            location=location,
            component_type=component_type,
            unit_system=self._unit_system,
            source_solver=self.SOLVER_NAME,
            source_field_name=source_field_name,
            source_file=self._result_file,
            coordinate_system=CoordinateSystemKind.GLOBAL.value,
            was_averaged="unknown",
        )


# Structural conformance to the ReaderHandle Protocol is verified at
# runtime by the test suite (``test_reader_implements_reader_handle_protocol``).
# We deliberately do NOT assert it at import time — Protocol structural
# checks against a class object (rather than an initialised instance)
# can be inconsistent across Python / typing-extensions versions, and
# we don't want a stricter typing module to break library import.
