"""SolutionState — RFC-001 §4.3."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .enums import CanonicalField


@dataclass(frozen=True)
class SolutionState:
    """A single (step, increment) pair the adapter can report on.

    ``time`` is wall-clock simulation time when meaningful; ``None`` for
    static analyses. ``load_factor`` is non-``None`` only for buckling /
    arc-length runs.

    ``available_fields`` is the *exhaustive* list of CanonicalFields the
    adapter can serve at this step; empty list means "no field data
    landed for this step", not "everything available" (ADR-003).
    """

    step_id: int
    step_name: str
    time: Optional[float]
    load_factor: Optional[float]
    available_fields: tuple[CanonicalField, ...]
