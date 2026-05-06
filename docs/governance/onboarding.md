# Onboarding

> **Audience:** human contributors and AI agents entering AI-Structure-FEA after
> the Codex-primary Linear/Symphony governance pivot.

## Read First

1. `AGENTS.md` for repo-local operating rules.
2. `README.md` for quick setup and rule summary.
3. `docs/adr/ADR-011-pivot-claude-code-takeover.md` for role authority, truth hierarchy, HF rules, Golden Rules, and commit trailers.
4. `docs/adr/ADR-012-calibration-cap-for-t1-self-pass-rate.md` for mechanical self-pass-rate.
5. `docs/adr/ADR-013-branch-protection-enforcement.md` for PR template, CI gates, and branch protection.
6. `docs/adr/ADR-023-lean-validation-workflow.md` for the fast development lanes and signed-claim boundary.
7. `docs/governance/routing.md` for the short operational routing map.
8. `.planning/STATE.md` for current phase status, PR ledger, and carry-overs.

## Local Setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,agents]"
pre-commit install
```

Use the repository `.venv` when running broad checks; the system Python may not
have project dependencies installed.

## Standard Checks

```bash
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m pytest -q
python3 scripts/compute_calibration_cap.py --human
python3 scripts/check_commit_trailers.py --range main..HEAD --require-reviewed-by --require-codex-verified
python3 scripts/validate_golden_samples.py
```

Run the closest relevant subset when a full suite is not appropriate, but say so
in the PR and proof comments.

## Before Opening A PR

1. Confirm the Linear issue or explicit user scope.
2. Check the current calibration ceiling:

   ```bash
   python3 scripts/compute_calibration_cap.py --human
   ```

3. Identify ADR-011 M1-M5 triggers honestly.
4. Prepare reviewer/auditor evidence when review is mandatory.
5. If reviewer evidence is mandatory, invoke local Claude Opus 4.7 in read-only
   mode when available; do not stop only to ask whether reviewer invocation is
   allowed.
6. Name the validation lane: Tier 0 sandbox/demo, Tier 1 engineering candidate,
   or Tier 2 signed validation.
7. Make sure commits include the required trailers:

   ```text
   Execution-by: codex-primary
   Codex-verified: <claim-id>@<7-40 hex sha>
   Reviewed-by: claude-opus47 APPROVE <proof-ref>
   Linear-Issue: ENG-<id>
   ```

## File Map

| Path | Meaning |
|---|---|
| `agents/`, `tools/`, `schemas/` | Core execution and schema surfaces. Some files are HF1 hard-stop paths. |
| `backend/` | Workbench, report, and well-harness application code. |
| `golden_samples/` | Read-only validation and fixture inputs unless a signed issue explicitly authorizes changes. |
| `.github/workflows/` | CI enforcement surface; changes require review and HF1 override discipline where applicable. |
| `scripts/` | Governance and utility scripts, including branch protection, trailer checks, calibration, and golden-sample validation. |
| `docs/adr/` | Architecture Decision Records; canonical governance text. |
| `docs/governance/` | Operational pointers and onboarding, subordinate to ADRs. |
| `docs/failure_patterns/` | Empirical failure-pattern records. |
| `.planning/STATE.md` | Repo-side execution snapshot, updated in the same PR as status-changing work. |
| `reports/codex_tool_reports/` | Reviewer/auditor evidence artifacts. |

## Validation Lanes

| Lane | Fast rule | Hard stop |
|---|---|---|
| Tier 0 — Sandbox / Demo | Iterate quickly with local verification and clear `demo-only` / `software-path evidence only` labels. | Do not imply validated physics, benchmark agreement, or signed evidence. |
| Tier 1 — Engineering Candidate | Capture a compact manifest: deck/model provenance, solver logs, units/material/BC/contact assumptions, hashes, and limitations. | Do not promote to signed validation without benchmark and signoff. |
| Tier 2 — Signed Validation | Use the strict gate: benchmark, metrics, tolerance, convergence, manifest, independent review/signoff. | Stop if benchmark/material/source evidence is missing. |

## Common Mistakes

- Treating Notion as code truth instead of a mirror.
- Reusing old Claude Code / Apex / Antigravity ownership language.
- Opening a PR with a guessed self-pass-rate.
- Leaking local absolute paths, secrets, raw env dumps, or machine-only
  credentials into review/proof artifacts.
- Forgetting that `golden-samples-validation` is required on `main`.
- Editing `golden_samples/**` without a signed validation issue.
- Closing, merging, transitioning Linear state, or mutating Notion without dry-run
  payload and explicit confirmation.
- Creating large validation packets for Tier 0 demos when a clear label and
  local verification would be sufficient.

## Self-Test

You are ready to contribute when you can answer:

1. Which surface is code truth?
2. Which surface is work-control truth?
3. What is Claude Opus allowed to do by default?
4. Which command computes the self-pass-rate ceiling?
5. Which four status checks are required on `main`?
6. What happens to unsigned or indefensible golden samples?
7. Which validation lane allows fast demo iteration, and which lane is required
   for signed physical claims?

Answers:

1. GitHub/repo.
2. Linear `Engineering`.
3. Review/audit prepared packets or diffs, automatically when required and
   available; not default execution.
4. `python3 scripts/compute_calibration_cap.py --human`.
5. `lint-and-test (3.11)`, `calibration-cap-check`, `trailer-check`, and `golden-samples-validation`.
6. They are marked or treated as `insufficient_evidence` and excluded from regression evidence.
7. Tier 0 allows fast demo iteration; Tier 2 is required for signed physical
   claims.
