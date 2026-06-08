# FM-04a Phase 5 — Reproducibility, Schema Versioning & Cohort Time-Series

> **Status:** Active local execution plan, 2026-05-16.
> **Branch:** `claude/FM-04a-tier1-ballistic-candidate`.
> **Authorization:** user direct-execution 2026-05-07/16, extended to
> Phase 5 with self-paced iteration to ≥95/100 on the same 8-axis
> scoring rubric Phase 4 used.
> **Boundary stamp:** Tier 1 engineering candidate; **not signed
> validation; not benchmark agreement; not a sealed FM-04b P8 bundle**;
> no `^GS-\d{3}$` registry mutation; no Linear / Notion writes; no
> real OpenRadioss dependency in CI.

---

## Why this phase, why now

Phase 4 made the cohort visible, scoreable, exportable, and diff-able.
But every output is a *point-in-time* artifact: a reviewer who
archived a packet last month has no machine-readable way to know
which rubric version scored it, which git commit produced its
evidence, or whether the cohort has drifted since.

Phase 5 closes that gap with three additive surfaces:

1. **Schema + rubric versioning** — every JSON output gains a
   `schema_version` field; the completeness scorer gains a
   `rubric_version` constant. Future schema evolution stays
   tractable.
2. **Per-case reproducibility manifest** — for one case, capture
   git commit SHA, Python version, key dependency versions, and
   generator script SHA-256. Reviewer can audit provenance without
   re-running anything.
3. **Cohort time-series via snapshots** — CLI writes a timestamped
   directory under `reports/snapshots/<UTC>/`; endpoint lists
   existing snapshots; a snapshot-diff endpoint emits structured
   drift between any two snapshot directories.

No FM-04b prerequisite is crossed. The completeness score remains an
evidence-presence signal; even a 100/100 cohort still surfaces the
FM-04b blockers list. The reproducibility manifest does NOT certify
validation; it only documents what is currently on disk.

---

## North star ("done when")

A non-author reviewer can, in one session:

1. **Open any archived JSON** (acceptance packet, completeness score,
   cohort overview, bundle manifest, archived diff, convergence
   study, case comparison) and see a `schema_version` field — a
   future reviewer with a newer client can dispatch on it.
2. **Fetch `/api/v1/reproducibility-manifest/<case-id>`** and see:
   git commit SHA, Python version, key dependency versions, the
   generator script's SHA-256 + path, the case_id, and a Tier 1
   banner + FM-04b blockers list.
3. **Write a cohort snapshot** via
   `python scripts/write_cohort_snapshot.py` (or equivalent CLI).
   Output lands at `reports/snapshots/<UTC>/` with the cohort
   overview JSON + per-case completeness scorecards + a reviewer
   bundle zip + the reproducibility manifests for the cohort.
4. **List existing snapshots** via `GET /api/v1/cohort-snapshots`
   to see every `reports/snapshots/<UTC>/` directory with its
   case count + creation timestamp.
5. **Diff two snapshots** via
   `GET /api/v1/cohort-snapshot-diff?a=<utc>&b=<utc>` and see a
   structured drift report: cases added / removed / score
   improved / score regressed, plus a per-case completeness delta.
6. Trust Center surfaces a new `cohort_snapshot_status` card.

Every artifact carries the Tier 1 banner; no positive `validated
against / benchmark agreement / signed validation / perforation
completed / bullet-through-steel complete / validated physics`
wording.

---

## Sub-phases

### Phase A — Schema + rubric versioning across every existing builder

**Goal:** Every JSON output gets `schema_version`; the completeness
scorer gains `rubric_version`. Atomic cross-cutting change.

**Deliverables:**

- `backend/app/services/reporting/_schema_versions.py` (NEW): single
  module declaring per-output schema version constants
  (`ACCEPTANCE_PACKET_SCHEMA_VERSION = "1.0.0"`, similarly for
  `CASE_COMPLETENESS_SCHEMA_VERSION`, `COHORT_OVERVIEW_SCHEMA_VERSION`,
  `REVIEWER_BUNDLE_MANIFEST_SCHEMA_VERSION`,
  `ARCHIVED_PACKET_DIFF_SCHEMA_VERSION`,
  `CASE_COMPARISON_SCHEMA_VERSION`,
  `TIER1_REPORT_SCHEMA_VERSION`,
  `CONVERGENCE_STUDY_SCHEMA_VERSION`) plus
  `COMPLETENESS_RUBRIC_VERSION = "1.0.0"`. Documentation at the
  top of the module declares the bump policy
  (major: breaking; minor: additive; patch: clarification).
- Every existing builder updated to import its constant and emit
  it in the rendered JSON. `_assert_no_overclaim` updated to
  audit-strip the version string itself (semver tokens are not
  forbidden claims).
- Every frontend client parses + preserves the field; new
  `schemaVersion` property on every typed payload.
- Tests: every existing builder test gains one assertion that
  `schema_version` matches the module constant; every frontend
  parser test asserts the version round-trips.

### Phase B — Per-case reproducibility manifest

**Goal:** A reviewer fetching the manifest sees provenance for one
case without running anything.

**Deliverables:**

- `backend/app/services/reporting/reproducibility_manifest.py` (NEW):
  pure builder. `ReproducibilityManifest` dataclass with: case_id,
  generated_at_utc, schema_version, claim_tier, claim_boundary,
  git_commit_sha, git_working_tree_clean, python_version,
  key_dependency_versions (dict of name → version),
  generator_script (path + sha256 + bytes), tier2_blockers_remaining,
  claim_impact. Git SHA + clean-flag read via `subprocess.run(["git", ...])`
  with safe error handling (manifest still emits with `git_commit_sha=None`
  when not in a git tree). _assert_no_overclaim live.
- `backend/app/api/routes/reproducibility_manifest.py` (NEW):
  GET `/api/v1/reproducibility-manifest/<case-id>` streams the
  manifest JSON. case_id validated against the established regex.
- Tests: 8 covering normal generation, git unavailable, dirty
  working tree flag, missing generator script handled, Tier 1
  boundary preserved, forbidden-claim audit, schema_version
  emitted, top-level key coverage.

### Phase C — Cohort snapshot writer (CLI) + listing endpoint

**Goal:** A reviewer writes a snapshot from CLI; an endpoint lists
existing snapshots so the frontend can drive the picker.

**Deliverables:**

- `backend/app/services/reporting/cohort_snapshot.py` (NEW): pure
  builder. `CohortSnapshot` dataclass + `build_cohort_snapshot(repo_root)`
  returns the full snapshot payload (cohort_overview + per-case
  completeness_scorecards + per-case reproducibility_manifests +
  bundle_bytes). `write_cohort_snapshot(snapshot, output_dir)`
  refuses any path under `golden_samples/**`; writes
  `<output_dir>/<UTC>/{cohort_overview.json,completeness/<case>.json,
   reproducibility/<case>.json,reviewer_bundle.zip,SNAPSHOT_MANIFEST.json}`.
- `scripts/write_cohort_snapshot.py` (NEW): CLI driver.
- `backend/app/services/reporting/cohort_snapshot_listing.py` (NEW):
  pure scanner over `reports/snapshots/*/` returning a list of
  `SnapshotListingEntry` records (utc_timestamp, case_count,
  mean_score_at_snapshot_time, manifest_path).
- `backend/app/api/routes/cohort_snapshots.py` (NEW): GET
  `/api/v1/cohort-snapshots` streams the listing.
- Tests: 9 covering snapshot construction, write refuses
  golden_samples/**, listing scanner over empty + populated
  reports/snapshots/, schema_version on every emitted artifact,
  Tier 1 boundary preservation, forbidden-claim audit.

### Phase D — Cohort snapshot diff endpoint

**Goal:** Reviewer picks two snapshots, sees drift.

**Deliverables:**

- `backend/app/services/reporting/cohort_snapshot_diff.py` (NEW):
  pure differ. `CohortSnapshotDiff` dataclass with:
  generated_at_utc, schema_version, claim_boundary, snapshot_a +
  snapshot_b provenance, cases_added (list of case_ids), cases_removed,
  cases_score_improved (list of {case_id, score_a, score_b, delta}),
  cases_score_regressed (same shape), cases_unchanged,
  rubric_version_drift (a→b string when versions differ; else null),
  tier2_blockers_remaining, claim_impact.
- `backend/app/api/routes/cohort_snapshot_diff.py` (NEW): GET
  `/api/v1/cohort-snapshot-diff?a=<utc>&b=<utc>` resolves both
  utc identifiers under `reports/snapshots/` with strict anchoring
  + rejects path traversal + 404 on missing.
- Tests: 8 covering identity diff (no drift), case added, case
  removed, score improved (decks-only → full evidence), score
  regressed, rubric version drift detected, path-traversal
  rejection, Tier 1 boundary preservation.

### Phase E — Frontend snapshot picker + drift panel + reproducibility card

**Goal:** Workbench surfaces the snapshot listing + diff + the
reproducibility manifest for the selected case.

**Deliverables:**

- `frontend/src/cohortSnapshotsClient.ts` (NEW): typed fetch +
  parser for the listing endpoint.
- `frontend/src/cohortSnapshotDiffClient.ts` (NEW): typed fetch +
  parser for the diff endpoint + tone helpers for score-improved
  (accent) vs score-regressed (danger) bands.
- `frontend/src/reproducibilityManifestClient.ts` (NEW): typed
  fetch + parser for `/reproducibility-manifest/<id>`.
- `frontend/src/components/CohortSnapshotPanel.tsx` (NEW): two
  snapshot dropdowns driven by the listing endpoint; "Compute drift"
  button → renders the structured diff with tone-coded sections.
- `frontend/src/components/ReproducibilityManifestCard.tsx` (NEW):
  inline card surfacing the selected case's manifest below the
  completeness card.
- `frontend/src/App.tsx`: integrate both panels in the Visual tab;
  new Trust Center review card `cohort_snapshot_status`.
- Tests: 13 covering parsers, fetch live/fallback/non-2xx, tone
  bands, URL builders, snake/camel for all three new endpoints.

### Phase F — HTTP-layer + E2E snapshot workflow tests

**Goal:** Every Phase 5 endpoint has HTTP-layer coverage; one
load-bearing E2E proves the full snapshot/repro/version workflow.

**Deliverables:**

- `tests/test_phase5_endpoints_integration.py` (NEW): TestClient
  suite covering `/reproducibility-manifest/<id>`,
  `/cohort-snapshots`, `/cohort-snapshot-diff?a=...&b=...` for
  status / content-type / Tier 1 boundary / schema_version /
  path-traversal rejection.
- `tests/test_fm04a_phase5_snapshot_workflow_e2e.py` (NEW): one
  load-bearing E2E test that:
  1. Seeds a 3-case synthetic cohort with mixed completeness;
  2. Writes snapshot A via the writer;
  3. Mutates one case's evidence (regression);
  4. Adds a 4th case (new case);
  5. Writes snapshot B;
  6. Lists both via the listing scanner;
  7. Diffs A vs B via the snapshot differ;
  8. Asserts: cases_added contains the new case, cases_score_regressed
     contains the mutated case with correct delta;
  9. Final Tier 1 audit + FM-04b blockers list still present.
- ≥15 new tests total.

### Phase G — STATE refresh + Phase 5 retrospective with final scorecard

**Goal:** STATE.md stamp + Phase 5 ledger; retrospective publishes
per-axis breakdown vs the binding rubric.

---

## SCORING RUBRIC (binding contract, same axes as Phase 4)

Each commit publishes a SCORECARD block; each sub-phase rolls up;
final retrospective publishes the phase total.

### Axes and weights (sum = 100)

| Code | Axis | Weight | Phase-5-specific anti-gaming guards |
|------|------|--------|--------------------------------------|
| **B** | Boundary discipline | 15 | -3 per positive-claim leak; -5 per HF1 hit; -3 per writer that can target `golden_samples/**`; **-2 per missing `schema_version` field on a new output** |
| **M** | Mechanical verification | 15 | -1 per failing test (cap -15); -3 per ruff/tsc/vite failure |
| **T** | Test coverage quality | 15 | -3 if any feature lacks integration test; -3 if any test depends on real OpenRadioss; -2 per missing edge case; **-2 per missing `schema_version` assertion in any new builder test** |
| **C** | Code quality | 10 | -2 per drive-by; -2 per backcompat shim; -1 per WHAT-comment; -2 per dead code block |
| **X** | API / UX coherence | 10 | -2 per inconsistent error code; -2 per duplicated tone logic; **-2 if any frontend client silently drops `schemaVersion`** |
| **D** | Documentation | 10 | -2 per undocumented public function; -3 if STATE not refreshed at G; -3 if retrospective omits a deferred FM-04b prerequisite; **-3 if Phase A's `_schema_versions.py` lacks a documented bump policy** |
| **A** | Architecture fit | 10 | -3 per new heavyweight dep (subprocess is stdlib; importlib.metadata is stdlib — not penalized); -3 per abstraction without ≥2 consumers; -3 per fork of existing pattern |
| **E** | E2E feature completeness | 15 | -3 per workflow step missing from E2E; -3 per stub frontend; -3 if reviewer cannot complete the workflow described in the north star |

### Stop conditions (identical to Phase 4)

- **≥95 total AND every axis ≥90% of its weight** → write retrospective and stop.
- **90 ≤ total < 95** → identify weakest axis, write a focused iteration commit, re-score.
- **80 ≤ total < 90** → iterate top-2 weakest axes, re-score.
- **< 80** → revisit blueprint scope.

### Honesty discipline (load-bearing)

- Every deduction must cite a concrete defect (commit SHA + file:line OR test name OR observed behavior).
- Re-scoring at sub-phase close re-evaluates **all axes against the running cumulative state**, not just the just-shipped sub-phase. Regressions count.
- Scores are not allowed to go up without a corresponding commit fixing the cited defect.
- No grade inflation: 95 means truly excellent, not "I tried hard".

---

## What this phase explicitly does NOT do

- **No FM-04b prerequisite work.** ADR-024 (full), benchmark
  comparison producer, sealed packet, independent reviewer signoff,
  user milestone-experience acceptance, signed registry flip, and
  Linear/Notion mirror writes all remain on the FM-04b side.
- **No real OpenRadioss dependency.** Synthetic fixtures only.
- **No HF1 forbidden zone touched.** Every new file lives under
  `backend/app/services/reporting/`, `backend/app/api/routes/`,
  `frontend/src/`, `frontend/test/`, `tests/`, or `scripts/`.
- **No new heavy dependencies.** `subprocess` and
  `importlib.metadata` are stdlib. Everything else reuses what
  Phase 1-4 already imports.
- **No schema migration logic in Phase 5.** Schema versions are
  emitted but no backward-compat dispatch is implemented yet —
  the versioning is structural foundation, not active dispatch.
  Future phases can add migration layers when needed.
- **No push, no PR, no external write.** Trailer rewrite reserved
  for human-user push time.

---

## Verification gates (mechanical, every commit)

1. `pytest -q` — all new tests pass; no regressions vs Phase 4 baseline (1375 / 8).
2. `node --test --experimental-strip-types frontend/test/*.test.ts` — all new tests pass; no regressions vs Phase 4 baseline (85).
3. `tsc -b` + `npm run build` (vite) — clean.
4. `pre-commit run --all-files` — ruff + ruff-format + HF1 path-guard pass.
