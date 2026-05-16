# FM-04a Phase 16 — Drift Attribution as Cross-Surface Primary Statistic

> **Tier 1 engineering candidate; not signed validation; not benchmark agreement.**

**Status:** Active. Extends the Phase 15 C `drift_attribution` SSOT surface (currently consumed by 2 envelopes — `trust-score-alerts` 1.1.0 + `trust-score-timeline` 1.1.0) to **4 envelopes**, turning cross-axis-comparable percentage delta into a first-class consumer-surface signal across the reviewer journey. Adds (1) CUMULATIVE multi-snapshot drift to the timeline (spanning snap-1 → snap-N, beside the existing consecutive-pair `inter_snapshot_drift_attribution`), (2) COHORT-SCOPED drift attribution on `cohort-anomalies` (alongside the existing z-score view), (3) SIGNOFF-RECORD drift snapshot at write time (closing the audit-trail gap between "WHAT regressed" and "WHO judged it"). Closes Phase 15 retrospective items §3 / §4 / §6 (drift on more envelopes / cohort-scoped percentage delta / cross-axis-comparable cohort signal).

**Author:** Local Claude Opus 4.7 under direct-execution authorization, mirroring Phase 10 / 11 / 12 / 13 / 14 / 15 protocol (binding 9-axis rubric + per-slice 6-axis sub-rubric + independent TAA gating). User authorization 2026-05-17 (verbatim, second invocation): "作为总负责人，构建下一个阶段的蓝图，我授权你全权开发，一直瞄准蓝图执行，要有一套专门的测试agent（对抗测试、测评），有明确的完成度评分机制（要绝对诚实客观），一直迭代开发下去，直至达到你眼里的优秀水准（99分以上）".

**Branch:** `claude/FM-04a-tier1-ballistic-candidate`. Local-only; no pushes; no PRs; no Linear / Notion writes.

**Hard constraints (inherited from Phase 11-15, NON-NEGOTIABLE):**
* Tier 1 disclaimer trio stamped on every new envelope.
* 9 forbidden tokens (`validated against / perforation completed / bullet-through-steel complete / validated physics / production ready / certified / approved for service / asme compliant / signed off`) refused outside `not <claim>` / `no <claim>` form.
* HF1.7a signed-registry hard-stop preserved (Phase 13 D `_SIGNED_REGISTRY_RE` + Phase 13 E `_SIGNED_REGISTRY_PREFIX_RE` defense in depth).
* HF1.7b `*-candidate` carve-out IN FORCE — no override needed for new fixture writes.
* HF1.8 path-guard self-protection: any modification requires explicit AR/ADR cover or override-with-reason.
* Cross-route signed-registry refusal SSOT (Phase 14 A) preserved: every new `/{case_id}` route MUST call `assert_not_signed_registry`.
* No real OpenRadioss / real LLM API calls. The Phase 15 A explicit_dynamics fixture trio remains synthetic-with-analytical-cross-check; no new candidate-case authoring in Phase 16.
* LLM-offline-first preserved.
* AI is advisor, NOT driver: 4-question gate audits preserved.
* No new candidate cases (Phase 15 A delivered 2; the 5-case cohort SSOT from Phase 15 D Journey 2 is the stable cohort surface).

---

## 1. North Star (1 sentence)

**Lift `drift_attribution` from a per-case surface (alerts + timeline) to a CROSS-SURFACE primary statistic by adding cumulative-arc drift on the timeline + cohort-scoped drift on cohort-anomalies + signoff-time drift snapshot on signoff records, so a reviewer asking "which axis regressed and when did the reviewer judge it" gets a single coherent answer across 4 envelopes.**

---

## 2. Closes these gaps

### From Phase 15 retrospective:
* **§3 (carry-forward)** — `drift_attribution` rendered on more than alerts + timeline. The Phase 15 C surface ships in only 2 envelopes; the cohort-scoped surfaces (`cohort-anomalies`, `cohort-trend-anomalies`, `signoff-history`) carry adjacent reviewer information but NOT the cross-axis-comparable percentage view. Phase 16 wires drift_attribution into 2 of those 3 (cohort-anomalies + signoff_record). The `cohort-trend-anomalies` extension is intentionally deferred to a future phase because trend slopes are a different statistic (axis-weighted-score-per-snapshot SLOPE vs per-pair-percentage DELTA); conflating them would over-broaden Phase 16's thesis.
* **§4 (carry-forward)** — per-axis percentage delta on `axis_deltas`-bearing surfaces beyond alerts + timeline. Phase 16 B addresses the cohort scope; the per-case axis_deltas surface on alerts already carries the percentage view (Phase 15 C).
* **§6 (carry-forward)** — cross-axis percentage delta as a scaling axis for cohort-anomalies. Phase 16 B adds the percentage view AS AN ADDITIVE FIELD beside the existing z-score view (NOT a replacement). Reviewers get BOTH: z-score outlier (statistical) + percentage delta (cross-axis-comparable engineering signal).
* **§7 + §8** — small SSOT consolidations in test code (8-token forbidden tuple + `_assert_tier1_trio` helper) bundled into Phase 16 D as janitorial tidy-up.

### What Phase 16 EXPLICITLY does NOT do:
* Real OpenRadioss / CalculiX `*DYNAMIC` solve (Phase 15 retro §1; same Tier 1 posture rule as Phase 14/15).
* Real-LLM advisor branch (Phase 15 retro §2; requires live LLM endpoint).
* Visual dev-server smoke (Phase 12 §2; requires running browser).
* New candidate cases / new analysis types (the 4 analysis types are substantiated; the cohort SSOT is stable).
* Cohort-trend-anomalies drift attribution extension (deferred — trend slope is a different statistic).
* FM-04b prerequisite work (`^GS-\d{3}$` signed-registry remains untouched).
* Push / PR / Linear / Notion writes.

---

## 3. Slice plan

### Slice A — Cumulative drift attribution on TrustScoreTimeline

**Goal:** Add `cumulative_drift_attribution: DriftAttribution | None` field to `TrustScoreTimeline` carrying the **snap-1 → snap-N** transition (vs the existing `inter_snapshot_drift_attribution: tuple[DriftAttribution, ...]` which carries N-1 consecutive-pair transitions). For a 1-point timeline: `cumulative_drift_attribution = None`. For a 2-point timeline: `cumulative_drift_attribution` equals the single inter-snapshot entry (degenerate but correct). For 3+ points: cumulative spans first-to-last.

**Deliverables:**
* `backend/app/services/reporting/trust_score_timeline.py` — new field on `TrustScoreTimeline` dataclass (default `None`); computed in `build_trust_score_timeline` from the first + last timeline points via the existing `compute_drift_attribution` helper (NO new percentage math; consumer of Phase 15 C SSOT).
* MINOR bump `TRUST_SCORE_TIMELINE_SCHEMA_VERSION` 1.1.0 → 1.2.0 with bump-history docstring citing "additive cumulative_drift_attribution field, back-compat with 1.1.0 readers (ignored as unknown JSON field)".
* JSON rendering — `cumulative_drift_attribution` rendered as `null` when None, as a `render_drift_attribution_dict` payload otherwise.
* New methodology paragraph in `.planning/methodology/trust_score_drift_attribution.md` documenting the cumulative vs per-pair distinction.
* ~10 tests:
    * Boundary pins: 3-snapshot leak arc → `cumulative_drift_attribution.dominant_axis == "energy_audit"` with `dominant_delta_pct == -100.0` exactly (snap-1 energy 15 → snap-3 energy 0 = -100% cumulative).
    * 1-point timeline → `cumulative_drift_attribution is None`.
    * 2-point timeline → `cumulative_drift_attribution` equals the single inter-snapshot entry's percentages.
    * Schema-version pin at 1.2.0.
    * Tier 1 trio preserved on envelope.
    * Forbidden-token grep clean.
    * Defensive parser raises on degenerate cases (negative cumulative axis values, etc.).

**Binding sub-rubric (slice A):** M ≥10/12, T ≥10/15, C ≥10/12, A ≥6/8, E ≥7/8, V ≥7/8.

---

### Slice B — Cohort-scoped drift attribution + wiring into cohort-anomalies

**Goal:** Introduce a cohort-scoped aggregation of per-case `DriftAttribution` and wire it as an ADDITIVE field on `cohort-anomalies` envelope alongside the existing z-score view. The cohort-anomalies surface already walks every `*-candidate/` case for z-score outlier detection; Phase 16 B adds a parallel walk that computes per-case drift_attribution for the latest 2 snapshots and aggregates into a `CohortDriftAttribution` envelope-level summary.

**Deliverables:**
* New SSOT module `backend/app/services/reporting/cohort_drift_attribution.py` exposing:
    * `COHORT_DOMINANT_AXIS_FLOOR_PCT: float = 5.0` — module-level, typed, named SSOT floor (parallel to per-case `DRIFT_DOMINANT_AXIS_DELTA_FLOOR_PCT`; can be tuned independently if cohort-scale noise differs from per-case; same 5.0 default with bump-policy mirroring).
    * `CohortDriftAttribution` frozen dataclass: `per_case_drift_attribution: tuple[DriftAttribution, ...]` + `cohort_dominant_axis: str | None` (the axis with the largest absolute delta_pct across ANY case in the cohort) + `cohort_max_abs_delta_pct: float` (the magnitude on that axis-case pair) + `dominant_case_id: str | None`.
    * `compute_cohort_drift_attribution(prev_snap_label, curr_snap_label, *, repo_root, dominant_floor_pct=COHORT_DOMINANT_AXIS_FLOOR_PCT) -> CohortDriftAttribution` — walks `golden_samples/*-candidate/` (signed-registry filtered), computes per-case drift_attribution via the Phase 15 C helper, aggregates.
    * `render_cohort_drift_attribution_dict(att) -> dict` — JSON helper.
* `cohort_anomalies.py` builder — wire new field `cohort_drift_attribution: CohortDriftAttribution | None` on `CohortAnomaliesReport` (None when fewer than 2 snapshots exist; otherwise computed from latest 2 snapshot labels). Renders as additive JSON field. Z-score surface preserved (additive, not replacement).
* MINOR bump `COHORT_ANOMALIES_SCHEMA_VERSION` 1.0.0 → 1.1.0 with bump-history.
* New methodology doc `.planning/methodology/cohort_drift_attribution.md` documenting the per-case → cohort aggregation, the 5.0% floor's independent tunability, and "what the cohort surface does NOT do" (no root-cause analysis; not Tier 2 promotion).
* ~15 tests:
    * M:-2 SSOT constant pins (floor=5.0, typed, named; bump-history docstring present).
    * T:-3 boundary pin: a leak-case-dominant cohort where 4/5 cases are full-credit + 1 leak case is energy-collapsed → `cohort_dominant_axis == "energy_audit"` + `dominant_case_id == LEAK_CASE_ID` + `cohort_max_abs_delta_pct == 100.0`.
    * A:-2 defensive parser raises on (a) cohort size 0; (b) prev_snap_label > curr_snap_label (anti-chronological); (c) snapshot label with signed-registry shape; (d) non-positive floor.
    * C:-1 Tier 1 trio preserved on `cohort-anomalies` envelope.
    * C:-8 forbidden-token grep clean on new module + methodology doc.
    * Schema-version pin at 1.1.0 with bump-history docstring.
    * Live ASGI integration test: `GET /api/v1/cohort-anomalies` carries the new `cohort_drift_attribution` field with energy_audit dominant.
    * Back-compat smoke: a hypothetical 1.0.0 reader ignoring unknown fields still parses; z-score view still emits at the same path.

**Binding sub-rubric (slice B):** M ≥10/12, T ≥10/15, C ≥10/12, A ≥6/8, E ≥7/8, V ≥7/8.

---

### Slice C — Drift attribution captured at signoff write time

**Goal:** Extend `write_signoff_record` to capture the per-case `drift_attribution` for the case's latest 2 snapshots AT WRITE TIME, embedded in the signoff record. Closes the audit-trail gap: 3 months from now a reviewer reading "Watching" signoff sees which axis was regressing AT THE TIME of the verdict, NOT recomputed from the live snapshot tree (which may have evolved past the signoff event).

**Deliverables:**
* `backend/app/services/reporting/signoff_record.py` — extend `write_signoff_record` to:
    1. Compute the per-case drift_attribution for the case's latest snapshot pair (via `build_trust_score_timeline` + the timeline's `inter_snapshot_drift_attribution[-1]`).
    2. Embed under `drift_attribution_at_signoff_time` field (None when fewer than 2 snapshots exist for the case).
    3. Persist alongside the existing verdict / notes / UTC / reviewer fields.
* MINOR bump `SIGNOFF_RECORD_SCHEMA_VERSION` 1.0.0 → 1.1.0 with bump-history.
* `build_signoff_history_report` — surface the field on the `records` list.
* ~12 tests:
    * Write a signoff after the Phase 15 B 3-snapshot arc → record carries `drift_attribution_at_signoff_time.dominant_axis == "energy_audit"` with `dominant_delta_pct == -100.0` on the snap-2→snap-3 transition pin.
    * Write a signoff on a fresh case with no snapshots → field is `None` (gracefully degrade, NOT raise).
    * Write a signoff on a 1-snapshot case (no prior pair) → field is `None`.
    * Schema-version pin at 1.1.0.
    * Defensive parser raises on (a) malformed prior signoff record (back-compat 1.0.0 → 1.1.0 reading).
    * Tier 1 trio preserved on `signoff-history` GET envelope.
    * Forbidden-token grep clean.
    * A:-2 cross-route signed-registry refusal SSOT preserved on POST.
    * E:-2 no real-solver invocation.

**Binding sub-rubric (slice C):** M ≥10/12, T ≥10/15, C ≥10/12, A ≥6/8, E ≥7/8, V ≥7/8.

---

### Slice D — Two E2E reviewer journeys + SSOT consolidation tidy-up

**Goal:** Two end-to-end reviewer journeys exercising the new 3-envelope drift_attribution surface, exactly as a real reviewer would, with assertions on each envelope. PLUS small SSOT consolidation closing Phase 15 retro §7 + §8 (hoist 8-token forbidden tuple + `_assert_tier1_trio` helper to a shared test utility).

**Deliverables:**

* `tests/_test_utils/__init__.py` — new shared utility module exposing:
    * `FORBIDDEN_POSITIVE_CLAIM_TOKENS_8: tuple[str, ...]` — the 8-tuple skipping `certified` (CLAIM_BOUNDARY variants legitimately use `not_signed_validation_or_certified_simulation`).
    * `FORBIDDEN_POSITIVE_CLAIM_TOKENS_9: tuple[str, ...]` — the 9-tuple including `certified` for source-file grep.
    * `assert_tier1_trio(envelope, *, check_impact=True)` helper (matches Phase 15 D Journey 1 strict version when `check_impact=True`; matches Journey 2 loose version when `check_impact=False`).
    * `assert_no_forbidden_positive_claims(text, *, allow_no=True)` helper that strips backticks/quotes and accepts `not <claim>` / `no <claim>` form.

* `tests/test_phase16_journey_drift_audit_trail.py` (new, 12+ tests):
    * Reviewer reads `cohort-anomalies` → sees leak case in z-score outliers AND `cohort_drift_attribution.cohort_dominant_axis == "energy_audit"` (Phase 16 B field).
    * Reviewer reads `trust-score-timeline/<leak>` → sees 3 snapshots + `inter_snapshot_drift_attribution` (Phase 15 C, 2 entries) + `cumulative_drift_attribution` (Phase 16 A, 1 entry naming energy_audit).
    * Reviewer POSTs a `watching` signoff on the leak case with a notes string referencing the drift event.
    * Reviewer reads `signoff-history/<leak>` → sees the new record with `drift_attribution_at_signoff_time.dominant_axis == "energy_audit"` + `dominant_delta_pct == -100.0` (Phase 16 C field; snap-2→snap-3 transition).
    * Crosses **4 distinct routes** (cohort-anomalies → trust-score-timeline → signoff-history POST → signoff-history GET).
    * Anti-gaming: per-route 422-refusal on `GS-001` for each parameterized route.

* `tests/test_phase16_journey_cumulative_vs_consecutive_drift.py` (new, 10+ tests):
    * Reviewer reads `trust-score-timeline/<leak>` → asserts the per-pair `inter_snapshot_drift_attribution[0]` (snap-1→snap-2) names `energy_audit` as dominant with `dominant_delta_pct == -100.0` AND the cumulative `cumulative_drift_attribution` ALSO names `energy_audit` as dominant with the SAME -100.0 magnitude (because the energy axis dropped at snap-2 and stayed at 0 through snap-3).
    * Reviewer reads `trust-score-timeline/<canonical>` (the healthy case across 3 snapshots) → asserts `inter_snapshot_drift_attribution` entries all have `dominant_axis = None` (sub-floor uniform drift) AND `cumulative_drift_attribution.dominant_axis = None` (no axis exceeded 5% cumulative).
    * Crosses **2 distinct routes** × multiple cases = ≥5 (route, case) tuples.
    * Asserts the **invariant**: when an axis collapses in a single transition AND stays at floor, the cumulative `dominant_delta_pct` equals the per-pair `dominant_delta_pct` (within float precision).

* SSOT consolidation refactor:
    * `tests/test_phase15_journey_explicit_dynamics_drift_triage.py` (Phase 15 D Journey 1): replace inline `_assert_tier1_trio` + inline 8-tuple with imports from `tests._test_utils`.
    * `tests/test_phase15_journey_cross_axis_cohort_comparison.py` (Phase 15 D Journey 2): same.
    * `tests/test_phase15_trust_score_drift_attribution.py` (Phase 15 C): same forbidden-token grep helper.
    * Meta-test in `tests/_test_utils/__init__.py` enforces: no Phase 15+ test file inlines the 8-token list; the shared helper is imported.

**Binding sub-rubric (slice D):** M ≥10/12, T ≥10/15, C ≥10/12, A ≥6/8, E ≥7/8, V ≥7/8.

---

### Slice E — STATE refresh + retrospective + FINAL whole-arc TAA

**Goal:** Close Phase 16 with the same protocol as Phase 10 / 11 / 12 / 13 / 14 / 15.

**Deliverables:**
* `.planning/STATE.md` refresh with the Phase 16 closure stamp.
* `.planning/retrospectives/fm04a_phase16_drift_attribution_cross_surface.md` (new) following the Phase 15 retrospective format.
* `.planning/phase16_audit_reports/{A,B,C,D}.md` archived (4 per-slice TAA reports).
* `.planning/phase16_audit_reports/FINAL.md` archived (whole-arc TAA).
* Phase 16 stop condition: **≥99/100 AND every axis ≥95% of weight**.

---

## 4. Binding rubric (whole-arc)

9-axis cumulative scoring, same as Phase 11 / 12 / 13 / 14 / 15:

| Axis | Weight | Description |
|---|---|---|
| B | 12 | Blueprint discipline: full Phase 16 scope shipped; no scope creep |
| M | 12 | Methodology: SSOTs typed/named; methodology docs cite identifiers |
| T | 15 | Tests: per-slice floors met; distinct behaviors |
| C | 12 | Coverage: Tier 1 disclaimer trio on every envelope; forbidden-token grep clean |
| X | 12 | Cross-cutting anti-gaming + defensive parsers (slice B cohort defensive parser + slice C signoff write-time defensive parser) |
| D | 8 | Slice disposition matrix completeness |
| A | 8 | Anti-gaming guards exercised per slice |
| E | 8 | Full sweep green; no real-solver/LLM calls |
| V | 13 | TAA evidence quality |
| **Total** | **100** | |

**Anti-gaming guards (whole-arc):**
* **M:-2** — every new constant is named + module-level + typed (`COHORT_DOMINANT_AXIS_FLOOR_PCT`, schema-version bumps with bump-history docstrings; consumers IMPORT helpers — no inline percentage math).
* **T:-3** — boundary-pinned tests: cumulative drift on leak arc = -100.0% exactly; cohort_dominant_axis pins to LEAK_CASE_ID + "energy_audit"; signoff-record drift captures -100.0 at snap-2→snap-3.
* **T:-4** — back-compat smoke pinning that a 1.0.0 / 1.1.0 reader ignoring unknown fields parses 1.2.0 / 1.1.0 envelopes (additive-field discipline preserved across 3 schema bumps).
* **C:-8** — no Tier-2-promoting language in any new module; forbidden-token grep clean on all new modules + methodology docs + journey envelopes.
* **A:-2** — `compute_cohort_drift_attribution` defensive parser raises on (a) cohort size 0; (b) anti-chronological snapshot labels; (c) signed-registry case_ids; (d) non-positive floor.
* **A:-3** — `drift_attribution_at_signoff_time` is COMPUTED at write time from the live snapshot tree, NOT trusted from a client-supplied field on the POST body. The POST body MUST NOT carry a client-side `drift_attribution_at_signoff_time` — the server computes it.
* **X:-2** — slice-A schema bump (TRUST_SCORE_TIMELINE 1.1.0 → 1.2.0), slice-B schema bump (COHORT_ANOMALIES 1.0.0 → 1.1.0), slice-C schema bump (SIGNOFF_RECORD 1.0.0 → 1.1.0) all carry bump-history docstrings naming Phase 16 + the additive field; back-compat pinned by test.
* **E:-2** — Phase 14 cross-route signed-registry refusal SSOT exercised in slice D's anti-gaming pin (per-route 422 regression guard on `GS-001` across every route the journey touches, including the Phase 16 C signoff POST path).
* **V:-2** — each per-slice TAA runs at least 2 adversarial probes; FINAL TAA runs ≥3 mandatory + ≥3 extra (matching Phase 15 FINAL TAA protocol).

---

## 5. Out of scope

* Real OpenRadioss / CalculiX invocation — explicit_dynamics fixture trio remains synthetic-with-analytical-cross-check (Phase 15 retro §1 carry-forward; same Tier 1 posture rule).
* Real-LLM advisor for any axis — Phase 15 retro §2 carry-forward; still requires live LLM endpoint.
* Visual dev-server smoke of any cohort dashboard component — Phase 12 §2 carry-forward; still requires browser.
* New analysis types beyond the existing 4 — `ANALYSIS_TYPE_TUPLE` remains the substantiated set.
* `cohort-trend-anomalies` drift attribution extension — deferred to a future phase because trend slopes are a different statistic (axis-weighted-score-per-snapshot SLOPE vs per-pair-percentage DELTA); conflating them would over-broaden Phase 16's thesis.
* FM-04b prerequisite work (`^GS-\d{3}$` signed registry remains untouched).
* Any push / PR / Linear / Notion writes.
* New candidate cases or new candidate fixtures (the 5-case cohort SSOT from Phase 15 D Journey 2 is stable).

---

## 6. Acceptance criteria (FINAL TAA gate)

Phase 16 closes when:
1. Slices A-D all ship with their binding sub-rubric scores met.
2. Slice E archives the retrospective + STATE refresh.
3. FINAL whole-arc TAA returns ≥99/100 with every axis ≥95% of weight.
4. All hard constraints PASS (HF1 guard, forbidden-token grep, Tier 1 disclaimer trio, cross-route signed-registry refusal SSOT).
5. Phase 15 retrospective §3 / §4 / §6 / §7 / §8 carry-forwards are explicitly CLOSED.
6. `drift_attribution` surface lands on **4 envelopes** total (alerts 1.1.0 + timeline 1.2.0 + cohort-anomalies 1.1.0 + signoff-record 1.1.0) with MINOR schema bumps documented in bump-history docstrings.
7. Backend test count >= 2457 + slice deliverable floors; frontend test count >= 135.

---

## 7. Test Auditor Agent (TAA) protocol

Per-slice TAA — same protocol as Phase 14/15:
* Independent general-purpose agent, no prior knowledge of the implementation conversation.
* Reads the slice's deliverables, runs the slice tests, runs the full backend sweep.
* Performs ≥2 adversarial probes (suggested probes documented in the TAA prompt; revert any temporary modifications).
* Scores against the 63-point per-slice sub-rubric (M 12 / T 15 / C 12 / A 8 / E 8 / V 8).
* Writes the verdict to `.planning/phase16_audit_reports/{A,B,C,D}.md`.
* Stop condition per slice: ≥60/63 AND every axis ≥ binding floor → APPROVE; otherwise REQUEST_CHANGES.

FINAL whole-arc TAA — same protocol as Phase 14/15 FINAL TAA:
* Independent general-purpose agent, no prior knowledge of the implementation conversation, did NOT author per-slice audits.
* Reads the blueprint + all per-slice audits + the codebase + the retrospective.
* Performs ≥3 mandatory + ≥3 extra adversarial probes (revert any modifications).
* Scores against the 100-point 9-axis whole-arc rubric.
* Writes the verdict to `.planning/phase16_audit_reports/FINAL.md`.
* Stop condition: ≥99/100 AND every axis ≥95% of weight → APPROVE; otherwise REQUEST_CHANGES with concrete bullets per axis below floor.

---

## 8. Open questions (none)

The blueprint thesis (extend drift_attribution to 4 envelopes) is bounded; each schema bump is additive (back-compat preserved by readers ignoring unknown fields); the 5-case cohort SSOT from Phase 15 D Journey 2 is reused (no new fixture authoring); all 3 new schema bumps target existing version constants (no new schema files). No open design questions; ready to execute slice A.
