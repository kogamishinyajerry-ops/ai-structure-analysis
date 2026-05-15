# GS-102 transient candidate run - GS-102-transient-refined-v365-diag-cfl100-20260512

> Status: Tier 1 engineering candidate.
> Solver: OpenRadioss via `openradioss-local-arm64:latest`.
> Claim boundary: not signed validation; not benchmark agreement.

## Purpose

Run a real OpenRadioss transient structural candidate for projectile impact on
a steel plate. Runtime decks and solver outputs live under `project_state/`.
This script refuses runtime writes inside `golden_samples/**`.

## Candidate setup

- Source deck directory: `project_state/diagnostic_sources/GS-102-v365-cfl_100/data`
- Runtime deck directory: `project_state/runs/GS-102-transient-refined-v365-diag-cfl100-20260512/data`
- Projectile initial velocity: `365 m/s`
- Projectile mass used by metrics: `0.005024 kg`
- Projectile node id range used by metrics: `1..27`

## Solver evidence

- Starter errors / warnings: `0` / `6`
- Engine normal termination: `True`
- Engine cycle count: `8496`
- Animation frame count: `150`
- Last-frame live solids: `71 / 80`
- Element deletion events:
  - element `30` at `3.4943E-02 ms`
  - element `23` at `3.5137E-02 ms`
  - element `29` at `3.5186E-02 ms`
  - element `24` at `3.5593E-02 ms`
  - element `28` at `1.1953E-01 ms`
  - element `22` at `1.2341E-01 ms`
  - element `31` at `1.2568E-01 ms`
  - element `18` at `1.3098E-01 ms`
  - element `36` at `1.3647E-01 ms`

## Candidate metrics

- `perforation_marker`: `embedded_candidate`
- `projectile_initial_velocity_m_per_s`: `365.0`
- `residual_velocity_candidate_m_per_s`: `15.076922`
- Metrics sidecar: `project_state/graph_executor/GS-102-transient-refined-v365-diag-cfl100-20260512/ballistic/ballistic_metrics.json`

## Crossing and energy evidence

- `crossing_status`: `partial_candidate`
- `front_face_crossed`: `True`
- `back_face_crossed`: `False`
- `first_back_face_crossing_t_s`: `None`
- `velocity_trace_sample_count`: `150`
- `velocity_trace_final_speed_m_per_s`: `15.076922171`
- `partial_energy_audit_status`: `partial_candidate`
- `partial_energy_missing_terms`: `plastic_dissipation_j, contact_friction_j, hourglass_energy_j`

## Visualization artifacts

- GIF: `project_state/graph_executor/GS-102-transient-refined-v365-diag-cfl100-20260512/visualization/openradioss_animation.gif`
- Visualization manifest: `project_state/graph_executor/GS-102-transient-refined-v365-diag-cfl100-20260512/visualization/openradioss_animation_manifest.json`

## Artifact hashes

```text
2253b6a6c0e9100032ca7fdb85c6f97034d663c33a5330ba58bd939a160d950e  project_state/runs/GS-102-transient-refined-v365-diag-cfl100-20260512/data/model_00_0000.rad
ba376e5499ccd8849d14f1499bb8d4d4b28230c032ac33147d6823d4dd865cbe  project_state/runs/GS-102-transient-refined-v365-diag-cfl100-20260512/data/model_00_0001.rad
6d88a6d4df6b44e7b769aaa4d7b6602981d6a2df86ee2411cbd7af00d76b08c3  project_state/runs/GS-102-transient-refined-v365-diag-cfl100-20260512/data/starter.log
5d7a048e67c7860eb3c909574f3fee94cba05ca2f911cff8fed47193880fc9ef  project_state/runs/GS-102-transient-refined-v365-diag-cfl100-20260512/data/engine.log
b454573d4572503301c42566eae702c22f7cea6f3656e59043828595bc99abc6  project_state/graph_executor/GS-102-transient-refined-v365-diag-cfl100-20260512/ballistic/ballistic_metrics.json
a8883a48a6e7579f695ed8a1e23c2b0267b91bcaef3cf208cee91a3633d31669  project_state/graph_executor/GS-102-transient-refined-v365-diag-cfl100-20260512/visualization/openradioss_animation_manifest.json
c06b1cccee4fcf84ea9b2c6c27295000767508a4afe822d36ea1a6b306ed2c46  project_state/graph_executor/GS-102-transient-refined-v365-diag-cfl100-20260512/visualization/openradioss_animation.gif
```

## Limitations

- Tier 1 only: no signed validation, no benchmark comparison, no tolerance
  agreement, and no independent reviewer signoff.
- This is a candidate workflow proof, not a locked validation configuration.
- Energy audit is partial unless future extraction adds plastic dissipation,
  hourglass energy, and contact friction to the metrics sidecar.
