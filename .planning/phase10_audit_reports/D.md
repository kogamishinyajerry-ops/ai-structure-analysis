# Phase 10 D — TAA report

**Slice commit:** `2ba8829`
**Verdict:** APPROVE
**Test count:** 12
**Test pass:** 12 / 12
**Full-suite pass:** 1879 / 1879 + 8 skipped
**No schema bump confirmed:** YES (`_schema_versions.py` absent from diff; 5 files touched, all additive except `signoff_history.py` +18 LoC)

## Per-axis evidence

- **M (12 / 12)** — Named constants `RATE_LIMIT_MAX_REQUESTS=5` + `RATE_LIMIT_WINDOW_SECONDS=60`, both with docstring pinning to specific test names. Lazy eviction at L100-101. Epoch-seconds via `time.time()` — semantically UTC-equivalent + monotonic in practice. `_reset_state_for_tests()` exposed at module level, documented as "Phase 10 anti-gaming guard M: -3". Sliding-window logic correct: oldest-entry expiry drives `retry_after_seconds` with `max(1, ...)` floor.
- **T (15 / 15)** — 12 tests = blueprint expected. Constants pinned (×2); single-allowed; 5-sub-limit-allowed; 6th-refused-with-retry-after; reviewer-independence; case-independence; window-expiry-resets; reset-hook-clears; retry-after≥1; same-second-burst; route HTTP-429 surfaced. `time.sleep` count in test file = 0.
- **C (12 / 12)** — 429 carries both detail string AND `Retry-After` header. HF1 zone untouched (no `_schema_versions.py`, no `golden_samples/**`, no signed-registry writes). Detail string contains no forbidden Tier-1 wording.
- **A (8 / 8)** — Service-layer tests all pass `now=` synthetic clock. Only the single route test uses real wall clock — bounded by `RATE_LIMIT_WINDOW_SECONDS=60` and runs in <1s. Autouse fixtures: conftest + in-module both call `_reset_state_for_tests`.
- **E (8 / 8)** — Route → service stack verified: 6th POST returns 429 + detail + Retry-After. Gate ordering top-to-bottom: Content-Type 415 → case_id 422 → signed-registry 422 → JSON parse 422 → Pydantic 422 → verdict whitelist 422 → **rate-limit 429** → service. Rate-limit correctly placed AFTER verdict whitelist so rejected verdicts don't consume a slot.
- **V (13 / 13)** — APPROVE. No high or medium findings. Implementation matches blueprint §3.D + §4 verbatim; anti-gaming guards M:-2, M:-3, T:-2, C:-8 all evidenced.

## Findings

- **LOW (informational)** — Reviewer stripping is applied for the rate-limit key but raw `body.reviewer` is passed to `write_signoff_record`. Behaviorally fine because the service layer also strips/rejects whitespace-only. Not a defect.
- **LOW (style)** — `check_and_record` uses `time.time()` rather than `datetime.now(UTC).timestamp()`. Functionally identical on POSIX; rubric accepts either.

## Cumulative slice D axes

M + T + C + A + E + V = 12 + 15 + 12 + 8 + 8 + 13 = **68 / 68** (B + D omitted per slice scope).
