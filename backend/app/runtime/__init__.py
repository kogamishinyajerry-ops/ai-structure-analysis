"""Workbench runtime — in-process event bus + LangGraph callback bridge (ADR-014).

The runtime layer translates between LangGraph's signal model and the
workbench's WebSocket event stream. This package owns:

- `event_bus`: asyncio.Queue + ring buffer + bounded backpressure
- `langgraph_callbacks` (Phase 2.1 follow-up): LangGraph signals → WS events

See `docs/adr/ADR-014-ws-event-bus-for-workbench.md`.
"""
