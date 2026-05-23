# Phase 38 A — Codex risk-tier review evidence

**Case:** `golden_samples/nafems-le10-thick-plate-candidate/` (NAFEMS LE10 thick-plate-pressure published reference, analytical-only)
**Architecture:** ADR-026 dual-engine — Opus 主驱动 + Codex relay risk-tier review (round cap = 3)
**Backend:** 86gs `gpt-5.4` xhigh (`codex-review-relay --uncommitted`)
**Risk-tier triggers hit:** `golden_samples/**` boundary + claim-tier semantics
**Date:** 2026-05-24

## R0 — 2 findings, both FIXED

- **[P1] Phase 35 B verdict-cohort pin would break.** Adding a 13th
  `*-candidate/cross_check_verdict.yaml` with `solver_kind: linear_static` would
  make `test_phase35b_verdict_yaml_solver_kind_backfill.py::
  test_solver_kind_distribution_matches_phase35_backfill` see 13 files / 6th
  `linear_static` while it pins the 12-case histogram → suite fails.
  **Fix (Opus alternative to Codex's "update the pin" suggestion):** renamed the
  artifact `cross_check_verdict.yaml` → **`published_reference.yaml`**. This case
  is a *reference*, not a *verdict* (no observed value, no residual, no
  cross-check), so it should not be in the verdict cohort at all. Renaming keeps
  it out of the Phase 35 B glob (no prior-phase pin edit → respects the
  additive-only constraint) AND is more honest. Verified: 128 tests pass incl.
  the full Phase 35 B suite.

- **[P2] LE10 stress sign.** Recorded `target_value_pa = +5.38e6` (magnitude) but
  the published σ_yy at point D is compressive (`-5.38e6` per blueprint). A future
  Phase 41-43 signed residual check would see a correct compressive result as a
  ~200% miss. **Fix:** recorded the signed value `-5.38e6` + added
  `target_sign_convention` documenting that the magnitude is cross-confirmed and
  the sign follows the blueprint convention pending primary-source verification.

## R1 — 2 findings, both addressed by scoping/reasoning (no code change)

- **[P1] `reports/snapshots/2026-05-16T...` self-contradictory.** Out of scope:
  these are **pre-existing untracked files** (timestamp 8 days before this work),
  swept into the review by `--uncommitted`. `git status` confirms they are not
  staged. The Phase 38 A commit includes only the 3 staged artifacts; the stale
  snapshot clutter is a separate cleanup item, not a 38 A change.

- **[P2] New case not in `FALLBACK_CANDIDATE_CASES`.** Pre-existing graceful
  design, not a new defect. `/candidate-cases` globs all `*-candidate/` dirs;
  `FALLBACK_CANDIDATE_CASES` is a **curated 7-case subset** that already excludes
  ~6 existing cohort cases (euler-column, plate-ss-shell, both modal cases,
  cantilever-buckle, hertz-contact, heat-transfer). `findCandidateCase` returns
  `null` gracefully for any live-only case (no crash). The nafems case matches
  those 6 peers' exact treatment; adding only it to the fallback would be the
  *inconsistent* choice. Fallback curation, if desired, is a dedicated frontend
  slice covering all live-only cases together.

## Verdict

R0 surfaced two real correctness issues (both fixed). R1 surfaced one
out-of-scope clutter item and one pre-existing-design observation (neither a
38 A defect). Committing at R1 with documented reasoning — no R2 needed (no
further code change to re-review). Round cap = 3 respected; deliberately not
spiraling (cf. the cylinder-pv 22-round anti-pattern).
