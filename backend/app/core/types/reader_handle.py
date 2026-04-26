"""ReaderHandle — Layer 2 contract that every solver adapter implements.

RFC-001 §4.3 + §4.2 layer rules:
  * Layer 1 adapters (``app.adapters.*``) implement this Protocol.
  * Layer 3 (``app.domain.*``) consumes ``ReaderHandle`` only — never a
    concrete adapter type.
  * Layer 4 (``app.services.report.*``) goes through Layer 3 and never
    sees ``ReaderHandle`` directly.
"""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

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
