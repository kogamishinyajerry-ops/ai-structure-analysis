# plate-ss-shell-pivot — Phase 30 D

## Trigger
Phase 30 D's blueprint slot was a single simply-supported plate
case using C3D8 solid elements (`plate-simply-supported-candidate`).
The C3D8 solid mesh hit a **small-deflection ratio of 1.32%** — well
within Timoshenko thin-plate theory's small-deflection envelope, but
the observed center-deflection was visibly off the analytical value
by ~5.8% (within the 15% tolerance for PASS, but uncomfortable for
a "first plate case in the cohort" claim).

## Decision
Ship BOTH variants. The solid C3D8 case lands at `plate-simply-supported-candidate`
with PASS but a documented residual. A new shell variant
(`plate-ss-shell-candidate`) with S4 shell elements lands beside it
at a tighter residual (0.49% PASS) — Timoshenko shell theory is the
canonical mesh formulation for plate-bending cross-checks.

## Evidence
- Deciding commit (solid case): see git log Phase 30 D commits
  shipping `backend/app/services/cross_check/plate_ss_runner.py`
- Deciding commit (shell variant): see git log Phase 30 D commits
  shipping `backend/app/services/cross_check/plate_ss_shell_runner.py`
- Surviving verdict YAMLs:
  - `golden_samples/plate-simply-supported-candidate/cross_check_verdict.yaml`
    (schema 1.0.0, PASS at -5.79% residual)
  - `golden_samples/plate-ss-shell-candidate/cross_check_verdict.yaml`
    (schema 1.1.0, PASS at 0.49% residual)
- Both readable via the `_apply_verdict_overlay` reader at
  `backend/app/services/reporting/_claim_tier.py:184`

## Closure status
CLOSED in Phase 30 D. Both variants stayed in the cohort through
Phase 31-35; Phase 35 B backfilled both with `solver_kind: linear_static`.

## Lessons
1. C3D8 solid plate at thin-plate aspect ratio is not the canonical
   element for plate-bending cross-checks; S4 shell is. The solid
   case is still valuable as a "Timoshenko envelope check" but its
   residual will always lag the shell variant.
2. Shipping two variants beside each other lets the reviewer see
   the convergence story, not just one number — useful pattern for
   future cases where formulation choice is contested.
