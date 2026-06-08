# Cohort trend anomalies — methodology

**Tier 1 engineering candidate; not signed validation; not benchmark agreement.**

This document substantiates the `cohort-trend-anomalies` HTTP surface
(`backend.app.services.reporting.cohort_trend_anomalies`). It is the
companion to `cohort_trend_slope_thresholds.md` (which pins the
severity bucket boundaries) and to `cohort_drift_attribution.md` (the
per-snapshot drift attribution view). Where `cohort-trend-anomalies`
walks each case's own timeline through time, `cohort_drift_attribution`
walks the cohort's snapshot-pair drift; the two surfaces are
**orthogonal** and answer different reviewer questions.

The explicit `claim_impact`: *"trend anomalies surface within-case
degradation over time; they do NOT diagnose root cause, validate
physics, or authorize Tier 2 promotion."*

## Two parallel slope views (Phase 9 D · Phase 17 C extension)

Every `TrendEvent` carries TWO slope values:

| Field | Units | Meaning | Cross-axis comparable? |
|---|---|---|---|
| `slope` (Phase 9 D · 1.0.0) | weighted-axis-points per snapshot | "axis loses N weighted trust-score points per snapshot" | NO |
| `percentage_delta_slope` (Phase 17 C · 1.1.0) | percent of axis ceiling per snapshot | "axis loses N% of its weight per snapshot" | YES |

The two views are **parallel**, not replacement. The raw `slope` value
is preserved verbatim post-Phase-17-C; the additive
`percentage_delta_slope` is computed server-side from the SSOT
`TRUST_AXIS_WEIGHTS` mapping (`backend.app.services.reporting.
trust_score_drift_attribution`).

## Why both surfaces are surfaced

* **Raw slope** answers "how fast is the case bleeding weighted points?"
  It is the natural unit for severity bucketing (the
  `cohort_trend_slope_thresholds.md` cells at -0.5 / -1.5 / -3.0 are in
  these units). A reviewer comparing two regressions on the SAME axis
  should consult raw slope.

* **Percentage slope** answers "how fast is the case bleeding *as a
  fraction of the axis's total weight*?" It is the natural unit for
  CROSS-AXIS comparison. A reviewer comparing a completeness regression
  to an energy_audit regression should consult percentage slope —
  otherwise the comparison is biased by axis weight (a -2.5 raw slope
  on the 50-weight completeness axis is mild; the same -2.5 raw slope
  on the 15-weight energy_audit axis is severe).

The two views agree on **sign** (a negative raw slope is a negative
percentage slope) and on **zero** (a flat axis has both 0.0). They
disagree on **magnitude proportionality** across axes — which is the
entire reason `percentage_delta_slope` exists.

## Worked example (Phase 17 C boundary test)

Synthesized 3-snapshot arc:

| Snapshot | completeness weighted | energy_audit weighted |
|---|---|---|
| snap-1 | 50 | 15 |
| snap-2 | 42 | 10 |
| snap-3 | 34 |  5 |

Least-squares slope (x = snapshot index 0/1/2):

* completeness: `slope = ((34-50) - (42-50)) / 2 ≈ -8.0` weighted-points per snapshot
* energy_audit: `slope = ((5-15) - (10-15)) / 2 = -5.0` weighted-points per snapshot

Raw slopes alone suggest "completeness is collapsing faster" (-8.0 vs
-5.0). But normalized by axis weight:

* completeness percentage_delta_slope = `-8.0 / 50 * 100.0 = -16.0`%/snap
* energy_audit percentage_delta_slope = `-5.0 / 15 * 100.0 ≈ -33.333333`%/snap

The percentage view inverts the reviewer's intuition: **energy_audit is
collapsing roughly twice as fast as completeness** when measured
against each axis's ceiling. Cross-axis comparison REQUIRES the
percentage view.

## Computation

```python
def _percentage_delta_slope(raw_slope: float, axis: str) -> float:
    if axis not in TRUST_AXIS_WEIGHTS:
        raise KeyError(f"unknown trust-score axis {axis!r}; ...")
    weight = TRUST_AXIS_WEIGHTS[axis]
    return round((raw_slope / weight) * 100.0, 6)
```

The helper imports `TRUST_AXIS_WEIGHTS` from the Phase 15 C SSOT —
**no inline weight constants** (anti-gaming guard M:-2 from the
Phase 17 binding rubric). If a future axis lands in
`TRUST_AXIS_WEIGHTS`, `_percentage_delta_slope` propagates without
edit; an unknown axis label trips a `KeyError` (anti-gaming guard A:-2).

The `round(..., 6)` is applied identically to both `slope` and
`percentage_delta_slope`, so the two views are equally truncated.

## Sign convention

* `raw_slope < 0` (regression) → `percentage_delta_slope < 0`.
* `raw_slope > 0` (recovery) → `percentage_delta_slope > 0`.
* `raw_slope == 0` (flat) → `percentage_delta_slope == 0.0`.

No sign-flip artifacts from the division: `TRUST_AXIS_WEIGHTS[axis]`
is strictly positive for every defined axis (the 4 trust-score axes
sum to 100; no axis has zero or negative weight).

## What this surface does NOT do

The Phase 17 C additive bump preserves every Phase 9 D semantic intact:

* The firing gate is still raw-slope-based (`slope > TREND_SLOPE_INFO_MAX
  → no event`). The percentage_delta_slope is **descriptive**, not a
  firing gate.
* The severity buckets are still raw-slope-based. A future revision
  could substantiate a parallel percentage-slope bucket scheme, but
  Phase 17 C does NOT — the raw-slope buckets remain authoritative.
* Trend anomalies surface within-case degradation over time; they do
  NOT diagnose root cause, validate physics, or authorize Tier 2
  promotion.

## Schema bump policy

`COHORT_TREND_ANOMALIES_SCHEMA_VERSION` bump history is canonical in
`backend/app/services/reporting/_schema_versions.py`:

* `1.0.0` (Phase 9 D) — initial schema.
* `1.1.0` (Phase 17 C · 2026-05-17) — additive `percentage_delta_slope`
  field on every TrendEvent. Closes Phase 16 retrospective
  carry-forward §1.

Pre-1.1.0 consumers that ignore `percentage_delta_slope` continue to
function; the field is computed server-side from the SSOT
`TRUST_AXIS_WEIGHTS` mapping so axis weight changes propagate without
further bumps.

## Forbidden wording

Per the cohort-trend-anomalies envelope-narrowed forbidden list (Phase 7 B
/ 8 B / 8 C / 8 D / 8 E / 9 A pattern): no `validated against`, no
`perforation completed`, no `bullet-through-steel complete`, no
`validated physics`. The envelope's `_assert_no_overclaim` raises if a
forbidden token appears outside the `not <claim>` disclaimer form.
