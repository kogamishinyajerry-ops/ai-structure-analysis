# GS-102 transient candidate run - GS-102-transient-refined-cfl085-v375-bracket-20260512

> Status: Tier 1 engineering candidate.
> Solver: OpenRadioss via `openradioss-local-arm64:latest`.
> Claim boundary: not signed validation; not benchmark agreement.

## Purpose

Run a real OpenRadioss transient structural candidate for projectile impact on
a steel plate. Runtime decks and solver outputs live under `project_state/`.
This script refuses runtime writes inside `golden_samples/**`.

## Candidate setup

- Source deck directory: `project_state/diagnostic_sources/GS-102-v365-cfl_085/data`
- Runtime deck directory: `project_state/runs/GS-102-transient-refined-cfl085-v375-bracket-20260512/data`
- Projectile initial velocity: `375 m/s`
- Projectile mass used by metrics: `0.005024 kg`
- Projectile node id range used by metrics: `1..27`

## Solver evidence

- Starter errors / warnings: `0` / `6`
- Engine normal termination: `True`
- Engine cycle count: `3829`
- Animation frame count: `150`
- Last-frame live solids: `76 / 80`
- Element deletion events:
  - element `23` at `3.4949E-02 ms`
  - element `29` at `3.4949E-02 ms`
  - element `24` at `3.4949E-02 ms`
  - element `30` at `3.4949E-02 ms`

## Candidate metrics

- `perforation_marker`: `perforated_candidate`
- `projectile_initial_velocity_m_per_s`: `375.0`
- `residual_velocity_candidate_m_per_s`: `35.407392`
- Metrics sidecar: `project_state/graph_executor/GS-102-transient-refined-cfl085-v375-bracket-20260512/ballistic/ballistic_metrics.json`

## Crossing and energy evidence

- `crossing_status`: `candidate_observed`
- `front_face_crossed`: `True`
- `back_face_crossed`: `True`
- `first_back_face_crossing_t_s`: `7.2006e-05`
- `velocity_trace_sample_count`: `150`
- `velocity_trace_final_speed_m_per_s`: `35.407391654`
- `partial_energy_audit_status`: `partial_candidate`
- `partial_energy_missing_terms`: `plastic_dissipation_j, contact_friction_j, hourglass_energy_j`

## Visualization artifacts

- GIF: `project_state/graph_executor/GS-102-transient-refined-cfl085-v375-bracket-20260512/visualization/openradioss_animation.gif`
- Visualization manifest: `project_state/graph_executor/GS-102-transient-refined-cfl085-v375-bracket-20260512/visualization/openradioss_animation_manifest.json`

## Artifact hashes

```text
81811d3d4f01dbffa31c2186440f83a2e02c3e568b39f18375c912cc19ca627d  project_state/runs/GS-102-transient-refined-cfl085-v375-bracket-20260512/data/model_00_0000.rad
ce7efcec9772e9d2d132bbf4c86f88328255a3ee25bc5b8ae52663cf51945d91  project_state/runs/GS-102-transient-refined-cfl085-v375-bracket-20260512/data/model_00_0001.rad
21c61c5d26bb25bc8761f0ce677bb2e8108ab29573b7ec8e56e9696fb19da87d  project_state/runs/GS-102-transient-refined-cfl085-v375-bracket-20260512/data/starter.log
1835e7d8a8dc977134501b5dbd687026527174bbcdc2a247c7ef70dee50df743  project_state/runs/GS-102-transient-refined-cfl085-v375-bracket-20260512/data/engine.log
c619d60b789661518331eca829486a8cd8fe6447086ea1fa1638c83b66fb0516  project_state/graph_executor/GS-102-transient-refined-cfl085-v375-bracket-20260512/ballistic/ballistic_metrics.json
abf0b585b2592e422a2339e6bb8b541c295bafb56c0b77d7e20ff2e9616abc26  project_state/graph_executor/GS-102-transient-refined-cfl085-v375-bracket-20260512/visualization/openradioss_animation_manifest.json
a3ce0a43444888b8c69b1394c84193911460a53b7a55939dafbf193bfb5f1cb7  project_state/graph_executor/GS-102-transient-refined-cfl085-v375-bracket-20260512/visualization/openradioss_animation.gif
```

## Limitations

- Tier 1 only: no signed validation, no benchmark comparison, no tolerance
  agreement, and no independent reviewer signoff.
- This is a candidate workflow proof, not a locked validation configuration.
- Energy audit is partial unless future extraction adds plastic dissipation,
  hourglass energy, and contact friction to the metrics sidecar.
