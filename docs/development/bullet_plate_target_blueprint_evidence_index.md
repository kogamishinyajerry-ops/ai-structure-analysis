# Bullet-Plate Blueprint Evidence Index

> Status: Tier 1 engineering-candidate evidence index.
> Case: `GS-102-transient-refined-cfl085-v365-bracket-20260512`.
> Claim boundary: not signed validation; not benchmark agreement.

This page binds the blueprint anchors from
`docs/development/bullet_plate_target_blueprint_goal.md` to existing local
OpenRadioss candidate artifacts. It is an evidence map only. It does not promote
the case to Tier 2 and does not change solver truth, schemas, golden samples, or
external control-plane state.

## Anchor Evidence Map

| Blueprint anchor | Evidence path | Evidence role | Boundary |
|---|---|---|---|
| `trajectory` / 冲击路径 | `project_state/graph_executor/GS-102-transient-refined-cfl085-v365-bracket-20260512/ballistic/ballistic_metrics.json` | V0, candidate residual velocity, crossing evidence | Tier 1 metric extraction only |
| `plate-mesh` / 靶板网格 | `project_state/runs/GS-102-transient-refined-cfl085-v365-bracket-20260512/data/model_00_0000.rad` | Runtime deck provenance | Mesh adequacy still needs review |
| `boundary-constraints` / 边界约束 | `project_state/runs/GS-102-transient-refined-cfl085-v365-bracket-20260512/data/model_00_0000.rad` | Boundary/contact assumptions are inspectable in the run deck | Fixture equivalence is not proven |
| `deformation-contour` / 变形云图 | `project_state/visualizations/GS-102-transient-refined-cfl085-v365-bracket-20260512/result_mesh.json` | 150-frame Text-to-CAE playback export from real OpenRadioss A-frame output | Viewer evidence only |
| `deformation-contour` / 变形云图 | `project_state/graph_executor/GS-102-transient-refined-cfl085-v365-bracket-20260512/visualization/openradioss_animation_manifest.json` | Solver-emitted animation frame manifest | Visualization evidence only |
| `validation-data` / 验证数据 | `project_state/runs/GS-102-transient-refined-cfl085-v365-bracket-20260512/data/engine.log` | Normal termination, cycle count, deletion events | Solver termination evidence only |
| `validation-data` / 验证数据 | `reports/gs102_GS-102-transient-refined-cfl085-v365-bracket-20260512_candidate_run.md` | Candidate metrics, hashes, limitations, no-overclaim wording | Review packet ingredient |

## Still Missing

- Locked Tier 2 benchmark case.
- Locked tolerance and uncertainty interval.
- Citation-compliance review for experimental data comparison.
- Sealed artifact hash packet.
- Independent reviewer/signoff evidence.
- User milestone-experience acceptance.

The Workbench panel reads the same path map from
`frontend/src/bulletPlateBlueprint.ts`.
