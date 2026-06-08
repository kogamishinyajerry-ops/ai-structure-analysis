# FM-04a Phase 12 — Cohort Substantiation + Modal Anchor

> **Tier 1 engineering candidate; not signed validation; not benchmark agreement.**

**Status:** Active. Closes Phase 11 carry-forwards § (TBD by retrospective) and the v1 blueprint gap analysis at `.planning/blueprints/v1_phase11_close/README.md#known-gaps`.

**Author:** Local Claude Opus 4.7 under direct-execution authorization, mirroring the Phase 10 / Phase 11 protocol (binding 9-axis rubric + independent TAA gating).

**Branch:** `claude/FM-04a-tier1-ballistic-candidate`. Local-only; no pushes; no PRs; no Linear/Notion writes.

**Hard constraints (inherited from Phase 11, NON-NEGOTIABLE):**
* Tier 1 disclaimer trio stamped on every new envelope.
* 9 forbidden tokens (`validated against / perforation completed / bullet-through-steel complete / validated physics / production ready / certified / approved for service / asme compliant / signed off`) refused outside `not <claim>` form.
* HF1 forbidden zone (`golden_samples/**` default read-only; only `*-candidate` writable; `^GS-\d{3}$` registry never touched).
* No real OpenRadioss solver in CI; CalculiX 2.23 is the only solver allowed in candidate cases.
* No real LLM API calls anywhere; placeholder + injection seam only.
* LLM-offline-first: every reviewer flow must complete without an LLM.
* AI is advisor, NOT driver: 4-question gate audits every advisor envelope.

---

## 1. North Star (1 sentence)

**Make the cohort dashboard (blueprint #07) and the "Day in the Life" workflow (blueprint #08) into screenshots a reviewer can take on the live workbench today**, by substantiating 4 real candidate cases across ≥2 analysis types and 3 snapshots, with real z-score / trend-slope alarms firing on real data.

---

## 2. Closes these gaps

### From v1 blueprint vs Phase 11 reality:
1. **Modal slot is a placeholder.** `ANALYSIS_TYPE_TUPLE` lists `'modal'` and `ANALYSIS_TYPE_RUBRIC_WEIGHTS['modal']` has weights, but there is no real `modal` service module, no Euler-Bernoulli cross-check, no `modal` advisor branch, no real `modal` candidate case.
2. **Cohort is single-case.** Only `cylinder-pv-candidate` is real; everything else in `tests/test_fm04a_phase11_advisor_e2e.py` writes synthetic snapshots. Trend / z-score / cohort-summary alarms have correct code paths but no real triggers.
3. **`convergence_kind` doesn't cover modal.** Slice-A only defined `linear_static` + `explicit_dynamics` branches in `trust_score._score_convergence_axis`; modal cases would fall back to `explicit_dynamics` two-axis scoring inappropriately.

### From Phase 11 retrospective carry-forwards (revisited, not all addressed in Phase 12):
* §1 — PV rubric inline weights `15` / `10`. **Will address in slice A** while touching `case_completeness.py`.
* §2 — `AdvisorContext.extra` unread slot. **Will address in slice B** by having modal advisor consume `extra['mode_count_target']`.
* §3 — Snapshot manifest version pinning in tests. **Will address in slice D** by replacing literal `"1.3.0"` with the SSOT constant.
* §4 — Permissive 400-499 status range assertions. **Will tighten in slice F** for the new endpoints; existing legacy assertions left untouched.
* §5 — Structured `refused_claims` field. **Deferred to Phase 13** (out of scope; would require schema bump on `AdvisorCritique` and is not blocking).

---

## 3. Seven-slice plan

Each slice has its own binding sub-rubric and independent TAA. Slice TAA reports archive under `.planning/phase12_audit_reports/`.

### Slice A — Modal eigenfrequency service + Euler-Bernoulli cross-check

**Goal:** add a real modal analysis path that mirrors the existing Lamé cross-check pattern from Phase 11 slice A.

**Deliverables:**
* `backend/app/domain/modal_extraction.py` (new):
  * `parse_modal_frd(path) -> ModalResult`: pulls eigenfrequencies + per-mode displacement field from a CalculiX modal FRD.
  * `euler_bernoulli_cantilever_freq(beam, mode_n) -> float`: closed-form analytical solution for the first N modes of a uniform-cross-section cantilever (β values for n=1..4 are SSOT constants).
  * `modal_residuals(numerical, analytical, mode_count) -> ModalResidualReport`: per-mode relative error report with bump-history docstring.
* `backend/app/services/reporting/_schema_versions.py`:
  * MINOR bump `CONVERGENCE_STUDY_SCHEMA_VERSION` 1.1.0 → 1.2.0 (the existing convergence_kind discriminator gains `"modal"` as a valid value; convergence axes become `{mode_count_sweep}` for modal cases instead of mesh/dt).
* `backend/app/services/reporting/trust_score.py`:
  * `_score_convergence_axis` gains a `convergence_kind == "modal"` branch (scores against mode_count_sweep, treats mesh_sweep + dt_sweep as N/A but still requires a coarsening-direction monotonicity check).
* `backend/app/services/reporting/case_completeness.py`:
  * Slice-A carry-forward fix: rename inline `15` / `10` in `ANALYSIS_TYPE_RUBRIC_WEIGHTS["linear_static_pv"]` to named constants `WEIGHT_BALLISTIC_METRICS_PV` / `WEIGHT_CONVERGENCE_STABLE_PV`.
* `.planning/methodology/analysis_type_completeness_rubric.md`: append a §Modal section explaining the modal axis weights + cross-check tolerance.
* `tests/test_phase12_modal_extraction.py` (new, ≥18 tests): Euler-Bernoulli β values pinned, FRD parser shape pins, per-mode residual math pin, convergence_kind == "modal" trust score branch verified, schema bump pinned in `test_schema_versions_stamping.py`.

**Binding sub-rubric (slice A):** M ≥10/12, T ≥13/15, C ≥10/12, A ≥7/8, E ≥7/8, V ≥7/8.

### Slice B — Modal advisor concerns + modal rubric substantiation

**Goal:** StubAdvisor produces modal-specific concerns when `convergence_kind == "modal"`; the modal rubric weights become substantively distinct from the ballistic/explicit_dynamics rubrics.

**Deliverables:**
* `backend/app/services/reporting/advisor_critique.py`:
  * `StubAdvisor.produce` gains a `convergence_kind == "modal"` branch that surfaces:
    * Mode-shape MAC concerns (mass-normalized assurance criterion).
    * Lanczos extraction method questions (CalculiX `*FREQUENCY` uses Lanczos; reviewer should verify shift-and-invert convergence on poorly-conditioned cases).
    * Mass participation ratio: requests reviewer confirm cumulative mass participation ≥ 80% for the extracted mode set, otherwise critical modes may be missing.
    * Frequency tolerance vs analytical: surfaces a concern when relative error on the dominant bending mode exceeds 5%.
  * The branch reads `context.extra["mode_count_target"]` if present (closes Phase 11 retro §2: `AdvisorContext.extra` unread slot).
* `backend/app/services/reporting/case_completeness.py`:
  * `ANALYSIS_TYPE_RUBRIC_WEIGHTS["modal"]` substantiated with named constants:
    * `WEIGHT_MODE_COUNT_COVERAGE = 15`
    * `WEIGHT_FREQ_CONVERGENCE = 15`
    * `WEIGHT_MODE_SHAPE_QUALITY = 10`
    * `WEIGHT_MASS_PARTICIPATION = 10`
    * Universal axes unchanged (10+10+10+10+10 = 50).
    * Sum = 100, audited by `_assert_rubric_weights_consistent`.
  * `_score_modal_specific_axes(score, metrics_path)` reads `modal_summary` block from metrics file, scores each axis with documented partial-credit boundaries.
* `.planning/methodology/analysis_type_completeness_rubric.md`: §Modal rebalance section appended.
* `tests/test_phase12_modal_advisor.py` (new, ≥14 tests): modal advisor branch surfaces named concerns; modal rubric weight sum boundary pinned; modal axes per-credit boundary tests; `AdvisorContext.extra` is now passed through to the modal branch.

**Binding sub-rubric (slice B):** M ≥10/12, T ≥12/15, C ≥10/12, A ≥6/8, E ≥7/8, V ≥7/8.

### Slice C — Three new real-runnable candidate cases

**Goal:** demo_*_candidate harness for three NEW cases, each running real CalculiX with verified analytical cross-check.

**Deliverables:**
* `demo_modal_cantilever_pv/` (new directory mirroring `demo_cylinder_pv/`):
  * `cantilever.geo` — 1m × 50mm × 50mm steel cantilever, 40 × 2 × 2 structured C3D20 hex mesh.
  * `assemble_modal_deck.py` — gmsh inp → CalculiX modal deck with `*FREQUENCY` extracting 10 modes.
  * `analyze_modal_results.py` — FRD parser + Euler-Bernoulli cross-check for modes 1, 3, 5 (skips degenerate pairs from square cross-section).
  * `run_modal_e2e_demo.py` — 8-stage orchestrator analogous to Phase 11 demo: gmsh → assemble → ccx → analyze → fixture → snapshot → trust score → HTTP round-trip.
  * Generates fixture `golden_samples/modal-cantilever-candidate/` (a *-candidate dir, HF1-permitted).
* `demo_cylinder_pv_extended/` (new): same PV analysis type but with a longer cylinder (L = 0.4m vs 0.2m baseline) and a higher internal pressure (P = 20 MPa). Provides a second PV case so cohort sees within-type variation.
* `demo_modal_cantilever_stiff/` (new): same beam but stiffer cross-section (75mm × 75mm) — drives different mode 1 frequency, provides a second modal case for cohort.
* Generator scripts under `scripts/gen_modal_cantilever_deck.py` / `scripts/gen_cylinder_pv_extended_deck.py` / `scripts/gen_modal_cantilever_stiff_deck.py` so the snapshot's `generator/` directory has SHA-attributable scripts (Phase 9 B + Phase 10 E compatibility).
* `pyproject.toml` ruff exclude extended to cover the three new `demo_*` dirs.
* `tests/test_phase12_candidate_cases_smoke.py` (new, ≥12 tests): synthetic-fast assertions on the candidate case fixtures (without re-running CalculiX in CI — the actual run is one-shot during slice authoring), confirming each fixture has the expected files + analysis_type + cross-check residual under tolerance.

**Binding sub-rubric (slice C):** M ≥10/12, T ≥11/15, C ≥10/12, A ≥6/8, E ≥7/8, V ≥7/8.

### Slice D — Multi-snapshot time-series + real anomaly trigger

**Goal:** cohort dashboard receives real data that exercises every alarm surface.

**Deliverables:**
* 3 cohort snapshots written at distinct UTC seconds, each containing all 4 cases (cylinder-pv-candidate from Phase 11 + 3 new from slice C):
  * Snapshot 1 (baseline): all 4 cases score ≥ 80 on trust score.
  * Snapshot 2 (regression): `cylinder-pv-extended-candidate` drops its reproducibility axis (deliberately remove a generator script) → trust score falls to ~50, qualifying for "regressed" bucket.
  * Snapshot 3 (trend): same drop maintained + additional degradation in completeness axis → `cylinder-pv-extended-candidate` slope across snapshots 1-2-3 trips the trend-slope alarm at the "minor degradation" threshold.
  * `modal-cantilever-stiff-candidate` deliberately has an outlier energy_audit score (5σ above cohort mean) on snapshot 3 → fires the z-score outlier alarm.
* `tests/test_phase12_cohort_alarms.py` (new, ≥10 tests):
  * Cohort summary bucket distribution: 2 healthy / 1 watching / 1 regressed.
  * Trend slope alarm fires on `cylinder-pv-extended-candidate` with severity == "minor_degradation".
  * Z-score outlier alarm fires on `modal-cantilever-stiff-candidate` axis == "energy_audit" with severity bucket >= 2σ.
  * Each alarm payload's case_id + axis + severity asserted distinctly.
  * Snapshot manifest schema_version reads from SSOT constant `COHORT_SNAPSHOT_MANIFEST_SCHEMA_VERSION` (closes Phase 11 retro §3).

**Binding sub-rubric (slice D):** M ≥10/12, T ≥10/15, C ≥10/12, A ≥6/8, E ≥7/8, V ≥7/8.

### Slice E — Cohort dashboard frontend to blueprint-#07 fidelity

**Goal:** the live UI renders blueprint #07 with the slice-D data.

**Deliverables:**
* `frontend/src/components/CohortDashboardPanel.tsx` (extend or replace existing): renders 4-case left rail with mini-sparklines + bucket badges; center 4-axis trust score timeline (line chart across 3 snapshots); right alerts panel showing trend events + z-score outliers + rate-limit events; bottom schema version footer (4 versions).
* `frontend/src/cohortDashboardClient.ts` (extend existing): defensive parser; falls back to `'unknown'` for unknown bucket / unknown alert kind (X:-2).
* `frontend/src/App.tsx`: mount the cohort dashboard panel as a stable Tab.
* `frontend/test/CohortDashboardPanel.test.tsx` (new, ≥10 tests): SSOT tuple pins; bucket badge color coding; alarm severity color coding; defensive parser for unknown bucket / unknown alert.

**Binding sub-rubric (slice E):** M ≥10/12, T ≥9/15, X ≥10/12, C ≥10/12, A ≥6/8, E ≥7/8, V ≥7/8.

### Slice F — Three new E2E reviewer journeys

**Goal:** the three "Day in the Life" workflow points from blueprint #08 turn into automated journey tests.

**Deliverables:**
* `tests/test_fm04a_phase12_cohort_journeys_e2e.py` (new):
  * **Journey 4 — cohort triage:** reviewer opens dashboard, sees 1 regressed bucket, drills into `cylinder-pv-extended-candidate`, reads its advisor critique (which by slice B should surface the reproducibility-axis concern), POSTs `needs_more_evidence` signoff, cohort summary bucket transitions. Crosses 5 routes.
  * **Journey 5 — cross-case investigation:** same reviewer audits 3 cases in one session (modal cantilever / PV cylinder / modal stiff cantilever); advisor critique surfaces analysis-type-distinct concerns (PV plasticity warning vs modal mass-participation question vs modal Lanczos extraction question). Crosses ≥6 routes.
  * **Journey 6 — trend alarm closure:** reviewer sees trend slope alarm for `cylinder-pv-extended-candidate`, signs off as `watching` with documented rationale; a new "snapshot 4" is written with restored evidence; trend alarm no longer surfaces that case_id in the next dashboard fetch. Crosses ≥4 routes.
* ≥12 supplemental integration tests in `tests/test_phase11_endpoints_integration.py` or a new file: tighten the permissive `400-499` ranges from Phase 11 retro §4 (closes Phase 11 retro §4 where feasible).
* Slice-F TAA archived at `.planning/phase12_audit_reports/F.md`.

**Binding sub-rubric (slice F):** M ≥10/12, T ≥12/15, C ≥10/12, A ≥6/8, E ≥7/8, V ≥7/8.

### Slice G — STATE refresh + retrospective + FINAL whole-arc TAA

**Goal:** mirror Phase 10 G / Phase 11 G protocol.

**Deliverables:**
* `.planning/retrospectives/fm04a_phase12_cohort_substantiation.md` with axis-by-axis honest scoring.
* `.planning/STATE.md` refreshed.
* `.planning/phase12_audit_reports/FINAL.md` archived after spawning the FINAL whole-arc TAA.
* **Stop condition: FINAL TAA verdict APPROVE ≥99/100 AND every axis ≥95% of weight.**

---

## 4. Binding 9-axis rubric (unchanged from Phase 10 / Phase 11)

| Axis | Weight | Description |
|---|---|---|
| **B** Blueprint discipline | 12 | Every slice maps to a named deliverable in §3; zero scope creep; gap-driven (closes a v1 blueprint gap or a Phase 11 carry-forward). |
| **M** Methodology / SSOT | 12 | New constants live in module-level SSOTs; bump-history docstrings; methodology doc references by Python identifier. |
| **T** Testing | 15 | Per-slice test floors in §3; parametrize over SSOT tuples; per-token / per-type / per-key tests for distinct anti-gaming guards. |
| **C** Claim discipline | 12 | Tier 1 disclaimer trio on every new envelope; forbidden-claim audit fires per token; 4-Q gate audit on every advisor critique. |
| **X** Frontend forward-compat | 12 | Defensive parser falls back to `'unknown'` for unknown values; pre-Phase-12 payloads coerce safely; tsc clean. |
| **D** Documentation | 8 | Methodology SSOT doc updated; per-slice TAA archives; retrospective with carry-forwards. |
| **A** Anti-gaming | 8 | Each named guard (M:-2 / T:-3 / T:-4 / T:-5 / C:-8 / C:-10 / A:-2 / A:-3 / A:-4 / A:-5 / E:-3 / E:-4 / X:-2) exercised distinctly. |
| **E** Execution | 8 | Full backend + frontend sweeps clean at HEAD; no regressions in pre-Phase-12 surfaces. |
| **V** Verdict | 13 | Per-slice TAA verdicts + FINAL whole-arc TAA verdict. |

**Cumulative score = sum of 9 axes (max 100). Stop condition for closure: ≥99/100 AND every axis ≥95% of weight (i.e. ≥11.4/12 for the 12-weight axes, ≥14.25/15 for T, ≥7.6/8 for the 8-weight axes, ≥12.35/13 for V).**

---

## 5. Anti-gaming guards inherited + new (Phase 12 list)

Same 18 named guards from Phase 11 §4 carry over. Phase 12 adds:

* **M:-2 (extended)** — modal axis weight constants (`WEIGHT_MODE_COUNT_COVERAGE`, etc.) must be named, not inline.
* **T:-6 (NEW)** — each of the 3 NEW candidate cases must have a per-case smoke test asserting the fixture has the expected files + analysis_type stamp.
* **A:-6 (NEW)** — the multi-snapshot anomaly fixture must produce alarms that are **distinguishable by case_id**, not by alarm count alone. A test reading the alarm payload must be able to assert "this alarm is for case X on axis Y at severity Z" without ambiguity.
* **E:-5 (NEW)** — the three new E2E journeys must walk ≥4 routes each (not ≥2 like Phase 11 floor) to prove cohort-level composition is real.

---

## 6. Stop condition (re-stated for emphasis)

Phase 12 closes when **all** of the following hold simultaneously at HEAD:

1. Full backend sweep clean (≥ 2064 + new tests, 0 failed).
2. Full frontend sweep clean (≥ 97 + new tests, 0 failed).
3. `tsc --noEmit` clean.
4. Per-slice TAAs: 7/7 APPROVE on first cut (or APPROVE_WITH_LOW with all findings carry-forward, no MEDIUM/HIGH).
5. FINAL whole-arc TAA verdict: **APPROVE** with cumulative score **≥ 99 / 100** AND every axis ≥ 95% of its weight.
6. HF1 zone untouched (`git diff <phase12-base>..HEAD -- golden_samples/^` returns empty for the signed registry; only `*-candidate` dirs may be added).
7. No real LLM API calls anywhere in the test sweep (`grep -rn "httpx|requests|anthropic|urllib|aiohttp"` on the advisor module returns only placeholder/docstring references).
8. Zero pushes; zero PRs; zero Linear/Notion writes.

If FINAL TAA returns CHANGES_REQUIRED or score < 99, **iterate** — fix the named defects, re-run sweeps, re-spawn FINAL TAA. Do not "explain away" a failing FINAL; address the finding or re-scope the slice.

---

## 7. Smoke validation (slice A de-risking, done 2026-05-16)

Before committing to slice A, the modal CalculiX `*FREQUENCY` card was smoke-tested on a 1m × 50mm × 50mm steel cantilever (gmsh structured 40×2×2 C3D20 hex mesh):

| Mode | CalculiX result (Hz) | Euler-Bernoulli analytical (Hz) | Relative error |
|---|---|---|---|
| 1 (1st bending Y) | 41.84 | 41.78 | **0.14 %** |
| 3 (2nd bending Y) | 259.23 | 261.79 | 0.98 % |
| 8 (1st axial) | 1295.45 | 1294.50 | **0.07 %** |

Modes 1/2 and 3/4 degenerate as expected (square cross-section). 10 modes extracted cleanly; PARTICIPATION FACTORS + EFFECTIVE MODAL MASS available in the `.dat` file. FRD file (2 MB) carries per-mode displacement field for visualization + MAC computation in slice B.

**Conclusion: slice A is technically de-risked. Proceeding.**
