# Phase 9 B — TAA report

**Slice author commit:** `e74790f`

**Verdict:** APPROVE
**Test count:** 16
**Test pass:** 16 / 16
**Phase 5/6/7/8 regression sweep:** 95 / 95
**Full-suite pass:** 1753 / 1753 (+8 skipped)

## Per-axis evidence

- **B (12 / 12)** — `TRUST_SCORE_PROVENANCE_SCHEMA_VERSION = "1.1.0"` lands with full bump history (closes pre-existing 1.0.0 docstring drift). `COHORT_SNAPSHOT_MANIFEST_SCHEMA_VERSION = "1.3.0"` lands with full bump history (Phase 9 B entry cites carry-forward §2). Both deltas MINOR-additive.
- **M (12 / 12)** — `PROVENANCE_INPUT_KINDS` tuple has 5 entries with `generator` last; `_PROVENANCE_KIND_EXTENSION` dict maps every tuple key 1:1. UTC-only timestamps preserved. No I/O leaks.
- **T (15 / 15)** — 16 `def test_` definitions (≥10 required). Independently rerun: 16/16 in 0.26s.
- **C (12 / 12)** — Forbidden-claim refusal pinned; envelope-narrowed 4-token audit list unchanged; Tier 1 disclaimer trio preserved; no envelope shape change beyond appending one input row.
- **A (8 / 8)** — Bump rationale blocks present; tuple SSOT pinned by test; non-UTF-8 generator handled via `decode(errors="replace")` + raw-byte SHA.
- **E (8 / 8)** — End-to-end pin: writer → walker → SHA over captured bytes (`test_provenance_emits_generator_row_present_true_with_sha`).
- **V (13 / 13)** — Full suite 1753 pass / 0 fail / 8 skip. Forward-compat probe verified actual unlink + rmdir before re-read.

## Findings

No HIGH, MEDIUM, or LOW findings. Slice is clean.

## Cumulative slice B axes

B + M + T + C + A + E + V = 12 + 12 + 15 + 12 + 8 + 8 + 13 = **80 / 80** (D + X omitted per blueprint)
