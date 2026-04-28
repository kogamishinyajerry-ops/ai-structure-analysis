"""W6e model-overview summary library (RFC-001 W6e).

Renders the data the DOCX § 模型概况 chapter needs: node count,
element-type distribution (when the adapter implements
:class:`SupportsElementInventory`), bounding-box diagonal in the
mesh's own length unit, and a representative element size estimated
as ``bbox_diag / N^(1/3)``.

Layer-4 service per RFC-001 §4.2 — depends on Layer-2 (ReaderHandle
+ optional capability protocols), never on a concrete adapter type.
Per ADR-003: when the adapter doesn't implement
:class:`SupportsElementInventory`, the renderer omits the element-
type breakdown rather than fabricating one. The roadmap end-state
("DOCX 出现'模型概况: 36 节点 / 10 单元 (HEX8) / 特征尺寸约 25 mm'")
is met when the adapter is CalculiX (which does carry FRD ``-2``
element records) and partially met when the adapter doesn't —
node count + bbox + characteristic size still render, the
``10 单元 (HEX8)`` portion is dropped with a [需工程师确认] flag.

The estimated characteristic length is flagged ``is_estimated=True``
so the DOCX template can render a ``[估算]`` superscript — this is
NOT the actual element edge length (which would require parsing
element connectivity), it's a back-of-envelope ``bbox_diag /
n_nodes^(1/3)`` that gives the right order of magnitude for the
engineer's sanity check.
"""

from __future__ import annotations

import inspect
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Final, Optional

import numpy as np
from app.core.types import (
    ReaderHandle,
    SupportsElementInventory,
    UnitSystem,
)

__all__ = [
    "ModelOverview",
    "ModelOverviewError",
    "summarize_model_overview",
]


_LENGTH_UNIT_BY_SYSTEM: Final[Mapping[UnitSystem, str]] = MappingProxyType(
    {
        UnitSystem.SI: "m",
        UnitSystem.SI_MM: "mm",
        UnitSystem.ENGLISH: "in",
        UnitSystem.UNKNOWN: "unknown",
    }
)


def _invoke_element_inventory(reader: object) -> Any:
    """Call ``reader.element_inventory()`` after checking arity.

    ``runtime_checkable`` Protocols only verify method PRESENCE, not
    signature. A reader with ``element_inventory(self, bucket)`` would
    pass ``isinstance(SupportsElementInventory)`` and raise an
    uncaught TypeError here. Validate at the call boundary so the
    Layer-4 service surfaces a clean ``ModelOverviewError`` with the
    misimplementing class name in the message.
    """
    method = getattr(reader, "element_inventory", None)
    if not callable(method):
        raise ModelOverviewError(
            f"reader of type {type(reader).__name__!r} satisfies "
            f"SupportsElementInventory protocol but element_inventory "
            f"is not callable"
        )
    try:
        sig = inspect.signature(method)
    except (TypeError, ValueError):
        # Built-in / C-implemented method — ``inspect.signature`` can't
        # introspect it, so we fall back to calling and translating any
        # arity-mismatch TypeError into ``ModelOverviewError``. Codex R2
        # PR #103 MEDIUM POC: ``sqlite3.Connection.execute`` (a bound
        # C-extension callable) attached as ``element_inventory`` would
        # leak a raw ``TypeError: execute expected at least 1 argument,
        # got 0`` instead of the promised clean refusal.
        try:
            return method()
        except TypeError as exc:
            raise ModelOverviewError(
                f"reader of type {type(reader).__name__!r} has a "
                f"non-introspectable element_inventory (likely a "
                f"C-extension or built-in callable) that rejected the "
                f"zero-arg call required by SupportsElementInventory: "
                f"{exc}. Adapter contract violation."
            ) from exc
    # Allow *args / **kwargs (the protocol contract leaves room for
    # future kwargs); reject only methods with one or more REQUIRED
    # positional / keyword parameters.
    required = [
        p
        for p in sig.parameters.values()
        if p.default is inspect.Parameter.empty
        and p.kind
        in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        )
    ]
    if required:
        raise ModelOverviewError(
            f"reader of type {type(reader).__name__!r} has "
            f"element_inventory({', '.join(p.name for p in required)}, "
            f"...) — the SupportsElementInventory protocol requires a "
            f"zero-arg method. Adapter contract violation."
        )
    return method()


def _normalise_element_inventory(raw: Any) -> dict[str, int]:
    """Validate-and-normalise a raw ``element_inventory()`` return.

    Codex R1 PR #103 demonstrated three audit-corruption paths:
    non-string keys, float / bool counts, and mutable count objects
    that survive ``dict(...)``. Reject all three at the boundary;
    accept only ``Mapping[str, int]`` with non-negative counts.
    Bool is rejected explicitly even though ``bool`` ⊂ ``int``.
    """
    if not isinstance(raw, Mapping):
        raise ModelOverviewError(
            f"element_inventory() must return a Mapping, got "
            f"{type(raw).__name__}"
        )
    normalised: dict[str, int] = {}
    for key, value in raw.items():
        if not isinstance(key, str):
            raise ModelOverviewError(
                f"element_inventory() keys must be strings (canonical "
                f"element-type labels), got {type(key).__name__} for "
                f"key {key!r}"
            )
        if not key:
            raise ModelOverviewError(
                "element_inventory() keys must be non-empty strings"
            )
        # bool first — bool ⊂ int silently coerces ``True``/``False`` to
        # 1/0, hiding adapter bugs in the audit count.
        if isinstance(value, bool) or not isinstance(value, int):
            raise ModelOverviewError(
                f"element_inventory()[{key!r}] must be a real int "
                f"(non-negative element count), got {value!r} "
                f"({type(value).__name__})"
            )
        if value < 0:
            raise ModelOverviewError(
                f"element_inventory()[{key!r}] must be non-negative, "
                f"got {value!r}"
            )
        # Coerce to plain Python int (defensively handles numpy
        # int subtypes that satisfy ``isinstance(int)``); the
        # snapshot is ``dict[str, int]`` after this.
        normalised[key] = int(value)
    return normalised


class ModelOverviewError(ValueError):
    """Raised when the reader's mesh is structurally unusable for
    overview rendering — empty node array, malformed coordinate
    array, etc. Per ADR-012, the section must cite a non-trivial
    evidence_id; an unsalvageable mesh refuses rather than emitting
    an uncited placeholder."""


# ---------------------------------------------------------------------------
# Public dataclass — what the DOCX renderer consumes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ModelOverview:
    """Aggregated mesh + element data for the DOCX § 模型概况 chapter.

    Field semantics:

    * ``node_count`` — non-negative integer (zero is allowed only
      from the synthetic-empty path; the real wedge raises before
      reaching this state).
    * ``element_inventory`` — ``Mapping[type_label, count]`` from the
      adapter's ``SupportsElementInventory`` implementation, or
      ``None`` if the adapter does not implement that capability.
      ``None`` means "data unknown to this adapter" (renderer flags
      with ``[需工程师确认]``); an empty mapping ``{}`` would mean
      "adapter said zero elements" (different meaning, never produced
      in practice — empty mesh raises in the constructor instead).
    * ``element_count`` — convenience, equals ``sum(element_inventory.values())``
      when the inventory is known, ``None`` otherwise.
    * ``bbox_diag`` — Euclidean diagonal of the node-coordinate
      bounding box, in the mesh's own length unit.
    * ``characteristic_length`` — ``bbox_diag / max(node_count, 1)**(1/3)``,
      a back-of-envelope element size for the engineer's sanity check.
      Always paired with ``is_estimated=True`` so the renderer flags it.
    * ``length_unit`` — pre-resolved string for the unit (e.g. ``"mm"``);
      pulled from :data:`_LENGTH_UNIT_BY_SYSTEM` so the DOCX renderer
      doesn't need to import ``UnitSystem``.
    * ``unit_system`` — the canonical enum, retained for the renderer
      to switch on if it wants to (e.g. flag ``UNKNOWN`` with a
      [需工程师确认] tag).

    All fields are deeply immutable: ``element_inventory`` (when
    present) is wrapped in ``MappingProxyType`` so the renderer can't
    corrupt the audit trail between extraction and template
    substitution.
    """

    node_count: int
    element_inventory: Optional[Mapping[str, int]]
    element_count: Optional[int]
    bbox_diag: float
    characteristic_length: float
    length_unit: str
    unit_system: UnitSystem
    is_estimated: bool = True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def summarize_model_overview(reader: ReaderHandle) -> ModelOverview:
    """Inspect ``reader.mesh`` (+ ``element_inventory()`` if the
    adapter implements :class:`SupportsElementInventory`) and return
    a frozen :class:`ModelOverview`.

    The function is pure observation: no field materialisation, no
    heavy I/O. The mesh and element inventory are typically already
    parsed by the time the report draft is being generated, so this
    runs in microseconds.

    Refusal contract:

    * Empty mesh (no nodes) → :class:`ModelOverviewError`. A report
      with zero nodes is not a structural-analysis report, full stop.
    * Coordinate array with the wrong shape (not ``(N, 3)``) →
      :class:`ModelOverviewError`. Defensive: a misshaped array
      indicates an upstream Layer-1 / Layer-2 contract bug, not a
      legitimate report.

    The function does NOT raise on missing element inventory — that's
    a known optional capability per the protocol design. The renderer
    decides how to flag the absence (typically ``[需工程师确认]``).
    """
    mesh = reader.mesh

    # Layer-2 contract: node_id_array is a 1-D int64 array, never None.
    node_ids = mesh.node_id_array
    node_count = int(node_ids.size)
    if node_count == 0:
        raise ModelOverviewError(
            "reader.mesh has zero nodes; a structural-analysis report "
            "with no nodes is contractually meaningless. Check the "
            "Layer-1 adapter — empty meshes should refuse at parse "
            "time, not propagate into draft generation."
        )

    coords = mesh.coordinates
    if coords.ndim != 2 or coords.shape[1] != 3 or coords.shape[0] != node_count:
        raise ModelOverviewError(
            f"reader.mesh.coordinates has shape {coords.shape!r}; "
            f"expected ({node_count}, 3). The Layer-1 adapter is "
            f"violating the Mesh protocol — fix the adapter, do not "
            f"work around it here."
        )

    # Bounding box diagonal: ``max - min`` along each axis, then
    # Euclidean norm of the resulting (3,) vector.
    bbox_min = coords.min(axis=0)
    bbox_max = coords.max(axis=0)
    diag_vec = bbox_max - bbox_min
    bbox_diag = float(np.linalg.norm(diag_vec))

    # Characteristic length per the W6 roadmap: ``bbox_diag / N^(1/3)``.
    # Caps at ``max(N, 1)`` to avoid division-by-zero at the boundary
    # case (already excluded by the empty-mesh refusal above, but
    # belt + braces).
    characteristic_length = bbox_diag / (max(node_count, 1) ** (1.0 / 3.0))

    # Element inventory is OPTIONAL per the protocol design; a reader
    # that doesn't implement ``SupportsElementInventory`` produces
    # ``None`` here, and the renderer flags it with [需工程师确认].
    #
    # Codex R1 PR #103 HIGH: ``runtime_checkable`` only proves method
    # PRESENCE, not signature or return shape. Three demonstrated
    # protocol-spoof paths:
    #   a. wrong arity → ``element_inventory(required_bucket)`` passes
    #      isinstance, raises TypeError at call time
    #   b. wrong types → ``{1: 2.5}`` passes silently, produces
    #      ``element_count = 2.5`` (audit corruption)
    #   c. mutable values → ``{"HEX8": MutableCount(5)}`` survives
    #      ``dict(raw_inventory)`` and can mutate the snapshot
    # Fix: validate the bound method is zero-arg, require a real
    # Mapping, normalise to ``dict[str, int]`` with non-negative ints
    # rejected for bool/non-finite, then wrap in MappingProxyType.
    element_inventory: Optional[Mapping[str, int]]
    element_count: Optional[int]
    if isinstance(reader, SupportsElementInventory):
        raw_inventory = _invoke_element_inventory(reader)
        normalised = _normalise_element_inventory(raw_inventory)
        element_inventory = MappingProxyType(normalised)
        element_count = sum(element_inventory.values())
    else:
        element_inventory = None
        element_count = None

    unit_system = mesh.unit_system
    length_unit = _LENGTH_UNIT_BY_SYSTEM.get(unit_system, "unknown")

    return ModelOverview(
        node_count=node_count,
        element_inventory=element_inventory,
        element_count=element_count,
        bbox_diag=bbox_diag,
        characteristic_length=characteristic_length,
        length_unit=length_unit,
        unit_system=unit_system,
        is_estimated=True,
    )
