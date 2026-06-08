# FM-04a Phase 6 — Reviewer Drift Narrative & Evidence Trust Score

> **Tier 1 engineering candidate; not signed validation; not benchmark agreement.**
>
> **Blueprint stamp:** `fm04a-phase6-trust-narrative-blueprint-2026-05-16`
> **Branch:** `claude/FM-04a-tier1-ballistic-candidate@<plan>`
> **Authoring authority:** local Claude Opus 4.7 under direct-execution authorization. No FM-04b prerequisite crossed.

---

## 1. North Star

A reviewer opens the workbench and can answer three questions in one glance:

1. **"Is this case in good shape right now?"** — one composite `trust_score` (0–100) per Tier 1 candidate case, with a transparent breakdown of how it was computed.
2. **"What specifically changed between two snapshots?"** — not just drift *signals* (Phase 5 D), but raw *values*: residual_velocity went from 75 → 80 m/s, energy balance error from 12 % → 8.5 %, convergence verdict still `candidate_observed_stable`.
3. **"What does that mean in plain English?"** — a data-driven drift narrative that turns deltas into sentences a non-author reviewer can act on.

Phase 6 ships the four surfaces that close those three questions:

- `/api/v1/trust-score/<case-id>` (composite + breakdown, stamped contract)
- `/api/v1/snapshot-narrative?a=<utc>&b=<utc>` (drift sentences per case)
- `/api/v1/trust-score-timeline/<case-id>` (case's trust score across every snapshot containing it)
- snapshot diff extended with raw numerical deltas (schema bump 1.0.0 → 1.1.0, MINOR per the documented bump policy)

Plus the frontend trio: trust score gauge, drift narrative panel, trust score timeline.

---

## 2. Scope boundaries (non-negotiable)

Carries forward verbatim from prior phases:

- Tier 1 engineering candidate ONLY. The wording `not signed validation` and `not benchmark agreement` must round-trip through every emitted manifest, every HTTP body, every UI panel header.
- No FM-04b prerequisite crossed: no ADR-024 full, no `benchmark_comparison_candidate.json`, no sealed packet, no signed validation language, no `^GS-\d{3}$` registry flip.
- No edits inside `^GS-\d{3}$` signed-registry directories (only `*-candidate` paths in test fixtures, all under `tmp_path`).
- No edits inside the HF1 hard-stop zone (`agents/solver.py`, `agents/router.py`, `agents/geometry.py`, `schemas/sim_state.py`, `tests/test_toolchain_probes.py`, `Dockerfile`, `Makefile`, `golden_samples/` prefix outside `*-candidate`, `scripts/hf1_path_guard.py`, `.github/workflows/`).
- No real OpenRadioss solver invocation. CI / dev path stays synthetic.
- No Linear / Notion writes. No push, no PR. Trailer rewrite for any future PR remains a human-user action.

Forbidden positive claims (must NEVER appear, except in `not <claim>` disclaimer form): `validated against`, `benchmark agreement`, `signed validation`, `perforation completed`, `bullet-through-steel complete`, `validated physics`.

Phase 6-specific additional constraint:

- **Trust score formula is data-driven, not opinionated.** Every weight, every penalty, every threshold appears as a named constant in `backend/app/services/reporting/trust_score.py`, is documented with a one-sentence rationale, and is asserted by a parametrized test. No "magic numbers" inline.
- **Narrative text is templated, not free-form.** Each narrative sentence is built from a fixed template + structured data. No LLM calls. No prose generation.

---

## 3. Sub-phase plan

### 3.A — Snapshot diff raw-value extension

Extend `cohort_snapshot_diff.CohortSnapshotDiff.reproducibility_deltas` siblings (NOT inside repro deltas — a new sibling list `numerical_deltas`) so each shared case carries:

```json
{
  "case_id": "GS-A-candidate",
  "residual_velocity_m_per_s": { "a": 75.0, "b": 80.0, "delta": 5.0, "delta_pct": 6.666... },
  "energy_balance_error_pct": { "a": 12.0, "b": 8.5, "delta": -3.5, "delta_abs_pct": 3.5 },
  "convergence_combined_verdict": { "a": "candidate_observed_stable", "b": "candidate_observed_stable", "same_verdict": true },
  "perforation_marker": { "a": "candidate_perforation", "b": "candidate_perforation", "same_marker": true }
}
```

The values are read from each snapshot's `completeness/<case>.json` and from the case's `ballistic_metrics.json` *as it existed at snapshot time*. Phase 5 C did NOT capture `ballistic_metrics.json` into the snapshot — so Phase 6 A also extends `cohort_snapshot.write_cohort_snapshot` to copy the source `ballistic_metrics.json` into `snapshots/<label>/metrics/<case>.json`. This is a MINOR schema bump on `COHORT_SNAPSHOT_MANIFEST_SCHEMA_VERSION` (1.0.0 → 1.1.0) and on `COHORT_SNAPSHOT_DIFF_SCHEMA_VERSION` (1.0.0 → 1.1.0). Both bumps documented per the policy in `_schema_versions.py`.

Backward compatibility: when reading an old (1.0.0) snapshot, the diff gracefully degrades — `numerical_deltas` becomes `[]` and a note is logged in the diff payload's `claim_impact`. No exception.

Deliverables:
- `backend/app/services/reporting/cohort_snapshot.py` — write `metrics/<case>.json` next to `completeness/<case>.json`
- `backend/app/services/reporting/cohort_snapshot_diff.py` — `numerical_deltas` field + reader that handles 1.0.0 fallback
- `_schema_versions.py` — bump both constants, document each in the bump policy
- `frontend/src/cohortSnapshotClient.ts` — surface `numericalDeltas` on `CohortSnapshotDiff`
- Tests: ≥10 new (snapshot writer copies metrics; diff surfaces numerical_deltas; fallback when snapshot is 1.0.0; schema bumps asserted)

### 3.B — Trust score builder + endpoint

`backend/app/services/reporting/trust_score.py`:

- `compute_trust_score(case_id, repo_root) -> TrustScore` reads the same evidence sources `case_completeness` already reads. Output:

```json
{
  "schema_version": "1.0.0",
  "formula_version": "1.0.0",
  "case_id": "GS-A-candidate",
  "claim_tier": "Tier 1 engineering candidate",
  "claim_boundary": "tier1_engineering_candidate; not_signed_validation; not_benchmark_agreement",
  "trust_score": 87,
  "trust_score_max": 100,
  "breakdown": [
    {"axis": "completeness", "weight": 50, "raw_score": 90, "weighted": 45, "rationale": "..."},
    {"axis": "convergence_stability", "weight": 20, "raw_score": 100, "weighted": 20, "rationale": "..."},
    {"axis": "energy_audit_closure", "weight": 15, "raw_score": 100, "weighted": 15, "rationale": "..."},
    {"axis": "reproducibility_clean", "weight": 15, "raw_score": 47, "weighted": 7, "rationale": "git dirty + python missing"}
  ],
  "tier2_blockers_remaining": [...],
  "claim_impact": "Tier 1 candidate trust score only; not signed validation; not benchmark agreement; not a substitute for FM-04b P8 sealed validation."
}
```

Formula constants (named + documented in module docstring):

- `COMPLETENESS_WEIGHT = 50` — proxy for "is there enough evidence"
- `CONVERGENCE_WEIGHT = 20` — proxy for "does refining mesh / dt change the answer"
- `ENERGY_AUDIT_WEIGHT = 15` — proxy for "do energies balance"
- `REPRODUCIBILITY_WEIGHT = 15` — proxy for "can we re-run this from a clean checkout"

Raw subscores (each 0–100):
- completeness = `completeness_score / completeness_score_max * 100`
- convergence_stability = `100` if both axes `candidate_observed_stable`, `60` if mixed, `30` if unstable, `0` if absent
- energy_audit_closure = `100` if `closed_aggregate`, `60` if `partial_candidate`, `0` otherwise
- reproducibility_clean = starts at `100`, `-30` if `git_dirty`, `-25` if `git_commit_sha` is null, `-20` per `not_installed` tracked package up to a floor of 0

`/api/v1/trust-score/<case-id>` returns the rendered JSON.

Deliverables:
- `backend/app/services/reporting/trust_score.py`
- `backend/app/api/routes/trust_score.py`
- Constant `TRUST_SCORE_SCHEMA_VERSION = "1.0.0"` + `TRUST_SCORE_FORMULA_VERSION = "1.0.0"` in `_schema_versions.py`
- `frontend/src/trustScoreClient.ts` with `parseTrustScore` preserving `schemaVersion` AND `formulaVersion`
- Tests: ≥12 (formula correctness across 4 axes, fallback when evidence missing, schema_version pinned, claim disclaimer round-trip)

### 3.C — Drift narrative builder + endpoint

`backend/app/services/reporting/snapshot_narrative.py`:

- Input: snapshot diff (from Phase 5 D extended in 3.A with `numerical_deltas`).
- Output: per-case list of `NarrativeLine` records, each with a fixed template ID + structured slot values:

```json
{
  "schema_version": "1.0.0",
  "snapshot_a_label": "2026-05-16T100000Z",
  "snapshot_b_label": "2026-05-16T200000Z",
  "claim_tier": "Tier 1 engineering candidate",
  "narratives": [
    {
      "case_id": "GS-A-candidate",
      "lines": [
        {"template_id": "residual_velocity_delta", "severity": "info",
         "text": "Residual velocity changed from 75.0 to 80.0 m/s (+6.67%)."},
        {"template_id": "energy_balance_improved", "severity": "info",
         "text": "Energy balance error tightened from 12.0% to 8.5%."},
        {"template_id": "script_sha_changed", "severity": "warn",
         "text": "Generator script SHA-256 changed (scripts/gen_gsa_deck.py); regression risk."},
        {"template_id": "completeness_improved", "severity": "info",
         "text": "Completeness score lifted from 80 to 85 (+5)."}
      ]
    }
  ],
  "claim_impact": "..."
}
```

Templates are *enumerated* in the module (a finite set: residual_velocity_delta, residual_velocity_unchanged, energy_balance_improved, energy_balance_degraded, energy_balance_unchanged, convergence_verdict_changed, perforation_marker_changed, script_sha_changed, python_version_changed, git_sha_changed, git_dirty_introduced, completeness_improved, completeness_regressed, completeness_unchanged, cohort_added, cohort_removed). Each template emits one short sentence with structured slot values from the diff. No free-form prose.

Severity: `info` (numerical change, no concern), `warn` (something a reviewer should look at — script SHA, python version, energy balance regressed, completeness regressed), `danger` (rare — only used today if convergence verdict regresses to unstable).

`/api/v1/snapshot-narrative?a=<utc>&b=<utc>` returns the rendered envelope.

Deliverables:
- `backend/app/services/reporting/snapshot_narrative.py`
- `backend/app/api/routes/snapshot_narrative.py`
- `SNAPSHOT_NARRATIVE_SCHEMA_VERSION = "1.0.0"` in `_schema_versions.py`
- `frontend/src/snapshotNarrativeClient.ts`
- Tests: ≥14 (each template fires correctly under the right diff input; severity escalation; no template fires when nothing changed; schema_version pinned)

### 3.D — Trust score timeline

`backend/app/services/reporting/trust_score_timeline.py`:

- For a given `case_id`, walks every snapshot under `reports/snapshots/<*>/` that contains the case, computes trust score from that snapshot's `completeness/<case>.json` + `reproducibility/<case>.json` + `metrics/<case>.json` (new in 3.A), and returns ordered `(snapshot_label, trust_score, breakdown)` records.

```json
{
  "schema_version": "1.0.0",
  "case_id": "GS-A-candidate",
  "claim_tier": "Tier 1 engineering candidate",
  "point_count": 3,
  "points": [
    {"snapshot_label": "2026-05-15T100000Z", "trust_score": 70, "completeness_weighted": 35, ...},
    {"snapshot_label": "2026-05-15T200000Z", "trust_score": 78, ...},
    {"snapshot_label": "2026-05-16T200000Z", "trust_score": 87, ...}
  ],
  "claim_impact": "..."
}
```

Trust score is computed from on-disk snapshot files, NOT by re-running the trust score builder (which reads live evidence) — this way the timeline is *historical*, not always-now.

Deliverables:
- `backend/app/services/reporting/trust_score_timeline.py`
- `backend/app/api/routes/trust_score_timeline.py`
- `TRUST_SCORE_TIMELINE_SCHEMA_VERSION = "1.0.0"` in `_schema_versions.py`
- `frontend/src/trustScoreTimelineClient.ts`
- Tests: ≥8 (timeline ordered oldest-to-newest, skips snapshots missing the case, schema_version pinned)

### 3.E — Frontend trust score gauge + narrative panel + timeline

- `frontend/src/components/TrustScoreGauge.tsx` — colored 0–100 bar + breakdown table; tone (`accent` ≥80, `warning` ≥50, `danger` <50)
- `frontend/src/components/DriftNarrativePanel.tsx` — list of narrative lines per case from the two selected snapshots, grouped by severity; integrates into the existing `CohortSnapshotPanel` (Phase 5 E) by reading the same `labelA` / `labelB`
- `frontend/src/components/TrustScoreTimeline.tsx` — simple inline SVG sparkline + table; no external charting lib
- Wire all three into `App.tsx`; bind `TrustScoreGauge` + `TrustScoreTimeline` to `selectedCandidateCaseId`, bind `DriftNarrativePanel` to the snapshot picker selections

Deliverables:
- 3 components
- Frontend tests: ≥18 (gauge tone breakpoints, sparkline path generation, narrative grouping by severity, schemaVersion preserved on every parsed object)

### 3.F — HTTP integration + E2E

- `tests/test_phase6_endpoints_integration.py` — drive every new endpoint through `_SyncASGIClient`: stamped payload, malformed case_id rejection, missing-snapshot fallback, Tier 1 disclaimer round-trip. Target: ≥14 tests.
- `tests/test_fm04a_phase6_trust_workflow_e2e.py` — 7-step reviewer journey: write baseline snapshot → drift case A (velocity + script body + dirty git) → write follow-up → list snapshots → fetch trust score for case A live → fetch trust score timeline → fetch snapshot narrative for the two snapshots → assert specific narrative lines fire with correct severity. Target: 2 tests (baseline + edge case).

### 3.G — STATE + retrospective

- `.planning/STATE.md` stamp advance + maintainer line append.
- `.planning/retrospectives/fm04a_phase6_trust_narrative.md` — same template as Phase 5: north-star check, commit ledger, axis-by-axis SCORECARD with evidence, mistakes & corrections, carry-forwards, constraint check, final score.

---

## 4. Binding 8-axis scoring rubric (Phase 6 specialization)

Weight totals 100. Stop condition: ≥95 total AND every axis ≥90 % of its weight.

| Axis | Weight | Phase 6 specialization |
|------|--------|------------------------|
| **B — schema versioning** | 15 | Every new emitted contract stamps `schema_version`; both bumps (snapshot manifest 1.0.0→1.1.0, snapshot diff 1.0.0→1.1.0) cite MINOR per the documented bump policy; trust score carries `formula_version` separately. |
| **M — module quality** | 15 | New builders pure; new routes thin (`Response(content=…)`); CLI not needed; narrative templates enumerated (closed set); trust score formula constants named + documented inline. |
| **T — testing** | 20 | ≥60 new tests across slices A–F; parametrized constants tests pin every version + every weight; HTTP layer test for every new route. |
| **C — claim-tier discipline** | 15 | Tier 1 disclaimer round-trips through every emitted manifest + HTTP body + UI panel header; forbidden-claim audit on every new builder; HF1 guard clean on every commit. |
| **X — frontend integration** | 15 | `trustScoreClient` + `snapshotNarrativeClient` + `trustScoreTimelineClient` all preserve `schemaVersion`; trust score client also preserves `formulaVersion`; UI gauge surfaces *exact* score, not rounded. |
| **D — documentation / SSOT** | 5 | `_schema_versions.py` policy still authoritative; bumps documented; trust score formula constants documented in module docstring with rationale per constant. |
| **A — anti-gaming discipline** | 5 | Every score deduction cites a concrete defect; Phase-6-specific guards published in this file *before* the first code commit. |
| **E — end-to-end workflow** | 5 | ≥1 E2E test that proves the full Phase 6 surface composes with Phase 5 surfaces: snapshot → diff → narrative → trust score → timeline. |

### Phase-6-specific anti-gaming guards

- **B: -2 per missing `schema_version` field on a new output** (carry-forward from Phase 5).
- **B: -3 if the snapshot manifest bump is undocumented in `_schema_versions.py`'s policy section** — the bump policy mandates a SCORECARD note; the bump itself mandates a citation here.
- **T: -2 per trust score axis whose weighted-score formula is not asserted by a dedicated test** — formulas without tests rot.
- **T: -3 if the trust score formula constants (`COMPLETENESS_WEIGHT` etc.) are not asserted by a constants test that sums to 100** — silent rebalancing across phases is a regression vector.
- **T: -2 per narrative template that is not exercised by at least one positive test case** — dead templates are technical debt.
- **X: -2 if `TrustScoreGauge` rounds the score without surfacing the exact integer** — gauges that lie about precision are a common UI anti-pattern.
- **D: -3 if any trust score weight or threshold is inline-magic-numbered** (e.g. `if score > 80` in a component) instead of imported from the SSOT constants module.
- **C: -3 if a narrative template ever emits text that could be parsed as a positive Tier 2 claim** — the templates must remain factual deltas, not endorsements.

---

## 5. Commit cadence + SCORECARD discipline

Each sub-phase closes with one commit carrying a SCORECARD block (per axis, with concrete defect citations for deductions). Re-scoring at sub-phase close re-evaluates *all* axes against cumulative state. Scores cannot go up without a commit fixing the cited defect.

Stop condition restated: **cumulative ≥95 total AND every axis ≥90 % of its weight at the same slice**.

---

## 6. Non-goals

- No live trust score computation for cohort overview (Phase 6 keeps `/cohort-overview` at its current schema; a future phase could elevate trust score into the cohort table, but the bump policy mandates a SCORECARD note + retrospective entry for that).
- No LLM / generative-text in narratives. Templates + structured slot values only.
- No alerting / notifications. Trust score timeline trends are surfaced; the reviewer decides what to do with them.
- No bench-marking against external numbers. Trust score remains a *Tier 1 candidate* signal.
- No FM-04b prerequisite crossed. Trust score is NOT a substitute for the sealed packet; the claim_impact string says so explicitly on every emitted manifest.
