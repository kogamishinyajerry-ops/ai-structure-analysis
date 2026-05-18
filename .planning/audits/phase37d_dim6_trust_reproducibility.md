# Phase 37 D · Dim 6 — Trust & reproducibility (synthesis)

> Scored by main session per anti-gaming guard B:-1.

## Inventory delta (codebase as of `f56f6ce` vs Phase 36 `de294c1`)

### What Phase 37 added to the Dim 6 surface

| Component | Was (Phase 36) | Now (Phase 37) | Δ to Dim 6 |
|---|---|---|---|
| WCAG audit doc | absent | `.planning/wcag_audit.md` 10 surfaces × 6 criteria explicit PASS/GAP/TODO/N/A grid | NEW (modest 90-anchor sub-bullet contribution; UI provenance gets a project-wide audit baseline) |
| 5th of 5 silent error paths closed (solver-start) | text-only `[ERROR]` log | styled ErrorCard + log trail + Retry; SOLVER-START code preserved via data-error-code; "Solver start" codeFriendly | strengthens 90-anchor "trust score explains every UI step" sub-bullet |
| Failed-attempt corpus | 7 entries (Phase 36 C) | 7 entries | unchanged |
| Candidate cases with `cross_check_verdict.yaml` | 12 | 12 | unchanged |
| Reviewer signoffs | 3 in 1 case | 3 in 1 case | unchanged |
| Audit-trail log | absent | absent | unchanged |
| Reproducibility CLI | absent | absent | unchanged |
| ADR cross-reference matrix | absent | absent | unchanged |

### What Phase 37 did NOT change

- All Phase 35 + Phase 36 Dim 6 artifacts carry verbatim
- Backend Trust services (`TrustCenterPanel`, `trustCenterSummary`,
  `ProvenancePanel`, `_claim_tier.py` overlay) — UNCHANGED
- Phase 35 B verdict YAML solver_kind invariant pin — UNCHANGED;
  27/27 pass

## Anchor matching (Phase 37 state)

| Anchor | Status | Δ from Phase 36 |
|---|---|---|
| 60 | ✓ | unchanged |
| 70 | ✓ | unchanged |
| 80 | partial (~78%) — cohort snapshots ✓ + cross-val pinning ✓ + cohort solver_kind invariant ✓ + signoffs partial 1/12 + runner_available transparency at case-open | unchanged |
| 90 | partial (~67%) — UI provenance stronger (now project-wide audit baseline + 5th error-path codeFriendly) + ADR ≥10 ✓ + trust_score ✓ | **+4%** — WCAG audit doc + 5/5 paths closure adds project-wide UI provenance |
| 95 | partial — failed-attempt corpus 7 entries ✓ (Phase 36 C) | unchanged |
| 99 | ~0% — audit-log absent; reproduce CLI absent | unchanged |

## Score

Phase 36 D Dim 6 score: 76/100.

Phase 37 changes:
- **WCAG audit doc as project-wide provenance artifact** — closes
  Phase 36 D friction point (b) ("no committed project-wide
  wcag_audit.md"). The doc is a real baseline; future phases that
  touch a surface must update its row. Contribution: ~+0.5.
- **5th of 5 silent error paths closed (solver-start)** — the
  novice now sees a styled ErrorCard surface for every fetch
  failure path in App.tsx. Contribution to the 90-anchor
  "trust score explains every UI step" sub-bullet: ~+0.3.
- **Honest counter-weight**: the WCAG audit doc's headline finding
  is itself a Dim 6 cost — 10/10 surfaces fail criterion 1.4.3
  (Contrast). The audit was published, but it documents a real
  gap. The Phase 37 lift on Dim 6 accounts for the doc being
  committed (+0.5) but doesn't pretend the contrast measurements
  are PASS yet.

Total Dim 6 delta: +0.8, rounded to **+1** for the integer score.

**Dim 6 score: 77/100** (Phase 36 D was 76/100).

Confidence: high. The score honestly reflects modest Phase 37 work
on Dim 6 — the failed-attempt corpus + cohort invariant pin (both
Phase 36) remain the load-bearing Dim 6 wins; Phase 37 added a
small but real WCAG audit baseline + 5th error-path closure.

The 99-anchor gaps (audit-trail log + reproduce CLI) remain
explicitly open — Phase 38+ priorities.

## Phase 38+ priorities for Dim 6

| Priority | Item | Anchor closed | Composite lift |
|---|---|---|---|
| 1 | Audit-trail log (`backend/app/services/audit_log.py` append-only JSONL) | 99 | +2-3 |
| 2 | Reproducibility CLI (`cli/reproduce.py --case_id <id>`) | 99 | +2-3 |
| 3 | Contrast measurement sweep + palette fix (closes 10 WCAG audit GAPs at once) | 90 | +1.5 |
| 4 | Reviewer signoff coverage to ≥6/12 cases via fixture | 80 | +0.5-1 |
| 5 | ADR cross-reference matrix at `.planning/adrs/CROSS_REFERENCE.md` | 95 | +0.5 |

## File:line evidence summary

| Claim | Evidence |
|---|---|
| WCAG audit doc exists | `ls .planning/wcag_audit.md` returns the file (10 surfaces × 6 criteria) |
| 5/5 silent error paths now closed | App.tsx wraps 5 paths through `useUploadErrorRecovery.withRecovery`: generateReportFromFile / selectCase (Phase 35 C) + downloadPDFReport / stopSolver (Phase 36 A) + runSolver (Phase 37 C). grep `withUploadRecovery(` in App.tsx returns 5 sites. |
| 5 option-template codes distinct | Phase 35 C + 36 A + 37 C tests pin UPLOAD / CASE-LOAD / PDF-EXPORT / STOP-REQUEST / SOLVER-START all distinct |
| WCAG audit headline 10/10 GAP on 1.4.3 | `.planning/wcag_audit.md` table "Summary" shows 0 PASS / 10 GAP on 1.4.3 |
| Failed-attempt corpus 7 entries (Phase 36 C carryover) | `ls .planning/failed_attempts/*.md \| wc -l` returns 8 (INDEX + 7 entries) |
| Audit-trail log absent | `find backend/app -name "audit_log*.py"` returns empty |
| Reproducibility CLI absent | `find . -name "reproduce*.py" -not -path "*/.venv/*"` returns empty |
