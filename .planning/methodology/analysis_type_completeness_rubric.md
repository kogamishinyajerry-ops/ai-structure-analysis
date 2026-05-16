# Analysis-Type-Aware Completeness Rubric — Methodology SSOT

**FM-04a Phase 11 A.** Tier 1 engineering candidate; not signed validation; not benchmark agreement.

This document is the single source of truth for the per-analysis-type completeness rubric weights surfaced by `backend/app/services/reporting/case_completeness.py`. A reviewer reading a `<case>_completeness_scorecard.json` payload can cross-check every weight against this doc by **Python identifier** (no inline magic numbers).

## Why per-analysis-type weights

The FM-04a milestone scaffold (Phases 5–10) shipped a single ballistic-flavored rubric with axes geared to OpenRadioss explicit-dynamics fixtures: `animation_manifest` (mode-shape playback), `result_mesh` (deformed-mesh artifact), and `notes` (free-form narrative). Those three axes are not load-bearing for a linear-static pressure-vessel case — they would never be populated, so a perfectly-converged PV fixture artificially capped at 85/100 (the cylinder-pv-candidate e2e demo of 2026-05-16 actually hit 75/100 for this reason).

The Phase 11 A rebuild dispatches per analysis type. Each rubric still sums to 100 (M:-2 anti-gaming guard) and each carries the 5 universal axes that any candidate fixture must have, but the closing 25 points are allocated differently per type.

## Identifiers — closed enum + weights map

The closed enum of supported analysis types is the module-level tuple:

```python
ANALYSIS_TYPE_TUPLE: tuple[str, ...] = (
    "ballistic",
    "linear_static_pv",
    "explicit_dynamics",
    "modal",
)
```

The per-type weights live in:

```python
ANALYSIS_TYPE_RUBRIC_WEIGHTS: dict[str, dict[str, int]]
```

Default for legacy callers (every FM-04a Phase 4–10 consumer):

```python
DEFAULT_ANALYSIS_TYPE: str = "ballistic"
```

Adding a new analysis type **requires updating both the tuple and the weights dict in lockstep**; the import-time audit `_assert_rubric_weights_consistent()` refuses to import the module if they drift.

## Universal axes (present in every rubric)

| Axis | Weight | Scored by |
|---|---:|---|
| `starter_deck` | 15 | File presence at `starter_deck_path`. |
| `engine_deck` | 15 | File presence at `engine_deck_path`. |
| `ballistic_metrics` | 15–20 | File presence at `ballistic_metrics_path`. (Filename retained for FM-04a back-compat; the JSON inside can be PV / modal / explicit content.) |
| `energy_audit` | 15 | `energy_audit.status` inside metrics JSON: `closed_aggregate` = full, `partial_candidate` = 2/3, anything else = 0. |
| `convergence_study` | 10–15 | `combined_verdict` or `convergence_combined_verdict` inside the convergence-study JSON. |

## Ballistic / explicit_dynamics / modal — closing 25 pts

| Axis | Weight | Rationale |
|---|---:|---|
| `animation_manifest` | 5 | Frame-by-frame mode-shape or transient-state playback artifact. |
| `result_mesh` | 5 | Deformed-mesh or per-mode shape artifact. |
| `generator_script` | 5 | Source-of-truth Python generator for the deck. |
| `notes` | 5 | Free-form narrative `NOTES.md`. |

> **modal note (Phase 12 A)**: the modal rubric reuses every ballistic axis verbatim — same weights, same scorers. `animation_manifest` is load-bearing here (mode-shape playback is the canonical modal artifact); `result_mesh` carries the per-mode deformed-mesh; `ballistic_metrics` carries the participation-factor + effective-modal-mass blocks under the inherited filename. The analytical Euler-Bernoulli cross-check (§Modal cross-check below) is a **separate slice-B advisor concern**, not a completeness axis.

## linear_static_pv — closing 25 pts (replacement axes)

The PV-specific axes are read from inside the metrics JSON under a `pv_summary` block. They replace the three non-applicable optional-artifact axes (`animation_manifest`, `result_mesh`, `notes`) AND pull 10 more points from a reduced `ballistic_metrics` weight (20 → 15) and a reduced `convergence_study` weight (15 → 10). The convergence weight is lower because `linear_static` cases have only `mesh_sweep` meaningful (no `dt_sweep`), so the convergence axis carries half its usual signal.

| Axis | Weight | Scored by |
|---|---:|---|
| `lame_cross_check` | 10 | `pv_summary.convergence_vs_lame.max_rel_err_sigma_{r,t,z,von_mises}_pct`: worst ≤ 5% → full; > 5% → half; absent → 0. |
| `scl_convergence` | 10 | `pv_summary.convergence_vs_lame.max_rel_err_sigma_{t,z,von_mises}_pct`: worst ≤ 2% → full; ≤ 5% → half; > 5% or absent → 0. (Tighter than `lame_cross_check` because the load-bearing through-wall stress components must converge tightly for the §5.5 categorized stresses to be trustworthy.) |
| `generator_script` | 5 | Same as ballistic rubric. |
| `allowable_margin` | 5 | `pv_summary.asme_section_5_5.ratio_P_m_over_S_m`: `< 1.0` → full; `>= 1.0` → 0 (engineering margin failure flagged). |

## Convergence-kind discriminator (linked schema bump)

`convergence_study.json` schema 1.0.0 → 1.1.0 → 1.2.0 evolution:

- **1.0.0**: two-axis (`mesh_sweep` + `dt_sweep`), no discriminator.
- **1.1.0**: adds optional top-level `convergence_kind` ∈ {`explicit_dynamics`, `nonlinear_static`, `linear_static`, `modal`}.
- **1.2.0** (Phase 12 A MINOR): adds optional `mode_count_sweep` axis used when `convergence_kind == "modal"`. The legacy `mesh_sweep` + `dt_sweep` axes are treated as N/A on modal cases (mode-count refinement is the only convergence dimension that matters for an eigenproblem).

The trust-score convergence axis (`_score_convergence_axis` in `backend/app/services/reporting/trust_score.py`) reads this discriminator:

- `convergence_kind == "linear_static"`: score on `mesh_sweep` only; `dt_sweep` absence is **not** a failure.
- `convergence_kind == "modal"`: score on `mode_count_sweep` only; `mesh_sweep` and `dt_sweep` absence is **not** a failure.
- Anything else (or absent): two-axis scoring (legacy back-compat).

A 1.0.0-era payload reads cleanly as `explicit_dynamics` (the back-compat default).

## Modal cross-check (Phase 12 A — Euler-Bernoulli analytical residual)

The modal rubric inherits the ballistic / explicit_dynamics closing 25 pts (`animation_manifest` + `result_mesh` + `generator_script` + `notes`) because mode-shape playback and per-mode deformed-mesh artifacts are first-class evidence for a modal sweep. The `ballistic_metrics` axis (15 pts) carries the participation-factor + effective-modal-mass blocks under the inherited filename; the `energy_audit` axis (15 pts) carries the strain-energy distribution `closed_aggregate` flag.

The analytical cross-check is **not** a rubric axis — it lives in `backend/app/domain/modal_extraction.py` and surfaces as a slice-B advisor concern, not a completeness score. The split is deliberate: completeness measures evidence presence; the cross-check measures evidence quality. A reviewer with the cross-check report can judge whether the modal sweep is converged enough to be a Tier 1 candidate; a reviewer without it still sees a 100/100 completeness score for a case that ships all artifacts.

| Concept | Symbol | Source |
|---|---|---|
| Closed-form β·L roots (cantilever) | `EULER_BERNOULLI_BETA_LN` | `backend/app/domain/modal_extraction.py` |
| Cross-check tolerance | `MODAL_CROSS_CHECK_TOLERANCE_PCT = 5.0` | Same module |
| `convergence_kind` sentinel | `MODAL_CONVERGENCE_KIND = "modal"` | Same module |
| Reference | Blevins 1979, "Formulas for Natural Frequency and Mode Shape", Table 8-1 p.108 | External |

The β·L roots are the dimensionless solutions of `cos(βL)·cosh(βL) + 1 = 0`. The first 4 roots are pinned by `test_euler_bernoulli_beta_ln_constants_are_correct`. The project intentionally does **not** extrapolate β·L past mode 4 (the closed-form Series approximation's convergence radius narrows past mode 6); `euler_bernoulli_cantilever_freq` raises ValueError if asked for mode 5+. A future slice that adds modes 5+ requires a methodology-doc update + retro entry, the same lock-step rule that gates every Phase 11/12 MINOR bump.

The 5 % tolerance is the conservative engineering-practice floor for first-2-bending-mode accuracy on a structured hex mesh; finer mesh routinely achieves < 1 % on bending modes. The smoke deck used to de-risk slice A (1 m × 50 mm × 50 mm steel cantilever, C3D20 structured hex) measured mode 1 = 0.14 %, mode 3 = 0.98 %, mode 8 axial = 0.07 % against analytical.

## Rebalance procedure (binding — follow in lock-step on any future change)

To change a weight in `ANALYSIS_TYPE_RUBRIC_WEIGHTS`:

1. Edit the dict in `backend/app/services/reporting/case_completeness.py`.
2. **Verify the sum stays at 100** for the affected analysis type. `_assert_rubric_weights_consistent()` enforces this at import time; the existing test `test_every_rubric_sums_to_100` is parametrized over `ANALYSIS_TYPE_TUPLE` and provides per-type pinning.
3. **Bump `CASE_COMPLETENESS_SCHEMA_VERSION`** per the bump policy in `_schema_versions.py`: rebalancing weights without adding/removing a key is a **PATCH**; adding/removing an axis key is **MINOR**; renaming an axis is **MAJOR**.
4. **Update the bump-history docstring** in `_schema_versions.py::CASE_COMPLETENESS_SCHEMA_VERSION` citing the rebalance retrospective entry.
5. **Add or update a boundary test in `tests/test_phase11_analysis_type_rubric.py`** asserting the new weight at the rebalance threshold.
6. **Update this methodology doc** (the per-axis table above) to reflect the new weights. The doc cites every weight by Python identifier, so the diff is grep-verifiable.

## What is NOT a rebalance (scope-creep carve-out)

- Adding a brand-new analysis type → **separate slice**, requires:
  - new entry in `ANALYSIS_TYPE_TUPLE`,
  - new entry in `ANALYSIS_TYPE_RUBRIC_WEIGHTS`,
  - matching slice-level test file,
  - retrospective entry naming the engineering case that drove the addition.
- Adding a new axis to an EXISTING rubric → also separate slice, same minor-bump policy.
- Changing the partial-credit ratios (e.g., 2/3 → 1/2 for `partial_candidate` energy audit) → **PATCH** if same scoring structure; **MINOR** if it changes the JSON shape.

## Closure cross-references

- Service module: `backend/app/services/reporting/case_completeness.py` (Phase 11 A; Phase 12 A added named PV weight constants — see `WEIGHT_BALLISTIC_METRICS_PV` / `WEIGHT_CONVERGENCE_STABLE_PV`)
- Schema constants: `backend/app/services/reporting/_schema_versions.py::CASE_COMPLETENESS_SCHEMA_VERSION` (1.1.0); `CONVERGENCE_STUDY_SCHEMA_VERSION` (1.2.0 — Phase 12 A MINOR adds `modal` + `mode_count_sweep`)
- Modal cross-check module: `backend/app/domain/modal_extraction.py` (Phase 12 A — Euler-Bernoulli β·L SSOT, .dat parser, residual report, cumulative mass-participation utility)
- Trust-score downstream: `backend/app/services/reporting/trust_score.py::_score_convergence_axis` honors `convergence_kind` for `linear_static` and `modal` cases
- Tests: `tests/test_phase11_analysis_type_rubric.py` (30 tests at slice A close); `tests/test_phase12_modal_extraction.py` (modal slice-A pins)
- Blueprint dispositions: `.planning/FM-04A_PHASE11_BLUEPRINT.md` §3.A (Phase 11 A); `.planning/FM-04A_PHASE12_BLUEPRINT.md` §3.A (Phase 12 A)
