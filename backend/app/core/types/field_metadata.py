"""FieldMetadata — RFC-001 §4.3."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Union

from .enums import (
    CanonicalField,
    ComponentType,
    FieldLocation,
    UnitSystem,
)


@dataclass(frozen=True)
class FieldMetadata:
    """Provenance + shape + units for a single physical field.

    Every value an adapter exposes carries one of these. Layer 3 reads
    only ``FieldMetadata`` plus ``FieldData`` — never the underlying
    solver-specific file format.

    ``coordinate_system`` is one of the strings ``"global"``,
    ``"local"``, or ``"nodal_local"`` (kept stringly to support
    solver-specific local-CS labels later without enum churn).

    ``was_averaged`` is ``True``, ``False``, or the string ``"unknown"``
    — adapters that cannot tell must say ``"unknown"``, not lie (ADR-003).
    """

    name: CanonicalField
    location: FieldLocation
    component_type: ComponentType
    unit_system: UnitSystem
    source_solver: str
    source_field_name: str
    source_file: Path
    coordinate_system: str
    was_averaged: Union[bool, str]
