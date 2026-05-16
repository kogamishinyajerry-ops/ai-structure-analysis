# FM-04a Phase 11 — Tier 1 AI Advisor Surface & Analysis-Type-Aware Reviewer Rubric

**Status:** PLANNED 2026-05-16, branch=claude/FM-04a-tier1-ballistic-candidate (off Phase 10 closure `0ccad79`).
**Tier:** Tier 1 engineering candidate; not signed validation; not benchmark agreement.
**Disposition:** Closes 2 real gaps surfaced by the cylinder-pv-candidate e2e demo (2026-05-16):
  1. `case_completeness` rubric is hard-coded to ballistic evidence axes — PV linear-static cases drop 25/100 on `animation_manifest`/`result_mesh`/`notes` regardless of how good the actual engineering content is.
  2. Project north star is "AI is advisor not driver" (memory: `feedback_cfd_harness_ai_advisor_pivot`) — reviewer surfaces have data infrastructure (Phase 8/9/10) but no AI advisor layer plugged in yet.

**Constraints (preserved verbatim, must continue to apply):**
- Tier 1 engineering candidate; not signed validation; not benchmark agreement.
- Never start FM-04b work.
- Never touch `^GS-\d{3}$` signed-registry directories.
- Never write to Linear or Notion.
- Never write inside `golden_samples/**` except `*-candidate` directories.
- Never use real OpenRadioss solver (CI must run synthetic-only paths).
- HF1 hard-stop zone preserved.
- Forbidden positive claims must NEVER appear except in `not <claim>` disclaimer form.
- No push, no PR, no external write.

**Phase 11 specific constraints:**
- AI advisor is LLM-offline-first. The workbench must run every reviewer flow (GET trust-score, POST signoff, GET history, GET cohort summary, GET trust-score-provenance) with the LLM unavailable. The advisor critique surfaces at a SEPARATE endpoint; offline returns a clean degrade-status payload, not a 5xx.
- Advisor is READ-ONLY: never writes a snapshot, signoff, generator script, deck, or any artifact under `golden_samples/`, `reports/`, `project_state/`.
- The four-question gate must appear in the advisor service module docstring AND in every critique payload's metadata block. Any payload missing any of the four questions FAILS its envelope audit.
- Advisor critique payloads are subject to the same forbidden-claim envelope audit as every other Tier 1 surface, with an *extended* token list that includes "production ready", "certified", "approved for service", "ASME compliant" (positive claim outside `not <claim>` form refused).

---

## 1. The 9-axis scoring rubric (sum = 100 / stop condition ≥99 AND every axis ≥95% of weight)

| Axis | Weight | Concretely measured by |
|---|---:|---|
| **B** Blueprint adherence | 12 | Every Phase 11 disposition item maps to exactly one named slice in §3 below. Zero scope creep beyond the 2 gap items. Every slice closes on a TAA APPROVE before next slice starts. |
| **M** Methodology / SSOT discipline | 12 | New constants (`ADVISOR_CRITIQUE_SCHEMA_VERSION`, `ADVISOR_FORBIDDEN_TOKENS`, `ANALYSIS_TYPE_TUPLE`, `ANALYSIS_TYPE_RUBRIC_WEIGHTS`) all live in module SSOTs with full bump-history docstrings. New methodology doc `.planning/methodology/analysis_type_completeness_rubric.md` cites every constant by Python identifier. |
| **T** Test coverage | 15 | Floor-per-slice: A ≥16 backend; B ≥12 backend; C ≥10 backend; D ≥14 backend (HTTP routes); E ≥8 frontend; F integration ≥16 + E2E ≥3. Each numeric threshold is pinned by an explicit boundary test. |
| **C** Claim discipline | 12 | Tier 1 disclaimer trio on every new response shape. Forbidden-claim envelope audit extended with advisor-specific tokens (production ready / certified / approved for service / ASME compliant). HF1 zone untouched. Four-question-gate audit fires on every advisor critique. |
| **X** Cross-layer integrity | 12 | Frontend parser surfaces `null` / `'offline'` for missing advisor fields on a pre-Phase-11 payload (forward-compat from schema 1.0.0). Defensive `parseAdvisorStatus` falls to `'unknown'` for unknown values. Frontend tuple SSOT matches backend tuple byte-for-byte. |
| **D** Disposition & documentation | 8 | `analysis_type_completeness_rubric.md` documents rebalance procedure (procedural numbered list). Carry-forward map enumerates every Phase 10 retro item + every e2e-demo finding with named slice owner. |
| **A** Anti-gaming guards | 8 | All 18 anti-gaming guards (§4 below) named and tested individually. Stub-advisor path has its own test (cannot use a stub bypass to game the live-advisor evaluation). Forbidden-claim audit re-verified post schema bump. |
| **E** End-to-end | 8 | Backend full sweep at slice F passes (≥1916 + Phase 11 added tests). E2E walks the real ASGI route stack via `httpx.ASGITransport`. Each E2E composes ≥3 routes. Advisor-offline E2E proves the workbench is functional with LLM down. |
| **V** Verdict (independent TAA) | 13 | 6/6 first-cut APPROVE on per-slice TAAs + FINAL whole-arc TAA APPROVE. V-axis judgment is the load-bearing call by the FINAL TAA agent. |

**Stop condition:** total ≥99 / 100 AND every axis ≥95% of its weight. Same protocol as Phase 9/10.

---

## 2. Carry-forward disposition map

### From Phase 10 retrospective (3 items)
| Item | Disposition |
|---|---|
| Signoff record filename second-precision collision | **Deferred to Phase 12** (scope: signoff record persistence; not in Phase 11 advisor/rubric scope). |
| ProvenancePanel 5-column responsive layout | **Deferred to Phase 12** (scope: UI responsive layout; not in Phase 11 scope). |
| Rate-limit per-reviewer policy variability | **Deferred to Phase 12** (scope: policy tiering; not in Phase 11 scope). |

### From cylinder-pv-candidate e2e demo (2 items + 1 enhancement)
| Item | Disposition |
|---|---|
| `case_completeness` rubric ballistic-hardcoded | **Slice A** — multi-analysis-type rubric. |
| No AI advisor surface in reviewer workbench | **Slices B, C, D, E** — advisor service + schema + HTTP + UI. |
| `convergence_study` schema mesh+dt assumes time integration | **Slice A subscope** — convergence schema gets `convergence_kind` discriminator (`linear_static` skips dt sweep cleanly). |

---

## 3. Slice plan

Linear arc, each slice gets independent TAA before next slice starts. Phase 10 protocol.

### Slice A — Analysis-type-aware completeness rubric + convergence schema

**Goal:** `case_completeness.score_case_completeness()` accepts `analysis_type` parameter and dispatches to the right rubric weights. `convergence_study.json` schema grows a `convergence_kind` discriminator; the trust-score convergence axis adapts to skip irrelevant axes cleanly (no "0/20 for missing dt sweep on a linear-static case").

**Deliverables:**
- New module-level SSOT `ANALYSIS_TYPE_TUPLE: tuple[str, ...] = ("ballistic", "linear_static_pv", "explicit_dynamics", "modal")` in `case_completeness.py`.
- `ANALYSIS_TYPE_RUBRIC_WEIGHTS: dict[str, dict[str, int]]` — per-type weight maps. `ballistic` keeps the current weights (back-compat). `linear_static_pv` swaps `animation_manifest` / `result_mesh` for `lame_cross_check_present` (10) and `scl_convergence_lt_5pct` (10) and `allowable_margin_present` (5).
- `CaseCompletenessInputs.analysis_type: str = "ballistic"` (default preserves back-compat).
- New methodology SSOT `.planning/methodology/analysis_type_completeness_rubric.md` — names every weight by Python identifier; per-type rebalance checklist.
- `convergence_study.json` grows top-level `convergence_kind` discriminator. `trust_score._score_convergence_axis` reads this discriminator and skips `dt_sweep` evaluation for `linear_static` cases (treats absent as N/A, not as failure).
- MINOR schema bump `CASE_COMPLETENESS_SCHEMA_VERSION` 1.0.0 → 1.1.0 (additive `analysis_type` envelope key) AND `CONVERGENCE_STUDY_SCHEMA_VERSION` 1.0.0 → 1.1.0 (additive `convergence_kind`).
- Tests ≥16 in `tests/test_phase11_analysis_type_rubric.py` including: per-type weight sum, boundary at every threshold, fixture-driven cross-check, back-compat reading of a pre-Phase-11 metrics file, schema bump pins, forbidden-claim audit re-verification.
- Slice-A TAA APPROVE archived at `.planning/phase11_audit_reports/A.md`.

### Slice B — AdvisorCritique schema + service module skeleton

**Goal:** define the advisor surface contract. Module-level `AdvisorCritique` dataclass + `build_advisor_critique` builder that takes (case_id, snapshot_label, advisor_backend) and returns a structured critique. Stub advisor and live-LLM advisor are concrete `AdvisorProvider` Protocol impls. The 4-question gate is enforced at envelope construction; missing answer = ValueError.

**Deliverables:**
- New module `backend/app/services/reporting/advisor_critique.py` with:
  - `ADVISOR_CRITIQUE_SCHEMA_VERSION = "1.0.0"` SSOT
  - `ADVISOR_FORBIDDEN_TOKENS = ("production ready", "certified", "approved for service", "ASME compliant", "signed off")` (extends the Tier 1 base list)
  - `FOUR_QUESTION_GATE: tuple[str, ...] = ("llm_offline_ok", "artifacts_user_owned", "trustgate_explains", "advisor_only")` (the four question keys)
  - `AdvisorCritique` dataclass: `schema_version, case_id, snapshot_label, advisor_status ∈ {"online", "offline", "stub"}, advisor_backend (str), generated_at_utc, four_question_gate (dict[str, bool]), mesh_quality_concerns (tuple[str, ...]), boundary_condition_questions (tuple[str, ...]), failure_modes_to_consider (tuple[str, ...]), unhandled_load_cases (tuple[str, ...]), claim_tier, claim_boundary, claim_impact`
  - `AdvisorProvider` Protocol with `name: str` + `is_available() -> bool` + `produce(context: AdvisorContext) -> AdvisorRawCritique`
  - `StubAdvisor` concrete impl: rule-based, always available, generates concerns from input data (e.g., trust_score < 70 → mesh_quality_concerns flag; energy_audit.status != closed_aggregate → boundary_condition_questions flag).
  - `build_advisor_critique(case_id, snapshot_label, repo_root, *, provider=None)` — picks `StubAdvisor` if `provider` is None; on `is_available() == False` falls back to stub; envelope audit; four-question gate audit; forbidden-token audit (uses extended token list).
- Bump `_schema_versions.py` to add `ADVISOR_CRITIQUE_SCHEMA_VERSION = "1.0.0"`.
- Tests ≥12 in `tests/test_phase11_advisor_critique.py` including: four-question gate refuses on missing key; forbidden-token audit fires on every extended token; stub advisor produces deterministic output from a fixed input; provider fallback path; envelope schema-version pin; `advisor_status` enum closed-set pin.
- Slice-B TAA archived at `.planning/phase11_audit_reports/B.md`.

### Slice C — LLMAdvisor + offline degrade path

**Goal:** add a concrete `LLMAdvisor` impl that calls an injectable LLM client (default: stub). Workbench shipping defaults to `StubAdvisor`; an env-var-driven factory enables `LLMAdvisor` if `AIFEA_ADVISOR_BACKEND=anthropic` and `ANTHROPIC_API_KEY` is set. **No real LLM API calls in tests** — the LLM client is injected via a callable. Offline path test pins `advisor_status == "offline"` and a non-empty stub critique.

**Deliverables:**
- `LLMAdvisor` class in `advisor_critique.py` with an injectable `llm_call: Callable[[str], str]` (sync, returns JSON).
- `_default_llm_factory()` reads env vars; missing → returns `None` (caller falls back to `StubAdvisor`).
- The live-LLM prompt template is a multi-shot system + user turn that asks for 4 lists of concerns and ENFORCES the four-question gate as part of the response schema. Response JSON is parsed defensively (`parseInputKind`-style); malformed responses fall back to stub critique with `advisor_status = "stub"` and a `degrade_reason` field.
- Tests ≥10 in `tests/test_phase11_llm_advisor.py` including: llm_call returning malformed JSON triggers stub fallback; llm_call raising exception triggers stub fallback; env-var absent → `_default_llm_factory()` returns None; forbidden-token in LLM response refused at envelope; four-question gate missing in LLM response refused.
- Slice-C TAA archived at `.planning/phase11_audit_reports/C.md`.

### Slice D — Advisor HTTP route + multi-analysis-type completeness route

**Goal:** expose two new endpoints:

1. `GET /api/v1/advisor-critique/<case_id>?snapshot=<label>` returns an `AdvisorCritique` payload (200 with `advisor_status` ∈ `online`/`offline`/`stub`; **never** 5xx for advisor outage). 422 for invalid case_id or absent snapshot. 404 for case not in snapshot.
2. `GET /api/v1/case-completeness/<case_id>?analysis_type=<type>` returns the rebuilt scorecard for the chosen analysis type. Defaults to `ballistic` for back-compat. Invalid `analysis_type` → 422 with the allowed-set echoed in the detail.

Both routes apply the same case_id pattern guards as Phase 8/9 (signed-registry refusal; candidate-only). Both honor the rate-limit infrastructure from Phase 10 D as a shared dependency where applicable.

**Deliverables:**
- New route module `backend/app/api/routes/advisor_critique.py`.
- New route module `backend/app/api/routes/case_completeness.py` (currently the completeness service exists but has no HTTP surface).
- Tests ≥14 in `tests/test_phase11_endpoints_integration.py` including the 6 standard gate compositions per route (415 / 422 case_id / 422 invalid analysis_type / 422 absent snapshot / 404 missing snapshot / 200 happy path / Tier 1 disclaimer in body).
- Slice-D TAA archived at `.planning/phase11_audit_reports/D.md`.

### Slice E — AdvisorPanel frontend + typed client

**Goal:** mount an `AdvisorPanel` inside the reviewer workbench next to `ProvenancePanel`. Render the 4 sections (concerns / questions / failure modes / unhandled loads) with severity-style chips. Header shows `advisor_status` badge (online/offline/stub) + 4-question-gate checklist (4 green ticks or X). Tier 1 disclaimer trio in footer. Forward-compat: if backend returns a schema-version not in the frontend tuple → `parseAdvisorStatus` falls to `'unknown'` and panel renders a neutral message (does NOT crash).

**Deliverables:**
- `frontend/src/advisorCritiqueClient.ts` (typed client; as-const `ADVISOR_STATUS_TUPLE` + `FOUR_QUESTION_GATE_KEYS` tuples matching backend SSOT).
- `frontend/src/components/AdvisorPanel.tsx` (mounts only when caseId AND snapshotLabel both non-empty; 4-section grid; status badge; 4-Q-gate checklist).
- `frontend/src/App.tsx` mounts AdvisorPanel adjacent to ProvenancePanel.
- Tests ≥8 in `frontend/test/AdvisorPanel.test.tsx` including offline-status renders cleanly; forbidden-token preview client-side; 4-Q-gate-missing-key surfaces explicit error message; forward-compat parsing of a pre-Phase-11 payload.
- Slice-E TAA archived at `.planning/phase11_audit_reports/E.md`.

### Slice F — HTTP integration + E2E reviewer journeys

**Goal:** prove cross-slice composition via the real ASGI stack.

**Deliverables:**
- 16 HTTP integration tests (8 advisor-critique gate composition + 8 case-completeness-route composition) in `tests/test_phase11_endpoints_integration.py` (extending slice D's count or adding a new file — TBD by slice author).
- 3 E2E reviewer journeys in `tests/test_fm04a_phase11_advisor_e2e.py`:
  1. Reviewer reads provenance + advisor critique side by side; advisor flags a concern; reviewer POSTs `needs_more_evidence` signoff; cohort summary bucket reflects.
  2. LLM offline — advisor returns stub critique; reviewer still completes full workflow (provenance → signoff → history → summary); proves workbench LLM-offline-functional.
  3. Multi-analysis case bucket: a `cylinder-pv-candidate` (linear_static_pv rubric) and a `GS-102-candidate` (ballistic rubric) coexist in the cohort; each gets its analysis-type-correct completeness score; cohort summary surfaces both without rubric collision.
- Slice-F TAA archived at `.planning/phase11_audit_reports/F.md`.

### Slice G — STATE refresh + retrospective + FINAL whole-arc TAA

Same protocol as Phase 9 G / Phase 10 G.

---

## 4. Anti-gaming guards (18 named)

**M-axis (3):**
- M:-2 — No magic numbers. All rubric weights live in module SSOT dicts; tested via "sum equals 100 per analysis_type" boundary test.
- M:-3 — Documented reset hook on advisor cache (if added). No hidden module-level state.
- M:-4 — Methodology SSOT doc cites every constant by Python identifier (grep-verifiable).

**T-axis (4):**
- T:-2 — No `time.sleep` in any new test. Synthetic clock injection where required (advisor cache TTL if added).
- T:-3 — Each numeric threshold (per-type weight sum; severity bucket boundary) pinned by an explicit test, not an inline magic constant.
- T:-4 — Each separate equivalence claim (e.g., "stub advisor reproduces identical output for identical input") has its own test, not one combined test.
- T:-5 — Forbidden-token list extension verified by a test that fires for EACH new token explicitly (per-token test, not a single loop test).

**C-axis (3):**
- C:-4 — Forbidden-claim envelope audit re-verified post Phase 11 schema bumps; explicit test injecting a forbidden token via monkeypatch.
- C:-8 — Tier 1 disclaimer trio asserted on every new response shape (5+ new shapes in Phase 11).
- C:-10 — Four-question gate audit at envelope construction; missing key = ValueError.

**A-axis (4):**
- A:-2 — Vacuous-stub-advisor guard: stub advisor must produce content correlated with the input (e.g., trust_score < 70 surfaces at least one mesh_quality_concern). Not just empty lists for every case.
- A:-3 — LLM-malformed-response path exercised by an explicit test (not just live-LLM happy path).
- A:-4 — Advisor cannot produce a critique flagging a case as "validated" or "production ready" — even via monkeypatched LLM response (envelope refuses).
- A:-5 — Stub-advisor tests cannot bypass the LLM-advisor coverage: each backend has its own forbidden-claim test.

**E-axis (4):**
- E:-2 — Gate ordering on advisor route: case_id pattern → snapshot existence → advisor invocation. Tested in order.
- E:-3 — HTTP integration walks real ASGI stack via `httpx.ASGITransport`, not a mock.
- E:-4 — Each E2E journey crosses ≥3 routes.
- E:-5 — Advisor-offline E2E proves the workbench is LLM-offline-functional. This is the load-bearing demonstration of the "AI is advisor not driver" principle.

---

## 5. Test Auditor Agent (TAA) protocol

Same as Phase 10. Each slice spawned with a `general-purpose` background subagent given:
- Slice commit SHA.
- Blueprint section + per-slice rubric subset.
- Prior TAA APPROVE reports.
- Independent re-run instructions (backend full sweep + frontend full sweep + grep guards).

TAA returns a structured Markdown report archived at `.planning/phase11_audit_reports/<X>.md`.

FINAL whole-arc TAA spawned after slice G. The V-axis 13/13 is gated on its APPROVE.

---

## 6. Stop condition

≥99 / 100 cumulative AND every axis ≥95% of its weight (= every axis at ≥95% of its weight slot — same as Phase 10).

Same honest scoring rule: pre-FINAL score includes V-axis holdback (~6.5/13). FINAL TAA APPROVE raises V to 13/13.

---

## 7. Execution cadence

| Slice | Estimated commits | Estimated edits |
|---|---:|---:|
| Plan (this file) | 1 | 1 |
| A — multi-analysis rubric | 1 | 6-8 |
| B — advisor schema + stub | 1 | 4-6 |
| C — LLM advisor + offline | 1 | 4-6 |
| D — HTTP routes | 1 | 4-6 |
| E — frontend AdvisorPanel | 1 | 4-6 |
| F — integration + E2E | 1 | 3-4 |
| G — STATE + retro + FINAL | 2 | 3-4 |

Background TAAs spawned per slice; results archived; STATE stamped after FINAL APPROVE.

---

## 8. Closure invariants (must hold at slice G close)

- Backend full sweep ≥1916 + Phase 11 added tests passing.
- Frontend full sweep ≥77 + Phase 11 added tests passing.
- HF1 forbidden-zone untouched.
- No `^GS-\d{3}$` write.
- No real OpenRadioss invocation.
- Tier 1 disclaimer trio on every new response shape.
- Forbidden-claim envelope audit extended; tests pin every new token individually.
- Four-question gate audit on every advisor critique.
- LLM-offline workbench E2E demonstrably functional.
- Branch is local (no push); no Linear / Notion write.
- FINAL whole-arc TAA APPROVE archived at `.planning/phase11_audit_reports/FINAL.md`.
- STATE.md stamp advances; retrospective written.
