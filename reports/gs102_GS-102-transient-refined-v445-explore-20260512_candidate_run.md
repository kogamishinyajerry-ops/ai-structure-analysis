# GS-102 transient candidate run - GS-102-transient-refined-v445-explore-20260512

> Status: Tier 1 engineering candidate.
> Solver: OpenRadioss via `openradioss-local-arm64:latest`.
> Claim boundary: not signed validation; not benchmark agreement.

## Purpose

Run a real OpenRadioss transient structural candidate for projectile impact on
a steel plate. Runtime decks and solver outputs live under `project_state/`.
This script refuses runtime writes inside `golden_samples/**`.

## Candidate setup

- Source deck directory: `golden_samples/GS-102-refined-candidate/data`
- Runtime deck directory: `project_state/runs/GS-102-transient-refined-v445-explore-20260512/data`
- Projectile initial velocity: `445 m/s`
- Projectile mass used by metrics: `0.005024 kg`
- Projectile node id range used by metrics: `1..27`

## Solver evidence

- Starter errors / warnings: `0` / `6`
- Engine normal termination: `True`
- Engine cycle count: `4854`
- Animation frame count: `150`
- Last-frame live solids: `68 / 80`
- Element deletion events:
  - element `23` at `2.8720E-02 ms`
  - element `29` at `2.8720E-02 ms`
  - element `24` at `2.8720E-02 ms`
  - element `30` at `2.8720E-02 ms`
  - element `35` at `1.0876E-01 ms`
  - element `17` at `1.0893E-01 ms`
  - element `18` at `1.0996E-01 ms`
  - element `36` at `1.0996E-01 ms`
  - element `37` at `1.3099E-01 ms`
  - element `19` at `1.3151E-01 ms`
  - element `16` at `1.3256E-01 ms`
  - element `34` at `1.3308E-01 ms`

## Candidate metrics

- `perforation_marker`: `embedded_candidate`
- `projectile_initial_velocity_m_per_s`: `445.0`
- `residual_velocity_candidate_m_per_s`: `12.725867`
- Metrics sidecar: `project_state/graph_executor/GS-102-transient-refined-v445-explore-20260512/ballistic/ballistic_metrics.json`

## Crossing and energy evidence

- `crossing_status`: `partial_candidate`
- `front_face_crossed`: `True`
- `back_face_crossed`: `False`
- `first_back_face_crossing_t_s`: `None`
- `velocity_trace_sample_count`: `150`
- `velocity_trace_final_speed_m_per_s`: `12.725867184`
- `partial_energy_audit_status`: `partial_candidate`
- `partial_energy_missing_terms`: `plastic_dissipation_j, contact_friction_j, hourglass_energy_j`

## Visualization artifacts

- GIF: `project_state/graph_executor/GS-102-transient-refined-v445-explore-20260512/visualization/openradioss_animation.gif`
- Visualization manifest: `project_state/graph_executor/GS-102-transient-refined-v445-explore-20260512/visualization/openradioss_animation_manifest.json`

## Artifact hashes

```text
ed67e7223014da6adc260f748aa306c014520d4cc592fd60935d7e381c3417d4  project_state/runs/GS-102-transient-refined-v445-explore-20260512/data/model_00_0000.rad
f792facf84aabea81a534977af08ada59c38cdae77657e4ea2aafd1a1ff50243  project_state/runs/GS-102-transient-refined-v445-explore-20260512/data/model_00_0001.rad
6002db5e6039b75a52eefe0375ce7f0a15cffd7ae2dfe68618043e09ac6950b7  project_state/runs/GS-102-transient-refined-v445-explore-20260512/data/starter.log
6a345af6daa5f3e064f3bd36972321b04f0a4cf85b45c9506935918eec674900  project_state/runs/GS-102-transient-refined-v445-explore-20260512/data/engine.log
502d158d6acf3d38672bb58e560a116d0581d782d91594a3d44bd0e3491ecb86  project_state/graph_executor/GS-102-transient-refined-v445-explore-20260512/ballistic/ballistic_metrics.json
8437572955cd358661d5889aaa8d1f83bbb2d6d9a29f3d0cf2bc73177201a198  project_state/graph_executor/GS-102-transient-refined-v445-explore-20260512/visualization/openradioss_animation_manifest.json
ae2d1cd576ceff0391b4c0b8cf7b65d1e17c23ffe540cffb750a1e93e1f23008  project_state/graph_executor/GS-102-transient-refined-v445-explore-20260512/visualization/openradioss_animation.gif
```

## Limitations

- Tier 1 only: no signed validation, no benchmark comparison, no tolerance
  agreement, and no independent reviewer signoff.
- This is a candidate workflow proof, not a locked validation configuration.
- Energy audit is partial unless future extraction adds plastic dissipation,
  hourglass energy, and contact friction to the metrics sidecar.
