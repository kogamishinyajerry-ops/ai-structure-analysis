"""Per-run in-process event bus (ADR-014 §Backpressure / §Resume semantics).

A `RunEventBus` owns:

- a producer-side bounded queue (cap 1024) — LangGraph callbacks enqueue
  events here as the run progresses; the WS endpoint drains it
- a 256-event ring buffer for resume-via-`?since_seq` — the WS endpoint
  uses this when a client reconnects mid-run
- monotonic per-run `seq` counter so consumers can detect gap

Backpressure rules (per ADR-014 §Backpressure):

- queue capacity = 1024
- when the queue is full and a non-critical event arrives: drop the
  arriving event and enqueue a synthetic `bus.dropped` so the frontend
  can render a banner
- critical events (`run.started`, `run.finished`, `handoff.required`)
  bypass the cap. They MAY push the queue temporarily above 1024.
  Losing them would leave the frontend hung forever, so the cap is a
  *non-critical-drop trigger*, not a hard size limit

Ring-buffer (per ADR-014 §Resume semantics):

- retains the last 256 events emitted on this run
- `replay_since(seq)` returns events with seq > `seq`
- if `seq` is older than the buffer's tail, the result starts with a
  synthetic `bus.gap` describing the requested window vs. what the
  buffer actually holds; the frontend must refetch state via REST

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

        Behavior:

        - assigns the next monotonic seq, records the event in the
          ring buffer, and enqueues for the consumer
        - when the queue is at `QUEUE_CAPACITY` and the new event is
          non-critical, the new event itself is dropped and a synthetic
          `bus.dropped` is enqueued in its place (the queue is sized
          for the worst chatty-progress scenario; under load the most
          recent progress is the most informative one to keep, but we
          deliberately drop *new* non-critical events rather than
          rewriting the queue's middle to keep ordering stable)
        - critical events (`run.started`, `run.finished`,
          `handoff.required`) bypass the cap. They MAY push the queue
          temporarily above `QUEUE_CAPACITY` — losing them would leave
          the frontend hung forever, which is unacceptable.

        Raises RuntimeError if the bus has been `close()`-d.
        """
        if self._closed:
            raise RuntimeError(f"event bus for run {self.run_id} is closed")

        async with self._lock:
            sealed = event.model_copy(update={"seq": self._next_seq})
            self._next_seq += 1
            self._ring.append(sealed)

            if len(self._queue) < QUEUE_CAPACITY:
                self._enqueue(sealed)
                return

            # Queue at capacity.
            if is_critical(sealed.event):
                # Critical events bypass the cap. Enqueue and let the
                # queue grow; the consumer will drain.
                self._enqueue(sealed)
                logger.info(
                    "run %s emitted critical event %s while queue at capacity %d",
                    self.run_id,
                    sealed.event,
                    QUEUE_CAPACITY,
                )
                return

            # Non-critical event arriving on a full queue: drop it
            # (most recent non-critical is "newest" and tends to be
            # `node.progress`; its loss is the documented degraded
            # mode in ADR-014 §Consequences) and emit a synthetic
            # `bus.dropped` so the frontend can show a banner.
            self._enqueue_synthetic_drop(sealed.event)

    def _enqueue(self, event: WSEvent) -> None:  # type: ignore[valid-type]
        self._queue.append(event)
        self._has_event.set()

    def _enqueue_synthetic_drop(self, dropped_kind: str) -> None:
        """Record (in the ring) and enqueue a synthetic `bus.dropped`.

        Always called under the bus lock from `emit()`. The synthetic
        event is exempt from the cap on the same grounds as critical
        events: losing the bus.dropped notification would mask the
        original loss from the frontend.
        """
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
        """Replay events with seq > since_seq from the ring buffer.

        If the requested `since_seq` is older than the buffer's tail
        (meaning events have been evicted), the iterable starts with a
        synthetic `bus.gap` describing the requested window. The caller
        must then refetch state via REST per ADR-014 §Resume semantics.
        """
        if since_seq < 0:
            raise ValueError("since_seq must be non-negative")

        # Materialize a snapshot to avoid concurrent-mutation surprises
        # mid-iteration.
        snapshot = list(self._ring)
        if not snapshot:
            return iter(())

        oldest_seq = snapshot[0].seq
        if since_seq + 1 < oldest_seq:
            gap = BusGap(
                run_id=self.run_id,
                seq=self._next_seq,
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

    def close(self) -> None:
        """Mark the bus closed.

        After close(), `emit()` raises. Consumers that are awaiting
        `get()` will continue to drain whatever is in-flight; the WS
        endpoint breaks out of its read loop on receipt of a terminal
        event (`run.finished` / `bus.gap`).
        """
        self._closed = True


__all__ = [
    "QUEUE_CAPACITY",
    "RING_BUFFER_CAPACITY",
    "RunEventBus",
    "CRITICAL_EVENT_KINDS",
]
