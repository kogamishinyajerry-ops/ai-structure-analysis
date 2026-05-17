# FM-04a Phase 17 Blueprint — Drift Surface Maturity (Cumulative + Trend Extensions)

**Tier:** Tier 1 engineering candidate; not signed validation; not benchmark agreement.

**Authorization:** Total-responsibility authorization (2026-05-17, third invocation of the verbatim Chinese authorization shape used for Phases 15 and 16): "作为总负责人，构建下一个阶段的蓝图，我授权你全权开发，一直瞄准蓝图执行，要有一套专门的测试agent（对抗测试、测评），有明确的完成度评分机制（要绝对诚实客观），一直迭代开发下去，直至达到你眼里的优秀水准（99分以上）" — full-scope development authority + blueprint-driven execution + dedicated adversarial test agent + absolutely honest scoring + iterate until ≥99/100.

**Direct prerequisite:** FM-04a Phase 16 closure (`8f0091d`, 2026-05-17), which bound `drift_attribution` as a cross-surface primary statistic across 4 envelopes (alerts + timeline-per-pair + timeline-cumulative + cohort-anomalies-latest-pair + signoff-record-latest-pair).

**Hard non-negotiable constraints** (PRESERVED VERBATIM from Phases 14 / 15 / 16):
* Tier 1 engineering candidate; not signed validation; not benchmark agreement.
* Never touch `^GS-\d{3}$` signed-registry entries.
* Never write inside `golden_samples/**` except `*-candidate` directories.
* HF1.7a signed-registry hard-stop preserved; HF1.7b `*-candidate` carve-out IN FORCE; HF1.8 path-guard self-protection preserved.
* Cross-route signed-registry refusal SSOT (Phase 14 A) honored on every reviewer-facing route (including any new POST surface).
* No real OpenRadioss / no real LLM API calls (CI synthetic-only). LLM-offline-first preserved.
* AI is advisor, NOT driver: 4-question gate audits preserved (`llm_offline_ok` / `artifacts_user_owned` / `trustgate_explains` / `advisor_only`).
* No push, no PR, no Linear writes, no Notion writes.
* No new candidate cases (Phase 15 A delivered 2; 5-case cohort SSOT from Phase 15 D Journey 2 is stable and inherited; Phase 16 D used it as-is).
* 9 forbidden positive-claim tokens refused outside `not <claim>` / `no <claim>` form: `validated against / perforation completed / bullet-through-steel complete / validated physics / production ready / certified / approved for service / asme compliant / signed off`.
* Tier 1 disclaimer trio enforced on every 200 envelope via SSOT `tests._test_utils.assert_tier1_trio`.

---

## 1. Thesis

Phase 16 bound `drift_attribution` across 4 envelopes at the **latest snapshot pair** (snap-N-1 → snap-N) view. The timeline envelope ALSO carries the **cumulative** view (snap-1 → snap-N) via Phase 16 A's `cumulative_drift_attribution`. Phase 17 completes the maturity arc by binding the cumulative view to the **two cohort + signoff consumers** that today only carry the latest-pair view, AND by adding a **percentage-of-axis-weight** view to the trend-slope statistic on the cohort-trend-anomalies envelope (which today reports slopes in raw weighted-axis-points, NOT cross-axis comparable).

The post-Phase-17 reviewer surface answers FOUR distinct drift questions simultaneously across 5 envelopes:

| Question | Statistic | Envelope (consumer) | Pre-Phase-17 | Post-Phase-17 |
|---|---|---|---|---|
| Where did the case drift on the LATEST pair? | snap-(N-1) → snap-N axis %-delta | trust-score-alerts + trust-score-timeline (per-pair) | ✓ (Phase 15 C) | ✓ |
| Where did the case drift across the WHOLE arc? | snap-1 → snap-N axis %-delta | trust-score-timeline (cumulative) | ✓ (Phase 16 A) | ✓ |
| Which case dominated cohort-wide drift on the LATEST pair? | per-case latest-pair → cohort max abs %-delta | cohort-anomalies (`cohort_drift_attribution`) | ✓ (Phase 16 B) | ✓ |
| Which case dominated cohort-wide drift across the WHOLE arc? | per-case cumulative → cohort max abs %-delta | cohort-anomalies (`cohort_cumulative_drift_attribution`) | ✗ | ✓ (Phase 17 A) |
| What was drifting at signoff time on the LATEST pair? | server-computed signoff pin (latest pair) | signoff-record | ✓ (Phase 16 C) | ✓ |
| What had drifted across the WHOLE arc at signoff time? | server-computed signoff pin (cumulative) | signoff-record (`cumulative_drift_attribution_at_signoff_time`) | ✗ | ✓ (Phase 17 B) |
| Which axes are trending down across the arc as %-of-weight (NOT raw points)? | least-squares slope → axis-weight %-normalized | cohort-trend-anomalies (`per_axis_percentage_delta_trend`) | ✗ (raw weighted points only) | ✓ (Phase 17 C) |

Phase 17 is **additive only** on three independent envelope schemas. Each consumer gets a MINOR bump + a new optional field + a SSOT helper invocation (no inline math). The existing latest-pair / raw-slope surfaces are preserved (NOT replaced — parallel views).

Phase 17 closes three Phase 16 retrospective carry-forwards directly:
* **§1**: cohort-trend-anomalies per-axis percentage delta surface → Phase 17 C.
* **§2**: multi-pair signoff drift capture (cumulative at signoff in addition to latest pair) → Phase 17 B.
* **§6**: cohort-scoped cumulative drift attribution → Phase 17 A.

---

## 2. Stop condition

A FINAL **whole-arc** Test Auditor Agent (TAA) — independent, never authoring the slices it audits — verifies the Phase 17 arc end-to-end against the 9-axis binding rubric below. The arc is **CLOSED** iff the TAA returns:

> **APPROVE — score ≥ 99 / 100 AND every axis ≥ 95% of weight.**

Both conditions are necessary. A 99/100 with one axis at 92% does NOT close. The TAA's verdict is recorded in `.planning/phase17_audit_reports/FINAL.md`.

Per-slice TAAs (one independent agent per slice A-D) score against the 6-axis sub-rubric (63 pts) below; each slice closes iff its TAA returns APPROVE ≥ 60 / 63 AND every axis ≥ 95% of weight. Sub-rubric failures land in slice retro queue + are addressed before the slice is committed.

---

## 3. Slice plan

### Slice A — Cohort-scoped cumulative drift attribution on `cohort-anomalies`

**Goal:** Add an additive `cohort_cumulative_drift_attribution: object | None` field on the `CohortAnomaliesReport` dataclass, parallel to the Phase 16 B `cohort_drift_attribution` (which spans the latest snapshot pair). The cumulative variant spans the cohort-wide **earliest → latest** snapshot pair.

**Deliverables:**
* Bump `COHORT_ANOMALIES_SCHEMA_VERSION` 1.1.0 → 1.2.0 with bump-history docstring citing Phase 17 A + the additive field.
* Extend `cohort_drift_attribution.py` (the Phase 16 B SSOT module) with a new function `compute_cohort_cumulative_drift_attribution(*, repo_root, dominant_floor_pct=COHORT_DOMINANT_AXIS_FLOOR_PCT)` that walks every `*-candidate/` case, finds the cohort-wide **earliest + latest** snapshot pair (NOT consecutive), and aggregates per-case `DriftAttribution` spanning those two endpoints. Returns `None` when fewer than 2 snapshots exist (graceful degrade, NOT raise — matches the Phase 16 B latest-pair function's contract).
* `CohortAnomaliesReport.cohort_cumulative_drift_attribution` field + `_report_to_dict` serialization (null when None).
* Methodology paragraph appended to `.planning/methodology/cohort_drift_attribution.md` documenting the cohort-cumulative-vs-cohort-latest-pair distinction (parallels the timeline-cumulative-vs-per-pair distinction in `trust_score_drift_attribution.md` from Phase 16 A). Include the "20→10→20 recovery" worked example at cohort scope.
* Tests in `tests/test_phase17_cohort_cumulative_drift_attribution.py`:
  * **M:-1** schema version pin at 1.2.0; bump-history docstring present.
  * **M:-2** consumer of the SSOT helper (NO inline percentage / aggregation math).
  * **T:-3** boundary pins on the 5-case cohort with leak case at energy 15→15→0 (stuck arc): cohort-cumulative `cohort_dominant_axis == "energy_audit"` + `dominant_case_id == LEAK_CASE_ID` + `cohort_max_abs_delta_pct == 100.0` exactly + `from_snapshot == SNAP_1_LABEL` + `to_snapshot == SNAP_3_LABEL`.
  * **T:-4** recovery arc pin (leak 15→0→15): cohort-cumulative `cohort_dominant_axis is None` (sub-floor); cohort-LATEST-pair (Phase 16 B field) still surfaces energy_audit.
  * **T:-5** degenerate cases: 0-snapshot / 1-snapshot → returns None; 2-snapshot → cumulative EQUALS latest-pair (cumulative is between same two endpoints).
  * **A:-2** defensive parser: raises on non-positive floor; returns None on <2 snapshots.
  * **C:-1** Tier 1 disclaimer trio preserved on the cohort-anomalies envelope at 1.2.0 (via SSOT helper).
  * **C:-8** forbidden-token grep on new methodology paragraph + new helper docstring (via SSOT 9-tuple).
  * **V:-3** all snapshot writes under tmp_path; real `reports/snapshots/` byte-identical pre/post run.

**Per-slice TAA scope:** Independent audit verifying M/T/C/A/E/V sub-rubric ≥ 60/63 with every axis ≥ 95%. Probes: cohort-cumulative WOULD trip on `-100.0 → +100.0` sign-flip mutation of helper; recovery-arc invariant; cumulative vs latest-pair returns SAME `DriftAttribution`-shaped dict (cross-envelope coherence).

---

### Slice B — Cumulative `drift_attribution_at_signoff_time` on signoff records

**Goal:** Add an additive `cumulative_drift_attribution_at_signoff_time: object | None` field on the `SignoffRecord` dataclass, parallel to the Phase 16 C `drift_attribution_at_signoff_time` (which captures the latest pair). The cumulative variant captures the full arc snap-1 → snap-N at signoff time.

**Deliverables:**
* Bump `SIGNOFF_RECORD_SCHEMA_VERSION` 1.1.0 → 1.2.0 with bump-history docstring.
* New server-side helper `_compute_cumulative_drift_attribution_at_signoff_time(case_id, *, repo_root)` in `signoff_record.py` that builds the timeline and returns `timeline.cumulative_drift_attribution` (Phase 16 A field) or None. Sister to the Phase 16 C `_compute_drift_attribution_at_signoff_time` helper.
* `SignoffRecord.cumulative_drift_attribution_at_signoff_time` field + `_record_to_dict` serialization + `_parse_drift_attribution` back-compat reader extended to also parse the cumulative key (NaN → None handling preserved).
* **A:-3 LOAD-BEARING SERVER-COMPUTED PIN** (PRESERVED): `write_signoff_record` signature accepts NO `cumulative_drift_attribution_at_signoff_time` parameter. Pinned by `inspect.signature` test (matching the Phase 16 C pattern for the latest-pair field). The signoff POST request body has no path to forge either drift field.
* Tests in `tests/test_phase17_signoff_cumulative_drift_capture.py`:
  * **M:-1** schema version pin at 1.2.0.
  * **T:-3** boundary pin: after 3-snapshot stuck arc (15→15→0), signoff captures `cumulative_drift_attribution_at_signoff_time.dominant_axis == "energy_audit"` + `dominant_delta_pct == -100.0` + `from_snapshot == SNAP_1_LABEL` + `to_snapshot == SNAP_3_LABEL`. Latest-pair pin (Phase 16 C) also surfaces energy_audit with -100.0 (snap-2 → snap-3 = 15→0 in this arc shape — DIFFERENT from Phase 16 C's arc shape where snap-2 was already at 0).
  * **T:-4** recovery arc pin: cumulative captured at signoff is None (sub-floor); latest-pair captured at signoff surfaces energy_audit (or its sign-flipped recovery counterpart, depending on the 5% floor crossing).
  * **A:-3** `inspect.signature(write_signoff_record)` audit — `cumulative_drift_attribution_at_signoff_time` NOT in parameters; forged-kwarg raises TypeError.
  * **D:-1** round-trip JSON preservation (write + re-read parses both drift fields).
  * **D:-2** back-compat: pre-1.2.0 on-disk records (carrying only the Phase 16 C latest-pair field) read as `cumulative_drift_attribution_at_signoff_time = None`.
  * **C:-1** Tier 1 disclaimer trio on the signoff history envelope at 1.2.0.

**Per-slice TAA scope:** Verifying server-computed posture is preserved on BOTH drift fields (latest-pair from Phase 16 C + cumulative from Phase 17 B). Probes: forge each kwarg independently → TypeError on both; corrupted JSON → graceful degrade on both; helper renames don't silently drop a field.

---

### Slice C — Per-axis percentage-of-axis-weight slope on `cohort-trend-anomalies`

**Goal:** Add an additive `per_axis_percentage_delta_trend: dict[str, float] | None` mapping on the `TrendEvent` dataclass (and propagated via `_report_to_dict`). Today the trend-anomalies surface reports raw weighted-axis-point slopes (e.g., -2.5 means "axis drops 2.5 weighted points per snapshot"); Phase 17 C adds a parallel view normalizing the slope to **percentage of the axis's total weight** per snapshot (e.g., -2.5 weighted-point slope on the 15-point energy axis → -16.7% per snapshot trend).

**Deliverables:**
* Bump `COHORT_TREND_ANOMALIES_SCHEMA_VERSION` 1.0.0 → 1.1.0 with bump-history docstring citing Phase 17 C + the additive field. The raw `slope` field on `TrendEvent` is preserved (parallel view, NOT replacement).
* Extend `cohort_trend_anomalies.py` with `_percentage_delta_slope(raw_slope: float, axis: str) -> float` helper that normalizes by `TRUST_AXIS_WEIGHTS[axis]` (the Phase 15 C SSOT mapping; completeness=50, convergence=20, energy_audit=15, reproducibility=15) — IMPORTS the SSOT, NO inline weight constants (M:-2 anti-gaming).
* `TrendEvent.percentage_delta_slope: float` field (per-event, NOT per-axis dict — each event already carries one axis; the dict form is unnecessary). Renamed from the blueprint sketch above to keep the event-level granularity.
* `_report_to_dict` renders `percentage_delta_slope` alongside `slope`.
* Methodology doc `.planning/methodology/cohort_trend_anomalies.md` (NEW; this surface had no methodology doc pre-Phase-17): documents the slope-vs-percentage-slope distinction + WHY both are surfaced (raw slope answers "how fast in weighted points?"; percentage slope answers "how fast as a fraction of axis ceiling?" — cross-axis comparable).
* Tests in `tests/test_phase17_trend_percentage_slope.py`:
  * **M:-1** schema version pin at 1.1.0; bump-history docstring present.
  * **M:-2** consumer IMPORTS `TRUST_AXIS_WEIGHTS` from the Phase 15 C SSOT (NOT inline-declared).
  * **T:-3** boundary pin: synthesized 3-snapshot arc with case dropping completeness from 50 → 42 → 34 (raw slope -8, weighted; percentage slope -16.0% per snapshot exactly). Energy axis 15 → 10 → 5 (raw slope -5; percentage slope -33.33% per snapshot exactly to 2 decimals). The percentage values are cross-axis comparable; the raw values are NOT.
  * **T:-4** sign convention: positive slope (recovery) → positive percentage_delta_slope; negative slope (regression) → negative percentage_delta_slope. No sign-flip artifacts from the normalization.
  * **T:-5** axis-coverage pin: every TrendEvent carries percentage_delta_slope for its named axis; the 4 trust axes (completeness / convergence / energy_audit / reproducibility) all produce coherent normalized values.
  * **A:-2** defensive: unknown axis name on the helper raises (since TRUST_AXIS_WEIGHTS is the 4-axis SSOT). Bump-policy: a future axis addition trips the unknown-axis raise.
  * **C:-1** Tier 1 trio preserved on the cohort-trend-anomalies envelope at 1.1.0.

**Per-slice TAA scope:** Verifies the percentage-slope view is cross-axis comparable (a -10% per-snapshot slope on completeness vs energy_audit indicates same relative urgency). Probes: TRUST_AXIS_WEIGHTS substituted with wrong values → trips T:-3 pin; raw slope sign flipped in helper → trips T:-4 pin; bump-history docstring removed → trips M:-1 doc audit.

---

### Slice D — Two E2E reviewer journeys + SSOT consolidation tidy-up

**Goal:** Two end-to-end reviewer journeys exercising the FIVE distinct drift views across the 6-envelope post-Phase-17 surface, plus a small SSOT consolidation closing residual Phase 16 retro deferred items.

**Deliverables:**

**Journey 1 — Five-drift-view audit trail** (`tests/test_phase17_journey_five_drift_views.py`, ≥ 10 tests). Walks **5 distinct route/verb pairs** in a single reviewer pass:
1. `GET /api/v1/trust-score-timeline/{LEAK_CASE_ID}` — pin per-pair drift entries (Phase 15 C) AND cumulative drift (Phase 16 A) both name energy_audit.
2. `GET /api/v1/cohort-anomalies` — pin BOTH `cohort_drift_attribution` (Phase 16 B latest-pair) AND `cohort_cumulative_drift_attribution` (Phase 17 A cumulative) name the leak case as dominant on energy_audit.
3. `GET /api/v1/cohort-trend-anomalies` — pin the leak case's energy-axis trend event carries `slope` (raw, in weighted points) AND `percentage_delta_slope` (Phase 17 C, in %-of-weight) — both negative.
4. `POST /api/v1/signoff-history/{LEAK_CASE_ID}` — issue `needs_more_evidence` signoff; the request body carries NO drift fields (server-computed pattern preserved).
5. `GET /api/v1/signoff-history/{LEAK_CASE_ID}` — pin the new record carries BOTH `drift_attribution_at_signoff_time` (Phase 16 C latest-pair) AND `cumulative_drift_attribution_at_signoff_time` (Phase 17 B cumulative).

Boundary pins (T:-3): in the stuck arc shape (snap-1 clean → snap-2 clean → snap-3 regressed), the cumulative drift across all 4 envelopes lands `dominant_axis == "energy_audit"` + `dominant_delta_pct == -100.0` exactly + `dominant_case_id == LEAK_CASE_ID` exactly (where applicable). Tier 1 trio on every 200 envelope via SSOT. Per-route 422-refusal on GS-001 across all 5 route/verb pairs.

**Journey 2 — Cumulative-vs-latest-pair coherence across cohort + signoff** (`tests/test_phase17_journey_cumulative_coherence.py`, ≥ 10 tests). Pins the invariant: when an arc has a STUCK regression on the latest pair, the cumulative view should ALSO surface that axis (because the regression hasn't recovered); when an arc has a RECOVERY, the cumulative view at cohort + signoff scope BOTH collapse to None while the per-pair / latest-pair views still surface the transient. Pins this on cohort-anomalies (latest vs cumulative) + signoff-history (latest vs cumulative) simultaneously. Two arc shapes (stuck + recovery), each tested through both endpoints.

**SSOT consolidation tidy-up** (closes Phase 16 retro carry-forward — the 5-case cohort fixture-seeding pattern):
* Hoist the 5-case journey fixture seeding helpers (`_healthy_case_input`, `_clean_leak_case_input`, `_regressed_leak_case_input`, `_pv_case_input`) from Phase 15 D Journey 2 + Phase 16 D Journey 1 + (this slice's) Phase 17 D Journey 1+2 to a new shared utility `tests/_test_utils/cohort_fixtures.py`.
* Each existing journey file refactored to import the fixture helpers from the SSOT.
* Meta-test `tests/test_phase17_cohort_fixtures_ssot.py` enforces no Phase 15+ journey file re-inlines the 5-case fixture seeding pattern (lexical detection of `def _healthy_case_input(` / `def _clean_leak_case_input(` / `def _pv_case_input(` not delegating to SSOT).

**Per-slice TAA scope:** Independent audit verifies the 2 journeys exercise the route contract frozensets exactly; the SSOT consolidation is real (NOT just relocation — the meta-test catches future re-inlining); the cumulative-vs-latest invariant trips on either the cohort or signoff surface independently. Probes: cumulative-collapse-to-None invariant on recovery arc; cross-envelope dominant-axis coherence under stuck arc; SSOT meta-test fingerprint detection for cohort-fixture re-inlining.

---

### Slice E — Closure (retrospective + STATE refresh + FINAL whole-arc TAA)

**Goal:** Archive the Phase 17 closure artifacts.

**Deliverables:**
* `.planning/retrospectives/fm04a_phase17_drift_surface_maturity.md` (NEW): scope, per-slice summary with commit SHAs + sub-rubric scores, quantitative outcome table (test surface delta, new schema versions, new SSOT helpers, etc.), what-worked, what-didn't-work, Phase 18 carry-forwards (if any), acceptance criteria checklist, closing posture.
* `.planning/STATE.md` refreshed with Phase 17 closure stamp; Phase 16 narrative preserved below as carry-forward.
* `.planning/phase17_audit_reports/A.md` / `B.md` / `C.md` / `D.md` (per-slice TAA reports, written by each slice TAA during their respective slices).
* `.planning/phase17_audit_reports/FINAL.md` (FINAL whole-arc TAA report).

**FINAL TAA scope:** Independent audit against the 9-axis whole-arc rubric. The TAA reads the blueprint + 4 per-slice reports + retrospective + actual source/tests/docs, runs ≥ 6 adversarial probes (≥ 3 mandatory + ≥ 3 of its own choice), and returns APPROVE / CHANGES_REQUIRED + per-axis scores.

---

## 4. Binding whole-arc 9-axis rubric (100 pts)

The FINAL TAA scores the arc against this rubric. APPROVE iff total ≥ 99 AND every axis ≥ 95% of weight.

| Axis | Weight | What it measures |
|---|---|---|
| **B** Behavior | 12 | Phase 16 retro §1/§2/§6 carry-forwards explicitly closed; cumulative drift surfaces at cohort + signoff scope; percentage-slope view at cohort-trend-anomalies; cross-envelope coherence (5 drift views across 6 envelopes after Phase 17). |
| **M** Module discipline | 12 | All consumers IMPORT helpers (no inline percentage / aggregation / weight constants); schema MINOR bumps documented with `(version → version)` annotations + bump-history docstrings; 3 schema bumps (cohort-anomalies 1.1.0→1.2.0, signoff-record 1.1.0→1.2.0, cohort-trend-anomalies 1.0.0→1.1.0); new + edited methodology docs Tier 1 wording compliant. |
| **T** Tests + boundaries | 15 | `==` boundary pins (NOT `>=` bounds) on -100.0 / 100.0 / "energy_audit" / LEAK_CASE_ID / snapshot labels; cumulative-vs-latest invariant exercised on TWO arc shapes (stuck + recovery); per-axis percentage-slope cross-axis comparability pinned; route contract frozensets; full sweep green (≥ 2527 + slice-deliverable floors). |
| **C** Claim discipline | 12 | Tier 1 disclaimer trio preserved on every 200 envelope; SSOT 8/9-tuple discipline preserved; new methodology docs Tier 1 wording compliant; new fields' renderers handle None gracefully; bump-history docstrings explicit. |
| **X** Cross-route + cross-surface coherence | 12 | All 5 drift views compose cleanly across the 6 post-Phase-17 envelopes (no signature drift between Phase 15 C / Phase 16 / Phase 17 consumers of `DriftAttribution`); per-route signed-registry SSOT helper covers all new route/verb pairs; the cohort-cumulative / signoff-cumulative / trend-percentage views all surface coherent `DriftAttribution`-shaped (or shape-coherent) dicts where applicable. |
| **D** Defensive parsers + back-compat | 8 | `compute_cohort_cumulative_drift_attribution` raises on non-positive floor + returns None on <2 snapshots; signoff `_parse_drift_attribution` handles None / dict / NaN / corrupted JSON for BOTH drift fields; back-compat reader pins all 1.1.0-era fields still present in 1.2.0 (cohort-anomalies + signoff); cohort-trend-anomalies 1.0.0-era fields preserved in 1.1.0. |
| **A** Anti-gaming | 8 | A:-3 server-computed pin preserved on BOTH signoff drift fields (`inspect.signature` audit + forged-kwarg TypeError on each); M:-2 consumers IMPORT helpers (no inline math); strictly-exceed floor semantic on cohort-cumulative at write-time AND test-time AND methodology doc; SSOT meta-test fingerprint detection for cohort-fixture re-inlining; per-route signed-registry refusal honored on new route/verb pairs. |
| **E** Engineering posture | 8 | No real solver / no real LLM; LLM-offline-first preserved; 4-question gate honored; AI advisor-only; all snapshot writes under tmp_path; HF1.7a + HF1.7b + HF1.8 path-guards preserved; cross-route signed-registry refusal SSOT honored. |
| **V** Verification + traceability | 13 | Per-slice TAA reports filed (A/B/C/D); retrospective complete; STATE refreshed with Phase 17 closure stamp; FINAL.md archived; commits trace via `git log` (blueprint + 4 slices + E closure); zero Notion / Linear writes verified. |

**Total:** 100. **Stop:** ≥ 99 AND every axis ≥ 95%.

---

## 5. Per-slice 6-axis sub-rubric (63 pts)

Each per-slice TAA scores the slice against M / T / C / A / E / V (sub-axes of the whole-arc rubric, scoped to the slice). APPROVE iff total ≥ 60 / 63 AND every axis ≥ 95% of weight.

| Axis | Weight | What it measures (per slice) |
|---|---|---|
| **M** Module discipline | 12 | Schema bump documented; helper IMPORTED (no inline math); module docstrings carry Tier 1 + forbidden-wording sentinels. |
| **T** Tests + boundaries | 15 | Boundary pins exact `==` (NOT `>=`); degenerate / recovery / sub-floor cases pinned; slice tests green. |
| **C** Claim discipline | 12 | Tier 1 disclaimer trio preserved on every 200 envelope in slice scope; SSOT 8/9-tuple discipline preserved; new methodology Tier 1 wording compliant. |
| **A** Anti-gaming | 8 | A:-3 server-computed pin (where applicable); M:-2 consumer IMPORTS helper; strictly-exceed floor at write-time AND test-time AND methodology. |
| **E** Engineering posture | 8 | No real solver / no real LLM; tmp_path-only snapshot writes; HF1 preserved; 4-Q gate honored. |
| **V** Verification + traceability | 8 | Slice TAA report filed; commit SHA traced; constraints checklist honored. |

---

## 6. Acceptance criteria

Per blueprint §3 / §4:

- [ ] Slices A-D all ship with their per-slice TAA sub-rubric scores met (≥ 60 / 63 AND every axis ≥ 95%).
- [ ] Slice E archives retrospective + STATE refresh + FINAL TAA report.
- [ ] FINAL whole-arc TAA returns APPROVE ≥ 99 / 100 AND every axis ≥ 95% of weight.
- [ ] All hard constraints PASS (HF1 guards, forbidden-token grep via SSOT, Tier 1 disclaimer trio via SSOT, cross-route signed-registry refusal SSOT including all new route/verb pairs).
- [ ] Phase 16 retro §1 + §2 + §6 carry-forwards explicitly CLOSED.
- [ ] Three additive MINOR schema bumps land cleanly with bump-history docstrings (cohort-anomalies 1.1.0→1.2.0; signoff-record 1.1.0→1.2.0; cohort-trend-anomalies 1.0.0→1.1.0).
- [ ] Backend test count ≥ 2527 + slice deliverable floors; frontend test count ≥ 135 (unchanged — Phase 17 explicitly scopes frontend OUT, matching Phase 12-16 pattern).
- [ ] No `^GS-\d{3}$` registry entries touched; no real solver / no real LLM; tmp_path-only snapshot writes verified.
- [ ] No Linear writes, no Notion writes, no PR opened, no push.

---

## 7. Explicitly out of scope

These are NOT Phase 17 deliverables; they remain Phase 16 retro carry-forwards or earlier carry-forwards:

* **Real OpenRadioss / CalculiX `*DYNAMIC` explicit_dynamics solve** for the leak case (Phase 15 §1 + Phase 16 §3 carry-forwards) — the leak fixture remains SYNTHETIC.
* **Real-LLM advisor referencing drift_attribution** (Phase 15 §2 + Phase 16 §4 carry-forwards) — `LLMAdvisor` remains placeholder with stub fallback.
* **Frontend rendering of drift surfaces** (Phase 15 §3 + Phase 16 §5 carry-forwards) — visual dev-server smoke still requires a browser.
* **Replacing the existing z-score view on cohort-anomalies with percentage-delta as PRIMARY** (Phase 16 §7 carry-forward) — Phase 17 preserves the additive pattern; replacement would break back-compat. Future phase candidate.
* **POST surface on cohort-anomalies + defense-in-depth pins** (Phase 16 §8 carry-forward) — cohort-anomalies has no POST today; adding one is a separate scope. Future phase candidate.
* **Drift-aware advisor stub** (i.e., StubAdvisor branches that prioritize themes by drift dominant axis) — a separate scope that would touch the Phase 11 / 14 C advisor surface. Future phase candidate.
* **Cohort drift digest** (cross-case consolidator naming top-N drifting cases) — a separate envelope surface. Future phase candidate.

---

## 8. Risk register

| Risk | Mitigation |
|---|---|
| Cumulative-vs-latest pair coherence drift between cohort + signoff surfaces | Journey 2 pins the invariant on both endpoints simultaneously; per-slice TAA cross-verifies. |
| Percentage-slope normalization sign convention errors | T:-4 explicitly pins sign coherence (positive raw slope ↔ positive percentage slope). |
| Server-computed posture regression on the new signoff cumulative field | A:-3 `inspect.signature` pin extended to BOTH drift fields; forged-kwarg TypeError tested on both. |
| SSOT cohort-fixture consolidation breaks Phase 15 D / Phase 16 D journey tests during refactor | Slice D consolidation is the LAST slice before closure; runs full sweep after refactor + per-slice TAA verifies; revert path is `git revert` of the consolidation commit. |
| Methodology doc drift from implementation behavior | T:-3 pins exact values; if methodology says "5%" and code says "5.5%", the boundary test trips. Methodology doc audited by slice TAA. |
| Cohort-trend-anomalies surface had no methodology doc pre-Phase-17 | Phase 17 C adds one (slope-vs-percentage-slope distinction); audited by slice TAA. |

---

## 9. Closing scope clarity

Phase 17 is **additive only** across 3 envelope schemas (cohort-anomalies, signoff-record, cohort-trend-anomalies). No existing field deleted. No existing surface replaced. The Phase 16 cross-surface drift binding is the foundation; Phase 17 fills in the cumulative + percentage-slope views that were Phase 16's explicit carry-forwards. Post-Phase-17, the drift surface answers 5 distinct questions across 6 envelopes (alerts per-pair / timeline per-pair / timeline cumulative / cohort latest-pair / cohort cumulative / cohort-trend percentage-slope / signoff latest-pair / signoff cumulative) — the maturity arc is complete.

No `LinkedIn writes` (CFD-harness-unified parlance — flagging the constraint even though it doesn't apply to this project). No Notion writes. No Linear writes. No push. No PR. Nothing leaves the local branch.

Posture: Tier 1 engineering candidate; not signed validation; not benchmark agreement.
