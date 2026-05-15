# GS-102 transient candidate run - GS-102-transient-refined-v485-probe-20260512

> Status: Tier 1 engineering candidate.
> Solver: OpenRadioss via `openradioss-local-arm64:latest`.
> Claim boundary: not signed validation; not benchmark agreement.

## Purpose

Run a real OpenRadioss transient structural candidate for projectile impact on
a steel plate. Runtime decks and solver outputs live under `project_state/`.
This script refuses runtime writes inside `golden_samples/**`.

## Candidate setup

- Source deck directory: `golden_samples/GS-102-refined-candidate/data`
- Runtime deck directory: `project_state/runs/GS-102-transient-refined-v485-probe-20260512/data`
- Projectile initial velocity: `485 m/s`
- Projectile mass used by metrics: `0.005024 kg`
- Projectile node id range used by metrics: `1..27`

## Solver evidence

- Starter errors / warnings: `0` / `6`
- Engine normal termination: `True`
- Engine cycle count: `12589`
- Animation frame count: `150`
- Last-frame live solids: `64 / 80`
- Element deletion events:
  - element `24` at `2.6373E-02 ms`
  - element `29` at `2.6495E-02 ms`
  - element `30` at `2.6513E-02 ms`
  - element `23` at `2.6557E-02 ms`
  - element `17` at `8.1924E-02 ms`
  - element `31` at `8.5133E-02 ms`
  - element `28` at `8.7127E-02 ms`
  - element `36` at `9.8125E-02 ms`
  - element `18` at `1.0266E-01 ms`
  - element `25` at `1.0283E-01 ms`
  - element `22` at `1.0552E-01 ms`
  - element `35` at `1.1143E-01 ms`
  - element `60` at `1.3268E-01 ms`
  - element `59` at `1.3491E-01 ms`
  - element `66` at `1.3953E-01 ms`
  - element `65` at `1.4262E-01 ms`

## Candidate metrics

- `perforation_marker`: `embedded_candidate`
- `projectile_initial_velocity_m_per_s`: `485.0`
- `residual_velocity_candidate_m_per_s`: `11.857689`
- Metrics sidecar: `project_state/graph_executor/GS-102-transient-refined-v485-probe-20260512/ballistic/ballistic_metrics.json`

## Crossing and energy evidence

- `crossing_status`: `partial_candidate`
- `front_face_crossed`: `True`
- `back_face_crossed`: `False`
- `first_back_face_crossing_t_s`: `None`
- `velocity_trace_sample_count`: `150`
- `velocity_trace_final_speed_m_per_s`: `11.857688591`
- `partial_energy_audit_status`: `partial_candidate`
- `partial_energy_missing_terms`: `plastic_dissipation_j, contact_friction_j, hourglass_energy_j`

## Visualization artifacts

- GIF: `project_state/graph_executor/GS-102-transient-refined-v485-probe-20260512/visualization/openradioss_animation.gif`
- Visualization manifest: `project_state/graph_executor/GS-102-transient-refined-v485-probe-20260512/visualization/openradioss_animation_manifest.json`

## Artifact hashes

```text
a58f4795686db3e2dbd9f8c1cbdecd148e858de5208b6673202bf70e46425a54  project_state/runs/GS-102-transient-refined-v485-probe-20260512/data/model_00_0000.rad
f792facf84aabea81a534977af08ada59c38cdae77657e4ea2aafd1a1ff50243  project_state/runs/GS-102-transient-refined-v485-probe-20260512/data/model_00_0001.rad
8927314e7360bf9d11387bdbec8381333c4ee70d993d585b690267cd4c7e5e6d  project_state/runs/GS-102-transient-refined-v485-probe-20260512/data/starter.log
dbc5b865b03436cd2c05f89061e12a2db084051eb8567f3e1d3c475af98820d5  project_state/runs/GS-102-transient-refined-v485-probe-20260512/data/engine.log
a4c8e6a8c771a69cc64f2809932cac2ffe6d0c38a004596f1a8bec891a6dd1c0  project_state/graph_executor/GS-102-transient-refined-v485-probe-20260512/ballistic/ballistic_metrics.json
de6d24a34054d76e53f9679d5c6a4c2c589f4491c028402c80703757278df0a6  project_state/graph_executor/GS-102-transient-refined-v485-probe-20260512/visualization/openradioss_animation_manifest.json
8aaad6246a99f6071d3af994f10cbd3c937aed82a4eadcc2c3b540a6a3e6ba9e  project_state/graph_executor/GS-102-transient-refined-v485-probe-20260512/visualization/openradioss_animation.gif
```

## Limitations

- Tier 1 only: no signed validation, no benchmark comparison, no tolerance
  agreement, and no independent reviewer signoff.
- This is a candidate workflow proof, not a locked validation configuration.
- Energy audit is partial unless future extraction adds plastic dissipation,
  hourglass energy, and contact friction to the metrics sidecar.
