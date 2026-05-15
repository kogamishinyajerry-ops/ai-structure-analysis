# GS-102 transient candidate run - GS-102-transient-refined-v385-probe-20260512

> Status: Tier 1 engineering candidate.
> Solver: OpenRadioss via `openradioss-local-arm64:latest`.
> Claim boundary: not signed validation; not benchmark agreement.

## Purpose

Run a real OpenRadioss transient structural candidate for projectile impact on
a steel plate. Runtime decks and solver outputs live under `project_state/`.
This script refuses runtime writes inside `golden_samples/**`.

## Candidate setup

- Source deck directory: `golden_samples/GS-102-refined-candidate/data`
- Runtime deck directory: `project_state/runs/GS-102-transient-refined-v385-probe-20260512/data`
- Projectile initial velocity: `385 m/s`
- Projectile mass used by metrics: `0.005024 kg`
- Projectile node id range used by metrics: `1..27`

## Solver evidence

- Starter errors / warnings: `0` / `6`
- Engine normal termination: `True`
- Engine cycle count: `11459`
- Animation frame count: `150`
- Last-frame live solids: `71 / 80`
- Element deletion events:
  - element `23` at `3.3408E-02 ms`
  - element `30` at `3.3419E-02 ms`
  - element `24` at `3.3455E-02 ms`
  - element `29` at `3.3514E-02 ms`
  - element `22` at `1.1012E-01 ms`
  - element `25` at `1.1976E-01 ms`
  - element `31` at `1.2118E-01 ms`
  - element `28` at `1.2566E-01 ms`
  - element `36` at `1.2668E-01 ms`

## Candidate metrics

- `perforation_marker`: `embedded_candidate`
- `projectile_initial_velocity_m_per_s`: `385.0`
- `residual_velocity_candidate_m_per_s`: `1.988066`
- Metrics sidecar: `project_state/graph_executor/GS-102-transient-refined-v385-probe-20260512/ballistic/ballistic_metrics.json`

## Crossing and energy evidence

- `crossing_status`: `partial_candidate`
- `front_face_crossed`: `True`
- `back_face_crossed`: `False`
- `first_back_face_crossing_t_s`: `None`
- `velocity_trace_sample_count`: `150`
- `velocity_trace_final_speed_m_per_s`: `1.988066122`
- `partial_energy_audit_status`: `partial_candidate`
- `partial_energy_missing_terms`: `plastic_dissipation_j, contact_friction_j, hourglass_energy_j`

## Visualization artifacts

- GIF: `project_state/graph_executor/GS-102-transient-refined-v385-probe-20260512/visualization/openradioss_animation.gif`
- Visualization manifest: `project_state/graph_executor/GS-102-transient-refined-v385-probe-20260512/visualization/openradioss_animation_manifest.json`

## Artifact hashes

```text
15a86ef9c1ce9df14fcf1df5ac1c4d131a3fb9cfdb8abad3ccdc88047fe47eba  project_state/runs/GS-102-transient-refined-v385-probe-20260512/data/model_00_0000.rad
f792facf84aabea81a534977af08ada59c38cdae77657e4ea2aafd1a1ff50243  project_state/runs/GS-102-transient-refined-v385-probe-20260512/data/model_00_0001.rad
403391d97ae46c6abd49bae28bcd2def13dea32a061635432942916d47fafc4e  project_state/runs/GS-102-transient-refined-v385-probe-20260512/data/starter.log
31add4f8a7a7a0288e3afd4054e94e56cb22eb7e2771a87321abc76ef142bfed  project_state/runs/GS-102-transient-refined-v385-probe-20260512/data/engine.log
523c815e6062ab3a9e47991a1c787446426571324c846501ab3734f0011db8a1  project_state/graph_executor/GS-102-transient-refined-v385-probe-20260512/ballistic/ballistic_metrics.json
cacccd0c8dd1fa9b9b14651dd316743137f8a72653edd8c41eae9c3135af0f00  project_state/graph_executor/GS-102-transient-refined-v385-probe-20260512/visualization/openradioss_animation_manifest.json
e24828be0928526fb8261ffe33ae2ecda66b8cfc3bb467a2142faeaefcd641cc  project_state/graph_executor/GS-102-transient-refined-v385-probe-20260512/visualization/openradioss_animation.gif
```

## Limitations

- Tier 1 only: no signed validation, no benchmark comparison, no tolerance
  agreement, and no independent reviewer signoff.
- This is a candidate workflow proof, not a locked validation configuration.
- Energy audit is partial unless future extraction adds plastic dissipation,
  hourglass energy, and contact friction to the metrics sidecar.
