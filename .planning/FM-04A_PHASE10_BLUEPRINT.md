# FM-04a Phase 10 — Reviewer Action Surface & Calibration Closure

> **Tier 1 engineering candidate; not signed validation; not benchmark agreement.**
>
> **Stamp target:** `fm04a-phase10-action-surface-calibration-2026-05-16`. Branch `claude/FM-04a-tier1-ballistic-candidate`. Author: local Claude Opus 4.7 under direct-execution authorization. No Codex review required for this Tier 1 candidate scope. No push, no PR, no Linear / Notion writes.
>
> **Forbidden wording (per ADR-023 + ADR-024 lite):** no `benchmark agreement`, no `signed validation`, no `perforation completed`, no `bullet-through-steel complete`, no `validated physics`, no `validated against` — except inside `not <claim>` disclaimer prefix.

## 1 · Why Phase 10 (Phase 9 carry-forward closure)

Phase 9 closed at 100/100 and identified five honest carry-forwards in its
retrospective §"Carry-forward into Phase 10 (or beyond)":

| # | Phase 9 carry-forward | Phase 10 slice |
|---|------------------------|----------------|
| 1 | POST endpoint not yet surfaced in the UI | **10-A** |
| 2 | Trend-anomaly UI panel missing | **10-B** |
| 3 | Trend severity thresholds uncalibrated (no methodology doc) | **10-C** |
| 4 | POST endpoint does not enforce per-reviewer rate limiting | **10-D** |
| 5 | `generator` SHA only over raw bytes (no canonical-form comparison) | **10-E** |

Phase 10 closes every one of them at the HTTP + frontend surface. No new
strategic scope is added beyond closing the Phase 9 retrospective.

## 2 · North-star reviewer questions

After Phase 10 the reviewer can answer five new questions on the live
workbench without leaving the UI:

1. **"Can I submit my signoff from the UI itself, with a verdict picker
   that refuses Tier 2 verbs by construction?"** — Today the only path
   is the HTTP API; Phase 10 A adds the UI form.
2. **"Where are the trend-degrading cases for the cohort?"** — Phase 9 D
   ships the trend endpoint; Phase 10 B surfaces it in a panel.
3. **"Are the trend-slope thresholds defensible the same way the bucket
   thresholds are?"** — Phase 10 C writes the parallel methodology doc.
4. **"Can a careless reviewer flood the signoff log?"** — Phase 10 D
   adds a per-(case, reviewer) rate limit.
5. **"Are these two generators logically equivalent even after a
   formatting change?"** — Phase 10 E adds the AST-canonical SHA next
   to the raw-bytes SHA.

## 3 · Slice plan (A → G)

### 3.A — `SignoffSubmissionForm` UI

**Files touched/added:**
* `frontend/src/components/SignoffHistoryPanel.tsx` — embed a submission
  form above the chronological list. Verdict dropdown bound to
  `SUPPORTED_SIGNOFF_VERDICTS` as-const (4 options). Notes textarea with
  a 4-token client-side preview that flags forbidden positive claims
  before submit (UX), but the server-side audit remains the load-bearing
  refusal (defense in depth).
* `frontend/src/signoffHistoryClient.ts` — add `submitSignoff(apiBase,
  caseId, body)` returning `{ ok, record?, error?, retryAfterSeconds? }`.
  On 429, surface `retryAfterSeconds` from header.

**UX behavior:**
* On successful submit (200), clear the form + call `onSubmitSuccess`
  callback so the panel re-fetches history.
* On 422, surface the response `detail` next to the form.
* On 429, surface "rate limit hit — try again in N seconds" with a
  countdown derived from `Retry-After`.
* On 415, never surface (the form always sends `application/json`); but
  defensively handle as an error rather than silent submit.
* Submit button disabled when verdict or reviewer is empty.

**Anti-gaming guards exercised:**
* C: -10 — verdict dropdown can only emit values from the
  `SUPPORTED_SIGNOFF_VERDICTS` as-const tuple. A future maintainer who
  adds a Tier 2 verb to the dropdown discovers the import-time backend
  audit (Phase 8 A) refuses module load — the UI cannot route around
  it.
* X: -2 — `onSubmitSuccess` triggers a single re-fetch; no duplicate
  fetch path.
* X: -3 — defensive error rendering: any non-200 response surfaces an
  error inline; the form does not silently no-op.

**Vitest coverage (≥7):**
* Form renders 4 verdict options matching `SUPPORTED_SIGNOFF_VERDICTS`.
* Disabled state when reviewer / verdict empty.
* Successful submit triggers `onSubmitSuccess`.
* 422 response surfaces `detail` inline.
* 429 response surfaces `Retry-After` countdown.
* Tier 2 verb cannot be selected (dropdown does not offer it).
* Client-side forbidden-claim preview warns on notes containing
  forbidden tokens outside `not <claim>` form (UX, not load-bearing).

### 3.B — `CohortTrendAnomaliesPanel` UI

**Files added:**
* `frontend/src/cohortTrendAnomaliesClient.ts` — typed client mirroring
  `cohortAnomaliesClient.ts` shape. Exports `SUPPORTED_TREND_SEVERITIES`
  as-const = `['info', 'warn', 'danger']`. Defensive parser maps
  unknown severity → `'info'` (most-conservative). Fetches
  `/api/v1/cohort-trend-anomalies`.
* `frontend/src/components/CohortTrendAnomaliesPanel.tsx` — mirrors
  `CohortAnomaliesPanel.tsx` layout: 5-column grid (case / axis /
  slope / points / severity). Slope rendered to 2 decimal places.
  Severity color matches Phase 8 E pattern (`info` = accent green,
  `warn` = warning amber, `danger` = danger red).

**App.tsx wiring:**
* Mount adjacent to `CohortAnomaliesPanel` so reviewers see both views
  side by side. No props beyond `apiBase`.

**Vitest coverage (≥5):**
* Empty cohort renders "no trend regressions" copy.
* Outlier row renders slope + severity.
* Severity color renders by class / inline style.
* Defensive parser maps unknown severity to `info`.
* Tier 1 disclaimer trio rendered in panel body.

### 3.C — Trend-slope threshold methodology + sensitivity

**Doc added:** `.planning/methodology/cohort_trend_slope_thresholds.md`.

* Names `TREND_SLOPE_INFO_MAX = -0.5`, `TREND_SLOPE_WARN_MAX = -1.5`,
  `TREND_SLOPE_DANGER_MAX = -3.0`, `TREND_MIN_POINTS = 3` by full
  Python identifier.
* Documents the "more negative is worse" convention.
* Documents the boundary semantics (`slope <= threshold` lands in the
  worse bucket).
* Documents the rebalance procedure (parallel to Phase 9 C bucket
  methodology): retrospective entry, sensitivity-matrix extension,
  `COHORT_TREND_ANOMALIES_SCHEMA_VERSION` PATCH or MINOR bump rule,
  frontend defensive-parser forward-compat check.
* Documents what is NOT a rebalance (changing `TREND_MIN_POINTS` is a
  separate decision; adding a new axis bumps `TREND_AXES` SSOT).
* States Tier 1 candidate scope explicitly.

**Test file added:** `tests/test_phase10_trend_slope_sensitivity_matrix.py`.

* ≥12 boundary cells pinning all four constants at exactly their
  current values.
* Severity outcome for slope at exactly `-0.49`, `-0.50`, `-1.49`,
  `-1.50`, `-2.99`, `-3.00`, `-3.01`, plus 0.0 / +1.0 (no fire).
* Point-count floor cells at 0/1/2/3/4 (only ≥3 fires).
* Drift guard: methodology doc cites all four constants by Python
  identifier + has Tier 1 disclaimer trio + has the precedence rule
  (`more negative is worse`).

**No envelope schema bump** — this slice ships methodology + pinning
only.

### 3.D — Per-reviewer rate limit on POST signoff

**Service module added:** `backend/app/services/reporting/signoff_rate_limit.py`.

* `RATE_LIMIT_MAX_REQUESTS: int = 5` — max signoffs per (case_id,
  reviewer) per window.
* `RATE_LIMIT_WINDOW_SECONDS: int = 60` — sliding window length.
* `check_and_record(case_id, reviewer, now=None) -> RateLimitResult`
  where `RateLimitResult` is a dataclass with `allowed: bool` and
  `retry_after_seconds: int` (0 when allowed).
* `_reset_state_for_tests()` clears the in-memory state (per-test
  fixture hook).
* Sliding window: drop entries older than `RATE_LIMIT_WINDOW_SECONDS`
  from the deque before counting. No background timer; eviction is
  lazy on each call.

**Route change:** `backend/app/api/routes/signoff_history.py` — inject
the rate limit check between Pydantic validation (step 4 in Phase 9 A
gate ordering) and the verdict whitelist check (step 5). On
`allowed=False`, raise `HTTPException(status_code=429,
headers={"Retry-After": str(retry_after_seconds)})` with detail
`"rate limit exceeded for case_id={case_id} reviewer={reviewer}; retry
in N seconds"`.

**Tests (≥10):**
* Two named constants pinned.
* Single submission allowed.
* 5 sub-limit submissions all allowed in same window.
* 6th submission in same window returns 429 + `Retry-After`.
* Different reviewer on same case is independent (full limit).
* Same reviewer on different case is independent (full limit).
* After window expires (mocked clock), counter resets.
* HTTP-429 surfaced through the route layer + `Retry-After` header.
* `_reset_state_for_tests` clears state cleanly.
* Concurrent same-reviewer same-second submissions are bounded.

### 3.E — Generator canonicalization SHA

**Service change:** `backend/app/services/reporting/trust_score_provenance.py`.

* Add new dataclass field `ProvenanceInput.sha256_normalized: str | None`
  and `ProvenanceInput.normalization_method: str | None`. New schema
  serialization includes both fields on every input row (`None` for
  non-generator rows; set for generator rows with parse success;
  `None` + `normalization_error` for generator rows with parse failure).
* New private helper `_canonical_python_sha(raw_bytes: bytes) -> tuple[str | None, str | None]`
  returning `(sha, error)`. Implementation:
  ```python
  source = raw_bytes.decode("utf-8", errors="replace")
  try:
      tree = ast.parse(source)
  except SyntaxError as exc:
      return None, f"ast.parse failed: {exc.msg}"
  canonical = ast.dump(tree, annotate_fields=True, include_attributes=False)
  return hashlib.sha256(canonical.encode("utf-8")).hexdigest(), None
  ```
* `_walk_inputs` applies the canonicalization only when
  `kind == "generator"` AND `path.is_file()`. Other kinds keep
  `sha256_normalized=None`, `normalization_method=None`.

**Schema bump:** `TRUST_SCORE_PROVENANCE_SCHEMA_VERSION` 1.1.0 → 1.2.0
MINOR (additive fields on every input row).

**Tests (≥12):**
* Schema bumped to 1.2.0; bump-history rationale block extended.
* Generator parse success: `sha256_normalized` non-None +
  `normalization_method = "ast.dump"`.
* Generator parse failure (syntax error): `sha256_normalized = None`
  + `normalization_error` populated.
* Whitespace-only formatting change yields same `sha256_normalized`
  but different `sha256` (load-bearing semantic equivalence pin).
* Comment-only change yields same `sha256_normalized` but different
  `sha256` (comments stripped by `ast.parse`).
* Logic change yields different `sha256_normalized` AND `sha256`.
* Non-generator rows have `sha256_normalized = None`.
* Forward-compat: a snapshot from 1.1.0 (no `generator/<case>.py` on
  disk or no canonicalization metadata) still reads cleanly.

### 3.F — HTTP integration + E2E reviewer journeys

**Tests added (`tests/test_phase10_endpoints_integration.py`):**
* ≥16 integration tests covering:
  - POST signoff sub-limit (5 succeed)
  - POST signoff 6th 429 + `Retry-After`
  - POST signoff different reviewers independent
  - POST signoff different cases independent
  - Generator canonical SHA present after Phase 10 E
  - Generator parse-failure path
  - Schema bumped 1.2.0
  - Provenance envelope still carries 5 input kinds × 2 SHA columns
  - Trend-slope endpoint unchanged (regression guard)
  - Cohort summary unchanged (regression guard)

**E2E added (`tests/test_fm04a_phase10_action_surface_e2e.py`):**
* ≥3 reviewer journeys:
  1. POST 5 signoffs in rapid succession → 5 succeed, 6th 429; wait
     past window (mocked clock) → 7th succeeds.
  2. Same generator with different whitespace produces same
     `sha256_normalized` but different `sha256` (logic equivalence).
  3. Reviewer submits a signoff via the HTTP endpoint; subsequent
     trend-anomaly endpoint call composes across phases.

### 3.G — STATE refresh + retrospective + final whole-arc TAA

* Update `.planning/STATE.md` stamp + add Phase 10 ledger.
* Author `.planning/retrospectives/fm04a_phase10_action_surface.md`.
* Spawn final whole-arc TAA via general-purpose subagent.
* Archive `FINAL.md` under `.planning/phase10_audit_reports/`.

## 4 · Binding 9-axis rubric (same shape as Phase 7 / 8 / 9 = 100 max)

| Axis | Weight | Definition | -X anti-gaming guards |
|------|--------|------------|-----------------------|
| **B** — schema versioning behavior | 12 | MINOR bump on `TRUST_SCORE_PROVENANCE_SCHEMA_VERSION` (1.1.0 → 1.2.0). Bump-history rationale block extended. Forward-compat preserved (1.1.0 reader tolerates missing `sha256_normalized` field). | -3 per missing rationale block, -5 per silent rename, -2 if reader is not forward-compatible across the MINOR bump |
| **M** — module quality | 12 | Pure builders. Named rate-limit constants. UTC-only timestamps. No I/O leaks. AST canonicalization is deterministic (idempotent for syntactically identical inputs). Rate limit state has a documented `_reset_state_for_tests` hook. | -2 per orphaned magic number, -2 per local-time fallback, -3 per circular import, -3 if rate-limit state cannot be cleared for testing |
| **T** — testing | 15 | ≥7 vitest A; ≥5 vitest B; ≥12 sensitivity matrix C; ≥10 rate-limit D; ≥12 canonicalization E; ≥16 integration F; ≥3 E2E F. Boundary pins at every severity threshold. | -2 per axis lacking a boundary pin, -3 if E2E is mocked instead of ASGITransport-driven, -2 per rate-limit test that lacks a clock-mock |
| **C** — claim-tier discipline | 12 | HF1 guard green. No `^GS-\d{3}$` registry edits. UI verdict dropdown bound to as-const tuple (cannot offer Tier 2 verb). Backend import-time audit unchanged. Tier 1 disclaimer trio in every new envelope. | -10 if UI offers any Tier 2 verb in dropdown, -8 if rate-limit response lacks Tier 1 disclaimer envelope, -5 if envelope audit uses notes-list and crashes on its own disclaimer text |
| **X** — frontend integration | 12 | `cohortTrendAnomaliesClient.ts` exports as-const `SUPPORTED_TREND_SEVERITIES` matching backend tuple. `SignoffSubmissionForm` defensive submit (single fetch + clear-on-success + inline error). `CohortTrendAnomaliesPanel` defensive parser. App wiring touches both new panels without duplicate fetches. | -3 per silent fetch failure, -2 if defensive parser falls to a Tier 2 verb on unknown input, -2 per duplicate fetch path |
| **D** — documentation / SSOT | 8 | Trend methodology doc lives at `.planning/methodology/cohort_trend_slope_thresholds.md` parallel to Phase 9 C bucket doc. Blueprint published BEFORE any code. Retrospective rebuilds the SCORECARD with evidence. | -2 if methodology doc is missing or references non-existent constants, -2 per stale retrospective cross-reference |
| **A** — anti-gaming discipline | 8 | Every slice carries an explicit anti-gaming guard hit-count of 0 in the retrospective. Self-attestation alone does NOT close the slice; the slice TAA returns APPROVE before commit. Rate-limit tests use deterministic mocked clock, not `time.sleep`. | -3 per gaming guard triggered, -3 per self-attestation closure without TAA APPROVE, -2 per rate-limit test relying on real wall clock |
| **E** — end-to-end workflow | 8 | All 5 new questions answerable from the live workbench. UI submission round-trip with rate-limit observed. Canonicalization SHA proves whitespace-equivalence. | -3 per question still unanswerable post-Phase-10, -2 per E2E that doesn't compose ≥3 phases of surfaces |
| **V** — verification by TAA | 13 | Per-slice TAA (A/B/C/D/E/F) + final whole-arc TAA in G. Every BLOCK / HIGH closed by fix commit, not waiver. | -2 per LOW finding, -5 per HIGH finding deferred without fix, -10 per BLOCK |
| **Total** | **100** | | |

**Stop condition:** cumulative ≥ 99 AND every axis ≥ 95 % of weight.

**Honest scoring policy:** if any slice TAA returns CHANGES_REQUIRED
for a HIGH finding, the relevant axis drops by the indicated amount
and a fix-up commit must close the gap before Phase 10 G can ship its
FINAL TAA. Same honest-pattern as Phase 7 / 8 / 9 — close gaps with
code, never with waivers.

## 5 · Test Auditor Agent (TAA) protocol

Same protocol as Phase 7 / 8 / 9:

1. After each slice A-F's author commit, spawn a general-purpose
   subagent prompted with:
   * The Phase 10 blueprint (this file)
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
   gates the Phase 10 closure stamp on STATE.md.

## 6 · Anti-gaming guard ledger (17 total)

Repeated from Phase 9 with Phase 10 deltas:

| Guard | Axis | Description |
|-------|------|-------------|
| C: -10 | C | UI verdict dropdown bound to `SUPPORTED_SIGNOFF_VERDICTS` as-const tuple. Cannot offer a Tier 2 verb. |
| C: -8 | C | Rate-limit 429 response carries Tier 1 disclaimer envelope (HTTPException detail string + claim_tier inferable from error wrapper). |
| C: -5 | C | Envelope audit on the new provenance schema uses the narrowed 4-token list, not the 6-token notes list. |
| M: -3 | M | UTC-only timestamps. No local time. |
| M: -2 | M | Named constants for every new rate-limit value. |
| M: -3 | M | Rate-limit state has a documented `_reset_state_for_tests` hook. |
| M: -2 | M | AST canonicalization is deterministic (same input → same SHA). |
| T: -2 | T | Each new severity boundary in slice C gets a pin. |
| T: -2 | T | Rate-limit window boundary pinned (5 succeed / 6th 429 / wait past window / 7th succeed). |
| T: -2 | T | Rate-limit test uses mocked clock, not `time.sleep`. |
| T: -3 | T | E2E must be ASGI-driven; mocking the route layer is a -3. |
| X: -3 | X | Defensive parser on UI falls back to most-conservative neutral state. |
| X: -2 | X | No duplicate fetch on the same panel mount. |
| X: -2 | X | UI submit-on-success clears form + triggers single history refresh (no double fetch). |
| D: -2 | D | Methodology doc references constants by full Python identifier. |
| A: -3 | A | Self-attestation alone does NOT close a slice. |
| V: -10 | V | Any BLOCK finding outstanding at Phase 10 G is a -10. |

## 7 · Phase 9 carry-forward disposition

| Phase 9 carry-forward | Disposition in Phase 10 |
|------------------------|--------------------------|
| POST endpoint not yet surfaced in the UI | **Closed by slice 10-A**. |
| Trend-anomaly UI panel | **Closed by slice 10-B**. |
| Trend severity uncalibrated | **Closed by slice 10-C** (methodology + sensitivity matrix). |
| Per-reviewer rate limiting | **Closed by slice 10-D**. |
| Generator canonicalization SHA | **Closed by slice 10-E**. |

## 8 · Constraints replicated from Phase 9

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

* `f5bf4f4` … `1be908f` (Phase 9) → Phase 10 begins at next commit.
* Each slice = one commit (or one slice commit + one TAA-driven fix-up
  commit if HIGH findings need closing).
* Final closure commit pattern: `docs(FM-04a/Phase10-G): archive FINAL
  whole-arc TAA — APPROVE NN/100; Phase 10 closed`.
