# FF-09 README / Governance Sync Claude Audit

- **Reviewer:** local Claude Opus 4.7
- **Mode:** reviewer/auditor only, tools disabled
- **Command:** `claude --model opus --tools "" --no-session-persistence`
- **Verdict:** `APPROVE`
- **Scope:** README / ADR-011 / `docs/governance/` sync after FF-07 and FF-08 landed.

## Reviewer Result

Claude Opus returned `APPROVE` with no required changes.

The reviewer confirmed that:

- the truth hierarchy is consistent: GitHub/repo is code truth, Linear
  `Engineering` is work-control truth, and Notion is a mirror after repo and
  Linear settle;
- Codex is consistently described as primary implementation agent;
- local Claude Opus 4.7 is consistently described as reviewer/auditor, not
  default executor or repo owner;
- Antigravity, Apex, and Claude-direct ownership are banned as default routes;
- the four required `main` checks are listed correctly:
  `lint-and-test (3.11)`, `calibration-cap-check`, `trailer-check`, and
  `golden-samples-validation`;
- README is correctly subordinate to ADR-011 / ADR-012 / ADR-013;
- ADR-011 now accurately reflects FF-07 and FF-08 landing and narrows residual
  maturity gaps to HF2 and HF4;
- `docs/governance/routing.md` and `docs/governance/onboarding.md` introduce no
  role-language or truth-hierarchy drift.

## Verification Evidence Provided

- `.venv/bin/ruff check .`
- `.venv/bin/ruff format --check .`
- `python3 scripts/validate_golden_samples.py`
- `.venv/bin/python -m pytest -q tests/test_validate_golden_samples.py tests/test_check_commit_trailers.py tests/test_compute_calibration_cap.py`
- `.venv/bin/python -m pytest -q`

## Optional Nits Checked

- `pyproject.toml` defines both `dev` and `agents` extras used by
  `docs/governance/onboarding.md`.
- `scripts/check_commit_trailers.py` supports the documented
  `--require-reviewed-by` and `--require-codex-verified` flags.
