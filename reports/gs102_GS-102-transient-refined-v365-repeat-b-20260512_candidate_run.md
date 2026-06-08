# GS-102 transient candidate run - GS-102-transient-refined-v365-repeat-b-20260512

> Status: Tier 1 engineering candidate.
> Solver: OpenRadioss via `openradioss-local-arm64:latest`.
> Claim boundary: not signed validation; not benchmark agreement.

## Purpose

Run a real OpenRadioss transient structural candidate for projectile impact on
a steel plate. Runtime decks and solver outputs live under `project_state/`.
This script refuses runtime writes inside `golden_samples/**`.

## Candidate setup

- Source deck directory: `golden_samples/GS-102-refined-candidate/data`
- Runtime deck directory: `project_state/runs/GS-102-transient-refined-v365-repeat-b-20260512/data`
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
- Metrics sidecar: `project_state/graph_executor/GS-102-transient-refined-v365-repeat-b-20260512/ballistic/ballistic_metrics.json`

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

- GIF: `project_state/graph_executor/GS-102-transient-refined-v365-repeat-b-20260512/visualization/openradioss_animation.gif`
- Visualization manifest: `project_state/graph_executor/GS-102-transient-refined-v365-repeat-b-20260512/visualization/openradioss_animation_manifest.json`

## Artifact hashes

```text
2253b6a6c0e9100032ca7fdb85c6f97034d663c33a5330ba58bd939a160d950e  project_state/runs/GS-102-transient-refined-v365-repeat-b-20260512/data/model_00_0000.rad
f792facf84aabea81a534977af08ada59c38cdae77657e4ea2aafd1a1ff50243  project_state/runs/GS-102-transient-refined-v365-repeat-b-20260512/data/model_00_0001.rad
a6776f4e0a7be962efa1b6534af15e8e680b4d4e0cd5339e20071d409185eee7  project_state/runs/GS-102-transient-refined-v365-repeat-b-20260512/data/starter.log
4a7ba0784a14d4d1b11a2b863b80c6833d644d1b9203d38fb2991457f3b29373  project_state/runs/GS-102-transient-refined-v365-repeat-b-20260512/data/engine.log
5318dfb0b081474f540662a09da2d7d59c77a9cc4d1e37a28a3cd8fe05ef6b25  project_state/graph_executor/GS-102-transient-refined-v365-repeat-b-20260512/ballistic/ballistic_metrics.json
e72522846b9507449b2b037208ff91227ce09a7f10f2d327f1001aec92799d55  project_state/graph_executor/GS-102-transient-refined-v365-repeat-b-20260512/visualization/openradioss_animation_manifest.json
bd8847b2be88c7aaec6cd1e75f98b3a672aceb6dddb3f3dee02792b66f9fe1f1  project_state/graph_executor/GS-102-transient-refined-v365-repeat-b-20260512/visualization/openradioss_animation.gif
```

## Limitations

- Tier 1 only: no signed validation, no benchmark comparison, no tolerance
  agreement, and no independent reviewer signoff.
- This is a candidate workflow proof, not a locked validation configuration.
- Energy audit is partial unless future extraction adds plastic dissipation,
  hourglass energy, and contact friction to the metrics sidecar.
