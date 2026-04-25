"""Tests for schemas/ws_events.py — the WebSocket event contract (ADR-014).

Pins the v1 schema before any runtime code consumes it. Every event kind
must:
  * round-trip through json (model_dump_json → model_validate_json)
  * reject unknown extra fields (extra="forbid")
  * be selected correctly by the discriminated union on the `event` tag
  * be frozen (immutable)
  * fail validation on missing required fields
"""

from __future__ import annotations

import json
from typing import Any

import pytest

try:
    from pydantic import TypeAdapter, ValidationError

    from schemas.ws_events import (
        CRITICAL_EVENT_KINDS,
        WS_SCHEMA_VERSION,
        ArtifactReady,
        BusDropped,
        BusGap,
        HandoffRequired,
        NodeEntered,
        NodeExited,
        NodeProgress,
        QuantitySummary,
        RagQueried,
        ReviewerVerdictEvent,
        RunFinished,
        RunStarted,
        SurrogateHintEvent,
        WSEvent,
        is_critical,
    )
except ImportError as e:
    pytest.skip(f"ws_events imports failed: {e}", allow_module_level=True)


VALID_DIGEST = "sha256:" + "a" * 64
RUN_ID = "run-12345"
TS = "2026-04-26T12:00:00Z"


def _common(seq: int = 0) -> dict[str, Any]:
    """Header fields every event needs."""
    return {"run_id": RUN_ID, "seq": seq, "ts": TS}


# ---------------------------------------------------------------------------
# Schema constants
# ---------------------------------------------------------------------------


def test_schema_version_is_v1():
    assert WS_SCHEMA_VERSION == "v1"


def test_critical_event_kinds_membership():
    assert "run.started" in CRITICAL_EVENT_KINDS
    assert "run.finished" in CRITICAL_EVENT_KINDS
    assert "handoff.required" in CRITICAL_EVENT_KINDS
    # Non-critical examples
    assert "node.progress" not in CRITICAL_EVENT_KINDS
    assert "rag.queried" not in CRITICAL_EVENT_KINDS


def test_is_critical_helper():
    assert is_critical("run.started") is True
    assert is_critical("run.finished") is True
    assert is_critical("handoff.required") is True
    assert is_critical("node.progress") is False
    assert is_critical("totally-unknown") is False


# ---------------------------------------------------------------------------
# RunStarted
# ---------------------------------------------------------------------------


def test_run_started_minimal():
    e = RunStarted(**_common(), task_spec_digest=VALID_DIGEST)
    assert e.event == "run.started"
    assert e.schema_version == "v1"


def test_run_started_round_trip():
    e = RunStarted(**_common(), task_spec_digest=VALID_DIGEST, submitted_by="alice")
    j = e.model_dump_json()
    parsed = RunStarted.model_validate_json(j)
    assert parsed == e


def test_run_started_rejects_extra_field():
    with pytest.raises(ValidationError):
        RunStarted(**_common(), task_spec_digest=VALID_DIGEST, sneaky="hi")


def test_run_started_rejects_bad_digest():
    with pytest.raises(ValidationError):
        RunStarted(**_common(), task_spec_digest="not-a-digest")


def test_run_started_rejects_short_run_id():
    with pytest.raises(ValidationError):
        RunStarted(run_id="", seq=0, ts=TS, task_spec_digest=VALID_DIGEST)


def test_run_started_rejects_negative_seq():
    with pytest.raises(ValidationError):
        RunStarted(run_id=RUN_ID, seq=-1, ts=TS, task_spec_digest=VALID_DIGEST)


# ---------------------------------------------------------------------------
# NodeEntered + stage enum
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("stage", ["intent", "geometry", "mesh", "solver", "review", "handoff"])
def test_node_entered_each_stage(stage):
    e = NodeEntered(**_common(), node_name="router", stage=stage)
    assert e.stage == stage


def test_node_entered_rejects_unknown_stage():
    with pytest.raises(ValidationError):
        NodeEntered(**_common(), node_name="router", stage="unknown_stage")


def test_node_entered_optional_inputs_digest():
    e = NodeEntered(**_common(), node_name="router", stage="intent", inputs_digest=VALID_DIGEST)
    assert e.inputs_digest == VALID_DIGEST


def test_node_entered_round_trip():
    e = NodeEntered(**_common(seq=42), node_name="solver", stage="solver")
    parsed = NodeEntered.model_validate_json(e.model_dump_json())
    assert parsed == e
    assert parsed.seq == 42


# ---------------------------------------------------------------------------
# NodeProgress
# ---------------------------------------------------------------------------


def test_node_progress_with_percent():
    e = NodeProgress(**_common(), node_name="solver", message="iter 50", percent=50)
    assert e.percent == 50


def test_node_progress_no_percent():
    e = NodeProgress(**_common(), node_name="solver", message="working")
    assert e.percent is None


@pytest.mark.parametrize("bad", [-1, 101, 200])
def test_node_progress_rejects_out_of_range_percent(bad):
    with pytest.raises(ValidationError):
        NodeProgress(**_common(), node_name="solver", message="x", percent=bad)


# ---------------------------------------------------------------------------
# NodeExited
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("status", ["ok", "err", "skipped"])
def test_node_exited_each_status(status):
    e = NodeExited(**_common(), node_name="solver", duration_ms=1234, status=status)
    assert e.status == status


def test_node_exited_rejects_unknown_status():
    with pytest.raises(ValidationError):
        NodeExited(**_common(), node_name="solver", duration_ms=1, status="maybe")


def test_node_exited_negative_duration_rejected():
    with pytest.raises(ValidationError):
        NodeExited(**_common(), node_name="solver", duration_ms=-1, status="ok")


# ---------------------------------------------------------------------------
# ArtifactReady
# ---------------------------------------------------------------------------


def test_artifact_ready_minimal():
    e = ArtifactReady(**_common(), kind="frd", path="runs/r1/result.frd", bytes=1024)
    assert e.kind == "frd"
    assert e.bytes == 1024


def test_artifact_ready_with_digest_and_mime():
    e = ArtifactReady(
        **_common(),
        kind="vtu",
        path="runs/r1/result.vtu",
        bytes=2048,
        digest=VALID_DIGEST,
        mime="application/xml",
    )
    assert e.digest == VALID_DIGEST
    assert e.mime == "application/xml"


# ---------------------------------------------------------------------------
# RagQueried — privacy: only digest + titles, never raw query
# ---------------------------------------------------------------------------


def test_rag_queried_no_raw_query_field():
    """The schema must NOT carry the raw query string. Only a digest."""
    fields = set(RagQueried.model_fields.keys())
    assert "query" not in fields, "raw query must not be a field — privacy boundary"
    assert "query_digest" in fields


def test_rag_queried_minimal():
    e = RagQueried(**_common(), query_digest=VALID_DIGEST)
    assert e.top_k_titles == ()
    assert e.scores == ()


def test_rag_queried_with_titles_and_scores():
    e = RagQueried(
        **_common(),
        query_digest=VALID_DIGEST,
        top_k_titles=("ADR-011", "FP-002"),
        scores=(0.9, 0.7),
    )
    assert e.top_k_titles == ("ADR-011", "FP-002")
    assert e.scores == (0.9, 0.7)


def test_rag_queried_with_source_filter():
    e = RagQueried(**_common(), query_digest=VALID_DIGEST, source_filter="project-adr-fp")
    assert e.source_filter == "project-adr-fp"


# ---------------------------------------------------------------------------
# SurrogateHintEvent — privacy: no notes, no extras
# ---------------------------------------------------------------------------


def test_surrogate_hint_event_no_notes_field():
    """The schema must NOT carry the surrogate's free-text notes."""
    fields = set(SurrogateHintEvent.model_fields.keys())
    assert "notes" not in fields, "raw notes must not be a field — privacy boundary"
    assert "extra" not in fields, "extra dict must not be a field — privacy boundary"


def test_surrogate_hint_event_minimal():
    e = SurrogateHintEvent(**_common(), provider="placeholder@v0", case_id="GS-001")
    assert e.quantities_summary == ()
    assert e.confidence_indicator == "low"


def test_surrogate_hint_event_with_quantities():
    q1 = QuantitySummary(name="max_displacement", value=1.234, unit="mm", confidence="low")
    q2 = QuantitySummary(name="sigma_vm_max", value=210.0, unit="MPa", confidence="medium")
    e = SurrogateHintEvent(
        **_common(),
        provider="manual@v0",
        case_id="GS-001",
        quantities_summary=(q1, q2),
        confidence_indicator="medium",
    )
    assert len(e.quantities_summary) == 2
    assert e.confidence_indicator == "medium"


def test_quantity_summary_frozen():
    q = QuantitySummary(name="x", value=1.0, unit="mm")
    with pytest.raises((TypeError, ValidationError, AttributeError)):
        q.name = "mutated"  # type: ignore[misc]


def test_quantity_summary_rejects_unknown_confidence():
    with pytest.raises(ValidationError):
        QuantitySummary(name="x", value=1.0, unit="mm", confidence="medium-high")


# ---------------------------------------------------------------------------
# ReviewerVerdictEvent
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "verdict", ["Accept", "Accept with Note", "Reject", "Needs Review", "Re-run"]
)
def test_reviewer_verdict_each_value(verdict):
    e = ReviewerVerdictEvent(**_common(), verdict=verdict, fault_class="solver_convergence")
    assert e.verdict == verdict


def test_reviewer_verdict_rejects_unknown():
    with pytest.raises(ValidationError):
        ReviewerVerdictEvent(**_common(), verdict="ApproveWithNits", fault_class="x")


def test_reviewer_verdict_optional_deviation():
    e = ReviewerVerdictEvent(
        **_common(),
        verdict="Accept",
        fault_class="none",
        deviation_pct=2.5,
    )
    assert e.deviation_pct == 2.5


# ---------------------------------------------------------------------------
# HandoffRequired
# ---------------------------------------------------------------------------


def test_handoff_required_minimal():
    e = HandoffRequired(**_common(), reason="deviation > 50%")
    assert e.reason == "deviation > 50%"
    assert e.notion_task_url is None


def test_handoff_required_with_notion_link():
    e = HandoffRequired(
        **_common(),
        reason="critical fault",
        notion_task_url="https://notion.so/task/123",
        recommended_action="Re-run with refined mesh",
    )
    assert e.notion_task_url.startswith("https://")


# ---------------------------------------------------------------------------
# BusDropped + BusGap
# ---------------------------------------------------------------------------


def test_bus_dropped_minimal():
    e = BusDropped(**_common(), dropped_count=3, dropped_kinds=("node.progress",))
    assert e.dropped_count == 3


def test_bus_dropped_zero_count_rejected():
    with pytest.raises(ValidationError):
        BusDropped(**_common(), dropped_count=0)


def test_bus_gap_minimal():
    e = BusGap(**_common(), requested_since=10, buffer_tail=50)
    assert e.requested_since == 10
    assert e.buffer_tail == 50


# ---------------------------------------------------------------------------
# RunFinished
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("status", ["success", "error", "cancelled", "handoff"])
def test_run_finished_each_terminal_status(status):
    e = RunFinished(**_common(), terminal_status=status, total_duration_ms=12345)
    assert e.terminal_status == status


def test_run_finished_rejects_unknown_status():
    with pytest.raises(ValidationError):
        RunFinished(**_common(), terminal_status="ok", total_duration_ms=1)


# ---------------------------------------------------------------------------
# Discriminated union — wire-format parsing
# ---------------------------------------------------------------------------


def _ws_event_adapter():
    return TypeAdapter(WSEvent)


def test_discriminator_parses_run_started():
    payload = {
        "schema_version": "v1",
        "event": "run.started",
        "run_id": RUN_ID,
        "seq": 0,
        "ts": TS,
        "task_spec_digest": VALID_DIGEST,
    }
    parsed = _ws_event_adapter().validate_python(payload)
    assert isinstance(parsed, RunStarted)


def test_discriminator_parses_node_exited():
    payload = {
        "schema_version": "v1",
        "event": "node.exited",
        "run_id": RUN_ID,
        "seq": 7,
        "ts": TS,
        "node_name": "solver",
        "duration_ms": 2000,
        "status": "ok",
    }
    parsed = _ws_event_adapter().validate_python(payload)
    assert isinstance(parsed, NodeExited)
    assert parsed.status == "ok"


def test_discriminator_rejects_unknown_event_kind():
    payload = {
        "schema_version": "v1",
        "event": "bogus.event",
        "run_id": RUN_ID,
        "seq": 0,
        "ts": TS,
    }
    with pytest.raises(ValidationError):
        _ws_event_adapter().validate_python(payload)


def test_round_trip_via_union_for_every_event_kind():
    """Build one of each, dump, and parse back through the union."""
    samples = [
        RunStarted(**_common(seq=0), task_spec_digest=VALID_DIGEST),
        NodeEntered(**_common(seq=1), node_name="router", stage="intent"),
        NodeProgress(**_common(seq=2), node_name="router", message="ok", percent=10),
        NodeExited(**_common(seq=3), node_name="router", duration_ms=100, status="ok"),
        ArtifactReady(**_common(seq=4), kind="frd", path="x", bytes=1),
        RagQueried(**_common(seq=5), query_digest=VALID_DIGEST),
        SurrogateHintEvent(**_common(seq=6), provider="p", case_id="c"),
        ReviewerVerdictEvent(**_common(seq=7), verdict="Accept", fault_class="none"),
        HandoffRequired(**_common(seq=8), reason="r"),
        BusDropped(**_common(seq=9), dropped_count=1),
        BusGap(**_common(seq=10), requested_since=0, buffer_tail=10),
        RunFinished(**_common(seq=11), terminal_status="success", total_duration_ms=10),
    ]
    adapter = _ws_event_adapter()
    for original in samples:
        payload = json.loads(original.model_dump_json())
        parsed = adapter.validate_python(payload)
        assert parsed == original, f"round-trip failed for {type(original).__name__}"


# ---------------------------------------------------------------------------
# Frozen invariant
# ---------------------------------------------------------------------------


def test_event_is_frozen():
    e = RunStarted(**_common(), task_spec_digest=VALID_DIGEST)
    with pytest.raises((TypeError, ValidationError, AttributeError)):
        e.run_id = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Privacy guard rails (negative tests)
# ---------------------------------------------------------------------------


def test_no_event_carries_secret_or_internal_fields():
    """Sweep every WSEvent variant for fields named *_secret / *_internal /
    raw_query / raw_text / agent_thought / prompt — these are the boundary
    classes that ADR-014 forbids."""
    forbidden_substrings = (
        "secret",
        "internal",
        "raw_query",
        "raw_text",
        "agent_thought",
        "prompt",
    )
    classes = [
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
        QuantitySummary,
    ]
    for cls in classes:
        for fname in cls.model_fields:
            lower = fname.lower()
            for forbidden in forbidden_substrings:
                assert forbidden not in lower, (
                    f"{cls.__name__}.{fname} contains forbidden substring "
                    f"{forbidden!r} — ADR-014 privacy boundary violated"
                )
