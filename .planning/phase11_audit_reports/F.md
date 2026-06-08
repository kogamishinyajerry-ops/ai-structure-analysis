# Phase 11 F — TAA report

**Slice commit:** `ae52a69`
**Verdict:** APPROVE
**Test count:** 27 integration + 3 E2E = 30
**Test pass:** 30/30 slice-F; full sweep 2064 passed + 7 skipped = 2071 total

## Per-axis evidence

- **M (12/12)** — SSOT tuples imported by identifier across both test files. `tests/test_phase11_endpoints_integration.py` lines 38-45 import `ADVISOR_CRITIQUE_SCHEMA_VERSION`, `ADVISOR_STATUS_TUPLE`, `ANALYSIS_TYPE_TUPLE`, `CASE_COMPLETENESS_SCHEMA_VERSION` from the service modules — no string duplication. `tests/test_fm04a_phase11_advisor_e2e.py` lines 52-57 import `ADVISOR_STATUS_TUPLE` + `ANALYSIS_TYPE_TUPLE` and assert membership. The slice-F 422-detail-echo test iterates `ANALYSIS_TYPE_TUPLE` directly — defending against silent drift. Zero magic strings for the allowed-sets.

- **T (15/15)** — Blueprint §3.F floor ≥16 integration + ≥3 E2E. Delivered 27 integration + 3 E2E = 30 (vs floor 19). E2E count = 3 distinct journey functions, each crossing ≥2 routes: J1 crosses 4 routes (advisor GET, signoff POST, signoff GET, completeness GET); J2 crosses 3 routes (advisor GET, signoff POST, completeness GET); J3 crosses 2 routes × 2 cases. pytest collection confirmed 30 items, all PASS in 0.69s.

- **C (12/12)** — Slice-D canonical happy-path tests assert the trio on both routes' 200 envelopes. Trio fields are dataclass-baked into the envelope at `backend/app/services/reporting/advisor_critique.py` lines 182-184 + serialized at 443-445 — every 200 body across both routes structurally carries it. Journey 2 (the load-bearing LLM-offline-functional north-star) is strongly verified: `AIFEA_ADVISOR_BACKEND=anthropic` + `ANTHROPIC_API_KEY=sk-test-placeholder` env set; advisor route returns 200 (not 5xx); `advisor_status == "stub"`; `advisor_backend == "llm-advisor-anthropic-unwired"`; `degrade_reason is not None` and contains `"NotImplementedError"`; signoff + completeness still complete. Memory `feedback_cfd_harness_ai_advisor_pivot` SSOT honoured.

- **A (8/8)** — All anti-gaming guards wired:
  - A:-3 (signed-registry refusal): slice-D test enforces.
  - A:-4 (no real network): grep on `httpx|requests|anthropic|urllib` returned ONLY docstring/comment/label hits. No operative network call.
  - A:-5 (unwired placeholder → stub at produce, never 5xx): verified by Journey 2.
  - E:-3 (real ASGI not mocked): both test files build `httpx.ASGITransport(app=app)`. Not a TestClient mock.
  - E:-4 (each journey crosses ≥2 routes): J1=4, J2=3, J3=2×2=4. All ≥2. The 405 tests use direct `httpx.AsyncClient + c.post(...)`, NOT the `_SyncASGIClient.get` helper.

- **E (8/8)** — Full sweep clean: `2064 passed, 7 skipped, 3 warnings in 19.18s`. Slice-D close was 2054+7; slice-F adds exactly +10. Zero regressions across pre-Phase-11 surfaces.

- **V (8/8)** — APPROVE. Rubric fully met; commit scope is exactly 3 files; no backend service/route code touched; HF1 untouched.

## Findings

(no HIGH / MEDIUM / LOW findings)

Side notes (informational, not findings):
- Slice-F supplemental 200-path tests do not re-assert the Tier 1 disclaimer trio. Defensible because the trio is dataclass-baked into the envelope shape and slice-D canonical tests already pin it.
- The advisor route's 404 disambiguation test only exercises the `metrics_missing_but_snapshot_present` branch; the inverse is covered by `test_advisor_route_404_when_snapshot_dir_missing` (slice-D). Coverage is complete across the union.
- Journey 3 cross-route consistency assertion reads `"linear_static_pv" in ANALYSIS_TYPE_TUPLE` rather than asserting an envelope echo — defensible because the advisor surface intentionally does NOT stamp `analysis_type` on its envelope.

## Cumulative slice F axes
M + T + C + A + E + V = 12 + 15 + 12 + 8 + 8 + 8 = **63 / 63**
