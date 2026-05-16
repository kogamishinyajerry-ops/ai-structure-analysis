# Cohort-scoped drift attribution — SSOT methodology

> **Tier 1 engineering candidate; not signed validation; not benchmark agreement.**
>
> **Scope:** the cohort-level per-axis percentage-delta aggregation surface on `cohort-anomalies` (schema 1.1.0). Given the cohort's latest two snapshots, surfaces (a) per-case `DriftAttribution` entries + (b) the cohort-level dominant (case, axis) pair (the worst absolute delta_pct across any case in the cohort).
>
> **Status:** Phase 16 B. Closes Phase 15 retrospective §4 (per-axis percentage delta on cohort-scoped surfaces) + §6 (cross-axis-comparable cohort signal).

## Why this surface exists

The existing `cohort-anomalies` envelope (Phase 8 E) surfaces statistical outliers via z-scores on per-axis weighted scores — answering "which case is statistically unusual on which axis?". The reviewer reads `case-X · axis=energy_audit · z=-2.0` and asks a follow-up: "by HOW MUCH did the energy axis drop, expressed as a percentage of the axis weight?". The Phase 15 C per-case `DriftAttribution` answers this on the alerts + timeline envelopes (per-case scope); Phase 16 B extends the same answer to the cohort scope.

The cohort drift attribution aggregates per-case `DriftAttribution` entries computed between the cohort's latest TWO snapshot labels (cohort-wide, not per-case-latest). This makes the comparison coherent: every case is scored on the SAME snapshot pair. Cases absent in one of the latest 2 snapshots are silently skipped (the per-case timeline walker enforces case-presence per snapshot).

The cohort-level dominant (case, axis) pair is the (case, axis) with the largest absolute delta_pct. Strictly-exceed floor: a cohort whose worst absolute delta_pct is `<= 5.0%` lands `cohort_dominant_axis = None` (uniform-drift cohort posture). This matches the per-case floor at 5.0% (`DRIFT_DOMINANT_AXIS_DELTA_FLOOR_PCT` in `trust_score_drift_attribution.py`) so reviewers reading the two surfaces side-by-side see a coherent threshold.

```
cohort_drift_attribution = {
    "from_snapshot": "2026-05-17T120000Z",
    "to_snapshot":   "2026-05-17T140000Z",
    "per_case_drift_attribution": [
        {"case_id": "rod-wave-impact-candidate",            "dominant_axis": None,         "dominant_delta_pct": None, ...},
        {"case_id": "rod-wave-impact-stiff-candidate",      "dominant_axis": None,         "dominant_delta_pct": None, ...},
        {"case_id": "rod-wave-impact-energy-leak-candidate","dominant_axis": "energy_audit","dominant_delta_pct": -100.0, ...},
        {"case_id": "cylinder-pv-candidate",                "dominant_axis": None,         "dominant_delta_pct": None, ...},
        {"case_id": "cylinder-pv-extended-candidate",       "dominant_axis": None,         "dominant_delta_pct": None, ...},
    ],
    "cohort_dominant_axis": "energy_audit",
    "cohort_max_abs_delta_pct": 100.0,
    "dominant_case_id": "rod-wave-impact-energy-leak-candidate",
}
```

A reviewer reading this immediately sees: the energy_audit axis collapsed on ONE case (the leak case); all other cohort members held; the cohort's dominant signal lives on (rod-wave-impact-energy-leak-candidate, energy_audit).

## The 5.0% cohort-dominant floor

`COHORT_DOMINANT_AXIS_FLOOR_PCT = 5.0` is a single SSOT constant at `backend/app/services/reporting/cohort_drift_attribution.py`. It is INDEPENDENT from the per-case floor (`DRIFT_DOMINANT_AXIS_DELTA_FLOOR_PCT`) so a future tuning step can adjust the cohort-scale noise sensitivity without affecting the per-case alerts surface.

Bump history:

* **5.0** (Phase 16 B · 2026-05-17) — initial Tier 1 candidate value. Rationale: matches the per-case Phase 15 C floor at 5.0% so reviewers reading the per-case + cohort surfaces side-by-side see a coherent threshold. If cohort-scale noise patterns later diverge from per-case (e.g., 5 cases all drifting by 4% would land below the per-case floor but the cohort signal might benefit from a tighter threshold), the floor can be bumped down here independently.

Bumping the floor down (e.g., 5.0 → 2.0) requires a retrospective entry naming the consumer that needs finer-grained cohort attribution AND verifying that the tightened floor doesn't false-positive on snapshot-time noise. Bumping the floor up requires a retrospective entry AND a paragraph explaining what false-positive cohort pattern was previously not budgeted for. Slipping the floor to mask a real cohort regression is anti-pattern; the retrospective entry is the audit trail.

## What this surface does NOT do

* It does NOT perform regression root-cause analysis. The dominant (case, axis) pair names WHICH BUCKET of evidence regressed on WHICH case, not WHY.
* It does NOT replace the existing z-score view on `cohort-anomalies`. Both surfaces are emitted in parallel; the z-score view is the STATISTICAL outlier signal, the cohort_drift_attribution is the CROSS-AXIS-COMPARABLE engineering signal. A reviewer should read both.
* It does NOT certify a Tier 2 benchmark. The Tier 1 disclaimer trio is preserved on every envelope; the cohort drift attribution is a candidate-evidence-cleanliness signal only.
* It does NOT classify the cohort drift as step-change vs slow-drift. The surface compares the latest 2 snapshots only; a multi-snapshot trend signature would require a separate surface (Phase 16 explicitly defers this).

## Module surface (SSOT)

`backend/app/services/reporting/cohort_drift_attribution.py` exposes:

* `COHORT_DOMINANT_AXIS_FLOOR_PCT: float = 5.0` — SSOT floor (strictly-exceed semantic; `<=` rejects).
* `CohortDriftAttribution` — frozen dataclass with `from_snapshot / to_snapshot / per_case_drift_attribution: tuple[tuple[str, DriftAttribution], ...] / cohort_dominant_axis / cohort_max_abs_delta_pct / dominant_case_id`.
* `compute_cohort_drift_attribution(*, repo_root, dominant_floor_pct=5.0) -> CohortDriftAttribution | None` — pure-function builder; walks `golden_samples/*-candidate/` (signed-registry filtered) and the latest 2 snapshots in `reports/snapshots/`. Returns `None` when fewer than 2 snapshots exist. Raises `ValueError` on non-positive floor.
* `render_cohort_drift_attribution_dict(att) -> dict | None` — JSON-serialization helper; renders `cohort_max_abs_delta_pct` as `null` when NaN; returns `None` when the attribution itself is None.

Consumer: `backend/app/services/reporting/cohort_anomalies.py` imports `compute_cohort_drift_attribution` + `render_cohort_drift_attribution_dict` (anti-gaming guard M:-2: no inline percentage math in the consumer).

## Anti-gaming guards pinned by tests

* **M:-2** — `COHORT_DOMINANT_AXIS_FLOOR_PCT` is module-level, typed, named; `CohortDriftAttribution` is a frozen dataclass; the consumer imports the helper rather than inline-aggregating per-case math.
* **T:-3** — boundary-pinned tests: a 5-case cohort with one leak case at energy_audit 15→0 produces `cohort_dominant_axis == "energy_audit"` + `dominant_case_id == LEAK_CASE_ID` + `cohort_max_abs_delta_pct == 100.0` exactly.
* **A:-2** — defensive parser raises on (a) non-positive floor. Returns `None` (not raises) when fewer than 2 snapshots exist (graceful degrade); silently skips cases absent in one of the latest 2 snapshots (per-case timeline walker handles this).
* **C:-8** — module docstring + this methodology doc cite the cross-axis-comparable signal vs the z-score statistical signal distinction. Neither is a Tier 2 promotion. The Tier 1 disclaimer trio is preserved on the `cohort-anomalies` envelope at schema 1.1.0.

## Reference

Phase 16 D's reviewer journey "drift audit trail" exercises the `cohort_dominant_axis == "energy_audit"` + `dominant_case_id == LEAK_CASE_ID` path on the 5-case explicit_dynamics + linear_static_pv cohort. The Phase 16 retrospective at `.planning/retrospectives/fm04a_phase16_drift_attribution_cross_surface.md` will document the closure of Phase 15 retro §4 + §6 by this slice.
