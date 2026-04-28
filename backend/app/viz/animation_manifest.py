"""Animation-manifest builder — RFC-001 §6.4 W7c.

Builds a JSON-serialisable description of a multi-state result run:
per-frame ``step_id``, ``time``, ``max_displacement_magnitude``, and
(when the reader supports it) ``eroded_facet_count``.

This is the **data contract** for downstream multi-frame
visualisation. It does NOT render PNG/MP4 frames itself — that's
W7c-v2 work, which needs the Layer-2 ``Mesh`` Protocol extended with
cell-connectivity (the current Protocol is point-only). Splitting
the manifest from the renderer means:

  * the Electron renderer can consume the JSON directly to drive a
    chart-style time-history plot today (no graphics stack needed);
  * the W7f DOCX template can table per-frame eroded counts /
    max-displacement values from the manifest;
  * once cell connectivity lands in the Mesh Protocol, the PNG
    renderer (W7c-v2) reads the same manifest and emits one PNG per
    frame, optionally writing the PNG path back into the manifest.

ADR compliance:
  * ADR-001: every per-frame quantity comes from Layer 3
    (``app.domain.ballistics``); we don't add new derivations here,
    we just stage them across the time axis.
  * ADR-003: states with no ``DISPLACEMENT`` field still appear in the
    manifest with ``max_displacement_magnitude = 0.0`` (mirrors
    ``displacement_history``). The state is not silently dropped —
    a missing frame would break frame-index ↔ step_id consistency
    for downstream Electron / DOCX consumers.
  * ADR-004: caching forbidden in Layer 1, but a manifest is a
    one-shot build — not a cache. Each call re-iterates the reader.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from ..core.types import ReaderHandle, SupportsElementDeletion
from ..domain.ballistics import displacement_history, eroded_history


@dataclass(frozen=True)
class AnimationFrame:
    """One row of the manifest — pinned per-state aggregates.

    Time units are whatever the underlying solver reports — for
    OpenRadioss this is milliseconds when the deck uses si-mm; the
    consumer is responsible for unit awareness via the reader's
    ``unit_system``.

    ``png_path``/``frame_index`` are reserved for W7c-v2 use; v1
    leaves them at their defaults.
    """

    step_id: int
    time: float
    max_displacement_magnitude: float
    eroded_facet_count: Optional[int] = None
    png_path: Optional[str] = None
    frame_index: Optional[int] = None


@dataclass(frozen=True)
class AnimationManifest:
    """Top-level manifest covering all rendered frames of a run.

    ``solver`` and ``unit_system`` come from the reader's metadata so
    a downstream chart / DOCX table can label axes correctly.
    ``has_erosion_data`` is a feature flag — Electron / DOCX skip the
    eroded-count column when ``False`` (e.g. CalculiX, contact-only
    OpenRadioss runs like GS-100).
    """

    solver: str
    unit_system: str
    has_erosion_data: bool
    frames: list[AnimationFrame] = field(default_factory=list)

    def to_json(self) -> str:
        """Pretty-print JSON, sorted keys, 2-space indent — matches the
        wedge's other JSON manifests for diff-friendly review."""
        return json.dumps(
            asdict(self), indent=2, sort_keys=True, ensure_ascii=False
        )

    def write(self, path: Path) -> Path:
        """Write the manifest to ``path``; mkdir parents; return ``path``."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")
        return path


def build_manifest(
    reader: ReaderHandle,
    *,
    solver_name: str,
    step_ids: Optional[list[int]] = None,
) -> AnimationManifest:
    """Compose the manifest from a Layer-2 ``ReaderHandle``.

    ``step_ids`` defaults to *all* states the reader advertises; pass
    a subset (e.g. every 10th frame) to drive a coarser animation
    without re-reading the file. The list is consumed in the order
    given — callers MUST sort first if they want chronological order
    (we deliberately don't re-sort because a non-monotonic order is
    occasionally meaningful, e.g. compare-frame plots).

    ``solver_name`` is recorded verbatim in the manifest so the
    consumer doesn't have to introspect the adapter type.

    Erosion data is included automatically when the reader satisfies
    ``SupportsElementDeletion``; otherwise ``eroded_facet_count`` is
    ``None`` on every frame and ``has_erosion_data=False`` so the
    consumer can skip that column.
    """
    if step_ids is None:
        step_ids = [s.step_id for s in reader.solution_states]

    disp_by_step = displacement_history(reader, step_ids)

    has_erosion = isinstance(reader, SupportsElementDeletion)
    erosion_by_step: dict[int, int] = (
        eroded_history(reader, step_ids) if has_erosion else {}
    )

    state_lookup = {s.step_id: s for s in reader.solution_states}

    frames = [
        AnimationFrame(
            step_id=sid,
            time=float(state_lookup[sid].time)
            if state_lookup[sid].time is not None
            else 0.0,
            max_displacement_magnitude=float(disp_by_step[sid]),
            eroded_facet_count=int(erosion_by_step[sid]) if has_erosion else None,
        )
        for sid in step_ids
    ]

    return AnimationManifest(
        solver=solver_name,
        unit_system=reader.mesh.unit_system.value,
        has_erosion_data=has_erosion,
        frames=frames,
    )


__all__ = [
    "AnimationFrame",
    "AnimationManifest",
    "build_manifest",
]
