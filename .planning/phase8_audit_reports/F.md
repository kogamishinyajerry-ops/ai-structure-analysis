## TAA report — FM-04a Phase 8 F @ bec24c7

- **Commit audited**: `bec24c7` — "test(FM-04a/Phase8-F): HTTP integration (15) + E2E reviewer journeys (3) + slice-C TAA archive"
- **Auditor**: Independent TAA (Test Auditor Agent, slice-F scope; not the author of `bec24c7`)
- **Date**: 2026-05-16
- **Binding blueprint**: `.planning/FM-04A_PHASE8_BLUEPRINT.md` §3.F
- **Audited paths** (3 files; `git show bec24c7 --stat`):
  - `tests/test_phase8_endpoints_integration.py` (+364 lines, NEW)
  - `tests/test_fm04a_phase8_reviewer_accountability_e2e.py` (+268 lines, NEW)
  - `.planning/phase8_audit_reports/C.md` (+151 lines, retroactive slice-C TAA archive)

### Verdict

**APPROVE WITH FINDINGS.** Slice F ships the HTTP-integration + E2E surfaces with high quality and full Tier 1 disclaimer discipline; however the §3.F floor of **≥16 HTTP integration tests** is undershot by **1 test** (shipped 15). The author is honest about this in the commit message rather than gaming counts; the gap is partially compensated by slice E unit-level severity boundary pins. The E2E trio is genuinely load-bearing (verified item-by-item below). One T-axis deduction is honest; one B-axis cumulative bookkeeping correction noted.

### Spot-verified facts

1. **Test counts (recount via `grep -c "^def test_"`).** `test_phase8_endpoints_integration.py` = **15** (exactly matches commit message claim); `test_fm04a_phase8_reviewer_accountability_e2e.py` = **3**. Neither file uses parametrize to inflate counts.

2. **§3.F floor adjudication — 15 vs 16.** Blueprint breakdown: signoff (3) + provenance (3) + cohort exec (3) + cohort anomalies (**4**) + cross-endpoint forbidden audit (1) + envelope disclaimer trio round-trip (**2**) = 16. Author shipped: 3 + 3 + 3 + **3** + 1 (forbidden) + **1** (disclaimer) + 1 (content-type — not in blueprint §3.F). Net shortfall: 1 cohort-anomalies severity boundary HTTP pin AND 1 disclaimer round-trip slot, **substituted by** 1 content-type test. Mathematically 15 vs ≥16. The "equivalent weight" argument the author advances (cross-endpoint tests sweep 4 URLs inside a loop, so worth 4×) is **rejected** for counting purposes: pytest node IDs are 1 per `def test_`, and a loop failure surfaces as 1 failure (not 4). Counted honestly = 15.

3. **Severity boundary pins compensation.** The "missing" cohort-anomalies severity boundary pin at HTTP layer (the 4th test the blueprint asked for) is **covered at unit level** in `tests/test_phase8_cohort_anomalies.py:test_severity_for_info_at_lower_bound` + `test_severity_for_warn_at_lower_bound` + `test_severity_for_danger_at_lower_bound`. Anti-gaming guard #9 ("T: -2 per anomaly severity bucket without a boundary pin test") is satisfied at the unit layer. Guard #9 does NOT specify the layer must be HTTP. So the HTTP shortfall does not trigger guard #9; it triggers a milder "blueprint floor undershoot."

4. **E2E #1 chronological + verdict + disclaimer trio.** `test_phase8_signoff_workflow_e2e` (lines 125-162) writes 2 signoffs at `09:00Z` + `14:30Z`; asserts `records[0].signoff_utc == "2026-05-16T090000Z"` + `records[-1].verdict == "needs_more_convergence"` + `reviewer == "bob"`; asserts all 3 Tier 1 disclaimer trio phrases on `res.text.lower()`. Genuine reviewer journey, not toy assertion.

5. **E2E #2 SHA-256 independently re-hashed.** `test_phase8_provenance_trace_e2e` (lines 170-202) writes snapshot, reads provenance via HTTP, then **independently** computes `hashlib.sha256((snap_dir / input_entry["path"]).read_bytes()).hexdigest()` on disk and compares against `input_entry["sha256"]` for every `present=True` input (line 192-196). This is genuine reproducibility proof — not a self-consistency check.

6. **E2E #3 7-case cohort with engineered outlier.** `test_phase8_cohort_outlier_and_signoff_e2e` (lines 210-268): 6 healthy completeness scores (85-87) + 1 outlier (`GS-Z-candidate` = 10). Asserts `summary["cohort_count"] == 7`, outlier `bucket == "regressed"`, anomaly fires (`"GS-Z-candidate" in outlier_cases`), then writes `blocked_pending_input` signoff and re-fetches; asserts `latest_signoff_verdict == "blocked_pending_input"` surfaces in row. Composes Phase 5/6/7/8 surfaces (snapshot/score/cohort/signoff). Disclaimer trio asserted on all 3 response bodies (lines 264-268).

7. **All 3 E2E docstrings name the reviewer journey + Tier 1 disclaimer line.** Lines 126-130, 171-176, 211-217 — each docstring explicitly states the journey AND repeats "Tier 1 engineering candidate; not signed validation; not benchmark agreement." Guard #17 ("E: -2 per E2E missing disclaimer trio assertion on HTTP response body") satisfied 3/3.

8. **Cross-endpoint audit honestly scoped.** `test_all_phase8_endpoints_contain_no_forbidden_positive_claim` (lines 312-344) uses a **4-token envelope-forbidden list** (`validated against`, `perforation completed`, `bullet-through-steel complete`, `validated physics`) — explicitly excluding `"signed validation"` + `"benchmark agreement"` because envelopes themselves emit those inside compound disclaimer sentences. The inline comment (lines 318-321) explains the same Phase 7 B two-list design rationale. Honest scoping, not gaming.

9. **HF1 zone clean.** `git show bec24c7 --name-only` touches only `tests/` + `.planning/`. No `agents/`, `schemas/sim_state.py`, `Dockerfile`, `Makefile`, `.github/workflows/`. HF1 path guard satisfied.

10. **Full test sweep**: `1706 passed, 8 skipped` in 15.76s (verified locally; matches commit message claim `+18` from `1688` baseline).

### Anti-gaming guard audit

| Guard | Slice F applicable? | Verdict |
|-------|---------------------|---------|
| **C: -10** verdict whitelist Tier 2 token | N/A (slice F adds no whitelist edits) | — |
| **C: -8** audit weakened/removed | N/A | — |
| **C: -5** notes body forbidden claim outside `not <claim>` form | Yes, indirectly — signoff notes written in E2E #1 + #3 + integration tests | All E2E + integration notes are plain reviewer prose ("Initial monitoring round...", "Mesh sweep too coarse...", "Blocked pending material card from supplier.") — no forbidden positive claims. **No deduction.** |
| **M: -3** z-score thresholds inline-magic | N/A (slice F is test-only) | — |
| **M: -3** cohort min size inline-magic | N/A | — |
| **M: -2** signoff filename uses local time | N/A | — |
| **B: -2** missing `schema_version` field on endpoint | All 4 endpoints stamp `schema_version` (verified by `test_signoff_history_endpoint_empty_case` line 121, `test_provenance_endpoint_returns_stamped_payload` line 166, `test_executive_summary_endpoint_empty_cohort` line 201, `test_anomalies_endpoint_empty_cohort_zero_anomalies` line 244). No deduction. |
| **B: -3** new schema constant skips bump-history | N/A (slice F adds no new schema constants) | — |
| **T: -2** anomaly severity bucket without boundary pin | All 3 buckets (info/warn/danger) pinned at unit level in slice E — `test_severity_for_info_at_lower_bound` / `_warn_` / `_danger_`. **No deduction.** |
| **T: -2** signoff verdict without positive test | All 4 verdicts (`watching`, `needs_more_evidence`, `needs_more_convergence`, `blocked_pending_input`) used in positive tests across slice A unit tests + slice F E2E. **No deduction.** |
| **T: -3** Hypothesis test lacks `derandomize=True` | N/A (slice F has no Hypothesis tests) | — |
| **T: -2** cohort size = 1 or 2 anomaly edge case unpinned | `test_anomalies_endpoint_under_min_cohort_size_returns_empty` (cohort size 2) at HTTP layer; `test_cohort_size_one_returns_empty` + `test_cohort_size_two_returns_empty` at unit layer. **No deduction.** |
| **X: -2** `SUPPORTED_SIGNOFF_VERDICTS` literal duplication | N/A (slice F is backend tests + E2E) | — |
| **X: -2** verdict tone colors inline hex | N/A | — |
| **D: -2** schema constant lacks rationale | N/A | — |
| **A: -3** CHANGES_REQUIRED closed by waiver | N/A (no waivers in slice F) | — |
| **E: -2** E2E missing disclaimer trio assertion | All 3 E2Es assert trio on HTTP response body (lines 159-162, 199-202, 264-268). **0 violations of guard #17.** |

**§3.F floor undershoot (custom T-axis deduction):** Blueprint asked for ≥16 HTTP integration tests; shipped 15. Although the cohort-anomalies severity boundary pin is covered at unit layer, the **2 disclaimer round-trip slots** the blueprint asked for were collapsed to 1 (compensated by 1 content-type test, which is useful but not the same scope). Honest T deduction: **-1**.

### Axis verdicts (slice F isolated)

| Axis | Weight | Slice-F score | Reasoning |
|------|--------|---------------|-----------|
| **B — schema versioning behavior** | 12 | **12/12** | All 4 endpoint envelopes assert `schema_version` field; no new constants in slice F (correctly so — test-only slice). |
| **M — module quality** | 12 | **12/12** | Test harness uses shared `_SyncASGIClient` helper (lines 46-57) + `_seed_case` + `_seed_snapshot_with_completeness` helpers identical across both files. Reasonable DRY without over-abstraction. |
| **T — testing** | 15 | **14/15** | §3.F floor undershoot: 15 vs ≥16. Full sweep 1706 passed +18 net. All 4 verdicts + 3 severity buckets + cohort min size edge cases pinned (across slice E + F). **-1 honest deduction**. |
| **C — claim-tier discipline** | 12 | **12/12** | Tier 1 disclaimer trio asserted across all endpoints (cross-endpoint test) + all 3 E2Es. Forbidden positive claim audit two-list design preserved. No `^GS-\d{3}$` registry writes (all test cases use `GS-A-candidate`/`GS-B-candidate`/`.../GS-Z-candidate` `*-candidate` shape). `_seed_case` writes inside `tmp_path` only. No `golden_samples/**` writes outside `*-candidate`. |
| **X — frontend integration** | 12 | **(carry from B) 12/12** | Slice F adds no frontend; existing X earned at slice B unchanged. |
| **D — documentation / SSOT** | 8 | **8/8** | Both new test files have load-bearing module docstrings (lines 1-8 + lines 1-22) naming the journey scope + Tier 1 boundary. |
| **A — anti-gaming discipline** | 8 | **8/8** | Author honest in commit message about 15 vs 16 ("equivalent weight" framing is rejected for counting but the honesty is noted). No waiver. No guard violation. |
| **E — end-to-end workflow** | 8 | **8/8** | 3 E2Es compose Phase 5/6/7/8 surfaces; all 3 assert disclaimer trio on HTTP response body. Guard #17 = 0 violations. |
| **V — verification by TAA** | 13 | **6/13** | After this archive: A.md, B.md, C.md, D.md, E.md, F.md on disk = **6 of 7 expected** (`A`, `B`, `C`, `D`, `E`, `F`, `FINAL`). Author's commit message claims "V should land at 6/13 after this archive" — **consistent**. Note: slice-E TAA flagged the C+D archives as missing at that time; this commit closes that gap by retroactively landing C.md (D.md already landed separately). V correctly advances 5→6/13. FINAL still owed at slice G. |

**Slice-F isolated score = 12 + 12 + 14 + 12 + 12 + 8 + 8 + 8 + 6 = 92/100.**

### Cumulative honest score after slice F

Independent assessment vs author's claim of 92 pre-TAA-D/E/F:

- B 12 + M 12 + T 14 + C 12 + X 12 + D 8 + A 8 + E 8 + V 6 = **92/100**

Matches the author's pre-TAA-D/E/F claim, but with a different decomposition: the author claimed T=15 / V=5 (pre-correction); honest is T=14 / V=6. Net cumulative is the same.

### HIGH findings

**None.** No BLOCK; no HIGH; one MEDIUM (T-axis -1) absorbed into the SCORECARD.

### MEDIUM findings

1. **T: -1 — §3.F HTTP integration floor undershoot.** Blueprint §3.F line 132 specifies "≥16 tests"; shipped 15. The author's "equivalent weight" defense (cross-endpoint tests sweep 4 URLs in a loop) is rejected — pytest node IDs count by `def test_`, not by URLs swept. Recommended remediation at slice G: add 1 HTTP-level cohort-anomalies severity boundary pin test (z=2.0 → info via the API surface) OR a second disclaimer round-trip test that asserts the trio appears in *every* endpoint envelope's `claim_impact` field specifically (rather than just substring-anywhere-in-body). Either lands the floor exactly. This is a soft finding — the 15 tests genuinely cover the §3.F surface intent; the deduction is for the floor mechanic.

### LOW findings

**None.**

### Recommendation

**APPROVE.** Proceed to slice G (STATE refresh + retrospective + FINAL whole-arc TAA). Recommend slice G author optionally land 1 additional HTTP integration test (severity boundary pin at API layer) to close the 15→16 floor exactly and recover the T -1, otherwise carry the -1 forward into FINAL transparently. Cumulative honest score after slice F = **92/100**; the ≥99 / per-axis ≥95% closure gate at slice G is still reachable if (a) FINAL TAA archives cleanly (V +7 to 13/13) and (b) the T -1 is either closed or accepted.

---

**Constraint reaffirmation:** Tier 1 engineering candidate; not signed validation; not benchmark agreement. No FM-04b. No `^GS-\d{3}$` writes outside tests. No HF1 zone edits. No push/PR/Linear/Notion. Audit performed read-only; no source code modified.
