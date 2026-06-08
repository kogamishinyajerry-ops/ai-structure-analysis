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

## Ballistic / explicit_dynamics — closing 25 pts

| Axis | Weight | Rationale |
|---|---:|---|
| `animation_manifest` | 5 | Frame-by-frame mode-shape or transient-state playback artifact. |
| `result_mesh` | 5 | Deformed-mesh or per-mode shape artifact. |
| `generator_script` | 5 | Source-of-truth Python generator for the deck. |
| `notes` | 5 | Free-form narrative `NOTES.md`. |

## modal — substantiated rubric (Phase 12 B replacement)

The Phase 12 A modal rubric started as a verbatim copy of the ballistic rubric so the modal case could land before the advisor + scorer surfaces existed. Phase 12 B replaces the inherited ballistic optional-artifact axes with four modal-specific quality gates that mirror the four named slice-B advisor concerns, so a reviewer reading the completeness scorecard alongside the advisor critique sees a 1:1 correspondence.

**Universal axes (rebalanced for modal)**:

| Axis | Weight | Scored by |
|---|---:|---|
| `starter_deck` | 10 | File presence at `starter_deck_path`. |
| `engine_deck` | 10 | File presence at `engine_deck_path`. |
| `ballistic_metrics` | 10 | File presence at `ballistic_metrics_path`. Filename inheritance — the JSON inside carries the `modal_summary` block. |
| `energy_audit` | 10 | `energy_audit.status` inside metrics JSON: `closed_aggregate` = full, `partial_candidate` = 2/3, anything else = 0. (Strain-energy distribution on a modal sweep.) |
| `convergence_study` | 10 | `combined_verdict` inside convergence-study JSON, dispatched by the `convergence_kind == "modal"` branch of `trust_score._score_convergence_axis` (scores on `mode_count_sweep` only). |

**Modal-specific axes (Phase 12 B substantiation, closing 50 pts)** — all read from `ballistic_metrics_path` JSON under a `modal_summary` block:

| Axis | Weight | Scored by |
|---|---:|---|
| `mode_count_coverage` | 15 | `modal_summary.mode_count_coverage.{cumulative_y_pct, cumulative_z_pct}`: both ≥ 80% → full; both ≥ 50% → half; either < 50% or absent → 0. |
| `freq_convergence` | 15 | `modal_summary.freq_convergence.dominant_mode_rel_err_pct`: \|err\| ≤ 1% → full; \|err\| ≤ 5% → half; > 5% or absent → 0. |
| `mode_shape_quality` | 10 | `modal_summary.mode_shape_quality.dominant_mac`: MAC ≥ 0.95 → full; MAC ≥ 0.80 → half; < 0.80 or absent → 0. |
| `mass_participation` | 10 | `modal_summary.mass_participation.dominant_mode_pct`: ≥ 50% → full; ≥ 20% → half; < 20% or absent → 0. |

**Why these four**:

* `mode_count_coverage` enforces the conservative engineering-practice floor (ASCE 7 / Eurocode 8) that cumulative effective mass participation in each significant direction must reach ≥ 80% before the modal sweep is considered complete. Missing critical modes is the silent-failure mode for modal extraction; this axis surfaces the gap.
* `freq_convergence` substantiates the Euler-Bernoulli analytical cross-check from `modal_extraction` slice A as a completeness signal alongside its existing slice-B advisor concern. A reviewer who never opens the advisor critique still sees the convergence quality on the scorecard.
* `mode_shape_quality` enforces the MAC discipline — orthogonality between successive mesh-refinement levels — that distinguishes a genuinely converged modal sweep from one where the natural frequency happens to be close but the shape is wrong.
* `mass_participation` is the single most consequential per-mode quality gate; a "dominant" mode with < 20% effective mass is likely a numerical artifact, not a physical mode.

**Dropped from modal**: `animation_manifest` / `result_mesh` / `notes`. These were inherited verbatim in Phase 12 A as scaffolding; the four named modal-specific axes do their load-bearing work (the MAC quality gate captures what the animation would; mass participation captures what the notes narrative would). `generator_script` is also dropped from the modal rubric because the optional-artifact axes are not part of the universal contract; a future case-author who wants to add it can do so without a rebalance because the import-time audit requires only the five universal axes.

**Math check**: 5 universal × 10 + 4 modal-specific (15+15+10+10) = 50 + 50 = 100. Audited at module import by `_assert_rubric_weights_consistent()`.

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

- Service module: `backend/app/services/reporting/case_completeness.py` (Phase 11 A; Phase 12 A added named PV weight constants `WEIGHT_BALLISTIC_METRICS_PV` / `WEIGHT_CONVERGENCE_STABLE_PV`; Phase 12 B substantiated the modal rubric with `WEIGHT_MODE_COUNT_COVERAGE` / `WEIGHT_FREQ_CONVERGENCE` / `WEIGHT_MODE_SHAPE_QUALITY` / `WEIGHT_MASS_PARTICIPATION` + modal-universal axes `WEIGHT_*_MODAL`)
- Schema constants: `backend/app/services/reporting/_schema_versions.py::CASE_COMPLETENESS_SCHEMA_VERSION` (1.2.0 — Phase 12 B MINOR adds the four modal-specific axes); `CONVERGENCE_STUDY_SCHEMA_VERSION` (1.2.0 — Phase 12 A MINOR adds `modal` + `mode_count_sweep`)
- Modal cross-check module: `backend/app/domain/modal_extraction.py` (Phase 12 A — Euler-Bernoulli β·L SSOT, .dat parser, residual report, cumulative mass-participation utility)
- Trust-score downstream: `backend/app/services/reporting/trust_score.py::_score_convergence_axis` honors `convergence_kind` for `linear_static` and `modal` cases
- Advisor downstream: `backend/app/services/reporting/advisor_critique.py::StubAdvisor.produce` carries a `convergence_kind == "modal"` branch surfacing four named modal concerns + reading `context.extra["mode_count_target"]` (closes Phase 11 retro §2)
- Tests: `tests/test_phase11_analysis_type_rubric.py` (Phase 11 A); `tests/test_phase12_modal_extraction.py` (Phase 12 A); `tests/test_phase12_modal_advisor.py` (Phase 12 B — advisor branch + modal rubric substantiation pins)
- Blueprint dispositions: `.planning/FM-04A_PHASE11_BLUEPRINT.md` §3.A (Phase 11 A); `.planning/FM-04A_PHASE12_BLUEPRINT.md` §3.A / §3.B (Phase 12 A + B)
