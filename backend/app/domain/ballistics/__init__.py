"""Layer-3 ballistic derivations — RFC-001 §6.4 W7d.

Pure derivations on top of Layer-2 reader Protocols. Two tiers:

Tier 1 — pure-array helpers
    Take ``numpy`` arrays directly; no reader dependency. These exist
    so callers can compose derivations on *synthesised* data (Layer-3
    pipelines, what-if studies) and so unit tests can run without the
    optional vortex-radioss extra installed.

Tier 2 — reader-aware orchestrators
    Take a ``ReaderHandle`` (and optionally ``SupportsElementDeletion``
    when erosion data is needed) plus a list of ``step_id``s, and
    return aggregates over time. These are the functions Layer-4
    DOCX templates and Layer-2 viz pipelines actually call.

ADR-001 reminder: every derivation lives HERE (Layer 3) — adapters
must NOT compute eroded fractions, perforation flags, max-disp
trajectories, or anything else derived from raw arrays. The
OpenRadioss adapter's narrow ADR-001 carve-out (DISPLACEMENT as
``coorA(t) - coorA(0)``) is a coordinate-frame re-expression, not a
ballistic derivation; it lands here unchanged.

The closed-set discipline (ADR-002) applies: ``CanonicalField`` is
exhaustive, and ballistic-specific quantities (eroded count,
perforation event step, etc.) are *derived* — they are not new
``CanonicalField`` members. Layer 4 surfaces them as named columns in
the ballistic-summary DOCX template (W7f).

Scope of v1 (W7d):
    * eroded element count + history + fraction
    * perforation-event step (first step with any erosion)
    * displacement-magnitude history (max |u| per step, optionally
      restricted to a node subset — e.g. plate-only)

Out of scope (deferred to W7d-v2 once GS-101 lands):
    * residual velocity (needs projectile node tagging)
    * crater geometry (needs facet-connectivity analysis)
    * full-perforation verdict (needs through-thickness erosion path)
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import numpy.typing as npt

from ...core.types import (
    CanonicalField,
    ReaderHandle,
    SupportsElementDeletion,
)

__all__ = [
    "count_alive",
    "count_eroded",
    "eroded_fraction",
    "max_displacement_magnitude",
    "eroded_history",
    "perforation_event_step",
    "displacement_history",
]


# ---------------------------------------------------------------------------
# Reader-input validation (shared by Tier 2)
# ---------------------------------------------------------------------------


def _validate_step_ids(reader: ReaderHandle, step_ids: list[int]) -> None:
    """All ``step_ids`` must be advertised by ``reader.solution_states``.

    Codex R1 finding: without this, an unknown step_id silently becomes
    "field unavailable" (because ``get_field`` returns ``None`` for both
    unknown-step AND known-step-with-no-field per ADR-003). Plots and
    DOCX summaries would then plot a flat zero where the engineer
    expects a hard failure. Distinguishing unknown-step at the orchestrator
    level keeps the API ergonomic — Tier 1 helpers keep their own
    validation contracts.
    """
    known = {s.step_id for s in reader.solution_states}
    bad = [sid for sid in step_ids if sid not in known]
    if bad:
        raise KeyError(
            f"step_id(s) {bad!r} not in reader.solution_states "
            f"(known: {sorted(known)!r})"
        )


def _validate_node_indices(
    node_indices: npt.NDArray[np.int64], n_nodes: int
) -> None:
    """``node_indices`` must be 1-D integer array with values in
    ``[0, n_nodes)``. Codex R1 finding: numpy advanced indexing is
    happy to silently wrap negative indices and to broadcast 2-D
    inputs — both produce *plausible-looking* but semantically wrong
    answers. The mesh contract (``Mesh.node_id_array`` vs
    ``Mesh.node_index``) explicitly separates external IDs from dense
    array positions, so passing the wrong one is a real footgun for
    downstream W7c viz / W7f DOCX callers.
    """
    if node_indices.ndim != 1:
        raise ValueError(
            f"node_indices must be 1-D; got shape {node_indices.shape}"
        )
    if not np.issubdtype(node_indices.dtype, np.integer):
        raise ValueError(
            f"node_indices must be integer dtype; got {node_indices.dtype}"
        )
    if node_indices.size == 0:
        # Allow empty subset — caller will get max=0.0 from
        # max_displacement_magnitude, which is consistent with the
        # documented empty-input behaviour.
        return
    if int(node_indices.min()) < 0:
        raise ValueError(
            f"node_indices must be non-negative (these are 0-based row "
            f"positions, not external node IDs); got "
            f"min={int(node_indices.min())}"
        )
    if int(node_indices.max()) >= n_nodes:
        raise ValueError(
            f"node_indices out of bounds for mesh with {n_nodes} nodes; "
            f"got max={int(node_indices.max())}"
        )


# ---------------------------------------------------------------------------
# Tier 1 — pure-array helpers
# ---------------------------------------------------------------------------


def _validate_flags(flags: npt.NDArray[np.int8]) -> None:
    """``flags`` must be 1-D int8 with values in ``{0, 1}``."""
    if flags.ndim != 1:
        raise ValueError(
            f"element-deletion flags must be 1-D; got shape {flags.shape}"
        )
    if flags.dtype != np.int8:
        raise ValueError(
            f"element-deletion flags must be int8 per "
            f"SupportsElementDeletion contract; got dtype {flags.dtype}"
        )
    # Don't iterate — just check unique set; on degenerate fixtures this is
    # a 1-element call. Callers MUST NOT invent values outside {0, 1}.
    bad = ~((flags == 0) | (flags == 1))
    if bool(bad.any()):
        raise ValueError(
            "element-deletion flags must be 0 (deleted) or 1 (alive); "
            f"got values {sorted(np.unique(flags[bad]).tolist())}"
        )


def count_alive(flags: npt.NDArray[np.int8]) -> int:
    """Number of facets still alive at this step (``flags == 1``)."""
    _validate_flags(flags)
    return int(flags.sum())


def count_eroded(flags: npt.NDArray[np.int8]) -> int:
    """Number of facets deleted/eroded at this step (``flags == 0``)."""
    _validate_flags(flags)
    return int(flags.size - flags.sum())


def eroded_fraction(flags: npt.NDArray[np.int8]) -> float:
    """Fraction in ``[0, 1]`` of facets deleted at this step.

    Returns 0.0 for an empty array — there's nothing to erode in a
    zero-facet case. (Callers depending on perforation logic should
    pre-check ``flags.size > 0``; this function does not raise on
    empty input because it is more often a degenerate path than a
    bug.)
    """
    _validate_flags(flags)
    if flags.size == 0:
        return 0.0
    return float(flags.size - flags.sum()) / float(flags.size)


def max_displacement_magnitude(disp: npt.NDArray[np.float64]) -> float:
    """Max nodal displacement magnitude ``max ||u_i||`` over a ``(N,3)``
    field array. Returns 0.0 for empty input (degenerate case)."""
    if disp.ndim != 2 or disp.shape[1] != 3:
        raise ValueError(
            f"displacement array must have shape (N, 3); got {disp.shape}"
        )
    if disp.shape[0] == 0:
        return 0.0
    return float(np.max(np.linalg.norm(disp, axis=1)))


# ---------------------------------------------------------------------------
# Tier 2 — reader-aware orchestrators
# ---------------------------------------------------------------------------


def eroded_history(
    reader: SupportsElementDeletion,
    step_ids: list[int],
) -> dict[int, int]:
    """Per-step eroded-facet count.

    Returns a dict ``{step_id: count_eroded}``. The reader must
    satisfy ``SupportsElementDeletion`` — Layer 4 callers should
    feature-detect via ``isinstance`` first and skip this section in
    DOCX/viz output if the active adapter does not implement it
    (e.g. CalculiX has no element erosion).

    Unknown ``step_id``s raise ``KeyError`` via the underlying
    ``deleted_facets_for`` per the ``SupportsElementDeletion``
    Protocol contract. We deliberately do NOT pre-validate against
    ``reader.solution_states`` here because that attribute is part of
    ``ReaderHandle`` and not of this sub-Protocol; tightening the
    accepted type would be a backwards-incompatible contract change.
    Callers needing fail-fast across many step_ids should compose
    with their own ``solution_states`` check first.
    """
    return {sid: count_eroded(reader.deleted_facets_for(sid)) for sid in step_ids}


def perforation_event_step(
    reader: SupportsElementDeletion,
    step_ids: list[int],
) -> Optional[int]:
    """Earliest ``step_id`` at which any facet is eroded.

    Returns ``None`` if no facet is eroded across the supplied steps —
    the contact-only GS-100 fixture (74/74 alive at every state) hits
    this path and gets ``None``, matching engineer intuition for "no
    perforation observed".

    Unknown ``step_id``s raise ``KeyError`` via
    ``deleted_facets_for`` (Protocol contract). Codex R3 finding: a
    naive early-return search (``return sid`` on first erosion)
    silently masked trailing invalid IDs — e.g. ``[1, 2, 999]`` with
    step 2 eroded returned ``2`` instead of raising on ``999``. We
    therefore pre-fetch all flags via ``deleted_facets_for`` before
    searching, so the KeyError on any unknown ``step_id`` fires
    regardless of where it sits in the list.
    """
    # Pre-fetch all flags (validates every step_id via the
    # deleted_facets_for KeyError contract) before searching for the
    # first erosion, so a trailing unknown id cannot be silently
    # masked by an early return.
    flags_per_step = [
        (sid, reader.deleted_facets_for(sid)) for sid in step_ids
    ]
    for sid, flags in flags_per_step:
        if count_eroded(flags) > 0:
            return sid
    return None


def displacement_history(
    reader: ReaderHandle,
    step_ids: list[int],
    *,
    node_indices: Optional[npt.NDArray[np.int64]] = None,
) -> dict[int, float]:
    """Per-step max displacement magnitude.

    ``node_indices`` (if given) restricts the max to a subset — handy
    for "plate-only" or "projectile-only" envelopes once a node
    partitioning exists. The indices are **0-based row positions in
    the mesh array**, not external solver node IDs (use
    ``Mesh.node_index`` to map IDs → row positions). Validated for
    1-D integer dtype, non-negative, in-bounds against the mesh size.

    Unknown ``step_id``s raise ``KeyError`` upfront — without this
    check, ``get_field`` returns ``None`` for both "unknown step" and
    "known step with no DISPLACEMENT field" (ADR-003), so a stale or
    mistyped ``step_ids`` list would silently fabricate zero rows in
    the output and downstream plots would flatten without warning.
    Codex R1 finding.

    States that DO appear in ``solution_states`` but happen to have
    no DISPLACEMENT field at this step (extremely rare — DISPLACEMENT
    is the OpenRadioss adapter's universal carve-out per ADR-021)
    record ``0.0``. ADR-003 fabrication still applies at the field
    level — the underlying ``get_field`` correctly returns ``None``;
    only the *aggregate* "no displacement available" is expressed as
    0.0 to keep plotting code free of ``None`` special cases.
    """
    _validate_step_ids(reader, step_ids)
    if node_indices is not None:
        _validate_node_indices(
            np.asarray(node_indices), reader.mesh.node_id_array.size
        )
    out: dict[int, float] = {}
    for sid in step_ids:
        f = reader.get_field(CanonicalField.DISPLACEMENT, sid)
        if f is None:
            out[sid] = 0.0
            continue
        vals = f.values()
        if node_indices is not None:
            vals = vals[node_indices]
        out[sid] = max_displacement_magnitude(vals)
    return out
