# Phase 34 D · Dim 6 — Trust & reproducibility (synthesis)

> Scored by main session per anti-gaming guard B:-1 (sub-agents
> score Dim 1/2/3/5 directly; main session synthesizes Dim 4/6
> from clear codebase inventory + file:line evidence per D:-1).

## Inventory delta (codebase as of `b78172a` vs Phase 33 `eb3f27a`)

### What Phase 34 added to Dim 6 surface

| Component | Was (Phase 33) | Now (Phase 34) | Δ to Dim 6 |
|---|---|---|---|
| Candidate cases with `cross_check_verdict.yaml` | 11 | 12 | +1 verdict YAML (Phase 34 C hertz-contact-candidate validated) |
| Verdict YAML schema versions in use | 1.0.0 / 1.3.0 mixed | 1.0.0 / 1.3.0 / **1.4.0** | additive schema bump (Phase 34 C solver_kind enum extension) |
| Solver kind enumeration | 5 (linear_static / modal / buckling / dynamic / heat_transfer_steady_state) | 6 (+ contact_pair_static) | additive enum |
| Verdict YAML schema heterogeneity (functional_tester latent issue) | 9 legacy at 1.0 without solver_kind / 3 at 1.3+ with solver_kind | 9 legacy at 1.0 / 4 at 1.3+ | one new case at 1.4 |
| Reviewer signoffs | 3 in 1 case | 3 in 1 case | unchanged |
| Failed-attempt corpus | 0 entries indexed at `.planning/failed_attempts/` | 0 entries | unchanged |
| Audit-trail log | absent | absent | unchanged |
| Reproducibility CLI | absent | absent | unchanged |
| ADR cross-reference matrix | absent | absent | unchanged |

### What Phase 34 did NOT change (Phase 33 inventory carries verbatim)

- 5 cohort snapshots at `reports/snapshots/` (Phase 5 lineage)
- 15 ADRs at `docs/adr/`
- schema_version usage across 5+ services
- `TrustCenterPanel.tsx` + `trustCenterSummary.ts` + `ProvenancePanel.tsx` (provenance UI surfaces)
- CASE_COMPLETENESS_SCHEMA + analysis-type-aware rubrics (Phase 11)

## Anchor matching (Phase 34 state)

| Anchor | Status | Δ from Phase 33 |
|---|---|---|
| 60 | ✓ (case dirs + INP + manifest) | unchanged |
| 70 | ✓ (schema_version + verdict YAML stable) | unchanged; schema bump 1.3→1.4 is additive, not breaking |
| 80 | partial (~70%) — cohort snapshots ✓ + cross-val pinning ✓ (now extended to 12 cases via Phase 34 C test pin) + signoffs partial 1/12 cases | tiny lift from 1/11 → 1/12 (negligible) |
| 90 | partial (~55%) — full provenance at every UI step partial; ADR ≥10 ✓; trust_score ✓ | unchanged |
| 95 | partial (~10%) — failed-attempt corpus 0/10; ADR cross-link matrix absent | unchanged |
| 99 | ~0% — audit-log absent; reproduce CLI absent | unchanged |

## Score

Phase 33 Dim 6 score: **72/100** with the following interpolation:
- 70 fully met → 70
- 80 partial 2/3 bullets met → +6 → 76 ceiling
- 90 anchor bullets contributing modestly: +1 from ADR-≥10 + trust-score sub-bullets

Phase 34 changes:
- +1 verdict YAML (12 instead of 11) — marginal sub-bullet contribution: ~+0.1
- Schema 1.4.0 additive bump — confirms schema rigor; ~+0.2 sub-bullet
- New Phase 34 C @requires_solver E2E test pin — strengthens cross-validation pinning evidence at the verdict YAML level: ~+0.4

Total Dim 6 delta: +0.7, rounded to **+0** for the integer score.

**Dim 6 score: 72/100** (unchanged from Phase 33)

Confidence: high. The score honestly reflects that Phase 34 didn't
invest in Dim 6 axis (no failed-attempt corpus, no audit-trail log,
no reproduce CLI, no ADR cross-link matrix, no broader signoff
coverage). The +0.7 sub-anchor lift is real but below the 1-point
rounding threshold for the dimensional integer score.

## Phase 35-40 priorities derived from this score

| Priority | Item | Anchor closed | Composite lift |
|---|---|---|---|
| 1 | Failed-attempt corpus at `.planning/failed_attempts/INDEX.md` with ≥5 initial entries (contact-pair recon, cylinder-pv BC, Richardson p≤0, C3D4 bias, ErrorCard rollback) | 95 | +1.5-2.5 (Phase 40 target) |
| 2 | Audit-trail log infrastructure (`backend/app/services/audit_log.py`) | 99 | +2-3 |
| 3 | Reproducibility CLI (`cli/reproduce.py`) | 99 | +2-3 |
| 4 | Reviewer signoff coverage to ≥6/12 cases via fixture | 80 | +0.5-1 |
| 5 | ADR cross-reference matrix at `.planning/adrs/CROSS_REFERENCE.md` | 95 | +0.5 |

## File:line evidence summary

| Claim | Evidence |
|---|---|
| 12 cross_check_verdict.yaml | `ls golden_samples/*-candidate/cross_check_verdict.yaml \| wc -l = 12` |
| Schema 1.4.0 additive bump | `golden_samples/hertz-contact-candidate/cross_check_verdict.yaml:75 → schema_version: "1.4.0"` |
| solver_kind enum extension | grep `solver_kind:` across verdict YAMLs returns 5 distinct + new `contact_pair_static` (6 total, 3 legacy cases at schema 1.0 lack the field) |
| Failed-attempt corpus absent | `ls .planning/failed_attempts/` ENOENT |
| Audit-trail log absent | `find backend/app -name "audit_log*.py"` returns empty |
| Reproducibility CLI absent | `find . -name "reproduce*.py" -not -path "*/.venv/*"` returns empty |
| ADR cross-link matrix absent | `ls .planning/adrs/CROSS_REFERENCE.md` ENOENT |
| 1/12 cases have signoffs | `find reports/signoffs -type f \| wc -l = 3 (all in 1 case)` |
| Cross-val pinning extended to contact-pair | `backend/tests/test_phase34c_contact_pair_runner.py:test_verdict_yaml_*` 5 pins + @requires_solver E2E |
