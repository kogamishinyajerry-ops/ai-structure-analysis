# AI-Structure-FEA · STATE

> **Stamp:** `post-pivot-foundation-freeze-2026-04-25 · post-#17/18/19/20/21/22/23-merge · ADR-012/013-in-flight`
> **Last updated:** 2026-04-25 (after PR #23 ADR-011 amendments merge; main = `e53b0f7`; PR #24 ADR-012 + PR #25 ADR-013 in flight, both pending Codex R1)
> **Maintained by:** T1 (Claude Code CLI · Opus 4.7) per ADR-011 §6 Sessions fully traced.

This file is the **repo-side execution status snapshot**. Notion 项目控制塔 (root_page_id `345c68942bed80f6a092c9c2b3d3f5b9`) is the human-facing process SSOT. When they conflict, **git is authoritative**; STATE.md is updated to match git, and Notion is patched from STATE.md.

---

## Phase ledger

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1 — Foundation | ✅ Done (Sprint 2) | See `docs/PHASE1_SPRINT2_COMPLETION.md` and `PHASE1_SPRINT1_COMPLETION.md`. |
| Phase 1.5 — Foundation-Freeze (post-pivot) | 🟡 Active (governance baseline merged 2026-04-25; FF-07/08/09 + ADR-012/013 still open) | FF-01 (ADR-011 + amendments), FF-02 (FailurePatterns), FF-05 (STATE.md), FF-06 (HF1 path-guard) all merged. ADR-012 (PR #24) + ADR-013 (PR #25) in Codex-review queue. FF-07/08/09 remain pending. |
| Phase 2 — Web Console | ⏳ Planned (next active) | Gated by FF-07/08/09 (HF5 trailer check, HF3 GS registry, README↔ADR-011 sync) per ADR-011 §Enforcement Maturity. |
| Phase 3 — Nonlinear & adaptive mesh | ⚪ Planned | No dates committed. |

---

## Phase 1.5 task table

| Task | Status | Branch | Commit | Notes |
|------|--------|--------|--------|-------|
| FF-01 — ADR-011 Pivot baseline | ✅ Merged (PR #17 · 2026-04-25) · **R5 APPROVE** | (deleted post-merge) | `34722ea` (squash) | 5-round Codex arc; reports landed at `reports/codex_tool_reports/adr_011_r{1..5}_review.md`. |
| FF-01a — ADR-011 amendments AR-2026-04-25-001 | ✅ Merged (PR #23 · 2026-04-25 12:06Z) · **R1 CR → R2 APPROVE** | (deleted post-merge) | `e53b0f7` (squash) | T2 rewording (Codex anti-shenanigans backstop + M1-M5 trigger taxonomy), §HF2 subagent split, §HF1 zone narrowing, §Enforcement Maturity post-FF-06 update, §Known Gaps ADR-012/013 number reassignment. R1 returned 3 BLOCKER + 1 SHOULD_FIX, fixed in commit `e96904d`. |
| FF-01b — Notion Decisions DS sync | ✅ Done | (no branch — Notion API write) | n/a | Page id `34dc6894-2bed-81f0-bf9a-edceb840945d`. Discovered DS schema gap (missing `Branch`/`Session Batch`/`ADR Link`); see ADR-011 Risk #3. |
| FF-02 — GS deviation attribution → FailurePatterns | ✅ Merged (PR #18 · 2026-04-25) | (deleted post-merge) | `77e6813` (squash) | 3 FPs (FP-001/002/003); recommends GS-001/002/003 → `insufficient_evidence`. R1 (CR, 1 HIGH + 3 MEDIUM) → R2 APPROVE. |
| FF-03 — Routing v6.2 doc (supersede Antigravity) | ⚪ Pending | — | — | Lower priority: ADR-011 already encodes the routing; this would be a thin pointer doc. |
| FF-04 — Onboarding manual (Claude Code edition) | ⚪ Pending | — | — | New-contributor entry doc. |
| FF-05 — STATE.md | ✅ Merged (PR #19 · 2026-04-25) | (deleted post-merge) | `4a64cfd` (squash) | Adopts `.planning/` directory convention from cfd-harness-unified. R1 (CR, 1 HIGH stale-state + 1 MEDIUM ADR-012/013 inventions) → R2 APPROVE. |
| FF-06 — pre-commit path-guard for HF1 forbidden zone | ✅ Merged (PR #22 · 2026-04-25 10:43Z) · **R1 CR → R2 APPROVE** | (deleted post-merge) | `ac98fc3` (squash) | `scripts/hf1_path_guard.py` + `tests/test_hf1_path_guard.py` (30 tests). R1 returned 1 BLOCKER (rename/delete bypass via `pass_filenames` default) + 2 SHOULD_FIX (HF1.6 over-block, override audit). Fixed via `--all-files` flag and HF1.6 scoping. |
| FF-07 — CI commit-trailer presence + claim-id format check (HF5) | ⚪ Pending | — | — | Per ADR-011 §Enforcement Maturity. Hard deadline 2026-05-23. |
| FF-08 — `golden_samples/<id>` registry schema validation (HF3) | ⚪ Pending | — | — | Same hard deadline. |
| FF-09 — README ↔ ADR-011 sync (Golden Rules vs 5 dev rules) | ⚪ Pending | — | — | Reconcile partial overlap noted in ADR-011 §Cross-References. |

### Governance ADRs in flight

| ADR | Status | PR | Branch | Notes |
|-----|--------|----|--------|-------|
| **ADR-012 — Calibration cap for T1 self-pass-rate** | 🟡 OPEN, CI green, awaiting Codex R1 | **#24** | `feature/AI-FEA-ADR-012-calibration-cap` | Replaces RETRO-V61-001's honor-system with a mechanical 5-PR rolling-window ceiling. Bootstrap: 5/5 CR → ceiling 30%, BLOCKING. 42 unit tests passing. Self-applies its own gate — must reach R1=APPROVE before merge. |
| **ADR-013 — Branch protection enforcement** | 🟡 OPEN, stacked on PR #24, awaiting Codex R1 | **#25** | `feature/AI-FEA-ADR-013-branch-protection` | 3-layer wrapper around ADR-012: PR template + CI `--check` workflow + `gh api` protection script. M1+M4+M5 triggers fire. Repo flipped private→public on 2026-04-25 to access protection API. CI doesn't run on this PR until #24 merges and base auto-rebases. |

---

## Repo state

`main == origin/main == e53b0f7` (post #17 + #18 + #19 + #20 + #21 + #22 + #23).

Merge timeline 2026-04-25 (UTC):

```
07:56  #17  ADR-011 baseline                               (FF-01)
07:56  #18  FailurePattern attribution                     (FF-02)
07:56  #19  STATE.md seed                                  (FF-05)
08:33  #20  Revert direct-push 815945c                     (governance hygiene)
10:26  #21  Post-merge cleanup — STATE.md + Codex archive  (chore)
10:43  #22  HF1 path-guard pre-commit                      (FF-06)
12:06  #23  ADR-011 amendments AR-2026-04-25-001           (FF-01a)
```

## Open PRs (governance-chain · this session)

| PR | Branch | Status |
|----|--------|--------|
| #24 | `feature/AI-FEA-ADR-012-calibration-cap` | OPEN · CI green · CLEAN/MERGEABLE · awaiting Codex R1 (BLOCKING gate self-applied) |
| #25 | `feature/AI-FEA-ADR-013-branch-protection` | OPEN · stacked on #24 (base will auto-rebase to main on #24 merge) · awaiting Codex R1 |

## Open PRs (Phase 1 sprint work · pre-pivot, not in governance chain)

The following PRs were opened on 2026-04-18 and remain OPEN as of 2026-04-25. They are orthogonal to the Phase 1.5 governance pivot and are owned by their original sprint authors. STATE.md tracks them here for repo-wide situational awareness; **disposition (rebase / close / merge under ADR-006) is not in scope for the FF-* work** and will be handled separately.

| PR | Branch | Title |
|----|--------|-------|
| #11 | `feature/AI-FEA-P1-02-hot-smoke` | AI-FEA-P1-02 hot-smoke: real ccx on GS-001 inside P1-01 image |
| #12 | `feature/AI-FEA-P1-03-golden-sample-validation` | AI-FEA-P1-03 golden-sample validation: fix 37.7% deviation (shear lock) on GS-001 |
| #13 | `feature/AI-FEA-P1-04a-rag-audit` | AI-FEA-P1-04a: RAG corpus audit — empirical SCRATCH-REBUILD evidence |
| #14 | `feature/AI-FEA-P1-06-gate-solve-lint` | AI-FEA-P1-06: Gate-Solve static .inp lint — pre-solver defect shield |
| #15 | `feature/AI-FEA-P1-06b-wire-linter-solver` | AI-FEA-P1-06b: wire Gate-Solve linter into Solver node (stacked on #14) |
| #16 | `feature/AI-FEA-P1-05-reviewer-fault-injection` | AI-FEA-P1-05: Reviewer fault-injection baseline + ADR-004 mirror |

**Carry-over flag:** these PRs predate ADR-011 and therefore predate the T0/T1/T2 routing contract. Any rebase onto current main must (a) inherit ADR-011 §HF1-HF5 zoning, (b) decide whether their original review trail is sufficient or whether re-review under v6.2 is required. This is a separate decision from FF-07/08/09 + ADR-012/013.

---

## Active ADRs

| ADR | Status | File |
|-----|--------|------|
| ADR-002 | Live | (referenced in code; file not in repo — in Notion) |
| ADR-004 | Live | (referenced in `agents/router.py`, `schemas/sim_state.py`) |
| ADR-005 | Live | (well_harness Notion writeback) |
| ADR-008 | Live | (FreeCAD N-3 dummy guard, see `tools/freecad_driver.py`) |
| ADR-010 | Live | (notion_sync contract — being aligned in S2.1-02) |
| **ADR-011** | **Accepted (R5 APPROVE) · merged + amended (R1 CR → R2 APPROVE) on main** | `docs/adr/ADR-011-pivot-claude-code-takeover.md` (with AR-2026-04-25-001 amendments) |
| **ADR-012** | **Drafted; awaiting Codex R1 on PR #24** | `docs/adr/ADR-012-calibration-cap-for-t1-self-pass-rate.md` (in `feature/AI-FEA-ADR-012-calibration-cap`) |
| **ADR-013** | **Drafted; awaiting Codex R1 on PR #25** | `docs/adr/ADR-013-branch-protection-enforcement.md` (in `feature/AI-FEA-ADR-013-branch-protection`) |

Two **further follow-up ADRs (numbers ADR-014 and beyond, not yet drafted)** are proposed in FP-001/002/003 cross-cutting findings + ADR-011 §Known Gaps:

- "Golden-sample triplet contract" (README + `expected_results.json` + theory script as one calculator)
- "Comparison-validity precondition for `REFERENCE_MISMATCH` retry routing"

These will be assigned numbers when drafted; do not pre-reserve ADR IDs.

---

## Carry-overs that ADR-011 R5 APPROVE does **not** make go away

1. HF1 hard-stop is now enforced via FF-06 pre-commit (PR #22 ✅); the **PR-protected zone** (`docs/adr/`, `docs/governance/`, `.github/workflows/**`) relies on Codex M1 + branch protection (ADR-013 in flight, PR #25). HF5 (commit-trailer) auto-detection remains FF-07. Hard deadline **2026-05-23**.
2. Branch protection rules + PR review state machine — proposed in ADR-013 (PR #25). Layer 3 activation (`bash scripts/apply_branch_protection.sh`) is a one-shot T0 action post-#25-merge.
3. Subagent failure SOP — still deferred to a future ADR (number TBD).
4. Notion Decisions DS schema gap (`Branch` / `Session Batch` / `ADR Link` properties missing, `notion_sync.register_decision()` would fail against the live schema). S2.1-02's `Sprint` add does not address it. Needs separate ADR.
5. GS-001/002/003 status flip pending_review → `insufficient_evidence` is **proposed in FP-001/002/003 only**; the Notion control-plane status field has not yet been changed. Action item attached to FF-02 PR merge.
6. Self-pass-rate honor-system (RETRO-V61-001) is empirically falsified by session 2026-04-25 (T1 estimated 80-95% on 5 PRs that all returned R1=CR). ADR-012 (PR #24) replaces it with a mechanical ceiling. Until #24 merges, T1 still operates under the falsified honor-system — i.e., this PR (#25) and the next few must explicitly cite the empirical 0/5 R1-pass-rate when self-rating.

---

## How to update this file

Update STATE.md whenever:

- A FF-task changes status (pending → in-flight → done).
- A branch is pushed or a PR opens / merges.
- An ADR is accepted, revised, or superseded.
- A carry-over is closed (delete the line, don't strike-through — git history holds the trail).
- The `Last updated` stamp must change in the same commit.

**STATE.md must be updated in the SAME PR as the change it reflects** (FF-05 R1 lesson). Do **not** update STATE.md to reflect things that have not yet landed in the repo. Forward-looking commitments belong in the relevant ADR / task tracker, not here. PRs in flight may be listed under "Open PRs" but their status must reflect actual git state, not aspirations.
