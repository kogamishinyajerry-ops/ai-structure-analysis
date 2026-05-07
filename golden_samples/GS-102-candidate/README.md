# GS-102-candidate — FM-04a Tier 1 ballistic candidate fixture (NOT signed validation)

> ## ⚠️ TIER 1 ENGINEERING CANDIDATE — NOT signed validation, NOT benchmark agreement
>
> Per **ADR-023 §Tier 0/1/2** + **ADR-024 (lite)**, this directory hosts a Tier 1
> *engineering-candidate* ballistic fixture only. It supports the FM-04a milestone
> goal of producing a reproducible OpenRadioss candidate run for the
> bullet-vs-steel-plate workflow. It does **not** carry signed validation, signed
> physics signoff, public benchmark agreement, or any Tier 2 promise.
>
> The Tier 2 signed validation gate is reserved for **FM-04b** under a future,
> full-scope ADR-024 revision that locks the benchmark case, tolerance, and
> independent reviewer/signoff. FM-04b is **not** authorized by ADR-024 (lite).

## Status (frozen at P3 scope)

- Claim tier: **Tier 1 engineering candidate**.
- Allowed wording: `engineering candidate; not signed validation; not benchmark agreement`,
  `JC parameters cited from Børvik 2002 Part II Table 2`,
  `Initial velocity V₀ = … m/s (Tier 1 candidate point sourced from Børvik 2002 Part I)`.
- Forbidden wording (per ADR-023 + ADR-024 lite): `validated against Børvik 2002`,
  `benchmark agreement`, `signed validation`, `signed GS-102`, `signed GS101`,
  `validated physics`, `bullet-through-steel complete`,
  `bullet-through-steel simulation complete`, `steel perforation completed`.
- Registry posture: name pattern `GS-102-candidate` is intentionally outside the
  signed `^GS-\d{3}$` set used by `scripts/validate_golden_samples.py`, mirroring
  the GS-100-radioss-smoke / GS-101-demo-unsigned precedent.

## Scope (locked by ADR-024 lite)

- Geometry envelope: 20 mm diameter projectile, hemispherical nose, 12 mm thick
  Weldox 460E mild steel plate.
- Material model (deck content authored in P4): Johnson-Cook plasticity + JC damage,
  parameter values cited from Børvik 2002 Part II Table 2; not republished here.
- Initial condition: single normal-incidence impact, V₀ ≈ 285 m/s as a non-marginal
  candidate point. FM-04a does **not** sweep V₀.
- Boundary condition: outer rim fully clamped; single projectile; normal incidence;
  no obliquity, no spaced plates, no layered targets.
- Solver: OpenRadioss explicit dynamics path via `aeron.drivers` (RFC-001 W7).

## What is in this directory at FM-04a P10 closeout

- `expected_results.json` — Tier 1 candidate metadata. `status =
  insufficient_evidence`, `status_reason` reaffirms FM-04b deferral,
  `benchmark_source_ref = ADR-024 (parameters only)`, ballistic block carries
  `projectile_initial_velocity_m_per_s` so the FM-03 spine (v2) can fall back to
  it before any runtime sidecar exists.
- `README.md` — this file.
- `data/model_00_0000.rad` — OpenRadioss starter deck. JC plasticity / damage
  parameters cited from Børvik 2002 Part II Table 2 per ADR-024 lite. Mesh is
  intentionally a 1-projectile-hex + 1-plate-hex syntax demonstration; it is
  NOT a physics-quality mesh and is NOT a benchmark-agreement claim.
- `data/model_00_0001.rad` — OpenRadioss engine deck. 0.5 ms run-time,
  animation cadence 0.05 ms, NODA constant time-step. Tier 1 candidate
  values.
- `data/NOTES.md` — explicit honesty notes + Docker / native-install run
  instructions. Reaffirms that no experimental data table from Børvik 2002
  appears in this repo.

The actual JC plasticity / damage / element-deletion path through the
OpenRadioss adapter (FM-04a P4 `aeron.drivers.OpenRadiossFEABackend`) now has
real deck content to consume. P10 also lands `scripts/openradioss_starter_docker.sh`
+ `scripts/openradioss_engine_docker.sh` + `scripts/openradioss_image_setup.sh`
so the deck can run in a `linux/amd64` Docker container on macOS Apple Silicon
(no native binaries required).

## What is *not* in this directory and why

- No real OpenRadioss `.rad` deck yet — that lives in P4 once the adapter is
  wired. P3's job is the directory + claim-tier discipline + spine fallback
  metadata, not the solver inputs.
- No experimental data tables from Børvik 2002 — ADR-024 (lite) does **not**
  authorize republication of experimental tables. Any republication review is
  reserved for ADR-024 (full) under FM-04b.
- No signed validation evidence, no convergence study, no residual-velocity
  comparison, no reviewer/signoff packet — all Tier 2 ingredients are deferred
  to FM-04b per ADR-023 §Tier 2.

## Use this fixture for

- FM-04a P4 OpenRadioss adapter wiring (target deck location).
- FM-04a P5 mesh × time-step convergence study (target deck location).
- FM-04a P6 residual-velocity / perforation marker extraction (target deck location).
- Tier 1 candidate spine consumption (`projectile_initial_velocity` fallback path
  via `expected_results.json.ballistic.projectile_initial_velocity_m_per_s`).

## Do **not** use this fixture for

- Any engineering signoff.
- Any claim of benchmark agreement against Børvik 2002 or any other public
  benchmark.
- Material qualification.
- Any Tier 2 promotion. Status flips to Tier 2 are reserved for FM-04b.

## References

- ADR-011 §HF1 (golden-sample directory governance + override mechanism)
- ADR-021 (GS-100 smoke fixture precedent)
- ADR-022 (GS-101-demo-unsigned precedent)
- ADR-023 (lean validation workflow + Tier 0/1/2 forbidden wording set)
- ADR-024 (lite) — `docs/adr/ADR-024-ballistic-benchmark-source-selection.md`
- `.planning/STATE.md` 2026-05-07 entry for FM-04a milestone
- `reports/fm03_candidate_report_spine_source_map.md` §FM-04a P1 (the spine read
  contract that consumes this fixture's metadata)
