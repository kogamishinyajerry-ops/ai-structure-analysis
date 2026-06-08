# Phase 15 C TAA — slice audit

Commit: 7efc3ba
Date: 2026-05-17
Auditor: independent general-purpose agent (no prior knowledge of the implementation conversation)

## Scope

Read all in-scope slice-C artefacts independently:

* `backend/app/services/reporting/trust_score_drift_attribution.py` (NEW SSOT module, 221 LOC)
* `backend/app/services/reporting/_schema_versions.py` (verified MINOR bumps on TRUST_SCORE_ALERTS_SCHEMA_VERSION 1.0.0 → 1.1.0 and TRUST_SCORE_TIMELINE_SCHEMA_VERSION 1.0.0 → 1.1.0 with bump-history docstrings citing Phase 15 C · 2026-05-17 and Phase 14 retro §1 closure)
* `backend/app/services/reporting/trust_score_alerts.py` (wires DriftAttribution; imports helper)
* `backend/app/services/reporting/trust_score_timeline.py` (wires `inter_snapshot_drift_attribution` tuple; imports helper)
* `tests/test_phase15_trust_score_drift_attribution.py` (20 tests covering M:-2, T:-3, A:-2, C:-8 anti-gaming guards)
* `tests/test_phase7_trust_score_alerts.py` (test renamed 1_0_0 → 1_1_0 at line 137)
* `.planning/methodology/trust_score_drift_attribution.md` (74-line methodology doc with bump policy + "what this does NOT do")

## Verification log

1. Full sweep: `uv run pytest tests/ -q --no-header` → **2433 passed, 7 skipped, 3 warnings in 25.78s** — matches expected count exactly.
2. Slice-C tests: `uv run pytest tests/test_phase15_trust_score_drift_attribution.py -v --no-header` → **20/20 PASSED in 0.19s**.
3. Manual trace of `compute_drift_attribution`:
   * energy_audit 15→0 → `delta_weighted = -15.0`, `delta_pct = 100.0 * -15 / 15 = -100.0` ✓; `abs(-100.0) > 5.0` → dominant_axis = "energy_audit", dominant_delta_pct = -100.0 ✓
   * completeness 50→42 → `delta_weighted = -8.0`, `delta_pct = 100.0 * -8 / 50 = -16.0` ✓; `abs(-16.0) > 5.0` → dominant_axis = "completeness" ✓
4. Floor semantic verified at line 192: `if max_abs <= dominant_floor_pct:` → confirms strict-exceed; module docstring (line 13-14) and methodology doc §"The 5.0% dominant-axis floor" both say "STRICTLY EXCEED" / "absolute delta_pct `<= 5.0%` is NOT counted as dominant" — three SSOTs aligned.
5. Back-compat: new field `drift_attribution` on `TrustScoreAlertEvent` and `inter_snapshot_drift_attribution` on `TrustScoreTimeline` are additive; pre-1.1.0 consumer dropping unknown fields keeps reading all existing 1.0.0 fields (schema_version, claim_tier, claim_boundary, claim_impact, alerts/axis_deltas/severity/primary_axis_shift on alerts; points/trust_score/axis-weighted on timeline). Confirmed by reading `_event_to_dict` + `_timeline_to_dict`.
6. Forbidden-token grep on new module + methodology doc: 5 occurrences in module (lines 24, 32, 33, 34, 35) — every one in `not <claim>` or ``` no ``<claim>`` ``` form within the "Forbidden wording" docstring header; doc has zero occurrences. Already pinned by `test_no_forbidden_positive_claims_in_new_module`.
7. Tier 1 disclaimer trio (`claim_tier` + `claim_boundary` + `claim_impact`) preserved on both alerts + timeline envelopes (verified at the dataclass def + builder + render-dict layers).

## Adversarial probes

Ran 6 Python probes directly against the imported module (no file modifications, so nothing to revert):

| Probe | Expected | Actual | Result |
|---|---|---|---|
| 1. energy_audit 15→0 | delta_pct = -100.0, dominant = energy_audit | -100.0, energy_audit, -100.0 | PASS |
| 2. completeness 50→42 | delta_pct = -16.0, dominant = completeness | -16.0, completeness, -16.0 | PASS |
| 3. dominant_floor_pct=0.0 | ValueError | `dominant_floor_pct must be > 0; got 0.0` | PASS |
| 4. uniform drift (prev==curr) | dominant_axis=None, dominant_delta_pct=NaN, renders null | None, isnan=True, rendered null | PASS |
| 5. convergence 20→19 (exactly -5.0%) | dominant=None (strict-exceed) | -5.0, dominant=None | PASS |
| 6. TRUST_AXIS_WEIGHTS sum / floor value | 100 / 5.0 | 100 / 5.0 | PASS |

**No source modifications were made during probing.** All probing was via `uv run python -c "..."` against the imported module.

## Per-axis scoring (63 total)

| Axis | Cap | Score | Rationale |
|---|---|---|---|
| M | 12 | **12/12** | M:-1 ✓ schema MINOR 1.0.0→1.1.0 applied on both envelopes with bump-history docstrings citing Phase 15 C · 2026-05-17 + Phase 14 retro §1. M:-2 ✓ SSOT constants module-level + typed + named (`DRIFT_DOMINANT_AXIS_DELTA_FLOOR_PCT: float = 5.0` line 53, `TRUST_AXIS_WEIGHTS: Mapping[str, int]` line 70); both consumers IMPORT `compute_drift_attribution` + `render_drift_attribution_dict` from the SSOT module (alerts line 41-45, timeline line 116/337) with no inline percentage math. M:-3 ✓ floor value 5.0 documented in methodology doc §"The 5.0% dominant-axis floor" with full bump-up + bump-down policy. |
| T | 15 | **15/15** | T:-1 ✓ unit tests for boundary cases (uniform_subfloor / at_floor_exact / just_above_floor / positive_drift). T:-2 ✓ both schema-version pins at 1.1.0 (`test_alerts_schema_at_1_1_0`, `test_timeline_schema_at_1_1_0`, plus renamed `test_alerts_schema_version_is_1_1_0` in test_phase7). T:-3 ✓ exact-value pins (`test_energy_audit_collapse_lands_at_minus_100_pct` asserts `== -100.0`, `test_completeness_eight_pt_drop_lands_at_minus_16_pct` asserts `== -16.0`); strict-exceed pinned by `test_at_floor_exact_does_not_count_as_dominant`. T:-4 ✓ live end-to-end tests via `seeded_repo_for_drift` fixture that writes 2 cohort snapshots and verifies timeline carries `inter_snapshot_drift_attribution` length 1 and alerts dominant_axis = "energy_audit" / dominant_delta_pct = -100.0. T:-5 ✓ forbidden-token grep on the new module + doc covers all 9 tokens. |
| C | 12 | **12/12** | C:-1 ✓ Tier 1 disclaimer trio (`claim_tier`, `claim_boundary`, `claim_impact`) preserved on both envelopes — dataclass fields + builder kwargs + dict-render lines all wired (alerts 112-118, 240-241, 246, 277-278, 283; timeline 79-84, 143-144, 148, 343-344, 348). C:-2 ✓ 9-token forbidden grep with `not`/`no` prefix discipline still passes. C:-3 ✓ methodology doc §"What this surface does NOT do" lists 4 explicit non-claims (no root cause / no step-vs-slow classification / does not replace axis_deltas / does not certify Tier 2). C:-4 ✓ no new endpoints; no real solver / LLM; pure SSOT module + 2 envelope additions; advisor-not-driver posture preserved. |
| A | 8 | **8/8** | A:-1 ✓ MINOR (additive) on both envelopes — `drift_attribution` on event and `inter_snapshot_drift_attribution=()` default on timeline dataclass mean 1.0.0 consumers keep working; `render_drift_attribution_dict` renders `dominant_delta_pct` as JSON `null` when NaN (line 215-219). A:-2 ✓ defensive parser raises on (a) missing axes via `missing_prev`/`missing_curr` set diff (line 164-171); (b) unknown labels via `_validate_axes` line 110-114; (c) out-of-band values via `_validate_axes` line 121-125 (rejects negative AND > max_weight); (d) non-positive floor via line 155-158 (rejects `<= 0.0`). All 4 paths covered by `test_compute_raises_on_*` tests. A:-3 ✓ strict-exceed semantic explicit ("STRICTLY EXCEED" in module docstring + methodology doc + `<=` operator in code + dedicated test `test_at_floor_exact_does_not_count_as_dominant`). |
| E | 8 | **8/8** | E:-1 ✓ 5%-floor rationale tied to "noise across all axes" vs "one axis collapsed" in methodology §"The 5.0% dominant-axis floor". E:-2 ✓ cross-axis-comparable rationale tied to existing methodology corpus — methodology doc opens by contrasting weighted-point delta (15 on a 15-pt axis vs 15 on a 50-pt axis) and explains why percentage is the cross-axis-comparable signal; the alerts module docstring extends `TrustScoreAlertEvent.drift_attribution` field with a fully-worked example. E:-3 ✓ NaN→null rendering well-formed; verified by `test_render_dict_nan_becomes_null` (round-trips through `json.dumps`). |
| V | 8 | **8/8** | V:-1 ✓ slice closes Phase 14 retro §1 — bump-history docstring on both schema constants explicitly cites "Closes Phase 14 retro §1 (per-axis drift attribution surface)"; methodology doc reiterates this in the front matter. V:-2 ✓ methodology doc §"Reference" wires the surface to Phase 15 D reviewer journey ("explicit_dynamics drift triage"); the live E2E test seeds the leak case used by D's `dominant_axis == "energy_audit"` path. V:-3 ✓ forbidden-token + Tier 1 trio + HF1 path-guard discipline preserved (no writes outside `golden_samples/**/*-candidate/`; no signed-registry edits; no new endpoints added). |
| **Total** | **63** | **63/63** | |

## Verdict

**APPROVE** — Score 63/63, every axis at cap (well above the binding floor on each axis: M ≥10, T ≥10, C ≥10, A ≥6, E ≥7, V ≥7). Full test sweep stays at 2433 passed / 7 skipped. All 6 adversarial probes pass without source modifications.

## Open observations (non-blocking)

1. **Naming nit**: the inter-axis label mismatch between `axis_deltas` keys (`completeness` / `convergence_stability` / `energy_audit_closure` / `reproducibility_clean`) on the alarm event vs `drift_attribution.per_axis_delta_pct` keys (`completeness` / `convergence` / `energy_audit` / `reproducibility`) is intentional (the alerts payload uses the trust-score breakdown axis names; drift attribution uses the SSOT TRUST_AXIS_WEIGHTS keys) but a future reviewer reading the JSON side-by-side may briefly wonder why `convergence_stability` and `convergence` coexist. Methodology doc could pin this contrast in 1 sentence. Not blocking.
2. **`render_drift_attribution_dict`** mutates nothing but returns `dict(att.per_axis_delta_pct)` (line 213). Good defensive copy — a downstream mutation cannot reach back into the frozen dataclass.
3. **Phase 15 D handoff**: the `seeded_repo_for_drift` fixture is module-scoped and re-runs the leak-case generator at import time via `subprocess.check_call`. Phase 15 D's reviewer-journey tests can either consume the same fixture (move it to `conftest.py`) or accept the per-module re-run cost; current code is correct either way.
4. **Module-level `Mapping` import**: the typed alias `TRUST_AXIS_WEIGHTS: Mapping[str, int]` correctly enforces read-only view at the type-check layer; runtime mutation is still possible (it's a `dict` under the hood) — could harden with `MappingProxyType` if a future maintainer attempts in-place mutation, but not material for Tier 1 candidate work.
