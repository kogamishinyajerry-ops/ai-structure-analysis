# Codex Governance Review — ADR-027 (Milestone Goal Reset)

- **Artifact reviewed:** `docs/adr/ADR-027-milestone-goal-reset.md` (+ `.planning/STATE.md` 2026-06-03 reconciliation block)
- **Relay / model:** 86gamestore `gpt-5.5` (xhigh), `CODEX_HOME=~/.codex-relay`
- **Trigger:** repo-level policy / governance change (ADR-026 §"repo-level policy changes need explicit review evidence")
- **Date:** 2026-06-03
- **Driver:** Claude Opus 4.8 (1M) under the human owner's Path-A directive
- **Round cap:** 3 (ADR-026). Used R0 + R1; R1's residual fix landed via the verbatim-exception (no R2 burned).

---

## R0 — VERDICT: CHANGES_REQUIRED (4 findings)

| # | Sev | Finding | Disposition |
|---|---|---|---|
| 1 | **P1 (blocking)** | AERON archive overbroad; "not integrated" likely FALSE → would break live CalculiX plumbing. Narrow D4; run an import/use audit; preserve the live path. | **FIXED.** Ran a full-repo import/use audit → AERON IS live (imported by `agents/solver.py`, ≥5 tests, `pyproject` pkg `aeron*`, reachable via `backend/app/workbench` facade). D4 reframed "archive" → "**clarify, do NOT archive**"; retire only the stale ROADMAP FM-02 framing + unmerged `ENG-35/36/38` branches. Audit recorded verbatim in D4. STATE.md + memory corrected (the "orphaned" claim was a scoped-grep error — checked only `backend/`+`frontend/`, missed top-level `agents/`). |
| 2 | P2 | Retiring the 6×99 gate needs an explicit replacement guardrail, not just "dashboard." Define a fixed v2 evidence packet + a regression floor for the 13 existing cases. | **FIXED.** Added **G-1** (regression floor: 13 candidates' residuals within tolerance + signed-refusal intact) and **G-2** (explicit 7-item Tier-2 evidence packet, no item substitutable by a score). |
| 3 | P2 | Declaring v1.0 "complete" is honest only if the label stays narrow; "Tier-1/Tier-2 candidate" can read like signed validation. | **FIXED (verbatim).** Adopted Codex's exact wording: "engineering-candidate complete; 13 `tier_2_validated` real-ccx ↔ analytical cross-checks; **zero public-benchmark agreements; not signed validation**." |
| 4 | P3 | Doc reconciliation must be part of acceptance, not deferred cleanup. | **FIXED.** Ratification now lists 5 required acceptance gates (CLAUDE.md + ROADMAP.md edits, STATE truth-up, AERON note/branch-prune, archived review evidence) that ALL land in the ratification commit before Status → Accepted. |

## R1 (re-review) — VERDICT: CHANGES_REQUIRED (1 residual)

- P1 → **RESOLVED** (AERON live/tested/imported; only stale framing + dead branches retired).
- P2 (guardrail) → **NOT-RESOLVED**: G-2 ok, but G-1 over-claimed CI enforcement — it cited
  `golden-samples-validation`, which only validates **signed `GS-###`** registry metadata, not
  the 13-candidate residual floor or the signed-refusal invariant.
- P2 (v1.0 label) → **RESOLVED**.
- P3 (acceptance gates) → **RESOLVED**.
- New blocking: **G-1 enforcement mismatch** — either wire a real CI guard for the 13-case
  floor or reword so it does not claim `golden-samples-validation` enforces it.

### R1 residual disposition — landed via verbatim-exception (Codex's own option b)

Verified the real CI surface: signed-refusal IS CI-enforced — but by the `ci.yml`
`lint-and-test` pytest job (`test_solver_run_signed_registry_refusal.py`,
`test_phase14_cross_route_signed_registry_refusal.py`, `test_phase13_refused_claims.py`), **not**
`golden-samples-validation`. The 13-case residual floor is **not** re-verified by a live-ccx
re-solve in CI (verdicts are static committed YAMLs; no `cross_check_verdict` re-run gate found in
`tests/`). G-1 reworded to state this honestly + ticket the automated gate as **v2 item V2-0**.
Per `~/CLAUDE.md` verbatim-exception (faithful landing of Codex's suggested fix), no R2 was run.

## Outcome

All R0 (4) + R1 (1) findings resolved. The reset is mission-coherent and honesty-preserving
(Codex R0/R1 both said so). ADR-027 remains **Proposed**; the human owner is the Decider.
**Recommend ratification.** On ratify: land the 5 acceptance-gate edits in one commit, flip
Status → Accepted, trailer `confidence: high`.
