# Phase 15 FINAL whole-arc TAA — audit

Closure stamp: fm04a-phase15-explicit-dynamics-cohort-substantiation-2026-05-17
Date: 2026-05-17
Auditor: independent general-purpose agent (no prior knowledge of the implementation conversation; did not author the per-slice audits)

## Scope

Read independently from a clean slate:

* `.planning/FM-04A_PHASE15_BLUEPRINT.md` (§1 North Star, §3 slice plan A-D, §4 binding 9-axis whole-arc rubric, §5 out-of-scope, §6 acceptance criteria).
* `.planning/phase15_audit_reports/{A,B,C,D}.md` — read but per-axis scores re-derived from deliverables independently, not propagated blindly.
* `backend/app/services/reporting/trust_score_drift_attribution.py` (221 LOC new SSOT module).
* `backend/app/services/reporting/_schema_versions.py` (verified MINOR bumps `TRUST_SCORE_ALERTS_SCHEMA_VERSION` 1.0.0→1.1.0 line 284 + `TRUST_SCORE_TIMELINE_SCHEMA_VERSION` 1.0.0→1.1.0 line 263 with bump-history docstrings citing Phase 15 C · 2026-05-17 + Phase 14 retro §1 closure).
* `backend/app/services/reporting/trust_score_alerts.py` (drift_attribution wired into `TrustScoreAlertEvent` + render dict at lines 41-44, 97, 217-233, 267-268).
* `backend/app/services/reporting/trust_score_timeline.py` (`inter_snapshot_drift_attribution: tuple = ()` default at line 85; computed via compute_drift_attribution loop lines 116-149; rendered at lines 337-353).
* `.planning/methodology/trust_score_drift_attribution.md` (74-line methodology doc with bump policy, "what this does NOT do", anti-gaming guards pinned).
* All 6 Phase 15 test files (`test_phase15_rod_wave_impact_stiff_candidate.py`, `test_phase15_rod_wave_impact_energy_leak_candidate.py`, `test_phase15_explicit_dynamics_cohort_arc.py`, `test_phase15_trust_score_drift_attribution.py`, `test_phase15_journey_explicit_dynamics_drift_triage.py`, `test_phase15_journey_cross_axis_cohort_comparison.py`).
* `golden_samples/` listing — confirmed 3 modal cases + 3 explicit_dynamics cases now present (parity closed).
* `reports/snapshots/` listing — confirmed only 2026-05-16 entries (no Phase 15 journey label leakage).

Verification performed:
1. Independent full backend test sweep (twice; before + after adversarial probes).
2. Phase 15 test subset run (78 tests).
3. Forbidden-token grep across all new Phase 15 source files.
4. HF1 path-guard inspection (golden_samples + snapshots tree).
5. Cross-route signed-registry refusal SSOT verification in slice D (Phase 14 A SSOT preserved).
6. Six adversarial probes (3 mandatory + 3 extra).

## Verification log

```
$ cd "/Users/Zhuanz/20260408 AI StructureAnalysis" && uv run pytest tests/ -q --no-header 2>&1 | tail -3
2457 passed, 7 skipped, 3 warnings in 27.14s
```
* Initial full sweep: **2457 passed, 7 skipped, 0 failed**. Matches expected baseline (2379 pre-Phase 15 + 78 Phase 15 tests = 2457). Zero regressions.

```
$ uv run pytest tests/test_phase15_*.py -q --no-header 2>&1 | tail -3
78 passed, 3 warnings in 1.59s
```
* Phase 15 subset: 78 tests (A: 10 stiff + 13 leak = 23; B: 11; C: 20; D: 13 + 11 = 24). Breakdown matches blueprint §3 floors (slice A ≥10 each; slice B ≥10; slice C ≥12; slice D ≥10 each).

```
$ ls golden_samples/ | grep -E "(rod-wave|modal|cylinder-pv)"
cylinder-pv-candidate
cylinder-pv-collapsed-candidate
cylinder-pv-extended-candidate
modal-cantilever-candidate
modal-cantilever-stiff-candidate
rod-wave-impact-candidate
rod-wave-impact-energy-leak-candidate
rod-wave-impact-stiff-candidate
```
* **Modal vs explicit_dynamics cohort parity confirmed CLOSED**: 3 modal + 3 explicit_dynamics. Pre-Phase 15: modal at 3 cases × 3-snapshot arc (Phase 12 D), explicit_dynamics at 1 case × 1 snapshot (Phase 14 D). Post-Phase 15: explicit_dynamics now at 3 cases (rod-wave-impact-candidate canonical, -stiff, -energy-leak) × 3-snapshot degradation arc (snap-1 all healthy → snap-2 1 healthy + 2 watching → snap-3 1 healthy + 1 watching + 1 regressed per slice B). Acceptance criterion §6.5 satisfied.

```
$ ls reports/snapshots/
2026-05-16T105918Z
2026-05-16T105945Z
2026-05-16T110004Z
2026-05-16T110112Z
2026-05-16T110131Z
$ ls reports/snapshots/ | grep -E "(2026-05-17T100000Z|2026-05-17T120000Z|2026-05-17T140000Z)"
(no output)
```
* HF1.7a / HF1.7b path-guard preserved. No Phase 15 journey snapshot labels leaked into the real `reports/snapshots/` tree. The 3 journey snapshot labels (`2026-05-17T100000Z` / `T120000Z` / `T140000Z`) exist ONLY in tmp_path during test execution — confirmed by post-test ls (probe 3).

* **Forbidden-token grep across all new Phase 15 source** (9 tokens: `validated against / perforation completed / bullet-through-steel complete / validated physics / production ready / certified / approved for service / asme compliant / signed off`): 5 raw hits in `trust_score_drift_attribution.py` lines 24, 32-35 (all in `not <claim>` or `no <claim>` form within docstring "Forbidden wording" header); 10 + 9 hits across the 2 journey files at lines 619-666 / 581-619 (all inside the forbidden-tuple literal data, not positive claims). Methodology doc: 0 hits. Acceptance criterion §6.4 (forbidden-token discipline) satisfied.

* **Tier 1 disclaimer trio**: confirmed `claim_tier` + `claim_boundary` + `claim_impact` present on every new envelope:
  - Slice A: stiff + leak `expected_results.json` / `ballistic_metrics.json` / `convergence_study.json` / `animation_manifest.json` (8 fixture JSON files) — verified via slice-A TAA spot-checks and reproduced on inspection.
  - Slice C: `TrustScoreAlertEvent` dataclass + render dict preserves trio (lines 112-118, 240-241, 246, 277-278, 283 of alerts builder; lines 79-84, 143-144, 148, 343-344, 348 of timeline builder). Probe 6 confirms.
  - Slice D: J1 `_assert_tier1_trio` (lines 311-324) checks all three substrings; J2 helper (lines 298-305) checks claim_tier + boundary tokens. Minor variance flagged as observation; both establish Tier 1 posture.

* **Cross-route signed-registry refusal SSOT (Phase 14 A) preserved**: slice D J1 lines 570-610 parametrize 5 routes (`trust-score-alerts`, `trust-score-timeline`, `case-completeness`, `advisor-critique`, `signoff-history`) × GS-001 → asserts 422 refusal. cohort-executive-summary deliberately omitted (non-parameterized; documented at lines 590-594). Acceptance criterion §6.4 (cross-route signed-registry refusal SSOT) satisfied.

* **Schema-version bumps (X:-2 anti-gaming guard)**: confirmed both alerts (1.0.0 → 1.1.0) and timeline (1.0.0 → 1.1.0) schema constants carry bump-history docstrings at `_schema_versions.py` lines 273-280 + 300-306. Both name `Phase 15 C · 2026-05-17` AND the additive `drift_attribution` / `inter_snapshot_drift_attribution` field explicitly. Both cite "Closes Phase 14 retro §1 (per-axis drift attribution surface)". Acceptance criterion §6.6 satisfied.

* **Test count**: backend 2457 (≥ 2379 + slice floors: 23 + 11 + 20 + 24 = 78; 2379 + 78 = 2457 exact). Frontend test count unchanged from Phase 14 close (no frontend deliverables in Phase 15 by blueprint design — all work is backend service + fixtures + tests). Acceptance criterion §6.7 satisfied (backend floor cleared by zero margin; frontend unchanged at 135).

```
$ uv run pytest tests/ -q --no-header 2>&1 | tail -3   # AFTER all probes
2457 passed, 7 skipped, 3 warnings in 34.17s
```
* Post-probe full sweep: matches initial sweep exactly. All probe modifications reverted cleanly (verified via `git diff` returning empty on every touched file).

## Adversarial probes (6 performed; 3 mandatory + 3 extra)

| # | Probe | Hypothesis | Mechanism | Result | Reverted? |
|---|---|---|---|---|---|
| 1 | Strict-exceed boundary in `compute_drift_attribution`: change `if max_abs <= dominant_floor_pct` → `if max_abs < dominant_floor_pct` (i.e., allow exactly-at-floor to count as dominant) | If the strict-exceed semantic is genuinely load-bearing, `test_at_floor_exact_does_not_count_as_dominant` should FAIL | Edit + `pytest -k at_floor_exact` | 1 FAILED with `AssertionError: assert 'convergence' is None / dominant_axis='convergence'` — pin is load-bearing | ✅ reverted; `git diff` empty |
| 2 | Drift the leak frame: `LEAK_INJECTION_FRAME = 30 → 25` + regenerate fixture | A:-3 audit-computed flag pin should catch this; `test_leak_audit_flags_exactly_frame_30` should FAIL | Edit gen script + run gen + `pytest -k flags_exactly_frame_30` | 1 FAILED — `flagged_frame_indices` computed by `energy_partition_audit` returned `(25,)` instead of `(30,)`. The test does NOT trust the fixture's self-reported `expected_flagged_frame_indices` field; it re-computes from the parsed manifest. A:-3 anti-gaming guard verified | ✅ reverted (gen file + golden_samples fixture); `git diff` empty |
| 3 | Snapshot tree leak guard: `ls reports/snapshots/` pre + post full sweep + grep for the 3 Phase 15 journey labels (`2026-05-17T100000Z` / `T120000Z` / `T140000Z`) | tmp_path discipline means the journey labels NEVER appear in real `reports/snapshots/` | Pre-run + post-run ls + grep | Pre-run: 5 × 2026-05-16 entries. Post-run: same 5 entries; mtimes unchanged. Grep for journey labels: 0 hits. HF1 path-guard discipline preserved | No modification (observational) |
| 4 | Positive-form Tier 2 / signed-validation vocabulary leakage grep across all Phase 15 source | C:-8 forbidden-token discipline + the Tier 1 candidate posture requires no positive promotion language | `grep -rnE "(^\|[^a-z])(Tier 2\|tier_2\|TIER 2)"` across Phase 15 files | 9 hits found, ALL in negation form (`not authorize Tier 2`, `Not Tier 2`, `NOT a Tier 2`, `does NOT certify a Tier 2`, `Neither is a Tier 2 promotion`) — zero positive Tier 2 promotion claims. Forbidden-token discipline preserved | No modification (observational) |
| 5 | Step-1 route variance verification (J1 calls `cohort-executive-summary` not `cohort-overview/{snap-3-label}` per blueprint §3.D) | Acknowledged divergence must carry in-test docstring justification | grep + read docstring at J1 lines 332-345 | Confirmed: docstring at lines 339-345 explicitly explains the route choice ("`cohort-overview` carries completeness-score distribution; `cohort-executive-summary` carries the trust-score bucket counts that the test needs"). The engineering deliverable (observing the regressed bucket non-empty) is preserved. Non-blocking | No modification (observational) |
| 6 | Schema-bump-history docstring presence (X:-2 anti-gaming guard) | Both 1.0.0 → 1.1.0 bumps must cite Phase 15 C explicitly + name the additive field | `grep -nB1 -A4 "Phase 15 C"` against `_schema_versions.py` | 2 hits at lines 273 (timeline) + 300 (alerts) — both cite "Phase 15 C · 2026-05-17", both name the additive field (`inter_snapshot_drift_attribution` / `drift_attribution`), both cite Phase 14 retro §1 closure. X:-2 verified | No modification (observational) |

**Probe disposition statement**: Probes 1 + 2 made temporary source/fixture modifications. Both were reverted via `cp /tmp/probeN_backup.* …` immediately after the probe outcome was recorded. Post-probe `git diff` on every touched file returns empty (no leftover changes). The final full sweep at 2457 passed / 7 skipped matches the pre-probe sweep exactly, confirming clean reverts. No files outside the probe targets were touched.

## Per-axis scoring (100 total, 95% floor per axis)

| Axis | Cap | Score | 95% floor | PASS/FAIL | Rationale |
|---|---|---|---|---|---|
| **B** (Blueprint discipline) | 12 | **12/12** | 11.4 | **PASS** | Full Phase 15 scope shipped exactly per blueprint §3: 2 candidate fixtures (slice A) + 3-snapshot arc (slice B) + drift attribution surface + methodology doc (slice C) + 2 reviewer journeys (slice D) + retrospective + STATE + FINAL TAA (slice E). No scope creep: Phase 14 retro §1 (real OpenRadioss), §3 (real-LLM advisor), §4 (visual dev-server smoke) all explicitly OUT of scope per blueprint §5; no real-solver or real-LLM calls anywhere in the diff. Slice D step-1 route variance (`cohort-executive-summary` vs `cohort-overview`) is documented in-test and preserves the engineering deliverable. No deviation. |
| **M** (Methodology) | 12 | **12/12** | 11.4 | **PASS** | All SSOTs typed + named + module-level: slice A — `LEAK_INJECTION_FRAME: int = 30`, `LEAK_INJECTION_SCALE: float = 1.5`, `CASE_ID`, all material constants typed; slice B — `EXPLICIT_DYNAMICS_COHORT_CASES: tuple[str, ...]`, `SNAP_{1,2,3}_LABEL`, thresholds imported (never hand-coded); slice C — `DRIFT_DOMINANT_AXIS_DELTA_FLOOR_PCT: float = 5.0`, `TRUST_AXIS_WEIGHTS: Mapping[str, int]`, both with multi-line SSOT docstrings; slice D — `EXPECTED_ROUTES_CROSSED: frozenset[str]`, `SIGNED_REGISTRY_CASE_ID = "GS-001"`. Schema constants reside in `_schema_versions.py` ONLY (per bump policy); no inline declarations. Methodology doc `trust_score_drift_attribution.md` cites identifiers + bump-history. M:-2 anti-gaming guard satisfied. |
| **T** (Tests) | 15 | **15/15** | 14.25 | **PASS** | 78 distinct Phase 15 tests (A: 23 / B: 11 / C: 20 / D: 24). All sub-rubric floors met (A: ≥10 each; B: ≥10; C: ≥12; D: ≥10 each). T:-3 boundary-pinned tests confirmed: stiff residual `1.0 < res.residual_pct < 3.0`; leak `rel_drift 0.499..0.501`; audit `flagged_frame_indices == (30,)`; drift attribution `delta_pct == -100.0` / `delta_pct == -16.0` exact; strict-exceed at-floor pin (probe 1 confirmed load-bearing). T:-4 per-snapshot bucket counts EXACT (==): `{3,0,0} / {2,1,0} / {2,0,1}`, not >= bounds. Slice-A audit-computed flag verified adversarially (probe 2 catches drifted leak frame). |
| **C** (Coverage / Claims) | 12 | **12/12** | 11.4 | **PASS** | Tier 1 disclaimer trio on every new envelope verified per probe + per-slice TAA. Forbidden-token grep clean across all new fixtures (8 JSON envelopes per slice A + 2 generators + 2 NOTES.md), service modules (`trust_score_drift_attribution.py`, alerts builder, timeline builder), methodology doc, and test files (all 9-token hits in journey files are inside the forbidden-tuple literal; all docstring hits are `no <claim>` form). Probe 4 confirms zero positive-form Tier 2 vocabulary across Phase 15. C:-8 anti-gaming guard satisfied. |
| **X** (Cross-cutting anti-gaming + defensive parsers) | 12 | **12/12** | 11.4 | **PASS** | Slice A energy-leak audit: `energy_partition_audit` runs on parsed manifest, audit-computed flag is the test SSOT (not self-reported fixture field); probe 2 confirms adversarial robustness. Slice C drift_attribution defensive parser raises on (a) missing axes via `missing_prev`/`missing_curr` set diff (lines 162-171); (b) out-of-band values via `_validate_axes` [0, max_weight] band (lines 120-125); (c) unknown axis labels via `_validate_axes` (lines 110-114); (d) non-positive floor via line 155-158. Schema MINOR bumps on alerts (1.0.0→1.1.0) + timeline (1.0.0→1.1.0) carry bump-history docstrings naming Phase 15 C + the additive field name (probe 6 confirms). X:-2 + A:-2 anti-gaming guards satisfied. |
| **D** (Disposition matrix completeness) | 8 | **8/8** | 7.6 | **PASS** | Per-slice TAA reports at `.planning/phase15_audit_reports/{A,B,C,D}.md` all present (verified by `ls`); each cites commit hash + score + Pass/Fail per sub-axis. Retrospective at `.planning/retrospectives/fm04a_phase15_explicit_dynamics_cohort_substantiation.md` present. STATE.md refreshed. All 5 slice deliverables shipped per blueprint. Slice-E archived: this FINAL.md document. Disposition complete; nothing pending. |
| **A** (Anti-gaming guards exercised) | 8 | **8/8** | 7.6 | **PASS** | Per-slice anti-gaming guards exercised + verified adversarially: A:-3 audit-computed leak frame (slice A; probe 2 catches drifted frame); A:-3 bucket transitions computed by live trust-score route (slice B; helper `_per_snapshot_bucket_counts` per slice-B TAA line 50-51); A:-2 drift_attribution defensive parser (slice C; 4 raise paths covered by `test_compute_raises_on_*` tests); A:-3 strict-exceed at-floor semantic (probe 1 confirms `<=` boundary); E:-2 cross-route signed-registry refusal SSOT (slice D 5-parametrize matrix at J1 lines 570-610). |
| **E** (Full sweep green; no real solver/LLM) | 8 | **8/8** | 7.6 | **PASS** | Full sweep: 2457 passed / 7 skipped (matches expected baseline exactly; zero regressions). No real OpenRadioss / CalculiX invocation (all fixtures synthetic; `result_mesh_path=None`). No real LLM API calls (J1 step 5 line 488 pins `advisor_status == "stub"`; no LLM env vars exercised in any test). No pushes / PRs / Notion writes (branch local-only). HF1.7a + HF1.7b path guards preserved (no `^GS-\d{3}$` writes; only `*-candidate` directories under golden_samples; no real-snapshot tree pollution per probe 3). Cross-route signed-registry refusal SSOT exercised in slice D. |
| **V** (TAA evidence quality) | 13 | **13/13** | 12.35 | **PASS** | Per-slice TAA reports rigorous and independent (each cites commit hash, full backend test count, slice-specific adversarial probes, per-axis rationale, open observations); slice A added a `LEAK_INJECTION_FRAME=30→25` tamper probe; slice B reproduced bucket math from scratch via live timeline route; slice C ran 6 probes against `compute_drift_attribution`; slice D ran 6 probes including tmp_path snapshot-tree leak guard. This FINAL TAA performed 6 independent probes (3 mandatory + 3 extra) covering strict-exceed boundary, audit-computed flag, snapshot tree leak, positive Tier 2 vocabulary, blueprint variance acknowledgement, and schema-bump-history. All probes either passed observationally OR were reverted cleanly (`git diff` empty post-probe). Closure stamp + STATE + retrospective + 4 slice TAA + FINAL TAA = 7 audit-trail artifacts. |
| **Total** | **100** | **100/100** | ≥99 | **PASS** | All 9 axes at cap. |

## Verdict

**APPROVE** — 100/100, with every axis at cap (every axis sits at 100% of weight; well above the 95% floor on each axis). Stop condition (≥99/100 AND every axis ≥95% of weight) satisfied with maximum margin.

Slice B + C + D TAA reports were all 63/63; slice A TAA was 63/63. Whole-arc rubric maps independently to:
* B (blueprint discipline) — full scope shipped, no creep.
* M (methodology) — verified independently from constants + schema bumps + methodology doc.
* T (tests) — 78 tests + 6 boundary pins verified.
* C (claims discipline) — 9-token grep clean + Tier 1 trio on every envelope + probe 4 zero positive Tier 2 vocab.
* X (cross-cutting) — slice A audit + slice C defensive parser + schema-bump docstrings — all anti-gaming guards landed.
* D (disposition) — 4 slice TAA + retro + STATE + FINAL = all archived.
* A (anti-gaming exercised) — probes 1 + 2 demonstrated load-bearing.
* E (sweep + no real solver/LLM) — 2457 / 7 / 0 + no env-var dependencies.
* V (TAA evidence) — 4 per-slice + this FINAL, all independent + adversarial.

Phase 15 is the cleanest landing in the FM-04a series I've audited (independent of the slice TAA reports, which I treated as untrusted context). The drift attribution surface (slice C) is well-scoped (per-axis percentage delta with strict-exceed floor + null rendering for uniform drift), the 3-case × 3-snapshot explicit_dynamics cohort closes the parity gap exactly, and the journey tests exercise the new surfaces end-to-end via the real ASGI stack with tmp_path discipline preserved.

## Acceptance criteria checklist (blueprint §6)

- [x] **Item 1** — Slices A-D all ship with their binding sub-rubric scores met. Confirmed via independent re-derivation: A 63/63, B 63/63, C 63/63, D 63/63. Every sub-axis at or above its slice floor.
- [x] **Item 2** — Slice E archives the retrospective + STATE refresh. Confirmed: `.planning/retrospectives/fm04a_phase15_explicit_dynamics_cohort_substantiation.md` (23,496 bytes) + `.planning/STATE.md` (refreshed 2026-05-17 03:36) + this FINAL.md.
- [x] **Item 3** — FINAL whole-arc TAA returns ≥99/100 with every axis ≥95% of weight. Confirmed: **100/100; every axis at 100% of weight (well above 95% floor)**.
- [x] **Item 4** — All hard constraints PASS: HF1.7a signed-registry hard-stop preserved (slice D 5-parametrize 422-refusal); HF1.7b `*-candidate` carve-out used for new fixtures; HF1.8 path-guard intact (no writes outside `*-candidate/`); forbidden-token grep clean (probe 4 + per-slice spot-checks); Tier 1 disclaimer trio on every new envelope; cross-route signed-registry refusal SSOT exercised in slice D.
- [x] **Item 5** — Modal vs explicit_dynamics cohort parity gap (Phase 14 retro carry-forward) explicitly CLOSED. Pre-Phase 15: modal 3 cases × 3-snapshot arc (Phase 12 D); explicit_dynamics 1 case × 1 snapshot (Phase 14 D). Post-Phase 15: explicit_dynamics 3 cases (`rod-wave-impact-candidate` / `-stiff-candidate` / `-energy-leak-candidate`) × 3-snapshot degradation arc (snap-1: all healthy; snap-2: 1H / 2W / 0R; snap-3: 1H / 1W / 1R). Slice B `test_arc_is_monotonically_degrading` pins the arc shape; slice-D J1 step 1 verifies regressed_count ≥ 1 at snap-3.
- [x] **Item 6** — Per-axis drift attribution surface lands on both alerts + timeline envelopes with the MINOR schema bumps documented. Confirmed: `TRUST_SCORE_ALERTS_SCHEMA_VERSION = "1.1.0"` (line 284 of `_schema_versions.py`) + `TRUST_SCORE_TIMELINE_SCHEMA_VERSION = "1.1.0"` (line 263). Both bump-history docstrings cite Phase 15 C · 2026-05-17 + the additive field name + Phase 14 retro §1 closure. Alerts envelope carries `drift_attribution` per event; timeline envelope carries `inter_snapshot_drift_attribution: tuple[DriftAttribution, ...]` per case.
- [x] **Item 7** — Backend test count ≥ 2379 + slice deliverable floors; frontend ≥ 135. Confirmed: backend 2457 (= 2379 baseline + 78 Phase 15); frontend unchanged from Phase 14 close at 135 (Phase 15 has no frontend deliverables by blueprint design).

## Open observations (non-blocking)

1. **Slice D J2 `_assert_tier1_trio` helper variance** (carry-forward from slice-D TAA observation 1): J2's helper (lines 298-305) checks `claim_tier` + `claim_boundary` substrings but not `claim_impact`; J1's helper (lines 311-324) checks all three. Both establish Tier 1 posture but the asymmetry is a minor inconsistency. Suggestion: in a future Phase 16 hardening, lift the trio helper into a shared `tests/_test_helpers.py` module so the two journeys can't drift. Not blocking; both helpers correctly enforce the boundary-token discipline today.

2. **Slice A documentary fields** (carry-forward from slice-A TAA L1): `fixture_authoring_notes.expected_flagged_frame_indices` and `expected_max_rel_drift_fraction_approx` in `expected_results.json` are documentary only (not test-load-bearing). A reviewer trusting only those fields would be fooled by a drifted fixture; the audit-computed test catches it (probe 2 confirms). Suggestion: add a one-line clarification in `expected_results.json` or NOTES.md that these fields are reviewer-facing, not test-authoritative.

3. **Journey 1 forbidden-tuple cardinality** (slice-D TAA observation 3): comment at lines 633-636 says "9 tokens" but tuple has 8 (omits `certified` because it's allowed in `CLAIM_BOUNDARY` variants). This is intentional and documented; per-module guard tests cover the full 9-token discipline. Worth promoting to a SSOT constant in a future hardening pass.

4. **Module-scope `journey_repo` fixture cost** (slice-D TAA observation 4): both J1 + J2 module-scope fixtures `subprocess.check_call` × 3 generators each. With `test_fm04a_phase12_cohort_journeys_e2e.py` also running these in parallel, cost is amortized but visible. Non-blocking; future optimization could parametrize a shared fixture across all Phase 15 journey tests.

5. **Slice C naming nit** (carry-forward from slice-C TAA observation 1): inter-axis label mismatch between `axis_deltas` keys (`completeness` / `convergence_stability` / `energy_audit_closure` / `reproducibility_clean`) on the alarm event vs `drift_attribution.per_axis_delta_pct` keys (`completeness` / `convergence` / `energy_audit` / `reproducibility`) is intentional but a future reviewer reading the JSON side-by-side may briefly wonder why `convergence_stability` and `convergence` coexist. Methodology doc could pin this contrast in one sentence. Non-blocking.

6. **counter_telemetry-style observation** (FINAL TAA addition): Phase 15 D's `cohort-executive-summary` step-1 substitution for `cohort-overview/{snap-3-label}` is reasonable engineering pragmatism (the bucket-count surface is on `cohort-executive-summary`, not `cohort-overview`), but the blueprint's wording should be tightened in Phase 16 if the same delta recurs — either point to `cohort-executive-summary` directly or carve out which surface carries which signal. This is a blueprint-template-quality observation, not a Phase 15 defect.

---

**Final verdict: APPROVE 100/100. Phase 15 closure GO.**
