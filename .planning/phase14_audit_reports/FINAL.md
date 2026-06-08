# FM-04a Phase 14 FINAL — Whole-arc TAA

**Commit under audit:** `373ab88` (slice D), inclusive of slice-E retrospective + STATE refresh landing in the same arc.
**Branch:** `claude/FM-04a-tier1-ballistic-candidate`.
**Auditor posture:** independent adversarial review against the binding 9-axis whole-arc rubric (`.planning/FM-04A_PHASE14_BLUEPRINT.md` §4). No exposure to the implementation conversation.
**Date:** 2026-05-17.

Commit chain audited:
```
efca6a9  plan(FM-04a/Phase14): bind blueprint
2dcdab7  slice A first cut
5779fe7  slice A rework (HIGH-1 + HIGH-2 + LOW-1 + LOW-2)
071a0f2  slice A re-audit closure (LOW-3 signoff POST through SSOT)
b72c507  slice B (extraction + cross-check)
9aba727  slice C (advisor explicit_dynamics branch)
373ab88  slice D (rod-wave-impact-candidate fixture)
```

---

## Verdict: **APPROVE** (100/100 — every axis at full weight)

Stop condition ≥99/100 AND every axis ≥95% of weight — **MET on both clauses**. Matches Phase 11 (100/100), Phase 12 post-slice-I (100/100), and Phase 13 (100/100) bar.

---

## Verification commands run by this auditor

| # | Command | Result |
|---|---------|--------|
| 1 | `git log --oneline efca6a9^..HEAD` | 7 commits (1 plan + 4 slices + 1 slice-A rework + 1 slice-A re-audit closure) |
| 2 | `uv run pytest tests/ -q --no-header` | **2379 passed, 7 skipped** in 23.31 s — matches retro arithmetic 2280 + 38 (A) + 32 (B) + 12 (C) + 17 (D) |
| 3 | `uv run pytest tests/test_phase14_cross_route_signed_registry_refusal.py -q` | 38 passed in 0.81 s |
| 4 | `uv run pytest tests/test_phase14_advisor_explicit_dynamics_branch.py::test_four_question_gate_fires_on_explicit_dynamics_branch -v` | PASSED — 4-question gate fires |
| 5 | Forbidden-token grep across 11 Phase-14 surfaces (module + routes + methodology + retro + fixture JSON + NOTES) | Zero hits outside `no <token>` enumeration form or the FORBIDDEN_CLAIM_TOKENS tuple itself (`advisor_critique.py:107-116` and `explicit_dynamics_extraction.py:29-32`); both are allow-listed |
| 6 | `git diff efca6a9^..HEAD -- scripts/hf1_path_guard.py` | empty — HF1 path-guard untouched |
| 7 | `git log --diff-filter=A --name-only efca6a9^..HEAD -- golden_samples/ \| grep ^golden_samples/GS-[0-9]{3}/` | empty — no `^GS-\d{3}$` directory created |
| 8 | Tier 1 trio probe across 4 new JSON envelopes (`expected_results`, `ballistic_metrics`, `animation_manifest`, `convergence_study`) | All four carry `claim_tier="Tier 1 engineering candidate"` + `claim_boundary="tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement"` |
| 9 | `grep "explicit_dynamics" backend/app/services/reporting/case_completeness.py` | Phase 11 A rubric entry at line 198-211 (shares ballistic rubric, weights sum to 100) — substantiation closes the v1 blueprint image #06 row 3 leg (a) |
| 10 | Real-solver/external-API grep across Phase 14 modified files | empty — no `subprocess`, `os.system`, `ccx`, `openradioss`, `requests.`, real `httpx.AsyncClient` invocation introduced |

All 10 checks pass.

---

## Scores per axis (binding 9-axis whole-arc rubric)

### B — Blueprint discipline — **12 / 12** (floor 11.4)
Slices A through E all shipped exactly as `.planning/FM-04A_PHASE14_BLUEPRINT.md` §3 demanded. Zero scope creep. The optional MINOR schema bump for `impact_response_sweep` (1.2.0 → 1.3.0) was honestly evaluated by the implementor and dropped as unnecessary (existing 1.2.0 contract works); blueprint §3.B explicitly framed it as "only if the service genuinely needs it" — the right disposition. The retro acceptance-checklist enumerates all six §6 acceptance criteria and ticks 6/7 (the seventh is THIS audit; checking it is this report's job). Both out-of-scope items from blueprint §5 (real OpenRadioss invocation, visual dev-server smoke) remain out of scope.

### M — Methodology — **12 / 12** (floor 11.4)
All SSOT constants typed and module-level: `WAVE_CROSS_CHECK_TOLERANCE_PCT: float = 5.0`, `EXPLICIT_DYNAMICS_CONVERGENCE_KIND: str`, `ENERGY_PARTITION_EPSILON: float`, `ENERGY_PARTITION_DRIFT_FRACTION: float`, `SIGNED_REGISTRY_RE`, `_KNOWN_CASE_ID_ROUTES: tuple[tuple[str, str, str], ...]`, `_OPT_OUT_ROUTES`, plus slice-D generator constants (`CASE_ID`, `L_M`, `E_PA`, `RHO_KG_PER_M3`, `IMPACT_VELOCITY_M_PER_S`, `FRAME_COUNT`, `FRAME_DT_S`, `TIER1_CLAIM_TIER`, `TIER1_CLAIM_BOUNDARY`). Two new methodology docs (`case_id_route_discipline.md`, `explicit_dynamics_cross_check.md`) both cite source-file identifiers + bump-history policy. Slice-A M cap (10/12) fired at first cut on regex duplication; rework `5779fe7` consolidated to one SSOT, restoring 12/12. Slice-B M = 12/12 (the LOW-1 docstring `[3]` → `[2]` index drift closed in slice C — cosmetic, runtime correct throughout).

### T — Tests — **15 / 15** (floor 14.25)
Per-slice floors met with margin: A 38 (target ≥10), B 32 (target ≥18), C 12 (target ≥10), D 17 (target ≥10) = 99 new backend tests. All four slices' final TAA T scores landed 15/15. Distinct behaviors anchor each test: 4 theme markers in slice C anchored on full theme-header phrase (not bare marker token), defeating the canonical sneak-into-adjacent-theme attack; slice-D A:-3 test RE-DERIVES the analytical pin from fixture-self-reported material constants rather than trusting the `observed_first_reflection_s` field; slice-B 8 defensive-parse raise sites each pinned by a dedicated test; slice-A per-route parametrize over BOTH 422-side AND candidate-passes-side (after LOW-1 closure).

### C — Coverage — **12 / 12** (floor 11.4)
Tier 1 disclaimer trio confirmed present on all four new JSON envelopes (`expected_results.json`, `ballistic_metrics.json`, `animation_manifest.json`, `convergence_study.json`). Forbidden-token grep across 11 Phase-14 surfaces produces zero hits outside the `no <token>` enumeration form OR the `ADVISOR_FORBIDDEN_TOKENS` tuple literal (which is itself the allowlist for the audit). No Tier-2-promoting language anywhere in new modules. Slice-A vocabulary drift (advisor surface vs SSOT-helper output) closed in rework — both routes now emit the canonical sentence verbatim. Per-route 422 contract verified via ASGI probe by slice-A TAA.

### X — Cross-cutting anti-gaming + defensive parsers — **12 / 12** (floor 11.4)
Two load-bearing cross-cutting deliverables:
1. **Slice-A meta-guard:** `_KNOWN_CASE_ID_ROUTES` SSOT tuple + `_OPT_OUT_ROUTES` opt-out list, asserted against FastAPI route introspection by `test_known_routes_match_app_introspection`. A new `/{case_id}` route that omits the gate trips the schema-check AND the per-route 422 test. Per-route parametrize on both 422 AND candidate-passes sides (LOW-1 closure).
2. **Slice-B 1D-bar wave-propagation cross-check:** closed-form physics pin (`c = sqrt(E/rho) = 5048 m/s` for steel; `t = L/c = 198.116 us` for L=1m), boundary-pinned with `math.isclose(rel_tol=1e-12)`. The 8-surface defensive parser raises BEFORE returning on every malformed input, each with a dedicated test.

Inter-slice integration: slice-C theme 4 cross-references slice-B `bar_wave_first_reflection_s` (verified by slice-C TAA probe 5). Slice-D A:-3 test calls slice-B SSOT functions directly — drift in the fixture trips the analytical cross-check before any downstream consumer can rely on a wrong pin.

### D — Slice disposition matrix completeness — **8 / 8** (floor 7.6)
Retrospective documents all 5 slices A-E by name with deliverables, test counts, TAA disposition, and disposition notes. Quantitative-outcome table covers 12 metrics with Δ column. "What worked" enumerates 6 patterns; "What did not work" enumerates 5 surprises with `Lesson:` extraction; "Carry-forwards" enumerates 5 deferred items each with scope rationale. Acceptance criteria §6 checklist explicit (6/7 ticked, this audit ticks the 7th).

### A — Anti-gaming guards exercised per slice — **8 / 8** (floor 7.6)
All seven blueprint §4 anti-gaming guards exercised:
- **M:-2** — every new constant is named + module-level + typed (verified above).
- **T:-3** — boundary-pinned tests: 5050 m/s wave speed AND 0.198 ms first-reflection both pinned exactly in slice B.
- **T:-4** — per-route parametrize on slice-A meta-guard such that a per-route failure surfaces with the route path in the test name.
- **C:-8** — no Tier-2-promoting language in any new module; forbidden-token grep clean.
- **A:-2** — slice-A meta-guard is meta-pinned via `_KNOWN_CASE_ID_ROUTES ∪ _OPT_OUT_ROUTES = introspected_set` assertion.
- **A:-3** — slice-D fixture verified BY ASSERTING observed-vs-analytical via `wave_propagation_residuals(...).within_tolerance`, NOT by trusting the fixture's `observed_first_reflection_s` field. Re-derived: `5047.545 m/s`, `t_refl = 198.116 us`, observed `200.0 us`, residual `0.9509%`.
- **E:-2** — optional schema bump for `impact_response_sweep` honestly dropped (not faked); the retro explicitly documents the dispensation.

### E — Full sweep green + no real solver/LLM — **8 / 8** (floor 7.6)
Full sweep verified by this auditor: **2379 passed, 7 skipped** in 23.31 s, matching the retro arithmetic exactly (2280 + 38 + 32 + 12 + 17 = 2379). No real OpenRadioss / CalculiX / OpenFOAM / external LLM invocation introduced anywhere in the Phase 14 diff (grep across all modified files for `subprocess`, `os.system`, `ccx`, `openradioss`, `requests.`, real `httpx.AsyncClient` returned empty). HF1 path-guard untouched. No `^GS-\d{3}$` directory created under `golden_samples/`. 4-question gate test verified passing on the advisor explicit_dynamics branch.

### V — TAA evidence quality — **13 / 13** (floor 12.35)
Per-slice TAA reports archived at `.planning/phase14_audit_reports/{A,B,C,D}.md`. All four are deeply substantive:
- **A.md** is unusual: the original audit returned **REQUIRES_REWORK 55/63** with 4 findings (HIGH-1 visualization.py call ordering, HIGH-2 advisor + case-completeness stragglers, LOW-1 single-anchor candidate-passes, LOW-2 missing methodology paragraph), then a full **re-audit section** independently verifies the closure at 63/63 + identifies the NEW LOW-3 (signoff POST stragglers) which was then closed in `071a0f2`. This is exactly the Phase 13 protocol — findings close inline, audit re-runs independently.
- **B.md** identifies LOW-1 docstring-`[3]`-vs-runtime-`[2]` drift with explicit math verification (`python -c "import math; print(math.sqrt(200e9/7850))"` → 5047.5), distinguishing documentation drift from runtime bug.
- **C.md** runs 6 adversarial probes including a marker-uniqueness analysis showing why `contact stiffness convergence` (theme-header anchor) defeats the canonical anti-gaming attack vector.
- **D.md** verifies live ASGI 95/100 + traces every fixture envelope's Tier 1 trio + verifies the A:-3 re-derive defense byte-for-byte.

Every report cites commit SHAs, file:line references, verification commands with output. Re-audit discipline applied where REQUIRES_REWORK fired. Average per-slice TAA score 63 + 61 + 63 + 63 = **62.5 / 63 = 99.2%** (Phase 13 average was 60.5 / 63 = 96%; the bar moved up).

---

## Subordinate gate checks

| Gate | Required | Observed | Status |
|------|----------|----------|--------|
| v1 blueprint image #06 row 3 closure (`explicit_dynamics`) | Substantiated end-to-end by (a) Phase 11 A rubric + (b) Phase 14 B service + (c) Phase 14 C advisor + (d) Phase 14 D fixture | (a) `case_completeness.py:198-211` weights sum to 100; (b) `explicit_dynamics_extraction.py` 342 LOC + methodology doc; (c) `advisor_critique.py:293-368` 4 themes + 12 tests; (d) `golden_samples/rod-wave-impact-candidate/` 4 envelopes + generator + 17 tests + live ASGI 95/100 | **CLOSED** |
| Phase 13 retro carry-forward §2 (cross-route meta-guard) | Enumerate every in-scope route + assert 422 + canonical detail on each | `tests/test_phase14_cross_route_signed_registry_refusal.py` enumerates 13 GET routes + 4 opt-outs via FastAPI introspection (`_KNOWN_CASE_ID_ROUTES` SSOT tuple); 38 tests all green; SSOT helper `_signed_registry_refusal.py` consumed by all 14 routes after slice-A rework; methodology doc `case_id_route_discipline.md` documents the helper-call-ordering invariant | **CLOSED** |
| Backend test count ≥ 2280 + slice floors | ≥ 2280 + 38 + 18 + 10 + 10 = ≥ 2356 | 2379 | **MET** (+23 margin) |
| Frontend test count ≥ 135 | ≥ 135 | 135 (unchanged) | **MET** |
| HF1 path-guard preserved | No edits to `scripts/hf1_path_guard.py` | Confirmed via `git diff` | **MET** |
| No `^GS-\d{3}$` dir created in Phase 14 | None | Confirmed via `git log --diff-filter=A` | **MET** |
| No real OpenRadioss / CalculiX / OpenFOAM invocation | None | Confirmed via subprocess/exec grep | **MET** |
| Tier 1 disclaimer trio on every new JSON envelope | All 4 fixture envelopes | All 4 carry the SSOT trio verbatim | **MET** |
| 4-question gate fires on advisor explicit_dynamics | Test passes | `test_four_question_gate_fires_on_explicit_dynamics_branch` PASSED | **MET** |
| LLM-offline-first preserved | No real LLM API calls | StubAdvisor used throughout; `LLMAdvisor` env-var-gated only | **MET** |

All 10 subordinate gates pass.

---

## Findings

**Zero HIGH. Zero MEDIUM. Zero LOW.**

Positive observations (not findings, but worth recording):

1. **Slice-A re-audit discipline is exemplary.** A.md contains BOTH the original REQUIRES_REWORK audit AND an independently-conducted re-audit after rework. The re-audit identifies a NEW LOW-3 (signoff POST stragglers + misleading test comment) that the implementor then closed in `071a0f2`. This is the gold-standard "audit catches its own blind spot" pattern.
2. **The A:-3 anti-gaming defense in slice D is unusually principled.** Rather than trusting `observed_first_reflection_s` from the fixture JSON, the test re-derives the analytical pin from `E_Pa`, `rho_kg_per_m3`, `rod_length_m` reported in the fixture's `explicit_dynamics_summary` and computes observed time as `frame_index * frame_dt` — one indirection more honest. A fixture authoring error (wrong rho, wrong L, wrong frame_dt) trips this assertion before any downstream consumer sees the wrong pin.
3. **Cross-slice integration is structural, not boilerplate.** Slice-C theme 4 cites slice-B `bar_wave_first_reflection_s` by name; slice-D test imports the same function. The methodology doc `explicit_dynamics_cross_check.md` cites the module path; the slice-A SSOT helper is consumed by 14 routes. The arc reads as one substantiation, not four disjoint slices.
4. **The retro distinguishes "what worked" (6 patterns) from "what surprised us" (5 surprises with `Lesson:` extraction).** Each surprise carries a concrete actionable lesson — e.g., "when a docstring cites an index into another module's data structure, the index MUST be verified at write-time" — that closes a future regression vector.
5. **Honest dispensation of the optional schema bump.** Blueprint §3.B optionally permitted a `CONVERGENCE_STUDY_SCHEMA_VERSION` 1.2.0 → 1.3.0 MINOR bump for `impact_response_sweep`. The implementor dropped the bump as unnecessary and the retro explicitly documents the dispensation. The "fake a schema bump to claim more work" anti-pattern was not committed.

---

## Closure recommendation

**APPROVE the Phase 14 arc.** Stamp `.planning/STATE.md` with the closure stamp (already present at `fm04a-phase14-explicit-dynamics-substantiation-CLOSED-LOCAL-2026-05-17 · @373ab88`). Tick the FINAL TAA acceptance-criteria box in the retro (§ "Phase 14 acceptance criteria — checklist" line 73). Nothing to push; no PR; no Linear / Notion writes; no FM-04b prerequisite crossed.

Phase 14 substantiates the fourth and final analysis-type entry in `ANALYSIS_TYPE_TUPLE` (`explicit_dynamics`) with a 1D-bar wave-propagation analytical cross-check + a 95/100 case-completeness-scoring synthetic Hopkinson-style fixture. The cross-route signed-registry discipline is now universal across the 14 reviewer-facing Tier 1 surfaces with an SSOT helper + introspection-driven meta-test. The v1 blueprint image #06 row 3 is CLOSED. The Phase 13 retrospective §2 carry-forward is CLOSED.

Arc joins Phase 11 / Phase 12 (post-slice-I) / Phase 13 at the 100/100 every-axis-full stop-condition ceiling.

---

## Verdict summary

**APPROVE — 100/100 — every axis at full weight — stop condition (≥99 AND every axis ≥95% of weight) MET**

| Axis | Weight | Score | % of weight |
|------|--------|-------|-------------|
| B | 12 | 12 | 100% |
| M | 12 | 12 | 100% |
| T | 15 | 15 | 100% |
| C | 12 | 12 | 100% |
| X | 12 | 12 | 100% |
| D | 8 | 8 | 100% |
| A | 8 | 8 | 100% |
| E | 8 | 8 | 100% |
| V | 13 | 13 | 100% |
| **Total** | **100** | **100** | **100%** |
