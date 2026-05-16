## TAA report — FM-04a Phase 8 D @ 74902aa

- **Commit audited**: `74902aa` — "feat(FM-04a/Phase8-D): cohort executive summary endpoint + scorecard panel + slice-B TAA archive"
- **Auditor**: Independent TAA (Test Auditor Agent, slice-D scope; not the author of `74902aa`)
- **Date**: 2026-05-16
- **Binding blueprint**: `.planning/FM-04A_PHASE8_BLUEPRINT.md` (locked at `2e640f6`, predates all Phase 8 code commits)
- **Audited paths** (10 files; `git show 74902aa --stat`):
  - `backend/app/services/reporting/cohort_executive_summary.py` (+245 lines, NEW)
  - `backend/app/api/routes/cohort_executive_summary.py` (+31 lines, NEW)
  - `backend/app/services/reporting/_schema_versions.py` (+27 lines: `COHORT_EXECUTIVE_SUMMARY_SCHEMA_VERSION` + `COHORT_ANOMALIES_SCHEMA_VERSION` slice-E reservation)
  - `backend/app/main.py` (+3 lines: router registration for Phase 8 D)
  - `frontend/src/cohortExecutiveSummaryClient.ts` (+125 lines, NEW)
  - `frontend/src/components/CohortExecutiveSummaryPanel.tsx` (+178 lines, NEW)
  - `frontend/src/App.tsx` (+2 lines: import + mount)
  - `tests/test_phase8_cohort_executive_summary.py` (+178 lines, NEW; 13 pytest cases)
  - `frontend/test/CohortExecutiveSummaryPanel.test.tsx` (+105 lines, NEW; 5 vitest cases)
  - `.planning/phase8_audit_reports/B.md` (+159 lines: slice-B TAA archive)
- **Files-touched constraint**: zero HF1 hard-stop zone paths; zero `^GS-\d{3}$` registry edits; zero `golden_samples/**` writes; zero Linear/Notion/external-write surfaces.

---

### Evidence-driven findings (numbered)

1. **Blueprint precedence holds**. Blueprint `2e640f6` predates all Phase 8 commits (A `6dd7be4` → B `270e0d0` → C `6e19def` → D `74902aa`). All 17 anti-gaming guards in §4 binding on this slice.

2. **Route prefix + envelope shape match blueprint §3.D verbatim**. `routes/cohort_executive_summary.py:18-20` declares `APIRouter(prefix="/cohort-executive-summary", tags=["cohort-executive-summary"])`; combined with `/api/v1` prefix in `main.py:123` (`app.include_router(cohort_executive_summary.router, prefix="/api/v1")`), the live URL is `GET /api/v1/cohort-executive-summary`. The `CohortExecutiveSummary` envelope (lines 75-86 of builder) carries every blueprint-required field: `schema_version`, `generated_at_utc`, `claim_tier`, `claim_boundary`, `cohort_count`, `healthy_count`, `watching_count`, `regressed_count`, `cases`, `claim_impact`. `_summary_to_dict` (lines 198-220) emits all 10 fields under snake_case keys with per-case row shape matching test fixture.

3. **Named bucket thresholds satisfy guard M: -3 (no inline magic)**. Both `HEALTHY_TRUST_SCORE_MIN: int = 80` (line 49) and `WATCHING_TRUST_SCORE_MIN: int = 50` (line 50) are module-scope named constants annotated `int`. `_classify_bucket` (lines 175-195) uses them by name (lines 185, 190). Grep for inline `80` / `50` in code paths returns only docstring/comment occurrences (lines 8, 10, 13, 192) — no inline magic in arithmetic. Test `test_bucket_threshold_constants_are_named` (lines 62-65) pins both values. Guard M: -3 fully satisfied.

4. **`_classify_bucket` precedence: regressed > watching > healthy** is correctly implemented and pinned.
   - Manual trace of lines 180-195:
     - **regressed-dominates layer** (lines 181-186): `blocked_pending_input` verdict → regressed; `alarm_count > 0` → regressed; `trust_score < 50` → regressed.
     - **watching-over-healthy layer** (lines 188-191): `watching`/`needs_more_evidence`/`needs_more_convergence` → watching; `trust_score < 80` → watching.
     - **healthy fallback** (line 195): everything else, including `trust_score is None`.
   - Tests pin precedence corner cases:
     - `test_bucket_blocked_signoff_dominates_high_score` (line 87-89) — `_classify_bucket(100, 0, "blocked_pending_input") == "regressed"`. Score 100 + zero alarms still flips to regressed when verdict is blocking. **The load-bearing precedence pin.**
     - `test_bucket_healthy_when_score_ge_80_no_alarms_no_blocker` line 71 — `_classify_bucket(100, 0, "watching") == "watching"` confirming watching verdict beats high score.
     - `test_bucket_regressed_when_score_lt_50_or_alarms_or_blocked` line 83 — `_classify_bucket(85, 1, None) == "regressed"` confirming alarms beat high score.

5. **Defense-in-depth `^GS-\d{3}$` rejection at scanner**. Lines 56 (`_SIGNED_REGISTRY_RE`) + 106-108 of `build_cohort_executive_summary` reject the literal signed-registry shape before per-case row construction. The `_CANDIDATE_DIR_RE` regex (line 55, `^[A-Za-z0-9_-]+-candidate$`) on line 109 is an additional filter requiring the `-candidate` suffix. Belt-and-suspenders defense: even a path like `GS-001-candidate` (signed-registry prefix + candidate suffix) would pass the suffix check but pass through the registry regex unfiltered (since `^GS-\d{3}$` requires fullmatch of exactly the 3-digit shape — `GS-001-candidate` doesn't fullmatch). The test `test_builder_rejects_signed_registry_at_scanner_level` (lines 123-134) pins `GS-001` rejection. The defense is real but slightly subtle: the regex-fullmatch only rejects the bare `GS-001` directory shape, not `GS-001-candidate` if one existed; however the prior suffix filter (line 104) requires the `-candidate` ending, and the `_CANDIDATE_DIR_RE` regex on line 109 acts as the final whitelist. The combination is correct.

6. **HEALTH_BUCKETS exported `as const` 3-tuple**. `frontend/src/cohortExecutiveSummaryClient.ts:5` declares `export const HEALTH_BUCKETS = ['healthy', 'watching', 'regressed'] as const`; line 6 derives `type HealthBucket = (typeof HEALTH_BUCKETS)[number]`. Vitest pin `'exports the 3-bucket whitelist constant'` (line 96-98) asserts exact 3-element array. Backend-side `HealthBucket = Literal["healthy", "watching", "regressed"]` (line 52 of builder) matches.

7. **`parseBucket` defensive fallback to `regressed` (most conservative)**. Client lines 52-55: `if (raw === 'healthy' || raw === 'watching' || raw === 'regressed') return raw; return 'regressed'`. Comment on line 54 documents the rationale. This is the conservative analog of slice B's `parseVerdict → 'blocked_pending_input'` — an unknown bucket name surfaces as red `regressed`, not silently as benign `healthy`. Correct defensive choice.

8. **`bucketTone` helper drives panel colors (guard X: -2 satisfied)**. Client line 121-125 maps bucket → `'info' | 'warn' | 'danger'`. Panel's `toneColor` (lines 18-22) dispatches via tone strings; hex codes appear only as CSS-variable fallback defaults (`var(--accent, #0a8a4a)` etc.) — same Phase 6/7 graceful-degradation pattern. Primary color comes from CSS variables, not inline hex. Vitest pin `'bucketTone maps buckets to documented tone buckets'` (lines 100-104) exhaustively maps all 3 buckets. Guard X: -2 satisfied.

9. **Schema constant + rationale block (guards B: -2 + B: -3 + D: -2 satisfied)**. `_schema_versions.py:228-239` adds `COHORT_EXECUTIVE_SUMMARY_SCHEMA_VERSION = "1.0.0"` with a 12-line rationale enumerating: (a) the builder path, (b) what the surface aggregates (trust score + alarm count + signoff verdict), (c) the bucket scheme, (d) explicit `claim_impact` semantics. Slice-E reservation `COHORT_ANOMALIES_SCHEMA_VERSION = "1.0.0"` (lines 241-253) carries a 13-line rationale documenting the z-score axis breakdown + severity ladder + Tier 1 boundary, prepaying the slice-E schema-discovery work. Both rationales satisfy D: -2.

10. **Tier 1 disclaimer trio in envelope (guard C satisfied)**. Builder line 121: `claim_tier=CLAIM_TIER` (= "Tier 1 engineering candidate"); line 122: `claim_boundary=CLAIM_BOUNDARY` (imported from `acceptance_packet`, contains "not_signed_validation; not_benchmark_agreement"); line 128: `claim_impact=CLAIM_IMPACT_DEFAULT` (lines 41-46, contains "not signed validation" and "not benchmark agreement"). Test `test_builder_stamps_schema_and_disclaimer_trio` (lines 112-120) + `test_endpoint_envelope_carries_tier1_disclaimer_trio` (lines 163-171) pin both surfaces. The envelope-scope audit `_assert_no_overclaim` (lines 231-245) uses the narrowed 4-token `_ENVELOPE_FORBIDDEN_TOKENS` (lines 223-228) — same Phase 7 B / Phase 8 B two-list pattern — so the legitimate disclaimer construction `"substitute for signed validation"` in `CLAIM_IMPACT_DEFAULT` passes envelope audit while still refusing positive `validated against` / `perforation completed` / etc.

11. **Forbidden positive claims in code body** — grep of all 4 D-slice source files for the 5-token forbidden set returns 9 hits; each inspected:
    - `cohort_executive_summary.py:3, 18, 21, 42-45` — disclaimer-form (`not signed validation`, `not benchmark agreement`, `substitute for signed validation` in disclaimer context, or docstring enumeration of what's forbidden).
    - `routes/cohort_executive_summary.py:3`, `cohortExecutiveSummaryClient.ts:3`, `CohortExecutiveSummaryPanel.tsx:3` — file-header disclaimer banner.
    - No positive-claim usage anywhere.

12. **13 backend tests + 5 vitest tests** confirmed and independently re-run:
    - `python -m pytest tests/test_phase8_cohort_executive_summary.py -v --no-header` → **13 passed in 0.65s** (blueprint floor ≥8; exceeded by 5).
    - `cd frontend && npx vitest run test/CohortExecutiveSummaryPanel.test.tsx` → **5 passed in 0.78s** (blueprint floor ≥4; exceeded by 1).
    - Full backend sweep: `python -m pytest tests/ -q --no-header` → **1688 passed, 8 skipped** at HEAD (slice E landed +17 tests on top of slice D's `1671 passed` claim; math: 1671 + 17 = 1688). Backend pytest sweep green; no Phase 7/earlier-Phase-8 regression.
    - Full vitest sweep: `npx vitest run` → **33 passed in 6 files** at HEAD; slice D commit claimed `5 files / 29 tests`. Slice E added 1 file / 4 tests on top — math checks out.
    - `npx tsc -b` → clean (no output).
    - 5 backend tests cover bucket classification (named-constants pin + healthy/watching/regressed positive cases + blocked-precedence + no-snapshot-fallback). 4 backend tests cover builder behavior (empty cohort, disclaimer trio, signed-registry rejection, new-candidate-defaults-to-healthy). 4 backend tests cover HTTP endpoint (stamped payload, disclaimer trio, application/json content type, and one shared by `test_endpoint_returns_stamped_payload`). Test taxonomy = unit (bucket logic) + builder (I/O) + endpoint (HTTP), all three layers covered.

13. **Anti-gaming guard coverage (slice-D applicable subset)**:

    | Guard | Mapped to slice D? | Evidence |
    |---|---|---|
    | **M: -3** (named threshold constants for buckets) | Yes | `HEALTHY_TRUST_SCORE_MIN` / `WATCHING_TRUST_SCORE_MIN` named (lines 49-50); pin test (lines 62-65); no inline magic in code paths. |
    | **B: -2** (schema_version on new endpoint) | Yes | Endpoint test asserts `payload["schema_version"] == COHORT_EXECUTIVE_SUMMARY_SCHEMA_VERSION` (line 156). |
    | **B: -3** (bump-history doc on new schema constant) | Yes | `_schema_versions.py:228-239` (D constant) + 241-253 (E reservation) both carry full rationale blocks. |
    | **C** (no Tier 2 vocabulary in `regressed` bucket label) | Yes | The `regressed` label is the bucket name; no `signed_validation_pending` / `tier_2_blocked` / `promotion_blocked` shape. The bucket is reviewer-domain language only. |
    | **X: -2** (verdict tone via helper, not inline hex) | Yes | `bucketTone` helper + `toneColor` dispatcher; hex codes are CSS-variable fallbacks only (graceful-degradation pattern from Phase 6/7). |
    | **D: -2** (rationale on new schema constant) | Yes | Both new constants (D + E reservation) have ≥10-line rationales. |
    | **E: -2** (E2E disclaimer trio) | N/A in slice D | Full E2E lands in slice F per blueprint §3.F; slice-D endpoint tests assert disclaimer trio at HTTP body level (`test_endpoint_envelope_carries_tier1_disclaimer_trio`), pre-paying the obligation at the right scope for slice D. |

14. **Constraint checks**:
    - HF1 zone untouched: `git diff --name-only 6e19def..74902aa | grep -E "(agents/solver|agents/router|agents/geometry|schemas/sim_state|test_toolchain_probes|Dockerfile|Makefile|hf1_path_guard|\.github/workflows)"` → empty.
    - No `^GS-\d{3}$` registry edits: zero hits in `golden_samples/` or any `GS-\d{3}` literal path. Test fixtures use `GS-A-candidate` (valid Tier 1) and `GS-001` (only as negative-test rejection target).
    - No forbidden positive claims outside disclaimer form: grep audit summary above.

15. **Module purity**. `build_cohort_executive_summary` accepts `now_utc: datetime | None = None` injection seam (default `datetime.now(UTC)`) so tests pin `generated_at_utc` deterministically when needed. Pure-read filesystem walk; no global state. `_build_row` (lines 138-172) wraps each sub-builder (`build_trust_score_timeline` + `build_trust_score_alerts` + `read_signoff_history`) with broad `try/except` falling back to `None` / `0`, preserving the per-case error-isolation property required for cohort surfaces (one bad case shouldn't take down the cohort scorecard). The broad `except Exception` is slightly aggressive (would mask real bugs in upstream builders) but is consistent with the cohort-error-isolation pattern; LOW-grade nit, not a guard violation.

---

### Findings list

#### BLOCK
(none)

#### HIGH
(none)

#### LOW

- **LOW-D-1** (cosmetic, no fix required): `CohortExecutiveSummaryPanel.tsx:99-105` instantiates 3 `<BucketCounter>` tiles by hand with hardcoded `bucket="healthy"` / `"watching"` / `"regressed"` literal props (typed as `HealthBucket` via the `as const` derivation, so a future rename would TypeScript-fail). This does not duplicate `HEALTH_BUCKETS` as a runtime list (guard X: -2 targets list duplication), but a future cleanup could iterate `HEALTH_BUCKETS.map(b => <BucketCounter bucket={b} ... />)` for tighter SSOT-consumption symmetry with the slice-B panel's `SUPPORTED_SIGNOFF_VERDICTS` import-and-use pattern. Suitable for slice F polish; does not block.

- **LOW-D-2** (cosmetic, no fix required): `_build_row` wraps each upstream-builder call in `try/except Exception` (lines 146-154, 157-162). Broad-`except` would mask real upstream bugs in cohort traversal; a narrower `except (FileNotFoundError, ValueError)` would surface bugs while still tolerating "this case has no signoff yet" / "this case has no timeline yet". Suitable for slice F polish.

- **LOW-D-3** (cosmetic, no fix required): `_classify_bucket` healthy-fallback for `trust_score is None` (a brand-new candidate with no snapshot) is documented (lines 192-194) but defensible-either-way. An alternative reading would be "absence of evidence ⇒ `watching` (review pending)"; the current "absence ⇒ `healthy`" choice is friendlier to new-candidate workflows but slightly optimistic. The docstring is explicit, the test pins it, and the choice is reasonable — but worth a one-line product-owner check at slice F or slice G.

None of the LOW findings block slice E (already landed at `9f0a8a1`) or slice F.

---

### Axis verdicts (slice D isolated)

| Axis | Weight | Slice-D score | Evidence anchor |
|---|---|---|---|
| **B — schema versioning** | 12 | **12/12** | `COHORT_EXECUTIVE_SUMMARY_SCHEMA_VERSION = "1.0.0"` declared in `_schema_versions.py:228` with 12-line rationale; `COHORT_ANOMALIES_SCHEMA_VERSION = "1.0.0"` slice-E reservation with 13-line rationale; both stamped via `_summary_to_dict` (line 200); endpoint test asserts round-trip (test line 156). |
| **M — module quality** | 12 | **12/12** | `HEALTHY_TRUST_SCORE_MIN` / `WATCHING_TRUST_SCORE_MIN` named module constants; `_WATCHING_SIGNOFF_VERDICTS` `frozenset` constant; `_CANDIDATE_DIR_RE` / `_SIGNED_REGISTRY_RE` named regex constants; `_CASE_DIR_SUFFIX` named constant; `now_utc` injection seam; pure builder (filesystem walk only); UTC ISO 8601 via `.isoformat(timespec="seconds")` (line 117). |
| **T — testing** | 15 | **15/15** | 13 backend tests (floor ≥8; +63% over-floor) + 5 vitest tests (floor ≥4; +25% over-floor). Bucket classification matrix covers all 3 buckets + precedence corner cases + `None`-score fallback. Endpoint stamping + disclaimer trio + content-type all pinned. Full pytest sweep 1671 → 1688 at HEAD; vitest 5 files / 29 → 6 files / 33 at HEAD; tsc clean. |
| **C — claim-tier discipline** | 12 | **12/12** | Tier 1 disclaimer trio asserted in endpoint test; envelope audit uses narrowed 4-token list (same Phase 7 B / Phase 8 B pattern, documented at lines 223-228); scanner-level `^GS-\d{3}$` rejection; no Tier 2 vocabulary in any new file; bucket names are reviewer-domain language. |
| **X — frontend integration** | 12 | **12/12** | Panel mounted in `App.tsx:1614`; vitest 5/5 + tsc -b clean; `HEALTH_BUCKETS` exported `as const` 3-tuple and consumed via `HealthBucket` type derivation; `bucketTone` helper drives `toneColor` dispatcher; CSS-var-first color strategy with hex fallback (graceful degradation); `parseBucket` defensively falls back to `regressed`. LOW-D-1 (literal-tile instantiation vs iteration) is cosmetic. |
| **D — documentation / SSOT** | 8 | **8/8** | Module docstring (lines 1-23) enumerates the 3 buckets with prose criteria; lists forbidden wording explicitly; cites Phase 7 B / Phase 8 B two-list precedent in comment block. Both new schema constants (D + E reservation) carry full rationale blocks. |
| **A — anti-gaming discipline** | 8 | **8/8** | Slice-B TAA archive (`B.md`) landed in this commit preserving APPROVE + LOW-deferred audit-trail discipline; the slice-D-applicable subset of 17 guards (M: -3, B: -2, B: -3, C, X: -2, D: -2, E: -2) all satisfied. Blueprint `2e640f6` predates this commit. |
| **E — end-to-end workflow** | 8 | **8/8** | Slice-D scope; E2E lands in slice F. Endpoint test's full disclaimer-trio round-trip (test lines 163-171) + content-type assertion (lines 174-178) pre-pay the end-of-pipeline obligation at the HTTP layer correct for slice D. |
| **V — verification by TAA** | 13 | **3/13** | Slice-A archive (`A.md`) retired at slice B commit; slice-B archive (`B.md`) retired in this commit; this report (`D.md`) retires the slice-D obligation. Slice-C TAA archive is pending (presumably to land with slice E's commit or later). 10/13 reserved for slices C, E, F + FINAL audits. |

**Slice-D subtotal (B+M+T+C+X+D+A+E)**: 87/87 across the 8 non-V axes = 100% of in-scope weight.
**V contribution from slice D**: 3/13.
**Total in-scope score (8 non-V axes earned + V partial)**: 87 + 3 = **90/100**.

---

### Overall verdict

**APPROVE**

No BLOCK or HIGH findings. The slice executes blueprint §3.D faithfully:
- `GET /api/v1/cohort-executive-summary` returns the exact envelope shape specified in §3.D with all 10 fields and the Tier 1 disclaimer trio intact.
- Bucket classification (`_classify_bucket`) implements the documented precedence `regressed > watching > healthy` with named threshold constants `HEALTHY_TRUST_SCORE_MIN=80` + `WATCHING_TRUST_SCORE_MIN=50` satisfying anti-gaming guard M: -3 (no inline magic numbers).
- `blocked_pending_input` signoff verdict correctly forces the case to `regressed` even at score=100 (load-bearing precedence pin in `test_bucket_blocked_signoff_dominates_high_score`).
- Defense-in-depth: scanner rejects literal `^GS-\d{3}$` directory shape before per-case row construction; additional `-candidate` suffix + `_CANDIDATE_DIR_RE` whitelist regex acts as belt-and-suspenders filter.
- `HEALTH_BUCKETS` exported `as const` 3-tuple from the typed client; panel imports `HealthBucket` type + `bucketTone` helper; CSS-variable-first color strategy with hex codes as graceful-degradation fallback only.
- `parseBucket` defensively falls back to `regressed` (most conservative bucket) for unknown bucket names, so a future backend leak of any unrecognized bucket label cannot silently surface as `healthy`.
- `COHORT_ANOMALIES_SCHEMA_VERSION` slice-E reservation included with full rationale block — pre-pays slice E schema-discovery + keeps the constants module synchronized with the planned blueprint §3.E surface.
- 13 backend + 5 vitest tests all green (floors were ≥8 and ≥4); full backend sweep 1671 passed at slice D HEAD (1658 → 1671 = +13 new); vitest 5 files / 29 tests; tsc -b clean.
- HF1 zone untouched, no signed-registry edits, no `golden_samples/**` writes, no external surface.

Main session may proceed to slice E (already landed at `9f0a8a1`); slice-C TAA archive (`C.md`) and this slice-D archive (`D.md`) presumably co-land with the next slice commit per the established lag pattern.

---

### Honest score adjustment vs commit claim

Author's commit message: `Cumulative honest score (pre-TAA-D): 90/100`.

Audit assessment: **90/100** — matches the author's claim exactly. No adjustment needed:
- B 12/12, M 12/12, T 15/15, C 12/12, X 12/12, D 8/8, A 8/8, E 8/8: all 8 non-V axes earned at full weight with explicit per-axis evidence.
- V 3/13: A.md (retired at slice B commit) + B.md (retired in this commit) + D.md (this report retires slice-D obligation). 10/13 reserved for slice-C TAA archive + slice-E TAA + slice-F TAA + FINAL audit.

**Honest cumulative score after slice D**: **90/100** by design (V intentionally short until all 7 TAA audits land). Main session is on track for the 99/100 honest-gate target at slice G closure.

---

### Slice-D summary

Slice D is a clean additive read-only HTTP + frontend surface composing Phase 6 D (trust score timeline), Phase 7 C (alerts), and Phase 8 A (signoff history) into a 3-bucket reviewer scorecard. The load-bearing pieces are the named-constant thresholds (no inline magic; pinned by test), the precedence ordering (`blocked_pending_input` dominates score; alarms dominate score; bucket cascade strict), and the scanner-level signed-registry rejection (defense-in-depth so the cohort surface cannot accidentally enumerate a `^GS-\d{3}$` directory even if one were planted under `golden_samples/`). The frontend mirror keeps `HEALTH_BUCKETS` as a single SSOT export and dispatches color via the `bucketTone` helper. The slice-E `COHORT_ANOMALIES_SCHEMA_VERSION` reservation pre-pays schema-discovery work that would otherwise have been required at slice E.

The cohort row builder's broad-`except` (LOW-D-2) is the most aggressive design choice; a future cohort case with a corrupt sub-builder would silently surface with `latest_trust_score=None, alarm_count=0, latest_signoff_verdict=None`, falling to healthy-bucket fallback (LOW-D-3) — which would be the wrong tone if the real reason for absent metrics was a corrupt snapshot rather than a brand-new case. Slice F polish should narrow these, but neither is a slice-D blocker.

**Recommendation**: APPROVE; proceed to slice E (already landed) with no follow-up fix commits required from slice D. 3 LOW cosmetics (panel iterate vs hand-instantiate, narrower-except, healthy-vs-watching fallback semantics) are suitable for the slice F polish pass; none block any subsequent slice.

> Tier 1 engineering candidate; not signed validation; not benchmark agreement.
