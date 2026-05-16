# Phase 7 sub-phase G — TAA audit report

**Commit:** `92aff40` — test(FM-04a/Phase7-G): HTTP integration + 3 E2E trust closure tests + slice-E TAA archive
**Auditor:** TAA-G (independent re-audit, no trust of author SCORECARD)
**Date:** 2026-05-16
**Audited paths:** `tests/test_phase7_endpoints_integration.py` (303 LOC, 9 tests) · `tests/test_fm04a_phase7_trust_closure_e2e.py` (313 LOC, 3 tests) · `.planning/phase7_audit_reports/E.md` (44 LOC)

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

---

## Evidence-driven findings

### 1. HTTP integration count vs blueprint §3.G floor — **SHORTFALL**
- Blueprint §3.G:234 says `tests/test_phase7_endpoints_integration.py` — **≥14 tests**.
- Commit ships **9 tests** (`grep -c "^def test_" tests/test_phase7_endpoints_integration.py = 9`); commit message also self-admits "9 HTTP integration tests".
- Coverage map of the 9 tests:
  - narrative locale: default en-US (`test_narrative_endpoint_defaults_to_en_us`), zh-CN (`..._renders_zh_cn`), reject unknown (`..._rejects_unknown_locale`) — 3
  - alerts: stamped (`..._returns_stamped_payload`), invalid case_id (`..._rejects_invalid_case_id`), clamp below (`..._clamps_threshold_below_min`), clamp above (`..._clamps_threshold_above_max`), severity (`..._returns_severity_buckets`) — 5
  - diff convergence recovery (`test_diff_endpoint_recovers_convergence_verdict_from_captured_file`) — 1
- **Missing per §3.G:235-237:** (a) explicit "no-alarms-when-stable" positive test, (b) explicit Tier 1 disclaimer round-trip test on narrative endpoint (only in alerts), (c) cross-locale forbidden-claim audit at the HTTP boundary, (d) probably 2 more axis-level integration tests to reach 14.
- **Mitigation:** the 5 missing tests partially live in slice C's `test_phase7_trust_score_alerts.py` (17 builder-level tests) and slice B's locale tests (34 narrative tests). The HTTP-boundary distinction is what §3.G actually requires; these are not full substitutes.
- **Net T-axis deduction:** -2 (floor undershoot by 5 tests; not by half — coverage breadth at the HTTP boundary is genuinely thin, e.g. no `claim_tier` envelope assertion on narrative endpoint).

### 2. E2E count + structure — **PASS**
- `grep -c "^def test_" tests/test_fm04a_phase7_trust_closure_e2e.py = 3`. Exactly the §3.G floor.
- Names: `test_phase7_convergence_recovery_flow_e2e` / `test_phase7_locale_roundtrip_flow_e2e` / `test_phase7_regression_alarm_flow_e2e`. Mapped 1:1 to Phase 7 carry-forwards §1 / §3 / §4.

### 3. Anti-gaming guard T:-2 per E2E missing disclaimer trio — **PASS (all 3)**
- E2E #1: lines 195-197 assert "tier 1 engineering candidate" + "not signed validation" + "not benchmark agreement" via `res.text.lower()`. PASS.
- E2E #2: lines 246-248 assert "Tier 1 engineering candidate" in `payload["claim_tier"]`, both "not signed validation" + "not benchmark agreement" in `payload["claim_impact"]`. **Note:** trio is split across two parsed fields (claim_tier + claim_impact), not in a single body grep. The guard text says "in the HTTP response body" — both fields are in the response body. PASS by both letter and spirit.
- E2E #3: lines 310-313 assert all three tokens + "not authorize tier 2" via `res.text.lower()`. PASS.
- **Net T-axis deduction:** 0.

### 4. E2E #1 convergence recovery — **GENUINE RECOVERY PROOF**
- `_write_case_evidence` builds `metrics_payload` (lines 100-119) with `perforation` + `energy_audit` + `extraction_metadata` only — **no `convergence_summary` block**.
- Convergence verdict only exists in the separate `convergence_study.json` file (lines 126-143, captured into the snapshot by `write_cohort_snapshot`).
- Test asserts `point["convergence_weighted"] > 0` (line 189). The only path to non-zero is reading the captured file → genuine recovery (not metrics-inlined fallback).
- **Closes Phase 6 §1.**

### 5. E2E #2 zh-CN glyph + English envelope — **PASS**
- Line 242 asserts `"残余速度" in case_lines`, line 244 asserts `"能量平衡误差" in case_lines`. Both real Chinese glyphs in parsed `payload["narratives"][...]["lines"][...]["text"]`.
- Lines 246-248 verify English-envelope disclaimer trio in `payload["claim_tier"]` + `payload["claim_impact"]`. Envelope correctly remains English even when narrative line bodies are zh-CN. PASS.
- **Closes Phase 6 §3.**

### 6. E2E #3 regression alarm — **PASS with one soft observation**
- 3 snapshots with completeness 100 → 70 → 20 (monotonically degrading); `threshold_delta=1` so both adjacent-pair drops fire.
- Line 294 asserts `payload["alert_count"] == 2` — exactly 2, not 3, not 1.
- Severity ladder: first drop (~15) asserted `"info"` exactly (line 299). Second drop (~25) asserted `severity in {"warn", "info"}` (line 305) — comment cites boundary depending on integer cast. Slightly loose (the test would also pass if both buckets were "info"), but the comment is honest and the `primary_axis_shift == "completeness"` assertion on both events ties it to the trajectory.
- **Closes Phase 6 §4.**

### 7. Threshold clamping at boundary (T:-2 guard) — **PASS**
- `test_alerts_endpoint_clamps_threshold_below_min`: asserts `res.status_code == 422` for `threshold_delta=-5`. PASS.
- `test_alerts_endpoint_clamps_threshold_above_max`: asserts `res.status_code == 422` for `threshold_delta=500`. PASS.
- FastAPI `Query(ge=1, le=100)` returns 422 before the builder's internal clamp ever fires. Correctly tested at the HTTP layer.

### 8. Phase 6 carry-forward closure coverage — **PASS for the 3 in-scope**
- §1 convergence: covered by E2E #1 (this slice) + integration test 9.
- §2 frontend smoke: closed in slice E (vitest harness); correctly out-of-scope for slice G.
- §3 locale: covered by E2E #2 + integration tests 1-3.
- §4 alarms: covered by E2E #3 + integration tests 4-8.
- §5 property/sensitivity: closed in slice D; correctly out-of-scope for slice G.
- Closure cross-reference must land in final retrospective (slice H) per D:-2 guard.

### 9. HF1 + signed registry — **CLEAN**
- `git diff 92aff40^..92aff40 --name-only` = 3 files (2 new tests + 1 audit report). No HF1 path. No `^GS-\d{3}$` registry edit (test fixtures use `GS-A-candidate`).

### 10. TAA E archive — **PRESENT**
- `.planning/phase7_audit_reports/E.md` exists (44 LOC), follows the standard 9-axis structure, returns APPROVE with 2 cosmetic LOWs logged (non-blocking). A:-2 guard (TAA file existence) cleared for slice E.

---

## Axis verdicts (slice G isolated)

- **B (12):** APPROVE — slice G emits no new contract. No bump needed.
- **M (12):** APPROVE — both new test files have module-scope helpers (`_SyncASGIClient`, `_write_case_evidence`, `_seed_snapshot`); no inline magic numbers; monkeypatch scoped per-fixture.
- **T (15):** **CHANGES_REQUIRED — 13/15**. 3 E2E tests meet floor (+ disclaimer trio clean), but 9 HTTP integration tests undershoot the 14-floor by 5. -2 net.
- **C (12):** APPROVE — Tier 1 disclaimer trio asserted in every E2E test; forbidden positive claims do not appear outside `not <claim>` form (manually verified the 660 LOC diff). HF1 + registry untouched.
- **X (12):** FLAG — slice G adds no frontend code. Cumulative X unchanged from slice E's 12/12.
- **D (8):** APPROVE — each E2E test has a docstring naming the Phase 6 carry-forward it closes; integration file docstring cites Phase 7 closure.
- **A (8):** APPROVE — anti-gaming guards from blueprint §4 enforced; T:-2-per-E2E-missing-disclaimer cleared; threshold clamping 422 boundary tested.
- **E (8):** APPROVE — 3 E2E tests compose Phase 5 (snapshot writer) + Phase 6 (narrative/alerts/timeline endpoints) + Phase 7 (convergence capture + alerts + locale) surfaces through real httpx ASGI transport. Each closes one named Phase 6 carry-forward.
- **V (13):** FLAG — slice G TAA report (this file) lands now → +1 from prior 6/13. Final whole-arc TAA in slice H still owed.

---

## Findings

- **HIGH** — `tests/test_phase7_endpoints_integration.py` ships 9 tests vs blueprint §3.G:234 explicit floor of ≥14. Coverage gap: no narrative endpoint disclaimer-trio assertion at HTTP boundary, no cross-locale forbidden-claim audit, no positive "no-alarms-when-stable" test (current `test_alerts_endpoint_returns_stamped_payload` only asserts `alert_count == 0` for an unseeded case, which is no-data not no-alarms). **Fix:** add 5 tests in slice H: narrative claim_tier+claim_impact envelope round-trip (en-US + zh-CN), narrative cross-locale forbidden-claim audit fires, alerts no-alarms-when-stable-cohort (seed 2+ snapshots with identical completeness, assert alert_count=0), alerts at exact severity boundary (delta=10 → info, delta=25 → warn). Without these, T-axis cannot recover to 15/15.

- **LOW** — E2E #3 (line 305) asserts `second["severity"] in {"warn", "info"}` rather than pinning the exact bucket. Comment acknowledges integer-cast boundary uncertainty. **Fix (optional):** compute expected severity from `_axis_deltas` ladder and pin it; or document why both are acceptable in a comment that cites the rounding rule from `trust_score_alerts.py`. Cosmetic only — the `alert_count == 2` + `primary_axis_shift == "completeness"` asserts are load-bearing.

- **LOW** — Integration test `test_alerts_endpoint_returns_stamped_payload` uses an unseeded `GS-A-candidate` case, so the 200 + `alert_count == 0` is a no-data path, not a stable-cohort path. This is what makes the "stable cohort produces 0 alerts" coverage gap above material. Tied to the HIGH finding.

---

## Overall verdict

**CHANGES_REQUIRED.** Slice G ships its named 3 E2E reviewer journeys cleanly and they genuinely close Phase 6 §1/§3/§4. But the HTTP integration test count is **5 short of the blueprint §3.G floor** — and the missing coverage is load-bearing (cross-locale forbidden-claim audit, narrative envelope disclaimer round-trip, stable-cohort no-alarms positive). T-axis cannot truthfully claim 15/15 with this gap.

---

## Honest score adjustment relative to commit's claimed 93/100 cumulative

Reading prior TAA reports:
- A: APPROVE — B 11/12, M 12/12, T 13/15 (8-axis floor; slice-local), C 12/12, X 0/12 (deferred), D 6/8 (-2 for deferred docs), A 7/8 (-1 for TAA pending, retired), V approving slice A only.
- B: APPROVE — M/T/C/A APPROVE, V FLAG (slice incomplete).
- C: APPROVE — B/M/T/C/D/A all APPROVE; X carried 2/12 (-1 from author's 3/12 for literal `10` drift, fixed in `beeb897`).
- D: APPROVE — T APPROVE, X carries forward 2/12 (E.md reconciles to post-`beeb897` 4/12), audit-recorded baseline drift noted.
- E: APPROVE — X earns 12/12 (with audit-chain caveat), T 15/15 cleared.

Honest cumulative through slice E (per E.md): ~83-84/100.

Slice G delta:
- T: -2 (integration shortfall vs §3.G floor of 14, real deduction; commit claimed 15/15 but the floor undershoot is unambiguous)
- E: +8 (genuine, 0/8 → 8/8 — 3 E2E tests land cleanly with disclaimer trio + Phase 6 closure proofs)
- V: +3 (slice G TAA archive landing; 6/13 → 9/13; final pass in slice H still owed for the remaining 4 points)
- B/M/C/D/A/X unchanged

**Honest cumulative through slice G: ~92/100** (≈ 83.5 prior + 8 E + 3 V − 2 T = 92.5, round to 92).

Author's claim of 93/100 is **1 point optimistic** because it does not absorb the T:-2 shortfall (commit message reports T 15/15; reality is T 13/15 with -2 for §3.G integration-count undershoot).

To reach ≥99/100 in slice H, slice H must:
1. Add ≥5 integration tests to close the §3.G:234 floor (restore T to 15/15, +2).
2. Land the final whole-arc TAA APPROVE (V from 9/13 → 12-13/13, +3 to +4).
3. Land Phase 7 retrospective with explicit Phase 6 carry-forward closure cross-reference (avoids D:-2 guard).
4. Reconcile X-axis audit chain (slice C's -1 already restored by `beeb897`; ensure final SCORECARD does not double-deduct).

If slice H closes the integration count + final TAA APPROVE, cumulative reaches ≈98-99. The 99/100 stop condition is tight but achievable if the integration gap is genuinely filled (not waved off as "covered indirectly by builder tests").

---

## Slice-G summary

APPROVE on the named deliverables (3 E2E + slice-E TAA archive); **CHANGES_REQUIRED on T-axis** until integration count reaches 14. No BLOCK. No HF1 / registry / forbidden-claim hits. E2E discipline is genuinely strong (real recovery proof in #1, real Chinese glyphs in #2, exact alert_count pin in #3). The shortfall is a quantity gap, not a quality gap — but the blueprint floor is binding.
