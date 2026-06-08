# FM-04a Phase 8 — Reviewer Accountability & Provenance Closure (Honest 99-Score Gate)

> **Tier 1 engineering candidate; not signed validation; not benchmark agreement.**

**Status:** Plan. Authored 2026-05-16 under direct-execution authorization. This blueprint is binding. Every Phase 8 slice commits against the 9-axis rubric in §4 and the 17 anti-gaming guards in §4. Every code slice goes through an independent **Test Auditor Agent (TAA)** before its SCORECARD is trusted. Final whole-arc TAA pass gates closure at ≥99/100.

Phase 8 is the natural sequel to Phase 7 (`fm04a-phase7-trust-closure-2026-05-16 · @9dae909`, closed at 100/100 with zero waivers). Phase 7 made trust **measurement** transparent; Phase 8 makes reviewer **judgments** about that measurement persistent, auditable, and provenance-traceable — without crossing the FM-04b Tier 2 line.

---

## 1. North Star

A reviewer opens the workbench today and sees: trust score gauge, history timeline, regression alerts, drift narrative (en-US or zh-CN), exact-integer breakdown across 4 axes. They form a judgment — "GS-A-candidate needs more convergence work" — and then **have nowhere to put that judgment**. The next session has no idea who reviewed what when with what verdict. The trust score is honest about its arithmetic but blind to its own consumers.

Phase 8 closes that gap:

1. **"Did anyone review this candidate yet?"** — `/api/v1/signoff-history/<case-id>` returns chronological signoff records per `*-candidate` case. Each record carries reviewer identifier, UTC timestamp, verdict from a restricted whitelist (`watching` / `needs_more_evidence` / `needs_more_convergence` / `blocked_pending_input`), free-text notes (audited for forbidden positive claims), and a stamped schema version. **The verdict whitelist deliberately excludes every Tier 2 promotion verb.** A signoff record cannot say "ready for FM-04b" or "ready for signed validation" or "benchmark agreement reached" — those constructions fail the import-time audit.
2. **"Exactly what produced this 87?"** — `/api/v1/trust-score-provenance/<case-id>?snapshot=<label>` walks back to every input SHA (metrics file, convergence file, completeness file, generator script) plus `formula_version` and evaluation timestamp, so a reviewer can deterministically reproduce the score.
3. **"What's the cohort look like at a glance?"** — `/api/v1/cohort-executive-summary` aggregates trust score + alarm count + signoff state across all `*-candidate` cases into a one-page reviewer scorecard with `healthy` / `watching` / `regressed` buckets.
4. **"Which case is statistically an outlier?"** — `/api/v1/cohort-anomalies` computes per-axis z-score within cohort and flags cases >2σ from mean on any axis. Severity bucketed. Explicit `claim_impact`: "anomalies surface statistical outliers; they do NOT diagnose root cause or authorize Tier 2 promotion."

Phase 8 is **strictly Tier 1 engineering candidate** scope. It introduces zero new Tier 2 prerequisites. It does NOT touch `^GS-\d{3}$` signed-registry directories. It does NOT promote any candidate. Every emitted manifest preserves the Tier 1 disclaimer trio. The signoff verdict whitelist is the load-bearing safety mechanism — an import-time audit verifies no Tier 2 promotion verb sneaks into the whitelist or into a signoff notes body.

## 2. Phase 7 carry-forward closure map

The Phase 7 retrospective documented 6 carry-forwards. Phase 8 either closes them or honestly defers:

| Phase 7 carry-forward | Phase 8 disposition |
|------------------------|---------------------|
| §1 Add additional locale beyond en-US / zh-CN | **Deferred** — no business signal yet; the catalog architecture already supports addition. Carry-forward to Phase 9+. |
| §2 Severity ladder beyond 3 buckets (info/warn/danger) | **Closed implicitly by §4 cohort anomaly** — anomaly detection adds a 4th-bucket severity dimension orthogonal to delta-threshold alerts. Not a literal `critical` bucket but a richer overall signal. |
| §3 Property-based test budget (25 → 100 examples) | **Deferred** — runtime concern, not correctness concern. Carry-forward. |
| §4 Frontend vitest harness widening | **Partially closed by §5** — Phase 8 adds tests for new components (`SignoffHistoryPanel`, `CohortExecutiveSummaryPanel`, `CohortAnomaliesPanel`) under the same vitest harness. |
| §5 TAA-G RE-AUDIT 2 LOWs | **Already closed in Phase 7 slice H** (`9dae909`). |
| §6 `convergence_summary` metrics-inlined deprecation | **Deferred** — destructive removal, needs explicit deprecation cycle. Carry-forward. |

## 3. Sub-phases

### 3.A — Tier 1 signoff record builder (3-5 LOC contract surface)

`backend/app/services/reporting/signoff_record.py` (NEW):

- `SignoffVerdict = Literal["watching", "needs_more_evidence", "needs_more_convergence", "blocked_pending_input"]` — **whitelisted** at module top; any addition requires updating the import-time audit.
- `_FORBIDDEN_VERDICT_TOKENS = ("tier_2", "tier 2", "signed_validation", "benchmark_agreement", "promoted", "ready_for_fm04b")` — import-time `_audit_verdict_whitelist()` asserts no whitelist entry contains any forbidden token; any future maintainer who tries to add `"ready_for_tier_2"` fails import, not runtime.
- `write_signoff_record(case_id, reviewer, verdict, notes, *, repo_root)` writes `reports/signoffs/<case_id>/<utc>.json` (UTC ISO 8601 filename); refuses to write inside `golden_samples/**` or any `^GS-\d{3}$` registry path; `_assert_no_overclaim(notes)` audits the free-text body for the standard 6-token forbidden list.
- `read_signoff_history(case_id, repo_root)` returns chronological `list[SignoffRecord]` parsed from disk; tolerant of empty dir (returns `[]`); tolerant of older 1.0.0 records when 1.1.0 ships.
- `SIGNOFF_RECORD_SCHEMA_VERSION = "1.0.0"` added to `_schema_versions.py` with bump-history block.

Deliverables: `signoff_record.py`, `tests/test_phase8_signoff_record.py` (≥12 tests including verdict-whitelist audit, notes audit, golden_samples write rejection, registry write rejection, chronological ordering, schema stamping).

### 3.B — signoff history endpoint + frontend

`backend/app/api/routes/signoff_history.py` (NEW):

- `GET /api/v1/signoff-history/<case-id>` returns full chronological history with envelope (`schema_version`, `claim_tier`, `claim_boundary`, `claim_impact`, `case_id`, `record_count`, `records`).
- `case_id` validated by existing `_assert_candidate_case_id` pattern (refuses `^GS-\d{3}$`).
- `claim_impact` explicitly says "Tier 1 candidate review judgments only; do NOT authorize Tier 2 promotion".

`frontend/src/signoffHistoryClient.ts` (NEW) — typed client with `SUPPORTED_SIGNOFF_VERDICTS` re-exported for UI dropdown rendering (component does not hardcode the list).

`frontend/src/components/SignoffHistoryPanel.tsx` (NEW) — chronological list with verdict pill, reviewer, timestamp, notes. Tone helper maps verdict → tone (`watching`=info, `needs_more_*`=warn, `blocked_*`=danger). Mounted in `App.tsx` next to `TrustScoreGauge`.

`TrustScoreGauge` extended to surface a "Latest signoff: <verdict> by <reviewer> at <utc>" subline when a signoff exists; absence-state shows nothing (no false-positive "needs review" prompt — reviewers decide; the system records).

Deliverables: route, client, panel, gauge subline, `tests/test_phase8_signoff_history_endpoint.py` (≥6 backend tests), `frontend/test/SignoffHistoryPanel.test.tsx` (≥5 vitest tests).

### 3.C — provenance trace endpoint

`backend/app/services/reporting/trust_score_provenance.py` (NEW):

- `build_trust_score_provenance(case_id, snapshot_label, repo_root)` returns dict with:
  - `case_id`, `snapshot_label`, `evaluation_utc`
  - `inputs`: `[{kind: "metrics", path: <rel>, sha256: <hex>, present: bool}, ...]` for metrics / convergence / completeness / reproducibility / generator
  - `formula_version` (read from `_schema_versions.py`)
  - `trust_score`, `axes` (recomputed from frozen snapshot bytes — same code path as Phase 6 D timeline reader)
  - `claim_tier`, `claim_boundary`, `claim_impact`, `schema_version`
- All SHA-256s computed from frozen snapshot bytes (not live evidence); a reviewer reading provenance gets exactly what the trust score arithmetic saw, not a moving target.

`backend/app/api/routes/trust_score_provenance.py` (NEW) — `GET /api/v1/trust-score-provenance/<case-id>?snapshot=<label>`. Snapshot label validated against `reports/snapshots/<label>/manifest.json` existence; 404 if not found.

`TRUST_SCORE_PROVENANCE_SCHEMA_VERSION = "1.0.0"`.

Deliverables: builder + route + `frontend/src/trustScoreProvenanceClient.ts` (lightweight typed client; no panel — provenance is reviewer's deep-dive tool, not surfaced in main UI), `tests/test_phase8_trust_score_provenance.py` (≥10 tests including SHA determinism, missing input handling, 404 on bad snapshot label, schema stamping).

### 3.D — cohort executive summary endpoint + panel

`backend/app/services/reporting/cohort_executive_summary.py` (NEW):

- Walks `golden_samples/*-candidate/` (defense in depth: rejects `^GS-\d{3}$` shape at scanner level).
- For each case, reads latest trust score + latest alarm count + latest signoff verdict.
- Buckets each case into:
  - `healthy` — trust score ≥ 80 AND no warn/danger alarms in latest 2 snapshots AND no `blocked_*` signoff
  - `watching` — trust score 50-79 OR has `watching` signoff OR has info-level alarms
  - `regressed` — trust score < 50 OR has warn/danger alarms OR has `blocked_pending_input` signoff
- Returns aggregate counts + per-case rows; explicit `claim_impact`: "cohort summary surfaces candidate population health; it does NOT promote any case to Tier 2 or substitute for signed validation".

`backend/app/api/routes/cohort_executive_summary.py` (NEW) — `GET /api/v1/cohort-executive-summary`.

`COHORT_EXECUTIVE_SUMMARY_SCHEMA_VERSION = "1.0.0"`.

`frontend/src/cohortExecutiveSummaryClient.ts` + `frontend/src/components/CohortExecutiveSummaryPanel.tsx` — top-of-Visual-tab panel showing 3 bucket counters + drill-down case list with per-case tone badges.

Deliverables: builder + route + client + panel, `tests/test_phase8_cohort_executive_summary.py` (≥8 backend tests), `frontend/test/CohortExecutiveSummaryPanel.test.tsx` (≥4 vitest tests).

### 3.E — cohort anomaly detection (per-axis z-score)

`backend/app/services/reporting/cohort_anomalies.py` (NEW):

- For each `*-candidate` case + each of the 4 trust-score axes (completeness, convergence, energy_audit, reproducibility), compute axis-weighted score; gather across cohort; compute mean + standard deviation; flag any case whose axis-score is >2σ from cohort mean.
- Returns `AnomalyReport(case_id, axis, score, cohort_mean, cohort_stdev, z_score, severity)` per flagged (case, axis) pair.
- Severity buckets:
  - `info` — 2σ ≤ |z| < 3σ
  - `warn` — 3σ ≤ |z| < 4σ
  - `danger` — |z| ≥ 4σ
- `claim_impact`: "anomalies surface statistical outliers from cohort mean; they do NOT diagnose root cause, validate physics, or authorize Tier 2 promotion".
- Handles edge cases honestly:
  - cohort of 1 case → no anomalies (stdev undefined; return empty)
  - cohort of 2 cases → no anomalies (insufficient for z-score; return empty)
  - cohort ≥ 3 → compute normally
- Named module constants: `ANOMALY_SIGMA_INFO_MIN = 2.0`, `ANOMALY_SIGMA_WARN_MIN = 3.0`, `ANOMALY_SIGMA_DANGER_MIN = 4.0`, `COHORT_MIN_SIZE_FOR_ANOMALY = 3`.

`backend/app/api/routes/cohort_anomalies.py` (NEW) — `GET /api/v1/cohort-anomalies`.

`COHORT_ANOMALIES_SCHEMA_VERSION = "1.0.0"`.

`frontend/src/cohortAnomaliesClient.ts` + `frontend/src/components/CohortAnomaliesPanel.tsx` — surfaces flagged outliers grouped by severity.

Deliverables: builder + route + client + panel + property-based tests for z-score arithmetic, `tests/test_phase8_cohort_anomalies.py` (≥10 tests), `tests/test_phase8_cohort_anomalies_properties.py` (≥4 Hypothesis tests with `derandomize=True`), `frontend/test/CohortAnomaliesPanel.test.tsx` (≥4 vitest tests).

### 3.F — HTTP integration + E2E + TAA closure

`tests/test_phase8_endpoints_integration.py` — **≥16 tests**:

- signoff history (3): empty case (record_count=0), populated case (chronological order), reject `^GS-\d{3}$` case_id
- provenance (3): present snapshot, 404 on missing snapshot, all SHAs match underlying bytes
- cohort executive summary (3): healthy/watching/regressed bucketing, Tier 1 disclaimer round-trip, empty cohort returns 0 buckets
- cohort anomalies (4): no anomalies on uniform cohort, single-case cohort returns empty, severity boundary pins (z=2.0/3.0/4.0 → info/warn/danger)
- cross-endpoint forbidden-claim audit (1): no positive Tier 2 vocabulary in any Phase 8 endpoint response
- envelope disclaimer trio round-trip (2): every Phase 8 endpoint surfaces the Tier 1 disclaimer trio

`tests/test_fm04a_phase8_reviewer_accountability_e2e.py` — **3 reviewer journeys**:

1. **Signoff workflow E2E**: write 2 signoffs to a candidate; fetch history; assert chronological order + envelope; assert latest verdict surfaces in trust score gauge subline.
2. **Provenance trace E2E**: write a snapshot; fetch trust score; fetch provenance; verify every input SHA matches the snapshot bytes; verify formula_version round-trips.
3. **Cohort anomaly + executive summary E2E**: write 5 candidate cases with one engineered outlier (completeness=10 vs rest=85); fetch cohort summary (regressed bucket contains the outlier); fetch anomalies (z-score > 2σ on completeness axis).

All TAAs archived under `.planning/phase8_audit_reports/`:
- `A.md`, `B.md`, `C.md`, `D.md`, `E.md`, `F.md`
- `FINAL.md` (whole-arc independent audit)

### 3.G — STATE refresh + Phase 8 retrospective

Same pattern as Phase 7 slice H: update `.planning/STATE.md` stamp; create `.planning/retrospectives/fm04a_phase8_reviewer_accountability.md` with axis-by-axis SCORECARD citing every TAA verdict + commit SHA + test file path; final whole-arc TAA pass; iterate if CHANGES_REQUIRED.

## 4. Binding 9-axis scoring rubric

Replicated verbatim into the retrospective at closure. Every Phase 8 commit SCORECARD scores against this rubric.

| Axis | Weight | Criteria |
|------|--------|----------|
| **B — schema versioning behavior** | 12 | Every new emitted JSON contract stamps `schema_version`; all 4 new constants (`SIGNOFF_RECORD_SCHEMA_VERSION`, `TRUST_SCORE_PROVENANCE_SCHEMA_VERSION`, `COHORT_EXECUTIVE_SUMMARY_SCHEMA_VERSION`, `COHORT_ANOMALIES_SCHEMA_VERSION`) live in `_schema_versions.py` with bump-history blocks; no inline magic. |
| **M — module quality** | 12 | Builders are pure (no I/O leaks); verdict whitelist + forbidden-token list are module constants with import-time audits; z-score arithmetic uses named threshold constants (not inline 2.0 / 3.0 / 4.0); cohort size minimum is a named constant; signoff filename uses ISO 8601 UTC (not local time). |
| **T — testing** | 15 | ≥12 + 6 + 10 + 8 + 10 + 4 + 16 + 3 = ≥69 new tests; backend pytest sweep stays green (≥1619 + ≥69 = ≥1688); frontend vitest stays green (≥17 + new); every signoff verdict has a positive test; every anomaly severity bucket has a boundary pin (z=2.0 / 3.0 / 4.0); every endpoint has a schema-stamping test. |
| **C — claim-tier discipline** | 12 | HF1 path guard passes on every commit; no `^GS-\d{3}$` registry edits; no `golden_samples/**` writes outside `*-candidate`; the verdict whitelist import-time audit refuses any Tier 2 token (`_audit_verdict_whitelist` runs at import); signoff notes audited via `_assert_no_overclaim`; cohort executive summary's `regressed` bucket label does NOT use any forbidden claim verb; Tier 1 disclaimer trio in every emitted manifest. |
| **X — frontend integration** | 12 | New components mounted in `App.tsx`; `vitest run` passes; `tsc -b` clean; verdict pill colors driven by tone helper (no inline hex codes); no rounding / truncation on score surfaces (gauge subline surfaces verdict + reviewer + UTC verbatim); typed clients export `SUPPORTED_SIGNOFF_VERDICTS` so dropdowns import the source of truth. |
| **D — documentation / SSOT** | 8 | `_schema_versions.py` documents 4 new constants with one-sentence rationale each; signoff verdict whitelist enumerated in module docstring; anomaly severity ladder enumerated in module docstring; provenance input enumeration listed in module docstring; cohort bucket criteria listed in module docstring. |
| **A — anti-gaming discipline** | 8 | The 17 Phase-8 anti-gaming guards in this file are published BEFORE first code commit; every TAA finding (BLOCK or HIGH) closed by a fix commit; SCORECARD deductions cite TAA report sections; verdict whitelist + import-time audit are PERMANENT (a future maintainer cannot add Tier 2 vocabulary without breaking import). |
| **E — end-to-end workflow** | 8 | 3 new E2E tests composing with Phase 5/6/7 surfaces (signoff + trust score + cohort + alarms); each E2E test asserts the Tier 1 disclaimer trio in the HTTP response body. |
| **V — verification by TAA** | 13 | A standardized TAA report at `.planning/phase8_audit_reports/<slice>.md` for every sub-phase A–F AND for the final pass; every BLOCK / HIGH-severity finding has a closed follow-up; the final TAA pass returns APPROVE with no open BLOCKs. |

**Stop condition:** total ≥99 AND every axis ≥95 % of its weight (integer-arithmetic edge cases resolved by tightening cosmetic LOWs rather than rationalizing).

### Phase-8-specific anti-gaming guards

1. **C: -10 if the verdict whitelist contains any Tier 2 promotion token** — load-bearing safety mechanism. Import-time audit must catch this.
2. **C: -8 if `_audit_verdict_whitelist` is removed or weakened** — the audit is permanent infrastructure.
3. **C: -5 per signoff notes body that contains a forbidden positive claim outside `not <claim>` form** — `_assert_no_overclaim` must run on every signoff write.
4. **M: -3 if z-score thresholds (2.0 / 3.0 / 4.0) are inline-magic-numbered instead of named constants.**
5. **M: -3 if `COHORT_MIN_SIZE_FOR_ANOMALY` is inline-magic-numbered.**
6. **M: -2 if signoff filename uses local time instead of UTC ISO 8601.**
7. **B: -2 per missing `schema_version` field on a new endpoint.**
8. **B: -3 if a new schema constant skips bump-history documentation.**
9. **T: -2 per anomaly severity bucket without a boundary pin test (z=2.0 / 3.0 / 4.0).**
10. **T: -2 per signoff verdict without a positive test.**
11. **T: -3 if a Hypothesis test in `cohort_anomalies_properties` lacks `derandomize=True`.**
12. **T: -2 if cohort size = 1 or 2 anomaly edge case is not pinned by a dedicated test.**
13. **X: -2 if `SUPPORTED_SIGNOFF_VERDICTS` is duplicated as a literal list in the panel instead of imported from the client.**
14. **X: -2 if verdict tone colors are inline hex codes instead of a tone helper.**
15. **D: -2 if a new schema constant lacks a one-sentence rationale in its declaration.**
16. **A: -3 if a TAA CHANGES_REQUIRED finding is closed by waiver instead of a fix commit.**
17. **E: -2 per E2E test missing the Tier 1 disclaimer trio assertion on the HTTP response body.**

## 5. TAA protocol (Test Auditor Agent)

Same protocol as Phase 7. Each code slice spawns a `general-purpose` agent with:
- HEAD commit SHA to audit
- Path to this blueprint
- Instructions to spot-verify every slice claim against the actual diff
- Output written to `.planning/phase8_audit_reports/<slice>.md` (new file)
- Return verdict APPROVE / CHANGES_REQUIRED / BLOCK + honest score adjustment

If TAA returns CHANGES_REQUIRED, the slice author either:
- Lands a follow-up fix commit (preferred), then re-spawns TAA → expects APPROVE
- Logs an explicit reject + reason in the TAA report (only if the TAA was wrong on a verifiable point)

The V-axis score is the count of BLOCK/HIGH findings closed vs. left open.

## 6. TAA invocation log

| Slice | Commit audited | Verdict | Honest score adjustment | Report |
|-------|----------------|---------|------------------------|--------|
| A | TBD | TBD | TBD | `.planning/phase8_audit_reports/A.md` |
| B | TBD | TBD | TBD | `.planning/phase8_audit_reports/B.md` |
| C | TBD | TBD | TBD | `.planning/phase8_audit_reports/C.md` |
| D | TBD | TBD | TBD | `.planning/phase8_audit_reports/D.md` |
| E | TBD | TBD | TBD | `.planning/phase8_audit_reports/E.md` |
| F | TBD | TBD | TBD | `.planning/phase8_audit_reports/F.md` |
| FINAL | TBD | TBD | TBD | `.planning/phase8_audit_reports/FINAL.md` |

## 7. Constraints (preserved verbatim)

- Tier 1 engineering candidate; not signed validation; not benchmark agreement.
- No FM-04b work. No ADR-024 full. No `benchmark_comparison_candidate.json`. No sealed packet. No signed validation. No signed-registry flip.
- No edits to `^GS-\d{3}$` signed-registry directories. `*-candidate` paths only, all under test `tmp_path`.
- No Linear writes. No Notion writes. (`mcp__claude_ai_Notion__*` tools are disconnected this session; this constraint is also operationally enforced.)
- No `golden_samples/**` writes outside `*-candidate`. Production builders enforce `_assert_not_in_golden_samples`.
- No real OpenRadioss solver invocation. Phase 8 reads the same on-disk evidence Phase 4/5/6/7 read; CI / dev path stays synthetic.
- "Tier 1 engineering candidate; not signed validation; not benchmark agreement." preserved in every emitted manifest header, every `claim_impact` string, every E2E HTTP-body assertion.
- No LLM call / no generative-text in any output. Signoff notes are reviewer-provided free text that passes `_assert_no_overclaim` audit; everything else is structured.
- No push, no PR, no external write. Trailer rewrite reserved for the human user when the branch is pushed.
- HF1 hard-stop zone preserved: `agents/solver.py`, `agents/router.py`, `agents/geometry.py`, `schemas/sim_state.py`, `tests/test_toolchain_probes.py`, `Dockerfile`, `Makefile`, `scripts/hf1_path_guard.py`, `.github/workflows/`.

## 8. Carry-forward closure proof (slice-by-slice)

Each slice commit message must include a closure proof block citing which Phase 7 carry-forward (if any) it closes.

## 9. North-star ergonomics check (closure criterion)

At slice G closure, a reviewer must be able to demonstrate the following 4-step workflow end-to-end through the HTTP layer:

1. `GET /api/v1/cohort-executive-summary` → reviewer sees 3-bucket scorecard; clicks `regressed` bucket.
2. `GET /api/v1/cohort-anomalies` → reviewer sees the engineered outlier flagged with z-score + severity.
3. `GET /api/v1/trust-score-provenance/<outlier>?snapshot=<latest>` → reviewer reads every input SHA + formula version; deterministically reproduces the score.
4. `POST` equivalent of `write_signoff_record(<outlier>, "alice", "needs_more_evidence", "Outlier flagged on completeness; pending more snapshots to confirm.")` — actually invoked through `write_signoff_record` direct call in the E2E test (no POST endpoint exposed in Phase 8 — write is via reviewer's local script / future Phase 9 POST endpoint). Then `GET /api/v1/signoff-history/<outlier>` → reviewer sees their own signoff with the verdict + UTC + notes.

This 4-step composite is the **E2E #1 signoff workflow** test in §3.F.

---

> Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Plan locked. Execution begins at slice A.
