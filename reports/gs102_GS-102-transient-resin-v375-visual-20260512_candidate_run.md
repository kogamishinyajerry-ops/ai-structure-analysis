# GS-102 transient candidate run - GS-102-transient-resin-v375-visual-20260512

> Status: Tier 1 engineering candidate.
> Solver: OpenRadioss via `openradioss-local-arm64:latest`.
> Claim boundary: not signed validation; not benchmark agreement.

## Purpose

Run a real OpenRadioss transient structural candidate for projectile impact on
a candidate plate. Runtime decks and solver outputs live under `project_state/`.
This script refuses runtime writes inside `golden_samples/**`.

## Candidate setup

- Source deck directory: `project_state/diagnostic_sources/GS-102-resin-plate-v1/data`
- Runtime deck directory: `project_state/runs/GS-102-transient-resin-v375-visual-20260512/data`
- Projectile initial velocity: `375 m/s`
- Projectile mass used by metrics: `0.005024 kg`
- Projectile node id range used by metrics: `1..27`

## Solver evidence

- Starter errors / warnings: `0` / `5`
- Engine normal termination: `True`
- Engine cycle count: `644`
- Animation frame count: `74`
- Last-frame live solids: `8 / 80`
- Element deletion events:
  - element `23` at `1.9996E-03 ms`
  - element `29` at `1.9996E-03 ms`
  - element `24` at `1.9996E-03 ms`
  - element `30` at `1.9996E-03 ms`
  - element `59` at `3.9637E-03 ms`
  - element `65` at `3.9637E-03 ms`
  - element `60` at `3.9637E-03 ms`
  - element `66` at `3.9637E-03 ms`
  - element `22` at `6.3894E-03 ms`
  - element `58` at `6.3894E-03 ms`
  - element `17` at `6.3894E-03 ms`
  - element `53` at `6.3894E-03 ms`
  - element `28` at `6.3894E-03 ms`
  - element `64` at `6.3894E-03 ms`
  - element `18` at `6.3894E-03 ms`
  - element `54` at `6.3894E-03 ms`
  - element `35` at `6.3894E-03 ms`
  - element `71` at `6.3894E-03 ms`
  - element `36` at `6.3894E-03 ms`
  - element `72` at `6.3894E-03 ms`

## Candidate metrics

- `perforation_marker`: `perforated_candidate`
- `projectile_initial_velocity_m_per_s`: `375.0`
- `residual_velocity_candidate_m_per_s`: `230.138542`
- Metrics sidecar: `project_state/graph_executor/GS-102-transient-resin-v375-visual-20260512/ballistic/ballistic_metrics.json`

## Crossing and energy evidence

- `crossing_status`: `candidate_observed`
- `front_face_crossed`: `True`
- `back_face_crossed`: `True`
- `first_back_face_crossing_t_s`: `4.2178e-05`
- `velocity_trace_sample_count`: `74`
- `velocity_trace_final_speed_m_per_s`: `230.138541893`
- `partial_energy_audit_status`: `partial_candidate`
- `partial_energy_missing_terms`: `plastic_dissipation_j, contact_friction_j, hourglass_energy_j`

## Visualization artifacts

- GIF: `project_state/graph_executor/GS-102-transient-resin-v375-visual-20260512/visualization/openradioss_animation.gif`
- Visualization manifest: `project_state/graph_executor/GS-102-transient-resin-v375-visual-20260512/visualization/openradioss_animation_manifest.json`

## Artifact hashes

```text
3f89ed6e601ba68c223466f3cdfba1bf29f4c081f881a4920b6a9e1adcd1b9d0  project_state/runs/GS-102-transient-resin-v375-visual-20260512/data/model_00_0000.rad
f792facf84aabea81a534977af08ada59c38cdae77657e4ea2aafd1a1ff50243  project_state/runs/GS-102-transient-resin-v375-visual-20260512/data/model_00_0001.rad
defd89904f9ec3f71fdb766785d731d81520ee9a697c8e22cb4dc261319b7314  project_state/runs/GS-102-transient-resin-v375-visual-20260512/data/starter.log
f3b2a3519d880693a0f8fc9a7f8032a9707cb3a38c55c3ec5aec056d32d33771  project_state/runs/GS-102-transient-resin-v375-visual-20260512/data/engine.log
7bc10f72f0976aa021042b16d6e382d2069c6ff4bb24c4a5b0da6e99d88d01ec  project_state/graph_executor/GS-102-transient-resin-v375-visual-20260512/ballistic/ballistic_metrics.json
c9d5a380cfa9c49268614e424c398f8a9aeb8d8a70a55744ade487160bd65b61  project_state/graph_executor/GS-102-transient-resin-v375-visual-20260512/visualization/openradioss_animation_manifest.json
c2b227e2c34a9651827c0123713a571c5b28572c9637686c9d542edf8e1fbc1e  project_state/graph_executor/GS-102-transient-resin-v375-visual-20260512/visualization/openradioss_animation.gif
```

## Limitations

- Tier 1 only: no signed validation, no benchmark comparison, no tolerance
  agreement, and no independent reviewer signoff.
- This is a candidate workflow proof, not a locked validation configuration.
- Energy audit is partial unless future extraction adds plastic dissipation,
  hourglass energy, and contact friction to the metrics sidecar.
