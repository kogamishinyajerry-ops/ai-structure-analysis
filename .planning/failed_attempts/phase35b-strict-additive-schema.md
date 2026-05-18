# phase35b-strict-additive-schema — Phase 35 B

## Trigger
Phase 35 B's blueprint called for both:
1. Backfill `solver_kind:` field to 9 legacy verdict YAMLs that
   lacked it (cohort-wide grep was returning 4/12 → 12/12 closure
   was the goal)
2. Bump `schema_version` 1.0.0 → 1.4.0 "additive minor" on each so
   the cohort's schema_version is homogeneous

On implementation, the second goal hit a wall: **Phase 21 / 29 / 30
backend tests pin EXACT schema_version labels per case**
(`test_phase21a_cantilever_kirsch_runners.py:225` asserts "1.0.0";
`test_phase29a_plate_ss_shell.py:163,263` assert "1.1.0";
`test_phase30a_cantilever_dynamic.py:187,300` assert "1.2.0";
etc.). Bumping schema_versions would force test-pin edits, which
the Phase 1-N "additive only; no test threshold edits" guard
treats as a code smell.

## Decision
Pivot to **strict-additive interpretation of L:-1**:
- Add `solver_kind:` field to all 9 missing verdicts
- KEEP each runner's existing schema_version verbatim
- Add a new test pin
  (`test_phase35b_verdict_yaml_solver_kind_backfill.py`) that
  asserts the cohort-wide invariant + parametrized per-case
  solver_kind presence + the schema-heterogeneity preservation
  itself (so a future "harmonisation" PR can't silently break the
  schema-1.0 reader contract)
- Update the blueprint inline to document the revised approach

## Evidence
- Deciding commit: `e0786ff` (Phase 35 B)
- Surviving cohort invariant test pin:
  `backend/tests/test_phase35b_verdict_yaml_solver_kind_backfill.py`
  (4 invariants + parametrized × 12 cases + schema heterogeneity
  guard; 27/27 pass)
- All 12 cohort verdicts now report solver_kind (verified via
  `python3 -c "import json,glob; [print(json.load(open(p))['solver_kind'])...]"`)
- Phase 21/29/30 schema_version pins remain UNCHANGED:
  232/232 pinning tests pass UNCHANGED after Phase 35 B landed

## Closure status
CLOSED in Phase 35 B. The cohort-grep gap is closed. The schema
heterogeneity remains an honest cohort artefact, now pinned by
the Phase 35 B test so it can't drift silently.

## Lessons
1. "Pure additive" has two readings: weak ("add a field, bump the
   version, readers ignore unknown versions") and strict ("add
   only the field, don't touch versions other consumers depend
   on"). When test pins exist on the version label itself, the
   strict reading is the safer choice.
2. Document the heterogeneity as an invariant pin. If "future me"
   wonders "why didn't we harmonise the schemas?", the test +
   this entry explain.
3. Honest revision of a blueprint at implementation time is a
   feature, not a bug. Phase 35 B's commit body documents the
   revision; the retro records it as the 5th honest pivot in
   FM-04a; this entry preserves the reasoning for future
   maintainers.
