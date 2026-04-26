"""WebSocket event schema v1 for the workbench (ADR-014).

The contract between LangGraph runtime and the React/TS frontend. Every
event carries `schema_version` (literal "v1"), `seq` (monotonic int per
run), `ts` (ISO-8601 UTC string), and `event` (discriminator).

Privacy: events MUST NOT carry agent prompt text, raw RAG chunk text,
raw user CAD bytes, or any field with `_secret` / `_internal` in its
name. Large bodies travel as digest references; the frontend pulls the
body via a separate authenticated REST endpoint.

This module is NOT in HF1.4 (`schemas/sim_state.py`). It is a sibling
file under `schemas/` per ADR-014's explicit non-touch of HF1.
"""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

WS_SCHEMA_VERSION: Literal["v1"] = "v1"

# Stage names match Phase 1's six-stage LangGraph DAG (router → architect →
# geometry → mesh → solver → reviewer + handoff). These are also the
# `stage` values on `node.entered`.
Stage = Literal["intent", "geometry", "mesh", "solver", "review", "handoff"]

NodeStatus = Literal["ok", "err", "skipped"]

# Reviewer verdicts mirror reviewer_advisor.GOVERNANCE_BIASING_VERDICTS plus
# the non-biasing ones; pin here as a literal so a new verdict requires
# a schema bump.
ReviewerVerdict = Literal["Accept", "Accept with Note", "Reject", "Needs Review", "Re-run"]

TerminalStatus = Literal["success", "error", "cancelled", "handoff"]

ConfidenceIndicator = Literal["high", "medium", "low", "n/a"]

# SHA-256 hex digest with `sha256:` prefix (71 chars total: "sha256:" (7)
# + 64 hex chars). The pattern below is anchored on those exact bounds.
DigestStr = Annotated[
    str,
    Field(
        pattern=r"^sha256:[0-9a-f]{64}$",
        description="SHA-256 hex digest with sha256: prefix (71 chars total)",
    ),
]

# ISO-8601 UTC timestamp accepted by the schema. The pattern allows
# both bare `YYYY-MM-DDTHH:MM:SSZ` and the fractional-second variant
# `YYYY-MM-DDTHH:MM:SS.SSSSSSZ`. Anchored on `Z` (Zulu / UTC) — agents
# emit UTC-only per ADR-014; non-UTC timestamps are a contract violation
# and should fail validation rather than passing through silently.
ISO8601_UTC_PATTERN = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,9})?Z$"
ISO8601UtcStr = Annotated[
    str,
    Field(
        pattern=ISO8601_UTC_PATTERN,
        description="ISO-8601 UTC timestamp (e.g. '2026-04-26T12:34:56Z')",
    ),
]


class _BaseEvent(BaseModel):
    """All events share this header."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["v1"] = WS_SCHEMA_VERSION
    run_id: str = Field(..., min_length=1)
    seq: int = Field(..., ge=0)
    ts: ISO8601UtcStr


class RunStarted(_BaseEvent):
    event: Literal["run.started"] = "run.started"
    task_spec_digest: DigestStr
    started_at: ISO8601UtcStr | None = None
    submitted_by: str | None = None


class NodeEntered(_BaseEvent):
    event: Literal["node.entered"] = "node.entered"
    node_name: str = Field(..., min_length=1)
    stage: Stage
    inputs_digest: DigestStr | None = None


class NodeProgress(_BaseEvent):
    event: Literal["node.progress"] = "node.progress"
    node_name: str = Field(..., min_length=1)
    message: str
    percent: int | None = Field(default=None, ge=0, le=100)


class NodeExited(_BaseEvent):
    event: Literal["node.exited"] = "node.exited"
    node_name: str = Field(..., min_length=1)
    duration_ms: int = Field(..., ge=0)
    status: NodeStatus
    outputs_digest: DigestStr | None = None
    error_class: str | None = None


class ArtifactReady(_BaseEvent):
    event: Literal["artifact.ready"] = "artifact.ready"
    kind: str = Field(..., min_length=1)
    path: str = Field(..., min_length=1)
    bytes: int = Field(..., ge=0)
    digest: DigestStr | None = None
    mime: str | None = None


class RagQueried(_BaseEvent):
    event: Literal["rag.queried"] = "rag.queried"
    query_digest: DigestStr
    top_k_titles: tuple[str, ...] = Field(default_factory=tuple)
    scores: tuple[float, ...] = Field(default_factory=tuple)
    source_filter: str | None = None

    @model_validator(mode="after")
    def _titles_and_scores_are_paired(self) -> RagQueried:
        """R2 (post Codex R1 MED): top_k_titles[i] ↔ scores[i] must be
        the same length. The frontend treats them as parallel arrays;
        a divergence would mis-render scores against titles silently.
        """
        if len(self.top_k_titles) != len(self.scores):
            raise ValueError(
                f"top_k_titles ({len(self.top_k_titles)}) and "
                f"scores ({len(self.scores)}) must be the same length "
                f"(parallel arrays — element i is title↔score)"
            )
        return self


class QuantitySummary(BaseModel):
    """Compact projection of a SurrogateHint quantity. No notes, no extras."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(..., min_length=1)
    value: float
    unit: str = Field(..., min_length=1)
    confidence: ConfidenceIndicator = "low"


class SurrogateHintEvent(_BaseEvent):
    event: Literal["surrogate.hint"] = "surrogate.hint"
    provider: str = Field(..., min_length=1)
    case_id: str = Field(..., min_length=1)
    quantities_summary: tuple[QuantitySummary, ...] = Field(default_factory=tuple)
    confidence_indicator: ConfidenceIndicator = "low"


class ReviewerVerdictEvent(_BaseEvent):
    event: Literal["reviewer.verdict"] = "reviewer.verdict"
    verdict: ReviewerVerdict
    fault_class: str
    deviation_pct: float | None = None
    notion_task_url: str | None = None


class HandoffRequired(_BaseEvent):
    event: Literal["handoff.required"] = "handoff.required"
    reason: str = Field(..., min_length=1)
    notion_task_url: str | None = None
    recommended_action: str | None = None


class BusDropped(_BaseEvent):
    event: Literal["bus.dropped"] = "bus.dropped"
    dropped_count: int = Field(..., ge=1)
    dropped_kinds: tuple[str, ...] = Field(default_factory=tuple)


class BusGap(_BaseEvent):
    event: Literal["bus.gap"] = "bus.gap"
    requested_since: int = Field(..., ge=0)
    buffer_tail: int = Field(..., ge=0)


class RunFinished(_BaseEvent):
    event: Literal["run.finished"] = "run.finished"
    terminal_status: TerminalStatus
    total_duration_ms: int = Field(..., ge=0)
    failure_summary: str | None = None


# Discriminated union for parsing a stream of mixed events.
# NOTE: typing.Union here (not X | Y) so this module loads on Python 3.9
# environments. The PEP-604 syntax requires 3.10+ at module-level.
WSEvent = Annotated[  # noqa: UP007
    Union[  # noqa: UP007
        RunStarted,
        NodeEntered,
        NodeProgress,
        NodeExited,
        ArtifactReady,
        RagQueried,
        SurrogateHintEvent,
        ReviewerVerdictEvent,
        HandoffRequired,
        BusDropped,
        BusGap,
        RunFinished,
    ],
    Field(discriminator="event"),
]

# Critical events that backpressure must NEVER drop. The bus is required
# to enqueue these even if the queue is otherwise full; older non-critical
# events are evicted instead.
CRITICAL_EVENT_KINDS: frozenset[str] = frozenset(
    {
        "run.started",
        "run.finished",
        "handoff.required",
    }
)


def is_critical(event_kind: str) -> bool:
    """True if the event kind must survive backpressure eviction.

    Note: `node.exited` with `status="err"` is also critical at the
    consumer level, but we keep that judgement in the event-bus
    eviction policy (it inspects the payload), not in this set.
    """
    return event_kind in CRITICAL_EVENT_KINDS
