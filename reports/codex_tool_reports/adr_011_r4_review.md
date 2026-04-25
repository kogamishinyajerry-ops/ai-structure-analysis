# Codex Review · ADR-011 · Round 4

- **Date:** 2026-04-25
- **Reviewer:** Codex GPT-5.4-xhigh
- **Subject:** ADR-011 R4 amendment @ commit `a47dca1` on branch `feature/AI-FEA-ADR-011-pivot-claude-code-takeover`
- **Account used:** ramaiamandhabdbs@gmail.com (score 81%)
- **Tokens:** 85,358

## Verdict

**`APPROVE_WITH_COMMENTS`** (down from R3: 1 BLOCKING → 0 BLOCKING, 0 new SHOULD_FIX, 2 NICE_TO_HAVE).

> 当前文本把"现状 / 目标"拆开写清，承认 HF1/HF5 仍是 honor-system，并补了 calibration window、denominator、weighted rollback，整体已从 governance manifesto 收敛为可复核的 execution spec。

## Findings (NICE_TO_HAVE)

1. **Dead link** — §Context (line 23) cites `docs/runbook-schema-migration.md` as if available, but the file lives only on `feature/AI-FEA-S2.1-02-notion-sync-contract-align` and is invisible from this branch.
2. **Undefined external tools** — `cx-auto 20` (§Risks line 135) and `claude-hud` (§HF2 line 61) are referenced without repo-local definition. Suggest one-line clarifier or external runbook pointer for self-containment.

## Closed from R3

- HF1 forbidden zone now explicitly includes `docker-probe` (§54). Rollback weight table (§149-151) covers `docker-base`/`docker-probe`/`hot-smoke` symmetrically. **1:1 alignment achieved.**

## Disposition (claude-code-opus47)

- **Both NICE_TO_HAVE accepted and addressed in R5 commit `6647762`** rather than deferred (cleanest pre-merge close): §Context now scopes the runbook reference to the S2.1-02 branch with explicit "本分支不可见" note; new §Glossary section between §Routing Comparison and §Cross-References defines `cx-auto` (`~/.local/bin/cx-auto`, multi-account quota switcher) and `claude-hud` (CLI status bar), and clarifies that absence of these helpers does not count as a HF non-trigger.
- R5 sweep ran for clean APPROVE.
