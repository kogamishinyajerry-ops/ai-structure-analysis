# Phase 7 sub-phase G — TAA RE-AUDIT report (post fix-up)

**Commit:** `3d681f2` — fix(FM-04a/Phase7-G): close §3.G HTTP integration floor 9->15; archive slice-G TAA
**Auditor:** TAA-G-REAUDIT (independent re-audit, no trust of author SCORECARD; superseding prior CHANGES_REQUIRED at `92aff40`)
**Date:** 2026-05-16
**Audited paths:**
- `tests/test_phase7_endpoints_integration.py` (455 LOC, 15 tests) — diff: +152 LOC, 6 new tests
- `.planning/phase7_audit_reports/G.md` (136 LOC, archived CHANGES_REQUIRED) — newly added

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

---

## Evidence-driven findings

### 1. Integration floor restored — **PASS**
- Blueprint §3.G:234 requires `tests/test_phase7_endpoints_integration.py` ≥ 14 tests.
- `grep -c "^def test_" tests/test_phase7_endpoints_integration.py = 15` (exceeds floor by 1).
- The 6 new tests are all genuine — not stubs, not tautologies, not duplicates of slice-C/B builder-level coverage. Verified per item below.

### 2. `test_narrative_endpoint_envelope_carries_tier1_disclaimer_trio` — **PASS (real round-trip both locales)**
- Lines 316-336. Iterates `for locale in ("en-US", "zh-CN")` — both locales exercised.
- Each iteration parses `payload = res.json()` and asserts:
  - `payload["claim_tier"] == "Tier 1 engineering candidate"` (exact equality, not substring)
  - `"not signed validation" in payload["claim_impact"]`
  - `"not benchmark agreement" in payload["claim_impact"]`
- This closes the §3.G coverage gap "Tier 1 disclaimer round-trip on narrative endpoint" that previously only existed for the alerts endpoint. Genuine HTTP-boundary envelope assertion — the parsed-field structure proves disclaimer trio survives serialization in both locales.

### 3. `test_narrative_endpoint_no_forbidden_claim_in_zh_cn_body` — **PASS (real cross-locale audit, not tautology)**
- Lines 339-366. Seeds two snapshots, fetches zh-CN narrative, lowercases `res.text` (full body, not parsed subfield).
- Audits 4 forbidden tokens absent: `"validated against"`, `"perforation completed"`, `"bullet-through-steel complete"`, `"validated physics"`.
- Comment honestly excludes `"signed validation"` and `"benchmark agreement"` from the audit because they legitimately appear in `not <claim>` form per the slice-B two-list design. This is a real, axis-discriminating audit — not a tautology. A regression where the zh-CN catalog translated "validated against" into a positive sentence would fire this test.
- Closes §3.G coverage gap "cross-locale forbidden-claim audit at the HTTP boundary".

### 4. `test_alerts_endpoint_no_alarms_when_cohort_stable` — **PASS (distinct from no-data path)**
- Lines 369-391. Seeds **3** snapshots with `completeness=80` (identical), then queries with `threshold_delta=1` (minimum, so even 1-point drops fire).
- Asserts `alert_count == 0` AND `alerts == []` AND disclaimer still present (`"tier 1 engineering candidate"` + `"not authorize tier 2"`).
- This is materially distinct from the prior `test_alerts_endpoint_returns_stamped_payload`, which queried an **unseeded** case (no-data path: 0 snapshots → no adjacent pairs → 0 alerts vacuously). The new test exercises the **populated cohort, no drops detected** path. Closes the slice-G TAA LOW finding #3 about the no-data-vs-stable distinction.

### 5. Severity boundary pins (3 tests) — **PASS (exact math + exact pin)**

Trust score arithmetic verification against `backend/app/services/reporting/trust_score.py` constants:
- `COMPLETENESS_WEIGHT = 50` (line 128); weighted = `int(round(raw * 50 / 100))` = `raw / 2`.
- Other axes held constant by `_seed_snapshot` (identical `git_dirty`, `convergence_verdict`, etc. across both snapshots), so axis_delta_completeness fully drives `trust_score` delta.

Boundary alignment vs `backend/app/services/reporting/trust_score_alerts.py:54-63`:

| Test | completeness path | weighted delta math | Asserts | thresholds (svc) |
|---|---|---|---|---|
| `severity_info_at_boundary` | 100→80 | 50−40 = **10** | `delta==10`, `severity=="info"` | INFO_MIN=10 ✓ |
| `severity_warn_at_boundary` | 100→50 | 50−25 = **25** | `delta==25`, `severity=="warn"` | WARN_MIN=25 ✓ |
| `severity_danger_at_boundary` | 100→20 | 50−10 = **40** | `delta==40`, `severity=="danger"` | DANGER_MIN=40 ✓ |

`_severity_for` (line 107-112) uses `>=` for each cutoff, so all three boundary values land exactly on the lower edge of their respective buckets. Pins are **load-bearing** — flip any threshold in service code and the corresponding test breaks. Closes anti-gaming guard "every alarm severity bucket has a positive test" (§4 rubric T row).

### 6. Test execution — **PASS (15/15)**
- `python -m pytest tests/test_phase7_endpoints_integration.py -v --no-header` → **15 passed, 3 warnings, 0.81s**.
- All 6 new tests appear in PASSED list. No skips, no xfail, no flakes observed.

### 7. Diff hygiene — **CLEAN**
- `git show 3d681f2 --name-only` = 2 files: `.planning/phase7_audit_reports/G.md` (archived prior TAA report, expected) + `tests/test_phase7_endpoints_integration.py` (the fix).
- **No HF1 zone hits**: 0 paths match `agents/{solver,router,geometry}.py | schemas/sim_state.py | tests/test_toolchain_probes.py | Dockerfile | Makefile | golden_samples/ | scripts/hf1_path_guard.py | .github/workflows/`.
- **No signed-registry edits**: fixtures use `GS-A-candidate` (already present, not new `^GS-\d{3}$` id).
- **No forbidden positive claims outside `not <claim>` form**: scanned `git show 3d681f2 -- tests/...py | grep '^+'` for `validated against | benchmark agreement | signed validation | perforation completed | bullet-through-steel complete | validated physics`. Matches:
  - `not signed validation` / `not benchmark agreement` — legitimate `not <claim>` form (assertions on `claim_impact`).
  - Comment lines explaining the audit two-list design — non-emitted.
  - Token list inside the `for token in (...)` audit — bare tokens that the test asserts MUST NOT appear in body; this is detection logic, not emission.
- No new contract, no schema bump, no code path modified.

### 8. Slice-G TAA archive — **PRESENT**
- `.planning/phase7_audit_reports/G.md` exists at 136 LOC, follows standard 9-axis structure, archives the original CHANGES_REQUIRED verdict at `92aff40`. V-axis anti-gaming guard "TAA report file does not actually exist" cleared.
- Note: prior TAA-G report intentionally retained as audit trail per commit message; this RE-AUDIT lives at `G_REAUDIT.md` (not overwriting `G.md`).

---

## Axis verdicts (slice G post-fix isolated)

- **B (12):** APPROVE — slice-G fix-up emits no new contract. No bump.
- **M (12):** APPROVE — new tests reuse `_seed_snapshot` helper (no inline magic snapshot construction); severity boundary thresholds named in service code (`ALERT_THRESHOLD_INFO_MIN` etc.) and reproduced in test docstrings (not as magic numbers inside assertion). Per-test monkeypatch scope preserved via `fake_repo` fixture. Test functions are short and assertion-dense.
- **T (15):** **APPROVE — 15/15 RESTORED**. 15 HTTP integration tests vs §3.G floor of 14 (exceeds by 1). 3 E2E tests still meet floor. Disclaimer trio guard cleared per E2E (carried forward from prior TAA-G §3). Severity buckets all positively pinned.
- **C (12):** APPROVE — Tier 1 disclaimer trio asserted at HTTP boundary in 2 new tests (envelope round-trip + alerts no-alarm path); forbidden positive claims do not appear outside `not <claim>` form in the 152-LOC diff (manually verified); cross-locale forbidden-claim audit now actively fires at HTTP layer. HF1 + registry untouched.
- **X (12):** FLAG — slice-G fix-up adds no frontend code. Cumulative X carry-forward unchanged at 12/12 from slice E.
- **D (8):** APPROVE — each new test has a docstring naming the §3.G TAA gap it closes; the comment block at lines 304-313 lists all four gap categories explicitly with a `Per TAA report .planning/phase7_audit_reports/G.md` cross-reference. Audit-trail discipline strong.
- **A (8):** APPROVE — all anti-gaming guards from §4 honored: T:-2-per-E2E-missing-disclaimer (3 E2E carry forward clean from prior audit); threshold clamping 422 boundary still tested; severity exact pins NOW present (was a TAA-G gap); two-list forbidden audit design honored (exclusion of `signed validation`/`benchmark agreement` from no-forbidden audit is principled, not concealment).
- **E (8):** APPROVE — slice-G E2E layer untouched by fix-up (`test_fm04a_phase7_trust_closure_e2e.py` still 3 tests). Phase 6 §1/§3/§4 closure proofs retained.
- **V (13):** FLAG — slice-G original TAA archive (`G.md`) lands at 9/13; this RE-AUDIT archive (`G_REAUDIT.md`) brings cumulative V to **10/13**. Final whole-arc TAA pass in slice H still owed for the remaining 3 V points (per §3.H:247 + §4 V-row anti-gaming guard "-3 if the final TAA pass returns CHANGES_REQUIRED but the retrospective claims ≥99/100").

---

## Findings

- **No HIGH findings.** All HIGH findings from prior TAA-G (`G.md`) are closed:
  - Prior HIGH ("9 vs floor 14, missing envelope round-trip / cross-locale forbidden audit / stable-cohort no-alarms / boundary pins") → **CLOSED** by 6 genuine tests covering each named gap.
  - Prior LOW #3 ("`test_alerts_endpoint_returns_stamped_payload` is no-data not stable-cohort") → **CLOSED** by `test_alerts_endpoint_no_alarms_when_cohort_stable` providing the missing positive path.

- **LOW (carry-forward, slice H scope):** Prior TAA-G LOW about E2E #3 line 305 (`severity in {"warn", "info"}` instead of exact pin) is **untouched by this fix-up**. The E2E file was not modified. This was already classified as cosmetic in the original audit. Slice H can either tighten the assertion or leave it; not blocking.

- **LOW (new, optional):** Severity boundary tests assert `payload["alert_count"] == 1` AND specific `alerts[0]` fields, but do not also assert `alerts[0]["primary_axis_shift"] == "completeness"`. Since the only varied input IS completeness, this is implicit, but explicit assertion would strengthen the load-bearing of the pin. Cosmetic; not blocking.

---

## Overall verdict

**APPROVE.** Slice-G fix-up cleanly closes the §3.G integration floor undershoot (9→15) with 6 genuine tests that map 1:1 to the gaps named in the prior TAA-G report. Every new test is real, exercises the HTTP boundary (not the builder layer), and either pins exact severity buckets, asserts the disclaimer trio round-trip in both locales, audits cross-locale forbidden claims, or distinguishes stable-cohort from no-data path. Boundary math is independently verified against `trust_score.py` constants (COMPLETENESS_WEIGHT=50) and `trust_score_alerts.py` thresholds (10/25/40). Full test file passes 15/15. No HF1 / signed-registry / forbidden-claim leakage. T-axis truthfully reaches **15/15**.

---

## Honest score adjustment vs commit's claimed SCORECARD (96/100)

Author's claim per commit message:
> Cumulative honest score: 92/100 (slice-G TAA) -> 96/100 (post-fix, pre-final-TAA)

Breakdown of claim: prior 92 + T:+2 (restoration) + V:+2 (slice-G TAA archive landing).

This re-audit verifies each leg:
- **T:+2 (13→15):** ✓ Verified. 6 genuine tests close all 4 named gap categories; `grep -c "^def test_"` = 15 vs floor 14; boundary math + test execution checked.
- **V:+2 (was 6/13 in prior TAA-G's own tally, post-archive becomes 9/13 per prior G.md §axis verdicts):** Prior TAA-G self-counted +3 (6→9) when its own report landed. With this RE-AUDIT also landing (slice G re-audit archive), V becomes **10/13**. Author's commit message says V=9/13 (matches the post-archive-of-G.md count, before this RE-AUDIT). So author's V tally is conservative by 1.
- **B/M/C/X/D/A/E unchanged:** ✓ Verified.

Reconciliation:

| Axis | Prior TAA-G (G.md) | Author post-fix claim | This RE-AUDIT verifies |
|---|---|---|---|
| B | 12/12 | 12/12 | 12/12 |
| M | 12/12 | 12/12 | 12/12 |
| T | 13/15 | 15/15 | **15/15** ✓ |
| C | 12/12 | 12/12 | 12/12 |
| X | 12/12 | 12/12 | 12/12 |
| D | 8/8 | 8/8 | 8/8 |
| A | 8/8 | 8/8 | 8/8 |
| E | 8/8 | 8/8 | 8/8 |
| V | 9/13 | 9/13 | **10/13** (this RE-AUDIT lands) |
| **Total** | **92/100** | **96/100** | **97/100** |

**Author's 96/100 is 1 point conservative** — does not yet credit the V:+1 from this RE-AUDIT archive landing. Honest cumulative post-RE-AUDIT = **97/100**.

Path to ≥99 in slice H (per §3.H):
1. Final whole-arc TAA APPROVE landing → V:+2 or +3 (10/13 → 12/13 or 13/13).
2. Phase 7 retrospective with explicit Phase 6 §"Carry-forward into Phase 7" closure cross-reference per item → avoids D:-2 anti-gaming guard (currently no deduction risk if retro lands correctly).
3. Optional: tighten E2E #3 line 305 severity assertion (cosmetic LOW; not required for 99 if final TAA accepts current form).

If slice H lands clean final TAA + retro, cumulative reaches **99/100 or 100/100**. The §3.G integration floor — the binding blocker through this slice — is **closed**.

---

## Slice-G post-fix summary

**APPROVE** on the fix-up commit. The §3.G:234 integration floor (≥14) is decisively crossed at 15, with each of the 6 new tests directly traceable to a named gap from the prior TAA-G CHANGES_REQUIRED finding. Boundary math is exact, locale coverage is complete, forbidden-claim cross-locale audit is operational at HTTP layer, and stable-cohort vs no-data paths are now disambiguated. No quality regressions; no forbidden-token leakage; no HF1 / registry touches. Slice G is closed; slice H proceeds with cumulative honest score **97/100** and a clear 2–3 point runway to the ≥99 stop condition.
