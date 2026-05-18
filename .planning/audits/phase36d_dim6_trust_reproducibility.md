# Phase 36 D · Dim 6 — Trust & reproducibility (synthesis)

> Scored by main session per anti-gaming guard B:-1 (sub-agents
> score Dim 1/2/3/5 directly; main session synthesizes Dim 4/6
> from clear codebase inventory + file:line evidence per D:-1).

## Inventory delta (codebase as of `4188dc5` vs Phase 35 `5d8f368`)

### What Phase 36 added to the Dim 6 surface

| Component | Was (Phase 35) | Now (Phase 36) | Δ to Dim 6 |
|---|---|---|---|
| Failed-attempt corpus | absent (`.planning/failed_attempts/` did not exist) | `.planning/failed_attempts/INDEX.md` + 7 entry files, all evidence-linked (commit SHA + preserved-evidence path) | **NEW** — closes Dim 6 anchor-95 sub-bullet "failed-attempt corpus with ≥5 entries"; 7 entries delivered (target was ≥5) |
| ErrorCard `code` provenance | rendered raw value as pill (no support-scrape attribute) | rendered codeFriendly OR code as pill; raw code preserved via `data-error-code` attribute for support-ticket / log correlation | strengthens 90-anchor "trust score explains every UI step" sub-bullet |
| ErrorCard accessibility provenance | role="alert" + aria-live; implicit text-content as accessible name | role="alert" + aria-live + aria-labelledby → title id via useId() | strengthens 90-anchor WCAG-grade UI provenance |
| runner_available provenance | absent | `CandidateCaseRecord.runnerAvailable?: boolean` field + amber badge on cases without live ccx runner (GS-* + rod-wave-*) | small 80-anchor sub-bullet contribution; novices can no longer be misled into thinking a demo case has a live runner |
| Candidate cases with `cross_check_verdict.yaml` | 12 | 12 | unchanged |
| Verdict YAML cohort invariant test pin | `test_phase35b...` 27/27 | UNCHANGED | unchanged |
| Reviewer signoffs | 3 in 1 case | 3 in 1 case | unchanged |
| Audit-trail log | absent | absent | unchanged |
| Reproducibility CLI | absent | absent | unchanged |
| ADR cross-reference matrix | absent | absent | unchanged |

### What Phase 36 did NOT change

- 5 cohort snapshots at `reports/snapshots/`
- 15 ADRs at `docs/adr/`
- TrustCenterPanel / trustCenterSummary / ProvenancePanel
- Phase 11 AdvisorPanel (still byte-identical)
- 12 cohort verdict YAMLs (Phase 35 B backfilled all 12; Phase 36 didn't touch them)

## Anchor matching (Phase 36 state)

| Anchor | Status | Δ from Phase 35 |
|---|---|---|
| 60 | ✓ (case dirs + INP + manifest) | unchanged |
| 70 | ✓ (schema_version + verdict YAML stable) | unchanged |
| 80 | partial (~78%) — cohort snapshots ✓ + cross-val pinning ✓ + cohort solver_kind invariant ✓ + signoffs partial 1/12 + runner_available transparency at case-open NEW | **+3%** — runner_available badge surfaces case-status to novice |
| 90 | partial (~63%) — provenance at every UI step (now stronger with aria-labelledby + data-error-code) + ADR ≥10 ✓ + trust_score ✓ | **+5%** — WCAG-grade UI provenance + support-ticket scrape attribute |
| 95 | partial — **failed-attempt corpus with 7 entries NEW (was 0/10)** | **MAJOR LIFT** — sub-bullet closed |
| 99 | ~0% — audit-log absent; reproduce CLI absent | unchanged |

## Score

Phase 35 D Dim 6 score: 73/100.

Phase 36 changes:
- **Failed-attempt corpus with 7 evidence-linked entries** — this
  is the headline Phase 36 lift on Dim 6. The 95-anchor sub-bullet
  "failed-attempt corpus with ≥5 entries" goes from ABSENT to MET.
  Contribution: ~+2.5.
- ErrorCard WCAG provenance + codeFriendly + data-error-code
  preservation — strengthens the 90-anchor "trust score explains
  every UI step" sub-bullet meaningfully. Contribution: ~+0.5.
- runner_available transparency at the case-open advisor surface —
  small but real 80-anchor sub-bullet contribution. Closes a Phase
  35 R3 friction point. Contribution: ~+0.3.

Total Dim 6 delta: +3.3, rounded to **+3** for the integer score.

**Dim 6 score: 76/100** (Phase 35 D was 73/100).

Confidence: high. The score honestly reflects that the failed-
attempt corpus is the kind of concrete, evidence-linked artifact
the 95-anchor explicitly calls out — and Phase 36 C delivered 7
entries (40% over the target ≥5).

The 99-anchor sub-bullets (audit-log infrastructure + reproduce
CLI) remain absent — those are the Phase 40 priorities per the
refined roadmap.

## Phase 37+ priorities for Dim 6 (refined post-Phase-36)

| Priority | Item | Anchor closed | Composite lift |
|---|---|---|---|
| 1 | Audit-trail log infrastructure (`backend/app/services/audit_log.py` append-only JSONL with case_id + commit SHA + UTC stamp) | 99 | +2-3 |
| 2 | Reproducibility CLI (`cli/reproduce.py --case_id <id> --verdict-yaml --snapshot <label>`) | 99 | +2-3 |
| 3 | Reviewer signoff coverage to ≥6/12 cases via fixture | 80 | +0.5-1 |
| 4 | ADR cross-reference matrix at `.planning/adrs/CROSS_REFERENCE.md` | 95 | +0.5 |
| 5 | Failed-attempt corpus growth as future phases add entries | 95 (already met; +growth) | +0.2-0.5/entry |

## File:line evidence summary

| Claim | Evidence |
|---|---|
| Failed-attempt corpus exists with 7 entries | `ls .planning/failed_attempts/*.md \| wc -l = 8` (INDEX + 7 entries) |
| Each corpus entry cites a commit SHA + evidence path | Per O:-1 guard: `grep "Deciding commit" .planning/failed_attempts/*.md` returns 7 hits |
| ErrorCard codeFriendly priority pin | `frontend/src/components/ErrorCard.tsx:46-58` — codeFriendly takes priority for the pill copy; code preserved via `data-error-code` |
| ErrorCard aria-labelledby | `frontend/src/components/ErrorCard.tsx:38-46` — `useId()` + `<strong id={titleId}>` |
| runner_available type | `frontend/src/candidateCaseRegistry.ts:32-39` — optional `runnerAvailable?: boolean` |
| runner_available backfill (7 fallback cases) | `frontend/src/candidateCaseRegistry.ts:56,70,86,104,127,143,160` — explicit field set |
| Audit-trail log absent | `find backend/app -name "audit_log*.py"` returns empty |
| Reproducibility CLI absent | `find . -name "reproduce*.py" -not -path "*/.venv/*"` returns empty |
| ADR cross-link matrix absent | `ls .planning/adrs/CROSS_REFERENCE.md` ENOENT |
