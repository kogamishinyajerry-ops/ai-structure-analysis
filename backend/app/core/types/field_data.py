"""FieldData — lazy field-value contract — RFC-001 §4.3."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from .field_metadata import FieldMetadata

if TYPE_CHECKING:
    import numpy as np
    import numpy.typing as npt


@runtime_checkable
class FieldData(Protocol):
    """Lazy access to a field's values.

    ``metadata`` is read eagerly (required for index / sanity checks).
    ``values()`` and ``at_nodes()`` trigger IO. ADR-004 forbids adapter
    caching — each call may re-read the underlying file.

    ``at_nodes()`` is required for fields whose natural location is the
    integration point: it returns the unaveraged per-element-at-node
    extrapolation, leaving averaging to Layer 3 (§4.6 trap #2).
    """

    metadata: FieldMetadata

    def values(self) -> "npt.NDArray[np.float64]":
        """Raw values in their natural location (NODE / IP / centroid / ELEMENT)."""
        ...

    def at_nodes(self) -> "npt.NDArray[np.float64]":
        """Values extrapolated/located at mesh nodes, *unaveraged*."""
        ...
