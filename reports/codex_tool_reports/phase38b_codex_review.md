# Phase 38 B — Codex risk-tier review evidence

**Case:** C3D6 wedge — 6th element class (real ccx, tier_2_validated)
**Architecture:** ADR-026 dual-engine — Opus 主驱动 + Codex relay risk-tier review (round cap = 3)
**Backend:** 86gs `gpt-5.4` xhigh (`codex-review-relay --uncommitted`)
**Risk-tier triggers hit:** CalculiX adapter (`inp_writer`) + new runner + `_claim_tier` registry + `golden_samples` boundary + cross-≥3-file
**Date:** 2026-05-24

## R0 — staged changes APPROVED ("internally consistent")

Codex headline: *"The staged wedge/C3D6 changes look internally consistent."*
The 38 B core (writer + runner + registry + verdict + census updates + tests)
passed review. Full backend suite: 1155 passed (10 pre-existing unrelated
failures confirmed on HEAD), 21 skipped.

## R0 findings — 2 × P2, both pre-existing untracked clutter (scoped out)

Both findings target `golden_samples/cylinder-pv-candidate/data/` — **untracked**
files (the user-flagged stale SA-516 provenance) swept into the review by
`--uncommitted`. Neither is part of the staged 38 B change set.

- **[P2] `.rad` files are mislabeled CalculiX inputs.** `data/model_00_0000.rad`
  / `model_00_0001.rad` contain `*NODE`/`*ELEMENT` (CalculiX/Abaqus), but
  `candidate_cases.py` / `case_completeness.py` / `cohort_overview.py` treat
  `model_00_000{0,1}.rad` as the canonical OpenRadioss starter/engine pair →
  cylinder-pv would falsely read as a complete Radioss fixture + gain
  deck-presence credit.

- **[P2] `data/generator.py` regeneration path broken.** Hard-codes
  `SRC = HERE / "cylinder.inp"`, which is not present → `FileNotFoundError` on
  any regeneration attempt.

**Resolution:** out of 38 B scope (untracked, not staged). These are exactly
the cylinder-pv `data/` provenance items already flagged for cleanup. Handled
as a dedicated cleanup step (remove the misleading untracked artifacts) rather
than folded into the 38 B commit. The 38 B commit contains only the 8 staged
files.

## Verdict

38 B core APPROVED at R0 (internally consistent). No R1 needed (no change to the
staged diff; both findings are pre-existing untracked clutter). The recurring
clutter noise (3rd review polluted) is being resolved by a separate untracked-
artifact cleanup so subsequent Phase 38 reviews are clean.
