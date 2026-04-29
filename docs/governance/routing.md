# Model Routing v6.2 — AI-Structure-FEA

> **Status:** Canonical routing for this project as of 2026-04-25.
> **Source of truth:** [ADR-011 §Decision (T0/T1/T2)](../adr/ADR-011-pivot-claude-code-takeover.md#decision) and [§T2 amendments per AR-2026-04-25-001](../adr/ADR-011-pivot-claude-code-takeover.md#decision).
> **Supersedes:** Prior "Antigravity 三模型分层分工" routing recorded as ADR-005 in the Notion 决策库 (the layered-3-model handoff with separate front-line / back-line / verification roles).

This document is a **thin pointer** to ADR-011. Read it for orientation; act per ADR-011.

---

## Three-tier architecture (T0 / T1 / T2)

| Tier | Identity | Role | Entrypoint |
|------|----------|------|------------|
| **T0** | Human admin (CFDJerry / Kogami) + Opus 4.7 (Notion architecture-gate) | Decision authority. Issues **AR-** records (Architecture-Ratification) that bind T1 and T2 conduct. Holds emergency override on branch protection. | Notion conversations + AR-* records in 决策库 |
| **T1** | Claude Code CLI (Opus 4.7, 1M context window) | **Sole development executor.** Edits code, opens PRs, runs scripts, owns the keyboard. Reads ADR-011 / ADR-012 as binding contract. | This terminal session |
| **T2** | Codex GPT-5.4 (verify mode) | **Independent reality-check anchor + joint-dev peer.** Reviews PRs as anti-shenanigans backstop with M1-M5 mandatory triggers. Cannot be invoked through Agent tool — must use `/codex-gpt54` slash command. | `/codex-gpt54 review PR #N` from T1's session |

## What changed from "Antigravity 三模型"

| Old (Antigravity) | New (v6.2 per ADR-011) |
|---|---|
| Three coordinated models with handoff protocol | Single-path execution (T1) with verification (T2) and decision (T0) — no developer-side coordination |
| Front-line / back-line / verification roles | T0 (decide) / T1 (execute) / T2 (verify) — collapsed roles |
| Handoff protocol between models | No model-to-model handoff; AR-* records bind T1; PR review binds merge |
| Three separate Notion sessions | One Notion control plane page per project + per-session entries in Sessions DB |

## Mandatory triggers (M1-M5) per AR-2026-04-25-001 §4

T2 (Codex) review is **mandatory** when any of these fire (M-trigger taxonomy ratified 2026-04-25):

| Trigger | What fires it |
|---------|---------------|
| **M1** | PRs touching governance text (`docs/adr/**`, `docs/governance/**`, `docs/failure_patterns/**`, ADR amendments) |
| **M2** | Non-trivial executable assertion (reverts, sign/direction math, CI claims, factual numerical computations) |
| **M3** | PRs claiming HF zone compliance (HF1/HF4 scope verification) |
| **M4** | Governance text → enforcement code translation (hooks, CI, validators, lints, schemas) |
| **M5** | Any PR opened while calibration ceiling ≤ 50% (per ADR-012) |

These triggers are **independent of the calibration ceiling**: M1-M5 can mandate Codex even when the ceiling is 95%, and the BLOCKING-30 ceiling can mandate Codex even when no M-trigger fires.

## Self-pass-rate (per ADR-012)

T1's self-rated pass-rate is **mechanically derived**, not honor-system. T1 reads the ceiling from `python3 scripts/compute_calibration_cap.py`; the PR template prefills the field; CI's `calibration-cap-check` validates the claim. Recovery: 3 trailing R1=APPROVE PRs reset the ceiling to 95%.

## Branch protection (per ADR-013)

After ADR-013 lands (PR #25), `main` requires:

- `lint-and-test (3.11)` green
- `calibration-cap-check` green
- linear history (squash-only)
- no force-pushes, no deletions
- conversation resolution

`enforce_admins: false` — T0 retains emergency override. The discipline binding (ADR-013 §"Discipline binding") prevents T1 from invoking that bypass.

## Discrepancy with global model-routing (`~/.claude/MODEL_ROUTING.md`)

Global Claude Code config in `~/.claude/MODEL_ROUTING.md` describes a slightly broader routing rule (includes Gemini for fast research, etc.). For **AI-Structure-FEA work specifically**, this document and ADR-011 are authoritative; global config applies to non-project work.

---

## Where to look up specifics

| Question | Source |
|----------|--------|
| What are the M-triggers? | ADR-011 §Decision (this doc §"Mandatory triggers") |
| What's HF1 hard-stop? | ADR-011 §Hard-Floor Rules |
| What does T0 / T1 / T2 mean? | ADR-011 §Decision |
| How do I run Codex on a PR? | `/codex-gpt54 review PR <N>` (T1's slash command, NOT `Agent`) |
| Why was the 3-model Antigravity routing replaced? | ADR-011 §Context (drift between coordinated models, no single accountable executor) |
| What's the rolling-window self-pass-rate? | ADR-012 |
| What enforces branch protection? | ADR-013 + `scripts/apply_branch_protection.sh` |
