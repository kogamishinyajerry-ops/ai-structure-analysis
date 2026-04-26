"""Layer 2 + Layer 3 schema — RFC-001 §4.3.

This package holds the *type definitions only* for the cross-solver
ResultReader abstraction. There is intentionally **no implementation**
here — concrete adapters live under ``app/adapters/{calculix,ansys,...}``
(Layer 1) and domain logic lives under ``app/domain/`` (Layer 3).

The closed-set discipline (RFC ADR-002): ``CanonicalField`` is the
exhaustive vocabulary of physical quantities the system understands.
Adding a member requires an RFC. Open-vocabulary stringly-typed fields
are not allowed.

mypy --strict must pass on this package.
"""

from __future__ import annotations

from .enums import (
    CanonicalElementType,
    CanonicalField,
    ComponentType,
    CoordinateSystemKind,
    FieldLocation,
    UnitSystem,
)
from .quantity import Quantity
from .field_metadata import FieldMetadata
from .field_data import FieldData
from .solution_state import SolutionState
from .domain import BoundaryCondition, Material, Mesh
from .reader_handle import ReaderHandle

__all__ = [
    "BoundaryCondition",
    "CanonicalElementType",
    "CanonicalField",
    "ComponentType",
    "CoordinateSystemKind",
    "FieldData",
    "FieldLocation",
    "FieldMetadata",
    "Material",
    "Mesh",
    "Quantity",
    "ReaderHandle",
    "SolutionState",
    "UnitSystem",
]
