# FM-04a Phase 9 — Reviewer Active Surface & Trend Visibility Closure

> **Tier 1 engineering candidate; not signed validation; not benchmark agreement.**
>
> **Stamp target:** `fm04a-phase9-active-surface-trend-closure-2026-05-16`. Branch `claude/FM-04a-tier1-ballistic-candidate`. Author: local Claude Opus 4.7 under direct-execution authorization. No Codex review required for this Tier 1 candidate scope. No push, no PR, no Linear / Notion writes.
>
> **Forbidden wording (per ADR-023 + ADR-024 lite):** no `benchmark agreement`, no `signed validation`, no `perforation completed`, no `bullet-through-steel complete`, no `validated physics`, no `validated against` — except inside `not <claim>` disclaimer prefix.

## 1 · Why Phase 9 (Phase 8 carry-forward closure)

Phase 8 closed at 100/100 and identified five honest carry-forwards in its
retrospective §"Carry-forward into Phase 9 (or beyond)":

| # | Phase 8 carry-forward | Phase 9 slice |
|---|------------------------|---------------|
| 1 | No `POST` endpoint for `write_signoff_record` | **9-A** |
| 2 | `generator` input kind not in `PROVENANCE_INPUT_KINDS` | **9-B** |
| 3 | Cohort bucket thresholds (80 / 50) opinionated first cut | **9-C** |
| 4 | Anomaly detection only walks the latest snapshot point | **9-D** |
| 5 | Frontend panels do not yet surface provenance | **9-E** |

Phase 9 closes every one of them at the HTTP + frontend surface. No new
strategic scope is added beyond closing the Phase 8 retrospective.

## 2 · North-star reviewer questions

After Phase 9 the reviewer can answer five new questions on the live
workbench without leaving the UI:

1. **"Can I record my judgment from the UI?"** — Today the only path is
   the direct Python API. Phase 9 A adds the HTTP write surface.
2. **"Is the recompute reproducible end-to-end, including the script?"** —
   Phase 9 B freezes the generator script bytes into the snapshot and
   surfaces its SHA in the provenance trace.
3. **"Are the cohort bucket thresholds defensible?"** — Phase 9 C ships a
   sensitivity-pinning test set + methodology doc so future rebalances
   are traceable.
4. **"Is the case trend-degrading even though no single point is an
   outlier?"** — Phase 9 D adds per-axis slope detection orthogonal to
   the z-score anomaly endpoint.
5. **"What input bytes produced this score?"** — Phase 9 E surfaces the
   provenance trace as a UI panel, not just an HTTP endpoint.

## 3 · Slice plan (A → G)

### 3.A — POST signoff-history endpoint

**Surface added:** `POST /api/v1/signoff-history/<case-id>`.

* Request body (JSON): `{ "reviewer": str, "verdict": str, "notes": str }`.
* Calls `write_signoff_record(...)` from the existing service layer.
* Returns 200 + the newly-written record JSON on success.
* Returns **422** with explicit `detail` for: empty `reviewer`, empty
  `verdict`, verdict not in `SUPPORTED_SIGNOFF_VERDICTS`, notes failing
  `_assert_no_overclaim`, or path-traversal attempt on the case id.
* Returns **422** for the `^GS-\d{3}$` signed-registry case id pattern
  (same refusal as the Python API).

**Tests (≥10):**
* 4 verdict-positive write+read roundtrips.
* Each 422 path pinned to the unique `detail` string.
* HTTP envelope echoes Tier 1 disclaimer trio on the success response.
* Header `Content-Type: application/json` required on POST (415 otherwise).
* Read-back via the existing `GET /api/v1/signoff-history/<case>` returns
  the POSTed record in the chronologically-ordered list.

### 3.B — `generator` input kind in provenance

**Service change:**
* Extend `cohort_snapshot.write_cohort_snapshot` to copy
  `generator_script_path` bytes into `<snap>/generator/<case>.py` (only
  when `generator_script_path` is set + the file exists; otherwise the
  case row is silently skipped, same fallback as Phase 6/7 metrics +
  convergence).
* Extend `PROVENANCE_INPUT_KINDS` from
  `("metrics", "convergence", "completeness", "reproducibility")` to
  `("metrics", "convergence", "completeness", "reproducibility", "generator")`.
* Extend `_walk_inputs` to look at `<snap>/generator/<case>.py` (the
  `.py` extension is intentional; not all input kinds are JSON, and the
  walker computes SHA-256 over raw bytes regardless of extension).
* Bump `TRUST_SCORE_PROVENANCE_SCHEMA_VERSION` **MINOR** to `"1.1.0"`
  (a new enum value added to an existing field; not a rename, not a
  removal). Bump `COHORT_SNAPSHOT_MANIFEST_SCHEMA_VERSION` **MINOR** to
  `"1.3.0"` (new optional snapshot subdirectory).

**Tests (≥10):**
* Generator-present case yields `present=True` + SHA matching captured bytes.
* Generator-missing case yields `present=False` + `sha256=None`.
* `PROVENANCE_INPUT_KINDS` length 5 + order pinned.
* Schema-version bump asserted in both timeline AND provenance tests.
* Snapshot writer integration test confirms the new subdirectory only
  exists when at least one case had a generator path that landed on disk.
* Old (1.0.0) provenance trace reads back without crash (forward-compat
  guard: 1.1.0 reader tolerates a snapshot that lacks `generator/`).

### 3.C — Bucket sensitivity + rebalance methodology

**Doc added:** `.planning/methodology/cohort_bucket_thresholds.md`.

* Names the two thresholds (`HEALTHY_TRUST_SCORE_MIN=80`,
  `WATCHING_TRUST_SCORE_MIN=50`).
* States the precedence rule (`regressed > watching > healthy`).
* Documents the rebalance procedure: which version field bumps,
  required sensitivity test additions, retrospective entry.
* Documents the rationale for 80 / 50 (engineering judgment, not
  benchmark agreement) — explicitly Tier 1 candidate scope.

**Test file added:** `tests/test_phase9_bucket_sensitivity_matrix.py`.

* ≥12 boundary tests pinning every neighbourhood of the two thresholds
  (49 / 50 / 51 / 79 / 80 / 81 for trust_score) × signoff state matrix
  (no signoff / `watching` / `needs_more_*` / `blocked_pending_input`).
* `blocked_pending_input` overrides bucket to `regressed` regardless of
  trust score — pinned at score=99 with this verdict.
* Drift guard: an assertion that the threshold constants are exactly 80
  and 50 (so a silent edit of the constant fails the suite).

**No envelope schema bump** — this slice ships pinning + methodology
only.

### 3.D — Trend-slope anomaly endpoint

**Service added:** `backend/app/services/reporting/cohort_trend_anomalies.py`.

* New schema constant `COHORT_TREND_ANOMALIES_SCHEMA_VERSION = "1.0.0"`.
* For each case in the cohort, walk its trust-score timeline via
  `build_trust_score_timeline`. If at least
  `TREND_MIN_POINTS = 3` points exist, compute the **least-squares slope**
  per axis (`completeness_weighted`, `convergence_weighted`,
  `energy_audit_weighted`, `reproducibility_weighted`) treating point
  index `0..N-1` as the x-axis (snapshots are time-ordered).
* Flag negative drift below named thresholds:
  - `TREND_SLOPE_INFO_MAX = -0.5` (units = weighted-points per snapshot)
  - `TREND_SLOPE_WARN_MAX = -1.5`
  - `TREND_SLOPE_DANGER_MAX = -3.0`
* `severity_for_slope(slope) -> "info" | "warn" | "danger"` mirrors the
  Phase 8 E severity function (most-conservative bucket on bypass).
* Tuple SSOT: `TREND_AXES = ("completeness", "convergence", "energy_audit", "reproducibility")` (matches `ANOMALY_AXES`).
* Envelope carries `point_count_floor: int = 3`,
  `cohort_count`, `anomaly_count`, plus the standard claim envelope.

**Endpoint added:** `GET /api/v1/cohort-trend-anomalies`.

**Tests (≥14):**
* `severity_for_slope` boundary pins at `-0.5 / -1.5 / -3.0` (≤ exact
  boundary returns the worse bucket per a documented rule: the slope is
  *more negative*, hence worse).
* `severity_for_slope(0.0) == "info"` (no firing because the gate is
  upstream).
* Cohort floor case: a case with only 2 snapshot points returns
  no anomalies (`TREND_MIN_POINTS = 3`).
* Engineered descending case (5 timeline points 90 → 80 → 70 → 60 → 50)
  fires danger on the completeness axis.
* Engineered flat case (5 timeline points 85 / 85 / 85 / 85 / 85) does
  not fire.
* Engineered ascending case does not fire (positive slope).
* `COHORT_TREND_ANOMALIES_SCHEMA_VERSION == "1.0.0"`.
* Tier 1 disclaimer trio in envelope.
* Endpoint pin: `GET /api/v1/cohort-trend-anomalies` returns 200 + the
  envelope shape on an empty cohort (`cohort_count=0`,
  `anomaly_count=0`).

### 3.E — `ProvenancePanel` frontend surface

**Files added:**
* `frontend/src/trustScoreProvenanceClient.ts` (typed client).
* `frontend/src/components/ProvenancePanel.tsx`.

**Wiring:**
* `App.tsx` mounts `ProvenancePanel` when a `latestSnapshotLabel` is
  available (lifted from the snapshot panel — pure pass-through, no
  duplicate fetch).
* The panel takes `caseId` + `snapshotLabel` props; on mount it fetches
  the provenance trace.
* Renders four columns: `kind`, `path`, `present`, `sha256` (first 12
  chars). Missing inputs render with a muted style + `—`.
* Renders the trust score recompute block + formula version + the new
  `generator` row (from slice 9-B).
* Defensive parser: unknown `kind` values fall back to `"unknown"` and
  render in a neutral state (UI must never crash on a 1.2.0+ provenance
  trace that adds another kind).

**Vitest coverage (≥6):**
* Empty inputs → empty rows + claim disclaimer rendered.
* All-present case → 5 rows with SHA chips.
* `present=false` case → muted row.
* Defensive parser: unknown kind falls back to "unknown".
* Provenance panel only mounts when a snapshot label is known.
* Tier 1 disclaimer trio rendered in the panel header / footer.

### 3.F — HTTP integration + E2E reviewer journeys

**Tests added (`tests/test_phase9_endpoints_integration.py`):**
* ≥16 integration tests covering:
  - POST signoff (success per verdict + every 422 path)
  - Generator-extended provenance trace
  - Trend anomaly endpoint envelope + danger fire
  - Cohort summary + anomaly + trend chained read
  - Severity boundary pin for `cohort-trend-anomalies` warn at exact `-1.5`

**E2E added (`tests/test_fm04a_phase9_reviewer_active_surface_e2e.py`):**
* ≥3 reviewer journeys:
  1. POST → GET signoff round-trip → cohort summary reflects new verdict.
  2. Generator-frozen snapshot → provenance trace surfaces generator SHA
     matching captured bytes.
  3. Five descending snapshots → trend anomaly fires on completeness axis,
     z-score anomaly does NOT fire (orthogonality check).

### 3.G — STATE refresh + retrospective + final whole-arc TAA

* Update `.planning/STATE.md` stamp + add Phase 9 ledger.
* Author `.planning/retrospectives/fm04a_phase9_active_surface.md`.
* Spawn final whole-arc TAA via general-purpose subagent.
* Archive `FINAL.md` under `.planning/phase9_audit_reports/`.

## 4 · Binding 9-axis rubric (same shape as Phase 7 / 8 = 100 max)

| Axis | Weight | Definition | -X anti-gaming guards |
|------|--------|------------|-----------------------|
| **B** — schema versioning behavior | 12 | New constant `COHORT_TREND_ANOMALIES_SCHEMA_VERSION`; MINOR bumps on `TRUST_SCORE_PROVENANCE_SCHEMA_VERSION` (1.0.0 → 1.1.0) and `COHORT_SNAPSHOT_MANIFEST_SCHEMA_VERSION` (1.2.0 → 1.3.0). Both bumps carry SCORECARD line in retrospective. | -3 per missing rationale block, -5 per silent rename, -2 if reader is not forward-compatible across the MINOR bump |
| **M** — module quality | 12 | Pure builders. Named threshold constants for trend slopes. No I/O leaks. UTC-only timestamps. Tuple SSOT for `PROVENANCE_INPUT_KINDS` + `TREND_AXES`. | -2 per orphaned magic number, -2 per local-time fallback, -3 per circular import |
| **T** — testing | 15 | ≥10 per slice A/B; ≥12 slice C boundary matrix; ≥14 slice D; ≥6 vitest slice E; ≥16 slice F integration; ≥3 slice F E2E. Boundary pins at every severity threshold. | -2 per axis lacking a boundary pin, -3 if E2E is mocked instead of ASGITransport-driven, -2 per slope-firing test that lacks an opposite-direction negative-control case |
| **C** — claim-tier discipline | 12 | HF1 guard green. No `^GS-\d{3}$` registry edits. POST endpoint refuses signed-registry case id with HTTP 422. Tier 1 disclaimer trio in every new envelope. Two-list forbidden-token design preserved on the new envelope (slice D). | -10 if any new surface emits without disclaimer trio, -8 if POST endpoint accepts a Tier 2 promotion verb in `verdict`, -5 if envelope audit uses notes-list and crashes on its own disclaimer text (Phase 7 B / 8 B trap) |
| **X** — frontend integration | 12 | New `trustScoreProvenanceClient.ts` exports as-const `PROVENANCE_INPUT_KINDS` tuple in TS that matches backend tuple exactly. `ProvenancePanel` defensive parser falls back to `"unknown"` for unknown kind. Panel only renders subline when SHA + present=true. | -3 per silent fetch failure, -2 if defensive parser falls to a Tier 2 verb on unknown input, -2 per duplicate fetch path |
| **D** — documentation / SSOT | 8 | Methodology doc lives at `.planning/methodology/cohort_bucket_thresholds.md` + linked from retrospective. Blueprint published BEFORE any code. Retrospective rebuilds the SCORECARD with evidence. | -2 if methodology doc is missing or references non-existent constants, -2 per stale retrospective cross-reference |
| **A** — anti-gaming discipline | 8 | Every slice carries an explicit anti-gaming guard hit-count of 0 in the retrospective. Self-attestation alone does NOT close the slice; the slice TAA returns APPROVE before commit. | -3 per gaming guard triggered, -3 per self-attestation closure without TAA APPROVE |
| **E** — end-to-end workflow | 8 | All 5 new questions answerable from the live workbench. POST → GET round-trip with cohort summary mirror. Trend endpoint orthogonal to z-score (engineered case that fires one but not the other). | -3 per question still unanswerable post-Phase-9, -2 per E2E that doesn't compose ≥3 phases of surfaces |
| **V** — verification by TAA | 13 | Per-slice TAA (A/B/C/D/E/F) + final whole-arc TAA in G. Every BLOCK / HIGH closed by fix commit, not waiver. | -2 per LOW finding, -5 per HIGH finding deferred without fix, -10 per BLOCK |
| **Total** | **100** | | |

**Stop condition:** cumulative ≥ 99 AND every axis ≥ 95 % of weight.

**Honest scoring policy:** if any slice TAA returns CHANGES_REQUIRED for
a HIGH finding, the relevant axis drops by the indicated amount and a
fix-up commit must close the gap before Phase 9 G can ship its FINAL TAA.
The same honest-pattern as Phase 7 G (`3d681f2`) and Phase 8 G — close
gaps with code, never with waivers.

## 5 · Test Auditor Agent (TAA) protocol

Same protocol as Phase 7 / Phase 8:

1. After each slice A-F's author commit, spawn a general-purpose
   subagent prompted with:
   * The Phase 9 blueprint (this file)
   * The exact slice author commit SHA + scope
   * The 9-axis rubric
   * A demand for independent verification: `pytest` count + `tsc -b` +
     `vitest run` count, plus a fresh read of the slice's source files
     + a probe for the anti-gaming guards.
2. The TAA returns one of `APPROVE` / `CHANGES_REQUIRED` / `BLOCK` per
   slice with HIGH / MEDIUM / LOW findings + a per-axis score
   contribution.
3. CHANGES_REQUIRED on HIGH → a fix-up commit closes the gap; the
   slice's V-axis contribution drops to reflect the round trip.
4. APPROVE without HIGH/BLOCK → the slice's contribution lands at full
   weight; LOW findings are honestly logged in the retrospective.
5. Slice G spawns a final whole-arc TAA that re-verifies every slice's
   composite + the SCORECARD's evidence chain. The final TAA's verdict
   gates the Phase 9 closure stamp on STATE.md.

## 6 · Anti-gaming guard ledger (17 total)

Repeated from Phase 8 with Phase 9 deltas:

| Guard | Axis | Description |
|-------|------|-------------|
| C: -10 | C | POST endpoint must refuse Tier 2 promotion verbs at request-validation time, NOT at write time. The whitelist is the load-bearing safety boundary. |
| C: -8 | C | Notes audit on POST must run before any disk write. |
| C: -5 | C | Envelope audit must use the narrowed 4-token list, not the 6-token notes list (Phase 7 B trap). |
| M: -3 | M | UTC-only timestamps. No local time. |
| M: -2 | M | Named constants for every trend-slope threshold. |
| M: -2 | M | Tuple SSOT for `PROVENANCE_INPUT_KINDS` AND `TREND_AXES`. Mismatch = -2. |
| T: -2 | T | Each severity bucket gets a boundary pin (info / warn / danger). |
| T: -2 | T | Cohort size 1 / 2 returns empty (same Phase 8 E pattern, here for trend point count floor). |
| T: -2 | T | Every trend-firing test has an opposite-direction negative-control test in the same module. |
| T: -3 | T | E2E must be ASGI-driven; mocking the route layer is a -3. |
| X: -3 | X | Defensive parser on UI falls back to most-conservative neutral state. |
| X: -2 | X | No duplicate fetch on the same panel mount. |
| D: -2 | D | Methodology doc must reference constants by their full Python identifier. |
| A: -3 | A | Self-attestation alone does NOT close a slice. |
| V: -10 | V | Any BLOCK finding outstanding at Phase 9 G is a -10. |
| V: -5 | V | Any HIGH finding deferred to Phase 10 is a -5 (only LOW may be deferred). |
| E: -3 | E | Every Phase 9 reviewer question must be answerable from the UI by closure. |

## 7 · Phase 8 carry-forward disposition

| Phase 8 carry-forward | Disposition in Phase 9 |
|------------------------|-------------------------|
| POST signoff endpoint | **Closed by slice 9-A**. |
| `generator` input kind | **Closed by slice 9-B**. |
| Cohort bucket thresholds | **Closed by slice 9-C** (methodology + sensitivity matrix). |
| Trend-slope anomalies | **Closed by slice 9-D**. |
| `ProvenancePanel` | **Closed by slice 9-E**. |

## 8 · Constraints replicated from Phase 8

* Tier 1 engineering candidate; not signed validation; not benchmark agreement.
* No FM-04b prerequisite crossed.
* No `^GS-\d{3}$` signed-registry edits.
* No Linear / Notion writes.
* No `golden_samples/**` writes outside `*-candidate`.
* No real OpenRadioss solver invocation.
* No LLM call.
* No push, no PR, no external write.
* No HF1 hard-stop zone edits.

## 9 · Commit cadence

* `2e640f6` … `a0585aa` (Phase 8) → Phase 9 begins at next commit.
* Each slice = one commit (or one slice commit + one TAA-driven fix-up
  commit if HIGH findings need closing).
* Final closure commit pattern: `docs(FM-04a/Phase9-G): archive FINAL
  whole-arc TAA — APPROVE NN/100; Phase 9 closed`.
