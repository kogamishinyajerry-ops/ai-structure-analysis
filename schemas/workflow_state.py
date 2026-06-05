"""Agentic FEA Workflow Runtime — per-stage state contract.

The single source of truth for the observable workflow state the runtime
publishes for each pipeline stage. This is the typed form of the per-task
JSON in the Agentic FEA Workflow Runtime plan
(`.planning/AGENTIC-FEA-RUNTIME-PLAN.md` §3).

Design rule: **extend, do not reinvent.** This module composes the existing
contracts rather than forking a parallel vocabulary:

* fault categories reuse :class:`schemas.sim_state.FaultClass` (ADR-004);
* the coarse stage taxonomy maps onto :data:`schemas.ws_events.Stage`
  (the 6-stage LangGraph DAG, ADR-014) via :data:`WORKFLOW_STAGE_TO_WS_STAGE`,
  so a :class:`StageState` change can emit the matching ``node.*`` WSEvent
  without a second event vocabulary;
* the UTC timestamp type reuses :data:`schemas.ws_events.ISO8601UtcStr`.

Wire format: models serialize to **camelCase** (``model_dump(by_alias=True)``)
so the emitted JSON matches both the plan's per-task contract and the
frontend's existing snake→camel client convention. Inputs accept either
case (``populate_by_name=True``).

Privacy (inherited from ADR-014): artifact fields carry **paths / URLs /
digests**, never raw CAD bytes or agent prompt text.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from schemas.sim_state import FaultClass
from schemas.ws_events import ISO8601UtcStr, Stage

WORKFLOW_STATE_SCHEMA_VERSION = "v1"


class WorkflowStage(StrEnum):
    """The 13 observable pipeline stages (plan §1). Finer-grained than the
    6-stage :data:`schemas.ws_events.Stage`; see :data:`WORKFLOW_STAGE_TO_WS_STAGE`."""

    PROJECT_INTAKE = "project_intake"
    CAD_IMPORT = "cad_import"
    GEOMETRY_VALIDATION = "geometry_validation"
    MATERIAL_ASSIGNMENT = "material_assignment"
    BOUNDARY_CONDITIONS = "boundary_conditions"
    LOAD_CASES = "load_cases"
    MESH_GENERATION = "mesh_generation"
    MESH_QUALITY_CHECK = "mesh_quality_check"
    SOLVER_RUN = "solver_run"
    CONVERGENCE_MONITORING = "convergence_monitoring"
    POST_PROCESSING = "post_processing"
    RESULT_ANALYSIS = "result_analysis"
    REPORT_GENERATION = "report_generation"


#: Canonical execution order of the 13 stages. The runtime walks this list.
CANONICAL_STAGE_ORDER: tuple[WorkflowStage, ...] = tuple(WorkflowStage)


class StageStatus(StrEnum):
    """Per-stage status (plan §3). ``WARNING`` is a *passing-with-caveats*
    state distinct from ``SUCCESS`` (e.g. mesh quality below target but
    solvable) — it is NOT a failure. Aligns with the well-harness
    ``HarnessRunStatus`` (running/completed/failed) and the frontend
    ``JobStatus`` union, adding the explicit ``pending``/``warning`` slots."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    WARNING = "warning"
    FAILED = "failed"


class StageProvenance(StrEnum):
    """Machine-checkable provenance of a stage's ``agent_explanation`` /
    ``next_action`` (ADR-028 D2 anti-over-claim gate). The runtime emits this as
    **first-class data**; the UI MUST NOT infer it. The default ``SCRIPTED_DEMO``
    keeps every un-wired stage honestly labeled as synthetic demo prose until a
    real agent node drives it — so wiring one stage cannot accidentally relabel
    the other twelve.

    * ``SCRIPTED_DEMO`` — hardcoded/synthetic demo text; **NOT** agent output.
    * ``DETERMINISTIC_AGENT`` — produced by a live **rule-based** agent node from
      the actual run input (no LLM; hermetic, reproducible).
    * ``LLM_AGENT`` — produced by a live **LLM-reasoning** agent node.
    """

    SCRIPTED_DEMO = "scripted_demo"
    DETERMINISTIC_AGENT = "deterministic_agent"
    LLM_AGENT = "llm_agent"


#: Lossy projection of each fine stage onto the coarse ADR-014 ``Stage`` so a
#: ``StageState`` can drive the existing ``node.entered``/``node.exited`` events.
#: Setup stages (material/BC/loads) project onto ``solver`` because they define
#: the solve input; post/result project onto ``review``; report onto ``handoff``.
WORKFLOW_STAGE_TO_WS_STAGE: dict[WorkflowStage, Stage] = {
    WorkflowStage.PROJECT_INTAKE: "intent",
    WorkflowStage.CAD_IMPORT: "geometry",
    WorkflowStage.GEOMETRY_VALIDATION: "geometry",
    WorkflowStage.MATERIAL_ASSIGNMENT: "solver",
    WorkflowStage.BOUNDARY_CONDITIONS: "solver",
    WorkflowStage.LOAD_CASES: "solver",
    WorkflowStage.MESH_GENERATION: "mesh",
    WorkflowStage.MESH_QUALITY_CHECK: "mesh",
    WorkflowStage.SOLVER_RUN: "solver",
    WorkflowStage.CONVERGENCE_MONITORING: "solver",
    WorkflowStage.POST_PROCESSING: "review",
    WorkflowStage.RESULT_ANALYSIS: "review",
    WorkflowStage.REPORT_GENERATION: "handoff",
}


def ws_stage_for(stage: WorkflowStage) -> Stage:
    """Coarse ADR-014 ``Stage`` for a fine :class:`WorkflowStage` (total)."""
    return WORKFLOW_STAGE_TO_WS_STAGE[stage]


class _CamelModel(BaseModel):
    """Base: strict (`extra='forbid'`), camelCase wire aliases, accepts either case."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )


class StageMetrics(BaseModel):
    """Per-stage observability metrics. The plan §3 documents the mesh-centric
    fields; metrics are open-ended (``extra='allow'``) so a stage can attach
    its own (e.g. solver residual, safety factor) without a schema bump."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="allow",
    )

    # Mesh-centric (the plan's worked example)
    nodes: int | None = None
    elements: int | None = None
    bad_elements: int | None = None
    max_aspect_ratio: float | None = None
    min_jacobian: float | None = None
    estimated_solve_time: str | None = None
    # Common cross-stage observables (optional)
    residual_pct: float | None = None
    iterations: int | None = None
    max_von_mises_pa: float | None = None
    max_displacement_m: float | None = None
    safety_factor: float | None = None


class StageArtifacts(_CamelModel):
    """Artifact references for a stage. Paths / URLs / digests only — never
    raw bytes (ADR-014 privacy)."""

    geometry_preview: str | None = None
    mesh_preview: str | None = None
    result_preview: str | None = None
    log_file: str | None = None
    report_file: str | None = None


class StageError(_CamelModel):
    """A typed stage error. ``fault_class`` reuses the ADR-004 enum so the
    runtime's retry/branch logic can route on a single fault taxonomy."""

    fault_class: FaultClass = FaultClass.UNKNOWN
    message: str = Field(..., min_length=1)
    detail: str | None = None


class StageState(_CamelModel):
    """The observable state of one pipeline stage — the typed per-task JSON.

    Serializes (``by_alias=True``) to exactly the plan §3 contract:
    ``{runId, stage, status, progress, currentObject, description, metrics,
    warnings, errors, artifacts, agentExplanation, nextAction}``.
    """

    schema_version: str = WORKFLOW_STATE_SCHEMA_VERSION
    run_id: str = Field(..., min_length=1)
    stage: WorkflowStage
    status: StageStatus = StageStatus.PENDING
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    current_object: str | None = None
    description: str = ""
    metrics: StageMetrics = Field(default_factory=StageMetrics)
    warnings: list[str] = Field(default_factory=list)
    errors: list[StageError] = Field(default_factory=list)
    artifacts: StageArtifacts = Field(default_factory=StageArtifacts)
    # The "agentic" layer the plan adds on top of the existing runtime.
    agent_explanation: str = ""
    next_action: str = ""
    # ADR-028 D2: machine-checkable provenance of agent_explanation/next_action.
    # Additive + back-compat; defaults to SCRIPTED_DEMO so un-wired stages stay
    # honestly labeled until a real agent node drives them.
    provenance: StageProvenance = StageProvenance.SCRIPTED_DEMO
    updated_at: ISO8601UtcStr | None = None


__all__ = [
    "WORKFLOW_STATE_SCHEMA_VERSION",
    "WorkflowStage",
    "CANONICAL_STAGE_ORDER",
    "StageStatus",
    "StageProvenance",
    "WORKFLOW_STAGE_TO_WS_STAGE",
    "ws_stage_for",
    "StageMetrics",
    "StageArtifacts",
    "StageError",
    "StageState",
]
