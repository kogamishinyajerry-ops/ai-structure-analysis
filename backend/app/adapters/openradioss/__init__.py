"""OpenRadioss Layer-1 adapter — RFC-001 W7b.

Second concrete ``ReaderHandle`` implementation after CalculiX. Reads
OpenRadioss animation (``.A%03d`` / ``.A%03d.gz``) and time-history
(``T%02d``) binaries via Vortex-CAE/Vortex-Radioss (MPL-2.0).

The OpenRadioss solver itself (AGPL-3.0) is NOT a Python dependency —
it runs out-of-process in a Docker container; the adapter only parses
its output files. License boundary stays clean: AGPL solver + MPL
parser + MIT wrapper are all linked at runtime, not at import.

ADR compliance:
  * ADR-001 — no derived quantities. Raw `coorA`, `tensValA`, `vectValA`
    surface as-is; von Mises / safety factor are Layer-3 work.
  * ADR-003 — ``UnitSystem`` is NOT inferred. The animation header
    carries no unit metadata; the constructor's ``unit_system`` argument
    must be explicit. ``UNKNOWN`` default makes Layer-3 refuse.
  * ADR-004 — no caching. Each call to ``mesh.coordinates`` /
    ``get_field`` re-reads the underlying animation file. Decompressed
    ``.gz`` files are kept on disk for the adapter's lifetime (cleaned
    on ``close``); reading them twice is the caller's price.
"""

from .reader import OpenRadiossReader

__all__ = ["OpenRadiossReader"]
