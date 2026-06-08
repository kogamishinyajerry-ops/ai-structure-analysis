# GS-102 transient candidate run - GS-102-transient-refined-v505-probe-20260512

> Status: Tier 1 engineering candidate.
> Solver: OpenRadioss via `openradioss-local-arm64:latest`.
> Claim boundary: not signed validation; not benchmark agreement.

## Purpose

Run a real OpenRadioss transient structural candidate for projectile impact on
a steel plate. Runtime decks and solver outputs live under `project_state/`.
This script refuses runtime writes inside `golden_samples/**`.

## Candidate setup

- Source deck directory: `golden_samples/GS-102-refined-candidate/data`
- Runtime deck directory: `project_state/runs/GS-102-transient-refined-v505-probe-20260512/data`
- Projectile initial velocity: `505 m/s`
- Projectile mass used by metrics: `0.005024 kg`
- Projectile node id range used by metrics: `1..27`

## Solver evidence

- Starter errors / warnings: `0` / `6`
- Engine normal termination: `True`
- Engine cycle count: `8520`
- Animation frame count: `150`
- Last-frame live solids: `69 / 80`
- Element deletion events:
  - element `23` at `2.5801E-02 ms`
  - element `30` at `2.5801E-02 ms`
  - element `29` at `2.5871E-02 ms`
  - element `24` at `2.5871E-02 ms`
  - element `35` at `1.0379E-01 ms`
  - element `28` at `1.1345E-01 ms`
  - element `25` at `1.1345E-01 ms`
  - element `59` at `1.4215E-01 ms`
  - element `66` at `1.4263E-01 ms`
  - element `65` at `1.4323E-01 ms`
  - element `60` at `1.4504E-01 ms`

## Candidate metrics

- `perforation_marker`: `perforated_candidate`
- `projectile_initial_velocity_m_per_s`: `505.0`
- `residual_velocity_candidate_m_per_s`: `40.374543`
- Metrics sidecar: `project_state/graph_executor/GS-102-transient-refined-v505-probe-20260512/ballistic/ballistic_metrics.json`

## Crossing and energy evidence

- `crossing_status`: `candidate_observed`
- `front_face_crossed`: `True`
- `back_face_crossed`: `True`
- `first_back_face_crossing_t_s`: `5.8012e-05`
- `velocity_trace_sample_count`: `150`
- `velocity_trace_final_speed_m_per_s`: `40.374543134`
- `partial_energy_audit_status`: `partial_candidate`
- `partial_energy_missing_terms`: `plastic_dissipation_j, contact_friction_j, hourglass_energy_j`

## Visualization artifacts

- GIF: `project_state/graph_executor/GS-102-transient-refined-v505-probe-20260512/visualization/openradioss_animation.gif`
- Visualization manifest: `project_state/graph_executor/GS-102-transient-refined-v505-probe-20260512/visualization/openradioss_animation_manifest.json`

## Artifact hashes

```text
a61777a1d985e57be59d79a99fa5210d7e0f4208caced0bec6bac27c6ae28caa  project_state/runs/GS-102-transient-refined-v505-probe-20260512/data/model_00_0000.rad
f792facf84aabea81a534977af08ada59c38cdae77657e4ea2aafd1a1ff50243  project_state/runs/GS-102-transient-refined-v505-probe-20260512/data/model_00_0001.rad
c7d62240a9e118c3add2108dd882492b8150c2329a058887989cb74b7c8da791  project_state/runs/GS-102-transient-refined-v505-probe-20260512/data/starter.log
06c2be19e9ecb7eceee49086df57db4c03c4a4309242b79c0a9684dba808637c  project_state/runs/GS-102-transient-refined-v505-probe-20260512/data/engine.log
69375ce5b1d92646ab9d3583ec2d4eda2448ab5eafbe42149d8b11078d056894  project_state/graph_executor/GS-102-transient-refined-v505-probe-20260512/ballistic/ballistic_metrics.json
3822f74dde556e4efbf7a172ebc1cc6c8a3a486822897da662f936cc76923f23  project_state/graph_executor/GS-102-transient-refined-v505-probe-20260512/visualization/openradioss_animation_manifest.json
cbb3ca906240e0e7a3f8f293dfe462eaad7334fd5ad268f17eebe8253c95f95b  project_state/graph_executor/GS-102-transient-refined-v505-probe-20260512/visualization/openradioss_animation.gif
```

## Limitations

- Tier 1 only: no signed validation, no benchmark comparison, no tolerance
  agreement, and no independent reviewer signoff.
- This is a candidate workflow proof, not a locked validation configuration.
- Energy audit is partial unless future extraction adds plastic dissipation,
  hourglass energy, and contact friction to the metrics sidecar.
