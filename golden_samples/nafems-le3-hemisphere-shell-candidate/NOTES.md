# NAFEMS LE3 — Hemispherical shell with point loads (CalculiX solver-limit study)

> **This is NOT a benchmark agreement.** It is an honest record of a CalculiX
> capability boundary. ccx converges to **ux@A = 0.2004 m**, **+8.3%** above the
> NAFEMS thin-shell reference of **0.185 m**. Claim tier: **Tier-0 software-path +
> documented limitation** — deliberately excluded from the tier_2 validated cohort.

## What this case is

The repo's first attempt at a *shell / curved-geometry / bending* public benchmark,
after two solid benchmarks (LE10 thick-plate stress, LE11 solid thermo-elastic).
NAFEMS LE3 is the canonical thin-shell point-load test: a hemisphere (R = 10 m,
t = 0.04 m, R/t = 250), two pairs of 4 kN point loads on the equator free edge (one
pair outward on X, one inward on Y), modelled as a 90° quarter by double symmetry.
The reference x-displacement at the outward-loaded point A is **0.185 m**.

## What ccx computes — and why it disagrees

ccx 2.23, quadratic S8R shells, converges monotonically to **0.2004 m**:

| na/edge | shell nodes | ux@A (m) | residual vs 0.185 |
|--------:|------------:|---------:|------------------:|
|       8 |         209 |  0.19562 |            +5.74% |
|      16 |         801 |  0.19976 |            +7.98% |
|      24 |        1777 |  0.20020 |            +8.22% |
|  **32** |    **3137** | **0.20033** |        **+8.29%** |
|      40 |        4881 |  0.20037 |            +8.31% |

The residual **grows** with refinement and **stabilises at +8.3%** — so this is a
*formulation* gap, not a discretisation error. Both S8R (reduced integration) and
S8 (full integration) converge to the same ~0.2004 (S8 merely membrane-locks at
coarse meshes, then climbs to the same value); linear S4 locks rigid (~4e-5 m).

**Root cause.** CalculiX has **no true thin-shell element**. Every shell is
*expanded to a solid brick* — `S8R → C3D20R`, `S6 → C3D15`. A concentrated load on
a solid shell creates a local through-thickness 3-D "dimple" that thin-shell
(Kirchhoff/Mindlin) theory does not contain. On a very thin, bending-dominated,
point-loaded shell that local flexibility adds ~8% to the displacement read **at**
the loaded node.

## Independent cross-check (this is the convincing part)

Altair OptiStruct OS-V:0030 solves the *same* benchmark with **CQUAD4** — a true
first-order **thin shell** — and converges **down** to the reference:

| mesh/edge | OptiStruct (normalized) | value (m) |
|----------:|------------------------:|----------:|
|         4 |                  0.9865 |   0.18250 |
|         8 |                  1.0200 |   0.18870 |
|        16 |                  1.0076 |   0.18641 |
|        32 |                  1.0032 |   0.18559 |
|        64 |                  1.0016 |   0.18530 |

Thin-shell converges **down to 0.185**; ccx solid-shell converges **up to 0.2004**.
The two element families **bracket** the answer from opposite sides — strong
evidence that the +8.3% is the documented thin-vs-solid-shell divergence under a
point load, on **both** of which the elements are behaving correctly.

## Why we did NOT make this "pass"

Two ways to make ccx read ~0.185 were rejected as dishonest:
1. **Cherry-pick a coarse mesh.** ccx passes *through* ~0.196 on its way up; reading
   a coarse rung and calling it converged would be gaming.
2. **Distribute the point load** over a small patch to soften the 3-D dimple. That
   changes the NAFEMS load definition specifically to hit the target — gaming.

Instead we record ccx's true converged number and its cause.

## ccx-shell lessons (each cost a P0 debugging round)

1. **Read by coordinate, not node id.** ccx renumbers/expands shell nodes; the
   original input node id reads ≈ 0. The real displacement lives on the expanded
   node sitting at the target coordinate. (`read_ux_at` in `data/generator.py`.)
2. **Symmetry is translational-only.** Constraining rotational DOFs 4/5/6 on the
   expanded-shell symmetry edges **locks the model rigid** (ux@A → ~7e-4). The
   translational `uy=0` / `ux=0` on the original shell nodes already propagates
   through the expanded thickness and enforces symmetry correctly. (This matches
   the PrePoMax LE3 report that *unwanted* rotational-DOF BCs are a known trap.)
3. **Quadratic elements are mandatory.** Linear S4 (→ C3D8I) membrane-locks rigid.

## Provenance / honesty

- **Tier:** Tier-0 software-path + documented limitation. **Not** tier_2_validated;
  **not** a public-benchmark agreement; **not** signed.
- **Cohort exclusion is structural:** no `cross_check_verdict.yaml` here (so the
  V2-0 residual-floor glob never admits it) and LE3 is **not** in
  `CLAIM_TIER_REGISTRY` (so the tier_2 overlay never promotes it). The
  machine-readable summary is `solver_limit_finding.yaml` (a non-verdict filename).
- **Reference not purchased:** target/loads/BCs triangulated from free sources
  (OptiStruct OS-V:0030, Abaqus Benchmarks Guide LE3, PrePoMax LE3 thread). TNSB
  Rev.3 itself not bought — same disclosed limitation as LE10/LE11.
- **Reproduce:** `python golden_samples/nafems-le3-hemisphere-shell-candidate/data/generator.py [--ladder]`

## Takeaway for the project

Thin-shell point-load benchmarks (LE2 / LE3 / LE5) are **outside ccx's clean
public-benchmark envelope**. The genuine third public-benchmark *agreement* is
pursued in a ccx-strong physics instead (free-vibration / eigenvalue and solid
stress), per the FM-05 plan. Knowing where the tool *fails* is part of honest
validation — that is what this directory is for.
