# ADR-021: GS-100 — OpenRadioss adapter smoke fixture

- **Status:** Accepted (RFC-001 W7b)
- **Decider:** Claude Code CLI (Opus 4.7, 1M context) — pending human-confirmation
- **Date:** 2026-04-28
- **Related Phase:** RFC-001 W7 — multi-solver workbench pivot
- **Branch:** `refactor/RFC-001-W7b-openradioss-adapter`
- **Companion ADRs:** ADR-019 / ADR-020 (W6 material data); future ADR-022 will register GS-101 (full ballistic case, W7e).
- **Upstream:** RFC-001 §6.4 W7 ("OpenRadioss adapter as v1 reference adapter")

---

## Context

Per ADR-011 §HF1 #7 the `golden_samples/<id>/` namespace is a forbidden
zone — adding a new GS bundle requires an ADR. W7b's adapter
(`backend/app/adapters/openradioss/`) needs a representative OpenRadioss
output set to validate the Layer-2 Protocol implementation. Without a
fixture the adapter is unverifiable; with a fixture but no ADR, ADR-011
HF1.7 blocks the commit.

This ADR registers **GS-100** as an OpenRadioss-adapter **smoke** fixture
— deliberately scoped *narrower* than a typical golden sample. It is not
a self-contained engineering case (no PASS/FAIL judgement, no
signing-engineer audit trail); it exists only to exercise the adapter's
plumbing against a tiny, real OpenRadioss output set.

W7e will register a separate **GS-101** golden sample for the actual
bullet-vs-plate ballistic demo with Johnson-Cook + element erosion.
Splitting smoke from demo lets W7b's adapter PR land independently of
the larger ballistic-case engineering work.

---

## Decision

`golden_samples/GS-100-radioss-smoke/` registered as a smoke fixture
with the following invariants:

### Origin
Derived from OpenRadioss QA test
`OpenRadioss/qa-tests/miniqa/INTERF/INT_7/igsti/small_boule_igsti/dtmin_02/`
(ball-impact contact verification, model © Altair Engineering Inc.,
licensed CC BY-NC 4.0).

Modifications from upstream (preserved in `BOULE1V5_0001.rad.orig` for
audit):

- `/RUN/BOULE1V5/1` run-time `0.0025 ms` → `0.5 ms`. The original ran
  for 1 cycle (0 frames); we extend to 7903 cycles to populate
  multi-frame time history.
- `/ANIM/DT 0. 0.05` → `0. 0.025`. Halves dump cadence so 21 frames
  are produced in 0.5 ms; we ship 3 representative ones.

### Bundle contents (60 KB total)
| Path | Why |
|---|---|
| `BOULE1V5_0000.rad` | Starter deck — required for reproduction |
| `BOULE1V5_0001.rad` | Engine deck (modified) — required for reproduction |
| `BOULE1V5_0001.rad.orig` | Pristine upstream engine deck — audit trail |
| `BOULE1V5A001.gz` | t=0.0 ms reference frame |
| `BOULE1V5A011.gz` | t=0.25 ms mid-run frame |
| `BOULE1V5A021.gz` | t=0.5 ms final frame |
| `readme.txt` | Altair upstream description |
| `ref.extract` | Altair upstream reference values |
| `README.md` | Our fixture-specific contract documentation |

### Adapter contract this fixture exercises
- Mesh extraction (114 nodes, 74 facets, 3 parts).
- Multi-state time-history reading (3 `SolutionState`s with monotonic time).
- Reference-frame DISPLACEMENT reconstruction (`coorA[t] - coorA[0]`).
- Empty field-data path: `vTextA`/`tTextA`/`fTextA` all empty in this
  legacy deck — adapter must report `STRESS_TENSOR` etc. as
  unavailable, not fabricate zeros (ADR-003 enforcement).
- `delEltA` element-deletion array shape + alive count (74/74 alive in
  this contact-only test).

### What this fixture explicitly does NOT exercise
- Element erosion under failure criteria (none in contact test).
- Stress / strain / velocity field extraction (legacy deck syntax
  doesn't accept modern `/ANIM/NODA/VEL` etc.; verified W7a probe).
- Johnson-Cook / strain-rate plasticity.
- Self-contact bullet→plate.

These all land in **GS-101** (W7e) via a fresh deck written from scratch.

---

## Why a separate smoke fixture (not just GS-101)

1. **Adapter PR independence** — W7b's adapter can ship + Codex-review
   + merge without dragging in the much larger W7d (Layer-3 ballistic
   derivations) + W7e (full ballistic case) + W7f (DOCX template) work.
2. **CI cost** — at 60 KB total this fixture barely registers in
   repo size. GS-101 will be ~20-50 MB (binary `.A###.gz` + .h3d).
3. **Failure-isolation** — when GS-101 breaks (bigger surface, more
   physics), GS-100 still exercises the adapter plumbing so we can
   tell "adapter regression" from "ballistic-physics regression".
4. **Honest scope** — explicitly labeling this `radioss-smoke` (not
   `radioss-demo`) keeps future readers from mistaking the fixture
   for something it isn't.

---

## Licensing

- Upstream model © Altair Engineering Inc., **CC BY-NC 4.0**. Re-
  distribution permitted with attribution; non-commercial qualifier
  honored — this repo is open-source research / engineering tooling,
  not a commercial product.
- Modifications (run-time + dump dt extensions) are minor parametric
  changes that don't constitute a derivative work in any material
  sense. Original deck preserved for verification.
- Animation outputs (`.A###.gz`) are produced by running the modified
  deck through OpenRadioss (AGPL-3.0) on the host. The output files
  themselves are not subject to AGPL because they are pure data, not
  copyrighted code.

W7g RFC-002 will formalize the multi-license boundary across the
workbench. For W7b, this fixture's redistribution is uncontroversial.

---

## Migration / backwards-compat

- The `HF1.7` golden-samples guard now sees an ADR registering
  `GS-100-radioss-smoke/`; commits touching this directory must
  cite ADR-021.
- No prior GS bundle is altered. GS-001 (CalculiX wedge) remains the
  primary signing-grade fixture.

---

## Open questions deferred to user

1. **Naming convention for non-signing fixtures**: Should smoke /
   plumbing-test fixtures use a separate prefix (`SMOKE-100`)? Or
   continue with `GS-NNN-<scope>` and document scope in the bundle's
   README? (Default: latter — already what GS-100 does.)
2. **Cleanup of pristine-original**: Keep `BOULE1V5_0001.rad.orig` in
   the bundle, or move audit copies to a separate
   `_attribution/` dir? (Default: keep alongside; size negligible
   and co-located audit beats split-directory hunting.)

---

## Revision history

| Version | Date | Notes |
|---|---|---|
| 0.1 | 2026-04-28 | Initial — registers GS-100 to satisfy ADR-011 HF1.7 |
