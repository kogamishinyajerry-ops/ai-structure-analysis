# GS-102 365 m/s Mechanism Sensitivity - 2026-05-12

> Status: Tier 1 mechanism diagnostic.
> Claim boundary: not signed validation; not benchmark agreement.

## Purpose

Diagnose why the 365 m/s GS-102 refined candidate run is perforated while
nearby velocity probes at 345 m/s and 385 m/s are embedded candidates. These
runs change one numerical control at a time in copied source decks under
`project_state/diagnostic_sources/**`.

No `golden_samples/**` deck is modified by this diagnostic.

## Diagnostic Matrix

| Case | Variant | Source deck | Marker | Back crossed | Residual m/s | First back crossing s | Solver / cycles / frames / live solids |
|---|---|---|---|---|---:|---:|---|
| `GS-102-transient-refined-v365-explore-20260512` | baseline CFL 0.90 / ANIM 0.001 ms | `golden_samples/GS-102-refined-candidate/data` | `perforated_candidate` | true | 34.469076 | 0.000071020 | true / 3672 / 150 / 76 of 80 |
| `GS-102-transient-refined-v365-repeat-a-20260512` | baseline repeat | `golden_samples/GS-102-refined-candidate/data` | `perforated_candidate` | true | 34.469076 | 0.000071020 | true / 3672 / 150 / 76 of 80 |
| `GS-102-transient-refined-v365-repeat-b-20260512` | baseline repeat | `golden_samples/GS-102-refined-candidate/data` | `perforated_candidate` | true | 34.469076 | 0.000071020 | true / 3672 / 150 / 76 of 80 |
| `GS-102-transient-refined-v365-diag-cfl080-20260512` | `/DT/NODA/CST/0 = 0.8 0.0` | `project_state/diagnostic_sources/GS-102-v365-cfl_080/data` | `embedded_candidate` | false | 12.820306 | n/a | true / 5409 / 150 / 72 of 80 |
| `GS-102-transient-refined-v365-diag-cfl085-20260512` | `/DT/NODA/CST/0 = 0.85 0.0` | `project_state/diagnostic_sources/GS-102-v365-cfl_085/data` | `embedded_candidate` | false | 10.405910 | n/a | true / 4872 / 150 / 72 of 80 |
| `GS-102-transient-refined-v365-diag-cfl095-20260512` | `/DT/NODA/CST/0 = 0.95 0.0` | `project_state/diagnostic_sources/GS-102-v365-cfl_095/data` | `perforated_candidate` | true | 34.454879 | 0.000124032 | true / 8681 / 150 / 71 of 80 |
| `GS-102-transient-refined-v365-diag-cfl100-20260512` | `/DT/NODA/CST/0 = 1.0 0.0` | `project_state/diagnostic_sources/GS-102-v365-cfl_100/data` | `embedded_candidate` | false | 15.076922 | n/a | true / 8496 / 150 / 71 of 80 |
| `GS-102-transient-refined-v365-diag-animdt0005-20260512` | `/ANIM/DT = 0.0 0.0005` | `project_state/diagnostic_sources/GS-102-v365-anim_dt_0005/data` | `perforated_candidate` | true | 34.501057 | 0.000071020 | true / 3672 / 300 / 76 of 80 |

## Interpretation

- The baseline 365 m/s result is reproducible under the same copied source
  deck and solver controls across three candidate runs.
- Halving the output cadence from 0.001 ms to 0.0005 ms preserves the
  perforated candidate classification and the first back-face crossing time.
  This argues against output sampling alone explaining the 365 m/s anomaly.
- Changing only the `/DT/NODA/CST/0` CFL value shows a non-monotone numerical
  path: 0.80 and 0.85 embed, 0.90 repeats perforate, 0.95 perforates later,
  and 1.00 embeds. This is a Tier 1 diagnostic signal of explicit time-step /
  numerical-path sensitivity rather than a stable physical threshold.
- The 0.95 perforated candidate has similar residual velocity to 0.90 but a
  later first back-face crossing time and a much larger cycle count, so it
  should be treated as a separate numerical path, not as independent physical
  confirmation of the 0.90 result.
- Do not treat any row here as a physical threshold or signed validation
  result.

## Artifact Index

- Variant source manifest:
  `project_state/diagnostic_sources/GS-102-v365-cfl_080/diagnostic_variant.json`
- Variant source manifest:
  `project_state/diagnostic_sources/GS-102-v365-cfl_085/diagnostic_variant.json`
- Variant source manifest:
  `project_state/diagnostic_sources/GS-102-v365-cfl_095/diagnostic_variant.json`
- Variant source manifest:
  `project_state/diagnostic_sources/GS-102-v365-cfl_100/diagnostic_variant.json`
- Variant source manifest:
  `project_state/diagnostic_sources/GS-102-v365-anim_dt_0005/diagnostic_variant.json`
- Case report:
  `reports/gs102_GS-102-transient-refined-v365-diag-cfl080-20260512_candidate_run.md`
- Case report:
  `reports/gs102_GS-102-transient-refined-v365-diag-cfl085-20260512_candidate_run.md`
- Case report:
  `reports/gs102_GS-102-transient-refined-v365-diag-cfl095-20260512_candidate_run.md`
- Case report:
  `reports/gs102_GS-102-transient-refined-v365-diag-cfl100-20260512_candidate_run.md`
- Case report:
  `reports/gs102_GS-102-transient-refined-v365-diag-animdt0005-20260512_candidate_run.md`

## Next Diagnostic Step

Stop narrowing the velocity threshold on the current settings until the
time-step path is made defensible. The next useful slice is to choose a
conservative Tier 1 operating control, likely CFL 0.85 or lower, then rerun a
small velocity bracket under that fixed control. If preserving the higher-CFL
path is important, inspect contact/deletion timing near 0.90, 0.95, and 1.00
before using those runs for design guidance.

## Hard Boundaries

- Tier 1 only: no signed validation, no benchmark comparison, no tolerance
  agreement, and no independent reviewer signoff.
- Runtime diagnostic decks and outputs must remain under `project_state/**`.
- Energy audit is partial because plastic dissipation, contact friction, and
  hourglass energy are still missing from the metrics sidecar.
