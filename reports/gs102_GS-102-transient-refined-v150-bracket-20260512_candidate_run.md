# GS-102 transient candidate run - GS-102-transient-refined-v150-bracket-20260512

> Status: Tier 1 engineering candidate.
> Solver: OpenRadioss via `openradioss-local-arm64:latest`.
> Claim boundary: not signed validation; not benchmark agreement.

## Purpose

Run a real OpenRadioss transient structural candidate for projectile impact on
a steel plate. Runtime decks and solver outputs live under `project_state/`.
This script refuses runtime writes inside `golden_samples/**`.

## Candidate setup

- Source deck directory: `golden_samples/GS-102-refined-candidate/data`
- Runtime deck directory: `project_state/runs/GS-102-transient-refined-v150-bracket-20260512/data`
- Projectile initial velocity: `150 m/s`
- Projectile mass used by metrics: `0.005024 kg`
- Projectile node id range used by metrics: `1..27`

## Solver evidence

- Starter errors / warnings: `0` / `6`
- Engine normal termination: `True`
- Engine cycle count: `3459`
- Animation frame count: `150`
- Last-frame live solids: `76 / 80`
- Element deletion events:
  - element `23` at `1.0231E-01 ms`
  - element `29` at `1.0231E-01 ms`
  - element `24` at `1.0231E-01 ms`
  - element `30` at `1.0231E-01 ms`

## Candidate metrics

- `perforation_marker`: `embedded_candidate`
- `projectile_initial_velocity_m_per_s`: `150.0`
- `residual_velocity_candidate_m_per_s`: `1.189671`
- Metrics sidecar: `project_state/graph_executor/GS-102-transient-refined-v150-bracket-20260512/ballistic/ballistic_metrics.json`

## Crossing and energy evidence

- `crossing_status`: `partial_candidate`
- `front_face_crossed`: `True`
- `back_face_crossed`: `False`
- `first_back_face_crossing_t_s`: `None`
- `velocity_trace_sample_count`: `150`
- `velocity_trace_final_speed_m_per_s`: `1.189670532`
- `partial_energy_audit_status`: `partial_candidate`
- `partial_energy_missing_terms`: `plastic_dissipation_j, contact_friction_j, hourglass_energy_j`

## Visualization artifacts

- GIF: `project_state/graph_executor/GS-102-transient-refined-v150-bracket-20260512/visualization/openradioss_animation.gif`
- Visualization manifest: `project_state/graph_executor/GS-102-transient-refined-v150-bracket-20260512/visualization/openradioss_animation_manifest.json`

## Artifact hashes

```text
63f00016b59e21a6e744c53a402758592c775c297004675cd133c506bc2e0e72  project_state/runs/GS-102-transient-refined-v150-bracket-20260512/data/model_00_0000.rad
f792facf84aabea81a534977af08ada59c38cdae77657e4ea2aafd1a1ff50243  project_state/runs/GS-102-transient-refined-v150-bracket-20260512/data/model_00_0001.rad
c6e99f8b20dff8e72feb9295d4cfc74d1aaa8007baa9666b6698f4eff6f4a17b  project_state/runs/GS-102-transient-refined-v150-bracket-20260512/data/starter.log
c6163d0b1b614caa75f7eb979e3444f4b01de0506154a7598bc37537206d39b9  project_state/runs/GS-102-transient-refined-v150-bracket-20260512/data/engine.log
a430e0ef26f2b362dfafa90cbd4f55ba7808866c0d48257f2268f11b54c49984  project_state/graph_executor/GS-102-transient-refined-v150-bracket-20260512/ballistic/ballistic_metrics.json
c0e15865ba6066f56e352d5d9d19edd5324ffae722d9d88c59beb730a4a5035d  project_state/graph_executor/GS-102-transient-refined-v150-bracket-20260512/visualization/openradioss_animation_manifest.json
002eabece756fe4d35106a2f3bbef3d02399957ae0ab0829019023cde2138ec1  project_state/graph_executor/GS-102-transient-refined-v150-bracket-20260512/visualization/openradioss_animation.gif
```

## Limitations

- Tier 1 only: no signed validation, no benchmark comparison, no tolerance
  agreement, and no independent reviewer signoff.
- This is a candidate workflow proof, not a locked validation configuration.
- Energy audit is partial unless future extraction adds plastic dissipation,
  hourglass energy, and contact friction to the metrics sidecar.
