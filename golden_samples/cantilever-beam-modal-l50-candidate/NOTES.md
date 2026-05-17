# cantilever-beam-modal-l50-candidate · NOTES

> **Phase 27 A** — 7th tier_2_validated case. Second modal case at
> the slenderness extreme (L/h = 50, 4× more slender than Phase 26 A's
> L/h = 25). Validates the Euler-Bernoulli envelope across 4× the
> slenderness range.

## Geometry

- `data/cantilever_modal_l50.geo` — 1.000 m × 0.020 m × 0.020 m steel beam.
- L / max(h, w) = 50 (well inside Euler-Bernoulli slender-beam
  envelope ≥ 10; 5× the validity threshold).
- Origin at the clamped end (x=0 face fully fixed). Free end at x=L.
- Vibration direction is +y (height); rectangular cross-section
  yields a degenerate doublet at modes 1+2 (as verified in Phase
  26 A and reconfirmed here).

## Cross-check (Phase 27 A)

- **Runner:** `backend/app/services/cross_check/cantilever_modal_runner.py`
  (Phase 26 A; reused verbatim — Phase 27 A is purely a NEW GEOMETRY
  + REGISTRY ENTRY, no runner change).
- **Analytical:** Same Euler-Bernoulli clamped-free closed-form as
  Phase 26 A: `f_1 = (β_1·L)² · √(EI / (ρA)) / (2π · L²)` with
  β_1·L = 1.875104. At L = 1.000 m, f_1 ≈ 16.71 Hz (vs Phase 26 A's
  66.84 Hz at L = 0.500 m); scaling 1/L² holds to machine precision.
- **Material:** steel-S355 (E = 210 GPa, ν = 0.3, ρ = 7850 kg/m³).
- **BC:** all 3 DOFs clamped on the x=0 face.
- **Solver:** `*FREQUENCY 5` Lanczos eigenvalue extraction.
- **Tolerance:** 12% (honest envelope inherited from Phase 26 A).

## Live run (2026-05-17)

- Analytical f_1 = 16.7103 Hz
- Observed   f_1 = 16.7331 Hz
- **Residual: +0.136%** (virtually identical to Phase 26 A's +0.13%
  at L/h = 25; 11.86% margin to 12% tolerance — the second-tightest
  residual across all 7 validated cases, splitting hairs with Phase
  26 A's first place).
- Mesh: 2,216 nodes / 993 C3D10 quadratic tets (cl_max = 0.020 m,
  element_order = 2).
- Slender ratio L/h = 50.

Full 5-mode eigenfrequency list (ascending):
1. 16.73305 Hz (bending mode 1, y-direction)
2. 16.73328 Hz (bending mode 1, z-direction — degenerate doublet)
3. 104.6872 Hz (bending mode 2, y-direction)
4. 104.6889 Hz (bending mode 2, z-direction)
5. 292.3426 Hz (bending mode 3 OR first torsional)

Mode-3 / mode-1 ≈ 6.26 matches the Euler-Bernoulli prediction
`(β_2/β_1)² ≈ 6.27` to within 0.2%. Mode-5 / mode-1 ≈ 17.47 (vs
Phase 26 A's 17.24 at L/h = 25) matches `(β_3/β_1)² ≈ 17.55` to
within 0.5%. Mode hierarchy is preserved at this aspect ratio.

## Why this 7th case matters

Phase 26 A validated cantilever modal at L/h = 25 (well inside
Euler-Bernoulli regime). A SECOND case at L/h = 50 doubles the
slenderness and exercises the SAME analytical helper at a far more
extreme aspect ratio. The +0.136% residual virtually matches Phase
26 A's +0.13% — confirming the Euler-Bernoulli envelope is
trustworthy across 4× the slenderness range, not just a lucky
single-aspect-ratio fit.

The case ALSO validates the runner's anti-gaming guard A:-1
(rigid-body-mode filter) holds at the slender extreme: the
lowest eigenfrequency is 16.73 Hz, still 1.5 orders of magnitude
above the 1.0 Hz reject threshold. If a Lanczos rigid-body
artifact at ~10⁻⁶ Hz had slipped through, the filter would have
caught it.

## Honest scope (绝对诚实客观)

This case does NOT lift FEA Dim 1 (element library still
C3D10/B31/C3D4/C3D8; no shell, no contact, no membrane).
This case does NOT lift FEA Dim 4 (solver kind still
`*FREQUENCY`; same as Phase 26 A).
This case DOES lift FEA Dim 2 (validated count 6 → 7) and FEA
Dim 3 (envelope honesty across aspect ratios).

The original Phase 27 blueprint targeted a shell-element S4 case
to lift Dim 1; reconnaissance revealed that CalculiX shell output
goes through internal node expansion requiring non-trivial
extension of `app/adapters/calculix/reader.py`. Shell elements
deferred to a dedicated future phase. Documented verbatim in
Phase 27 blueprint and Phase 27 retro.

Not signed validation; not benchmark agreement.
