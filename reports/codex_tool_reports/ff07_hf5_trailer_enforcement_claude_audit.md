# Claude Opus Audit — FF-07 / ENG-16 HF5 Commit-Trailer Enforcement

- Command: `claude --model opus --tools "" --no-session-persistence`
- Input: `reports/codex_tool_reports/ff07_hf5_trailer_enforcement_packet.md` + staged diff
- Result: `APPROVE`

## Verdict: APPROVE

### Evidence

**#27 R1 blocker classes — all closed:**

- *Arbitrary `Co-Authored-By` acceptance:* validator only honors `Execution-by`, `Linear-Issue`, `Reviewed-by`, `Codex-verified`; `Co-Authored-By` is irrelevant to the gate (`scripts/check_commit_trailers.py:18-23,121-167`).
- *Body-regex trailer spoofing:* trailer extraction is delegated to `git interpret-trailers --parse`, which only honors the final trailer block. `tests/test_check_commit_trailers.py:test_body_text_cannot_spoof_real_trailers` explicitly proves prose-embedded "trailers" fail.
- *PR-controlled validator checkout:* `.github/workflows/trailer-check.yml` uses `pull_request_target`, checks out `ref: main` to `trusted/`, then checks out PR head to `candidate/` with `persist-credentials: false`, and invokes `python3 ../trusted/scripts/check_commit_trailers.py`. Validator and gate computation both come from trusted main; PR head is consumed only as git data.

**`pull_request_target` does not execute untrusted code:**

- No `setup` steps from candidate, no `pip install -r candidate/...`, no PR-supplied scripts run.
- `git interpret-trailers --parse`, `rev-list`, `log` operate on git objects (data), not PR code.
- `git remote add base ... && git fetch ... base "$BASE_SHA"` uses HTTPS to the public repo without exposing the workflow token to PR-controlled refs.

**ADR/branch-protection wording matches behavior:**

- ADR-013 §Layer 2 now describes both checks; §Required files lists `trailer-check.yml` and `check_commit_trailers.py`; activation sequence requires `trailer-check` green; consequences explicitly note the squash commit is a merge-operator responsibility.
- `scripts/apply_branch_protection.sh` adds `"trailer-check"` to `required_status_checks.contexts` matching the workflow `name`/job structure.
- ADR-011 trailer schema now includes `Codex-verified: <claim-id>@<7-40 hex sha>` with placeholder prohibition aligned to validator constants.

**Residuals are honestly stated:**

- Prospective workflow (must land on main first) — acknowledged.
- Branch protection requires post-merge `apply_branch_protection.sh` run — acknowledged.
- `Codex-verified` enforces format only, not artifact existence — acknowledged as future work.
- Squash-merge commit not validated by `pull_request_target` — acknowledged with mitigation via PR-template merge-trailer block.

### Notes (non-blocking)

- The two prior advisory items are resolved: PR template uses `<verdict-or-proof-ref>` as a paste-through placeholder which the validator now explicitly rejects (`test_reviewed_by_rejects_template_placeholder`); ADR squash wording in §Consequences now distinguishes per-commit enforcement from squash-operator responsibility.
- Future-work suggestion (out of scope for FF-07): a follow-up that cross-checks `Codex-verified <claim-id>` against `reports/codex_tool_reports/<claim-id>.*` existence.
