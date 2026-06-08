# FM-04a Phase 4 — Tier 1 Cohort Operations Console

> **Status:** Active local execution plan, 2026-05-16.
> **Branch:** `claude/FM-04a-tier1-ballistic-candidate`.
> **Authorization:** user direct-execution 2026-05-07/16, extended to
> Phase 4 with self-paced iteration to ≥95/100 on the scoring rubric
> below.
> **Boundary stamp:** Tier 1 engineering candidate; **not signed
> validation; not benchmark agreement; not a sealed FM-04b P8 bundle**;
> no `^GS-\d{3}$` registry mutation; no Linear / Notion writes; no
> real OpenRadioss dependency in CI.

---

## Why this phase, why now

After Phase 1-3 the single-case Tier 1 review path is solid: pick a
candidate, see its acceptance manifest, compare against another, render
its convergence study. But a real reviewer asks **cohort-level**
questions: "Of the N candidate cases on disk, which are most complete?
Which are missing what? Can I export one bundle and hand it to an
archivist? Can I diff the manifest I archived last week against the
manifest I just generated?"

Phase 4 closes that gap **without** crossing into FM-04b. The
completeness score is explicitly an *evidence-presence* signal, not a
validation-quality signal. Even a 100/100 score keeps every FM-04b
blocker visible.

---

## North star ("done when")

A non-author reviewer can, in one Workbench session:

1. Open the **cohort dashboard** and see every `*-candidate/` case as
   one row: completeness score (0-100) with breakdown, perforation
   marker, residual velocity, energy balance error, convergence
   verdict, last-modified.
2. Click any row → drill into the existing Phase 3 reviewer panel for
   that case (acceptance packet + comparison + convergence viewer).
3. **Score one case** via `/api/v1/case-completeness/<id>` and see
   the rubric-driven breakdown — which evidence files exist, which
   are missing, what each contributes to the score, and the
   verbatim FM-04b blockers list.
4. **Multi-select N cases** and export one **reviewer bundle** zip
   containing each case's acceptance packet + convergence study +
   Tier 1 markdown report + completeness scorecard, plus a
   top-level `BUNDLE_MANIFEST.json` with the Tier 1 banner.
5. **Diff two archived packets** by uploading or specifying paths to
   two `<case>_acceptance_packet.json` files; see the same structured
   diff Phase 3 B produces for live cases.
6. Trust Center surfaces a new `cohort_completeness_status` card
   summarizing the cohort.

Every output carries the Tier 1 boundary; no positive `validated
against / benchmark agreement / signed validation / perforation
completed / bullet-through-steel complete / validated physics` wording.

---

## Sub-phases

### Phase A — Evidence completeness scoring engine

**Goal:** A pure function takes the evidence inventory for one
candidate case and returns a 0-100 score + breakdown + missing list.

**Deliverables:**

- `backend/app/services/reporting/case_completeness.py` (NEW):
  `CaseCompletenessScore` dataclass + `score_case_completeness(inputs)
  -> CaseCompletenessScore`. Inputs mirror `AcceptancePacketInputs`
  (paths) — the scorer probes each one's existence and tallies points
  per the rubric below.
- Score rubric (deterministic, weighted, exact bands):
  * Starter deck present: 15 pts
  * Engine deck present: 15 pts
  * `ballistic_metrics.json` present: 20 pts
  * Energy audit closed_aggregate (vs partial / unavailable): 15 pts
  * `convergence_study.json` present with `candidate_observed_stable`
    verdict: 15 pts (10 if present but not stable; 0 if absent)
  * Animation manifest: 5 pts
  * Result mesh: 5 pts
  * Generator script: 5 pts
  * NOTES.md: 5 pts
- Always emits the verbatim FM-04b blockers list alongside the score.
- Build-time `_assert_no_overclaim` on the rendered JSON.
- Tests: 8 cases covering 0 / 35 (decks only) / 65 (decks + metrics +
  audit) / 80 (decks + metrics + audit + convergence) / 100 (every
  evidence file) / unstable convergence band / partial audit band /
  forbidden-claim audit.

### Phase B — Cohort overview endpoint

**Goal:** One endpoint enumerates every `*-candidate/` case under
`golden_samples/` and returns each case's scored summary.

**Deliverables:**

- `backend/app/services/reporting/cohort_overview.py` (NEW): pure
  builder taking a repo root, scanning `golden_samples/*-candidate/`,
  and emitting `CohortOverview` with per-case
  `CohortOverviewEntry`: case_id, completeness_score,
  perforation_marker, residual_velocity, energy_balance_error_pct,
  convergence_verdict, last_modified_iso, plus aggregate fields
  (cohort_count, mean_score, completeness_distribution).
- `backend/app/api/routes/cohort_overview.py` (NEW): GET
  `/api/v1/cohort-overview` streams the JSON.
- Tests: 7 cases covering empty cohort / single case / cohort with
  mixed scores / forbidden-wording audit / read-only over
  golden_samples/ / no signed registry leakage.

### Phase C — Reviewer bundle exporter + endpoint

**Goal:** Multi-case zip download with one manifest entry per case.

**Deliverables:**

- `backend/app/services/reporting/reviewer_bundle.py` (NEW):
  `build_reviewer_bundle(case_ids, repo_root) -> bytes` produces an
  in-memory zip containing per-case (acceptance packet JSON +
  convergence study JSON if exists + Tier 1 markdown report +
  completeness scorecard JSON) plus a top-level
  `BUNDLE_MANIFEST.json` with case list + Tier 1 banner + claim
  boundary + generated_at_utc. Build-time positive-claim audit on
  every entry. Refuses to write to disk (caller decides).
- `backend/app/api/routes/reviewer_bundle.py` (NEW): GET
  `/api/v1/reviewer-bundle?ids=GS-102-candidate,GS-102-refined-candidate`
  returns the zip with `Content-Type: application/zip` and
  `Content-Disposition: attachment;
  filename="tier1_reviewer_bundle_<n>cases.zip"`.
- `scripts/export_reviewer_bundle.py` (NEW): CLI driver.
- Tests: 8 cases covering single case / multi case / missing case →
  404 / bad id → 400 / unzip contents / manifest schema / Tier 1
  banner in every member / claim boundary preserved.

### Phase D — Archived acceptance packet diff endpoint

**Goal:** Diff two archived `<case>_acceptance_packet.json` files on
disk so reviewer can compare "last week's snapshot" vs "today's".

**Deliverables:**

- `backend/app/services/reporting/archived_packet_diff.py` (NEW):
  `diff_archived_packets(path_a, path_b) -> ArchivedPacketDiff` reads
  both JSON files, validates each carries Tier 1 claim_boundary,
  reuses Phase 3 B `build_case_comparison` semantics but on archived
  inputs. Emits an `archive_provenance` block per side (file path,
  sha256, mtime, generated_at_utc from payload).
- `backend/app/api/routes/archived_packet_diff.py` (NEW): GET
  `/api/v1/archived-packet-diff?a=<relpath>&b=<relpath>` validates
  both paths anchor under `reports/` (whitelisted root) and returns
  the structured diff.
- Tests: 6 cases covering identity diff / different cases / missing
  file → 404 / path traversal → 400 / Tier 1 banner preservation /
  forbidden-claim audit.

### Phase E — Frontend cohort dashboard panel

**Goal:** Cohort overview rendered as a sortable leaderboard with
drill-down anchors and a Trust Center summary card.

**Deliverables:**

- `frontend/src/cohortOverviewClient.ts` (NEW): typed fetch helper
  + parser + tone helpers (`scoreTone`: ≥80 accent, ≥50 warning,
  <50 danger).
- `frontend/src/caseCompletenessClient.ts` (NEW): typed fetch helper
  for `/case-completeness/<id>` + parser.
- `frontend/src/components/CohortDashboardPanel.tsx` (NEW): rows are
  sortable by score / case_id / verdict; "Drill" button anchors at
  the existing AcceptancePacketPanel by switching
  `selectedCandidateCaseId`; aggregate banner shows cohort size +
  mean score.
- `frontend/src/components/CaseCompletenessCard.tsx` (NEW): inline
  expand for the selected case — bar chart of evidence points +
  missing-evidence list + verbatim FM-04b blockers.
- `frontend/src/App.tsx`: integrate the dashboard above the
  Phase 3 panels in the Visual tab; new Trust Center review card
  `cohort_completeness_status`.
- Tests: 12 covering parser snake/camel, fetch fallback, score
  tone bands, sort logic, drill-down state plumbing.

### Phase F — Reviewer bundle UI + archive diff UI

**Goal:** Multi-select picker + bundle download + archive diff
form.

**Deliverables:**

- `frontend/src/reviewerBundleClient.ts` (NEW): URL builder for the
  zip download + multi-select state helper.
- `frontend/src/archivedPacketDiffClient.ts` (NEW): typed fetch +
  parser.
- `frontend/src/components/ReviewerBundlePanel.tsx` (NEW): checkbox
  list of cases (driven by `candidateCaseRegistry`); "Export bundle"
  link anchors at the endpoint with selected ids.
- `frontend/src/components/ArchivedPacketDiffPanel.tsx` (NEW): two
  text fields for archived JSON paths + "Compute diff" → renders
  the structured diff using the same DiffRow component as Phase 3 C.
- `frontend/src/App.tsx`: integrate below the cohort dashboard.
- Tests: 8 covering snake/camel parse, URL building with multi-ids,
  fallback handling, tone-coded diff rendering.

### Phase G — HTTP-layer + E2E reviewer-workflow tests

**Goal:** Every new Phase 4 endpoint has an HTTP-layer test;
ONE E2E test drives the full reviewer-cohort workflow on synthetic
fixtures.

**Deliverables:**

- `tests/test_phase4_endpoints_integration.py` (NEW): TestClient
  suite covering `/api/v1/case-completeness/<id>`,
  `/api/v1/cohort-overview`, `/api/v1/reviewer-bundle?ids=...`,
  `/api/v1/archived-packet-diff?a=...&b=...` for 200 OK / 400 / 404
  / content-type / content-disposition / Tier 1 boundary in body.
- `tests/test_fm04a_phase4_reviewer_workflow_e2e.py` (NEW): synthetic
  E2E that:
  1. seeds 3 candidate cases with different evidence completeness,
  2. scores each via `score_case_completeness`,
  3. builds cohort overview,
  4. builds reviewer bundle and unzips it in memory,
  5. asserts every bundle member carries Tier 1 banner,
  6. archives one packet, then diffs archived-vs-live.
- ≥16 new tests total.

### Phase H — STATE refresh + Phase 4 retrospective with final scorecard

**Goal:** STATE.md stamp + Phase 4 ledger; retrospective publishes
the final scorecard, per-axis breakdown, deferred work, and
candidate next slices.

---

## SCORING RUBRIC (binding contract)

This rubric is the binding completion contract. Each commit publishes
a SCORECARD block in its commit message; each sub-phase ends with a
sub-phase rollup; the final retrospective publishes the phase total.

### Axes and weights (sum = 100)

| Code | Axis | Weight | Mandatory anti-gaming guards |
|------|------|--------|------------------------------|
| **B** | Boundary discipline | 15 | -3 per positive-claim leak; -5 per HF1 path-guard hit; -3 per writer that can target `golden_samples/**` |
| **M** | Mechanical verification | 15 | -1 per failing test (cap -15); -3 per ruff/tsc/vite failure at sub-phase close |
| **T** | Test coverage quality | 15 | -3 if any feature lacks integration test; -3 if any test depends on real OpenRadioss; -2 per missing edge-case test |
| **C** | Code quality | 10 | -2 per drive-by refactor; -2 per backwards-compat shim; -1 per WHAT-comment; -2 per dead code block left in |
| **X** | API / UX coherence | 10 | -2 per inconsistent error code; -2 per duplicated tone logic; -2 per stylistic divergence from Phase 2/3 baseline |
| **D** | Documentation | 10 | -2 per undocumented public function; -3 if STATE not refreshed at sub-phase H; -3 if retrospective omits a deferred FM-04b prerequisite |
| **A** | Architecture fit | 10 | -3 per new heavyweight dep; -3 per abstraction added without ≥2 consumers; -3 per fork of existing pattern |
| **E** | E2E feature completeness | 15 | -3 per workflow step missing from E2E test; -3 per stub frontend component; -3 if reviewer cannot complete the workflow described in the north star |

### Stop conditions

- **≥95 total AND every axis ≥90% of its weight** → write retrospective and stop.
- **90 ≤ total < 95** → identify weakest axis, write a focused iteration commit, re-score.
- **80 ≤ total < 90** → iterate top-2 weakest axes, re-score.
- **< 80** → revisit blueprint scope; reset weakest sub-phase.

### Honesty discipline

- Every deduction must cite a concrete defect (commit SHA + file:line OR test name OR observed behavior).
- Re-scoring at sub-phase close re-evaluates **all axes against the running cumulative state**, not just the just-shipped sub-phase. Regressions count.
- Scores are not allowed to go up without a corresponding commit fixing the cited defect.
- Self-attestations like "I tried hard" or "this is essentially good" are not allowed — every score is a number with evidence.

---

## What this phase explicitly does NOT do

- **No FM-04b prerequisite work.** ADR-024 (full), benchmark
  comparison producer, sealed packet, independent reviewer signoff,
  user milestone-experience acceptance, signed registry flip, and
  Linear/Notion mirror writes all remain on the FM-04b side.
- **No `^GS-\d{3}$` registry mutation.** Cohort scanner filters
  signed-registry shapes by construction.
- **No real OpenRadioss dependency.** CI must run on synthetic
  fixtures only.
- **No HF1 forbidden zones touched.** Every new file lives under
  `backend/app/services/reporting/`, `backend/app/api/routes/`,
  `frontend/src/`, `frontend/test/`, `tests/`, or `scripts/`.
- **No new heavy dependencies.** `zipfile` is stdlib; everything
  else reuses what Phase 1-3 already imports.
- **No push, no PR, no external write.** Trailer rewrite reserved
  for human-user push time.

---

## Verification gates (mechanical, run at every commit)

1. `pytest -q` — all new tests pass; no regressions vs Phase 3 baseline (1333 passed / 8 skipped).
2. `node --test --experimental-strip-types frontend/test/*.test.ts` — all new tests pass; no regressions vs Phase 3 baseline (54).
3. `tsc -b` + `npm run build` (vite) — clean.
4. `pre-commit run --all-files` — ruff + ruff-format + HF1 path-guard pass.

These are **mechanical preconditions** for any commit, not part of the score. Failing any gate is a hard block, not a deduction.
