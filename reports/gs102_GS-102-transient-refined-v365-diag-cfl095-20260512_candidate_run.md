# GS-102 transient candidate run - GS-102-transient-refined-v365-diag-cfl095-20260512

> Status: Tier 1 engineering candidate.
> Solver: OpenRadioss via `openradioss-local-arm64:latest`.
> Claim boundary: not signed validation; not benchmark agreement.

## Purpose

Run a real OpenRadioss transient structural candidate for projectile impact on
a steel plate. Runtime decks and solver outputs live under `project_state/`.
This script refuses runtime writes inside `golden_samples/**`.

## Candidate setup

- Source deck directory: `project_state/diagnostic_sources/GS-102-v365-cfl_095/data`
- Runtime deck directory: `project_state/runs/GS-102-transient-refined-v365-diag-cfl095-20260512/data`
- Projectile initial velocity: `365 m/s`
- Projectile mass used by metrics: `0.005024 kg`
- Projectile node id range used by metrics: `1..27`

## Solver evidence

- Starter errors / warnings: `0` / `6`
- Engine normal termination: `True`
- Engine cycle count: `8681`
- Animation frame count: `150`
- Last-frame live solids: `71 / 80`
- Element deletion events:
  - element `24` at `3.4680E-02 ms`
  - element `29` at `3.5536E-02 ms`
  - element `30` at `3.6282E-02 ms`
  - element `23` at `3.6415E-02 ms`
  - element `22` at `1.2218E-01 ms`
  - element `19` at `1.2314E-01 ms`
  - element `28` at `1.2329E-01 ms`
  - element `25` at `1.2899E-01 ms`
  - element `35` at `1.3990E-01 ms`

## Candidate metrics

- `perforation_marker`: `perforated_candidate`
- `projectile_initial_velocity_m_per_s`: `365.0`
- `residual_velocity_candidate_m_per_s`: `34.454879`
- Metrics sidecar: `project_state/graph_executor/GS-102-transient-refined-v365-diag-cfl095-20260512/ballistic/ballistic_metrics.json`

## Crossing and energy evidence

- `crossing_status`: `candidate_observed`
- `front_face_crossed`: `True`
- `back_face_crossed`: `True`
- `first_back_face_crossing_t_s`: `0.000124032`
- `velocity_trace_sample_count`: `150`
- `velocity_trace_final_speed_m_per_s`: `34.454878697`
- `partial_energy_audit_status`: `partial_candidate`
- `partial_energy_missing_terms`: `plastic_dissipation_j, contact_friction_j, hourglass_energy_j`

## Visualization artifacts

- GIF: `project_state/graph_executor/GS-102-transient-refined-v365-diag-cfl095-20260512/visualization/openradioss_animation.gif`
- Visualization manifest: `project_state/graph_executor/GS-102-transient-refined-v365-diag-cfl095-20260512/visualization/openradioss_animation_manifest.json`

## Artifact hashes

```text
2253b6a6c0e9100032ca7fdb85c6f97034d663c33a5330ba58bd939a160d950e  project_state/runs/GS-102-transient-refined-v365-diag-cfl095-20260512/data/model_00_0000.rad
2c11c1647f5e386e0edce78c2fe950be07ead12ef932e245285ff39595da2e57  project_state/runs/GS-102-transient-refined-v365-diag-cfl095-20260512/data/model_00_0001.rad
a6776f4e0a7be962efa1b6534af15e8e680b4d4e0cd5339e20071d409185eee7  project_state/runs/GS-102-transient-refined-v365-diag-cfl095-20260512/data/starter.log
6064845f9c27a5ba7d77a9683343843acedb4189e058e1fa5e93ad86501b18ad  project_state/runs/GS-102-transient-refined-v365-diag-cfl095-20260512/data/engine.log
e54fdb042aeee3c371c8d1d21741e1710acbe5f9b81f1a224337069dd7019e60  project_state/graph_executor/GS-102-transient-refined-v365-diag-cfl095-20260512/ballistic/ballistic_metrics.json
a086ce04b070bf500f1c9302cb3b7ad72533af8b261ab6c4b4e2373fd9eadc5a  project_state/graph_executor/GS-102-transient-refined-v365-diag-cfl095-20260512/visualization/openradioss_animation_manifest.json
e69d3196dd0dafa2f4d47ebe0a6887d255a0205841c1f3ddd4dca9b3090c149c  project_state/graph_executor/GS-102-transient-refined-v365-diag-cfl095-20260512/visualization/openradioss_animation.gif
```

## Limitations

- Tier 1 only: no signed validation, no benchmark comparison, no tolerance
  agreement, and no independent reviewer signoff.
- This is a candidate workflow proof, not a locked validation configuration.
- Energy audit is partial unless future extraction adds plastic dissipation,
  hourglass energy, and contact friction to the metrics sidecar.
