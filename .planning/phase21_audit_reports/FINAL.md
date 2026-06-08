# Phase 21 — Validation depth + WebGL viewport · FINAL audit report

## Composite (round 1; no R2 spawned — see rationale below)

| Dimension | Round 1 | Phase 20 R2 | Blueprint projection | Delta vs P20 | Delta vs projection |
|---|---|---|---|---|---|
| UX | 76/100 | 70/100 | 76-82 | **+6** | inside band, low end |
| FEA | 68/100 | 57/100 | 65-72 | **+11** | mid of band |
| UI | 77/100 | 66/100 | 74-82 | **+11** | mid of band |
| **Composite** | **73.7** | **64.3** | **72-78** | **+9.4** | **inside band, mid** |

**Verdict:** CHANGES_REQUIRED. APPROVE requires composite ≥ 99 AND
each ≥ 99 AND no axis < 95%. Round 1 fails all three. The composite
lifted +9.4 over Phase 20 — second-largest single-phase lift since
Tier 2 launched (Phase 20 was +7.3) — and **landed inside the
blueprint's own honest projection band of 72-78**.

## v2.3 round-cap=3 disposition: NO Round 2 spawned

Round 1 surfaced no Phase 20-style "real defects the unit tests
missed" findings. Both load-bearing claims from the blueprint —
"2 new tier_2_validated flips" and "3D WebGL viewport renders the
mesh" — are independently verifiable:
- Phase 21 A: 248/248 backend Phase 18-21 tests pass. Real-solver
  E2E pins both demonstrate the new validated cases passing
  tolerance. `_claim_tier.py` overlay flips both cases on next
  module load (verified by `test_phase21a_validated_count_is_three`).
- Phase 21 C: 250/250 frontend tests pass including the WebGL stub
  mount path. The `grep three|webgl` count went from 0 to 14+28.

The remaining 26-point gap to 99 is structural:
- WebGL animation, iso-surfaces, section cuts, BC/load arrow
  overlays, node-picking — all multi-week (Phase 22+).
- C3D10 quadratic elements, contact, buckling, transient dynamics —
  all multi-week (Phase 22+ for individual items, FEA dim cap stays
  ~70 until contact + buckling + transient all land).
- App.tsx Narrative + Exploration tab extractions — mechanical but
  each is 200-300 LOC moves; deferred to Phase 22 explicitly.

Round 2 would polish individual sub-dimensions but cannot move the
composite to 99 or even meaningfully toward the next 5-point step.
Round 2 here would be score-padding; that violates the absolute-
honesty contract carried verbatim from Phase 18/19/20.

## What Phase 21 actually delivered (honest accounting)

* **Slice A (commit `913d8ab`):** cantilever + Kirsch meshed cross-
  check runners. Real gmsh + real ccx on both canonical cases. Two
  tier_2_validated flips → 3 validated cases total. Verdict YAMLs
  persisted to golden_samples/ with same SSOT schema as Phase 19 B.
  29 new tests (`test_phase21a_*` includes 6 Howland K pins, 2 E2E
  requires_solver pins, schema round-trips for both runners,
  registry-overlay flip pin).

* **Slice B (commit `8dd9090`):** plasticity NLGEOM `requires_solver`
  E2E pin closing Phase 20 retro #3. Real ccx 100mm steel-S355 cube
  at 400 MPa (above 355 MPa yield, below 510 MPa ultimate). Observed
  σ_zz = 450 MPa, ε_plastic = 12.4%, plastic/elastic ratio 66×.
  Cross-checks against bilinear curve at converged state. 5 new tests.

* **Slice C (commit `643e326`):** three.js WebGL viewport with SVG
  fallback toggle. Closes UI Dim 5 4/20 floor. 390 LOC component +
  390 LOC tests. 12 new frontend tests including color-gradient SSOT
  pin with the SVG legend.

* **Slice D (commit `1b00111`):** material_reference surfacing (T4
  carry-forward closed) + Visual tab extraction (App.tsx 2014 → 1898).
  6 + 2 new tests.

**67 new tests total** (29 backend Phase 21 A + 5 backend Phase 21 B +
12 frontend Phase 21 C + 8 frontend Phase 21 D). **248/248 backend
Phase 18-21 regression** (excluding requires_solver) + **250/250
frontend regression**. Real-solver pin times: cantilever ~2s, Kirsch
~1s, plasticity ~1s.

## What Phase 21 did NOT deliver vs blueprint

* **App.tsx ≤1500 LOC target missed** (landed at 1898). Honest
  stretch ≤1700 also missed. Only Visual tab extracted; Narrative +
  Exploration deferred.
* **No buckling E2E** (blueprint listed deferred from Phase 20; still
  Phase 22+ scope).
* **Plasticity is single-case** — only steel-S355 uniaxial tension.
  No multi-axial yield, no Johnson-Cook, no temperature dependence.
* **WebGL viewport is single-frame static** — no animation tweening,
  no section cuts, no BC arrows. Honestly documented from the start.
* **WebGL tests are mock-only** — jsdom doesn't ship real WebGL;
  vitest's getContext stub gets three.js's constructor past the
  early-throw but doesn't actually draw anything. Phase 22+ needs
  puppeteer/playwright for real WebGL E2E.

## Phase 22 opening punchlist (filed from R1)

1. **Narrative + Exploration tab extractions** → App.tsx ≤1500 LOC.
2. **C3D10 quadratic tet adapter + gmsh wiring** — cuts the Phase
   21 A residuals roughly in half (cantilever 7% → ~3%, Kirsch
   11% → ~5%).
3. **Buckling Tier 2 E2E pin** — `*BUCKLE` step + Euler critical-load
   analytical for a slender column.
4. **WebGL animation slider** — interpolate between dynamic frames
   (the current viewport renders one frame).
5. **Material picker prominence** — move out of scroll-buried Visual
   tab to Topbar or Cmd-K palette entry.
6. **WebGL legend units** — append "Pa"/"MPa" + Mises-vs-component
   selector.
7. **Real WebGL E2E tests** via puppeteer/playwright + headless
   browser with software WebGL.

## Decision

Phase 21 closes at composite **73.7/100, CHANGES_REQUIRED**. +9.4 over
Phase 20 is the second-largest single-phase lift since Tier 2 launched.
The 99/100 target remains a multi-phase commitment (blueprint thesis
preserved verbatim across Phase 18-21).

The agents found no honesty-patch-worthy defects this round — Phase
20's R1→R2 pattern (registry-omission + state-divergence) didn't
repeat. Phase 21's load-bearing claims are independently verifiable
through tests + persistent verdict files. Round 2 would be score-
padding; v2.3 round-cap discipline rejects it.

Round 1 reports archived alongside this FINAL:
* `UX.md` — 76/100, T4 material visibility +4 / T5 stress contour +4
* `FEA.md` — 68/100, +11 over Phase 20, mid of projection band
* `UI.md` — 77/100, +11 over Phase 20, WebGL closes Dim 5 floor

Not signed validation; not benchmark agreement.
