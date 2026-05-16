# Explicit-dynamics 1D-bar wave-propagation analytical cross-check — SSOT methodology

> **Tier 1 engineering candidate; not signed validation; not benchmark agreement.**
>
> **Scope:** the analytical cross-check that pins the expected first-reflection time for an axial-impact 1D rod in any explicit-dynamics Tier 1 candidate case. Substantiates the fourth and final analysis type in `ANALYSIS_TYPE_TUPLE` (`explicit_dynamics`).
>
> **Status:** Phase 14 B. Closes v1 blueprint image #06 row 3 — the explicit_dynamics analysis-type substantiation gap carried forward from Phase 11 retrospective §A.

## Why this cross-check exists

Phase 11 A added the `explicit_dynamics` rubric entry to `case_completeness.py` `ANALYSIS_TYPE_RUBRIC_WEIGHTS`, but no real-runnable candidate case ever shipped. Phase 12 substantiated the modal axis with a cantilever beam analytical cross-check (`f_n = (k_n * L)^2 / (2*pi*L^2) * sqrt(E*I / (rho*A))`); Phase 14 substantiates `explicit_dynamics` with a 1D-bar wave-propagation cross-check.

The chosen analytical pin is the **first arrival of a stress wave at the far boundary of a 1D elastic rod under axial impact**:

```
c       = sqrt(E / rho)            # rod wave speed
t_refl  = L / c                    # one-way travel time
```

This is the classical 1D elastic-rod result (e.g., Achenbach §5.1, Graff §1.1). It applies when:

* The rod cross-section is small compared to its length (small Poisson coupling).
* The material is linear-elastic over the simulation horizon.
* No plasticity / damage / contact softening enters the response.

A Tier 1 candidate observed first-reflection that lands within ±5% of `t_refl` is "on the 1D-rod manifold". That is **not** a benchmark agreement; it is an engineering ballpark pin that catches grossly wrong material constants, off-by-one frame indexing, mis-stated units, or wave-speed mis-encoding.

## The 5% tolerance constant

`WAVE_CROSS_CHECK_TOLERANCE_PCT = 5.0` is a single SSOT constant at `backend/app/services/reporting/explicit_dynamics_extraction.py`. Bump history:

* **5.0** (Phase 14 B · 2026-05-17) — initial Tier 1 candidate value. Rationale: in canonical 1D-bar references the lateral-inertia (Pochhammer-Chree) correction is sub-1% for slender rods; an additional ~3-4% headroom covers (a) time-step quantization (`frame_dt` discretizes the reflection arrival), (b) finite-element dispersion of explicit integrators (~2% on 8-node hex meshes per Hughes §9.4), (c) small contact-stiffness softening on the impact face. 5% lands a clean candidate inside; a candidate at 12-20% deviation is a real engineering concern that the cross-check correctly surfaces.

Bumping the tolerance is a separate methodology step from bumping the explicit-dynamics envelope schema:

* **Bumping the tolerance down** (e.g., 5.0 → 3.0) requires a retrospective entry naming the consumer (which fixture now lands outside the band) AND citing the better dispersion model that justifies tightening.
* **Bumping the tolerance up** (e.g., 5.0 → 10.0) requires a retrospective entry AND a paragraph here explaining what physical effect was previously not budgeted for. Slipping the tolerance to mask a real candidate drift is anti-pattern; the retrospective entry is the audit trail that prevents that.

## Why 1D-bar (not 3D solid)

The 1D bar speed `c = sqrt(E/rho)` differs from the 3D bulk dilatational speed `c_d = sqrt((K + 4G/3)/rho)` because the 1D rod is free to contract laterally under axial load (Poisson coupling absent in the equation of motion). For steel (E=200 GPa, rho=7850 kg/m³, nu=0.30):

* `c_bar       ≈ 5050 m/s`
* `c_dilatational ≈ 5950 m/s` (uses bulk modulus)
* `c_shear     ≈ 3210 m/s`

A Tier 1 candidate fixture that reports a "wave speed" closer to 5950 m/s than 5050 m/s is using the wrong formula (or the wrong geometry); the cross-check correctly catches this even though the deviation is ~18%, well outside the 5% band.

The candidate fixture (`golden_samples/rod-wave-impact-candidate/` in slice D) is constructed as a 1D rod EXACTLY so the analytical pin applies. A future analysis class that needs the 3D dilatational speed must add its OWN methodology doc + cross-check; this doc covers ONLY the 1D-rod case.

## What the cross-check does NOT do

* It does NOT certify energy conservation. The companion `energy_partition_audit` checks per-frame kinetic + internal vs external work, but the audit fires a deviation flag only — it does NOT claim the solve is exact.
* It does NOT validate the underlying solver. Even if observed lands within 5% of analytical, that is one ballpark check, not a full V&V campaign.
* It does NOT replace the FM-04b sealed packet's role in benchmark agreement. The Tier 1 disclaimer trio on every emitted envelope ensures readers know this is a candidate ballpark pin, not a Tier 2 benchmark.

## Module surface (SSOT)

`backend/app/services/reporting/explicit_dynamics_extraction.py` exposes:

* `WAVE_CROSS_CHECK_TOLERANCE_PCT: float = 5.0` — SSOT tolerance.
* `EXPLICIT_DYNAMICS_CONVERGENCE_KIND: str = "explicit_dynamics"` — discriminator value matching `ANALYSIS_TYPE_TUPLE[3]`.
* `ENERGY_PARTITION_EPSILON: float = 1e-9` — float-arithmetic floor.
* `ENERGY_PARTITION_DRIFT_FRACTION: float = 0.01` — 1% relative-drift flag threshold.
* `parse_animation_manifest(path) -> AnimationManifest` — defensive parser.
* `bar_wave_speed_m_per_s(E_Pa, rho_kg_per_m3) -> float` — analytical wave speed.
* `bar_wave_first_reflection_s(L_m, c_m_per_s) -> float` — analytical first-reflection time.
* `wave_propagation_residuals(observed_s, analytical_s, tolerance_pct?) -> WaveResiduals` — residual + verdict.
* `energy_partition_audit(manifest, drift_fraction_tolerance?) -> EnergyPartitionAudit` — per-frame audit.

Every consumer that wants the tolerance constant MUST import from this module rather than inline-declaring its own value (anti-gaming guard M:-2 in the Phase 14 binding rubric).

## Anti-gaming guards pinned by tests

* **M:-2** — `WAVE_CROSS_CHECK_TOLERANCE_PCT` + `EXPLICIT_DYNAMICS_CONVERGENCE_KIND` are module-level SSOT constants; tests assert they live at the documented names and types.
* **T:-3** — boundary-pinned cross-check: `bar_wave_speed_m_per_s(200e9, 7850)` must land at ~5050 m/s (relative tolerance 1e-3); `bar_wave_first_reflection_s(1.0, 5050)` must land at ~0.000198 s (relative tolerance 1e-3).
* **A:-3** — defense in depth: the parser raises on missing keys, malformed JSON, inconsistent per-frame array lengths, frame_count ≤ 0, non-positive frame_dt, and out-of-range `first_reflection_frame_index` BEFORE returning the manifest. A future slice-D fixture that ships an inconsistent payload trips the parser, not a downstream silent miscount.
* **C:-8** — module docstring + methodology doc cite the 1D-rod-vs-3D-solid distinction explicitly; no Tier-2-promoting language.

## Reference

Slice D builds the candidate fixture (`golden_samples/rod-wave-impact-candidate/`) on top of this cross-check. The Phase 14 retrospective at `.planning/retrospectives/fm04a_phase14_explicit_dynamics_substantiation.md` will document the closure of v1 blueprint image #06 row 3 by this slice.
