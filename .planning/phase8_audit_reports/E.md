## TAA report — FM-04a Phase 8 E @ 9f0a8a1

> Tier 1 engineering candidate; not signed validation; not benchmark agreement.

**Auditor:** Independent Test Auditor Agent (TAA) — spawned 2026-05-16 against the binding blueprint `.planning/FM-04A_PHASE8_BLUEPRINT.md` §3.E.
**Subject:** Single commit `9f0a8a1` "feat(FM-04a/Phase8-E): cohort anomaly detection via per-axis z-score" — 9 files / +936 LOC.
**Verdict:** **APPROVE.**

---

### Diff inventory (verified against `git show 9f0a8a1 --stat`)

| File | Δ | Confirmed against blueprint §3.E |
|---|---|---|
| `backend/app/services/reporting/cohort_anomalies.py` | NEW +252 | builder + `severity_for` + `_assert_no_overclaim` + named constants + dataclasses |
| `backend/app/api/routes/cohort_anomalies.py` | NEW +29 | `GET /api/v1/cohort-anomalies` (no path params) |
| `backend/app/main.py` | +3 | `cohort_anomalies` import + `include_router` at line 125 |
| `tests/test_phase8_cohort_anomalies.py` | NEW +242 / 13 tests | severity boundary pins + cohort-size edge cases + outlier + envelope + endpoint |
| `tests/test_phase8_cohort_anomalies_properties.py` | NEW +68 / 4 Hypothesis tests | shared `_PROFILE = settings(derandomize=True, max_examples=25, deadline=None)` |
| `frontend/src/cohortAnomaliesClient.ts` | NEW +116 | typed client + `SUPPORTED_ANOMALY_SEVERITIES` `as const` |
| `frontend/src/components/CohortAnomaliesPanel.tsx` | NEW +143 | severity-tone helper, no inline hex as primary (CSS-var fallbacks only) |
| `frontend/src/App.tsx` | +2 | import + mount after `CohortExecutiveSummaryPanel` at line 1615 |
| `frontend/test/CohortAnomaliesPanel.test.tsx` | NEW +81 / 4 vitest tests | empty-state, outlier row, fetch-error, whitelist pin |

Blueprint deliverable counts: ≥10 backend tests / ≥4 property tests / ≥4 vitest. **Actual: 13 / 4 / 4.** Floor met with margin.

---

### Anti-gaming guard verification (Phase 8 specific, items relevant to slice E)

| Guard | Met? | Evidence |
|---|---|---|
| **M: -3 inline-magic z-thresholds** | Yes | `ANOMALY_SIGMA_INFO_MIN = 2.0` / `_WARN_MIN = 3.0` / `_DANGER_MIN = 4.0` declared at lines 59/62/65 with one-sentence docstrings (also satisfies D: -2). `severity_for` (lines 112-120) reads only these named constants — no inline `2.0`/`3.0`/`4.0` anywhere in the builder. |
| **M: -3 inline `COHORT_MIN_SIZE_FOR_ANOMALY`** | Yes | Declared at line 69 with rationale docstring referencing the two pinning tests. Builder line 162 reads the named constant. |
| **T: -2 per severity bucket without boundary pin** | Yes | `test_severity_for_info_at_lower_bound` (z=±2.0 → info), `_warn_at_lower_bound` (z=±3.0 → warn), `_danger_at_lower_bound` (z=±4.0 → danger). All three buckets pinned positively and negatively. |
| **T: -2 cohort size 1/2 edge cases not pinned** | Yes | `test_cohort_size_one_returns_empty` and `test_cohort_size_two_returns_empty` each construct a dedicated fixture (1 case / 2 cases) and assert `anomaly_count == 0` while `cohort_count` reflects truth (1 / 2). Not collapsed into a parametrized form — dedicated per Phase 8 guard wording. |
| **T: -3 Hypothesis test missing `derandomize=True`** | Yes | All 4 property tests share `_PROFILE = settings(derandomize=True, max_examples=25, deadline=None)` at line 21 of `test_phase8_cohort_anomalies_properties.py`; each test decorated with `@_PROFILE` (lines 29, 36, 48, 60). Spot-verified that `_PROFILE` is the *only* settings decorator on each test. |
| **B: -2 missing `schema_version` on endpoint** | Yes | `COHORT_ANOMALIES_SCHEMA_VERSION = "1.0.0"` declared in `_schema_versions.py:241` with rationale block (lines 242-253) referencing builder path + axes + severity ladder. Builder stamps it into the `CohortAnomaliesReport` dataclass at line 189; endpoint payload includes it (HTTP test `test_endpoint_returns_stamped_payload` line 229 asserts `payload["schema_version"] == COHORT_ANOMALIES_SCHEMA_VERSION`). |
| **B: -3 schema constant missing bump-history block** | Yes | Rationale block at `_schema_versions.py:242-253` documents builder, axes, severity ladder, claim_impact. Constant is `1.0.0` — no prior history to record yet, but the block form matches the four other Phase 8 constants. |
| **C: -10 verdict whitelist Tier 2 token** | N/A | Slice E does not touch the signoff verdict whitelist. |
| **C — no `^GS-\d{3}$` registry writes** | Yes | Builder scanner (lines 140-143) rejects names matching `_SIGNED_REGISTRY_RE = re.compile(r"^GS-\d{3}$")` **before** the candidate-suffix check (defense-in-depth as advertised in the commit body). No new code path writes anywhere; the builder is read-only over `golden_samples/*-candidate/`. |
| **C — Tier 1 disclaimer trio** | Yes | `CLAIM_TIER = "Tier 1 engineering candidate"` (line 48), `CLAIM_IMPACT_DEFAULT` contains both `"not signed validation"` and `"not benchmark agreement"` (lines 49-56). Two dedicated tests pin the trio: `test_anomaly_envelope_stamps_schema_and_disclaimer` (envelope path) + `test_endpoint_envelope_carries_disclaimer_trio` (HTTP path). |
| **X: -2 frontend whitelist duplicated inline** | Yes | `CohortAnomaliesPanel.tsx` imports `AnomalySeverity` type only; the SUPPORTED_ANOMALY_SEVERITIES literal is **not** duplicated. The vitest pin (`test/CohortAnomaliesPanel.test.tsx:78-80`) imports the constant from the client and asserts the exact 3-element array, guarding against future inline-list regression. |
| **X: -2 inline hex codes for severity tone** | Yes | `severityColor` (lines 17-21) returns `'var(--accent, #0a8a4a)'` / `'var(--text-warning, #b8860b)'` / `'var(--danger, #c0392b)'`. Primary color comes from CSS variables; hex codes are graceful-degradation fallbacks only — same Phase 7 / 8 B pattern. |
| **A — TAA findings closed by fix not waiver** | Yes (vacuous) | No prior CHANGES_REQUIRED findings against slice E. |
| **Envelope `_ENVELOPE_FORBIDDEN_TOKENS` narrowed to 4** | Yes | Tuple at lines 230-235 contains exactly: `"validated against"`, `"perforation completed"`, `"bullet-through-steel complete"`, `"validated physics"`. **4 tokens.** Matches Phase 7 B / Phase 8 B precedent (excludes `signed validation` / `benchmark agreement` so the legitimate `not signed validation; not benchmark agreement` disclaimer in `CLAIM_IMPACT_DEFAULT` passes audit). Spot-verified `_assert_no_overclaim` (lines 238-252) with `idx == 0` edge case: empty prefix doesn't end with `"not "` → raises, as designed. |

---

### Spot-verifications (load-bearing)

1. **`severity_for` boundary semantics**. Source lines 115-120: `abs_z >= ANOMALY_SIGMA_DANGER_MIN → danger`; `abs_z >= ANOMALY_SIGMA_WARN_MIN → warn`; else `info`. At z=2.0 → `info` (≥2.0 but <3.0). At z=3.0 → `warn` (≥3.0 but <4.0). At z=4.0 → `danger` (≥4.0). Matches blueprint §3.E severity ladder exactly. Negative z handled via `abs_z = abs(z_score)` (line 115) — both positive and negative tail rows trigger the same bucket. Boundary tests pin both signs.
2. **Below-floor routing test (`test_severity_for_below_info_returns_info_default`)**. Author claims this is the most-conservative bucket if a caller bypasses the gate. Verified at line 116: the function has no explicit "below 2σ" branch — falls through to the `info` default at line 120. The gate that actually prevents below-floor z-scores from emitting anomaly events lives in the **builder** (line 174: `if abs(z) >= ANOMALY_SIGMA_INFO_MIN`). This is the right split — `severity_for` is total over reals; the gate is a builder responsibility. Property test `test_property_below_info_floor_returns_info` (lines 60-68) makes this contract explicit.
3. **Engineered outlier test produces real evidence (not asymptote)**. `test_anomaly_detected_when_one_case_is_outlier` (lines 163-181): 6 cases at scores {85, 86, 87, 86, 85, 86} plus 1 outlier at 10. Cohort mean ≈ 75.0; cohort σ from these 7 values ≈ 27.5 (population stdev as used at line 166). z for outlier ≈ (10 − 75) / 27.5 ≈ −2.36 — comfortably above 2σ floor (≈18 % of the way into `info` bucket), not at the boundary asymptote. The test asserts only `abs(z) ≥ ANOMALY_SIGMA_INFO_MIN` (line 181) so it's robust to slight cohort-mean drift, but the engineered gap (75-point spread) gives ~2.4σ — real evidence that the anomaly path fires under realistic outlier conditions.
4. **Uniform cohort produces zero anomalies**. `test_uniform_cohort_has_zero_anomalies` (lines 184-190): 3 cases all at score 85. Builder line 168-170 detects `stdev == 0` and `continue`s the axis loop; report.anomaly_count = 0; report.cohort_count = 3 (assertion at line 190). Honest no-spread handling — neither divides-by-zero nor fakes an anomaly.
5. **`ANOMALY_AXES` covers all 4 trust-score axes**. Line 77-82: `("completeness", "convergence", "energy_audit", "reproducibility")`. Pinned by `test_anomaly_axes_constant_covers_four_trust_score_axes` (lines 211-217). Builder lines 156-159 read exactly these 4 weighted fields from the timeline's latest point; cross-checked against `trust_score_timeline.py:68-71` where the same 4 `_weighted: int` fields are declared.
6. **Population stdev (not sample) — and that's correct here**. Builder lines 166-167: `variance = sum((s - mean) ** 2 for s in scores) / len(scores)`; `stdev = math.sqrt(variance)`. This is **population** stdev (N divisor), not sample stdev (N−1). The blueprint doesn't dictate which — for cohort outlier detection the population form is the right call (the cohort *is* the population in this context, not a sample of a larger distribution). Acceptable; would only warrant a LOW if blueprint had specified otherwise.
7. **Frontend `as const` typing**. `cohortAnomaliesClient.ts:5-6`: `SUPPORTED_ANOMALY_SEVERITIES = ['info', 'warn', 'danger'] as const`; `type AnomalySeverity = (typeof SUPPORTED_ANOMALY_SEVERITIES)[number]`. Vitest pin (line 78-80) asserts exact tuple. `parseSeverity` (lines 50-53) defensively buckets unknown raw strings to `'info'` — *not* the most-conservative bucket in a strict sense (`danger` would be more conservative), but for anomaly *severity* the "unknown → quietest" choice is defensible because the panel's empty-state and tone-fallback semantics expect `info`-tone for non-actionable rows. Minor stylistic note, not a finding.
8. **HTTP test fixture `fake_repo`**. Lines 56-58 monkeypatch `route_module._repo_root` to `tmp_path`, so endpoint tests run against an empty repo and assert `cohort_count == 0` + `anomaly_count == 0` (line 230-231). Clean isolation; no side effects on real `golden_samples/`.

---

### Verification command results

```text
$ python -m pytest tests/test_phase8_cohort_anomalies.py \
                  tests/test_phase8_cohort_anomalies_properties.py -v
17 passed, 3 warnings in 1.17s
```

```text
$ python -m pytest tests/ -q
1703 passed, 8 skipped, 3 warnings in 18.11s
```

Note: commit message reports 1688 / 8 skipped. Actual is **1703 / 8 skipped** — author was conservative; full sweep is even cleaner than claimed. No regressions.

```text
$ cd frontend && npx vitest run
Test Files  6 passed (6)
Tests       33 passed (33)
```

Vitest expectation met (6 files / 33 tests). No `tsc -b` issues observed via the running build path.

HF1 path guard: clean (no edits to `agents/solver.py`, `router.py`, `geometry.py`, `schemas/sim_state.py`, `tests/test_toolchain_probes.py`, `Dockerfile`, `Makefile`, `scripts/hf1_path_guard.py`, `.github/workflows/`).
Signed-registry check: clean (no `^GS-\d{3}$` registry edits; builder rejects at scanner level).
Golden-samples writes outside `*-candidate`: none (builder is read-only).
Forbidden-positive-claim check on every Phase 8 endpoint envelope: passes (all 4 endpoints stamp `claim_tier` / `claim_boundary` / `claim_impact` with disclaimer trio; `_assert_no_overclaim` on the cohort-anomalies report runs at every `build_cohort_anomalies` call).

---

### Axis verdicts (slice E isolated)

| Axis | Weight | Score | Rationale |
|---|---|---|---|
| **B — schema versioning** | 12 | **12/12** | `COHORT_ANOMALIES_SCHEMA_VERSION = "1.0.0"` in `_schema_versions.py:241` with documented rationale; stamped into dataclass + JSON payload + tested. |
| **M — module quality** | 12 | **12/12** | Builder is pure (no I/O leak beyond `iterdir` + `timeline` read); named constants for all 4 thresholds + cohort floor (Phase 8 guard M: -3 × 2 satisfied); `severity_for` exported for direct tests; population stdev is a deliberate honest choice; envelope-narrowed forbidden list correctly tuned. |
| **T — testing** | 15 | **15/15** | 17 (13 backend + 4 properties) + 4 vitest = 21 new tests vs blueprint floor 10+4+4. Boundary pins at z=±2.0/±3.0/±4.0 for all 3 severity buckets; cohort-size 1 and 2 each have dedicated tests; engineered outlier produces real evidence (~−2.4σ, not asymptote); uniform cohort returns 0; Hypothesis tests share single `_PROFILE` with `derandomize=True` + `max_examples=25` + `deadline=None`. |
| **C — claim-tier discipline** | 12 | **12/12** | Tier 1 disclaimer trio in both envelope (`test_anomaly_envelope_stamps_schema_and_disclaimer`) and HTTP path (`test_endpoint_envelope_carries_disclaimer_trio`); `_assert_no_overclaim` runs on every build; `^GS-\d{3}$` rejection at scanner level (defense in depth); no `golden_samples` writes; no HF1 zone edits; no Linear/Notion writes; envelope-narrowed forbidden token list matches Phase 7 B / 8 B precedent. |
| **X — frontend integration** | 12 | **12/12** | Panel mounted in `App.tsx:1615`; vitest 4/4 + suite 33/33; `SUPPORTED_ANOMALY_SEVERITIES` imported from client (no inline literal in panel); `severityColor` driven by tone helper with CSS-variable primaries (hex codes are fallbacks only); `parseSeverity` defensively buckets unknown values; `z.toFixed(2)` for display is presentation-only and does not affect the underlying `cohort_anomalies.json` numeric stamping. |
| **D — documentation / SSOT** | 8 | **8/8** | `_schema_versions.py:241-253` rationale block; `cohort_anomalies.py` module docstring (lines 1-32) enumerates severity ladder, cohort size edge cases, and claim_impact; every threshold constant has a one-sentence rationale docstring on its own line; `COHORT_MIN_SIZE_FOR_ANOMALY` docstring (lines 70-72) explicitly cross-references the two pinning tests. |
| **A — anti-gaming discipline** | 8 | **8/8** | All Phase 8 anti-gaming guards relevant to slice E satisfied (verified item-by-item in the table above). No `_audit_verdict_whitelist` weakening (untouched). No magic-number regression. |
| **E — end-to-end workflow** | 8 | **8/8** | Two HTTP tests (`test_endpoint_returns_stamped_payload`, `test_endpoint_envelope_carries_disclaimer_trio`) compose endpoint with Phase 6 D `trust_score_timeline` reader. Cross-slice E2E is deferred to slice F per blueprint — slice E carries its share of integration evidence (endpoint goes through `app.main` router stack with `httpx.ASGITransport`). |
| **V — verification by TAA** | 13 | **3/13** | After this archive, TAA reports on disk: `A.md`, `B.md`, `E.md` = **3 of 7 expected** (`A`, `B`, `C`, `D`, `E`, `F`, `FINAL`). Author's commit message claims "V should land at 5/13 after this archive" — that claim is **not** consistent with the on-disk reality: slices C (`6e19def`) and D (`74902aa`) did not archive their TAA reports under `.planning/phase8_audit_reports/`. **Honest V = 3/13**, not 5/13. This is a counting discrepancy in the author scorecard, **not a finding against slice E itself** — slice E correctly produced its own audit (this file). V will naturally climb to 5/13 only after retroactive `C.md` + `D.md` archives land (or to 4/13 if only one of those gets retroactively audited). |

**Slice-E isolated score = 12 + 12 + 15 + 12 + 12 + 8 + 8 + 8 + 3 = 90/100.**

---

### Cumulative honest score after slice E

Slice A archived at 88/100 (V=1/13). Slice B archived at 89/100 (V=2/13). Slices C and D commits landed without TAA archives → no additional cumulative bump beyond their non-V axes. Slice E adds its own audit → V increments to 3/13.

Author's pre-TAA-E baseline claim was **91/100**. That figure pre-supposes C and D each got their TAA archive (which would put V at 4/13 before E, becoming 5/13 after E = author's claim). On-disk reality contradicts the V component of that claim.

**Honest cumulative score after slice E**: held to **89/100** + 1 V point for `E.md` = **90/100** by the strict reading of "V is the count of TAA archives landed under `.planning/phase8_audit_reports/`." The non-V axes for slice E are individually full-credit; the cumulative gap vs. the 99/100 target is entirely concentrated in V (missing TAA-C, TAA-D, TAA-F, TAA-FINAL) — exactly as the blueprint planned (V intentionally short until all 7 audits land at slice G).

**Main session is still on track** for the 99/100 honest-gate target at slice G closure, but **must** retroactively archive `C.md` and `D.md` (and produce `F.md` + `FINAL.md`) before claiming V is closed. The author SCORECARD's projection of 91/100 → 92/100 after slice E was off by ~2 points purely because the C/D audits were skipped — a recoverable bookkeeping gap, not a correctness or anti-gaming gap.

---

### Findings

**HIGH:** *(none)*

**LOW:**

1. **TAA-C and TAA-D archives missing.** The blueprint §3 says "All TAAs archived under `.planning/phase8_audit_reports/` — `A.md`, `B.md`, `C.md`, `D.md`, `E.md`, `F.md`, `FINAL.md`." Commits `6e19def` (C) and `74902aa` (D) merged without those archives. This is a **process-axis** (A) gap that the slice-E author should not have papered over via the "Cumulative honest score (pre-TAA-E): 91/100" assertion in the commit body — that figure depends on TAA archives that were never produced. Recommend retroactive `C.md` + `D.md` audits before slice G closes V. (Not a slice-E content finding — slice E itself is clean.)

2. **Author scorecard V miscount.** Commit body's "V should land at 5/13 after this archive" overstates V by 2 points relative to on-disk reality. Slice E's own delivery is unaffected; this is a cumulative-bookkeeping note.

3. **Population vs. sample stdev not documented in module docstring.** Builder uses population stdev (N divisor at line 166). Defensible for cohort-as-population framing; could be made explicit in the module docstring or the `_schema_versions.py` rationale block to head off future reviewer confusion. One-line addition; cosmetic only.

**BLOCK:** *(none)*

---

### Constraint check

- Tier 1 disclaimer trio present in every emitted payload: yes.
- No `^GS-\d{3}$` registry edits: yes (defense-in-depth at scanner level, line 140-143).
- No `golden_samples/**` writes outside `*-candidate`: yes (builder is read-only).
- HF1 hard-stop zone untouched: yes.
- No push / PR / Linear / Notion writes in this commit: yes (`git show 9f0a8a1 --name-only` confirms 9 files, all in `backend/` / `frontend/` / `tests/`).
- Forbidden positive claims only in `not <claim>` form: yes (audit verified for envelope-narrowed 4-token list; `claim_impact` clears the audit via `"not signed validation; not benchmark agreement"` patterns).
- No real OpenRadioss invocation: yes (builder reads frozen snapshot bytes via Phase 6 D timeline reader; no solver call).
- No LLM call / generative text: yes (deterministic arithmetic + dataclass serialization).

---

### Overall verdict

Slice E is a **clean, full-credit additive surface** on top of the Phase 6 D `trust_score_timeline` reader. The author got every load-bearing detail right:

- Named threshold constants with rationale docstrings (M guard satisfied).
- Boundary-pin tests at z=±2.0/±3.0/±4.0 for all three severity buckets, plus dedicated cohort-size-1 and cohort-size-2 edge-case tests (T guards satisfied).
- Shared `_PROFILE = settings(derandomize=True, max_examples=25, deadline=None)` on every property test (T: -3 guard satisfied).
- Engineered-outlier test produces real evidence (~−2.4σ), not asymptote.
- Uniform-cohort case honestly returns zero anomalies via the `stdev == 0` early-continue.
- Envelope-narrowed `_ENVELOPE_FORBIDDEN_TOKENS` tuple at exactly 4 tokens — same pattern as Phase 7 B and Phase 8 B — and the `not <claim>` prefix check correctly tolerates the legitimate disclaimer wording.
- Frontend client / panel / vitest harness follow the established Phase 8 B / D precedent; no inline-list regression, no inline-hex regression.
- HTTP endpoint cleanly integrated via `app.main:125`; both stamped-payload and disclaimer-trio HTTP tests pass.

The only adjustment vs. the author's SCORECARD is a **V-axis counting correction** (3/13 honestly, not 5/13) driven by missing TAA-C and TAA-D archives — that's a Phase-8 cumulative bookkeeping issue, not a slice-E quality issue.

**Audit assessment: 90/100 cumulative after slice E** (author's claim: 92/100 post-E — overstated by 2 V points). Slice E itself: APPROVE with no fixes required.

**Recommendation to main session:**
- Land retroactive `C.md` and `D.md` audits before slice F to bring V back in line with the blueprint plan.
- Slice F may proceed without slice-E rework.

> Tier 1 engineering candidate; not signed validation; not benchmark agreement.
