# GS-102 transient candidate run - GS-102-transient-refined-cfl085-v385-bracket-20260512

> Status: Tier 1 engineering candidate.
> Solver: OpenRadioss via `openradioss-local-arm64:latest`.
> Claim boundary: not signed validation; not benchmark agreement.

## Purpose

Run a real OpenRadioss transient structural candidate for projectile impact on
a steel plate. Runtime decks and solver outputs live under `project_state/`.
This script refuses runtime writes inside `golden_samples/**`.

## Candidate setup

- Source deck directory: `project_state/diagnostic_sources/GS-102-v365-cfl_085/data`
- Runtime deck directory: `project_state/runs/GS-102-transient-refined-cfl085-v385-bracket-20260512/data`
- Projectile initial velocity: `385 m/s`
- Projectile mass used by metrics: `0.005024 kg`
- Projectile node id range used by metrics: `1..27`

## Solver evidence

- Starter errors / warnings: `0` / `6`
- Engine normal termination: `True`
- Engine cycle count: `6664`
- Animation frame count: `150`
- Last-frame live solids: `72 / 80`
- Element deletion events:
  - element `23` at `3.3243E-02 ms`
  - element `29` at `3.3243E-02 ms`
  - element `24` at `3.3243E-02 ms`
  - element `30` at `3.3243E-02 ms`
  - element `31` at `1.1284E-01 ms`
  - element `22` at `1.1329E-01 ms`
  - element `25` at `1.1712E-01 ms`
  - element `28` at `1.1783E-01 ms`

## Candidate metrics

- `perforation_marker`: `embedded_candidate`
- `projectile_initial_velocity_m_per_s`: `385.0`
- `residual_velocity_candidate_m_per_s`: `11.306249`
- Metrics sidecar: `project_state/graph_executor/GS-102-transient-refined-cfl085-v385-bracket-20260512/ballistic/ballistic_metrics.json`

## Crossing and energy evidence

- `crossing_status`: `partial_candidate`
- `front_face_crossed`: `True`
- `back_face_crossed`: `False`
- `first_back_face_crossing_t_s`: `None`
- `velocity_trace_sample_count`: `150`
- `velocity_trace_final_speed_m_per_s`: `11.306248634`
- `partial_energy_audit_status`: `partial_candidate`
- `partial_energy_missing_terms`: `plastic_dissipation_j, contact_friction_j, hourglass_energy_j`

## Visualization artifacts

- GIF: `project_state/graph_executor/GS-102-transient-refined-cfl085-v385-bracket-20260512/visualization/openradioss_animation.gif`
- Visualization manifest: `project_state/graph_executor/GS-102-transient-refined-cfl085-v385-bracket-20260512/visualization/openradioss_animation_manifest.json`

## Artifact hashes

```text
15a86ef9c1ce9df14fcf1df5ac1c4d131a3fb9cfdb8abad3ccdc88047fe47eba  project_state/runs/GS-102-transient-refined-cfl085-v385-bracket-20260512/data/model_00_0000.rad
ce7efcec9772e9d2d132bbf4c86f88328255a3ee25bc5b8ae52663cf51945d91  project_state/runs/GS-102-transient-refined-cfl085-v385-bracket-20260512/data/model_00_0001.rad
0afabb9d75a06206719971f9321f10885aad54e9e4aec902f53e98a10e45c510  project_state/runs/GS-102-transient-refined-cfl085-v385-bracket-20260512/data/starter.log
d8015be91174c832469c6d6d5c693765a01b3feb5970fc0e528e975985976d82  project_state/runs/GS-102-transient-refined-cfl085-v385-bracket-20260512/data/engine.log
83c34597cc1dedffab34d44453c52b9fe0377e9af6c7e695e9d07b691f6439d3  project_state/graph_executor/GS-102-transient-refined-cfl085-v385-bracket-20260512/ballistic/ballistic_metrics.json
b2bdb2ecb2c8d60fb0ef15fe76b91a047d9f7f1ff18fc02b0c00cf9bfa5a5390  project_state/graph_executor/GS-102-transient-refined-cfl085-v385-bracket-20260512/visualization/openradioss_animation_manifest.json
38426a6d44a41e04050286b35ddffc4ea5bd040cc5ba1cd30ab3b857318911d2  project_state/graph_executor/GS-102-transient-refined-cfl085-v385-bracket-20260512/visualization/openradioss_animation.gif
```

## Limitations

- Tier 1 only: no signed validation, no benchmark comparison, no tolerance
  agreement, and no independent reviewer signoff.
- This is a candidate workflow proof, not a locked validation configuration.
- Energy audit is partial unless future extraction adds plastic dissipation,
  hourglass energy, and contact friction to the metrics sidecar.
