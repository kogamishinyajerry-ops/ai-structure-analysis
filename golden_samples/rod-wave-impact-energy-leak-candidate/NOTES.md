# rod-wave-impact-energy-leak-candidate — fixture notes

Tier 1 engineering candidate; not signed validation; not benchmark agreement.

Regressed-bucket sibling of the canonical `rod-wave-impact-candidate` (Phase 14 D). Same geometry / material / velocity / frame_dt; ONLY the animation manifest injects 50% non-physical energy at frame 30.

## Failure mode (by construction)

* `per_frame_kinetic_energy_j[30]` and `per_frame_internal_energy_j[30]` each scaled by 1.5.
* `per_frame_external_work_j[30]` unchanged.
* `energy_partition_audit.flagged_frame_indices` = `(30,)`.
* `energy_partition_audit.max_rel_drift_fraction` ~= 0.50 (well above the 1% ENERGY_PARTITION_DRIFT_FRACTION threshold).
* `ballistic_metrics.energy_audit.status` = `open_residual`.
* `case_completeness` scorecard lands below the 80-pt healthy floor.

## What this fixture is NOT

* Not a real OpenRadioss or CalculiX *DYNAMIC run.
* Not a real physical energy injection; the leak is synthetic and pinned by `LEAK_INJECTION_FRAME` + `LEAK_INJECTION_SCALE` SSOT constants.
* Not Tier 2 benchmark agreement.
* Not a signed validation packet.

Regenerate with `python scripts/gen_rod_wave_impact_energy_leak_deck.py`.
