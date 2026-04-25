"""Agent facade — the SOLE workbench call site that imports `agents.*`.

ADR-015 §Decision pins the discipline contract:

- only this file may import `agents.*` from anywhere in `backend/app/workbench/`
- all calls into agents are read-only with respect to agent state
- agents observe nothing about the workbench (no `workbench` kwarg, no
  callback registration through the facade)

This module currently exposes the architect-agent surface only. The
geometry / mesh / solver / reviewer agents are reached through the
LangGraph compiled state machine in `run_orchestrator` (Phase 2.1
follow-up); they do not need a dedicated facade entrypoint.

Design notes:

- The facade does NOT import `schemas.sim_state` (HF1.4). It builds the
  per-call agent input as a plain dict; the architect's `run()` reads
  via `state.get(key)` and tolerates missing keys.
- The facade does NOT touch agent module-level state — see
  `tests/test_workbench_facade_discipline.py`.
- The facade does NOT cache `SimPlan`s; HMAC binding lives in
  `task_spec_builder` so the draft → submit roundtrip is verifiable.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from agents import architect
from schemas.sim_plan import SimPlan

logger = logging.getLogger(__name__)


class ArchitectError(Exception):
    """Raised when the architect agent fails to produce a SimPlan."""


@dataclass(frozen=True)
class ArchitectResult:
    """Outcome of a single architect invocation.

    Attributes
    ----------
    plan:
        The SimPlan the architect produced. Always present when the
        result is returned by `draft_simplan_from_nl` (failures raise
        instead).
    fault_class:
        Stringified `FaultClass` value the architect emitted alongside
        the plan. Stored as a plain string to keep the facade free of
        `schemas.sim_state` imports (ADR-015 rule #3 / HF1.4).
    """

    plan: SimPlan
    fault_class: str


def draft_simplan_from_nl(nl_request: str, *, case_id: str | None = None) -> ArchitectResult:
    """Translate a natural-language request to a `SimPlan` via the architect agent.

    The architect agent runs ONCE per request (per ADR-015's confirmation
    protocol — there is no LLM regeneration between draft and submit).
    Edits the user makes after seeing the rendered SimPlan are applied
    as a structured diff in `task_spec_builder`, NOT by re-invoking the
    agent.

    Parameters
    ----------
    nl_request:
        The engineer's free-form problem description from the workbench
        dialog. Must be non-empty.
    case_id:
        Optional pre-assigned case id. When omitted, the architect
        derives one deterministically from the request body.

    Returns
    -------
    ArchitectResult
        Wraps the produced `SimPlan` and the fault-class signal the
        architect emitted.

    Raises
    ------
    ValueError
        If `nl_request` is empty.
    ArchitectError
        If the architect failed to produce a `SimPlan` (LLM error,
        validation error, etc.). The error message includes the
        agent's diagnostic history when available.
    """
    if not nl_request or not nl_request.strip():
        raise ValueError("nl_request must be a non-empty string")

    state: dict[str, object] = {"user_request": nl_request}
    if case_id is not None:
        state["case_id"] = case_id

    result = architect.run(state)  # type: ignore[arg-type]

    plan = result.get("plan")
    if not isinstance(plan, SimPlan):
        history = result.get("history", [])
        fault = result.get("fault_class", "unknown")
        raise ArchitectError(
            f"architect failed to produce a SimPlan (fault_class={fault!s}); "
            f"history={history!r}"
        )

    return ArchitectResult(plan=plan, fault_class=str(result.get("fault_class", "none")))


__all__ = ["ArchitectError", "ArchitectResult", "draft_simplan_from_nl"]
