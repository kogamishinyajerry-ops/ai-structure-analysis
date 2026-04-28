"""ReaderHandle — Layer 2 contract that every solver adapter implements.

RFC-001 §4.3 + §4.2 layer rules:
  * Layer 1 adapters (``app.adapters.*``) implement this Protocol.
  * Layer 3 (``app.domain.*``) consumes ``ReaderHandle`` only — never a
    concrete adapter type.
  * Layer 4 (``app.services.report.*``) goes through Layer 3 and never
    sees ``ReaderHandle`` directly.

Sub-protocols (e.g. ``SupportsElementDeletion``) declare optional
capabilities for non-canonical data — element erosion, contact-pair
state, etc. Adding such data to ``CanonicalField`` would expand the
closed enum and require an RFC; a runtime-checkable sub-protocol lets
Layer 3 feature-detect the capability without leaking the concrete
adapter type.
"""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

import numpy as np
import numpy.typing as npt

from .enums import CanonicalField
from .field_data import FieldData
from .solution_state import SolutionState
from .domain import BoundaryCondition, Material, Mesh


@runtime_checkable
class ReaderHandle(Protocol):
    """Cross-solver reader contract.

    Every property is a getter — adapters MUST NOT mutate state across
    calls (ADR-004 forbids hidden caches and IO optimisation in Layer 1).
    ``close`` is for releasing native handles (e.g. a held HDF5 file).
    """

    @property
    def mesh(self) -> Mesh: ...

    @property
    def materials(self) -> dict[str, Material]: ...

    @property
    def boundary_conditions(self) -> list[BoundaryCondition]: ...

    @property
    def solution_states(self) -> list[SolutionState]: ...

    def get_field(
        self,
        name: CanonicalField,
        step_id: int,
    ) -> Optional[FieldData]:
        """Return the field for ``(name, step_id)``, or ``None`` if the
        adapter has nothing on disk for that combination.

        The adapter MUST NOT fabricate a zero-valued ``FieldData`` to
        paper over a missing dataset (ADR-003).
        """
        ...

    def close(self) -> None: ...


@runtime_checkable
class SupportsElementDeletion(Protocol):
    """Optional Layer-2 capability: per-step element-alive flags.

    Adapters that read solvers with element erosion (OpenRadioss
    Johnson-Cook failure, LS-DYNA *MAT_ADD_EROSION, etc.) implement
    this. Layer-3 ballistic derivations feature-detect it via
    ``isinstance(reader, SupportsElementDeletion)`` rather than
    importing the concrete adapter type — keeps the Layer-3 → Layer-1
    arrow forbidden by RFC-001 §4.2.

    Returns: int8 array of shape ``(n_facets,)``; 1 = alive, 0 =
    deleted/eroded. Raises ``KeyError`` for unknown step IDs.
    """

    def deleted_facets_for(self, step_id: int) -> "npt.NDArray[np.int8]": ...


@runtime_checkable
class SupportsElementInventory(Protocol):
    """Optional Layer-2 capability: per-element type strings (RFC-001 W6e).

    Adapters that can enumerate element types (CalculiX FRD's
    ``-3``-block ``element_type`` field, OpenRadioss A-frame mesh
    metadata, Abaqus .inp ``*ELEMENT, TYPE=`` keywords, etc.)
    implement this. The W6e ``model_overview`` library feature-
    detects it via ``isinstance(reader, SupportsElementInventory)``
    so the § 模型概览 section gracefully degrades to "node count
    only" on adapters that haven't yet wired the capability.

    Returns:
        * ``tuple[str, ...]`` of solver-native element-type identifiers
          (e.g. ``("C3D10", "C3D10", "S4R", ...)``) when the adapter
          has fully-parsed element-inventory data. One entry per
          element, in the adapter's natural enumeration order. The
          string vocabulary is solver-native — no cross-solver
          normalization happens at Layer 2.
        * ``None`` when the underlying solver result file is missing
          the element block (e.g. CalculiX ``.frd`` written with
          ``--no-element``, partial FRD parse, or any case where the
          adapter cannot reliably enumerate element types). The
          ``ModelOverview`` consumer treats this as "inventory
          unknown" rather than fabricating "0 elements".

    The contract is intentionally three-state — adapter declares the
    capability AND returns either real data OR explicit ``None`` —
    rather than two-state (declares + always returns a tuple). The
    three-state form is what lets the W6e.2 DOCX renderer
    distinguish "really zero elements (confirmed)" from "inventory
    not parsed for this run". A capable adapter returning the empty
    tuple ``()`` means the mesh genuinely has no elements (degenerate
    but valid). A capable adapter returning ``None`` means the
    inventory could not be determined.

    The library that consumes this (``model_overview.summarize_model``)
    is responsible for human-readable grouping in the DOCX (e.g.
    ``"C3D10"`` → ``"四面体 (C3D10)"``).
    """

    def element_types(self) -> tuple[str, ...] | None: ...
