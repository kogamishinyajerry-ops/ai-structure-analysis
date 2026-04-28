# GS-100 — OpenRadioss adapter smoke fixture

> **Attribution.** The simulation deck (`BOULE1V5_0000.rad`,
> `BOULE1V5_0001.rad.orig`), the unmodified text artefacts (`readme.txt`,
> `ref.extract`) and the geometry / material / interface definitions are
> derived from
> `OpenRadioss/qa-tests/miniqa/INTERF/INT_7/igsti/small_boule_igsti/dtmin_02/`
> (model © **Altair Engineering Inc.**), redistributed under
> [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/).
> See `LICENSE-NOTICES.md` at the repo root for the project-wide mixed-
> license boundary. Engine-deck modifications (`BOULE1V5_0001.rad` —
> two scalar parameters changed, see "Origin" below) are released
> alongside the original under the same CC BY-NC 4.0 terms.

**Purpose**: smallest possible OpenRadioss output set sufficient to validate
that `app.adapters.openradioss.OpenRadiossReader` implements the Layer-2
`ReaderHandle` Protocol correctly. **Not** a ballistic-penetration demo — that
lands as **GS-101** in W7e once we have a real bullet-vs-plate `.rad` deck
with proper Johnson-Cook material + element-erosion criteria.

## Origin

Derived from OpenRadioss QA test
`OpenRadioss/qa-tests/miniqa/INTERF/INT_7/igsti/small_boule_igsti/dtmin_02/`
(model © Altair Engineering Inc., licensed CC BY-NC 4.0). The original is a
ball-impact contact-test deck (`/INTER/TYPE19`) — we extended:

- `/RUN/BOULE1V5/1` from `0.0025 ms` → `0.5 ms` (so the engine actually
  produces multiple animation frames; the original 0.0025 ms run only
  dumped the t=0 initial state)
- `/ANIM/DT 0. 0.05` → `0. 0.025` (40-frame dump cadence; we ship 3
  representative frames for the smoke fixture)

The diff is preserved as `BOULE1V5_0001.rad` (modified) vs.
`BOULE1V5_0001.rad.orig` (original).

## Files

| File | Size | What |
|---|---|---|
| `BOULE1V5_0000.rad` | 30 KB | Starter deck (mesh + materials + parts + interfaces) |
| `BOULE1V5_0001.rad` | 0.3 KB | Engine deck (run-time + animation directives, modified) |
| `BOULE1V5_0001.rad.orig` | 0.3 KB | Original engine deck (Altair upstream) |
| `BOULE1V5A001.gz` | 1.9 KB | Animation frame at t=0.0 ms (initial state) |
| `BOULE1V5A011.gz` | 2.1 KB | Animation frame at t=0.25 ms (mid-run) |
| `BOULE1V5A021.gz` | 2.1 KB | Animation frame at t=0.5 ms (final) |
| `readme.txt` | 0.5 KB | Altair upstream model description |
| `ref.extract` | 0.4 KB | Altair upstream reference QA values |

## Adapter contract this fixture exercises

- ✅ Mesh extraction: 114 nodes, 74 facets, 3 parts (consistent across all
  frames — shape is constant for this contact-test case).
- ✅ Multi-state time history: 3 ``SolutionState`` entries with monotonic
  `time` values 0.0 → 0.25 → 0.5 ms.
- ✅ Element-deletion array (`delEltA`): all-1 (74/74 alive) for all frames
  in this case — no element erosion in a contact-only test. **The W7d
  ballistic derivations (penetration / element-kill) are not validated by
  this fixture; they need GS-101.**
- ✅ DISPLACEMENT reconstruction (`coorA(t) - coorA(0)`): the adapter
  surfaces `CanonicalField.DISPLACEMENT` for every state because every
  OpenRadioss animation frame ships `coorA`. This is a coordinate-frame
  re-expression, not a derived quantity (see ADR-021 §Decision —
  ADR-001 carve-out).
- ✅ Empty native-field path (`vTextA`/`tTextA`/`fTextA` all empty in
  this legacy contact-test deck): adapter must NOT advertise
  `STRESS_TENSOR` / `STRAIN_TENSOR` (no `tTextA` entry) and must NOT
  fabricate zero-valued tensors (ADR-003). DISPLACEMENT is the only
  field on `available_fields` in this fixture.

## What this fixture does NOT exercise

- Stress / displacement / velocity field extraction — see GS-101 (W7e) for
  a fixture that ships actual `/ANIM/ELEM/STRESS` + `/ANIM/NODA/DISPL`
  output. The legacy keyword set used by this Altair upstream model is not
  compatible with field-output keywords.
- Element erosion (`delEltA` differs from all-1) — same; needs Johnson-
  Cook + failure criterion in GS-101.
- Multi-part materials / multi-property interfaces — minimal here.

## Reproducing on host (manual)

```bash
docker build -t openradioss:arm64 -f tools/openradioss/Dockerfile tools/openradioss/  # (W7e)
docker run --rm -v $PWD:/work openradioss:arm64 bash -c '
  cd /work
  starter_linuxa64 -i BOULE1V5_0000.rad -np 1
  engine_linuxa64  -i BOULE1V5_0001.rad
'
gunzip -k BOULE1V5A*.gz
```

The adapter consumes the decompressed `BOULE1V5A001` / `BOULE1V5A011` /
`BOULE1V5A021` files. Vortex-Radioss (the underlying parser) does NOT
auto-decompress; the adapter handles that.
