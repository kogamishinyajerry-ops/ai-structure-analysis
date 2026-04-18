from __future__ import annotations

from schemas.sim_state import FaultClass, SimState

# ADR-004 Fault to Node Mapping
FAULT_TO_NODE: dict[FaultClass, str] = {
    FaultClass.GEOMETRY_INVALID: "geometry",
    FaultClass.MESH_JACOBIAN: "mesh",
    FaultClass.MESH_RESOLUTION: "mesh",
    FaultClass.SOLVER_CONVERGENCE: "solver",
    FaultClass.SOLVER_TIMESTEP: "solver",
    FaultClass.SOLVER_SYNTAX: "solver",
    FaultClass.REFERENCE_MISMATCH: "architect",
    FaultClass.UNKNOWN: "human_fallback",
    # If re-run is requested without a fault_class, treat it as unknown.
    FaultClass.NONE: "human_fallback",
}

MAX_RETRIES = 3


def _normalize_verdict(verdict: str | None) -> str:
    """Normalize reviewer verdict labels to routing tokens."""
    if not verdict:
        return ""

    normalized = verdict.strip().lower().replace("_", " ").replace("-", " ")
    normalized = " ".join(normalized.split())
    if normalized in {"accept", "accept with note"}:
        return "accept"
    if normalized == "re run":
        return "re-run"
    if normalized in {"needs review", "reject"}:
        return normalized
    return normalized


def route_reviewer(state: SimState) -> str:
    """Determine the next node after reviewer validation."""
    verdict = _normalize_verdict(state.get("verdict"))
    fault_class = state.get("fault_class", FaultClass.NONE)
    budgets = state.get("retry_budgets", {})

    if verdict == "accept":
        return "viz"

    if verdict == "re-run":
        target_node = FAULT_TO_NODE.get(fault_class, "human_fallback")

        # Check if the target node exceeds retry budget
        current_retries = budgets.get(target_node, 0)

        if current_retries >= MAX_RETRIES:
            return "human_fallback"

        return target_node

    return "human_fallback"
