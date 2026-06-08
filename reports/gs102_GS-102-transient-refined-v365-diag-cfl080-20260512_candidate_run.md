# GS-102 transient candidate run - GS-102-transient-refined-v365-diag-cfl080-20260512

> Status: Tier 1 engineering candidate.
> Solver: OpenRadioss via `openradioss-local-arm64:latest`.
> Claim boundary: not signed validation; not benchmark agreement.

## Purpose

Run a real OpenRadioss transient structural candidate for projectile impact on
a steel plate. Runtime decks and solver outputs live under `project_state/`.
This script refuses runtime writes inside `golden_samples/**`.

## Candidate setup

- Source deck directory: `project_state/diagnostic_sources/GS-102-v365-cfl_080/data`
- Runtime deck directory: `project_state/runs/GS-102-transient-refined-v365-diag-cfl080-20260512/data`
- Projectile initial velocity: `365 m/s`
- Projectile mass used by metrics: `0.005024 kg`
- Projectile node id range used by metrics: `1..27`

## Solver evidence

- Starter errors / warnings: `0` / `6`
- Engine normal termination: `True`
- Engine cycle count: `5409`
- Animation frame count: `150`
- Last-frame live solids: `72 / 80`
- Element deletion events:
  - element `23` at `3.4948E-02 ms`
  - element `29` at `3.4948E-02 ms`
  - element `24` at `3.4948E-02 ms`
  - element `30` at `3.4948E-02 ms`
  - element `31` at `1.2038E-01 ms`
  - element `22` at `1.2060E-01 ms`
  - element `28` at `1.2440E-01 ms`
  - element `25` at `1.2440E-01 ms`

## Candidate metrics

- `perforation_marker`: `embedded_candidate`
- `projectile_initial_velocity_m_per_s`: `365.0`
- `residual_velocity_candidate_m_per_s`: `12.820306`
- Metrics sidecar: `project_state/graph_executor/GS-102-transient-refined-v365-diag-cfl080-20260512/ballistic/ballistic_metrics.json`

## Crossing and energy evidence

- `crossing_status`: `partial_candidate`
- `front_face_crossed`: `True`
- `back_face_crossed`: `False`
- `first_back_face_crossing_t_s`: `None`
- `velocity_trace_sample_count`: `150`
- `velocity_trace_final_speed_m_per_s`: `12.82030621`
- `partial_energy_audit_status`: `partial_candidate`
- `partial_energy_missing_terms`: `plastic_dissipation_j, contact_friction_j, hourglass_energy_j`

## Visualization artifacts

- GIF: `project_state/graph_executor/GS-102-transient-refined-v365-diag-cfl080-20260512/visualization/openradioss_animation.gif`
- Visualization manifest: `project_state/graph_executor/GS-102-transient-refined-v365-diag-cfl080-20260512/visualization/openradioss_animation_manifest.json`

## Artifact hashes

```text
2253b6a6c0e9100032ca7fdb85c6f97034d663c33a5330ba58bd939a160d950e  project_state/runs/GS-102-transient-refined-v365-diag-cfl080-20260512/data/model_00_0000.rad
20e629f1f17668c6207bec742668e9d775438b616ec27311b5e41245c379f3b2  project_state/runs/GS-102-transient-refined-v365-diag-cfl080-20260512/data/model_00_0001.rad
72098a90cb99ce21a9147ead14b7b1cb63f248da5a78fc8e20325cc927d48496  project_state/runs/GS-102-transient-refined-v365-diag-cfl080-20260512/data/starter.log
7edcec3568089111547c16ad4ea444b980403a9ead8694e8e74164d857c1e3eb  project_state/runs/GS-102-transient-refined-v365-diag-cfl080-20260512/data/engine.log
3c36d5d44a67485648b58ce63c1c376a245334ba5095383b9916781b500df20a  project_state/graph_executor/GS-102-transient-refined-v365-diag-cfl080-20260512/ballistic/ballistic_metrics.json
501363b38b7c97d2d076c735bf2cc742c00b8ec016cd5eb3e47002842bf57772  project_state/graph_executor/GS-102-transient-refined-v365-diag-cfl080-20260512/visualization/openradioss_animation_manifest.json
a0672e92871f991292f3de2c88a085b698372721065204139fc36c3e701a2847  project_state/graph_executor/GS-102-transient-refined-v365-diag-cfl080-20260512/visualization/openradioss_animation.gif
```

## Limitations

- Tier 1 only: no signed validation, no benchmark comparison, no tolerance
  agreement, and no independent reviewer signoff.
- This is a candidate workflow proof, not a locked validation configuration.
- Energy audit is partial unless future extraction adds plastic dissipation,
  hourglass energy, and contact friction to the metrics sidecar.
