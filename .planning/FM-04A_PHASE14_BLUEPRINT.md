# FM-04a Phase 14 — Explicit Dynamics Substantiation + Cross-Route Discipline

> **Tier 1 engineering candidate; not signed validation; not benchmark agreement.**

**Status:** Active. Substantiates the fourth and final analysis-type (`explicit_dynamics`) end-to-end, mirroring Phase 12's modal-axis arc but more compressed because the rubric is already defined (Phase 11 A; shares the ballistic rubric per `case_completeness.py:198-211`). Closes Phase 13 retrospective carry-forward §2 (cross-route signed-registry meta-guard).

**Author:** Local Claude Opus 4.7 under direct-execution authorization, mirroring the Phase 10 / Phase 11 / Phase 12 / Phase 13 protocol (binding 9-axis rubric + independent TAA gating). User authorization 2026-05-17: "作为总负责人，构建下一个阶段的蓝图，我授权你全权开发 ... 一直瞄准蓝图执行 ... 完成度评分机制（要绝对诚实客观）... 一直迭代下去，直至达到你眼里的优秀水准（99 分以上）".

**Branch:** `claude/FM-04a-tier1-ballistic-candidate`. Local-only; no pushes; no PRs; no Linear / Notion writes.

**Hard constraints (inherited from Phase 11-13, NON-NEGOTIABLE):**
* Tier 1 disclaimer trio stamped on every new envelope.
* 9 forbidden tokens (`validated against / perforation completed / bullet-through-steel complete / validated physics / production ready / certified / approved for service / asme compliant / signed off`) refused outside `not <claim>` form.
* HF1.7a signed-registry hard-stop preserved (Phase 13 D `_SIGNED_REGISTRY_RE` + Phase 13 E `_SIGNED_REGISTRY_PREFIX_RE` defense in depth).
* HF1.7b `*-candidate` carve-out IN FORCE — no override needed for new fixture writes.
* HF1.8 path-guard self-protection: any modification requires explicit AR/ADR cover or override-with-reason.
* No real OpenRadioss / real LLM API calls. Real solvers (CalculiX *DYNAMIC, gmsh meshing) are allowed for fixture authoring with analytical cross-check, mirroring Phase 12 C modal protocol.
* LLM-offline-first preserved.
* AI is advisor, NOT driver: 4-question gate audits.

---

## 1. North Star (1 sentence)

**Substantiate `explicit_dynamics` end-to-end as the fourth real-runnable analysis type with an analytically-cross-checked candidate case, and add the cross-route signed-registry refusal meta-guard so every reviewer-facing `/api/v1/.../{case_id}` route consistently rejects sealed FM-04b P8 packet identifiers.**

---

## 2. Closes these gaps

### From v1 blueprint (image #06 row 3 — Phase 11 carry-forward):
* **`explicit_dynamics` real candidate case** — the v1 blueprint image #06 row 3 listed `explicit_dynamics` as a planned analysis type alongside ballistic / linear_static_pv / modal; Phase 11 A added the rubric entry but no real-runnable candidate case ever shipped, and Phase 11 retro §A explicitly deferred it. Phase 12 substantiated modal; Phase 14 substantiates the remaining gap.

### From Phase 13 retrospective:
* **Slice-B TAA LOW #3 — cross-route signed-registry meta-guard.** Phase 13 B closed the case-completeness signed-registry route gap (originally Phase 12 F slice-F LOW); the meta-guard pin was deferred to Phase 14. The pin is preventive: enumerate every `/{case_id}` reviewer-facing route and assert each one consistently refuses `^GS-\d{3}$` identifiers with a 422 + matching detail vocabulary. Pays for itself the first time someone adds a new route.

### Phase 13 retrospective §1 (cosmetic numerical accounting drift) and §3 (visual dev-server smoke) are EXPLICITLY out of scope:
* §1 is cosmetic; will be cleaned up naturally next time the methodology doc gets touched.
* §3 requires a running browser the engineering pass does not have; the component-level contract is fully pinned by 10 vitest cases (Phase 12 I).

---

## 3. Slice plan

### Slice A — Cross-route signed-registry refusal meta-guard

**Goal:** A meta-test that enumerates every reviewer-facing `/api/v1/.*/{case_id}` route and asserts each one rejects `^GS-\d{3}$` identifiers with a consistent 422 + detail-vocabulary contract. Preventive discipline: a new route that forgets the gate trips the meta-test.

**Deliverables:**
* `tests/test_phase14_cross_route_signed_registry_refusal.py` (new, ≥10 tests):
  * Enumerate every route under `backend/app/api/routes/` matching the `/{case_id}` pattern via FastAPI route introspection.
  * For each enumerated route, hit it with `GS-001`, `GS-102`, `GS-999` via `httpx.ASGITransport` and assert:
      - `response.status_code == 422`
      - `"signed-registry" in response.json()["detail"]`
      - `"candidate" in response.json()["detail"]`
      - `"out of scope" in response.json()["detail"]`
  * Per-route parametrize: each enumerated route is a SEPARATE test case so a per-route failure surfaces with the route path in the test name.
  * Anti-loosening: a `_KNOWN_CASE_ID_ROUTES` SSOT tuple naming the expected route set; a test asserts the introspected set matches the SSOT so a NEW `/{case_id}` route that omits the gate trips the SSOT mismatch AND the gate test.
  * Defensive: routes that legitimately accept signed-registry case_ids (e.g., a hypothetical FM-04b-prereq introspection route) get a documented opt-out list with rationale.
* `backend/app/api/routes/<route>.py` — if any enumerated route is missing the gate, add it with the same detail vocabulary as advisor-critique + case-completeness (Phase 13 B closure).
* `.planning/methodology/case_id_route_discipline.md` (new) — SSOT for the route-level case_id discipline + the meta-guard's purpose.

**Binding sub-rubric (slice A):** M ≥10/12, T ≥12/15, C ≥10/12, A ≥6/8, E ≥7/8, V ≥7/8.

---

### Slice B — Explicit dynamics extraction service + analytical cross-check

**Goal:** A pure-Python service that parses the canonical explicit-dynamics output shape (animation manifest + per-frame energy partition + first-impact response) AND a `bar_wave_propagation` analytical cross-check that pins the wave-propagation timing for a 1D bar under axial impact. Mirrors Phase 12 A's modal-extraction service.

**Deliverables:**
* `backend/app/services/reporting/explicit_dynamics_extraction.py` (new):
  * `parse_animation_manifest(path) -> AnimationManifest` — extracts `frame_count`, `frame_dt_s`, `total_duration_s`, `per_frame_internal_energy_j` (optional), `per_frame_kinetic_energy_j` (optional), `per_frame_external_work_j` (optional).
  * `bar_wave_speed_m_per_s(E_Pa, rho_kg_per_m3) -> float` — analytical: `c = sqrt(E/rho)`.
  * `bar_wave_first_reflection_s(L_m, c_m_per_s) -> float` — analytical: `t_refl = L/c`.
  * `wave_propagation_residuals(case_obs, analytical) -> WaveResiduals` — observed first-reflection time vs analytical, with a `WAVE_CROSS_CHECK_TOLERANCE_PCT = 5.0` SSOT.
  * `energy_partition_audit(frames) -> EnergyPartitionAudit` — kinetic + internal energy at every frame should sum to ≤ external work (machine-epsilon tolerance); a deviation flag fires if the partition is non-physical.
* `backend/app/services/reporting/_schema_versions.py`:
  * Optional MINOR bump `CONVERGENCE_STUDY_SCHEMA_VERSION` 1.2.0 → 1.3.0 if an `impact_response_sweep` axis is added (mirrors mode_count_sweep). Only if the service genuinely needs it; bump-history docstring required.
* `.planning/methodology/explicit_dynamics_cross_check.md` (new) — SSOT for the wave-propagation analytical cross-check + the 5%-tolerance constant + bump-history of the formula.
* `tests/test_phase14_explicit_dynamics_extraction.py` (new, ≥18 tests):
  * Parser round-trips on synthetic animation manifests (frame counts 1 / 10 / 100; varying frame_dt).
  * Wave speed formula pinned for steel (E=200 GPa, rho=7850 kg/m³) → c ≈ 5050 m/s.
  * First-reflection formula pinned for L=1.0 m steel bar → t ≈ 0.198 ms.
  * Residuals contract: synthetic observed-correct case lands within 0.5%; synthetic observed-wrong case lands at the 12% the fixture defines.
  * Energy partition: clean + drifted cases distinguished.
  * Defensive: missing-file / malformed-json / empty-frames gracefully degraded.

**Binding sub-rubric (slice B):** M ≥10/12, T ≥12/15, C ≥10/12, A ≥6/8, E ≥7/8, V ≥7/8.

---

### Slice C — StubAdvisor explicit_dynamics branch

**Goal:** The `StubAdvisor` (`backend/app/services/reporting/advisor_critique.py` and friends) emits explicit-dynamics-specific concerns when `context.analysis_type == "explicit_dynamics"`. Mirrors Phase 12 B's modal-advisor-branch pattern.

**Deliverables:**
* `backend/app/services/reporting/advisor_critique.py`:
  * `StubAdvisor.produce()` adds an explicit_dynamics branch surfacing 4 concerns:
      1. **Time-step CFL stability** — "Explicit time integration requires `dt ≤ Δx / c_wave`; with `dt > CFL_limit` the solve diverges (NOT energy-conserving)."
      2. **Energy partition closure** — "Per-frame kinetic + internal energy should sum to external work within machine epsilon; deviation flag indicates non-physical energy injection."
      3. **Contact stiffness convergence** — "Hourglass control + contact stiffness affect transient response; the candidate should sweep both."
      4. **Wave reflection vs boundary condition** — "Free / clamped end conditions change reflection sign; the candidate must enumerate which BC is asserted."
* `frontend/src/components/AdvisorPanel.tsx` — no change needed (concerns render via existing `_Section` component).
* `tests/test_phase14_advisor_explicit_dynamics_branch.py` (new, ≥10 tests):
  * Each of the 4 concerns is emitted distinctly (not boilerplate).
  * Advisor branch is reachable via `context.analysis_type == "explicit_dynamics"`.
  * Phase 12 B's modal branch is unchanged (no regression).
  * Phase 11 A's ballistic / linear_static_pv branches unchanged.
  * 4-question gate still fires; Tier 1 disclaimer trio preserved.

**Binding sub-rubric (slice C):** M ≥10/12, T ≥10/15, C ≥10/12, A ≥6/8, E ≥7/8, V ≥7/8.

---

### Slice D — Real-runnable explicit dynamics candidate case fixture

**Goal:** A synthetic-but-analytically-cross-checked candidate case under `golden_samples/rod-wave-impact-candidate/` (HF1.7b carve-out applies; no override needed post-Phase-13 D). Fixture emits a small 1D rod-wave-impact response with analytically-correct first-reflection timing.

**Deliverables:**
* `golden_samples/rod-wave-impact-candidate/`:
  * `expected_results.json` — case_id + Tier 1 disclaimer trio + fixture_authoring_notes + expected wave-propagation timing.
  * `data/ballistic_metrics.json` — explicit_dynamics-flavored payload with `analysis_type: "explicit_dynamics_transient"`, energy_audit closed_aggregate.
  * `data/convergence_study.json` — `convergence_kind: "explicit_dynamics"`, both mesh + dt sweeps `candidate_observed_stable`.
  * `data/animation_manifest.json` — synthetic 100-frame manifest with analytically-correct first-reflection at frame ~20 (t=0.198 ms for L=1m steel bar @ frame_dt=10 μs). Per-frame kinetic+internal energy partitioned correctly.
* `scripts/gen_rod_wave_impact_deck.py` — generator that emits the fixture deterministically from material+geometry constants. Mirrors `scripts/gen_modal_cantilever_deck.py` style.
* `tests/test_phase14_rod_wave_impact_candidate.py` (new, ≥10 tests):
  * Fixture directory + expected files present.
  * `expected_results.json` carries Tier 1 disclaimer trio + analytical-cross-check claim_impact.
  * Animation manifest frame count + first-reflection frame match the analytical prediction within 5% tolerance (calling `bar_wave_first_reflection_s` from slice B).
  * Energy partition audit clean across all 100 frames.
  * Case completeness scorecard via the live ASGI `/api/v1/case-completeness/{case_id}?analysis_type=explicit_dynamics` route lands ≥80/100 (explicit_dynamics rubric weights: starter+engine 30 + ballistic_metrics 20 + energy_audit 15 + convergence_study 15 + animation_manifest 5 + result_mesh 5 + generator_script 5 + notes 5 = 100; the fixture has decks + metrics + animation + generator, with notes absent → ≥80 by construction).
  * Trust-score timeline (after `write_cohort_snapshot`) lands the case in the `healthy` bucket (trust ≥ 80).
  * Advisor critique route returns explicit_dynamics-specific concerns (4 from slice C).
  * Constraint guards: case_id is `*-candidate`, no signed-registry pattern, no real-solver artifact suffixes, fixture inside the carve-out directory.

**Binding sub-rubric (slice D):** M ≥10/12, T ≥10/15, C ≥10/12, A ≥6/8, E ≥7/8, V ≥7/8.

---

### Slice E — STATE refresh + retrospective + FINAL whole-arc TAA

**Goal:** Close Phase 14 with the same protocol as Phase 10 / 11 / 12 / 13.

**Deliverables:**
* `.planning/STATE.md` refresh with the Phase 14 closure stamp.
* `.planning/retrospectives/fm04a_phase14_explicit_dynamics_substantiation.md` (new) following the Phase 13 retrospective format.
* `.planning/phase14_audit_reports/{A,B,C,D}.md` archived (4 per-slice TAA reports).
* `.planning/phase14_audit_reports/FINAL.md` archived (whole-arc TAA).
* Phase 14 stop condition: **≥99/100 AND every axis ≥95% of weight**.

---

## 4. Binding rubric (whole-arc)

9-axis cumulative scoring, same as Phase 11 / Phase 12 / Phase 13:

| Axis | Weight | Description |
|---|---|---|
| B | 12 | Blueprint discipline: full Phase 14 scope shipped; no scope creep |
| M | 12 | Methodology: SSOTs typed/named; methodology docs cite identifiers |
| T | 15 | Tests: per-slice floors met; distinct behaviors |
| C | 12 | Coverage: Tier 1 disclaimer trio on every envelope; forbidden-token grep clean |
| X | 12 | Cross-cutting anti-gaming + defensive parsers (slice A meta-guard + slice B wave-propagation cross-check) |
| D | 8 | Slice disposition matrix completeness |
| A | 8 | Anti-gaming guards exercised per slice |
| E | 8 | Full sweep green; no real-solver/LLM calls |
| V | 13 | TAA evidence quality |
| **Total** | **100** | |

**Anti-gaming guards (whole-arc):**
* **M:-2** — every new constant is named + module-level + typed (`WAVE_CROSS_CHECK_TOLERANCE_PCT`, `EXPLICIT_DYNAMICS_CONVERGENCE_KIND`, `_KNOWN_CASE_ID_ROUTES`, `ROD_WAVE_IMPACT_CASE_ID`).
* **T:-3** — boundary-pinned tests for the analytical cross-check: 5050 m/s wave speed for steel pinned exactly; 0.198 ms first-reflection pinned exactly.
* **T:-4** — per-route parametrize on the slice-A meta-guard so a per-route failure surfaces with the route path in the test name.
* **C:-8** — no Tier-2-promoting language in any new module; forbidden-token grep clean.
* **A:-2** — slice-A meta-guard is *meta-pinned* (the SSOT tuple `_KNOWN_CASE_ID_ROUTES` trips if a new route is added without the gate AND a route that opts out lands in a documented opt-out list).
* **A:-3** — defense in depth: slice-D fixture verified to fail the `bar_wave_first_reflection_s` analytical cross-check by ASSERTING the observed-correct timing matches analytical (not just trusting the fixture file).
* **E:-2** — optional schema bump for `impact_response_sweep` axis lands with bump-history docstring + centralized SSOT pin.

---

## 5. Out of scope

* New analysis types beyond ballistic / linear_static_pv / explicit_dynamics / modal (the existing 4 are the FINAL set).
* FM-04b prerequisite work (`^GS-\d{3}$` signed registry remains untouched).
* Visual dev-server smoke of `CohortSubstantiationPanel.tsx` (Phase 12 §2 carry-forward — still requires browser).
* Real OpenRadioss invocation — explicit_dynamics fixture is synthetic-with-analytical-cross-check, mirroring Phase 12 C modal protocol.
* Any push / PR / Linear / Notion writes.

---

## 6. Acceptance criteria (FINAL TAA gate)

Phase 14 closes when:
1. Slices A-D all ship with their binding sub-rubric scores met.
2. Slice E archives the retrospective + STATE refresh.
3. FINAL whole-arc TAA returns ≥99/100 with every axis ≥95% of weight.
4. All hard constraints PASS (HF1 guard, forbidden-token grep, Tier 1 disclaimer trio).
5. v1 blueprint image #06 row 3 (`explicit_dynamics` candidate case) is explicitly CLOSED.
6. Phase 13 retro carry-forward §2 (cross-route meta-guard) is explicitly CLOSED.
7. Backend test count ≥ 2280 + slice deliverable floors; frontend test count ≥ 135.
