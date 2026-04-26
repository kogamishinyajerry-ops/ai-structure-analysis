# Sprint 3 · Week 1 — Foundation Rebuild Handoff

**Branch:** `refactor/RFC-001-W1-foundation-rebuild` (8 commits ahead of `main`).
**Driver:** Claude Code takeover, 2026-04-26.
**RFC:** [`docs/RFC-001-strategic-pivot-and-mvp.md`](RFC-001-strategic-pivot-and-mvp.md) v1.0 FROZEN.

## 1. RFC summary (in one paragraph)

Strategic pivot from Sprint-1/2 "broad coverage" to a single MVP wedge:
**chemical / power design-institute static-strength report Copilot**
(equipment foundation, lifting lug, pressure-vessel local stress).
Architecture frozen at 4 layers — Layer-1 solver adapters, Layer-2
`ReaderHandle` Protocol over a closed `CanonicalField` vocabulary,
Layer-3 domain (stress derivatives / units / coordinates), Layer-4
report generation with mandatory evidence-ID citation (ADR-012). Six
weeks to technical foundation; 90 days to ≥5 signed reports from seed
users. Twelve ADRs codify non-negotiables (closed-set fields, no
Layer-1 derived quantities, no-LLM arithmetic, Aliyun LLM proxy only).

## 2. W1 buckets — done state

| Bucket | RFC § | Commits | Status |
|---|---|---|---|
| E delete (venv / cache) | §6.1 | (already in `.gitignore`) | ✅ |
| C deprecate (`result_parser`, `api/result`) | §6.1 | `0ccee3a` | ✅ |
| B freeze (Sprint-2 KB / viz / knowledge route → `_frozen/sprint2/`) | §6.1 | `4249bbe` | ✅ |
| D core types (Layer-2/3 enums + dataclasses + Protocols) | §4.3, §6.1 | `22b4af9`, `5c18c7a` | ✅ |
| A schema slim (`task_spec` / `report_spec` slimmed; `evidence_bundle` enriched with `field_metadata`, `derivation`, discriminated `data` union) | §6.2 | `57bf0dc` | ✅ |
| Empty placeholders (`adapters/`, `domain/`, `services/report/`) | §6.1 | (Bucket-D placeholders commit) | ✅ |

## 3. §6.5 done-gates verified

1. ✅ `from app.parsers.result_parser` import count: **0** (grep clean).
2. ✅ `core/types/` exports **6 enums + 5 dataclasses + 3 protocols**;
   `mypy --strict backend/app/core/types/` passes (8 files, 0 errors).
3. ⏸ Adapter cross-solver gate (W2-W6).
4. ⏸ Abaqus stub (W6).
5. ⏸ Windows .exe (W5).
6. ⏸ LLM proxy (W6).

## 4. Notion hub sync — BLOCKED

`mcp__claude_ai_Notion__authenticate` requires a one-shot OAuth handshake
that only the user can initiate. **Action for user:** run `/mcp` in Claude
Code and authorize the *claude.ai Notion* connector. Once authorized, the
hub sync will land:

- create RFC-001 page under the project root, embedding the markdown
- create the 5-bucket migration tracker (1 row per bucket with W-target)
- create the 6 done-gate checklist as a status board
- link existing Sprint-1/2 decision pages to the W1 commit shas above

## 5. W2 pointer

Per RFC §6.4, W2 lands the **CalculiX adapter rewrite** as the first
concrete `ReaderHandle`. Done criterion: `GS-001` end-to-end pipes
σ_max within 5 % of the analytical 7.5 MPa. Use the §4.4 field-mapping
table (`DISP / STRESS / TOSTRAIN / FORC`) and the existing Sprint-2
`parsers/frd_parser.py` as the implementation seed — that file is
**still live** (intentionally — only the result_parser / .frd-stub
went to Bucket C, the working FRD parser stays).

## 6. RFC-002 candidate observations

Logged here without acting on them, per takeover protocol:

- **Pre-existing Py 3.9 vs PEP-604 mismatch.** `routes/visualization.py:69`,
  `tests/test_well_harness_notion_sync.py` use 3.10+ syntax; the project
  declares `requires-python>=3.11`, but the local venv is 3.9. RFC-002
  candidate: lock the dev venv to 3.12 per `.python-version`.
- **`well_harness/` is wide.** Its consumers were Sprint-2-shaped and
  were patched to the slimmed TaskSpec API; full-freeze migration to
  `_frozen/sprint2/` (matching `knowledge_base.py` etc.) may be cleaner
  than per-file patching. RFC-002 candidate.
- **GS-001 fixture has unit mismatch** (test expected `-493 m`, gets
  `-0.493 m`; FP-001 already flagged). RFC-002 candidate: regenerate
  `gs001` per the GS contract before W2 cross-solver gate fires.
- **Original ANSYS adapter wrap** (`ansys-mapdl-reader`) does not cover
  `.rst` produced by ANSYS Mechanical APDL 2024+; verify version pin
  during W6.
