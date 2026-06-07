# Codex Review — FM-05 3rd benchmark: rotating-disk centrifugal agreement (+ LE11 solver_kind fix) — R1→R3 APPROVE

**Scope (risk-tier: golden_samples *-candidate write + solver-truth (real ccx CENTRIF) + claim-tier
registry/tolerance change + cross-file cohort wiring):** the project's THIRD public-benchmark agreement
and FIRST centrifugal (rotational body-force) load. Real ccx 2.23 `*DLOAD CENTRIF`, C3D20 thin quarter
annulus, bore hoop stress σ_θ(a) vs the Timoshenko & Goodier plane-stress closed form. Also corrects a
pre-existing `test_phase35b` enum failure shipped by this session's LE11 commit.

**Reviewer:** `codex-relay-with gpt-5.5` (xhigh), static review, stdin-closed. Round cap = 3 (R1→R3).

## Why a rotating disk (the LE3/FV52 lesson)

Two prior attempts at a SHELL/PLATE 3rd benchmark (LE3, FV52) failed with a converged ~6-8% gap because
ccx solves full 3-D elasticity while those references assume a reduced displacement KINEMATICS
(thin-shell / Mindlin-plate). Generalisation: ccx cleanly matches CONTINUUM-ELASTICITY references
(LE10 +1.08%, LE11 +0.38%) and not reduced-kinematic ones. The rotating disk's reference is the exact
PLANE-STRESS elasticity stress field — a continuum-elasticity reduction (exact in the thin limit), which
a thin 3-D solid converges to. No reduced-kinematic gap.

## Result (Codex-verified arithmetic + physics)

- Analytic: σ_θ(a) = ρω²/4·[(3+ν)b² + (1-ν)a²] = 7850·100²/4·[3.3·1.0 + 0.7·0.04] = **65.312 MPa**.
- ccx C3D20 canonical nr=48: **65.353 MPa, +0.063%** (tol 1%). MONOTONE convergence CLOSING to ~0:
  65.591/65.428/65.353/65.323/65.308 MPa at nr=20/32/48/64/80 (resid +0.43% → −0.01%).
- σ_θ(r)/σ_r(r) profile along the +x radial line matches the closed form to ±0.1%; σ_r(a)=0.109≈0
  confirms the free inner edge. Codex: *"a legitimate agreement, not an obvious mesh-picked coincidence."*
- Modelling: plane stress via z=0 mid-plane symmetry + free top surface (Codex: *"does not impose global
  plane strain by itself"*). CENTRIF magnitude = ω² (ccx convention). Hoop = SYY at the +x bore node;
  frd reader stops at the `-3` terminator so the `-4 ERROR` block is not misparsed.

## LE11 solver_kind correction (documented fix to this session's own commit)

The LE11 verdict shipped `solver_kind="thermoelastic_linear_static"`, which is NOT in the 6-value
Phase-35B enum — so `backend/tests/test_phase35b...py` had been RED since the LE11 commit. Corrected to
`linear_static` (the enum records ANALYSIS type; the imposed temperature is a LOAD, preserved in
`cross_check_kind`/`load`). Same logic for the centrifugal disk. LE11 verdict + published_reference
re-sealed in LE11's manifest. Codex: *"linear_static is the right enum correction."*

## Rounds

- **R1 — CHANGES_REQUIRED (P2/P3 wording only; all substance validated):** (P2-1) artifacts overclaimed
  the reference as "3-D elasticity" — it is plane-stress elasticity; (P2-2) claim-tier inconsistent
  (generator "Tier-1" vs YAML "tier_2"); (P3-1) "no paywalled doc" while citing a textbook; (P3-2)
  "full field matches" overclaim (profile is one +x radial line).
- **R2 — CHANGES_REQUIRED:** P2-2 closed; P2-1/P3-1/P3-2 had STALE DUPLICATE occurrences in fields I
  missed (Codex read the files and found them). Fixed every occurrence across NOTES/verdict/study/manifest.
- **R3 — APPROVE.** Codex re-verified via `rg`: *"R2 P2-1, P3-1, and P3-2 are closed ... No remaining
  stale wording findings."* No physics/number issue in any pass.

## Cohort wiring (all green)

- `cross_check_verdict.yaml` verdict=PASS, residual_pct=0.063, observed_pa=65353300, analytical_pa=
  65312000, tolerance_pct=1.0. Registry baseline tier_1_candidate → overlay-promoted tier_2_validated;
  `CLAIM_BOUNDARY_OVERRIDES` + `CANONICAL_TOLERANCES`(1.0) added. tier_2 cohort 15→16.
- Gates: residual-floor 18 verdicts; phase29d 19; phase35b distribution linear_static:9/total 16.
  Full backend cohort/census/manifest sweep **254 passed, 0 failed**. Manifest hashes verified vs disk.

## Files

- `golden_samples/rotating-disk-centrifugal-candidate/data/generator.py` (NEW) — ccx C3D20 *DLOAD CENTRIF
  quarter-annulus solve, mid-plane symmetry, coordinate-based SYY frd read, `--ladder`/`--profile`.
- `golden_samples/rotating-disk-centrifugal-candidate/{cross_check_verdict.yaml, convergence_study.json,
  published_reference.yaml, NOTES.md, artifact_manifest.json, data/run_nr48_C3D20/solve.inp}` (NEW) — G-2 packet.
- `backend/app/services/reporting/_claim_tier.py` — registry + boundary-override entries.
- `backend/tests/test_phase29d_registry_tolerance_pin.py` — tolerance pin (1.0).
- `backend/tests/test_phase35b_verdict_yaml_solver_kind_backfill.py` — distribution linear_static 7→9 / total 16.
- `golden_samples/nafems-le11-solid-cyl-temperature-candidate/{cross_check_verdict.yaml,
  published_reference.yaml, artifact_manifest.json}` — solver_kind correction + reseal.

**Closure:** R3 **APPROVE** after 2 fix rounds (all P2/P3 wording; zero correctness findings). Local
commit, `confidence: high`, no push.
