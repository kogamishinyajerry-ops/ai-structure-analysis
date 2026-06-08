# ADR-026: Development Team Architecture Realignment — Dual-Engine + Evaluation Fleet

- **Status:** Accepted (ratified by user 2026-05-24 after dogfood Codex review R0; 2 × P2 findings fixed inline — evidence: `reports/codex_tool_reports/adr026_r0_codex_review.md`)
- **Date:** 2026-05-24
- **Decider:** Human owner (ratified 2026-05-24) — drafted by local Claude Opus 4.7 under the
  "深度调整开发团队架构, 参考 cfd-harness-unified 多 agent 施工队" directive
- **Amends:** ADR-011 §role-assignment (AR-2026-05-06-001 Codex-primary → dual-engine).
  Does NOT touch ADR-011 HF1–HF5 path guards, ADR-012 calibration cap,
  ADR-013 branch protection, or ADR-023 Tier system.
- **Related:** ADR-011, ADR-023; `~/CLAUDE.md` model-routing v2.3;
  cfd-harness-unified three-layer governance (DEC-V61-087 / DEC-V61-133)
- **Related Phase:** FM-04a (post Phase 38)

---

## Context

ADR-011 amendment **AR-2026-05-06-001** established Codex as the *primary
implementation agent* and local Claude Opus 4.7 as *reviewer/auditor, not
owner/executor*. This was a deliberate user directive for the Linear/Symphony
PR-based workflow, and it remains Accepted.

However, since **2026-05-07** the FM-04a milestone (and FM-03 before it) has run
under explicit **user direct-execution authorization** (STATE.md `Repo state`:
"FM-04a … under user direct-execution authorization on 2026-05-07"). Under that
authorization Claude Code (Opus 4.7) drives blueprint → slice implementation →
composite scoring single-handedly, local-commit only, no push, no Linear. **38
phases shipped this way.**

The result is a de-facto two-mode reality that was never written down as one
coherent architecture:

| Mode | Status during FM-04a |
|---|---|
| ADR-011 Codex-primary (Linear/Symphony PR) | **Dormant** — 0 Codex relay reviews across the entire milestone |
| FM-04a direct-execution (Opus solo) | **Active but informal** — no independent code review; no first-class team architecture |

Measured against the mature `cfd-harness-unified` three-layer 施工队
(Opus 主驱动 + Codex 双 relay 审查 + Sonnet subagent + Kogami opt-in strategic),
three gaps stand out:

1. **No independent code review.** Codex relay sat idle the entire FM-04a
   milestone. The only review was Opus self-review plus the 3 evaluation
   sub-agents — but those test the **product end-to-end**, not the **diff**.
2. **No formal evaluation fleet.** The 3 sub-agents (`functional_tester` /
   `novice_simulator` / `industrial_ui_comparator`, Phase 33 B) are excellent
   and codebase-grounded, but live as `.planning/test_subagents/*.md` protocols
   re-prompted by hand each phase — not as first-class `.claude/agents/`
   definitions invokable via `subagent_type=`.
3. **Single-engine.** Opus solo; none of the four collaboration paths
   (Codex codegen / dual-blind / Codex review / Opus solo) are available.

The user requests aligning this project's **development-team architecture** to
the proven cfd-harness model. Scope selected by the user: **core dual-layer**
(implementation dual-engine + evaluation fleet) — the strategic Kogami layer is
deferred.

## Decision

Realign to a **dual-engine + evaluation-fleet** architecture. This formalizes
the FM-04a direct-execution mode as the mainline and **amends ADR-011's role
assignment**. ADR-011's path guards, calibration, and branch-protection
machinery are untouched.

### Layer 1 — Implementation (dual-engine)

- **Opus 4.7 主驱动**: blueprint authoring, slice implementation, composite
  synthesis, final audit. *(Amends ADR-011: Opus is no longer "reviewer-only /
  not executor" for direct-execution work.)*
- **Codex relay code review (activated)**: risk-tier triggers =
  schema change · CalculiX adapter · solver-truth path · `golden_samples`
  boundary · cross-≥3-file refactor. **Round cap = 3** (R0 + 2 fix iterations);
  after R3, remaining P1 → user ratify, remaining P2/P3 → retro queue. Invoked
  via `codex-review-relay` (86gs `gpt-5.4` xhigh governance baseline; CRS `high`
  fallback marked in trailer).
- **Four collaboration paths** (per `~/CLAUDE.md`): Opus-led (default) /
  Codex-led codegen / dual-blind parallel / Opus-solo.
- Codex's ADR-011 "primary implementation agent" role is **narrowed** to
  "independent code reviewer + optional delegated codegen" — it is no longer the
  default executor for FM-04a-class direct-execution work. The Linear/Symphony
  Codex-primary path remains available for bounded-issue PR work when the user
  routes work that way.

### Layer 2 — Evaluation Fleet (formalized)

- The 3 evaluation sub-agents are promoted from `.planning/test_subagents/*.md`
  protocols to first-class `.claude/agents/` definitions:
  `functional-tester`, `novice-simulator`, `industrial-ui-comparator` —
  invokable via `subagent_type=`.
- **Anti-gaming guards B/D/F/G:-1 preserved verbatim**: sub-agents score (not
  the main session) · every score cites file:line · sub-agents are never given
  prior audit files · sub-agents test what the codebase IS, not what it CLAIMS.
- `.planning/test_subagents/*.md` remains the canonical protocol SSOT; the
  `.claude/agents/` definitions are thin frontmatter wrappers that point back to
  it (single source of truth, no protocol duplication drift).
- Optional future: an FEA physics-correctness evaluator (deferred).

### Layer 3 — Strategic (deferred, opt-in)

A Kogami-FEA equivalent (`claude -p` zero-tool independent reviewer for
decision-arc coherence / roadmap fit / **Tier-claim honesty**, e.g. catching a
Tier 1 result summarized as Tier 2) is **deferred** per the user's core
dual-layer scope. The architecture leaves a clean seat for it; it is not built
in this ADR.

### Governance alignment (carried, unchanged)

- `confidence: <h/m/l>` commit tag (already in use across FM-04a) — retained.
- Codex review round cap = 3 — adopted from cfd-harness v2.3 (DEC-V61-133).
- Tier 0/1/2 claim boundary (ADR-023) — unchanged; this project's strength.
- Calibration cap (ADR-012), branch protection (ADR-013), `golden_samples`
  HF1.7a/b carve-out (ADR-011 AR-2026-05-16) — unchanged.
- Linear work-control + PR-only-to-`main` — unchanged for Linear-routed work;
  FM-04a-class direct-execution stays local-commit / no-push under the standing
  user authorization.

## Landed artifacts

This ADR is accompanied by:

- Project `CLAUDE.md` (three-layer config, inherits `~/CLAUDE.md`) — the
  development-team-architecture SSOT.
- `AGENTS.md` rewrite (role realignment) — the Codex-facing operating rules.
- `.claude/agents/{functional-tester,novice-simulator,industrial-ui-comparator}.md`.

## Dogfood ratification

Per **AGENTS.md §"A green CI run is not sufficient … Repo-level policy changes
need explicit review evidence"**, this realignment is itself reviewed via the
newly-activated **Codex relay** — the first dual-engine instance — before user
ratification. Flow: write package → `codex-review-relay` APPROVE → user ratify
→ Status flips to Accepted → local commit. This validates the new architecture
by using it to ratify itself.

## Consequences

**Positive:**
- Independent code review re-activated after a 38-phase dormancy.
- Evaluation fleet becomes first-class and reusable (`subagent_type=`).
- The honest-but-informal two-mode reality is replaced with one coherent,
  documented mainline.
- Aligns with the proven cfd-harness-unified model without importing its
  overhead (Kogami deferred; no governance-script fleet required at this scope).

**Tradeoffs:**
- Codex relay review adds latency on risk-tier changes (bounded by round cap=3).
- Two config files must stay in sync: **`CLAUDE.md` = team-architecture SSOT**,
  **`AGENTS.md` = Codex-facing operating rules**. ADR-026 is the reconciliation
  anchor if they drift.

## Non-Goals

This ADR does **not**:

- build the strategic Kogami layer (deferred to a future ADR);
- change the Tier system, calibration cap, branch protection, `golden_samples`
  guards, solver truth, schemas, public APIs, CI, or dependencies;
- push FM-04a to remote or open PRs (standing no-push authorization unchanged);
- retroactively re-review or re-score the 38 shipped FM-04a phases;
- remove the Linear/Symphony Codex-primary path — it remains available for
  bounded-issue PR work the user explicitly routes through Linear.
