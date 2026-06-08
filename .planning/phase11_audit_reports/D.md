# Phase 11 D — TAA report

**Slice commit:** `fd2c0f3`
**Verdict:** APPROVE
**Test count:** 20 (17 test functions; `accepts_every_analysis_type_in_tuple` parametrizes ×4 over `ANALYSIS_TYPE_TUPLE`, adding 3 over function count)
**Test pass:** 20/20; full sweep `2054 passed + 7 skipped` (matches commit claim byte-for-byte; +20 over slice-C's 2034+7)

## Per-axis evidence

- **M (12/12)** — `METRICS_ANALYSIS_TYPE_MAP` (`advisor_critique.py:824-830`) is a module-level SSOT dict; no inline literal anywhere in `build_advisor_context_from_snapshot`. Verified at runtime that `MAP["linear_static_pressure_vessel"] == MAP["linear_static_pv"] == "linear_static_pv"`. Route imports SSOT constants by identifier — `case_completeness.py` imports `ANALYSIS_TYPE_TUPLE` + `DEFAULT_ANALYSIS_TYPE` from the service module, uses `DEFAULT_ANALYSIS_TYPE` as the `Query()` default, and gates against `ANALYSIS_TYPE_TUPLE`. `advisor_critique.py` route imports `SNAPSHOT_LABEL_RE` from `cohort_snapshot`, plus all four service-layer entry points by identifier; no re-declared tuples. `_repo_root` uses `Path(__file__).resolve().parents[4]` (integer path-depth, consistent with every other route).

- **T (15/15)** — 20 distinct tests over function-count of 17, comfortably above floor (≥14). Each of the 6 required gate compositions has its own test on the advisor route: 422 invalid case_id shape, 422 signed-registry, 422 missing snapshot query param, 422 invalid snapshot label shape, 404 manifest-missing branch, 404 case-missing branch. Plus 200 happy-path with Tier 1 disclaimer trio + 200 default-stub-status + 200 unwired-anthropic-fallback + 200 schema-version + 200 stub-correlated-content. Case-completeness covers 422 invalid analysis_type, 422 empty analysis_type, 422 invalid case_id (FastAPI surfaces 400 here per Phase 4 back-compat), 200 default + 200 explicit analysis_type + parametrized 200 across all four `ANALYSIS_TYPE_TUPLE` values. Parametrize iterates `list(ANALYSIS_TYPE_TUPLE)` (T:-3 — reads from SSOT). The two distinct `AdvisorSnapshotNotFound` branches have dedicated separate tests.

- **C (12/12)** — `test_advisor_route_200_on_happy_path_returns_tier1_disclaimer_trio` asserts all three banner fields. `test_case_completeness_route_200_with_explicit_analysis_type` re-asserts `claim_tier` on the completeness body. The advisor route NEVER 5xx's for an LLM outage — `test_advisor_route_unwired_anthropic_backend_falls_back_to_stub` asserts 200 + `advisor_status == "stub"` + `"NotImplementedError" in degrade_reason` + `advisor_backend == "llm-advisor-anthropic-unwired"`. Signed-registry refusal asserts both `"signed-registry"` AND `"candidate"` substrings in the 422 detail.

- **A (8/8)** — A:-3 distinct refusal test for `GS-101` returning 422 with both required tokens. A:-4 verified by `grep -rn "import httpx\|import requests\|from httpx\|from requests\|import anthropic\|from anthropic\|urllib\|aiohttp"` on both slice-D modules returning empty — zero network imports. A:-5 pinned by the unwired-anthropic test. The two distinct `AdvisorSnapshotNotFound` branches verified by separate test functions hitting separate code paths.

- **E (8/8)** — Full sweep `2054 passed, 7 skipped, 3 warnings in 17.68s` — matches commit message byte-for-byte. Phase 4 back-compat test `test_case_completeness_rejects_invalid_case_id` (which accepts `(400, 404)`) still passes — the route preserved 400 on invalid case_id as documented. No regressions across pre-Phase-11 endpoint surfaces.

- **V (8/8)** — APPROVE. Slice D delivers every blueprint §3.D deliverable: SSOT `METRICS_ANALYSIS_TYPE_MAP`, distinct `AdvisorSnapshotNotFound(LookupError)`, HTTP route with 6-step gate composition, `case_completeness` analysis_type extension with Phase 4 back-compat preserved, ≥14 tests (delivered 20 with parametrize over SSOT), no real network, no 5xx-on-LLM-outage. Slice-C TAA archive present. Exactly 6 files touched. HF1 hard-stop zones untouched.

## Findings

- **LOW** — `test_advisor_route_422_on_invalid_case_id_shape` and `test_case_completeness_route_422_on_invalid_case_id_shape` both assert the permissive `400 <= status < 500` rather than pinning to the actual `422` (advisor) / `400` (case-completeness) the routes emit. Tightening the assertions would lock in the exact status posture. Not blocking.

- **LOW** — `_repo_root()` is re-declared in `advisor_critique.py:55-56` with identical body to a dozen other route modules. Project-wide cleanup, not a slice-D concern.

- **LOW** — The advisor route's `_CASE_ID_RE` and `_SIGNED_REGISTRY_RE` are re-declared module-locally rather than imported from a shared SSOT. Same project-wide pattern; future consolidation candidate.

- **LOW** — `test_advisor_route_422_on_missing_snapshot_query_param` does not also assert any field of the response body (just the status). A `"snapshot" in detail` style assertion would harden the pin.

## Cumulative slice D axes
M + T + C + A + E + V = 12 + 15 + 12 + 8 + 8 + 8 = **63 / 63**
