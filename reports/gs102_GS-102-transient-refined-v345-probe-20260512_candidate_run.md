# GS-102 transient candidate run - GS-102-transient-refined-v345-probe-20260512

> Status: Tier 1 engineering candidate.
> Solver: OpenRadioss via `openradioss-local-arm64:latest`.
> Claim boundary: not signed validation; not benchmark agreement.

## Purpose

Run a real OpenRadioss transient structural candidate for projectile impact on
a steel plate. Runtime decks and solver outputs live under `project_state/`.
This script refuses runtime writes inside `golden_samples/**`.

## Candidate setup

- Source deck directory: `golden_samples/GS-102-refined-candidate/data`
- Runtime deck directory: `project_state/runs/GS-102-transient-refined-v345-probe-20260512/data`
- Projectile initial velocity: `345 m/s`
- Projectile mass used by metrics: `0.005024 kg`
- Projectile node id range used by metrics: `1..27`

## Solver evidence

- Starter errors / warnings: `0` / `6`
- Engine normal termination: `True`
- Engine cycle count: `5435`
- Animation frame count: `150`
- Last-frame live solids: `72 / 80`
- Element deletion events:
  - element `23` at `3.6794E-02 ms`
  - element `29` at `3.6794E-02 ms`
  - element `24` at `3.6794E-02 ms`
  - element `30` at `3.6794E-02 ms`
  - element `25` at `1.2945E-01 ms`
  - element `22` at `1.3125E-01 ms`
  - element `31` at `1.3125E-01 ms`
  - element `28` at `1.3238E-01 ms`

## Candidate metrics

- `perforation_marker`: `embedded_candidate`
- `projectile_initial_velocity_m_per_s`: `345.0`
- `residual_velocity_candidate_m_per_s`: `12.244106`
- Metrics sidecar: `project_state/graph_executor/GS-102-transient-refined-v345-probe-20260512/ballistic/ballistic_metrics.json`

## Crossing and energy evidence

- `crossing_status`: `partial_candidate`
- `front_face_crossed`: `True`
- `back_face_crossed`: `False`
- `first_back_face_crossing_t_s`: `None`
- `velocity_trace_sample_count`: `150`
- `velocity_trace_final_speed_m_per_s`: `12.244106438`
- `partial_energy_audit_status`: `partial_candidate`
- `partial_energy_missing_terms`: `plastic_dissipation_j, contact_friction_j, hourglass_energy_j`

## Visualization artifacts

- GIF: `project_state/graph_executor/GS-102-transient-refined-v345-probe-20260512/visualization/openradioss_animation.gif`
- Visualization manifest: `project_state/graph_executor/GS-102-transient-refined-v345-probe-20260512/visualization/openradioss_animation_manifest.json`

## Artifact hashes

```text
1a84b1fe19f0e2d51e39d2b9dcc9559254da96d32a46712744550241b97b7dc7  project_state/runs/GS-102-transient-refined-v345-probe-20260512/data/model_00_0000.rad
f792facf84aabea81a534977af08ada59c38cdae77657e4ea2aafd1a1ff50243  project_state/runs/GS-102-transient-refined-v345-probe-20260512/data/model_00_0001.rad
06173180aadc4e2122ba0f382897743ef171a843f7827b0b356ea19211dce248  project_state/runs/GS-102-transient-refined-v345-probe-20260512/data/starter.log
354566668c021b9f65dcbba0f384d859d895747a35e85eaa94f7ba6eb1f32f7b  project_state/runs/GS-102-transient-refined-v345-probe-20260512/data/engine.log
460ed1d2e5afe6eed35391d0391e1e69661528019b470ca329c52ef41ebddcf5  project_state/graph_executor/GS-102-transient-refined-v345-probe-20260512/ballistic/ballistic_metrics.json
c133828e969d5d24e84304ee0c5c0e76f3fcbc2e2b7b5c8936a9ce32103e9f31  project_state/graph_executor/GS-102-transient-refined-v345-probe-20260512/visualization/openradioss_animation_manifest.json
a4e5040022c7967ddc5c0a243b6979ddbda77993a427709d993fa05d36c256ce  project_state/graph_executor/GS-102-transient-refined-v345-probe-20260512/visualization/openradioss_animation.gif
```

## Limitations

- Tier 1 only: no signed validation, no benchmark comparison, no tolerance
  agreement, and no independent reviewer signoff.
- This is a candidate workflow proof, not a locked validation configuration.
- Energy audit is partial unless future extraction adds plastic dissipation,
  hourglass energy, and contact friction to the metrics sidecar.
