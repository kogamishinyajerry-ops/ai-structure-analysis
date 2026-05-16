# Phase 9 E — TAA report

**Slice author commit:** `6cfe21c`

**Verdict:** APPROVE
**Test count:** 13 vitest cases
**Test pass:** 13 / 13
**Full-suite vitest:** 46 / 46 across 7 files
**tsc -b clean:** YES
**No schema bump confirmed:** YES (`_schema_versions.py` not in diff)

## Per-axis evidence

- **M (12 / 12)** — Typed client structurally clean: `PROVENANCE_INPUT_KINDS` as-const 5-tuple, union type derived from tuple, type-predicate filtering. No `any` leaks. Single narrowing cast on `await res.json()`.
- **T (15 / 15)** — 13 `it()` definitions covering SSOT tuple pin, null/undefined parser rejects, unknown-kind fallback, shortSha, all-5-rows render, SHA chip, muted dash, header schema+formula+score, Tier 1 disclaimer trio, fetch failure, empty-param skip.
- **C (12 / 12)** — Tier 1 disclaimer trio rendered (TIER1_BANNER header + claimImpact footer). Defensive parser maps unknown → `'unknown'`; future Tier 2 verb cannot silently render.
- **X (12 / 12)** — App.tsx mount gate is `selectedCandidateCaseId && snapshotLabelA`; sole consumer of the endpoint; no duplicate fetch.
- **A (8 / 8)** — Defense in depth: App-level mount gate + in-component useEffect early-return on empty params (pinned by `fetchSpy` test).
- **E (8 / 8)** — All 5 input kinds including the Phase 9 B `generator` rendered + asserted.
- **V (13 / 13)** — Structurally clean, all rubric criteria pinned, integrates cleanly with Phase 8 C + Phase 9 B backend SSOT.

## Findings

- No HIGH / MEDIUM.
- **LOW (cosmetic)** — `Boolean(raw.present)` coerces non-boolean truthy values (e.g., string `"false"`) to `true`. Backend produces strict booleans so non-issue in practice.
- **LOW (cosmetic)** — `parseAxis` defaults `weighted` to 0 silently when missing. Acceptable since axes are not surfaced as a row count.

## Cumulative slice E axes

M + T + C + X + A + E + V = 12 + 15 + 12 + 12 + 8 + 8 + 13 = **80 / 80** (B + D omitted per slice scope)
