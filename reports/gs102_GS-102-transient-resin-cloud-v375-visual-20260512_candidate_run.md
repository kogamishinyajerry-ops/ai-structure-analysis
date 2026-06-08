# GS-102 transient candidate run - GS-102-transient-resin-cloud-v375-visual-20260512

> Status: Tier 1 engineering candidate.
> Solver: OpenRadioss via `openradioss-local-arm64:latest`.
> Claim boundary: not signed validation; not benchmark agreement.

## Purpose

Run a real OpenRadioss transient structural candidate for projectile impact on
a candidate plate. Runtime decks and solver outputs live under `project_state/`.
This script refuses runtime writes inside `golden_samples/**`.

## Candidate setup

- Source deck directory: `project_state/diagnostic_sources/GS-102-resin-plate-v1/data`
- Runtime deck directory: `project_state/runs/GS-102-transient-resin-cloud-v375-visual-20260512/data`
- Projectile initial velocity: `375 m/s`
- Projectile mass used by metrics: `0.005024 kg`
- Projectile node id range used by metrics: `1..27`

## Solver evidence

- Starter errors / warnings: `0` / `4`
- Engine normal termination: `True`
- Engine cycle count: `22329`
- Animation frame count: `150`
- Last-frame live solids: `80 / 80`
- Element deletion events:
  - none recorded

## Candidate metrics

- `perforation_marker`: `perforated_candidate`
- `projectile_initial_velocity_m_per_s`: `375.0`
- `residual_velocity_candidate_m_per_s`: `60.093739`
- Metrics sidecar: `project_state/graph_executor/GS-102-transient-resin-cloud-v375-visual-20260512/ballistic/ballistic_metrics.json`

## Crossing and energy evidence

- `crossing_status`: `candidate_observed`
- `front_face_crossed`: `True`
- `back_face_crossed`: `True`
- `first_back_face_crossing_t_s`: `4.6001e-05`
- `velocity_trace_sample_count`: `150`
- `velocity_trace_final_speed_m_per_s`: `60.093738595`
- `partial_energy_audit_status`: `partial_candidate`
- `partial_energy_missing_terms`: `plastic_dissipation_j, contact_friction_j, hourglass_energy_j`

## Visualization artifacts

- GIF: `project_state/graph_executor/GS-102-transient-resin-cloud-v375-visual-20260512/visualization/openradioss_animation.gif`
- Visualization manifest: `project_state/graph_executor/GS-102-transient-resin-cloud-v375-visual-20260512/visualization/openradioss_animation_manifest.json`

## Artifact hashes

```text
76087a2848336b81c8ea1522ca72149d167a8df1cb97f858423432d175c58a7d  project_state/runs/GS-102-transient-resin-cloud-v375-visual-20260512/data/model_00_0000.rad
f792facf84aabea81a534977af08ada59c38cdae77657e4ea2aafd1a1ff50243  project_state/runs/GS-102-transient-resin-cloud-v375-visual-20260512/data/model_00_0001.rad
90367b6fa31310df9197d6e2db74abfa066d83ed4ad90f078a03431aef35fc5c  project_state/runs/GS-102-transient-resin-cloud-v375-visual-20260512/data/starter.log
05c21e24ee847d01e9ac8eea20bc894a538e3ac9943b5403d7d12c85a3e181cf  project_state/runs/GS-102-transient-resin-cloud-v375-visual-20260512/data/engine.log
132d1a5f4108efa9fb63b304231050a5b011216ddd6477605f4c82e3240e17f4  project_state/graph_executor/GS-102-transient-resin-cloud-v375-visual-20260512/ballistic/ballistic_metrics.json
9dc4ecbbe356149e3fe0b27c284f0fe20eca3b0e91a813aecc2a8c4325ee41b2  project_state/graph_executor/GS-102-transient-resin-cloud-v375-visual-20260512/visualization/openradioss_animation_manifest.json
be88351a579bf68062366b0d49523f0777e30e93aff71bd4d258ab95c74edcd8  project_state/graph_executor/GS-102-transient-resin-cloud-v375-visual-20260512/visualization/openradioss_animation.gif
```

## Limitations

- Tier 1 only: no signed validation, no benchmark comparison, no tolerance
  agreement, and no independent reviewer signoff.
- This is a candidate workflow proof, not a locked validation configuration.
- Energy audit is partial unless future extraction adds plastic dissipation,
  hourglass energy, and contact friction to the metrics sidecar.
