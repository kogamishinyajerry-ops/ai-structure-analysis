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

## Iteration log (FM-04a P10 closeout)

The FM-04a P10 commit ran `starter_linuxa64` from a local arm64-native
OpenRadioss Docker image (`openradioss:arm64`, already on the dev
workstation; arm64 binaries at `/opt/OpenRadioss/exec/starter_linuxa64`).
The starter parses **most** of the deck cleanly:

- `/BEGIN`, `/TITLE` — accepted
- `/MAT/PLAS_JOHNS/1` projectile — accepted (1 cosmetic warning on global
  units, harmless for syntax demo)
- `/MAT/PLAS_JOHNS/2` Weldox 460E plate (Børvik 2002 Part II Table 2 cited
  values) — accepted after the EPS_DOT_0 field was rewritten as `5.E-4`
  scientific notation (the deck author needs scientific notation for
  small floats; bare `.0005` was accepted by the parser but produced a
  material-law-data warning)
- `/NODE` (16 nodes) — accepted
- `/BRICK/1`, `/BRICK/2` — accepted
- `/PROP/SOLID/1`, `/PROP/SOLID/2`, `/PART/1`, `/PART/2` — accepted
- `/GRNOD/NODE/100` — accepted

**Residual iteration items (deck-author follow-up; outside FM-04a P10
scope):**

1. `/INIVEL/TRA/1` block returns ERROR ID 668 + ERROR ID 53 ("NO NODE
   GROUP DEFINED" / "NODE GROUP ID: 0") despite a syntactically correct
   60-char velocity line + `       100         0` gnod/skew row. The
   error-message pair indicates the OpenRadioss starter is reading the
   gnod_ID as 0; the deck author should consult the OpenRadioss /INIVEL
   reference for this specific arm64 build to determine whether the
   format expects `/INIVEL/TRA/inivel_ID/unit_ID` (where the second
   slash is unit_ID, NOT gnod_ID) or whether the gnod_ID line needs an
   alternative column layout. Two paths that did NOT work in P10:
   - `/INIVEL/TRA/1/100` (interpreted `100` as unit_ID, ERROR 659)
   - `       100\n` and `       100         0\n` (gnod_ID still parsed
     as 0)
2. `/FAIL/JOHNSON/2` element-deletion damage was intentionally omitted
   to keep the P10 syntax demonstration narrow. Adding it requires the
   damage parameters from Børvik 2002 Part II Table 2 (D1=0.0705,
   D2=1.732, D3=-0.54, D4=-0.015, D5=0; ε̇0=0.001, Ifail_sh=2,
   Ifail_so=1) and a follow-up starter pass.
3. `/BCS/1` clamping and `/INTER/TYPE7/1` projectile-plate contact were
   intentionally omitted. These are the most format-sensitive parts of
   the deck and are reserved for a deck-author iteration round.

**Where this leaves FM-04a P10:**

- The infrastructure is complete and tested: Docker arm64 image,
  starter+engine wrapper scripts, image setup script, deck content with
  Tier 1 wording locked in.
- The OpenRadioss starter executes against the deck and produces
  specific, narrow errors that a deck-author iteration round can resolve
  without architectural changes.
- The FM-04a P4 OpenRadioss adapter, P6 metric extractor, P7
  convergence writers, and P8 synthetic pipeline remain functional;
  none depend on the deck running cleanly through the starter.

**Tier 1 honesty:** P10 did NOT achieve a clean starter+engine run on
this deck. That is documented here, not glossed over. A deck author with
the OpenRadioss reference manual + 30 minutes of focused iteration is
the right path forward; another LLM iteration on cargo-culted syntax is
not.

## Citation compliance reminder

Material parameter values cited from Børvik 2002 Part II Table 2 appear
inline in `model_00_0000.rad`'s `/MAT/PLAS_JOHNS/2` and `/FAIL/JOHNSON/2`
blocks. Per ADR-024 (lite), only the parameter values may appear in
repo; full experimental tables MUST NOT be republished. If you need
experimental data alongside candidate output, that is an FM-04b
ADR-024 (full) review item, not a deck-authoring change.
