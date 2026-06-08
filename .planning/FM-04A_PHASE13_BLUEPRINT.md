# FM-04a Phase 13 — Carry-Forward Closure + Schema Evolution

> **Tier 1 engineering candidate; not signed validation; not benchmark agreement.**

**Status:** Active. Closes named carry-forwards from the Phase 11 + Phase 12 retrospectives. Lift-and-shift execution profile: small, surgical, all-closure work; no new analysis types; no v1 blueprint row additions.

**Author:** Local Claude Opus 4.7 under direct-execution authorization, mirroring the Phase 10 / Phase 11 / Phase 12 protocol (binding 9-axis rubric + independent TAA gating). User authorization 2026-05-16: "全权开发 ... 一直瞄准蓝图执行 ... 完成度评分机制 (绝对诚实客观) ... 一直迭代下去，直至达到你眼里的优秀水准（99 分以上）".

**Branch:** `claude/FM-04a-tier1-ballistic-candidate`. Local-only; no pushes; no PRs; no Linear / Notion writes.

**Hard constraints (inherited from Phase 11/12, NON-NEGOTIABLE):**
* Tier 1 disclaimer trio stamped on every new envelope.
* 9 forbidden tokens (`validated against / perforation completed / bullet-through-steel complete / validated physics / production ready / certified / approved for service / asme compliant / signed off`) refused outside `not <claim>` form.
* HF1 hard-stop zone preserved (`scripts/hf1_path_guard.py` defaults unchanged; slice D AMENDS but does NOT widen the protective surface).
* No real OpenRadioss / real LLM API calls.
* LLM-offline-first preserved.
* AI is advisor, NOT driver: 4-question gate audits.

---

## 1. North Star (1 sentence)

**Close the named per-slice carry-forwards from Phase 11 (§4 permissive 4xx assertions; §5 structured refused_claims surface) and Phase 12 (§3 HF1.7 *-candidate carve-out; §4 deeper-degradation regressed-bucket fixture) so a future Phase 14 starts on a clean carry-forward slate.**

---

## 2. Closes these gaps

### From Phase 11 retrospective:
* **§4 — Permissive 4xx-range assertions across the test suite.** `assert response.status_code in (400, 404)` and `assert 400 <= response.status_code < 500` patterns let unintended status-code drifts slip through silently. Slice F of Phase 11 + slice F of Phase 12 each tightened individual call sites; Phase 13 sweeps the rest.
* **§5 — Structured `refused_claims` field on AdvisorCritique envelope.** When the LLM emits a forbidden positive claim, Phase 11 raises at construction. A reviewer cannot see what the LLM *would have said* unless they manually inspect logs. Phase 13 ships a structured `refused_claims: tuple[str, ...]` field surfaced through the envelope so reviewers audit what was suppressed without exposing the positive claim itself.

### From Phase 12 retrospective:
* **§3 — HF1.7 ADR amendment for `*-candidate` carve-out.** HF1.7 is whole-directory read-only over `golden_samples/**`; the binding constraint explicitly authorizes `*-candidate` writes. Slice D ships an ADR amendment formalizing the carve-out + updates `scripts/hf1_path_guard.py` to recognize `*-candidate` writes without requiring `HF1_GUARD_OVERRIDE` (close the audit-trail loop at `reports/hf_audit.md`).
* **§4 — Deeper-degradation 5th cohort case.** Phase 12 D's `cylinder-pv-extended-candidate` snapshot 3 landed at trust=84 (still "healthy" by bucket math); blueprint wording was aspirational. Phase 13 ships a 5th synthetic fixture whose snapshot 3 lands trust < 50, forcing the `regressed` bucket and making the slice-D blueprint assertion load-bearing.

### Phase 11 §2 (AdvisorContext.extra) and Phase 12 retro §1 / §5 are **already closed** inside slice H of Phase 12 — not in scope.

---

## 3. Slice plan

### Slice A — Structured refused_claims surface on AdvisorCritique

**Goal:** When the LLM advisor or stub emits content that would trip the forbidden-claim audit, surface the refused-then-redacted claim text as a structured `refused_claims` field on the envelope instead of raising at construction. Reviewers can audit suppression history; the positive claim never reaches the rendered surface.

**Deliverables:**
* `backend/app/services/reporting/advisor_critique.py`:
  * Add `refused_claims: tuple[str, ...] = ()` field to `AdvisorCritique` dataclass (frozen).
  * Add `_audit_and_collect_refused(text: str) -> tuple[str | None, str | None]` helper: returns `(safe_text, refused_marker)` — if the input contains a forbidden token outside disclaimer form, returns `(None, marker)`; otherwise `(text, None)`.
  * Update `build_advisor_critique` to collect refused markers across all 4 content sections; populate `refused_claims` tuple; the safe sections continue to render normally.
  * Backward-compat: an absent `refused_claims` field on a pre-1.1.0 payload parses as empty tuple.
* `backend/app/services/reporting/_schema_versions.py`:
  * MINOR bump `ADVISOR_CRITIQUE_SCHEMA_VERSION` 1.0.0 → 1.1.0 with bump-history docstring naming the new optional field and the back-compat contract.
* `backend/app/api/routes/advisor_critique.py`: no route signature change; envelope JSON gains the new field automatically through the dataclass serializer.
* `frontend/src/advisorCritiqueClient.ts`: parse the new field with safe-default to empty tuple; add `REFUSED_CLAIMS_MAX_ITEMS` constant for client-side render cap.
* `frontend/src/components/AdvisorPanel.tsx`: render a "Refused LLM claims (N)" collapsible section when `refused_claims.length > 0`; each refused entry shows the marker text (NOT the original positive claim).
* Methodology: `.planning/methodology/advisor_critique_refused_claims.md` (new) — SSOT for the marker format + reviewer-audit semantics.
* `tests/test_phase13_refused_claims.py` (new, ≥14 tests): every forbidden token round-trips through the refused-claim collection layer; marker text is reproducible (deterministic for a given input); pre-1.1.0 payload parses without the field; envelope-level audit on the rendered JSON still trips on a positive claim that somehow reaches it.
* `tests/test_schema_versions_stamping.py`: pin updated for `ADVISOR_CRITIQUE_SCHEMA_VERSION == "1.1.0"`.

**Binding sub-rubric (slice A):** M ≥10/12, T ≥12/15, C ≥10/12, A ≥6/8, E ≥7/8, V ≥7/8.

---

### Slice B — Cross-phase test discipline sweep

**Goal:** Tighten `400 <= code < 500` permissive assertions across the test suite to exact-code contracts (matching the slice-F supplementals from Phase 11 + Phase 12). Per Phase 11 retro §4, this is project-wide test-discipline carry-forward.

**Deliverables:**
* Audit every test file under `tests/` for permissive 4xx-range patterns:
  * `grep -rn "400 <= .*status_code < 500" tests/`
  * `grep -rn "status_code in (4" tests/`
  * `grep -rn "in (400," tests/`
* For each hit, identify the route's documented status code (in the route module) and replace the permissive range with an exact-code assertion.
* Edge cases preserved (intentional permissive ranges with rationale comments) are documented; the test suite must remain green after the sweep.
* `tests/test_phase13_status_code_discipline.py` (new, ≥8 tests): meta-test that scans every `tests/test_*.py` file and counts permissive-range patterns; fails if the count exceeds a pinned ceiling (initial ceiling = the count of intentional-permissive sites that survive the sweep). This is a load-bearing regression-prevention pin.

**Binding sub-rubric (slice B):** M ≥10/12, T ≥12/15, C ≥10/12, A ≥6/8, E ≥7/8, V ≥7/8.

---

### Slice C — Deeper-degradation 5th cohort case

**Goal:** A synthetic 5th cohort case whose snapshot-3 trust score lands < 50 so the slice-D Phase 12 blueprint's "regressed bucket fires" wording becomes load-bearing on real fixture math.

**Deliverables:**
* `golden_samples/cylinder-pv-collapsed-candidate/` (new `*-candidate` directory; HF1-permitted): a synthetic PV case authored to land trust ≈ 30-40 on a 3rd snapshot:
  * Drop reproducibility entirely (no generator script in any snapshot).
  * Drop energy_audit (status `unavailable` from snapshot 2 onwards).
  * Drop completeness via degraded `ballistic_metrics.json` (all PV-quality fields fail).
  * Mesh + dt sweeps land `candidate_observed_unstable` in snapshot 3.
* `tests/test_phase13_deeper_degradation_cohort.py` (new, ≥10 tests):
  * Extends the Phase 12 D `_write_three_snapshots` to include the 5th case.
  * Asserts snapshot 3 trust score on `cylinder-pv-collapsed-candidate` is strictly < 50.
  * Asserts the `cohort_executive_summary` bucket count `regressed >= 1`.
  * Asserts the dashboard view-model surfaces the collapsed case in the `regressed` bucket count via the slice-E `cohortDashboardClient.ts` orchestrator + slice-I panel.
* `.planning/methodology/cohort_bucket_thresholds.md`: append an audit note documenting the deeper-degradation fixture as the load-bearing regressed-bucket trigger evidence.

**Binding sub-rubric (slice C):** M ≥10/12, T ≥10/15, C ≥10/12, A ≥6/8, E ≥7/8, V ≥7/8.

---

### Slice D — HF1.7 ADR amendment + `*-candidate` path-guard carve-out

**Goal:** Formalize the `*-candidate` carve-out in ADR-011 HF1.7 + update the path guard so future `*-candidate` writes don't require `HF1_GUARD_OVERRIDE`. The audit-log entry at `reports/hf_audit.md` rolls over to the next window post-amendment.

**Deliverables:**
* `docs/adr/ADR-011-pivot-claude-code-takeover.md`:
  * Add amendment row `AR-2026-05-16-001` to the amendments table.
  * §HF1.7 split into HF1.7a (`golden_samples/<signed-registry>` whole-directory read-only) + HF1.7b (`golden_samples/*-candidate/` writable per FM-04a binding constraint).
  * Methodology rationale + override-deprecation note.
* `scripts/hf1_path_guard.py`:
  * `*-candidate` paths inside `golden_samples/**` are allowed without `HF1_GUARD_OVERRIDE`.
  * Signed-registry pattern `^golden_samples/GS-\d{3}(/.*)?$` remains hard-stop.
  * The guard's audit log entry mentions the AR-2026-05-16-001 amendment in the rejection / override message.
* `reports/hf_audit.md`: roll over to window-001 post-amendment; the current Phase 12 C entries become historical context under window-000.
* `reports/archive/hf_audit_window-000.md` (new): archive the pre-amendment window per the ADR-011 rolling-window protocol.
* `tests/test_hf1_path_guard_candidate_carveout.py` (new, ≥6 tests):
  * `*-candidate` write inside `golden_samples/` passes the guard without override.
  * `^GS-\d{3}` write inside `golden_samples/` still hard-stops.
  * Override env-var still works (as defense-in-depth for any future edge case).
  * Guard's rejection message references the amendment ID.

**Binding sub-rubric (slice D):** M ≥10/12, T ≥10/15, C ≥11/12, A ≥7/8, E ≥7/8, V ≥7/8.

> **Special discipline for slice D**: this slice touches ADR-011 + `scripts/hf1_path_guard.py` (BOTH in HF1.8 meta-protection zone). The amendment must be ADR-cycle-disciplined: the slice's commit message names the AR id; the guard self-protects (HF1.8 hard-stop still trips if the slice tries to silently widen the protective surface).

---

### Slice E — STATE refresh + retrospective + FINAL whole-arc TAA

**Goal:** Close Phase 13 with the same protocol as Phase 10 / 11 / 12.

**Deliverables:**
* `.planning/STATE.md` refresh with the Phase 13 closure stamp.
* `.planning/retrospectives/fm04a_phase13_carry_forward_closure.md` (new) following the Phase 12 retrospective format.
* `.planning/phase13_audit_reports/{A,B,C,D}.md` archived (4 per-slice TAA reports).
* `.planning/phase13_audit_reports/FINAL.md` archived (whole-arc TAA).
* Phase 13 stop condition: **≥99/100 AND every axis ≥95% of weight**.

---

## 4. Binding rubric (whole-arc)

9-axis cumulative scoring, same as Phase 11 / Phase 12:

| Axis | Weight | Description |
|---|---|---|
| B | 12 | Blueprint discipline: full Phase 13 scope shipped; no scope creep |
| M | 12 | Methodology: SSOTs typed/named; methodology docs cite identifiers |
| T | 15 | Tests: per-slice floors met; distinct behaviors |
| C | 12 | Coverage: Tier 1 disclaimer trio on every envelope; forbidden-token grep clean |
| X | 12 | Cross-cutting anti-gaming + defensive parsers (slice A `refused_claims` audit + slice B test-discipline meta-test) |
| D | 8 | Slice disposition matrix completeness |
| A | 8 | Anti-gaming guards exercised per slice |
| E | 8 | Full sweep green; no real-solver/LLM calls |
| V | 13 | TAA evidence quality |
| **Total** | **100** | |

**Anti-gaming guards (whole-arc):**
* **M:-2** — every new constant is named + module-level + typed.
* **T:-3** — boundary-pinned tests for the refused-claim text matching.
* **T:-4** — per-failure-mode tests across all 9 forbidden tokens × disclaimer-form-passes (= 18 distinct pins minimum on slice A).
* **C:-8** — no Tier-2-promoting language in any new module; forbidden-token grep clean.
* **A:-2** — refused-claim collection is a *reported list*, not a raised exception (mirror the Phase 11 stress-linearization "thresholds reported not raised" guard).
* **A:-3** — defense in depth: the envelope's `_assert_no_overclaim` still trips on a positive claim that somehow reaches the rendered surface (not relying solely on the upstream collection layer).
* **E:-2** — schema bump bump-history docstring; centralized SSOT pin in `tests/test_schema_versions_stamping.py`.

---

## 5. Out of scope

* New analysis types beyond ballistic / linear_static_pv / explicit_dynamics / modal (the existing 4 are preserved).
* `explicit_dynamics` real candidate case (v1 blueprint image #06 row 3 — deferred to Phase 14).
* Visual dev-server smoke of `CohortSubstantiationPanel.tsx` (Phase 12 §2 carry-forward — still requires browser).
* FM-04b prerequisite work (`^GS-\d{3}$` signed registry remains untouched).
* Any push / PR / Linear / Notion writes.

---

## 6. Acceptance criteria (FINAL TAA gate)

Phase 13 closes when:
1. Slices A-D all ship with their binding sub-rubric scores met.
2. Slice E archives the retrospective + STATE refresh.
3. FINAL whole-arc TAA returns ≥99/100 with every axis ≥95% of weight.
4. All hard constraints PASS (HF1 guard, forbidden-token grep, Tier 1 disclaimer trio).
5. Phase 11 carry-forwards §4 and §5 are explicitly CLOSED.
6. Phase 12 carry-forwards §3 and §4 are explicitly CLOSED.
7. Backend test count ≥ 2191 + slice deliverable floors; frontend test count ≥ 127.
