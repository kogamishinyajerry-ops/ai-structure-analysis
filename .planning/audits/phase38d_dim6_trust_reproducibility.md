# Phase 38 D — Dim 6 (Trust & reproducibility) · main-session synthesis

> Tier 1 / Tier 2 engineering candidate; not signed validation; not benchmark
> agreement. 绝对诚实客观. Rubric v2.0 Dim 6. Main-session synthesis (no dedicated
> sub-agent), per the Phase 37 D precedent (`phase37d_dim6_trust_reproducibility.md`).

## Verdict: **Dim 6 = 78 (+1 from Phase 37's 77)**

Unlike Dim 4/5, Phase 38 made **real trust/reproducibility code changes**, so a
fresh (modest) lift is warranted:
- **38 F** (`9439841`): tier-2 promotion now resolved at the API boundary —
  `candidate_cases.py` / `cohort_overview.py` call `_claim_tier` instead of
  hard-coding "Tier 1". Provenance that was a dead letter to the frontend is now
  surfaced (strengthens the 90-anchor provenance chain).
- **38 H** (`a7ec424`): a **drift-guard test** that fails when the frontend fallback
  registry diverges from `golden_samples/` on disk, + a committed provenance script
  `scripts/gen_fallback_candidate_registry.py`. The drift-guard is an
  automatic-cross-validation-pin-flavored artifact (99-anchor direction) and the
  script gives reproducible data provenance (no hand-fabrication; nafems-le10 stays
  Tier 1 — no over-claim).

## Evidence (anchor placement)
- **anchor 80 — fully met**: cohort snapshots (Phase 5) + reviewer signoffs
  (Phase 8-9) + cross-validation pinning (12 `cross_check` test files in
  `backend/tests/`).
- **anchor 90 — partial**: provenance routes present
  (`backend/app/api/routes/trust_score_provenance.py` + `_timeline` + `_alerts`) ✓;
  16 ADRs (`docs/adr/`, ≥10 ✓); trust score from `CASE_COMPLETENESS` +
  `trust_score.py` ✓ — BUT "full provenance chain visible at **every** UI step" is
  not literally every step.
- **anchor 95 — partial**: failed-attempt corpus indexed
  (`.planning/failed_attempts/INDEX.md`, **7 entries** with commit SHAs +
  preserved-evidence paths) ✓; BUT ADR cross-reference matrix **ABSENT** (no
  `.planning/adrs/CROSS_REFERENCE.md`) → "ADR cross-linked from components" not met.
- **anchor 99 — gaps**: NO `backend/app/services/audit_log.py` (audit-trail log);
  NO reproduce CLI (`cli/reproduce.py` / byte-match); corpus 7 < 10.

## Why +1 (78), not more
The 38 F / 38 H additions are real but **modest** against the wide-open 90/95/99
gates (provenance-at-every-step, ADR cross-ref matrix, audit-trail log, reproduce
CLI, corpus ≥10). +1 is the honest lift; deliberately not inflated. The bulk of
Dim 6's 99-journey (audit log + reproduce CLI + corpus completion) remains
Phase 40 / Phase 45 work.
