# Phase 14 B TAA — slice audit

Commit: b72c507
Date: 2026-05-17
Auditor: independent general-purpose agent (Opus 4.7 1M, no prior knowledge of the implementation conversation)

## Scope

Slice B of FM-04a Phase 14: explicit_dynamics extraction service + 1D-bar wave-propagation analytical cross-check.

Artifacts reviewed:
* `.planning/FM-04A_PHASE14_BLUEPRINT.md` §3.B
* `.planning/methodology/explicit_dynamics_cross_check.md` (82 lines, new)
* `backend/app/services/reporting/explicit_dynamics_extraction.py` (342 lines, new)
* `tests/test_phase14_explicit_dynamics_extraction.py` (463 lines, 32 tests, new)
* `backend/app/services/reporting/case_completeness.py` (`ANALYSIS_TYPE_TUPLE` cross-reference)
* `.planning/phase14_audit_reports/A.md` (format precedent)

Verification:
* Slice test: **32 passed** in 0.10 s.
* Full backend sweep: **2350 passed, 7 skipped** in 22.62 s — matches blueprint baseline (2280 + 38 slice A + 32 slice B = 2350).
* Adversarial probes (below).

## Scores (sub-rubric, 63 pts)

**M (Methodology): 12/12** — Clean.

All four SSOT constants are correctly module-level, type-annotated, and named per the binding rubric:

* `WAVE_CROSS_CHECK_TOLERANCE_PCT: float = 5.0` (line 46)
* `EXPLICIT_DYNAMICS_CONVERGENCE_KIND: str = "explicit_dynamics"` (line 60)
* `ENERGY_PARTITION_EPSILON: float = 1e-9` (line 66)
* `ENERGY_PARTITION_DRIFT_FRACTION: float = 0.01` (line 71)

Each carries a load-bearing docstring. None is inline-declared at a use site. `EXPLICIT_DYNAMICS_CONVERGENCE_KIND` is verified to equal `ANALYSIS_TYPE_TUPLE[2]` by `test_explicit_dynamics_convergence_kind_matches_analysis_tuple` (line 68 of the test file) — the actual tuple in `case_completeness.py:79-84` is `("ballistic", "linear_static_pv", "explicit_dynamics", "modal")`, so index [2] is correct. Neither M cap fires. Score: **12/12**.

**T (Testing): 15/15** — Clean.

32 tests cover every binding surface:
* 4 SSOT constant pins (M:-2).
* Boundary-pinned analytical cross-check (T:-3): steel 200 GPa / 7850 kg/m³ → c≈5048 m/s and L=1m → t≈0.198 ms, both pinned with `math.isclose(..., rel_tol=1e-12)` against the closed form. Aluminum check is a bonus.
* Numerical defense on `bar_wave_speed_m_per_s` and `bar_wave_first_reflection_s` (non-positive inputs raise).
* `wave_propagation_residuals` contract: clean within tolerance, drifted out, negative-drift absolute-value, non-positive analytical / tolerance raise.
* Parser round-trips at 1 / 10 / 100 frames; str-path accepted.
* 8 dedicated defensive-raise tests (missing file, malformed JSON, non-object top-level, missing required key, inconsistent lengths, zero frame_count, non-positive frame_dt, out-of-range reflection index) — every one of the parser's 8 raise sites is pinned by a dedicated test.
* `energy_partition_audit`: clean balanced manifest, flagged non-physical injection, sub-epsilon drift treated clean, custom tolerance, dataclass default field round-trip.
* Slice-D bridge: 1m steel rod with frame_dt=10 µs lands first reflection at frame ~20 (analytical pin only, no fixture access).

Clean-vs-drifted energy audit explicitly distinguished by `test_energy_audit_clean_when_kinetic_plus_internal_equals_external` vs `test_energy_audit_flags_non_physical_injection`. No T cap fires. Score: **15/15**.

**C (Claims discipline / Coverage): 11/12** — Soft.

Module docstring (lines 1-34) carries the full Tier 1 disclaimer trio: "Tier 1 engineering candidate; not signed validation; not benchmark agreement." + enumerated NOT-claims (no real solver, not benchmark agreement, does not certify energy conservation) + explicit forbidden-wording enumeration in `no <token>` form. Methodology doc lines 1-7 carry the same disclaimer and add a per-sub-section "What the cross-check does NOT do" §.

The 1D-rod-vs-3D-solid distinction is cited explicitly in TWO places:
* Module docstring line 232 (`bar_wave_speed_m_per_s` docstring): "the elementary 1D-rod wave speed, NOT the bulk 3D dilatational speed (which is sqrt((K+4G/3)/rho))".
* Methodology doc § "Why 1D-bar (not 3D solid)" (lines 39-49): numeric comparison for steel (c_bar ≈ 5050 m/s, c_dilatational ≈ 5950 m/s, c_shear ≈ 3210 m/s) plus the "wrong formula catch" explanation.

Adversarial forbidden-token grep on the module + methodology doc returns only hits inside the `no <token>` enumeration block (module lines 28-33) — every hit is in the explicitly-allowed disclaimer form. No Tier-2 promoting language; every "Tier 2" occurrence is in `NOT Tier 2 benchmark` / `not Tier 2` / `no Tier-2-promoting language` form. C cap does not fire. **-1 for one weakness** — see LOW-1 below. Score: **11/12**.

**A (Anti-gaming / adversarial defense): 8/8** — Clean.

The parser raises BEFORE returning on every one of the 8 defensive surfaces, each with a dedicated test:

| Failure mode | Raise site | Test |
|---|---|---|
| Missing file | line 149 (`FileNotFoundError`) | `test_parser_raises_on_missing_file` |
| Malformed JSON | line 153 (`ValueError`) | `test_parser_raises_on_malformed_json` |
| Non-object top-level | line 157 | `test_parser_raises_on_non_object_top_level` |
| Missing required key | line 171 | `test_parser_raises_on_missing_required_key` |
| Inconsistent per-frame array lengths | line 183 | `test_parser_raises_on_inconsistent_array_lengths` |
| frame_count < 1 | line 189 | `test_parser_raises_on_zero_frame_count` |
| frame_dt <= 0 | line 194 | `test_parser_raises_on_non_positive_frame_dt` |
| Out-of-range reflection index | line 206 | `test_parser_raises_on_out_of_range_reflection_index` |

All 8 raises sit BEFORE the `return AnimationManifest(...)` at line 212. Numerical-defense raises also fire on `bar_wave_speed_m_per_s` / `bar_wave_first_reflection_s` / `wave_propagation_residuals` for non-positive inputs. A cap does not fire. Score: **8/8**.

**E (Evidence): 7/8** — Borderline.

* Methodology doc § "The 5% tolerance constant" explicitly cites `backend/app/services/reporting/explicit_dynamics_extraction.py` as the SSOT path (lines 30, 59).
* Bump-history policy is explicit and asymmetric: bumping DOWN requires retrospective + dispersion-model citation; bumping UP requires retrospective + paragraph naming the previously-unbudgeted physical effect (lines 36-37). "Slipping the tolerance to mask a real candidate drift is anti-pattern; the retrospective entry is the audit trail that prevents that" is exactly the audit-trail framing the rubric asks for.
* Cross-cite is asymmetric: the methodology doc cites the module path twice (lines 30, 59), but the module docstring does NOT cite the methodology doc path. A reader landing in `explicit_dynamics_extraction.py` has no in-source pointer to `.planning/methodology/explicit_dynamics_cross_check.md`. The cross-cite contract is half-satisfied. See LOW-2 below. Score: **7/8**.

**V (Verification): 8/8** — Clean.

* Slice tests: 32/32 PASSED in 0.10 s.
* Full backend sweep: **2350 passed**, 7 skipped (baseline 2280 + slice A 38 + slice B 32 = 2350, exact match).
* No regression introduced by the new module / methodology doc. V cap does not fire. Score: **8/8**.

## Total: 61/63

## Adversarial findings

**LOW-1 — Docstring index drift: module + methodology doc claim `ANALYSIS_TYPE_TUPLE[3]`, runtime is `[2]`.** The module docstring at line 64 says `EXPLICIT_DYNAMICS_CONVERGENCE_KIND ... MUST match ANALYSIS_TYPE_TUPLE[3]`, and the methodology doc at line 62 says `discriminator value matching ANALYSIS_TYPE_TUPLE[3]`. But the actual tuple in `backend/app/services/reporting/case_completeness.py:79-84` is `("ballistic", "linear_static_pv", "explicit_dynamics", "modal")` — index [2] = `"explicit_dynamics"`. The test `test_explicit_dynamics_convergence_kind_matches_analysis_tuple` correctly asserts `ANALYSIS_TYPE_TUPLE[2] == EXPLICIT_DYNAMICS_CONVERGENCE_KIND` and passes; the docstring + methodology doc are documentation drift, not a runtime bug. The binding M cap is on the discriminator string itself matching the tuple (it does, test verifies); the cap does NOT fire on docstring index references. **Fix:** change `[3]` → `[2]` in line 64 of the module docstring and line 62 of the methodology doc. Trivial 2-character edits. This is the most surprising finding because the test would have failed if the discriminator string were wrong, but a future contributor who reads the docstring and treats it as gospel could relocate the constant in the tuple based on the wrong index. -1 to C.

**LOW-2 — Module docstring does not cite the methodology doc by path.** The methodology doc cites the module path twice (lines 30, 59); the inverse is missing. A reader in `backend/app/services/reporting/explicit_dynamics_extraction.py` has no in-source pointer to `.planning/methodology/explicit_dynamics_cross_check.md`. The cross-cite is half-asymmetric. **Fix:** append one line to the module docstring: `See ``.planning/methodology/explicit_dynamics_cross_check.md`` for the SSOT methodology, the 1D-rod vs 3D-solid distinction, and the bump-history policy.` -1 to E.

**INFO — All forbidden-token grep hits are in disclaimer form.** Adversarial grep `grep -iE "validated against|perforation completed|bullet-through-steel complete|validated physics|production ready|certified|approved for service|asme compliant|signed off"` over the module + methodology doc returns 4 hits, all inside the explicit `no <token>` enumeration block at module lines 28-33 — the allowed disclaimer form. No drift; this is the test fixture for the forbidden-wording grep itself, correctly listing what is forbidden in `no <token>` syntax. No finding.

**INFO — 5050 m/s pin is real math.** `python -c "import math; print(math.sqrt(200e9/7850))"` → 5047.544651250688, matching the test bounds `5040.0 < c < 5060.0` and the methodology doc's "≈ 5050 m/s" claim. Not a hard-coded return. No finding.

## Verdict

**APPROVE_WITH_COMMENTS**

Stop-condition floors: M≥10, T≥12, C≥10, A≥6, E≥7, V≥7. Slice scores M=12, T=15, C=11, A=8, E=7, V=8 — every floor cleared with margin (only E sits exactly at floor, with a documented single fix).

Slice B target was 60+/63; achieved **61/63** (96.8%). Zero HIGH findings. Two LOW findings, both trivial to close:
1. LOW-1: change `[3]` → `[2]` in module docstring line 64 + methodology doc line 62 (2-character edit, restores C to 12/12).
2. LOW-2: append a one-line methodology-doc cross-cite to the module docstring (restores E to 8/8).

Post-fix projected score: **63/63**. Neither finding blocks slice-D fixture construction; both should be closed in the same commit that opens slice D (or as a trivial follow-up commit on the same branch) to keep the whole-arc 99/100 target reachable.

Slice B substantiates the fourth analysis-type axis exactly as the blueprint demanded: SSOT constants, boundary-pinned analytical cross-check, 8-surface defensive parser, clean-vs-drifted energy audit distinguished, full Tier 1 disclaimer discipline, methodology doc with explicit 1D-vs-3D distinction and asymmetric bump-history policy. The work is materially complete; the two LOW findings are cosmetic.
