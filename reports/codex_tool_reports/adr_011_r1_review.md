# Codex Review · ADR-011 · Round 1

- **Date:** 2026-04-25
- **Reviewer:** Codex GPT-5.4-xhigh (`-c model="gpt-5.4"`, reasoning effort xhigh)
- **Subject:** `docs/adr/ADR-011-pivot-claude-code-takeover.md` @ commit `f267228` on branch `feature/AI-FEA-ADR-011-pivot-claude-code-takeover`
- **Trigger:** ADR-011 §Commit Trailer Convention requires `Codex-verified` for governance / critical-claim commits. Pre-merge review per CLAUDE.md ≤70% self-pass-rate rule (treaty document, no executable claims yet).
- **Account used:** picassoer651@gmail.com (score 100%)
- **Tokens:** 101,777

## Verdict

**`CHANGES_REQUIRED`**

## Findings (verbatim from Codex)

### BLOCKING

1. **HF1/HF5 enforcement is honor-system, not auditable.** ADR-011 §49-53, §71-81 builds HF1/HF5 on `pre-commit hook + CI path-guard` and `Codex-verified: <claim-id>@<sha>` trailer. The repo currently has only a `ruff` pre-commit (`.pre-commit-config.yaml:1`) and lint+pytest CI (`.github/workflows/ci.yml:32`). There is no path-guard, no trailer-presence check.

2. **Rollback metrics are unstable.** `>15% mismatch` (§107-112) has no minimum sample size. `>2× HF1` mixes solver-core / golden-samples / governance-doc severity classes without weighting. With no auto-recording mechanism for HF1/HF5, the threshold itself is hard to track.

### SHOULD_FIX

3. **Forbidden zone is too narrow.** ADR-011 §49-50 lists only `agents/solver.py` and `tools/calculix_driver.py`. The real ADR-002/004/008 surface also includes `schemas/sim_state.py:9` (FaultClass enum), `agents/router.py:5` (fault routing), `agents/geometry.py:41` (ADR-008 N-3 dummy guard), `tests/test_toolchain_probes.py:28`, and `Dockerfile:17` (ADR-002 CalculiX 2.21 pin). Bypass risk in unfrozen surface.

4. **HF2 self-contradicts itself.** ADR-011 §45+§50 say "trigger → STOP". Risks §97-100 say "first 4 weeks attach reason and continue". Therefore HF2 is not actually a hard floor.

5. **Cross-references overstate alignment.** ADR-011 §134-135 claims README's 5 development rules and 9 Golden Rules are "一致". They overlap partially. `docs/architecture.md:7` and `docs/well_harness_architecture.md:23` do not define four-layer import boundary at an enforceable level.

### NICE_TO_HAVE

6. **Significant omissions confirmed.** Main-branch protection, PR review state machine, and subagent-failure rollback SOP are not in ADR-011 and not in the repo. Current "all code via PR" line in `README.md:81` is too thin to back the single-path treaty.

## Overall

> 方向是对的，但现在更像"治理宣言"，还不是"可验证执行规约"；因此不建议直接 `APPROVE`，但也没到 `BLOCK` 整个治理方向的程度。

## Disposition (claude-code-opus47)

- **Accepted:** all 6 findings.
- **Plan:** amend ADR-011 in a follow-up commit on the same branch. Findings #1, #4, #6 dictate explicit "Enforcement maturity" + "Known gaps" subsections; #2 tightens rollback math; #3 expands forbidden-zone list; #5 softens the cross-reference language. Re-Codex after amendment.
- **No HF5:** Codex's findings agree with repo state (the hooks really do not exist) — this is an over-claim in the ADR text, not a verification mismatch on a code claim.
