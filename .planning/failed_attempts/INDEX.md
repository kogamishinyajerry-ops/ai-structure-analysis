# FM-04a failed-attempt corpus · INDEX

> Tier 1 / Tier 2 engineering candidate; not signed validation; not
> benchmark agreement. Per 绝对诚实客观 contract carried verbatim
> from Phase 18-35.

This corpus seeds the Dim 6 anchor-95 sub-bullet "failed-attempt
corpus with ≥5 entries". Each entry documents a real pivot or
deferral that landed during the FM-04a journey — the deciding
commit, the analytical SSOT (or other evidence) preserved across
the pivot, and whether the deferral has since been closed or still
carries.

The corpus exists for two audiences:

1. **Future reviewers** who want to understand WHY the codebase
   shipped some surfaces in their current shape — not the
   sanitized "what" of git log, but the honest "what did we try
   first that didn't work, and why".
2. **Future maintainers** considering a similar pivot — each
   entry's "evidence" link lets them re-read the actual surviving
   artifacts (analytical formula files, blueprint docs, retro
   notes) and judge whether the original constraint still applies.

Anti-gaming guard **O:-1 (Phase 36)**: every entry MUST cite a
real commit SHA and a real preserved-evidence path. If evidence
was lost (rollback without artifact preservation), the entry says
so explicitly rather than fabricating a synthetic SSOT.

## Entries

| # | Slug | Pivot | Closure status |
|---|---|---|---|
| 1 | [plate-ss-shell-pivot](./plate-ss-shell-pivot.md) | Phase 30 D: solid plate → shell formulation pivot when C3D8 small-deflection ratio sat at 1.32% (within thin-plate theory but visibly off-converged) | CLOSED — Phase 30 D shipped both solid (`plate-simply-supported-candidate`) and shell (`plate-ss-shell-candidate`) variants |
| 2 | [heat-transfer-pivot-from-contact](./heat-transfer-pivot-from-contact.md) | Phase 31 A: contact mechanics first slot → heat transfer because contact requires *CONTACT PAIR + surface composition (Phase 31 budget < runtime) | CLOSED — Phase 34 C delivered the contact case via stacked-cube uniaxial geometry |
| 3 | [richardson-extrapolation-p-le-0-guard](./richardson-extrapolation-p-le-0-guard.md) | Phase 31 C: Richardson sweep at coarsest meshes hit `p ≤ 0` (negative observed order); originally a "throw and fail" but pivoted to a guard that records the diagnosis | CLOSED — Phase 31 C ships the `p ≤ 0 → richardson_anomaly` guard with diagnostic verdict |
| 4 | [hertz-contact-analytical-only-deferral](./hertz-contact-analytical-only-deferral.md) | Phase 33 D: live ccx Hertz curvature deferred to Phase 34 because cylindrical hex meshing needs gmsh tetmesh + peak pressure exceeded S355 yield at session-budget geometry | CLOSED — Phase 33 D analytical SSOT + Phase 34 C stacked-cube uniaxial together cover the contact mechanics use case at tier_2_validated |
| 5 | [contact-pair-stacked-cube-pivot](./contact-pair-stacked-cube-pivot.md) | Phase 34 C: original blueprint called for cylinder-on-block Hertz; pivoted to stacked-cube uniaxial when cylindrical hex meshing exceeded scope and Hertz peak pressure exceeded yield | CLOSED — Phase 34 C ships `hertz-contact-candidate` with stacked-cube uniaxial geometry, live ccx PASS at -6.823% residual |
| 6 | [phase35b-strict-additive-schema](./phase35b-strict-additive-schema.md) | Phase 35 B: blueprint called for schema_version 1.0→1.4 bump alongside solver_kind backfill; pivoted to strict-additive (preserve schema_versions) when Phase 21/29/30 backend tests pinned exact schema labels | CLOSED — Phase 35 B ships solver_kind backfill at the heterogeneous existing schema_versions; cohort-grep gap closed; 232/232 Phase 18-31 pinning tests pass UNCHANGED |
| 7 | [phase33d-errorcard-app-tsx-loc-rollback](./phase33d-errorcard-app-tsx-loc-rollback.md) | Phase 33 D: attempted ErrorCard wiring directly in App.tsx added ~71 LOC and tripped the Phase 29 B <1500 regression pin; rolled back | CLOSED — Phase 35 C extracted state into `useUploadErrorRecovery` hook; App.tsx growth shrank to +11 LOC; pin holds |

## How to add a new entry

When a future phase commits a pivot or deferral worth recording:

1. Pick a kebab-case slug describing the pivot's domain
   (`<area>-<reason>` or `<phase-id>-<pivot-name>`)
2. Create `.planning/failed_attempts/<slug>.md` using the template
   below
3. Add a one-line row to the INDEX table here
4. Cite the deciding commit SHA + at least one surviving evidence
   path (analytical SSOT / blueprint doc / retro section)

## Entry template

```markdown
# <Pivot name>

## Trigger
What forced the pivot. Cite the original goal + the blocker.

## Decision
What was decided instead. One paragraph.

## Evidence
- Deciding commit: `<SHA>` (one-line gist)
- Preserved analytical SSOT or alternative artifact:
  `<path>`
- Blueprint section that documents the original goal:
  `<path>`
- Retro section that documents the decision:
  `<path>`

## Closure status
- CLOSED in Phase X — link to closing commit / artifact
- OR: still deferred; next opportunity in Phase Y; what would
  trigger closure
- OR: lost-work record — evidence not preserved, documented here
  for audit but not re-runnable

## Lessons
1–3 bullets on what we learned that future maintainers should
know before attempting a similar pivot.
```
