# Phase 9 F — TAA report

**Slice author commit:** `6a18d4f`

**Verdict:** APPROVE
**Integration test count:** 16 (≥16 required)
**E2E test count:** 3 (≥3 required)
**All Phase 9 F tests pass:** 19 / 19
**Full-suite pass:** 1843 / 1843 (+8 skipped)

## Per-axis evidence

- **T (15 / 15)** — 16 integration + 3 E2E = 19 functions matching blueprint §3.F floor exactly. ASGITransport real, no mocks. Orthogonality genuine.
- **C (12 / 12)** — Tier 1 disclaimer trio asserted in all 3 E2E bodies; Tier-2 verb refusal HTTP-422 + signed-registry refusal HTTP-422 + forbidden-claim notes HTTP-422 + disclaimer-form notes accepted.
- **E (8 / 8)** — Every E2E composes ≥3 phase surfaces. Orthogonality proved in BOTH integration F.4 AND E2E #3.
- **A (8 / 8)** — `_SyncASGIClient.post` uses real ASGITransport; `fake_repo` only monkeypatches `_repo_root` lambdas (filesystem isolation, not route mocks).
- **V (13 / 13)** — Independent verification: ran slice (1.03s) + full sweep (18.36s) + read both files (467+312 lines) + grep'd `def test_` count + traced orthogonality + traced disclaimer trio across all E2E.

## Findings

- **LOW (cosmetic)** — E2E #1 disclaimer trio assertion stringifies dict bodies via `json.dumps`. Works because route handlers serialize verbatim; a future schema change nesting disclaimers under non-ASCII keys could silently false-negative.
- **LOW (cosmetic)** — `test_post_signoff_propagates_to_cohort_executive_summary` intentionally does NOT pin `starting_bucket` (honest because trust-score sum is multi-axis); comment-only justification means a future axis-weight refactor could silently weaken this test.

No HIGH or MEDIUM findings.

## Cumulative slice F axes

T + C + E + A + V = 15 + 12 + 8 + 8 + 13 = **56 / 56** (B + M + X + D omitted per slice scope)
