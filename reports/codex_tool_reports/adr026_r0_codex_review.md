# Codex Relay Review — ADR-026 Dev-Team Architecture Realignment (R0)

- **Date:** 2026-05-24
- **Backend:** 86gs `gpt-5.4` (xhigh)
- **Command:** `codex review --uncommitted` (DOGFOOD — first Codex relay activation on this repo)
- **Scope reviewed:** full uncommitted tree; architecture package = ADR-026 + CLAUDE.md + AGENTS.md + `.claude/agents/*`
- **Verdict:** CHANGES_REQUIRED (1 × P1 out-of-scope + 2 × P2 in-scope)
- **Satisfies:** AGENTS.md "repo-level policy changes need explicit review evidence"

## Findings

### [P1] cylinder-pv-candidate metadata vs `_claim_tier.py` mismatch — OUT OF SCOPE
`golden_samples/cylinder-pv-candidate/expected_results.json:6-9` labels the case
Tier 1 engineering candidate (Tier 2 deferred), but
`backend/app/services/reporting/_claim_tier.py` promotes it to `tier_2_validated`
when `cross_check_verdict.yaml` is PASS (current repo state). Code paths reading
`expected_results.json` verbatim (`backend/app/api/routes/cases.py`, candidate-report
spine) would surface stale Tier 1 text. **Not part of this architecture change** —
pre-existing untracked file, swept in by `--uncommitted`. Flagged for separate handling.

### [P2] CLAUDE.md "Established" vs ADR-026 Proposed — FIXED
CLAUDE.md stated the architecture was "Established by ADR-026" while ADR-026 is still
`Proposed`; future sessions would adopt the new governance path before the review gate
and ratification. **Fixed:** CLAUDE.md now states "Proposed by ADR-026, Status: Proposed
— NOT yet in force; ADR-011 Codex-primary governance remains authoritative until ratify."

### [P2] AGENTS.md golden_samples blanket read-only vs HF1.7b carve-out — FIXED
AGENTS.md Code Boundaries declared a blanket `golden_samples/** read-only` rule,
contradicting HF1.7b (`*-candidate` writable, per ADR-011 AR-2026-05-16, pinned by
`tests/test_hf1_path_guard_candidate_carveout.py`). As the Codex-facing rules file,
this would make legitimate FM-04a `*-candidate` updates look forbidden. **Fixed:**
AGENTS.md now distinguishes signed-registry hard-stop vs `*-candidate` carve-out,
aligned with CLAUDE.md and ADR-011.

## Dogfood outcome

First Codex relay activation on this repo succeeded (Layer 1 dual-engine validated).
The independent review caught 2 real in-scope consistency defects + 1 out-of-scope bug
that Opus self-review had missed. Round cap = 3: R0 findings addressed (2 fixed inline,
1 deferred out-of-scope). No R1 needed — the remaining P1 is out-of-scope, and the
in-scope architecture package is internally consistent post-fix. (A clean R1 would
require excluding the unrelated `cylinder-pv-candidate` untracked file, which
`--uncommitted` cannot scope out.)
