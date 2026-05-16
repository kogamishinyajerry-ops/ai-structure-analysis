# Cohort bucket thresholds — SSOT methodology

> **Tier 1 engineering candidate; not signed validation; not benchmark agreement.**
>
> **Scope:** the two named constants that drive the cohort-executive-summary `healthy` / `watching` / `regressed` bucketing. This is the SSOT — any rebalance follows the checklist below; any downstream UI / chart / pill colour reads the same constants by name.
>
> **Status:** Phase 9 C (closes Phase 8 retrospective carry-forward §3).

## The constants

Defined in [`backend/app/services/reporting/cohort_executive_summary.py`](../../backend/app/services/reporting/cohort_executive_summary.py):

| Python identifier | Value | Meaning |
|-------------------|-------|---------|
| `HEALTHY_TRUST_SCORE_MIN` | `80` | Minimum recomputed trust score (0–100) for a case to land in the `healthy` bucket, all else equal. |
| `WATCHING_TRUST_SCORE_MIN` | `50` | Minimum recomputed trust score for a case to land in `watching` rather than `regressed`, all else equal. |

Trust score itself is the sum of four weighted axes (`completeness` + `convergence` + `energy_audit` + `reproducibility`) computed by `backend/app/services/reporting/trust_score.py`. Axis weights are versioned separately by `TRUST_SCORE_FORMULA_VERSION` (see `_schema_versions.py`).

## Bucket precedence (load-bearing)

`_classify_bucket(trust_score, alarm_count, signoff_verdict)` applies these checks in order; the first match wins:

1. **`signoff_verdict == "blocked_pending_input"`** → `regressed` (verdict overrides score)
2. **`alarm_count > 0`** → `regressed` (any warn/danger alarm on the timeline dominates score)
3. **`trust_score < WATCHING_TRUST_SCORE_MIN`** → `regressed`
4. **`signoff_verdict ∈ {watching, needs_more_evidence, needs_more_convergence}`** → `watching` (verdict downgrades a healthy score)
5. **`trust_score < HEALTHY_TRUST_SCORE_MIN`** → `watching`
6. **otherwise** → `healthy` (covers `trust_score ≥ 80` with no regressed signal, **and** the no-snapshot case where `trust_score is None`)

Documented mnemonic: `regressed > watching > healthy`. The check order is deliberately layered so that a reviewer signoff verdict can either lift a score-only-healthy case into `watching` (rule 4) or push any case into `regressed` (rule 1), never the other way.

## Rationale for 80 / 50

These are **engineering judgments**, not benchmark agreement.

* **80** — at four equally-weighted axes of 25 each, a `healthy` case carries at least 80% of the trust-score envelope. Bucket reads "we believe the candidate's evidence is internally consistent with no major axis collapsed."
* **50** — half the envelope. Below 50 at least two of four axes are collapsed (or one is collapsed and another is heavily attenuated). Bucket reads "candidate evidence has structural gaps the reviewer must inspect."

These thresholds are **not derived from a held-out test set**; they are the team's first cut at carving the `0..100` line into three reviewer-readable bands. A future rebalance must follow the checklist below.

## Rebalance checklist (procedure for changing the thresholds)

A rebalance is any change to `HEALTHY_TRUST_SCORE_MIN` or `WATCHING_TRUST_SCORE_MIN`.

1. **Publish a retrospective entry** in `.planning/retrospectives/` naming:
   * the new value pair,
   * the empirical signal motivating it (which case(s) were misclassified under the old thresholds, and why),
   * the reviewer who proposed the change.
2. **Extend the sensitivity matrix** in `tests/test_phase9_bucket_sensitivity_matrix.py` to pin the new boundaries (the existing matrix pins 49/50/51, 79/80/81 — the rebalance must add analogous pins for the new values, then run the whole matrix to confirm no neighbour case silently flipped buckets).
3. **Bump `COHORT_EXECUTIVE_SUMMARY_SCHEMA_VERSION`**:
   * **PATCH** if only the threshold value moved and the response shape did not change (`1.0.0 → 1.0.1`).
   * **MINOR** if a new envelope field was added (e.g. `bucket_thresholds: {...}`) so downstream consumers can read the active thresholds rather than hardcoding them.
4. **Add a SCORECARD note** in the retrospective explaining the bump category.
5. **Confirm forward-compat**: the frontend `cohortExecutiveSummaryClient.ts` defensive parser MUST continue to fall back to `regressed` for any unknown bucket. The threshold rebalance must not introduce a new bucket name; if a new band is genuinely needed, that is a separate MAJOR-bumping refactor.
6. **Run the full integration sweep** (`pytest tests/test_phase{5,6,7,8,9}_*.py`) and confirm the cohort-executive-summary integration tests still pass.

## What is NOT a rebalance

* Adding a fourth axis to trust score → that is a `TRUST_SCORE_FORMULA_VERSION` bump + a new retrospective entry naming the formula change, NOT a bucket-threshold rebalance.
* Adding a new signoff verdict that should force a bucket → that is a `SIGNOFF_RECORD_SCHEMA_VERSION` MINOR (additive enum value) + an extension of the bucket precedence ladder, NOT a threshold rebalance.
* Adjusting the `_WATCHING_SIGNOFF_VERDICTS` frozenset → that is a precedence-ladder change, also retrospective-worthy, also not a threshold rebalance.

## What is explicitly out of scope

The thresholds are **Tier 1 candidate scope only.** They do **not** authorize Tier 2 promotion, substitute for signed validation, or constitute benchmark agreement. A Tier 2 promotion decision lives behind the sealed FM-04b P8 packet path and is not driven by the bucket label.

## Sensitivity matrix

The behavior at every neighbour of the two thresholds is pinned by [`tests/test_phase9_bucket_sensitivity_matrix.py`](../../tests/test_phase9_bucket_sensitivity_matrix.py). The matrix exercises:

* `trust_score ∈ {None, 0, 49, 50, 51, 79, 80, 81, 99, 100}`
* `alarm_count ∈ {0, 1}` (only the binary "any-alarm-fires" branch matters; `> 0` is the only check)
* `signoff_verdict ∈ {None, watching, needs_more_evidence, needs_more_convergence, blocked_pending_input}`

…and pins the bucket outcome for every combination the precedence ladder cares about. A silent edit of either constant (`80 → 79`, `50 → 51`, etc.) will cause at least one boundary cell to flip bucket, surfacing the change in CI.
