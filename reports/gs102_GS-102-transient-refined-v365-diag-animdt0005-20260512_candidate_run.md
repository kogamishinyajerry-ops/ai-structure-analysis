# GS-102 transient candidate run - GS-102-transient-refined-v365-diag-animdt0005-20260512

> Status: Tier 1 engineering candidate.
> Solver: OpenRadioss via `openradioss-local-arm64:latest`.
> Claim boundary: not signed validation; not benchmark agreement.

## Purpose

Run a real OpenRadioss transient structural candidate for projectile impact on
a steel plate. Runtime decks and solver outputs live under `project_state/`.
This script refuses runtime writes inside `golden_samples/**`.

## Candidate setup

- Source deck directory: `project_state/diagnostic_sources/GS-102-v365-anim_dt_0005/data`
- Runtime deck directory: `project_state/runs/GS-102-transient-refined-v365-diag-animdt0005-20260512/data`
- Projectile initial velocity: `365 m/s`
- Projectile mass used by metrics: `0.005024 kg`
- Projectile node id range used by metrics: `1..27`

## Solver evidence

- Starter errors / warnings: `0` / `6`
- Engine normal termination: `True`
- Engine cycle count: `3672`
- Animation frame count: `300`
- Last-frame live solids: `76 / 80`
- Element deletion events:
  - element `23` at `3.5910E-02 ms`
  - element `29` at `3.5910E-02 ms`
  - element `24` at `3.5910E-02 ms`
  - element `30` at `3.5910E-02 ms`

## Candidate metrics

- `perforation_marker`: `perforated_candidate`
- `projectile_initial_velocity_m_per_s`: `365.0`
- `residual_velocity_candidate_m_per_s`: `34.501057`
- Metrics sidecar: `project_state/graph_executor/GS-102-transient-refined-v365-diag-animdt0005-20260512/ballistic/ballistic_metrics.json`

## Crossing and energy evidence

- `crossing_status`: `candidate_observed`
- `front_face_crossed`: `True`
- `back_face_crossed`: `True`
- `first_back_face_crossing_t_s`: `7.102e-05`
- `velocity_trace_sample_count`: `300`
- `velocity_trace_final_speed_m_per_s`: `34.501057457`
- `partial_energy_audit_status`: `partial_candidate`
- `partial_energy_missing_terms`: `plastic_dissipation_j, contact_friction_j, hourglass_energy_j`

## Visualization artifacts

- GIF: `project_state/graph_executor/GS-102-transient-refined-v365-diag-animdt0005-20260512/visualization/openradioss_animation.gif`
- Visualization manifest: `project_state/graph_executor/GS-102-transient-refined-v365-diag-animdt0005-20260512/visualization/openradioss_animation_manifest.json`

## Artifact hashes

```text
2253b6a6c0e9100032ca7fdb85c6f97034d663c33a5330ba58bd939a160d950e  project_state/runs/GS-102-transient-refined-v365-diag-animdt0005-20260512/data/model_00_0000.rad
aa3f316c42bb47856acc01953da99345ad1eb3e9d9241674ce511cb8551698b2  project_state/runs/GS-102-transient-refined-v365-diag-animdt0005-20260512/data/model_00_0001.rad
21dcac1c7fb8eafc78af80d9a109eba79481bd31f5563eaa7b9a9000f3b5c32b  project_state/runs/GS-102-transient-refined-v365-diag-animdt0005-20260512/data/starter.log
bfa1a6681c69ba2ef84c8dfe168a880691a152632d50ec2b526f8ff8461613ad  project_state/runs/GS-102-transient-refined-v365-diag-animdt0005-20260512/data/engine.log
6b33592ed262e0b13ee6b2979187f021332d577de429350e67b7d58240b37b6b  project_state/graph_executor/GS-102-transient-refined-v365-diag-animdt0005-20260512/ballistic/ballistic_metrics.json
356631f5d4e9517b7a3a361a40ba9eee486393a4a61080aa603b0650cbd6fff9  project_state/graph_executor/GS-102-transient-refined-v365-diag-animdt0005-20260512/visualization/openradioss_animation_manifest.json
0e3f4fff97608e3dfe7437e684d01fbe2f2117c5cc47421d303ac91db91e8d9b  project_state/graph_executor/GS-102-transient-refined-v365-diag-animdt0005-20260512/visualization/openradioss_animation.gif
```

## Limitations

- Tier 1 only: no signed validation, no benchmark comparison, no tolerance
  agreement, and no independent reviewer signoff.
- This is a candidate workflow proof, not a locked validation configuration.
- Energy audit is partial unless future extraction adds plastic dissipation,
  hourglass energy, and contact friction to the metrics sidecar.
