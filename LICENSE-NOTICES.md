# License Notices

Cross-component license map for the AI-Structure-FEA project. Promised by
[ADR-021 §Mixed-license notice](docs/adr/ADR-021-gs100-radioss-smoke-fixture.md)
and [`tools/openradioss/README.md` §License boundary](tools/openradioss/README.md);
landed by RFC-002 (W7g).

This document is informational and is **not legal advice**. Each
component's authoritative license is in the file or upstream project
referenced below. Where this document conflicts with an upstream
LICENSE file, the upstream file wins.

---

## 1. Project source code — MIT

Everything under the project root that we authored ourselves —
`backend/`, `frontend/`, `scripts/`, `tools/<solver>/Dockerfile +
README.md + .gitignore`, `docs/`, `tests/` — is licensed **MIT**, as
declared in `pyproject.toml`:

```toml
[project]
license = {text = "MIT"}
```

This includes:

- All Python in `backend/app/` (CalculiX adapter, OpenRadioss adapter,
  Layer-2 Protocol contracts, Layer-3 derivations, Layer-4 report
  generation, CLI, services).
- All Electron / TypeScript in `frontend/`.
- All ADRs, RFCs, and project docs under `docs/`.
- Container recipes under `tools/<solver>/` (the recipes themselves;
  the binaries they pull are governed by upstream licenses — see §2).

---

## 2. Out-of-process solvers — separate licenses, AGPL boundary

The project drives external solver binaries as **out-of-process**
subprocesses inside containers. We never link against the solver
binaries from project code.

### 2.1 OpenRadioss — AGPL-3.0

[OpenRadioss](https://github.com/OpenRadioss/OpenRadioss) is licensed
under **AGPL-3.0**. We use the upstream prebuilt ARM64 Linux binaries
(`OpenRadioss_linuxa64.zip` from the `latest-YYYYMMDD` release
channel), pulled at container build time and copied into
`/opt/OpenRadioss/` inside `tools/openradioss/Dockerfile`.

**The AGPL boundary is preserved by**:

1. The solver runs as a separate process (`docker run … starter_linuxa64
   …`); project code never imports the solver binary, never links it
   against project Python, and never modifies it.
2. The Python adapter (`backend/app/adapters/openradioss/`) imports
   only `vortex_radioss` (MPL-2.0; see §3.1), which itself reads the
   solver's *output files* — also AGPL-disjoint, since the output
   bytes are simulation data, not solver code.
3. The solver tree is not redistributed by this repository. The
   `tools/openradioss/.gitignore` blocks `OpenRadioss/`,
   `OpenRadioss_*.zip`, and `OpenRadioss_*.tar.gz` from being staged.
4. Users pull the AGPL binaries from upstream's own GitHub releases
   channel, which is upstream's primary distribution path.

The recipe for staging the solver inside the container is in
[`tools/openradioss/README.md`](tools/openradioss/README.md). The
fixture-level licensing detail (separate from the binary) is in §4
below.

### 2.2 CalculiX — GPL-2.0+

[CalculiX](http://www.calculix.de/) is licensed under **GPL-2.0+**.
The binary is invoked out-of-process by the user (or by the local
runtime spawn) and we read its `.frd` output files. Same boundary
discipline as OpenRadioss: no linking, no redistribution, output bytes
are AGPL/GPL-disjoint.

Adapter: `backend/app/adapters/calculix/`.

### 2.3 Future solvers

Each new solver under `tools/<solver>/` carries its own upstream
license. Add a §2.N subsection here when the solver lands. The
boundary discipline (out-of-process, no linking, no redistribution
of the binary) applies uniformly.

---

## 3. Vendored / imported Python dependencies — third-party licenses

### 3.1 vortex_radioss — MPL-2.0

[vortex-radioss](https://github.com/Vortex-CAE/Vortex-Radioss) is a
Python parser for OpenRadioss `.A###` animation binaries, licensed
**MPL-2.0** (license file at the upstream repo root). We import it
from `pyproject.toml` and use its `RadiossReader` class in
`backend/app/adapters/openradioss/reader.py` (around line 466).

MPL-2.0 is a file-level copyleft. It does NOT propagate to the rest
of our codebase; only files that contain MPL-2.0 source must remain
MPL-2.0. The adapter file imports the module but does not contain
MPL-2.0 source.

### 3.2 Other Python dependencies

All other Python dependencies (numpy, python-docx, pydantic, …) carry
their own licenses (BSD, MIT, Apache-2.0). Their license terms apply
to those packages individually. The lockfile (`uv.lock` or
`requirements.txt`) is the authoritative inventory; `pip-licenses` or
equivalent can produce the full audit.

---

## 4. Golden-sample fixtures — per-fixture licenses

### 4.1 GS-100 (OpenRadioss adapter smoke) — CC BY-NC 4.0

`golden_samples/GS-100-radioss-smoke/` is derived from the upstream
OpenRadioss QA test
`OpenRadioss/qa-tests/miniqa/INTERF/INT_7/igsti/small_boule_igsti/`
(model © **Altair Engineering Inc.**), redistributed under
[CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) per
the upstream QA test bundle. The full licensing analysis is in
[ADR-021 §Licensing](docs/adr/ADR-021-gs100-radioss-smoke-fixture.md).

**The CC BY-NC 4.0 NC ("non-commercial") qualifier governs**:

- Verbatim redistribution of `BOULE1V5_0000.rad`,
  `BOULE1V5_0001.rad`, `BOULE1V5_0001.rad.orig`, `readme.txt`,
  `ref.extract`.
- The Altair-derived animation outputs (`BOULE1V5A001.gz`,
  `BOULE1V5A011.gz`, `BOULE1V5A021.gz`) — these are simulation data
  produced from the Altair-derived deck.

**The CC BY-NC 4.0 boundary does NOT propagate to**:

- The adapter source code (`backend/app/adapters/openradioss/`) —
  MIT.
- The test suite (`tests/test_openradioss_adapter.py`) — MIT.
- The `OpenRadiossReader` Protocol implementation — MIT.
- Any other MIT code in this repository.

For commercial redistribution of the GS-100 fixture verbatim
(e.g. embedding it in a commercial DOCX template demo), the fixture
must be replaced with a non-Altair-derived equivalent. **GS-101**
(W7e, deferred per RFC-002 §4.1) will be authored from scratch
precisely to remove the NC qualifier from the bullet-vs-plate demo
path.

### 4.2 Other GS-* fixtures

The `golden_samples/<id>/` registry is the canonical inventory of
fixtures and their license terms. Each ADR-registered GS-* directory
ships a README naming its license. When in doubt, **do not
redistribute** without checking the ADR.

---

## 5. Mixed-license summary

| Component | License | Boundary |
|---|---|---|
| Project Python / TypeScript / docs | MIT | This repo |
| OpenRadioss solver binary | AGPL-3.0 | Out-of-process, upstream releases |
| CalculiX solver binary | GPL-2.0+ | Out-of-process, upstream releases |
| vortex_radioss parser | MPL-2.0 | File-level; we import, do not vendor |
| GS-100 fixture (decks + Altair animation outputs) | CC BY-NC 4.0 | Per-fixture |
| Future fixtures | Per-fixture (see ADR) | Per-fixture |

**Practical guidance for downstream users**:

- Embedding this project's MIT code in a commercial product: **OK**.
- Calling OpenRadioss / CalculiX out-of-process from a commercial
  product: **OK** — the AGPL/GPL boundary is on the solver process,
  not on a network/IPC consumer. Verify with counsel for your
  specific deployment.
- Redistributing the GS-100 fixture verbatim in a commercial product:
  **NOT OK** — replace with a non-Altair-derived equivalent first.
- Redistributing the OpenRadioss solver binary as part of a
  commercial product: **AGPL applies** — consult OpenRadioss
  upstream and/or counsel.

---

## 6. Updates

- New solver added → §2.N + §3.N if it pulls a new Python parser.
- New fixture added → §4.N pointing to that fixture's ADR.
- Anyone tightening or loosening upstream licenses → update §2 / §3
  in the same PR that updates the lockfile or container recipe.

This document is maintained alongside the code; if it gets stale,
file an issue rather than acting on it.
