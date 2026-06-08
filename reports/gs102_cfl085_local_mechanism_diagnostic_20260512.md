# GS-102 CFL 0.85 Local Mechanism Diagnostic - 2026-05-12

> Status: Tier 1 mechanism diagnostic.
> Claim boundary: not signed validation; not benchmark agreement.

## Purpose

Diagnose the local mechanism behind the fixed-CFL 0.85 non-monotonic
candidate response at 365, 375, 385 m/s. This report compares deletion
timing, back-face crossing windows, and residual velocity traces from
existing sidecars and solver logs.

No solver run is launched by this report. No `golden_samples/**` file is
modified or used as a runtime output target.

## Fixed Inputs

- Source deck directory:
  `project_state/diagnostic_sources/GS-102-v365-cfl_085/data`
- Variant manifest:
  `project_state/diagnostic_sources/GS-102-v365-cfl_085/diagnostic_variant.json`
- Changed control:
  `/DT/NODA/CST/0 = 0.85 0.0`
- Compared cases:
  - `GS-102-transient-refined-cfl085-v365-bracket-20260512`
  - `GS-102-transient-refined-cfl085-v375-bracket-20260512`
  - `GS-102-transient-refined-cfl085-v385-bracket-20260512`

## Case-Level Evidence

| Case | V0 m/s | Marker | Back crossed | First back crossing s | Final gap to back face mm | Residual m/s | Cycles | Delete events | Live solids |
|---|---:|---|---|---:|---:|---:|---:|---:|---|
| `GS-102-transient-refined-cfl085-v365-bracket-20260512` | 365 | `embedded_candidate` | false | n/a | 0.521555 | 10.40591 | 4872 | 8 | 72 of 80 |
| `GS-102-transient-refined-cfl085-v375-bracket-20260512` | 375 | `perforated_candidate` | true | 0.000072006 | -2.523992 | 35.407392 | 3829 | 4 | 76 of 80 |
| `GS-102-transient-refined-cfl085-v385-bracket-20260512` | 385 | `embedded_candidate` | false | n/a | 0.466312 | 11.306249 | 6664 | 8 | 72 of 80 |

## Deletion And EPS Timing

| Case | EPS events | First EPS log time | EPS elements | Delete events | First delete log time | Last delete log time | Deleted elements |
|---|---:|---:|---|---:|---:|---:|---|
| `GS-102-transient-refined-cfl085-v365-bracket-20260512` | 16 | 0.3392E-01 | `23`, `29`, `24`, `30`, `22`, `31`, `28`, `25`, `59`, `65`, `60`, `66`, `58`, `67`, `64`, `61` | 8 | 3.5011E-02 | 1.2369E-01 | `23`, `29`, `24`, `30`, `22`, `31`, `28`, `25` |
| `GS-102-transient-refined-cfl085-v375-bracket-20260512` | 12 | 0.3266E-01 | `23`, `29`, `24`, `30`, `59`, `65`, `60`, `66`, `53`, `72`, `71`, `54` | 4 | 3.4949E-02 | 3.4949E-02 | `23`, `29`, `24`, `30` |
| `GS-102-transient-refined-cfl085-v385-bracket-20260512` | 16 | 0.3196E-01 | `23`, `29`, `24`, `30`, `25`, `28`, `31`, `22`, `65`, `60`, `66`, `59`, `64`, `61`, `67`, `58` | 8 | 3.3243E-02 | 1.1783E-01 | `23`, `29`, `24`, `30`, `31`, `22`, `25`, `28` |

## Frame-Level Deletion Accumulation

| Case | Manifest frames | First deleted frame | First deleted timestep | First deleted count | Max deleted | First max-deleted timestep |
|---|---:|---|---:|---:|---:|---:|
| `GS-102-transient-refined-cfl085-v365-bracket-20260512` | 150 | `model_00A037` | 0.036037 | 4 | 8 | 0.125184 |
| `GS-102-transient-refined-cfl085-v375-bracket-20260512` | 150 | `model_00A037` | 0.036095 | 4 | 4 | 0.036095 |
| `GS-102-transient-refined-cfl085-v385-bracket-20260512` | 150 | `model_00A035` | 0.034022 | 4 | 8 | 0.11903 |

## Time-Scale Note

- Metrics sidecars expose projectile trace times as `t_s`; animation
  manifests expose the raw OpenRadioss `timestep` value. They are useful
  for ordered frame comparison, but this report does not subtract engine
  log deletion times from crossing times as if a single verified physical
  clock had been established.

## Crossing Or Terminal Windows

### `GS-102-transient-refined-cfl085-v365-bracket-20260512`

- Window: terminal window; no back-face crossing observed.
- Plate back face x: `0.036 m`.

| Sample | t s | Centroid x m | Gap to back face mm | Speed m/s |
|---:|---:|---:|---:|---:|
| 145 | 0.000145252 | 0.03544 | 0.56044 | 10.242516 |
| 146 | 0.000146010 | 0.035447 | 0.552667 | 10.269708 |
| 147 | 0.000147251 | 0.03546 | 0.539897 | 10.320795 |
| 148 | 0.000148009 | 0.035468 | 0.532055 | 10.358136 |
| 149 | 0.000149021 | 0.035478 | 0.521555 | 10.40591 |

### `GS-102-transient-refined-cfl085-v375-bracket-20260512`

- Window: back-face crossing window around sample 72.
- Plate back face x: `0.036 m`.

| Sample | t s | Centroid x m | Gap to back face mm | Speed m/s |
|---:|---:|---:|---:|---:|
| 69 | 0.000069015 | 0.035939 | 0.061228 | 27.217814 |
| 70 | 0.000070044 | 0.035966 | 0.033693 | 27.352295 |
| 71 | 0.000071019 | 0.035993 | 0.007452 | 27.471739 |
| 72 | 0.000072006 | 0.036019 | -0.019211 | 27.58395 |
| 73 | 0.000073011 | 0.036047 | -0.046538 | 28.227941 |
| 74 | 0.000074047 | 0.036075 | -0.07538 | 28.473188 |
| 75 | 0.000075120 | 0.036105 | -0.105448 | 28.549176 |

### `GS-102-transient-refined-cfl085-v385-bracket-20260512`

- Window: terminal window; no back-face crossing observed.
- Plate back face x: `0.036 m`.

| Sample | t s | Centroid x m | Gap to back face mm | Speed m/s |
|---:|---:|---:|---:|---:|
| 145 | 0.000145021 | 0.035489 | 0.511425 | 11.103107 |
| 146 | 0.000146226 | 0.035502 | 0.498239 | 11.163769 |
| 147 | 0.000147190 | 0.035512 | 0.487641 | 11.211788 |
| 148 | 0.000148154 | 0.035523 | 0.476998 | 11.259304 |
| 149 | 0.000149119 | 0.035534 | 0.466312 | 11.306249 |

## Mechanism Reading

- The fixed-CFL 0.85 local window remains non-monotonic: 365 m/s embeds,
  375 m/s perforates in the candidate sidecar, and 385 m/s embeds.
- The 375 m/s run crosses the back face near sample
  `72` at `0.000072006 s`,
  while 365 m/s and 385 m/s remain short of the back face at the
  terminal frame by
  `0.521555 mm` and `0.466312 mm`.
- The deletion pattern is also different: 365 m/s and 385 m/s record
  eight deletion events including a later `22/25/28/31` group, while
  375 m/s records only the earlier `23/24/29/30` group in the engine
  log and sidecar. This is a numerical-path clue, not a contact-state
  conclusion.
- Contact-force history and full energy accounting are not present in
  the current sidecars, so this report cannot attribute the 375 m/s
  crossing to physical contact/friction behavior.
- The frame manifest confirms cumulative deletion timing in frame order,
  but it does not map deleted element ids to each frame; the element-id
  list still comes from `engine.log`.

## Artifact Index

### `GS-102-transient-refined-cfl085-v365-bracket-20260512`

- Case report:
  `reports/gs102_GS-102-transient-refined-cfl085-v365-bracket-20260512_candidate_run.md`
- Runtime deck/log directory:
  `project_state/runs/GS-102-transient-refined-cfl085-v365-bracket-20260512/data`
- Engine log:
  `project_state/runs/GS-102-transient-refined-cfl085-v365-bracket-20260512/data/engine.log`
- Metrics:
  `project_state/graph_executor/GS-102-transient-refined-cfl085-v365-bracket-20260512/ballistic/ballistic_metrics.json`
- Visualization manifest:
  `project_state/graph_executor/GS-102-transient-refined-cfl085-v365-bracket-20260512/visualization/openradioss_animation_manifest.json`
- GIF:
  `project_state/graph_executor/GS-102-transient-refined-cfl085-v365-bracket-20260512/visualization/openradioss_animation.gif`

### `GS-102-transient-refined-cfl085-v375-bracket-20260512`

- Case report:
  `reports/gs102_GS-102-transient-refined-cfl085-v375-bracket-20260512_candidate_run.md`
- Runtime deck/log directory:
  `project_state/runs/GS-102-transient-refined-cfl085-v375-bracket-20260512/data`
- Engine log:
  `project_state/runs/GS-102-transient-refined-cfl085-v375-bracket-20260512/data/engine.log`
- Metrics:
  `project_state/graph_executor/GS-102-transient-refined-cfl085-v375-bracket-20260512/ballistic/ballistic_metrics.json`
- Visualization manifest:
  `project_state/graph_executor/GS-102-transient-refined-cfl085-v375-bracket-20260512/visualization/openradioss_animation_manifest.json`
- GIF:
  `project_state/graph_executor/GS-102-transient-refined-cfl085-v375-bracket-20260512/visualization/openradioss_animation.gif`

### `GS-102-transient-refined-cfl085-v385-bracket-20260512`

- Case report:
  `reports/gs102_GS-102-transient-refined-cfl085-v385-bracket-20260512_candidate_run.md`
- Runtime deck/log directory:
  `project_state/runs/GS-102-transient-refined-cfl085-v385-bracket-20260512/data`
- Engine log:
  `project_state/runs/GS-102-transient-refined-cfl085-v385-bracket-20260512/data/engine.log`
- Metrics:
  `project_state/graph_executor/GS-102-transient-refined-cfl085-v385-bracket-20260512/ballistic/ballistic_metrics.json`
- Visualization manifest:
  `project_state/graph_executor/GS-102-transient-refined-cfl085-v385-bracket-20260512/visualization/openradioss_animation_manifest.json`
- GIF:
  `project_state/graph_executor/GS-102-transient-refined-cfl085-v385-bracket-20260512/visualization/openradioss_animation.gif`

## Hard Boundaries

- Tier 1 only: no signed validation, no benchmark comparison, no tolerance
  agreement, and no independent reviewer signoff.
- `perforated_candidate` means the current centroid sidecar observed
  back-face crossing; it does not define a Tier 2 perforation threshold.
- Current sidecars do not expose contact-force history, contact friction
  work, hourglass energy, or complete plastic dissipation. This report
  therefore treats contact-state and energy-closure causes as unproven.

## Next Diagnostic Step

- Add a narrow extractor for element centroid/alive-state history around
  the deleted element groups and, if available from OpenRadioss outputs,
  contact/energy time-history terms before spending more runs on velocity
  threshold narrowing.
