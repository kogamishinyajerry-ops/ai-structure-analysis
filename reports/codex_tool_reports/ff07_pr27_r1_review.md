# Codex R1 — PR #27 (FF-07 HF5 commit-trailer enforcement)

- **Branch**: `feature/AI-FEA-FF-07-trailer-check`
- **Head SHA**: `a5e22bd` (against `origin/main = a254a23`)
- **Reviewer**: Codex via 86gs `gpt-5.4 (xhigh)` — `codex-relay` exec mode (governance baseline)
- **Reviewed at**: 2026-05-03
- **Risk-tier triggers HIT**: M1 (`.github/workflows/**` HF1.9 hard-stop zone) + M3 (claims HF5 enforcement) + M4 (governance text → mechanical enforcement translation)
- **Diff size**: 512 lines / 3 new files

## Verdict

**BLOCKER**

## Findings

### BLOCKER

1. **`scripts/check_commit_trailers.py:49`** — Any `Co-Authored-By:` line satisfies execution attribution, so a commit can pass HF5 with `Co-Authored-By: Alice <a@x>` and no evidence that T1/Claude executed it. ADR-011's compromise only justifies the specific Claude alias, not arbitrary coauthors.
   - **Suggested fix**: keep `Execution-by:` as the canonical path and, if the compromise remains, only accept an explicit allowlist of Claude/T1 `Co-Authored-By` identities.

2. **`scripts/check_commit_trailers.py:57`** — Trailer detection is a multiline regex over the entire commit body rather than a parse of the final trailer block, so quoted prose or pasted email text containing `Execution-by:` / `Codex-verified:` can spoof compliance without real trailers.
   - **Suggested fix**: parse trailers with git's trailer semantics (`git interpret-trailers --parse` or equivalent) and only evaluate the terminal trailer block, including continuation-line handling.

3. **`.github/workflows/trailer-check.yml:19`** — The workflow checks out the PR's own tree and runs `python3 scripts/check_commit_trailers.py` from that untrusted checkout, so a PR can weaken the validator and self-green the HF5 gate. This is exactly the self-bypass class that `calibration-cap-check.yml` hardens against by using a trusted `main` checkout.
   - **Suggested fix**: checkout trusted `main` into a separate path, run the validator from there, and inspect the PR commit range as untrusted input only.

### HIGH

4. **`scripts/check_commit_trailers.py:61`** — `_CODEX_VALUE_RE` accepts `@HEAD` and `@<sha>`, which widens ADR-011's documented `Codex-verified: <claim-id>@<sha>` contract to mutable or unresolved refs and weakens the audit trail HF5 is supposed to pin to a specific reviewed commit.
   - **Suggested fix**: require a 7-40 hex SHA after `@`; if placeholder SHA support is desired, amend ADR-011 first and then update code/tests in lockstep.

5. **`scripts/apply_branch_protection.sh:27`** — ADR-013's branch-protection script still requires only `lint-and-test (3.11)` and `calibration-cap-check`, so this new `trailer-check` job would not actually be a required merge gate on `main` after landing.
   - **Suggested fix**: add `trailer-check` to the required status-check contexts and update the ADR-013 implementation contract accordingly.

### MEDIUM

6. **`tests/test_check_commit_trailers.py:143`** — The test suite codifies arbitrary `Co-Authored-By` acceptance and never exercises the main adversarial cases here: quoted body text that looks like trailers, non-terminal footer text, and trailer continuation/malformed-block parsing.
   - **Suggested fix**: replace the generic coauthor case with an allowlisted Claude alias case and add negative tests for spoofed body text and trailer-block edge cases.

## Overall risk

As written, FF-07 can be self-bypassed and can accept spoofed or non-authoritative trailer data, so merging it would overstate HF5 enforcement on an HF1.9 governance surface.

## Calibration entry (post-merge backfill target)

Until R1 → R2 → APPROVE arc completes, this PR's R1 outcome is `BLOCKER`. Per outcome canon, BLOCKER counts as CHANGES_REQUIRED.

```json
{
  "pr": 27,
  "sha": "<merge-commit-sha-tbd>",
  "title": "[FF-07] CI commit-trailer presence + claim-id format check (HF5)",
  "merged_at": "<TBD>",
  "r1_outcome": "BLOCKER",
  "r1_severity": "3 BLOCKER + 2 HIGH + 1 MEDIUM",
  "r1_review_report": "reports/codex_tool_reports/ff07_pr27_r1_review.md",
  "notes": "First independent Codex review on FF-07 (2026-05-03 R1). Surfaces 3 self-bypass classes: arbitrary Co-Authored-By acceptance, regex-over-body-text trailer parsing, and PR-controlled validator checkout. Pre-merge fix arc required before merge."
}
```

## Recommended next-action sequence

1. Apply BLOCKER #3 fix first (workflow trusted-main checkout) — most mechanical, mirrors the `calibration-cap-check.yml` R2 hardening pattern verbatim.
2. Apply BLOCKER #2 fix (use `git interpret-trailers --parse`) + BLOCKER #1 fix (Claude-alias allowlist for `Co-Authored-By`).
3. Apply HIGH #4 + #5 (regex tightening + branch protection script update).
4. Rewrite the test suite per MEDIUM #6 — adversarial cases are required, not optional.
5. Re-run Codex R2.

This is multi-hour governance code work, not a quick fix.
