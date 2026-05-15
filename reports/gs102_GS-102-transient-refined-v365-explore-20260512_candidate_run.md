# GS-102 transient candidate run - GS-102-transient-refined-v365-explore-20260512

> Status: Tier 1 engineering candidate.
> Solver: OpenRadioss via `openradioss-local-arm64:latest`.
> Claim boundary: not signed validation; not benchmark agreement.

## Purpose

Run a real OpenRadioss transient structural candidate for projectile impact on
a steel plate. Runtime decks and solver outputs live under `project_state/`.
This script refuses runtime writes inside `golden_samples/**`.

## Candidate setup

- Source deck directory: `golden_samples/GS-102-refined-candidate/data`
- Runtime deck directory: `project_state/runs/GS-102-transient-refined-v365-explore-20260512/data`
- Projectile initial velocity: `365 m/s`
- Projectile mass used by metrics: `0.005024 kg`
- Projectile node id range used by metrics: `1..27`

## Solver evidence

- Starter errors / warnings: `0` / `6`
- Engine normal termination: `True`
- Engine cycle count: `3672`
- Animation frame count: `150`
- Last-frame live solids: `76 / 80`
- Element deletion events:
  - element `23` at `3.5910E-02 ms`
  - element `29` at `3.5910E-02 ms`
  - element `24` at `3.5910E-02 ms`
  - element `30` at `3.5910E-02 ms`

## Candidate metrics

- `perforation_marker`: `perforated_candidate`
- `projectile_initial_velocity_m_per_s`: `365.0`
- `residual_velocity_candidate_m_per_s`: `34.469076`
- Metrics sidecar: `project_state/graph_executor/GS-102-transient-refined-v365-explore-20260512/ballistic/ballistic_metrics.json`

## Crossing and energy evidence

- `crossing_status`: `candidate_observed`
- `front_face_crossed`: `True`
- `back_face_crossed`: `True`
- `first_back_face_crossing_t_s`: `7.102e-05`
- `velocity_trace_sample_count`: `150`
- `velocity_trace_final_speed_m_per_s`: `34.469076088`
- `partial_energy_audit_status`: `partial_candidate`
- `partial_energy_missing_terms`: `plastic_dissipation_j, contact_friction_j, hourglass_energy_j`

## Visualization artifacts

- GIF: `project_state/graph_executor/GS-102-transient-refined-v365-explore-20260512/visualization/openradioss_animation.gif`
- Visualization manifest: `project_state/graph_executor/GS-102-transient-refined-v365-explore-20260512/visualization/openradioss_animation_manifest.json`

## Artifact hashes

```text
2253b6a6c0e9100032ca7fdb85c6f97034d663c33a5330ba58bd939a160d950e  project_state/runs/GS-102-transient-refined-v365-explore-20260512/data/model_00_0000.rad
f792facf84aabea81a534977af08ada59c38cdae77657e4ea2aafd1a1ff50243  project_state/runs/GS-102-transient-refined-v365-explore-20260512/data/model_00_0001.rad
ad2fba3d3bf32d1e4a9bc6bed61b1b107ac70a98283e59188ed051ea8dfc633e  project_state/runs/GS-102-transient-refined-v365-explore-20260512/data/starter.log
7e6eb5bba4cf3328612a0d188fc9f25a7136fb623598dc4f86b469b1bfad444b  project_state/runs/GS-102-transient-refined-v365-explore-20260512/data/engine.log
3d75926688abb6bee5b8db4e176324e0ee7b05237bf8bb1f53db3cd0c42e1ed0  project_state/graph_executor/GS-102-transient-refined-v365-explore-20260512/ballistic/ballistic_metrics.json
63e80beab7e5ad9a2b34c8704ae33a59ad721775642d752a805b76c5bc1ae0cc  project_state/graph_executor/GS-102-transient-refined-v365-explore-20260512/visualization/openradioss_animation_manifest.json
367aeae966fca3f2f395d6567a4898723783dfcdd04ff757eed188c77c3d9082  project_state/graph_executor/GS-102-transient-refined-v365-explore-20260512/visualization/openradioss_animation.gif
```

## Limitations

- Tier 1 only: no signed validation, no benchmark comparison, no tolerance
  agreement, and no independent reviewer signoff.
- This is a candidate workflow proof, not a locked validation configuration.
- Energy audit is partial unless future extraction adds plastic dissipation,
  hourglass energy, and contact friction to the metrics sidecar.
