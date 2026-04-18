"""Machine-readable mirror of ADR-004 fault classes and their recovery paths.

The Reviewer and Router already have independent parametric coverage of each
``FaultClass``. P1-05's contribution is to make the *contract* between them
explicit: one table that says, for every fault_class defined by ADR-004,

  * which downstream node owns recovery,
  * what verdict the Reviewer should emit when it sees that fault_class
    on an upstream propagation,
  * which retry-budget key accumulates for that fault_class.

Drift between this table and ``agents.router.FAULT_TO_NODE`` or
``agents.reviewer.RERUN_FAULTS`` is caught by ``test_fault_injection``
regression guards. Add a new FaultClass? The tests fail until this table
is extended.
"""

from __future__ import annotations

from dataclasses import dataclass

from schemas.sim_state import FaultClass


@dataclass(frozen=True)
class FaultRecoveryContract:
    """The canonical recovery spec for one fault_class per ADR-004."""

    fault_class: FaultClass
    target_node: str
    expected_verdict: str  # "Re-run" or "Needs Review"
    budget_key: str
    human_summary: str  # short, reviewer-friendly explanation


# ADR-004 is the source of truth. This mirror is explicitly named so the
# symmetry is reviewable in a single place.
FAULT_RECOVERY_TABLE: tuple[FaultRecoveryContract, ...] = (
    FaultRecoveryContract(
        fault_class=FaultClass.GEOMETRY_INVALID,
        target_node="geometry",
        expected_verdict="Re-run",
        budget_key="geometry",
        human_summary="Non-watertight or invalid CAD — Geometry Agent must re-emit.",
    ),
    FaultRecoveryContract(
        fault_class=FaultClass.MESH_JACOBIAN,
        target_node="mesh",
        expected_verdict="Re-run",
        budget_key="mesh",
        human_summary="Negative/low Jacobian elements — Mesh Agent tightens quality gate.",
    ),
    FaultRecoveryContract(
        fault_class=FaultClass.MESH_RESOLUTION,
        target_node="mesh",
        expected_verdict="Re-run",
        budget_key="mesh",
        human_summary="Solution drift vs reference beyond 5% — Mesh Agent refines.",
    ),
    FaultRecoveryContract(
        fault_class=FaultClass.SOLVER_CONVERGENCE,
        target_node="solver",
        expected_verdict="Re-run",
        budget_key="solver",
        human_summary="Residual divergence — Solver Agent relaxes NR controls.",
    ),
    FaultRecoveryContract(
        fault_class=FaultClass.SOLVER_TIMESTEP,
        target_node="solver",
        expected_verdict="Re-run",
        budget_key="solver",
        human_summary="Time-increment cutback floor hit — Solver Agent adjusts stepping.",
    ),
    FaultRecoveryContract(
        fault_class=FaultClass.SOLVER_SYNTAX,
        target_node="solver",
        expected_verdict="Re-run",
        budget_key="solver",
        human_summary="Malformed deck — Solver Agent rebuilds via Gate-Solve lint.",
    ),
    # NOTE (architectural gap, flagged for ADR-004 review):
    # agents.router.FAULT_TO_NODE maps REFERENCE_MISMATCH → "architect", but
    # that branch is only reached when verdict == "Re-run". The Reviewer
    # currently emits verdict = "Needs Review" for REFERENCE_MISMATCH, so the
    # router falls through to human_fallback. The "architect loop" recovery
    # is wired but never triggered via the Reviewer path today. Until the
    # ADR is settled, this contract reflects observed runtime behavior.
    FaultRecoveryContract(
        fault_class=FaultClass.REFERENCE_MISMATCH,
        target_node="human_fallback",
        expected_verdict="Needs Review",
        budget_key="human_fallback",
        human_summary=(
            "Reference drift >50% — Reviewer surfaces for human review. "
            "Router's architect-loop mapping is present but unreachable "
            "via current Reviewer verdict; see ADR-004 follow-up."
        ),
    ),
    FaultRecoveryContract(
        fault_class=FaultClass.UNKNOWN,
        target_node="human_fallback",
        expected_verdict="Needs Review",
        budget_key="human_fallback",
        human_summary="Unclassified fault — human fallback, per ADR-004.",
    ),
)


FAULT_RECOVERY_BY_CLASS: dict[FaultClass, FaultRecoveryContract] = {
    c.fault_class: c for c in FAULT_RECOVERY_TABLE
}


def all_fault_classes_except_none() -> tuple[FaultClass, ...]:
    """All FaultClass members ADR-004 defines as injectable faults."""
    return tuple(c.fault_class for c in FAULT_RECOVERY_TABLE)
