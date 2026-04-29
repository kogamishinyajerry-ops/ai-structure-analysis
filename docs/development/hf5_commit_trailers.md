# HF5 Commit Trailer Check

HF5 requires each Codex-authored commit to carry audit trailers that
bind the commit to execution, self-verification, and Linear state.

Required trailers:

```text
Execution-by: codex-gpt-5.4-xhigh
Self-verified: <CLAIM-ID>@<sha> (fresh-subtask <subtask-id>)
Linear-issue: ENG-<n>
```

Optional decision trailer:

```text
Linear-decision: <ENG-* / ADR-* / DEC-*>
```

## Local Hook

Install both hooks:

```bash
pre-commit install --hook-type pre-commit --hook-type commit-msg
```

The `commit-msg` hook runs:

```bash
python3 scripts/hf5_commit_trailer_check.py --message-file .git/COMMIT_EDITMSG
```

## PR-Range Check

Before opening or updating a PR, run:

```bash
python scripts/hf5_commit_trailer_check.py --from-ref origin/main
```

This validates every commit in `merge-base(origin/main, HEAD)..HEAD`.
It is a local check path for ENG-16 and does not by itself move a
Linear issue through Pending Review.
