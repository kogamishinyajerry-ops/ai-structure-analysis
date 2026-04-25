# AI-Structure-FEA · STATE

> **Stamp:** `post-pivot-foundation-freeze-2026-04-25`
> **Last updated:** 2026-04-25
> **Maintained by:** T1 (Claude Code CLI · Opus 4.7) per ADR-011 §6 Sessions fully traced.

This file is the **repo-side execution status snapshot**. Notion 项目控制塔 (root_page_id `345c68942bed80f6a092c9c2b3d3f5b9`) is the human-facing process SSOT. When they conflict, **git is authoritative**; STATE.md is updated to match git, and Notion is patched from STATE.md.

---

## Phase ledger

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1 — Foundation | ✅ Done (Sprint 2) | See `docs/PHASE1_SPRINT2_COMPLETION.md` and `PHASE1_SPRINT1_COMPLETION.md`. |
| Phase 1.5 — Foundation-Freeze (post-pivot) | 🟡 Active (48h window opened 2026-04-25) | This phase exists to land the Claude Code single-path governance baseline before Phase 2 starts. |
| Phase 2 — Web Console | ⏳ Planned (next active) | Gated by Phase 1.5 closure + GS deviation attribution (FF-02). |
| Phase 3 — Nonlinear & adaptive mesh | ⚪ Planned | No dates committed. |

---

## Phase 1.5 task table

| Task | Status | Branch | Commit | Notes |
|------|--------|--------|--------|-------|
| FF-01 — ADR-011 Pivot baseline | ✅ Done · **R5 APPROVE** | `feature/AI-FEA-ADR-011-pivot-claude-code-takeover` | `9a7afad` | 5-round Codex arc; reports in `reports/codex_tool_reports/adr_011_r{1..5}_review.md`. PR pending push. |
| FF-01b — Notion Decisions DS sync | ✅ Done | (no branch — Notion API write) | n/a | Page id `34dc6894-2bed-81f0-bf9a-edceb840945d`. Discovered DS schema gap (missing `Branch`/`Session Batch`/`ADR Link`); see ADR-011 Risk #3. |
| FF-02 — GS deviation attribution → FailurePatterns | ✅ Done | `feature/AI-FEA-FF-02-failure-patterns` | `020f2d3` | 3 FPs (FP-001/002/003); proposes GS-001/002/003 → `insufficient_evidence`. PR pending push. |
| FF-03 — Routing v6.2 doc (supersede Antigravity) | ⚪ Pending | — | — | Lower priority: ADR-011 already encodes the routing; this would be a thin pointer doc. |
| FF-04 — Onboarding manual (Claude Code edition) | ⚪ Pending | — | — | New-contributor entry doc. |
| FF-05 — STATE.md | 🟡 In-flight (this commit) | `feature/AI-FEA-FF-05-state-md` | (this commit) | Adopts `.planning/` directory convention from cfd-harness-unified for cross-project consistency. |
| FF-06 — pre-commit path-guard for HF1 forbidden zone | ⚪ Pending | — | — | Per ADR-011 §Enforcement Maturity. Hard deadline 2026-05-23. |
| FF-07 — CI commit-trailer presence + claim-id format check (HF5) | ⚪ Pending | — | — | Same hard deadline. |
| FF-08 — `golden_samples/<id>` registry schema validation (HF3) | ⚪ Pending | — | — | Same hard deadline. |
| FF-09 — README ↔ ADR-011 sync (Golden Rules vs 5 dev rules) | ⚪ Pending | — | — | Reconcile partial overlap noted in ADR-011 §Cross-References. |

---

## Active branches (local · 2026-04-25 pre-push)

```
feature/AI-FEA-ADR-011-pivot-claude-code-takeover  (8+ commits · ADR-011 R5 APPROVE)
feature/AI-FEA-FF-02-failure-patterns               (1 commit · 4 FP files)
feature/AI-FEA-FF-05-state-md                      (this commit)
feature/AI-FEA-S2.1-02-notion-sync-contract-align  (origin tracked + 5 dirty + 4 untracked · pre-existing in-flight, not touched by pivot work)
```

`main` is clean and matches `origin/main` (`815945c`).

## Open PRs

(None pending — all branches still local. About to push and open 3 PRs: ADR-011, FF-02, FF-05.)

---

## Active ADRs

| ADR | Status | File |
|-----|--------|------|
| ADR-002 | Live | (referenced in code; file not in repo — in Notion) |
| ADR-004 | Live | (referenced in `agents/router.py`, `schemas/sim_state.py`) |
| ADR-005 | Live | (well_harness Notion writeback) |
| ADR-008 | Live | (FreeCAD N-3 dummy guard, see `tools/freecad_driver.py`) |
| ADR-010 | Live | (notion_sync contract — being aligned in S2.1-02) |
| **ADR-011** | **Accepted (R5 APPROVE)** | `docs/adr/ADR-011-pivot-claude-code-takeover.md` (on FF-01 branch) |

ADR-012 / ADR-013 are **proposed candidates** (per FP-001/002/003 cross-cutting findings + ADR-011 §Known Gaps), not yet drafted.

---

## Carry-overs that ADR-011 R5 APPROVE does **not** make go away

1. HF1 / HF5 enforcement is honor-system today (only `ruff` pre-commit + lint+pytest CI exist). Auto-detection is FF-06/07/08, deadline **2026-05-23**.
2. `main` branch protection rules, PR review state machine, subagent failure SOP — all deferred to ADR-012/013 candidates (per ADR-011 §Known Gaps).
3. Notion Decisions DS schema gap (`Branch` / `Session Batch` / `ADR Link` properties missing, `notion_sync.register_decision()` would fail against the live schema). S2.1-02's `Sprint` add does not address it. Needs separate ADR.
4. GS-001/002/003 status flip pending_review → `insufficient_evidence` is **proposed in FP-001/002/003 only**; the Notion control-plane status field has not yet been changed. Action item attached to FF-02 PR merge.

---

## How to update this file

Update STATE.md whenever:

- A FF-task changes status (pending → in-flight → done).
- A branch is pushed or a PR opens / merges.
- An ADR is accepted, revised, or superseded.
- A carry-over is closed (delete the line, don't strike-through — git history holds the trail).
- The `Last updated` stamp must change in the same commit.

Do **not** update STATE.md to reflect things that have not yet landed in the repo. Forward-looking commitments belong in the relevant ADR / task tracker, not here.
