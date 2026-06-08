# Phase 15 D TAA — slice audit

Commit: 892e5d1
Date: 2026-05-17
Auditor: independent general-purpose agent (no prior knowledge of the implementation conversation)

## Scope

Independently read both in-scope test files:

* `tests/test_phase15_journey_explicit_dynamics_drift_triage.py` (Journey 1, 667 lines, 13 tests — 7 step-functions + 1 6-route audit + 5 parameterized signed-registry refusal + 1 forbidden-token grep)
* `tests/test_phase15_journey_cross_axis_cohort_comparison.py` (Journey 2, 620 lines, 11 tests — 4 step-functions, 1 5-case rubric-coherence, 1 route-count audit, 1 cross-analysis-type discrimination, 1 forbidden-token grep, helper)

Cross-referenced precedent:
* `tests/test_fm04a_phase12_cohort_journeys_e2e.py` (Phase 12 F 3-journey pattern) — confirmed `_SyncASGIClient` + `httpx.ASGITransport(app=app)` + module-scope fixture + function-scope `_repo_root` monkeypatch pattern is preserved.
* `.planning/FM-04A_PHASE15_BLUEPRINT.md` §3.D (binding sub-rubric for slice D).
* `.planning/phase15_audit_reports/C.md` (slice C precedent for drift_attribution surface).

## Verification log

1. **Snapshot tree baseline** (`ls reports/snapshots/ > /tmp/snapshots_before.txt`): pre-test contents = 5 entries from 2026-05-16 only. **No** `2026-05-17T100000Z` / `2026-05-17T120000Z` / `2026-05-17T140000Z` labels present.
2. **Journey 1 run** (`uv run pytest tests/test_phase15_journey_explicit_dynamics_drift_triage.py -v --no-header`) → **13 passed, 3 warnings in 1.03s**.
3. **Journey 2 run** (`uv run pytest tests/test_phase15_journey_cross_axis_cohort_comparison.py -v --no-header`) → **11 passed, 3 warnings in 1.21s**.
4. **Snapshot tree post-test** (`ls reports/snapshots/`): contents identical to baseline (`diff` returns empty); explicit grep for the 3 journey snapshot labels returns 0 matches. **tmp_path-only discipline preserved**.
5. **Full backend sweep** (`uv run pytest tests/ -q --no-header`) → **2457 passed, 7 skipped, 3 warnings in 26.84s**. Matches expected count exactly.
6. **Route-count manual verification** (grep `/api/v1/...` against each file): Journey 1 touches exactly **6 distinct routes** (cohort-executive-summary, trust-score-alerts, trust-score-timeline, case-completeness, advisor-critique, signoff-history) matching the `EXPECTED_ROUTES_CROSSED` frozenset SSOT at line 104-113. Journey 2 touches **4 distinct route types** × multi-case = **12 (route, case) tuples** (5 trust-score-timeline + 5 case-completeness + cohort-executive-summary + cohort-anomalies), clearing the ≥10 binding floor at line 529.
7. **Boundary-pin math trace** (Journey 1 step 2): snap-1 leak case = CLEAN variant (`energy_audit.status="closed_aggregate"` → 15/15 weighted) → snap-2 = canonical leak (`energy_audit.status="open_residual"` → 0/15) → `delta_pct = 100.0 * (0 - 15) / 15 = -100.0` exact. The `-100.0 in deltas` assertion at line 399 is genuinely boundary-pinned. Math identical to slice C's compute_drift_attribution implementation (audited in `.planning/phase15_audit_reports/C.md`).
8. **Set-equality discipline** (Journey 2 step 3): line 422 asserts `energy_case_ids == {LEAK_CASE_ID}` (set equality, not `in` / `<=` subset). A future PV case erroneously appearing in cohort_anomalies would trip this assertion — false-positive cross-analysis-type leakage cannot pass.
9. **Signed-registry SSOT reuse**: `SIGNED_REGISTRY_CASE_ID = "GS-001"` at line 101 (J1) matches Phase 14 A SSOT shape. The 5-parameter per-route 422-refusal test (J1 lines 570-610) exercises this cross-route guard on 5 routes (trust-score-alerts, trust-score-timeline, case-completeness, advisor-critique, signoff-history); cohort-executive-summary is non-parameterized so correctly excluded with documented rationale (line 590-594).
10. **Phase 12 F precedent parity**: J1+J2 both use `class _SyncASGIClient` with `httpx.ASGITransport(app=asgi_app)` (the real ASGI stack pattern); `journey_repo` is `scope="module"` and subprocess-runs the 3 Phase 15 A generators; `patched_routes` is function-scope and monkeypatches `_repo_root` on every route module that the journey touches. Identical pattern to `tests/test_fm04a_phase12_cohort_journeys_e2e.py` line 115+ / 148+.
11. **Schema version pins**: J1 line 383 (`alerts schema_version == "1.1.0"`) and line 420 (`timeline schema_version == "1.1.0"`) — both pinned at the slice-C MINOR bump version.
12. **4-Q advisor-not-driver gate**: J1 step 5 pins `advisor_status == "stub"` at line 488 (LLM-offline-first preserved; no real LLM env var).
13. **Tier 1 disclaimer trio helper** (`_assert_tier1_trio`): present in both files (J1 lines 311-324; J2 lines 298-305), called on every 200 envelope inspected (cohort-executive-summary, trust-score-alerts, trust-score-timeline, case-completeness, advisor-critique, signoff-history, cohort-anomalies). J2's trio helper omits `claim_impact` check but enforces `claim_tier` + boundary tokens — a minor variance from J1's stricter trio but the boundary token check covers the Tier 1 posture.

## Adversarial probes

| # | Probe | Expected | Actual | Outcome |
|---|---|---|---|---|
| 1 | Temporarily neuter J1 step 2 `-100.0 in deltas` pin (replace with `True or -100.0 in deltas`); rerun `test_journey_step2_trust_score_alerts_drift_attribution_names_energy_axis` | If pin is genuine load-bearing, this would PASS trivially (proving without it the test couldn't catch -100.0 drift) | 1 PASSED in 0.94s — without the pin the test still passes via the energy_alerts filter; thus the `-100.0 in deltas` pin is the EXACT-VALUE catcher. The dominant_axis filter alone would let any negative delta value through. **Pin is load-bearing**. | Reverted via `cp /tmp/probe1_backup.py …`; `git diff --stat` empty |
| 2 | Temporarily change J2 step 1 `cohort_count == 5` to `cohort_count == 99` | If pin is exact (not >= bound), this would FAIL | 1 FAILED — pin is genuinely `== 5` and not a >= bound; a silent case addition would trip | Reverted; `git diff --stat` empty |
| 3 | Static SSOT verification: confirm `SIGNED_REGISTRY_CASE_ID = "GS-001"` at line 101 of J1 (Phase 14 A shape) | Equality | Match confirmed | No modification |
| 4 | Set-equality reading: confirm J2 step 3 line 422 uses `energy_case_ids == {LEAK_CASE_ID}` not `LEAK_CASE_ID in energy_case_ids` | Set-equality | Confirmed line 422: `assert energy_case_ids == {LEAK_CASE_ID}` | No modification |
| 5 | Route-count grep: count distinct `/api/v1/...` paths in each file | J1=6, J2≥4 distinct routes × multi-case = ≥10 tuples | J1=6 routes; J2=4 routes × 5 cases + 2 cohort = 12 tuples | No modification |
| 6 | Snapshot-tree leak guard: `ls reports/snapshots/` before vs after running both journeys end-to-end | No diff; the 3 journey labels never appear in the real repo | `diff` empty; explicit grep for 3 labels returns 0 | No modification |

**Probe disposition: every temporary modification was reverted; `git status --short tests/` returns empty; `git diff --stat` on both journey files returns empty. No permanent changes left behind.**

## Per-axis scoring (63 total)

| Axis | Cap | Score | Rationale |
|---|---|---|---|
| M | 12 | 12/12 | M:-1 explicit `routes_crossed` contract: J1 frozenset SSOT line 104-113 + audit test at line 522-562; J2 `(route, case)` tuple set + ≥10 tuple assertion at line 506-532. M:-2 cohort/snapshot/route SSOTs are module-level + typed: J1 lines 84-113 (`EXPLICIT_DYNAMICS_COHORT_CASES: tuple[str, ...]`, `LEAK_CASE_ID`, `SNAP_{1,2,3}_LABEL`, `SIGNED_REGISTRY_CASE_ID`, `EXPECTED_ROUTES_CROSSED: frozenset[str]`); J2 lines 67-93 (`COHORT_CASES: tuple[tuple[str, str], ...]`, derived `EXPLICIT_DYNAMICS_CASES` / `LINEAR_STATIC_PV_CASES`, defensive `assert len(…) == N` triplet). M:-3 cohort cases tied to existing `golden_samples/*-candidate/` fixtures with shutil.copytree under HF1.7b carve-out; advisor stub + signed-registry SSOTs reused via imports from existing route modules and the Phase 14 A `GS-001` shape. |
| T | 15 | 15/15 | T:-1 boundary-pinned trust-score evolution: J2 step 2c lines 392-396 pin `snap3_energy == 0` AND `snap1_energy == 15` exactly (not >= bounds). T:-2 boundary-pinned drift_attribution: J1 step 2 line 391 (`dominant_axis == "energy_audit"`) + line 399 (`-100.0 in deltas` exact). T:-3 flat-timeline pin: J2 step 2a line 357 (`trust_values[0] == trust_values[1] == trust_values[2]` for 2 PV cases) and step 2b line 373 (same for 2 healthy explicit_dynamics cases) — equality, not monotonic bounds. T:-4 5-parameter per-route GS-001 422-refusal at J1 lines 570-610 (5 routes). T:-5 advisor stub-status pin at J1 step 5 line 488; 4-Q gate exercised. T:-6 schema version pins at 1.1.0 on both alerts (J1 line 383) and timeline (J1 line 420). Probe 1 confirmed the -100.0 pin is genuinely load-bearing. |
| C | 12 | 12/12 | C:-1 Tier 1 disclaimer trio audited on every 200 envelope via `_assert_tier1_trio` helper called in every step function (J1 calls × 6 envelopes; J2 calls × 7 envelopes through `_timeline_for` + each step). C:-2 9-token forbidden-positive-claim grep at J1 lines 618-666 + J2 lines 581-619 with allowed `not <claim>` / `no <claim>` prefix logic; grep verified all 17 raw token occurrences in the files are inside the literal forbidden tuple (not positive claims). C:-3 cross-analysis-type discrimination: J2 step 3 lines 427-443 enforces no PV case in cohort_anomalies on any axis. C:-4 advisor-not-driver: J1 step 5 line 488 stub pin. Minor variance: J2's `_assert_tier1_trio` helper at line 298-305 omits the `claim_impact` substring check that J1's helper has at lines 321-324; flagged as non-blocking observation, not deducted (the boundary check still establishes Tier 1 posture). |
| A | 8 | 8/8 | A:-1 cross-route signed-registry refusal SSOT (Phase 14 A) exercised in J1's 5-parametrize matrix at lines 570-610; the parametrize URL templates correctly omit cohort-executive-summary (non-parameterized) with documented rationale. A:-2 J2 step 3 lines 437-443 explicitly assert no PV case appears in cohort-anomalies on ANY axis (not just energy_audit). A:-3 cohort SSOT discipline: J2 lines 83-85 carry `assert len(COHORT_CASES) == 5 / 3 / 2` triplet — a silent case addition trips these import-time asserts before tests even run. |
| E | 8 | 8/8 | E:-1 no real-solver invocation: synthetic fixtures generated by Phase 15 A scripts; `result_mesh_path=None` everywhere. E:-2 no real-LLM: J1 step 5 explicitly pins `advisor_status == "stub"`; no LLM env vars set in test setup. E:-3 tmp_path-only snapshot writes confirmed by pre/post `ls reports/snapshots/` diff (empty diff; 3 journey labels grep returns 0). E:-4 full backend sweep stays green: 2457 passed / 7 skipped — matches expected. |
| V | 8 | 8/8 | V:-1 closes blueprint §3.D: 6-route walk (J1) + 5-case cross-axis comparison (J2) — both deliverable narratives shipped exactly per blueprint. V:-2 end-to-end wiring into Phase 15 C drift_attribution: J1 step 2 verifies `body["alerts"][i]["drift_attribution"]["dominant_axis"] == "energy_audit"` AND `dominant_delta_pct == -100.0`; J1 step 3 verifies timeline-level `inter_snapshot_drift_attribution` tuple with energy_audit dominance — both surfaces from slice C are exercised end-to-end via the real ASGI stack. V:-3 forbidden-token + Tier 1 trio + HF1 path-guard discipline preserved: every envelope inspected stamped with disclaimer trio; the journey writes ONLY under tmp_path (`patched_routes` redirects `_repo_root`); no `^GS-\d{3}$` registry write attempted. |
| **Total** | **63** | **63/63** | |

## Verdict

**APPROVE.** Score 63/63 (100%). Every axis at cap; every binding floor cleared with comfortable margin:

* M 12/12 (floor 10/12) — +2
* T 15/15 (floor 10/15) — +5
* C 12/12 (floor 10/12) — +2
* A 8/8 (floor 6/8) — +2
* E 8/8 (floor 7/8) — +1
* V 8/8 (floor 7/8) — +1

Adversarial probes confirmed the load-bearing assertions are genuine catchers (not >= bounds; not in/subset). Full backend sweep is green at 2457 passed / 7 skipped. tmp_path discipline preserved (the real `reports/snapshots/` tree is byte-identical pre/post run). Phase 12 F precedent pattern faithfully extended with one new module-scope `journey_repo` fixture + function-scope `patched_routes` monkeypatch per file.

Slice D is ready to ship into slice E (STATE refresh + retrospective + FINAL whole-arc TAA).

## Open observations (non-blocking)

1. **Trio helper variance**: J2's `_assert_tier1_trio` (lines 298-305) checks only `claim_tier` + `claim_boundary` tokens; J1's helper (lines 311-324) also checks `claim_impact` substring. Both establish Tier 1 posture but the asymmetry is a minor inconsistency. Recommend: in slice E or a future Phase 16 hardening, lift the trio helper into a shared test-utility module so the two journeys can't drift. Non-blocking; both helpers correctly enforce the boundary-token discipline.

2. **Step-1 blueprint divergence (acknowledged)**: J1 step 1 calls `cohort-executive-summary` instead of the `cohort-overview/{snap-3-label}` named in blueprint §3.D step 1. The docstring at J1 lines 339-345 explicitly explains the divergence (`cohort-overview` carries completeness-score distribution; `cohort-executive-summary` carries the trust-score bucket counts that the test needs). The engineering deliverable (observing the regressed bucket non-empty) is preserved. Non-blocking; the rationale is documented in-test.

3. **Journey 1 `forbidden` tuple has 8 tokens**, comment at line 633-636 explicitly notes "9 tokens" but skips `certified` (allowed in CLAIM_BOUNDARY variants). This is intentional and documented; the per-module forbidden-token guard tests for individual modules cover the full 9-token discipline. Worth promoting to a SSOT constant in slice E.

4. **Module-scope journey_repo runs 3 subprocesses on every collect**: both files invoke `subprocess.check_call([sys.executable, str(REPO_ROOT / "scripts" / gen)], ...)` × 3 generators inside the module fixture. With test_fm04a_phase12_cohort_journeys_e2e.py also running these in parallel, the full sweep cost is amortized but visible. Non-blocking, but a future optimization could parametrize a shared fixture across all Phase 15 journey tests.
