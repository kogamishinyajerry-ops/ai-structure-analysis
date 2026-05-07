# GS-102-candidate/data/NOTES.md — deck content notes

> Tier 1 engineering candidate; not signed validation; not benchmark agreement.

## What lives here

| File | Role | Tier 1 honesty notes |
|---|---|---|
| `model_00_0000.rad` | OpenRadioss starter deck | 1 hex projectile + 1 hex plate element. JC plasticity / damage parameters cited from Børvik 2002 Part II Table 2 (Weldox 460E). Mesh is intentionally too coarse for any physics claim — it is a syntax demonstration only. |
| `model_00_0001.rad` | OpenRadioss engine deck | 0.5 ms run-time, animation cadence 0.05 ms, NODA constant time-step. Tier 1 candidate values; tighten in FM-04b. |

## What is intentionally NOT here

- A refined mesh that would imply benchmark-quality geometry. The Børvik
  2002 geometry envelope (20 mm hemispherical-nose projectile / 12 mm
  Weldox 460E plate, fully clamped rim) is encoded only at the syntax
  level; geometric refinement is reserved for FM-04b under ADR-024 (full).
- Republished experimental tables from Børvik 2002. ADR-024 (lite)
  authorizes parameter-value citation only.
- Any wording, comment, or output that implies benchmark agreement,
  signed validation, validated physics, or "perforation completed".

## How to actually run this deck

OpenRadioss is not installed natively on macOS Apple Silicon. Two paths:

### Path A — Docker (recommended on macOS)

```sh
# One-time: pull or fallback-build the image
./scripts/openradioss_image_setup.sh

# Run starter then engine inside the case dir
cd golden_samples/GS-102-candidate/data
../../../scripts/openradioss_starter_docker.sh -i model_00_0000.rad
../../../scripts/openradioss_engine_docker.sh -i model_00_0001.rad
```

After the run completes, the directory should carry `.h3d` / `.anim` /
`.out` / `.rst` files. The FM-04a P4 adapter discovers these output
suffixes automatically when invoked through `aeron.drivers.OpenRadiossFEABackend`.

### Path B — Native install

If you have OpenRadioss installed natively (Linux, or a custom macOS
arm64 build), put `starter_linux64_gf` and `engine_linux64_gf` on PATH
(or any of the candidate names listed in `aeron.drivers.openradioss_backend.RADIOSS_STARTER_CANDIDATES`),
then run them directly:

```sh
cd golden_samples/GS-102-candidate/data
starter_linux64_gf -i model_00_0000.rad
engine_linux64_gf  -i model_00_0001.rad
```

The adapter probes PATH the same way regardless of whether the binary is
a real native one or a Docker wrapper script.

## Verifying the syntax

The OpenRadioss starter performs a deck integrity check before any
solve. If the starter exits 0 the deck is syntactically valid; if it
exits non-zero it prints a `*ERROR*` line indicating the offending
section. Treat any such error as a Tier 1 candidate authoring issue,
not a Tier 2 finding.

## Citation compliance reminder

Material parameter values cited from Børvik 2002 Part II Table 2 appear
inline in `model_00_0000.rad`'s `/MAT/PLAS_JOHNS/2` and `/FAIL/JOHNSON/2`
blocks. Per ADR-024 (lite), only the parameter values may appear in
repo; full experimental tables MUST NOT be republished. If you need
experimental data alongside candidate output, that is an FM-04b
ADR-024 (full) review item, not a deck-authoring change.
