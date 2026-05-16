# Cohort trend-slope thresholds — SSOT methodology

> **Tier 1 engineering candidate; not signed validation; not benchmark agreement.**
>
> **Scope:** the four named constants that drive the cohort-trend-anomalies `info` / `warn` / `danger` severity bucketing + the cohort timeline-length floor. This is the SSOT — any rebalance follows the checklist below; any downstream UI / chart / pill colour reads the same constants by name.
>
> **Status:** Phase 10 C (closes Phase 9 retrospective carry-forward §3).

## The constants

Defined in [`backend/app/services/reporting/cohort_trend_anomalies.py`](../../backend/app/services/reporting/cohort_trend_anomalies.py):

| Python identifier | Value | Meaning |
|-------------------|-------|---------|
| `TREND_SLOPE_INFO_MAX` | `-0.5` | Maximum slope (least negative) that still fires an `info` event. A slope `> -0.5` does NOT fire at all. |
| `TREND_SLOPE_WARN_MAX` | `-1.5` | Maximum slope that lands in `warn` bucket. Slopes in `(-1.5, -0.5]` → `info`. |
| `TREND_SLOPE_DANGER_MAX` | `-3.0` | Maximum slope that lands in `danger` bucket. Slopes `≤ -3.0` → `danger`. |
| `TREND_MIN_POINTS` | `3` | Minimum case timeline length to compute slope. Below this, slope is under-determined and the builder yields no anomaly for that case. |

The slope is the least-squares fit of the trust-score axis values
(weighted points) against the snapshot index (`0..N-1`). Units are
**weighted-axis-points per snapshot**.

## The "more negative is worse" convention

Slope at the exact boundary value goes into the **worse** bucket. The
threshold inequalities are `slope <= TREND_SLOPE_*_MAX`:

* `slope <= -3.0` → `danger`
* `-3.0 < slope <= -1.5` → `warn`
* `-1.5 < slope <= -0.5` → `info`
* `-0.5 < slope` → no event (case is not regressing on this axis)

This convention is preserved verbatim in `severity_for_slope()` so a
slope at exactly `-3.0` lands in `danger`, not `warn`. Tests pin every
boundary cell.

## Bucket precedence (load-bearing)

`severity_for_slope(slope)` applies in this order:

1. **`slope <= TREND_SLOPE_DANGER_MAX (-3.0)`** → `danger`
2. **`slope <= TREND_SLOPE_WARN_MAX (-1.5)`** → `warn`
3. otherwise → `info` (the most-conservative bucket when the firing
   gate has already determined an event should fire)

The firing gate is in `_build_event_for_axis`:

* If `slope > TREND_SLOPE_INFO_MAX (-0.5)` → no event emitted (case is
  not regressing).
* Otherwise: compute severity via the precedence ladder above.

Standalone calls to `severity_for_slope()` with `slope > -0.5` return
`'info'` (most-conservative fallback). The firing gate prevents that
result from ever reaching production output.

## Rationale for -0.5 / -1.5 / -3.0 / floor 3

These are **engineering judgments**, not benchmark agreement.

* **TREND_SLOPE_INFO_MAX = -0.5** — the noise floor. A case that loses
  half a weighted point per snapshot is barely distinguishable from
  measurement noise on the 0–50 / 0–25 / 0–15 / 0–10 axis weights.
  Below this the case is more likely drifting than truly regressing.
* **TREND_SLOPE_WARN_MAX = -1.5** — three times the noise floor.
  A reviewer should look at the case but it has not yet lost a full
  bucket-width.
* **TREND_SLOPE_DANGER_MAX = -3.0** — six times the noise floor. A
  case losing 3 weighted points per snapshot will exhaust its
  contribution to trust score within 5–8 snapshots; the cohort
  health is materially at risk.
* **TREND_MIN_POINTS = 3** — least-squares slope is under-determined
  for `N < 2`. We require `N >= 3` to reduce the chance that a single
  noisy snapshot triggers a spurious slope event.

These thresholds are **not derived from a held-out test set**; they
are the team's first cut at carving the slope domain into three
reviewer-readable bands. A future rebalance must follow the checklist
below.

## Rebalance checklist (procedure for changing the thresholds)

A rebalance is any change to `TREND_SLOPE_INFO_MAX`,
`TREND_SLOPE_WARN_MAX`, `TREND_SLOPE_DANGER_MAX`, or
`TREND_MIN_POINTS`.

1. **Publish a retrospective entry** in `.planning/retrospectives/`
   naming:
   * the new value(s),
   * the empirical signal motivating the change (which case(s) were
     misclassified, and why),
   * the reviewer who proposed the change.
2. **Extend the sensitivity matrix** in
   `tests/test_phase10_trend_slope_sensitivity_matrix.py` to pin the
   new boundaries (the existing matrix pins `-0.5 / -1.5 / -3.0`
   ± `0.01` and `TREND_MIN_POINTS` at 0/1/2/3/4). Add analogous pins
   for the new values + run the whole matrix to confirm no neighbour
   cell silently flipped severity.
3. **Bump `COHORT_TREND_ANOMALIES_SCHEMA_VERSION`**:
   * **PATCH** if only the threshold value moved and the response
     shape did not change (`1.0.0 → 1.0.1`).
   * **MINOR** if a new envelope field was added (e.g.
     `slope_thresholds: {...}`) so downstream consumers can read the
     active thresholds rather than hardcoding them.
4. **Add a SCORECARD note** in the retrospective explaining the bump
   category.
5. **Confirm forward-compat**: the frontend
   `cohortTrendAnomaliesClient.ts` defensive parser MUST continue to
   fall back to `'info'` for any unknown severity. The threshold
   rebalance must not introduce a new severity name; if a new band is
   genuinely needed, that is a separate MAJOR-bumping refactor.
6. **Run the full integration sweep** (`pytest tests/test_phase{5,6,7,8,9,10}_*.py`)
   and confirm the trend integration tests still pass.

## What is NOT a rebalance

* Adding a fourth axis to trust score → that is a
  `TRUST_SCORE_FORMULA_VERSION` bump + a new retrospective entry
  naming the formula change. The trend-slope thresholds remain
  unchanged because they're per-axis; the new axis joins
  `TREND_AXES` and gets its slope computed under the same
  thresholds.
* Adding a new severity bucket (e.g. `'critical'` above `danger`) →
  that is a MAJOR-bumping refactor + frontend defensive-parser
  update + new color in the panel.
* Changing the least-squares slope formula (e.g. weighted regression
  vs. simple OLS) → that is a new methodology entirely; the constant
  values may remain the same but the slope's numerical meaning
  changes. Requires retrospective + formula version bump.

## What is explicitly out of scope

The thresholds are **Tier 1 candidate scope only.** They do **not**
authorize Tier 2 promotion, substitute for signed validation, or
constitute benchmark agreement. A Tier 2 promotion decision lives
behind the sealed FM-04b P8 packet path and is not driven by the
trend-event severity.

## Sensitivity matrix

The behavior at every neighbour of the four constants is pinned by
[`tests/test_phase10_trend_slope_sensitivity_matrix.py`](../../tests/test_phase10_trend_slope_sensitivity_matrix.py).
The matrix exercises:

* `slope ∈ {0.0, -0.49, -0.5, -0.51, -1.49, -1.5, -1.51, -2.99, -3.0, -3.01, -10.0}`
* `point_count ∈ {0, 1, 2, 3, 4}`

…and pins the severity outcome / firing-gate behavior for every
combination the firing gate cares about. A silent edit of any
constant (`-0.5 → -0.4`, `-1.5 → -1.6`, etc.) will cause at least one
boundary cell to flip, surfacing the change in CI.
