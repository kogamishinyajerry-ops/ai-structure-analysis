# ADR-014: WebSocket Event Bus for the Workbench

- **Status:** Draft (post-R2 of #24/#25, pending Codex R1)
- **Decider:** Claude Code CLI (Opus 4.7, 1M context) — human-confirmed
- **Date:** 2026-04-26
- **Related Phase:** 2.0 — Workbench Skeleton (the first concrete artifact of the engineer-facing visualization workbench pivot)
- **Branch:** `feature/AI-FEA-ADR-014-ws-event-bus`
- **Companion ADRs (Draft, parallel):** ADR-015 (Workbench → Agent RPC boundary), ADR-016 (`.frd → .vtu` + result viz stack), ADR-017 (RAG facade in-process + CLI/lib parity)

---

## Context

Phase 1.5 closes a Foundation-Freeze that culminates in Phase 2: a Web Console that lets engineers run end-to-end FEA simulations through this project. Phase 2's North Star (per the 2026-04-26 architecture review by Opus 4.7 in Notion):

> "可视化仿真工作台,让任何一个工程师一上手就能用这个系统进行全流程仿真,并且清晰的看到逐步的流程"

The Phase 2 architecture review settled three questions whose joint answer determines the workbench's runtime shape:

1. **Backend stack** = FastAPI + Pydantic v2 (already on `main`); the workbench is not a Streamlit demo
2. **Frontend stack** = React/TypeScript over WebSocket
3. **Visibility** = engineers must see every LangGraph node entered/exited, every agent decision, every RAG retrieval, every Reviewer verdict — not a black-box "spinner then result"

The remaining design question, which **this ADR closes**, is: *what is the on-the-wire contract between the LangGraph runtime and the React frontend*?

This is the first time agent-internal state will leave the Python process. The contract chosen here will determine:

- whether agents on `main` need to be modified (HF1 risk)
- what raw text leaks to a browser tab (security/privacy risk per Q7-R3 of the architecture review)
- how the frontend handles disconnect/reconnect during a 30-minute CalculiX run (engineering-trust risk per Q7-R8)
- whether the four already-merged-in-PR-stack RAG CLIs (`#38`–`#48`) can plug into the workbench without re-implementation

---

## Decision

**Wire format**: a single WebSocket endpoint at `/ws/runs/{run_id}` emitting an append-only stream of typed JSON events. Each event carries `schema_version: "v1"`, an integer `seq`, an ISO-8601 `ts`, and a discriminator field `event`.

**Transport**: native WebSockets via FastAPI's `websockets` integration. **No Redis / Kafka / RabbitMQ.** Phase 2 is single-node; an in-process `asyncio.Queue` is the bus, fed by LangGraph callbacks and drained by the WebSocket endpoint.

**Schema location**: a new file `schemas/ws_events.py` (Pydantic v2 models, `frozen=True`, `extra="forbid"`). **Not** in `schemas/sim_state.py` (HF1.4); a separate file with no overlap to existing state.

**LangGraph integration**: a new module `backend/app/runtime/langgraph_callbacks.py` registers a callback handler with `config={"callbacks": [...]}`. **No agent file is modified** — `agents/router.py`, `agents/architect.py`, `agents/geometry.py`, `agents/mesh.py`, `agents/solver.py`, `agents/reviewer.py`, `agents/calculix_driver.py` are all untouched. (Of these, HF1.1, HF1.2, HF1.3, HF1.5 are HF1 — touching them would require an HF1 zone-carve ADR, which we are deliberately avoiding.)

**Privacy / data-leak boundary**: events MUST NOT carry agent prompt text, raw RAG chunk text, raw user CAD bytes, or any field with `_secret` / `_internal` in its name. Large bodies travel as **digest references** (`inputs_digest: "sha256:..."`); the frontend pulls the body via a separate authenticated REST endpoint `GET /runs/{run_id}/nodes/{node_name}/io` only when a user explicitly clicks "Show details".

**Backpressure**: the in-process queue is bounded (capacity 1024). On overflow the *oldest non-critical* event is dropped (terminal events `run.started` / `run.finished` / `handoff.required` / `node.exited(status=err)` are never dropped). A `bus.dropped` event records the loss, so the frontend can show a banner.

**Resume semantics**: the endpoint accepts `?since_seq=N` on connect; the bus retains a per-run ring buffer of the last 256 events. If `N` is older than the buffer's tail, the endpoint emits `bus.gap` and the frontend MUST refetch state via REST (not from the bus alone).

---

## Event schema (v1)

The full Pydantic models will live in `schemas/ws_events.py`. This section is the contract reviewers must approve.

| event | when emitted | required fields | optional fields |
|-------|--------------|----------------|----------------|
| `run.started` | LangGraph compile + invoke succeeded | `run_id`, `seq`, `ts`, `task_spec_digest` | `started_at`, `submitted_by` |
| `node.entered` | LangGraph node function entered | `run_id`, `seq`, `ts`, `node_name`, `stage` | `inputs_digest` |
| `node.progress` | node-internal explicit emit | `run_id`, `seq`, `ts`, `node_name`, `message` | `percent` (0–100) |
| `node.exited` | node function returned (success or error) | `run_id`, `seq`, `ts`, `node_name`, `duration_ms`, `status` | `outputs_digest`, `error_class` |
| `artifact.ready` | a tracked artifact landed on disk | `run_id`, `seq`, `ts`, `kind`, `path`, `bytes` | `digest`, `mime` |
| `rag.queried` | `reviewer_advisor.advise()` or kb.query was called | `run_id`, `seq`, `ts`, `query_digest`, `top_k_titles[]`, `scores[]` | `source_filter` |
| `surrogate.hint` | a `SurrogateHint` was generated | `run_id`, `seq`, `ts`, `provider`, `case_id`, `quantities_summary[]` | `confidence_indicator` |
| `reviewer.verdict` | the Reviewer node produced a verdict | `run_id`, `seq`, `ts`, `verdict`, `fault_class`, `deviation_pct?` | `notion_task_url` |
| `handoff.required` | a TrustGate verdict requires human review | `run_id`, `seq`, `ts`, `reason`, `notion_task_url` | `recommended_action` |
| `bus.dropped` | bounded queue dropped a non-critical event | `run_id`, `seq`, `ts`, `dropped_count`, `dropped_kinds[]` | — |
| `bus.gap` | resume requested before the ring buffer's tail | `run_id`, `seq`, `ts`, `requested_since`, `buffer_tail` | — |
| `run.finished` | the LangGraph state machine exited | `run_id`, `seq`, `ts`, `terminal_status`, `total_duration_ms` | `failure_summary` |

Key constraints:

- `stage` ∈ `{intent, geometry, mesh, solver, review, handoff}` — fixed enum, names match Phase 1's existing six-stage DAG
- `status` (on `node.exited`) ∈ `{ok, err, skipped}`
- `verdict` ∈ `{Accept, Accept with Note, Reject, Needs Review, Re-run}` — matches `reviewer_advisor.GOVERNANCE_BIASING_VERDICTS` plus the non-biasing ones
- `terminal_status` ∈ `{success, error, cancelled, handoff}`
- `quantities_summary[]` is a tuple of `(name, value, unit, confidence)` — **never** the full SurrogateHint (no notes, no provider-specific extras)
- `task_spec_digest`, `inputs_digest`, `outputs_digest`, `query_digest` are SHA-256 hex strings

---

## Considered alternatives

### gRPC streaming
Pros: typed, multiplexed, mature.
Cons: requires `grpc-web` proxy in front of the React app; adds an extra hop and a new mental-model burden. We are running everything in one Python process; multiplexing is overkill. **Rejected.**

### Server-Sent Events (SSE)
Pros: simpler than WebSocket (one-way HTTP stream, browser-native); no upgrade handshake.
Cons: one-way only — but the workbench will eventually need user → server commands (cancel run, request retry). Re-using WebSocket here saves a future migration. **Rejected for the workbench critical path; SSE retained as a fallback for read-only embedded views in Phase 2.3+.**

### Polling + REST snapshots
Pros: no long-lived connections; works through any proxy.
Cons: latency floor ≥ poll interval; for engineering trust we need <500 ms node-state latency. **Rejected.**

### Redis pub/sub now
Pros: future-proof for multi-node.
Cons: adds an operational dependency before any user has logged in. The architecture review explicitly recommends *not* introducing Redis until Phase 3. **Rejected for Phase 2.**

---

## Consequences

**Intended:**

- Workbench frontend can render every LangGraph stage transition in <100 ms of the agent producing it
- Disconnect/reconnect during a 30-min CalculiX run survives via `?since_seq` resume
- New event kinds add to the schema as `v1` minor extensions; consumers ignore unknown `event` strings
- Agents and HF1 zones stay untouched; the visibility layer is purely additive
- The four RAG CLIs from PR #38–#48 plug into `rag.queried` events via the in-process facade ADR-017 will define

**Unintended (acknowledged):**

- One process bug now spans Python + JS — debugging requires both stacks; ADR-014 includes a contract test (described below) to keep regressions on one side
- The 1024-event queue cap means a sufficiently chatty run can drop `node.progress` events; users will see progress jump rather than animate. Acceptable: progress is informational, not authoritative
- The ring-buffer tail of 256 events means a frontend can permanently miss events if it disconnects for more than ~10 minutes during a busy run. The `bus.gap` event tells it to refetch via REST; not silent loss

**Out of scope:**

- Multi-tenant isolation: Phase 2 assumes a single trusted operator per server. Multi-user comes in Phase 2.4+
- Authentication on the WS endpoint: deferred to Phase 2.1 (ADR-015 will spec the auth boundary alongside the RPC contract)
- Persisting the event stream to disk for replay/audit: a future ADR (likely ADR-019 or later)

---

## Implementation plan

This ADR alone produces no executable code beyond the schema file; the workbench code is in subsequent PRs (Phase 2.0).

| File | Status | Owner | Notes |
|------|--------|-------|-------|
| `docs/adr/ADR-014-ws-event-bus-for-workbench.md` | this PR | Claude Code | M1 trigger |
| `schemas/ws_events.py` | this PR | Claude Code | Pydantic v2 models matching the table above |
| `tests/test_ws_events_schema.py` | this PR | Claude Code | unit tests: each event kind round-trips JSON; required-field validation; `extra="forbid"` enforcement; `schema_version` constant |
| `backend/app/runtime/event_bus.py` | Phase 2.0 follow-up | Claude Code | `asyncio.Queue` + ring buffer + bounded backpressure |
| `backend/app/runtime/langgraph_callbacks.py` | Phase 2.0 follow-up | Claude Code | translates LangGraph callback signals → WS events |
| `backend/app/api/ws_runs.py` | Phase 2.0 follow-up | Claude Code | the `/ws/runs/{run_id}` endpoint |
| `frontend/` | Phase 2.0 follow-up | Claude Code | React/TS skeleton consuming the bus |

The schema PR (this one) and the runtime PRs land sequentially; no PR depends on R2 of PR #24/#25 because no path here changes governance enforcement. **This PR's self-pass-rate is `50%`** — under the BLOCKING ceiling currently in force, deliberately conservative because the schema is the contract the rest of Phase 2 will follow.

---

## Codex review expectation

This PR triggers M1 (governance text in `docs/adr/` and `schemas/`) and M2 (executable assertions in the test file). It does NOT trigger M3 (no HF1 hot-zone touched), M4 (no enforcement coupling — the schema is read-only contract), or M5 (50% claim is below the 50% threshold in the M5 trigger language; but under the current 30% BLOCKING ceiling the cap-check still fires).

Self-pass-rate: **30%** — match the current BLOCKING ceiling. We are deliberately conservative on the contract PR because every downstream Phase 2 PR will pivot off it; Codex review here saves N future R2 cycles.

---

## Cross-references

- ADR-011 §T2 — M1+M2 trigger compliance basis
- ADR-011 §HF1 — explicit non-touch of HF1.1–HF1.9 (this ADR adds `schemas/ws_events.py` which is a new file alongside HF1.4 `schemas/sim_state.py`, NOT inside HF1.4)
- ADR-012 R2 (PR #24) — the calibration cap whose 30% BLOCKING ceiling this PR honors
- ADR-015 (Draft, parallel) — Workbench → Agent RPC boundary; defines what triggers `node.entered`
- ADR-016 (Draft, parallel) — Result viz stack; `artifact.ready` events feed it
- ADR-017 (Draft, parallel) — RAG facade; `rag.queried` events come from there
- Architecture review by Opus 4.7 (Notion async, 2026-04-26) — Q1, Q2, Q5, Q7 are the inputs to this ADR's specific decisions

---

## Status notes

**Draft → Final criteria:**

1. Codex R1 returns APPROVE or APPROVE_WITH_NITS
2. The Phase 2.0 follow-up PRs (event bus, callbacks, WS endpoint) implement this schema verbatim
3. After 3 consecutive workbench runs in dev, no event-kind addition is needed (revisit `schema_version` if it does)

Until all three are met, this ADR remains `Draft`.
