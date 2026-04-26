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

from pathlib import Path
from typing import Any, Callable, Optional

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
        out = np.zeros((self._n_nodes, max(self._cols, 1)), dtype=np.float64)
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
        # block is announced with its own header. Layer-2 ``step_id``
        # is the CalculiX *step* number (``inc.step``), not the parser's
        # sequential ``index`` — so we collapse increments sharing the
        # same step into a single ``SolutionState`` whose
        # ``available_fields`` is the union of theirs.
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

        # Collapse on (type, value) — Sprint-2 parser may emit one
        # increment per .frd block (DISP / STRESS / TOSTRAIN) and stamp
        # them with sequential ``step`` values even when they belong to
        # the same logical CalculiX step. Two increments with identical
        # (type, value) — e.g. ('static', 1.0) — are the same step.
        merged: list[dict[str, Any]] = []
        seen: dict[tuple[str, float], int] = {}
        for inc in increments:
            key = (inc.type or "static", float(inc.value))
            if key in seen:
                slot = merged[seen[key]]
            else:
                seen[key] = len(merged)
                merged.append(
                    {
                        "step_id": inc.step,
                        "type": inc.type or "static",
                        "value": inc.value,
                        "disp": {},
                        "stress": {},
                    }
                )
                slot = merged[-1]
            if inc.displacements:
                slot["disp"] = inc.displacements
            if inc.stresses:
                slot["stress"] = inc.stresses

        return [
            SolutionState(
                step_id=slot["step_id"],
                step_name=slot["type"] or "static",
                time=slot["value"] if (slot["type"] or "") == "static" else None,
                load_factor=slot["value"] if (slot["type"] or "") == "buckling" else None,
                available_fields=self._available_fields_for_dicts(
                    slot["disp"], slot["stress"]
                ),
            )
            for slot in merged
        ]

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

    # --- helpers ---------------------------------------------------------

    def _check_open(self) -> None:
        if self._closed:
            raise RuntimeError(
                "CalculiXReader is closed; create a fresh instance to read again."
            )

    def _dicts_for_step(
        self, step_id: int
    ) -> tuple[dict[int, Any], dict[int, Any]]:
        # Resolve ``step_id`` against the merged ``solution_states``
        # representation (NOT the raw ``inc.step``) — see the merge
        # rationale in ``solution_states``.
        states = self.solution_states
        target = next((s for s in states if s.step_id == step_id), None)
        if target is None:
            return {}, {}
        # Walk increments accepting all that match the target's identity.
        target_key = (target.step_name, target.time if target.time is not None else target.load_factor)
        disp: dict[int, Any] = {}
        stress: dict[int, Any] = {}
        for inc in self._parsed.increments:
            inc_key = (inc.type or "static", float(inc.value))
            target_value = target_key[1] if target_key[1] is not None else float("nan")
            if inc_key != (target_key[0], float(target_value) if target_value == target_value else inc.value):
                continue
            if inc.displacements:
                disp = inc.displacements
            if inc.stresses:
                stress = inc.stresses
        if disp or stress:
            return disp, stress
        # Final fallback: top-level (single-static-step .frd, no increments)
        if not self._parsed.increments and step_id == 1:
            return self._parsed.displacements, self._parsed.stresses
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
