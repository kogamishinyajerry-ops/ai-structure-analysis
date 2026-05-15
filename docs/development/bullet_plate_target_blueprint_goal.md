# Bullet-Plate Target Blueprint Goal

> Status: local blueprint memory and implementation goal.
> Claim tier: Tier 1 engineering candidate only.
> Evidence boundary: not signed validation; not benchmark agreement.
> Blueprint image: `docs/visualization/blueprints/bullet_plate_target_blueprint.png`.
> Evidence index: `docs/development/bullet_plate_target_blueprint_evidence_index.md`.

## Objective

Remember the generated bullet-plate target blueprint as the visual north star
for the next FM-04a-adjacent implementation slice, then surface it in the
Workbench as a Tier 1 engineering-candidate blueprint entry without changing
solver truth, golden samples, schemas, or external control-plane state.

## Scope

- Repository: `/Users/Zhuanz/20260408 AI StructureAnalysis`.
- Blueprint memory artifact:
  `docs/visualization/blueprints/bullet_plate_target_blueprint.png`.
- Planning artifact:
  `docs/development/bullet_plate_target_blueprint_goal.md`.
- Frontend-only entry point:
  `frontend/src/bulletPlateBlueprint.ts`,
  `frontend/src/components/BulletPlateBlueprintPanel.tsx`, and the narrow
  `frontend/src/App.tsx` integration.
- Test artifact:
  `frontend/test/bulletPlateBlueprint.test.ts`.

## Constraints

- Follow `AGENTS.md`, ADR-023, ADR-024 lite, `.planning/STATE.md`, and
  `.planning/FM-04B_READINESS.md`.
- Keep this slice local and repo-bound: no Linear mutation, Notion mutation,
  branch-protection change, merge, or signed-claim promotion.
- Do not modify `golden_samples/**`, solver decks, schemas, public APIs,
  persistent data formats, CI policy, or dependencies.
- Treat the blueprint as a target architecture and evidence map, not as proof
  that any physical validation has succeeded.
- Every user-facing claim must preserve Tier 1 wording: engineering candidate
  only; not signed validation; not benchmark agreement.

## Continuation Note

The first continuation slice binds the blueprint anchors to the existing local
`GS-102-transient-refined-cfl085-v365-bracket-20260512` OpenRadioss candidate
artifacts through `frontend/src/bulletPlateBlueprint.ts` and
`docs/development/bullet_plate_target_blueprint_evidence_index.md`. This binding
is still Tier 1 evidence only.

## Done when

1. `docs/visualization/blueprints/bullet_plate_target_blueprint.png` exists and
   preserves the generated visual blueprint.
2. `docs/development/bullet_plate_target_blueprint_goal.md` records this
   five-section goal and the blueprint evidence boundary.
3. `frontend/src/bulletPlateBlueprint.ts` exposes a typed blueprint contract
   with visual anchors, implementation slices, Tier 2 blockers, and no-overclaim
   wording.
4. `frontend/src/components/BulletPlateBlueprintPanel.tsx` renders the
   bullet-plate target blueprint panel with trajectory, plate mesh, deformation
   contour, boundary constraints, validation-data nodes, and Tier 1 guardrails.
5. `frontend/src/App.tsx` surfaces the panel and Trust Center summary without
   changing existing solver/report behavior.
6. `node --test --experimental-strip-types frontend/test/bulletPlateBlueprint.test.ts`
   exits 0.
7. `npm run build --prefix frontend` exits 0.

## Stop if

- A required change would touch `golden_samples/**`, solver decks, schemas,
  public APIs, persistent data formats, CI policy, or dependencies.
- The implementation would need to claim signed validation, benchmark agreement,
  or final physical completion from Tier 0/Tier 1 evidence.
- The current dirty branch contains conflicting edits in the same frontend files
  that cannot be integrated without overwriting existing user/Claude work.
- Frontend build or focused blueprint tests fail for reasons unrelated to this
  slice and cannot be isolated without broad refactoring.
