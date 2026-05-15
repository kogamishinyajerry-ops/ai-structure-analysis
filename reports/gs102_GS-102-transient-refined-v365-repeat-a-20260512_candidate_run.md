# GS-102 transient candidate run - GS-102-transient-refined-v365-repeat-a-20260512

> Status: Tier 1 engineering candidate.
> Solver: OpenRadioss via `openradioss-local-arm64:latest`.
> Claim boundary: not signed validation; not benchmark agreement.

## Purpose

Run a real OpenRadioss transient structural candidate for projectile impact on
a steel plate. Runtime decks and solver outputs live under `project_state/`.
This script refuses runtime writes inside `golden_samples/**`.

## Candidate setup

- Source deck directory: `golden_samples/GS-102-refined-candidate/data`
- Runtime deck directory: `project_state/runs/GS-102-transient-refined-v365-repeat-a-20260512/data`
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
- Metrics sidecar: `project_state/graph_executor/GS-102-transient-refined-v365-repeat-a-20260512/ballistic/ballistic_metrics.json`

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

- GIF: `project_state/graph_executor/GS-102-transient-refined-v365-repeat-a-20260512/visualization/openradioss_animation.gif`
- Visualization manifest: `project_state/graph_executor/GS-102-transient-refined-v365-repeat-a-20260512/visualization/openradioss_animation_manifest.json`

## Artifact hashes

```text
2253b6a6c0e9100032ca7fdb85c6f97034d663c33a5330ba58bd939a160d950e  project_state/runs/GS-102-transient-refined-v365-repeat-a-20260512/data/model_00_0000.rad
f792facf84aabea81a534977af08ada59c38cdae77657e4ea2aafd1a1ff50243  project_state/runs/GS-102-transient-refined-v365-repeat-a-20260512/data/model_00_0001.rad
292ec99372678f0a0f4cb960d45446846fb6a97e7c88954b65f7ab4086f5358f  project_state/runs/GS-102-transient-refined-v365-repeat-a-20260512/data/starter.log
5927c68b41c66e7c06e11d9a262d69d2707e5e67cc88a4fbb73572b694b5e270  project_state/runs/GS-102-transient-refined-v365-repeat-a-20260512/data/engine.log
12352c05538e2f6157eb5e8849227c7a917055f5ddf847a909ffa569a1f8fd45  project_state/graph_executor/GS-102-transient-refined-v365-repeat-a-20260512/ballistic/ballistic_metrics.json
d8e591351e6c3aeb4c026e580301343e6dee33179b7c0cdca8e057fbe9fb5fcf  project_state/graph_executor/GS-102-transient-refined-v365-repeat-a-20260512/visualization/openradioss_animation_manifest.json
190582a564b1e230b7eb226872d89340fe3f97c2e6d749ac640155c15c6e0551  project_state/graph_executor/GS-102-transient-refined-v365-repeat-a-20260512/visualization/openradioss_animation.gif
```

## Limitations

- Tier 1 only: no signed validation, no benchmark comparison, no tolerance
  agreement, and no independent reviewer signoff.
- This is a candidate workflow proof, not a locked validation configuration.
- Energy audit is partial unless future extraction adds plastic dissipation,
  hourglass energy, and contact friction to the metrics sidecar.
