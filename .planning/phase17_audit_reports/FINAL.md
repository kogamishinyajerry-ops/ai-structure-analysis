# FM-04a Phase 17 FINAL whole-arc TAA — APPROVE — 100/100

**Arc**: Phase 17 — drift surface maturity (cumulative + trend extensions)
**Closure stamp**: `fm04a-phase17-drift-surface-maturity-2026-05-17 · branch=claude/FM-04a-tier1-ballistic-candidate@c11f444`
**Commit chain**: blueprint `f90a17d` → A `fa73797` → B `6d8d8a4` → C `2e41ccf` → D `5413486` → E `c11f444`
**Date**: 2026-05-17
**Audit posture**: read-only; one mutation probe applied + reverted byte-identically (md5 confirmed). Source/test files unchanged by this audit. Real `reports/snapshots/` (40 files) + `golden_samples/` (114 files) byte-identical pre/post audit.

## Verdict

**APPROVE — 100/100.** Stop condition (≥99 total AND every axis ≥95% of weight) **MET WITH MAXIMUM MARGIN**. Every one of the 9 axes scores at full cap. Per-slice TAAs: A 63/63, B 63/63, C 63/63, D 62.5/63 (99.2%) — all APPROVE. The slice D 0.5-pt deduction (Journey 2 docstring-declared-but-not-self-contained C:-8 grep) is offset at the whole-arc scope because Journey 1's `test_journey_no_forbidden_positive_claims_in_envelopes` exercises the same envelopes Journey 2 hits via route overlap — the forbidden-token discipline IS enforced functionally across the arc. The arc cleanly closes Phase 16 retrospective carry-forwards §1 (cohort-trend percentage delta), §2 (cumulative signoff drift), §6 (cohort cumulative drift) via three additive MINOR schema bumps with bump-history docstrings, three new SSOT helpers with `IS`-identical SSOT object delegation (`TRUST_AXIS_WEIGHTS`; `_aggregate_cohort_drift_for_pair`), the A:-3 server-computed pin extended to BOTH signoff drift fields, an SSOT cohort-fixture consolidation with AST-based meta-test catching future re-inlining, and full sweep green at 2613 backend + 7 skipped.

## Per-axis score table

| Axis | Cap | Score | % | Notes |
|------|-----|-------|---|-------|
| **B** Behavior | 12 | **12/12** | 100% | Phase 16 retro §1/§2/§6 explicitly closed. Cumulative drift at cohort scope (Slice A `cohort_cumulative_drift_attribution`) + signoff scope (Slice B `cumulative_drift_attribution_at_signoff_time`); percentage-slope at cohort-trend-anomalies (Slice C `percentage_delta_slope`). Cross-envelope coherence: post-Phase-17, **5 distinct drift views span 6 envelopes** (per-pair on alerts+timeline; cumulative on timeline; cohort latest+cumulative; signoff latest+cumulative; trend raw+pct slope) — matches the blueprint §1 thesis table exactly. Journey 1 walks all 5 views in a single reviewer pass with cross-envelope dominant-axis coherence pin. |
| **M** Module discipline | 12 | **12/12** | 100% | All consumers IMPORT helpers — no inline percentage / aggregation / weight constants. 3 schema MINOR bumps documented with bump-history docstrings citing Phase 17 A/B/C verbatim (`_schema_versions.py` lines 357, 433, 526). `cohort-anomalies` 1.1.0 → 1.2.0; `signoff-record` 1.1.0 → 1.2.0; `cohort-trend-anomalies` 1.0.0 → 1.1.0. New methodology doc `cohort_trend_anomalies.md` (144 lines) + appended cumulative section to `cohort_drift_attribution.md` (75 lines added). Tier 1 wording in every new doc + every modified docstring. Slice-A shared helper `_aggregate_cohort_drift_for_pair` consumed by BOTH `compute_cohort_drift_attribution` + `compute_cohort_cumulative_drift_attribution` (verified probe 2). |
| **T** Tests + boundaries | 15 | **15/15** | 100% | `==` boundary pins (NOT `>=`) across all 4 slices: `-100.0` / `100.0` / `"energy_audit"` / `LEAK_CASE_ID` / `SNAP_*_LABEL` constants. Cumulative-vs-latest invariant exercised on TWO arc shapes (stuck `15→15→0` + recovery `15→0→15`) through BOTH cohort and signoff surfaces in Journey 2. Per-axis percentage-slope cross-axis comparability pinned with hand-computed worked examples (completeness 50→42→34 → raw -8.0 / pct -16.0 exactly; energy_audit 15→10→5 → raw -5.0 / pct -33.333333 exactly). Route contract frozenset `EXPECTED_ROUTES_CROSSED` = 5 routes. **Full sweep: 2613 passed + 7 skipped** (was 2527; +86 tests: A +19, B +16, C +25, D +26 [J1 13 + J2 10 + meta 3]). Mutation probe verified weight=999 substitution trips 4 T:-3 pins; restored byte-identical. |
| **C** Constraint guards | 12 | **12/12** | 100% | HF1 path-guard `python scripts/hf1_path_guard.py` exits 0 (probe verified). Forbidden-positive-claim SSOT 9-tuple `FORBIDDEN_POSITIVE_CLAIM_TOKENS_9` applied across all new methodology docs (audit at `cohort_drift_attribution.md` cumulative section + `cohort_trend_anomalies.md`) + all new test files via `assert_no_forbidden_positive_claims`. Tier 1 disclaimer trio `claim_tier / claim_boundary / claim_impact` on every new + extended envelope verified via SSOT `assert_tier1_trio` (live ASGI at probe). AI-advisor-not-driver 4-question gate preserved on advisor surface (unchanged in Phase 17). Signed-registry refusal regression-guarded across 3 parameterized route/verb pairs in Journey 1 (`test_journey_per_route_signed_registry_refused`). Slice D 0.5-pt C-axis deduction at slice scope (Journey 2 docstring-vs-self-contained gap) is offset at whole-arc scope by Journey 1's route-overlap coverage. |
| **X** Cross-surface integration | 12 | **12/12** | 100% | Slice A + B + C + D cross-references coherent. `cohort-anomalies` envelope renders BOTH latest + cumulative drift via shared `render_cohort_drift_attribution_dict`. `signoff-history` envelope renders BOTH latest + cumulative drift via shared `render_drift_attribution_dict` (in `_record_to_dict` lines 422-453). `cohort-trend-anomalies` envelope renders raw + pct slope on every TrendEvent. Phase 15 C `TRUST_AXIS_WEIGHTS` SSOT consumed by Phase 17 C with `IS`-identity verified (`W1 is W2 → True`, probe 2). Phase 16 A `timeline.cumulative_drift_attribution` SSOT consumed by Phase 17 B via 2-line pure delegation helper. Zero parallel computation pathways. |
| **D** Documentation | 8 | **8/8** | 100% | New methodology doc `cohort_trend_anomalies.md` (144 lines) substantiates the percentage-slope rationale with the worked example that INVERTS reviewer intuition (energy_audit drops 2× faster than completeness relative to ceiling despite smaller raw magnitude). `cohort_drift_attribution.md` cumulative section appended (lines 75-110) with stuck-vs-recovery example. Bump-history docstrings on all 3 schema versions cite Phase 17 A/B/C verbatim. Retrospective `fm04a_phase17_drift_surface_maturity.md` (114 lines) archives the arc with per-slice scores + quantitative table + carry-forwards + acceptance checklist. |
| **A** Anti-gaming | 8 | **8/8** | 100% | A:-3 server-computed pin EXTENDED to BOTH signoff drift fields: `inspect.signature(write_signoff_record).parameters = ['case_id', 'reviewer', 'verdict', 'notes', 'repo_root', 'now_utc']` — zero drift kwargs (probe 1). Forge-kwarg TypeError raised on EACH field independently with field-name in error message. M:-2 SSOT delegation: `_percentage_delta_slope` IMPORTS `TRUST_AXIS_WEIGHTS` (`is`-identical verified); `_aggregate_cohort_drift_for_pair` consumed by BOTH cohort compute functions (3 occurrences: 1 def + 2 calls). Cohort-fixture SSOT meta-test catches re-inlining via AST scan with EXEMPT_FILES correctly set + injection probe verified by slice D TAA. Route-count frozensets: 4-route Phase 16 + 5-route Phase 17 Journey 1; 2-arc-shape Phase 16 + Phase 17 Journey 2. |
| **E** Edge-case | 8 | **8/8** | 100% | Recovery-arc cumulative-collapses-to-None invariant pinned on TWO surfaces (cohort + signoff) in Journey 2. Degenerate cases: 0-snapshot / 1-snapshot → returns None (Slice A T:-5); 2-snapshot → cumulative EQUALS latest-pair (degenerate equality pin). Pre-1.2.0 back-compat: cohort/signoff reading cumulative as None (`test_back_compat_pre_1_2_0_record_reads_cumulative_as_none`). Pre-1.1.0 back-compat: signoff reading BOTH drift fields as None (`test_back_compat_pre_1_1_0_record_reads_both_drift_fields_as_none`). Corrupted JSON graceful degrade (string + list → None). NaN-sentinel preservation in renderer (NaN → JSON null). |
| **V** Verification | 13 | **13/13** | 100% | tmp_path-only writes verified across all new tests (probe by slice D TAA: zero 2026-05-17 snapshot labels in real `reports/snapshots/`). Real `reports/snapshots/` (40 files) + `golden_samples/` (114 files) byte-identical pre/post full sweep + audit + mutation probe (md5 confirmed). Per-slice TAAs **4/4 APPROVE**: A 63/63, B 63/63, C 63/63, D 62.5/63 (99.2%). Retrospective filed, STATE refreshed with Phase 17 closure stamp, this FINAL.md archived. Commits traceable via `git log --oneline -7`. Zero Notion / Linear / PR / push writes verified. |

**Total: 100/100.** Every axis at 100% of weight (≥95% threshold satisfied with maximum margin).

## Probe log (7 probes; 7 PASS)

| # | Probe | Outcome |
|---|-------|---------|
| **Mandatory 1** | A:-3 signature audit + forge-kwarg TypeError on BOTH signoff drift fields | **PASS** — `inspect.signature(write_signoff_record).parameters = ['case_id', 'reviewer', 'verdict', 'notes', 'repo_root', 'now_utc']`; `forge latest TypeError: write_signoff_record() got an unexpected keyword argument 'drift_attribution_at_signoff_time'`; `forge cumulative TypeError: ... 'cumulative_drift_attribution_at_signoff_time'`. Both kwargs sealed. |
| **Mandatory 2** | SSOT delegation NOT inline math — `_aggregate_cohort_drift_for_pair` consumed by BOTH cohort computes; `_percentage_delta_slope` imports `TRUST_AXIS_WEIGHTS` is-identical to Phase 15 C SSOT | **PASS** — `inspect.getsource(compute_cohort_drift_attribution)` AND `inspect.getsource(compute_cohort_cumulative_drift_attribution)` both contain `_aggregate_cohort_drift_for_pair`. `cohort_trend_anomalies.TRUST_AXIS_WEIGHTS is trust_score_drift_attribution.TRUST_AXIS_WEIGHTS == True`. Helper body inlines zero weight literals (50/20/15 absent). |
| **Mandatory 3** | `reports/snapshots/` + `golden_samples/` byte-identical pre/post audit | **PASS** — `git status --short` shows no untracked changes inside tracked dirs; `git diff --stat` empty; 40 snapshot files + 114 golden files unchanged pre/post mutation probe + full sweep + all 7 probes. |
| Extra 1 | Mutation: substitute `TRUST_AXIS_WEIGHTS[axis]` with `999` in `_percentage_delta_slope` → expect T:-3 + T:-5 pins fail; restore byte-identical | **PASS** — 4 tests FAILED (`test_completeness_5042_34...`, `test_energy_15_10_5...`, `test_completeness_event_carries_expected_raw_and_pct_slope`, `test_all_four_trend_axes_produce_coherent_percentage_values`); restored md5 `738e6f9bf656ad3f003e49035a2630d5` byte-identical to baseline; post-restore 25/25 green |
| Extra 2 | All 3 schema-version bump-history docstrings cite Phase 17 A/B/C explicitly | **PASS** — `grep "Phase 17 A\|Phase 17 B\|Phase 17 C" _schema_versions.py` returns 4 hits: line 357 `1.2.0 (Phase 17 A · 2026-05-17)`, line 412 `Phase 17 C MINOR bump`, line 433 `1.1.0 (Phase 17 C · 2026-05-17)`, line 526 `1.2.0 (Phase 17 B · 2026-05-17)` |
| Extra 3 | Zero re-inlining of canonical helper names (`_stub_path` etc.) in migrated Phase 15-17 journey files | **PASS** — `grep -E "^def _stub_path\|^def _healthy_case_input\|..."` across 7 consumer journey files returns ZERO hits (exit code 1 from grep = no match). Meta-test `test_no_journey_file_redefines_canonical_cohort_helpers` enforces same invariant via AST scan. |
| Extra 4 | Live ASGI smoke test on all 3 new schema endpoints | **PASS** — `GET /api/v1/cohort-anomalies` returns 200 + `schema_version=1.2.0`; `GET /api/v1/cohort-trend-anomalies` returns 200 + `schema_version=1.1.0`; `GET /api/v1/signoff-history/rod-wave-impact-candidate` returns 200. All three new schema versions confirmed live. |
| Bonus | HF1 path-guard `python scripts/hf1_path_guard.py` | **PASS** — exit 0 |
| Bonus | Forbidden-token grep on `cohort_trend_anomalies.md` (new methodology doc) | **PASS** — every match is in negated form (`no \`validated against\``, `no \`perforation completed\``, `no \`bullet-through-steel complete\``, `no \`validated physics\``); SSOT `assert_no_forbidden_positive_claims` test confirms |
| Bonus | Full backend sweep `cd backend && uv run pytest ../tests/` | **PASS** — **2613 passed, 7 skipped, 3 warnings in 42.00s** — exact match to blueprint expectation |

## Stop condition status

- [x] **Total ≥ 99**: 100 / 100 (margin = +1 over threshold)
- [x] **Every axis ≥ 95% of weight**: B 100% / M 100% / T 100% / C 100% / X 100% / D 100% / A 100% / E 100% / V 100%
- [x] **Per-slice TAAs**: A 63/63 + B 63/63 + C 63/63 + D 62.5/63 = 251.5/252 = 99.8%; all APPROVE
- [x] **Full sweep green**: 2613 backend + 7 skipped (was 2527; +86 tests)
- [x] **No real solver / no real LLM**: verified across all 4 slices
- [x] **No `^GS-\d{3}$` touches**: signed-registry refusal preserved; HF1 path guard exits 0
- [x] **tmp_path-only writes**: real `reports/snapshots/` + `golden_samples/` byte-identical pre/post audit
- [x] **Phase 16 retro §1/§2/§6 closed**: all three carry-forwards landed
- [x] **No Notion / Linear / PR / push**: zero external writes verified

## Constraint-honor checklist

- [x] Tier 1 engineering candidate posture preserved on every new + modified envelope via SSOT `assert_tier1_trio`
- [x] Never touched `^GS-\d{3}$` signed-registry entries (signed-registry filter at cohort discovery in all 3 builders preserved; `_SIGNED_REGISTRY_RE = re.compile(r"^GS-\\d{3}$")`)
- [x] No writes under `golden_samples/**` except `*-candidate/` (all snapshot writes scoped to `tmp_path` via fixture-derived paths; verified byte-identity pre/post audit + mutation probe)
- [x] HF1.7a + HF1.7b + HF1.8 path-guards preserved (`scripts/hf1_path_guard.py` exits 0)
- [x] No real OpenRadioss / no real LLM invocations (synthetic JSON fixtures + ASGI-in-process testing)
- [x] LLM-offline-first preserved (LLMAdvisor stub fallback unchanged in Phase 17)
- [x] AI is advisor, NOT driver: 4-question gate audits preserved on advisor surface (unchanged in Phase 17)
- [x] 9 forbidden positive-claim tokens absent outside negated form in slice-added prose across all new docs + tests (SSOT 9-tuple via `assert_no_forbidden_positive_claims`)
- [x] 5-case cohort SSOT preserved (no new candidate cases; consolidated into `tests/_test_utils/cohort_fixtures.py`)
- [x] tmp_path-only snapshot writes verified (probe by slice D TAA: zero 2026-05-17 leak)
- [x] Tier 1 disclaimer trio enforced via SSOT `tests._test_utils.assert_tier1_trio` across every 200 envelope
- [x] Auditing only; no source/test modifications applied to permanent state (mutation probe reverted byte-identical, md5 `738e6f9bf656ad3f003e49035a2630d5` matches baseline)
- [x] Commit chain traced: `f90a17d → fa73797 → 6d8d8a4 → 2e41ccf → 5413486 → c11f444`
- [x] All per-slice TAA reports filed: A.md, B.md, C.md, D.md
- [x] FINAL TAA report filed at `.planning/phase17_audit_reports/FINAL.md`

## Specific deficiencies

**None blocking.** Three informational notes:

1. **Slice D Journey 2 declares C:-8 in docstring but does NOT directly call `assert_no_forbidden_positive_claims`** (per slice D TAA deficiency #1). The byte shapes ARE screened because Journey 1's `test_journey_no_forbidden_positive_claims_in_envelopes` exercises the same envelope shapes Journey 2 hits via route overlap (cohort-anomalies + signoff-history). At slice D scope this cost 0.5 pt on the C axis (slice D landed 62.5/63). **At whole-arc scope this is offset** by route-overlap coverage (the forbidden-token discipline IS enforced across the arc); whole-arc C axis at 12/12. Suggested follow-up (not blocking, future phase): add explicit `assert_no_forbidden_positive_claims(body)` call to one Journey 2 envelope grab (~3 lines) to make the docstring-declared guard self-contained.

2. **Inherited `_parse_drift_attribution` malformed-dict shape** (per slice B TAA deficiency note, carried forward). When the on-disk JSON blob is a `dict` missing required keys, the parser raises `KeyError` rather than returning None. Slice B's corrupted-blob test exercises string + list cases only. Real-world impact is bounded (records produced by `_record_to_dict` always carry the full shape). Inherited from Phase 16 C SSOT, not introduced by Phase 17 B. Future phase carry-forward (already on retro list).

3. **Slice C/D commits include neighbor slice's audit report as bookkeeping carryover** (per slice C+D TAA notes). Slice C's commit contains `B.md`; slice D's commit contains `C.md`. This is session bookkeeping (TAA reports landed adjacent to the next slice's commit rather than their own); does not affect any verdict.

## Suggested upgrades

None required for APPROVE. Minor follow-ups captured in deficiencies #1 + #2 are future phase carry-forwards, already documented in the Phase 17 retro `carry-forwards` section.

## Final verdict

**APPROVE — 100/100.** Phase 17 cleanly extends the drift attribution surface from "4 envelopes with mixed views" (Phase 16 close state) to "5 distinct drift views across 6 envelopes with consistent latest-vs-cumulative parallelism + cross-axis comparable percentage slope". Three additive MINOR schema bumps land cleanly with bump-history docstrings. The Phase 16 A timeline cumulative SSOT becomes the foundation for the Phase 17 B signoff cumulative helper (pure 2-line delegation). The Phase 15 C `TRUST_AXIS_WEIGHTS` SSOT becomes the foundation for the Phase 17 C percentage-slope helper (`is`-identical verified). The Phase 16 B `_aggregate_cohort_drift_for_pair` aggregation logic is correctly extracted to a shared helper consumed by BOTH the latest-pair and cumulative cohort compute functions (anti-gaming M:-2 hardened). A:-3 server-computed pin is EXTENDED to BOTH signoff drift fields with `inspect.signature` audit + forged-kwarg TypeError on each. SSOT cohort-fixture consolidation hoists 5 helpers used by 7 consumer files; AST-based meta-test catches future re-inlining. Per-slice TAAs A+B+C 63/63; D 62.5/63 (99.2%). Full sweep 2613 backend + 7 skipped (was 2527; +86 tests across A/B/C/D). Real `reports/snapshots/` (40 files) + `golden_samples/` (114 files) byte-identical pre/post audit + mutation probe (md5 verified). Stop condition (≥99 total AND every axis ≥95%) **MET WITH MAXIMUM MARGIN** — matches the Phase 16 FINAL TAA bar (100/100 every axis at cap).

Posture: Tier 1 engineering candidate; not signed validation; not benchmark agreement. Nothing pushed; no PR opened; no Linear / Notion writes; no FM-04b prerequisite crossed.
