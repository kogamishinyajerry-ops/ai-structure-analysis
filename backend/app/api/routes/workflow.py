"""Agentic FEA Workflow Runtime — M1 read/trigger API.

Drives the Mock pipeline (synthetic solver data, real StageState events) so the
Monitor UI can watch the 13-stage flow run. Endpoints:

* ``POST /api/v1/workflow/trigger``      — start a mock run (``?sync=true`` runs
  it to completion synchronously for tests); returns the run.
* ``GET  /api/v1/workflow/runs/{run_id}``— current snapshot of all 13 stages.
* ``GET  /api/v1/workflow/runs``         — recent runs.
* ``GET  /api/v1/workflow/stages``       — the static 13-stage catalog (lets the
  Monitor draw the node graph before a run starts).

At M2 the same surface is fronted by Trigger.dev; at M4 the Mock backend swaps
for the real CalculiX backend with no contract change.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from schemas.workflow_state import (
    CANONICAL_STAGE_ORDER,
    WorkflowStage,
    ws_stage_for,
)

from ...services.workflow.mock_pipeline import STAGE_SPECS, store

router = APIRouter(prefix="/workflow", tags=["workflow-runtime"])


class WorkflowTriggerRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")

    label: str | None = None
    fail_at_stage: WorkflowStage | None = None


@router.post("/trigger")
async def trigger_workflow(req: WorkflowTriggerRequest | None = None, sync: bool = False) -> dict:
    """Start a mock pipeline run. ``sync=true`` runs it to completion before
    returning (deterministic, for tests); otherwise it advances in the
    background and the caller polls ``GET /runs/{run_id}``."""
    req = req or WorkflowTriggerRequest()
    if sync:
        run = store.run_sync(label=req.label, fail_at_stage=req.fail_at_stage)
    else:
        run = store.trigger(label=req.label, fail_at_stage=req.fail_at_stage)
    return run.model_dump(by_alias=True)


@router.get("/runs/{run_id}")
async def get_run(run_id: str) -> dict:
    run = store.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"workflow run {run_id!r} not found")
    return run.model_dump(by_alias=True)


@router.get("/runs")
async def list_runs(limit: int = 20) -> dict:
    return {"runs": [r.model_dump(by_alias=True) for r in store.list_runs(limit=limit)]}


@router.get("/stages")
async def stage_catalog() -> dict:
    """The static 13-stage catalog (order + coarse ADR-014 stage mapping)."""
    return {
        "stages": [
            {
                "order": i,
                "stage": stage.value,
                "wsStage": ws_stage_for(stage),
                "currentObject": STAGE_SPECS[stage].current_object,
                "description": STAGE_SPECS[stage].description,
            }
            for i, stage in enumerate(CANONICAL_STAGE_ORDER)
        ]
    }
