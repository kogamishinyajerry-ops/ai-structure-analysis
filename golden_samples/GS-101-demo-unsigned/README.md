# GS-101-demo-unsigned — Functional bullet-penetration demo (Johnson-Cook deck)

> ## ⚠️ DEMO ONLY — parameters NOT validated, NOT physics-signed
>
> Per **RFC-002 §4.1 acceptance gate**, a fixture only enters
> `golden_samples/` as a signed-off `GS-101` after:
>
> 1. `/FAIL/JOHNSON` D1..D5 parameters compared against published
>    experimental data (Børvik et al. or equivalent).
> 2. Erosion-time-step series matched within ±10% of a published
>    bullet-vs-plate experiment.
> 3. **Physics engineer signature.**
>
> This fixture has **none of the above**. It uses Altair upstream
> default J-C parameters (D1=0.1, D2=0.1, D3=−0.1) which are
> placeholder values from the upstream contact-test suite, NOT
> validated for any specific real-world projectile-armor pair. The
> aluminum-impactor / steel-plate geometry is contrived (an idealized
> rigid-body-driven indentation, not a free-flight projectile).
>
> **Use this fixture for**:
> - End-to-end smoke testing of the W7 adapter → derivation → DOCX
>   pipeline against a deck that is more representative than GS-100
>   (which has zero element erosion).
> - Demonstrating "the software path is built" — what the wedge looks
>   like once a real GS-101 is authored.
>
> **Do NOT use this fixture for**:
> - Any engineering signoff.
> - Comparison to real ballistic-impact data.
> - Material qualification.

## Attribution

The starter deck (`data/model_00_0000.rad`) and the upstream original
engine deck (`data/model_00_0001.rad.orig`) are **derived from
OpenRadioss QA test
`qa-tests/miniqa/INTERF/INT_25/hexa8/data/model_00_*.rad`**, model ©
**Altair Engineering Inc.**, redistributed under
[CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/).

This README, the modifications to the engine deck (`model_00_0001.rad`),
and the addition of `/FAIL/JOHNSON/4` to the starter deck are
released alongside the original under the same CC BY-NC 4.0 terms.

## Origin

The upstream test (`small_boule` family in OpenRadioss QA, INT_25
contact-interface variant on hexa8 mesh) is a contact-test suite
verifying the `/INTER/TYPE25` self-contact algorithm. The geometry is:

- **Impactor**: 3 aluminum solid-element blocks (`/PART/1`, `/PART/2`,
  `/PART/3`) using `/MAT/PLAS_JOHNS/1` (J-C plasticity) with
  `/FAIL/JOHNSON/1` (D1=0.1, D2=0.1, D3=−0.1).
- **Plate**: 1 steel shell-element part (`/PART/5`, 180 facets,
  thickness 1 mm) using `/MAT/PLAS_JOHNS/4` (J-C plasticity) — the
  upstream deck has **no failure criterion** on the steel plate.
- **Loading**: `/RBODY/2` rigid body driven by `/IMPDISP` along X,
  scale (10, −25). Function-1 ramps 0→1 linearly. Imposed motion
  `0.6 mm/ms` constant velocity.

## Modifications from upstream

Three changes were made relative to the upstream deck (preserved
side-by-side as `data/model_00_0001.rad.orig`):

### 1. Engine deck — added `/ANIM/DT` so animation frames dump

The upstream engine deck has no `/ANIM/DT` directive; the engine
writes only the t=0 frame (or none, depending on solver build) and
the W7 adapter cannot ingest the run. Without animation frames, no
ballistic-summary report can be generated regardless of how the
physics resolves.

Modified engine deck appends:

```
/ANIM/DT
  0.    0.3
/ANIM/BRICK/EPSP
/ANIM/SHELL/EPSP
/ANIM/SHELL/TENS/STRESS/ALL
/ANIM/BRICK/TENS/STRESS
```

`0.3 ms` cadence over a 3 ms run yields 11 animation frames — enough
for the Layer-3 derivations to compute peak displacement and per-step
erosion history.

### 2. Engine deck — `/RUN` shortened from 5 ms to 3 ms

The upstream deck runs to 5 ms and the upstream `ref.extract`
(preserved as `data/upstream-ref.extract`) shows the run **errors at
cycle 8000 with `ERR=−25.4%`** energy violation — a known consequence
of severe element erosion at full-displacement contact in the upstream
contact-test setup. We trim to 3 ms to get a clean
`NORMAL TERMINATION` at ~4777 cycles with manageable energy error
(`ERR=−7.4%`) while still capturing impactor-on-plate deformation.

### 3. Starter deck — added `/FAIL/JOHNSON/4` for steel

The upstream steel material has no failure criterion, so the steel
plate cannot erode under any loading. To exercise the
`SupportsElementDeletion` capability path in the W7 reader against a
material that *can* fail, we add:

```
/FAIL/JOHNSON/4
#                 D1                  D2                  D3                  D4                  D5
                  .1                  .1                 -.1                   0                   0
#              EPS_0  Ifail_sh  Ifail_so                                    Dadv               Ixfem
                   0         2         0                                       0                   0
```

The `D1`/`D2`/`D3` values mirror the aluminum failure criterion already
present in the upstream deck; **these are placeholder values, not real
J-C steel failure parameters**. `Ifail_sh=2` enables shell-element
deletion at the first integration-point failure.

Even with this modification the steel plate **does not perforate** in
this run — it disintegrates the aluminum impactor first. The deck
demonstrates a "projectile defeat" regime (the impactor breaks up
against the harder plate), not "perforation". This is exactly why the
fixture is `-demo-unsigned`: with real J-C parameters tuned for a
specific projectile-armor pair, the regime would resolve correctly.

## Files

| File | Size | What |
|---|---|---|
| `data/model_00_0000.rad` | 60 KB | Starter deck (modified — added `/FAIL/JOHNSON/4`) |
| `data/model_00_0001.rad` | 0.4 KB | Engine deck (modified — added `/ANIM/DT`, run trimmed) |
| `data/model_00_0001.rad.orig` | 0.2 KB | Original engine deck (Altair upstream) |
| `data/upstream-ref.extract` | 0.4 KB | Altair upstream reference output (5 ms run, energy abort) |

**Animation frames are NOT shipped.** This fixture is bake-required —
follow the recipe below to generate `model_00A001.gz` …
`model_00A011.gz` locally. We deliberately do not ship the baked
output because (a) the fixture is unsigned so its purpose is
demonstrating the end-to-end pipeline including the bake step, and
(b) baking cleanly takes ~3 s in the docker image.

## Bake recipe

Requires the OpenRadioss runtime image from `tools/openradioss/`.

```bash
# 1. Stage the deck files into a scratch dir.
mkdir -p /tmp/gs101-bake
cp golden_samples/GS-101-demo-unsigned/data/model_00_0000.rad \
   golden_samples/GS-101-demo-unsigned/data/model_00_0001.rad \
   /tmp/gs101-bake/

# 2. Run starter + engine in the docker image.
docker run --rm -v /tmp/gs101-bake:/work openradioss:arm64 bash -c '
    cd /work
    starter_linuxa64 -i model_00_0000.rad -np 1
    engine_linuxa64  -i model_00_0001.rad
'

# 3. Compress animation frames (the OpenRadioss reader expects .gz).
cd /tmp/gs101-bake
for f in model_00A0[0-9][0-9]; do
    [ -f "$f" ] && gzip "$f"
done
```

Expected output:

- starter: `0 ERROR(S)`, `0 WARNING(S)`, `NORMAL TERMINATION`.
- engine: `NORMAL TERMINATION`, `TOTAL NUMBER OF CYCLES : 4777`,
  `ELAPSED TIME = 2.3 s` on Apple Silicon arm64.
- 11 files: `model_00A001.gz` through `model_00A011.gz`.
- Engine listing reports `~30 DELETE SOLID ELEMENT` lines (aluminum
  impactor erodes), 0 shell deletions (plate stays intact).

## Generating a ballistic-summary DOCX

> **Requires** the W7f no-perforation evidence-cite fix (PR landing
> alongside or before this fixture). Pre-fix, the export refuses with
> `section ... has uncited content line: ... 'no perforation observed'`
> because this fixture exercises the formerly-uncited else-branch in
> `draft.py:generate_ballistic_penetration_summary`.

After the bake:

```bash
report-cli \
  --kind ballistic \
  --openradioss-root /tmp/gs101-bake \
  --rootname model_00 \
  --unit-system si-mm \
  --project-id GS-101-DEMO \
  --task-id BULLET-PLATE-INT25 \
  --report-id RPT-GS101-DEMO-001 \
  --output /tmp/gs101-bake/GS-101-demo.docx \
  --no-validate-template \
  --no-figures
```

Expected DOCX content (3 evidence items, full audit trail):

| Claim | Value | Evidence |
|---|---|---|
| Run duration | 3.00 ms @ step_id=11 | EV-BALLISTIC-DURATION |
| Peak displacement | 125.4 mm @ step_id=11 | EV-BALLISTIC-MAX-DISP |
| Eroded shells at final | 0 facets | EV-BALLISTIC-EROSION-FINAL |
| Perforation event | not observed | EV-BALLISTIC-EROSION-FINAL |

## Adapter contract this fixture exercises

Beyond what GS-100 covers:

- ✅ Multi-frame state count: 11 states (vs. GS-100's 3) — exercises
  the per-step `_field_at(step_id)` audit binding harder.
- ✅ Significant nodal displacement: peak 125 mm (vs. GS-100's
  near-rigid contact) — exercises the `peak_displacement_history`
  derivation against real motion.
- ✅ Erosion-aware adapter path with `delEltA` reporting an actual
  zero (no shells eroded), exercising the no-perforation
  evidence-cite path that GS-100 cannot exercise (GS-100 has no J-C
  failure setup at all).
- ✅ The `(EV-BALLISTIC-EROSION-FINAL)` cite on the no-perforation
  observation line — see `backend/app/services/report/draft.py`
  history.

## When to retire this fixture

Retire when a real signed-off `golden_samples/GS-101/` lands per
RFC-002 §4.1 acceptance gate. At that point this fixture's job
("show the software path works while we wait for physics signoff")
is complete and it can be removed in the same PR as GS-101.
