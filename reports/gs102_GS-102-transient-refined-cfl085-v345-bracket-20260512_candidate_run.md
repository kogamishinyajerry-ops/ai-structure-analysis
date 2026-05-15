# GS-102 transient candidate run - GS-102-transient-refined-cfl085-v345-bracket-20260512

> Status: Tier 1 engineering candidate.
> Solver: OpenRadioss via `openradioss-local-arm64:latest`.
> Claim boundary: not signed validation; not benchmark agreement.

## Purpose

Run a real OpenRadioss transient structural candidate for projectile impact on
a steel plate. Runtime decks and solver outputs live under `project_state/`.
This script refuses runtime writes inside `golden_samples/**`.

## Candidate setup

- Source deck directory: `project_state/diagnostic_sources/GS-102-v365-cfl_085/data`
- Runtime deck directory: `project_state/runs/GS-102-transient-refined-cfl085-v345-bracket-20260512/data`
- Projectile initial velocity: `345 m/s`
- Projectile mass used by metrics: `0.005024 kg`
- Projectile node id range used by metrics: `1..27`

## Solver evidence

- Starter errors / warnings: `0` / `6`
- Engine normal termination: `True`
- Engine cycle count: `4389`
- Animation frame count: `150`
- Last-frame live solids: `72 / 80`
- Element deletion events:
  - element `23` at `3.7073E-02 ms`
  - element `29` at `3.7073E-02 ms`
  - element `24` at `3.7073E-02 ms`
  - element `30` at `3.7073E-02 ms`
  - element `22` at `1.2621E-01 ms`
  - element `25` at `1.2648E-01 ms`
  - element `28` at `1.2915E-01 ms`
  - element `31` at `1.2915E-01 ms`

## Candidate metrics

- `perforation_marker`: `embedded_candidate`
- `projectile_initial_velocity_m_per_s`: `345.0`
- `residual_velocity_candidate_m_per_s`: `9.05465`
- Metrics sidecar: `project_state/graph_executor/GS-102-transient-refined-cfl085-v345-bracket-20260512/ballistic/ballistic_metrics.json`

## Crossing and energy evidence

- `crossing_status`: `partial_candidate`
- `front_face_crossed`: `True`
- `back_face_crossed`: `False`
- `first_back_face_crossing_t_s`: `None`
- `velocity_trace_sample_count`: `150`
- `velocity_trace_final_speed_m_per_s`: `9.054650336`
- `partial_energy_audit_status`: `partial_candidate`
- `partial_energy_missing_terms`: `plastic_dissipation_j, contact_friction_j, hourglass_energy_j`

## Visualization artifacts

- GIF: `project_state/graph_executor/GS-102-transient-refined-cfl085-v345-bracket-20260512/visualization/openradioss_animation.gif`
- Visualization manifest: `project_state/graph_executor/GS-102-transient-refined-cfl085-v345-bracket-20260512/visualization/openradioss_animation_manifest.json`

## Artifact hashes

```text
1a84b1fe19f0e2d51e39d2b9dcc9559254da96d32a46712744550241b97b7dc7  project_state/runs/GS-102-transient-refined-cfl085-v345-bracket-20260512/data/model_00_0000.rad
ce7efcec9772e9d2d132bbf4c86f88328255a3ee25bc5b8ae52663cf51945d91  project_state/runs/GS-102-transient-refined-cfl085-v345-bracket-20260512/data/model_00_0001.rad
64a448fc2e0fcb05824dcda25d2c793c17fab85cb8145ef2dd0ad5318b0d9874  project_state/runs/GS-102-transient-refined-cfl085-v345-bracket-20260512/data/starter.log
7c49252f67b7f659f0f6ba56addc8871fe8341e54f085cf1ad25622dd074a7da  project_state/runs/GS-102-transient-refined-cfl085-v345-bracket-20260512/data/engine.log
6f85c64b20726b8f7d5769cc5bbdb0775c84fca55f74bf5fbb15d2a27ae32258  project_state/graph_executor/GS-102-transient-refined-cfl085-v345-bracket-20260512/ballistic/ballistic_metrics.json
1088db3a065a4a900d29ac58521d98a88636ecf3d3a2178e639de6e7926cc8dc  project_state/graph_executor/GS-102-transient-refined-cfl085-v345-bracket-20260512/visualization/openradioss_animation_manifest.json
070620d76e51370c96747376f599c151aa8ad6de0ce8f8e0ff92d81ad3a62568  project_state/graph_executor/GS-102-transient-refined-cfl085-v345-bracket-20260512/visualization/openradioss_animation.gif
```

## Limitations

- Tier 1 only: no signed validation, no benchmark comparison, no tolerance
  agreement, and no independent reviewer signoff.
- This is a candidate workflow proof, not a locked validation configuration.
- Energy audit is partial unless future extraction adds plastic dissipation,
  hourglass energy, and contact friction to the metrics sidecar.
