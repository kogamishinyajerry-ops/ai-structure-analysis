# GS-102-candidate/data/ — placeholder (FM-04a P3 closeout)

> Tier 1 engineering candidate; not signed validation; not benchmark agreement.

This directory is the target location for the OpenRadioss explicit-dynamics
deck files authored in **FM-04a P4** (Johnson-Cook plasticity + JC damage +
element-deletion erosion path through the existing `aeron.drivers` OpenRadioss
adapter). It is intentionally empty at FM-04a P3 closeout because:

1. ADR-011 §HF1 #7 keeps `golden_samples/<id>/` a hard-stop zone. P3 establishes
   the directory + claim-tier discipline + spine fallback metadata under ADR-024
   (lite) cover, then stops. Authoring deck content requires the OpenRadioss
   adapter extension landed in P4 — modifying `agents/solver.py` triggers the
   ADR-011 §HF1 override path documented per the ENG-36 precedent.
2. FM-04a is staged so each phase is independently reviewable. Putting deck
   content in P3 would couple it to the adapter wiring it depends on.
3. No deck content here means no risk of an accidental Tier 2 implication on
   the contents of this directory before the adapter is even wired.

## Expected layout once P4 lands

- `model_00_0000.rad` — OpenRadioss starter deck citing Børvik 2002 hemispherical
  Ø20mm projectile / 12mm Weldox 460E plate geometry (parameters only).
- `model_00_0001.rad` — engine deck with `/MAT/PLAS_JOHNS/...` + `/FAIL/JOHNSON/...`
  + element-deletion configuration. JC parameter values cited from Børvik 2002
  Part II Table 2; full table is **not** republished in repo (ADR-024 lite).
- `attribution.md` — explicit attribution + license posture for any upstream
  starter material (mirrors GS-101-demo-unsigned attribution discipline).

## Forbidden content (every authoring round)

- No claim of benchmark agreement, signed validation, validated physics,
  or Tier 2 promotion in any deck comment.
- No republication of Børvik 2002 experimental tables. Cite parameter values
  only.
- No copy of any deck content from a non-permissively-licensed source without an
  attribution.md cover.

## Reference

- ADR-024 (lite) — `docs/adr/ADR-024-ballistic-benchmark-source-selection.md`
- README at the parent `GS-102-candidate/` directory for the full claim-tier
  posture.
