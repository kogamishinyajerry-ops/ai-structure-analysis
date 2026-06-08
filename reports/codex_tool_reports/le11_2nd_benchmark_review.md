# Codex Review — FM-05 2nd NAFEMS benchmark: LE11 thermal-stress — R0→R1 APPROVE

**Scope (risk-tier: golden_samples boundary + solver-truth (real ccx thermal-stress) + claim-tier
registry change + cross-file):** add the repo's SECOND NAFEMS public-benchmark agreement — LE11
"Solid Cylinder/Taper/Sphere - Temperature", a real ccx 2.23 thermo-elastic solve. σ_zz at point
A = (1,0,0), target −105 MPa.

**Reviewer:** `codex-relay-with gpt-5.5` (xhigh), static diff review, stdin-closed. Round cap = 3.

**Selection:** an `ultracode` adjudication workflow (3 lens-diverse proposers → adversarial
feasibility/honesty verifiers → synthesizer) picked LE11 over LE1: LE1 reuses LE10's exact elliptical
planform (near-duplicate), whereas LE11 is independent on every axis (thermal physics, no `*DLOAD`,
solid of revolution, new ccx keyword path, different stress component/location).

## Honesty contract upheld (machine-pinned)

- **Real solver, genuine agreement:** real ccx 2.23, quarter revolved C3D20, imposed temperature
  field T=√(x²+y²)+z (NO mechanical load). Convergence ladder (live, this host): 88→5632 el,
  σ_zz@A −102.49 → −104.47 → −105.12 → −105.40 MPa.
- **Anti-cherry-pick:** the CONVERGED finest (5632-el) value −105.398 MPa (+0.38%) is pinned canonical
  — NOT the +0.11% (2376-el) rung nearest −105. Stated explicitly in the verdict + convergence study.
- **Geometry from a free byte-oracle:** ported verbatim from the FeenoX `nafems-le11.geo`/`.fee`
  (FeenoX itself gets −105.04 MPa). Target −105 MPa triangulated from 7 FREE sources; TNSB Rev.3 NOT
  purchased (disclosed, same Tier-1/2 limitation as LE10).
- **ccx capability empirically verified on this binary** (not asserted): the thermal-stress keyword
  triple is exactly what `beamt.inp` + `lin_stat_initial_temp_condition.inp` ship in ccx 2.23.
- **Disclosed deltas:** E=210 GPa (NAFEMS canonical) vs FeenoX's 2.11e11 (0.5%, within tol); sign
  normalized to ccx tension-positive convention (unanimous compressive).
- **Claim tier:** Tier-1 candidate / public-benchmark agreement; item 7 (independent signoff) OPEN;
  **NOT signed validation**. Registered tier_1 baseline → overlay promotes to tier_2_validated on the
  PASS verdict; CANONICAL_TOLERANCES + CLAIM_BOUNDARY_OVERRIDES pinned.

## Review rounds

- **R0 — CHANGES_REQUIRED (3):** (P1) `CANONICAL_REFINE=2` contradicted the pinned canonical r=4 →
  default reproduction ran the wrong rung; (P2) convergence wording false (claimed target bracketed
  2376↔5632 el and implied |residual| monotone); (P3) `node_A()` returned the nearest node
  unconditionally (could silently validate a wrong point after a geometry regression). → all fixed.
- **R1 — APPROVE.** Verbatim: *"APPROVE. R0-1 closed: canonical refine is now 4. R0-2 closed: wording
  now distinguishes monotone stress magnitude from non-monotone residual magnitude. R0-3 closed:
  node_A() now gates nearest-node selection by TOL_PLANE."*

## Fixes applied (R1)

- `CANONICAL_REFINE = 4` → default `generator.py` reproduces the pinned −105.398 MPa (+0.38%).
- `node_A()` asserts the nearest node is within `TOL_PLANE` (1e-4 m) of (1,0,0), else `RuntimeError`.
- Convergence note (verdict + convergence_study) reworded: the stress MAGNITUDE is monotone, crosses
  the 105 MPa target between the 704- and 2376-el rungs, and the SIGNED residual changes sign so
  |residual| is NOT monotone (`_convergence_monotone_note` / `_trend_monotone_note` added).

## Files

- `golden_samples/nafems-le11-solid-cyl-temperature-candidate/data/generator.py` (NEW) — gmsh meridian
  (FeenoX port) + π/2 revolution → C3D20, node classify, per-node temperature field, ccx thermal deck,
  σ_zz frd parse, convergence ladder.
- `cross_check_verdict.yaml` / `convergence_study.json` / `published_reference.yaml` / `NOTES.md` /
  `artifact_manifest.json` (NEW) — the ADR-027 G-2 evidence packet (mirrors LE10's layout).
- `data/run_r4_C3D20/solve.inp` (NEW) — the canonical self-contained deck (sealed).
- `backend/app/services/reporting/_claim_tier.py` — LE11 registry + boundary-override entries.
- `backend/tests/test_phase29d_registry_tolerance_pin.py` — LE11 tolerance pin (3.0).

## Gates

- Default `generator.py` (r=4) = −105.398 MPa, +0.38%, node A=(1,0,0), converged. ruff clean
  (generator.py; backend/ + golden_samples/ are pyproject-excluded). residual-floor 17 (LE11 admitted,
  census 15) + reproduce-cli + le10-seal 37 + phase29d/phase27a/phase38f cohort 35 pass.
  validate_golden_samples exit 0; HF1 guard exit 0; `reproduce_case.py nafems-le11 --no-solve`
  REPRODUCED=True (sealed-hash integrity + recompute).

**Closure:** R1 **APPROVE** after 1 fix round. Local commit, `confidence: high`, no push.
