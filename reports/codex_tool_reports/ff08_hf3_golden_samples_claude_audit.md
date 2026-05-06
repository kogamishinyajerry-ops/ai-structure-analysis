# FF-08 / HF3 Golden-Sample Registry Validation Claude Audit

- **Reviewer:** local Claude Opus 4.7
- **Mode:** reviewer/auditor only, tools disabled
- **Command:** `claude --model opus --tools "" --no-session-persistence`
- **Verdict:** `APPROVE`
- **Scope:** staged FF-08 diff for signed golden-sample registry validation and CI gate.

## Verification Evidence Provided To Reviewer

- `python3 scripts/validate_golden_samples.py`
- `.venv/bin/python -m pytest -q tests/test_validate_golden_samples.py tests/test_check_commit_trailers.py tests/test_compute_calibration_cap.py`
- `.venv/bin/ruff check .`
- `.venv/bin/ruff format --check .`
- `.venv/bin/python -m pytest -q`

## Reviewer Findings

Claude Opus returned `APPROVE` with no blocking or required-change findings.

Advisory notes:

- The workflow uses the correct trusted-main pattern: `pull_request_target`
  invokes `trusted/scripts/validate_golden_samples.py`, while the PR checkout
  is only the candidate data root and uses `persist-credentials: false`.
- The job key `golden-samples-validation` matches the branch-protection context
  added to `scripts/apply_branch_protection.sh`.
- The signed sample filter `^GS-\d{3}$` correctly excludes
  `GS-100-radioss-smoke` and `GS-101-demo-unsigned`.
- Validator coverage includes `case_id` matching, status validation,
  `insufficient_evidence` failure-pattern linkage, missing-file errors, current
  real-sample pass behavior, and CLI exit codes.
- Non-blocking observations: evidence artifact discovery is top-level only;
  `.py` suffix matching is case-sensitive; `pull-requests: read` permission is
  unused; non-UTF-8 README input would fail as a Python decode error rather
  than a structured validation message.

## Conclusion

No changes are required for FF-08 to merge.
