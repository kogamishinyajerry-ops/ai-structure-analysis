# Phase 17 A slice TAA — APPROVE — 63/63

**Slice**: A — cohort-scoped cumulative drift attribution on cohort-anomalies (1.1.0 → 1.2.0)
**Commit**: `fa73797` on `claude/FM-04a-tier1-ballistic-candidate`
**Date**: 2026-05-17
**Audit posture**: read-only; source/test files unchanged by this audit. Pre-existing slice B WIP in the working tree was stashed for the audit then restored.

## Verdict

**APPROVE.** Slice A meets the Phase 17 per-slice 6-axis sub-rubric stop condition (≥60/63 with every axis ≥95% of weight). The implementation is a clean additive 1.1.0 → 1.2.0 bump with a properly extracted shared `_aggregate_cohort_drift_for_pair` SSOT helper (M:-2 anti-gaming), boundary-pinned dual-arc tests, NaN-sentinel rendering, defensive parsing, and Tier-1 wording discipline preserved across all touched surfaces.

## Per-axis score table

| Axis | Score | Evidence |
|------|-------|----------|
| **M (SSOT discipline)** | **12/12** | `_schema_versions.py:330-369` documents 1.1.0 → 1.2.0 with `(version → version)`-style bump-history entry citing Phase 17 A + the additive `cohort_cumulative_drift_attribution` field. `cohort_anomalies.py:211-214` IMPORTS both `compute_cohort_drift_attribution` + `compute_cohort_cumulative_drift_attribution`; no inline aggregation math at the builder. `cohort_drift_attribution.py:184` defines `_aggregate_cohort_drift_for_pair`; lines 299 + 350 are the two call sites (3 occurrences total). Module docstring (lines 1-50) updated for Phase 17 A and explicitly names BOTH compute functions. |
| **T (Boundary pinning)** | **15/15** | Stuck arc test pins exact `==` on `cohort_max_abs_delta_pct == 100.0`, `cohort_dominant_axis == "energy_audit"`, `dominant_case_id == LEAK_CASE_ID`, `from_snapshot == SNAP_1_LABEL`, `to_snapshot == SNAP_3_LABEL` (lines 393-407). Recovery arc test pins cumulative `cohort_dominant_axis is None` + NaN sentinel + latest-pair view still firing on energy_audit at -100% (lines 436-472) → cumulative-vs-latest divergence pinned on TWO arc shapes. 2-snapshot degenerate-equal pin (lines 480-495) asserts identical endpoint labels + aggregate result. Phase 17 A delivers 19 new tests across the slice's test file (verified by collection). All green. |
| **C (Tier-1 discipline)** | **12/12** | Tier-1 disclaimer trio present in all 4 slice-touched files; live ASGI integration test (`test_live_asgi_cohort_anomalies_carries_cumulative_field`) asserts trio on the rendered envelope at schema 1.2.0. SSOT 9-tuple `FORBIDDEN_POSITIVE_CLAIM_TOKENS_9` consumed via `tests/_test_utils/__init__.py` SSOT helper (probe 7). New methodology paragraph (37 lines appended to `.planning/methodology/cohort_drift_attribution.md`) passes slice-test forbidden grep + probe 9b confirms slice-added prose across all 4 files is clean. `render_cohort_drift_attribution_dict` handles `None` gracefully (returns `None`) and renders NaN as JSON null (probe 5). |
| **A (Anti-gaming)** | **8/8** | M:-2 anti-gaming guard exercised by 2 dedicated tests: (1) `test_cohort_anomalies_imports_cumulative_helper` verifies the consumer's import line via source-file read; (2) `test_aggregate_helper_is_shared_by_both_compute_functions` requires `_aggregate_cohort_drift_for_pair(` count ≥3 in the source (probe 3 confirms exactly 3: 1 def + 2 calls). Strictly-exceed floor semantic preserved in shared helper at `cohort_drift_attribution.py:253` (`if cohort_max_abs <= dominant_floor_pct`) AND in test surface (recovery-arc cumulative-None test enforces it) AND in methodology doc ("strictly-exceed semantic preserved"). Probe 4 independently confirms a 5.0%-exact convergence delta lands `dominant_axis = None`. |
| **E (No real solver / LLM)** | **8/8** | No real OpenRadioss / LLM invocations. Module-scope fixtures use `tmp_path_factory.mktemp(...)` (lines 290, 326, 363); all snapshot writes go to `tmp` (V:-3). `_stub()` helper writes tiny ASCII stubs only. Live ASGI tests monkeypatch the `_repo_root` route helper to a tmp (lines 574, 599) so the real `reports/snapshots/` is never touched. HF1.7a + HF1.7b + HF1.8 path-guards preserved: `_SIGNED_REGISTRY_RE = re.compile(r"^GS-\\d{3}$")` filter present in both `cohort_drift_attribution.py:86` (line 176 enforces) and `cohort_anomalies.py:86` (line 160 enforces). Probe 8 confirms `reports/snapshots/` + `golden_samples/` byte-identical pre/post probe runs (40/114 file counts unchanged). |
| **V (Verification artifacts)** | **8/8** | Slice TAA report filed at `.planning/phase17_audit_reports/A.md`. Commit SHA `fa73797` traced. Constraints checklist honored (see below). 8 adversarial probes executed; results documented. |

**Total: 63/63.** Every axis at 100% of weight (≥95% threshold satisfied).

## Probe results

| # | Probe | Outcome |
|---|-------|---------|
| 1 | Boundary-pin survival under mutation (halve `dominant_delta_pct` via conftest_mutation patch on `cohort_drift_attribution.compute_drift_attribution` ref) | **PASS** — patched run trips `test_cumulative_stuck_arc_dominant_axis_is_energy_audit` (returncode 1); confirms `cohort_max_abs_delta_pct == 100.0` pin is load-bearing, not coincidental |
| 2 | Earliest-latest discovery correctness (5 fake snapshot dirs in tmp) | **PASS** — `_discover_earliest_latest_snapshot_pair` returns `(labels[0], labels[-1])`; `_discover_latest_snapshot_pair` returns `(labels[-2], labels[-1])`; the two functions diverge for ≥3 snapshots as designed |
| 3 | Shared aggregation helper invocation count | **PASS** — grep yields exactly 3 occurrences of `_aggregate_cohort_drift_for_pair(`: 1 def (line 184) + 2 calls (lines 299, 350). Future drift that inlines math at either call site reduces this count and trips `test_aggregate_helper_is_shared_by_both_compute_functions` |
| 4 | Strictly-exceed floor preserved (5.0% exactly vs 10.0%) | **PASS** — `compute_drift_attribution` with convergence 20→19 (= -5.0% exactly, weight 20) yields `dominant_axis = None`; convergence 20→18 (= -10.0%) yields `dominant_axis = "convergence"`. Confirms strict `<=` floor semantic at the per-case helper consumed by the cohort aggregator |
| 5 | NaN sentinel preservation in renderer | **PASS** — `CohortDriftAttribution(cohort_max_abs_delta_pct=math.nan, …)` → `render_cohort_drift_attribution_dict` returns `{"cohort_max_abs_delta_pct": null, …}` (JSON null). NaN never leaks to wire format |
| 6 | 2-snapshot degenerate equality | **PASS** — `test_cumulative_equals_latest_pair_when_only_two_snapshots` passes with EXACT endpoint label equality + aggregate result equality (5 axis-pin assertions); cumulative and latest-pair surfaces correctly degenerate to the same pair |
| 7 | Forbidden-token grep on methodology paragraph via SSOT 9-tuple | **PASS** — `test_methodology_doc_cumulative_section_passes_forbidden_grep` consumes `FORBIDDEN_POSITIVE_CLAIM_TOKENS_9` (line 76) and `assert_no_forbidden_positive_claims` (line 625); test green |
| 8 | `reports/snapshots/` + `golden_samples/` byte-identity pre/post probe | **PASS** — pre-probe state: 40 files in snapshots, 114 in golden, `git status --short` shows only the pre-existing untracked entries; post-probe state: identical (40, 114, same `git status` output). All test snapshot writes contained within `tmp_path` |
| 9 | Tier 1 trio preserved + slice-added prose forbidden grep | **PASS** (probe 9b) — Tier 1 trio (`Tier 1 engineering candidate`, `not_signed_validation`, `not_benchmark_agreement`) present in all 4 slice-touched files. Slice-A-added prose (12758 bytes after filtering forbidden-token list literals) contains zero forbidden positive claims outside negated form. Note: bare-file grep flags legitimate forbidden-token *list constants* (`_ENVELOPE_FORBIDDEN_TOKENS` in `cohort_anomalies.py:286`; advisor token list in `_schema_versions.py:449`) — these are the audit haystack, not claims |
| 10 | Back-compat 1.1.0 field intact at 1.2.0 | **PASS** — `test_back_compat_1_1_0_reader_field_present_in_1_2_0` asserts `report.cohort_drift_attribution is not None` and `isinstance(... , CohortDriftAttribution)` on the stuck-arc fixture; Phase 16 B field preserved intact |

**Bonus full-sweep verification**: at clean fa73797 (slice B WIP stashed away), `pytest tests/` collected and ran **2546 passed, 7 skipped** — exact match to the slice claim "2527 → 2546 (+19); 7 skipped; all green".

## Constraint-honor checklist

- [x] Auditing only, no source/test modifications (`git diff fa73797 -- <slice files>` returned empty after audit)
- [x] Never touched `^GS-\d{3}$` signed-registry entries (cohort discovery in both `cohort_drift_attribution.py` + `cohort_anomalies.py` filters them out; HF guards preserved)
- [x] No writes under `golden_samples/**` except `*-candidate/` (slice fixtures use `tmp_path`-scoped golden_samples copies; verified by probe 8 byte-identity)
- [x] No real OpenRadioss / no real LLM invocations (`_stub()` helper + JSON fixture-copy approach; live ASGI tests monkeypatch `_repo_root`)
- [x] Tier 1 wording discipline absolute: every artifact carries the Tier 1 trio; 9 forbidden positive-claim tokens absent outside negated form in slice-added prose (probe 9b)
- [x] HF1.7a + HF1.7b + HF1.8 path-guards preserved (signed-registry filter + tmp_path scoping for all snapshot writes)
- [x] Cohort dominant floor 5.0% strictly-exceed semantic preserved at write-time (shared helper line 253), test-time (recovery-arc None test), and methodology-time (doc explicitly cites "strictly-exceed semantic preserved")
- [x] Used `tempfile.TemporaryDirectory()` repos for probes 1, 2, 5; pytest with narrow selectors for probes 6, 7, 10; standalone python for probes 3, 4, 8, 9b
- [x] Audit report filed at `.planning/phase17_audit_reports/A.md`
- [x] Commit SHA fa73797 traced throughout

## Notes (informational, not blocking)

- **Working-tree slice B WIP detected during audit**: prior to the audit, the working tree contained uncommitted slice B work-in-progress (Phase 17 B schema bump 1.1.0 → 1.2.0 on `SIGNOFF_RECORD_SCHEMA_VERSION` + parallel updates to `signoff_record.py` + test pins in `test_phase16_signoff_drift_capture.py` + `test_phase16_journey_drift_audit_trail.py` line 509 + new `test_phase17_signoff_cumulative_drift_capture.py`). This WIP was orthogonal to slice A (no shared files modified). I stashed it for the audit and partially restored after — `git stash list` retains `stash@{0}: phase17_taa_audit_a_temp` containing the full slice B `signoff_record.py` patch that did not auto-merge on pop. The slice B engineer can recover via `git stash apply stash@{0}` and resolve manually. This is a session-bookkeeping note only; **does not affect slice A verdict**.
- **Bare-file forbidden-token grep flags audit-haystack list constants**: a naive scan of the four slice-touched files flags `"production ready"` (in advisor-tokens list at `_schema_versions.py:449`) and `"validated against"` (in `_ENVELOPE_FORBIDDEN_TOKENS` at `cohort_anomalies.py:286`). These are list literals naming the forbidden tokens for audit, not actual positive claims. The slice's own `test_methodology_doc_cumulative_section_passes_forbidden_grep` correctly scopes to the new methodology paragraph for this reason. Probe 9b's prose-only filtered grep (12758 bytes across all 4 files) is clean. No action required; informational only.

## Final verdict

**APPROVE — 63/63.** Slice A is a clean additive bump with extracted SSOT helper, dual-arc boundary pins, NaN-sentinel discipline, defensive parsing, and full Tier-1 wording discipline. Stop condition (≥60/63 AND every axis ≥95% of weight) satisfied with margin.
