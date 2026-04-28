# ADR-022: GS-101-demo-unsigned — Functional bullet-penetration demo (NOT signed)

- **Status:** Accepted (RFC-002 §4.1 path-(a) demo)
- **Decider:** Claude Code CLI (Opus 4.7, 1M context) — pending human-confirmation
- **Date:** 2026-04-28
- **Related Phase:** RFC-001 §6.4 W7 (OpenRadioss adapter v1) → RFC-002 (multi-solver workbench)
- **Branch:** `feature/GS-101-demo-unsigned-fixture`
- **Companion ADRs:** ADR-021 (GS-100 smoke fixture); future ADR registering signed `GS-101` per RFC-002 §4.1.
- **Upstream:** RFC-002 §4.1 path (a) — "use Altair upstream QA bullet test" path

---

## Context

ADR-011 §HF1 #7 declares `golden_samples/<id>/` a forbidden zone:
adding a new GS bundle requires an ADR. ADR-021 registered GS-100 as a
narrowly-scoped *smoke* fixture (contact-only, zero erosion); future
ADR will register the actual signed `GS-101` (Johnson-Cook + verified
parameters + physics signoff per RFC-002 §4.1 acceptance gate).

This ADR registers an **intermediate** fixture between those two:
**GS-101-demo-unsigned**, a *functional* but explicitly *unsigned*
demo bundle that exercises the W7 stack end-to-end against a Johnson-
Cook deck while we wait for the proper signed `GS-101`.

The motivation, per RFC-002 §4.1: GS-101 (signed) is gated on a
physics engineer review channel that does not currently exist. The
W7 stack (Layers 1-4 + tools/openradioss/) is built and works. The
gap is a worked example demonstrating "the path is built". Without
an in-repo demo:

- New engineers cannot see what a J-C ballistic run looks like end-
  to-end without first sourcing their own deck.
- The no-perforation evidence-cite path in `draft.py` (companion W7f
  fix) has no in-repo fixture to regression-test against.
- The reproducibility of "Altair QA → bake → reader → derivation →
  DOCX" is undocumented.

---

## Decision

`golden_samples/GS-101-demo-unsigned/` registered as a **demo** fixture
under explicit "DEMO ONLY — parameters NOT validated" banner. The
suffix `-demo-unsigned` is a load-bearing label: `golden_samples/`
consumers MUST NOT treat this fixture as carrying any engineering
warranty. The README's leading block enumerates the things this
fixture is *not* before any positive description of what it is.

### Origin

Derived from OpenRadioss QA test
`qa-tests/miniqa/INTERF/INT_25/hexa8/data/model_00_*.rad` (model ©
Altair Engineering Inc., CC BY-NC 4.0). Selected from 24 candidate
J-C decks across the QA tree because:

1. Smallest deck (60 KB starter, single hexa8 mesh, single shell
   plate) that exercises both `/MAT/PLAS_JOHNS` plasticity and
   `/FAIL/JOHNSON` failure.
2. Self-contained — no `#include` dependencies on un-vendored upstream
   files, unlike GS-100's `qadiags.inc` requirement.
3. Runs to completion in <3 seconds wall on Apple Silicon — fast
   enough that bake-on-demand is reasonable.

### Modifications from upstream

Three modifications, preserved as audit trail:

1. **Engine deck** (`model_00_0001.rad`): added `/ANIM/DT 0. 0.3` plus
   `/ANIM/BRICK/EPSP`, `/ANIM/SHELL/EPSP`, `/ANIM/SHELL/TENS/STRESS/ALL`,
   `/ANIM/BRICK/TENS/STRESS`. The upstream engine deck has no `/ANIM/DT`
   so no animation frames are written; without frames the W7 reader
   has nothing to ingest.
2. **Engine deck** (`model_00_0001.rad`): trimmed `/RUN` from 5 ms to
   3 ms. The upstream 5 ms run errors at cycle 8000 with `ERR=−25.4%`
   energy violation (preserved in `upstream-ref.extract`); 3 ms gives
   `NORMAL TERMINATION` at 4777 cycles with `ERR=−7.4%`.
3. **Starter deck** (`model_00_0000.rad`): added `/FAIL/JOHNSON/4` for
   the steel material. Upstream steel has no failure criterion at all,
   so the steel plate cannot erode under any loading. The added
   parameters (D1=0.1, D2=0.1, D3=−0.1, Ifail_sh=2) mirror the upstream
   aluminum values — these are **placeholder values**, not real J-C
   steel failure parameters.

The pristine upstream files are preserved as `model_00_0001.rad.orig`
and `upstream-ref.extract` for audit.

### Bundle contents (62 KB total — no animation frames shipped)

| Path | Why |
|---|---|
| `data/model_00_0000.rad` | Starter (modified) — required for bake |
| `data/model_00_0001.rad` | Engine (modified) — required for bake |
| `data/model_00_0001.rad.orig` | Pristine upstream engine — audit trail |
| `data/upstream-ref.extract` | Upstream reference — shows the 5 ms run aborts |
| `README.md` | DEMO banner + attribution + bake recipe |

Animation frames are deliberately not vendored. Bake takes ~3 s in
the openradioss:arm64 container; shipping the output set would add
~35 KB without value (the bake-on-demand path is itself the
demonstration).

### What this fixture exercises

Beyond GS-100:

- 11-frame multi-state (vs. GS-100's 3) — exercises per-step audit
  binding harder.
- Significant nodal motion (peak |u|=125 mm vs. GS-100's near-rigid
  contact) — exercises peak-displacement-history derivation.
- Erosion-aware reader path against `delEltA` reporting actual zero
  shell deletions — the formerly-unflagged W7f no-perforation
  evidence-cite path (companion fix in `draft.py`).

### Self-pass-rate context

The signed-fixture acceptance gate from RFC-002 §4.1 is:

1. D1..D5 parameters compared against published experimental data
2. Erosion-time-step series within ±10% of published bullet-vs-plate
   experiments
3. Physics engineer signature

This fixture passes **none** of those. The "demo unsigned" naming is
the explicit acknowledgment.

---

## Consequences

**Positive:**

- The W7 stack now has an in-repo end-to-end demo against a J-C deck.
  New engineers can exercise the full pipeline from `git clone` in
  ~5 minutes.
- The W7f no-perforation evidence-cite path (which GS-100 cannot
  exercise because GS-100 has no J-C failure setup at all) has a
  fixture to regression-test against.
- RFC-002 §4.1 path (a) is no longer aspirational — it is a
  reproducible recipe in `golden_samples/GS-101-demo-unsigned/`.

**Negative:**

- A `golden_samples/` entry exists that is explicitly NOT
  engineering-grade. Mitigation: `-demo-unsigned` suffix and leading
  README banner are both load-bearing. The fixture name itself
  prevents accidental treatment as a signed sample.
- Risk that the placeholder J-C parameters get copy-pasted into other
  contexts. Mitigation: README banner explicitly enumerates
  "do NOT use this fixture for" cases. ADR-022 itself is searchable
  for this concern.

**Neutral:**

- Adds one more path to `golden_samples/`. Retire when a real signed-
  off `GS-101` lands per RFC-002 §4.1 — the same PR that adds the
  signed fixture should remove this one.

---

## Alternatives considered

1. **Wait for signed GS-101.** Rejected — the wait is open-ended (no
   physics review channel currently exists). The W7 stack would
   remain undemoed in-repo indefinitely.

2. **Ship a demo outside `golden_samples/`** (e.g., in `tests/fixtures/`
   or `examples/`). Rejected — `tests/fixtures/` is for testing, not
   engineering demonstration; `examples/` doesn't exist as a top-level
   path. `golden_samples/` is the documented "real cases" namespace,
   and the gap this fixture fills is a real-cases gap (not a test
   gap).

3. **Author a new deck from scratch.** Rejected — would require the
   same physics review channel that's blocking GS-101. Using the
   Altair upstream deck inherits its calibration and license.

4. **Skip the `-demo-unsigned` suffix and just call it `GS-101`.**
   Rejected — collides with the future signed `GS-101`, and the
   suffix is the load-bearing safety label.
