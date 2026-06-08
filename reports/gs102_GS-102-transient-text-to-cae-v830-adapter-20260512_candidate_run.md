# GS-102 transient candidate run - GS-102-transient-text-to-cae-v830-adapter-20260512

> Status: Tier 1 engineering candidate.
> Solver: OpenRadioss via `openradioss-local-arm64:latest`.
> Claim boundary: not signed validation; not benchmark agreement.

## Purpose

Run a real OpenRadioss transient structural candidate for projectile impact on
a candidate plate. Runtime decks and solver outputs live under `project_state/`.
This script refuses runtime writes inside `golden_samples/**`.

## Candidate setup

- Source deck directory: `project_state/diagnostic_sources/GS-102-text-to-cae-openradioss-v1/data`
- Runtime deck directory: `project_state/runs/GS-102-transient-text-to-cae-v830-adapter-20260512/data`
- Projectile initial velocity: `830 m/s`
- Projectile mass used by metrics: `0.005024 kg`
- Projectile node id range used by metrics: `1..27`

## Solver evidence

- Starter errors / warnings: `0` / `6`
- Engine normal termination: `True`
- Engine cycle count: `14645`
- Animation frame count: `240`
- Last-frame live solids: `68 / 80`
- Element deletion events:
  - element `24` at `1.5622E-02 ms`
  - element `23` at `1.5690E-02 ms`
  - element `29` at `1.6174E-02 ms`
  - element `30` at `1.6224E-02 ms`
  - element `36` at `5.3852E-02 ms`
  - element `17` at `5.6275E-02 ms`
  - element `16` at `6.2295E-02 ms`
  - element `22` at `6.5315E-02 ms`
  - element `35` at `6.5749E-02 ms`
  - element `28` at `6.6344E-02 ms`
  - element `25` at `6.7075E-02 ms`
  - element `31` at `6.7824E-02 ms`

## Candidate metrics

- `perforation_marker`: `perforated_candidate`
- `projectile_initial_velocity_m_per_s`: `830.0`
- `residual_velocity_candidate_m_per_s`: `74.665064`
- Metrics sidecar: `project_state/graph_executor/GS-102-transient-text-to-cae-v830-adapter-20260512/ballistic/ballistic_metrics.json`

## Crossing and energy evidence

- `crossing_status`: `candidate_observed`
- `front_face_crossed`: `True`
- `back_face_crossed`: `True`
- `first_back_face_crossing_t_s`: `3.267e-05`
- `velocity_trace_sample_count`: `240`
- `velocity_trace_final_speed_m_per_s`: `74.665064372`
- `partial_energy_audit_status`: `partial_candidate`
- `partial_energy_missing_terms`: `plastic_dissipation_j, contact_friction_j, hourglass_energy_j`

## Visualization artifacts

- GIF: `project_state/graph_executor/GS-102-transient-text-to-cae-v830-adapter-20260512/visualization/openradioss_animation.gif`
- Visualization manifest: `project_state/graph_executor/GS-102-transient-text-to-cae-v830-adapter-20260512/visualization/openradioss_animation_manifest.json`

## Artifact hashes

```text
79e24848c1cf3d1d2d71924f38592b802c52d610350a9cc18a0b69a19d503279  project_state/runs/GS-102-transient-text-to-cae-v830-adapter-20260512/data/model_00_0000.rad
cf9fe5e5215f5495735c7b47745306b6090a49b7be684f9651fb8ef108d810d7  project_state/runs/GS-102-transient-text-to-cae-v830-adapter-20260512/data/model_00_0001.rad
20be42461513bb956025e773d2d4f67c8ac6d6c91f7b496051403d8c88a53883  project_state/runs/GS-102-transient-text-to-cae-v830-adapter-20260512/data/starter.log
39017e6ba3e65154cd31667b07e5b4589f9f09fde76ed6335d9942aa95e84de8  project_state/runs/GS-102-transient-text-to-cae-v830-adapter-20260512/data/engine.log
2b6a5a7290f2252dc42594c4d65a4ef4cd4871d765f3acd9db9a29126ccd008c  project_state/graph_executor/GS-102-transient-text-to-cae-v830-adapter-20260512/ballistic/ballistic_metrics.json
e733f814a5872162ebfcafd6ad6669ff313355405dd81910850b5f2b9e9bd766  project_state/graph_executor/GS-102-transient-text-to-cae-v830-adapter-20260512/visualization/openradioss_animation_manifest.json
5e62c81d2bce1853930d370e80fb7f3bffbdf4c62a926994860ddb3b3e23188a  project_state/graph_executor/GS-102-transient-text-to-cae-v830-adapter-20260512/visualization/openradioss_animation.gif
```

## Limitations

- Tier 1 only: no signed validation, no benchmark comparison, no tolerance
  agreement, and no independent reviewer signoff.
- This is a candidate workflow proof, not a locked validation configuration.
- Energy audit is partial unless future extraction adds plastic dissipation,
  hourglass energy, and contact friction to the metrics sidecar.
