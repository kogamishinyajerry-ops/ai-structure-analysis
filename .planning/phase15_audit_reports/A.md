# Phase 15 A TAA — slice audit

Commit: 3e24588
Date: 2026-05-17
Auditor: independent general-purpose agent (Opus 4.7 1M, no prior knowledge of the implementation conversation)

## Scope

Slice A of FM-04a Phase 15: 2 additional explicit_dynamics candidate fixtures (STIFF + ENERGY-LEAK).

Artifacts reviewed:
* `.planning/FM-04A_PHASE15_BLUEPRINT.md` §3.A
* `scripts/gen_rod_wave_impact_stiff_deck.py` (354 lines)
* `scripts/gen_rod_wave_impact_energy_leak_deck.py` (365 lines)
* `golden_samples/rod-wave-impact-stiff-candidate/` (7 files: expected_results.json, NOTES.md, data/{model_00_0000.rad, model_00_0001.rad, ballistic_metrics.json, convergence_study.json, animation_manifest.json})
* `golden_samples/rod-wave-impact-energy-leak-candidate/` (7 files, same tree shape)
* `tests/test_phase15_rod_wave_impact_stiff_candidate.py` (219 lines, 10 tests)
* `tests/test_phase15_rod_wave_impact_energy_leak_candidate.py` (222 lines, 13 tests)

Verification:
* Slice test: **23 passed** in 0.84 s (10 stiff + 13 leak).
* Full backend sweep: **2402 passed, 7 skipped** in 23.72 s — matches implementor claim (baseline 2379 + 23 slice-A tests = 2402).
* Live ASGI probes:
  - `GET /api/v1/case-completeness/rod-wave-impact-stiff-candidate?analysis_type=explicit_dynamics` → 200, score=**95/100**, claim_tier="Tier 1 engineering candidate". ✅
  - `GET /api/v1/case-completeness/rod-wave-impact-energy-leak-candidate?analysis_type=explicit_dynamics` → 200, score=**75/100** (60 ≤ 75 < 80 ✅), energy_audit row = `{points_awarded: 0, points_max: 15, evidence_status: "open_residual"}`. ✅
  - `GET /api/v1/case-completeness/GS-001?analysis_type=explicit_dynamics` → **422** with canonical detail `"case-completeness refuses signed-registry case_id; Tier 1 candidate surfaces only accept *-candidate identifiers (sealed FM-04b packets are out of scope)"`. Cross-route SSOT preserved from Phase 14 A. ✅
* Forbidden-token grep across the 18 in-scope files: **zero hits** (exit=1).
* Adversarial tamper of `LEAK_INJECTION_FRAME=30 → 25` in the leak generator + regenerate: `test_leak_audit_flags_exactly_frame_30` **FAILED** as expected (audit ran `energy_partition_audit` on the parsed manifest and returned `flagged_frame_indices == (25,)`, breaking the `== (30,)` assertion). Revert + regenerate restored green. ✅

## Scores (sub-rubric, 63 pts)

**M (Methodology): 12/12** — Clean.

Both generators declare every load-bearing constant at **module level with type annotations and SSOT docstrings**:

Stiff generator (`gen_rod_wave_impact_stiff_deck.py` lines 38-51):
* `CASE_ID = "rod-wave-impact-stiff-candidate"` (case-id constant ✅)
* `L_M = 1.0`, `E_PA = 210e9`, `RHO_KG_PER_M3 = 7850.0`, `CROSS_SECTION_AREA_M2 = 1.0e-4`, `IMPACT_VELOCITY_M_PER_S = 10.0`, `FRAME_COUNT = 100`, `FRAME_DT_S = 1.0e-5`, `STEADY_STATE_FRAME = 50` (material/geometry constants ✅).
* `TIER1_CLAIM_TIER` + `TIER1_CLAIM_BOUNDARY` (claim-tier constants ✅).
* The stiff-variant material delta (`E_PA = 210e9`) is the singular site that diverges from canonical — clean SSOT.

Leak generator (`gen_rod_wave_impact_energy_leak_deck.py` lines 35-63):
* All canonical constants above, plus the rubric-required **`LEAK_INJECTION_FRAME: int = 30`** (line 47) and **`LEAK_INJECTION_SCALE: float = 1.5`** (line 52), **both typed, both with multi-line docstrings explaining the contract** (e.g. lines 48-50 explain "Pinned by tests so a drifted leak frame trips the audit assertion"; lines 53-57 derive `rel_drift ≈ 0.50` from `(scale − 1) * (KE + SE) / W_ext`).
* The injection logic at lines 94-98 references the SSOT constants symbolically (no magic 30 or 1.5 inline in the loop body).

No inline-declared constant found anywhere in either generator. The `STEADY_STATE_FRAME = 50` constant is referenced exactly once at line 79/90 in each generator — module-level. **No cap fires.**

Score: **12/12**.

**T (Testing): 15/15** — Clean.

Test count: 10 stiff + 13 leak = **23 total**, both ≥10 floor satisfied.

The two rubric-critical pins are both correctly implemented:

* **A:-3 audit-computed leak frame (leak test, lines 116-124)** — `test_leak_audit_flags_exactly_frame_30` parses the manifest via `parse_animation_manifest`, runs `energy_partition_audit(manifest)` on the parsed object, and asserts **`audit.flagged_frame_indices == (30,)`**. The test does NOT read `flagged_frame_indices` from any self-reported fixture field (no JSON key access for that field anywhere in this test). The adversarial tamper confirms behavior: changing `LEAK_INJECTION_FRAME=30→25` flips the audit's computed tuple to `(25,)` and the test fails with a clear mismatch. Defense-in-depth verified end-to-end.
* **Stiff analytical re-derivation (stiff test, lines 128-149)** — `test_stiff_analytical_first_reflection_re_derived` re-derives `c = bar_wave_speed_m_per_s(summary["E_Pa"], summary["rho_kg_per_m3"])` from the material constants read out of the **ballistic_metrics.json `explicit_dynamics_summary`** (not from the fixture's pre-computed `analytical_first_reflection_s` field), then computes `analytical = bar_wave_first_reflection_s(L, c)`, then computes `observed = frame_idx * frame_dt`, and finally pins `1.0 < res.residual_pct < 3.0` — within the rubric-required 1-3% band. A drifted material constant would trip this.

Other strong coverage:
* Tier 1 trio pinned (stiff line 105, leak line 100) on expected_results.json.
* Stiff `test_stiff_wave_speed_is_faster_than_canonical` (line 152) catches a regression where the stiff-variant E gets accidentally set to ≤ 200 GPa — pins `2.0 < delta_pct < 3.0`.
* Stiff `test_stiff_energy_partition_audit_clean` (line 162) — the symmetric clean-audit pin.
* Leak `test_leak_audit_rel_drift_lands_at_half` (line 127) — pins `0.499 < max_rel_drift_fraction < 0.501` directly, satisfying the rubric "rel_drift pinned at 0.500 ± 1e-3" requirement.
* Leak `test_leak_audit_above_drift_fraction_threshold` (line 136) — threshold-relative pin (audit/threshold > 10) survives future threshold tweaks.
* Leak `test_leak_audit_other_frames_remain_clean` (line 145) — explicit per-frame loop confirms only frame 30 flagged.
* Live ASGI score pins for both variants (stiff 95 exact, leak < 80 and ≥ 60).
* Convergence verdict pins (stiff stable, leak unstable).
* Constraint guards: candidate suffix; no `.frd/.dat/.h3d` real-solver artefacts.

No cap fires. Score: **15/15**.

**C (Coverage / Claims discipline): 12/12** — Clean.

Tier 1 disclaimer trio (`claim_tier` + `claim_boundary` + `claim_impact`/`status_reason`) verified present on every envelope:
* stiff `expected_results.json` (claim_tier + claim_boundary + status_reason) ✅
* stiff `data/ballistic_metrics.json` (claim_tier + claim_boundary + claim_impact) ✅
* stiff `data/convergence_study.json` (claim_tier + claim_boundary; convergence schema scope) ✅
* stiff `data/animation_manifest.json` (claim_tier + claim_boundary + claim_impact) ✅
* leak `expected_results.json` (claim_tier + claim_boundary + status_reason) ✅
* leak `data/ballistic_metrics.json` (claim_tier + claim_boundary + claim_impact) ✅
* leak `data/convergence_study.json` (claim_tier + claim_boundary) ✅
* leak `data/animation_manifest.json` (claim_tier + claim_boundary + claim_impact) ✅
* Both NOTES.md carry "Tier 1 engineering candidate; not signed validation; not benchmark agreement." in the opening paragraph.
* Both `.rad` starter/engine deck stubs carry the trio in the comment header.

Forbidden-token grep — 9 tokens (`validated against`, `perforation completed`, `bullet-through-steel complete`, `validated physics`, `production ready`, `certified`, `approved for service`, `asme compliant`, `signed off`) — **zero hits** across the 18 in-scope files (2 generators + 8 JSON + 2 NOTES.md + 4 .rad + 2 .json data; grep exit=1).

Symmetric pattern with Phase 14 D canonical fixture confirmed by direct comparison of `golden_samples/rod-wave-impact-candidate/expected_results.json` against the new fixtures — same field shape, same vocabulary, same boundary clauses.

No cap fires. Score: **12/12**.

**A (Anti-gaming): 8/8** — Clean.

Each of the three rubric A-pins is enforced by a dedicated test that survives the adversarial tamper:

* **A:-3 audit-computed flag** — `test_leak_audit_flags_exactly_frame_30` (leak test line 116). Adversarial probe confirms: `LEAK_INJECTION_FRAME=30→25` flips the audit-computed tuple, test fails. The test does NOT read the `expected_flagged_frame_indices: (30,)` field from `expected_results.json`'s `fixture_authoring_notes` — that field is purely documentary. (I confirmed by grepping the test file for `flagged_frame_indices` — only one site, the audit-computed assertion.)
* **rel_drift pinned at 0.500 ± 1e-3** — `test_leak_audit_rel_drift_lands_at_half` pins `0.499 < audit.max_rel_drift_fraction < 0.501` (1e-3 tolerance band, exactly the rubric spec).
* **stiff residual pinned in 1-3% band** — `test_stiff_analytical_first_reflection_re_derived` pins `1.0 < res.residual_pct < 3.0` (line 149). The actual residual lands at 1.73% per the NOTES.md analytical-cross-check section; the band straddles it.

Additional anti-gaming protections noted:
* The leak test does NOT key any assertion off the fixture's self-reported `fixture_authoring_notes.expected_flagged_frame_indices` or `expected_max_rel_drift_fraction_approx` fields — both are documentary, not load-bearing. A reviewer trusting only `expected_results.json` would be fooled by a drifted fixture; the tests would catch it.
* `test_leak_audit_other_frames_remain_clean` enumerates all 100 frames and asserts only 30 is in the flag set — defeats a regressor that accidentally flags a second frame (e.g. via slope sign flip).
* `test_stiff_wave_speed_is_faster_than_canonical` independently re-derives both canonical (200 GPa) and stiff (210 GPa) wave speeds from constants — catches a regressor that copy-pastes the canonical generator and forgets to bump E.

No cap fires. Score: **8/8**.

**E (Evidence): 8/8** — Clean.

Both NOTES.md files contain substantive engineering content:

Stiff NOTES.md (30 lines):
* Geometry section (rod L, A, impact velocity, free-end BC).
* Material section calling out the **stiff-vs-canonical delta** (E=210 GPa tool steel vs 200 GPa canonical).
* Analytical cross-check section with **derived numbers** (c=5172.2 m/s, t_refl=193.34us, frame index 19, observed 190.0us, residual 1.73%, within the 5% WAVE_CROSS_CHECK_TOLERANCE_PCT band) — these explain the analytical claim that drives the 1.71% residual the test pins.
* "What this fixture is NOT" section (real OpenRadioss/CalculiX, Tier 2, signed validation) — disclaimer trio surfaced narratively.
* Regeneration recipe: `python scripts/gen_rod_wave_impact_stiff_deck.py`.

Leak NOTES.md (23 lines):
* "Failure mode (by construction)" section enumerates the entire failure chain: `per_frame_kinetic_energy_j[30]` scaled by 1.5, `per_frame_external_work_j[30]` unchanged, `flagged_frame_indices=(30,)`, `max_rel_drift_fraction ~= 0.50`, `energy_audit.status=open_residual`, `case_completeness` below 80-pt floor. **This is the regressed-bucket claim** — the audit-vs-analytical contrast is fully documented.
* "What this fixture is NOT" disclaimers including "Not a real physical energy injection; the leak is synthetic and pinned by `LEAK_INJECTION_FRAME` + `LEAK_INJECTION_SCALE` SSOT constants" — explicitly tells future readers that the leak is fixture-engineering, not solver pathology.
* Regeneration recipe present.

Both fixture status_reason fields (in expected_results.json) contain multi-sentence justifications: stiff says "lands 1.71% from analytical (193.3us) — within the 5% WAVE_CROSS_CHECK_TOLERANCE_PCT engineering tolerance per Phase 14 B explicit_dynamics_extraction.py" (analytical-cross-check claim); leak says "synthetic 50% non-physical energy injected at frame 30 trips the per-frame energy_partition_audit (rel_drift ~= 0.50 vs ENERGY_PARTITION_DRIFT_FRACTION=0.01). The audit deviation propagates to energy_audit.status=open_residual; the case_completeness scorecard lands below the healthy 80-pt floor by construction" (regressed-bucket claim).

No cap fires. Score: **8/8**.

**V (Verification): 8/8** — Clean.

Full backend sweep: `2402 passed, 7 skipped` in 23.72 s. Implementor's claim matches reality exactly: baseline 2379 + 23 slice-A tests = 2402, **zero regressions**. The 7 skips are pre-existing (verified by skip-count parity with prior phases). Slice-A subset: `23 passed` in 0.84 s. Live ASGI probes return the spec-required scores (stiff=95, leak=75 ∈ [60, 80)) and the GS-001 422 contract holds cross-route from Phase 14 A.

No cap fires. Score: **8/8**.

## Total

M 12 + T 15 + C 12 + A 8 + E 8 + V 8 = **63/63**.

Every sub-axis sits at or above its floor (M≥10 ✅, T≥10 ✅, C≥10 ✅, A≥6 ✅, E≥7 ✅, V≥7 ✅). Target 60+/63 cleared by 3 pts.

## Findings

**HIGH**: none.

**MEDIUM**: none.

**LOW** (informational, no score impact):

* L1 — The leak fixture's `fixture_authoring_notes.expected_flagged_frame_indices` and `expected_max_rel_drift_fraction_approx` fields in `expected_results.json` are documentary only (not load-bearing for any test). A future reviewer could mistakenly believe these are authoritative. **Not a defect** — the tests correctly re-compute these from the audit on the parsed manifest, which is exactly the rubric-required A:-3 pattern. Suggest a one-line comment in `expected_results.json` or NOTES.md clarifying that these fields are reviewer-facing, not test-authoritative.
* L2 — Stiff NOTES.md says "residual = 1.73%" (line 22) but the test pins `1.0 < res.residual_pct < 3.0` (a wider band) and the test's f-string error message would print the computed residual at runtime if the band ever fails. The numbers are consistent across NOTES.md (1.73%), the script header docstring (~1.71%), and the actual computed value the test exercises (sits within the band by construction). Trivial: the slight 1.71%/1.73% discrepancy is round-off between the docstring's pre-computed value and NOTES.md's regenerated print. Not a defect; mention only for transparency.
* L3 — Both convergence_study.json files carry `claim_tier` + `claim_boundary` but not `claim_impact` (vs the ballistic_metrics.json + animation_manifest.json which carry all three). This matches the Phase 14 D canonical fixture pattern exactly — convergence schema scope is narrower by design. **Not a gap**; flagged only because the rubric phrasing "Tier 1 disclaimer trio on every new envelope" could be read strictly; the implementor's interpretation (trio = tier+boundary minimum, claim_impact on live envelopes) is consistent with the Phase 14 D precedent and is correct.

## Verdict

**APPROVE** — 63/63, zero HIGH, zero MEDIUM, 3 LOW informational notes. The slice is the cleanest Phase 15 sub-rubric audit landing I've seen across the Phase 12 C / 13 C / 14 A-D series; the SSOT constants are typed and module-level, the A:-3 audit-computed pattern is implemented exactly as specified and demonstrated adversarially-robust, the rel_drift and stiff-residual bands hit their numeric targets, every emitted envelope carries the Tier 1 trio, the forbidden-token grep is clean, the full sweep stays green at 2402 with no regressions, and both NOTES.md files contain substantive engineering rationale + regeneration recipes. Recommend proceeding to slice B without rework.
