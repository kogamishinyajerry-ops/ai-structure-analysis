# GS-102 transient candidate run - GS-102-transient-refined-v600-bracket-20260512

> Status: Tier 1 engineering candidate.
> Solver: OpenRadioss via `openradioss-local-arm64:latest`.
> Claim boundary: not signed validation; not benchmark agreement.

## Purpose

Run a real OpenRadioss transient structural candidate for projectile impact on
a steel plate. Runtime decks and solver outputs live under `project_state/`.
This script refuses runtime writes inside `golden_samples/**`.

## Candidate setup

- Source deck directory: `golden_samples/GS-102-refined-candidate/data`
- Runtime deck directory: `project_state/runs/GS-102-transient-refined-v600-bracket-20260512/data`
- Projectile initial velocity: `600 m/s`
- Projectile mass used by metrics: `0.005024 kg`
- Projectile node id range used by metrics: `1..27`

## Solver evidence

- Starter errors / warnings: `0` / `6`
- Engine normal termination: `True`
- Engine cycle count: `8831`
- Animation frame count: `150`
- Last-frame live solids: `68 / 80`
- Element deletion events:
  - element `29` at `2.1788E-02 ms`
  - element `23` at `2.1906E-02 ms`
  - element `24` at `2.1906E-02 ms`
  - element `30` at `2.1906E-02 ms`
  - element `18` at `8.4889E-02 ms`
  - element `35` at `1.0023E-01 ms`
  - element `59` at `1.3004E-01 ms`
  - element `60` at `1.3110E-01 ms`
  - element `66` at `1.3384E-01 ms`
  - element `34` at `1.3584E-01 ms`
  - element `65` at `1.3794E-01 ms`
  - element `67` at `1.4257E-01 ms`
  - element `61` at `1.4997E-01 ms`

## Candidate metrics

- `perforation_marker`: `perforated_candidate`
- `projectile_initial_velocity_m_per_s`: `600.0`
- `residual_velocity_candidate_m_per_s`: `52.676288`
- Metrics sidecar: `project_state/graph_executor/GS-102-transient-refined-v600-bracket-20260512/ballistic/ballistic_metrics.json`

## Crossing and energy evidence

- `crossing_status`: `candidate_observed`
- `front_face_crossed`: `True`
- `back_face_crossed`: `True`
- `first_back_face_crossing_t_s`: `4.9014e-05`
- `velocity_trace_sample_count`: `150`
- `velocity_trace_final_speed_m_per_s`: `52.67628783`
- `partial_energy_audit_status`: `partial_candidate`
- `partial_energy_missing_terms`: `plastic_dissipation_j, contact_friction_j, hourglass_energy_j`

## Visualization artifacts

- GIF: `project_state/graph_executor/GS-102-transient-refined-v600-bracket-20260512/visualization/openradioss_animation.gif`
- Visualization manifest: `project_state/graph_executor/GS-102-transient-refined-v600-bracket-20260512/visualization/openradioss_animation_manifest.json`

## Artifact hashes

```text
f5136cdb0af4734d7e0e352dfcc8167fcf35dfc58bbd972d770742f6bfc0b886  project_state/runs/GS-102-transient-refined-v600-bracket-20260512/data/model_00_0000.rad
f792facf84aabea81a534977af08ada59c38cdae77657e4ea2aafd1a1ff50243  project_state/runs/GS-102-transient-refined-v600-bracket-20260512/data/model_00_0001.rad
e7dd926e40a775d5b72524c23be5d882e8c570343988b75837f1c2a373b239e3  project_state/runs/GS-102-transient-refined-v600-bracket-20260512/data/starter.log
e2be7f1bcdfd201e663d118eb1ae25a5596dd6c73ac0260303383b88f604e9ba  project_state/runs/GS-102-transient-refined-v600-bracket-20260512/data/engine.log
f5f0c6e4fae6f5c64b6b8890278ea7af0d539e8c502fc676abb06473e6a5b68e  project_state/graph_executor/GS-102-transient-refined-v600-bracket-20260512/ballistic/ballistic_metrics.json
19683b85937f5ce15f7ed95e29340366c2e0d777bc024da0e6b197302a143f17  project_state/graph_executor/GS-102-transient-refined-v600-bracket-20260512/visualization/openradioss_animation_manifest.json
0db50816c87a763a6488837045a56733cca765d0d8415d1348366f2029d482ae  project_state/graph_executor/GS-102-transient-refined-v600-bracket-20260512/visualization/openradioss_animation.gif
```

## Limitations

- Tier 1 only: no signed validation, no benchmark comparison, no tolerance
  agreement, and no independent reviewer signoff.
- This is a candidate workflow proof, not a locked validation configuration.
- Energy audit is partial unless future extraction adds plastic dissipation,
  hourglass energy, and contact friction to the metrics sidecar.
