# FM-04a Phase 14 D — TAA Audit Report

**Commit under audit:** `373ab88` on `claude/FM-04a-tier1-ballistic-candidate`
**Slice:** D — rod-wave-impact-candidate fixture + analytical cross-check
**Auditor posture:** independent adversarial review; no exposure to implementation conversation
**Binding rubric:** `.planning/FM-04A_PHASE14_BLUEPRINT.md` §3.D (63 pts total, axis floors M>=10/T>=10/C>=10/A>=6/E>=7/V>=7)

---

## Verdict: **APPROVE** (63/63 — zero findings)

All six axes pass at full points. Every blueprint-binding requirement substantiated by direct evidence.

---

## Scores per axis

### M (Methodology) — **12 / 12**
- `scripts/gen_rod_wave_impact_deck.py` is deterministic: pure-Python, no `random`, no `datetime.now`, no env-dependent reads. Verified by visual scan of all 379 LOC.
- Module-level SSOT constants present and named per spec: `CASE_ID`, `L_M`, `E_PA`, `RHO_KG_PER_M3`, `CROSS_SECTION_AREA_M2`, `IMPACT_VELOCITY_M_PER_S`, `FRAME_COUNT`, `FRAME_DT_S`, `STEADY_STATE_FRAME`, `TIER1_CLAIM_TIER`, `TIER1_CLAIM_BOUNDARY` (script lines 47-60).
- Generator writes BOTH the version-controlled `golden_samples/.../` self-documenting copy AND the gitignored `project_state/graph_executor/.../` route-readable copy from one source — guarantees no drift between reviewer-visible and route-visible bytes (`main()` lines 326-374).
- Fixture authoring notes (`expected_results.json` `fixture_authoring_notes` block + `NOTES.md` "Analytical cross-check" section) cite the closed-form 1D-bar formula `c = sqrt(E/rho)` / `t_refl = L/c` explicitly with numeric values.

### T (Testing) — **15 / 15**
- 17 tests delivered (target >= 10). `uv run pytest tests/test_phase14_rod_wave_impact_candidate.py -v` -> **17 passed in 0.57s**.
- Inventory tests (4): `test_fixture_directory_present`, `test_fixture_self_documenting_files_present`, `test_route_readable_files_present`, `test_generator_script_present`.
- Tier 1 trio + analytical claim_impact (4): `test_expected_results_carries_tier1_disclaimer_trio`, `test_expected_results_cites_analytical_cross_check`, `test_ballistic_metrics_carries_tier1_disclaimer_trio`, `test_convergence_study_is_explicit_dynamics_stable`.
- Animation cross-check (3): A:-3 anti-gaming test + parser round-trip + energy-partition clean.
- Live ASGI scorecard (2): >=80 floor + load-bearing axes full.
- Constraint guards (4): case_id shape, no real-solver artifacts, synthetic disclaimer, cross-route refusal regression-guard on GS-001.

### C (Coverage) — **12 / 12**
- Tier 1 disclaimer trio (claim_tier / claim_boundary / not-signed-validation language) verified present on every emitted JSON envelope: `expected_results.json`, `ballistic_metrics.json`, `convergence_study.json`, `animation_manifest.json` — all four carry the SSOT strings from `TIER1_CLAIM_TIER` / `TIER1_CLAIM_BOUNDARY`.
- Forbidden-token grep on all 7 GS-tracked files (NOTES.md, expected_results.json, 5 data/*) **clean** for: `validated`, `qualified`, `certified`, `production-ready`, `deployment-ready`, `sign-off`, `signoff`. Zero hits.
- Live ASGI response carries the trio: probe confirmed `claim_tier: "Tier 1 engineering candidate"`, `claim_boundary: "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"`.

### A (Anti-gaming) — **8 / 8** (KEY axis)
- The load-bearing `test_animation_manifest_first_reflection_matches_analytical` (lines 198-233) RE-DERIVES the analytical pin: it reads `E_Pa`, `rho_kg_per_m3`, `rod_length_m` from `ballistic_metrics.json`'s `explicit_dynamics_summary`, then calls `bar_wave_speed_m_per_s(E, rho)` + `bar_wave_first_reflection_s(L, c)` (Phase 14 B SSOT) to compute `analytical_t`.
- Observed time is computed as `int(manifest["first_reflection_frame_index"]) * float(manifest["frame_dt_s"])` — NOT trusted from the `observed_first_reflection_s` field. A drifted fixture (wrong rho, wrong L, wrong frame_dt) trips THIS assertion before any downstream consumer can rely on the wrong pin.
- Residual is gated by `wave_propagation_residuals(...).within_tolerance` against `WAVE_CROSS_CHECK_TOLERANCE_PCT` (5%). Verified independently: `c = 5047.545 m/s`, `t_refl = 198.116 us`, observed `200.0 us`, residual `0.9509%` — well within tolerance.

### E (Evidence) — **8 / 8**
- `NOTES.md` (27 lines) present with engineering content: geometry block, loading block, analytical cross-check block with numeric residual (0.95%), explicit "What this fixture is NOT" boundary block.
- Regeneration recipe present at NOTES.md line 27: `python scripts/gen_rod_wave_impact_deck.py`. Recipe verified: `rm -rf project_state/graph_executor/rod-wave-impact-candidate && uv run pytest tests/test_phase14_rod_wave_impact_candidate.py -q` -> **17 passed** (autouse fixture re-emits route-readable copies).
- Live ASGI lands **exactly 95/100** per blueprint construction: starter_deck 15+15, ballistic_metrics 20, energy_audit 15, convergence_study 15, generator_script 5, animation_manifest 5, notes 5; result_mesh 0/5 (expected absent for explicit_dynamics).

### V (Verification) — **8 / 8**
- Full backend sweep: `uv run pytest tests/ -q` -> **2379 passed, 7 skipped in 21.11s**.
- Matches blueprint baseline arithmetic: 2280 (pre-Phase-14) + 38 (A) + 32 (B) + 12 (C) + 17 (D) = 2379. **No regression.**

---

## Findings

**Zero HIGH. Zero MEDIUM. Zero LOW.**

The slice is unusually clean. Three positive observations:

1. The autouse module-scope `_ensure_fixture_regenerated` fixture (test file lines 60-85) elegantly closes the gitignored-route-readable-copy gap without requiring reviewers to run the generator manually. Regeneration recipe tested end-to-end.
2. Generator deterministically writes IDENTICAL bytes to both `golden_samples/` and `project_state/` trees from a single computed payload (single `ballistic = _ballistic_metrics()` etc., then two `.write_text()` calls per artifact). No drift possible by construction.
3. A:-3 anti-gaming defense correctly avoids the trap of trusting `observed_first_reflection_s` from the fixture — re-derives from the `frame_index * frame_dt` product, which is one indirection more honest than reading the seconds field.

---

## Verdict summary

**APPROVE** — 63/63, all axes at full points, zero findings, full sweep 2379 passed.
