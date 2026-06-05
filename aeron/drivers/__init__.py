"""Concrete AERON driver adapters."""

from typing import Any

from aeron.drivers.calculix_backend import CalculiXFEABackend
from aeron.drivers.openradioss_backend import (
    BALLISTIC_CANDIDATE_CLAIM_BOUNDARY,
    BALLISTIC_CANDIDATE_DECK_DISCIPLINE,
    BALLISTIC_CANDIDATE_TIER,
    OpenRadiossFEABackend,
)
from aeron.protocols import FEABackend
from schemas.sim_plan import SolverBackend

__all__ = [
    "BALLISTIC_CANDIDATE_CLAIM_BOUNDARY",
    "BALLISTIC_CANDIDATE_DECK_DISCIPLINE",
    "BALLISTIC_CANDIDATE_TIER",
    "CalculiXFEABackend",
    "OpenRadiossFEABackend",
    "get_backend",
]


def get_backend(name: SolverBackend | str, **kwargs: Any) -> FEABackend:
    """Dispatch a SimPlan solver name to a concrete ``FEABackend`` (ADR-028 D4 P2).

    CalculiX-first. A non-CalculiX request is rejected HONESTLY with a clear
    ``NotImplementedError`` — never a silent fallback to the CalculiX solver, so an
    unsupported physics can never be solved as if it were the requested one.
    OpenRadioss is implemented but deliberately NOT dispatched here: its ballistic
    path is deferred to ADR-028 P5, and its constructor takes starter/engine decks
    rather than a mesh ``.inp``. An unknown name raises ``ValueError`` at
    normalization (``SolverBackend(name)``), before any backend is constructed.
    """
    key = SolverBackend(name)  # str | member -> member; ValueError on unknown
    if key is SolverBackend.CALCULIX:
        return CalculiXFEABackend(**kwargs)
    raise NotImplementedError(
        f"Solver backend {key.value!r} is not implemented in this graph yet "
        f"(CalculiX-first per ADR-028 D5; OpenRadioss deferred to P5)."
    )
