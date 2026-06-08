# Phase 9 D — TAA report

**Slice author commit:** `985b528`

**Verdict:** APPROVE
**Test count:** 22 (≥14 required)
**Test pass:** 22 / 22
**Full-suite pass:** 1824 / 1824 (+8 skipped)

## Per-axis evidence

- **B (12 / 12)** — `COHORT_TREND_ANOMALIES_SCHEMA_VERSION = "1.0.0"` with full rationale block (orthogonality to Phase 8 E, severity buckets, point-count floor, "Closes Phase 8 retrospective carry-forward §4").
- **M (12 / 12)** — Named thresholds pinned exactly (-0.5 / -1.5 / -3.0); `TREND_MIN_POINTS = 3`; `TREND_AXES` matches `ANOMALY_AXES` byte-for-byte (cross-module lock-step); `_TREND_AXIS_ATTRIBUTE` dict keys = `set(TREND_AXES)`. UTC-only.
- **T (15 / 15)** — 22 tests independently rerun 22/22 in 0.92s. Severity pins at exact threshold values. Every firing test has opposite-direction negative control (flat + ascending).
- **C (12 / 12)** — `_ENVELOPE_FORBIDDEN_TOKENS` is the 4-token list; trap avoided. Tier 1 disclaimer trio pinned.
- **A (8 / 8)** — Two distinct negative controls (flat AND ascending). Firing gate refuses event for `slope > -0.5`. `_least_squares_slope` handles degenerate denominator by returning 0.0.
- **E (8 / 8)** — Engineered 5-snapshot timeline fires danger; HTTP endpoint surface pin.
- **V (13 / 13)** — Cohesive slice. Orthogonality documented at module-doc + schema-stamp level. Closed-form least-squares correct.

## Findings

No HIGH / MEDIUM / LOW findings.

(Minor positive note: `test_mild_descent_fires_info_not_danger` is correctly conditional — if the event fires it must be info — because exact weighted slope depends on Phase 6 D trust-score weighting.)

## Cumulative slice D axes

B + M + T + C + A + E + V = 12 + 12 + 15 + 12 + 8 + 8 + 13 = **80 / 80** (D + X omitted per blueprint)
