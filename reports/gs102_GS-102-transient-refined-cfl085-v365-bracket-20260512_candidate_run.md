# GS-102 transient candidate run - GS-102-transient-refined-cfl085-v365-bracket-20260512

> Status: Tier 1 engineering candidate.
> Solver: OpenRadioss via `openradioss-local-arm64:latest`.
> Claim boundary: not signed validation; not benchmark agreement.

## Purpose

Run a real OpenRadioss transient structural candidate for projectile impact on
a steel plate. Runtime decks and solver outputs live under `project_state/`.
This script refuses runtime writes inside `golden_samples/**`.

## Candidate setup

- Source deck directory: `project_state/diagnostic_sources/GS-102-v365-cfl_085/data`
- Runtime deck directory: `project_state/runs/GS-102-transient-refined-cfl085-v365-bracket-20260512/data`
- Projectile initial velocity: `365 m/s`
- Projectile mass used by metrics: `0.005024 kg`
- Projectile node id range used by metrics: `1..27`

## Solver evidence

- Starter errors / warnings: `0` / `6`
- Engine normal termination: `True`
- Engine cycle count: `4872`
- Animation frame count: `150`
- Last-frame live solids: `72 / 80`
- Element deletion events:
  - element `23` at `3.5011E-02 ms`
  - element `29` at `3.5011E-02 ms`
  - element `24` at `3.5011E-02 ms`
  - element `30` at `3.5011E-02 ms`
  - element `22` at `1.2045E-01 ms`
  - element `31` at `1.2045E-01 ms`
  - element `28` at `1.2369E-01 ms`
  - element `25` at `1.2369E-01 ms`

## Candidate metrics

- `perforation_marker`: `embedded_candidate`
- `projectile_initial_velocity_m_per_s`: `365.0`
- `residual_velocity_candidate_m_per_s`: `10.40591`
- Metrics sidecar: `project_state/graph_executor/GS-102-transient-refined-cfl085-v365-bracket-20260512/ballistic/ballistic_metrics.json`

## Crossing and energy evidence

- `crossing_status`: `partial_candidate`
- `front_face_crossed`: `True`
- `back_face_crossed`: `False`
- `first_back_face_crossing_t_s`: `None`
- `velocity_trace_sample_count`: `150`
- `velocity_trace_final_speed_m_per_s`: `10.405910355`
- `partial_energy_audit_status`: `partial_candidate`
- `partial_energy_missing_terms`: `plastic_dissipation_j, contact_friction_j, hourglass_energy_j`

## Visualization artifacts

- GIF: `project_state/graph_executor/GS-102-transient-refined-cfl085-v365-bracket-20260512/visualization/openradioss_animation.gif`
- Visualization manifest: `project_state/graph_executor/GS-102-transient-refined-cfl085-v365-bracket-20260512/visualization/openradioss_animation_manifest.json`

## Artifact hashes

```text
2253b6a6c0e9100032ca7fdb85c6f97034d663c33a5330ba58bd939a160d950e  project_state/runs/GS-102-transient-refined-cfl085-v365-bracket-20260512/data/model_00_0000.rad
ce7efcec9772e9d2d132bbf4c86f88328255a3ee25bc5b8ae52663cf51945d91  project_state/runs/GS-102-transient-refined-cfl085-v365-bracket-20260512/data/model_00_0001.rad
646a0d212e10d4b67a1c865407cf04317366d98543b227d6e640a4d08b102f6a  project_state/runs/GS-102-transient-refined-cfl085-v365-bracket-20260512/data/starter.log
49ffb2cb12133d600dc9eb8721555211f2c721f38f112f41d9c3095e4b2c82e6  project_state/runs/GS-102-transient-refined-cfl085-v365-bracket-20260512/data/engine.log
27f1d28139c8233af64014d0b910c2abd0da3e7fc809f117041f9fcaa7697205  project_state/graph_executor/GS-102-transient-refined-cfl085-v365-bracket-20260512/ballistic/ballistic_metrics.json
770c2570c9662facdf8e4e40b5477afb10916d3e324e0c45c4dc9bfed1995324  project_state/graph_executor/GS-102-transient-refined-cfl085-v365-bracket-20260512/visualization/openradioss_animation_manifest.json
c25518ad5eebd46df3c3a5b61bbc2cded35d9c37640cd3ba75706b23086a191c  project_state/graph_executor/GS-102-transient-refined-cfl085-v365-bracket-20260512/visualization/openradioss_animation.gif
```

## Limitations

- Tier 1 only: no signed validation, no benchmark comparison, no tolerance
  agreement, and no independent reviewer signoff.
- This is a candidate workflow proof, not a locked validation configuration.
- Energy audit is partial unless future extraction adds plastic dissipation,
  hourglass energy, and contact friction to the metrics sidecar.
