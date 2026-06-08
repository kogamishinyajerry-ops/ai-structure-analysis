# Codex relay review — ADR-029 P3 OR-1 (classifier deck-parse mislabel fix)

- **Date:** 2026-06-08
- **Relay:** `codex-relay-with gpt-5.5` (86gs, reasoning xhigh), **diff-only static review**
  ("STATIC REVIEW ONLY, no tools/no repo files") — governance-tier trigger: solver-truth path
  (`tools/calculix_driver.classify_solver_failure`). Small, well-enumerated diff; the diff-only
  prompt is canonical here (the repo-walking relay over-explores the large untracked working tree —
  the documented failure mode).
- **Scope reviewed:** the 4-file staged diff — `tools/calculix_driver.py`,
  `tests/test_calculix_driver.py`, `tests/test_aeron_calculix_backend.py`,
  `.planning/ADR029_P3_SOLVER_GATE_DESIGN.md`.

## The bug (OR-1, pre-existing)

`classify_solver_failure` checked SYNTAX → TIMESTEP → CONVERGENCE patterns, then a
`if returncode != 0: return SOLVER_CONVERGENCE` catch-all. A real ccx 2.x deck-parse error
(deck references an undefined node/element set) emits `*ERROR reading *SOLID SECTION: element set
Eall has not yet been defined` / `*ERROR in calinput`, rc=201 — matching NONE of the patterns, so it
fell to the catch-all and was mislabeled `SOLVER_CONVERGENCE`. Downstream,
`aeron/drivers/calculix_backend._failure_status_code` maps **only** `SOLVER_CONVERGENCE → DIVERGED`
(every other class → `SOLVER_ERROR`), so a deck error was cosmetically reported as a numerical
divergence that never happened (the solve never entered the equilibrium loop).

## The fix (smallest correct, safe-refactor enumerated)

Extend `SYNTAX_PATTERNS` with the three real ccx substrings (`*error reading`, `*error in calinput`,
`has not yet been defined`) → undefined-set deck error now classifies `SOLVER_SYNTAX` →
`SolveStatusCode.SOLVER_ERROR`, never `DIVERGED`. **No new FaultClass** introduced. Consumer
enumeration (verified safe): `agents/router.py` maps both SOLVER_SYNTAX and SOLVER_CONVERGENCE →
`"solver"` (no routing change); `agents/reviewer.py` retriable-set contains both (no behavior
change); the DIVERGED mapping keys only on SOLVER_CONVERGENCE; no existing test feeds the new
patterns. Regression tests added on both sides of the seam (classifier + aeron status mapping),
plus an over-reach guard (a genuine divergence still → SOLVER_CONVERGENCE → DIVERGED).

## R0 — APPROVE (1×P3, addressed)

- **VERDICT: APPROVE.** Codex confirmed: patterns are sound (`.lower()` + `in`-substring makes
  `*ERROR reading` / `*ERROR in calinput` match despite case and leading whitespace); SYNTAX-first
  ordering does not plausibly steal a real timestep/convergence line (these are deck/input parse
  markers); tests pin both sides (deck-parse ≠ convergence/DIVERGED; real divergence still →
  convergence/DIVERGED). No P1/P2.
- **P3 (honesty wording, addressed):** the code comment / test docstring said "verified on ccx 2.x",
  stronger than the diff alone proves (the tests feed a *captured* string; they do not run a live
  ccx solve). Tightened to "wording observed from real ccx 2.x output (fed here as a captured string,
  not a live solve)" — the *classification* is what the automated tests verify; the *source wording*
  is empirically observed. The design-doc OR-1 line already scoped its claim correctly ("Verified
  safe via safe-refactor consumer enumeration") and was left unchanged.

Round cap respected (R0 APPROVE + 1 honesty-wording tightening). Local commit, no push.
