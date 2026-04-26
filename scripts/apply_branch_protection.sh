#!/usr/bin/env bash
# ADR-013: applies the protection ruleset to main.
#
# Idempotent — re-running with the same settings is a no-op.
# Requires: `gh` authenticated as a user with admin permission on the repo.
#
# Settings rationale (see ADR-013 §"Protection ruleset"):
# - required_status_checks: lint-and-test (3.11) + calibration-cap-check
# - enforce_admins: false        (T0 retains emergency override)
# - required_pull_request_reviews: null  (solo-dev — Codex is the de facto reviewer)
# - allow_force_pushes: false
# - allow_deletions: false
# - required_linear_history: true        (squash-only style)
# - lock_branch: false
# - required_conversation_resolution: true

set -euo pipefail

REPO="${1:-kogamishinyajerry-ops/ai-structure-analysis}"
BRANCH="${2:-main}"

echo "Applying branch protection to $REPO:$BRANCH ..."

gh api -X PUT "repos/$REPO/branches/$BRANCH/protection" \
  --input - <<'JSON'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["lint-and-test (3.11)", "calibration-cap-check"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": true,
  "lock_branch": false,
  "allow_fork_syncing": true
}
JSON

echo
echo "Protection applied. Verifying..."
gh api "repos/$REPO/branches/$BRANCH/protection" \
  --jq '{checks: .required_status_checks.contexts, enforce_admins: .enforce_admins.enabled, linear: .required_linear_history.enabled, force_push: .allow_force_pushes.enabled, deletions: .allow_deletions.enabled}'
