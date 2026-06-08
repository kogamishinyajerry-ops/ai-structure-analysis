# FM-04a Phase 7 — Trust Closure & Honest 99-Score Gate

> **Tier 1 engineering candidate; not signed validation; not benchmark agreement.**
>
> **Blueprint stamp:** `fm04a-phase7-trust-closure-2026-05-16`
> **Branch:** `claude/FM-04a-tier1-ballistic-candidate@<plan>`
> **Authoring authority:** local Claude Opus 4.7 under direct-execution authorization with explicit "iterate until ≥99/100, with absolute honest scoring" mandate. No FM-04b prerequisite crossed.

---

## 1. North Star

Phase 6 closed at 95/100 with five deliberate carry-forwards on file. Phase 7 retires that escape hatch.

A reviewer at Phase 7 close can answer all three Phase 6 questions AND:

4. **"Did this case ever degrade?"** — a regression-alarm surface that walks the timeline and emits structured events when the trust score drops by more than a configurable threshold.
5. **"Can a Chinese-language reviewer use it?"** — the narrative renderer is locale-parametrized; en-US (existing 16 templates) + zh-CN (pilot of the same 16) ship.
6. **"What if the formula is wrong?"** — property-based tests prove every axis is in-bounds across the input space; a formula-sensitivity test pins the relationship between weight perturbation and score delta.
7. **"Does the UI actually render correctly?"** — a headless frontend smoke harness (vitest + jsdom) mounts the three Phase 6 E components against in-memory fetch stubs and asserts on rendered DOM.
8. **"Who checked the work?"** — every sub-phase commit is independently audited by a Test Auditor Agent (TAA) whose report is archived at `.planning/phase7_audit_reports/<slice>.md` and whose findings are deductions in the SCORECARD.

Plus the Phase 6 carry-forward §1 closure: `convergence_study.json` is now copied into `snapshots/<label>/convergence/<case>.json`, so the timeline + diff recover the convergence verdict from the captured file directly (not from a `convergence_summary` inline block in metrics). MINOR bump on `COHORT_SNAPSHOT_MANIFEST_SCHEMA_VERSION` (1.1.0 → 1.2.0).

---

## 2. Scope boundaries (non-negotiable; carried forward verbatim)

- Tier 1 engineering candidate ONLY. Wording `not signed validation` and `not benchmark agreement` must round-trip through every emitted manifest, every HTTP body, every UI panel header.
- No FM-04b prerequisite crossed: no ADR-024 full, no `benchmark_comparison_candidate.json`, no sealed packet, no signed validation language, no `^GS-\d{3}$` registry flip.
- No edits inside `^GS-\d{3}$` signed-registry directories (only `*-candidate` paths in test fixtures, all under `tmp_path`).
- No edits inside the HF1 hard-stop zone (`agents/solver.py`, `agents/router.py`, `agents/geometry.py`, `schemas/sim_state.py`, `tests/test_toolchain_probes.py`, `Dockerfile`, `Makefile`, `golden_samples/` prefix outside `*-candidate`, `scripts/hf1_path_guard.py`, `.github/workflows/`).
- No real OpenRadioss solver invocation. CI / dev path stays synthetic.
- No Linear / Notion writes. No push, no PR. Trailer rewrite for any future PR remains a human-user action.

Forbidden positive claims (must NEVER appear, except in `not <claim>` disclaimer form): `validated against`, `benchmark agreement`, `signed validation`, `perforation completed`, `bullet-through-steel complete`, `validated physics`.

Phase-7-specific additional constraints:

- **Trust score regression alarms are advisory, not signoff.** Every alarm payload carries the Tier 1 disclaimer trio + a `claim_impact` explicitly stating "alarms surface candidate drift; they do NOT authorize Tier 2 promotion or reject signed validation".
- **Locale templates are fixed translations, not LLM output.** zh-CN templates are pre-translated strings with the same slot structure as en-US; the `NarrativeRenderer` swaps catalogs but never calls a translation model.
- **Property-based tests must use seeded strategies.** All Hypothesis tests declare `derandomize=True` or use a fixed seed so failures are reproducible across runs.
- **Headless frontend tests do NOT spin up a real backend.** They use `fetch` stubs / MSW so the smoke harness stays deterministic and hermetic.
- **The TAA audit is a hard gate.** A sub-phase commit's claimed SCORECARD is provisional until the TAA returns APPROVE or until every TAA finding has a follow-up fix commit (or an explicit reject + reason logged in the TAA report).

---

## 3. Sub-phase plan

### 3.A — Convergence snapshot capture + MINOR bump

Extend `cohort_snapshot.write_cohort_snapshot` to copy each case's live `convergence_study.json` into `snapshots/<label>/convergence/<case>.json` alongside the existing `completeness/<case>.json` + `reproducibility/<case>.json` + `metrics/<case>.json`.

- Bump `COHORT_SNAPSHOT_MANIFEST_SCHEMA_VERSION` from `1.1.0` to `1.2.0` (MINOR, additive). Document the bump in the `_schema_versions.py` bump-history block.
- Extend `cohort_snapshot_diff._extract_convergence_verdict()` to also accept the captured `convergence/<case>.json` (priority order: captured convergence file → inlined `convergence_summary` in metrics → None).
- Extend `trust_score_timeline._build_point()` similarly: prefer the captured convergence file when present.
- Backward-compatible: when reading an older (1.1.0) snapshot without a `convergence/` directory, the diff and timeline fall back to the existing behavior.

Deliverables:
- `backend/app/services/reporting/cohort_snapshot.py` — write `convergence/<case>.json`
- `backend/app/services/reporting/cohort_snapshot_diff.py` — recover verdict from captured convergence file
- `backend/app/services/reporting/trust_score_timeline.py` — score convergence axis when captured file present
- `_schema_versions.py` — bump + bump-history note
- Tests: ≥8 new (snapshot writes file, diff recovers verdict, timeline scores axis, 1.1.0 fallback)

### 3.B — Locale-parametrized narrative templates

Refactor `snapshot_narrative.py` so each template emits via a `NarrativeRenderer` that selects from a per-locale catalog. Two catalogs ship:

- `en-US` — the existing 16 English templates (verbatim, unchanged behavior).
- `zh-CN` — pilot Chinese catalog covering the same 16 templates with the same `template_id` + `severity`, with translated slot-fill sentences (e.g. `Residual velocity changed from {a:g} to {b:g} m/s ({delta_pct:+.2f}%)` → `残余速度从 {a:g} 改变到 {b:g} m/s ({delta_pct:+.2f}%).`).

Endpoint adds `?locale=en-US|zh-CN` (default `en-US`); unknown locale → 400.

- `_assert_no_overclaim` runs per locale so a translation mistake cannot smuggle in a forbidden positive claim.
- Each locale's 16 templates have a dedicated positive test (32 new tests).

Deliverables:
- `backend/app/services/reporting/snapshot_narrative.py` refactor
- `backend/app/services/reporting/snapshot_narrative_catalogs/{en_us,zh_cn}.py` (or single file with two dicts; keep at module scope so import-time validation runs)
- `frontend/src/snapshotNarrativeClient.ts` — accepts optional `locale` param
- `frontend/src/components/DriftNarrativePanel.tsx` — optional locale selector
- Tests: ≥32 (16 templates × 2 locales) + locale-rejection test + cross-locale forbidden-claim audit

### 3.C — Trust score regression alarm endpoint

`backend/app/services/reporting/trust_score_alerts.py`:

- `build_trust_score_alerts(case_id, repo_root, threshold_delta=10) -> TrustScoreAlertReport`:
  - Walks the case's trust-score timeline (oldest-first).
  - For each adjacent pair, computes `delta = older.trust_score - newer.trust_score`.
  - If `delta > threshold_delta`, emits an alert with severity `info` (10 ≤ delta < 25) / `warn` (25 ≤ delta < 40) / `danger` (delta ≥ 40).
  - Per-axis contribution: which axis(es) shifted the most.

```json
{
  "schema_version": "1.0.0",
  "case_id": "GS-A-candidate",
  "claim_tier": "Tier 1 engineering candidate",
  "claim_boundary": "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement",
  "threshold_delta": 10,
  "alert_count": 1,
  "alerts": [
    {
      "from_snapshot": "2026-05-16T100000Z",
      "to_snapshot": "2026-05-16T200000Z",
      "from_trust_score": 87,
      "to_trust_score": 65,
      "delta": 22,
      "severity": "info",
      "primary_axis_shift": "reproducibility_clean",
      "axis_deltas": {"completeness": 0, "convergence_stability": 0, "energy_audit_closure": 0, "reproducibility_clean": -22}
    }
  ],
  "claim_impact": "Tier 1 candidate trust score regression alerts only; not signed validation; not benchmark agreement. Alerts surface candidate drift; they do NOT authorize Tier 2 promotion or reject signed validation."
}
```

`/api/v1/trust-score-alerts/<case-id>?threshold_delta=N` returns the rendered JSON. Threshold defaults to 10, clamped to `[1, 100]`. Invalid case_id → 400.

Deliverables:
- `backend/app/services/reporting/trust_score_alerts.py`
- `backend/app/api/routes/trust_score_alerts.py`
- `TRUST_SCORE_ALERTS_SCHEMA_VERSION = "1.0.0"` in `_schema_versions.py`
- `frontend/src/trustScoreAlertsClient.ts`
- `frontend/src/components/TrustScoreAlertsPanel.tsx` (mounted in App.tsx alongside the timeline)
- Tests: ≥10 (severity buckets, primary_axis_shift correctness, no-alerts-when-stable, threshold boundary, claim disclaimer round-trip)

### 3.D — Property-based testing + formula sensitivity

Add `hypothesis` to test dev dependencies. Property strategies pin invariants the formula must satisfy regardless of input:

- For every `TrustScoreInputs` generated from the strategy, the returned `trust_score` is in `[0, 100]`.
- For every breakdown entry, `weighted ≤ weight` and `raw_score ∈ [0, 100]`.
- Sum of `weighted` across breakdown equals `trust_score`.
- The weight constants sum to 100 (already pinned, now redundantly proven across the input space).

Formula sensitivity test (deterministic, not Hypothesis):
- Construct a `TrustScoreInputs` with known scores (e.g. completeness 80, convergence 100, energy 100, reproducibility 100).
- Manually perturb a weight constant in a controlled test (monkeypatch the module attribute) and assert the score delta matches the expected mathematical delta.
- Document the test as the "rebalance methodology" referenced in Phase 6 carry-forward §5.

Deliverables:
- `pyproject.toml` test extras include `hypothesis>=6.0`
- `tests/test_trust_score_properties.py` — ≥6 property-based tests with seeded strategies
- `tests/test_trust_score_formula_sensitivity.py` — ≥4 sensitivity / rebalance methodology tests
- The trust score module's docstring grows a "Sensitivity & Rebalance Methodology" section pointing at the new test file

### 3.E — Headless frontend smoke harness (vitest + jsdom)

- Add dev deps: `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `jsdom`, `@types/node`-ext as needed
- Add `vitest.config.ts` with jsdom environment and a setup file
- Add `"test"` npm script wired to `vitest run`
- Tests:
  - `TrustScoreGauge.test.tsx`: renders exact integer score (no rounding); tone classes based on threshold; breakdown table column count
  - `DriftNarrativePanel.test.tsx`: severity-pill DOM; lines grouped by severity; empty-state copy
  - `TrustScoreTimelineChart.test.tsx`: SVG path generated from points; gridlines rendered at 80 + 50; per-snapshot table shape

Stubs / mocks use a thin `vi.fn()` over `fetch`; no real backend; no real network.

Deliverables:
- `frontend/vitest.config.ts`, `frontend/test/setup.ts`, `frontend/test/**/*.test.tsx`
- `frontend/package.json` `"test": "vitest run"`
- Tests: ≥12 new, all pass under `npm test`

### 3.F — Test Auditor Agent (TAA) integration + audit reports archive

After each sub-phase A/B/C/D/E commit, spawn a `general-purpose` subagent with this standardized TAA prompt template:

```text
You are the Test Auditor Agent for FM-04a Phase 7 sub-phase <slice>.

Mission: independently audit commit <SHA> against the Phase 7 binding rubric.
Do NOT trust any SCORECARD claim in the commit message; audit from scratch.

Read first:
- The commit diff via `git show <SHA>`
- The sub-phase plan in .planning/FM-04A_PHASE7_BLUEPRINT.md §3.<slice>
- The 9-axis rubric in §4
- The Phase-7-specific anti-gaming guards in §4

For each axis B/M/T/C/X/D/A/E/V, decide APPROVE / FLAG / BLOCK with at least
one citation (file:line or test name).

Specifically check:
1. Every code path the diff adds is covered by a test.
2. Every claim the diff makes about Tier 1 disclaimer + forbidden-claim
   audit + schema_version stamping is independently verifiable.
3. No anti-gaming guard from §4 should have triggered but didn't.
4. No "validated against" / "perforation completed" / "bullet-through-steel
   complete" / "validated physics" snuck in.
5. Pure builder + thin Response route patterns are honored.
6. Phase 7 carry-forward closures (where this slice claims to close one)
   actually close them — verify against the explicit Phase 6 retrospective
   §"Carry-forward into Phase 7 (or beyond)" list.

Report format (write to .planning/phase7_audit_reports/<slice>.md):

  ## TAA report — Phase 7 <slice> @ <SHA>
  ### Axis verdicts
  - B: APPROVE | FLAG | BLOCK — <one-line citation>
  - M: ...
  - (every axis B/M/T/C/X/D/A/E/V)

  ### Defects
  Severity-sorted list, each: (severity, file:line, finding, recommended fix)

  ### Carry-forward closure status (if applicable)
  Each Phase 6 carry-forward referenced; status: CLOSED / PARTIAL / NOT_TOUCHED

  ### Overall verdict
  APPROVE | CHANGES_REQUIRED

Be honest. Do NOT mark APPROVE just because the commit author wants it.
Do NOT lower severity to be polite. The point is independent verification,
not validation theater. Report ≤2000 tokens.
```

Spawn protocol:
- Slice closes → main session writes commit
- Main session spawns TAA via `Agent` tool (`subagent_type=general-purpose`) with the slice / SHA filled in
- TAA's report lands at `.planning/phase7_audit_reports/<slice>.md` (TAA writes directly; main session retrieves)
- For every BLOCK or HIGH-severity FLAG, main session either:
  - Lands a follow-up fix commit (preferred), then re-spawns TAA → expects APPROVE
  - Logs an explicit reject + reason in the TAA report (only if the TAA was wrong on a verifiable point)
- The V-axis score is the count of BLOCK/HIGH findings closed vs. left open

Deliverables:
- `.planning/phase7_audit_reports/` directory with one report per slice
- The blueprint's §6 "TAA invocation log" tracks each spawn

### 3.G — HTTP integration + E2E

- `tests/test_phase7_endpoints_integration.py` — ≥14 tests:
  - alarms endpoint: stamped payload + severity buckets + no-alarms-when-stable + threshold clamping + invalid case_id rejection + Tier 1 disclaimer round-trip
  - narrative endpoint with `?locale=`: en-US default + zh-CN render + unknown-locale rejection + cross-locale forbidden-claim audit
  - snapshot diff after Phase 7 A: verdict recovered from captured `convergence/<case>.json`
- `tests/test_fm04a_phase7_trust_workflow_e2e.py` — 3 E2E tests:
  - convergence recovery flow (write snapshot with `convergence/<case>.json`, fetch timeline, assert non-zero convergence_weighted because verdict was captured)
  - locale roundtrip flow (write two snapshots with drift, fetch zh-CN narrative, assert specific Chinese sentence + Tier 1 disclaimer in zh-CN form)
  - regression alarm flow (write 3 snapshots with monotonically degrading trust score, fetch alarms, assert exactly 2 alarms with correct severity ladder + primary_axis_shift)

### 3.H — STATE + retrospective + final TAA pass

- `.planning/STATE.md` stamp advance + Phase 7 ledger.
- `.planning/retrospectives/fm04a_phase7_trust_closure.md` — axis-by-axis SCORECARD citing TAA verdicts per slice.
- Final whole-arc TAA pass: spawn TAA against `HEAD` with §3.F protocol but with `<slice>` = `final`; the report's overall verdict must be APPROVE before the retrospective claims ≥99/100. Otherwise, iterate (more fix commits, re-spawn TAA) until APPROVE.

---

## 4. Binding 9-axis scoring rubric (Phase 7 specialization)

Weight totals 100. **Stop condition: ≥99 total AND every axis ≥95 % of its weight.** This is tighter than the Phase 5/6 rubric (95 / 90% ladder) on purpose.

| Axis | Weight | Phase 7 specialization |
|------|--------|------------------------|
| **B — schema versioning** | 12 | Every new emitted contract stamps `schema_version`; Phase 7 A bump (snapshot manifest 1.1.0 → 1.2.0) cited in bump-history; trust-score-alerts carries its own `schema_version = "1.0.0"`. |
| **M — module quality** | 12 | New builders pure (`trust_score_alerts.py`, `snapshot_narrative_catalogs/*`); new routes thin (`Response(content=…)`); locale catalog stays at module scope so import-time validation runs; no inline magic numbers (alert severity boundaries are named constants). |
| **T — testing depth** | 15 | ≥6 property-based tests + ≥4 sensitivity tests + ≥12 headless frontend tests + per-axis HTTP integration tests; sum-to-100 constants test still pins formula weights; every alarm severity bucket has a positive test. |
| **C — claim-tier discipline** | 12 | Tier 1 disclaimer trio round-trips through every new HTTP body in *every locale*; cross-locale forbidden-claim audit; HF1 path guard clean on every commit; no `^GS-\d{3}$` registry edit. |
| **X — frontend integration** | 12 | New `trustScoreAlertsClient` preserves `schemaVersion`; vitest + jsdom harness runs ≥12 component tests; `npm test` is the new CI/dev verification command alongside `tsc -b`. |
| **D — documentation / SSOT** | 8 | `_schema_versions.py` bump-history grows for 1.2.0; trust score module docstring gains "Sensitivity & Rebalance Methodology" pointer to the sensitivity test file; locale catalog documented in the narrative module docstring. |
| **A — anti-gaming discipline** | 8 | Phase-7 anti-gaming guards published in §4 below BEFORE first code commit; every TAA finding (BLOCK or HIGH) closed by a fix commit or explicit + reasoned reject; SCORECARD deductions cite TAA report sections, not author intent. |
| **E — end-to-end workflow** | 8 | 3 new E2E tests (convergence recovery / locale roundtrip / regression alarm); each composes with at least one Phase 5/6 endpoint to prove the seven-surface stack still composes after Phase 7 additions. |
| **V — verification independence** | 13 | A standardized TAA report exists at `.planning/phase7_audit_reports/<slice>.md` for every sub-phase A–E AND for the final pass; every BLOCK / HIGH-severity finding has a closed follow-up; the final TAA pass returns APPROVE with no open BLOCKs. |

Phase-7-specific anti-gaming guards (applied to the cumulative state at each SCORECARD):

- **B: -3 if the snapshot manifest 1.2.0 bump is undocumented in `_schema_versions.py` bump-history.**
- **B: -2 if `TRUST_SCORE_ALERTS_SCHEMA_VERSION` is inline-magic-numbered instead of imported from `_schema_versions.py`.**
- **M: -3 if alarm severity thresholds (10 / 25 / 40) are inline-magic-numbered instead of named constants.**
- **M: -3 if the locale catalog is created via runtime `if locale == 'zh-CN'` branches instead of a dict-based dispatch.**
- **T: -2 per axis whose property-based test does not include a `derandomize=True` or fixed-seed declaration.**
- **T: -3 if any frontend component is mounted in `App.tsx` without a vitest test file covering its render path.**
- **T: -2 per E2E test that does not assert the Tier 1 disclaimer trio in the HTTP response body.**
- **C: -5 if a forbidden positive claim appears in the zh-CN catalog** (must NEVER appear, not even in `not <claim>` form, since zh-CN translation conventions differ).
- **C: -3 per locale that does not run `_assert_no_overclaim` at module import time.**
- **X: -3 if the vitest harness is configured but not wired into `npm test`** (a harness that does not run is no harness).
- **A: -4 if any TAA finding marked BLOCK is left open at the time of the final SCORECARD** (this is the hard gate; the score cannot reach 99 with an open BLOCK).
- **A: -2 if the TAA report file does not actually exist** at the expected `.planning/phase7_audit_reports/<slice>.md` path.
- **V: -5 per sub-phase A–E that lacks a TAA report file.**
- **V: -3 if the final TAA pass returns CHANGES_REQUIRED** but the retrospective claims ≥99/100 anyway.
- **D: -2 if the Phase 6 retrospective §"Carry-forward into Phase 7" list is not explicitly cross-referenced in the Phase 7 retrospective with closure status per item.**

---

## 5. Commit cadence + SCORECARD discipline

Each sub-phase closes with one commit carrying a SCORECARD block. Re-scoring at sub-phase close re-evaluates *all* axes against cumulative state. After each commit, the TAA is spawned; if any BLOCK or HIGH-severity FLAG is returned, the score is provisionally lowered until the next fix commit closes the finding. Scores cannot go up without either a commit fixing the cited defect or a TAA re-spawn that explicitly retracts the finding (with reason logged).

Stop condition restated: **cumulative ≥99 total AND every axis ≥95 % of its weight at the same slice, AND the final whole-arc TAA pass returns APPROVE with zero open BLOCKs**.

If the final TAA pass returns CHANGES_REQUIRED, Phase 7 is not closed. Iterate (more fix commits, re-spawn TAA) until APPROVE. There is no "deliberate scope cut" escape hatch in Phase 7.

---

## 6. TAA invocation log

| Slice | Commit SHA | TAA report path | Verdict | Open findings |
|-------|-----------|-----------------|---------|----------------|
| A | TBD | `.planning/phase7_audit_reports/A.md` | TBD | TBD |
| B | TBD | `.planning/phase7_audit_reports/B.md` | TBD | TBD |
| C | TBD | `.planning/phase7_audit_reports/C.md` | TBD | TBD |
| D | TBD | `.planning/phase7_audit_reports/D.md` | TBD | TBD |
| E | TBD | `.planning/phase7_audit_reports/E.md` | TBD | TBD |
| G | TBD | `.planning/phase7_audit_reports/G.md` | TBD | TBD |
| final | TBD | `.planning/phase7_audit_reports/final.md` | TBD | TBD |

This table is updated in-place as each slice closes. The Phase 7 retrospective treats this log as the canonical record of independent verification.

---

## 7. Non-goals

- No LLM-driven translation for zh-CN templates; the catalog is hand-written and reviewed for forbidden-claim leakage.
- No alerting transport (email / Slack / webhook); the alarm endpoint is a passive surface a reviewer polls.
- No browser-driven E2E (Playwright / Cypress); the headless smoke harness is vitest + jsdom only.
- No move from `_SyncASGIClient` to `TestClient`; the existing shim is the supported migration path for httpx ≥ 0.28.
- No FM-04b prerequisite crossed. Trust score regression alarms are NOT a substitute for the sealed packet; the `claim_impact` string says so explicitly on every emitted alert payload.
- No retroactive rescoring of Phase 5 / 6. Those retrospectives stay at 95/100; Phase 7's 99-target applies only to Phase 7 deliverables + carry-forward closures.

---

## 8. Phase 7 carry-forward closure map

Cross-reference for the A-axis deduction guard. Each Phase 6 carry-forward maps to a Phase 7 slice that closes it:

| Phase 6 carry-forward | Phase 7 slice | Closure mechanism |
|----------------------|---------------|-------------------|
| §1 convergence snapshot capture | **A** | `convergence/<case>.json` captured; manifest 1.1.0 → 1.2.0 |
| §2 headless frontend smoke | **E** | vitest + jsdom harness with ≥12 component tests wired into `npm test` |
| §3 narrative templates English-only | **B** | en-US + zh-CN catalogs; endpoint `?locale=` |
| §4 trust score regression alarm | **C** | `/api/v1/trust-score-alerts/<case-id>` with severity ladder |
| §5 weight balance opinionated | **D** | Property-based invariants + formula sensitivity test as documented "rebalance methodology" |

A Phase 7 SCORECARD that claims ≥99 must show all five rows are CLOSED in the final TAA report's "Carry-forward closure status" section.
