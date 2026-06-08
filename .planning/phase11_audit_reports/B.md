# Phase 11 B — TAA report

**Slice commit:** `61a8a02`
**Verdict:** APPROVE
**Test count:** 45 (26 test functions; parametrize expands `missing_key×4` + `forbidden×9` + `disclaimer×9` = 22 cases adding 19 over function count)
**Test pass:** 45/45; full sweep 1992 passed + 7 skipped (matches claim exactly, +45 over slice-A's 1947)

## Per-axis evidence

- **M (12/12)** — SSOT discipline is exemplary. Every closed-set tuple and constant is module-level with explicit `tuple[str, ...]` type pin: `ADVISOR_STATUS_TUPLE` (`advisor_critique.py:68`), `FOUR_QUESTION_GATE_KEYS` (`advisor_critique.py:78-83`), `ADVISOR_FORBIDDEN_TOKENS` (`advisor_critique.py:104-116`), `CLAIM_TIER` / `CLAIM_IMPACT_DEFAULT` (`advisor_critique.py:54-62`). Schema-version constant is imported by identifier (`advisor_critique.py:51`) — no inline literal in the builder. The `_schema_versions.py:346-373` block documents bump policy AND explicitly acknowledges closed-set SSOTs and per-token T:-5 audit requirement ("each new token is exercised by a dedicated test per Phase 11 anti-gaming guard T:-5") satisfying the rubric's docstring requirement. `CLAIM_BOUNDARY` is reused from `acceptance_packet.py:38` (consistent with rest of reporting surface).

- **T (15/15)** — Comfortably over floor (≥12). All required test categories present:
  - 4-Q gate refuses missing key — parametrized × 4 (`test_phase11_advisor_critique.py:348-358`)
  - Forbidden-token audit per-token — parametrized × 9 over `ADVISOR_FORBIDDEN_TOKENS` (`tests:406-424`)
  - Stub deterministic on fixed input (`tests:269-279`)
  - Provider fallback path (`tests:296-308`)
  - Envelope schema-version pin (`tests:117-119`)
  - `advisor_status` enum closed-set pin (`tests:122-126`)
  Plus per-token `not <claim>` disclaimer form parametrized × 9 (`tests:427-444`), case-fold audit (`tests:447-463`), envelope key pin (`tests:471-492`), dataclass-isinstance pin (`tests:495-500`), stub-correlated content tests for trust=42 / open_residual / linear_static / explicit_dynamics / always-emit prompts (`tests:212-288`). 45 collected, all green.

- **C (12/12)** — Tier 1 disclaimer trio stamped on every envelope: `claim_tier=CLAIM_TIER`, `claim_boundary=CLAIM_BOUNDARY`, `claim_impact=CLAIM_IMPACT_DEFAULT` set in `build_advisor_critique` (`advisor_critique.py:402-404`). Test `test_envelope_carries_schema_version_and_claim_banners` (`tests:165-173`) asserts all three plus explicit "not signed validation" / "not benchmark agreement" substrings. C:-10 4-Q gate audit has distinct refusal paths in `_audit_four_question_gate` (`advisor_critique.py:435-466`): missing keys → `ValueError("missing keys")`, unknown keys → `ValueError("unknown keys")`, non-bool → `ValueError("non-boolean")`, False answer → `ValueError("False answer(s)")` — all four exercised by tests at lines 348-398. The forbidden-claim audit fires per ADVISOR_FORBIDDEN_TOKENS at `advisor_critique.py:474-486` with `not <claim>` 4-char prefix relief and case-fold.

- **A (8/8)** — All named guards exercised distinctly:
  - **M:-2 (closed-set pinned)**: `test_advisor_status_tuple_closed_set` + `test_four_question_gate_keys_pinned_exactly` + `test_advisor_forbidden_tokens_extends_base_with_phase11_additions` (tests 122 / 129 / 140) pin each tuple by identity AND value.
  - **T:-5 (per-token)**: parametrized over EACH of 9 ADVISOR_FORBIDDEN_TOKENS (`tests:406-424`). Verified independently — all 9 cases pass.
  - **A:-2 (vacuous-stub)**: trust_score=42 surfaces concern naming "42" (verified: `tests:212-220`); energy_audit_status="open_residual" surfaces question naming "open_residual" (`tests:223-231`); always-emit mesh baseline + load-case prompts (`tests:260-266, 282-288`).
  - **A:-3 (envelope refused, not silently scrubbed)**: `_assert_no_overclaim` raises `ValueError` rather than mutating payload (`advisor_critique.py:482-485`); parametrized test fires `pytest.raises(ValueError, match="forbidden positive claim")` over all 9 tokens.
  - **C:-10 (4-Q gate refusal modes)**: 4 distinct refusal tests as enumerated above.

- **E (8/8)** — Full sweep clean: `1992 passed, 7 skipped, 3 warnings in 18.51s` — matches commit claim byte-for-byte (was 1947+7 at slice-A close, +45 new). No regressions in `schema_versions` stamping / `case_completeness` / `trust_score` / endpoint surfaces. Module imports clean (the test file imports 13 symbols from `advisor_critique` including private `_critique_to_dict` for envelope-key pin). New module is properly wired into the `reporting` package without disturbing other builders.

- **V (8/8)** — APPROVE verdict justified. Slice B delivers every blueprint §3.B deliverable verbatim (advisor module, schema-version constant, 45 tests, slice-A archive). Every numbered rubric subset criterion is met. Anti-gaming guards are exercised DISTINCTLY per the §4 named list with parametrization providing per-element coverage rather than collapsing to representative cases. Full sweep passes; module imports clean; HF1 hard-stop zone untouched; no out-of-scope writes (only 4 files changed, all listed). StubAdvisor's load-bearing fallback role is preserved (always-available, never raises on well-formed context, deterministic, correlated outputs).

## Findings

- **LOW** — `_audit_four_question_gate` uses 4 sequential checks (missing → extra → non-bool → not-true) at `advisor_critique.py:444-466`. While each gets a distinct error message + test, a maintainer who supplies `{ "advisor_only": "yes" }` will get the "non-boolean" message (since "yes" is not a bool), which is the correct precedence — but the precedence is not documented. Suggested: docstring addition noting check order, or consolidate into a single audit pass. Not load-bearing for APPROVE.

- **LOW** — `AdvisorContext.extra: dict[str, Any]` (`advisor_critique.py:145-147`) is a forward-compat slot but is not currently exercised by any test. A scripted provider that reads `context.extra` cannot regress silently because there is no caller, but slice C (LLMAdvisor) will lean on this — recommend slice-C adds a test that asserts `extra` is passed through to `produce()` byte-identically. Not a slice-B blocker.

- **LOW** — `render_advisor_critique_json` (`advisor_critique.py:410-412`) emits sorted-keys 2-space-indent JSON, which is asserted via `json.loads` round-trip at `tests:176-190` but not pinned for byte-equality. Two consecutive envelopes with identical content (and `now_utc` pinned) will produce identical bytes — pinning that would harden the schema-stamping contract for slice D's HTTP route. Suggested for slice D carry-forward.

- **LOW** — Stub's "always emit mesh baseline" guard (`advisor_critique.py:313-319`) makes `mesh_quality_concerns` non-empty in all cases. The test `test_stub_advisor_high_trust_score_still_emits_mesh_baseline_prompt` (`tests:282-288`) asserts `len >= 1` but does NOT assert the BASELINE prompt text appears specifically (vs an accidentally fired trust-score concern). Hardening: assert "stress-gradient length scale" substring in the high-trust-score case. Minor.

## Cumulative slice B axes
M + T + C + A + E + V = 12 + 15 + 12 + 8 + 8 + 8 = **63 / 63**
