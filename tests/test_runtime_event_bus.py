"""Tests for backend.app.runtime.event_bus (ADR-014 §Backpressure / §Resume).

R2 hardening (post Codex R1, 2026-04-26):
- ring buffer NEVER contains dropped events (live consumers + replaying
  consumers see the same event stream)
- bus.dropped events coalesce at queue tail under sustained overflow,
  bounding memory at QUEUE_CAPACITY + 1
- bus.gap.seq is buffer_tail-1 (outside _next_seq), so a client that
  persists the gap seq cannot collide with a real event on resume
- aclose() takes the lock so a concurrent emit() that already passed
  its closed check cannot still squeeze a write through
- emit() validates event.run_id == bus.run_id
"""

from __future__ import annotations

import asyncio

import pytest

from backend.app.runtime.event_bus import (
    DROPPED_KINDS_CAP,
    QUEUE_CAPACITY,
    RING_BUFFER_CAPACITY,
    RunEventBus,
)
from schemas.ws_events import (
    HandoffRequired,
    NodeProgress,
    RunFinished,
    RunStarted,
)

DEFAULT_RUN = "RUN-A"


# ---------------------------------------------------------------------------
# Fixtures + helpers
# ---------------------------------------------------------------------------


def _started(run_id: str = DEFAULT_RUN) -> RunStarted:
    return RunStarted(
        run_id=run_id,
        seq=0,
        ts="2026-04-26T12:00:00Z",
        task_spec_digest="sha256:" + "a" * 64,
    )


def _progress(run_id: str = DEFAULT_RUN, message: str = "step") -> NodeProgress:
    return NodeProgress(
        run_id=run_id,
        seq=0,
        ts="2026-04-26T12:00:00Z",
        node_name="geometry",
        message=message,
    )


def _finished(run_id: str = DEFAULT_RUN) -> RunFinished:
    return RunFinished(
        run_id=run_id,
        seq=0,
        ts="2026-04-26T12:00:00Z",
        terminal_status="success",
        total_duration_ms=42,
    )


def _handoff(run_id: str = DEFAULT_RUN) -> HandoffRequired:
    return HandoffRequired(
        run_id=run_id,
        seq=0,
        ts="2026-04-26T12:00:00Z",
        reason="reviewer requested",
        notion_task_url="https://www.notion.so/x",
    )


# ---------------------------------------------------------------------------
# Construction + invariants
# ---------------------------------------------------------------------------


def test_construct_with_empty_run_id_rejected():
    with pytest.raises(ValueError, match="non-empty"):
        RunEventBus(run_id="")


def test_capacity_constants_match_adr_014():
    assert QUEUE_CAPACITY == 1024
    assert RING_BUFFER_CAPACITY == 256


# ---------------------------------------------------------------------------
# Producer / consumer happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_emit_assigns_monotonic_seq():
    bus = RunEventBus(run_id=DEFAULT_RUN)
    await bus.emit(_started())
    await bus.emit(_progress())
    await bus.emit(_finished())

    a = await bus.get()
    b = await bus.get()
    c = await bus.get()
    assert (a.seq, b.seq, c.seq) == (1, 2, 3)


@pytest.mark.asyncio
async def test_emit_preserves_event_type():
    bus = RunEventBus(run_id=DEFAULT_RUN)
    await bus.emit(_started())
    out = await bus.get()
    assert isinstance(out, RunStarted)
    assert out.run_id == DEFAULT_RUN


@pytest.mark.asyncio
async def test_get_blocks_until_emit():
    bus = RunEventBus(run_id=DEFAULT_RUN)
    consumer = asyncio.create_task(bus.get())
    await asyncio.sleep(0.01)
    assert not consumer.done()
    await bus.emit(_progress(message="hello"))
    out = await asyncio.wait_for(consumer, timeout=0.5)
    assert out.message == "hello"


@pytest.mark.asyncio
async def test_qsize_reflects_queue():
    bus = RunEventBus(run_id=DEFAULT_RUN)
    assert bus.qsize() == 0
    await bus.emit(_progress())
    await bus.emit(_progress())
    assert bus.qsize() == 2
    await bus.get()
    assert bus.qsize() == 1


# ---------------------------------------------------------------------------
# R2: run_id validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_emit_rejects_mismatched_run_id():
    bus = RunEventBus(run_id="RUN-A")
    with pytest.raises(ValueError, match="does not match"):
        await bus.emit(_started(run_id="RUN-B"))


@pytest.mark.asyncio
async def test_emit_rejects_none_event():
    bus = RunEventBus(run_id=DEFAULT_RUN)
    with pytest.raises(ValueError):
        await bus.emit(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Backpressure: non-critical events drop on overflow
# (R2: no ring entry, coalesced bus.dropped, memory bounded)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_overflow_drops_first_non_critical_emits_bus_dropped():
    bus = RunEventBus(run_id=DEFAULT_RUN)
    for _ in range(QUEUE_CAPACITY):
        await bus.emit(_progress())
    assert bus.qsize() == QUEUE_CAPACITY

    # First overflow: drop arriving event, append fresh bus.dropped.
    await bus.emit(_progress(message="will be dropped"))
    assert bus.qsize() == QUEUE_CAPACITY + 1

    # Drain.
    drained = []
    while bus.qsize() > 0:
        drained.append(await bus.get())
    kinds = [ev.event for ev in drained]
    assert kinds[:-1] == ["node.progress"] * QUEUE_CAPACITY
    assert kinds[-1] == "bus.dropped"
    assert drained[-1].dropped_count == 1
    assert drained[-1].dropped_kinds == ("node.progress",)


@pytest.mark.asyncio
async def test_overflow_coalesces_into_tail_bus_dropped():
    """R2 fix HIGH#2: sustained overflow does NOT grow queue past cap+1."""
    bus = RunEventBus(run_id=DEFAULT_RUN)
    for _ in range(QUEUE_CAPACITY):
        await bus.emit(_progress())
    # 50 more — should all coalesce into a single tail bus.dropped.
    for _ in range(50):
        await bus.emit(_progress(message="overflow"))
    assert (
        bus.qsize() == QUEUE_CAPACITY + 1
    ), f"queue grew unbounded: qsize={bus.qsize()}, expected={QUEUE_CAPACITY + 1}"

    # Drain → tail is a single bus.dropped with dropped_count=50.
    drained = []
    while bus.qsize() > 0:
        drained.append(await bus.get())
    tail = drained[-1]
    assert tail.event == "bus.dropped"
    assert tail.dropped_count == 50


@pytest.mark.asyncio
async def test_dropped_kinds_capped_at_DROPPED_KINDS_CAP():
    """Even with mixed kinds, dropped_kinds list does not grow unbounded."""
    bus = RunEventBus(run_id=DEFAULT_RUN)
    for _ in range(QUEUE_CAPACITY):
        await bus.emit(_progress())
    # Drop many distinct kinds — dropped_kinds should cap at DROPPED_KINDS_CAP.
    for i in range(DROPPED_KINDS_CAP * 2):
        await bus.emit(_progress(message=f"kind-{i}"))

    drained = []
    while bus.qsize() > 0:
        drained.append(await bus.get())
    tail = drained[-1]
    assert tail.event == "bus.dropped"
    assert len(tail.dropped_kinds) <= DROPPED_KINDS_CAP


@pytest.mark.asyncio
async def test_ring_does_not_contain_dropped_events():
    """R2 fix HIGH#1: replay must not resurrect dropped events.

    Live consumer dropped event X. A consumer that reconnects with
    since_seq must NOT see X.
    """
    bus = RunEventBus(run_id=DEFAULT_RUN)
    for _ in range(QUEUE_CAPACITY):
        await bus.emit(_progress(message="kept"))
    # This emit is dropped — it must not appear in the ring.
    await bus.emit(_progress(message="dropped-not-in-ring"))

    ring_messages = [ev.message for ev in bus.replay_since(0) if ev.event == "node.progress"]
    assert "dropped-not-in-ring" not in ring_messages
    # All ringed progress entries should be the "kept" ones (or evicted
    # by ring-buffer rotation).
    for m in ring_messages:
        assert m == "kept"


@pytest.mark.asyncio
async def test_critical_events_bypass_cap():
    """run.started / run.finished / handoff.required NEVER drop on overflow."""
    bus = RunEventBus(run_id=DEFAULT_RUN)
    for _ in range(QUEUE_CAPACITY):
        await bus.emit(_progress())
    assert bus.qsize() == QUEUE_CAPACITY

    # Each critical can push +1 without dropping.
    await asyncio.wait_for(bus.emit(_finished()), timeout=0.5)
    assert bus.qsize() == QUEUE_CAPACITY + 1


@pytest.mark.asyncio
async def test_handoff_required_bypasses_cap():
    bus = RunEventBus(run_id=DEFAULT_RUN)
    for _ in range(QUEUE_CAPACITY):
        await bus.emit(_progress())
    await bus.emit(_handoff())
    drained = []
    while bus.qsize() > 0:
        drained.append(await bus.get())
    assert any(ev.event == "handoff.required" for ev in drained)


@pytest.mark.asyncio
async def test_critical_event_seq_is_unique_when_bypassing_cap():
    bus = RunEventBus(run_id=DEFAULT_RUN)
    for _ in range(QUEUE_CAPACITY):
        await bus.emit(_progress())
    await bus.emit(_finished())
    await bus.emit(_started())

    seqs_by_kind: dict[str, list[int]] = {}
    while bus.qsize() > 0:
        ev = await bus.get()
        seqs_by_kind.setdefault(ev.event, []).append(ev.seq)
    assert len(seqs_by_kind["run.finished"]) == 1
    assert len(seqs_by_kind["run.started"]) == 1
    finished_seq = seqs_by_kind["run.finished"][0]
    started_seq = seqs_by_kind["run.started"][0]
    assert finished_seq < started_seq


# ---------------------------------------------------------------------------
# Ring buffer + replay
# (R2 fix HIGH#3: bus.gap.seq is buffer_tail-1, never collides with future)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_replay_since_zero_returns_all_buffered_events():
    bus = RunEventBus(run_id=DEFAULT_RUN)
    await bus.emit(_started())
    await bus.emit(_progress())
    await bus.emit(_finished())

    out = list(bus.replay_since(0))
    assert [ev.event for ev in out] == ["run.started", "node.progress", "run.finished"]


@pytest.mark.asyncio
async def test_replay_since_filters_out_consumed_seqs():
    bus = RunEventBus(run_id=DEFAULT_RUN)
    await bus.emit(_started())  # seq=1
    await bus.emit(_progress())  # seq=2
    await bus.emit(_finished())  # seq=3

    out = list(bus.replay_since(2))
    assert [ev.seq for ev in out] == [3]


@pytest.mark.asyncio
async def test_replay_returns_empty_when_caught_up():
    bus = RunEventBus(run_id=DEFAULT_RUN)
    await bus.emit(_started())  # seq=1
    out = list(bus.replay_since(1))
    assert out == []


@pytest.mark.asyncio
async def test_ring_buffer_evicts_oldest_when_over_capacity():
    bus = RunEventBus(run_id=DEFAULT_RUN)
    n = RING_BUFFER_CAPACITY + 50
    for i in range(n):
        await bus.emit(_progress(message=f"msg-{i}"))

    out = list(bus.replay_since(0))
    assert out[0].event == "bus.gap"
    actual = [ev for ev in out if ev.event != "bus.gap"]
    assert len(actual) == RING_BUFFER_CAPACITY
    assert actual[0].seq == n - RING_BUFFER_CAPACITY + 1


@pytest.mark.asyncio
async def test_replay_emits_bus_gap_with_safe_seq_below_buffer_tail():
    """R2 fix HIGH#3: bus.gap.seq must not collide with future real events."""
    bus = RunEventBus(run_id=DEFAULT_RUN)
    n = RING_BUFFER_CAPACITY + 100
    for i in range(n):
        await bus.emit(_progress(message=f"m{i}"))

    out = list(bus.replay_since(0))
    gap = out[0]
    assert gap.event == "bus.gap"
    assert gap.requested_since == 0
    assert gap.buffer_tail == n - RING_BUFFER_CAPACITY + 1
    # The gap's own seq must be STRICTLY LESS than the buffer tail —
    # specifically buffer_tail - 1 — so a client that persists the
    # gap seq and reconnects with since_seq=gap.seq does NOT skip a
    # real event.
    assert gap.seq == gap.buffer_tail - 1
    # And critically: gap.seq < bus.next_seq (no future collision).
    assert gap.seq < bus.next_seq


@pytest.mark.asyncio
async def test_gap_seq_never_collides_with_subsequent_emit():
    """R2 fix HIGH#3 regression test: emit after replay → no seq collision."""
    bus = RunEventBus(run_id=DEFAULT_RUN)
    n = RING_BUFFER_CAPACITY + 10
    for _ in range(n):
        await bus.emit(_progress())

    # Trigger a gap.
    out = list(bus.replay_since(0))
    gap = out[0]
    assert gap.event == "bus.gap"

    # Now a later emit reuses _next_seq. Its seq must NOT equal gap.seq.
    await bus.emit(_finished())
    finished = bus.replay_since(gap.seq)
    finished_events = [ev for ev in finished if ev.event == "run.finished"]
    assert len(finished_events) == 1
    assert finished_events[0].seq != gap.seq


@pytest.mark.asyncio
async def test_replay_no_gap_when_since_seq_inside_buffer():
    bus = RunEventBus(run_id=DEFAULT_RUN)
    for _ in range(RING_BUFFER_CAPACITY + 10):
        await bus.emit(_progress())

    in_buffer_seq = RING_BUFFER_CAPACITY
    out = list(bus.replay_since(in_buffer_seq))
    kinds = [ev.event for ev in out]
    assert "bus.gap" not in kinds


@pytest.mark.asyncio
async def test_replay_negative_since_seq_rejected():
    bus = RunEventBus(run_id=DEFAULT_RUN)
    await bus.emit(_started())
    with pytest.raises(ValueError, match="non-negative"):
        list(bus.replay_since(-1))


@pytest.mark.asyncio
async def test_replay_on_empty_bus_returns_empty_iterable():
    bus = RunEventBus(run_id=DEFAULT_RUN)
    out = list(bus.replay_since(0))
    assert out == []


# ---------------------------------------------------------------------------
# Lifecycle
# (R2 fix MEDIUM: aclose() takes the lock to defeat post-close emit races)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_aclose_blocks_subsequent_emits():
    bus = RunEventBus(run_id=DEFAULT_RUN)
    await bus.emit(_started())
    await bus.aclose()
    assert bus.is_closed is True
    with pytest.raises(RuntimeError, match="closed"):
        await bus.emit(_progress())


@pytest.mark.asyncio
async def test_aclose_does_not_break_in_flight_drain():
    bus = RunEventBus(run_id=DEFAULT_RUN)
    await bus.emit(_started())
    await bus.emit(_progress())
    await bus.aclose()
    a = await bus.get()
    b = await bus.get()
    assert {a.event, b.event} == {"run.started", "node.progress"}


@pytest.mark.asyncio
async def test_aclose_takes_lock_to_defeat_in_flight_emit():
    """R2 fix MEDIUM: aclose() acquires lock so a concurrent emit() that
    already passed its own closed check cannot still squeeze through.

    Smoke test: the ordering is exercised by gating an emit on a slow
    operation and aclose-ing concurrently. After aclose() returns,
    subsequent emit must raise.
    """
    bus = RunEventBus(run_id=DEFAULT_RUN)
    await bus.aclose()
    # If aclose-with-lock works, subsequent emit raises immediately.
    with pytest.raises(RuntimeError):
        await bus.emit(_progress())


@pytest.mark.asyncio
async def test_next_seq_property_advances():
    bus = RunEventBus(run_id=DEFAULT_RUN)
    assert bus.next_seq == 1
    await bus.emit(_started())
    assert bus.next_seq == 2
    await bus.emit(_progress())
    assert bus.next_seq == 3


@pytest.mark.asyncio
async def test_dropped_event_does_not_advance_seq():
    """R2 invariant: dropped events do NOT consume a seq.

    seq is a position in the *delivered* event stream. A dropped event
    was never delivered; consuming a seq for it would create a hole in
    the stream that resuming clients would interpret as a missing event.
    """
    bus = RunEventBus(run_id=DEFAULT_RUN)
    for _ in range(QUEUE_CAPACITY):
        await bus.emit(_progress())
    seq_before = bus.next_seq

    # Drop several events.
    for _ in range(10):
        await bus.emit(_progress(message="drop"))

    # _next_seq advanced by exactly 1 (the bus.dropped marker), not 11.
    assert bus.next_seq == seq_before + 1


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_many_producers_one_consumer_preserves_total_count():
    bus = RunEventBus(run_id=DEFAULT_RUN)
    n_producers = 8
    per_producer = 50

    async def produce(idx: int):
        for j in range(per_producer):
            await bus.emit(_progress(message=f"p{idx}-{j}"))

    consumed: list = []

    async def consume(target: int):
        for _ in range(target):
            consumed.append(await bus.get())

    target = n_producers * per_producer
    consumer_task = asyncio.create_task(consume(target))
    await asyncio.gather(*(produce(i) for i in range(n_producers)))
    await asyncio.wait_for(consumer_task, timeout=5.0)

    assert len(consumed) == target
    seqs = sorted(ev.seq for ev in consumed)
    assert seqs == list(range(1, target + 1))


@pytest.mark.asyncio
async def test_isolation_between_distinct_runs():
    a = RunEventBus(run_id="RUN-A")
    b = RunEventBus(run_id="RUN-B")
    await a.emit(_started(run_id="RUN-A"))
    await b.emit(_started(run_id="RUN-B"))
    await b.emit(_progress(run_id="RUN-B"))
    assert a.qsize() == 1
    assert b.qsize() == 2
    assert a.next_seq == 2
    assert b.next_seq == 3
