# Phase 35 D · Dim 6 — Trust & reproducibility (synthesis)

> Scored by main session per anti-gaming guard B:-1 (sub-agents
> score Dim 1/2/3/5 directly; main session synthesizes Dim 4/6
> from clear codebase inventory + file:line evidence per D:-1).

## Inventory delta (codebase as of `31856d1` vs Phase 34 `b78172a`)

### What Phase 35 added to the Dim 6 surface

| Component | Was (Phase 34) | Now (Phase 35) | Δ to Dim 6 |
|---|---|---|---|
| Candidate cases with `cross_check_verdict.yaml` | 12 | 12 | unchanged |
| Verdicts with `solver_kind:` field populated | 4 (Phase 34 C added hertz-contact; pre-existed on heat-transfer + cantilever-dynamic + half-implicitly elsewhere) | 12 | **+8 cases gained explicit solver_kind**; cohort-wide grep gap closed |
| Verdict YAML cohort invariant test pin | none cohort-wide | `test_phase35b_verdict_yaml_solver_kind_backfill.py` (27 pinned cases: 4 invariants + parametrized × 12 + schema-heterogeneity guard) | NEW |
| User-facing error code surface | absent | ErrorCard `code` field surfaced for UPLOAD + CASE-LOAD codepaths (`useUploadErrorRecovery.ts:114-176`) | NEW (provenance lift for support-ticket / log correlation) |
| Reviewer signoffs | 3 in 1 case | 3 in 1 case | unchanged |
| Failed-attempt corpus | 0 entries indexed at `.planning/failed_attempts/` | 0 entries | unchanged |
| Audit-trail log | absent | absent | unchanged |
| Reproducibility CLI | absent | absent | unchanged |
| ADR cross-reference matrix | absent | absent | unchanged |

### What Phase 35 did NOT change (Phase 34 inventory carries verbatim)

- 5 cohort snapshots at `reports/snapshots/`
- 15 ADRs at `docs/adr/`
- `TrustCenterPanel.tsx` + `trustCenterSummary.ts` + `ProvenancePanel.tsx`
- CASE_COMPLETENESS_SCHEMA + analysis-type-aware rubrics

## Anchor matching (Phase 35 state)

| Anchor | Status | Δ from Phase 34 |
|---|---|---|
| 60 | ✓ (case dirs + INP + manifest) | unchanged |
| 70 | ✓ (schema_version + verdict YAML stable; Phase 35 B preserved schema heterogeneity verbatim per L:-1 strict additive guard) | unchanged |
| 80 | partial (~75%) — cohort snapshots ✓ + cross-val pinning ✓ extended to 12 cases + cohort-wide solver_kind invariant pin ✓ + signoffs partial 1/12 cases | **+5%** — cohort-wide solver_kind invariant pin is new |
| 90 | partial (~58%) — full provenance at every UI step partial (ErrorCard code field new) + ADR ≥10 ✓ + trust_score ✓ | **+3%** — error-code surface adds support-ticket / log-correlation provenance |
| 95 | partial (~10%) — failed-attempt corpus 0/10; ADR cross-link matrix absent | unchanged |
| 99 | ~0% — audit-log absent; reproduce CLI absent | unchanged |

## Score

Phase 34 D Dim 6 score: **72/100** with the following interpolation:
- 70 fully met → 70
- 80 partial 2/3 bullets met → +6 → 76 ceiling
- 90 anchor bullets contributing modestly: +1 from ADR-≥10 + trust-score sub-bullets

Phase 35 changes:
- Cohort-wide `solver_kind` invariant pin (12/12 cases, 6-enum tag,
  distribution map, schema-heterogeneity guard). This is a real
  80-anchor lift on the cross-validation pinning + provenance
  sub-bullets: ~+0.6.
- Error-code surface for upload + case-load failures
  (UPLOAD / CASE-LOAD codes). Minor 90-anchor lift on the
  provenance sub-bullet ("trust score explains every UI step"):
  ~+0.3.
- Schema heterogeneity explicitly pinned by the new test —
  L:-1 strict-additive guard means future "harmonisation" PRs
  can't silently break the schema-1.0 reader contract. Small
  reproducibility lift: ~+0.2.

Total Dim 6 delta: +1.1, rounded to **+1** for the integer score.

**Dim 6 score: 73/100** (Phase 34 D was 72/100).

Confidence: high. The score honestly reflects that Phase 35 added
concrete provenance + reproducibility lifts (cohort invariant pin,
error code surface, schema heterogeneity declaration) without
investing in the larger 90/95/99-anchor gaps (failed-attempt
corpus, audit-trail log, reproduce CLI, ADR cross-link matrix).

## Phase 36+ priorities derived from this score

| Priority | Item | Anchor closed | Composite lift |
|---|---|---|---|
| 1 | Failed-attempt corpus at `.planning/failed_attempts/INDEX.md` with ≥5 initial entries (Hertz curvature deferral, plate-ss-shell pivot, Richardson p≤0, ErrorCard rollback, contact-pair geometry pivot) | 95 | +1.5-2.5 |
| 2 | Audit-trail log infrastructure (`backend/app/services/audit_log.py` with append-only JSONL) | 99 | +2-3 |
| 3 | Reproducibility CLI (`cli/reproduce.py` accepting `--case_id <id>` + `--verdict-yaml` + `--snapshot <label>`) | 99 | +2-3 |
| 4 | Reviewer signoff coverage to ≥6/12 cases via fixture | 80 | +0.5-1 |
| 5 | ADR cross-reference matrix at `.planning/adrs/CROSS_REFERENCE.md` | 95 | +0.5 |

## File:line evidence summary

| Claim | Evidence |
|---|---|
| 12 cross_check_verdict.yaml (unchanged from Phase 34) | `ls golden_samples/*-candidate/cross_check_verdict.yaml \| wc -l = 12` |
| 12/12 verdicts have solver_kind | Phase 35 B `python3` inventory output records `solver_kind ∈ {linear_static×5, modal×2, buckling×2, dynamic×1, heat_transfer_steady_state×1, contact_pair_static×1}` |
| Cohort invariant pin | `backend/tests/test_phase35b_verdict_yaml_solver_kind_backfill.py` 4 invariants + 12-case parametrized check + schema-heterogeneity preservation guard; 27/27 pass |
| Error-code surface | `frontend/src/state/useUploadErrorRecovery.ts:114-176` — `code: 'UPLOAD'` and `code: 'CASE-LOAD'` for the two upload + case-load paths |
| ErrorCard `code` rendering | `frontend/src/components/ErrorCard.tsx:48-52` — `data-testid="error-code"` monospace pill |
| Failed-attempt corpus absent | `ls .planning/failed_attempts/` ENOENT |
| Audit-trail log absent | `find backend/app -name "audit_log*.py"` returns empty |
| Reproducibility CLI absent | `find . -name "reproduce*.py" -not -path "*/.venv/*"` returns empty |
| ADR cross-link matrix absent | `ls .planning/adrs/CROSS_REFERENCE.md` ENOENT |
| 1/12 cases have signoffs (unchanged) | `find reports/signoffs -type f \| wc -l = 3 (all in 1 case)` |
| Cross-val pinning extended (Phase 34 C) | `backend/tests/test_phase34c_contact_pair_runner.py` 5 pins + @requires_solver E2E |
| Schema heterogeneity preserved (L:-1 strict additive) | `test_phase35b...py:test_schema_versions_preserved_for_existing_readers` — 12-case schema_version map (1.0.0/1.1.0/1.2.0/1.3.0/1.4.0) pinned |
