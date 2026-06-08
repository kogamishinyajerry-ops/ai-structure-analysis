# FM-04a Phase 13 — Slice C Audit Report

**Verdict: APPROVE — 63/63**

Commit: `710176a` — "FM-04a Phase 13 C: deeper-degradation 5th cohort case"
Scope: Close Phase 12 retro §4 carry-forward by shipping `cylinder-pv-collapsed-candidate` fixture engineered to land trust < 50 on snapshot 3, making the slice-D `regressed_count >= 1` blueprint assertion load-bearing on real fixture math.
Auditor posture: Tier 1 engineering candidate audit; adversarial; binding 6-axis sub-rubric (floors M≥10, T≥10, C≥10, A≥6, E≥7, V≥7; stop ≥60/63 with every axis at floor).

---

## Per-axis scoring

- **M 12/12** — `COLLAPSED_CASE_ID:str` and `COLLAPSED_TRUST_SCORE_CEILING:int = 50` are module-level + typed + documented in `tests/test_phase13_deeper_degradation_cohort.py:71-83`. The `fixture_authoring_notes` block in `expected_results.json:9-14` makes the synthetic construction (drop reproducibility / energy / completeness / convergence) explicit. Methodology SSOT (`.planning/methodology/cohort_bucket_thresholds.md`) gains a full Phase 13 C section with per-axis failure-mode table, load-bearing pin location, "what this fixture is NOT" disclaimer, and a "why both ceilings pinned in tandem" note.

- **T 15/15** — 13 tests ship (floor was ≥10). The load-bearing assertion is strictly `trust < COLLAPSED_TRUST_SCORE_CEILING` where the constant equals exactly 50 (`tests/test_phase13_deeper_degradation_cohort.py:390`). Per-axis weighted pins at lines 418 (`energy_audit_weighted == 0`), 421 (`convergence_weighted == 6`), 424 (`completeness_weighted < 30`) defend against silent rebalance lifting the case back to healthy via an unrelated axis. Anti-loosening guard at line 563 pins `COLLAPSED_TRUST_SCORE_CEILING == 50` AND its tandem with `WATCHING_TRUST_SCORE_MIN`.

- **C 12/12** — Tier 1 disclaimer trio (`claim_tier` / `claim_boundary` / `claim_impact`) appears on all 3 fixture files (`expected_results.json`, `data/ballistic_metrics.json`, `data/convergence_study.json`). `claim_impact` strings explicitly name "NOT a physical claim of any kind" / "NOT a physical claim" / fixture-purpose framing. Forbidden-token grep (`validated against | perforation completed | bullet-through-steel complete | validated physics | production ready | certified | approved for service | asme compliant | signed off`) returns **zero hits** across the collapsed fixture directory.

- **A 8/8** — `case_id = "cylinder-pv-collapsed-candidate"` ends in `-candidate` and does NOT match `^GS-\d{3}$` (asserted at `test_collapsed_case_id_is_candidate_form_not_signed_registry`). Failure modes ASSERTED on every PV-quality gate (`test_collapsed_ballistic_metrics_failing_every_pv_gate` checks `energy_audit.status == "unavailable"`, `ratio_P_m_over_S_m >= 1.0`, all 4 `max_rel_err_*_pct > 5.0`). Real-solver artifact guard (`test_collapsed_fixture_no_real_solver_artifacts`) excludes `.out / .frd / .odb / .vtu / .cgns`.

- **E 8/8** — Backend pytest stays exactly green: **2262 passed, 7 skipped** (slice-B baseline 2248+14 = 2262 ✓). HF1 hard-stop preserved: `git diff 9dede37..710176a -- 'scripts/hf1_path_guard.py' 'docs/adr/ADR-011*'` is **empty** (carve-out formalization is slice-D scope). HF1_GUARD_OVERRIDE used per-commit with explicit ADR-011 §HF1 Recovery rationale in the commit body — not a config-wide bypass.

- **V 8/8** — **LIVE ASGI PROBE CONFIRMS** the regressed bucket fires on real fixture math, not blueprint promises:
  - `cohort-executive-summary` → `status=200, regressed_count=1, healthy=6, watching=0`
  - Regressed set: `cylinder-pv-collapsed-candidate trust=45` (strictly < 50)
  - Trust-score-timeline snapshot 3: `trust_score=45, energy_audit_weighted=0, convergence_weighted=6, completeness_weighted=28` — matches the predicted decomposition from the methodology table.
  - `case_completeness._score_pv_quality_gates` (`backend/app/services/reporting/case_completeness.py:783-810`) explicitly routes `ratio_P_m_over_S_m >= 1.0 → points_awarded=0` for `allowable_margin`, confirming the fixture math is correct.
  - Slice-B LOW finding #1 closed inline: `test_phase6_endpoints_integration.py` now in the parametrize list at `tests/test_phase13_status_code_discipline.py:293`.

---

## Adversarial probes

1. **Live ASGI cohort-summary fire** (step 4 of the audit) — PASS. Seeded 5-fixture + 2-filler cohort across 3 snapshots, hit the cohort-executive-summary route through ASGITransport, confirmed `regressed_count=1` with collapsed case as the sole occupant. This is the load-bearing V-axis evidence.

2. **Scorer trace** (step 5) — PASS. Direct read of `case_completeness.py:783-810` confirms `ratio = 1.5 >= 1.0` → `evidence_status = "margin_failure"` → `points_awarded = 0`. The fixture math is anchored in real production code paths, not assumed.

3. **Forbidden-token grep** (step 6) — PASS. Zero hits across the collapsed fixture.

4. **HF1 untouched** (step 7) — PASS. Empty diff for `scripts/hf1_path_guard.py` and `docs/adr/ADR-011*`.

5. **Fixture-math sabotage** (step 8) — PARTIALLY DESTRUCTIVE BUT EXPECTED. Flipping `ratio_P_m_over_S_m = 1.5 → 0.5` made `test_collapsed_ballistic_metrics_failing_every_pv_gate` correctly FAIL (asserting `ratio >= 1.0`). The load-bearing `test_collapsed_candidate_snapshot3_trust_strictly_below_50` still PASSED because `WEIGHT_ALLOWABLE_MARGIN = 5` only contributes a small weighted delta (+2-3); other axes provide defense-in-depth (completeness/convergence/energy together push trust well below 50). This is a STRENGTH, not a gap — the per-axis test catches single-axis tampering, the trust-floor test catches multi-axis catastrophic regression. Fixture reverted cleanly via `git checkout --`.

6. **Slice-B LOW finding closure** (step 9) — PASS. `test_phase6_endpoints_integration.py` present in the parametrize list.

---

## Top findings

**None.** No HIGH, MEDIUM, or LOW findings against slice C. Every axis is at full marks and every adversarial probe held. The single observation worth noting (single-axis flip not tripping the trust-floor test) is by-design defense in depth, not a defect — the per-axis weighted test is the correct guard at that resolution.

---

## Engineering-coherence summary

Slice C closes Phase 12 retro §4 honestly: the deeper-degradation fixture is engineered with explicit per-axis failure modes (PV-gate fail / mesh unstable / energy unavailable / reproducibility dropped) that route through the real `case_completeness` scorer and `cohort_executive_summary` classifier to land snapshot 3 at trust=45 in the regressed bucket — verified live on the ASGI surface, not just in the diff math.

---

## Recommendation

**APPROVE for landing into the slice-D arc.** Slice C delivers exactly what Phase 12 retro §4 carry-forward demanded: the `regressed_count >= 1` blueprint promise is now load-bearing on real fixture math. The slice-D blueprint (carve-out formalization in ADR-011 + `scripts/hf1_path_guard.py`) can proceed on this foundation.
