# ADR-028: Product Multi-Agent Repositioning — Wire the Real Workbench Agents Behind the Live Runtime

- **Status:** **Accepted** (ratified 2026-06-04 by the human owner after the Codex relay governance
  review closed APPROVE — R0 CHANGES_REQUIRED 5 findings → R1 5/6 + 1 partial → R2 **APPROVE**,
  within round-cap 3; evidence `reports/codex_tool_reports/adr028_r0_r2_product_multiagent_governance_review.md`.
  Drafted 2026-06-04 by Claude Opus 4.8 (1M) under the owner directive "深度优化项目，把它定位成一个
  多agent分工协作的智能体系统" + the 2026-06-04 decision "agentic 重定位为头条，amend ADR-027". All six
  acceptance gates landed in the single ratification commit.)
- **Date:** 2026-06-04
- **Decider:** Human owner (directive 2026-06-04: agentic repositioning = the active milestone
  headline; amend ADR-027). Drafted by Claude Opus 4.8.
- **Amends / partially REVERSES (stated plainly, not a silent extension):**
  - **ADR-027 D3** (v2 ordered as FM-05 "NAFEMS-benchmark-first") → this ADR makes **agentic
    wiring the headline**; FM-05 NAFEMS-benchmark agreement is **deferred, NOT cancelled**.
  - **ADR-027 D4** (the 2026-06-03 owner decision that the `agents/solver.py`→AERON path is "left
    **as-is** … **NOT wired** into the live workbench solve flow, NOT a v2 item; AERON is **not
    pursued**") → this ADR **reverses that**: wiring the real product agents into the live runtime
    *is* the work, and a thin `get_backend()` dispatch over the existing, tested AERON `FEABackend`
    Protocol is part of it.
- **Implements at last:** ADR-015 (workbench-agent RPC boundary — the facade seam, currently a
  docstring-only stub).
- **Does NOT touch (remain in force and CONSTRAIN this work):** ADR-011 HF path guards · ADR-012
  calibration cap · ADR-013 branch protection · ADR-023 Tier 0/1/2 claim system (this ADR is
  **bound by it**) · ADR-026 dual-engine **dev-team** architecture (the DEV agents — explicitly
  **distinct** from the PRODUCT agents this ADR governs) · ADR-027 **G-1 / G-2 guardrails** ·
  solver truth · schemas (save the single additive `StageState.provenance` field per D2) ·
  `golden_samples/**` · the 6-dim rubric definition · CI · no-retroactive-rescore.
- **Related:** ADR-023 (the claim discipline this binds to), ADR-026 (dev-vs-product agent
  distinction), ADR-027 (the milestone reset this amends/reverses), `~/CLAUDE.md` honesty contract.
- **Related Phase:** post-FM-04a v1.0; supersedes the FM-05-first ordering of ADR-027 D3.

---

## Context

A 2026-06-04 read-only architecture map (6-dimension parallel verification workflow, run under the
G:-1 "test what the codebase IS, not what it CLAIMS" doctrine, measuring HEAD `3e47825`) established
the following **verified** ground truth. It exposes a positioning/honesty problem, not a
missing-feature one.

### The honesty-critical finding

The product ships **two disjoint pipelines and surfaces the WRONG one as "multi-agent":**

1. **The live surface the user watches** — `frontend/src/components/WorkflowMonitorTabPanel.tsx`
   ← Trigger.dev `trigger/src/feaPipeline.ts` ← `backend/app/services/workflow/mock_pipeline.py`
   — is a **linear 13-stage state machine whose `agent_explanation`/`next_action` are 27 hardcoded
   Chinese strings** (`mock_pipeline.py:76-270`), with **zero LLM/agent calls** and **one** real
   ccx solve (the pinned NAFEMS LE10 deck via `real_le10.py`).
2. **The genuine division-of-labor** — `agents/graph.py`: a 7-node LangGraph (architect /
   geometry / mesh / solver / reviewer / viz + human_fallback), with fault-class routing
   (`agents/router.py`), per-node retry budgets, an LLM architect with deterministic fallback, and
   a real interrupt-based human_fallback — is **orphaned**: `compile_graph`/`build_graph` have
   **zero non-test callers**, `backend/` has **zero `from agents` imports**, and the ADR-015 bridge
   `backend/app/workbench/__init__.py` is a **docstring-only stub** (verified 2026-06-04).

Per the ADR-023 / ADR-027 / `~/CLAUDE.md` honesty contract, surfacing pre-written prose as agent
intelligence is an **active Tier-0-masquerading-as-agent over-claim** — the single highest-priority
honesty defect in the product today, and the core reason "reposition as multi-agent" is a
*correctness* task, not merely a feature.

### Why this is tractable (WIRING, not greenfield)

~70–80% of the substrate already exists **and is tested** but is **unwired**: the aeron
`FEABackend` Protocol (both the CalculiX and OpenRadioss drivers implement it), the shared
`FaultClass` taxonomy (reused by the graph **and** `StageState`), the `StageState` wire contract
(`schemas/workflow_state.py`), the `SqliteSaver` checkpointer (`tests/test_checkpointer.py`), and
the RAG `reviewer_advisor` (built + tested; its own docstring admits it is **not** wired into any
run loop). The repositioning is therefore a **WIRING + PROJECTION** problem, not a rebuild.

### Collision with ADR-027 (recorded honestly)

ADR-027 (Accepted 2026-06-03, owner-ratified **one day** before this ADR) made two decisions this
ADR reverses, per the owner's 2026-06-04 directive — see *Amends/Reverses* above. This is a
legitimate owner change of direction, recorded as a **reversal**, not a silent extension.
Everything ADR-027 did **not** touch (the Tier system, G-1/G-2 guardrails, calibration cap, branch
protection, `golden_samples` guards, schemas, solver truth, CI, no-retroactive-rescore) **remains
binding** on this work.

---

## Decision

Reposition the **PRODUCT** as a genuine multi-agent division-of-labor intelligent system by
**wiring the existing, tested agent graph behind the existing live runtime** — reusing LangGraph +
Trigger.dev, not rebuilding — bound to ADR-023 claim discipline.

### D1 — Target claim tier: honest **Tier-1 agentic engineering-candidate**

The repositioned product targets **Tier-1**: a real, LLM-capable division of labor whose runtime
output is produced by **actual agent nodes**. It is **NOT** a signed-Tier-2 claim (agentic wiring
adds **no** validation/benchmark claim), and explicitly **NOT** a marketing "intelligent system"
claim that the honesty contract forbids absent validation. The 13 `tier_2_validated` per-case
analytical cross-checks of ADR-027 keep their **exact, narrow** meaning; agentic wiring does not
touch, re-tier, or re-score them.

### D2 — Anti-over-claim interim-wording gate (eliminates the current Tier-0 masquerade incrementally)

Until a given stage is driven by a real agent node at runtime, the UI **MUST** mark that stage's
output as **synthetic / scripted demo data**. An **"agent-driven"** label is permitted **only** for
a stage whose `agent_explanation`/`next_action` is produced by a live agent node at runtime. **No
stage may present hardcoded prose as agent output.** This converts the current over-claim into an
honest, incrementally-shrinking disclosure as stages are wired (P1→P3). Shipping multi-agent UI
framing over still-mock stages **without** this subtitle would itself be an ADR-023 violation — the
exact failure this ADR exists to fix.

**Machine-checkable provenance + run-level coverage (per Codex R0 P1 — per-stage wording alone is
insufficient; the 7 product nodes project onto 13 UI stages, so after P1 only 1/13 is real).** Every
rendered stage MUST carry a machine-checkable provenance class — `scripted_demo`,
`deterministic_agent`, or `llm_agent` — emitted as first-class data by the runtime (NOT inferred by
the UI). Until **all** visible stages are agent-backed, the run-level UI MUST display a coverage
qualifier — e.g. *"progressive agentic wiring: N/13 stages agent-driven"* — and **no global
"multi-agent system" headline is permitted without that qualifier**. The provenance class is the
honest unit of the D2 gate; the subtitle wording above is its per-stage expression.

To carry it on the wire (and resolve the otherwise-contradiction with "schemas untouched" — Codex
R1), D2 sanctions **exactly one additive, backward-compatible schema field**:
`StageState.provenance ∈ {scripted_demo, deterministic_agent, llm_agent}`
(`schemas/workflow_state.py`), defaulting to `scripted_demo` so pre-existing/un-wired stages remain
honest by default. This is the **sole** schema change this ADR authorizes; it is purely additive
(no field renamed/removed/retyped), Codex-reviewed at implementation, and carved out explicitly in
the Non-Goals + acceptance below.

### D3 — Product agents are namespaced + distinct from the ADR-026 dev agents

The PRODUCT agent roster (the `agents/` graph: architect / geometry / mesh / solver / reviewer /
viz / human_fallback) is the **"workbench-agents"** and is **distinct** from the ADR-026
dev-process eval fleet (functional-tester / novice-simulator / industrial-ui-comparator). This ADR
governs **only** product agents. (Prevents the #1 conflation risk flagged by the architecture map.)

### D4 — Architecture: reuse the seams, add the missing connective tissue

- **Facade seam (builds ADR-015's specified-but-never-built choke point; per Codex R0 P2):** the
  implementation lives in the new `backend/app/workbench/agent_facade.py` — the ADR-015-sanctioned
  **only** file that may import `agents.*` — exposing `run_node(stage, ...) -> StageState`;
  `backend/app/workbench/__init__.py` only **re-exports** safe symbols (no `agents.*` /
  `schemas.sim_state` imports). `mock_pipeline.run_one_stage` **delegates** per-stage execution to
  the facade. This honors `tests/test_workbench_facade_discipline.py`.
- **State projection (ADR-015 rule 3 compliant — NO workbench file imports `schemas.sim_state`):**
  the `sim_state_to_stage_state()` projector lives in the **agent layer / schemas**, NOT in
  `workbench/`; `agent_facade.run_node()` returns an **already-projected** `StageState` so the
  workbench never touches `SimState`. Node transitions thus emit **real**
  `agentExplanation`/`nextAction` instead of the 27 hardcoded strings; `StageState` is the **wire
  projection** of `SimState`. If this is found to amend ADR-015's tested discipline, ADR-015 + the
  facade static tests are updated in the same change (acceptance gate 5 below).
- **Solver dispatch (the specific reversal of ADR-027 D4):** add an aeron
  `get_backend(plan.solver.name)` factory and remove `agents/solver.py`'s non-CalculiX hard-reject,
  so **one** graph runs either physics over the already-tested `FEABackend` Protocol.
- **Orchestration unchanged:** keep Trigger.dev's durable wait-token seam (SSRF-guarded,
  idempotent) and the FastAPI stage runner. Per-stage execution now flows through real agent nodes;
  the plumbing is **reused, not replaced**.
- **Run-state single source of truth (tightened per Codex R0 P2):** the LangGraph `SqliteSaver`
  checkpoint is the **single durable authority**. Any FastAPI-side persistence (P3) is a
  **reconstructable read model only** — it holds NO transition authority, retry budgets, HITL
  decisions, or artifact ownership outside the checkpoint, and MUST be rebuildable from it (proven
  by recovery tests). `StageState` is a **projection** (prevents a 4th state-vocabulary drift and a
  second durable authority).
- **HITL:** surface the existing `human_fallback` interrupt as a **blocking "Agent-needs-you"
  Accept/Retry/Escalate panel** with a new resolve endpoint — the defining differentiator of an
  intelligent agent system, today invisible backend code.

### D5 — Posture defaults (owner, 2026-06-04)

- **LLM posture:** deterministic-fallback is the **shippable/CI default**; real-LLM reasoning is
  **explicit opt-in** (key-gated). The agentic claim is honest in both modes (deterministic =
  rule-based agents; LLM = reasoning agents); CI stays hermetic and reproducible.
- **Scope v1:** **CalculiX-first.** The ballistic GS-102 (OpenRadioss) codepath folds in **last**
  (deferred to P5), via the same `get_backend()` factory.

### D6 — Phased delivery (each phase = one shippable, Codex-reviewed increment)

- **P0** — this ADR + canon truth-up (CLAUDE.md stale dashboard, ADR-027 cross-ref, ROADMAP pointer).
- **P1** — the facade seam: route **ONE** stage (architect/project-intake) through `run_node`; its
  `agentExplanation` becomes real; deterministic default. Proves the seam end-to-end.
- **P2** — aeron `get_backend()` factory + remove solver hard-reject + default a `SqliteSaver` in
  `compile_graph` (HITL-resumable).
- **P3** — route the remaining stages through the facade + a FastAPI-side **read-model** rebuildable
  from the checkpoint (D4) + forward-flowing artifact bus + wire `reviewer_advisor` into the reviewer
  node. Verify G-1 via the **committed `cross_check_verdict.yaml` residual + registry-consistency
  checks** plus the existing **non-required `real-le10-e2e`** representative live-solve job — do NOT
  claim all 13 residuals are live-CI-enforced until ADR-027 V2-0 lands (per Codex R0 P2).
- **P4** — UI: named agent lanes (now backed by real output) + the HITL Accept/Retry/Escalate panel.
- **P5 (deferrable)** — WSEvent emitter as the single telemetry spine; fold the ballistic GS-102
  codepath into the same node roster.

Risk-tier changes (schema / solver-truth / operator-endpoint / `golden_samples`) require a Codex
review **before** local commit (round cap 3), per ADR-026 / CLAUDE.md.

---

## Consequences

**Positive:**
- Eliminates the product's **highest-priority honesty defect** (scripted prose masquerading as
  agent intelligence).
- Converts dead-but-tested substrate into a **live, defensible Tier-1 agentic product**.
- **Reuses** existing infra (LangGraph + Trigger.dev + aeron Protocol + StageState + SqliteSaver) —
  no new framework, no greenfield orchestration layer.
- Makes **HITL the differentiator** — turns invisible interrupt code into the product's headline
  collaborative-intelligence feature.

**Tradeoffs / risks (+ mitigations):**
- **Reverses a one-day-old owner-ratified decision (ADR-027 D4)** — recorded honestly; ADR-027's
  guardrails and untouched scope remain binding.
- **LLM cost / latency / nondeterminism** — mitigated by the deterministic-fallback default
  (LLM opt-in); CI/demo stay hermetic.
- **Wiring touches solver-adjacent + regression-floor code** — mitigated by Codex risk-tier review
  + **G-1 verification** (the committed 13 `cross_check_verdict.yaml` residual/registry checks must
  not regress, plus the non-required `real-le10-e2e` representative job — NOT a claim that all 13 are
  live-CI-enforced; that awaits ADR-027 V2-0).
- **Premature multi-agent UI framing before wiring** — mitigated by the **D2 interim-wording gate**.
- **Two durable stores drift** (graph SqliteSaver vs FastAPI store) — resolved by D4 (graph
  checkpoint = SoT, StageState = projection).
- **Scope creep / framework bloat** (P5 WSEvent + ballistic) — sequenced **last**, deferrable.

---

## Non-Goals

This ADR does **NOT**: change the Tier 0/1/2 system, the G-1/G-2 guardrails, the calibration cap,
branch protection, `golden_samples` guards, solver truth, CI, or the 6-dim rubric definition; change
**schemas** — **except** the single additive, back-compat `StageState.provenance` field D2 requires
(Codex-reviewed); change **existing** public APIs — **except** P4's new **operator-only HITL resolve
endpoint**, which is explicitly risk-tier, auth-gated, Codex-reviewed, and route-tested (per Codex
R0 P1); re-tier or re-score any case (the 13 `tier_2_validated` cross-checks keep their exact
meaning); **cancel** FM-05 (it is **deferred**); touch the ADR-026 **dev** agents; or require an LLM
key for the shippable default.

---

## Ratification

Per ADR-026 / AGENTS.md ("repo-level policy changes need explicit review evidence"), this ADR is
reviewed via the Codex relay (governance risk-tier) before user ratification. Flow: draft (this
file, **Proposed**) → `codex-relay-with gpt-5.5` governance review → APPROVE → user ratify →
Status → **Accepted**.

**Required acceptance gates (land in the single ratification commit before Status → Accepted):**

1. `CLAUDE.md` — refresh the stale dashboard read (`81.33 @ Phase 43`) and add ADR-028 as the
   active **product** direction (governance-locked file; edit **only** after Codex + ratification).
2. `docs/adr/ADR-027-milestone-goal-reset.md` — add a cross-reference note to D3/D4 that **ADR-028
   (2026-06-04) amends/reverses them** per an owner direction change, so the canon is internally
   consistent (no silent contradiction between two Accepted ADRs).
3. `.planning/ROADMAP.md` — already SUPERSEDED by ADR-027; add an ADR-028 pointer for the agentic
   product direction.
4. `.planning/STATE.md` — truth-up so the live state reflects the ADR-028 product direction and is
   consistent with the corrected canon (per Codex R0 completeness note).
5. **ADR-015 + facade-test reconciliation** — if the D4 `agent_facade.py` seam amends ADR-015's
   tested discipline (`tests/test_workbench_facade_discipline.py`), update ADR-015 and the static
   facade tests in lockstep so no Accepted ADR is silently contradicted (per Codex R0 P2).
6. Codex governance review **APPROVE** evidence archived under `reports/codex_tool_reports/`.

The Tier system, G-1/G-2 guardrails, calibration cap, branch protection, `golden_samples` guards,
solver truth, and CI are **untouched** by this acceptance; **schemas** are untouched save the single
additive `StageState.provenance` field per D2 (Codex-reviewed at implementation).
