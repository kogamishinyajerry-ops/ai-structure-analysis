# GS-102 CFL 0.85 Velocity Bracket Summary - 2026-05-12

> Status: Tier 1 engineering candidate.
> Claim boundary: not signed validation; not benchmark agreement.

## Purpose

This report summarizes a GS-102 refined OpenRadioss transient candidate
bracket at 345, 355, 365, 375, 385 m/s with `/DT/NODA/CST/0` fixed at
`0.85 0.0`.
Generated from `ballistic_metrics.json` sidecars.

No new solver run is claimed by this report. It only summarizes existing
candidate artifacts.

## Fixed Setup Control

- Source deck directory:
  `project_state/diagnostic_sources/GS-102-v365-cfl_085/data`
- Variant manifest:
  `project_state/diagnostic_sources/GS-102-v365-cfl_085/diagnostic_variant.json`
- Source variant:
  copied from the GS-102 refined candidate runtime input and changed only from
  `/DT/NODA/CST/0 = 0.9 0.0` to `/DT/NODA/CST/0 = 0.85 0.0`.
- Runtime deck/log directories:
  `project_state/runs/GS-102-transient-refined-cfl085-v*/data`
- Claim boundary:
  Tier 1 engineering candidate only; not signed validation; not benchmark
  agreement.

## Bracket Results

| Case | V0 m/s | Marker | Residual m/s | Crossing status | Back crossed | First back crossing s | Solver / cycles / frames / live solids |
|---|---:|---|---:|---|---|---:|---|
| `GS-102-transient-refined-cfl085-v345-bracket-20260512` | 345 | `embedded_candidate` | 9.05465 | `partial_candidate` | false | n/a | true / 4389 / 150 / 72 of 80 |
| `GS-102-transient-refined-cfl085-v355-bracket-20260512` | 355 | `embedded_candidate` | 9.520614 | `partial_candidate` | false | n/a | true / 6094 / 150 / 72 of 80 |
| `GS-102-transient-refined-cfl085-v365-bracket-20260512` | 365 | `embedded_candidate` | 10.40591 | `partial_candidate` | false | n/a | true / 4872 / 150 / 72 of 80 |
| `GS-102-transient-refined-cfl085-v375-bracket-20260512` | 375 | `perforated_candidate` | 35.407392 | `candidate_observed` | true | 0.000072006 | true / 3829 / 150 / 76 of 80 |
| `GS-102-transient-refined-cfl085-v385-bracket-20260512` | 385 | `embedded_candidate` | 11.306249 | `partial_candidate` | false | n/a | true / 6664 / 150 / 72 of 80 |

## Candidate Interpretation

- 345 m/s remains `embedded_candidate`: front-face crossing is observed, but
  back-face crossing is not observed in the sidecar.
- 355 m/s remains `embedded_candidate`: front-face crossing is observed, but
  back-face crossing is not observed in the sidecar.
- 365 m/s remains `embedded_candidate`: front-face crossing is observed, but
  back-face crossing is not observed in the sidecar.
- 375 m/s is `perforated_candidate`: back-face crossing is observed at
  `0.000072006 s` with candidate residual velocity
  `35.407392 m/s`.
- 385 m/s remains `embedded_candidate`: front-face crossing is observed, but
  back-face crossing is not observed in the sidecar.
- Non-monotonic candidate response is present across adjacent velocities:
  `365 m/s -> 375 m/s`: embedded -> perforated; `375 m/s -> 385 m/s`: perforated -> embedded.
- Treat this as a Tier 1 diagnostic pattern, not a single physical threshold.
- Energy audit is partial. Missing terms are
  `plastic_dissipation_j`, `contact_friction_j`, `hourglass_energy_j`.
- These trends are engineering-candidate evidence only. They are not
  signed validation and are not benchmark agreement.

## Artifact Index

### 345 m/s

- Case report:
  `reports/gs102_GS-102-transient-refined-cfl085-v345-bracket-20260512_candidate_run.md`
- Runtime deck/log directory:
  `project_state/runs/GS-102-transient-refined-cfl085-v345-bracket-20260512/data`
- Metrics:
  `project_state/graph_executor/GS-102-transient-refined-cfl085-v345-bracket-20260512/ballistic/ballistic_metrics.json`
- Visualization manifest:
  `project_state/graph_executor/GS-102-transient-refined-cfl085-v345-bracket-20260512/visualization/openradioss_animation_manifest.json`
- GIF:
  `project_state/graph_executor/GS-102-transient-refined-cfl085-v345-bracket-20260512/visualization/openradioss_animation.gif`

### 355 m/s

- Case report:
  `reports/gs102_GS-102-transient-refined-cfl085-v355-bracket-20260512_candidate_run.md`
- Runtime deck/log directory:
  `project_state/runs/GS-102-transient-refined-cfl085-v355-bracket-20260512/data`
- Metrics:
  `project_state/graph_executor/GS-102-transient-refined-cfl085-v355-bracket-20260512/ballistic/ballistic_metrics.json`
- Visualization manifest:
  `project_state/graph_executor/GS-102-transient-refined-cfl085-v355-bracket-20260512/visualization/openradioss_animation_manifest.json`
- GIF:
  `project_state/graph_executor/GS-102-transient-refined-cfl085-v355-bracket-20260512/visualization/openradioss_animation.gif`

### 365 m/s

- Case report:
  `reports/gs102_GS-102-transient-refined-cfl085-v365-bracket-20260512_candidate_run.md`
- Runtime deck/log directory:
  `project_state/runs/GS-102-transient-refined-cfl085-v365-bracket-20260512/data`
- Metrics:
  `project_state/graph_executor/GS-102-transient-refined-cfl085-v365-bracket-20260512/ballistic/ballistic_metrics.json`
- Visualization manifest:
  `project_state/graph_executor/GS-102-transient-refined-cfl085-v365-bracket-20260512/visualization/openradioss_animation_manifest.json`
- GIF:
  `project_state/graph_executor/GS-102-transient-refined-cfl085-v365-bracket-20260512/visualization/openradioss_animation.gif`

### 375 m/s

- Case report:
  `reports/gs102_GS-102-transient-refined-cfl085-v375-bracket-20260512_candidate_run.md`
- Runtime deck/log directory:
  `project_state/runs/GS-102-transient-refined-cfl085-v375-bracket-20260512/data`
- Metrics:
  `project_state/graph_executor/GS-102-transient-refined-cfl085-v375-bracket-20260512/ballistic/ballistic_metrics.json`
- Visualization manifest:
  `project_state/graph_executor/GS-102-transient-refined-cfl085-v375-bracket-20260512/visualization/openradioss_animation_manifest.json`
- GIF:
  `project_state/graph_executor/GS-102-transient-refined-cfl085-v375-bracket-20260512/visualization/openradioss_animation.gif`

### 385 m/s

- Case report:
  `reports/gs102_GS-102-transient-refined-cfl085-v385-bracket-20260512_candidate_run.md`
- Runtime deck/log directory:
  `project_state/runs/GS-102-transient-refined-cfl085-v385-bracket-20260512/data`
- Metrics:
  `project_state/graph_executor/GS-102-transient-refined-cfl085-v385-bracket-20260512/ballistic/ballistic_metrics.json`
- Visualization manifest:
  `project_state/graph_executor/GS-102-transient-refined-cfl085-v385-bracket-20260512/visualization/openradioss_animation_manifest.json`
- GIF:
  `project_state/graph_executor/GS-102-transient-refined-cfl085-v385-bracket-20260512/visualization/openradioss_animation.gif`

## Review Notes

- The bracket uses the fixed CFL 0.85 diagnostic source deck under
  `project_state/diagnostic_sources/GS-102-v365-cfl_085/data`; it should not be
  mixed with different-CFL bracket rows when making mechanism claims.
- Runtime decks and outputs are kept under `project_state/runs`, not under
  `golden_samples/**`.
- Each metrics sidecar carries a `solver_evidence` block with normal
  termination, cycle count, frame count, live solids, and deletion counts.
- The current evidence supports a Tier 1 candidate trend only.
- Do not promote this summary to Tier 2 without benchmark source lock,
  tolerance definition, complete energy accounting, and independent
  reviewer signoff.
