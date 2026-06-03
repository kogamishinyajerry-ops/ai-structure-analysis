# AI-Structure-FEA · Project CLAUDE.md

> Project-specific Claude Code configuration. Inherits from `~/CLAUDE.md` (user-level).
> See user-level for: 模型分工 v2.3 (Opus 4.7 主驱动 + Codex 双 relay · round cap=3),
> Codex 调用规则, Subagent 优先原则, 压缩阈值.
>
> **Established by ADR-026** (2026-05-24, **Status: Accepted** — ratified by user after
> dogfood Codex review R0). This architecture is **in force**, amending ADR-011's
> Codex-primary role assignment. This file is the **development-team-architecture SSOT**;
> `AGENTS.md` mirrors the Codex-facing operating rules; ADR-026 is the reconciliation anchor.

---

## Development team architecture (three-layer · ADR-026)

| Layer | Who | Trigger | Output |
|---|---|---|---|
| **Implementation** (dual-engine) | Opus 4.7 主驱动 + Codex relay 审查 | Opus: all direct-execution work · Codex: risk-tier code review | code + `reports/codex_tool_reports/` |
| **Evaluation** (fleet) | 3 `.claude/agents/` sub-agents | every phase audit cycle · regression checkpoint | `.planning/audits/phase<N>_*.md` |
| **Strategic** (deferred, opt-in) | Kogami-FEA equivalent — *seat reserved, not built* | — | — |

### Layer 1 — Implementation (dual-engine)

- **Opus 4.7 主驱动**: blueprint authoring → slice implementation → composite
  synthesis → final audit. The default driver for FM-04a-class direct-execution
  work (local-commit, no-push, under standing user authorization).
- **Codex relay code review** — **activated** (was dormant the entire FM-04a
  milestone). Risk-tier triggers requiring a Codex review **before local commit**:
  - schema change (`schemas/`, Pydantic models)
  - CalculiX adapter / `inp_writer` / solver-truth path
  - `golden_samples/**` boundary (incl. `*-candidate` writes)
  - cross-≥3-file refactor
  - any change Opus self-flags `confidence: low`
- **Round cap = 3** (R0 + 2 fix iterations). After R3: remaining P1 → user
  ratify; remaining P2/P3 → retro queue (`.planning/retrospectives/`).
- **Four collaboration paths** (per `~/CLAUDE.md`): Opus-led (default) /
  Codex-led codegen / dual-blind parallel / Opus-solo.

**Codex invocation (Claude Code's responsibility — do not push to user):**

```bash
# Governance/risk-tier review (86gs gpt-5.4 xhigh baseline):
codex-review-relay --uncommitted              # review working-tree changes (FM-04a local mode)
codex-review-relay --commit <SHA>             # review a single local commit
codex-review-relay --base origin/main         # only when a real PR branch exists

# Specialized models (86gs):
codex-relay-with gpt-5.5 "<prompt>"           # complex architecture 2nd opinion
codex-relay-with gpt-5.3-codex "<prompt>"     # delegated codegen

# Default exec (CRS, off-loads 86gs quota):
codex-crs "<prompt>"
```

APPROVE → proceed. CHANGES_REQUIRED → fix in a new commit, re-review (≤ round cap 3).
If a relay 503s, switch to the other backend; if a governance review degrades
86gs xhigh → CRS high, mark the commit trailer `codex_review_relay: crs (effort=high, fallback)`.

### Layer 2 — Evaluation fleet (formalized · ADR-026)

3 codebase-grounded testing sub-agents, invokable via `subagent_type=`:

| `subagent_type` | Tests | Rubric dim |
|---|---|---|
| `functional-tester` | end-to-end codepath wiring, broken handoffs, dead code (does NOT run real CCX) | Dim 1 / Dim 5 |
| `novice-simulator` | first-time-engineer friction + missing recovery paths | Dim 2 |
| `industrial-ui-comparator` | UI parity vs Hyperworks / Abaqus / ANSYS | Dim 3 |

**Canonical protocol SSOT** = `.planning/test_subagents/*.md`. The
`.claude/agents/` definitions are thin frontmatter wrappers pointing back to it
(no protocol duplication). **Anti-gaming guards (verbatim, ADR-026):**

- **B:-1** scoring done by sub-agents, NOT the main session
- **D:-1** every score cites file:line evidence
- **F:-1** sub-agents are NEVER given prior audit / retro / blueprint files
- **G:-1** sub-agents test what the codebase IS, not what it CLAIMS (no README/comment trust)

Spawn the 3 in parallel (one message, multiple Agent calls); the main session
collects reports and synthesizes the composite. Reports → `.planning/audits/`.

### Layer 3 — Strategic (deferred)

A Kogami-FEA equivalent (`claude -p` zero-tool independent reviewer for
decision-arc coherence / roadmap fit / **Tier-claim honesty**) is deferred per
the core-dual-layer scope. Seat reserved; build via a future ADR if needed.

---

## Claim-tier discipline (ADR-023 · unchanged)

Name the claim tier in every simulation summary. Never let Tier 0/1 evidence
imply Tier 2.

- **Tier 0** sandbox/demo — `demo-only` / `software-path evidence only` / `candidate-only`
- **Tier 1** engineering candidate — reproducibility manifest + units/material/BC/contact trace + hashes + limitations
- **Tier 2** signed validation — public benchmark + metrics + tolerance + convergence + signoff (strict gate)

## Honesty contract (绝对诚实客观)

FM-04a ran a long strict-honesty milestone. **Honest correction (ADR-027 §6):** the "22+
consecutive Tier-2 phases" framing over-claims — the Tier-2 *analytical-cross-check* march ran
through ~Phase 38; **Phases 40–45 were Tier-0 demo / UX work**, not Tier-2. Do not summarize the
whole run as "22+ consecutive Tier-2 phases." Honesty contract carried verbatim:

- `confidence: <h|m|l>` tag on **every** commit (already standard).
- Honest scope adjustment at implementation time is documented inline, not
  hidden (6 such pivots logged across FM-04a) — **not** score-gaming.
- NEVER re-score prior phases retroactively; NEVER apply weights/transforms to
  the composite; composite = simple arithmetic mean of 6 dims.
- Additive-only on the Phase 1-N chain (no test-threshold edits; App.tsx LOC pin).

## Governance carried (unchanged by ADR-026)

- **Calibration cap** (ADR-012): self-pass-rate from
  `scripts/compute_calibration_cap.py --human`, not intuition.
- **Branch protection** (ADR-013): required checks on `main` =
  `lint-and-test (3.11)` · `calibration-cap-check` · `trailer-check` ·
  `golden-samples-validation`.
- **golden_samples HF guards** (ADR-011 AR-2026-05-16): `^GS-\d{3}$`
  signed-registry = hard-stop read-only; `*-candidate` = writable carve-out.
- **Linear work-control** + PR-only-to-`main` for Linear-routed work.
  FM-04a-class direct-execution = local-commit / no-push (standing authorization).
- **No date/schedule gating** (ADR-011 AR-2026-05-03): gates are
  dependency/task-completion-driven, never calendar-driven.
- **Composite rubric mandate → REFRAMED by ADR-027 (2026-06-03, Accepted)**: the 6-dim
  rubric v2.0 is now a **health dashboard / direction signal, NOT a binary ship gate**. The
  former "all-6-dims-≥99 APPROVE gate" is **retired** (unreachable at the real ~+0.4/phase
  slope; two anchors — commercial-CAE UI parity, signed public benchmark — mission-incompatible).
  **FM-04a v1.0 = honest engineering-candidate, COMPLETE** (13 `tier_2_validated` real-ccx ↔
  analytical cross-checks; **zero public-benchmark agreements; not signed validation**). Rigor is
  held by two hard guardrails (ADR-027 **G-1** regression floor + **G-2** Tier-2 evidence packet),
  not by a score. v2 (FM-05) = NAFEMS real benchmark agreement + reproduce-CLI/audit-log; UI
  parity de-scoped. Latest dashboard read: **81.33 @ Phase 43** (code ~Phase 45 unscored).

## Files comprising the dev-team architecture (do NOT modify without Codex + user ratification)

- `docs/adr/ADR-026-dev-team-architecture-realignment.md` (governance record)
- `CLAUDE.md` (this — team-architecture SSOT)
- `AGENTS.md` (Codex-facing operating rules)
- `.claude/agents/{functional-tester,novice-simulator,industrial-ui-comparator}.md`
- `.planning/test_subagents/*.md` (evaluation protocol SSOT)

## Inherited rules from `~/CLAUDE.md` (user-level governs)

- Model routing v2.3 (Opus 4.7 主驱动 + Codex 4-model 双引擎 · round cap=3)
- Subagent 优先原则 (push 主 context ≥35% 或真并行/隔离才外包 · 1M ctx 校准)
- Codex relay (86gs xhigh primary, CRS high fallback; 跨 relay 同名模型不等价)
- 压缩阈值 40/60/75% (1M ctx 校准)
- 长技术 session 末尾叠加大白话中文总结
