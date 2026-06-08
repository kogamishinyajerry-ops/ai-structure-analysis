# Phase 16 D slice TAA — APPROVE — 63/63

Commit: `02b3862`
Branch: `claude/FM-04a-tier1-ballistic-candidate`
Date: 2026-05-17
Auditor: independent Test Auditor Agent (TAA), no prior implementation context

## Scope

Files read independently against the binding §3.D 6-axis sub-rubric:

* `tests/_test_utils/__init__.py` (SSOT module, 146 lines, 4 exports).
* `tests/test_phase16_journey_drift_audit_trail.py` (Journey 1; 8 `def test_` + 1 3-way parametrized = 10 tests).
* `tests/test_phase16_journey_cumulative_vs_consecutive_drift.py` (Journey 2; 10 tests).
* `tests/test_phase16_test_utils_ssot.py` (meta-test; 11 tests).
* 5 edited Phase 15+ files (cross_axis_cohort_comparison / explicit_dynamics_drift_triage / trust_score_drift_attribution / cohort_drift_attribution / cumulative_drift_attribution).
* Slice-C TAA report `.planning/phase16_audit_reports/C.md` confirmed present alongside.

Slice-D test surface (31 tests) is GREEN in isolation; full Phase 15+16 sweep (148 tests) is GREEN combined.

## Per-axis score table

| Axis | Score | Cap | Evidence |
|---|---|---|---|
| **M (SSOT discipline)** | 12 | 12 | `tests/_test_utils/__init__.py` cleanly exports the 4 canonical names (8/9-tuples + `assert_tier1_trio` + `assert_no_forbidden_positive_claims`); meta-test §test_no_phase15_plus_file_inlines_forbidden_token_tuple + §test_no_phase15_plus_file_inlines_trio_audit_helper enforce no inline duplication; 5 Phase 15+ files refactored to consume SSOT (verified via grep `from tests._test_utils`). Thin-wrapper carve-out in `test_phase15_journey_cross_axis_cohort_comparison.py:304-314` delegates to `assert_tier1_trio(envelope, check_impact=False)` for the PV rubric path. |
| **T (boundary pinning)** | 15 | 15 | `==` pins (not `>=`) for `dominant_axis=="energy_audit"`, `dominant_case_id==LEAK_CASE_ID`, `cohort_max_abs_delta_pct==100.0`, `dominant_delta_pct==-100.0`, snapshot labels `==SNAP_1_LABEL`/`SNAP_2_LABEL`/`SNAP_3_LABEL`. Journey 2 exercises TWO arc shapes (stuck `("clean","clean","regressed")` + recovery `("clean","regressed","clean")`) with the cumulative-vs-per-pair invariant pinned on both. Route contract pinned as `EXPECTED_ROUTES_CROSSED` `frozenset({"cohort-anomalies","trust-score-timeline","signoff-history-GET","signoff-history-POST"})` — set equality + len==4. Probe 1 confirmed pins TRIP when drift halved. |
| **C (Tier 1 trio + forbidden token)** | 12 | 12 | Every 200 envelope inspected via SSOT `assert_tier1_trio(body)` in Journey 1 steps 1/2/3/5 + Journey 2 steps 1/2/3/8; forbidden-token grep on all 3 GET envelopes (concatenated) via SSOT `assert_no_forbidden_positive_claims`; Probe 6 runtime-confirmed `claim_tier=="Tier 1 engineering candidate"` AND `not_signed_validation` + `not_benchmark_agreement` in `claim_boundary` on every envelope. No bare positive-claim token outside negated form in either journey file (forbidden tokens appear only in the SSOT module + meta-test where they are legitimately data/inputs). |
| **A (anti-gaming)** | 8 | 8 | Per-route signed-registry 422-refusal `@pytest.mark.parametrize` matrix covers 3 cases — `GET trust-score-timeline / GET signoff-history / POST signoff-history` (Probe 5 collected exactly 3); cohort-anomalies omission documented in docstring (lines 609-612). Meta-test rejects local helper defs without SSOT delegation (Probe 4). Probe 8 confirmed `inspect.signature(write_signoff_record).parameters` has no `drift_attribution_at_signoff_time`; forged kwarg raises TypeError. Defensive parser `dominant_floor_pct > 0` preserved (`backend/app/services/reporting/trust_score_drift_attribution.py:155-158`). |
| **E (LLM-offline-first / no real solver)** | 8 | 8 | No OpenRadioss / `subprocess` solver invocation in either journey — only `subprocess.check_call` on `scripts/gen_*_deck.py` which are pure-Python fixture generators (verified by reading import block + body). No `openai` / `anthropic` / real-LLM call. ASGI walk uses `httpx.ASGITransport(app=app)` in-process. 4-Q gate: AI surfaces are advisory; no journey step writes verdicts via AI. |
| **V (snapshot tree containment)** | 8 | 8 | Every `write_cohort_snapshot(..., repo_root=tmp, ...)` call uses the module-scoped `tmp_path_factory.mktemp(...)` fixture; route patching via `monkeypatch.setattr(route_module, "_repo_root", lambda r=journey_repo: r)`. Probe 9 confirmed `reports/snapshots/` + `golden_samples/*-candidate/` byte-identical before/after running the 31 slice-D tests. HF1.7a (`^GS-\d{3}$` blocked) + HF1.8 (path-guard) preserved; `GS-001` only appears as 422-refusal probe shape. |

**Stop condition**: ≥ 60/63 AND every axis ≥ 95% of weight — MET (63/63 exact, every axis at cap).

## Probe results (10)

1. **Boundary-pin survival (drift × 0.5 monkeypatch)** — PASS. Cumulative pin `dominant_delta_pct == -100.0` tripped with `assert -50.0 == -100.0` failure in Journey 1 Step 2 + Journey 2 Step 1. Cohort Step 1 pin on `cohort_max_abs_delta_pct == 100.0` is by-design independent of `dominant_delta_pct` (it sources from `per_axis_delta_pct`, not scaled by the probe), confirming pins are surface-specific and load-bearing.
2. **SSOT meta-test fingerprint sensitivity (5/9 tokens in tuple-shape)** — PASS. 5-token tuple offender classified as offender (hits=5 ≥ threshold=5); 4-token below-threshold case NOT classified.
3. **SSOT meta-test thin-wrapper acceptance** — PASS. `def _assert_tier1_trio(env): assert_tier1_trio(env, check_impact=False)` + `from tests._test_utils import assert_tier1_trio` → `is_offender == False`.
4. **SSOT meta-test body-inlined rejection** — PASS. `def _assert_tier1_trio(envelope): assert envelope["claim_tier"] == "Tier 1 engineering candidate"; ...` without SSOT import → `is_offender == True`.
5. **Per-route 422 refusal exhaustive** — PASS. `pytest --collect-only` shows 3 parametrized cases: `GET-/api/v1/trust-score-timeline/{cid}` / `GET-/api/v1/signoff-history/{cid}` / `POST-/api/v1/signoff-history/{cid}`. Cohort-anomalies omission documented in test docstring.
6. **Tier 1 trio runtime preservation** — PASS. Independent journey_repo build (probe6_trio_runtime.py) confirmed `claim_tier=="Tier 1 engineering candidate"` AND `claim_boundary` carries `not_signed_validation` + `not_benchmark_agreement` on cohort-anomalies + trust-score-timeline + signoff-history GET envelopes.
7. **SSOT helper `check_impact=False` knob** — PASS. `assert_tier1_trio({...no claim_impact...}, check_impact=False)` does NOT raise; same envelope with `check_impact=True` raises `AssertionError: claim_impact missing tokens: ''`.
8. **A:-3 server-computed pin on write_signoff_record** — PASS. `inspect.signature(write_signoff_record).parameters` = `['case_id', 'reviewer', 'verdict', 'notes', 'repo_root', 'now_utc']` — `drift_attribution_at_signoff_time` ABSENT. Forged kwarg raises `TypeError: write_signoff_record() got an unexpected keyword argument 'drift_attribution_at_signoff_time'`.
9. **`reports/snapshots/` NOT mutated** — PASS. `find reports/snapshots -type f | sort` AND `find golden_samples -maxdepth 1 -type d | sort` byte-identical before/after `pytest tests/test_phase16_journey_drift_audit_trail.py tests/test_phase16_journey_cumulative_vs_consecutive_drift.py tests/test_phase16_test_utils_ssot.py`. No `2026-05-17T*` labels in real snapshots tree.
10. **Cross-arc-shape invariant (recovery arc)** — PASS. Independent build of `(clean, regressed, clean)` arc on tmp_path → `cumulative_drift_attribution.dominant_axis is None` AND `per_pair[0].dominant_axis == "energy_audit"` AND `per_pair[1].dominant_axis == "energy_audit"`. Phase 16 A docstring's "20→10→20 recovery" semantic preserved on real ASGI walk.

## Constraint-honor checklist

* [x] Audited, did NOT modify source / test / methodology files of the slice itself. Temporary probe-side conftest helpers were written under `tests/_probe1_tmp/` and `tests/_probe1b_tmp/` for runtime-only monkeypatching, then `shutil.rmtree`'d. No git-tracked files touched.
* [x] No real OpenRadioss invocation; no real LLM call.
* [x] `^GS-\d{3}$` signed-registry never written (only used as 422-refusal probe in `SIGNED_REGISTRY_CASE_ID = "GS-001"`).
* [x] Every snapshot write under `tmp_path_factory.mktemp(...)`. Real `reports/snapshots/` + `golden_samples/` trees byte-identical pre/post (Probe 9).
* [x] HF1.7a (signed-registry hard-stop) preserved; HF1.7b (`*-candidate/` carve-out) IN FORCE in all 5 cohort cases; HF1.8 (path-guard) preserved.
* [x] Tier 1 wording discipline: every artifact carries `"Tier 1 engineering candidate; not signed validation; not benchmark agreement"` in the docstring head. 9 forbidden positive-claim tokens absent in both journey files; meta-test legitimately holds them as fingerprint data + test inputs (file exempted via `EXEMPT_FILES` from its own enforcement).
* [x] Cohort min size 3 + cohort/per-case drift floor 5.0% strictly-exceed preserved (verified via `backend/app/services/reporting/trust_score_drift_attribution.py:192` `max_abs <= dominant_floor_pct`).
* [x] No push, PR, Notion, Linear touched.

## Verdict

**APPROVE — 63/63** — Slice D lands the 2 reviewer-journey E2E coverage + SSOT consolidation cleanly. All 31 new tests + 70 refactored Phase 15+ tests are green; the SSOT module exposes 4 canonical names with semantic correctness verified by probes 2/3/4/7; boundary pins are load-bearing (probe 1); Tier 1 trio + server-computed signoff drift discipline preserved (probes 6/8); snapshot containment is byte-clean (probe 9); cross-arc invariant holds (probe 10).

No fixes required.
