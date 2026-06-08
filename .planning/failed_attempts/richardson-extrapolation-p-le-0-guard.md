# richardson-extrapolation-p-le-0-guard — Phase 31 C

## Trigger
Phase 31 C shipped a Richardson extrapolation sweep that compares
observed convergence order `p` against the theoretical expectation
(p ≈ 2 for second-order elements; p ≈ 1 for first-order). At the
coarsest meshes in the sweep, `p` came out **negative** — a
mathematical artefact of the Richardson formula when the
"converged" value moves non-monotonically as the mesh refines.

The original "throw and fail" implementation interpreted negative
`p` as a runner bug and exited with a verbose backtrace. That made
the Richardson runner unusable on real first-attempt meshes.

## Decision
Replace the throw with a structured guard: when `p ≤ 0` is
observed, the runner records `richardson_anomaly` in the verdict
+ diagnoses the cause (non-monotone refinement / mesh-too-coarse
/ analytical reference questionable) rather than crashing. The
sweep continues, and finer-mesh `p` values still get computed +
reported.

## Evidence
- Deciding commit: see git log Phase 31 C commits shipping the
  `p_le_zero_guard` branch in
  `backend/app/services/cross_check/convergence_study.py`
- Surviving Richardson diagnosis pin tests:
  `backend/tests/test_phase31c_richardson.py`
- The guard is exercised on real cases — anomaly path tested in
  the Phase 31 C suite

## Closure status
CLOSED in Phase 31 C. The guard has stayed verbatim through Phase
32-35 with zero regressions.

## Lessons
1. "Throw on unexpected value" is the wrong instinct for numerical
   diagnostics — the user benefits more from a structured report of
   "here's what we saw + here's what it usually means" than from a
   stack trace.
2. The Richardson sweep is now robust to operator error (coarse
   mesh, wrong analytical reference). Future numerical pipelines
   should default to the same diagnostic-not-crash pattern.
