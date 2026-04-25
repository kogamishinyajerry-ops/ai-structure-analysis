# ADR-017: RAG Facade In-Process + CLI/Library Parity

- **Status:** Draft (parallel to ADR-014, ADR-015, ADR-016)
- **Decider:** Claude Code CLI (Opus 4.7, 1M context) — human-confirmed
- **Date:** 2026-04-26
- **Related Phase:** 2.1 — Engineer Entry & Run Submission (RAG advisor surfaces in 2.1; preflight publish loops in 2.2)
- **Branch:** `feature/AI-FEA-ADR-017-rag-facade-cli-lib-parity`
- **Companion ADRs (Draft, parallel):** ADR-014 (WS event bus), ADR-015 (workbench → agent RPC), ADR-016 (`.frd → .vtu` + result viz)

---

## Context

The RAG track (PR #38–#47) lands a complete corpus + advisor + preflight publish loop:

```
SimPlan → predict_for_simplan → SurrogateHint
                                    ↓
KB → advise(verdict, fault) → ReviewerAdvice    [PR #40]
                                    ↓
combine(hint, advice) → PreflightSummary        [PR #42]
                                    ↓
publish_preflight(...) → PublishResult          [PR #43, #44 upsert]
                                    ↓
GitHub PR comment
```

These modules currently expose **two parallel call paths**:

1. **CLI path:** `python3 -m backend.app.rag.advise_cli`, `…preflight_publish_cli`, etc. (operator-facing, rich `--json` output)
2. **Library path:** `backend.app.rag.reviewer_advisor.advise(...)`, `backend.app.rag.preflight_summary.combine(...)` (Python-import-facing)

The **workbench** (Phase 2.1, ADR-015) is a **third** consumer that needs the same surface. The risk is:

- **Drift between CLI and library** as new flags/output fields are added — the workbench could end up matching neither
- **Three independent integration paths** into the same RAG modules — every RAG change re-validated three times
- **Privacy boundary leaks** if the workbench facade independently re-implements logic that the CLI/library already correctly redact

This ADR pins the contract:

- A single in-process **`backend.app.workbench.rag_facade`** module wraps the RAG library API (NOT the CLI)
- The CLI continues to wrap the same library API — both surfaces are thin shells over the lib layer
- A discipline test asserts CLI and lib hit identical core code paths on identical inputs (parity)

---

## Decision

**Pattern:** the workbench imports `backend.app.rag.{reviewer_advisor, preflight_summary, preflight_publish}` through a single facade module, **`backend/app/workbench/rag_facade.py`**, sibling to `agent_facade.py` (ADR-015).

**The CLI is not a dependency.** The workbench does NOT shell out to `python3 -m backend.app.rag.advise_cli`. Three reasons:

1. **Process spawning cost.** BGE-M3 model load is ~6 s per CLI invocation; the workbench would wear that on every advisor request.
2. **Type erasure.** CLI returns JSON-on-stdout; the facade would re-parse and re-validate something the library already returns as a typed object.
3. **Cancellation semantics.** The workbench needs `asyncio` cancellation; subprocess cancellation requires a SIGTERM dance.

**The CLI must remain a thin shell over the library.** The discipline test (below) enforces this.

**Direction:** workbench → rag library only. RAG library does not know the workbench exists. No RAG function gains a `workbench` keyword argument or callback. Same direction-of-coupling rule as ADR-015.

**Privacy boundary:** the facade is the choke point for redaction. RAG queries can include user-typed natural language; the facade scrubs sensitive sub-strings (per ADR-014 §Privacy) before passing to `reviewer_advisor.advise(...)`. The library trusts its inputs; the facade is responsible for not passing things it shouldn't.

---

## Facade module map

| Module | New / existing | Purpose |
|--------|----------------|---------|
| `backend/app/workbench/rag_facade.py` | **new (this PR)** | the only file in `backend/app/workbench/` that imports `backend.app.rag.*` |
| `backend/app/workbench/__init__.py` | existing (ADR-015) | package marker |
| `backend/app/rag/reviewer_advisor.py` | covered by PR #40 | `advise(verdict, fault) → ReviewerAdvice` |
| `backend/app/rag/preflight_summary.py` | covered by PR #42 | `combine(hint, advice) → PreflightSummary` |
| `backend/app/rag/preflight_publish.py` | covered by PR #43, #44 | `publish_preflight(...) → PublishResult` |

The split between `agent_facade.py` (ADR-015) and `rag_facade.py` (this ADR) is deliberate: agents are stateful (LangGraph state machine) and have HF1 zone protection; RAG is stateless query + advisory. They have different lifetimes, different failure modes, and different test surfaces.

**`rag_facade.py` is the workbench's choke point for `backend.app.rag.*`.** A static check in `tests/test_workbench_facade_discipline.py` (this PR extends the ADR-015 test) enforces the rule.

---

## CLI/library parity

The contract has three rules:

1. **Every CLI subcommand shells through the library API.** The CLI may add presentation logic (formatting, `--json` mode, exit-code mapping) but MUST NOT re-implement the underlying advise/combine/publish logic.
2. **Every CLI flag corresponds to a library function parameter.** New flags require library-side parameters first. The CLI never reads from globals or env vars that the library cannot.
3. **Every library function has at least one CLI test that round-trips its output.** This guarantees that library-side breaking changes are caught by CLI tests, not just import-only tests.

Operationally, this means:

- The **library** is what the workbench facade imports
- The **CLI** is what the operator uses on a terminal
- The **discipline tests** assert the two paths cannot drift

---

## Singleton policy for BGE-M3

The workbench backend loads BGE-M3 **once at startup** as a process-level singleton (`backend.app.rag.kb.get_kb()` cached). All facade calls reuse the same model object.

This decision was made independently in the architecture review (Notion 2026-04-26, Q3 startup-singleton). It avoids:

- Per-request model load (~6 s) — would render the workbench unusable
- Per-request memory churn (~2 GB resident) — would OOM on small VMs

The CLI continues to load BGE-M3 per invocation — that's fine; CLI users absorb the cold-start once per session.

The discipline test asserts that the workbench does NOT take a per-request `KnowledgeBase` parameter into the facade — only the singleton accessor.

---

## Authorization

`POST /workbench/rag/advise` and `POST /workbench/rag/preflight` (Phase 2.1 follow-up) are gated by the same `X-Workbench-Token` header from ADR-015. The facade does not perform its own auth.

---

## Discipline tests

This PR adds a new test file, **`tests/test_rag_facade_parity.py`**, asserting:

1. **Only `rag_facade.py` imports from `backend.app.rag.*` inside `backend/app/workbench/`.** R2 fix (post Codex R1 HIGH): the previous wording allowed both `rag_facade.py` and `agent_facade.py`, but the ADR's stated intent is a single choke point. `agent_facade.py` does NOT import `backend.app.rag.*`; agents that internally call RAG do so via the agent-internal call site, not via the workbench facade.
2. **`rag_facade.py` does not import `backend.app.rag.cli` / `query_cli` / `advise_cli` / `preflight_publish_cli` / `coverage_audit`.** The facade goes through the library, not the CLI shell.
3. **CLI parity surface check.** For each CLI module that exists (skipped if not present yet — RAG track lands in PRs #38–#47), assert the CLI module imports the corresponding library module. Detects when someone adds a new CLI subcommand without backing it with a library function.
4. **No CLI module imports another CLI module's `main`.** CLI modules compose through the library, never through each other's `main()`.
5. **Singleton policy** (§97-108): three assertions on `rag_facade.py` —
   (a) the module invokes `kb.get_kb()` (or `get_kb()` after relative import) at least once;
   (b) no public function (non-underscore-prefixed) takes a parameter annotated as `KnowledgeBase` (catches bare-name, dotted-path, string forward-ref, and `Optional[KnowledgeBase]` forms);
   (c) no `KnowledgeBase(...)` constructor call appears in the module body (catches both bare-name and attribute-form constructions).
   Together these prevent the three known bypass patterns: per-request load via parameter, per-call `KnowledgeBase()` construction, and forgetting the accessor entirely.

R2 fix (post Codex R1 MEDIUM): rules #3/#4 also record relative-import targets (`from . import kb`, `from .kb import X`, `from .. import kb`) so the parity surface cannot be bypassed by switching to relative syntax.

R3 fix (post Codex R3 MEDIUM): rule #5 added — the §97-108 singleton-policy assertion was promised in the R2 ADR text but missing from the test file. R3 adds three integration tests + 13 synthetic-fixture predicate tests.

R4 fix (post Codex R4 MEDIUM/LOW): the R3 predicates were syntax-pinned and let three live bypass classes through. R4 hardens them:
- `_knowledgebase_local_aliases()` resolves `from x import KnowledgeBase as KB` and simple `cls = KnowledgeBase` chains (multi-hop fixpoint, bounded 8 iterations) so renamed/aliased constructor calls (`KB()`, `cls()`, `c()` after `a = KB; b = a; c = b`) are flagged.
- `_calls_get_kb_singleton()` is now provenance-aware: rejects locally-defined `def get_kb` shadows when no `get_kb` is imported from `backend.app.rag.kb` / `.kb` / `backend.app.rag` (closes the Codex repro `def get_kb(): return KB(); def f(): return get_kb()`). Reflective `getattr(kb, "get_kb")()` is documented as a known LOW — pure-AST checks cannot resolve that.
- `_annotation_mentions_knowledgebase()` skips inside `type[X]` / `Type[X]` subscripts — `cls: type[KnowledgeBase]` accepts a class object, not an instance, so it is not a singleton bypass. `Annotated[KB, ...]` and `List[KB]` carry instances and remain flagged.
- Module docstring (line 5) updated: `rag_facade.py` is the SOLE choke point; `agent_facade.py` does NOT import RAG (matches R2 enforcement).

Pure-AST static checks — no import-time execution; <100ms on the whole repo.

---

## Considered alternatives

### Workbench shells out to `advise_cli` / `preflight_publish_cli`
Pros: maximum reuse of operator-facing surface; no second integration point.
Cons: ~6s BGE-M3 cold start per request; type erasure through JSON-on-stdout; cancellation requires SIGTERM. **Rejected.**

### Workbench reimplements its own RAG client (parallel to lib + CLI)
Pros: full control over privacy/redaction.
Cons: triple validation surface; redaction logic drifts; bug fixes need three patches. **Rejected.**

### Library exposes async API; facade is a no-op pass-through
Pros: thinnest possible facade.
Cons: privacy redaction needs a place to live; without a facade, the redaction lives in the library (forces RAG to know about workbench-specific concerns) or in every caller (drifts). The facade is the right home for redaction. **Rejected.**

### Single package `backend.app.rag.workbench_adapter` instead of `workbench.rag_facade`
Pros: keeps RAG-related code in one tree.
Cons: violates ADR-015's direction-of-coupling (RAG library would gain a workbench-aware module). **Rejected.**

---

## Implementation plan

This ADR alone produces no executable RAG code beyond the discipline test. The actual `rag_facade.py` and the wired endpoints land in Phase 2.1 follow-up PRs **after** the RAG track (PR #38–#47) has merged.

| File | Status | Owner | Notes |
|------|--------|-------|-------|
| `docs/adr/ADR-017-rag-facade-cli-lib-parity.md` | this PR | Claude Code | M1 trigger |
| `tests/test_rag_facade_parity.py` | this PR | Claude Code | static parity + discipline checks (M2) |
| `backend/app/workbench/rag_facade.py` | Phase 2.1 follow-up | Claude Code | the only `backend.app.rag.*` import site from workbench |
| `backend/app/api/rag.py` | Phase 2.1 follow-up | Claude Code | `POST /workbench/rag/advise`, `POST /workbench/rag/preflight` |
| (CLI modules, RAG library) | already in flight | Claude Code | PR #38–#47 |

---

## Codex review expectation

This PR triggers M1 (governance text) and M2 (executable assertions in `test_rag_facade_parity.py`). It does **not** touch HF1 zones. It is **not** an enforcement-coupling PR.

Self-pass-rate: **30%** — match the BLOCKING ceiling. The parity tests are the contract every Phase 2.1 RAG-touching PR will be measured against.

---

## Cross-references

- ADR-011 §T2 — M1+M2 trigger compliance basis
- ADR-011 §HF1 — no HF1.x file touched
- ADR-012 R2 (PR #24) — 30% BLOCKING ceiling honored
- ADR-014 (Draft, parallel) — privacy-boundary spec; this ADR's facade is the redaction site
- ADR-015 (Draft, parallel) — sibling facade pattern; same direction-of-coupling rule
- ADR-016 (Draft, parallel) — independent surface (viz), no overlap
- PR #38–#47 — the RAG library + CLI surface this ADR pins
- Architecture review by Opus 4.7 (Notion, 2026-04-26) — Q3 (BGE-M3 startup singleton), Q7-R2 (privacy boundary), CLI/lib parity

---

## Status notes

**Draft → Final criteria:**

1. Codex R1 returns APPROVE or APPROVE_WITH_NITS
2. The parity tests pass on `main` and on every workbench-track PR
3. Phase 2.1 follow-up PR implements `rag_facade.py` without ever calling the CLI

Until all three are met, this ADR remains `Draft`.
