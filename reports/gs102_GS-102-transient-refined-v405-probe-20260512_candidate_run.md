# GS-102 transient candidate run - GS-102-transient-refined-v405-probe-20260512

> Status: Tier 1 engineering candidate.
> Solver: OpenRadioss via `openradioss-local-arm64:latest`.
> Claim boundary: not signed validation; not benchmark agreement.

## Purpose

Run a real OpenRadioss transient structural candidate for projectile impact on
a steel plate. Runtime decks and solver outputs live under `project_state/`.
This script refuses runtime writes inside `golden_samples/**`.

## Candidate setup

- Source deck directory: `golden_samples/GS-102-refined-candidate/data`
- Runtime deck directory: `project_state/runs/GS-102-transient-refined-v405-probe-20260512/data`
- Projectile initial velocity: `405 m/s`
- Projectile mass used by metrics: `0.005024 kg`
- Projectile node id range used by metrics: `1..27`

## Solver evidence

- Starter errors / warnings: `0` / `6`
- Engine normal termination: `True`
- Engine cycle count: `5185`
- Animation frame count: `150`
- Last-frame live solids: `72 / 80`
- Element deletion events:
  - element `23` at `3.1628E-02 ms`
  - element `29` at `3.1628E-02 ms`
  - element `24` at `3.1628E-02 ms`
  - element `30` at `3.1628E-02 ms`
  - element `17` at `1.0953E-01 ms`
  - element `35` at `1.0953E-01 ms`
  - element `18` at `1.1413E-01 ms`
  - element `36` at `1.1413E-01 ms`

## Candidate metrics

- `perforation_marker`: `embedded_candidate`
- `projectile_initial_velocity_m_per_s`: `405.0`
- `residual_velocity_candidate_m_per_s`: `14.932447`
- Metrics sidecar: `project_state/graph_executor/GS-102-transient-refined-v405-probe-20260512/ballistic/ballistic_metrics.json`

## Crossing and energy evidence

- `crossing_status`: `partial_candidate`
- `front_face_crossed`: `True`
- `back_face_crossed`: `False`
- `first_back_face_crossing_t_s`: `None`
- `velocity_trace_sample_count`: `150`
- `velocity_trace_final_speed_m_per_s`: `14.9324473`
- `partial_energy_audit_status`: `partial_candidate`
- `partial_energy_missing_terms`: `plastic_dissipation_j, contact_friction_j, hourglass_energy_j`

## Visualization artifacts

- GIF: `project_state/graph_executor/GS-102-transient-refined-v405-probe-20260512/visualization/openradioss_animation.gif`
- Visualization manifest: `project_state/graph_executor/GS-102-transient-refined-v405-probe-20260512/visualization/openradioss_animation_manifest.json`

## Artifact hashes

```text
f12bde6b55d4132043d58a82af42cafa7dc34c8b167826efd24b1f148ee70c86  project_state/runs/GS-102-transient-refined-v405-probe-20260512/data/model_00_0000.rad
f792facf84aabea81a534977af08ada59c38cdae77657e4ea2aafd1a1ff50243  project_state/runs/GS-102-transient-refined-v405-probe-20260512/data/model_00_0001.rad
27e14de0a045e0d39d77f3e84cc2d18af03ee5259f8282972d1014a06526bd13  project_state/runs/GS-102-transient-refined-v405-probe-20260512/data/starter.log
861b3c6cfd4c3540ecc97b82a3377161ea2fb6b898a06fa266ac48cafe9ed0dd  project_state/runs/GS-102-transient-refined-v405-probe-20260512/data/engine.log
d170e79b1a9380e57eb15df7aedc68e3ad926ccd12037341fbe33cfb670b2d66  project_state/graph_executor/GS-102-transient-refined-v405-probe-20260512/ballistic/ballistic_metrics.json
46b3ba491d2106a5a89a6258e946e54e69d37942768feb4db7dcebdbdf825023  project_state/graph_executor/GS-102-transient-refined-v405-probe-20260512/visualization/openradioss_animation_manifest.json
4d1aeba09deb521221e240bf300e406087bb28b6234280ff5941f6241fafe33b  project_state/graph_executor/GS-102-transient-refined-v405-probe-20260512/visualization/openradioss_animation.gif
```

## Limitations

- Tier 1 only: no signed validation, no benchmark comparison, no tolerance
  agreement, and no independent reviewer signoff.
- This is a candidate workflow proof, not a locked validation configuration.
- Energy audit is partial unless future extraction adds plastic dissipation,
  hourglass energy, and contact friction to the metrics sidecar.
