# FF-07 / ENG-16 — HF5 Commit-Trailer Enforcement Packet

## Target

- Linear: ENG-16 `P1.5-06 · HF5 commit trailer enforcement`
- Repo task: FF-07 `CI commit-trailer presence + claim-id format check (HF5)`
- Branch: `codex/ff-07-hf5-trailer-enforcement`

## Disposition

This Codex-owned implementation supersedes the old FF-07/ENG-16 attempts:

- PR #27 is blocked by its R1 findings: arbitrary `Co-Authored-By` acceptance,
  body-regex trailer spoofing, and PR-controlled validator checkout.
- PR #117 was closed as a duplicate and only covered a local hook path.

## Implemented Controls

1. `scripts/check_commit_trailers.py`
   - Parses the final git trailer block with `git interpret-trailers --parse`.
   - Requires `Execution-by: codex-primary`.
   - Requires `Linear-Issue: ENG-<id>`.
   - Requires `Reviewed-by: claude-opus47 APPROVE <proof-ref>` when the review gate is active.
   - Requires or format-checks `Codex-verified: <claim-id>@<7-40 hex sha>`.
   - Rejects placeholders such as `HEAD`, `<sha>`, `pending`, and `todo`.
   - Rejects paste-through `Reviewed-by` template placeholders.

2. `.github/workflows/trailer-check.yml`
   - Uses `pull_request_target` so the workflow runs from trusted `main`.
   - Checks out PR head only as git data.
   - Runs the validator from trusted `main`.
   - Computes the current review gate from trusted `scripts/compute_calibration_cap.py`.

3. Local/developer surfaces
   - Adds a `commit-msg` pre-commit hook for base trailers.
   - Adds `docs/development/hf5_commit_trailers.md`.
   - Adds the required merge-trailer block to the PR template.
   - Adds `trailer-check` to `scripts/apply_branch_protection.sh` required contexts.
   - Updates ADR-011/ADR-013 wording to match the mechanical gate.

## Verification

- `uvx ruff check .` -> PASS
- `uvx ruff format --check .` -> PASS
- `python3 -m pytest tests/test_check_commit_trailers.py -q` -> 14 passed
- `python3 -m pytest tests/test_check_commit_trailers.py tests/test_hf1_path_guard.py tests/test_extract_pr_self_pass_rate.py tests/test_compute_calibration_cap.py -q` -> 170 passed
- `uv run --frozen --extra dev --extra agents python -m pytest tests/ -q` -> 1130 passed, 9 skipped, 1 warning
- `python3 scripts/compute_calibration_cap.py --check 50` -> PASS
- `ruby -e 'require "yaml"; ...' .github/workflows/trailer-check.yml .github/workflows/calibration-cap-check.yml` -> PASS
- Bad message probe with `/dev/null` -> expected FAIL with missing trailer errors
- Claude Opus audit (`claude --model opus --tools "" --no-session-persistence`) -> APPROVE, see `reports/codex_tool_reports/ff07_hf5_trailer_enforcement_claude_audit.md`

## Known Residual Gates

- The new `pull_request_target` workflow is prospective. It becomes enforceable
  only after this PR lands and the validator exists on `main`.
- Branch protection must be updated after merge by running
  `bash scripts/apply_branch_protection.sh`; this is a GitHub external mutation
  and requires a separate dry-run/confirmation gate.
- The `Codex-verified` check enforces presence and format, not proof-artifact
  existence. Cross-checking claim IDs to report files remains future work.
- Final squash merge must use merge trailers matching the PR template; CI checks
  PR commits before merge, not the not-yet-created squash commit.

## Reviewer Request

Return one of `APPROVE`, `CHANGES_REQUIRED`, or `BLOCKER`.

Focus on:

- Whether the implementation closes the three #27 R1 blocker classes.
- Whether the `pull_request_target` workflow avoids executing untrusted PR code.
- Whether ADR/branch-protection wording matches the actual gate behavior.
- Whether residual limitations are honestly stated and acceptable for FF-07.
