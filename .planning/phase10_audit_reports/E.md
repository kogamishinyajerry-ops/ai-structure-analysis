# Phase 10 E — TAA report

**Slice commit:** `9555ce6`
**Verdict:** APPROVE
**Test count:** 18 backend new + 9 frontend new
**Test pass:** 27 / 27; full sweep 1897 / 1897 + 8 skipped backend, 77 / 77 frontend
**Schema bump:** TRUST_SCORE_PROVENANCE_SCHEMA_VERSION 1.1.0 -> 1.2.0 (MINOR) — verified YES

## Per-axis evidence

- **M (12 / 12)** — `GENERATOR_NORMALIZATION_METHOD = "python-ast-dump-v1"` declared in `trust_score_provenance.py` and documented. Schema bump at `_schema_versions.py:264` to `"1.2.0"` with full Phase 8C/9B/10E bump history citing MINOR per bump policy and additive-only rationale. `ast.dump` flags explicit: `annotate_fields=True, include_attributes=False` with rationale on include_attributes. Pure helper `_canonical_python_sha` isolated with docstring explaining canonical form + parse-failure contract.

- **T (15 / 15)** — 18 backend tests in `tests/test_phase10_generator_canonicalization.py`, exceeding the 12 floor. Independent tests: whitespace, comment, docstring-differs, logic-change, parse-failure, empty input, walker canonical fields, broken-generator walker, non-generator None, missing-row None, walker-matches-helper, walker whitespace e2e, walker logic-change e2e, JSON envelope, forbidden-claim audit-still-fires. Each equivalence axis has its own dedicated test per anti-gaming guard T: -4.

- **C (12 / 12)** — Tier 1 disclaimer trio preserved. HF1 forbidden-zone untouched: `_ENVELOPE_FORBIDDEN_TOKENS` tuple and `_assert_no_overclaim` identical structure with `not <claim>` prefix-check. `test_forbidden_claim_audit_still_fires_after_canonical_fields` monkey-patches `CLAIM_IMPACT_DEFAULT` to inject `"validated physics"` without `not ` prefix and asserts `ValueError, match="forbidden positive claim"` — proving the audit survives the schema bump.

- **A (8 / 8)** — Parse-failure path: dedicated test + walker-side test — guard A: -3 satisfied. Vacuous-raw-SHA guard: asserts `hashlib.sha256(a).hexdigest() != hashlib.sha256(b).hexdigest()` — proving the equivalence is non-vacuous. No `time.sleep` / wall-clock dependence.

- **E (8 / 8)** — Backend full sweep: 1897 passed, 8 skipped. Frontend full sweep: 77/77 in 10 files. Forward-compat: `parseInput` uses `raw.sha256_normalized ?? null` — 1.1.0-era payload without keys yields parsed object with `null` fields. Existing schema-version assertions in 3 places bumped.

- **V (13 / 13)** — Slice 10-E delivers a load-bearing additive feature: AST-based canonical SHA on generator scripts that makes whitespace/comment-only edits no longer break provenance equivalence, while keeping docstrings + logic changes detectable. Implementation is small (~75 LOC + 25 LOC parser + 23 LOC panel), additive, contained, well-named. Bump policy followed scrupulously (MINOR + bump-history docstring entry). Test discipline is excellent: each equivalence axis isolated; parse-failure has its own test; vacuous-raw-SHA explicitly guarded; forbidden-claim audit re-verified post-bump. Forward-compat parser proven.

## Findings

- **LOW** — `_canonical_python_sha` catches `(SyntaxError, ValueError)` but the parse-failure test only exercises `SyntaxError`. A future malformed-bytes path hitting `ValueError` is uncovered. Not blocking — the catch is correct and the SyntaxError path is the dominant real-world failure.
- **LOW** — `test_walker_whitespace_equivalence_yields_same_normalized_sha` uses two different `case_id`s to seed independent generators. The test could equivalently re-snapshot one case with two body versions to be more direct, but the current form is correct.

## Cumulative slice E axes

M + T + C + A + E + V = 12 + 15 + 12 + 8 + 8 + 13 = **68 / 68**
