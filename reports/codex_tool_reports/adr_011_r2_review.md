# Codex Review · ADR-011 · Round 2

- **Date:** 2026-04-25
- **Reviewer:** Codex GPT-5.4-xhigh
- **Subject:** ADR-011 R2 amendment @ commit `a77bc99` on branch `feature/AI-FEA-ADR-011-pivot-claude-code-takeover`
- **Account used:** picassoer651@gmail.com (score 90%)
- **Tokens:** 66,027

## Verdict

**`CHANGES_REQUIRED`** (down from R1: 2 BLOCKING + 3 SHOULD_FIX + 1 NICE_TO_HAVE → 1 BLOCKING + 2 SHOULD_FIX). Substantive progress on R1 findings #1, #3, #4, #5, #6.

## Findings (verbatim from Codex)

### BLOCKING

1. **R1 BLOCKING #2 only half-fixed.** HF1 forbidden zone now includes `Makefile` `docker-base` / `hot-smoke` segments, but the rollback weighted table only assigns weight to `Dockerfile` — `Makefile` zone is uncovered. The "weighted by zone severity" rollback rule does not span all HF1 zones. Audit accounting still incomplete. Refs: ADR-011 §HF1 zone (line 54), §Rollback (line 149).

### SHOULD_FIX

2. **Calibration log filename inconsistent inside ADR.** §Calibration Mode says HF2 trigger writes `reports/hf2_calibration.md`. §Risks → mini-retro paragraph still says it is based on `hf2_calibration.log`. The file on disk is the `.md` form. Refs: §Calibration Mode (line 86), §Risks (line 138), `reports/hf2_calibration.md`.

3. **R2 introduced a new repo-truth over-claim.** Cross-References says FF-02 "已完成，见 `docs/failure_patterns/FP-001/002/003`", and Known Gaps says `docs/failure_patterns/` was created. But on the current branch (`feature/AI-FEA-ADR-011-pivot-claude-code-takeover`) those files do not exist. They live on `feature/AI-FEA-FF-02-failure-patterns` (commit `020f2d3`). Refs: §Known Gaps (line 184), §Cross-References (line 190).

## Overall

> R1 的 #1/#3/#4/#5/#6 都算实质处理，不是单纯改口；但 #2 由于 HF1 加权表未覆盖全部 forbidden zones，不能批准。

## Disposition (claude-code-opus47)

- **Accepted:** all 3 findings.
- **Plan:** R3 amendment in this commit chain — (a) add `Makefile` line to rollback weight table at the same severity tier as `Dockerfile`; (b) fix the residual `.log` reference to `.md`; (c) explicitly call out that `docs/failure_patterns/` lives on a separate branch and **not** on this branch. Re-run Codex (R3) for verdict.
- **No HF5:** all three findings agree with repo state; they are over-claims / inconsistencies in the ADR text itself, not verification mismatches against working code.
