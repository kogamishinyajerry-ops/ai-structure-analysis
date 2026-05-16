# Cross-snapshot trust-score drift attribution — SSOT methodology

> **Tier 1 engineering candidate; not signed validation; not benchmark agreement.**
>
> **Scope:** the per-consecutive-snapshot per-axis percentage-delta surface on `trust-score-alerts` (schema 1.1.0) and `trust-score-timeline` (schema 1.1.0). Given two consecutive timeline points expressed in weighted axis points, surfaces which trust axis regressed most as a percentage of that axis's weight.
>
> **Status:** Phase 15 C. Closes Phase 14 retrospective §1 (per-axis drift attribution surface).

## Why this surface exists

The existing `trust-score-alerts` envelope (Phase 7 C) carries an `axis_deltas: dict[str, int]` field with per-axis WEIGHTED-point deltas (e.g., `energy_audit_closure: -15` for a 15→0 collapse). A reviewer reading an alarm needs to answer "which axis regressed most?" — and the answer depends on the AXIS WEIGHT, not the raw delta. A -15 weighted-point drop on the energy axis (15-pt weight; -100% of the axis) is a much bigger signal than a -15 weighted-point drop on the completeness axis (50-pt weight; -30% of the axis).

Phase 15 C surfaces the PERCENTAGE delta per axis so cross-axis comparison is meaningful:

```
trust_score_drift_attribution = {
    "from_snapshot": "2026-05-17T120000Z",
    "to_snapshot":   "2026-05-17T140000Z",
    "per_axis_delta_pct": {
        "completeness":   -16.0,   # 50-pt axis dropped 8 pts
        "convergence":      0.0,   # 20-pt axis unchanged
        "energy_audit":  -100.0,   # 15-pt axis dropped 15 pts
        "reproducibility": -33.3,  # 15-pt axis dropped 5 pts
    },
    "dominant_axis": "energy_audit",
    "dominant_delta_pct": -100.0,
}
```

The reviewer immediately sees: the energy_audit axis collapsed; the completeness + reproducibility axes also drifted but not by as much; the convergence axis held.

## The 5.0% dominant-axis floor

`DRIFT_DOMINANT_AXIS_DELTA_FLOOR_PCT = 5.0` is a single SSOT constant at `backend/app/services/reporting/trust_score_drift_attribution.py`. An axis with absolute delta_pct `<= 5.0%` is NOT counted as dominant (the floor must be STRICTLY EXCEEDED); a regression in which every axis drifted by 3-4% lands as a uniform drift with `dominant_axis = None`.

Bump history:

* **5.0** (Phase 15 C · 2026-05-17) — initial Tier 1 candidate value. Rationale: a 5% drift is the engineering-evidence-cleanliness floor that separates "noise across all axes" (every axis moved together by a few percent — likely a snapshot-time issue, not an evidence-quality regression) from "one axis collapsed" (energy_audit dropping 100% is a real regression event). A 5.0% exact delta lands AT the floor (not dominant); only deltas strictly above 5% surface that axis as dominant.

Bumping the tolerance is a separate methodology step from bumping the alerts / timeline schema versions:

* **Bumping the floor down** (e.g., 5.0 → 2.0) requires a retrospective entry naming the consumer that now needs finer-grained attribution AND verifying that the tightened floor doesn't false-positive on snapshot-time noise.
* **Bumping the floor up** (e.g., 5.0 → 10.0) requires a retrospective entry AND a paragraph here explaining what false-positive pattern was previously not budgeted for. Slipping the floor to mask a real regression is anti-pattern; the retrospective entry is the audit trail.

## What this surface does NOT do

* It does NOT perform regression root-cause analysis. The dominant_axis names WHICH BUCKET of evidence regressed, not WHY.
* It does NOT classify the drift as step-change vs slow-drift (that would require >= 3 snapshots). It only compares CONSECUTIVE pairs.
* It does NOT replace the existing `axis_deltas` (weighted-point) surface; both fields are carried in the alarm event for back-compat AND because both views are useful to reviewers (weighted points for absolute magnitude; percentages for cross-axis comparison).
* It does NOT certify a Tier 2 benchmark. The Tier 1 disclaimer trio is preserved on every envelope; the drift attribution is a candidate-evidence-cleanliness signal only.

## Module surface (SSOT)

`backend/app/services/reporting/trust_score_drift_attribution.py` exposes:

* `DRIFT_DOMINANT_AXIS_DELTA_FLOOR_PCT: float = 5.0` — SSOT floor.
* `TRUST_AXIS_WEIGHTS: Mapping[str, int]` — SSOT axis label → axis weight mapping (`completeness=50 / convergence=20 / energy_audit=15 / reproducibility=15`). Pinned to sum to 100 by tests.
* `DriftAttribution` — frozen dataclass with `from_snapshot / to_snapshot / per_axis_delta_pct / dominant_axis / dominant_delta_pct`.
* `compute_drift_attribution(prev_axes, curr_axes, *, from_snapshot, to_snapshot, dominant_floor_pct=5.0) -> DriftAttribution` — pure-function builder; raises on unknown axis labels, out-of-band values, missing axes, non-positive floor.
* `render_drift_attribution_dict(att) -> dict` — JSON-serialization helper; renders `dominant_delta_pct` as `null` when NaN.

Every consumer (alerts builder + timeline builder) imports the helper from this module rather than inline-declaring the per-axis percentage math (anti-gaming guard M:-2 in the Phase 15 binding rubric).

## Anti-gaming guards pinned by tests

* **M:-2** — `DRIFT_DOMINANT_AXIS_DELTA_FLOOR_PCT` is module-level, typed, named; `TRUST_AXIS_WEIGHTS` sums to 100 (pinned by `test_trust_axis_weights_sum_to_one_hundred`).
* **T:-3** — boundary-pinned tests: a 15→0 collapse on energy_audit produces `delta_pct = -100.0` exactly; a 50→42 drop on completeness produces `delta_pct = -16.0` exactly.
* **A:-2** — defensive parser raises on (a) missing axes; (b) values outside `[0, axis_weight]`; (c) unknown axis label keys; (d) non-positive floor. Below-floor uniform drift produces `dominant_axis = None` (NOT a default axis, NOT raised); the reviewer reads "uniform drift" as the intended signal.
* **C:-8** — module docstring + methodology doc cite the 1D-rod-vs-3D-solid distinction's analogue: percentage delta is the cross-axis-comparable signal; weighted points are the absolute-magnitude signal. Neither is a Tier 2 promotion.

## Reference

Phase 15 D's reviewer journey "explicit_dynamics drift triage" exercises the `dominant_axis == "energy_audit"` path on the rod-wave-impact-energy-leak-candidate snap-2→snap-3 transition. The Phase 15 retrospective at `.planning/retrospectives/fm04a_phase15_explicit_dynamics_cohort_substantiation.md` documents the closure of Phase 14 retro §1 by this slice.

## Cumulative drift attribution (Phase 16 A · 2026-05-17)

The Phase 15 C surface ships `inter_snapshot_drift_attribution: tuple[DriftAttribution, ...]` on the `trust-score-timeline` envelope (length `N-1` for N timeline points; one entry per consecutive pair). Phase 16 A adds `cumulative_drift_attribution: DriftAttribution | None` on the SAME envelope (schema MINOR bump 1.1.0 → 1.2.0; additive field; pre-1.2.0 readers ignore it).

The cumulative entry spans snap-1 → snap-N (one entry per timeline, regardless of point count). The cumulative value answers a different reviewer question than the per-pair entries:

* **Per-pair** answers "where in the arc did each axis change?"
* **Cumulative** answers "what is the NET change between the first and last observation, regardless of the path taken?"

For an axis that monotonically drops, per-pair sum equals cumulative. For an axis that drops and recovers, cumulative is SMALLER in absolute magnitude than the worst per-pair entry. For example: convergence axis goes 20 → 10 → 20 across 3 snapshots — per-pair: `-50% / +100%`; cumulative: `0%`. Reading per-pair alone would surface the +100% recovery as a (positive) regression event; reading cumulative alone would miss the transient drop. Both views are useful; surface both.

Degenerate cases:
* 0-point timeline: `cumulative_drift_attribution = null`. Vacuous (no observation).
* 1-point timeline: `cumulative_drift_attribution = null`. No transition exists.
* 2-point timeline: `cumulative_drift_attribution` EQUALS the single `inter_snapshot_drift_attribution[0]` entry (degenerate-correct).
* 3+ point timeline: `cumulative_drift_attribution` may differ from the per-pair entries; see the convergence example above.

The 5.0% SSOT floor (`DRIFT_DOMINANT_AXIS_DELTA_FLOOR_PCT`) applies to both surfaces uniformly: an axis must STRICTLY EXCEED 5% cumulative absolute delta to be counted as the cumulative `dominant_axis`. Sub-floor cumulative drift surfaces `dominant_axis = None` (uniform-drift posture; the recovery + drop canceled out within the noise floor).

Closes Phase 15 retrospective §3 (drift attribution rendered on more envelopes than alerts + timeline-per-pair).
