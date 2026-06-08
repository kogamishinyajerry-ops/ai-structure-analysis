# Codex Governance Review — ADR-028 Product Multi-Agent Repositioning (R0 → R2)

- **Subject:** `docs/adr/ADR-028-product-multi-agent-repositioning.md` (Status: Proposed)
- **Reviewer:** Codex relay `gpt-5.5` (86gs xhigh), governance risk-tier
- **Driver:** Claude Opus 4.8 (1M)
- **Date:** 2026-06-04
- **Outcome:** **APPROVE** at R2 (within round-cap 3). This file is acceptance gate #6; ADR-028
  flips Status → Accepted only upon human-owner ratification with all acceptance gates landed in a
  single ratification commit.

## Why reviewed

Per ADR-026 / AGENTS.md, repo-level policy changes need explicit Codex review evidence. ADR-028
amends/**reverses** ADR-027 D3 (FM-05-benchmark-first ordering) and D4 (the 2026-06-03 owner
decision that `agents/solver.py`→AERON is not wired into the live flow), per a 2026-06-04 owner
directive. A reversal of a one-day-old ratified ADR was scrutinized hardest.

## R0 — CHANGES_REQUIRED (5 findings)

- **P1 (D2/D6)** — anti-over-claim gate insufficient: per-stage wording only; 7 product nodes
  project onto 13 UI stages; no first-class provenance ⇒ after P1 the UI could still globally claim
  "multi-agent" with only 1/13 stages real.
- **P1 (D4 vs Non-Goals)** — new HITL resolve endpoint contradicts "public APIs untouched";
  operator-endpoint risk-tier.
- **P2 (D4/ADR-015)** — facade in `__init__.py` + `sim_state_to_stage_state()` in workbench
  violates ADR-015's tested discipline (only `agent_facade.py` imports `agents.*`; no workbench file
  imports `schemas.sim_state`; enforced by `tests/test_workbench_facade_discipline.py`).
- **P2 (D4/P3)** — `SqliteSaver` SoT vs "FastAPI-store durability" risks a second durable authority.
- **P2 (D6/Consequences)** — "verify against G-1 + LE10 CI" reintroduces the ADR-027 CI over-claim
  (the 13-residual floor is a documented invariant, not a live-CI gate; LE10 CI is one non-required
  representative job).
- Completeness: acceptance gates should also include `.planning/STATE.md` + ADR-015/test reconciliation.

Honesty verdict (R0): D3/D4 reversal recorded honestly; no silent extension.

## R1 fixes (Claude, verbatim-faithful) → re-review: 5/6 RESOLVED, 1 PARTIAL

- Added machine-checkable provenance classes (`scripted_demo`/`deterministic_agent`/`llm_agent`) +
  run-level "N/13 agent-driven" coverage qualifier to D2.
- Carved the operator-only HITL endpoint out of Non-Goals.
- Moved the facade to `agent_facade.py` (re-exports only in `__init__.py`), projector out of
  workbench, added ADR-015/test reconciliation gate.
- Made FastAPI persistence a rebuildable read-model (SqliteSaver = single durable authority) +
  recovery tests.
- Reworded G-1 verification to committed residual/registry + non-required `real-le10-e2e`; no
  all-13 live-CI claim before V2-0.
- Added STATE.md + ADR-015 reconciliation acceptance gates.

R1 PARTIAL: D2's first-class provenance needs a wire field, but ADR claimed "schemas untouched" and
`StageState` is strict ⇒ internal contradiction.

## R2 fix → APPROVE

Authorized **exactly one** additive, backward-compatible field `StageState.provenance ∈
{scripted_demo, deterministic_agent, llm_agent}` (default `scripted_demo`), carved out consistently
in the front-matter "Does NOT touch", Non-Goals, acceptance closing line, and D2. All other schema
changes remain out of scope.

**R2 VERDICT: APPROVE** — "D2, front-matter, Non-Goals, and acceptance now consistently authorize
exactly one additive `StageState.provenance` schema field and keep all other schema changes out of
scope."

## Pending (human owner)

Ratify ADR-028; land acceptance gates 1–5 (CLAUDE.md refresh, ADR-027 cross-ref, ROADMAP pointer,
STATE.md truth-up, ADR-015/test reconciliation note) + this evidence in the single ratification
commit; flip Status → Accepted. Then proceed to P1 (facade seam, one stage real).
