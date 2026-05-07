# ADR-024: Ballistic benchmark source selection — parameters-only (FM-04a Tier 1, lite)

- **Status:** Accepted (lite scope) by user directive 2026-05-07; implementation under user direct-execution authorization
- **Decider:** Claude Code CLI (Opus 4.7, 1M context), under user direct-execution authorization
- **Date:** 2026-05-07
- **Related Phase:** FM-04a (Tier 1 ballistic candidate full-flow milestone, planned in `.planning/ROADMAP.md` + STATE.md 2026-05-07)
- **Branch:** `claude/FM-04a-tier1-ballistic-candidate`
- **Companion ADRs:** ADR-011 (HF1 forbidden zones, golden-sample governance), ADR-021 (GS-100 smoke fixture), ADR-022 (GS-101-demo-unsigned), ADR-023 (lean validation workflow + Tier 0/1/2 boundaries)
- **Tier promise:** `tier-1-candidate-only; tier-2-promotion-deferred-to-fm04b`

---

## Context

`bullet-through-steel` ballistic perforation is the long-horizon target of the project. The work is split into two milestones (user directive 2026-05-07):

- **FM-04a — Tier 1 ballistic candidate full-flow.** Reproducible candidate run that exercises the OpenRadioss path under Johnson-Cook plasticity + Johnson-Cook damage + element-deletion erosion against a Børvik-style geometry. **No signed validation, no benchmark agreement.** This ADR (lite scope) belongs to FM-04a.
- **FM-04b — Tier 2 signed validation gate.** Public benchmark linkage, tolerance comparison, convergence study evidence, artifact hashes, and independent reviewer/signoff against a specific public benchmark case. **A separate, full-scope ADR-024 revision belongs to FM-04b** and is explicitly out of scope for this lite ADR.

ADR-023 §GS101 Application keeps `GS-101-demo-unsigned` Tier 0 demo only and reserves Tier 2 for a strict signed gate. ADR-011 §HF1 #7 keeps `golden_samples/<id>/` a forbidden zone — any new GS directory must be registered by an explicit ADR. ADR-021 / ADR-022 already registered GS-100 / GS-101 with explicit "not signed" wording.

We need a single, narrowly-scoped reference that says: "When we author the next candidate ballistic deck, where do the geometry, material, and initial-condition numbers come from, and what does that mean for claim tier?"

## Decision

For FM-04a Tier 1 candidate work, the ballistic deck (FM-04a P3, registering `golden_samples/GS-102-candidate/`) **cites Børvik 2002** as the parameter source for projectile/plate geometry, Johnson-Cook plasticity / damage parameters, and nominal projectile initial velocity. **No claim of benchmark agreement is permitted under this lite ADR.**

### Selected parameter source

- **Børvik, T.; Hopperstad, O. S.; Berstad, T.; Langseth, M. (2002).** *Perforation of 12 mm thick steel plates by 20 mm diameter projectiles with flat, hemispherical and conical noses. Part I: Experimental study; Part II: Numerical simulations.* International Journal of Impact Engineering, 27(1), pp. 19–60.
- Companion: **Børvik, T.; Hopperstad, O. S.; Berstad, T. (2003).** *On the influence of stress triaxiality and strain rate on the behaviour of a structural steel. Part II: Numerical study.* European Journal of Mechanics A/Solids, 22, pp. 15–32. — used only for additional parameter context; primary citation is Børvik 2002.

### Scope-locked ingredients (Tier 1 use only)

- **Geometry envelope:** 20 mm diameter projectile (hemispherical nose preferred; flat / conical reserved for FM-04b sensitivity), 12 mm thick mild steel plate (Weldox 460E equivalent).
- **Material model:** Johnson-Cook plasticity + Johnson-Cook damage parameters as published in Børvik 2002 Part II for Weldox 460E. Numerical values are **cited** in ADR-024 metadata + the deck top-line comment, not paraphrased into project-original wording. The deck must say "JC parameters cited from Børvik 2002 Part II Table 2" verbatim.
- **Initial condition:** projectile initial velocity selected from the Børvik 2002 Part I hemispherical-nose test set (e.g., V₀ ≈ 285 m/s as a non-marginal candidate point). FM-04a does **not** sweep V₀; sweeps are deferred to FM-04b.
- **Boundary condition:** plate fully clamped at the outer rim, single-projectile impact, normal incidence. No obliquity, no spaced plates, no layered targets in FM-04a.
- **Solver:** OpenRadioss explicit dynamics path (RFC-001 W7 OpenRadioss adapter), invoked via the existing `aeron.drivers` interface. CalculiX is not the solver for FM-04a.

### Citation compliance posture (lite)

- For FM-04a Tier 1 internal reproducibility, citing published JC parameter values from Børvik 2002 Part II Table 2 is treated as fair use. ADR-024 (lite) does **not** authorize republication of the full experimental table; only the parameter values used in the deck appear in repo, alongside an explicit pointer to the published table.
- A formal citation-compliance review is **deferred to ADR-024 (full)** in FM-04b. If FM-04b requires reproducing benchmark experimental data alongside candidate output (for tolerance comparison), that is a separate Tier 2 review and is **not authorized by this lite ADR**.

### Allowed wording

- "JC plasticity / damage parameters cited from Børvik 2002 Part II"
- "Geometry envelope follows Børvik 2002 Part I hemispherical-nose 20 mm × 12 mm plate"
- "Initial velocity V₀ = … m/s (Tier 1 candidate point sourced from Børvik 2002 Part I)"
- "Tier 1 engineering candidate; not signed validation; not benchmark agreement"

### Forbidden wording (per ADR-023 + this ADR)

- `validated against Børvik 2002`
- `benchmark agreement with Børvik 2002`
- `Børvik 2002 perforation completed`
- `Børvik signed validation`
- `signed GS-102` / `signed GS101` / `signed validation`
- `bullet-through-steel complete` / `steel perforation completed` / `bullet-through-steel simulation complete`
- Any wording that lets a reader infer Tier 2 or signed status from Tier 1 candidate output.

### Tier 2 boundary (deferred to FM-04b · ADR-024 full)

The following are explicitly **out of scope** for ADR-024 lite and remain Tier 2 blockers:

1. Selection and locking of a single benchmark case (e.g., one specific {nose shape, V₀, plate thickness} tuple from Børvik 2002 Part I).
2. Tolerance specification (proposed but not locked: ±10 % residual velocity vs Børvik 2002 published vR; final value set by FM-04b independent reviewer).
3. Uncertainty interval and measurement traceability for the experimental data.
4. Citation compliance review for republishing experimental data alongside candidate output.
5. Independent reviewer/signoff packet (ADR-011 + ADR-023 §Tier 2 strict gate).
6. Tier 2 status flip on `golden_samples/GS-102-candidate/expected_results.json`.
7. Notion / Linear external mirror updates carrying any Tier 2 promotion claim.

## Consequences

Positive:

- FM-04a P3 can author `golden_samples/GS-102-candidate/` with a clear, narrow citation scope and unambiguous claim-tier wording.
- FM-04a P4 OpenRadioss adapter extension can call out parameter sources cleanly in adapter docstrings + tests.
- FM-04b ADR-024 (full) has a stable starting point; it only needs to add benchmark locking + tolerance + citation compliance review + signoff.

Tradeoffs:

- Until FM-04b lands, every FM-04a artifact must say "Tier 1 candidate; cited parameters; not benchmark agreement" verbatim. Drift in this wording is treated as an ADR-023 forbidden-wording violation and blocks the affected commit.
- ADR-024 lite is intentionally narrower than the eventual ADR-024 full; the two will share an ID but the full version supersedes the lite version once FM-04b begins.

## Non-Goals

This ADR does **not**:

- promote any GS sample to Tier 2 or signed validation;
- authorize republication of Børvik 2002 experimental data tables;
- lock a specific benchmark case or tolerance for Tier 2 comparison;
- modify `golden_samples/**`, solver decks, schemas, CI policy, dependencies, branch protection, or Notion;
- authorize any wording listed under "Forbidden wording" above.

## References

- ADR-011 §HF1 #7 (golden-sample directory governance)
- ADR-021 (GS-100 smoke fixture)
- ADR-022 (GS-101-demo-unsigned)
- ADR-023 (lean validation workflow + Tier 0/1/2 boundaries; §GS101 Application; forbidden wording set)
- `.planning/STATE.md` 2026-05-07 entry for FM-04a milestone
- `reports/fm03_candidate_report_spine_source_map.md` §FM-04a P1 (the read side of the contract this ADR informs)
