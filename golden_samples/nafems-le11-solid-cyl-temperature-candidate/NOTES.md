# NAFEMS LE11 — Solid Cylinder/Taper/Sphere, Temperature (candidate notes)

**Second independent public-benchmark agreement** for this repo (after LE10). Real
ccx 2.23 thermo-elastic solve; σ_zz at point A = **−105.398 MPa** vs the published
**−105 MPa** → **+0.38%**, PASS (tol 3%). Tier-1 engineering candidate /
public-benchmark agreement — **NOT signed validation** (no independent reviewer
signoff per ADR-023 / ADR-027 G-2).

## Why LE11 (not LE1)

LE1 (elliptic membrane) reuses LE10's *exact elliptical planform* + pure-elasticity
+ `*DLOAD` family — a near-duplicate. LE11 is independent on **every** axis:
thermo-elastic physics (imposed temperature field, NO mechanical load), a
solid-of-revolution geometry, a new ccx keyword path
(`*INITIAL CONDITIONS,TYPE=TEMPERATURE` + `*EXPANSION` + `*TEMPERATURE` in a purely
mechanical `*STATIC` step), and a different stress component/location (σ_zz at the
inner-radius base corner). It is the single biggest evidence-coverage jump in the
NAFEMS LE pool, so it is the genuine "second benchmark."

## Source triangulation (7 FREE independent reproductions; TNSB Rev.3 NOT purchased)

| source | σ_zz(A) | notes |
|---|---|---|
| FeenoX `nafems-le11` (.geo/.fee) | −105.04 MPa | runnable; the gmsh geometry byte-oracle this case was ported from |
| Abaqus Benchmarks Guide (MIT mirror) | −105 MPa | "Direct stress, sigma_zz = −105 MPa at point A" |
| bConverged LE11 | −105 MPa | "vertical stress at the lower inside corner is −105 MPa" |
| FEATool | −105e6 Pa | explicit meridian vertices |
| Altair OS-V:0070 | −105 MPa | multi-element (Hex20/Pyr15/Tet10) |
| OnScale Solve | −105 MPa | validation case |
| DIANA FEA | −1.05e8 Pa | six element variants |

Magnitude **and negative (compressive) sign** are unanimous. Primary NAFEMS TNSB
Rev.3 was **not** purchased/fetched; the target rests on these secondary
reproductions — the project's accepted Tier-1/2 standard (identical disclosed
limitation as LE10).

## Honest caveats

1. **TNSB not fetched** — geometry, temperature field, and target rest on the 7
   free reproductions above, not the primary document.
2. **Temperature field** is `T = sqrt(x²+y²) + z` (cylindrical radius + height).
   The Abaqus-MIT HTML page rendered it with the `sqrt` radical dropped
   (`(x²+y²)+z`); the other six sources + the FeenoX `.fee` confirm `sqrt`. The
   `sqrt` form is used (and verified: it reproduces −105 MPa; the no-sqrt form
   would not).
3. **Young's modulus** is E = 210 GPa (NAFEMS canonical, cited by Abaqus-MIT and
   the synthesis). The FeenoX `.fee` uses E = 2.11e11 Pa (211 GPa, a 0.5%
   deviation); thermal stress scales ∝ E, so this shifts the result ≤0.5% —
   inside the 3% tolerance either way. 210 GPa is pinned for fidelity to the spec.
4. **Point A** is a re-entrant inner-radius base corner → mesh-sensitive. The
   claim is backed by a **monotone convergence ladder** (88→5632 el), and the
   **converged (finest, 5632-el) value −105.398 MPa is pinned canonical** — not
   the rung nearest −105 (which would be the 2376-el +0.11% rung). This avoids
   cherry-picking.
5. **Sign** is normalized to ccx's own tension-positive output convention
   (unanimous compressive across all sources).
6. **ccx capability is empirically confirmed on this binary**: the thermal-stress
   keyword triple is exactly what ccx 2.23 ships in `beamt.inp`
   (`C3D20R + *INITIAL CONDITIONS,TYPE=TEMPERATURE + *EXPANSION,ZERO= + *STATIC +
   *TEMPERATURE`) and cross-checks against Abaqus in
   `lin_stat_initial_temp_condition.inp` (`.frd.ref`/`.dat.ref`).

## Reproduce

```
python golden_samples/nafems-le11-solid-cyl-temperature-candidate/data/generator.py --ladder
```

Convergence ladder (real ccx 2.23, C3D20):

```
r=1 | el=  88 | sigma_zz@A = -102.491 MPa | resid -2.39%
r=2 | el= 704 | sigma_zz@A = -104.469 MPa | resid -0.51%
r=3 | el=2376 | sigma_zz@A = -105.116 MPa | resid +0.11%
r=4 | el=5632 | sigma_zz@A = -105.398 MPa | resid +0.38%   <- canonical
```
