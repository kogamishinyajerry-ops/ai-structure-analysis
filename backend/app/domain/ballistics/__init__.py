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
    """
    for sid in step_ids:
        flags = reader.deleted_facets_for(sid)
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
    partitioning exists. Without it the result is the global max.

    States that don't advertise ``DISPLACEMENT`` are recorded as
    ``0.0`` (mirrors ``max_displacement_magnitude`` on empty input)
    — this matches the contract that ``get_field`` returns ``None``
    for unavailable fields rather than fabricating zeros (ADR-003);
    the *aggregate* "no displacement available at this step" is best
    expressed as 0.0 here so downstream plotting code does not have
    to special-case ``None``.
    """
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
