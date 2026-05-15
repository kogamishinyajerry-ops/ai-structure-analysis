# GS-102 transient candidate run - GS-102-transient-refined-v285-bracket-20260512

> Status: Tier 1 engineering candidate.
> Solver: OpenRadioss via `openradioss-local-arm64:latest`.
> Claim boundary: not signed validation; not benchmark agreement.

## Purpose

Run a real OpenRadioss transient structural candidate for projectile impact on
a steel plate. Runtime decks and solver outputs live under `project_state/`.
This script refuses runtime writes inside `golden_samples/**`.

## Candidate setup

- Source deck directory: `golden_samples/GS-102-refined-candidate/data`
- Runtime deck directory: `project_state/runs/GS-102-transient-refined-v285-bracket-20260512/data`
- Projectile initial velocity: `285 m/s`
- Projectile mass used by metrics: `0.005024 kg`
- Projectile node id range used by metrics: `1..27`

## Solver evidence

- Starter errors / warnings: `0` / `6`
- Engine normal termination: `True`
- Engine cycle count: `7448`
- Animation frame count: `150`
- Last-frame live solids: `76 / 80`
- Element deletion events:
  - element `23` at `4.4484E-02 ms`
  - element `30` at `4.4487E-02 ms`
  - element `24` at `4.4890E-02 ms`
  - element `29` at `4.4894E-02 ms`

## Candidate metrics

- `perforation_marker`: `embedded_candidate`
- `projectile_initial_velocity_m_per_s`: `285.0`
- `residual_velocity_candidate_m_per_s`: `4.667462`
- Metrics sidecar: `project_state/graph_executor/GS-102-transient-refined-v285-bracket-20260512/ballistic/ballistic_metrics.json`

## Crossing and energy evidence

- `crossing_status`: `partial_candidate`
- `front_face_crossed`: `True`
- `back_face_crossed`: `False`
- `first_back_face_crossing_t_s`: `None`
- `velocity_trace_sample_count`: `150`
- `velocity_trace_final_speed_m_per_s`: `4.667462355`
- `partial_energy_audit_status`: `partial_candidate`
- `partial_energy_missing_terms`: `plastic_dissipation_j, contact_friction_j, hourglass_energy_j`

## Visualization artifacts

- GIF: `project_state/graph_executor/GS-102-transient-refined-v285-bracket-20260512/visualization/openradioss_animation.gif`
- Visualization manifest: `project_state/graph_executor/GS-102-transient-refined-v285-bracket-20260512/visualization/openradioss_animation_manifest.json`

## Artifact hashes

```text
b33130875d9317ec69ef4a08f5e6f691bd55e0c085be34f691398f15fbea2522  project_state/runs/GS-102-transient-refined-v285-bracket-20260512/data/model_00_0000.rad
f792facf84aabea81a534977af08ada59c38cdae77657e4ea2aafd1a1ff50243  project_state/runs/GS-102-transient-refined-v285-bracket-20260512/data/model_00_0001.rad
3f79541cc111a558a2954b9a03499c29f0d5604cbfe5351b26e7d7d4ccb37dcc  project_state/runs/GS-102-transient-refined-v285-bracket-20260512/data/starter.log
6867533714efd4d016ad8f104dc1a87c48389dba50a4d938e99fe24cf8e538df  project_state/runs/GS-102-transient-refined-v285-bracket-20260512/data/engine.log
92d61676c5d377883eab7bef9e4792b9849113df0ed412f8173f34c0a33b00f1  project_state/graph_executor/GS-102-transient-refined-v285-bracket-20260512/ballistic/ballistic_metrics.json
21d5d06622455790c064a695f5951bfece657fbaf5ba77491720d535ac2d1ea0  project_state/graph_executor/GS-102-transient-refined-v285-bracket-20260512/visualization/openradioss_animation_manifest.json
0058bccf3e1df7027c40c1e86f8c2968012739f2ce9c8d0950c70f1362fb9336  project_state/graph_executor/GS-102-transient-refined-v285-bracket-20260512/visualization/openradioss_animation.gif
```

## Limitations

- Tier 1 only: no signed validation, no benchmark comparison, no tolerance
  agreement, and no independent reviewer signoff.
- This is a candidate workflow proof, not a locked validation configuration.
- Energy audit is partial unless future extraction adds plastic dissipation,
  hourglass energy, and contact friction to the metrics sidecar.
