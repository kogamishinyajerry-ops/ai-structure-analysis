# cantilever-buckle-candidate · NOTES

> **Phase 28 A** — 8th tier_2_validated case. Second buckling case
> at the **fixed-free (cantilever) end condition** (k = 2.0), distinct
> from Phase 22 A's pinned-pinned (k = 1.0). Validates Euler's
> effective-length-factor discipline across the k-factor family.

## Geometry

- 1.000 m × 0.020 m × 0.020 m steel column, single-axis buckling.
- L / r = L / (h/√12) = 1.0 / 0.005774 = 173 (deep slender regime).
- Boundary: x=0 face fully clamped; x=L tip COMPLETELY FREE (no
  transverse pins). Compressive load P applied as `*CLOAD` at the
  tip node in -x direction.

## Cross-check (Phase 28 A)

- **Runner:** `backend/app/services/cross_check/buckling_b31_runner.py`
  (Phase 23 A; the same B31 Timoshenko-beam runner that already
  supports all 4 end conditions). Phase 28 A is purely a new
  geometry + registry entry — NO runner code change.
- **Analytical:** Euler's `P_cr = π²EI / (kL)²` with **k = 2.0** for
  the fixed-free condition (Timoshenko & Gere §2.4 / Roark Table
  15.1 case 2 / Bazant & Cedolin §2.2).
- **Material:** steel-S355 (E = 210 GPa, ν = 0.3).
- **Solver:** `*BUCKLE 4` Lanczos eigenvalue extraction; observed
  P_cr = λ · P_ref where λ is the lowest eigenvalue.
- **Tolerance:** 10% (inherited from Phase 22 A; Euler-Bernoulli
  buckling on B31 beams is well-conditioned).

## Live run (2026-05-17)

- Analytical P_cr (k=2.0) = 6908.7231 N
- Observed   P_cr        = 6910.7790 N
- **Residual: +0.0298%** (TIGHTEST RESIDUAL ACROSS ALL 8 VALIDATED
  CASES; 9.97% margin to 10% tolerance — the B31 beam-element
  formulation matches the 1D Euler-Bernoulli closed-form to
  3 significant digits at this aspect ratio).
- Eigenvalue: 6.910779 (P_ref = 1000 N).
- Mesh: 20 B31 elements along x; 21 nodes.

## Why this 8th case matters

Phase 22 A validated Euler buckling at the canonical k = 1.0
(pinned-pinned). Phase 28 A validates Euler buckling at k = 2.0
(fixed-free / cantilever) — the OTHER end of the slender-column
k-factor family that students typically learn first (longest
effective length, smallest critical load for a given column).

The analytical `P_cr ∝ 1/(kL)²` means cantilever P_cr is 1/4 of
pinned-pinned P_cr at the same geometry/material — and the
observed residuals match the analytical at BOTH ends of the
k-factor family to under 0.3%. This pins the effective-length-
factor discipline at two points; clamped-pinned (k=0.7) and
clamped-clamped (k=0.5) remain candidates for future phases.

## Honest scope (绝对诚实客观)

This case does NOT lift FEA Dim 1 (element library still
C3D10/B31/C3D4/C3D8 cohort; no shell, no contact).
This case does NOT lift FEA Dim 4 (solver kind still `*BUCKLE`;
same as Phase 22 A).
This case DOES lift FEA Dim 2 (validated count 7 → 8) and FEA
Dim 3 (envelope honesty across k-factor family).

## Honest scope record — C3D8 hex cantilever attempt (rejected)

The Phase 28 A blueprint originally proposed extending the
**existing C3D8 hex runner** (`buckling_runner.py`) with a
`_write_cantilever_buckle_inp` composer for the cantilever case.
Implementation attempt produced a 256% residual (observed
24622 N vs analytical 6908 N) — about 3.6× the analytical.

Root cause: linear C3D8 hex elements suffer severe shear locking
when a single hex through the thickness is fully clamped at one
end. Phase 22 A's pinned-pinned worked because end rotation
freedom relieved the locking; cantilever's fully-clamped base
exposes it.

The C3D8 attempt is preserved as `_write_cantilever_buckle_inp`
in `buckling_runner.py` for documentation (with explicit
NotImplementedError if anyone tries to dispatch to it). The
canonical Phase 28 A path uses Phase 23 A's B31 Timoshenko-beam
runner which avoids locking entirely.

Documented honestly in commit message + this NOTES.md + Phase 28
retro.

Not signed validation; not benchmark agreement.
