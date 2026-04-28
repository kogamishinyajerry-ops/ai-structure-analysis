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

from collections.abc import Mapping
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
    """Optional Layer-2 capability: element-type inventory.

    Adapters that parsed an element block from the solver result file
    (CalculiX FRD ``-1`` / ``-2`` records, OpenRadioss ``.h3d``
    element groups, etc.) implement this. Layer-4 model-overview
    rendering feature-detects via
    ``isinstance(reader, SupportsElementInventory)`` rather than
    importing the concrete adapter type — keeps the Layer-4 → Layer-1
    arrow forbidden by RFC-001 §4.2.

    Returns: ``Mapping[str, int]`` keyed by canonical element-type
    label as the solver named it (``"HEX8"``, ``"TET4"``, ``"S4R"``,
    etc.); value is the count of elements of that type. The mapping
    is ordered (``dict``-style) so the renderer can present the
    distribution in a stable order — typically descending by count
    or in source order, at the adapter's discretion.

    The implementation MUST return a fresh / immutable mapping per
    call so callers can iterate without worrying about mid-iteration
    mutation.
    """

    def element_inventory(self) -> Mapping[str, int]: ...
