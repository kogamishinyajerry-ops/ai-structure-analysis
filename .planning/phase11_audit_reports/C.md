# Phase 11 C — TAA report

**Slice commit:** `5b6771b`
**Verdict:** APPROVE
**Test count:** 42 (33 test functions; parametrize expands `forbidden×9` adding 8 over function count)
**Test pass:** 42/42; full sweep 2034 passed + 7 skipped (matches commit claim byte-for-byte; +42 over slice-B's 1992+7)

## Per-axis evidence

- **M (12/12)** — Every new SSOT is module-level with explicit type pin and bump-history docstring: `LLM_RESPONSE_KEYS: tuple[str, ...]` at `advisor_critique.py:511-517` with docstring naming T:-4, `MAX_ITEMS_PER_AXIS = 12` at `:529`, `MAX_CHARS_PER_ITEM = 600` at `:534`, `ENV_VAR_BACKEND = "AIFEA_ADVISOR_BACKEND"` and `ENV_VAR_ANTHROPIC_API_KEY = "ANTHROPIC_API_KEY"` at `:751-752` with "Pinned by" comment. `test_llm_response_keys_closed_set_pinned` (`tests:112-121`) pins identity AND value. `test_max_items_and_chars_are_named_constants` (`tests:124-128`) pins both caps. No magic numbers in parser or factory: parser uses `LLM_RESPONSE_KEYS[:4]` (tuple slice over the SSOT, not a literal `4`) and `MAX_ITEMS_PER_AXIS` / `MAX_CHARS_PER_ITEM` by identifier; factory uses `ENV_VAR_*` by identifier only.

- **T (15/15)** — Comfortably over floor (≥10). All §3.C-required categories present and distinct: malformed JSON → stub (`tests:270-285`); exception → stub (`tests:287-305`); env-var absent → factory None (`tests:471-474`) plus 4 sibling None paths; per-token forbidden refusal parametrized × 9 (`tests:447-463`); 4-Q gate missing key → envelope refused (`tests:433-444`); 4-Q gate False answer → envelope refused (`tests:410-430`). **T:-4 distinct shape-drift guard**: 6 distinct shape-drift paths in `_parse_llm_response` each have a dedicated LLMAdvisor-routed test asserting status="stub" + degrade_reason populated (top-level-not-object / missing key / extra key / non-list axis / non-string entry / non-dict gate). Plus 3 direct `_parse_llm_response` tests (`:552-573`) pinning the parser independently. Truncation per-axis cap + per-item char cap both pinned to constants. Context-extra carry-forward test closes slice-B LOW finding §2.

- **C (12/12)** — Every degrade path lands on `advisor_status == "stub"` (NOT "online"). The downgrade branch at `advisor_critique.py:393-394` is exercised by all 8 stub-fallback tests. The 8 tests assert distinctive substrings to prevent a single catch-all error string from passing all eight. Tier 1 disclaimer trio in LLM prompt verified by `test_llm_prompt_contains_tier1_disclaimer_trio` (`tests:147-154`). Envelope-level audits (4-Q gate + forbidden-claim) still fire. Forbidden-token list and gate keys rendered verbatim into prompt and pinned by tests.

- **A (8/8)** — All four named guards exercised distinctly:
  - **A:-4 (env-var seam, no real network)**: 5 None-returning env paths, `_default_llm_factory` is hermetic (accepts `environ` dict for injection at `:757-758`). Module-wide `grep` for `httpx|requests|anthropic|urllib|socket|aiohttp` returns ONLY docstring text references — no imports, no real client. Tests inject callables only.
  - **A:-5 (unwired placeholder → stub at produce, NOT 5xx)**: `_default_llm_factory` returns LLMAdvisor wired against `_placeholder_anthropic_call` that raises `NotImplementedError` (`:787-793`); `test_default_llm_factory_placeholder_falls_back_to_stub_at_produce_time` (`tests:507-523`) asserts envelope.advisor_status == "stub" + degrade_reason contains "NotImplementedError" + advisor_backend == "llm-advisor-anthropic-unwired". No raise propagates to the caller.
  - **T:-4 + T:-5**: enumerated above.

- **E (8/8)** — Full sweep `2034 passed, 7 skipped, 3 warnings in 21.18s` — matches commit message claim exactly. Module imports clean for all 12 newly-exported symbols. No regressions in existing slice-B 45-test surface, schema-version stamping, endpoint surfaces.

- **V (8/8)** — APPROVE. Slice C delivers every blueprint §3.C deliverable verbatim. Anti-gaming guards exercised DISTINCTLY rather than collapsed to representative cases. HF1 hard-stop zone untouched, no out-of-scope writes — only 3 files changed.

## Findings

- **LOW** — `LLMAdvisor.is_available()` returns `self._llm_call is not None` (`advisor_critique.py:577`). Because `__init__` does not validate `llm_call` at construction, a caller passing `LLMAdvisor(None)` would construct successfully and `is_available()` would return `False`, routing through the `advisor_status="offline"` branch — but `produce()` would then raise `TypeError`. Current call sites never pass None, so unreachable in practice; a `__post_init__`-style guard or `Callable` runtime check would harden the seam. Slice-D carry-forward.

- **LOW** — `_parse_llm_response` uses `LLM_RESPONSE_KEYS[:4]` (`advisor_critique.py:710`) — relies on the tuple ordering being stable. The SSOT pin test pins the exact order, so a re-order would loudly break the pin test. Acceptable, but a named constant `LLM_LIST_AXES = LLM_RESPONSE_KEYS[:4]` (or splitting into `LLM_LIST_AXIS_KEYS + LLM_GATE_KEY`) would surface the contract by identifier rather than slice index. Minor.

- **LOW** — `test_llm_advisor_passes_context_extra_through_to_prompt` (`tests:239-262`) builds an `_capturing_call` but the assertion only checks `"GS-PV-cyl-candidate" in captured_prompts[0]` — i.e., it verifies the canonical fields are rendered, not that `extra` itself is passed through. The docstring acknowledges this is the current contract; suggested rename to `test_llm_advisor_renders_canonical_context_fields_to_prompt`. Not blocking.

## Cumulative slice C axes
M + T + C + A + E + V = 12 + 15 + 12 + 8 + 8 + 8 = **63 / 63**
