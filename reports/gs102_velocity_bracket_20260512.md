# GS-102 Velocity Bracket Summary - 2026-05-12

> Status: Tier 1 engineering candidate.
> Claim boundary: not signed validation; not benchmark agreement.

## Purpose

This report summarizes the current GS-102 refined OpenRadioss transient
candidate bracket at 150, 285, 325, 345, 365, 365, 385, 405, 445, 485, 505, 520, 600 m/s.
Generated from `ballistic_metrics.json` sidecars.

No new solver run is claimed by this report. It only summarizes existing
candidate artifacts.

## Bracket Results

| Case | V0 m/s | Marker | Residual m/s | Crossing status | Back crossed | First back crossing s | Solver / cycles / frames / live solids |
|---|---:|---|---:|---|---|---:|---|
| `GS-102-transient-refined-v150-bracket-20260512` | 150 | `embedded_candidate` | 1.189671 | `partial_candidate` | false | n/a | true / 3459 / 150 / 76 of 80 |
| `GS-102-transient-refined-v285-bracket-20260512` | 285 | `embedded_candidate` | 4.667462 | `partial_candidate` | false | n/a | true / 7448 / 150 / 76 of 80 |
| `GS-102-transient-refined-v325-probe-20260512` | 325 | `embedded_candidate` | 5.614325 | `partial_candidate` | false | n/a | true / 4051 / 150 / 76 of 80 |
| `GS-102-transient-refined-v345-probe-20260512` | 345 | `embedded_candidate` | 12.244106 | `partial_candidate` | false | n/a | true / 5435 / 150 / 72 of 80 |
| `GS-102-transient-refined-v365-explore-20260512` | 365 | `perforated_candidate` | 34.469076 | `candidate_observed` | true | 0.000071020 | true / 3672 / 150 / 76 of 80 |
| `GS-102-transient-refined-v365-repeat-a-20260512` | 365 | `perforated_candidate` | 34.469076 | `candidate_observed` | true | 0.000071020 | true / 3672 / 150 / 76 of 80 |
| `GS-102-transient-refined-v385-probe-20260512` | 385 | `embedded_candidate` | 1.988066 | `partial_candidate` | false | n/a | true / 11459 / 150 / 71 of 80 |
| `GS-102-transient-refined-v405-probe-20260512` | 405 | `embedded_candidate` | 14.932447 | `partial_candidate` | false | n/a | true / 5185 / 150 / 72 of 80 |
| `GS-102-transient-refined-v445-explore-20260512` | 445 | `embedded_candidate` | 12.725867 | `partial_candidate` | false | n/a | true / 4854 / 150 / 68 of 80 |
| `GS-102-transient-refined-v485-probe-20260512` | 485 | `embedded_candidate` | 11.857689 | `partial_candidate` | false | n/a | true / 12589 / 150 / 64 of 80 |
| `GS-102-transient-refined-v505-probe-20260512` | 505 | `perforated_candidate` | 40.374543 | `candidate_observed` | true | 0.000058012 | true / 8520 / 150 / 69 of 80 |
| `GS-102-transient-refined-v520-explore-20260512` | 520 | `perforated_candidate` | 19.570806 | `candidate_observed` | true | 0.000120109 | true / 12760 / 150 / 62 of 80 |
| `GS-102-transient-refined-v600-bracket-20260512` | 600 | `perforated_candidate` | 52.676288 | `candidate_observed` | true | 0.000049014 | true / 8831 / 150 / 68 of 80 |

## Candidate Interpretation

- 150 m/s remains `embedded_candidate`: front-face crossing is observed, but
  back-face crossing is not observed in the sidecar.
- 285 m/s remains `embedded_candidate`: front-face crossing is observed, but
  back-face crossing is not observed in the sidecar.
- 325 m/s remains `embedded_candidate`: front-face crossing is observed, but
  back-face crossing is not observed in the sidecar.
- 345 m/s remains `embedded_candidate`: front-face crossing is observed, but
  back-face crossing is not observed in the sidecar.
- 365 m/s is `perforated_candidate`: back-face crossing is observed at
  `0.000071020 s` with candidate residual velocity
  `34.469076 m/s`.
- 365 m/s is `perforated_candidate`: back-face crossing is observed at
  `0.000071020 s` with candidate residual velocity
  `34.469076 m/s`.
- 385 m/s remains `embedded_candidate`: front-face crossing is observed, but
  back-face crossing is not observed in the sidecar.
- 405 m/s remains `embedded_candidate`: front-face crossing is observed, but
  back-face crossing is not observed in the sidecar.
- 445 m/s remains `embedded_candidate`: front-face crossing is observed, but
  back-face crossing is not observed in the sidecar.
- 485 m/s remains `embedded_candidate`: front-face crossing is observed, but
  back-face crossing is not observed in the sidecar.
- 505 m/s is `perforated_candidate`: back-face crossing is observed at
  `0.000058012 s` with candidate residual velocity
  `40.374543 m/s`.
- 520 m/s is `perforated_candidate`: back-face crossing is observed at
  `0.000120109 s` with candidate residual velocity
  `19.570806 m/s`.
- 600 m/s is `perforated_candidate`: back-face crossing is observed at
  `0.000049014 s` with candidate residual velocity
  `52.676288 m/s`.
- Non-monotonic candidate response is present across adjacent velocities:
  `345 m/s -> 365 m/s`: embedded -> perforated; `365 m/s -> 385 m/s`: perforated -> embedded; `485 m/s -> 505 m/s`: embedded -> perforated.
- Treat this as a Tier 1 diagnostic pattern, not a single physical threshold.
- Energy audit is partial. Missing terms are
  `plastic_dissipation_j`, `contact_friction_j`, `hourglass_energy_j`.
- These trends are engineering-candidate evidence only. They are not
  signed validation and are not benchmark agreement.

## Artifact Index

### 150 m/s

- Case report:
  `reports/gs102_GS-102-transient-refined-v150-bracket-20260512_candidate_run.md`
- Runtime deck/log directory:
  `project_state/runs/GS-102-transient-refined-v150-bracket-20260512/data`
- Metrics:
  `project_state/graph_executor/GS-102-transient-refined-v150-bracket-20260512/ballistic/ballistic_metrics.json`
- Visualization manifest:
  `project_state/graph_executor/GS-102-transient-refined-v150-bracket-20260512/visualization/openradioss_animation_manifest.json`
- GIF:
  `project_state/graph_executor/GS-102-transient-refined-v150-bracket-20260512/visualization/openradioss_animation.gif`

### 285 m/s

- Case report:
  `reports/gs102_GS-102-transient-refined-v285-bracket-20260512_candidate_run.md`
- Runtime deck/log directory:
  `project_state/runs/GS-102-transient-refined-v285-bracket-20260512/data`
- Metrics:
  `project_state/graph_executor/GS-102-transient-refined-v285-bracket-20260512/ballistic/ballistic_metrics.json`
- Visualization manifest:
  `project_state/graph_executor/GS-102-transient-refined-v285-bracket-20260512/visualization/openradioss_animation_manifest.json`
- GIF:
  `project_state/graph_executor/GS-102-transient-refined-v285-bracket-20260512/visualization/openradioss_animation.gif`

### 325 m/s

- Case report:
  `reports/gs102_GS-102-transient-refined-v325-probe-20260512_candidate_run.md`
- Runtime deck/log directory:
  `project_state/runs/GS-102-transient-refined-v325-probe-20260512/data`
- Metrics:
  `project_state/graph_executor/GS-102-transient-refined-v325-probe-20260512/ballistic/ballistic_metrics.json`
- Visualization manifest:
  `project_state/graph_executor/GS-102-transient-refined-v325-probe-20260512/visualization/openradioss_animation_manifest.json`
- GIF:
  `project_state/graph_executor/GS-102-transient-refined-v325-probe-20260512/visualization/openradioss_animation.gif`

### 345 m/s

- Case report:
  `reports/gs102_GS-102-transient-refined-v345-probe-20260512_candidate_run.md`
- Runtime deck/log directory:
  `project_state/runs/GS-102-transient-refined-v345-probe-20260512/data`
- Metrics:
  `project_state/graph_executor/GS-102-transient-refined-v345-probe-20260512/ballistic/ballistic_metrics.json`
- Visualization manifest:
  `project_state/graph_executor/GS-102-transient-refined-v345-probe-20260512/visualization/openradioss_animation_manifest.json`
- GIF:
  `project_state/graph_executor/GS-102-transient-refined-v345-probe-20260512/visualization/openradioss_animation.gif`

### 365 m/s

- Case report:
  `reports/gs102_GS-102-transient-refined-v365-explore-20260512_candidate_run.md`
- Runtime deck/log directory:
  `project_state/runs/GS-102-transient-refined-v365-explore-20260512/data`
- Metrics:
  `project_state/graph_executor/GS-102-transient-refined-v365-explore-20260512/ballistic/ballistic_metrics.json`
- Visualization manifest:
  `project_state/graph_executor/GS-102-transient-refined-v365-explore-20260512/visualization/openradioss_animation_manifest.json`
- GIF:
  `project_state/graph_executor/GS-102-transient-refined-v365-explore-20260512/visualization/openradioss_animation.gif`

### 365 m/s

- Case report:
  `reports/gs102_GS-102-transient-refined-v365-repeat-a-20260512_candidate_run.md`
- Runtime deck/log directory:
  `project_state/runs/GS-102-transient-refined-v365-repeat-a-20260512/data`
- Metrics:
  `project_state/graph_executor/GS-102-transient-refined-v365-repeat-a-20260512/ballistic/ballistic_metrics.json`
- Visualization manifest:
  `project_state/graph_executor/GS-102-transient-refined-v365-repeat-a-20260512/visualization/openradioss_animation_manifest.json`
- GIF:
  `project_state/graph_executor/GS-102-transient-refined-v365-repeat-a-20260512/visualization/openradioss_animation.gif`

### 385 m/s

- Case report:
  `reports/gs102_GS-102-transient-refined-v385-probe-20260512_candidate_run.md`
- Runtime deck/log directory:
  `project_state/runs/GS-102-transient-refined-v385-probe-20260512/data`
- Metrics:
  `project_state/graph_executor/GS-102-transient-refined-v385-probe-20260512/ballistic/ballistic_metrics.json`
- Visualization manifest:
  `project_state/graph_executor/GS-102-transient-refined-v385-probe-20260512/visualization/openradioss_animation_manifest.json`
- GIF:
  `project_state/graph_executor/GS-102-transient-refined-v385-probe-20260512/visualization/openradioss_animation.gif`

### 405 m/s

- Case report:
  `reports/gs102_GS-102-transient-refined-v405-probe-20260512_candidate_run.md`
- Runtime deck/log directory:
  `project_state/runs/GS-102-transient-refined-v405-probe-20260512/data`
- Metrics:
  `project_state/graph_executor/GS-102-transient-refined-v405-probe-20260512/ballistic/ballistic_metrics.json`
- Visualization manifest:
  `project_state/graph_executor/GS-102-transient-refined-v405-probe-20260512/visualization/openradioss_animation_manifest.json`
- GIF:
  `project_state/graph_executor/GS-102-transient-refined-v405-probe-20260512/visualization/openradioss_animation.gif`

### 445 m/s

- Case report:
  `reports/gs102_GS-102-transient-refined-v445-explore-20260512_candidate_run.md`
- Runtime deck/log directory:
  `project_state/runs/GS-102-transient-refined-v445-explore-20260512/data`
- Metrics:
  `project_state/graph_executor/GS-102-transient-refined-v445-explore-20260512/ballistic/ballistic_metrics.json`
- Visualization manifest:
  `project_state/graph_executor/GS-102-transient-refined-v445-explore-20260512/visualization/openradioss_animation_manifest.json`
- GIF:
  `project_state/graph_executor/GS-102-transient-refined-v445-explore-20260512/visualization/openradioss_animation.gif`

### 485 m/s

- Case report:
  `reports/gs102_GS-102-transient-refined-v485-probe-20260512_candidate_run.md`
- Runtime deck/log directory:
  `project_state/runs/GS-102-transient-refined-v485-probe-20260512/data`
- Metrics:
  `project_state/graph_executor/GS-102-transient-refined-v485-probe-20260512/ballistic/ballistic_metrics.json`
- Visualization manifest:
  `project_state/graph_executor/GS-102-transient-refined-v485-probe-20260512/visualization/openradioss_animation_manifest.json`
- GIF:
  `project_state/graph_executor/GS-102-transient-refined-v485-probe-20260512/visualization/openradioss_animation.gif`

### 505 m/s

- Case report:
  `reports/gs102_GS-102-transient-refined-v505-probe-20260512_candidate_run.md`
- Runtime deck/log directory:
  `project_state/runs/GS-102-transient-refined-v505-probe-20260512/data`
- Metrics:
  `project_state/graph_executor/GS-102-transient-refined-v505-probe-20260512/ballistic/ballistic_metrics.json`
- Visualization manifest:
  `project_state/graph_executor/GS-102-transient-refined-v505-probe-20260512/visualization/openradioss_animation_manifest.json`
- GIF:
  `project_state/graph_executor/GS-102-transient-refined-v505-probe-20260512/visualization/openradioss_animation.gif`

### 520 m/s

- Case report:
  `reports/gs102_GS-102-transient-refined-v520-explore-20260512_candidate_run.md`
- Runtime deck/log directory:
  `project_state/runs/GS-102-transient-refined-v520-explore-20260512/data`
- Metrics:
  `project_state/graph_executor/GS-102-transient-refined-v520-explore-20260512/ballistic/ballistic_metrics.json`
- Visualization manifest:
  `project_state/graph_executor/GS-102-transient-refined-v520-explore-20260512/visualization/openradioss_animation_manifest.json`
- GIF:
  `project_state/graph_executor/GS-102-transient-refined-v520-explore-20260512/visualization/openradioss_animation.gif`

### 600 m/s

- Case report:
  `reports/gs102_GS-102-transient-refined-v600-bracket-20260512_candidate_run.md`
- Runtime deck/log directory:
  `project_state/runs/GS-102-transient-refined-v600-bracket-20260512/data`
- Metrics:
  `project_state/graph_executor/GS-102-transient-refined-v600-bracket-20260512/ballistic/ballistic_metrics.json`
- Visualization manifest:
  `project_state/graph_executor/GS-102-transient-refined-v600-bracket-20260512/visualization/openradioss_animation_manifest.json`
- GIF:
  `project_state/graph_executor/GS-102-transient-refined-v600-bracket-20260512/visualization/openradioss_animation.gif`

## Review Notes

- The bracket uses the refined fixture source decks from
  `golden_samples/GS-102-refined-candidate/data`.
- Runtime decks and outputs are kept under `project_state/runs`, not under
  `golden_samples/**`.
- Each metrics sidecar carries a `solver_evidence` block with normal
  termination, cycle count, frame count, live solids, and deletion counts.
- The current evidence supports a Tier 1 candidate trend only.
- Do not promote this summary to Tier 2 without benchmark source lock,
  tolerance definition, complete energy accounting, and independent
  reviewer signoff.
