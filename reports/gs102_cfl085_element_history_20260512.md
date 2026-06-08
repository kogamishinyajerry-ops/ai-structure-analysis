# GS-102 CFL 0.85 Element History - 2026-05-12

> Status: Tier 1 element-history diagnostic.
> Claim boundary: not signed validation; not benchmark agreement.

## Purpose

Map selected solid-element alive-state and centroid histories for the
fixed-CFL 0.85 GS-102 local window. The focus is the early deleted group
`23/24/29/30` and the later deleted group `22/25/28/31` across 365,
375, and 385 m/s candidate runs.

No solver run is launched by this report. Runtime inputs and outputs stay
under `project_state/**`; `golden_samples/**` is not modified.

## Group Summary

| Case | Marker | Back crossed | Group | Final live / total | First any-dead frame | First all-dead frame | First all-dead timestep | Final centroid-x range mm |
|---|---|---|---|---:|---|---|---:|---:|
| `GS-102-transient-refined-cfl085-v365-bracket-20260512` | `embedded_candidate` | false | `early_deleted_23_24_29_30` | 0 / 4 | `model_00A037` | `model_00A037` | 0.036037 | 48.222231..48.223087 |
| `GS-102-transient-refined-cfl085-v365-bracket-20260512` | `embedded_candidate` | false | `late_deleted_22_25_28_31` | 0 / 4 | `model_00A122` | `model_00A126` | 0.125184 | 33.451533..33.46663 |
| `GS-102-transient-refined-cfl085-v375-bracket-20260512` | `perforated_candidate` | true | `early_deleted_23_24_29_30` | 0 / 4 | `model_00A037` | `model_00A037` | 0.036095 | 48.320455..48.335237 |
| `GS-102-transient-refined-cfl085-v375-bracket-20260512` | `perforated_candidate` | true | `late_deleted_22_25_28_31` | 4 / 4 | `n/a` | `n/a` | n/a | 33.572172..33.585509 |
| `GS-102-transient-refined-cfl085-v385-bracket-20260512` | `embedded_candidate` | false | `early_deleted_23_24_29_30` | 0 / 4 | `model_00A035` | `model_00A035` | 0.034022 | 49.08491..49.151757 |
| `GS-102-transient-refined-cfl085-v385-bracket-20260512` | `embedded_candidate` | false | `late_deleted_22_25_28_31` | 0 / 4 | `model_00A115` | `model_00A120` | 0.11903 | 33.493335..33.614803 |

## Element-Level History Summary

| Case | Group | Element | First dead frame | First dead timestep | Final alive | Initial centroid mm | Final centroid mm |
|---|---|---:|---|---:|---|---|---|
| `GS-102-transient-refined-cfl085-v365-bracket-20260512` | `early_deleted_23_24_29_30` | 23 | `model_00A037` | 0.036037 | false | (31.5, -1.5, -1.5) | (48.222231, -3.301223, -1.613762) |
| `GS-102-transient-refined-cfl085-v365-bracket-20260512` | `early_deleted_23_24_29_30` | 24 | `model_00A037` | 0.036037 | false | (31.5, -1.5, 1.5) | (48.222972, -3.301287, 1.614584) |
| `GS-102-transient-refined-cfl085-v365-bracket-20260512` | `early_deleted_23_24_29_30` | 29 | `model_00A037` | 0.036037 | false | (31.5, 1.5, -1.5) | (48.223087, 3.301166, -1.614482) |
| `GS-102-transient-refined-cfl085-v365-bracket-20260512` | `early_deleted_23_24_29_30` | 30 | `model_00A037` | 0.036037 | false | (31.5, 1.5, 1.5) | (48.222825, 3.30114, 1.613899) |
| `GS-102-transient-refined-cfl085-v365-bracket-20260512` | `late_deleted_22_25_28_31` | 22 | `model_00A122` | 0.121199 | false | (31.5, -1.5, -4.5) | (33.46663, -2.405886, -9.180234) |
| `GS-102-transient-refined-cfl085-v365-bracket-20260512` | `late_deleted_22_25_28_31` | 25 | `model_00A126` | 0.125184 | false | (31.5, -1.5, 4.5) | (33.451533, -2.518579, 9.161705) |
| `GS-102-transient-refined-cfl085-v365-bracket-20260512` | `late_deleted_22_25_28_31` | 28 | `model_00A126` | 0.125184 | false | (31.5, 1.5, -4.5) | (33.454646, 2.518157, -9.16993) |
| `GS-102-transient-refined-cfl085-v365-bracket-20260512` | `late_deleted_22_25_28_31` | 31 | `model_00A122` | 0.121199 | false | (31.5, 1.5, 4.5) | (33.464363, 2.404076, 9.178666) |
| `GS-102-transient-refined-cfl085-v375-bracket-20260512` | `early_deleted_23_24_29_30` | 23 | `model_00A037` | 0.036095 | false | (31.5, -1.5, -1.5) | (48.321503, -2.138393, -3.634448) |
| `GS-102-transient-refined-cfl085-v375-bracket-20260512` | `early_deleted_23_24_29_30` | 24 | `model_00A037` | 0.036095 | false | (31.5, -1.5, 1.5) | (48.320455, -2.136705, 3.64077) |
| `GS-102-transient-refined-cfl085-v375-bracket-20260512` | `early_deleted_23_24_29_30` | 29 | `model_00A037` | 0.036095 | false | (31.5, 1.5, -1.5) | (48.335237, 2.14086, -3.628965) |
| `GS-102-transient-refined-cfl085-v375-bracket-20260512` | `early_deleted_23_24_29_30` | 30 | `model_00A037` | 0.036095 | false | (31.5, 1.5, 1.5) | (48.334194, 2.143611, 3.623038) |
| `GS-102-transient-refined-cfl085-v375-bracket-20260512` | `late_deleted_22_25_28_31` | 22 | `n/a` | n/a | true | (31.5, -1.5, -4.5) | (33.572172, -1.037447, -11.408109) |
| `GS-102-transient-refined-cfl085-v375-bracket-20260512` | `late_deleted_22_25_28_31` | 25 | `n/a` | n/a | true | (31.5, -1.5, 4.5) | (33.577677, -1.039775, 11.406464) |
| `GS-102-transient-refined-cfl085-v375-bracket-20260512` | `late_deleted_22_25_28_31` | 28 | `n/a` | n/a | true | (31.5, 1.5, -4.5) | (33.572812, 1.356436, -11.290915) |
| `GS-102-transient-refined-cfl085-v375-bracket-20260512` | `late_deleted_22_25_28_31` | 31 | `n/a` | n/a | true | (31.5, 1.5, 4.5) | (33.585509, 1.355004, 11.299161) |
| `GS-102-transient-refined-cfl085-v385-bracket-20260512` | `early_deleted_23_24_29_30` | 23 | `model_00A035` | 0.034022 | false | (31.5, -1.5, -1.5) | (49.08491, -3.26469, -1.544479) |
| `GS-102-transient-refined-cfl085-v385-bracket-20260512` | `early_deleted_23_24_29_30` | 24 | `model_00A035` | 0.034022 | false | (31.5, -1.5, 1.5) | (49.151757, -3.255316, 1.418337) |
| `GS-102-transient-refined-cfl085-v385-bracket-20260512` | `early_deleted_23_24_29_30` | 29 | `model_00A035` | 0.034022 | false | (31.5, 1.5, -1.5) | (49.098379, 3.272373, -1.500046) |
| `GS-102-transient-refined-cfl085-v385-bracket-20260512` | `early_deleted_23_24_29_30` | 30 | `model_00A035` | 0.034022 | false | (31.5, 1.5, 1.5) | (49.091843, 3.296078, 1.507916) |
| `GS-102-transient-refined-cfl085-v385-bracket-20260512` | `late_deleted_22_25_28_31` | 22 | `model_00A115` | 0.11401 | false | (31.5, -1.5, -4.5) | (33.506393, -2.352094, -9.426202) |
| `GS-102-transient-refined-cfl085-v385-bracket-20260512` | `late_deleted_22_25_28_31` | 25 | `model_00A119` | 0.118073 | false | (31.5, -1.5, 4.5) | (33.614803, -2.524273, 9.435421) |
| `GS-102-transient-refined-cfl085-v385-bracket-20260512` | `late_deleted_22_25_28_31` | 28 | `model_00A120` | 0.11903 | false | (31.5, 1.5, -4.5) | (33.493335, 2.514349, -9.369551) |
| `GS-102-transient-refined-cfl085-v385-bracket-20260512` | `late_deleted_22_25_28_31` | 31 | `model_00A115` | 0.11401 | false | (31.5, 1.5, 4.5) | (33.522009, 2.396343, 9.430808) |

## Mechanism Reading

- The 375 m/s case is the only selected fixed-CFL 0.85 run whose centroid
  trace crosses the back face. In that run, the later `22/25/28/31`
  group remains alive through the final animation frame.
- The 365 m/s and 385 m/s cases do not show back-face crossing, and both
  eventually lose the later `22/25/28/31` group. This means deletion
  count alone is not a perforation explanation for this local window.
- Treat this as a numerical-path clue. The available sidecars do not
  expose contact-force history, contact friction work, hourglass energy,
  or full plastic-dissipation accounting.
- Raw animation timesteps are retained for frame-order comparison only;
  this report does not claim a unified physical clock between metrics,
  manifests, and engine-log text.

## Visual Comparison

- Synchronized full-flow GIF:
  `project_state/visualizations/gs102_cfl085_365_375_385_sync.gif`

## Artifact Index

### `GS-102-transient-refined-cfl085-v365-bracket-20260512`

- Metrics:
  `project_state/graph_executor/GS-102-transient-refined-cfl085-v365-bracket-20260512/ballistic/ballistic_metrics.json`
- Runtime animation frames:
  `project_state/runs/GS-102-transient-refined-cfl085-v365-bracket-20260512/data`
- Case report:
  `reports/gs102_GS-102-transient-refined-cfl085-v365-bracket-20260512_candidate_run.md`
- Full-flow animation GIF:
  `project_state/graph_executor/GS-102-transient-refined-cfl085-v365-bracket-20260512/visualization/openradioss_animation.gif`
- Animation manifest:
  `project_state/graph_executor/GS-102-transient-refined-cfl085-v365-bracket-20260512/visualization/openradioss_animation_manifest.json`

### `GS-102-transient-refined-cfl085-v375-bracket-20260512`

- Metrics:
  `project_state/graph_executor/GS-102-transient-refined-cfl085-v375-bracket-20260512/ballistic/ballistic_metrics.json`
- Runtime animation frames:
  `project_state/runs/GS-102-transient-refined-cfl085-v375-bracket-20260512/data`
- Case report:
  `reports/gs102_GS-102-transient-refined-cfl085-v375-bracket-20260512_candidate_run.md`
- Full-flow animation GIF:
  `project_state/graph_executor/GS-102-transient-refined-cfl085-v375-bracket-20260512/visualization/openradioss_animation.gif`
- Animation manifest:
  `project_state/graph_executor/GS-102-transient-refined-cfl085-v375-bracket-20260512/visualization/openradioss_animation_manifest.json`

### `GS-102-transient-refined-cfl085-v385-bracket-20260512`

- Metrics:
  `project_state/graph_executor/GS-102-transient-refined-cfl085-v385-bracket-20260512/ballistic/ballistic_metrics.json`
- Runtime animation frames:
  `project_state/runs/GS-102-transient-refined-cfl085-v385-bracket-20260512/data`
- Case report:
  `reports/gs102_GS-102-transient-refined-cfl085-v385-bracket-20260512_candidate_run.md`
- Full-flow animation GIF:
  `project_state/graph_executor/GS-102-transient-refined-cfl085-v385-bracket-20260512/visualization/openradioss_animation.gif`
- Animation manifest:
  `project_state/graph_executor/GS-102-transient-refined-cfl085-v385-bracket-20260512/visualization/openradioss_animation_manifest.json`

## Hard Boundaries

- Tier 1 only: no signed validation, no benchmark comparison, no tolerance
  agreement, and no independent reviewer signoff.
- `perforated_candidate` means the current centroid sidecar observed
  back-face crossing; it does not define a Tier 2 perforation threshold.
- The full-flow animation is visual evidence for the run sequence, not a
  substitute for element-level contact or energy accounting.
