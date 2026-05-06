# PR #126 Claude Opus Audit — WF-00

**Pilot issue:** ENG-32 · WF-00 Codex-primary / Claude-audited workflow pilot
**Target PR:** #126 · `feat(aeron): S0+S1 — AGENTS.md + L0 FEABackend protocol`
**Command:** `claude -p <packet> --model opus --no-session-persistence --tools "" --max-budget-usd 0.80`
**Tool access:** Disabled
**Date:** 2026-05-06

## Verdict

**BLOCKER**

## Findings

### P1 (Blocking) — Root `AGENTS.md` reverses approved execution model

The proposed `AGENTS.md` encodes Apex/Claude ownership of `main`, Apex merge
authority, and Codex as delegated-branch worker. This directly inverts the
user-approved Codex-primary / Linear-controlled / Claude-auditor model. Merging
would let a repo-level policy file silently re-route authority for all future
agents reading `AGENTS.md` as local truth. Concur with Codex disposition.

### P2 (Blocking, derived) — Governance change bundled with code

PR #126 mixes a repo-wide governance artifact (`AGENTS.md`) with salvageable L0
protocol code (`aeron/protocols/fea_backend.py`). Bundling these means a single
merge decision covers two distinct risk classes. Governance must land in its
own PR with explicit reviewer acceptance.

### N1 (Non-blocking) — CI green is not policy approved

`lint-and-test`, `calibration-cap-check`, and `build-and-push` passing does
not validate role-authority semantics. Codex pre-merge gate is mandatory at T1
ceiling 50% (4/5 prior CHANGES_REQUIRED). No final post-fix independent
acceptance is on record.

### N2 (Non-blocking) — AERON protocol code is salvageable

`fea_backend.py` already absorbed two Codex review rounds (packaging, strict
status vocabulary, fault taxonomy, strict Pydantic carriers). Worth preserving
in a follow-up Codex-owned PR.

## Required Next Action

1. Do not merge #126 as-is.
2. Split the PR:
   - Close #126 or convert it to draft.
   - Open a new Codex-owned PR containing only a rewritten `AGENTS.md` that
     encodes Codex = primary executor, Linear = work-control truth, GitHub =
     code truth, Claude Opus 4.7 = reviewer/auditor, Notion = post-truth
     mirror.
   - Open a separate Codex-owned PR for the L0 AERON protocol code
     (`aeron/protocols/fea_backend.py` + tests).
3. Each new PR requires a final post-fix independent acceptance from local
   Claude Opus before merge.
4. Calibration: log this disposition as the 5th of last 5 outcomes; ceiling
   remains <=50% until a streak of APPROVE-on-first-round outcomes lifts it.
