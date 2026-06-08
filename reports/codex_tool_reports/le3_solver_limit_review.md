# Codex Review — FM-05 3rd benchmark attempt: NAFEMS LE3 hemisphere shell → SOLVER-LIMIT finding — R0 APPROVE

**Scope (risk-tier: golden_samples *-candidate write + solver-truth (real ccx shell solve)):** the
project's third NAFEMS public-benchmark attempt — LE3 "Hemispherical shell with point loads". Unlike
LE10/LE11 (clean solid agreements), ccx **does not agree**: it converges to ux@A = 0.2004 m, +8.3%
above the 0.185 m thin-shell reference. This change records the result HONESTLY as a Tier-0/1
solver-capability-limit study, deliberately EXCLUDED from the tier_2 validated cohort — NOT dressed up
as an agreement.

**Reviewer:** `codex-relay-with gpt-5.5` (xhigh), static review, stdin-closed. Round cap = 3.

## The finding (why ccx disagrees)

- ccx 2.23, quadratic S8R shell (expands to solid C3D20R), quarter hemisphere, converges monotonically
  to **0.2004 m** (na=8→40: 0.19562, 0.19976, 0.20020, 0.20033, 0.20037). The +8.3% residual GROWS
  with refinement and stabilises — a CONVERGED gap, not discretisation error.
- **Formulation-independent:** S8R (reduced-int) and S8 (full-int) both converge to ~0.2004 (S8 merely
  membrane-locks at coarse meshes then climbs). Linear S4 locks rigid (~4e-5 m).
- **Root cause:** ccx has no true thin-shell element — every shell expands to a solid brick. A point
  load on a solid shell adds a local through-thickness 3-D "dimple" absent from thin-shell theory; on a
  very thin (R/t=250) point-loaded shell that adds ~8% to the loaded-node displacement.
- **Independent bracket:** Altair OptiStruct CQUAD4 (true thin shell) converges DOWN to 0.185
  (normalized 0.9865→1.0016 at 4→64 per edge); ccx solid-shell converges UP to 0.2004. The two element
  FAMILIES bracket the answer — strong evidence the gap is a real thin-vs-solid divergence, not a bug.

## Honesty upheld (machine-pinned)

- **NOT an agreement, NOT tier_2, NOT signed.** Tagged Tier-0 software-path + documented-limitation.
- **Cohort-exclusion is structural** (Codex verified airtight): no `cross_check_verdict.yaml` (so the
  V2-0 residual-floor glob never admits it), LE3 absent from `CLAIM_TIER_REGISTRY` + `CANONICAL_TOLERANCES`,
  and `validate_golden_samples.py` ignores `*-candidate`. The exact-match registry↔verdict cohort test
  cannot pull LE3 in. Machine record lives in `solver_limit_finding.yaml` (verdict "DOCUMENTED_GAP").
- **Gaming explicitly rejected:** (a) cherry-picking a coarse mesh reading ~0.196 on the way up; (b)
  distributing the point load to soften the dimple. ccx's true converged number is recorded instead.
- Post-add: `pytest tests/test_v2_0_residual_floor.py` = 17 passed; phase29d = 18 passed (unchanged).

## Verdict — R0 APPROVE (no P1/P2/P3)

Verbatim: *"Verdict: APPROVE. No P1/P2/P3 findings. The exclusion looks airtight for the stated cohort
machinery ... Given the exact-match registry check, LE3 cannot silently enter the Tier 2 validated set
through the described V2-0 path. The physical framing is also sound enough for a Tier-0/1 solver-limit
finding. The mesh-converged ccx result, S8R/S8 convergence agreement, and independent thin-shell family
converging toward the NAFEMS value are legitimate evidence that this is a formulation/loaded-node
local-effect mismatch, not just a random modeling miss ... Residual risk: only external or future
automation that ignores the registry/verdict contract and classifies by directory name or prose could
confuse it. The docstring repeatedly says NOT agreement / NOT Tier 2, so I do not see a required change."*

## Files

- `golden_samples/nafems-le3-hemisphere-shell-candidate/data/generator.py` (NEW) — real ccx S8R/S6
  quarter-hemisphere solve, translational-only symmetry, coordinate-based frd read, `--ladder`.
- `golden_samples/nafems-le3-hemisphere-shell-candidate/convergence_study.json` (NEW) — ladder +
  OptiStruct thin-shell cross-check.
- `golden_samples/nafems-le3-hemisphere-shell-candidate/solver_limit_finding.yaml` (NEW) — machine
  record, non-verdict filename, verdict "DOCUMENTED_GAP", is_tier2_agreement false.
- `golden_samples/nafems-le3-hemisphere-shell-candidate/NOTES.md` (NEW) — honest finding writeup.

**Closure:** R0 **APPROVE**. Local commit, `confidence: high`, no push. The genuine 3rd public-benchmark
AGREEMENT is pursued separately in a ccx-strong physics (NAFEMS FV52 solid-plate free vibration).
