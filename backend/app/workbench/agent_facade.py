"""Workbench → agent-layer facade (ADR-015 choke point; built at last per ADR-028 D4).

This is the **one** file under ``backend/app/workbench/`` permitted to import
``agents.*`` — enforced by ``tests/test_workbench_facade_discipline.py``. It does
**not** import ``schemas.sim_state`` (ADR-015 rule 3): the ``SimState`` → ``StageState``
projection lives in the agent layer (:mod:`agents.state_projection`), so the facade
only ever returns an already-projected :class:`~schemas.workflow_state.StageState`.

ADR-028 P1 scope: :func:`run_node` drives the ``PROJECT_INTAKE`` stage through a real
agent node — **deterministic** ("rule-based agent") by default, with an explicit,
**key-gated LLM opt-in** that falls back to deterministic on any failure (so CI stays
hermetic). The remaining stages are wired in P3 and raise ``NotImplementedError`` until
then — the facade never silently fabricates agent output for an un-wired stage.
"""

from __future__ import annotations

import logging

from agents import architect, state_projection
from schemas.workflow_state import StageState, StageStatus, WorkflowStage

logger = logging.getLogger(__name__)

__all__ = ["run_node"]


def _try_intake_llm(user_request: str, existing_case_id: str | None) -> dict | None:
    """Run the real LLM architect node; return a completed ``sim_state`` dict
    (``{"plan": SimPlan, "user_request": str}``) or ``None`` on any non-result
    (missing key, parse failure, fault) so the caller falls back to the
    deterministic agent. Key-gating is handled inside ``agents.llm`` (no key →
    ``None`` plan)."""
    result = architect.run({"user_request": user_request, "case_id": existing_case_id})
    plan = result.get("plan")
    if plan is None:
        return None
    return {"plan": plan, "user_request": user_request}


def run_node(
    stage: WorkflowStage,
    *,
    run_id: str,
    user_request: str | None = None,
    existing_case_id: str | None = None,
    status: StageStatus = StageStatus.SUCCESS,
    progress: float = 1.0,
    allow_llm: bool = False,
) -> StageState:
    """Execute ONE workbench-agent stage and return its already-projected wire
    :class:`StageState` (ADR-028 D4).

    P1 supports ``PROJECT_INTAKE`` only. ``allow_llm`` opts into the real LLM
    architect (key-gated; falls back to the deterministic node on any failure);
    the default is the deterministic ("rule-based agent") path.
    """
    if stage is not WorkflowStage.PROJECT_INTAKE:
        raise NotImplementedError(
            f"agent_facade.run_node: stage {stage.value!r} is not wired yet "
            "(ADR-028 P1 covers project_intake; remaining stages land in P3)."
        )

    req = (user_request or "").strip()

    if allow_llm and req:
        try:
            sim_state = _try_intake_llm(req, existing_case_id)
        except Exception as exc:  # never hard-crash the demo path on an LLM hiccup
            logger.warning("intake LLM node failed (%s); falling back to deterministic", exc)
            sim_state = None
        if sim_state is not None:
            return state_projection.sim_state_to_stage_state(
                sim_state, run_id=run_id, status=status, progress=progress
            )

    outcome = state_projection.analyze_intake(req, existing_case_id=existing_case_id)
    return state_projection.intake_outcome_to_stage_state(
        run_id, outcome, status=status, progress=progress
    )
