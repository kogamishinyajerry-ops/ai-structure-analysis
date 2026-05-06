# ADR-013: Branch protection enforcement for the calibration cap

- **Status:** Accepted
- **Decider:** T0 / Opus 4.7 Architecture Gate (CFDJerry) per AR-2026-04-25-001
- **Date:** 2026-04-25
- **Related:** ADR-011 (parent), ADR-012 (calibration math — sibling), DEC-T0-2026-04-25-001 (Notion record)
- **Branch:** `feature/AI-FEA-ADR-013-branch-protection`
- **Repo-tier prerequisite:** repo must be **public** OR on **GitHub Pro** (required for branch protection + rulesets API). Repo was flipped from private→public on 2026-04-25 to satisfy this.

---

## Context

ADR-012 defines a *calibration ceiling* (mechanical, derived from rolling 5-PR Codex R1 outcomes). That math is meaningless if T1 can self-merge under any ceiling — including 30%/BLOCKING. Session 2026-04-25 demonstrated empirically that T1 wrote `95%` self-estimates five times in a row while Codex was actively returning CHANGES_REQUIRED on each PR. The honor-system has zero enforcement surface; the calibration cap needs a wrapper that physically prevents T1 from merging when the gate is BLOCKING and that surfaces the gate's claim-vs-ceiling check on every PR.

ADR-013 is that wrapper.

## Decision

Enforce ADR-012's gate via three concentric layers:

### Layer 1 — PR template (`.github/PULL_REQUEST_TEMPLATE.md`)

Every PR is opened from a template that:

- Reserves a section labeled `## Self-pass-rate (mechanically derived)`.
- Instructs the author to fill it from `python3 scripts/compute_calibration_cap.py`'s output, **never from intuition**.
- Forces the author to tick exactly one Codex pre-merge gate level (BLOCKING / MANDATORY / RECOMMENDED / OPTIONAL).
- Forces the author to tick any ADR-011 §T2 M1-M5 mandatory triggers that fire (independent override).
- Includes a `## Test plan` section validated by reviewers.

The template is only a *prompt*; the actual enforcement is in Layer 2.

### Layer 2 — CI workflows

#### Calibration cap check (`.github/workflows/calibration-cap-check.yml`)

Triggered on every `pull_request` event (`opened` / `edited` / `synchronize` / `reopened`):

1. Computes the current ceiling via `compute_calibration_cap.py`.
2. Extracts the claimed ceiling from the PR body via `scripts/extract_pr_self_pass_rate.py`.
3. Runs `compute_calibration_cap.py --check <claim>` — exits non-zero if the claim exceeds the ceiling.

Result: a PR whose body claims 80% while the formula says 30% fails CI. The author cannot fix this by editing the body to a higher number — only by either correcting downward to ≤ ceiling or by adding R1=APPROVE entries to `calibration_state.json` (which requires merging clean PRs first, which require Codex review, which is the whole point).

#### HF5 trailer check (`.github/workflows/trailer-check.yml`)

FF-07 adds a `pull_request_target` workflow that runs from trusted `main`, checks out the PR head as git data only, and runs `scripts/check_commit_trailers.py` from trusted `main`. It validates:

1. `Execution-by: codex-primary` presence and exact value.
2. `Linear-Issue: ENG-<id>` presence and format.
3. `Reviewed-by: claude-opus47 APPROVE <proof-ref>` when the trusted calibration state says review is mandatory.
4. `Codex-verified: <claim-id>@<7-40 hex sha>` presence and format for the HF5 claim-proof path.

This is intentionally prospective: the FF-07 bootstrap PR lands the workflow and validator, then the trusted-main workflow applies to subsequent PRs.

#### HF3 golden-sample registry check (`.github/workflows/golden-samples-validation.yml`)

FF-08 adds a `pull_request_target` workflow that runs from trusted `main`,
checks out the PR head only as untrusted sample data, and runs
`scripts/validate_golden_samples.py` from trusted `main`. It validates:

1. Signed sample directories are exactly `golden_samples/GS-###/`.
2. Smoke/demo fixtures such as `GS-100-radioss-smoke` and
   `GS-101-demo-unsigned` are excluded from signed-registry validation.
3. Every signed sample has `README.md`, `expected_results.json`, matching
   `case_id`, non-empty `case_name` / `analysis_type`, a valid `status`, and
   at least one `.inp` or theory `.py` evidence artifact.
4. Samples marked `insufficient_evidence` carry a `FP-###`
   `failure_pattern_ref` and non-empty `status_reason`.

This workflow is deliberately not path-filtered. Once it is a required status
check, a skipped required workflow would either block unrelated PRs or fail to
protect sample-registry changes.

### Layer 3 — GitHub branch protection (`scripts/apply_branch_protection.sh`)

A protection ruleset on `main` requires:

- **`required_status_checks`** = `["lint-and-test (3.11)", "calibration-cap-check", "trailer-check", "golden-samples-validation"]` with `strict: true` (PR must be up-to-date with main before merge).
- **`required_linear_history`** = `true` — squash-only style, no merge commits.
- **`allow_force_pushes`** = `false`, **`allow_deletions`** = `false` — protect against accidental destruction of main.
- **`required_conversation_resolution`** = `true` — Codex review threads must be resolved.
- **`enforce_admins`** = `false` — T0 (the human admin) retains emergency override. Justification: solo-developer setup; without admin override, any CI infrastructure breakage would brick the repo. ADR-013's discipline is procedural, not coercive at the admin level.
- **`required_pull_request_reviews`** = `null` — solo-dev; Codex (via the M1-M5 + ceiling gate) is the de facto reviewer rather than a human approver. Adding a human-required-review on a single-author repo would just stamp the author's own approvals.

### Discipline binding (T1 contract)

The gate cannot mechanically prevent admin-bypass merges by T1 acting through the user's authenticated `gh` CLI. This residual loophole is closed by **discipline**:

> **T1 must NOT merge a PR while its ceiling-derived gate is BLOCKING (30%) unless either:**
> **(a) Codex Round 1 returned `APPROVE` (or `APPROVE_WITH_NITS` with all nits resolved) on the latest commit, OR**
> **(b) T0 (the human) explicitly authorizes the merge in writing in the conversation, citing the BLOCKING state.**

Any T1 merge that violates this contract is a P0 procedural failure and triggers a retro entry per RETRO cadence rules. Layer 1 + 2 surface the BLOCKING state in CI and PR template so T1 cannot plausibly miss it; Layer 3 makes the merge *physically possible* only via deliberate admin-bypass *that T1 has no business invoking*.

## Implementation contract

| File | Purpose |
|---|---|
| `.github/PULL_REQUEST_TEMPLATE.md` | Layer 1 — PR template |
| `.github/workflows/calibration-cap-check.yml` | Layer 2 — CI claim-vs-ceiling check |
| `.github/workflows/trailer-check.yml` | Layer 2 — HF5 commit-trailer check |
| `.github/workflows/golden-samples-validation.yml` | Layer 2 — HF3 golden-sample registry check |
| `scripts/extract_pr_self_pass_rate.py` | Layer 2 — PR body parser (16 unit tests) |
| `scripts/check_commit_trailers.py` | Layer 2 — trusted commit-trailer validator |
| `scripts/validate_golden_samples.py` | Layer 2 — trusted signed sample-registry validator |
| `scripts/apply_branch_protection.sh` | Layer 3 — idempotent protection setup |
| `docs/adr/ADR-013-branch-protection-enforcement.md` | This doc |

## Activation sequence

1. **Land this PR via Codex R1=APPROVE.** Layers 1 and 2 take effect on merge (template applies to subsequent PRs; CI workflow runs on subsequent PRs).
2. **T0 runs** `bash scripts/apply_branch_protection.sh` once after merge. Layer 3 takes effect immediately; from this moment forward, no merge to main can land without `lint-and-test (3.11)` + `calibration-cap-check` + `trailer-check` + `golden-samples-validation` all green.
3. **Subsequent PRs** open from the new template; the calibration-cap-check, trailer-check, and golden-samples-validation workflows validate each automatically.

The bootstrap PR for ADR-013 itself (this PR) is NOT subject to Layer 2 yet because the workflow file lands as part of this PR — GitHub doesn't run workflow files that don't exist on the base branch yet. ADR-012's PR (#24) is also NOT subject to Layer 2 for the same reason. **Both PRs land under Layer 0 (no enforcement) but are required by ADR-012/AR-2026-04-25-001 §1 to reach Codex R1=APPROVE before merge** — the discipline binding above applies retroactively to the same session that authored these ADRs.

The FF-08 `golden-samples-validation` addition follows the same prospective
pattern: the workflow and trusted validator land first, then
`scripts/apply_branch_protection.sh` is rerun so subsequent PRs must satisfy the
new HF3 status check.

## Consequences

**Intended:**

- T1's mechanical ceiling becomes physically enforced at PR-merge time once Layer 3 is on. HF5 trailer discipline is physically enforced for PR commits before merge; the final squash commit remains a merge-operator responsibility.
- Layer 1 + 2 produce a clear paper trail: every PR body declares a ceiling; CI validates it; every PR commit carries execution/work-control/review/claim trailers where required; the PR template carries the merge-trailer block that must be used for the squash commit.
- Layer 3 prevents accidental force-push or deletion of main (defense against the same class of error that produced PR #20's revert).
- The discipline binding turns the residual admin-bypass into a documented retro-eligible event rather than a silent loophole.

**Acknowledged:**

- `enforce_admins: false` means a determined or careless admin can bypass everything. This is a deliberate trade-off for solo-dev recoverability; revisit if/when the project grows to multi-author.
- Layer 3 doesn't run until after this PR merges (chicken-and-egg). The first two ADR PRs (#24 and this one) ride on Layer 0 = nothing. ADR-012/013 is therefore a *prospective* gate, not retroactive.
- The CI check uses GitHub's `pull_request.body` field, which can be edited freely. An author could in principle merge a PR, then edit the body to game future tooling. The state file (Layer 0 of ADR-012) is the actual source of truth, not the body claim. The body claim is just a checksum.
- Repo had to be made public to access protection APIs on the free tier. Future-proof: if the project ever needs to go private again, options are (a) GitHub Pro, (b) move to GitLab (free private branch protection), (c) drop Layer 3 and rely on Layer 1 + 2 + discipline alone.

**Out of scope:**

- Multi-reviewer / CODEOWNERS enforcement (single-author repo, no value yet).
- Signed-commit requirements (would block T1's automated commits without GPG keypair setup).
- Blocking direct push to feature branches (low value; force-push protection on main is enough).

## Open follow-ups

- After 10 post-ADR-013 PRs, audit: did the `calibration-cap-check` job ever fail? Did it ever falsely pass? Sample 3 PR bodies to confirm the template was followed.
- Consider extending the workflow to also scrape ADR-011 §T2 M1-M5 checkboxes; if any is ticked, require a `Codex-Approved-By:` trailer in the merge commit.
- If a future PR rewords the `Self-pass-rate` heading, add a heading-rename safety check to `extract_pr_self_pass_rate.py` (currently tolerates `Self-pass-rate` and `Self pass rate` only).
