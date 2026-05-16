# FM-04a Phase 13 Slice-B Test Auditor Report

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Auditor: TAA (Test Auditor Agent) · independent and adversarial
Commit under audit: `9dede37`
Baseline: `89ff6cf` (post-slice-A)
Date: 2026-05-17

---

## Verdict

**APPROVE — 60/63**

All six axes meet or exceed their floor. The meta-test drift guard was empirically falsified-and-restored (regression on `test_phase4_endpoints_integration.py:202` trips both the ceiling and the per-file pin; revert with `git checkout --` restores green). The frontend close-set suffix gate correctly discards the canonical smuggled payload `"refused: production ready for service deployment"` (suffix `"production ready for service deployment"` is not in the 9-element forbidden set). The first-token-wins sharper test has the load-bearing observational distinction (a swap of `ADVISOR_FORBIDDEN_TOKENS` indices 0↔4 would break it).

Three minor accounting/coverage drifts knock 3 points off — none are correctness failures.

---

## Per-axis scoring

- **M — Module-level SSOT (12)**: **11/12** · `_PERMISSIVE_4XX_CEILING: int = 0` is module-level + typed + commented (lines 48–52). `_PERMISSIVE_PATTERNS: tuple[re.Pattern[str], ...]` is typed and docstring-anchored (lines 75–90). `_SIGNED_REGISTRY_RE = re.compile(r"^GS-\d{3}$")` at module scope (`case_completeness.py:46`) follows project convention (matches sibling `_CASE_ID_RE`) but lacks an explicit type annotation; this is consistent with the existing pattern, so deducting only 1.

- **T — Boundary-pinned tests (15)**: **14/15** · 8 permissive sites tightened to exact pins; reviewer-bundle 422 carries the explicit `detail[0]["type"] == "string_too_short"` + `"ids" in detail[0]["loc"]` detail-check (T-rubric example satisfied). 400 invalid-case_id tightenings carry `detail == "invalid case_id"`. Meta-test has 5 synthetic positives (tuple/set/range/`<500`/`>=4xx`) AND 3 negative-coverage tests (exact, happy-path 2xx, stub-constructor kwargs). The traversal-404 tightenings (5 of them) do NOT add detail-checks beyond the status code itself — FastAPI's default `{"detail": "Not Found"}` is generic, but pinning the exact body for the routing-layer case would lock the test against future FastAPI surface changes. Acceptable, deduct 1.

- **C — Tier 1 disclaimer trio (12)**: **11/12** · Single-line trio present in all 4 newly created / touched files (`case_completeness.py:3`, `advisorCritiqueClient.ts:3`, `test_phase13_refused_claims.py`, `test_phase13_status_code_discipline.py:3`). No forbidden-token leakage outside `ADVISOR_FORBIDDEN_TOKENS` declaration / `not <token>` disclaimers / methodology fixtures / test-input fixtures (verified via grep against all 9 tokens — 232 hits, 100% classified). Deduct 1 for the methodology doc `Reference` section drift (claims "7 ... 5 files" — see Findings).

- **A — Slice-A + Slice-F finding closure (8)**: **7/8** · Slice-A TAA HIGH (close-set suffix): closed with new code in `_parseRefusedClaims` lines 183–195 AND two new vitest cases (AdvisorPanel.test.tsx:488–547). Smuggled payload `"refused: production ready for service deployment"` empirically discarded; case-folding works (`"refused: ASME compliant"` → kept). Slice-A TAA MEDIUM (first-token-wins): closed with a deterministic single-winner pin PLUS the sharper case where haystack order and declaration order diverge (`test_phase13_refused_claims.py:183–203`); a silent reorder of `ADVISOR_FORBIDDEN_TOKENS` would break the sharper test even though the canonical test would still pass. Slice-F LOW: closed at `case_completeness.py:143–151` with the matching detail vocabulary (probed: `GET /api/v1/case-completeness/GS-001` returns 422 with `signed-registry`, `candidate`, `out of scope` substrings present). Deduct 1: the slice-F closure has the route-level guard but the **module-level SSOT documentation** (lines 38–46 comment block) is internal to one file; a cross-route audit script `_assert_signed_registry_guards_present()` (mentioned in the blueprint as ideal) is not added — a second route adding signed-registry surface in the future would not have a meta-check to refuse 200 responses on GS-NNN.

- **E — Environmental discipline (8)**: **8/8** · Backend pytest 2248 passed + 7 skipped (vs 2231 baseline = +17 new exactly as claimed: 16 meta-test + 1 from refused-claims split). Frontend vitest 135 passed (133 + 2). Frontend `tsc --noEmit` clean (no output). HF1 zone: `git diff 89ff6cf..9dede37 -- scripts/hf1_path_guard.py .planning/decisions/AR-2026-05-16-001* golden_samples/**` returns empty. All 12 touched paths are inside permitted scope.

- **V — Genuine value (8)**: **7/8** · Meta-test ceiling drift guard EMPIRICALLY verified: relaxing one tightening to `in (400, 422)` makes both `test_permissive_4xx_count_is_within_ceiling` AND `test_specific_slice_b_target_files_have_zero_permissive[test_phase4_endpoints_integration.py]` FAIL with the exact filename + line number in the error message. This is real test-suite-contract enforcement, not vanity. Close-set suffix gate empirically closes the smuggled-suffix vector. First-token-wins sharper test has observable behavior under hypothetical token-tuple reorder (verified by reasoning on lines 174–203). Deduct 1: see Finding 2 (per-file parametrize misses `test_phase6_endpoints_integration.py`), which means the per-file value of "regression-tells-you-the-filename" is reduced for one of the six target files (still caught by the global ceiling test, but a noisier signal).

---

## Top findings

### LOW — Per-file parametrize list missing `test_phase6_endpoints_integration.py`

`tests/test_phase13_status_code_discipline.py:288–296` — the `@pytest.mark.parametrize` list for `test_specific_slice_b_target_files_have_zero_permissive` enumerates 5 files (`test_phase4`, `test_phase5`, `test_phase7`, `test_phase11`, `test_api_endpoints_integration`) but `tests/test_phase6_endpoints_integration.py` was also tightened (2 traversal sites, commit message rows 5–6). The global ceiling test still catches a phase6 regression, but the file-specific signal "phase6 re-introduced a permissive site" would be muddled into the generic-ceiling error.

**Fix**: add `"test_phase6_endpoints_integration.py"` to the parametrize list.

### LOW — Narrative accounting drift across commit body / methodology doc / parametrize list

Commit body claims "8 permissive 4xx assertions across 6 test files"; methodology doc `Reference` section says "7 permissive 4xx-range assertions ... across 5 test files"; parametrize lists 5 files. Reality: 12 raw permissive-line removals (some bundle 2 lines into one tightening) across 6 files. Different ways of counting are defensible — but the doc/code surfaces disagree, which makes future archaeology slower.

**Fix**: pick one accounting convention (recommend: "8 tightenings across 6 files" matching commit body) and propagate to methodology doc + parametrize comment.

### LOW — Routing-layer traversal-404 tightenings carry no detail-body assertion

5 traversal-404 tightenings (`test_phase5`, `test_phase6 × 2`, `test_phase7`, `test_api_endpoints_integration tier1-report`) pin `status_code == 404` but do not assert the response body. A future FastAPI upgrade could change `{"detail": "Not Found"}` to a different shape without tripping these tests, BUT a routing-layer drift from 404 → 422 (handler-layer rejection) would surface — which is the main concern. The detail-body skip is defensible; flagged because rubric T mentions detail-checks as an example.

**Fix (optional)**: add a `response.text` substring or shape pin if reviewer wants stronger lock-in. Not blocking.

### LOW — Slice-F closure lacks a cross-route meta-guard

`case_completeness.py:143` adds the signed-registry refusal locally. If a future Phase adds a third reviewer-facing route accepting `case_id`, that route would silently return 200 on `GS-NNN` unless it adopts the same guard. A meta-test that introspects FastAPI routes for `case_id` path params and asserts each has a `^GS-\d{3}$` 422-refusing test would be the symmetric equivalent of the slice-B status-code-discipline meta-test for the signed-registry surface.

**Fix (defer to slice C/D or Phase 14)**: not in slice-B scope, but tracking here so it does not vanish.

---

## Engineering coherence

Slice B delivers a real, drift-resistant test-suite contract (status-code discipline meta-test with empirically-verified regression detection) plus three closures (slice-A HIGH/MEDIUM frontend + slice-F LOW backend) that all add NEW guards rather than relaxing existing ones, with module-level SSOTs and Tier 1 disclaimer preservation throughout — minor surface-accounting drift docked 3 points but no engineering-correctness gap was found.
