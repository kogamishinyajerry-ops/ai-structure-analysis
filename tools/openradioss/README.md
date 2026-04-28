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

## Re-bake GS-100 (reference recipe)

```bash
cd <repo-root>
docker run --rm \
  -v $PWD/golden_samples/GS-100-radioss-smoke:/work \
  openradioss:arm64 bash -c '
    cd /work
    starter_linuxa64 -i BOULE1V5_0000.rad -np 1
    engine_linuxa64  -i BOULE1V5_0001.rad
  '
gunzip -k golden_samples/GS-100-radioss-smoke/BOULE1V5A*.gz   # adapter consumes the gzip directly
```

Expected output: starter prints `0 ERROR(S)`, engine prints `NORMAL TERMINATION`. The animation files (`BOULE1V5A001.gz` … `BOULE1V5A021.gz`) are produced; the W7b adapter ships only the 3 representative frames (A001 / A011 / A021) — the in-between frames can be discarded after the bake. (The adapter also auto-decompresses on first read; the `gunzip` step is only useful if you want to inspect the binary contents directly.)

## Apple Silicon notes

`docker info --format '{{.OSType}}/{{.Architecture}}'` should report `linux/aarch64` (or `linux/arm64`). The binaries are native ARM64 — no Rosetta x86 emulation involved. If you accidentally pull the x86_64 OpenRadioss zip on an ARM64 host, the starter will print `exec format error`; redownload the `_linuxa64.zip`.

## Deferred work

- **GS-101 (W7e)** — Johnson-Cook bullet-vs-plate fixture. Needs a hand-authored or QA-derived `.rad` deck with `/MAT/PLAS_JOHNS` material card + `/FAIL/JOHNSON` failure criterion. The deck-physics review is graduate-level explicit-dynamics work and lives in a dedicated milestone (not this PR).
