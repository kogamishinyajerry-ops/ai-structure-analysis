# GS-102 transient candidate run - GS-102-transient-refined-v520-explore-20260512

> Status: Tier 1 engineering candidate.
> Solver: OpenRadioss via `openradioss-local-arm64:latest`.
> Claim boundary: not signed validation; not benchmark agreement.

## Purpose

Run a real OpenRadioss transient structural candidate for projectile impact on
a steel plate. Runtime decks and solver outputs live under `project_state/`.
This script refuses runtime writes inside `golden_samples/**`.

## Candidate setup

- Source deck directory: `golden_samples/GS-102-refined-candidate/data`
- Runtime deck directory: `project_state/runs/GS-102-transient-refined-v520-explore-20260512/data`
- Projectile initial velocity: `520 m/s`
- Projectile mass used by metrics: `0.005024 kg`
- Projectile node id range used by metrics: `1..27`

## Solver evidence

- Starter errors / warnings: `0` / `6`
- Engine normal termination: `True`
- Engine cycle count: `12760`
- Animation frame count: `150`
- Last-frame live solids: `62 / 80`
- Element deletion events:
  - element `24` at `2.4818E-02 ms`
  - element `29` at `2.4832E-02 ms`
  - element `30` at `2.5193E-02 ms`
  - element `23` at `2.5312E-02 ms`
  - element `31` at `8.5972E-02 ms`
  - element `36` at `9.0387E-02 ms`
  - element `18` at `9.5953E-02 ms`
  - element `25` at `9.8811E-02 ms`
  - element `35` at `9.9597E-02 ms`
  - element `22` at `1.0039E-01 ms`
  - element `28` at `1.0199E-01 ms`
  - element `66` at `1.2703E-01 ms`
  - element `58` at `1.3316E-01 ms`
  - element `60` at `1.3445E-01 ms`
  - element `65` at `1.3494E-01 ms`
  - element `53` at `1.3623E-01 ms`
  - element `59` at `1.4284E-01 ms`
  - element `37` at `1.4671E-01 ms`

## Candidate metrics

- `perforation_marker`: `perforated_candidate`
- `projectile_initial_velocity_m_per_s`: `520.0`
- `residual_velocity_candidate_m_per_s`: `19.570806`
- Metrics sidecar: `project_state/graph_executor/GS-102-transient-refined-v520-explore-20260512/ballistic/ballistic_metrics.json`

## Crossing and energy evidence

- `crossing_status`: `candidate_observed`
- `front_face_crossed`: `True`
- `back_face_crossed`: `True`
- `first_back_face_crossing_t_s`: `0.000120109`
- `velocity_trace_sample_count`: `150`
- `velocity_trace_final_speed_m_per_s`: `19.570806025`
- `partial_energy_audit_status`: `partial_candidate`
- `partial_energy_missing_terms`: `plastic_dissipation_j, contact_friction_j, hourglass_energy_j`

## Visualization artifacts

- GIF: `project_state/graph_executor/GS-102-transient-refined-v520-explore-20260512/visualization/openradioss_animation.gif`
- Visualization manifest: `project_state/graph_executor/GS-102-transient-refined-v520-explore-20260512/visualization/openradioss_animation_manifest.json`

## Artifact hashes

```text
c87e95532c974a0efefba62e09393f044c1b1e4f7135afcf00230a0afdc5343d  project_state/runs/GS-102-transient-refined-v520-explore-20260512/data/model_00_0000.rad
f792facf84aabea81a534977af08ada59c38cdae77657e4ea2aafd1a1ff50243  project_state/runs/GS-102-transient-refined-v520-explore-20260512/data/model_00_0001.rad
ad2fba3d3bf32d1e4a9bc6bed61b1b107ac70a98283e59188ed051ea8dfc633e  project_state/runs/GS-102-transient-refined-v520-explore-20260512/data/starter.log
cf785c9a82e55ba75aaefc7dd0f6f71559967aaad92fb1d90b3cf1732be54061  project_state/runs/GS-102-transient-refined-v520-explore-20260512/data/engine.log
58c8850f8a0e57e2c5dd7675f80d525ee28d32818410e49c05fc23a759a29ec4  project_state/graph_executor/GS-102-transient-refined-v520-explore-20260512/ballistic/ballistic_metrics.json
4a09a5b56e86d19503c884d10d9cd246f18cacc7921437c92a2fc2332d6f6853  project_state/graph_executor/GS-102-transient-refined-v520-explore-20260512/visualization/openradioss_animation_manifest.json
3a1e614e09e89b8a85e3451aed1005cd19a3794d20ae58289a37ec424e7db85a  project_state/graph_executor/GS-102-transient-refined-v520-explore-20260512/visualization/openradioss_animation.gif
```

## Limitations

- Tier 1 only: no signed validation, no benchmark comparison, no tolerance
  agreement, and no independent reviewer signoff.
- This is a candidate workflow proof, not a locked validation configuration.
- Energy audit is partial unless future extraction adds plastic dissipation,
  hourglass energy, and contact friction to the metrics sidecar.
