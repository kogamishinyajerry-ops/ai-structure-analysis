"""Per-run in-process event bus (ADR-014 §Backpressure / §Resume semantics).

A `RunEventBus` owns:

- a producer-side soft-bounded queue (cap 1024) — LangGraph callbacks
  enqueue events here as the run progresses; the WS endpoint drains it
- a 256-event ring buffer for resume-via-`?since_seq` — the WS endpoint
  uses this when a client reconnects mid-run
- a monotonic per-run `seq` counter so consumers can detect gaps

Backpressure rules (per ADR-014 §Backpressure):

- soft cap = 1024 entries. The cap is a non-critical-drop trigger,
  not a hard memory ceiling.
- when the queue is at cap and a NON-CRITICAL event arrives: drop the
  arriving event. Consumers learn about the loss via a `bus.dropped`
  event. To bound memory, consecutive drops *coalesce* into a single
  tail `bus.dropped` (incrementing `dropped_count`, appending to
  `dropped_kinds`). The queue grows by AT MOST one extra slot for the
  bus.dropped marker itself; further drops mutate that marker rather
  than appending a new one.
- CRITICAL events (`run.started`, `run.finished`, `handoff.required`)
  bypass the cap. They MAY push the queue temporarily above 1024.
  Losing them would leave the frontend hung forever.

Ring-buffer (per ADR-014 §Resume semantics):

- retains the last 256 events ACTUALLY DELIVERED to the queue
- events that get dropped on overflow are NOT in the ring (dropped
  means dropped — replay must not resurrect them or live clients
  would have seen events that resuming clients now see for the first
  time)
- `replay_since(seq)` returns events with seq > `seq`
- if `seq` is older than the buffer's tail, the result starts with a
  synthetic `bus.gap` carrying `requested_since` + `buffer_tail`. The
  gap's `seq` is `buffer_tail - 1` (just outside the buffer) — it is
  NOT drawn from `_next_seq` so it cannot collide with a real event a
  later resume might receive.
- the gap event is NEVER added to the ring/queue. It is purely a
  resume-protocol artifact.

Implementation note: the queue is a `collections.deque` + an
`asyncio.Event` for "events available", NOT `asyncio.Queue`. The cap
is a soft trigger for the drop-non-critical path; we do not need
`asyncio.Queue`'s internal `put` semaphore + `_unfinished_tasks`
machinery, which is private API.

This module is pure asyncio + Pydantic; no FastAPI / no LangGraph
imports. The WS endpoint and the LangGraph callbacks are separate
modules that wrap this bus.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone

from schemas.ws_events import (
    CRITICAL_EVENT_KINDS,
    BusDropped,
    BusGap,
    WSEvent,
    is_critical,
)

logger = logging.getLogger(__name__)

# Per ADR-014 §Backpressure / §Resume semantics.
QUEUE_CAPACITY = 1024
RING_BUFFER_CAPACITY = 256
# Cap on `dropped_kinds` list inside a coalesced bus.dropped — keeps
# the marker bounded under arbitrary-long bursts of distinct kinds.
DROPPED_KINDS_CAP = 16


def _utcnow_iso() -> str:
    """ISO 8601 UTC timestamp with second precision and trailing 'Z'."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class RunEventBus:
    """Per-run event bus.

    Construct one bus per run id. The orchestrator that invokes
    LangGraph holds a reference; the WS endpoint resolves the bus from
    a registry (Phase 2.1 follow-up) when a client connects.
    """

    run_id: str
    _queue: deque = field(init=False)
    _has_event: asyncio.Event = field(init=False)
    _ring: deque = field(init=False)
    _next_seq: int = field(init=False, default=1)
    _closed: bool = field(init=False, default=False)
    _lock: asyncio.Lock = field(init=False)

    def __post_init__(self) -> None:
        if not self.run_id:
            raise ValueError("run_id must be a non-empty string")
        self._queue = deque()
        self._has_event = asyncio.Event()
        self._ring = deque(maxlen=RING_BUFFER_CAPACITY)
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Producer side
    # ------------------------------------------------------------------

    async def emit(self, event: WSEvent) -> None:  # type: ignore[valid-type]
        """Append an event to the bus.

        - validates `event.run_id == self.run_id` (defends against a
          caller bug contaminating one run's stream with another run's
          event)
        - assigns the next monotonic seq
        - on enqueue success: also records in the ring buffer for
          replay; dropped events are NEVER ringed
        - critical events bypass the cap; non-critical events arriving
          on a full queue coalesce into a tail `bus.dropped` (no
          unbounded growth)

        Raises RuntimeError if the bus has been `close()`-d.
        Raises ValueError on run_id mismatch or empty input.
        """
        if event is None:
            raise ValueError("event must not be None")
        if event.run_id != self.run_id:
            raise ValueError(
                f"event.run_id={event.run_id!r} does not match "
                f"bus.run_id={self.run_id!r}"
            )

        async with self._lock:
            if self._closed:
                raise RuntimeError(f"event bus for run {self.run_id} is closed")

            critical = is_critical(event.event)

            if not critical and len(self._queue) >= QUEUE_CAPACITY:
                # Non-critical event arriving on a full queue → DROP.
                # Do NOT assign a seq, do NOT ring-append. The fact of
                # the drop surfaces via a coalesced bus.dropped tail.
                self._record_drop(event.event)
                return

            # Path A (normal) or critical-bypass.
            sealed = event.model_copy(update={"seq": self._next_seq})
            self._next_seq += 1
            self._ring.append(sealed)
            self._enqueue(sealed)

            if critical and len(self._queue) > QUEUE_CAPACITY:
                logger.info(
                    "run %s emitted critical event %s while queue at capacity %d",
                    self.run_id,
                    sealed.event,
                    QUEUE_CAPACITY,
                )

    def _enqueue(self, event: WSEvent) -> None:  # type: ignore[valid-type]
        self._queue.append(event)
        self._has_event.set()

    def _record_drop(self, dropped_kind: str) -> None:
        """Coalesce a drop into a tail `bus.dropped`.

        Always called under the bus lock. The contract is "queue grows
        by at most one extra slot for the bus.dropped marker itself;
        further drops mutate that marker rather than appending".

        Implementation: if the queue's tail is already a `bus.dropped`,
        replace it with an incremented copy (Pydantic frozen forbids
        in-place mutation). If not, append a fresh bus.dropped — that
        single extra slot above QUEUE_CAPACITY is the documented +1
        overhead; subsequent drops coalesce into it.
        """
        # Look at the queue's current tail.
        tail = self._queue[-1] if self._queue else None
        if tail is not None and tail.event == "bus.dropped":
            # Coalesce: replace tail with an incremented copy.
            existing_kinds = list(tail.dropped_kinds)
            new_kinds = (
                tuple(existing_kinds + [dropped_kind])
                if len(existing_kinds) < DROPPED_KINDS_CAP
                else tuple(existing_kinds)
            )
            new_tail = tail.model_copy(
                update={
                    "dropped_count": tail.dropped_count + 1,
                    "dropped_kinds": new_kinds,
                    "ts": _utcnow_iso(),
                }
            )
            # Replace queue tail.
            self._queue[-1] = new_tail
            # Replace ring tail (the same object lives there if it
            # was the most-recent entry; otherwise leave the ring
            # alone — replay should still surface this loss via the
            # queue if the consumer drains, or via the next ring
            # entry if it doesn't).
            for i in range(len(self._ring) - 1, -1, -1):
                if self._ring[i] is tail:
                    self._ring[i] = new_tail
                    break
            return

        # No bus.dropped at tail — emit a fresh one. This is the only
        # path that can grow the queue past QUEUE_CAPACITY for
        # non-critical reasons; the ADR's "documented +1 overhead".
        bus_dropped = BusDropped(
            run_id=self.run_id,
            seq=self._next_seq,
            ts=_utcnow_iso(),
            dropped_count=1,
            dropped_kinds=(dropped_kind,),
        )
        self._next_seq += 1
        self._ring.append(bus_dropped)
        self._enqueue(bus_dropped)

    # ------------------------------------------------------------------
    # Consumer side
    # ------------------------------------------------------------------

    async def get(self) -> WSEvent:  # type: ignore[valid-type]
        """Block until an event is available, then return it."""
        while True:
            async with self._lock:
                if self._queue:
                    event = self._queue.popleft()
                    if not self._queue:
                        self._has_event.clear()
                    return event
            await self._has_event.wait()

    def qsize(self) -> int:
        return len(self._queue)

    def replay_since(self, since_seq: int) -> Iterable[WSEvent]:  # type: ignore[valid-type]
        """Replay events with seq > `since_seq` from the ring buffer.

        If `since_seq` is older than the buffer's tail (events have
        been evicted), the iterable starts with a synthetic `bus.gap`
        carrying `requested_since` and `buffer_tail`. The gap's seq is
        `max(0, buffer_tail - 1)` — purposely OUTSIDE `_next_seq`'s
        sequence so a later resume that persists this seq cannot
        collide with a real event.

        The gap event is NEVER added to the ring/queue. It is a
        resume-protocol artifact.
        """
        if since_seq < 0:
            raise ValueError("since_seq must be non-negative")

        # Materialize a snapshot — the ring may mutate concurrently if
        # an emit() lands while iteration is in flight.
        snapshot = list(self._ring)
        if not snapshot:
            return iter(())

        oldest_seq = snapshot[0].seq
        if since_seq + 1 < oldest_seq:
            # Gap seq sits just below the buffer's tail; never overlaps
            # with a real event seq.
            gap_seq = max(0, oldest_seq - 1)
            gap = BusGap(
                run_id=self.run_id,
                seq=gap_seq,
                ts=_utcnow_iso(),
                requested_since=since_seq,
                buffer_tail=oldest_seq,
            )
            tail = [ev for ev in snapshot if ev.seq > since_seq]
            return iter([gap, *tail])

        return iter(ev for ev in snapshot if ev.seq > since_seq)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @property
    def next_seq(self) -> int:
        return self._next_seq

    @property
    def is_closed(self) -> bool:
        return self._closed

    async def aclose(self) -> None:
        """Mark the bus closed under the lock.

        After aclose(), `emit()` raises. Consumers awaiting `get()`
        continue to drain whatever is in-flight; the WS endpoint breaks
        out of its read loop on receipt of a terminal event
        (`run.finished` / `bus.gap`).

        We take the lock so a concurrent emit() that already passed its
        own closed check cannot still squeeze a write through.
        """
        async with self._lock:
            self._closed = True

    def close(self) -> None:
        """Synchronous convenience for tests/single-threaded callers.

        Prefer `aclose()` from async contexts. This sets the flag
        without lock acquisition; concurrent emits MAY race past the
        flag check exactly once. The async path is safe.
        """
        self._closed = True


__all__ = [
    "QUEUE_CAPACITY",
    "RING_BUFFER_CAPACITY",
    "DROPPED_KINDS_CAP",
    "RunEventBus",
    "CRITICAL_EVENT_KINDS",
]
