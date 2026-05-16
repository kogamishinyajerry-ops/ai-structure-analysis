# FM-04a Phase 15 — Explicit-Dynamics Cohort Substantiation + Cross-Snapshot Drift Attribution

> **Tier 1 engineering candidate; not signed validation; not benchmark agreement.**

**Status:** Active. Extends Phase 12's modal-cohort treatment pattern to the `explicit_dynamics` axis: adds 2 additional candidate fixtures (a healthy variant + an energy-leak regressed case), wires a 3-snapshot degradation arc, surfaces per-axis drift attribution between consecutive snapshots, and ships 2 reviewer journeys exercising the new cohort surfaces. Closes the parity gap between modal (3 cases / multi-snapshot via Phase 12) and explicit_dynamics (1 case / single snapshot via Phase 14).

**Author:** Local Claude Opus 4.7 under direct-execution authorization, mirroring Phase 10 / 11 / 12 / 13 / 14 protocol (binding 9-axis rubric + per-slice 6-axis sub-rubric + independent TAA gating). User authorization 2026-05-17 (verbatim): "作为总负责人，构建下一个阶段的蓝图，我授权你全权开发，一直瞄准蓝图执行，要有一套专门的测试agent（对抗测试、测评），有明确的完成度评分机制（要绝对诚实客观），一直迭代开发下去，直至达到你眼里的优秀水准（99分以上）".

**Branch:** `claude/FM-04a-tier1-ballistic-candidate`. Local-only; no pushes; no PRs; no Linear / Notion writes.

**Hard constraints (inherited from Phase 11-14, NON-NEGOTIABLE):**
* Tier 1 disclaimer trio stamped on every new envelope.
* 9 forbidden tokens (`validated against / perforation completed / bullet-through-steel complete / validated physics / production ready / certified / approved for service / asme compliant / signed off`) refused outside `not <claim>` form.
* HF1.7a signed-registry hard-stop preserved (Phase 13 D `_SIGNED_REGISTRY_RE` + Phase 13 E `_SIGNED_REGISTRY_PREFIX_RE` defense in depth).
* HF1.7b `*-candidate` carve-out IN FORCE — no override needed for new fixture writes.
* HF1.8 path-guard self-protection: any modification requires explicit AR/ADR cover or override-with-reason.
* Cross-route signed-registry refusal SSOT (Phase 14 A) preserved: every new `/{case_id}` route MUST call `assert_not_signed_registry`.
* No real OpenRadioss / real LLM API calls. The explicit_dynamics fixture trio remains synthetic-with-analytical-cross-check per the Phase 14 D pattern.
* LLM-offline-first preserved.
* AI is advisor, NOT driver: 4-question gate audits.

---

## 1. North Star (1 sentence)

**Substantiate the `explicit_dynamics` axis at the cohort dimension by shipping a 3-snapshot degradation arc across 3 candidate cases (stable → watching → regressed) AND wire per-axis drift attribution into trust-score-alerts / trust-score-timeline so a reviewer reading the cohort timeline can immediately see WHICH axis regressed by HOW MUCH between consecutive snapshots.**

---

## 2. Closes these gaps

### From Phase 14 carry-forwards:
* **Modal vs explicit_dynamics cohort parity gap**. Phase 12 D shipped 3 modal cases (modal-cantilever-candidate / modal-cantilever-stiff-candidate / cylinder-pv-extended-candidate) + a 3-snapshot degradation arc. Phase 14 D shipped ONE explicit_dynamics case (rod-wave-impact-candidate) at a single snapshot. The cohort timeline currently shows no explicit_dynamics axis evolution. Phase 15 closes the parity.

### From Phase 13 retro §1 (carried through Phase 14):
* **Per-axis drift attribution**. Trust-score-alerts fires on bucket-crossing thresholds, but does NOT today surface WHICH AXIS caused the regression. A reviewer reading "case X dropped from healthy to regressed" must currently drill into trust-score-provenance to find the cause; Phase 15 surfaces the per-axis delta directly on the alert envelope. This was implicit in the cohort-bucket-trigger work but never formally substantiated.

### Phase 14 retro §1 (real OpenRadioss invocation), §3 (real-LLM advisor for explicit_dynamics), §4 (visual dev-server smoke) are EXPLICITLY out of scope:
* §1 violates the Tier 1 candidate posture (synthetic-with-analytical-cross-check is the load-bearing rule).
* §3 requires a live LLM endpoint the engineering pass does not have.
* §4 requires a running browser the engineering pass does not have.

---

## 3. Slice plan

### Slice A — Two additional explicit_dynamics candidate fixtures

**Goal:** Add `rod-wave-impact-stiff-candidate` (healthy variant; different material; wave speed still within 5% tolerance band) AND `rod-wave-impact-energy-leak-candidate` (synthetic non-physical energy injection at frame 30 → trips per-frame energy_partition_audit → trust collapses into regressed bucket). Mirrors Phase 12 C modal-cantilever-stiff-candidate + Phase 13 C cylinder-pv-collapsed-candidate authoring pattern.

**Deliverables:**
* `scripts/gen_rod_wave_impact_stiff_deck.py` (new) — emits a stiffer-rod variant (E=210 GPa for tool-steel; rho=7850 unchanged) so wave speed c ≈ 5174 m/s and t_refl ≈ 0.000193 s. Frame_dt is held at 1e-5 s so first_reflection_frame_index = round(193/10) = 19 (observed=190us vs analytical=193.3us; residual 1.71% — still well within the 5% tolerance, healthy).
* `scripts/gen_rod_wave_impact_energy_leak_deck.py` (new) — emits the regressed variant. Identical geometry/material to the canonical candidate, but the animation manifest injects 50% non-physical energy at frame 30 (KE[30] = SE[30] = 1.5x the analytical value; W_ext[30] unchanged → `energy_partition_audit` flags frame 30 with rel_drift = 0.50, well above the 1% ENERGY_PARTITION_DRIFT_FRACTION threshold). The ballistic_metrics emits `energy_audit.status = "open_residual"` so the case_completeness energy_audit axis lands 0 / 15.
* `golden_samples/rod-wave-impact-stiff-candidate/` + `golden_samples/rod-wave-impact-energy-leak-candidate/` (new fixture dirs under the HF1.7b carve-out).
* `tests/test_phase15_rod_wave_impact_stiff_candidate.py` (new, ≥10 tests) — mirrors `tests/test_phase14_rod_wave_impact_candidate.py` test pattern; A:-3 analytical re-derivation MUST land within 5% tolerance.
* `tests/test_phase15_rod_wave_impact_energy_leak_candidate.py` (new, ≥10 tests) — pins the energy-leak frame index + the audit's flagged_frame_indices + the case_completeness scorecard landing BELOW the healthy 80-pt floor (target ~65 because energy_audit axis is 0).

**Binding sub-rubric (slice A):** M ≥10/12, T ≥10/15, C ≥10/12, A ≥6/8, E ≥7/8, V ≥7/8.

**Anti-gaming pin (A:-3 per slice):** the energy-leak fixture's flagged frame index is computed BY THE AUDIT (running `energy_partition_audit` on the parsed manifest), NOT read from the fixture's self-reported `flagged_frame_indices` field. A drifted fixture (leak injected at frame 25 instead of 30) would trip THIS test.

---

### Slice B — Three-snapshot degradation arc across the explicit_dynamics cohort

**Goal:** Multi-snapshot time series for the 3-case explicit_dynamics cohort showing a degradation arc:
* **Snapshot-1** (2026-05-17T10:00:00Z): all 3 cases trust >=80 (healthy).
* **Snapshot-2** (2026-05-17T12:00:00Z): rod-wave-impact-candidate stays healthy; rod-wave-impact-stiff-candidate drifts to watching (50 <= trust < 80); rod-wave-impact-energy-leak-candidate at watching too.
* **Snapshot-3** (2026-05-17T14:00:00Z): rod-wave-impact-candidate stays healthy; rod-wave-impact-stiff-candidate slips further to watching low-edge; rod-wave-impact-energy-leak-candidate at regressed (trust < 50).

Mirrors Phase 12 D's 3-snapshot cylinder-pv-extended arc + Phase 13 C's cylinder-pv-collapsed regressed-bucket trigger.

**Deliverables:**
* `scripts/gen_phase15_explicit_dynamics_cohort_snapshots.py` (new) — emits 3 snapshot directories under `reports/snapshots/2026-05-17T100000Z/`, `2026-05-17T120000Z/`, `2026-05-17T140000Z/` with the explicit_dynamics cohort + filler cases bringing cohort_count to n=5 per snapshot (mirroring Phase 12 D's n=6 pattern).
* `tests/test_phase15_explicit_dynamics_cohort_arc.py` (new, ≥10 tests):
    * 3-snapshot manifest existence + Tier 1 disclaimer trio.
    * Per-snapshot bucket transitions: snap-1 = (3 healthy / 0 watching / 0 regressed); snap-2 = (1 healthy / 2 watching / 0 regressed); snap-3 = (1 healthy / 1 watching / 1 regressed) — `regressed_count >= 1` fires on the leak case at snap-3.
    * Trust-score-timeline route pin: rod-wave-impact-energy-leak-candidate's snap-3 trust strictly < 50 (regressed bucket trigger load-bearing on real fixture math).
    * Trust-score-alerts route pin: snap-3 fires AT LEAST one regressed-bucket alert with rod-wave-impact-energy-leak-candidate named.
    * Cohort-overview route pin: cohort_count + per-bucket counts match the manifest math.

**Binding sub-rubric (slice B):** M ≥10/12, T ≥10/15, C ≥10/12, A ≥6/8, E ≥7/8, V ≥7/8.

---

### Slice C — Cross-snapshot per-axis drift attribution surface

**Goal:** Trust-score-alerts + trust-score-timeline now carry a per-axis `drift_attribution: dict[axis, delta_pct]` field naming which trust axis (completeness / convergence / energy_audit / reproducibility) regressed most between consecutive snapshots, with the per-axis delta as a percentage. A reviewer reading "rod-wave-impact-energy-leak-candidate dropped from snap-2 watching to snap-3 regressed" sees immediately that `drift_attribution = {"energy_audit": -100.0, "convergence": -8.0, ...}` — the energy_audit axis collapsed.

**Deliverables:**
* `backend/app/services/reporting/trust_score_drift_attribution.py` (new) — pure-Python service exposing `compute_drift_attribution(prev_axes, curr_axes) -> DriftAttribution` returning a frozen dataclass with `per_axis_delta_pct: dict[str, float]`, `dominant_axis: str | None`, `dominant_delta_pct: float`. SSOT constants: `DRIFT_DOMINANT_AXIS_DELTA_FLOOR_PCT = 5.0` (only axes whose absolute delta exceeds 5% are considered "dominant"; below that the dominant_axis is None — i.e., the alert is a uniform drift, not an axis-attributed regression).
* `backend/app/services/reporting/_schema_versions.py`:
    * MINOR bump `TRUST_SCORE_ALERTS_SCHEMA_VERSION` 1.0.0 → 1.1.0 (additive `drift_attribution` field).
    * MINOR bump `TRUST_SCORE_TIMELINE_SCHEMA_VERSION` 1.0.0 → 1.1.0 (additive `inter_snapshot_drift_attribution: tuple[DriftAttribution, ...]` field per case).
    * Bump-history docstrings on both.
* `backend/app/services/reporting/trust_score_alerts.py`: when a case crosses a bucket between consecutive snapshots, the alert envelope carries `drift_attribution` for that transition.
* `backend/app/services/reporting/trust_score_timeline.py`: per-case timeline carries inter-snapshot drift attribution for every consecutive snapshot pair.
* `.planning/methodology/trust_score_drift_attribution.md` (new) — SSOT methodology doc citing the 5%-dominant-axis floor + bump-history policy + what the attribution does NOT do (NOT a regression root-cause analysis; ONLY a per-axis delta surface).
* `tests/test_phase15_trust_score_drift_attribution.py` (new, ≥12 tests):
    * Empty prev_axes → all current axes flagged.
    * Uniform drift (every axis -3%) → dominant_axis = None.
    * Axis-attributed drift (one axis collapses, others stable) → dominant_axis names the collapsed axis.
    * Numerical defense: rejects None / negative / non-axis-name keys.
    * Schema version pinned at 1.1.0 for both alerts + timeline.
    * Tier 1 disclaimer trio + 9 forbidden tokens grep clean.
    * Live ASGI: snap-2 → snap-3 transition for rod-wave-impact-energy-leak-candidate has `drift_attribution.dominant_axis == "energy_audit"`.

**Binding sub-rubric (slice C):** M ≥10/12, T ≥10/15, C ≥10/12, A ≥6/8, E ≥7/8, V ≥7/8.

---

### Slice D — Two E2E reviewer journeys exercising the new cohort surfaces

**Goal:** Two end-to-end journey tests that walk the reviewer through the new explicit_dynamics cohort + drift attribution surfaces, exactly as a real reviewer would (multi-route, multi-snapshot, with assertions on the surfaces between each step). Mirrors Phase 12 F's 3-journey pattern.

**Deliverables:**
* `tests/test_phase15_journey_explicit_dynamics_drift_triage.py` (new, 10+ tests):
    * Step 1: GET `/api/v1/cohort-overview/{snap-3-label}` — observe regressed_count >= 1.
    * Step 2: GET `/api/v1/trust-score-alerts/rod-wave-impact-energy-leak-candidate` — observe regressed-bucket alert + `drift_attribution.dominant_axis == "energy_audit"`.
    * Step 3: GET `/api/v1/trust-score-timeline/rod-wave-impact-energy-leak-candidate` — observe 3 snapshots with the snap-2→snap-3 inter-snapshot-drift naming energy_audit.
    * Step 4: GET `/api/v1/case-completeness/rod-wave-impact-energy-leak-candidate?analysis_type=explicit_dynamics` — observe energy_audit axis at 0/15.
    * Step 5: GET `/api/v1/advisor-critique/rod-wave-impact-energy-leak-candidate?snapshot={snap-3}` — observe explicit_dynamics branch + the energy-partition-closure theme cites the audit deviation.
    * Step 6: GET `/api/v1/signoff-history/rod-wave-impact-energy-leak-candidate` — observe empty record list (no prior signoff).
    * Anti-gaming: per-route 422-refusal regression-guard on `GS-001` for each of the 6 routes touched.
* `tests/test_phase15_journey_cross_axis_cohort_comparison.py` (new, 10+ tests):
    * Step 1: GET `/api/v1/cohort-overview/{snap-3-label}` — cohort_count = 5.
    * Step 2: For each of 3 explicit_dynamics cases + 2 linear_static_pv cases, GET trust-score-timeline; assert the linear_static_pv axis is FLAT across snapshots (no drift) while the explicit_dynamics axis evolves.
    * Step 3: GET `/api/v1/cohort-anomalies/{snap-3-label}` — assert it surfaces the explicit_dynamics drift, NOT the linear_static_pv axis.
    * Step 4: GET `/api/v1/case-completeness/{case_id}?analysis_type=<type>` for each case at the appropriate type — verify the rubric scores per axis are coherent.
    * Anti-gaming: routes distinct; no false-positive cross-leakage between analysis types.

**Binding sub-rubric (slice D):** M ≥10/12, T ≥10/15, C ≥10/12, A ≥6/8, E ≥7/8, V ≥7/8.

---

### Slice E — STATE refresh + retrospective + FINAL whole-arc TAA

**Goal:** Close Phase 15 with the same protocol as Phase 10 / 11 / 12 / 13 / 14.

**Deliverables:**
* `.planning/STATE.md` refresh with the Phase 15 closure stamp.
* `.planning/retrospectives/fm04a_phase15_explicit_dynamics_cohort_substantiation.md` (new) following the Phase 14 retrospective format.
* `.planning/phase15_audit_reports/{A,B,C,D}.md` archived (4 per-slice TAA reports).
* `.planning/phase15_audit_reports/FINAL.md` archived (whole-arc TAA).
* Phase 15 stop condition: **≥99/100 AND every axis ≥95% of weight**.

---

## 4. Binding rubric (whole-arc)

9-axis cumulative scoring, same as Phase 11 / 12 / 13 / 14:

| Axis | Weight | Description |
|---|---|---|
| B | 12 | Blueprint discipline: full Phase 15 scope shipped; no scope creep |
| M | 12 | Methodology: SSOTs typed/named; methodology docs cite identifiers |
| T | 15 | Tests: per-slice floors met; distinct behaviors |
| C | 12 | Coverage: Tier 1 disclaimer trio on every envelope; forbidden-token grep clean |
| X | 12 | Cross-cutting anti-gaming + defensive parsers (slice A energy-leak audit + slice C drift-attribution defensive parser) |
| D | 8 | Slice disposition matrix completeness |
| A | 8 | Anti-gaming guards exercised per slice |
| E | 8 | Full sweep green; no real-solver/LLM calls |
| V | 13 | TAA evidence quality |
| **Total** | **100** | |

**Anti-gaming guards (whole-arc):**
* **M:-2** — every new constant is named + module-level + typed (`DRIFT_DOMINANT_AXIS_DELTA_FLOOR_PCT`, `ROD_WAVE_IMPACT_STIFF_CASE_ID`, `ROD_WAVE_IMPACT_ENERGY_LEAK_CASE_ID`, schema-version bumps with bump-history docstrings).
* **T:-3** — boundary-pinned tests: stiff variant lands at 1.71% residual (within 5% tolerance band); leak variant's audit flags exactly frame 30 with rel_drift = 0.50 ± 0.001.
* **T:-4** — per-snapshot bucket-count pins are EXACT (not >= bounds) so a drifted fixture immediately surfaces the wrong count.
* **C:-8** — no Tier-2-promoting language in any new module; forbidden-token grep clean on all new fixtures + service modules + methodology docs.
* **A:-2** — drift_attribution defensive parser raises on (a) missing axes; (b) negative percentages outside the legitimate [-100, +Inf] band; (c) non-axis-name keys.
* **A:-3** — slice-A energy-leak fixture's flagged frame index is computed BY THE AUDIT (running `energy_partition_audit` on the parsed manifest), NOT trusted from the fixture's self-reported field. Slice-B 3-snapshot transitions are computed BY THE LIVE TRUST-SCORE ROUTE, NOT trusted from a hand-rolled snapshot manifest.
* **X:-2** — slice-C MINOR schema bumps on alerts (1.0.0→1.1.0) + timeline (1.0.0→1.1.0) carry bump-history docstrings naming Phase 15 C + the additive `drift_attribution` field.
* **E:-2** — Phase 14 cross-route signed-registry refusal SSOT exercised in slice D's anti-gaming pin (per-route 422 regression guard on GS-001 across every route the journey touches).

---

## 5. Out of scope

* Real OpenRadioss invocation — explicit_dynamics fixture trio remains synthetic-with-analytical-cross-check.
* Real-LLM advisor for explicit_dynamics — Phase 14 retro §3 carry-forward; still out of scope.
* Visual dev-server smoke of any cohort dashboard component — Phase 12 §2 carry-forward; still requires browser.
* New analysis types beyond the existing 4 — the v1 blueprint image #06 row 3 is closed (Phase 14 D); no further additions.
* FM-04b prerequisite work (`^GS-\d{3}$` signed registry remains untouched).
* Any push / PR / Linear / Notion writes.

---

## 6. Acceptance criteria (FINAL TAA gate)

Phase 15 closes when:
1. Slices A-D all ship with their binding sub-rubric scores met.
2. Slice E archives the retrospective + STATE refresh.
3. FINAL whole-arc TAA returns ≥99/100 with every axis ≥95% of weight.
4. All hard constraints PASS (HF1 guard, forbidden-token grep, Tier 1 disclaimer trio, cross-route signed-registry refusal SSOT).
5. Modal vs explicit_dynamics cohort parity gap (Phase 14 retro carry-forward) is explicitly CLOSED.
6. Per-axis drift attribution surface lands on both alerts + timeline envelopes with the MINOR schema bumps documented.
7. Backend test count ≥ 2379 + slice deliverable floors; frontend test count ≥ 135.
