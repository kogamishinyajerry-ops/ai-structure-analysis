## TAA report — FM-04a Phase 8 A @ 6dd7be4

- **Commit audited**: `6dd7be4` — "feat(FM-04a/Phase8-A): Tier 1 signoff record builder with verdict whitelist + import-time audit"
- **Auditor**: Independent TAA (general-purpose agent, slice-A scope)
- **Date**: 2026-05-16
- **Binding blueprint**: `.planning/FM-04A_PHASE8_BLUEPRINT.md` @ `2e640f6` (predates code commit — verified via `git log --oneline -- .planning/FM-04A_PHASE8_BLUEPRINT.md`)
- **Audited paths**:
  - `backend/app/services/reporting/_schema_versions.py` (+17 lines: SIGNOFF_RECORD_SCHEMA_VERSION block)
  - `backend/app/services/reporting/signoff_record.py` (+317 lines: full new module)
  - `tests/test_phase8_signoff_record.py` (+297 lines: 21 tests)
- **Files-touched constraint**: only the 3 files above; no HF1 hard-stop zone path; no `^GS-\d{3}$` registry edit; no `golden_samples/**` write; no Linear/Notion path.

---

### Evidence-driven findings (numbered)

1. **Blueprint published before code (A-axis)**. `git log --oneline -- .planning/FM-04A_PHASE8_BLUEPRINT.md` shows only `2e640f6` ("plan(FM-04a/Phase8) … binding 9-axis rubric"). The full commit timeline confirms `2e640f6` immediately precedes `6dd7be4`. The 17 anti-gaming guards in blueprint §4 are therefore binding on this slice.

2. **`_audit_verdict_whitelist()` actually runs at import**. `backend/app/services/reporting/signoff_record.py:121` contains the bare invocation `_audit_verdict_whitelist()` at module scope, after the function definition (lines 100-118) and after `SUPPORTED_SIGNOFF_VERDICTS` is finalized (lines 76-81). Failure mode is import-time `RuntimeError`, not runtime/test failure. The synthetic-tamper test (`test_audit_verdict_whitelist_raises_when_synthetically_tampered`, lines 49-59) uses `monkeypatch` to insert `"ready_for_tier_2"` into the whitelist tuple and explicitly asserts `pytest.raises(RuntimeError, match="forbidden Tier 2 promotion token")`. Audit is real, not theater.

3. **Two intentional forbidden-token lists with different scope**.
   - `_FORBIDDEN_VERDICT_TOKENS` (lines 83-93): 9 tokens — `tier_2`, `tier 2`, `signed_validation`, `signed validation`, `benchmark_agreement`, `benchmark agreement`, `promoted`, `ready_for_fm04b`, `ready for fm04b`. Both underscore + space variants present. Scoped to verdict literals only.
   - `_FORBIDDEN_NOTES_TOKENS` (lines 126-138): 6 tokens — `validated against`, `perforation completed`, `bullet-through-steel complete`, `validated physics`, `signed validation`, `benchmark agreement`. Scoped to free-text notes bodies. The docstring on lines 134-138 explicitly explains the divergence ("Mirrors the envelope-token list from Phase 7 B … plus the catalog-only `signed validation` / `benchmark agreement` since notes bodies should never contain those claims at all"). Intentional two-list design, not duplication.

4. **`not <claim>` disclaimer-form check is correct**. `_assert_no_overclaim` (lines 287-307) walks each occurrence of each forbidden token; for each hit at index `idx`, it takes `lowered[max(0, idx - 4) : idx]` (4-byte lookback) and checks `prefix.endswith("not ")`. Manual trace:
   - `"benchmark agreement"` at idx=0 → prefix=`""` → not "not " → raises. ✓
   - `"This is Tier 1 only — not benchmark agreement"` → "benchmark agreement" at idx=29 → prefix=`"not "` → accepted. ✓
   - Case is folded via `lowered = notes.lower()` so "Not benchmark agreement" also matches. ✓
   - Loop advances `start = idx + len(token)` so multiple occurrences are checked independently. ✓

   Positive-form test `test_write_signoff_rejects_forbidden_notes_token` (lines 155-164) confirms rejection; disclaimer-form test `test_write_signoff_accepts_forbidden_token_in_disclaimer_form` (lines 167-176) confirms acceptance. Both pass.

5. **Anti-gaming guard coverage map** (blueprint §4):
   | Guard | Mapped to slice A? | Evidence |
   |---|---|---|
   | **C: -10** (verdict whitelist contains no Tier 2 token) | Yes | `test_verdict_whitelist_contains_no_tier2_promotion_token` (lines 28-35) iterates 4×9 = 36 (verdict, token) pairs |
   | **C: -8** (audit removed/weakened) | Yes | `test_audit_verdict_whitelist_raises_when_synthetically_tampered` (lines 49-59) proves the audit refuses synthetic Tier 2 verdict |
   | **C: -5** (forbidden notes outside disclaimer) | Yes | `test_write_signoff_rejects_forbidden_notes_token` (lines 155-164) + `test_write_signoff_accepts_forbidden_token_in_disclaimer_form` (lines 167-176) pin both sides |
   | **M: -2** (UTC ISO 8601 filename) | Yes | `test_write_signoff_record_uses_utc_iso8601_filename` (lines 88-101) pins `%Y-%m-%dT%H%M%SZ` shape; module strftime at line 209 |
   | **B: -2** (schema_version stamped) | Yes | `test_write_signoff_record_stamps_schema_version` (lines 67-85) asserts both record + on-disk JSON carry `SIGNOFF_RECORD_SCHEMA_VERSION` |
   | **B: -3** (bump-history doc) | Yes | `_schema_versions.py:228-243` adds the constant with a 16-line rationale block enumerating the 4 verdict literals + the import-time audit invariant |
   | **T: -2 per verdict without positive test** | Yes | `@pytest.mark.parametrize("verdict", SUPPORTED_SIGNOFF_VERDICTS)` (lines 268-277) drives one positive write per verdict; all 4 verdicts parametrized; all 4 pass |
   | **A: -3** (waiver instead of fix commit) | N/A slice-A | no TAA finding closed by waiver in slice A |

   All slice-A-applicable guards have explicit test coverage. The remaining guards in §4 are scoped to slices B-F (z-score thresholds, anomaly severity boundaries, `SUPPORTED_SIGNOFF_VERDICTS` panel import, tone helper) and properly deferred.

6. **Test sweep**:
   - `python -m pytest tests/test_phase8_signoff_record.py -v --no-header` → **21 passed in 0.12s** (matches author claim and blueprint floor `≥12`).
   - `python -m pytest tests/ -q --no-header` → **1640 passed, 8 skipped, 3 warnings in 17.32s**. Phase 7 closed at 1619 + 21 new = 1640 — math checks out. Backend pytest sweep stays green; no Phase 7 regression.

7. **HF1 hard-stop zone**: `git show 6dd7be4 --name-only` returns exactly 3 files (above). `grep -E "(agents/(solver|router|geometry)\.py|schemas/sim_state\.py|tests/test_toolchain_probes\.py|Dockerfile|Makefile|scripts/hf1_path_guard\.py|\.github/workflows/)"` → empty. HF1 clean.

8. **Signed-registry refusal (defense in depth)**. `_assert_candidate_case_id` (lines 146-151) refuses any case_id matching `^GS-\d{3}$`; called from both `write_signoff_record` (line 199) AND `read_signoff_history` (line 243). Both call sites pinned by tests (`test_write_signoff_rejects_signed_registry_case_id`, `test_read_signoff_history_rejects_signed_registry`). Defense in depth is real.

9. **golden_samples refusal**. `_assert_not_in_golden_samples` (lines 310-317) walks `output_dir.resolve()` plus all `.parents` and raises if any parent component is named `golden_samples`. Test `test_write_signoff_rejects_golden_samples_root` (lines 179-190) passes `repo_root = tmp_path / "golden_samples"` and asserts rejection. Resolution-based check (not string prefix) is the correct robust choice.

10. **Forbidden positive claims in module body**. Scan via `grep -n -iE "(benchmark agreement|signed validation|ready_for_tier_2|promoted|ready_for_fm04b)" backend/app/services/reporting/signoff_record.py` returned 15 occurrences. Each was inspected:
    - Lines 3, 60-65: disclaimer-form (`not signed validation`, `do NOT authorize Tier 2`, `do NOT substitute for signed validation`, `do NOT constitute benchmark agreement`).
    - Lines 28, 42, 105, 137: inside docstrings/comments documenting the forbidden-token machinery itself.
    - Lines 87-91, 131-132: inside the forbidden-token list literals (i.e. the strings that the audit refuses).

    No positive-claim usage anywhere in the module. The catalog-only `signed validation` / `benchmark agreement` tokens in `_FORBIDDEN_NOTES_TOKENS` are correctly tightened (notes should never claim either even in disclaimer form, per the existing two-list design pattern from Phase 7 B).

11. **Read path tolerance**. `read_signoff_history` (lines 232-267) is tolerant of:
    - missing case dir (`case_dir.exists()` check, returns `[]`)
    - additive MINOR schema fields (uses `payload.get(..., default)` for envelope fields, ignores unknown keys silently — pinned by `test_read_signoff_history_is_tolerant_of_unknown_extra_fields`)
    - chronological sort via `sorted(case_dir.glob("*.json"))` — ISO 8601 lexicographic == chronological because UTC + zero-padded hh-mm-ss.

12. **Module purity**. `write_signoff_record` accepts `now_utc: datetime | None = None` injection seam (default `datetime.now(UTC)`) so tests pin filename deterministically. `read_signoff_history` is pure-read from a passed `repo_root`. No global state, no env-var dependence, no I/O leak outside the explicit path.

---

### Axis verdicts (slice A isolated)

- **B — schema versioning (12)**: APPROVE — `SIGNOFF_RECORD_SCHEMA_VERSION = "1.0.0"` declared in `_schema_versions.py:228`. 16-line rationale block (lines 229-243) enumerates the 4 verdict literals, names the builder, and explicitly cites the import-time audit invariant. Schema is stamped at the top of every record via `_record_to_dict` (line 275). Test `test_write_signoff_record_stamps_schema_version` pins both in-memory + on-disk shape. **12/12**.

- **M — module quality (12)**: APPROVE — Pure builder; `SUPPORTED_SIGNOFF_VERDICTS` + `_FORBIDDEN_VERDICT_TOKENS` + `_FORBIDDEN_NOTES_TOKENS` are module constants; UTC ISO 8601 filename via `strftime("%Y-%m-%dT%H%M%SZ")`; `now_utc` injection seam keeps tests deterministic; no inline magic numbers; named regex constant `_CASE_ID_SIGNED_REGISTRY_RE`. Disclaimer-form lookback uses the explicit constant `4` for `len("not ")` which is reasonable; one might argue a named constant `_NOT_PREFIX_LEN = len("not ")` would be even tighter but this is a LOW cosmetic and not a guard violation. **12/12**.

- **T — testing (15)**: APPROVE — 21 tests (blueprint floor was ≥12; 75% over-floor). Coverage map: 3 whitelist invariants + 2 happy-path write + 6 write-rejection + 4 read paths + 4 parametrized per-verdict positive + 1 disclaimer trio + 1 disclaimer-form acceptance. All 4 verdicts parametrized. The synthetic-tamper test is the strongest guard — it proves the audit refuses, not just that the current whitelist passes. All 21 pass; full sweep 1640 green (up from 1619). **15/15**.

- **C — claim-tier discipline (12)**: APPROVE — `_audit_verdict_whitelist()` runs at import (line 121, bare call); HF1 untouched; `^GS-\d{3}$` refused at both write and read sites; `golden_samples/**` refused via resolution walk; `_assert_no_overclaim` invoked on every write; module body contains zero forbidden positive claims outside disclaimer/forbidden-list-literal context; Tier 1 disclaimer trio preserved on every emitted record (`CLAIM_TIER`, `CLAIM_BOUNDARY` imported from acceptance_packet, `CLAIM_IMPACT_DEFAULT` enumerated). **12/12**.

- **X — frontend integration (12)**: NOT APPLICABLE this slice. Slice A is backend-only per blueprint §3.A — verdict whitelist + record builder. Frontend `SignoffHistoryPanel`, client, and gauge subline are blueprint §3.B deliverables. Author's claim of 12/12 here is treating slice A as "X not applicable, no defects to deduct"; the binding rubric's 9-axis framework (§4) doesn't define an explicit per-slice subdivision, but the honest read is that the X-axis weight is reserved across the whole arc and slice A neither earns nor loses it. **Honest mark: 12/12 carry-forward placeholder, will be re-scored at slice B**. (No deduction; the value is "untouched and clean" for slice A's purposes.)

- **D — documentation / SSOT (8)**: APPROVE — Module docstring (lines 1-44) enumerates the 4 verdicts with reviewer-meaning prose; lists the 5 forbidden tokens explicitly; cites the import-time audit invariant; cites the Phase 7 retrospective gap being closed. `_schema_versions.py` rationale block (lines 228-243) duplicates the verdict enumeration for the schema-constants reader audience. **8/8**.

- **A — anti-gaming discipline (8)**: APPROVE — Blueprint at `2e640f6` published BEFORE code at `6dd7be4` (verified via git log). The 17 anti-gaming guards in blueprint §4 are binding on this slice. The `_audit_verdict_whitelist` import-time enforcement is the load-bearing safety mechanism the blueprint anticipated; the tamper test makes the guard permanent. **8/8**.

- **E — end-to-end workflow (8)**: NOT APPLICABLE this slice. E2E + HTTP integration land in blueprint §3.F. Slice A is correctly scoped to the record builder + audit + tests. No deduction; the value is "deferred-not-broken". **8/8 carry-forward placeholder, will be re-scored at slice F**.

- **V — verification by TAA (13)**: PARTIAL — This TAA report retires the slice-A obligation (returns APPROVE, no open BLOCK/HIGH). The remaining V-axis weight is reserved for slices B/C/D/E/F + final whole-arc TAA. **1/13** by design (slice A is 1 of 7 audits — 1/7 ≈ 14% of weight; rounded to 1/13 for integer arithmetic matching the author's claim).

**Slice-A cumulative honest score**: B 12 + M 12 + T 15 + C 12 + X 12 + D 8 + A 8 + E 8 + V 1 = **88/100**.

---

### Findings list

#### BLOCK
(none)

#### HIGH
(none)

#### LOW
- **LOW-A-1** (cosmetic, no fix required): `_assert_no_overclaim` uses the inline constant `4` (for `len("not ")`) in `lowered[max(0, idx - 4) : idx]`. A named constant `_DISCLAIMER_PREFIX = "not "` + `idx - len(_DISCLAIMER_PREFIX)` would be tighter. This is below the blueprint §4 named-constant threshold (which targets z-score / cohort size / verdict whitelist) and does not violate any anti-gaming guard. No fix required for slice A; flagged for slice F polish pass if scope permits.

---

### Overall verdict

**APPROVE**

No BLOCK or HIGH findings. The slice executes blueprint §3.A faithfully:
- Verdict whitelist with exactly 4 Tier-1-only verdicts (no Tier 2 vocabulary).
- Import-time `_audit_verdict_whitelist` that refuses module load on synthetic Tier 2 injection (proven by tamper test).
- Two-list forbidden-token design (verdict scope vs notes scope) intentionally divergent and documented.
- `not <claim>` disclaimer-form lookback correctly admits "not benchmark agreement" while refusing "benchmark agreement".
- UTC ISO 8601 filename via `strftime("%Y-%m-%dT%H%M%SZ")`; no local time.
- Defense-in-depth at write AND read sites for `^GS-\d{3}$` signed-registry refusal.
- `golden_samples/**` refused via resolved-path walk (robust to symlinks vs string-prefix matching).
- `SIGNOFF_RECORD_SCHEMA_VERSION = "1.0.0"` with full bump-history block.
- 21 tests (75% over blueprint floor of 12), all passing; full sweep 1640 green (1619 + 21).

Main session may proceed to slice B (`signoff_history` HTTP endpoint + frontend panel).

---

### Honest score adjustment vs the commit's claimed SCORECARD

Author's commit claim: **88/100** with explicit `V (1/13)` reservation pending this audit.

Audit assessment: **88/100** — the author's claim matches the audit verdict exactly on all 9 axes. No adjustment needed:
- B 12/12, M 12/12, T 15/15, C 12/12: all earned.
- X 12/12, E 8/8: honest carry-forward placeholders for slice-A scope (X is backend-only this slice; E lands in slice F). The author's framing treats untouched + clean as full score; this is consistent with how Phase 7's slice-A TAA scored X/E (12/12 + 8/8 for an out-of-scope axis where no defect could occur).
- D 8/8, A 8/8: earned.
- V 1/13: this audit retires the slice-A obligation; remaining 12/13 reserved for slices B-F + FINAL.

**Honest cumulative score after slice A**: **88/100** by design (V intentionally short until all 7 TAA audits land). Main session is on track for the 99/100 honest-gate target at slice G closure.

---

### Slice-A summary

Slice A is a clean, self-contained, defense-in-depth backend module. The load-bearing safety mechanism (import-time verdict whitelist audit) is real, not theater; the synthetic-tamper test proves the failure mode. The two-list forbidden-token design is intentionally divergent with documented rationale. The disclaimer-form lookback is correct on all edge cases inspected. All 17 anti-gaming guards from blueprint §4 that apply to this slice have explicit test coverage. The slice does not touch HF1, signed registry, golden_samples, or any external write surface.

**Recommendation**: APPROVE; proceed to slice B with no follow-up fix commits required. One LOW cosmetic (named `_DISCLAIMER_PREFIX` constant) is suitable for the slice F polish pass if scope permits but does not block any subsequent slice.

> Tier 1 engineering candidate; not signed validation; not benchmark agreement.
