# ADR-015: Workbench → Agent RPC Boundary

- **Status:** Draft (parallel to ADR-014, ahead of Phase 2.1)
- **Decider:** Claude Code CLI (Opus 4.7, 1M context) — human-confirmed
- **Date:** 2026-04-26
- **Related Phase:** 2.1 — Engineer Entry & Run Submission
- **Branch:** `feature/AI-FEA-ADR-015-workbench-agent-rpc`
- **Companion ADRs (Draft, parallel):** ADR-014 (WS event bus contract), ADR-016 (`.frd → .vtu` + result viz), ADR-017 (RAG facade in-process + CLI/lib parity)

---

## Context

Phase 2.1 brings the engineer's first interaction surface online: a browser dialog where they describe a problem in natural language, see the architect agent translate it into a `SimPlan`, confirm or correct that plan, and submit a run. The frontend then watches the resulting LangGraph execution through ADR-014's WebSocket event bus.

This ADR closes the **call-direction** question that ADR-014 deliberately punts: *how does the workbench backend invoke the agent layer without modifying it?*

The constraint is severe. Six agent files (`agents/router.py`, `agents/architect.py`, `agents/geometry.py`, `agents/mesh.py`, `agents/solver.py`, `agents/reviewer.py`, plus `agents/calculix_driver.py`) collectively encode the LangGraph state machine. Three of them (`router`, `geometry`, `solver`, `calculix_driver`) are HF1-protected. None can be modified by a Phase 2 PR without an HF1 zone-carve ADR — which we are deliberately avoiding for the workbench track.

Additionally, ADR-006's autonomous-merge regime relies on the agent layer being a stable target. Adding "the workbench dialed in here" coupling on the agent side would force every workbench iteration to re-validate ADR-006 invariants. That coupling must point the other direction: the agent layer is the stable surface; the workbench is the consumer.

---

## Decision

**Pattern:** in-process **facade** module(s) under `backend/app/workbench/`. The workbench facade IS the only call site that touches the agent layer; the React frontend never imports agents.

**Direction:** workbench → agents only. Agents do not know the workbench exists. No agent function gains a `workbench` keyword argument, a callback, a global, or a class-level mixin.

**Read-only contract:** facade calls into agents are *read-only* with respect to agent state. The agents continue to emit their effects (artifacts on disk, LangGraph state transitions, log lines); the workbench observes those effects through ADR-014's event bus, NOT through return values that the facade then mutates.

**No HTTP-internal RPC:** we do **not** wrap agents in a separate FastAPI service the workbench calls over the network. The cost would be: serialization, an extra port, and an authentication boundary, all to talk to code in the same process. Phase 3 may revisit if multi-process becomes useful (e.g. running agents in a sandbox), but Phase 2 is single-process.

**No LangGraph "as a service":** we do **not** put LangGraph behind a gRPC service either. The workbench backend constructs the same LangGraph compiled state machine that the existing CLI does, and invokes it directly.

---

## Facade module map

| Module | New / existing | Purpose |
|--------|----------------|---------|
| `backend/app/workbench/__init__.py` | **new** | package marker |
| `backend/app/workbench/agent_facade.py` | **new** | the only file that imports `agents.*` from workbench code |
| `backend/app/workbench/run_orchestrator.py` | **new** | builds and invokes the LangGraph compiled graph; wires the ADR-014 callback |
| `backend/app/workbench/task_spec_builder.py` | **new** | calls `agents.architect` to translate NL → SimPlan; returns the SimPlan + a "confirmation token" the user signs off on |
| `backend/app/workbench/rag_facade.py` | covered by ADR-017 | imports `app.rag.*` for `advise()` / `combine()`; sibling to `agent_facade` |
| `backend/app/runtime/event_bus.py` | covered by ADR-014 | `asyncio.Queue` + ring buffer |
| `backend/app/runtime/langgraph_callbacks.py` | covered by ADR-014 | translates LangGraph signals → WS events |

The split between `workbench/` (semantic operations) and `runtime/` (event-bus plumbing) is deliberate: ADR-014 owns the wire format; ADR-015 owns the in-process call sites.

**`agent_facade.py` is the choke point.** Every import of `agents.*` from outside the agent layer goes through this file. A pre-merge static check (defined below) enforces the rule.

---

## Authentication & authorization for `POST /runs`

The Phase 2.1 first-run scope is **single-trusted-operator-per-server** (per ADR-014). That means:

- The browser is assumed to be on the same network as the backend (LAN / VPN) and has been pre-authenticated at the session boundary
- `POST /runs` requires an `X-Workbench-Token` header that matches `os.environ["WORKBENCH_TOKEN"]` (a per-deployment secret)
- The same token gates `GET /runs/{id}/nodes/{name}/io` (the digest-fetch endpoint from ADR-014)
- WS handshake is gated by a query-string `?token=...` (browsers cannot set arbitrary headers on WS upgrade); the WS endpoint validates the token against `os.environ["WORKBENCH_TOKEN"]` before accepting the connection

This is intentionally simple. A future ADR will introduce per-user identity once the workbench has more than one operator. **No OAuth / JWT in Phase 2.1.**

---

## Confirmation protocol (NL → SimPlan → user-signed run)

The Phase 2.1 user flow (R2 — post Codex R1 fix for the edit-flow gap):

1. Browser sends `POST /runs/draft { "nl_request": "..." }` with the workbench token
2. Backend calls `task_spec_builder.draft_from_nl(nl_request)`:
   - architect runs ONCE → SimPlan
   - server stores `(draft_id → original_plan)` in an in-process draft registry (Phase 2.1 single-operator scope; Phase 3 may swap for Redis or a persistent store)
   - returns `(sim_plan, draft_id, draft_token)` where `draft_token = HMAC(draft_id || canonical-JSON(original_plan))`
3. Browser displays the rendered SimPlan; user can edit or accept
4. **If the user edits**, browser calls `POST /runs/precommit { "draft_id", "edited_plan", "draft_token" }` with the workbench token:
   - server validates `draft_token` against the STORED original plan
   - server applies `edited_plan` (constrained: same `case_id` as the draft — case identity is fixed at draft time)
   - server returns `(rebuilt_plan, submit_token)` where `submit_token = HMAC(draft_id || canonical-JSON(rebuilt_plan))`
   If no edits, the browser uses the original `draft_token` as the submit_token directly (rebuilt_plan == original_plan).
5. Browser sends `POST /runs/submit { "draft_id", "submit_token" }` with the workbench token:
   - server looks up the rebuilt plan it computed in step 4 (or the original_plan if no edits)
   - validates `submit_token` against that plan via HMAC
   - on success, `discard_draft(draft_id)` and invokes `run_orchestrator.invoke(sim_plan)`

**Why two tokens?** The original (R1) design minted a single token over the pre-edit plan and rechecked against the post-edit plan. Codex R1 caught the contradiction: any legitimate edit invalidated the token, so the protocol could not actually accept edits. The R2 fix splits the flow — the SERVER re-mints the token over the rebuilt plan during the precommit step. The client never holds the workbench secret, so a client-side re-mint is impossible. Each token witnesses the plan version it was issued for.

The HMAC-SHA256 is keyed by `WORKBENCH_TOKEN` and computed over `draft_id || NUL || canonical-JSON(plan)`. It guarantees:

- the SimPlan the user committed to (in step 4 if edited, or step 2 if accepted as-is) is identical to the SimPlan that runs in step 5 (no silent drift)
- a draft cannot be submitted by a third party who didn't see the rendered SimPlan and complete the precommit step
- replay of the same `submit_token` against a different `draft_id` fails

**No LLM regeneration between draft and submit.** Architect agent runs ONCE per request — at draft time. Edits are deterministic server-mediated transformations of the original plan; the LLM is not re-invoked.

---

## Considered alternatives

### Direct frontend → agent imports
Pros: zero glue layer.
Cons: every JS bundle change forces a Python rebuild; cross-language type drift; the architect agent's prompt-engineering details would leak to the browser. **Rejected.**

### HTTP-internal RPC (`POST /internal/agent/architect/draft`)
Pros: language-agnostic; future multi-process viability.
Cons: serialization round-trip per call; auth boundary inside the same process; no Phase 2 use case justifies the cost. **Rejected.**

### LangGraph behind gRPC streaming
Pros: typed, future-multi-host.
Cons: complexity dwarfs the win; ADR-014 already streams events via WS. **Rejected.**

### Subprocess invocation (fork/exec the existing CLI)
Pros: maximum process isolation.
Cons: cold-start cost (BGE-M3, LangGraph compile) per call; stdout parsing instead of typed return; cancellation requires SIGTERM dance. **Rejected.**

---

## Static check — facade discipline

A new test, `tests/test_workbench_facade_discipline.py`, walks every `.py` file under `backend/app/workbench/` (when those files land in Phase 2.1) and asserts:

1. **Only `agent_facade.py` imports from `agents.*`.** Any other workbench file importing `agents.*` is a violation.
2. **`agent_facade.py` does not modify agent module-level state.** It calls functions and reads return values; it never assigns to `agents.X.Y`.
3. **No workbench file imports from `schemas.sim_state`** (HF1.4) directly. They use `schemas.sim_plan` (which is also HF1-adjacent but not in the hard floor — see ADR-011 §HF1).

The check is pure-AST (no import-time execution); fast (<100ms on the whole repo); and bound to ADR-015 by docstring reference.

---

## Implementation plan

This ADR alone produces no executable code beyond the discipline test stub. The workbench code lands in subsequent PRs (Phase 2.1).

| File | Status | Owner | Notes |
|------|--------|-------|-------|
| `docs/adr/ADR-015-workbench-agent-rpc-boundary.md` | this PR | Claude Code | M1 trigger |
| `tests/test_workbench_facade_discipline.py` | this PR | Claude Code | static check, runs even before workbench/ exists (skips if dir missing) |
| `backend/app/workbench/__init__.py` | this PR | Claude Code | package marker, single-line docstring referencing ADR-015 |
| `backend/app/workbench/agent_facade.py` | Phase 2.1 follow-up | Claude Code | the only `agents.*` import site |
| `backend/app/workbench/task_spec_builder.py` | Phase 2.1 follow-up | Claude Code | NL → SimPlan + confirmation_token |
| `backend/app/workbench/run_orchestrator.py` | Phase 2.1 follow-up | Claude Code | LangGraph invocation + ADR-014 wiring |
| `backend/app/api/runs.py` | Phase 2.1 follow-up | Claude Code | `POST /runs/draft`, `POST /runs/submit`, `GET /runs/{id}/nodes/{name}/io` |

---

## Codex review expectation

This PR triggers M1 (governance text in `docs/adr/`) and M2 (executable assertion in `test_workbench_facade_discipline.py`). It does **not** touch HF1 zones (only adds new files outside HF1.x). It is **not** an enforcement-coupling PR (the workbench observes effects through ADR-014's bus, not through agent return values that mutate enforcement state).

Self-pass-rate: **30%** — match the current BLOCKING ceiling. The discipline-check test is the contract every Phase 2.1 PR will be measured against; conservative review here saves N future R2 cycles on workbench code PRs.

---

## Cross-references

- ADR-011 §T2 — M1+M2 trigger compliance basis
- ADR-011 §HF1 — explicit non-touch of HF1.1–HF1.9; the discipline test is the durable enforcement
- ADR-012 R2 (PR #24) — the calibration cap whose 30% BLOCKING ceiling this PR honors
- ADR-014 (Draft, parallel) — WS event bus; this ADR's `run_orchestrator` consumes its event types
- ADR-006 — autonomous-merge regime; this ADR strengthens the "agents are a stable target" pre-condition
- Architecture review by Opus 4.7 (Notion, 2026-04-26) — Q1 (in-process facade), Q5 (Phase 2.1 scope), Q7-R2 (privacy boundary), Q7-R7 (HF1 boundary)

---

## Status notes

**Draft → Final criteria:**

1. Codex R1 returns APPROVE or APPROVE_WITH_NITS
2. The discipline test passes on `main` and on every workbench-track PR
3. Phase 2.1 follow-up PRs implement `agent_facade` / `task_spec_builder` / `run_orchestrator` without ever importing `agents.*` from outside the facade

Until all three are met, this ADR remains `Draft`.
