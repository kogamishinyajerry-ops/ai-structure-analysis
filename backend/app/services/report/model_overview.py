"""W6e model-overview summary library (RFC-001 W6e).

Produces a ``ModelOverview`` dataclass for the DOCX § 模型概览
(Model Overview) section: total node count, total element count,
and a per-element-type breakdown grouped into engineer-readable
buckets (四面体 / 六面体 / 壳 / 梁 / 其他).

Why a separate library (mirrors W6b/W6c/W6d shape):

* Pure data: no IO, no derivation. Counts are coordinate-frame
  statistics, not constitutive judgments — ADR-001 / ADR-020 do not
  forbid them.
* Adapter-agnostic: feature-detects the optional Layer-2 capability
  ``SupportsElementInventory`` (added alongside this library in
  ``app.core.types.reader_handle``). Adapters that haven't wired the
  capability yet (OpenRadioss W7b, Ansys / Abaqus stubs) gracefully
  degrade to "node count only" — the DOCX renderer surfaces a
  "无单元清单 [需工程师确认]" placeholder rather than fabricating a
  count.

Element-type grouping is a UI concern only — the underlying
``type_counts`` map keeps the solver-native type strings verbatim
(e.g. ``"C3D10"``) so a future "show raw FRD types" toggle in the
report renderer can read them without re-parsing.

Refusal contract:

* ``ModelOverviewError`` (subclass of ``ValueError``) when the
  reader returns malformed data — e.g. an ``element_types()`` tuple
  whose length does not match what the mesh implies, or a non-string
  type token. The DOCX render path treats this as a hard failure
  (no silent fallback to "0 elements") because a malformed inventory
  is more dangerous than a missing one.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from app.core.types import ReaderHandle, SupportsElementInventory

__all__ = [
    "ELEMENT_TYPE_GROUPS",
    "GROUP_OTHER",
    "ModelOverview",
    "ModelOverviewError",
    "summarize_model",
]


class ModelOverviewError(ValueError):
    """Raised when the reader returns malformed inventory data.

    Subclasses ``ValueError`` so callers can catch this and the
    constructor argument-validation errors uniformly. Mirrors the
    ``BCSummaryError`` / ``AllowableStressError`` pattern from W6b/W6d.
    """


# ---------------------------------------------------------------------------
# Element-type grouping table
# ---------------------------------------------------------------------------

# Bucket label for solver-native types not in the table below. Kept as a
# module-level constant so the renderer's "fallback group" footnote can
# reference the same string.
GROUP_OTHER: Final[str] = "其他"


# Open-set table mapping solver-native element type strings to
# engineer-facing group labels. The mapping is intentionally narrow —
# adding a new family (cohesive elements, gaskets, springs) is a
# library-only PR, not an ADR. Unknown types fall into ``GROUP_OTHER``.
#
# Naming conventions cross-checked:
#   * CalculiX / Abaqus: C3D10 / C3D8 / S4 / S4R / B31 etc. (Abaqus manual
#     §27.1 element library — type prefix encodes shape).
#   * OpenRadioss A-frame (W7b reader): currently does not declare
#     ``SupportsElementInventory``; entries reserved for the W7b PR
#     that adds it.
#   * Ansys (.rst W7-future): n/a.
#
# A solver-native string maps to *exactly one* group; if a future
# adapter emits a string already in the table, the engineer sees the
# expected group label without a library change.
ELEMENT_TYPE_GROUPS: Final[Mapping[str, str]] = MappingProxyType(
    {
        # --- 四面体 / Tetrahedra -------------------------------------
        "C3D4": "四面体",      # Abaqus / CalculiX 4-node lin tet
        "C3D10": "四面体",     # 10-node quadratic tet (most common)
        "C3D10M": "四面体",    # Abaqus modified quadratic tet
        # --- 六面体 / Hexahedra --------------------------------------
        "C3D8": "六面体",      # 8-node lin hex
        "C3D8R": "六面体",     # reduced-integration hex
        "C3D8I": "六面体",     # incompatible-modes hex
        "C3D20": "六面体",     # 20-node quad hex
        "C3D20R": "六面体",    # reduced-integration quad hex
        # --- 楔形 / Wedge --------------------------------------------
        "C3D6": "楔形",        # 6-node lin wedge
        "C3D15": "楔形",       # 15-node quad wedge
        # --- 壳 / Shell ----------------------------------------------
        "S3": "壳",            # 3-node lin tri shell
        "S3R": "壳",
        "S4": "壳",            # 4-node lin quad shell
        "S4R": "壳",
        "S6": "壳",            # 6-node quad tri shell
        "S8": "壳",            # 8-node quad shell
        "S8R": "壳",
        # --- 梁 / Beam -----------------------------------------------
        "B31": "梁",           # 3D 2-node lin beam
        "B32": "梁",           # 3D 3-node quad beam
        "B33": "梁",           # 3D 2-node Hermite beam
    }
)


# ---------------------------------------------------------------------------
# Public dataclass — what the DOCX renderer consumes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ModelOverview:
    """Aggregated mesh-level statistics for the DOCX § 模型概览 section.

    Field semantics:

    * ``total_nodes`` — total node count from the Mesh Protocol
      (``len(reader.mesh.node_id_array)``). Always populated; the Mesh
      Protocol is mandatory.
    * ``total_elements`` — total element count. ``0`` when the reader
      does not declare ``SupportsElementInventory`` AND the renderer
      should surface the "无单元清单 [需工程师确认]" placeholder. Use
      ``has_inventory`` to disambiguate "really zero" from "unknown".
    * ``type_counts`` — solver-native type string → count, e.g.
      ``{"C3D10": 1234, "S4R": 56}``. Empty when ``has_inventory`` is
      False.
    * ``group_counts`` — bucket label → count, e.g. ``{"四面体": 1234,
      "壳": 56}``. Engineer-facing aggregation of ``type_counts``;
      types not in ``ELEMENT_TYPE_GROUPS`` bucket into
      :data:`GROUP_OTHER`.
    * ``has_inventory`` — True when the adapter declared
      ``SupportsElementInventory`` AND ``element_types()`` returned
      a tuple (possibly empty). False when either the capability is
      absent OR the capability returned ``None`` to signal "inventory
      not available for this instance" (Codex R1 HIGH on PR #109,
      three-state contract). The DOCX renderer uses this flag to
      decide whether to render the breakdown table or the "no
      inventory" placeholder; without it, "0 elements" would be
      structurally indistinguishable from "inventory not available".

    All fields are deeply immutable (the maps are
    ``MappingProxyType``) so the renderer cannot mutate the audit
    trail between extraction and template substitution.
    """

    total_nodes: int
    total_elements: int
    type_counts: Mapping[str, int]
    group_counts: Mapping[str, int]
    has_inventory: bool


# ---------------------------------------------------------------------------
# Factory — feature-detects SupportsElementInventory
# ---------------------------------------------------------------------------


def _no_inventory(total_nodes: int) -> ModelOverview:
    """Build the canonical "inventory unavailable" ModelOverview.

    Used both by the capability-absent path (adapter doesn't declare
    ``SupportsElementInventory``) and the capability-returns-None path
    (adapter declared the capability but the underlying solver result
    file did not carry element data — Codex R1 HIGH on PR #109).
    """
    return ModelOverview(
        total_nodes=total_nodes,
        total_elements=0,
        type_counts=MappingProxyType({}),
        group_counts=MappingProxyType({}),
        has_inventory=False,
    )


def summarize_model(reader: ReaderHandle) -> ModelOverview:
    """Build a :class:`ModelOverview` from a Layer-2 ReaderHandle.

    Always reads ``reader.mesh.node_id_array`` for the node count.
    Element data is gated on ``isinstance(reader, SupportsElementInventory)``:

    * Capability absent → ``has_inventory=False``,
      ``total_elements=0``, no fabricated counts. DOCX renderer
      surfaces "no inventory" placeholder.
    * Capability present and ``element_types()`` returns ``None`` →
      same shape as capability-absent. The adapter explicitly
      reported "the underlying file did not include element data"
      (e.g. CalculiX FRD with no ``-3`` block). Per Codex R1 HIGH
      on PR #109, this three-state contract is what lets the W6e.2
      DOCX renderer distinguish "really zero (confirmed)" from
      "inventory not parsed for this run".
    * Capability present and returns a ``tuple`` → bucketed into
      ``type_counts`` + ``group_counts``, ``has_inventory=True``.
      A zero-length tuple is permitted and produces
      ``total_elements=0, has_inventory=True`` — "0 elements
      (confirmed)" rather than "inventory unknown".

    Raises :class:`ModelOverviewError` when a capable adapter returns
    malformed data:

    * ``element_types`` is not callable.
    * Calling it raises an unexpected exception (signature mismatch,
      broken adapter, etc.).
    * The result is neither ``None`` nor a ``tuple``.
    * The result contains a non-string entry.
    * The result contains an empty, whitespace-only, or
      leading/trailing-whitespace-padded string. (Padding is rejected
      rather than normalized: silently accepting ``" C3D10 "`` would
      produce a stray bucket in the DOCX that the engineer can't
      reconcile back to any solver-deck entry.)
    """
    node_id_array = reader.mesh.node_id_array
    total_nodes = int(len(node_id_array))

    if not isinstance(reader, SupportsElementInventory):
        return _no_inventory(total_nodes)

    # Codex R1 MEDIUM: ``@runtime_checkable`` Protocol checks
    # attribute presence, not callability or signature. Validate
    # callability + wrap unexpected invocation errors so a malformed
    # adapter surfaces as ``ModelOverviewError`` rather than a raw
    # ``TypeError``/``AttributeError`` from deep inside the call.
    #
    # Codex R2 MEDIUM: ``getattr(reader, "element_types", None)`` must
    # also run inside the ``try`` because ``element_types`` may be a
    # ``@property`` whose getter raises (e.g. an adapter holding an
    # unrecoverable state). Pulling the attribute access into the
    # same wrap so descriptor-side errors come out canonicalised too.
    try:
        fn = getattr(reader, "element_types", None)
        if not callable(fn):
            raise ModelOverviewError(
                f"reader.element_types is not callable, got "
                f"{type(fn).__name__}"
            )
        types = fn()
    except ModelOverviewError:
        raise
    except Exception as exc:
        raise ModelOverviewError(
            f"reader.element_types raised "
            f"{type(exc).__name__}: {exc}"
        ) from exc

    if types is None:
        # Adapter explicitly declared "inventory unavailable for this
        # instance". Same DOCX shape as the capability-absent case.
        return _no_inventory(total_nodes)

    if not isinstance(types, tuple):
        raise ModelOverviewError(
            f"reader.element_types() must return tuple[str, ...] | None, "
            f"got {type(types).__name__}"
        )

    # Validate every entry before counting so a malformed adapter
    # surfaces the exact bad index rather than ending up as a stray
    # entry in ``type_counts``.
    for idx, t in enumerate(types):
        if not isinstance(t, str):
            raise ModelOverviewError(
                f"reader.element_types()[{idx}] must be a string, got "
                f"{type(t).__name__}"
            )
        if not t.strip():
            raise ModelOverviewError(
                f"reader.element_types()[{idx}] is empty / whitespace-only"
            )
        # Codex R1 LOW: refuse leading/trailing whitespace explicitly
        # rather than silently normalizing. Otherwise a malformed
        # adapter that emits ``" C3D10 "`` would land in a separate
        # ``GROUP_OTHER`` bucket the engineer can't reconcile back to
        # the deck.
        if t != t.strip():
            raise ModelOverviewError(
                f"reader.element_types()[{idx}]={t!r} has leading or "
                f"trailing whitespace; adapter must emit canonical tokens"
            )

    type_counter: Counter[str] = Counter(types)
    group_counter: Counter[str] = Counter()
    for type_name, count in type_counter.items():
        group = ELEMENT_TYPE_GROUPS.get(type_name, GROUP_OTHER)
        group_counter[group] += count

    return ModelOverview(
        total_nodes=total_nodes,
        total_elements=int(len(types)),
        # Render type_counts in sorted-by-key order so the DOCX table
        # is stable across runs (Counter is insertion-ordered, which
        # would couple the rendered output to FRD parser ordering).
        type_counts=MappingProxyType(dict(sorted(type_counter.items()))),
        group_counts=MappingProxyType(dict(sorted(group_counter.items()))),
        has_inventory=True,
    )
