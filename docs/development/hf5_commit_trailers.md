# HF5 Commit Trailer Check

FF-07 validates ADR-011 audit trailers with `scripts/check_commit_trailers.py`.
The checker parses only the final git trailer block via
`git interpret-trailers --parse`; text in the commit body cannot spoof
compliance.

Required base trailers:

```text
Execution-by: codex-primary
Linear-Issue: ENG-<id>
```

When the calibration gate or M1-M5 rules require independent review, add:

```text
Reviewed-by: claude-opus47 APPROVE <verdict-or-proof-ref>
```

For HF5 claim-proof paths, add:

```text
Codex-verified: <claim-id>@<7-40 hex sha>
```

`HEAD`, `<sha>`, `pending`, and other placeholders are rejected.

## Local Checks

Validate one commit message file:

```bash
python3 scripts/check_commit_trailers.py --message-file .git/COMMIT_EDITMSG
```

Validate a PR branch against `origin/main`:

```bash
python3 scripts/check_commit_trailers.py \
  --from-ref origin/main \
  --require-reviewed-by \
  --require-codex-verified
```

## CI Path

`.github/workflows/trailer-check.yml` runs from trusted `main` with
`pull_request_target`, checks out the PR head as git data, and runs the
trusted-main validator. The FF-07 bootstrap PR is the exception: the workflow
becomes enforceable only after the validator exists on `main` and branch
protection is updated to require `trailer-check`.
