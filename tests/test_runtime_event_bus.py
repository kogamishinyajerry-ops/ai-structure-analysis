"""Tests for backend.app.runtime.event_bus (ADR-014 §Backpressure / §Resume)."""

from __future__ import annotations

import asyncio

import pytest

from backend.app.runtime.event_bus import (
    QUEUE_CAPACITY,
    RING_BUFFER_CAPACITY,
    RunEventBus,
)
from schemas.ws_events import (
    NodeEntered,
    NodeProgress,
    RunFinished,
    RunStarted,
)

# ---------------------------------------------------------------------------
# Fixtures + helpers
# ---------------------------------------------------------------------------


def _started(run_id: str = "RUN-1") -> RunStarted:
    return RunStarted(
        run_id=run_id,
        seq=0,  # placeholder; emit() reassigns
        ts="2026-04-26T12:00:00Z",
        task_spec_digest="sha256:" + "a" * 64,
    )


def _progress(run_id: str = "RUN-1", message: str = "step") -> NodeProgress:
    return NodeProgress(
        run_id=run_id,
        seq=0,
        ts="2026-04-26T12:00:00Z",
        node_name="geometry",
        message=message,
    )


def _node_entered(run_id: str = "RUN-1", node_name: str = "geometry") -> NodeEntered:
    return NodeEntered(
        run_id=run_id,
        seq=0,
        ts="2026-04-26T12:00:00Z",
        node_name=node_name,
        stage="geometry",
    )


def _finished(run_id: str = "RUN-1") -> RunFinished:
    return RunFinished(
        run_id=run_id,
        seq=0,
        ts="2026-04-26T12:00:00Z",
        terminal_status="success",
        total_duration_ms=42,
    )


# ---------------------------------------------------------------------------
# Construction + invariants
# ---------------------------------------------------------------------------


def test_construct_with_empty_run_id_rejected():
    with pytest.raises(ValueError, match="non-empty"):
        RunEventBus(run_id="")


def test_capacity_constants_match_adr_014():
    """ADR-014 §Backpressure pins QUEUE=1024 / RING=256."""
    assert QUEUE_CAPACITY == 1024
    assert RING_BUFFER_CAPACITY == 256


# ---------------------------------------------------------------------------
# Producer / consumer happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_emit_assigns_monotonic_seq():
    bus = RunEventBus(run_id="RUN-A")
    await bus.emit(_started())
    await bus.emit(_progress())
    await bus.emit(_finished())

    a = await bus.get()
    b = await bus.get()
    c = await bus.get()
    assert (a.seq, b.seq, c.seq) == (1, 2, 3)


@pytest.mark.asyncio
async def test_emit_preserves_event_type():
    bus = RunEventBus(run_id="RUN-A")
    await bus.emit(_started(run_id="RUN-A"))
    out = await bus.get()
    assert isinstance(out, RunStarted)
    assert out.run_id == "RUN-A"


@pytest.mark.asyncio
async def test_get_blocks_until_emit():
    bus = RunEventBus(run_id="RUN-A")
    consumer = asyncio.create_task(bus.get())
    await asyncio.sleep(0.01)  # let the consumer start awaiting
    assert not consumer.done()
    await bus.emit(_progress(message="hello"))
    out = await asyncio.wait_for(consumer, timeout=0.5)
    assert out.message == "hello"


@pytest.mark.asyncio
async def test_qsize_reflects_queue():
    bus = RunEventBus(run_id="RUN-A")
    assert bus.qsize() == 0
    await bus.emit(_progress())
    await bus.emit(_progress())
    assert bus.qsize() == 2
    await bus.get()
    assert bus.qsize() == 1


# ---------------------------------------------------------------------------
# Backpressure: non-critical events drop on overflow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_overflow_drops_non_critical_and_emits_bus_dropped():
    bus = RunEventBus(run_id="RUN-A")
    # Fill queue to cap with non-critical events.
    for _ in range(QUEUE_CAPACITY):
        await bus.emit(_progress())
    assert bus.qsize() == QUEUE_CAPACITY

    # One more non-critical event → it gets dropped, bus.dropped enqueued.
    await bus.emit(_progress(message="will be dropped"))

    # Queue size should be cap+1 now (the synthetic bus.dropped pushed
    # above cap because synthetic events bypass it).
    assert bus.qsize() == QUEUE_CAPACITY + 1

    # Drain everything; the FIRST cap items are the original progress
    # events; the LAST is bus.dropped — the dropping happened "newest
    # first" per the impl.
    drained = []
    while bus.qsize() > 0:
        drained.append(await bus.get())
    kinds = [ev.event for ev in drained]
    # All but the last should be node.progress; last must be bus.dropped.
    assert kinds[:-1] == ["node.progress"] * QUEUE_CAPACITY
    assert kinds[-1] == "bus.dropped"

    # The bus.dropped should record the dropped kind.
    assert drained[-1].dropped_kinds == ("node.progress",)
    assert drained[-1].dropped_count == 1


@pytest.mark.asyncio
async def test_critical_events_bypass_cap():
    """run.started / run.finished / handoff.required NEVER drop on overflow."""
    bus = RunEventBus(run_id="RUN-A")
    # Fill queue to cap with non-critical.
    for _ in range(QUEUE_CAPACITY):
        await bus.emit(_progress())
    assert bus.qsize() == QUEUE_CAPACITY

    # Critical event should enqueue and exceed cap (not drop, not block).
    await asyncio.wait_for(bus.emit(_finished()), timeout=0.5)
    assert bus.qsize() == QUEUE_CAPACITY + 1


@pytest.mark.asyncio
async def test_critical_event_seq_is_unique_when_bypassing_cap():
    bus = RunEventBus(run_id="RUN-A")
    for _ in range(QUEUE_CAPACITY):
        await bus.emit(_progress())
    await bus.emit(_finished())
    await bus.emit(_started())  # also critical

    # Drain everything; collect seqs for critical events.
    seqs_by_kind: dict[str, list[int]] = {}
    while bus.qsize() > 0:
        ev = await bus.get()
        seqs_by_kind.setdefault(ev.event, []).append(ev.seq)
    assert len(seqs_by_kind["run.finished"]) == 1
    assert len(seqs_by_kind["run.started"]) == 1
    # Seqs are still strictly monotonic across critical-bypass.
    finished_seq = seqs_by_kind["run.finished"][0]
    started_seq = seqs_by_kind["run.started"][0]
    assert finished_seq < started_seq  # finished was emitted first


# ---------------------------------------------------------------------------
# Ring buffer + replay
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_replay_since_zero_returns_all_buffered_events():
    bus = RunEventBus(run_id="RUN-A")
    await bus.emit(_started())
    await bus.emit(_progress())
    await bus.emit(_finished())

    out = list(bus.replay_since(0))
    assert [ev.event for ev in out] == ["run.started", "node.progress", "run.finished"]


@pytest.mark.asyncio
async def test_replay_since_filters_out_consumed_seqs():
    bus = RunEventBus(run_id="RUN-A")
    await bus.emit(_started())  # seq=1
    await bus.emit(_progress())  # seq=2
    await bus.emit(_finished())  # seq=3

    out = list(bus.replay_since(2))
    assert [ev.seq for ev in out] == [3]


@pytest.mark.asyncio
async def test_replay_returns_empty_when_caught_up():
    bus = RunEventBus(run_id="RUN-A")
    await bus.emit(_started())  # seq=1
    out = list(bus.replay_since(1))
    assert out == []


@pytest.mark.asyncio
async def test_ring_buffer_evicts_oldest_when_over_capacity():
    bus = RunEventBus(run_id="RUN-A")
    # Emit MORE than ring buffer capacity.
    n = RING_BUFFER_CAPACITY + 50
    for i in range(n):
        await bus.emit(_progress(message=f"msg-{i}"))

    # Ring should hold only the LAST RING_BUFFER_CAPACITY events.
    out = list(bus.replay_since(0))
    # First entry will be a synthetic bus.gap because seq=0+1=1 is older
    # than the ring's tail (which starts at seq=51).
    assert out[0].event == "bus.gap"
    # The remaining events are the actual progress entries kept.
    actual = [ev for ev in out if ev.event != "bus.gap"]
    assert len(actual) == RING_BUFFER_CAPACITY
    # Oldest kept seq is 51 (since first 50 evicted).
    assert actual[0].seq == n - RING_BUFFER_CAPACITY + 1


@pytest.mark.asyncio
async def test_replay_emits_bus_gap_when_since_seq_below_buffer_tail():
    bus = RunEventBus(run_id="RUN-A")
    # Force eviction.
    n = RING_BUFFER_CAPACITY + 100
    for i in range(n):
        await bus.emit(_progress(message=f"m{i}"))

    out = list(bus.replay_since(0))
    gap = out[0]
    assert gap.event == "bus.gap"
    assert gap.requested_since == 0
    # buffer_tail is the seq of the oldest *retained* event.
    assert gap.buffer_tail == n - RING_BUFFER_CAPACITY + 1


@pytest.mark.asyncio
async def test_replay_no_gap_when_since_seq_inside_buffer():
    bus = RunEventBus(run_id="RUN-A")
    for _ in range(RING_BUFFER_CAPACITY + 10):  # cause eviction
        await bus.emit(_progress())

    # Pick a seq that's still in the buffer.
    in_buffer_seq = RING_BUFFER_CAPACITY  # safely past the eviction edge
    out = list(bus.replay_since(in_buffer_seq))
    kinds = [ev.event for ev in out]
    assert "bus.gap" not in kinds


@pytest.mark.asyncio
async def test_replay_negative_since_seq_rejected():
    bus = RunEventBus(run_id="RUN-A")
    await bus.emit(_started())
    with pytest.raises(ValueError, match="non-negative"):
        list(bus.replay_since(-1))


@pytest.mark.asyncio
async def test_replay_on_empty_bus_returns_empty_iterable():
    bus = RunEventBus(run_id="RUN-A")
    out = list(bus.replay_since(0))
    assert out == []


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_close_blocks_subsequent_emits():
    bus = RunEventBus(run_id="RUN-A")
    await bus.emit(_started())
    bus.close()
    assert bus.is_closed is True
    with pytest.raises(RuntimeError, match="closed"):
        await bus.emit(_progress())


@pytest.mark.asyncio
async def test_close_does_not_break_in_flight_drain():
    bus = RunEventBus(run_id="RUN-A")
    await bus.emit(_started())
    await bus.emit(_progress())
    bus.close()
    # Already-enqueued events still drain.
    a = await bus.get()
    b = await bus.get()
    assert {a.event, b.event} == {"run.started", "node.progress"}


@pytest.mark.asyncio
async def test_next_seq_property_advances():
    bus = RunEventBus(run_id="RUN-A")
    assert bus.next_seq == 1
    await bus.emit(_started())
    assert bus.next_seq == 2
    await bus.emit(_progress())
    assert bus.next_seq == 3


# ---------------------------------------------------------------------------
# Concurrency: many producers, one consumer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_many_producers_one_consumer_preserves_total_count():
    bus = RunEventBus(run_id="RUN-A")
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
    # All seqs are unique and form 1..target.
    seqs = sorted(ev.seq for ev in consumed)
    assert seqs == list(range(1, target + 1))


@pytest.mark.asyncio
async def test_isolation_between_distinct_runs():
    """Distinct run_ids own distinct seq counters and queues."""
    a = RunEventBus(run_id="RUN-A")
    b = RunEventBus(run_id="RUN-B")
    await a.emit(_started(run_id="RUN-A"))
    await b.emit(_started(run_id="RUN-B"))
    await b.emit(_progress(run_id="RUN-B"))
    assert a.qsize() == 1
    assert b.qsize() == 2
    assert a.next_seq == 2
    assert b.next_seq == 3
