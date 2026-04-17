from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any, TypedDict

from schemas.sim_plan import SimPlan


class FaultClass(StrEnum):
    """Fault classifications as defined in ADR-004."""

    GEOMETRY_INVALID = "geometry_invalid"
    MESH_JACOBIAN = "mesh_jacobian"
    MESH_RESOLUTION = "mesh_resolution"
    SOLVER_CONVERGENCE = "solver_convergence"
    SOLVER_TIMESTEP = "solver_timestep"
    SOLVER_SYNTAX = "solver_syntax"
    REFERENCE_MISMATCH = "reference_mismatch"
    UNKNOWN = "unknown"
    NONE = "none"  # Used when there is no fault


def update_retry_budget(current: dict[str, int], update: dict[str, int]) -> dict[str, int]:
    """Reducer for updating independent retry counters per node."""
    res = dict(current)
    for k, v in update.items():
        res[k] = res.get(k, 0) + v
    return res


def append_history(
    current: list[dict[str, Any]], update: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Reducer for appending to retry history."""
    return current + update


class SimState(TypedDict):
    """LangGraph global state for AI-FEA engine."""

    # 1. Inputs
    user_request: str  # Original natural language request
    plan: SimPlan

    # 2. Intermediate Artifacts
    geometry_path: str | None
    mesh_path: str | None
    frd_path: str | None

    # 3. Validation and Fault Routing
    verdict: str | None
    fault_class: FaultClass

    # 4. Independent Retry Budgets (e.g., {"solver": 1}, max 3 per node)
    retry_budgets: Annotated[dict[str, int], update_retry_budget]

    # 5. Fault History
    history: Annotated[list[dict[str, Any]], append_history]

    # 6. Outputs
    reports: dict[str, str] | None
