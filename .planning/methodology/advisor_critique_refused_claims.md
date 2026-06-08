# AdvisorCritique `refused_claims` surface — SSOT methodology

> **Tier 1 engineering candidate; not signed validation; not benchmark agreement.**
>
> **Scope:** the structured marker format + reviewer-audit semantics for the `refused_claims` field on the `AdvisorCritique` envelope.
>
> **Status:** Phase 13 A. Closes Phase 11 retrospective carry-forward §5.

## Why this surface exists

Before Phase 13 A, the advisor critique builder ran a single envelope-level audit (`_assert_no_overclaim`) that raised on the FIRST forbidden positive claim found in the rendered JSON. The behavior was correct but had two reviewer-audit gaps:

1. **No suppression history.** A reviewer auditing the LLM's safety posture could not see WHICH claims the system suppressed; the audit either passed (envelope rendered) or failed (envelope construction raised). The middle ground — "the LLM tried to assert X, we filtered it out" — was invisible.
2. **First-token-wins behavior.** If a single envelope tried to assert multiple distinct forbidden tokens, only the first one surfaced as a refusal reason; the others were never logged.

Phase 13 A introduces a **collection layer** that replaces forbidden-entry text with structured markers (`refused: <token>`) BEFORE envelope construction. The markers populate the new `refused_claims: tuple[str, ...]` envelope field; the original positive claim never reaches the rendered surface; the envelope-level audit remains in place as **defense in depth** (A:-3) for any metadata-path forbidden token the per-section filter does not traverse.

## Marker format SSOT

Pinned by the constant `REFUSED_CLAIM_MARKER_PREFIX` in `backend/app/services/reporting/advisor_critique.py`:

```python
REFUSED_CLAIM_MARKER_PREFIX = "refused: "
```

Each marker = `REFUSED_CLAIM_MARKER_PREFIX + <token>` where `<token>` is the verbatim string from `ADVISOR_FORBIDDEN_TOKENS`. Example markers:

| Forbidden token | Marker |
|---|---|
| `validated against` | `refused: validated against` |
| `perforation completed` | `refused: perforation completed` |
| `production ready` | `refused: production ready` |
| `signed off` | `refused: signed off` |

Rationale for the marker format:

* **Reviewer-readable.** A human auditing `refused_claims` sees the verbatim token; no need to cross-reference a code map.
* **Does NOT echo original content.** The marker names WHICH token tripped the audit, not WHAT context the LLM tried to assert. A future "what context did the LLM try" extension would be a separate MAJOR schema bump under a different field name (e.g., `refused_claims_with_context`).
* **One marker per refused entry.** If an entry contains MULTIPLE forbidden tokens, only the FIRST encountered token (in `ADVISOR_FORBIDDEN_TOKENS` declaration order) is recorded. This is intentional: the marker tracks *that the entry was refused*, not exhaustively *which tokens contributed*. A future extension may add a multi-token marker.

## Collection layer flow

`build_advisor_critique` calls `_filter_section` per content section (mesh / BC / failure-mode / load-case), each running `_audit_and_collect_refused` per entry:

```text
raw.mesh_quality_concerns ──→ _filter_section ──→ (mesh_clean, [markers...])
raw.boundary_condition_questions ──→ _filter_section ──→ (bc_clean, [markers...])
raw.failure_modes_to_consider ──→ _filter_section ──→ (fm_clean, [markers...])
raw.unhandled_load_cases ──→ _filter_section ──→ (load_clean, [markers...])
                                                          │
                                                          ▼
                                                  tuple(all_markers)
                                                          │
                                                          ▼
                                              envelope.refused_claims
```

Section ordering for marker collection: mesh → BC → failure-mode → load-case (matches the envelope's content-field ordering). Within a section, entry order is preserved.

## Back-compat contract

* **Pre-1.1.0 consumers** that don't read `refused_claims` continue to function — the field defaults to empty tuple, the four content sections render normally.
* **Pre-1.1.0 payloads** parsed by a Phase 13+ client: the frontend `parseAdvisorCritique` treats absent `refused_claims` as empty tuple. The frontend's "Refused LLM claims (N)" collapsible section renders only when N > 0.
* **A schema 1.0.0 producer + a schema 1.1.0 consumer**: the consumer sees `refused_claims === undefined`, parses it as empty tuple, and continues normally.
* **A schema 1.1.0 producer + a schema 1.0.0 consumer**: the consumer ignores the new field per standard JSON object semantics. The four content sections (which the 1.0.0 consumer reads) are CLEANER under 1.1.0 because forbidden entries have been filtered out; the consumer sees a strictly safer payload than under 1.0.0.

## Reviewer-audit semantics

A reviewer reading the advisor panel with `refused_claims.length > 0`:

1. **Sees the count.** "Refused LLM claims (3)" header makes suppression visible.
2. **Inspects markers.** Each marker is the verbatim refused token. The reviewer learns the LLM tried to assert "production ready" or "validated against" or similar — they DO NOT see what specific claim text the LLM constructed.
3. **Cross-references the suppression history with the case's verdict.** A high `refused_claims.length` may signal the LLM is being prompted toward overclaim, or that the model is drifting toward overconfidence — actionable telemetry without leaking the unsafe content.

The marker is NOT a "log entry" with a UTC timestamp. It is a **suppression record** scoped to the envelope's lifetime. A future extension may add timestamps, but the current schema deliberately keeps the marker minimal.

## What `refused_claims` does NOT do

* It does NOT replace `_assert_no_overclaim`. The envelope-level audit still runs and still raises if a positive claim reaches the rendered JSON via any path (metadata, debug fields, etc.) — defense in depth.
* It does NOT signal the LLM was "wrong". An LLM may legitimately emit text containing a forbidden token in a context that LOOKS overclaiming but is structurally legal (e.g., a long quote from a reviewer's prior note that names a forbidden phrase). The collection layer is intentionally conservative: it refuses any entry containing a forbidden token outside `not <claim>` disclaimer form, accepting some false-positive refusals as the cost of zero false-negative leaks.
* It does NOT route the refused content elsewhere. The refused entry is **discarded** — only the marker survives. The original text is not logged to disk, not sent to telemetry, not stored in the envelope's metadata. A reviewer who wants to debug "what did the LLM actually say" must re-run the advisor or inspect the upstream provider's local logs, not the envelope.
* It does NOT promote any case to Tier 2. Refused-claim presence does not change the Tier 1 disclaimer trio; the envelope still stamps `claim_tier="Tier 1 engineering candidate"` etc.

## Anti-gaming guards pinned by tests

* **M:-2** — marker prefix is a module-level constant (`REFUSED_CLAIM_MARKER_PREFIX`), typed, with a docstring naming this methodology doc.
* **T:-3** — boundary-pinned tests for every forbidden token round-trip through the collection layer.
* **T:-4** — distinct tests per content section (mesh / BC / FM / load-case) confirm filter applies uniformly.
* **T:-5** — **Phase 13 B tightening**: the first-token-wins contract is pinned by TWO tests in `tests/test_phase13_refused_claims.py` — one canonical case where declaration order and haystack order coincide, and one sharper case where the LATER-declared token appears FIRST in the haystack. The sharper case is the load-bearing pin: a silent reordering of `ADVISOR_FORBIDDEN_TOKENS` (which would NOT change observable behavior on the canonical case) WILL change observable behavior on the sharper case. (Closes slice-A TAA MEDIUM finding.)
* **C:-8** — Tier 1 disclaimer trio still asserted; rendered JSON still has zero forbidden tokens outside disclaimer form.
* **A:-2** — refused-claim collection is a reported list, not a raised exception (reviewer judges, advisor reports).
* **A:-3** — defense in depth: `_assert_no_overclaim` still trips on metadata-path forbidden tokens.
* **E:-2** — schema bump bump-history docstring + centralized SSOT pin in `tests/test_schema_versions_stamping.py`.
* **X:-2** — **Phase 13 B tightening**: frontend `_parseRefusedClaims` validates BOTH the marker prefix AND the suffix (close-set membership in `ADVISOR_FORBIDDEN_TOKENS`, case-folded). A tampered backend response such as `"refused: production ready for service deployment"` (a forbidden token + smuggled positive-claim copy) is now DISCARDED at parse time instead of rendering verbatim inside the suppression-history surface. Two new vitest cases (`AdvisorPanel.test.tsx`) pin the close-set contract: one with a smuggled-suffix payload, one with case-folded close-set members. (Closes slice-A TAA HIGH finding.)

## Reference

The Phase 13 retrospective at `.planning/retrospectives/fm04a_phase13_carry_forward_closure.md` will document the closure of Phase 11 retro §4–§5 + Phase 12 retro §3–§4 across slices A–E. Slice-B-specific items:

* The 7 permissive 4xx-range assertions tightened to exact-code pins across 5 test files (Phase 4 + Phase 5 + Phase 6 + Phase 7 + Phase 11 + Phase 4 reviewer-bundle + the API-endpoints generic file).
* The new meta-test `tests/test_phase13_status_code_discipline.py` (16 tests) that scans `tests/test_*.py` for permissive 4xx patterns and trips at the ceiling (0).
* The case-completeness signed-registry gate added at `backend/app/api/routes/case_completeness.py` (Phase 12 F honest-flag LOW finding).
