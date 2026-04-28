# OpenRadioss runtime — `tools/openradioss/`

Docker recipe for the out-of-process OpenRadioss solver. Used by:

- **GS-100 fixture re-bake** — see `golden_samples/GS-100-radioss-smoke/` for the deck files; the bake recipe lives there.
- **GS-101 fixture bake** — pending; will land alongside ADR-022 once a Johnson-Cook bullet-vs-plate deck is authored.
- **Engineer-side experimental runs** — the same image any developer can pull to try a `.rad` deck before promoting it to a fixture.

## License boundary

OpenRadioss itself is **AGPL-3.0**. We run it out-of-process inside the container; the Python adapter (`backend/app/adapters/openradioss/`) imports `vortex_radioss` (MPL-2.0) only, never the AGPL solver code. See `docs/adr/ADR-021-gs100-radioss-smoke-fixture.md` §Licensing for the full mixed-license map; W7g RFC-002 will lift it to a repo-root `LICENSE-NOTICES.md` once more adapters land.

## Build

The Dockerfile expects a sibling `OpenRadioss/` directory containing the unzipped prebuilt binaries:

```bash
cd tools/openradioss

# 1. Download the ARM64 prebuilt binaries (~137 MB) — pin the release tag.
gh release download latest-20260319 --repo OpenRadioss/OpenRadioss \
  --pattern "OpenRadioss_linuxa64.zip"
unzip OpenRadioss_linuxa64.zip   # → ./OpenRadioss/

# 2. Build the runtime image (~752 MB).
docker build -t openradioss:arm64 .
```

The `OpenRadioss/` tree and the `.zip` are deliberately git-ignored — they're 137-200 MB binaries that bloat the repo and have their own AGPL distribution channel.

## Smoke probe

After build:

```bash
docker run --rm openradioss:arm64 starter_linuxa64 -help
# Expected: starter usage banner, exit 0.
```

## Re-bake GS-100 (requires upstream QA include)

The shipped GS-100 fixture is a baked output set; the W7b adapter consumes the
`A*.gz` frames directly and does not need to be re-baked for routine use.
A re-bake from `BOULE1V5_0000.rad` is **not** self-contained because the deck
contains `#include qadiags.inc` near the end, and `qadiags.inc` lives in the
OpenRadioss QA tree under
`OpenRadioss/qa-tests/miniqa/INTERF/INT_7/igsti/small_boule_igsti/data/qadiags.inc`
(verified against `gh api repos/OpenRadioss/OpenRadioss/contents/...` —
the file sits in the `data/` subdirectory, not the top of `small_boule_igsti/`).
We deliberately do not vendor it (CC BY-NC 4.0 + size).

To re-bake, stage `qadiags.inc` next to the local `BOULE1V5_*` deck files in
`/work`, then run the docker recipe below. (Mounting the upstream
`.../small_boule_igsti/data/` directory directly at `/work` would NOT work —
that directory ships the upstream `BOULEV44_0000.rad` / `BOULEV44_0001.rad`
deck files, not our renamed `BOULE1V5_*` derivatives.)

```bash
cd <repo-root>
# Stage the deck + the upstream qadiags.inc into a scratch dir.
# /work must contain BOULE1V5_0000.rad, BOULE1V5_0001.rad, AND qadiags.inc.
mkdir -p /tmp/gs100-rebake
cp golden_samples/GS-100-radioss-smoke/BOULE1V5_0000.rad /tmp/gs100-rebake/
cp golden_samples/GS-100-radioss-smoke/BOULE1V5_0001.rad /tmp/gs100-rebake/
cp /path/to/OpenRadioss/qa-tests/miniqa/INTERF/INT_7/igsti/small_boule_igsti/data/qadiags.inc \
   /tmp/gs100-rebake/

docker run --rm \
  -v /tmp/gs100-rebake:/work \
  openradioss:arm64 bash -c '
    cd /work
    starter_linuxa64 -i BOULE1V5_0000.rad -np 1
    engine_linuxa64  -i BOULE1V5_0001.rad
  '
```

Expected on a successful re-bake: starter prints `0 ERROR(S)`, engine prints
`NORMAL TERMINATION`, and `BOULE1V5A001.gz` … `BOULE1V5A021.gz` are written to
`/tmp/gs100-rebake/`. The W7b adapter ships only the 3 representative frames
(A001 / A011 / A021); the in-between frames can be discarded after the bake.

**Common failure**: omitting `qadiags.inc` makes the starter abort with
`ERROR ID : 100002 — Include file qadiags.inc not found` and exit 2. That is
not a Docker problem — it means the QA include was not staged into `/work`.

## Apple Silicon notes

`docker info --format '{{.OSType}}/{{.Architecture}}'` should report `linux/aarch64` (or `linux/arm64`). The binaries are native ARM64 — no Rosetta x86 emulation involved. If you accidentally pull the x86_64 OpenRadioss zip on an ARM64 host, the starter will print `exec format error`; redownload the `_linuxa64.zip`.

## Deferred work

- **GS-101 (W7e)** — Johnson-Cook bullet-vs-plate fixture. Needs a hand-authored or QA-derived `.rad` deck with `/MAT/PLAS_JOHNS` material card + `/FAIL/JOHNSON` failure criterion. The deck-physics review is graduate-level explicit-dynamics work and lives in a dedicated milestone (not this PR).
