# GS-102 transient candidate run - GS-102-transient-refined-v325-probe-20260512

> Status: Tier 1 engineering candidate.
> Solver: OpenRadioss via `openradioss-local-arm64:latest`.
> Claim boundary: not signed validation; not benchmark agreement.

## Purpose

Run a real OpenRadioss transient structural candidate for projectile impact on
a steel plate. Runtime decks and solver outputs live under `project_state/`.
This script refuses runtime writes inside `golden_samples/**`.

## Candidate setup

- Source deck directory: `golden_samples/GS-102-refined-candidate/data`
- Runtime deck directory: `project_state/runs/GS-102-transient-refined-v325-probe-20260512/data`
- Projectile initial velocity: `325 m/s`
- Projectile mass used by metrics: `0.005024 kg`
- Projectile node id range used by metrics: `1..27`

## Solver evidence

- Starter errors / warnings: `0` / `6`
- Engine normal termination: `True`
- Engine cycle count: `4051`
- Animation frame count: `150`
- Last-frame live solids: `76 / 80`
- Element deletion events:
  - element `23` at `3.9215E-02 ms`
  - element `29` at `3.9215E-02 ms`
  - element `24` at `3.9215E-02 ms`
  - element `30` at `3.9215E-02 ms`

## Candidate metrics

- `perforation_marker`: `embedded_candidate`
- `projectile_initial_velocity_m_per_s`: `325.0`
- `residual_velocity_candidate_m_per_s`: `5.614325`
- Metrics sidecar: `project_state/graph_executor/GS-102-transient-refined-v325-probe-20260512/ballistic/ballistic_metrics.json`

## Crossing and energy evidence

- `crossing_status`: `partial_candidate`
- `front_face_crossed`: `True`
- `back_face_crossed`: `False`
- `first_back_face_crossing_t_s`: `None`
- `velocity_trace_sample_count`: `150`
- `velocity_trace_final_speed_m_per_s`: `5.614325166`
- `partial_energy_audit_status`: `partial_candidate`
- `partial_energy_missing_terms`: `plastic_dissipation_j, contact_friction_j, hourglass_energy_j`

## Visualization artifacts

- GIF: `project_state/graph_executor/GS-102-transient-refined-v325-probe-20260512/visualization/openradioss_animation.gif`
- Visualization manifest: `project_state/graph_executor/GS-102-transient-refined-v325-probe-20260512/visualization/openradioss_animation_manifest.json`

## Artifact hashes

```text
bbdc31718015f4bf545d0a6edea514f3097a9a38402745558a1ea5b88aa3fc3f  project_state/runs/GS-102-transient-refined-v325-probe-20260512/data/model_00_0000.rad
f792facf84aabea81a534977af08ada59c38cdae77657e4ea2aafd1a1ff50243  project_state/runs/GS-102-transient-refined-v325-probe-20260512/data/model_00_0001.rad
6ea1ef5962c907c88dda4aaa740a7e2e310c7d1db5eebeb57f90e9a2e3047071  project_state/runs/GS-102-transient-refined-v325-probe-20260512/data/starter.log
e14f5ab65b1820bfe16525293c440d924842a3cbf954fb46c8d8206f741772f2  project_state/runs/GS-102-transient-refined-v325-probe-20260512/data/engine.log
e7aef4e9573e76fd8a32aa396a52b3309cd8704ec19f50a5a00d223f617fa57b  project_state/graph_executor/GS-102-transient-refined-v325-probe-20260512/ballistic/ballistic_metrics.json
b559cdcad700781ebaa1b3920f390718165feb55032c9add211deb3f27c7fa82  project_state/graph_executor/GS-102-transient-refined-v325-probe-20260512/visualization/openradioss_animation_manifest.json
737493f6ed7145944349193f28c22a0e3637fdfd252217cfa7ef3c45f6a91ffd  project_state/graph_executor/GS-102-transient-refined-v325-probe-20260512/visualization/openradioss_animation.gif
```

## Limitations

- Tier 1 only: no signed validation, no benchmark comparison, no tolerance
  agreement, and no independent reviewer signoff.
- This is a candidate workflow proof, not a locked validation configuration.
- Energy audit is partial unless future extraction adds plastic dissipation,
  hourglass energy, and contact friction to the metrics sidecar.
