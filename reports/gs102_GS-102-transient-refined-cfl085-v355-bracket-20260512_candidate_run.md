# GS-102 transient candidate run - GS-102-transient-refined-cfl085-v355-bracket-20260512

> Status: Tier 1 engineering candidate.
> Solver: OpenRadioss via `openradioss-local-arm64:latest`.
> Claim boundary: not signed validation; not benchmark agreement.

## Purpose

Run a real OpenRadioss transient structural candidate for projectile impact on
a steel plate. Runtime decks and solver outputs live under `project_state/`.
This script refuses runtime writes inside `golden_samples/**`.

## Candidate setup

- Source deck directory: `project_state/diagnostic_sources/GS-102-v365-cfl_085/data`
- Runtime deck directory: `project_state/runs/GS-102-transient-refined-cfl085-v355-bracket-20260512/data`
- Projectile initial velocity: `355 m/s`
- Projectile mass used by metrics: `0.005024 kg`
- Projectile node id range used by metrics: `1..27`

## Solver evidence

- Starter errors / warnings: `0` / `6`
- Engine normal termination: `True`
- Engine cycle count: `6094`
- Animation frame count: `150`
- Last-frame live solids: `72 / 80`
- Element deletion events:
  - element `23` at `3.6195E-02 ms`
  - element `29` at `3.6195E-02 ms`
  - element `24` at `3.6195E-02 ms`
  - element `30` at `3.6195E-02 ms`
  - element `17` at `1.2119E-01 ms`
  - element `35` at `1.2166E-01 ms`
  - element `36` at `1.2532E-01 ms`
  - element `18` at `1.2549E-01 ms`

## Candidate metrics

- `perforation_marker`: `embedded_candidate`
- `projectile_initial_velocity_m_per_s`: `355.0`
- `residual_velocity_candidate_m_per_s`: `9.520614`
- Metrics sidecar: `project_state/graph_executor/GS-102-transient-refined-cfl085-v355-bracket-20260512/ballistic/ballistic_metrics.json`

## Crossing and energy evidence

- `crossing_status`: `partial_candidate`
- `front_face_crossed`: `True`
- `back_face_crossed`: `False`
- `first_back_face_crossing_t_s`: `None`
- `velocity_trace_sample_count`: `150`
- `velocity_trace_final_speed_m_per_s`: `9.520613564`
- `partial_energy_audit_status`: `partial_candidate`
- `partial_energy_missing_terms`: `plastic_dissipation_j, contact_friction_j, hourglass_energy_j`

## Visualization artifacts

- GIF: `project_state/graph_executor/GS-102-transient-refined-cfl085-v355-bracket-20260512/visualization/openradioss_animation.gif`
- Visualization manifest: `project_state/graph_executor/GS-102-transient-refined-cfl085-v355-bracket-20260512/visualization/openradioss_animation_manifest.json`

## Artifact hashes

```text
f6be6bbd7baca4690960ba043bdf194cfb91c0deae75082581e889f1a298f1c0  project_state/runs/GS-102-transient-refined-cfl085-v355-bracket-20260512/data/model_00_0000.rad
ce7efcec9772e9d2d132bbf4c86f88328255a3ee25bc5b8ae52663cf51945d91  project_state/runs/GS-102-transient-refined-cfl085-v355-bracket-20260512/data/model_00_0001.rad
2f269f5742b0718d989e8d8f5e3dc0cf862051aa823c3ad65895759753c33168  project_state/runs/GS-102-transient-refined-cfl085-v355-bracket-20260512/data/starter.log
25d08d693a137766335639a7fe5c58c1309d77858ea3c90bfcbdba47fe5af847  project_state/runs/GS-102-transient-refined-cfl085-v355-bracket-20260512/data/engine.log
eac12795734f295bceb666aba3a035c91e182886ccb5c8a1d61e5b1696cf6bef  project_state/graph_executor/GS-102-transient-refined-cfl085-v355-bracket-20260512/ballistic/ballistic_metrics.json
b89f5d5116e51d0e1b3540368e578e963532508a6703ee2c81580022c39db012  project_state/graph_executor/GS-102-transient-refined-cfl085-v355-bracket-20260512/visualization/openradioss_animation_manifest.json
cd5f808623b0cc4b128dd54fb5d0a4053ca85d0d69cf8112be82944761611fc0  project_state/graph_executor/GS-102-transient-refined-cfl085-v355-bracket-20260512/visualization/openradioss_animation.gif
```

## Limitations

- Tier 1 only: no signed validation, no benchmark comparison, no tolerance
  agreement, and no independent reviewer signoff.
- This is a candidate workflow proof, not a locked validation configuration.
- Energy audit is partial unless future extraction adds plastic dissipation,
  hourglass energy, and contact friction to the metrics sidecar.
