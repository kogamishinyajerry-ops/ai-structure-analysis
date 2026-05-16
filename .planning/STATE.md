# AI-Structure-FEA · STATE

> **Stamp:** `fm04a-phase16-drift-attribution-cross-surface-CLOSED-LOCAL-2026-05-17 · branch=claude/FM-04a-tier1-ballistic-candidate@<SLICE_E_COMMIT_PLACEHOLDER>`
> **Last updated:** 2026-05-17 (FM-04a Phase 16 A-E drift-attribution cross-surface binding FULLY CLOSED locally; closes Phase 15 retro §3 (cumulative trust-score-timeline drift attribution) + §4 (cross-axis percentage delta as cohort-anomalies scaling axis) + §6 (per-axis percentage delta beyond alerts+timeline) + §7 (8-token forbidden-positive-claim tuple SSOT) + §8 (`_assert_tier1_trio` audit helper SSOT). 4/4 slices shipped: slice A `47b1374` cumulative drift attribution on TrustScoreTimeline (`TRUST_SCORE_TIMELINE_SCHEMA_VERSION` 1.1.0→1.2.0 with bump-history; additive `cumulative_drift_attribution: object | None` field spanning `points[0]` → `points[-1]`; consumer IMPORTS Phase 15 C `compute_drift_attribution` SSOT helper (M:-2 no inline math); methodology paragraph appended with "20→10→20 recovery" worked example documenting cumulative-vs-per-pair distinction; 11 tests with T:-4 degenerate-case pins (0-point / 1-point → None; 2-point → cumulative EQUALS single per-pair) + T:-3 leak arc cumulative dominant_axis=="energy_audit" + dominant_delta_pct==-100.0 exactly); slice-A TAA APPROVE **63/63** every axis at cap. Slice B `0293fea` cohort-scoped drift attribution on cohort-anomalies: NEW SSOT module `backend/app/services/reporting/cohort_drift_attribution.py` with `COHORT_DOMINANT_AXIS_FLOOR_PCT: float = 5.0` (strictly-exceed semantic, parallel to per-case floor) + `CohortDriftAttribution` frozen dataclass + `compute_cohort_drift_attribution(*, repo_root, dominant_floor_pct=5.0)` builder (walks signed-registry-filtered `*-candidate/` cases, finds cohort-wide latest snapshot pair chronologically, surfaces (case, axis) pair with largest |delta_pct| strictly-exceeding floor) + `render_cohort_drift_attribution_dict` JSON helper; `COHORT_ANOMALIES_SCHEMA_VERSION` 1.0.0→1.1.0 with bump-history; cohort-anomalies envelope wires new `cohort_drift_attribution` field additively (z-score view preserved); 15 tests with T:-3 boundary pins (5-case cohort with leak energy 15→0 lands `cohort_dominant_axis=="energy_audit"` + `dominant_case_id==LEAK_CASE_ID` + `cohort_max_abs_delta_pct==100.0` exactly) + A:-2 defensive parser raises on non-positive floor + returns None on <2 snapshots + C:-1 Tier 1 trio + live ASGI + back-compat; new methodology doc `.planning/methodology/cohort_drift_attribution.md`; slice-B TAA APPROVE **63/63** every axis at cap. Slice C `bbe3402` drift_attribution_at_signoff_time on signoff records: `SIGNOFF_RECORD_SCHEMA_VERSION` 1.0.0→1.1.0 with bump-history; additive `drift_attribution_at_signoff_time: object | None` field on `SignoffRecord` dataclass; server-side helper `_compute_drift_attribution_at_signoff_time(case_id, *, repo_root)` returns `build_trust_score_timeline(case_id, repo_root).inter_snapshot_drift_attribution[-1]` (latest snapshot pair at signoff time) or None when no transition exists; **A:-3 LOAD-BEARING SERVER-COMPUTED PIN**: `write_signoff_record` signature accepts NO drift parameter (pinned by `inspect.signature` test — a future maintainer who adds a client-trusted kwarg trips the test); back-compat `_parse_drift_attribution(blob)` handles None / dict / NaN / corrupted JSON gracefully; 13 tests with T:-3 snap-2→snap-3 boundary pin (dominant_axis=="energy_audit" + dominant_delta_pct==-100.0 exactly) + fresh 2-snapshot 15→0 arc + A:-3 server-computed audit + round-trip JSON + back-compat 1.0.0 reader; slice-C TAA APPROVE **63/63** every axis at cap with 9 adversarial probes including forged-kwarg TypeError + corrupted-JSON graceful-degrade + snapshot-tree-not-mutated. Slice D `02b3862` 2 E2E reviewer journeys + SSOT test-utility consolidation: Journey 1 `test_phase16_journey_drift_audit_trail.py` (10 tests) walks **4 distinct route/verb pairs** (cohort-anomalies / trust-score-timeline / signoff-history GET / signoff-history POST) pinning all 3 drift_attribution surfaces (cohort + cumulative + signoff-pinned) at boundary values (-100.0 / 100.0 / "energy_audit" / LEAK_CASE_ID); A:-3 server-computed body audit (POST request body has NO drift_attribution field); per-route 422-refusal matrix covers GET trust-score-timeline + GET signoff-history + POST signoff-history (cohort-anomalies non-parameterized — documented). Journey 2 `test_phase16_journey_cumulative_vs_consecutive_drift.py` (10 tests) pins the Phase 16 A cumulative-vs-per-pair invariant on TWO arc shapes: stuck regression arc (15→15→0; cumulative MATCHES worst per-pair, dominant_delta_pct==-100.0) AND recovery arc (15→0→15; cumulative collapses to dominant_axis=None sub-floor while per-pair entries still surface energy_audit on at least one transition). SSOT consolidation `tests/_test_utils/__init__.py` hoists `FORBIDDEN_POSITIVE_CLAIM_TOKENS_8` (8 envelope-rendering tokens skipping `certified`) + `FORBIDDEN_POSITIVE_CLAIM_TOKENS_9` (9 strict source-file tokens including `certified`) + `assert_tier1_trio(envelope, *, check_impact=True)` + `assert_no_forbidden_positive_claims(text, *, tokens, allow_no=True)`; Phase 15 D Journey 1 + 2 + Phase 15 C + Phase 16 A + Phase 16 B drift test files refactored to consume SSOT (closes Phase 15 retro §7 + §8). Meta-test `tests/test_phase16_test_utils_ssot.py` (11 tests) enforces no inline duplication via LEXICAL fingerprint detection (>= 5 of 9 tokens in tuple-shape for the forbidden-token SSOT; `def _assert_tier1_trio(` / `def assert_tier1_trio(` without `from tests._test_utils` import + `assert_tier1_trio(` call for the trio audit SSOT); ad-hoc inline 3-assert blocks NOT in scope (Phase 15 retro §8 consolidates HELPERS, not all inline assertions). Slice-D TAA APPROVE **63/63** every axis at cap with 10 adversarial probes (boundary pins TRIP when dominant_delta_pct halved; SSOT fingerprint detection at 5/9 threshold; thin-wrapper acceptance vs body-inlined helper rejection; per-route 422-refusal matrix exhaustive; `check_impact=False` knob; forged-kwarg TypeError; `reports/snapshots/` + `golden_samples/` byte-identical pre/post run; recovery arc invariant). New SSOTs: `COHORT_DOMINANT_AXIS_FLOOR_PCT=5.0` + `CohortDriftAttribution` dataclass + `FORBIDDEN_POSITIVE_CLAIM_TOKENS_8/_9` + `assert_tier1_trio` + `assert_no_forbidden_positive_claims` + `EXPECTED_ROUTES_CROSSED` (Journey 1 4-route frozenset) + `EXPECTED_ARC_SHAPES` (Journey 2 2-shape frozenset) + `TOKEN_TUPLE_FINGERPRINT` + `LOCAL_TRIO_DEF_PREFIXES`. **Per-slice TAA: 4/4 first-cut APPROVE, 63+63+63+63 = 252/252 = 100%** with zero HIGH/MEDIUM/LOW findings across all 4 audits. **FINAL whole-arc TAA APPROVE 100/100** with every axis at 100% of weight — stop condition (≥99 AND every axis ≥95%) MET with maximum margin. Per-axis: B 12/12, M 12/12, T 15/15, C 12/12, X 12/12, D 8/8, A 8/8, E 8/8, V 13/13. 12 adversarial probes performed (≥3 mandatory + ≥3 extra met): cumulative sign flip trips 3 boundary pins; cohort floor bump to 200% trips 4 pins; A:-3 server-computed posture confirmed via `inspect.signature` + forged-kwarg TypeError; SSOT meta-test fingerprint detection works at 5/9 threshold; all 4 schema versions match SSOT (timeline 1.2.0 / alerts 1.1.0 / cohort 1.1.0 / signoff 1.1.0); all 5 consumer renderers (cohort + signoff + timeline-per-pair + timeline-cumulative + alerts) delegate to `render_drift_attribution_dict` SSOT (no parallel implementation); `reports/snapshots/` + `golden_samples/` byte-identical pre/post test runs; HF1 path-guard exits 0; 119 HF1/signed_registry tests pass; defensive parsers reject non-positive floors + corrupted JSON. FINAL.md archived at `.planning/phase16_audit_reports/FINAL.md`. Backend **2527/2527 + 7 skipped** (was 2457; +70 tests across slices A/B/C/D — A 11, B 15, C 13, D 31 [J1 10 + J2 10 + meta 11]); frontend unchanged from Phase 15 (135/135). FM-04a Phase 15 carry-forward state preserved below for context. Phase 15 stamp `fm04a-phase15-explicit-dynamics-cohort-substantiation-CLOSED-LOCAL-2026-05-17 · @892e5d1` preserved in git history. Nothing pushed; no PR opened; no Linear / Notion writes; no FM-04b prerequisite crossed.
>
> Phase 15 (CLOSED 2026-05-17 @ `892e5d1`): A-E explicit_dynamics cohort substantiation + cross-snapshot drift attribution FULLY CLOSED locally; closes Phase 14 retro §1 (per-axis drift attribution surface deferred from Phase 7 C) AND the modal-vs-explicit_dynamics cohort-parity gap. 4/4 slices shipped: slice A `3e24588` 2 additional explicit_dynamics candidate fixtures (`rod-wave-impact-stiff-candidate` healthy variant @1.71% residual within `WAVE_CROSS_CHECK_TOLERANCE_PCT=5.0%` + `rod-wave-impact-energy-leak-candidate` regressed variant with synthetic energy injection at `LEAK_INJECTION_FRAME=30` × `LEAK_INJECTION_SCALE=1.5` flagging exactly frame 30 with rel_drift ~ 0.50) + 22 tests with load-bearing A:-3 audit-computed pattern (re-runs `energy_partition_audit` on the parsed manifest, NOT trusting fixture's self-reported field); slice-A TAA APPROVE **63/63** zero findings. Slice B `51799ac` 3-snapshot degradation arc (`test_phase15_explicit_dynamics_cohort_arc.py`, 11 tests) over the 3-case explicit_dynamics cohort: snap-1 (3 healthy, leak in synthesized clean variant) → snap-2 (canonical+stiff healthy, leak watching) → snap-3 (canonical+stiff healthy, leak regressed via 3 optional-artifact drops); EXACT per-snapshot bucket counts (3/0/0, 2/1/0, 2/0/1) COMPUTED via live `build_trust_score_timeline` route, NOT trusted from hand-rolled manifest; slice-B TAA APPROVE **63/63** every axis at cap. Slice C `7efc3ba` cross-snapshot drift attribution surface: new SSOT module `backend/app/services/reporting/trust_score_drift_attribution.py` with `DRIFT_DOMINANT_AXIS_DELTA_FLOOR_PCT=5.0` (strictly-exceed semantic) + `TRUST_AXIS_WEIGHTS` mapping (completeness=50/convergence=20/energy_audit=15/reproducibility=15, pinned to sum to 100) + `DriftAttribution` frozen dataclass + `compute_drift_attribution` pure-function builder + `render_drift_attribution_dict` JSON helper (NaN→null); MINOR schema bumps `TRUST_SCORE_ALERTS_SCHEMA_VERSION` 1.0.0→1.1.0 + `TRUST_SCORE_TIMELINE_SCHEMA_VERSION` 1.0.0→1.1.0 with bump-history docstrings; consumers IMPORT helper (no inline percentage math, anti-gaming M:-2); 20 tests with T:-3 boundary pins (energy_audit 15→0 = -100.0% exactly; completeness 50→42 = -16.0% exactly); new methodology doc `.planning/methodology/trust_score_drift_attribution.md`; slice-C TAA APPROVE **63/63** every axis at cap. Slice D `892e5d1` 2 E2E reviewer journeys: `test_phase15_journey_explicit_dynamics_drift_triage.py` (13 tests) walks 6 distinct routes for leak case at snap-3 (cohort-executive-summary → trust-score-alerts → trust-score-timeline → case-completeness → advisor-critique → signoff-history) + per-route GS-001 422-refusal regression-guard on 5 parameterized routes via Phase 14 A cross-route SSOT; `test_phase15_journey_cross_axis_cohort_comparison.py` (11 tests) constructs 5-case cohort (3 explicit_dynamics + 2 linear_static_pv via cylinder-pv-candidate + cylinder-pv-extended-candidate) with FLAT timelines for 4 cases + STRICTLY DECREASING leak case, cohort-anomalies pins leak as SOLE outlier on energy_audit axis + NEITHER PV case in anomaly set (A:-2 cross-analysis-type leakage guard); 12 distinct (route, case) tuples crossed (>= 10 per blueprint); tmp_path-only snapshot writes (real `reports/snapshots/` byte-identical pre/post run); slice-D TAA APPROVE **63/63** every axis at cap with 2 adversarial probes confirming `-100.0` + `cohort_count == 5` are EXACT pins. New SSOTs: `DRIFT_DOMINANT_AXIS_DELTA_FLOOR_PCT=5.0` + `TRUST_AXIS_WEIGHTS` 4-key + `EXPLICIT_DYNAMICS_COHORT_CASES` 3-tuple + `LEAK_INJECTION_FRAME=30` + `LEAK_INJECTION_SCALE=1.5` + case-id constants + 3 snap-label SSOTs. **Per-slice TAA: 4/4 first-cut APPROVE, 63+63+63+63 = 252/252 = 100%** with zero HIGH/MEDIUM/LOW findings across all 4 audits. **FINAL whole-arc TAA APPROVE 100/100** with every axis at 100% of weight — stop condition (≥99 AND every axis ≥95%) MET with maximum margin. Per-axis: B 12/12, M 12/12, T 15/15, C 12/12, X 12/12, D 8/8, A 8/8, E 8/8, V 13/13. 6 adversarial probes performed (3 mandatory + 3 extra) all reverted cleanly. Backend **2457/2457 + 7 skipped** (was 2379; +78 tests across slices A/B/C/D); frontend unchanged from Phase 14 (135/135). FM-04a Phase 14 carry-forward state preserved below for context. Phase 14 stamp `fm04a-phase14-explicit-dynamics-substantiation-CLOSED-LOCAL-2026-05-17 · @7e7638b` preserved in git history. Nothing pushed; no PR opened; no Linear / Notion writes; no FM-04b prerequisite crossed.
>
> Phase 14 (CLOSED 2026-05-17 @ `7e7638b`): A-E explicit_dynamics substantiation + cross-route signed-registry meta-guard FULLY CLOSED locally; closes v1 blueprint image #06 row 3 (explicit_dynamics candidate case carried forward from Phase 11 retro §A) + Phase 13 retro slice-B LOW #3 (cross-route meta-guard). 4/4 slices shipped: slice A `2dcdab7..5779fe7..071a0f2` cross-route SSOT helper `_signed_registry_refusal.py` + 14 reviewer-facing routes harmonized to call `assert_not_signed_registry` (12 newly + advisor-critique + case-completeness migrated from inline refusal; +38 meta-tests with `_KNOWN_CASE_ID_ROUTES` SSOT tuple enumeration + per-route parametrize over candidate-passes + 4-variant shape probes; slice-A TAA returned REQUIRES_REWORK 55/63 with HIGH-1 visualization.py ordering + HIGH-2 stragglers + LOW-1 candidate-passes single-anchor + LOW-2 missing methodology paragraph; rework `5779fe7` closes all 4; slice-A re-audit APPROVE_WITH_COMMENTS 63/63 with LOW-3 follow-up `071a0f2` closing signoff POST through the SSOT). Slice B `b72c507` explicit_dynamics_extraction service + 1D-bar wave-propagation analytical cross-check + 32 tests (TAA APPROVE_WITH_COMMENTS 61/63; LOW-1 ANALYSIS_TYPE_TUPLE[3]→[2] docstring drift closed in slice-C commit). Slice C `9aba727` StubAdvisor 4-theme explicit_dynamics branch (CFL stability / energy partition closure / contact stiffness convergence / wave reflection vs BC) with 12 distinct-theme-header tests; legacy Phase 11 mass-scaling+dt/hourglass tokens preserved; TAA APPROVE 63/63 zero findings with strong inter-slice integration (theme 4 cross-references slice-B `bar_wave_first_reflection_s`). Slice D `373ab88` rod-wave-impact-candidate fixture (synthetic 1D rod L=1m steel + v=10 m/s impact + 100 frames @ 10us; Hopkinson-style closed energy balance) + deterministic generator + 17 tests; the load-bearing A:-3 test RE-DERIVES analytical from the fixture's self-reported material constants and asserts observed-vs-analytical residual within `WAVE_CROSS_CHECK_TOLERANCE_PCT` (5%) — NOT just trusting the fixture; live ASGI case-completeness `/api/v1/case-completeness/rod-wave-impact-candidate?analysis_type=explicit_dynamics` lands **95/100** (load-bearing axes all full-points; only `result_mesh` 5 pts absent). New SSOTs: `WAVE_CROSS_CHECK_TOLERANCE_PCT=5.0` (5% engineering ballpark for 1D-rod first-reflection cross-check) + `EXPLICIT_DYNAMICS_CONVERGENCE_KIND="explicit_dynamics"` + `ENERGY_PARTITION_EPSILON=1e-9` + `ENERGY_PARTITION_DRIFT_FRACTION=0.01` + `_KNOWN_CASE_ID_ROUTES` 13-tuple + `_OPT_OUT_ROUTES` 4-tuple. New methodology docs: `case_id_route_discipline.md` + `explicit_dynamics_cross_check.md`. Backend **2379/2379 + 7 skipped** (was 2280; +99 tests across slices A/B/C/D); frontend unchanged from Phase 13 (135/135). FM-04a Phase 13 carry-forward state preserved below for context:
>
> Phase 13 (CLOSED 2026-05-17 @ `c3f86c9`): A-E carry-forward closure FULLY CLOSED locally; closes Phase 11 retro §4 (permissive 4xx) + §5 (structured refused_claims) + Phase 12 retro §3 (HF1.7 ADR amendment) + §4 (deeper-degradation 5th cohort case). 4/4 first-cut APPROVE on slices A-D with per-slice TAA scores 59 (A; HIGH+MEDIUM closed inline in B), 60 (B), 63 (C; perfect with live ASGI verification), 60 (D; MEDIUM-1 doc-vs-code inconsistency closed inline in E); average 60.5/63 = 96%. ADVISOR_CRITIQUE MINOR bump 1.0.0→1.1.0 with structured refused_claims surface + close-set suffix validation. ADR-011 amended (AR-2026-05-16-001) splitting HF1.7 into HF1.7a (signed-registry hard-stop) + HF1.7b (`*-candidate` writable carve-out, defense in depth via canonical fullmatch + prefix shape rejection); audit log rolled over to window-001. New synthetic cohort case `cylinder-pv-collapsed-candidate` lands snapshot-3 trust at ~43 (regressed-bucket trigger load-bearing). Meta-test ceiling-driven drift guard (`tests/test_phase13_status_code_discipline.py`) pins permissive 4xx assertions to 0 across the test suite. Backend 2280/2280 + 7 skipped; frontend 135/135 across 13 files; tsc exit 0. **FINAL whole-arc TAA APPROVE 100/100** with every axis at 100% of weight — stop condition (≥99 AND every axis ≥95%) MET. Per-axis: B 12/12, M 12/12, T 15/15, C 12/12, X 12/12, D 8/8, A 8/8, E 8/8, V 13/13. Phase 12 closure stamp `fm04a-phase12-cohort-substantiation-CLOSED-LOCAL-2026-05-16 · @36ad732` preserved in git history. Nothing pushed, no PR opened, no Linear / Notion writes, no FM-04b prerequisite crossed. The legacy Phase 12 narrative below is preserved for context:
>
> Phase 12 (CLOSED): A-I modal axis end-to-end + cohort substantiation + real anomaly triggers + cohort dashboard defensive parsers + 3 E2E reviewer journeys + 12 supplemental gate tests + slice-H gap-close pass + slice-I consumer-surface closure FULLY CLOSED locally; FINAL whole-arc TAA two-pass arc: first-pass APPROVE_WITH_COMMENTS 98/100 (T 93.3% + X 91.7% shared consumer-surface deduction), post-slice-I re-verification **APPROVE 100/100** with every axis at 100% of weight — **stop condition (≥99 AND every axis ≥95% of weight) MET**. 6/6 first-cut APPROVE on slices A-F (averaging 58.5/63 = 93%, with proportional honest small deductions vs Phase 11's perfect 63/63); slice H closes 6 of the per-slice carry-forwards directly; slice I closes the consumer-surface T+X deduction; FINAL re-verification independently confirms the score lift. Closes the 5 e2e-demo gaps from Phase 11: modal axis was rubric-defined but not behavior-substantiated; trust_score modal branch was Phase-11-promised not tested; cohort surfaces ran on synthetic data only; cohort dashboard had no defensive parser layer; Phase 11 retro §4 permissive 4xx-range assertions. Phase 12 ships: `parse_modal_dat()` + `euler_bernoulli_cantilever_freq()` + `modal_residuals()` + `cumulative_mass_participation()` (slice A); modal substantiated rubric (4 modal-specific axes × 10 + 5 universal axes × 10 = 100) + `StubAdvisor` modal branch with 4 concerns (MAC / Lanczos / mass participation / frequency tolerance) (slice B); 3 new real-runnable candidate cases (modal-cantilever 0.14% err vs analytical; modal-cantilever-stiff 0.18% err; cylinder-pv-extended) (slice C); multi-snapshot time-series with 3-snapshot degradation arc + 2 synthetic filler cases lifting cohort to n=6 (slice D); cohort-dashboard client orchestrator + defensive parsers (4 anti-promotion guards verified) reading raw JSON to surface schema drift as `'unknown'` not `'regressed'` / `'danger'` (slice E); 3 new reviewer journeys (cohort triage 5 routes / cross-case investigation 6 routes / trend alarm closure 4 routes) + 12 supplemental integration tests tightening Phase 11 D permissive ranges to exact-code contracts (slice F); slice-H closes the gap-class findings: Journey 6 conditional-guard skip-through (filesystem pre-condition + service-vs-route parity); Journey 5 cross-leakage forbidden-keyword pins; Journey 4 distinct-(method,url) route counting; 4 new `_score_convergence_axis` modal-branch behavioral tests; slope-recovery semantics methodology doc; HF1 override audit log. MINOR bumps: `CONVERGENCE_STUDY_SCHEMA_VERSION` 1.1.0 → 1.2.0 (mode_count_sweep axis); `CASE_COMPLETENESS_SCHEMA_VERSION` 1.1.0 → 1.2.0 (modal substantiation). Backend 2191/2191 + 7 skipped; frontend 117/117 across 12 files. Phase 11 closure stamp `fm04a-phase11-advisor-surface-CLOSED-2026-05-16 · @60ae3fb` preserved in git history. Nothing pushed, no PR opened, no Linear / Notion writes, no FM-04b prerequisite crossed. The legacy Phase 11 narrative below is preserved for context:
>
> Phase 11 (CLOSED): A-G AI advisor surface + analysis-type-aware reviewer rubric FULLY CLOSED locally with the binding 9-axis scoring rubric + independent Test Auditor Agent (TAA) gating; FINAL whole-arc TAA APPROVE **100/100** with every axis at 100% of weight — stop condition (≥99 AND every axis ≥95% of weight) MET. 6/6 first-cut APPROVE 63/63 across slices A-F (zero CHANGES_REQUIRED rounds, zero fix-up commits across the entire arc — matching Phase 10's perfect first-cut record). Closes two e2e-demo-surfaced gaps: (1) the `case_completeness` rubric was ballistic-hardcoded and penalized correct PV work (75/100 because animation/result-mesh/notes axes were treated as missing evidence on a linear-static analysis that does not produce them); (2) the project's load-bearing AI-is-advisor-not-driver north star (memory `feedback_cfd_harness_ai_advisor_pivot`) had no HTTP route, no UI panel, no test surface. Phase 11 ships: `ANALYSIS_TYPE_TUPLE` SSOT + 4 named rubrics (ballistic / linear_static_pv / explicit_dynamics / modal) with MINOR bumps CASE_COMPLETENESS_SCHEMA_VERSION 1.0.0 → 1.1.0 and CONVERGENCE_STUDY_SCHEMA_VERSION 1.0.0 → 1.1.0; trust_score convergence axis honors the new `convergence_kind` discriminator (linear_static treats dt_sweep as N/A); `AdvisorCritique` schema (NEW 1.0.0) + `AdvisorProvider` Protocol + `StubAdvisor` rule-based always-available impl + `LLMAdvisor` env-var-gated with injectable `llm_call` callable + defensive `_parse_llm_response` with stub-fallback on every shape-drift branch + 4-question-gate audit + 9-token forbidden-claim audit (Tier 1 base 4 + Phase-11 5 = 9); `GET /api/v1/advisor-critique/<case_id>?snapshot=<label>` route with 6-step gate composition (422/422/422/404/422/200; never 5xx for LLM outage); `GET /api/v1/case-completeness/<case_id>?analysis_type=<type>` route extended (default `ballistic` for back-compat); `AdvisorPanel.tsx` frontend mounted adjacent to ProvenancePanel with status badge / degrade_reason / 4-Q-gate checklist / 4 content sections / Tier 1 footer + client-side `isAdvisorEntrySafe` preview audit (defense in depth); 3 E2E reviewer journeys (advisor→signoff→history; LLM-offline workflow; multi-analysis cohort round-trip). Backend 2064/2064 + 7 skipped; frontend 97/97 across 11 files; zero real LLM API calls anywhere (LLMAdvisor placeholder caught by produce-time stub fallback). Nothing pushed, no PR opened, no Linear / Notion writes, no FM-04b prerequisite crossed). Phase 10 closure stamp `fm04a-phase10-reviewer-action-surface-CLOSED-2026-05-16 · @2aa15fb` preserved in git history.
> **Maintained by:** Codex primary executor (default); under user direct-execution authorization 2026-05-07/16 the FM-03 closeout, FM-04a P1-P9, the local-arc closure commits (`61857f5..88362ad`), the FM-04a Phase 2 industrial polish (`b3c97ef..477c529`), the FM-04a Phase 3 reviewer-workbench polish (`7f726bb..de3e90d`), the FM-04a Phase 4 cohort-operations console (`2399c11..3e2de76`), the FM-04a Phase 5 reproducibility / schema versioning / cohort snapshots stack (`fd23f7f..4df64e2`), and the FM-04a Phase 6 reviewer drift narrative + evidence trust score stack (`cc057c5..1bf3df4` plus this STATE refresh) are authored by local Claude Opus 4.7 with the same ADR-011/012/013/023 boundaries. Codex review remains required for any path that flips this back to Codex-primary or that promotes Tier 1 → Tier 2.

This file is the **repo-side execution status snapshot**. Linear is the work-control truth for scoped issues, acceptance, blockers, and proof. GitHub/repo is the code truth. Notion 项目控制塔 (root_page_id `345c68942bed80f6a092c9c2b3d3f5b9`) is an architecture/control mirror patched after repo and Linear truth settle. When they conflict, **git is authoritative**; STATE.md is updated to match git, and external mirrors are patched from STATE.md.

---

## Phase ledger

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1 — Foundation | ✅ Done (Sprint 2) | See `docs/PHASE1_SPRINT2_COMPLETION.md` and `PHASE1_SPRINT1_COMPLETION.md`. |
| Phase 1.5 — Foundation-Freeze (post-pivot) | ✅ Governance/workflow gates closed: WF-00 / ENG-32 established Codex-primary + Linear work-control + Claude Opus audit; ENG-33 AERON L0 protocol salvage done via #128; FF-07 done via #129; FF-08 done via #131; FF-09 done via #132. Branch protection requires `trailer-check` and `golden-samples-validation`. |
| Phase 1.6 — RFC-001 Foundation rebuild (W1→W4) | ✅ Done 2026-04-26 → 2026-04-27 (#68-#82) | Buckets A/B/C/D + Layer-2/3 schema + CalculiX adapter + L1→L4 producers + report-cli driver. |
| Phase 1.7 — RFC-001 Workbench shell (W5) | ✅ Done 2026-04-27 (#83-#90) | Electron shell + GS-001 quick-start + violation panel + --doctor + viz tracking. |
| Phase 1.8 — RFC-001 Reporting libs + GS-101 ballistic (W6+W7) | ✅ Done 2026-04-28 (#91-#110) | Material/allowable_stress/verdict/BC/model-overview libs + DOCX wiring; OpenRadioss adapter + ballistic derivations + Dockerfile + Electron --kind=ballistic. |
| Phase 1.9 — RFC-001 3D viewport + live bake (W8) | ✅ Done 2026-04-29 (#111-#114) | OpenRadioss → VTU exporter + PyVista viewport + live streaming + Electron live-bake orchestration. |
| Phase 2 — Web Console hardening | 🟡 Active candidate lane (lean validation workflow being adopted) | Frontend build-smoke restoration landed in PR #121. Governance/workflow gates are closed. AERON-01 landed the first concrete AERON L0 backend adapter in PR #135; AERON-02 wired that backend into exactly one solver caller path in PR #137; AERON-03 surfaced backend provenance through graph cold-smoke in PR #139. ENG-39 introduces ADR-023 so Tier 0/Tier 1 development can move faster while signed physical claims remain strictly gated. |
| Phase 3 — Nonlinear & adaptive mesh | ⚪ Planned | No dates committed. |

---

## Phase 1.5 — Foundation-Freeze final tally

| Task | Status | PR | Commit | Notes |
|------|--------|----|--------|-------|
| FF-01 — ADR-011 Pivot baseline | ✅ Merged 2026-04-25 · R5 APPROVE | #17 | `34722ea` | 5-round Codex arc; reports at `reports/codex_tool_reports/adr_011_r{1..5}_review.md`. |
| FF-01a — ADR-011 amendments AR-2026-04-25-001 | ✅ Merged 2026-04-25 · R1 CR → R2 APPROVE | #23 | `e53b0f7` | T2 rewording, §HF1/§HF2 narrowing, §Enforcement Maturity update. |
| FF-01b — Notion Decisions DS sync | ✅ Done | (Notion API) | n/a | Page id `34dc6894-2bed-81f0-bf9a-edceb840945d`. |
| FF-02 — GS deviation attribution → FailurePatterns | ✅ Merged 2026-04-25 | #18 | `77e6813` | 3 FPs (FP-001/002/003); R1 CR → R2 APPROVE. |
| FF-05 — STATE.md | ✅ Merged 2026-04-25 | #19 | `4a64cfd` | Adopts `.planning/` directory convention. |
| FF-06 — pre-commit path-guard for HF1 forbidden zone | ✅ Merged 2026-04-25 | #22 | `ac98fc3` | `scripts/hf1_path_guard.py` + 30 tests. R1 CR → R2 APPROVE. |
| ADR-012 — Calibration cap for T1 self-pass-rate | ✅ Merged 2026-04-26 01:01Z | #24 | `6f660ba` | Mechanical 5-PR rolling-window ceiling. CI workflow `.github/workflows/calibration-cap-check.yml` enforces on every PR. |
| ADR-013 — Branch protection enforcement | ✅ Merged 2026-04-26 01:02Z | #25 | `303233c` | 3-layer wrapper (PR template + CI `--check` workflow + `gh api` protection script). |
| FF-07 — CI commit-trailer presence + claim-id format check (HF5) | ✅ Merged 2026-05-06 · Claude Opus APPROVE · CI green | #129 | `e62a4e7` | Supersedes blocked PR #27 and closed duplicate #117. Adds trusted-main trailer validator, `pull_request_target` workflow, branch-protection `trailer-check` context, PR template merge trailers, and docs/ADR sync. Branch protection applied 2026-05-06; `trailer-check` is now required on `main`. |
| FF-08 — `golden_samples/<id>` registry schema validation (HF3) | ✅ Merged 2026-05-06 · Claude Opus APPROVE · CI green · Linear ENG-17 Done | #131 | `0913792` | Adds trusted signed-registry validator, always-on `golden-samples-validation` workflow, ADR-011/013 sync, symlink-bypass fix, and branch-protection context update. Old #28 closed as superseded. |
| FF-09 — README ↔ ADR-011 sync (Golden Rules vs 5 dev rules) | ✅ Merged 2026-05-06 · Claude Opus APPROVE · CI green · Linear ENG-18 Done | #132 | `a5c3dc4` | Syncs README quick rules, ADR-011 maturity/cross-reference text, and `docs/governance/` routing/onboarding with Codex-primary workflow truth. Old #26 closed as superseded. |

---

## Phase 1.6-1.9 highlights (RFC-001 W1-W8 build-out, 2026-04-26 → 2026-04-29)

> Full per-PR ledger in `git log a254a23 --grep "RFC-001 W"`. Below is the architectural beat sheet.

- **W1 (PR #68)** — Foundation rebuild buckets A/B/C/D; Layer-2/3 schema + handoff doc.
- **W2 (PR #69)** — CalculiX Layer-1 adapter on `ReaderHandle` Protocol (first concrete reader).
- **W3a/W3b/W3c (PRs #70/#71/#76)** — Layer-3 derivations: stress derivatives (vM/principals/max-shear) + Quantity unit conversion + ASME VIII Div 2 §5.5 SCL stress-linearization.
- **W4 (PRs #72-#78)** — Layer-4 services/report: `draft.py` (L1→L3→L4 spine) + `exporter.py` (DOCX export) + `templates.py` (template specs+validation) + 3 producers (`generate_*_summary`) + `report-cli` engineer driver.
- **W5 (PRs #83-#90)** — Electron workbench shell: minimal shell over report-cli, GS-001 quick-start button, structured violation panel, `--doctor` install probe, ADR-018 (defer electron-builder packaging), per-stage progress lines, viz tracking (mesh/displacement/von_mises figs).
- **W6 (PRs #91, #98-102, #109-110)** — Reporting libraries with DOCX wiring: material data (W6a, ADR-019), allowable_stress GB/ASME (W6b, ADR-020), verdict PASS/FAIL+safety_factor (W6c+W6c.2), boundary-condition summary (W6d+W6d.2), model-overview + SupportsElementInventory (W6e+W6e.2).
- **W7 (PRs #92-97, #105-108)** — OpenRadioss / ballistic track: Layer-1 adapter (W7b), animation manifest (W7c), Layer-3 ballistic derivations (W7d), summary template (W7f), Dockerfile (W7-tools), RFC-002 retrospective (W7g), `--kind=ballistic` Electron wiring (W7h), ADR-021 (gs100-radioss-smoke-fixture), ADR-022 (gs101-demo-unsigned).
- **W8 (PRs #111-114)** — 3D viewport + live bake: OpenRadioss → VTU + viewport manifest exporter (W8a), PyVista native viewport + Electron Open-3D-viewport button (W8b), live streaming exporter + viewport polling (W8c), Electron live-bake one-click ballistic demo (W8d).

---

## Repo state

`origin/main == 9d77042` (post ENG-44 PR #148 merge, 2026-05-07).

ENG-39 created 2026-05-06 to adopt a lean validation workflow:

- Tier 0 sandbox/demo work moves quickly with explicit software-path-only labels.
- Tier 1 engineering-candidate work uses compact reproducibility manifests and automatic read-only Claude Opus review when triggered.
- Tier 2 signed validation remains strict at the physical-claim boundary: benchmark, metrics, tolerance comparison, convergence, hashes, and reviewer/signoff.
- This change is governance/documentation only and does not mutate `golden_samples/**`, solver decks, schemas, protocols, CI, dependencies, or signed-validation evidence.
- PR #143 merged 2026-05-07 for ENG-39. The same branch introduced
  `.planning/ROADMAP.md` and `docs/governance/goal_driven_development.md` so
  future feature work is organized as Linear-backed milestone `/goal` runs with
  Claude Opus read-only review gates.
- ENG-40 / FM-01 merged in PR #144 at `776fdae`. It added the first Tier 0 Web
  Console operator shell/status surface and closed with local Claude Opus 4.7
  owner-gate `APPROVE_TO_MERGE`. Linear ENG-40 is Done as an issue-level slice;
  human acceptance remains deferred to the feature-milestone experience
  checkpoint.
- ENG-41 merged in PR #145 at `4a6caf1`. It documents the delegated Claude
  Opus 4.7 issue-level owner gate and keeps human acceptance at feature
  milestone checkpoints. Linear ENG-41 is Done.
- ENG-42 / FM-01 merged in PR #146 at `222e9f4`. It made the operator shell
  derive case/run/evidence/next-action values from existing frontend session
  state. Linear ENG-42 is Done as an issue-level slice.
- ENG-43 / FM-01 merged in PR #147 at `f133f5a`. It added current solver job
  id/status, active analysis mode, and software-path backend provenance to the
  operator shell from existing frontend session state. Linear ENG-43 is Done.
- ENG-44 / FM-01 merged in PR #148 at `9d77042`. It prepared the repo-local
  FM-01 candidate acceptance packet for human milestone experience review.
  FM-01 remains not user-accepted until the human milestone checkpoint records
  it.
- ENG-45 / FM-01 polish is active after milestone experience found a recoverable
  UX defect: a backend solver startup failure can leave the operator shell stuck
  in `running` / `stop requested` with `Run Solver` disabled. Branch
  `codex/ENG-45-fm01-solver-failure-recovery` starts from `9d77042` and is
  limited to frontend state recovery plus repo-local evidence. PR #149 merged
  2026-05-07 at `de65d15`.
- FM-03 candidate report spine slice committed locally on
  `codex/evidence-first-workbench-trust-center` under user direct-execution
  authorization 2026-05-07. Adds `backend/app/services/candidate_report_spine.py`,
  the `mesh_quality.json` Tier 1 sidecar in `agents/mesh.py`, frontend Trust
  Center / Copilot consumption of spine fields, and the
  `reports/fm03_candidate_report_spine_source_map.md` source map. Claim tier:
  Tier 1 engineering candidate; not signed validation; not benchmark agreement.
  Verification (re-run on this machine 2026-05-07): backend candidate-spine tests
  3 passed; mesh agent tests 4 passed; frontend `tsc -b && vite build` clean;
  `eslint .` clean; `git diff --check` clean; `git diff --name-only -- golden_samples`
  empty. Forbidden-wording audit clean. PR / trailer rewrite is reserved for the
  human user. No Linear/Notion mutation.
- FM-04a Tier 1 ballistic candidate full-flow milestone authored under
  user direct-execution authorization on 2026-05-07 to advance toward the
  bullet-through-steel transient simulation goal. Plan stages P0 → P6 against
  Børvik 2002 hemispherical Ø20mm projectile / 12mm Weldox 460E plate
  parameters (parameters-only, ADR-024 lite). FM-04a does NOT promote any GS
  sample to signed validation, does NOT claim benchmark agreement, and does NOT
  start FM-04b (Tier 2 signed validation gate). The forbidden-wording set in
  ADR-023 §Tier 0 still applies to every artifact in this milestone.
- FM-04a all nine phases (P1 ballistic spine extension, P2-lite ADR-024,
  P3 GS-102-candidate registration, P4 OpenRadioss AERON adapter,
  P5 mesh × time-step convergence study scaffold, P6 residual-velocity /
  perforation metric extraction + frontend Trust Center surfacing,
  P7 Tier 1 convergence sidecar writers, P8 end-to-end synthetic pipeline,
  P9 FM-04b readiness doc) are committed locally on
  `claude/FM-04a-tier1-ballistic-candidate` (descended from
  `codex/evidence-first-workbench-trust-center`). Verification gates re-ran
  on this workstation after every phase: backend candidate-spine, extractor,
  and convergence-writer tests passed (26 cases total in those three test
  files); mesh agent + OpenRadioss adapter + synthetic-pipeline tests
  passed; full repo-root pytest passed (1141 / 9 skipped); frontend
  `tsc -b && vite build` and `eslint .` clean throughout. No PR opened, no
  Linear issue created, no Notion mutation, no merge to main. Trailer
  rewrite for `trailer-check` / `calibration-cap-check` / ADR-013 PR
  template is reserved for the human user when the branches are pushed.
- `.planning/FM-04B_READINESS.md` authored at FM-04a P9 closeout
  documents what FM-04a delivered, what it deliberately deferred, what
  Tier 2 needs that is still missing, and the FM-04b path. The document is
  preparation material only; it does NOT promote any artifact to Tier 2 and
  does NOT authorize FM-04b to start.
- FM-04a local-arc closure (commits `61857f5..88362ad`, 2026-05-16) wrapped
  the 2026-05-12 GS-102 velocity-bracket / mechanism-diagnostic exploration
  into seven atomic commits: gitignore for GS-001 local report output;
  OpenRadioss dynamic result-mesh exporter + viewer endpoint; frontend
  result-mesh playback panel + bullet-plate blueprint surfaces; GS-102
  candidate deck refinement (JC damage + BCS clamp + TYPE7 contact + engine
  retune) with the pipeline result-mesh wiring; new `GS-102-hifi-candidate`
  + `GS-102-refined-candidate` deck variants + generators; 33 GS-102
  transient candidate run reports (synthesis + per-run). Two HF1 path-guard
  overrides cited ADR-011 §HF1.7 + FM-04a P3 precedent (`-candidate` suffix
  is registry-excluded). All Tier 1 candidate evidence; no `^GS-\d{3}$`
  mutation; no Linear / Notion writes; no PR opened.
- `.planning/FM-04A_PHASE2_BLUEPRINT.md` authored at `7d7e5c6` (2026-05-16)
  as the local execution plan for closing four industrial-readiness gaps
  surfaced by the exploration arc.
- FM-04a Phase 2 A-F shipped 2026-05-16 (commits `b3c97ef..477c529`):
  * **Phase A** (`b3c97ef`) — `backend/app/services/ballistics/{engine_energy_history,energy_audit_extractor}.py` graduate the energy audit from `partial_candidate` to `closed_aggregate` by parsing the OpenRadioss `model_00_0001.out` progress table. 17 new tests. Pipeline emits the new `energy_audit` block alongside the legacy `partial_energy_audit` so the 33 historical reports keep their read contract.
  * **Phase B** (`346c32a`) — `backend/app/services/ballistics/convergence_orchestrator.py` + `scripts/gs102_convergence_sweep.py` build a 2-axis mesh × dt convergence study from existing `ballistic_metrics.json` sidecars with a combined `candidate_observed_stable / unstable / insufficient_data` verdict. 14 new tests. CLI smoke against the CFL diagnostic series correctly flagged dt-axis instability (56% jump between cfl_0.95 and cfl_1.00).
  * **Phase C** (`3476280`) — `/api/v1/candidate-cases` endpoint + `frontend/src/candidateCaseRegistry.ts` + `CandidateCasePicker.tsx` let users switch between the three `*-candidate` decks. 7 backend + 7 frontend tests. Signed `^GS-\d{3}$` registry never exposed through the picker.
  * **Phase D** (`4a52a1a`) — `frontend/src/trustCenterSummary.ts` adds 3 Trust Center review cards (energy_balance_status, convergence_study_status, candidate_case_selection) with pure tone helpers; ChatPanel filter updated. 15 new frontend tests.
  * **Phase E** (`15b671f`) — `backend/app/services/reporting/tier1_candidate_report.py` + `/api/v1/tier1-report/<case-id>` endpoint + `scripts/export_tier1_candidate_report.py` CLI build a structured markdown + DOCX packet consolidating every Phase 2 surface plus artifact hashes + Tier 1 banner. 10 new tests. Build-time forbidden-wording audit.
  * **Phase F** (`477c529`) — `tests/test_fm04a_phase2_e2e.py` proves the full A → B → C → E loop on synthetic inputs in one 0.5s test, including the combined forbidden-wording audit across markdown + study payload + picker payload + audit block.
- Final mechanical state on `claude/FM-04a-tier1-ballistic-candidate`
  after Phase 2 closure: backend pytest **1293 passed / 8 skipped**;
  frontend node:test **29 passed**; `tsc -b` + `vite build` clean.

`.planning/FM-04A_PHASE3_BLUEPRINT.md` authored at `f22f619` (2026-05-16)
as the local execution plan for closing five reviewer-experience gaps
identified after the Phase 2 industrial-readiness pass:
R1 acceptance evidence packet; R2 case comparison; R3 reviewer panel;
R4 convergence study viewer; R5 HTTP-layer endpoint tests.

- FM-04a Phase 3 A-E shipped 2026-05-16 (commits `7f726bb..de3e90d`):
  * **Phase A** (`7f726bb`) — `backend/app/services/reporting/acceptance_packet.py` + `/api/v1/acceptance-packet/<case-id>` + `scripts/export_acceptance_packet.py` build a structured Tier 1 candidate manifest with deck/evidence/visualization artifact hashes, ballistic / energy / convergence summaries, assumptions, limitations, and an explicit 8-tuple of FM-04b blockers remaining. 9 new tests. `_assert_no_overclaim` refuses to emit any positive claim; `_assert_not_in_golden_samples` refuses to write under `golden_samples/**`.
  * **Phase B** (`c7d71eb`) — `backend/app/services/reporting/case_comparison.py` + `/api/v1/case-comparison?a=<id>&b=<id>` diff two acceptance packets across residual velocity, perforation marker, energy balance error, energy audit status, convergence verdict, deck artifacts, and evidence artifacts (with shared / a-only / b-only / hash-changed buckets). 9 new tests. Comparison is case-vs-case (not vs experimental benchmark data).
  * **Phase C** (`73c4b3d`) — `frontend/src/{acceptancePacketClient,caseComparisonClient}.ts` typed clients + `frontend/src/components/{AcceptancePacketPanel,CaseComparisonPanel}.tsx` reviewer panels wired into the Visual tab between the candidate picker and blueprint. 15 new frontend tests. Two new Trust Center review cards (`acceptance_packet_status`, `case_comparison_status`) surface the boundary in the operator strip.
  * **Phase D** (`2796a20`) — `backend/app/api/routes/convergence_study.py` (NEW sidecar endpoint) + `frontend/src/convergenceStudyClient.ts` + `frontend/src/components/ConvergenceStudyViewer.tsx` render the orchestrator payload as two stacked tables (mesh sweep + dt sweep) with per-axis verdict badges + tone-coded rows + a combined verdict badge. 6 backend + 10 frontend tests. `axisTone` + `combinedVerdictTone` route through `trustCenterSummary.convergenceTone` so viewer + Trust Center card stay aligned.
  * **Phase E** (`de3e90d`) — `tests/test_api_endpoints_integration.py` drives every Phase 2 / Phase 3 endpoint through a real HTTP client (httpx.AsyncClient + ASGITransport, the supported migration path now that starlette.testclient is incompatible with httpx >= 0.28). 16 new tests covering status codes, content-types, Content-Disposition, Tier 1 boundary in body, and a cross-endpoint positive-claim audit.

- Final mechanical state on `claude/FM-04a-tier1-ballistic-candidate`
  after Phase 3 closure: backend pytest **1333 passed / 8 skipped**;
  frontend node:test **54 passed**; `tsc -b` + `vite build` clean
  (1739 modules; 325.96 kB / 95.13 kB gzipped).

`.planning/FM-04A_PHASE4_BLUEPRINT.md` authored at `2399c11`
(2026-05-16) as the local execution plan for a Tier 1 cohort-
operations layer above the single-case Phase 3 surface. The blueprint
publishes a binding 8-axis scoring rubric (B/M/T/C/X/D/A/E weighted
to 100; target ≥95 with no axis below 90% of its weight) that every
Phase 4 commit must publish against in a SCORECARD block. Every
Phase 4 commit's SCORECARD is preserved in `git log`.

- FM-04a Phase 4 A-G shipped 2026-05-16 (commits `7f0a52a` and peers
  in `7f726bb..3e2de76`):
  * **Phase A** (`137511e`) — `backend/app/services/reporting/case_completeness.py`
    + `/api/v1/case-completeness/<id>` deterministic 100-point
    evidence-presence rubric (15+15+20+15+15+5+5+5+5 = 100) with
    explicit `claim_impact` stating "100/100 does NOT authorize
    promotion to Tier 2". 9 new unit tests. SCORECARD: 96/100.
  * **Phase B** (`4b5f39b`) — `backend/app/services/reporting/cohort_overview.py`
    + `/api/v1/cohort-overview` scans `golden_samples/*-candidate/`,
    scores each via Phase 4 A, emits aggregate + distribution
    buckets. Signed `^GS-\d{3}$` registry shape rejected at scanner
    level (defense in depth on top of the `-candidate` suffix
    filter). 7 new unit tests. SCORECARD: 97/100.
  * **Phase C** (`a02ba39`) — `backend/app/services/reporting/reviewer_bundle.py`
    + `/api/v1/reviewer-bundle?ids=<csv>` + `scripts/export_reviewer_bundle.py`
    in-memory multi-case zip exporter composing acceptance packet +
    convergence study + Tier 1 markdown + completeness scorecard
    per case plus a top-level `BUNDLE_MANIFEST.json`. 32-case cap
    on the endpoint; cross-member positive-claim audit at build
    time. 8 new unit tests. SCORECARD: 98/100.
  * **Phase D** (`f0b7364`) — `backend/app/services/reporting/archived_packet_diff.py`
    + `/api/v1/archived-packet-diff?a=<relpath>&b=<relpath>`
    archive-vs-archive diff anchored under `reports/`; rejects any
    packet whose `claim_boundary` lacks `tier1_engineering_candidate`;
    rejects path traversal into `golden_samples/**` as defense in
    depth. 6 new unit tests. SCORECARD: 97/100.
  * **Phase E** (`7f0a52a`) — `frontend/src/cohortOverviewClient.ts`
    + `frontend/src/caseCompletenessClient.ts` +
    `frontend/src/components/CohortDashboardPanel.tsx` +
    `frontend/src/components/CaseCompletenessCard.tsx` surface the
    Phase A/B endpoints as the new top-of-Visual-tab panels with
    sortable leaderboard + drill-down + rubric breakdown card +
    new `cohort_completeness_status` Trust Center card. 18 new
    frontend tests. SCORECARD: 98/100.
  * **Phase F** (`e9441cc`) — `frontend/src/reviewerBundleClient.ts`
    + `frontend/src/archivedPacketDiffClient.ts` +
    `frontend/src/components/ReviewerBundlePanel.tsx` +
    `frontend/src/components/ArchivedPacketDiffPanel.tsx` surface
    the Phase C/D endpoints as multi-select export + diff form
    panels. 13 new frontend tests. SCORECARD: 98/100.
  * **Phase G** (`3e2de76`) — `tests/test_phase4_endpoints_integration.py`
    drives every Phase 4 endpoint through httpx ASGITransport
    (status, content-type, content-disposition, body audit) with
    explicit path-traversal rejection test;
    `tests/test_fm04a_phase4_reviewer_workflow_e2e.py` is the one
    6-step load-bearing reviewer-cohort workflow proof on synthetic
    3-case fixture (seed → score → cohort overview → bundle → audit
    → archive-vs-current diff with engineered drift). 12 new tests
    total. SCORECARD: 100/100.

- Final mechanical state on `claude/FM-04a-tier1-ballistic-candidate`
  after Phase 4 closure: backend pytest **1375 passed / 8 skipped**;
  frontend node:test **85 passed**; `tsc -b` + `vite build` clean
  (1739 modules; 347.46 kB / 98.29 kB gzipped). Branch is 35 commits
  ahead of the most recently authored Codex baseline (`de65d15`)
  without any push, PR, Linear, or Notion write. Trailer rewrite for
  `trailer-check` / `calibration-cap-check` / ADR-013 PR template
  remains reserved for the human user when the branch is pushed.
- Phase 4 cumulative scorecard: **97.86/100**, every axis ≥91% of
  weight. Per-axis: B 15.00/15 (100%), M 15.00/15 (100%),
  T 14.14/15 (94.3%), C 10.00/10 (100%), X 10.00/10 (100%),
  D 10.00/10 (100%), A 10.00/10 (100%), E 13.71/15 (91.4%). Stop
  conditions satisfied per Phase 4 blueprint rubric: ≥95 total AND
  every axis ≥90% of weight.

`.planning/FM-04A_PHASE6_BLUEPRINT.md` authored at `cc057c5`
(2026-05-16) as the local execution plan for closing three reviewer-
trust gaps after Phase 5: composite trust score (with transparent
breakdown), templated drift narrative (no LLM), and raw-value
snapshot diff (closing Phase 5 §5 carry-forward). The blueprint
publishes a binding 8-axis scoring rubric (B/M/T/C/X/D/A/E weighted
to 100; target ≥95 with no axis below 90% of its weight) plus 8
Phase-6-specific anti-gaming guards that every Phase 6 commit must
publish against in a SCORECARD block.

- FM-04a Phase 6 A-F shipped 2026-05-16 (commits `cc057c5..1bf3df4`):
  * **Phase A** (`4018671`) — `backend/app/services/reporting/cohort_snapshot.py`
    writes each case's `ballistic_metrics.json` as `metrics/<case>.json`
    next to `completeness/<case>.json` / `reproducibility/<case>.json`;
    `cohort_snapshot_diff.py` gains a `NumericalDelta` sibling list
    with raw residual_velocity / energy_balance / convergence_verdict
    / perforation_marker pairs. MINOR schema bump on both
    `COHORT_SNAPSHOT_MANIFEST_SCHEMA_VERSION` (1.0.0→1.1.0) and
    `COHORT_SNAPSHOT_DIFF_SCHEMA_VERSION` (1.0.0→1.1.0). 10 new tests.
    Closes Phase 5 §5 carry-forward "diff only surfaces drift signals,
    not raw values". SCORECARD: 84/100.
  * **Phase B** (`fbe84c1`) — `backend/app/services/reporting/trust_score.py`
    composite 0–100 score across 4 axes (completeness 50 + convergence
    20 + energy_audit 15 + reproducibility 15 = 100); named weight +
    penalty constants (`COMPLETENESS_WEIGHT`, `CONVERGENCE_WEIGHT`,
    `ENERGY_AUDIT_WEIGHT`, `REPRODUCIBILITY_WEIGHT`,
    `REPRO_PENALTY_GIT_DIRTY=30`, `REPRO_PENALTY_GIT_SHA_MISSING=25`,
    `REPRO_PENALTY_PER_NOT_INSTALLED_PACKAGE=20`). `TRUST_SCORE_SCHEMA_VERSION`
    AND `TRUST_SCORE_FORMULA_VERSION` are independently versioned
    (rebalance bumps formula even when envelope is stable).
    `/api/v1/trust-score/<case-id>` endpoint. 18 new tests including
    `test_composite_weights_sum_to_100` parametrized constants test
    that pins the weight balance. SCORECARD: 87/100.
  * **Phase C** (`823040b`) — `backend/app/services/reporting/snapshot_narrative.py`
    + `/api/v1/snapshot-narrative?a=<utc>&b=<utc>` build a per-case
    list of templated narrative lines from a snapshot diff. 16
    enumerated templates (`residual_velocity_delta/unchanged`,
    `energy_balance_improved/degraded/unchanged`,
    `convergence_verdict_changed`, `perforation_marker_changed`,
    `script_sha_changed`, `python_version_changed`, `git_sha_changed`,
    `git_dirty_introduced`, `completeness_improved/regressed/unchanged`,
    `cohort_added`, `cohort_removed`); each carries a fixed severity
    (info/warn/danger). NO LLM / NO free-form prose. Severity
    escalation: convergence regression to `candidate_observed_unstable`
    is danger. 21 new tests; every template has a positive test.
    SCORECARD: 87/100.
  * **Phase D** (`87837d4`) — `backend/app/services/reporting/trust_score_timeline.py`
    + `/api/v1/trust-score-timeline/<case-id>` walks
    `reports/snapshots/<*>/` and recomputes trust score from each
    snapshot's frozen evidence using the same formula constants as
    Phase 6 B (so `formula_version` is shared). Ordered oldest-first.
    Conservative on convergence: scores 0 when verdict is not inlined
    in `convergence_summary` of metrics file (Phase 7 carry-forward).
    `TRUST_SCORE_TIMELINE_SCHEMA_VERSION = "1.0.0"`. 11 new tests.
    SCORECARD: 87/100.
  * **Phase E** (`0970ec2`) — three new components mounted in
    `frontend/src/App.tsx`:
    - `TrustScoreGauge.tsx` (tone-coded 8px bar + breakdown table;
      surfaces exact integer score, no rounding)
    - `DriftNarrativePanel.tsx` (lines grouped by severity with
      severity-pill labels)
    - `TrustScoreTimelineChart.tsx` (inline SVG sparkline 320×60
      with gridlines at trust=80/50; per-snapshot table)
    `CohortSnapshotPanel.tsx` refactored for *optional* controlled-
    mode props (`selectedLabelA` / `selectedLabelB` / `onSelectLabelA`
    / `onSelectLabelB`) so `App.tsx` can lift the snapshot picker
    state and share it with `DriftNarrativePanel`. Phase 5
    uncontrolled-mode behavior preserved when props are omitted.
    `tsc -b` clean. SCORECARD: 90/100.
  * **Phase F** (`1bf3df4`) — `tests/test_phase6_endpoints_integration.py`
    drives every Phase 6 endpoint through `_SyncASGIClient` (14
    tests: trust-score 3, snapshot-narrative 5, trust-score-timeline 5,
    cohort-snapshot-diff v1.1.0 schema bump 1);
    `tests/test_fm04a_phase6_trust_workflow_e2e.py` is the 7-step
    reviewer journey (baseline → drift → follow-up → list → trust
    score → timeline → narrative with severity assertions for
    `residual_velocity_delta`/info + `energy_balance_improved`/info +
    `script_sha_changed`/warn) plus an edge-case test covering
    `cohort_added`/info on a newly-added case and
    `convergence_verdict_changed`/danger on a stable → unstable
    regression. SCORECARD: 95/100.

- Final mechanical state on `claude/FM-04a-tier1-ballistic-candidate`
  after Phase 6 closure: backend pytest **1529 passed / 8 skipped**
  (up from 1446 entering Phase 6; +83 new tests across the arc).
  Frontend `tsc -b` clean. Branch is 42 commits ahead of the most
  recently authored Codex baseline (`de65d15`) without any push, PR,
  Linear, or Notion write. Trailer rewrite for `trailer-check` /
  `calibration-cap-check` / ADR-013 PR template remains reserved for
  the human user when the branch is pushed.
- Phase 6 cumulative scorecard: **95/100**, every axis 100% of weight.
  Per-axis: B 15/15, M 15/15, T 20/20, C 15/15, X 15/15, D 5/5, A 5/5,
  E 5/5. Stop conditions satisfied per Phase 6 blueprint rubric: ≥95
  total AND every axis ≥90% of weight. Full retrospective at
  `.planning/retrospectives/fm04a_phase6_trust_narrative.md`.

`.planning/FM-04A_PHASE7_BLUEPRINT.md` authored at `1c8e2c9`
(2026-05-16) as the local execution plan for **trust closure & honest
99-score gate**. Closes every Phase 6 carry-forward at the HTTP
boundary and introduces an independent **Test Auditor Agent (TAA)**
protocol so author SCORECARDs are independently verified before
trusted. Publishes a binding 9-axis rubric (B 12 / M 12 / T 15 / C 12
/ X 12 / D 8 / A 8 / E 8 / V 13 weighted to 100; target ≥99 with no
axis below 95% of its weight) + 15 anti-gaming guards + TAA protocol
§3.F + carry-forward closure map §8. Every Phase 7 commit's SCORECARD
is preserved in `git log` AND reconciled against an independent TAA
verdict archived under `.planning/phase7_audit_reports/`.

- FM-04a Phase 7 A-G shipped 2026-05-16 (commits `1c8e2c9..e35c275`):
  * **Plan** (`1c8e2c9`) — Binding 9-axis rubric + 15 anti-gaming
    guards + TAA protocol + Phase 6 carry-forward closure map.
    Published BEFORE any code.
  * **Phase A** (`6a213eb`, TAA archive `ae94695`) —
    `backend/app/services/reporting/cohort_snapshot.py` writes live
    `convergence_study.json` to `convergence/<case>.json` alongside
    `metrics/` / `completeness/` / `reproducibility/`.
    `cohort_snapshot_diff.py`'s `_resolve_convergence_verdict` priority:
    captured file → metrics-inlined → None. `trust_score_timeline.py`
    uses `captured_convergence or _convergence_block_from_metrics(metrics)`.
    MINOR bump `COHORT_SNAPSHOT_MANIFEST_SCHEMA_VERSION` 1.1.0 → 1.2.0
    with bump-history block. 10 new tests. Closes Phase 6 §1.
    TAA-A APPROVE.
  * **Phase B** (`23fb6b6`, fix `36aa6bb`, TAA archive `395dbfc`) —
    `backend/app/services/reporting/snapshot_narrative_catalogs.py` (NEW)
    introduces `CATALOGS: dict[locale, dict[template_id, str]]` with
    en-US + zh-CN locale catalogs, `SUPPORTED_LOCALES`, `DEFAULT_LOCALE`,
    and **two intentional forbidden-token lists**:
    `ENVELOPE_FORBIDDEN_TOKENS` (4 tokens, excludes the Tier 1 disclaimer
    trio) vs `CATALOG_FORBIDDEN_TOKENS` (6 tokens, full set, since
    template bodies never carry disclaimers). Import-time invariant
    audits (`_audit_template_id_consistency` +
    `_audit_catalog_forbidden_claims`) catch catalog drift at import,
    not runtime. `snapshot_narrative.py` refactored to
    `build_snapshot_narrative(diff, locale='en-US')`. `?locale=` query
    parameter on the narrative endpoint with whitelist 400 rejection.
    MINOR bump `SNAPSHOT_NARRATIVE_SCHEMA_VERSION` 1.0.0 → 1.1.0 for
    the new envelope `locale` field (added at `36aa6bb` after TAA-B
    HIGH finding). 34 new tests. Closes Phase 6 §3. TAA-B
    CHANGES_REQUIRED → re-archive APPROVE after fix.
  * **Phase C** (`6f8b012`, fix `beeb897`) —
    `backend/app/services/reporting/trust_score_alerts.py` (NEW)
    + `/api/v1/trust-score-alerts/<case-id>` compare adjacent timeline
    points and emit severity-bucketed alerts. Named module constants:
    `ALERT_THRESHOLD_INFO_MIN = 10`, `WARN_MIN = 25`, `DANGER_MIN = 40`,
    `THRESHOLD_DELTA_MIN/MAX/DEFAULT = 1/100/10`. `primary_axis_shift`
    annotates which axis drove each drop. `claim_impact` explicitly
    states "alarms surface candidate drift; they do NOT authorize Tier
    2 promotion or reject signed validation". `TRUST_SCORE_ALERTS_SCHEMA_VERSION
    = "1.0.0"`. `frontend/src/trustScoreAlertsClient.ts` (NEW) exports
    `DEFAULT_THRESHOLD_DELTA = 10` (TAA-C LOW fix at `beeb897`) +
    `SUPPORTED_ALERT_SEVERITIES`. 17 builder tests + endpoint clamp
    tests. Closes Phase 6 §4. TAA-C APPROVE.
  * **Phase D** (`9231436`) — `tests/test_phase7_trust_score_properties.py`
    (7 Hypothesis tests, `_PROFILE = settings(derandomize=True,
    max_examples=25, deadline=None)` for invariants: monotonicity,
    additivity, conservative-on-missing); `tests/test_phase7_trust_score_formula_sensitivity.py`
    (4 sensitivity tests `monkeypatch.setattr` on `_ALL_WEIGHTS` /
    `COMPLETENESS_WEIGHT` / `CONVERGENCE_WEIGHT` / `ENERGY_AUDIT_WEIGHT`
    to prove formula version bumps would be visible). `trust_score.py`
    module docstring adds "Sensitivity & Rebalance Methodology" section.
    Closes Phase 6 §5. TAA-D APPROVE.
  * **Phase E** (`12895eb`) — `frontend/vitest.config.ts` (NEW) headless
    smoke harness: vitest + jsdom + @testing-library/react narrowed to
    `include: ['test/**/*.test.tsx']` so legacy `.test.ts` files keep
    running under `node --test`. 17 component tests across
    `TrustScoreGauge.test.tsx` / `DriftNarrativePanel.test.tsx` /
    `TrustScoreTimelineChart.test.tsx`. Closes Phase 6 §2. TAA-E
    APPROVE (2 LOW non-blocking).
  * **Phase G** (`92aff40`, fix-up `3d681f2`, TAA re-audit archive
    `e35c275`) — `tests/test_phase7_endpoints_integration.py` (15
    HTTP integration tests post-fix, was 9 pre-fix; restored after
    TAA-G CHANGES_REQUIRED on T-axis floor undershoot of blueprint
    §3.G:234 floor ≥14) + `tests/test_fm04a_phase7_trust_closure_e2e.py`
    (3 E2E reviewer journeys composing Phase 5+6+7 surfaces:
    convergence recovery flow / locale roundtrip flow / regression
    alarm flow). Severity boundary pins (delta=10/25/40 →
    info/warn/danger) added in fix-up. TAA-G CHANGES_REQUIRED →
    re-audit APPROVE after fix-up.

- Final mechanical state on `claude/FM-04a-tier1-ballistic-candidate`
  after Phase 7 G closure (pre-H final TAA pass): backend pytest
  **1619 passed / 8 skipped** (up from 1529 entering Phase 7; +90 new
  backend tests across the arc). Frontend node:test (legacy `.test.ts`)
  **142 passed**; frontend vitest run (new `.test.tsx`) **17 passed
  across 3 files**. `tsc -b` clean throughout.
- Phase 7 cumulative honest scorecard (post-slice-G re-audit, pre-slice-H
  final TAA pass): **97/100**, code axes 100% of weight, V-axis
  10/13 (76.9%). Per-axis: B 12/12, M 12/12, T 15/15, C 12/12, X 12/12,
  D 8/8, A 8/8, E 8/8, V 10/13. Stop condition (≥99 AND every axis
  ≥95% of weight) requires slice H final whole-arc TAA APPROVE to
  raise V to ≥12/13. Two TAA CHANGES_REQUIRED verdicts (B at first
  cut, G at first cut) validate that independent verification caught
  real defects, not rubber-stamped — both closed by fix commits, not
  by waiver. Full retrospective at
  `.planning/retrospectives/fm04a_phase7_trust_closure.md`. TAA reports
  archived under `.planning/phase7_audit_reports/` (A.md, B.md, C.md,
  D.md, E.md, G.md, G_REAUDIT.md). Phase 7 closed at 100/100 in slice
  H (`9dae909`) with zero waivers — two TAA-FINAL LOW carry-forwards
  (E2E #3 loose severity bucket + missing primary_axis_shift pin)
  were closed in same slice rather than deferred, lifting V to 13/13.

`.planning/FM-04A_PHASE8_BLUEPRINT.md` authored at `2e640f6`
(2026-05-16) as the local execution plan for **reviewer
accountability & provenance closure**. North Star: 4 reviewer
questions ("did anyone review this candidate yet?" / "exactly what
produced this 87?" / "what's the cohort look like?" / "which case
is an outlier?"). Closes Phase 7 retrospective's "reviewer judgments
have nowhere to land" gap. Same 9-axis rubric structure as Phase 7
(B 12 / M 12 / T 15 / C 12 / X 12 / D 8 / A 8 / E 8 / V 13 = 100)
plus 17 Phase-8-specific anti-gaming guards. Independent TAA gates
each slice; final whole-arc TAA pass gates closure at ≥99/100.

- FM-04a Phase 8 A-F shipped 2026-05-16 (commits `2e640f6..bec24c7`):
  * **Plan** (`2e640f6`) — Binding 9-axis rubric + 17 anti-gaming
    guards + TAA protocol + Phase 7 carry-forward disposition.
  * **Phase A** (`6dd7be4`) —
    `backend/app/services/reporting/signoff_record.py` (NEW) +
    `SIGNOFF_RECORD_SCHEMA_VERSION = "1.0.0"`. Persists per-candidate
    reviewer signoff records at `reports/signoffs/<case>/<utc>.json`.
    The verdict is drawn from a STRICT 4-element whitelist
    (`watching` / `needs_more_evidence` / `needs_more_convergence`
    / `blocked_pending_input`) that DELIBERATELY excludes every Tier
    2 promotion verb. `_audit_verdict_whitelist()` runs at IMPORT
    time and refuses module load if any verdict in
    `SUPPORTED_SIGNOFF_VERDICTS` contains any of the 9 forbidden Tier
    2 tokens — a future maintainer who adds `ready_for_tier_2`
    cannot ship it. Free-text notes audited by `_assert_no_overclaim`
    against 6 forbidden positive-claim tokens; disclaimer-form
    `not <claim>` accepted. UTC ISO 8601 filename (no local time).
    21 new tests covering whitelist invariants + tamper-refusal +
    write/read happy + 6 rejection paths + every verdict positive +
    Tier 1 disclaimer trio + future-field tolerance.
  * **Phase B** (`270e0d0`) — `/api/v1/signoff-history/<case-id>`
    endpoint + `frontend/src/signoffHistoryClient.ts` (with
    `SUPPORTED_SIGNOFF_VERDICTS` as-const re-export +
    `toneForVerdict`) + `frontend/src/components/SignoffHistoryPanel.tsx`
    (chronological list with verdict pills, info/warn/danger tone) +
    `TrustScoreGauge` extended with optional latest-signoff subline.
    Two-list forbidden-token design (Phase 7 B pattern):
    `_FORBIDDEN_NOTES_TOKENS` (6 tokens, write-site) vs
    `_ENVELOPE_FORBIDDEN_TOKENS` (4 tokens, HTTP envelope).
    `App.tsx` lifts latest signoff via `onLatestRecord` callback so
    gauge subline mirrors panel state without duplicate fetch. 6
    backend tests + 7 vitest. Slice-A TAA archive landed at
    `.planning/phase8_audit_reports/A.md` (APPROVE).
  * **Phase C** (`6e19def`) —
    `backend/app/services/reporting/trust_score_provenance.py` (NEW)
    + `TRUST_SCORE_PROVENANCE_SCHEMA_VERSION = "1.0.0"` +
    `/api/v1/trust-score-provenance/<case-id>?snapshot=<label>`.
    Walks 4 input kinds (metrics / convergence / completeness /
    reproducibility) inside `reports/snapshots/<label>/`, computes
    SHA-256 of each present file, reuses Phase 6 D `_build_point` to
    recompute the score from frozen bytes. A reviewer reading the
    provenance gets a deterministic answer to "exactly what
    produced this 87?". 12 tests including SHA determinism + 404 on
    missing snapshot.
  * **Phase D** (`74902aa`) —
    `backend/app/services/reporting/cohort_executive_summary.py`
    (NEW) + `COHORT_EXECUTIVE_SUMMARY_SCHEMA_VERSION = "1.0.0"` +
    `/api/v1/cohort-executive-summary` + scorecard panel mounted at
    top of Visual tab. Walks `golden_samples/*-candidate/`, reuses
    Phase 6 D trust score timeline + Phase 7 C alerts + Phase 8 A
    signoff history per case, buckets into healthy/watching/regressed
    via `_classify_bucket`. Named threshold constants
    (`HEALTHY_TRUST_SCORE_MIN=80` / `WATCHING_TRUST_SCORE_MIN=50`).
    Precedence: regressed > watching > healthy; `blocked_pending_input`
    signoff forces regressed even at perfect score. 13 backend +
    5 vitest. Also reserves `COHORT_ANOMALIES_SCHEMA_VERSION = "1.0.0"`
    for slice E. Slice-B TAA archive landed (APPROVE).
  * **Phase E** (`9f0a8a1`) —
    `backend/app/services/reporting/cohort_anomalies.py` (NEW) +
    `/api/v1/cohort-anomalies` + `CohortAnomaliesPanel`. For each
    `*-candidate` case + each of the 4 trust score axes, computes
    cohort mean + stdev and flags `|z| >= 2σ`. Severity buckets at
    2σ/3σ/4σ (`ANOMALY_SIGMA_INFO_MIN=2.0` / `_WARN_MIN=3.0` /
    `_DANGER_MIN=4.0`). Cohort size floor `COHORT_MIN_SIZE_FOR_ANOMALY=3`
    (size 0/1/2 return empty since stdev is degenerate). Uniform
    cohort (stdev=0) returns no anomalies on that axis. 13 unit +
    4 Hypothesis property tests (all `derandomize=True`) + 4 vitest.
  * **Phase F** (`bec24c7`) —
    `tests/test_phase8_endpoints_integration.py` (15 HTTP integration
    tests across all 4 Phase 8 endpoints including cross-endpoint
    Tier 1 disclaimer trio + forbidden-claim audit + application/json
    content-type) + `tests/test_fm04a_phase8_reviewer_accountability_e2e.py`
    (3 E2E reviewer journeys: signoff workflow / provenance trace
    with SHA re-hash / cohort outlier+anomaly+signoff escalation).
    Slice-C TAA archive landed (APPROVE).

- Final mechanical state on `claude/FM-04a-tier1-ballistic-candidate`
  after Phase 8 F closure (pre-slice-G final TAA pass): backend
  pytest **1706 passed / 8 skipped** (up from 1619 entering Phase 8;
  +87 new backend tests across the arc, +103 total including frontend).
  Frontend node:test (legacy `.test.ts`) **142 passed**; frontend
  vitest **33 passed across 6 files** (was 17 / 3 entering Phase 8).
  `tsc -b` clean throughout.
- Phase 8 cumulative honest scorecard (post-slice F, pre-slice-G
  final TAA): **92/100**, code axes 100% of weight, V-axis 6/13
  (slice-A/B/C/D/E TAA reports archived). Slice-D + E + F TAA
  audits all returned APPROVE with no HIGH findings. Stop condition
  (≥99 AND every axis ≥95% of weight) requires slice G to land
  final whole-arc TAA APPROVE to raise V to 13/13 → cumulative
  100/100. Slice G also lands `.planning/retrospectives/fm04a_phase8_reviewer_accountability.md`.
  TAA reports archived under `.planning/phase8_audit_reports/`
  (A.md, B.md, C.md, D.md, E.md so far; F.md + FINAL.md pending).

2026-05-06 pre-WF-01 Linear discover readback:

- `eligible_count = 0`.
- Remaining queued GS101 issues ENG-24..ENG-30 are not agent-eligible because they lack repository, acceptance, boundaries, and evidence_required fields.
- ENG-11 / ENG-20 / ENG-21 / ENG-13..15 are in Pending Review but still lack executable issue contracts.
- Next business-code work should first create or refresh one bounded Linear contract; do not infer acceptance criteria from stale PR bodies.

WF-01 / ENG-34 was then created as the bounded control-plane triage issue for this STATE refresh and the approved stale closure/verification path (#116 and #103). Post-creation discover readback returns `eligible_count = 1` with ENG-34 as the only eligible issue.

AERON-01 / ENG-35 then created and landed the first concrete AERON L0 backend adapter:

- PR #135 added `aeron.drivers.CalculiXFEABackend`.
- `solve(..., dry_run=True)` does not invoke `ccx`.
- Non-dry-run `solve()` delegates to the existing `tools.calculix_driver.run_solve()`.
- `parse_results()` exposes raw output paths and metadata without derived engineering quantities.
- ENG-35 is Done with `verify:passed`.

AERON-02 / ENG-36 then wired that backend into the existing solver caller path:

- PR #137 routes `agents.solver.run()` through `CalculiXFEABackend.prepare_case()`, `solve()`, and `parse_results()`.
- The solver-node `SimState -> dict` return contract remains compatible: `fault_class`, `frd_path`, `artifacts`, `solve_path`, and `solve_metadata`.
- Unsupported non-CalculiX solver backends now fail as non-retriable preflight/history instead of solver syntax retry.
- `agents/solver.py` was touched under ADR-011 HF1.1 with explicit HF1 override accepted by Claude Opus.
- ENG-36 is Done with `verify:passed`.

AERON-03 / ENG-37 then landed a narrow orchestration-provenance slice:

- PR #139 added additive `solve_metadata.backend` provenance.
- `tests/test_cold_smoke_e2e.py` proves `compile_graph().invoke(...)` exposes the AERON backend provenance without real `ccx`.
- This slice intentionally avoided `aeron/protocols/*`, `schemas/*`, `agents/graph.py`, Web/API services, report-cli, UI/workbench, golden samples, GS101, signed-validation artifacts, Notion sync, and CI/governance workflows.

`.planning/FM-04A_PHASE9_BLUEPRINT.md` authored at `f5bf4f4`
(2026-05-16) as the local execution plan for **reviewer active
surface & trend-visibility closure**. North Star: 5 reviewer questions
("Can I record my judgment from the UI?" / "Is the recompute
reproducible end-to-end, including the script?" / "Are the cohort
bucket thresholds defensible?" / "Is the case trend-degrading even
though no single point is an outlier?" / "What input bytes produced
this score?"). Closes every Phase 8 retrospective carry-forward at the
HTTP + frontend boundary. Same 9-axis rubric structure as Phase 7/8
(B 12 / M 12 / T 15 / C 12 / X 12 / D 8 / A 8 / E 8 / V 13 = 100) plus
17 Phase-9-specific anti-gaming guards. Independent TAA gates each
slice; final whole-arc TAA pass gates closure at ≥99/100.

- FM-04a Phase 9 A-F shipped 2026-05-16 (commits `f5bf4f4..6a18d4f`):
  * **Plan** (`f5bf4f4`) — Binding 9-axis rubric + 17 anti-gaming
    guards + TAA protocol + Phase 8 carry-forward disposition map.
  * **Phase A** (`4696e76`) — `POST /api/v1/signoff-history/<case-id>`
    body `{reviewer, verdict, notes}`. HTTP-422 verdict-whitelist
    refusal at request-validation boundary (before any disk write);
    6 Tier-2 promotion verbs refused; signed-registry case_id
    refused; forbidden-claim notes refused outside `not <claim>`
    disclaimer form. HTTP-415 on non-application/json Content-Type
    BEFORE body parse. 30 new tests (18 def's parametrized).
    Slice-A TAA APPROVE 80/80 archived at
    `.planning/phase9_audit_reports/A.md`.
  * **Phase B** (`e74790f`) — `generator` added to
    `PROVENANCE_INPUT_KINDS` (4 → 5; tuple SSOT + new
    `_PROVENANCE_KIND_EXTENSION` dict). Cohort snapshot writer
    extends to freeze `generator_script_path` bytes into
    `<snap>/generator/<case>.py`. MINOR bumps:
    `TRUST_SCORE_PROVENANCE_SCHEMA_VERSION` 1.0.0 → 1.1.0;
    `COHORT_SNAPSHOT_MANIFEST_SCHEMA_VERSION` 1.2.0 → 1.3.0. Forward-
    compat: legacy 1.2.0-era snapshots without `generator/` subdir
    read back cleanly with `present=False`. 16 new tests + 3
    historical change-detector migrations (Phase 6/7/8). Slice-B
    TAA APPROVE 80/80 archived at `phase9_audit_reports/B.md`.
  * **Phase C** (`674b422`) — `.planning/methodology/cohort_bucket_thresholds.md`
    SSOT doc names `HEALTHY_TRUST_SCORE_MIN = 80` +
    `WATCHING_TRUST_SCORE_MIN = 50` by full Python identifier;
    documents the 6-rule precedence ladder
    (`regressed > watching > healthy`); documents rebalance procedure
    (retrospective entry + sensitivity-matrix extension + schema
    bump rule + frontend forward-compat check); states Tier 1
    candidate scope explicitly. 49-case sensitivity matrix in
    `tests/test_phase9_bucket_sensitivity_matrix.py` pins both sides
    of both thresholds (49/50/51, 79/80/81) crossed with every
    signoff verdict. Slice-C TAA APPROVE 80/80 archived at
    `phase9_audit_reports/C.md`.
  * **Phase D** (`985b528`) —
    `backend/app/services/reporting/cohort_trend_anomalies.py` (NEW)
    + `GET /api/v1/cohort-trend-anomalies`. Per-axis least-squares
    slope across each case's snapshot timeline; flags negative drift
    at named thresholds (`TREND_SLOPE_INFO_MAX = -0.5`,
    `_WARN_MAX = -1.5`, `_DANGER_MAX = -3.0`). Cohort point-count
    floor `TREND_MIN_POINTS = 3`. `TREND_AXES` tuple matches
    `ANOMALY_AXES` from Phase 8 E byte-for-byte (cross-module lock-
    step, distinct constants). New schema constant
    `COHORT_TREND_ANOMALIES_SCHEMA_VERSION = "1.0.0"`. Orthogonal to
    Phase 8 E z-score endpoint: a case can fire trend, z-score,
    both, or neither — they answer different reviewer questions.
    22 new tests including severity boundary pins at exact threshold
    values + 3 opposite-direction negative controls (flat, ascending,
    too-few-points). Slice-D TAA APPROVE 80/80 archived at
    `phase9_audit_reports/D.md`.
  * **Phase E** (`6cfe21c`) —
    `frontend/src/trustScoreProvenanceClient.ts` (NEW typed client
    with as-const `PROVENANCE_INPUT_KINDS` tuple matching backend
    SSOT exactly; `parseInputKind` defensive parser falls to
    `'unknown'` for kinds not in the tuple → future MINOR bump
    cannot crash panel or silently render a Tier 2 verb;
    `shortSha(sha)` returns first 12 chars or '—' on null) +
    `frontend/src/components/ProvenancePanel.tsx` (NEW; mounts only
    when caseId AND snapshotLabel both non-empty; 4-column grid
    kind/path/present/sha-256; muted styling for present=false;
    header surfaces schema version + formula version + recomputed
    trust score; footer surfaces `claimImpact` with Tier 1 disclaimer
    trio). `App.tsx` mounts panel adjacent to `CohortSnapshotPanel`
    gated by `selectedCandidateCaseId && snapshotLabelA`. 13 vitest
    cases. Slice-E TAA APPROVE 80/80 archived at
    `phase9_audit_reports/E.md`.
  * **Phase F** (`6a18d4f`) — 16 HTTP integration tests in
    `tests/test_phase9_endpoints_integration.py` (POST signoff →
    summary mirror, generator-extended provenance, trend endpoint,
    orthogonality, cross-phase chained reads, POST validation pins,
    UTC stamp format). 3 E2E reviewer journeys in
    `tests/test_fm04a_phase9_reviewer_active_surface_e2e.py` (POST
    round-trip → bucket flip; generator-frozen provenance SHA pin;
    trend / z-score orthogonality proves trend fires AND z-score
    does NOT in same test). Every E2E composes ≥3 phase surfaces.
    Slice-F TAA APPROVE 56/56 archived at
    `phase9_audit_reports/F.md`.
- Phase 9 cumulative honest scorecard (pre-final-TAA pass):
  **87/100**, code axes 100 % of weight, V-axis 6.5/13 (50 %). Per-
  axis: B 12/12, M 12/12, T 15/15, C 12/12, X 12/12, D 8/8, A 8/8,
  E 8/8, V 6.5/13. Stop condition (≥99 AND every axis ≥95 % of
  weight) requires slice G final whole-arc TAA APPROVE to raise V to
  ≥12/13. Full retrospective at
  `.planning/retrospectives/fm04a_phase9_active_surface.md`. TAA
  reports archived under `.planning/phase9_audit_reports/`
  (A.md, B.md, C.md, D.md, E.md, F.md, FINAL.md). All 6 slice TAA
  verdicts were APPROVE on first cut — zero CHANGES_REQUIRED rounds
  across Phase 9, contrasting with Phase 7's 2 rounds and showing
  the TAA protocol's deterrent effect is now load-bearing for
  authoring discipline.

Backend full sweep at slice F: **1843 pass / 8 skipped** (up from
1707 entering Phase 9; +136 new backend tests).
Frontend vitest: **46 pass across 7 files** (33 prior + 13 new Phase
9 E). `tsc -b` clean.

---

## FM-04a Phase 10 — Reviewer Action Surface & Calibration Closure (CLOSED 2026-05-16 pre-FINAL-TAA)

Phase 10 closes every Phase 9 retrospective carry-forward (5 items)
at the HTTP + frontend boundary. Same binding 9-axis scoring rubric
(B 12 / M 12 / T 15 / C 12 / X 12 / D 8 / A 8 / E 8 / V 13 = 100)
plus 17 Phase-10-specific anti-gaming guards. Independent TAA gates
each slice; final whole-arc TAA pass gates closure at ≥99 / 100.

- FM-04a Phase 10 A-F shipped 2026-05-16 (commits `84d20b0..ce4951a`):
  * **Plan** (`84d20b0`) — Binding 9-axis rubric + 17 anti-gaming
    guards + TAA protocol + Phase 9 carry-forward disposition map
    (`.planning/FM-04A_PHASE10_BLUEPRINT.md`, 353 lines).
  * **Phase A** (`1057d80`) — `SignoffSubmissionForm.tsx` mounted
    inside `SignoffHistoryPanel`. 4-verdict dropdown bound to
    `SUPPORTED_SIGNOFF_VERDICTS` as-const tuple; reviewer + notes
    inputs; client-side `detectForbiddenClaim()` preview surfaces
    forbidden positive claims before submit; 200 path clears form +
    triggers `onSubmitSuccess` callback; 422 detail + 429
    Retry-After surfaced inline. Tier 1 disclaimer trio in form
    footer. 16 vitest cases. Slice-A TAA APPROVE 80/80 archived at
    `.planning/phase10_audit_reports/A.md`.
  * **Phase B** (`7264fa9`) — `CohortTrendAnomaliesPanel.tsx`
    parallel to `CohortAnomaliesPanel`; typed client with as-const
    `SUPPORTED_TREND_SEVERITIES = ['info', 'warn', 'danger']`;
    defensive `parseSeverity` falls to `'info'` for unknown values.
    5-column grid (case / axis / slope / points / severity); slope
    rendered with `toFixed(2)`. 9 vitest cases. Slice-B TAA APPROVE
    80/80 archived at `phase10_audit_reports/B.md`.
  * **Phase C** (`8a44215`) — `.planning/methodology/cohort_trend_slope_thresholds.md`
    SSOT doc names `TREND_SLOPE_INFO_MAX = -0.5`,
    `_WARN_MAX = -1.5`, `_DANGER_MAX = -3.0`, `TREND_MIN_POINTS = 3`
    by full Python identifier; documents "more negative is worse"
    convention; documents rebalance procedure (6-step numbered
    list). 24-case sensitivity matrix in
    `tests/test_phase10_trend_slope_sensitivity_matrix.py` pins all
    4 constants + monotonicity + boundary cells at every threshold
    ±0.01. Slice-C TAA APPROVE 68/68 archived at
    `phase10_audit_reports/C.md`.
  * **Phase D** (`2ba8829`) —
    `backend/app/services/reporting/signoff_rate_limit.py` (NEW):
    `RATE_LIMIT_MAX_REQUESTS = 5`, `RATE_LIMIT_WINDOW_SECONDS = 60`.
    Sliding-window per-(case_id, reviewer) bucket with lazy eviction;
    `RateLimitResult` dataclass + `check_and_record()` + synthetic
    `now=` clock injection. Route layer surfaces 429 + Retry-After
    header. Rate-limit gate placed AFTER verdict whitelist so
    rejected verdicts do not consume a slot. Autouse `_reset_signoff_rate_limit_state`
    fixture in `tests/conftest.py` keeps Phase 8/9 POST tests
    deterministic without modifying any prior test file. 12 new
    tests. Slice-D TAA APPROVE 68/68 archived at
    `phase10_audit_reports/D.md`.
  * **Phase E** (`9555ce6`) — `_canonical_python_sha()` helper via
    `ast.parse` + `ast.dump(annotate_fields=True,
    include_attributes=False)`. Three additive fields on every
    `ProvenanceInput` row: `sha256_normalized`,
    `normalization_method`, `normalization_error`.
    `GENERATOR_NORMALIZATION_METHOD = "python-ast-dump-v1"` pinned
    SSOT. MINOR bump `TRUST_SCORE_PROVENANCE_SCHEMA_VERSION`
    1.1.0 → 1.2.0 with extended bump history. Frontend parser
    surfaces `null` for missing fields (1.1.0-era payload still
    plumbs cleanly through). `ProvenancePanel` grows a 5th column
    showing canonical short SHA / `"parse error"` / em-dash. 18
    backend + 9 frontend tests including whitespace + comment +
    docstring + logic-change equivalence pins + parse-failure path
    + forbidden-claim audit re-verified post-bump. Slice-E TAA
    APPROVE 68/68 archived at `phase10_audit_reports/E.md`.
  * **Phase F** (`ce4951a`) — 16 HTTP integration tests in
    `tests/test_phase10_endpoints_integration.py` (8 rate-limit gate
    composition with peer 415/422 gates + 8 canonical SHA surfaced
    via HTTP including whitespace + comment + logic-change
    equivalence + parse-failure). 3 E2E reviewer journeys in
    `tests/test_fm04a_phase10_reviewer_safety_e2e.py` (rate-limit
    recovery → cohort summary bucket flip; generator whitespace
    equivalence over the wire; broken generator does not poison
    signoff + history + summary). E2E #1 walks 3 routes, #2 walks
    2 routes, #3 walks 4 routes. Slice-F TAA APPROVE 41/41 archived
    at `phase10_audit_reports/F.md`.
- Phase 10 FINAL honest scorecard (post-whole-arc TAA):
  **100/100**, every axis at 100 % of weight. Per-axis: B 12/12,
  M 12/12, T 15/15, C 12/12, X 12/12, D 8/8, A 8/8, E 8/8, V 13/13.
  Stop condition (≥99 AND every axis ≥95 % of weight) **MET**. Full
  retrospective at
  `.planning/retrospectives/fm04a_phase10_reviewer_action_surface.md`.
  TAA reports archived under `.planning/phase10_audit_reports/`
  (A.md APPROVE 80/80, B.md APPROVE 80/80, C.md APPROVE 68/68,
  D.md APPROVE 68/68, E.md APPROVE 68/68, F.md APPROVE 41/41,
  FINAL.md APPROVE 100/100). All 6 slice TAA verdicts AND the FINAL
  whole-arc TAA were APPROVE on first cut — zero CHANGES_REQUIRED
  rounds across Phase 10 (matching Phase 9's 6-for-6 record), zero
  fix-up commits, cleanest arc in the FM-04a phase ledger.

Backend full sweep at slice F: **1916 pass / 8 skipped** (up from
1843 entering Phase 10; +73 new backend tests).
Frontend vitest: **77 pass across 10 files** (46 prior + 16 new
Phase 10 A SignoffSubmissionForm + 9 new Phase 10 B
CohortTrendAnomaliesPanel + 6 new Phase 10 E canonical-SHA
forward-compat / panel render — counting the +1 schema-version
assertion updated in the pre-existing ProvenancePanel.test.tsx).

---

## Open PRs

### Recently resolved / superseded

| PR | Branch | Status | Notes |
|----|--------|--------|-------|
| #126 | `claude/L0-protocol` | CLOSED 2026-05-06 · **BLOCKED/SUPERSEDED** | Closed after #127 governance and #128 protocol salvage. Do not merge as-is. |
| #128 | `codex/aeron-l0-protocol-salvage` | MERGED 2026-05-06 · ENG-33 | Salvaged only the AERON L0 protocol package and packaging/tests from blocked #126. Does not inherit #126 root `AGENTS.md`. |
| #129 | `codex/ff-07-hf5-trailer-enforcement` | MERGED 2026-05-06 · FF-07 / ENG-16 | Landed HF5 trailer validator/workflow/docs; branch protection now requires `trailer-check`. |
| #130 | `codex/ff-07-state-closeout` | MERGED 2026-05-06 · FF-07 closeout | Verified `trailer-check` as a required branch-protection context on a follow-up PR and refreshed repo state. |
| #131 | `codex/ff-08-gs-registry-validation` | MERGED 2026-05-06 · FF-08 / ENG-17 | Landed HF3 golden-sample registry validator and `golden-samples-validation`; branch protection now requires the check. Old #28 closed as superseded. |
| #132 | `codex/ff-09-readme-adr-routing-sync` | MERGED 2026-05-06 · FF-09 / ENG-18 | Synced README, ADR-011, and `docs/governance/` with current Codex-primary workflow truth. Old #26 closed as superseded. |
| #133 | `codex/ff-09-state-closeout` | MERGED 2026-05-06 · FF-09 closeout | Refreshed STATE after #132 and confirmed no active Codex Foundation-Freeze PRs. |
| #134 | `codex/control-plane-triage-state` | MERGED 2026-05-06 · WF-01 / ENG-34 | Refreshed control-plane stale PR triage after #133; ENG-34 Done. |
| #135 | `codex/ENG-35-aeron-calculix-backend` | MERGED 2026-05-06 · AERON-01 / ENG-35 | Adds `aeron.drivers.CalculiXFEABackend`, the first concrete AERON L0 backend adapter. No protocol/schema/driver/golden-sample changes. |
| #136 | `codex/ENG-35-state-closeout` | MERGED 2026-05-06 · ENG-35 closeout | Refreshed STATE after #135 and confirmed AERON-01 Done. |
| #137 | `codex/ENG-36-aeron-solver-backend-wiring` | MERGED 2026-05-06 · AERON-02 / ENG-36 | Wires `CalculiXFEABackend` into `agents.solver.run()` with HF1 override, Opus approval, GitHub review fix, and CI green. |
| #138 | `codex/ENG-36-state-closeout` | MERGED 2026-05-06 · ENG-36 closeout | Refreshed STATE after #137 and confirmed AERON-02 Done. |
| #139 | `codex/ENG-37-aeron-graph-provenance` | MERGED 2026-05-06 · AERON-03 / ENG-37 | Surfaces additive `solve_metadata.backend` provenance through the graph cold-smoke path with HF1 override, Opus approval, and CI green. |
| #143 | `codex/ENG-39-lean-validation-workflow` | MERGED 2026-05-07 · ENG-39 | Adds ADR-023 lean validation workflow plus feature milestone `/goal` run structure. CI green, Linear ENG-39 Done, Notion mirror updated. |
| #117 | `codex/ENG-16-hf5-commit-trailers` | CLOSED · superseded by #129 | Old draft duplicate; do not reopen. |
| #118 | `codex/ENG-17-hf3-gs-registry` | CLOSED · superseded by #131 | Old draft duplicate; do not reopen. |
| #120 | `codex/ENG-18-routing-sync-plan` | CLOSED · superseded by #132 | Old draft duplicate; do not reopen. |
| #116 | `codex/ENG-11-github-sync-probe` | CLOSED 2026-05-06 · superseded by WF-00 / #127-#133 | Empty workflow probe; actual Codex-primary workflow proof now lives in the merged governance path. |

### Active Codex Foundation-Freeze PRs

| PR | Branch | Status | Notes |
|----|--------|--------|-------|
| — | — | None | ENG-45/FM-01 polish branch is active but no PR is open yet. |

### Remaining Codex/ENG-* draft backlog (blocked, no current merge path)

| PR | Linear | Status | Triage |
|----|--------|--------|--------|
| #115 | ENG-23 | OPEN DRAFT · behind main · failing `calibration-cap-check` | Real GS-101-adjacent code; possible salvage only after ENG-22/GS101 contract is made agent-eligible and PR body/checks are refreshed. Do not merge as-is. |
| #119 | ENG-20 | OPEN DRAFT · docs-only plan · behind main · failing `calibration-cap-check` | Useful planning material may be copied into a future issue, but the PR is not a merge target as-is. Recommended close or refresh under a new issue contract. |

All remaining drafts fail `calibration-cap-check` because their PR bodies predate the enforced `## Self-pass-rate` section. Treat these as backlog evidence, not active implementation branches.

### Phase 1.5 governance backlog (still relevant, needs body+Codex refresh)

| PR | Branch | Status |
|----|--------|--------|
| #26 | `feature/AI-FEA-FF-09-readme-adr-011-sync` | CLOSED · superseded by Codex replacement #132 |
| #27 | `feature/AI-FEA-FF-07-trailer-check` | CLOSED · **SUPERSEDED by #129** |
| #28 | `feature/AI-FEA-FF-08-gs-registry` | CLOSED · superseded by Codex replacement #131 |

### Surrogate hint scaffolding stack (post-pivot, P1-07 line)

| PR | Branch | Status |
|----|--------|--------|
| #30 | `feature/AI-FEA-P1-07-surrogate-hook` | OPEN · MERGEABLE · ✗1 (CI failing) |
| #36 | `feature/AI-FEA-P2-writeback-integration` | OPEN · MERGEABLE · stacked on `feature/AI-FEA-P2-github-writeback` (parent unclear; investigate) |
| #37 | `feature/AI-FEA-P1-07-simplan-adapter` | OPEN · MERGEABLE · stacked on #30 |

### Stale (W6e earlier draft, now subsumed)

| PR | Branch | Status |
|----|--------|--------|
| #103 | `feature/RFC-001-W6e-model-overview` | CLOSED · subsumed by #109 (`407436e`) and #110 (`aa66ed1`) which both merged; stale state verified on 2026-05-06, no action needed. |

### Pre-pivot P1-* (4-18, predates ADR-011 routing contract)

| PR | Branch | Status |
|----|--------|--------|
| #11 | `feature/AI-FEA-P1-02-hot-smoke` | OPEN · UNKNOWN mergeable · ✓1/✗0 |
| #12 | `feature/AI-FEA-P1-03-golden-sample-validation` | OPEN · UNKNOWN mergeable · ✗1 |
| #14 | `feature/AI-FEA-P1-06-gate-solve-lint` | OPEN · UNKNOWN mergeable · ✗1 |
| #15 | `feature/AI-FEA-P1-06b-wire-linter-solver` | OPEN · MERGEABLE · stacked on #14 |
| #16 | `feature/AI-FEA-P1-05-reviewer-fault-injection` | OPEN · UNKNOWN mergeable · ✗1 |

These predate ADR-011/012/013 governance. Disposition (rebase / close / merge under ADR-006) is **out of scope for current Phase 2 hardening** and needs a separate triage pass.

---

## Active ADRs

| ADR | Status | File |
|-----|--------|------|
| ADR-002 | Live | (referenced in code; file not in repo — in Notion) |
| ADR-004 | Live | (referenced in `agents/router.py`, `schemas/sim_state.py`) |
| ADR-005 | Live | (well_harness Notion writeback) |
| ADR-008 | Live | (FreeCAD N-3 dummy guard, see `tools/freecad_driver.py`) |
| ADR-010 | Live | (notion_sync contract) |
| ADR-011 | Accepted (R5 APPROVE + R2 APPROVE on amendments) | `docs/adr/ADR-011-pivot-claude-code-takeover.md` |
| ADR-012 | Accepted · enforced via `.github/workflows/calibration-cap-check.yml` | `docs/adr/ADR-012-calibration-cap-for-t1-self-pass-rate.md` |
| ADR-013 | Accepted · CI `--check` workflow live; branch protection script `scripts/apply_branch_protection.sh` | `docs/adr/ADR-013-branch-protection-enforcement.md` |
| ADR-014 | Accepted | `docs/adr/ADR-014-ws-event-bus-for-workbench.md` |
| ADR-015 | Accepted | `docs/adr/ADR-015-workbench-agent-rpc-boundary.md` |
| ADR-016 | Accepted | `docs/adr/ADR-016-frd-vtu-result-viz.md` |
| ADR-017 | Accepted (R7 alias-annotation + subclass bypass close, PR #104) | `docs/adr/ADR-017-rag-facade-cli-lib-parity.md` |
| ADR-018 | Accepted (defer electron-builder packaging) | `docs/adr/ADR-018-electron-packaging-strategy.md` |
| ADR-019 | Accepted | `docs/adr/ADR-019-material-properties-data-model.md` |
| ADR-020 | Accepted | `docs/adr/ADR-020-allowable-stress-lookup.md` |
| ADR-021 | Accepted | `docs/adr/ADR-021-gs100-radioss-smoke-fixture.md` |
| ADR-022 | Accepted | `docs/adr/ADR-022-gs101-demo-unsigned-fixture.md` |
| ADR-023 | Accepted by user directive, implementation PR pending | `docs/adr/ADR-023-lean-validation-workflow.md` |
| ADR-024 (lite) | Accepted under user direct-execution authorization 2026-05-07; lite scope = parameters-only Børvik 2002 citation for FM-04a Tier 1; full version reserved for FM-04b | `docs/adr/ADR-024-ballistic-benchmark-source-selection.md` |

---

## Carry-overs (still open)

1. **Foundation-Freeze governance gate path**: FF-07/08/09 are merged, old #26/#27/#28 and draft duplicates #117/#118/#120 are closed, ENG-17/18 are Done, and required checks now include `trailer-check` + `golden-samples-validation`. Workflow gates are reliable enough to select a next issue, but the current Linear backlog has no agent-eligible contract.
2. **Codex/ENG-* DRAFT lane**: remaining open drafts are ENG-20 (#119 planning doc) and ENG-23 (#115 real GS-101-adjacent code). Recommended: close or refresh #119 under a new issue; keep #115 only if ENG-22/GS101 acceptance is explicitly contracted.
3. **Pre-pivot P1-* (#11-#16) and surrogate stack (#30/#36/#37)** disposition deferred since 2026-04-25. These PRs predate ADR-011/012/013 and should not be merged without a separate Codex-owned triage/rebuild issue.
4. **GS-001/002/003 status flip** to `insufficient_evidence` (proposed in FP-001/002/003) — Notion control-plane status field still not changed.
5. **AERON L0 adoption**: ENG-33 / PR #128 salvaged the protocol package; ENG-35 / PR #135 landed the first concrete `CalculiXFEABackend`; ENG-36 / PR #137 wired that backend into `agents.solver.run()` while preserving the existing solver-node `SimState -> dict` contract; ENG-37 / PR #139 surfaced backend provenance through the graph cold-smoke path without starting GS101 or signed-validation work. Next AERON work should be an explicit Linear contract for one user-facing adoption point, not GS101 or signed validation by implication.

---

## How to update this file

Update STATE.md whenever:

- A FF-task changes status (pending → in-flight → done).
- A branch is pushed or a PR opens / merges.
- An ADR is accepted, revised, or superseded.
- A carry-over is closed (delete the line, don't strike-through — git history holds the trail).
- The `Last updated` stamp must change in the same commit.

**STATE.md must be updated in the SAME PR as the change it reflects** (FF-05 R1 lesson). Do **not** update STATE.md to reflect things that have not yet landed in the repo. Forward-looking commitments belong in the relevant ADR / task tracker, not here. PRs in flight may be listed under "Open PRs" but their status must reflect actual git state, not aspirations.
